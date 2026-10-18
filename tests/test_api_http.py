#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""HTTP API tests — every endpoint serves real repo artefacts.

Skips cleanly and visibly when FastAPI (or httpx for the test client) is not
installed.

Run: python -m unittest tests.test_api_http
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
HAS_HTTPX = importlib.util.find_spec("httpx") is not None
SKIP_REASON = ("fastapi/httpx absent — tests API skippés "
               "(import paresseux respecté)")


@unittest.skipUnless(HAS_FASTAPI and HAS_HTTPX, SKIP_REASON)
class TestApiHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        from orvyren.api.main import create_app

        cls.app = create_app()
        cls.client = TestClient(cls.app)

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertTrue(body["graph_db"].endswith(".sqlite"))

    def test_runs_and_journal_and_events(self):
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        runs = response.json()["runs"]
        self.assertGreaterEqual(len(runs), 3)
        run = next(r for r in runs if r["journals"]["orchestrator"].get("present"))
        run_id = run["run_id"]
        bundle = self.client.get("/api/runs/%s" % run_id).json()
        self.assertEqual(bundle["run_id"], run_id)
        self.assertIsNotNone(bundle["spec"])
        journal = self.client.get(
            "/api/runs/%s/journal?agent=orchestrator&limit=5" % run_id).json()
        self.assertGreater(journal["total"], 0)
        self.assertIn("prev_hash", journal["entries"][0])
        events = self.client.get("/api/runs/%s/events?limit=5" % run_id).json()
        self.assertEqual(events["events"][0]["seq"], 0)
        self.assertIn("type", events["events"][0])
        verify = self.client.get("/api/runs/%s/verify" % run_id).json()
        self.assertTrue(verify["agents"]["orchestrator"]["verified"])

    def test_run_404(self):
        response = self.client.get("/api/runs/run-does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_graph_full_and_etag(self):
        response = self.client.get("/api/graph/full")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["counts"]["nodes"], 0)
        self.assertGreater(body["counts"]["edges"], 0)
        self.assertIn("x", body["nodes"][0])
        etag = response.headers["etag"]
        cached = self.client.get("/api/graph/full",
                                 headers={"If-None-Match": etag})
        self.assertEqual(cached.status_code, 304)

    def test_graph_queries_q1_to_q8(self):
        defaults = {
            "q1": "holder=addr:eip155:8453:0xbe00a0de23a02a85d7fb7451ab9b69d84fd61fe3",
            "q2": ("src=addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427"
                   "&dst=asset:eip155:8453:0x4200000000000000000000000000000000000006"),
            "q3": "",
            "q4": "limit=5",
            "q5": "limit=5",
            "q6": "relation_id=struct:constrains:0xecac9c5f704e954931349da37f60e39f515c11c1",
            "q7": ("asset=debt:eip155:8453:0xa238dd80c259a72e81d7e4664a9801593f98d1c5:"
                   "0x4200000000000000000000000000000000000006"),
            "q8": "subject=addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427",
        }
        for name, params in defaults.items():
            url = "/api/graph/query/%s" % name
            if params:
                url += "?" + params
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, name)
            body = response.json()
            self.assertEqual(body["query"].lower(), name)
            self.assertTrue(
                any(key in body for key in ("status", "count", "rows", "counterparties")),
                name,
            )

    def test_graph_query_unknown(self):
        response = self.client.get("/api/graph/query/q99")
        self.assertEqual(response.status_code, 404)

    def test_graph_node_and_neighbors(self):
        full = self.client.get("/api/graph/full").json()
        node_id = full["nodes"][0]["id"]
        detail = self.client.get("/api/graph/node/%s" % node_id).json()
        self.assertEqual(detail["id"], node_id)
        neighbors = self.client.get(
            "/api/graph/neighbors/%s?depth=1" % node_id).json()
        self.assertGreaterEqual(neighbors["count_nodes"], 1)

    def test_market_endpoints(self):
        episodes = self.client.get("/api/market/episodes").json()
        self.assertEqual(episodes["count"], 3)
        series = self.client.get(
            "/api/market/series?episode=usdc-2023-03").json()
        self.assertTrue(series["lines"])
        self.assertTrue(series["lines"][0]["points"])
        episode = self.client.get("/api/market/episodes/usdc-2023-03").json()
        self.assertIn("hourly", episode)
        corpus = self.client.get("/api/market/corpus").json()
        self.assertTrue(corpus["series"])

    def test_decision_policy_execution(self):
        cases = self.client.get("/api/decision/cases").json()["cases"]
        self.assertIn("usdc-2023-03", cases)
        decision = self.client.get("/api/decision/usdc-2023-03").json()
        self.assertIn("axes", decision)
        self.assertIn("rdof", decision)
        record = self.client.get("/api/decision/usdc-2023-03/record").json()
        self.assertEqual(record["schema"], "orvyren-decision-record/v1")
        policy = self.client.get("/api/policy/verdicts").json()
        verdicts = [case["verdict"] for case in policy["cases"]]
        self.assertEqual(verdicts, ["ALLOW", "DENY", "REQUIRE_APPROVAL"])
        intents = self.client.get("/api/execution/intents").json()
        self.assertEqual(len(intents["cases"]), 3)
        receipts = self.client.get("/api/execution/receipts").json()
        self.assertGreaterEqual(len(receipts["chain_receipts"]), 12)

    def test_audit_endpoints(self):
        summary = self.client.get("/api/audit/summary").json()
        self.assertGreaterEqual(len(summary["snapshots"]), 3)
        self.assertTrue(summary["chains"])
        self.assertTrue(summary["runs"])
        self.assertTrue(all("verify" in run for run in summary["runs"]))
        stream = self.client.get("/api/audit/stream?limit=10").json()
        self.assertGreater(stream["total"], 10)
        self.assertEqual(stream["returned"], 10)
        self.assertEqual(stream["records"][0]["seq"], 1)

    def test_spa_serving(self):
        response = self.client.get("/live-route/deep")
        self.assertIn(response.status_code, (200, 503))
        if response.status_code == 200:
            self.assertIn("<!doctype html", response.text.lower())
        else:
            self.assertIn("frontend build not found", response.text)


if __name__ == "__main__":
    unittest.main()
