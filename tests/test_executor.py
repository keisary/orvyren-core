#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — autonomous executor bench (loop, ledger, journal, CLI).

Everything is offline and stdlib: injected decision (or real replay for the CLI),
fixed clock, temporary paths. No key is read; ``--execute`` without a
key must fail before the first tick.

Run: python -m unittest tests.test_executor -v
            python -m pytest tests/test_executor.py -q
"""

import ast
import contextlib
import io
import json
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

from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID  # noqa: E402

from orvyren.execution import loop as executor  # noqa: E402
from orvyren.execution.guard import ExecutionConfig  # noqa: E402

import run_execution_demo as demo  # noqa: E402
import run_executor  # noqa: E402

POLICY = os.path.join(ROOT, "policy_v1.yaml")
LOOP_SOURCE = os.path.join(ROOT, "src", "orvyren", "execution", "loop.py")
RESERVE = "0x1111111111111111111111111111111111111111"
OTHER = "0x" + "bb" * 20
NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)


def make_bundle(recipient=RESERVE, policy_path=POLICY):
    bundle = executor.load_bundle(policy_path, {"B": recipient})
    executor.apply_permission_window(bundle, NOW)
    return bundle


def make_provider(amount=100.0, recipient=RESERVE):
    """Synthetic decision: a bounded transfer, without depending on the corpus."""

    def provider(tick, now):
        return {
            "case": "usdc-2023-03",
            "epistemic_verdict": "CONCLUANT",
            "economic_action": "CONVERTIR/TRANSFÉRER",
            "authorization_verdict": "ALLOW",
            "intent": {
                "intent_id": "intent-test-a-d1",
                "action": "transfer",
                "chain_id": ALLOWED_CHAIN_ID,
                "asset": ALLOWED_ASSET,
                "amount": amount,
                "recipient": recipient,
            },
        }

    return provider


def invoke_cli(argv, env=None, clock=None):
    """Call the CLI while capturing stdout/stderr: silent bench, code + output."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run_executor.main(argv, env={} if env is None else env,
                                 clock=clock or (lambda: NOW))
    return code, out.getvalue(), err.getvalue()


class ExecutorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_executor_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.journal = os.path.join(self.tmp, "journal.jsonl")
        self.ledger = os.path.join(self.tmp, "ledger.json")

    def run_loop(self, **overrides):
        params = dict(
            bundle=make_bundle(),
            case="usdc-2023-03",
            recipient=RESERVE,
            journal_path=self.journal,
            ledger_path=self.ledger,
            ticks=1,
            dry_run=True,
            decision_provider=make_provider(),
            policy_path=POLICY,
            env={},
            clock=lambda: NOW,
            sleep=lambda seconds: None,
        )
        params.update(overrides)
        return executor.run_loop(**params)


