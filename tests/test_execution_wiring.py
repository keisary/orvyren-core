#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — wiring contracts: the preflight gate and the agents->decision link.

Two links that used to be missing are asserted here:

1. ``run_loop(preflight_runner=...)`` never signs when the preflight says no
   (fail-closed), and reaches the executor only when it says yes.
2. ``--decision-source agents`` builds the DecisionRecord from a sealed agents
   run instead of re-deriving the corpus pilot: an inconclusive run yields an
   abstention, therefore no intent and no signature.

Everything is offline and stdlib: injected callables, fixed clock, temporary
paths, no key read, no network.

Run: python -m unittest tests.test_execution_wiring -v
"""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.decision import agents_source  # noqa: E402
from orvyren.execution import loop as executor  # noqa: E402
from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID  # noqa: E402

import run_executor  # noqa: E402

POLICY = os.path.join(ROOT, "policy_v1.yaml")
RESERVE = "0x1111111111111111111111111111111111111111"
BASE_ENV = {"ORVYREN_AGENT_MEMBER": "true", "ORVYREN_AVAILABLE_BALANCE": "1000"}
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
RUN_ID = "run-20261018T120000000000Z-00aabbccdd11"
SEALED_RUNS = (
    os.path.join(ROOT, "evidence", "agents_live", "usdc-2023-03_live_20261017T013034Z"),
    os.path.join(ROOT, "evidence", "demo_runs", "agents", "usdc-2023-03",
                 "usdc-2023-03_live_20261017T013034Z"),
)


def make_bundle():
    bundle = executor.load_bundle(POLICY, {"B": RESERVE})
    executor.apply_permission_window(bundle, NOW)
    return bundle


def allow_provider(amount=100.0):
    """One bounded transfer, no corpus dependency: the ALLOW path."""
    def provider(tick, now):
        return {
            "case": "usdc-2023-03",
            "epistemic_verdict": "CONCLUANT",
            "economic_action": "CONVERTIR/TRANSFÉRER",
            "authorization_verdict": "ALLOW",
            "intent": {
                "intent_id": "intent-wiring",
                "action": "transfer",
                "chain_id": ALLOWED_CHAIN_ID,
                "asset": ALLOWED_ASSET,
                "amount": amount,
                "recipient": RESERVE,
            },
        }
    return provider


class WiringHarness(unittest.TestCase):
    case = "usdc-2023-03"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_wiring_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.journal = os.path.join(self.tmp, "journal.jsonl")
        self.ledger = os.path.join(self.tmp, "ledger.json")
        self.chain_root = os.path.join(self.tmp, "chain")

    def run_loop(self, **overrides):
        params = dict(
            bundle=make_bundle(),
            case=self.case,
            recipient=RESERVE,
            journal_path=self.journal,
            ledger_path=self.ledger,
            ticks=1,
            dry_run=True,
            decision_provider=allow_provider(),
            policy_path=POLICY,
            env=dict(BASE_ENV),
            clock=lambda: NOW,
            sleep=lambda seconds: None,
            chain_root=self.chain_root,
        )
        params.update(overrides)
        return executor.run_loop(**params)


class PreflightGateTests(WiringHarness):
    """The preflight is a gate in the execution path, not a report."""

    def test_refusal_blocks_the_signature(self):
        calls = []
        summary = self.run_loop(
            dry_run=False, run_id=RUN_ID,
            execute=lambda intent, record: calls.append(intent.intent_id) or {"sent": True},
            preflight_runner=lambda intent, now: {
                "ok": False, "failed_code": "SIMULATION_REVERT", "checks": []})
        record = summary["records"][0]
        self.assertEqual([], calls, "the executor must never see a refused intent")
        self.assertEqual("PREFLIGHT_REFUSED", record["outcome"])
        self.assertFalse(record["executed"])
        self.assertIn("SIMULATION_REVERT", record["error"])
        self.assertEqual("ALLOW", record["policy_verdict"], "the policy verdict is intact")
        self.assertEqual("preflight", summary["stopped"])
        self.assertEqual(0, summary["counts"]["signed"])

    def test_a_non_mapping_answer_is_a_refusal(self):
        calls = []
        summary = self.run_loop(
            dry_run=False, run_id=RUN_ID,
            execute=lambda intent, record: calls.append(intent.intent_id) or {"sent": True},
            preflight_runner=lambda intent, now: None)
        self.assertEqual([], calls)
        self.assertEqual("PREFLIGHT_REFUSED", summary["records"][0]["outcome"])
        self.assertIn("PREFLIGHT_UNAVAILABLE", summary["records"][0]["error"])

    def test_pass_reaches_the_executor(self):
        calls = []
        summary = self.run_loop(
            dry_run=False, run_id=RUN_ID,
            execute=lambda intent, record: calls.append(intent.intent_id) or {
                "sent": True, "tx_hash": "0x" + "ab" * 32, "error": None},
            preflight_runner=lambda intent, now: {
                "ok": True, "failed_code": "", "checks": [], "gas_limit": 26250})
        self.assertEqual(1, len(calls))
        record = summary["records"][0]
        self.assertTrue(record["preflight"]["ok"])
        self.assertEqual(26250, record["preflight"]["gas_limit"])

    def test_no_preflight_keeps_the_old_behaviour(self):
        calls = []
        summary = self.run_loop(
            dry_run=False, run_id=RUN_ID,
            execute=lambda intent, record: calls.append(intent.intent_id) or {"sent": True})
        self.assertEqual(1, len(calls))
        self.assertNotIn("preflight", summary["records"][0])

    def test_dry_run_never_calls_the_preflight(self):
        seen = []
        self.run_loop(preflight_runner=lambda intent, now: seen.append(1) or {"ok": True})
        self.assertEqual([], seen, "a dry-run touches no RPC")


class PreflightConfigTests(unittest.TestCase):
    """Startup refusal, not a silent skip."""

    def test_missing_configuration_is_refused_by_name(self):
        with self.assertRaises(executor.ExecuteUnavailable) as ctx:
            run_executor._build_preflight_runner({}, "/nonexistent/ledger.json")
        message = str(ctx.exception)
        for name in ("ORVYREN_RPC_URL_BASE_SEPOLIA", "ORVYREN_AGENT_ADDRESS",
                     "ORVYREN_SAFE_ADDRESS"):
            self.assertIn(name, message)

    def test_complete_configuration_builds_a_runner(self):
        env = {
            "ORVYREN_RPC_URL_BASE_SEPOLIA": "http://127.0.0.1:8545",
            "ORVYREN_AGENT_ADDRESS": "0x" + "11" * 20,
            "ORVYREN_SAFE_ADDRESS": "0x" + "22" * 20,
        }
        runner = run_executor._build_preflight_runner(env, "/nonexistent/ledger.json")
        self.assertTrue(callable(runner))

    def test_unknown_ledger_yields_no_processed_id(self):
        self.assertEqual(set(), run_executor._seen_intent_ids("/nonexistent/ledger.json"))


class AgentsDecisionWiringTests(WiringHarness):
    """The agent run feeds the decision, and an abstention stops the chain."""

    case = "usdc-2023-03"

    def sealed_run(self):
        for candidate in SEALED_RUNS:
            if os.path.isfile(os.path.join(candidate, "run_outcome.json")):
                return candidate
        self.skipTest("no sealed agents run on disk")

    def test_abstention_produces_no_intent_and_no_signature(self):
        record = agents_source.build_decision_from_agents(self.sealed_run(),
                                                          case_id=self.case)
        self.assertIsNone(record["intent"])
        calls = []
        summary = self.run_loop(
            dry_run=False, run_id=RUN_ID,
            decision_provider=lambda tick, now: record,
            execute=lambda intent, r: calls.append(intent.intent_id) or {"sent": True},
            preflight_runner=lambda intent, now: {"ok": True, "failed_code": "CHAIN_ID_MISMATCH"})
        self.assertEqual([], calls, "an abstention must never reach the executor")
        first = summary["records"][0]
        self.assertEqual("NO_ACTION", first["outcome"])
        self.assertEqual("REQUIRE_APPROVAL",
                         first["decision_summary"]["authorization_verdict"])

    def test_the_record_carries_the_agents_provenance(self):
        record = agents_source.build_decision_from_agents(self.sealed_run(),
                                                          case_id=self.case)
        self.assertEqual("agents", record["source"]["kind"])
        self.assertTrue(record["source"]["chain_heads"],
                        "the provenance must be the real journal heads")

    def test_cli_refuses_agents_without_a_run_directory(self):
        code = run_executor.main(["--case", self.case, "--decision-source", "agents"],
                                 env=dict(BASE_ENV))
        self.assertEqual(executor.EXIT_USAGE, code)

    def test_cli_refuses_a_missing_run_directory(self):
        missing = os.path.join(self.tmp, "nope")
        code = run_executor.main(["--case", self.case, "--decision-source", "agents",
                                  "--agents-run", missing,
                                  "--journal", self.journal, "--ledger", self.ledger],
                                 env=dict(BASE_ENV))
        self.assertEqual(executor.EXIT_USAGE, code)


if __name__ == "__main__":
    unittest.main()
