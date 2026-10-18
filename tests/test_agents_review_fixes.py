#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests — 2026-10-18 full bug-hunt review (agents + chain).

One test per fix of this review (report: D:/orvyren_work_2026-10-18/review/
agents_chain.md):

- reflexion: a bare-string ``refs`` is refused (it would be iterated
  character by character into one-character "references") — in
  ``add_evidence``, ``add_claim`` and the ``from_dict`` tamper path;
- memory: ``recall`` refuses a bound that would become ``LIMIT -1``
  (unlimited) — P1-1 style limits are enforced everywhere;
- worker.build_evidence_packet (P0-6): a REJECTED ``OBSERVATION_REF`` line
  never whitewashes its invented refs into the provenance ledger, and an
  unobserved ref never travels in the packet's ``refs``;
- loop: the journal_write LLM provenance/accounting columns are bound by the
  loop, never model-supplied (no forged hashes/cost in the journal);
- run_agents: default session/store paths use the safe case token, the run
  stamp has sub-second precision (no same-second collision), the write is
  atomic and the worker timeout derives from the wall budget;
- chain: identifiers are ASCII per contract, artifact paths are contained in
  ``root_dir`` (Windows drive-letter escape), a tampered manifest stage is
  refused at load and a deleted manifest is detected by ``verify()``.

Execution: ``python -m unittest tests.test_agents_review_fixes``
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.agents import contracts, reflexion  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.loop import BoundedLoop  # noqa: E402
from orvyren.agents.memory import E_MEMORY_K, FTSMemory  # noqa: E402
from orvyren.agents.worker import build_evidence_packet  # noqa: E402
from orvyren.chain import ChainContractError, RunChain, new_run_id  # noqa: E402

import run_agents  # noqa: E402

REF_OK = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"
REF_FAKE = "observation:invented/never-returned"
SNAPSHOT_REF = "graph_snapshot:usdc-2023-03@2023-03-11T12:00:00Z"
CASE = "usdc-2023-03"


