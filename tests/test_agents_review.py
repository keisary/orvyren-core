#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: review findings on ``agents`` (replay determinism + robustness).

Covers the fixes of the deep review (D:/orvyren_10h_2026-10-17/review/agents.md):

- ``ToolTurnRunner`` journal timestamps come from the injected clock (a
  replayed turn must rewrite byte-identical journal lines);
- a terminal ``LiveBackend`` failure (transport / provider chain / no key) is
  archived and replayed as the SAME failure, never as ``E_LLM_NOT_RECORDED``;
- ``RecordedBackend`` walks the recorded calls of one prompt hash **in
  recorded order** (fail then success stays fail then success);
- ``worker.VirtualClock`` never falls back to the real clock;
- a tool that raises is data (``E_TOOL_RUNTIME``), never a crash of the loop;
- ``journal_write`` refuses a mistyped ``refs`` / ``step_index``;
- graph tools forward an explicit ``0`` instead of silently using the default;
- ``deterministic_validator`` rejects mistyped columns instead of raising.

Execution: ``python -m pytest tests/test_agents_review.py -q``
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import worker as worker_mod  # noqa: E402
from orvyren.agents.journal import (  # noqa: E402
    AgentJournal,
    entry_hash,
)
from orvyren.agents.llm import (  # noqa: E402
    LiveBackend,
    RecordedBackend,
    ToolTurnRunner,
    load_models_config,
)
from orvyren.agents.store import ResponseStore, response_hash  # noqa: E402

ENV = {"ORVYREN_DEEPSEEK_API_KEY": "cle-de-test"}
ROLE = "orchestrator"
ROLE_VERSION = "orch-p1.1.0"
SCHEMA_ID = "orvyren/orch/v1"
SYSTEM = "SYSTEME DE TEST (revue)."
PAYLOAD = {"snapshot_at": "2023-03-12T00:00:00Z", "question": "etat du graphe"}

ORCH_RESPONSE = contracts.canonical_json(
    {"$schema": "orvyren/orch/v1", "lacune_id": "L1", "tache": None,
     "stop": True, "motif_stop": "rien a chercher", "non_recherche": []})


def kwargs(**overrides):
    data = dict(role=ROLE, role_version=ROLE_VERSION, schema_id=SCHEMA_ID,
                system_prompt=SYSTEM, payload=PAYLOAD)
    data.update(overrides)
    return data


def call_line(prompt_hash, resp_hash, **overrides):
    entry = {
        "record_id": "rec-" + prompt_hash[:12], "prompt_hash": prompt_hash,
        "response_hash": resp_hash, "role": ROLE, "role_version": ROLE_VERSION,
        "schema_id": SCHEMA_ID, "ts_utc": "2026-10-16T00:00:00Z",
    }
    entry.update(overrides)
    return entry


class FakeHTTP:
    """Scripted transport: (status, text) tuples or exceptions, in order."""

    def __init__(self, script):
        self.script = list(script)

    def __call__(self, url, headers, body_bytes, timeout):
        if not self.script:
            raise AssertionError("unexpected extra HTTP call")
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FixedClock:
    """Clock with a fixed ``now_iso`` (loop/worker clock shape)."""

    def __init__(self, stamp="2023-03-11T12:00:00+00:00"):
        self.stamp = stamp
        self.t = 0.0

    def monotonic(self):
        self.t += 0.02
        return self.t

    def now_iso(self):
        return self.stamp


class TestToolTurnJournalDeterminism(unittest.TestCase):
    """llm.py:769 — the journal stamp comes from the injected clock."""

    def _journal(self, clock):
        journal = AgentJournal()
        runner = ToolTurnRunner(object(), object(), journal,
                                agent_id="revue", clock=clock)
        runner._journal("TOOL_CALL", "call graph_query")
        runner._journal("TOOL_RESULT", "graph_query -> OK")
        return journal

    def test_toolturn_journal_ts_is_injectable(self):
        journal = self._journal(FixedClock())
        stamps = [entry.ts_utc for entry in journal.entries()]
        self.assertEqual(stamps, ["2023-03-11T12:00:00+00:00"] * 2)

    def test_two_runs_with_the_same_clock_rewrite_identical_journals(self):
        first, second = self._journal(FixedClock()), self._journal(FixedClock())
        self.assertEqual([entry_hash(e) for e in first.entries()],
                         [entry_hash(e) for e in second.entries()])
        self.assertEqual(first.entries()[-1].prev_hash,
                         second.entries()[-1].prev_hash)

    def test_without_now_iso_the_live_default_stamps_a_utc_timestamp(self):
        journal = self._journal(None)
        self.assertRegex(journal.entries()[0].ts_utc, r"^\d{4}-\d{2}-\d{2}T")


