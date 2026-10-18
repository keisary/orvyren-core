"""Live event hub: replays real run artefacts over the WebSocket.

The runs are **recorded artefacts** (the pipeline is never launched from the
API): the hub walks the hash-chained journals of a run and pushes each line as
it would have appeared live — the same envelope as the spec (``type``, ``seq``,
``run_id``, ``ts``, ``payload``), with a monotonic ``seq``, a ring buffer for
``since_seq`` resume, subscribe channels (``run:<id>``, ``market:<episode>``)
and a heartbeat. Clients that miss events get a ``resync`` and refetch REST.

Uses asyncio primitives tied to FastAPI's loop, but imports no web framework:
``fastapi`` stays lazily imported in :mod:`orvyren.api.main`.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set

from orvyren.api import artifacts
from orvyren.api.config import Settings, load_settings


class LiveHub:
    """Single producer + broadcast fan-out (FastAPI WS dashboard pattern)."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or load_settings()
        self.clients: Set[Any] = set()
        self.ring: List[Dict[str, Any]] = []
        self.seq = 0
        self.current_run: Optional[str] = None
        self.position = 0
        self._events: List[Dict[str, Any]] = []
        self._producer: Optional[asyncio.Task] = None
        self._market_tasks: Set[asyncio.Task] = set()
        self.started_at = time.time()

    # -- envelope ---------------------------------------------------------

    def envelope(self, event_type: str, payload: Dict[str, Any],
                 run_id: str = "", ts: str = "") -> Dict[str, Any]:
        self.seq += 1
        envelope = {
            "type": event_type,
            "seq": self.seq,
            "run_id": run_id,
            "ts": ts or time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "payload": payload,
        }
        self.ring.append(envelope)
        if len(self.ring) > self.settings.ring_size:
            self.ring = self.ring[-self.settings.ring_size:]
        return envelope

    def since(self, seq: int) -> List[Dict[str, Any]]:
        if seq <= 0:
            return []
        return [item for item in self.ring if item["seq"] > seq]

    # -- playlist ---------------------------------------------------------

    def load_run(self, run_id: str) -> int:
        self._events = artifacts.build_run_events(run_id, self.settings)
        self.current_run = run_id
        self.position = 0
        return len(self._events)

    def playlist(self) -> List[Dict[str, Any]]:
        if not self._events:
            runs = artifacts.discover_runs(self.settings)
            pick = ""
            for run in runs:
                if run["journals"].get("orchestrator", {}).get("present"):
                    pick = run["run_id"]
                    break
            if pick:
                self.load_run(pick)
        return self._events

    # -- fan-out ----------------------------------------------------------

    async def broadcast(self, envelope: Dict[str, Any]) -> None:
        """Send to every client; a dead OR slow client is dropped, never blocks
        the fan-out for the others (bounded per-send timeout = backpressure)."""
        dead = []
        text = json.dumps(envelope, ensure_ascii=False, default=str)
        for client in list(self.clients):
            try:
                # asyncio.timeout, NOT wait_for: an external cancellation of
                # the broadcasting task must propagate — wait_for can swallow
                # it when the send completes in the same step (bpo-46830),
                # which would make a cancelled producer immortal.
                async with asyncio.timeout(self.settings.ws_send_timeout_seconds):
                    await client.send_text(text)
            except TimeoutError:
                dead.append(client)
            except Exception:
                dead.append(client)
        for client in dead:
            self.clients.discard(client)

    async def register(self, websocket: Any) -> None:
        self.clients.add(websocket)
        if self._producer is None or self._producer.done():
            self._producer = asyncio.create_task(self.producer_loop())

    async def unregister(self, websocket: Any) -> None:
        self.clients.discard(websocket)

    async def shutdown(self) -> None:
        """Cancel the producer and any market stream — no task outlives the app."""
        pending: List[asyncio.Task] = []
        if self._producer is not None:
            self._producer.cancel()
            pending.append(self._producer)
            self._producer = None
        for task in list(self._market_tasks):
            task.cancel()
            pending.append(task)
        self._market_tasks.clear()
        if not pending:
            return
        # Bounded wait + second cancel: shutdown must never block forever even
        # if a task swallowed one cancellation.
        _done, still = await asyncio.wait(pending, timeout=5.0)
        for task in still:
            task.cancel()
        if still:
            await asyncio.wait(still, timeout=1.0)

    # -- producer ---------------------------------------------------------

    async def producer_loop(self) -> None:
        """Walk the recorded journal timeline at demo pace, forever."""
        last_beat = time.monotonic()
        while True:
            try:
                events = self.playlist()
                if self.position >= len(events):
                    self.position = 0  # loop the recorded run for the demo
                event = events[self.position]
                self.position += 1
                envelope = self.envelope(
                    event["type"],
                    {**event["payload"], "run_seq": event["seq"],
                     "run_total": len(events)},
                    run_id=event.get("run_id", self.current_run or ""),
                    ts=event.get("ts", ""),
                )
                await self.broadcast(envelope)
                if self.position >= len(events):
                    done = self.envelope(
                        "run.status",
                        {"phase": "replay_complete",
                         "run_id": self.current_run,
                         "events": len(events)},
                        run_id=self.current_run or "")
                    await self.broadcast(done)
                if time.monotonic() - last_beat > self.settings.ws_heartbeat_seconds:
                    last_beat = time.monotonic()
                    await self.broadcast(self.envelope("ping", {"hub_uptime_s": round(
                        time.time() - self.started_at, 1)}))
                await asyncio.sleep(self.settings.ws_tick_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # keep the demo alive on any hiccup
                await self.broadcast(self.envelope(
                    "resync", {"error": str(exc), "note": "client should refetch REST"}))
                await asyncio.sleep(2.0)

    # -- client commands --------------------------------------------------

    async def handle_client_message(self, raw: str, client: Any = None) -> None:
        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            return
        if not isinstance(message, dict):
            return
        mtype = message.get("type", "")
        if mtype == "ping":
            pong = self.envelope("pong", {})
            if client is not None:
                try:
                    await client.send_text(
                        json.dumps(pong, ensure_ascii=False, default=str))
                except Exception:
                    self.clients.discard(client)
            else:
                await self.broadcast(pong)
        elif mtype == "subscribe":
            channels = message.get("channels")
            if not isinstance(channels, list):
                channels = []
            raw_since = message.get("since_seq") or 0
            try:
                since_seq = int(raw_since)
            except (TypeError, ValueError):
                await self.broadcast(self.envelope(
                    "resync", {"reason": "bad_since_seq",
                               "value": str(raw_since)[:32]}))
                return
            for channel in channels:
                if isinstance(channel, str) and channel.startswith("run:"):
                    run_id = channel.split(":", 1)[1]
                    try:
                        total = self.load_run(run_id)
                    except (OSError, ValueError):
                        # Unknown or unreadable run: tell the client, never
                        # blow up its receive loop.
                        await self.broadcast(self.envelope(
                            "resync", {"reason": "unknown_run", "run_id": run_id}))
                        continue
                    await self.broadcast(self.envelope(
                        "run.status",
                        {"phase": "subscribed", "run_id": run_id, "events": total},
                        run_id=run_id))
                elif isinstance(channel, str) and channel.startswith("market:"):
                    episode = channel.split(":", 1)[1]
                    task = asyncio.create_task(self.stream_market(episode))
                    self._market_tasks.add(task)
                    task.add_done_callback(self._market_tasks.discard)
            if since_seq > 0:
                # Ring overflow = the client missed more envelopes than the
                # ring still holds: say resync instead of replaying a partial
                # window that would look complete.
                if self.seq - since_seq > len(self.ring):
                    await self.broadcast(self.envelope(
                        "resync", {"reason": "ring_overflow"}))
                else:
                    for envelope in self.since(since_seq):
                        await self.broadcast(envelope)
        elif mtype == "resync":
            await self.broadcast(self.envelope("resync", {"reason": "client_request"}))

    async def stream_market(self, episode_id: str, limit: int = 400) -> None:
        """Replay one episode's measured price points as ``market.tick``."""
        try:
            series = artifacts.episode_series(episode_id, self.settings)
            merged: List[Dict[str, Any]] = []
            for line in series.get("lines", []):
                for ts, value in line.get("points", [])[:limit]:
                    merged.append({"episode": episode_id, "series_id": line["id"],
                                   "label": line["label"], "unit": line["unit"],
                                   "time": ts, "value": value})
            merged.sort(key=lambda item: item["time"])
        except FileNotFoundError:
            await self.broadcast(self.envelope(
                "resync", {"reason": "unknown_episode", "episode": episode_id}))
            return
        except Exception as exc:  # a broken artefact must surface, not vanish
            await self.broadcast(self.envelope(
                "resync", {"reason": "episode_error", "episode": episode_id,
                           "error": str(exc)}))
            return
        for tick in merged[:limit]:
            await self.broadcast(self.envelope("market.tick", tick))
            await asyncio.sleep(0.02)