def _entry_data(**overrides):
    """One schema-valid journal line as an append_dict mapping."""
    data = {
        "journal_id": "jw-test-1", "run_id": "run-test", "episode_id": CASE,
        "agent_id": "orchestrator", "role_version": "tool-jw/v1", "step_index": 0,
        "ts_utc": "2023-03-11T12:00:00+00:00", "kind": "REFLECTION",
        "content": "la lecture est confirmee par la source archivee",
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# reflexion — refs typing (a bare string must never become char refs).
# ---------------------------------------------------------------------------
class AchRefsTypeTest(unittest.TestCase):
    def test_add_evidence_refuses_a_bare_string(self):
        matrix = reflexion.EvidenceMatrix()
        with self.assertRaises(ValueError) as caught:
            matrix.add_evidence("EV-1", "ref:abc")
        self.assertIn("E_ACH_REFS_TYPE", str(caught.exception))

    def test_add_claim_refuses_a_bare_string_refs(self):
        matrix = reflexion.EvidenceMatrix()
        matrix.add_hypothesis("HYP-001", "h")
        with self.assertRaises(ValueError) as caught:
            matrix.add_claim({"enonce": "c", "sens": "POUR",
                              "refs": "ref:abc",
                              "branches_concernees": ["HYP-001"]}, "EV-001")
        self.assertIn("E_ACH_REFS_TYPE", str(caught.exception))
        self.assertEqual(matrix.evidence_ids(), ())  # nothing half-registered

    def test_from_dict_refuses_a_tampered_string_refs(self):
        matrix = reflexion.EvidenceMatrix()
        matrix.add_hypothesis("HYP-001", "h")
        matrix.add_evidence("EV-1", ["r:1"], 1.0)
        matrix.score("HYP-001", "EV-1", reflexion.COHERENT)
        data = matrix.to_dict()
        data["evidence"][0]["refs"] = "r:1"  # tampered: a bare string
        with self.assertRaises(ValueError) as caught:
            reflexion.EvidenceMatrix.from_dict(data)
        self.assertIn("E_ACH_REFS_TYPE", str(caught.exception))

    def test_round_trip_stays_exact(self):
        matrix = reflexion.EvidenceMatrix()
        matrix.add_hypothesis("HYP-001", "h")
        matrix.add_evidence("EV-1", ["r:1", "r:2"], 0.5)
        matrix.score("HYP-001", "EV-1", reflexion.INCOHERENT)
        data = matrix.to_dict()
        self.assertEqual(reflexion.EvidenceMatrix.from_dict(data).to_dict(), data)


# ---------------------------------------------------------------------------
# memory — recall is bounded (no silent LIMIT -1).
# ---------------------------------------------------------------------------
class MemoryRecallBoundTest(unittest.TestCase):
    def setUp(self):
        self.memory = FTSMemory()
        for index in range(3):
            self.memory.remember("m%d" % index, "exposition WETH %d" % index,
                                 ["rel:%d" % index])

    def test_negative_k_is_refused_not_unlimited(self):
        with self.assertRaises(ValueError) as caught:
            self.memory.recall("exposition", -1)
        self.assertIn(E_MEMORY_K, str(caught.exception))

    def test_non_integer_k_is_refused(self):
        for bad in (True, 2.5, "2"):
            with self.assertRaises(ValueError):
                self.memory.recall("exposition", bad)

    def test_zero_is_a_bounded_empty_answer(self):
        self.assertEqual(self.memory.recall("exposition", 0), ())

    def test_default_bound_still_answers(self):
        self.assertEqual(len(self.memory.recall("exposition")), 3)


# ---------------------------------------------------------------------------
# worker.build_evidence_packet — P0-6 provenance on the packet path.
# ---------------------------------------------------------------------------
class EvidencePacketProvenanceTest(unittest.TestCase):
    def test_rejected_observation_ref_never_whitewashes_an_invented_ref(self):
        journal = AgentJournal()
        journal.append_dict(
            _entry_data(journal_id="jw-obs", kind="OBSERVATION_REF",
                        refs=(REF_FAKE,), content="observation inventee"),
            reject_reason="E_REF_NOT_OBSERVED: %s" % REF_FAKE)
        journal.append_dict(
            _entry_data(journal_id="jw-claim", refs=(REF_FAKE,),
                        content="claim sur une ref inventee"))
        ledger = contracts.ObservedRefs([SNAPSHOT_REF])
        packet = build_evidence_packet(journal, ledger, run_id="run-test",
                                       case_id=CASE, snapshot_ref=SNAPSHOT_REF)
        self.assertEqual(packet.claims, ())
        self.assertNotIn(REF_FAKE, packet.refs)
        self.assertIn("1 claim(s) excluded: ref not observed (P0-6)",
                      packet.summary)

    def test_an_invented_ref_never_travels_in_packet_refs(self):
        journal = AgentJournal()
        journal.append_dict(_entry_data(
            journal_id="jw-tr", kind="TOOL_RESULT", refs=(REF_OK,),
            content="read_prices status=OK error=-"))
        journal.append_dict(_entry_data(
            journal_id="jw-bad", refs=(REF_FAKE,), content="claim inventé"),
            reject_reason="E_REF_NOT_OBSERVED: %s" % REF_FAKE)
        ledger = contracts.ObservedRefs([SNAPSHOT_REF])
        packet = build_evidence_packet(journal, ledger, run_id="run-test",
                                       case_id=CASE, snapshot_ref=SNAPSHOT_REF)
        self.assertEqual(list(packet.refs), [REF_OK])

    def test_usable_tool_results_still_seed_the_ledger(self):
        journal = AgentJournal()
        journal.append_dict(_entry_data(
            journal_id="jw-tr", kind="TOOL_RESULT", refs=(REF_OK,),
            content="read_prices status=OK error=-"))
        journal.append_dict(_entry_data(
            journal_id="jw-good", refs=(REF_OK,), content="claim sourcé"))
        ledger = contracts.ObservedRefs([SNAPSHOT_REF])
        packet = build_evidence_packet(journal, ledger, run_id="run-test",
                                       case_id=CASE, snapshot_ref=SNAPSHOT_REF)
        self.assertEqual([claim["journal_id"] for claim in packet.claims],
                         ["jw-good"])
        self.assertEqual(list(packet.refs), [REF_OK])
        self.assertNotIn("excluded", packet.summary)


# ---------------------------------------------------------------------------
# loop — the journal_write LLM columns are bound by the loop.
# ---------------------------------------------------------------------------
class LoopReservedJournalFieldsTest(unittest.TestCase):
    def setUp(self):
        self.loop = BoundedLoop(
            case_id=CASE, run_id="run-test", agent_id="orchestrator",
            backend=object(), tools=object(), journal=AgentJournal(),
            snapshot={}, lacunes=(), hypotheses=())

    def test_model_supplied_llm_accounting_is_never_bound(self):
        task = contracts.ResearchTask(
            question="q", outil="journal_write",
            args={"kind": "REFLECTION", "content": "note",
                  "llm": {"provider": "fake", "model": "fake"},
                  "prompt_hash": "f" * 64, "response_hash": "e" * 64,
                  "tokens_in": 999, "tokens_out": 999, "cached_in": 999,
                  "cost_usd": 9.9, "latency_ms": 9999,
                  "run_id": "forged", "journal_id": "forged"})
        args = self.loop._bound_tool_args(task)
        for key in ("llm", "prompt_hash", "response_hash", "tokens_in",
                    "tokens_out", "cached_in", "cost_usd", "latency_ms"):
            self.assertNotIn(key, args, key)
        self.assertEqual(args["run_id"], "run-test")   # bound by the loop
        self.assertEqual(args["agent_id"], "orchestrator")

    def test_only_reflection_and_observation_ref_pass(self):
        task = contracts.ResearchTask(question="q", outil="journal_write",
                                      args={"kind": "STOP", "content": "x"})
        self.assertIsNone(self.loop._bound_tool_args(task))


# ---------------------------------------------------------------------------
# run_agents — paths, stamps, atomic write, worker timeout.
# ---------------------------------------------------------------------------
class RunAgentsPathsAndTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.session = tempfile.mkdtemp(prefix="orvyren_review_")
        self.addCleanup(shutil.rmtree, self.session, ignore_errors=True)

    def _capture_spawn(self, argv, extra_env=None):
        captured = {}

        def fake_spawn(role, run_dir, timeout_s):
            captured.setdefault("timeouts", []).append(timeout_s)
            return 3  # stop before any real worker runs

        buffer = io.StringIO()
        with mock.patch.object(run_agents, "_spawn", fake_spawn), \
                contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                run_agents.main(argv + ["--session", self.session])
        return captured

    def test_default_store_path_uses_the_safe_case_token(self):
        self._capture_spawn(["--case", "x/../usdc-2023-03", "--replay", "journal"])
        run_dirs = [name for name in os.listdir(self.session)
                    if os.path.isdir(os.path.join(self.session, name))]
        self.assertEqual(len(run_dirs), 1)
        with open(os.path.join(self.session, run_dirs[0], "run.json"),
                  encoding="utf-8") as handle:
            spec = json.load(handle)
        self.assertEqual(spec["store_dir"],
                         os.path.join(ROOT, "fixtures", "agents",
                                      "store_usdc-2023-03"))

    def test_default_worker_timeout_outlives_the_wall_budget(self):
        captured = self._capture_spawn(["--case", CASE, "--replay", "journal"])
        self.assertTrue(captured["timeouts"])
        self.assertGreater(captured["timeouts"][0], 600.0)

    def test_explicit_timeout_is_forwarded_verbatim(self):
        captured = self._capture_spawn(["--case", CASE, "--replay", "journal",
                                        "--timeout-s", "42"])
        self.assertEqual(captured["timeouts"], [42.0])

    def test_run_stamps_never_collide_within_one_second(self):
        inputs = {"snapshot": {}, "lacunes": [], "hypotheses": [],
                  "tool_fixtures": {}}
        dirs = {run_agents.prepare_run(
            case_id=CASE, mode="journal", session_dir=self.session,
            inputs=inputs, store_dir=self.session, budget={"llm_calls": 30})
            for _ in range(3)}
        self.assertEqual(len(dirs), 3)

    def test_write_json_is_atomic(self):
        path = os.path.join(self.session, "out.json")
        run_agents._write_json(path, {"b": 1, "a": 2})
        self.assertFalse(os.path.exists(path + ".tmp"))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), {"a": 2, "b": 1})