class TestDryRunLoop(ExecutorTestCase):
    def test_five_ticks_dry_run_journal_chain_and_zero_signature(self):
        summary = self.run_loop(ticks=5)

        self.assertEqual(5, summary["ticks_run"])
        self.assertEqual(3, summary["counts"]["dry_run"])
        self.assertEqual(2, summary["counts"]["deny"])
        self.assertEqual(0, summary["counts"]["signed"])
        self.assertEqual(0, summary["counts"]["errors"])
        self.assertTrue(summary["journal"]["ok"], summary["journal"]["error"])
        self.assertEqual(5, summary["journal"]["records"])
        self.assertEqual(["ALLOW", "ALLOW", "ALLOW", "DENY", "DENY"],
                         [record["verdict"] for record in summary["records"]])
        self.assertEqual(["AMOUNT_ABOVE_PERIOD_CAP"],
                         summary["records"][3]["reasons"])
        for record in summary["records"]:
            self.assertEqual("dry-run", record["mode"])
            self.assertIsNone(record["tx_hash"])
            self.assertIsNone(record["receipt_verification"])
            self.assertNotIn("signature", record)
            self.assertFalse(record["executed"])
        self.assertEqual(300.0, summary["ledger"]["spent_24h_after"])

        with open(self.journal, "r", encoding="utf-8") as handle:
            self.assertEqual(5, len([line for line in handle if line.strip()]))
        verification = executor.verify_journal(self.journal)
        self.assertTrue(verification["ok"])
        self.assertEqual(5, verification["records"])

    def test_policy_identity_is_carried_by_every_verdict(self):
        summary = self.run_loop(ticks=2)
        bundle = make_bundle()
        for record in summary["records"]:
            self.assertEqual("v1.0", record["policy_version"])
            self.assertEqual(bundle.policy_hash, record["policy_hash"])
            self.assertEqual(64, len(record["policy_hash"]))

    def test_no_state_rule_is_skipped_on_the_transfer_path(self):
        record = self.run_loop(ticks=1)["records"][0]
        results = {rule["rule"]: rule["result"] for rule in record["rules_evaluated"]}
        for rule in ("P7-exposure", "P11-pause", "P12-envelope", "P14-budget"):
            self.assertIn(rule, results)
            self.assertEqual("OK", results[rule], rule)
        self.assertNotIn("SKIPPED", results.values())
        self.assertEqual([], record["skipped_rules"])
        self.assertEqual("PASS", record["state"]["envelope_status"])

    def test_journal_tampering_breaks_the_chain(self):
        self.run_loop(ticks=3)
        with open(self.journal, "r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        tampered = json.loads(lines[1])
        tampered["intent"]["amount"] = 1.0
        lines[1] = json.dumps(tampered, ensure_ascii=False) + "\n"
        with open(self.journal, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
        verification = executor.verify_journal(self.journal)
        self.assertFalse(verification["ok"])
        self.assertIn("record_hash", verification["error"])

    def test_executor_refuses_to_append_to_a_tampered_journal(self):
        self.run_loop(ticks=2)
        with open(self.journal, "r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        tampered = json.loads(lines[0])
        tampered["verdict"] = "DENY"  # the line was ALLOW: the hash no longer matches
        lines[0] = json.dumps(tampered, ensure_ascii=False) + "\n"
        with open(self.journal, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
        with self.assertRaises(executor.JournalError):
            self.run_loop(ticks=1)
        code, _, _ = invoke_cli(["--ticks", "1", "--dry-run",
                                 "--journal", self.journal, "--ledger", self.ledger])
        self.assertEqual(executor.EXIT_RUNTIME, code)

    def test_json_cli_output_is_machine_readable(self):
        code, out, _ = invoke_cli([
            "--ticks", "2", "--dry-run", "--json",
            "--journal", self.journal, "--ledger", self.ledger,
        ])
        self.assertEqual(0, code)
        payload = json.loads(out)
        self.assertEqual(executor.SCHEMA_RUN, payload["schema"])
        self.assertEqual(2, payload["ticks_run"])
        self.assertTrue(payload["journal"]["ok"])

    def test_cli_default_five_tick_command_is_clean(self):
        code, out, _ = invoke_cli([
            "--case", "usdc-2023-03", "--ticks", "5", "--dry-run",
            "--journal", self.journal, "--ledger", self.ledger,
        ])
        self.assertEqual(0, code)
        self.assertEqual(5, executor.verify_journal(self.journal)["records"])
        self.assertNotIn("ERROR", out)


class TestKillSwitch(ExecutorTestCase):
    def test_pause_refuses_every_tick_without_crashing(self):
        summary = self.run_loop(ticks=3, env={"ORVYREN_K0_PAUSED": "1"})
        self.assertTrue(summary["paused"])
        self.assertEqual(3, summary["ticks_run"])
        self.assertEqual(3, summary["journal"]["records"])
        for record in summary["records"]:
            self.assertEqual("DENY", record["verdict"])
            self.assertEqual("DENIED_POLICY", record["outcome"])
            self.assertIn("PAUSED", record["reasons"])
        self.assertEqual(0, summary["ledger"]["entries"])
        self.assertTrue(summary["journal"]["ok"])

    def test_pause_flag_file_is_honoured(self):
        flag = os.path.join(self.tmp, "K0_PAUSED")
        with open(flag, "w", encoding="utf-8") as handle:
            handle.write("paused\n")
        summary = self.run_loop(ticks=1, env={"ORVYREN_K0_PAUSE_FLAG": flag})
        self.assertTrue(summary["paused"])
        self.assertIn("PAUSED", summary["records"][0]["reasons"])

    def test_unreadable_pause_value_fails_closed(self):
        summary = self.run_loop(ticks=1, env={"ORVYREN_K0_PAUSED": "maybe"})
        self.assertTrue(summary["paused"])
        self.assertIn("PAUSED", summary["records"][0]["reasons"])

    def test_cli_returns_non_zero_when_paused(self):
        code, _, _ = invoke_cli([
            "--ticks", "2", "--dry-run",
            "--journal", self.journal, "--ledger", self.ledger,
        ], env={"ORVYREN_K0_PAUSED": "1"})
        self.assertEqual(executor.EXIT_PAUSED, code)
        self.assertEqual(2, executor.verify_journal(self.journal)["records"])

    def test_pause_is_rechecked_on_each_tick(self):
        calls = {"count": 0}
        real_resolve = executor.resolve_pause

        def flaky_pause(env=None, flag_path=None):
            calls["count"] += 1
            return calls["count"] > 1  # the kill switch flips on the 2nd tick

        executor.resolve_pause = flaky_pause
        try:
            summary = self.run_loop(ticks=3)
        finally:
            executor.resolve_pause = real_resolve
        self.assertEqual(3, calls["count"])
        self.assertEqual(["ALLOW", "DENY", "DENY"],
                         [record["verdict"] for record in summary["records"]])
        self.assertIn("PAUSED", summary["records"][1]["reasons"])


class TestRecipientFailClosed(ExecutorTestCase):
    def call_main(self, argv, env=None):
        code, _, _ = invoke_cli(argv + ["--journal", self.journal, "--ledger", self.ledger],
                                env=env or {})
        return code

    def test_empty_recipient_is_refused(self):
        self.assertEqual(executor.EXIT_USAGE, self.call_main(["--recipient", ""]))
        self.assertFalse(os.path.exists(self.journal))

    def test_empty_environment_label_is_refused(self):
        self.assertEqual(executor.EXIT_USAGE,
                         self.call_main([], env={"ORVYREN_RECIPIENT_B": "  "}))
        self.assertFalse(os.path.exists(self.journal))

    def test_invalid_recipient_is_refused(self):
        self.assertEqual(executor.EXIT_USAGE, self.call_main(["--recipient", "0x1234"]))

    def test_recipient_outside_allowlist_is_refused(self):
        env = {"ORVYREN_RECIPIENT_B": "0x" + "aa" * 20}
        self.assertEqual(executor.EXIT_USAGE,
                         self.call_main(["--recipient", OTHER], env=env))
        self.assertFalse(os.path.exists(self.journal))

    def test_missing_policy_is_refused(self):
        missing = os.path.join(self.tmp, "absent.yaml")
        code, _, _ = invoke_cli(["--policy", missing])
        self.assertEqual(executor.EXIT_USAGE, code)


class TestPeriodCapPersistence(ExecutorTestCase):
    def test_four_transfers_of_100_fourth_is_denied_across_restarts(self):
        first = self.run_loop(ticks=2)
        self.assertEqual(2, first["counts"]["dry_run"])
        self.assertEqual(200.0, first["ledger"]["spent_24h_after"])

        # Second invocation: new journal/ledger instances, same file.
        second = self.run_loop(ticks=2)
        self.assertEqual(200.0, second["ledger"]["spent_24h_before"])
        self.assertEqual(300.0, second["ledger"]["spent_24h_after"])
        self.assertEqual("ALLOW", second["records"][0]["verdict"])
        self.assertEqual("DENY", second["records"][1]["verdict"])
        self.assertIn("AMOUNT_ABOVE_PERIOD_CAP", second["records"][1]["reasons"])

        verification = executor.verify_journal(self.journal)
        self.assertTrue(verification["ok"])
        self.assertEqual(4, verification["records"])
        self.assertEqual(3, len(executor.PeriodLedger(self.ledger).entries()))
        self.assertEqual(300.0, executor.PeriodLedger(self.ledger).spent(NOW))

    def test_denied_transfer_does_not_consume_the_ledger(self):
        summary = self.run_loop(ticks=2, max_usd=50.0)
        self.assertEqual(0, summary["ledger"]["entries"])
        for record in summary["records"]:
            self.assertEqual("DENIED_TICK_BUDGET", record["outcome"])
            self.assertIn(executor.TICK_BUDGET_CODE, record["reasons"])

    def test_corrupt_ledger_is_fail_closed(self):
        with open(self.ledger, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        code, _, _ = invoke_cli(["--ticks", "1", "--dry-run",
                                 "--journal", self.journal, "--ledger", self.ledger])
        self.assertEqual(executor.EXIT_RUNTIME, code)
        self.assertFalse(os.path.exists(self.journal))


class TestExecuteFailClosed(ExecutorTestCase):
    def test_execute_without_key_or_library_returns_non_zero_before_any_tick(self):
        code, _, _ = invoke_cli(["--execute", "--ticks", "1",
                                 "--journal", self.journal, "--ledger", self.ledger])
        self.assertEqual(executor.EXIT_EXECUTE, code)
        self.assertFalse(os.path.exists(self.journal))
        self.assertFalse(os.path.exists(self.ledger))

    def test_dry_run_never_imports_the_signer_module_at_top_level(self):
        with open(LOOP_SOURCE, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        banned = {"signer", "eth_account", "demo", "scripts"}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], banned,
                                     "top-level import of scripts/signer is forbidden")
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                self.assertNotIn(module, banned,
                                 "top-level import of scripts/signer is forbidden")
                self.assertNotEqual("orvyren.decide", node.module,
                                    "the decision engine must stay a lazy import")


class TestDemoWiring(ExecutorTestCase):
    def test_demo_loads_policy_and_has_no_skipped_state_rule(self):
        report = demo.build_report(ExecutionConfig.from_env({}), NOW, env={})
        self.assertEqual("v1.0", report["policy"]["version"])
        self.assertEqual(64, len(report["policy"]["policy_hash"]))
        self.assertEqual("PASS", report["policy_state"]["envelope_status"])
        self.assertFalse(report["policy_state"]["paused"])
        for case in report["cases"]:
            self.assertEqual(case["policy_hash"], report["policy"]["policy_hash"])
            for rule in case["rules_evaluated"]:
                if rule["rule"] in ("P7-exposure", "P11-pause", "P12-envelope"):
                    self.assertNotEqual("SKIPPED", rule["result"], rule["rule"])
        by_id = {case["intent_id"]: case for case in report["cases"]}
        self.assertEqual(["P4-function"], by_id["I3"]["skipped_rules"])
        self.assertEqual([], by_id["I1"]["skipped_rules"])

    def test_demo_period_cap_fourth_transfer_is_denied(self):
        report = demo.build_report(ExecutionConfig.from_env({}), NOW, env={})
        cap = report["period_cap_check"]
        self.assertEqual(["ALLOW", "ALLOW", "ALLOW", "DENY"],
                         [item["verdict"] for item in cap["verdicts"]])
        self.assertEqual("DENY", cap["fourth_verdict"])
        self.assertIn("AMOUNT_ABOVE_PERIOD_CAP", cap["fourth_deny_codes"])
        self.assertEqual(300.0, cap["spent_24h_after_restart"])
        self.assertEqual(3, cap["ledger_entries_after_restart"])

    def test_demo_verdicts_are_unchanged(self):
        report = demo.build_report(ExecutionConfig.from_env({}), NOW, env={})
        self.assertEqual({"I1": "ALLOW", "I2": "DENY", "I3": "REQUIRE_APPROVAL"},
                         {case["intent_id"]: case["verdict"] for case in report["cases"]})
        self.assertEqual([], report["verdict_check"]["unexpected"])
        self.assertEqual(2, len(report["guard_blocks"]))


class TestEnvelopeSafety(ExecutorTestCase):
    def test_drifted_fixture_denies_every_tick(self):
        with open(os.path.join(ROOT, "fixtures", "roles_agent_config.json"),
                  "r", encoding="utf-8") as handle:
            fixture = json.load(handle)
        fixture["role"]["allowances"]["usdc_daily"]["refill_base_units"] = 10_000_000
        drifted = os.path.join(self.tmp, "fixture_drift.json")
        with open(drifted, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(fixture, handle)
        summary = self.run_loop(ticks=1, fixture_path=drifted)
        record = summary["records"][0]
        self.assertEqual("DRIFT", record["state"]["envelope_status"])
        self.assertEqual("DENY", record["verdict"])
        self.assertIn("ENVELOPE_DRIFT", record["reasons"])

    def test_missing_fixture_is_unverified_and_denies(self):
        summary = self.run_loop(ticks=1, fixture_path=os.path.join(self.tmp, "absent.json"))
        self.assertEqual("UNVERIFIED", summary["records"][0]["state"]["envelope_status"])
        self.assertIn("ENVELOPE_UNVERIFIED", summary["records"][0]["reasons"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
