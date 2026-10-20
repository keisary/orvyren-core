#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""API artefact tests — the real system artefacts behind the frontend.

Every assertion is against the artefacts already in the repo (run journals,
hash chains, episodes, policy verdicts, receipts, audit chains). The modules
skip cleanly and visibly when FastAPI is not installed.

Run: python -m unittest tests.test_api_artifacts
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.api import artifacts  # noqa: E402
from orvyren.api.config import load_settings, resolve_graph_db  # noqa: E402
from orvyren.api.graph_service import GraphService  # noqa: E402

HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
SKIP_REASON = "fastapi absent — tests API skippés (import paresseux respecté)"

BIG_DB = "D:/orvyren_10h_2026-10-17/graph_v3.sqlite"


@unittest.skipUnless(HAS_FASTAPI, SKIP_REASON)
class TestArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = load_settings()

    def test_runs_discovered_with_real_counters(self):
        runs = artifacts.discover_runs(self.settings)
        self.assertGreaterEqual(len(runs), 3)
        with_journal = [r for r in runs
                        if r["journals"]["orchestrator"].get("present")]
        self.assertTrue(with_journal)
        first = with_journal[0]
        self.assertTrue(first["case_id"])
        self.assertGreater(first["journals"]["orchestrator"]["lines"], 0)

    def test_journal_hash_chain_matches_recorded_head(self):
        runs = artifacts.discover_runs(self.settings)
        checked = 0
        for run in runs:
            if not run["journals"]["orchestrator"].get("present"):
                continue
            report = artifacts.verify_journal_chain(run["run_id"], self.settings)
            orch = report["agents"].get("orchestrator", {})
            if orch.get("present") and orch.get("recorded_head"):
                self.assertTrue(orch["links_ok"], report)
                self.assertEqual(orch["recomputed_head"], orch["recorded_head"], report)
                self.assertTrue(orch["verified"], report)
                checked += 1
        self.assertGreaterEqual(checked, 1)

    def test_run_events_carry_artefact_fields(self):
        runs = [r for r in artifacts.discover_runs(self.settings)
                if r["journals"]["orchestrator"].get("present")]
        events = artifacts.build_run_events(runs[0]["run_id"], self.settings)
        self.assertGreater(len(events), 3)
        self.assertEqual(events[0]["seq"], 0)
        types = {e["type"] for e in events}
        self.assertIn("run.status", types)
        self.assertTrue(types & {"agent.thought", "agent.evidence", "agent.decision"})

    def test_episodes_index_and_series(self):
        index = artifacts.episodes_index(self.settings)
        self.assertEqual(len(index), 3)
        ids = {item["id"] for item in index}
        self.assertIn("usdc-2023-03", ids)
        usdc = artifacts.episode_series("usdc-2023-03", self.settings)
        price_lines = [l for l in usdc["lines"] if l["kind"] == "price"]
        self.assertGreaterEqual(len(price_lines), 3)
        self.assertTrue(all(len(l["points"]) > 10 for l in price_lines))
        for episode_id in ids:
            series = artifacts.episode_series(episode_id, self.settings)
            self.assertTrue(series["lines"], episode_id)

    def test_decision_axes_and_rdof(self):
        decision = artifacts.decision_case("usdc-2023-03", self.settings)
        axes = decision["axes"]
        self.assertIn(axes["epistemic_verdict"], ("CONCLUANT", "INCONCLUSIVE"))
        self.assertTrue(axes["economic_action"])
        self.assertTrue(decision["rdof"]["trace"])
        self.assertIn("H2", decision["hypothesis_verdicts"])
        record = artifacts.decision_record("usdc-2023-03", self.settings)
        self.assertEqual(record["schema"], "orvyren-decision-record/v1")

    def test_policy_verdicts_three_intents(self):
        demo = artifacts.policy_verdicts(self.settings)
        verdicts = {case["intent_id"]: case["verdict"] for case in demo["cases"]}
        self.assertEqual(verdicts.get("I1"), "ALLOW")
        self.assertEqual(verdicts.get("I2"), "DENY")
        self.assertEqual(verdicts.get("I3"), "REQUIRE_APPROVAL")
        first = demo["cases"][0]
        self.assertEqual(len(first["rules_evaluated"]), 14)
        self.assertTrue(first["instruction"]["calldata"].startswith("0xa9059cbb"))

    def test_execution_receipts_real_onchain(self):
        receipts = artifacts.execution_receipts(self.settings)
        self.assertGreaterEqual(len(receipts["setup_receipts"]), 8)
        self.assertGreaterEqual(len(receipts["chain_receipts"]), 12)
        sample = receipts["setup_receipts"][0]
        self.assertTrue(sample["tx_hash"].startswith("0x"))
        self.assertIn(sample["status"], ("0x1", "0x0"))

    def test_audit_summary_chains_and_packets(self):
        summary = artifacts.audit_summary(self.settings)
        self.assertGreaterEqual(len(summary["snapshots"]), 3)
        # One reference packet is shipped by design: the superseded ones live in
        # the out-of-repository archive. Assert integrity, not a count.
        self.assertGreaterEqual(len(summary["packets"]), 1)

        self.assertTrue(summary["chains"])
        chain = summary["chains"][0]
        self.assertGreater(chain["records"], 10)
        self.assertTrue(chain["links_ok"])
        self.assertTrue(chain["genesis_ok"])

    def test_corpus_index(self):
        corpus = artifacts.corpus_index(self.settings)
        self.assertGreaterEqual(len(corpus["series"]), 2)