# ---------------------------------------------------------------------------
# chain — identifiers, path containment, tamper resistance.
# ---------------------------------------------------------------------------
class ChainHardeningTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_chain_review_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "chain")

    def test_identifiers_are_ascii_per_contract(self):
        with self.assertRaises(ValueError):
            new_run_id("run\u00e9")  # non-ASCII prefix
        with self.assertRaises(ChainContractError):
            RunChain("run-\u00e9", CASE, root_dir=self.root)

    @unittest.skipUnless(os.name == "nt", "Windows drive-letter escape")
    def test_drive_letter_stage_cannot_escape_root_dir(self):
        chain = RunChain("run-test", CASE, root_dir=self.root)
        with self.assertRaises(ChainContractError):
            chain.write_artifact("C:", "x.json", {})
        self.assertFalse(os.path.exists("x.json"))

    @unittest.skipUnless(os.name == "nt", "Windows drive-letter escape")
    def test_tampered_manifest_stage_is_refused_at_load(self):
        chain = RunChain("run-test", CASE, root_dir=self.root)
        chain.write_artifact("decision", "intent.json", {"amount": 1})
        with open(chain.manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        manifest["artifacts"]["intent.json"]["stage"] = "C:"
        with open(chain.manifest_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle)
        with self.assertRaises(ChainContractError) as caught:
            RunChain("run-test", CASE, root_dir=self.root)
        self.assertIn("invalid stage", str(caught.exception))

    def test_deleted_manifest_is_detected_by_verify(self):
        chain = RunChain("run-test", CASE, root_dir=self.root)
        chain.record("decision", "DECISION_REPLAYED", {"tick": 1})
        os.remove(chain.manifest_path)
        ok, message = chain.verify()
        self.assertFalse(ok)
        self.assertIn("manifest", message)

    def test_empty_chain_without_manifest_still_verifies(self):
        chain = RunChain("run-test", CASE, root_dir=self.root)
        self.assertEqual((True, ""), chain.verify())


if __name__ == "__main__":
    unittest.main()
