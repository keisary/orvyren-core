#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared helpers for the ORVYREN episode-reconstruction scripts.

Nothing here is episode-specific: it provides

* repo paths (``evidence/``, ``research/raw_w2a``, ``research/raw_w2b``);
* JSON helpers with **atomic** writes, so a killed run never leaves a half
  written evidence file (the file is replaced by ``os.replace``);
* :func:`resolve_blocks` -- timestamp -> block resolution over a rising grid,
  with a sliding window and an explicit ``ts(block) <= ts < ts(block+1)`` check
  (the guarantee is what makes the "block" columns of the evidence citable);
* :func:`parallel_measure` -- a small thread pool (stdlib ``concurrent.futures``)
  that gives every worker **its own** :class:`~orvyren.data.rpc.ArchiveRpc`
  (the client is not thread-safe) and alternates the primary endpoint, so a
  2 000-call reconstruction runs in minutes instead of tens of minutes;
* :func:`load_raw` -- read a JSON file already archived in ``research/`` (the
  ``--from-cache`` fallback, used when the network is unavailable).

Standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

EVIDENCE_DIR = os.path.join(ROOT, "evidence")
RESEARCH_DIR = os.path.join(ROOT, "research")
RAW_W2A = os.path.join(RESEARCH_DIR, "raw_w2a")
RAW_W2B = os.path.join(RESEARCH_DIR, "raw_w2b")

from orvyren.data import ArchiveRpc, utc_iso  # noqa: E402  (after sys.path setup)

#: Endpoint preference per worker; workers alternate so both archives are used.
ENDPOINT_SPECS: Tuple[Tuple[str, ...], ...] = (
    ("https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"),
    ("https://eth-mainnet.public.blastapi.io", "https://eth.drpc.org"),
)

#: Measured mean block time (research/W2A): 13.35 s before The Merge, 12.09 s after.
MERGE_TIMESTAMP = 1663224179
SECONDS_PER_BLOCK_PRE_MERGE = 13.35
SECONDS_PER_BLOCK_POST_MERGE = 12.09

#: Half-width of the block window built around a linear estimate (in blocks).
BLOCK_WINDOW_MARGIN = 400

_worker_counter = 0
_worker_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_raw(name: str, *directories: str) -> Any:
    """Read a JSON file archived under ``research/`` (searching the given dirs)."""
    candidates: List[str] = []
    for directory in (directories or (RAW_W2A, RAW_W2B)):
        candidates.append(os.path.join(directory, name))
    candidates.append(os.path.join(RESEARCH_DIR, name))
    candidates.append(name)
    for path in candidates:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise FileNotFoundError(
        f"{name} not found under research/ (looked in {len(candidates)} paths, e.g. {candidates[0]})"
    )


def dump_json_atomic(path: str, payload: Any) -> None:
    """Write ``payload`` as indented JSON, replacing ``path`` atomically."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def load_partial(path: str, *, mode: str, grid_key: str) -> Dict[str, Any]:
    """Load an interrupted run's evidence file, if it matches the requested grid."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return {}
    meta = payload.get("meta") or {}
    if meta.get("mode") != mode or meta.get("grid_key") != grid_key:
        return {}
    if meta.get("complete"):
        return {}
    return payload


def merge_provenance(primary: ArchiveRpc, others: Sequence[ArchiveRpc] = ()) -> Dict[str, Any]:
    """Aggregate the call counts of every client used by a run."""
    clients = [primary] + [client for client in others if client is not primary]
    hits: Dict[str, int] = {}
    for client in clients:
        for url, count in client.url_hits.items():
            hits[url] = hits.get(url, 0) + count
    return {
        "endpoints": list(primary.urls),
        "clients": len(clients),
        "calls": sum(client.calls for client in clients),
        "errors": sum(client.errors for client in clients),
        "hits": dict(sorted(hits.items())),
        "last_url": primary.last_url,
    }


def new_client(worker_index: Optional[int] = None) -> ArchiveRpc:
    """A fresh client; ``worker_index`` selects which endpoint is primary."""
    index = worker_index
    if index is None:
        global _worker_counter
        with _worker_lock:
            index = _worker_counter
            _worker_counter += 1
    spec = ENDPOINT_SPECS[index % len(ENDPOINT_SPECS)]
    return ArchiveRpc(spec, timeout=30.0, retries=2, backoff=0.8)


def seconds_per_block(timestamp: int) -> float:
    """Measured mean block time at ``timestamp`` (The Merge changed it on 2022-09-15)."""
    return SECONDS_PER_BLOCK_PRE_MERGE if int(timestamp) < MERGE_TIMESTAMP else SECONDS_PER_BLOCK_POST_MERGE