class TestTerminalFailuresAreRecorded(unittest.TestCase):
    """llm.py — transport / provider-chain failures must replay as failures."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = ResponseStore(self._tmp.name)
        self.config = load_models_config()

    def _live(self, env, script):
        return LiveBackend(self.config, store=self.store, env=env,
                           http_post=FakeHTTP(script))

    def test_transport_failure_is_recorded_and_replayed(self):
        live = self._live(ENV, [(500, "boom")] * 3)
        result = live.complete(**kwargs())
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_LLM_ALL_PROVIDERS_FAILED")
        recorded = self.store.calls()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["error"], "E_LLM_ALL_PROVIDERS_FAILED")
        replay = RecordedBackend(self.store, self.config).complete(**kwargs())
        self.assertFalse(replay.ok)
        self.assertEqual(replay.error, "E_LLM_ALL_PROVIDERS_FAILED")
        self.assertEqual(replay.to_dict(), result.to_dict(),
                         "a replayed failure is bit-identical")

    def test_no_key_failure_is_recorded_and_replayed(self):
        live = self._live({}, [])
        result = live.complete(**kwargs())
        self.assertEqual(result.error, "E_LLM_NO_KEY")
        replay = RecordedBackend(self.store, self.config).complete(**kwargs())
        self.assertEqual(replay.error, "E_LLM_NO_KEY")

    def test_store_still_verifies_after_a_recorded_failure(self):
        self._live(ENV, [(500, "boom")] * 3).complete(**kwargs())
        ok, problems = self.store.verify()
        self.assertTrue(ok, msg=f"problems: {problems}")


class TestRecordedSequenceConsumption(unittest.TestCase):
    """llm.py — same prompt twice: fail then success stays fail then success."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = ResponseStore(self._tmp.name)
        self.config = load_models_config()
        self.p_hash = self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                             SYSTEM, PAYLOAD)
        # record 1: a content failure; record 2: the success of the retry.
        self.r_fail = response_hash("")
        self.r_ok = response_hash(ORCH_RESPONSE)
        self.store.save_prompt(self.p_hash, SYSTEM, PAYLOAD)
        self.store.save_response(self.r_fail, "")
        self.store.save_response(self.r_ok, ORCH_RESPONSE)
        self.store.record_call(call_line(self.p_hash, self.r_fail,
                                         record_id="rec-fail",
                                         error="E_LLM_EMPTY_RESPONSE"))
        self.store.record_call(call_line(self.p_hash, self.r_ok,
                                         record_id="rec-ok"))

    def test_replay_walks_the_recorded_sequence(self):
        backend = RecordedBackend(self.store, self.config)
        first = backend.complete(**kwargs())
        self.assertFalse(first.ok)
        self.assertEqual(first.error, "E_LLM_EMPTY_RESPONSE")
        self.assertEqual(first.response_hash, self.r_fail)
        second = backend.complete(**kwargs())
        self.assertTrue(second.ok, second.error)
        self.assertEqual(second.response_hash, self.r_ok)
        # the recorded sequence is exhausted: the last call answers again
        third = backend.complete(**kwargs())
        self.assertTrue(third.ok, third.error)
        self.assertEqual(third.response_hash, self.r_ok)

    def test_a_fresh_backend_replays_the_same_sequence(self):
        again = RecordedBackend(self.store, self.config)
        self.assertFalse(again.complete(**kwargs()).ok)
        self.assertTrue(again.complete(**kwargs()).ok)


class TestVirtualClockFallback(unittest.TestCase):
    """worker.py:95 — a missing/unparseable base must never read the real clock."""

    def test_fallback_base_is_deterministic(self):
        first = worker_mod.VirtualClock("")
        second = worker_mod.VirtualClock("pas un timestamp")
        self.assertEqual([first.now_iso() for _ in range(3)],
                         [second.now_iso() for _ in range(3)])

    def test_monotonic_reads_advance_the_frozen_base(self):
        clock = worker_mod.VirtualClock("2026-10-16T18:00:00+00:00",
                                        step_seconds=0.02)
        self.assertEqual(clock.now_iso(), "2026-10-16T18:00:00+00:00")
        clock.monotonic()
        self.assertEqual(clock.now_iso(), "2026-10-16T18:00:00.020000+00:00")