@unittest.skipUnless(HAS_FASTAPI, SKIP_REASON)
class TestGraphService(unittest.TestCase):
    def test_fallback_schema_degrades_openly(self):
        root = load_settings().root
        legacy = os.path.join(root, "evidence", "graph.sqlite")
        if not os.path.exists(legacy):
            self.skipTest("evidence/graph.sqlite absent")
        service = GraphService(db_path=legacy)
        info = service.schema_info()
        self.assertEqual(info["schema"], "legacy")
        payload = service.full()
        self.assertGreater(len(payload["nodes"]), 0)
        self.assertIn("graph_version", payload)
        detail = service.node_detail(payload["nodes"][0]["id"])
        self.assertIn("relations", detail)
        q3 = service.query("q3")
        self.assertIn("status", q3)

    @unittest.skipUnless(os.path.exists(BIG_DB), "demo graph_v3.sqlite absent")
    def test_demo_db_counts_and_q1(self):
        service = GraphService(db_path=BIG_DB)
        info = service.schema_info()
        self.assertEqual(info["schema"], "v3")
        self.assertEqual(info["nodes"]["count"], 16174)
        self.assertEqual(info["relations"]["count"], 12937)
        payload = service.full()
        self.assertEqual(payload["counts"]["nodes"], 16174)
        self.assertEqual(payload["counts"]["edges"], 12937)
        self.assertTrue(payload["classes"])
        q1 = service.query(
            "q1", holder="addr:eip155:8453:0xbe00a0de23a02a85d7fb7451ab9b69d84fd61fe3",
            as_of_block=52723115)
        self.assertEqual(q1["query"], "Q1")
        self.assertEqual(q1["count"], 4)
        q7 = service.query(
            "q7",
            asset="debt:eip155:8453:0xa238dd80c259a72e81d7e4664a9801593f98d1c5:"
                  "0x4200000000000000000000000000000000000006",
            as_of_block=52723115)
        self.assertEqual(q7["counterparties"], 44)
        self.assertAlmostEqual(q7["hhi"], 0.29739028631918696, places=9)
        snapshot = service.query("snapshot")
        self.assertEqual(snapshot["counts"]["nodes"], 16174)
        self.assertEqual(snapshot["counts"]["relations"], 12937)

    def test_configurable_db_path(self):
        settings = load_settings()
        db, is_fallback = resolve_graph_db(settings.root)
        self.assertTrue(os.path.exists(db) or is_fallback)
        self.assertTrue(db.endswith(".sqlite"))


if __name__ == "__main__":
    unittest.main()