def resolve_blocks(
    timestamps: Iterable[int],
    client: Optional[ArchiveRpc] = None,
    *,
    log: Optional[Callable[[str], None]] = None,
    max_attempts: int = 3,
) -> Dict[int, Dict[str, Any]]:
    """Map each timestamp to ``{"block", "block_ts"}`` with a verified floor.

    Three escalating attempts per point, all validated against the chain
    (``ts(block) <= target < ts(block+1)``):

    1. **estimate** -- the next block is estimated linearly from the previous point
       (cached timestamp + measured block time).  If that estimate already is the floor
       block, it is kept: 2 reads.  Otherwise a secant search runs inside a +-400 block
       window around it (~4-6 reads when the block rate behaves).
    2. **permissive window** -- ``[previous block, estimate + 4 x margin]``: the answer is
       necessarily inside it (the grid rises), which covers the episodes where the block
       rate drifts from the mean (measured: June 2022 ran at ~14.3 s/block against a
       13.35 s mean, so a 24 h step lands ~430 blocks below the estimate).
    3. **full-range search** -- anchors + bisection guard, nothing assumed.
    """
    client = client or new_client(0)
    resolved: Dict[int, Dict[str, Any]] = {}
    previous_block: Optional[int] = None
    history: List[Tuple[int, int]] = []          # (block, timestamp) of the last points
    for timestamp in sorted(int(t) for t in timestamps):
        attempt = 0
        while True:
            attempt += 1
            try:
                if previous_block is not None and attempt < max_attempts:
                    previous_stamp = client.block_timestamp(previous_block)
                    # Prefer the *local* block rate measured on the two previous points over
                    # the long-run mean: June 2022 ran at ~14.3 s/block while the mean was
                    # 13.35 s, which is enough to push a 24 h estimate out of a narrow window.
                    if len(history) >= 2:
                        (block_a, stamp_a), (block_b, stamp_b) = history[-2], history[-1]
                        span = stamp_b - stamp_a
                        rate = (block_b - block_a) / span if span > 0 and block_b > block_a else 0.0
                    else:
                        rate = 0.0
                    if rate <= 0:
                        rate = 1.0 / seconds_per_block(timestamp)
                    estimate = previous_block + int((timestamp - previous_stamp) * rate)
                    estimate = max(0, estimate)
                    if attempt == 1:
                        estimate_ts = client.block_timestamp(estimate)
                        if estimate_ts <= timestamp < client.block_timestamp(estimate + 1):
                            block, block_ts = estimate, estimate_ts
                            break
                        low = max(0, estimate - BLOCK_WINDOW_MARGIN)
                        high = max(low + 1, estimate + BLOCK_WINDOW_MARGIN)
                    else:
                        low = previous_block
                        high = max(previous_block + 2, estimate + 4 * BLOCK_WINDOW_MARGIN)
                    block = client.block_at_timestamp(timestamp, low=low, high=high)
                else:
                    block = client.block_at_timestamp(timestamp)
                block_ts = client.block_timestamp(block)
                next_ts = client.block_timestamp(block + 1)
            except Exception as exc:
                if attempt >= max_attempts:
                    raise
                if log:
                    log(f"  block search retry {attempt} for {utc_iso(timestamp)}: {exc}")
                time.sleep(0.5)
                continue
            if block_ts <= timestamp < next_ts:
                break
            if attempt >= max_attempts:
                raise RuntimeError(
                    f"block search did not converge for {utc_iso(timestamp)}: block {block} "
                    f"holds {utc_iso(block_ts)}..{utc_iso(next_ts)}"
                )
        resolved[timestamp] = {"block": block, "block_ts": block_ts}
        history.append((block, block_ts))
        if len(history) > 4:
            del history[0]
        previous_block = block
    return resolved


def resolve_blocks_parallel(
    timestamps: Iterable[int],
    *,
    workers: int = 5,
    client_factory: Optional[Callable[[], ArchiveRpc]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> Dict[int, Dict[str, Any]]:
    """Resolve a whole grid with one thread per contiguous chunk of timestamps.

    The block phase is the slowest part of a reconstruction (the search costs ~2-3
    ``eth_getBlockByNumber`` calls per point, and a public endpoint answers in ~0.3-1 s).
    Splitting the sorted grid into ``workers`` contiguous chunks costs one full-range
    search per chunk and divides the wall time by ``workers``.
    """
    ordered = sorted(int(t) for t in timestamps)
    if not ordered:
        return {}
    factory = client_factory or (lambda: new_client())
    chunk_size = max(1, -(-len(ordered) // max(1, workers)))
    chunks = [ordered[index:index + chunk_size] for index in range(0, len(ordered), chunk_size)]

    def run(chunk: List[int]) -> Dict[int, Dict[str, Any]]:
        return resolve_blocks(chunk, factory(), log=log)

    resolved: Dict[int, Dict[str, Any]] = {}
    if len(chunks) == 1:
        return run(chunks[0])
    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        for part in executor.map(run, chunks):
            resolved.update(part)
    return resolved


def parallel_measure(
    items: Sequence[Any],
    worker: Callable[[ArchiveRpc, Any], Dict[str, Any]],
    *,
    workers: int = 6,
    log: Optional[Callable[[str], None]] = None,
    on_result: Optional[Callable[[Any, Dict[str, Any]], None]] = None,
    clients_out: Optional[List[ArchiveRpc]] = None,
) -> Dict[Any, Dict[str, Any]]:
    """Run ``worker(client, item)`` over ``items`` with ``workers`` threads.

    Every thread owns its client (a client is not thread-safe); when
    ``clients_out`` is given, the created clients are appended to it so the
    caller can report the **total** number of RPC calls of the run.  A failing
    item is recorded as ``{"error": ...}`` instead of aborting the whole run, so
    a reconstruction always produces an evidence file it can be honest about.
    """
    results: Dict[Any, Dict[str, Any]] = {}
    if not items:
        return results
    thread_local = threading.local()

    def run(item: Any) -> Tuple[Any, Dict[str, Any]]:
        client = getattr(thread_local, "client", None)
        if client is None:
            thread_local.client = client = new_client()
            if clients_out is not None:
                with _worker_lock:
                    clients_out.append(client)
        return item, worker(client, item)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {executor.submit(run, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                _, payload = future.result()
            except Exception as exc:
                payload = {"error": f"{type(exc).__name__}: {exc}"}
                if log:
                    log(f"  point failed ({exc.__class__.__name__}): {exc}")
            results[item] = payload
            if on_result is not None:
                on_result(item, payload)
    return results