class _RaisingTool:
    name = "read_prices"

    def run(self, args, *, deadline_s=20.0):
        raise RuntimeError("boom")


class _FakeLoopBackend(contracts.LLMBackend):
    def __init__(self, script):
        self.script = list(script)

    def complete(self, **call):
        return self.script.pop(0)


def _llm_result(data, n):
    return contracts.LLMResult(
        ok=True, raw=contracts.canonical_json(data), data=data,
        provider="fake", model="fake-orch", model_version_pinned="fake-2026",
        temperature=0.0, tokens_in=10, cached_in=0, tokens_out=5,
        cost_usd=0.001, latency_ms=1,
        prompt_hash=("%02d" % n) * 32, response_hash=("%02d" % (n + 50)) * 32,
        ts_utc="2023-03-11T12:00:00+00:00")


class TestToolCrashIsData(unittest.TestCase):
    """loop.py — a tool that raises is a FAILED result, never a crash."""

    def test_a_raising_tool_never_crashes_the_run(self):
        from orvyren.agents.loop import BoundedLoop
        from orvyren.agents.tools import ToolRegistry

        registry = ToolRegistry()
        registry.register("read_prices", _RaisingTool())
        plan_task = {"$schema": "orvyren/orch/v1", "lacune_id": "L-1",
                     "tache": {"question": "la venue est-elle sous le pair",
                               "outil": "read_prices", "args": {},
                               "critere_discriminant": "deux venues",
                               "branches_concernees": [], "cout_max": {}},
                     "stop": False, "motif_stop": None, "non_recherche": []}
        plan_stop = {"$schema": "orvyren/orch/v1", "lacune_id": "",
                     "tache": None, "stop": True,
                     "motif_stop": "aucune tache utile", "non_recherche": []}
        script = [_llm_result(plan_task, 1), _llm_result(plan_stop, 2)]
        journal = AgentJournal()
        loop = BoundedLoop(
            case_id="c", run_id="r", agent_id="orchestrator",
            backend=_FakeLoopBackend(script), tools=registry,
            journal=journal, clock=FixedClock(),
            snapshot={}, lacunes=(), hypotheses=())
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition),
                         ("DONE", "ARRET-1"))
        results = [entry for entry in journal.entries()
                   if entry.kind == "TOOL_RESULT"]
        self.assertTrue(results)
        self.assertTrue(all("E_TOOL_RUNTIME:RuntimeError" in entry.content
                            for entry in results))


