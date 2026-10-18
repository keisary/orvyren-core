#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the 2026-10-18 API/frontend bug-hunt (W-revue).

One test (or tight group) per fixed bug in ``src/orvyren/api/**``; the fixes
and their rationale are listed in ``D:/orvyren_work_2026-10-18/review/api_frontend.md``.
Standard library everywhere except the HTTP-level cases, which skip visibly
when fastapi/httpx are absent.

Run: python -m unittest tests.test_api_review_fixes
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.api import artifacts  # noqa: E402
from orvyren.api.config import Settings  # noqa: E402
from orvyren.api.graph_service import GraphService  # noqa: E402
from orvyren.api.live import LiveHub  # noqa: E402

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
HAS_HTTPX = importlib.util.find_spec("httpx") is not None
SKIP_REASON = ("fastapi/httpx absent — tests API skippés "
               "(import paresseux respecté)")


def _settings(root: str, **overrides) -> Settings:
    return Settings(root=root,
                    graph_db=os.path.join(root, "graph.sqlite"),
                    graph_db_is_fallback=True,
                    frontend_dist=os.path.join(root, "dist"),
                    **overrides)


def _make_graph_db(path: str, edges, nodes=None) -> None:
    """Minimal v3-shaped relations table (q4 contract + full() payload)."""
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    try:
        if nodes is not None:
            con.execute("CREATE TABLE nodes (node_id TEXT, kind TEXT, "
                        "node_class TEXT, label TEXT, address TEXT)")
            con.executemany("INSERT INTO nodes (node_id, kind) VALUES (?, ?)",
                            list(nodes))
        con.execute(
            "CREATE TABLE relations (relation_id TEXT, revision INTEGER DEFAULT 1,"
            " kind TEXT, src TEXT, dst TEXT, payload TEXT, family TEXT,"
            " sign_prior TEXT, epistemic_status TEXT, source_family_id TEXT,"
            " valid_from TEXT, valid_to TEXT, valid_from_block INTEGER,"
            " valid_to_block INTEGER, lifecycle TEXT DEFAULT 'ACTIVE',"
            " validation_status TEXT DEFAULT 'VALIDATED')")
        con.executemany(
            "INSERT INTO relations (relation_id, revision, kind, src, dst)"
            " VALUES (?, ?, ?, ?, ?)",
            [(r[0], 1, r[1], r[2], r[3]) for r in edges])
        con.commit()
    finally:
        con.close()


class TestIsoTimestamps(unittest.TestCase):
    """``_iso`` must honour non-UTC offsets instead of re-labelling them UTC."""

    def test_offset_timestamp_is_not_relabelled_utc(self):
        from datetime import datetime, timezone
        expected = int(datetime(2023, 3, 10, 22, 0, tzinfo=timezone.utc).timestamp())
        self.assertEqual(artifacts._iso("2023-03-11T00:00:00+02:00"), expected)

    def test_z_and_naive_stay_utc(self):
        self.assertEqual(artifacts._iso("2023-03-11T00:00:00Z"),
                         artifacts._iso("2023-03-11T00:00:00"))
        self.assertEqual(artifacts._iso("2023-03-11T00:00:00Z"), 1678492800)

    def test_numeric_passthrough_and_unparseable_degrade(self):
        self.assertEqual(artifacts._iso(1678492800), 1678492800)
        self.assertEqual(artifacts._iso("not-a-timestamp"), 0)


class TestVerifyJournalChain(unittest.TestCase):
    """The verify endpoint must REPORT tampering, never crash on it."""

    @staticmethod
    def _entries():
        from orvyren.agents.journal import GENESIS_HASH, JournalEntry, entry_hash
        rows = []
        previous = GENESIS_HASH
        for step in range(2):
            entry = JournalEntry(
                journal_id="j%d" % step, run_id="run-1", episode_id="ep",
                agent_id="orch", role_version="v1", step_index=step,
                ts_utc="2026-10-18T00:00:0%dZ" % step, kind="PLAN",
                content="line %d" % step, prev_hash=previous)
            previous = entry_hash(entry)
            rows.append(dataclasses.asdict(entry))
        return rows, previous

    def _write_run(self, root, rows, head, journal_lines=None):
        run_dir = os.path.join(root, "evidence", "demo_runs", "agents", "run-1")
        os.makedirs(run_dir, exist_ok=True)
        with open(os.path.join(run_dir, "journal_orchestrator.jsonl"),
                  "w", encoding="utf-8", newline="\n") as handle:
            if journal_lines is not None:
                for line in journal_lines:
                    handle.write(line + "\n")
            else:
                for row in rows:
                    handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        with open(os.path.join(run_dir, "run_outcome.json"),
                  "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"journals": {"orchestrator": {"chain_head": head}}}, handle)
        return _settings(root)

    def test_valid_chain_verifies(self):
        rows, head = self._entries()
        with tempfile.TemporaryDirectory() as root:
            report = artifacts.verify_journal_chain(
                "run-1", self._write_run(root, rows, head))
        orch = report["agents"]["orchestrator"]
        self.assertTrue(orch["verified"], report)
        self.assertEqual(orch["recomputed_head"], head)

    def test_missing_required_field_is_reported_not_raised(self):
        rows, head = self._entries()
        del rows[1]["kind"]  # tamper: drop a required column of line 2
        with tempfile.TemporaryDirectory() as root:
            report = artifacts.verify_journal_chain(
                "run-1", self._write_run(root, rows, head))
        orch = report["agents"]["orchestrator"]
        self.assertFalse(orch["verified"])
        self.assertFalse(orch["links_ok"])
        self.assertIn("unreadable journal line 1", orch.get("error", ""))

    def test_broken_json_line_is_reported_not_raised(self):
        rows, head = self._entries()
        lines = [json.dumps(row, sort_keys=True, default=str) for row in rows]
        lines[1] = "{broken json"
        with tempfile.TemporaryDirectory() as root:
            report = artifacts.verify_journal_chain(
                "run-1", self._write_run(root, rows, head, journal_lines=lines))
        orch = report["agents"]["orchestrator"]
        self.assertFalse(orch["verified"])
        self.assertTrue(orch.get("error"), report)

    def test_tampered_content_moves_the_recomputed_head(self):
        rows, head = self._entries()
        rows[1]["content"] = "tampered"
        with tempfile.TemporaryDirectory() as root:
            report = artifacts.verify_journal_chain(
                "run-1", self._write_run(root, rows, head))
        orch = report["agents"]["orchestrator"]
        self.assertFalse(orch["verified"])
        self.assertNotEqual(orch["recomputed_head"], orch["recorded_head"])


class TestGraphVersionDigest(unittest.TestCase):
    """``graph_version`` is a content digest: every id counts, not the first 64."""

    def test_change_beyond_edge_64_changes_the_version(self):
        edges_a = [("r%03d" % i, "HOLDS", "n%d" % i, "n%d" % (i + 1))
                   for i in range(80)]
        edges_b = list(edges_a)
        edges_b[75] = ("r075x", "HOLDS", "n75", "n76")
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "graph.sqlite")
            _make_graph_db(db, edges_a)
            version_a = GraphService(db_path=db).full()["graph_version"]
            _make_graph_db(db, edges_b)  # same path, same counts, edge #75 differs
            version_b = GraphService(db_path=db).full()["graph_version"]
            _make_graph_db(db, edges_a)  # same content again
            version_a2 = GraphService(db_path=db).full()["graph_version"]
        self.assertNotEqual(version_a, version_b,
                            "a changed edge beyond #64 must change the version")
        self.assertEqual(version_a, version_a2, "same content, same version")


class TestGraphServiceQueries(unittest.TestCase):
    """Bounded query args: 0 stays legal, -1 is refused (P1-1 convention)."""

    @staticmethod
    def _service(root):
        db = os.path.join(root, "graph.sqlite")
        _make_graph_db(db, [("r%d" % i, "HOLDS", "a", "b") for i in range(5)])
        return GraphService(db_path=db)

    def test_negative_limit_is_refused_not_unlimited(self):
        with tempfile.TemporaryDirectory() as root:
            result = self._service(root).query("q4", limit=-1)
        self.assertEqual(result["status"], "BAD_ARGS")
        self.assertNotIn("rows", result)

    def test_zero_limit_stays_zero(self):
        with tempfile.TemporaryDirectory() as root:
            service = self._service(root)
            empty = service.query("q4", limit=0)
            two = service.query("q4", limit=2)
        self.assertNotEqual(empty.get("status"), "BAD_ARGS")
        self.assertEqual(empty.get("count"), 5)  # the count query is unbounded
        self.assertEqual(empty.get("rows"), [])  # ... but the page is empty
        self.assertEqual(len(two.get("rows", [])), 2)

    def test_out_of_range_max_depth_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            service = self._service(root)
            self.assertEqual(service.query("q1", max_depth=99)["status"], "BAD_ARGS")
            self.assertEqual(service.query("q2", max_depth=-1)["status"], "BAD_ARGS")
            self.assertEqual(service.query("q4", limit="abc")["status"], "BAD_ARGS")

    def test_q3_reports_schema_errors_like_the_other_queries(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "empty.sqlite")
            con = sqlite3.connect(db)
            try:
                con.execute("CREATE TABLE other (x)")
                con.commit()
            finally:
                con.close()
            result = GraphService(db_path=db).query("q3")
        self.assertEqual(result["query"].lower(), "q3")
        self.assertEqual(result["status"], "SCHEMA_UNSUPPORTED")
        self.assertIn("detail", result)

    def test_relation_count_is_not_truncated_by_the_200_row_cap(self):
        edges = [("r%03d" % i, "HOLDS", "hub", "n%d" % i) for i in range(205)]
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "graph.sqlite")
            _make_graph_db(db, edges)
            detail = GraphService(db_path=db).node_detail("hub")
        self.assertEqual(detail["relation_count"], 205)
        self.assertEqual(len(detail["relations"]), 200)  # the cap itself stays
        self.assertTrue(detail["relations_truncated"])


class TestLiveHubRobustness(unittest.TestCase):
    """WS hub: bad input, ring overflow, slow clients, task leaks."""

    @staticmethod
    def _capture(hub):
        sent = []

        async def capture(envelope):
            sent.append(envelope)

        hub.broadcast = capture  # type: ignore[assignment]
        return sent

    def test_garbage_client_messages_never_raise(self):
        hub = LiveHub(_settings(tempfile.gettempdir()))

        async def run():
            await hub.handle_client_message("not json at all")
            await hub.handle_client_message("5")
            await hub.handle_client_message('"just a string"')
            await hub.handle_client_message(json.dumps(
                {"type": "subscribe", "channels": "run:x", "since_seq": "abc"}))
            await hub.handle_client_message(json.dumps({"type": 42}))

        asyncio.run(run())

    def test_unknown_run_subscription_reports_instead_of_crashing(self):
        hub = LiveHub(_settings(tempfile.gettempdir()))
        sent = self._capture(hub)

        async def run():
            await hub.handle_client_message(json.dumps(
                {"type": "subscribe", "channels": ["run:nope"]}))

        asyncio.run(run())
        self.assertTrue(any(e["type"] == "resync"
                            and e["payload"].get("reason") == "unknown_run"
                            for e in sent), sent)
        self.assertFalse(any(e["payload"].get("phase") == "subscribed"
                             for e in sent))

    def test_ring_overflow_gets_resync_not_a_partial_window(self):
        hub = LiveHub(_settings(tempfile.gettempdir(), ring_size=4))
        sent = self._capture(hub)
        for _ in range(10):
            hub.envelope("ping", {})  # seq 1..10, ring keeps 7..10

        async def run():
            await hub.handle_client_message(json.dumps(
                {"type": "subscribe", "channels": [], "since_seq": 9}))
            await hub.handle_client_message(json.dumps(
                {"type": "subscribe", "channels": [], "since_seq": 2}))

        asyncio.run(run())
        overflows = [e for e in sent if e["payload"].get("reason") == "ring_overflow"]
        self.assertEqual(len(overflows), 1, sent)
        replayed = [e["seq"] for e in sent if e["type"] == "ping"]
        self.assertEqual(replayed, [10], sent)

    def test_slow_client_is_dropped_instead_of_stalling_the_fanout(self):
        hub = LiveHub(_settings(tempfile.gettempdir(),
                                ws_send_timeout_seconds=0.05))

        class SlowClient:
            async def send_text(self, text):
                await asyncio.sleep(30)

        class OkClient:
            def __init__(self):
                self.sent = []

            async def send_text(self, text):
                self.sent.append(text)

        slow, ok = SlowClient(), OkClient()
        hub.clients.update([slow, ok])

        async def run():
            await hub.broadcast(hub.envelope("ping", {}))

        asyncio.run(run())
        self.assertNotIn(slow, hub.clients)
        self.assertIn(ok, hub.clients)
        self.assertEqual(len(ok.sent), 1)

    def test_pong_replies_only_to_the_ping_sender(self):
        hub = LiveHub(_settings(tempfile.gettempdir()))

        class Client:
            def __init__(self):
                self.sent = []

            async def send_text(self, text):
                self.sent.append(json.loads(text))

        first, second = Client(), Client()
        hub.clients.update([first, second])

        async def run():
            await hub.handle_client_message(json.dumps({"type": "ping"}), first)

        asyncio.run(run())
        self.assertTrue(any(e["type"] == "pong" for e in first.sent))
        self.assertEqual(second.sent, [])

    def test_shutdown_cancels_producer_and_market_tasks(self):
        hub = LiveHub()  # real repo settings (the episode must exist)
        started = []

        class Client:
            async def send_text(self, text):
                pass

        async def run():
            await hub.register(Client())
            self.assertIsNotNone(hub._producer)
            started.append(hub._producer)
            await hub.handle_client_message(json.dumps(
                {"type": "subscribe", "channels": ["market:usdc-2023-03"]}))
            await asyncio.sleep(0)
            started.extend(hub._market_tasks)
            await hub.shutdown()
            self.assertIsNone(hub._producer)
            self.assertEqual(hub._market_tasks, set())

        asyncio.run(run())
        self.assertTrue(all(task.done() for task in started), started)


@unittest.skipUnless(HAS_FASTAPI and HAS_HTTPX, SKIP_REASON)
class TestApiHttpHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from orvyren.api.main import create_app
        cls.app = create_app()
        cls.client = TestClient(cls.app)

    def test_unknown_api_route_is_404_json_not_index_html(self):
        response = self.client.get("/api/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertIn("unknown API route", response.text)
        self.assertNotIn("<!doctype html", response.text.lower())

    def test_negative_and_out_of_range_args_are_rejected(self):
        for url in ("/api/audit/stream?limit=-1",
                    "/api/audit/stream?after_seq=-1",
                    "/api/audit/stream?limit=5000",
                    "/api/graph/query/q4?limit=-1",
                    "/api/graph/query/q4?max_depth=-1",
                    "/api/graph/query/q2?max_depth=99",
                    "/api/graph/neighbors/n1?depth=0",
                    "/api/graph/neighbors/n1?depth=9"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 422, url)

    def test_run_scoped_limits_are_bounded(self):
        runs = self.client.get("/api/runs").json()["runs"]
        run_id = next(r["run_id"] for r in runs
                      if r["journals"]["orchestrator"].get("present"))
        for url in ("/api/runs/%s/journal?limit=-1" % run_id,
                    "/api/runs/%s/journal?after_seq=-1" % run_id,
                    "/api/runs/%s/events?limit=-1" % run_id):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 422, url)
        ok = self.client.get("/api/runs/%s/journal?limit=1" % run_id)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["returned"], 1)

    def test_percent_encoded_node_id_round_trips(self):
        # Pins the frontend's encodeURIComponent(node id) against the route.
        node_id = GraphService().full()["nodes"][0]["id"]
        encoded = urllib.parse.quote(node_id, safe="")
        self.assertIn("%", encoded)  # node ids carry ':' at the very least
        response = self.client.get("/api/graph/node/%s" % encoded)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], node_id)


@unittest.skipUnless(HAS_FASTAPI, SKIP_REASON)
class TestSpaPathSafety(unittest.TestCase):
    def test_sibling_directory_with_matching_prefix_is_refused(self):
        from orvyren.api.main import _safe_dist_path
        with tempfile.TemporaryDirectory() as root:
            dist = os.path.join(root, "dist")
            evil = os.path.join(root, "dist_evil")
            os.makedirs(dist)
            os.makedirs(evil)
            inside = os.path.join(dist, "index.html")
            outside = os.path.join(evil, "secret.txt")
            for path in (inside, outside):
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("x")
            self.assertEqual(_safe_dist_path(dist, "index.html"),
                             os.path.normcase(inside))
            self.assertIsNone(_safe_dist_path(dist, "../dist_evil/secret.txt"))
            self.assertIsNone(_safe_dist_path(dist, "..\\dist_evil\\secret.txt"))
            self.assertIsNone(_safe_dist_path(dist, "nope.txt"))
            self.assertIsNone(_safe_dist_path(dist, ""))


if __name__ == "__main__":
    unittest.main()
