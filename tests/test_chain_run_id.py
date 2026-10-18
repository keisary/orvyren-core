#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — shared ``run_id`` run chain bench (event-sourcing + contracts).

Regression suite for ``orvyren.chain`` and its executor integration (P0-2):
unique run identity, hash-chained events, hashed artifact contracts, verified
handoffs between decision -> policy -> execution, ``parent_run_id`` on re-runs
and the fail-closed refusal of real execution without an explicit ``run_id``.

Everything is offline and stdlib: fixed clock, temporary paths, no key read.

Run: python -m unittest tests.test_chain_run_id -v
            python -m pytest tests/test_chain_run_id.py -q
"""

import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.chain import (  # noqa: E402
    E_CHAIN_CONTRACT,
    E_CHAIN_RUN_ID_REQUIRED,
    GENESIS_HASH,
    SCHEMA_ARTIFACT,
    SCHEMA_MANIFEST,
    ChainContractError,
    ChainRunIdRequired,
    RunChain,
    new_run_id,
)
from orvyren.execution import loop as executor  # noqa: E402
from orvyren.policy import ALLOWED_ASSET, ALLOWED_CHAIN_ID  # noqa: E402

import run_executor  # noqa: E402

POLICY = os.path.join(ROOT, "policy_v1.yaml")
RESERVE = "0x1111111111111111111111111111111111111111"
BASE_ENV = {"ORVYREN_AGENT_MEMBER": "true", "ORVYREN_AVAILABLE_BALANCE": "1000"}
NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
RUN_ID = "run-20261018T120000000000Z-001122334455"
PARENT_RUN_ID = "run-20261017T090000000000Z-554433221100"

RUN_ID_PATTERN = re.compile(r"^run-\d{8}T\d{12}Z-[0-9a-f]{12}$")


def make_bundle():
    bundle = executor.load_bundle(POLICY, {"B": RESERVE})
    executor.apply_permission_window(bundle, NOW)
    return bundle


def make_provider(amount=100.0):
    """Synthetic decision: one bounded transfer, no corpus dependency."""
    def provider(tick, now):
        return {
            "case": "usdc-2023-03",
            "epistemic_verdict": "CONCLUANT",
            "economic_action": "CONVERTIR/TRANSFÉRER",
            "authorization_verdict": "ALLOW",
            "intent": {
                "intent_id": "intent-test-chain",
                "action": "transfer",
                "chain_id": ALLOWED_CHAIN_ID,
                "asset": ALLOWED_ASSET,
                "amount": amount,
                "recipient": RESERVE,
            },
        }
    return provider


def read_events(root_dir):
    with open(os.path.join(root_dir, "events.jsonl"), "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def file_sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def invoke_cli(argv, env=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run_executor.main(argv, env={} if env is None else env,
                                 clock=lambda: NOW)
    return code, out.getvalue(), err.getvalue()


# --------------------------------------------------------------------------
# run_id
# --------------------------------------------------------------------------
class TestRunId(unittest.TestCase):
    def test_run_ids_are_unique(self):
        generated = [new_run_id() for _ in range(500)]
        self.assertEqual(500, len(set(generated)), "run_id must never repeat")

    def test_run_id_is_readable_utc_plus_hex(self):
        for identifier in (new_run_id() for _ in range(20)):
            self.assertRegex(identifier, RUN_ID_PATTERN)

    def test_prefix_is_carried(self):
        self.assertTrue(new_run_id("replay").startswith("replay-"))

    def test_invalid_prefix_is_rejected(self):
        for bad in ("", "  ", "../escape", "a/b", None, 7):
            with self.assertRaises(ValueError):
                new_run_id(bad)


# --------------------------------------------------------------------------
# event chain
# --------------------------------------------------------------------------
class TestRunChainEvents(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "chain")
        self.chain = RunChain(RUN_ID, "usdc-2023-03", parent_run_id=PARENT_RUN_ID,
                              root_dir=self.root)

    def test_event_lines_carry_run_id_case_id_stage_ts_prev_hash(self):
        self.chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        self.chain.record("policy", "POLICY_DECIDED", {"tick": 1})
        events = read_events(self.root)
        self.assertEqual(2, len(events))
        for index, event in enumerate(events, start=1):
            self.assertEqual(RUN_ID, event["run_id"])
            self.assertEqual(PARENT_RUN_ID, event["parent_run_id"])
            self.assertEqual("usdc-2023-03", event["case_id"])
            self.assertIn("stage", event)
            self.assertTrue(event["ts_utc"])
            self.assertEqual(index, event["seq"])
            self.assertEqual(64, len(event["prev_hash"]))
            self.assertEqual(64, len(event["event_hash"]))
        self.assertEqual(GENESIS_HASH, events[0]["prev_hash"])
        self.assertEqual(events[0]["event_hash"], events[1]["prev_hash"])
        ok, message = self.chain.verify()
        self.assertTrue(ok, message)

    def test_broken_event_chain_is_detected_by_verify(self):
        self.chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        self.chain.record("policy", "POLICY_DECIDED", {"tick": 1})
        events = read_events(self.root)
        events[0]["payload"] = {"tick": 99}  # silent rewrite of a signed line
        with open(os.path.join(self.root, "events.jsonl"), "w",
                  encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        ok, message = self.chain.verify()
        self.assertFalse(ok)
        self.assertIn("events: line 1", message)

    def test_broken_event_chain_refuses_to_load(self):
        self.chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        with open(os.path.join(self.root, "events.jsonl"), "a",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"run_id": RUN_ID, "seq": 2,
                                     "prev_hash": "f" * 64}) + "\n")
        with self.assertRaises(ChainContractError):
            RunChain(RUN_ID, "usdc-2023-03", parent_run_id=PARENT_RUN_ID,
                     root_dir=self.root)

    def test_record_returns_the_persisted_line(self):
        line = self.chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        self.assertEqual(line, read_events(self.root)[0])
        self.assertEqual(RUN_ID, line["run_id"])
        self.assertEqual("decision", line["stage"])

    def test_record_rejects_non_mapping_payload(self):
        with self.assertRaises(ChainContractError):
            self.chain.record("decision", "DECISION_REPLAYED", ["not", "a", "mapping"])


# --------------------------------------------------------------------------
# artifact contracts
# --------------------------------------------------------------------------
class TestRunChainArtifacts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "chain")
        self.chain = RunChain(RUN_ID, "usdc-2023-03", root_dir=self.root)

    def write(self, name="intent.json", payload=None):
        return self.chain.write_artifact(
            "decision", name, payload if payload is not None else {"amount": 100.0})

    def test_write_artifact_returns_sha256_and_updates_manifest(self):
        digest = self.write()
        path = os.path.join(self.root, "decision", "intent.json")
        self.assertEqual(digest, file_sha256(path))
        entry = self.chain.manifest()["artifacts"]["intent.json"]
        self.assertEqual({"stage": "decision", "sha256": digest,
                          "bytes": os.path.getsize(path)}, entry)

    def test_artifact_carries_its_provenance_envelope(self):
        self.write()
        with open(os.path.join(self.root, "decision", "intent.json"),
                  "r", encoding="utf-8") as handle:
            envelope = json.load(handle)
        self.assertEqual(SCHEMA_ARTIFACT, envelope["schema"])
        self.assertEqual(RUN_ID, envelope["run_id"])
        self.assertEqual("usdc-2023-03", envelope["case_id"])
        self.assertEqual("decision", envelope["stage"])
        self.assertEqual({"amount": 100.0}, envelope["payload"])

    def test_altered_artifact_is_detected_by_verify(self):
        self.write()
        ok, message = self.chain.verify()
        self.assertTrue(ok, message)
        with open(os.path.join(self.root, "decision", "intent.json"), "a",
                  encoding="utf-8", newline="\n") as handle:
            handle.write(" ")
        ok, message = self.chain.verify()
        self.assertFalse(ok)
        self.assertIn("sha256 mismatch", message)

    def test_handoff_on_missing_artifact_raises(self):
        with self.assertRaises(ChainContractError) as caught:
            self.chain.handoff("decision", "policy", ["absent.json"])
        self.assertEqual(E_CHAIN_CONTRACT, caught.exception.code)

    def test_handoff_detects_altered_artifact(self):
        self.write()
        with open(os.path.join(self.root, "decision", "intent.json"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write("{}\n")
        with self.assertRaises(ChainContractError):
            self.chain.handoff("decision", "policy", ["intent.json"])

    def test_handoff_returns_verified_artifacts(self):
        digest = self.write()
        handed = self.chain.handoff("decision", "policy", ["intent.json"])
        self.assertTrue(handed["ok"])
        self.assertEqual("decision", handed["stage_from"])
        self.assertEqual("policy", handed["stage_to"])
        self.assertEqual(digest, handed["artifacts"]["intent.json"]["sha256"])

    def test_handoff_rejects_a_bare_string(self):
        with self.assertRaises(ChainContractError):
            self.chain.handoff("decision", "policy", "intent.json")

    def test_artifacts_are_immutable(self):
        self.write(payload={"amount": 100.0})
        with self.assertRaises(ChainContractError):
            self.write(payload={"amount": 1.0})

    def test_artifact_names_and_stages_are_flat(self):
        for stage, name in (("decision", "../escape.json"), ("dec/ision", "a.json"),
                            ("decision", "sub/dir.json"), ("", "a.json")):
            with self.assertRaises(ChainContractError):
                self.chain.write_artifact(stage, name, {})


# --------------------------------------------------------------------------
# manifest + re-run identity
# --------------------------------------------------------------------------
class TestRunChainManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "chain")

    def test_manifest_is_schema_version_plus_sha256_per_file(self):
        chain = RunChain(RUN_ID, "usdc-2023-03", root_dir=self.root)
        chain.write_artifact("decision", "intent.json", {"amount": 100.0})
        chain.write_artifact("policy", "policy.json", {"verdict": "ALLOW"})
        manifest = chain.manifest()
        self.assertEqual(SCHEMA_MANIFEST, manifest["schema_version"])
        self.assertEqual(RUN_ID, manifest["run_id"])
        self.assertEqual("usdc-2023-03", manifest["case_id"])
        self.assertEqual(2, len(manifest["artifacts"]))
        for name, entry in manifest["artifacts"].items():
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$", name)
            self.assertGreater(entry["bytes"], 0)
        with open(os.path.join(self.root, "manifest.json"), "r", encoding="utf-8") as handle:
            self.assertEqual(manifest, json.load(handle))

    def test_rerun_carries_parent_run_id(self):
        chain = RunChain(RUN_ID, "usdc-2023-03", parent_run_id=PARENT_RUN_ID,
                         root_dir=self.root)
        chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        self.assertEqual(PARENT_RUN_ID, chain.manifest()["parent_run_id"])
        self.assertEqual(PARENT_RUN_ID, read_events(self.root)[0]["parent_run_id"])

    def test_same_run_id_with_another_parent_is_refused(self):
        RunChain(RUN_ID, "usdc-2023-03", parent_run_id=PARENT_RUN_ID,
                 root_dir=self.root).record("decision", "DECISION_REPLAYED", {"tick": 1})
        with self.assertRaises(ChainContractError):
            RunChain(RUN_ID, "usdc-2023-03", parent_run_id="run-20260101T000000000000Z-010101010101",
                     root_dir=self.root)

    def test_parent_run_id_equal_to_run_id_is_refused(self):
        with self.assertRaises(ChainContractError):
            RunChain(RUN_ID, "usdc-2023-03", parent_run_id=RUN_ID, root_dir=self.root)

    def test_events_head_matches_the_last_event(self):
        chain = RunChain(RUN_ID, "usdc-2023-03", root_dir=self.root)
        line = chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        self.assertEqual(line["event_hash"], chain.manifest()["events_head"])

    def test_verify_is_clean_on_a_consistent_chain(self):
        chain = RunChain(RUN_ID, "usdc-2023-03", root_dir=self.root)
        chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        chain.write_artifact("decision", "intent.json", {"amount": 100.0})
        self.assertEqual((True, ""), chain.verify())


# --------------------------------------------------------------------------
# executor integration
# --------------------------------------------------------------------------
class TestExecutorChainIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_run_")
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
            env=dict(BASE_ENV),
            clock=lambda: NOW,
            sleep=lambda seconds: None,
        )
        params.update(overrides)
        return executor.run_loop(**params)

    def test_dry_run_auto_generates_run_id_and_writes_the_shared_chain(self):
        summary = self.run_loop(ticks=2)
        self.assertRegex(summary["run_id"], RUN_ID_PATTERN)
        self.assertEqual(summary["run_id"], summary["chain"]["run_id"])
        self.assertTrue(summary["chain"]["verify_ok"], summary["chain"]["verify_error"])
        self.assertEqual(6, summary["chain"]["artifacts"])  # 2 ticks x 3 artifacts
        with open(self.journal, "r", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(2, len(lines))
        for line in lines:
            self.assertEqual(summary["run_id"], line["chain"]["run_id"])
            self.assertTrue(line["chain"]["verify_ok"], line["chain"]["verify_error"])
            self.assertNotEqual(GENESIS_HASH, line["chain"]["events_head"])

    def test_intent_policy_receipt_artifacts_are_hashed_in_the_manifest(self):
        summary = self.run_loop(ticks=1)
        root = summary["chain"]["root_dir"]
        manifest = load_json(os.path.join(root, "manifest.json"))
        self.assertEqual(SCHEMA_MANIFEST, manifest["schema_version"])
        self.assertEqual(
            {"decision": "intent-t001.json",
             "policy": "policy-t001.json",
             "execution": "receipt-t001.json"},
            {entry["stage"]: name for name, entry in manifest["artifacts"].items()})
        for name, entry in manifest["artifacts"].items():
            path = os.path.join(root, entry["stage"], name)
            self.assertEqual(entry["sha256"], file_sha256(path), name)
            self.assertEqual(entry["bytes"], os.path.getsize(path), name)
        intent = load_json(os.path.join(root, "decision", "intent-t001.json"))
        self.assertNotIn("created_at", intent["payload"])  # wall-clock free payload

    def test_transitions_decision_policy_execution_are_event_sourced(self):
        summary = self.run_loop(ticks=1)
        events = read_events(summary["chain"]["root_dir"])
        self.assertEqual(
            [("decision", "DECISION_REPLAYED"),
             ("decision", "TRANSITION"),
             ("policy", "POLICY_DECIDED"),
             ("policy", "TRANSITION"),
             ("execution", "EXECUTION_RESULT")],
            [(event["stage"], event["event"]) for event in events])
        transitions = [event for event in events if event["event"] == "TRANSITION"]
        self.assertEqual([("decision", "policy"), ("policy", "execution")],
                         [(t["payload"]["stage_from"], t["payload"]["stage_to"])
                          for t in transitions])
        self.assertEqual(summary["run_id"], events[-1]["run_id"])
        for event in events:
            self.assertNotIn("ts_utc", event["payload"])  # ts_utc is signed apart

    def test_denied_tick_still_writes_the_policy_decision_artifact(self):
        summary = self.run_loop(ticks=1, env={"ORVYREN_K0_PAUSED": "1"})
        self.assertEqual("DENIED_POLICY", summary["records"][0]["outcome"])
        self.assertEqual(2, summary["chain"]["artifacts"])  # intent + policy, no receipt
        events = read_events(summary["chain"]["root_dir"])
        self.assertEqual(("policy", "POLICY_DECIDED"), (events[-1]["stage"],
                                                        events[-1]["event"]))

    def test_explicit_run_id_and_parent_run_id_are_carried_everywhere(self):
        summary = self.run_loop(ticks=1, run_id=RUN_ID, parent_run_id=PARENT_RUN_ID)
        self.assertEqual(RUN_ID, summary["run_id"])
        self.assertEqual(PARENT_RUN_ID, summary["parent_run_id"])
        self.assertEqual(PARENT_RUN_ID, summary["chain"]["parent_run_id"])
        root = summary["chain"]["root_dir"]
        manifest = load_json(os.path.join(root, "manifest.json"))
        self.assertEqual(RUN_ID, manifest["run_id"])
        self.assertEqual(PARENT_RUN_ID, manifest["parent_run_id"])
        for event in read_events(root):
            self.assertEqual(PARENT_RUN_ID, event["parent_run_id"])

    def test_real_mode_without_run_id_is_refused_fail_closed(self):
        with self.assertRaises(ChainRunIdRequired) as caught:
            self.run_loop(dry_run=False,
                          execute=lambda intent, record: {"tx_hash": "0x" + "12" * 32})
        self.assertEqual(E_CHAIN_RUN_ID_REQUIRED, caught.exception.code)
        self.assertFalse(os.path.exists(self.journal))
        self.assertFalse(os.path.exists(self.ledger))

    def test_contract_failure_stops_the_run_fail_closed(self):
        """An artifact altered between ticks is caught by verify() — stop."""
        tampered = {"done": False}

        def provider(tick, now):
            if tick == 2 and not tampered["done"]:
                path = os.path.join(self.tmp, "chain", RUN_ID,
                                    "decision", "intent-t001.json")
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("{}\n")
                tampered["done"] = True
            return make_provider()(tick, now)

        with self.assertRaises(ChainContractError) as caught:
            self.run_loop(ticks=2, run_id=RUN_ID, decision_provider=provider)
        self.assertEqual(E_CHAIN_CONTRACT, caught.exception.code)
        with open(self.journal, "r", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(2, len(lines))  # evidence is journaled before the stop
        self.assertTrue(lines[0]["chain"]["verify_ok"])
        self.assertFalse(lines[1]["chain"]["verify_ok"])
        self.assertIn("intent-t001.json", lines[1]["chain"]["verify_error"])


# --------------------------------------------------------------------------
# CLI integration
# --------------------------------------------------------------------------
class TestExecutorCliRunId(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_cli_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.journal = os.path.join(self.tmp, "journal.jsonl")
        self.ledger = os.path.join(self.tmp, "ledger.json")

    def argv(self, *extra):
        return ["--ticks", "1", "--dry-run", "--json",
                "--journal", self.journal, "--ledger", self.ledger] + list(extra)

    def test_execute_without_run_id_is_refused_before_any_tick(self):
        code, _, err = invoke_cli(["--execute", "--ticks", "1",
                                   "--journal", self.journal, "--ledger", self.ledger])
        self.assertEqual(run_executor.executor.EXIT_EXECUTE, code)
        self.assertIn(E_CHAIN_RUN_ID_REQUIRED, err)
        self.assertFalse(os.path.exists(self.journal))
        self.assertFalse(os.path.exists(self.ledger))

    def test_dry_run_auto_generates_run_id(self):
        code, out, _ = invoke_cli(self.argv("--demo-defaults"))
        self.assertEqual(0, code)
        payload = json.loads(out)
        self.assertRegex(payload["run_id"], RUN_ID_PATTERN)
        self.assertTrue(payload["chain"]["verify_ok"], payload["chain"]["verify_error"])

    def test_cli_run_id_and_parent_run_id_reach_the_chain(self):
        code, out, _ = invoke_cli(self.argv("--demo-defaults",
                                            "--run-id", RUN_ID,
                                            "--parent-run-id", PARENT_RUN_ID))
        self.assertEqual(0, code)
        payload = json.loads(out)
        self.assertEqual(RUN_ID, payload["run_id"])
        self.assertEqual(PARENT_RUN_ID, payload["parent_run_id"])
        manifest = load_json(os.path.join(payload["chain"]["root_dir"], "manifest.json"))
        self.assertEqual(PARENT_RUN_ID, manifest["parent_run_id"])

    def test_cli_rejects_parent_run_id_equal_to_run_id(self):
        code, _, err = invoke_cli(self.argv("--run-id", RUN_ID,
                                            "--parent-run-id", RUN_ID))
        self.assertEqual(run_executor.executor.EXIT_USAGE, code)
        self.assertIn("E_CHAIN_CONTRACT", err)
        self.assertFalse(os.path.exists(self.journal))


if __name__ == "__main__":
    unittest.main(verbosity=2)