class TestJournalWriteArgTypes(unittest.TestCase):
    """tools.py — a mistyped refs/step_index never reaches the journal."""

    def setUp(self):
        from orvyren.agents.tools import JournalWriteTool
        self.journal = AgentJournal()
        self.tool = JournalWriteTool(self.journal, clock=FixedClock())

    def test_refs_as_a_bare_string_is_refused(self):
        result = self.tool.run({"content": "x", "refs": "rel:1"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_TOOL_ARGS_TYPE:refs")
        self.assertEqual(len(self.journal), 0)

    def test_mistyped_step_index_is_refused(self):
        result = self.tool.run({"content": "x", "step_index": "quatre"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "E_TOOL_ARGS_TYPE:step_index")
        self.assertEqual(len(self.journal), 0)

    def test_a_list_of_refs_still_writes(self):
        result = self.tool.run({"content": "x", "refs": ["rel:1"]})
        self.assertTrue(result.ok, result.error)
        self.assertEqual(self.journal.entries()[0].refs, ("rel:1",))


class _CapturingApi:
    def __init__(self):
        self.seen = {}

    def exposure(self, db, holder, **kw):
        self.seen["exposure"] = dict(kw, holder=holder)
        return {"rows": []}

    def pit(self, db, **kw):
        self.seen["pit"] = dict(kw)
        return {"rows": []}

    def dependency_paths(self, db, src, dst, **kw):
        self.seen["q2"] = dict(kw, src=src, dst=dst)
        return {"paths": []}


class TestExplicitZeroArgsAreForwarded(unittest.TestCase):
    """graph_tools — ``0`` is a value, never a missing key."""

    def test_zero_max_depth_and_limit_are_forwarded(self):
        from orvyren.agents.graph_tools import GraphPathTool, GraphQueryTool

        api = _CapturingApi()
        GraphQueryTool(db=None, api=api).run(
            {"query": "Q1", "holder": "h", "max_depth": 0})
        GraphQueryTool(db=None, api=api).run({"query": "Q4", "limit": 0})
        GraphPathTool(db=None, api=api).run(
            {"src": "a", "dst": "b", "max_depth": 0})
        self.assertEqual(api.seen["exposure"]["max_depth"], 0)
        self.assertEqual(api.seen["pit"]["limit"], 0)
        self.assertEqual(api.seen["q2"]["max_depth"], 0)

    def test_absent_args_keep_the_defaults(self):
        from orvyren.agents.graph_tools import GraphQueryTool

        api = _CapturingApi()
        GraphQueryTool(db=None, api=api).run({"query": "Q1", "holder": "h"})
        self.assertEqual(api.seen["exposure"]["max_depth"], 3)


class TestValidatorNeverRaises(unittest.TestCase):
    """journal.py — mistyped columns are REJECTED, never a crash."""

    def test_mistyped_step_index_is_rejected_not_crashed(self):
        journal = AgentJournal()
        entry = journal.append_dict({
            "journal_id": "j-1", "run_id": "r", "episode_id": "e",
            "agent_id": "a", "role_version": "v1", "step_index": "quatre",
            "ts_utc": "2023-03-11T12:00:00+00:00", "kind": "REFLECTION",
            "content": "x"})
        self.assertEqual(entry.status, "REJECTED")
        self.assertTrue(journal.verify_chain()[0])

    def test_mistyped_identity_columns_are_rejected(self):
        journal = AgentJournal()
        entry = journal.append_dict({
            "journal_id": 42, "run_id": "r", "episode_id": "e",
            "agent_id": "a", "role_version": "v1", "step_index": 0,
            "ts_utc": "2023-03-11T12:00:00+00:00", "kind": "REFLECTION",
            "content": "x"})
        self.assertEqual(entry.status, "REJECTED")

    def test_a_conforming_line_is_still_proposed(self):
        journal = AgentJournal()
        entry = journal.append_dict({
            "journal_id": "j-1", "run_id": "r", "episode_id": "e",
            "agent_id": "a", "role_version": "v1", "step_index": 0,
            "ts_utc": "2023-03-11T12:00:00+00:00", "kind": "REFLECTION",
            "content": "x", "refs": ("rel:1",)})
        self.assertEqual(entry.status, "PROPOSED")
        self.assertTrue(journal.promote(entry))


class _NotRecordedBackend:
    """A replay backend answering like RecordedBackend on a missing record."""

    def complete(self, **call):
        return contracts.LLMResult(
            ok=False, error="E_LLM_NOT_RECORDED:" + "f" * 64,
            provider="deepseek", model="deepseek-flash",
            model_version_pinned="V4.1-Flash", temperature=0.0,
            prompt_hash="f" * 64, response_hash="", ts_utc="2026-10-16T00:00:00Z")


class TestCriticLineWithoutResponseHash(unittest.TestCase):
    """worker.py — a failed call without response blob keeps its line usable."""

    def test_critic_quarantine_line_is_proposed_without_llm_mapping(self):
        run_dir = tempfile.mkdtemp(prefix="orvyren-critic-")
        self.addCleanup(shutil.rmtree, run_dir, ignore_errors=True)
        os.makedirs(os.path.join(run_dir, "exchanges"))
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema": "orvyren/agent-run/v1", "run_id": "r",
                       "case_id": "c", "mode": "journal",
                       "budget": {"llm_calls": 30, "tool_calls": 12,
                                  "wall_seconds": 600, "cost_usd": 0.10},
                       "snapshot": {}, "lacunes": [], "hypotheses": [],
                       "tool_fixtures": {}, "store_dir": "store",
                       "created_at": "2026-10-16T18:00:00+00:00"}, handle)
        packet = contracts.EvidencePacket(packet_id="r-packet", refs=("rel:1",))
        with open(os.path.join(run_dir, "exchanges", "001_evidence_packet.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(packet.to_dict(), handle)
        with mock.patch.object(worker_mod, "build_backend",
                               lambda spec, run_dir, role: _NotRecordedBackend()):
            code = worker_mod.run_critic(run_dir, wait_s=1.0)
        self.assertEqual(code, 0)
        entries = worker_mod.load_journal(
            os.path.join(run_dir, "journal_critic.jsonl"))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].llm, {})
        self.assertEqual(entries[0].status, "PROPOSED",
                         "a failed call without response blob is documented, "
                         "never REJECTED for a missing hash")


if __name__ == "__main__":
    unittest.main()
