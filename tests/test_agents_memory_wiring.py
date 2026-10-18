#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: the ``--memory`` wiring of the agent runtime (M9).

``FTSMemory`` used to be an orphan module: defined, tested in isolation, and
never instantiated by any runner. This bench proves the two halves of the
wiring contract, through the REAL assembly path
(``run_agents.prepare_run`` → ``worker.load_run_spec`` →
``worker._build_tools`` → the registry → a real ``BoundedLoop`` run) — no
reimplementation of the production code:

- DEFAULT (flag absent): the allow-list is exactly the historical seven tools
  (no ``memory_recall``), no ``memory.sqlite`` is created and ``run.json``
  carries no ``memory`` key — so the sealed response store keeps replaying
  bit for bit. This is the regression the whole flag exists to protect.
- FLAG ON: ``FTSMemory`` is instantiated on ``<run_dir>/memory.sqlite``,
  ``memory_recall`` is registered (closed args, bounds enforced by the code),
  every successful observation is remembered with its evidence refs and a
  deterministic ``sha256(role|run_id|step)`` id, the journal's ``TOOL_RESULT``
  line carries the refs of the returned entries and no prompt text, and a
  ``memory_recall`` call consumes the existing tool budget.

Offline, standard library only, no LLM call and no network: the loop runs on a
scripted backend double and fixture data.

Execution: ``python -m unittest tests.test_agents_memory_wiring -v``
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import tools as tools_module  # noqa: E402
from orvyren.agents import worker as worker_mod  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.loop import BoundedLoop  # noqa: E402
from orvyren.agents.memory import FTSMemory  # noqa: E402
from orvyren.agents.tools import (  # noqa: E402
    MEMORY_K_MAX,
    MEMORY_K_MIN,
    MEMORY_QUERY_MAX_CHARS,
    MEMORY_TOOL_NAME,
    TOOL_NAMES,
    MemoryRecallTool,
    ObservationMemory,
    RememberingTool,
    build_registry,
    observation_memory_id,
)

import run_agents  # noqa: E402

CASE = "usdc-2023-03"
PRICE_REF = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"
KRAKEN_REF = "observation:kraken/usdc-usd/2023-03-11T12:00Z"
SUPPLY_REF = "observation:circle/supply/2023-03-11T12:00Z"
SNAPSHOT_REF = "graph_snapshot:usdc-2023-03"
BUDGET = {"llm_calls": 30, "tool_calls": 12, "wall_seconds": 600, "cost_usd": 0.10}


def run_inputs():
    """Minimal, frozen-schema run inputs (fixtures with real ``source_ref``)."""
    return {
        "snapshot": {"ref": SNAPSHOT_REF, "as_of": "2023-03-11T12:00:00Z"},
        "lacunes": [],
        "hypotheses": [{"id": "HYP-1", "enonce": "la dispersion est reutilisable"}],
        "tool_fixtures": {
            "prices": {
                "bitstamp|USDC-USD": [
                    {"venue": "bitstamp", "symbol": "USDC-USD",
                     "ts": "2023-03-11T12:00:00Z", "value": 0.8053,
                     "source_ref": PRICE_REF}],
                "kraken|USDC-USD": [
                    {"venue": "kraken", "symbol": "USDC-USD",
                     "ts": "2023-03-11T12:00:00Z", "value": 0.8801,
                     "source_ref": KRAKEN_REF}],
            },
            "supply": {"usdc": [{"asset": "usdc", "value": 41000000000,
                                 "source_ref": SUPPLY_REF}]},
            "chain": {},
            "documents": {},
            "signals": {},
            "snapshot": {"ref": SNAPSHOT_REF},
        },
    }


def make_run(tmpdir, *, memory):
    """Run the real preparation path; returns ``(run_dir, spec)``."""
    os.makedirs(tmpdir, exist_ok=True)
    session = tempfile.mkdtemp(prefix="session_", dir=tmpdir)
    run_dir = run_agents.prepare_run(
        case_id=CASE, mode="journal", session_dir=session,
        inputs=run_inputs(), store_dir=os.path.join(tmpdir, "store_unused"),
        budget=dict(BUDGET), memory=memory)
    return run_dir, worker_mod.load_run_spec(run_dir)


def memory_path(run_dir):
    return os.path.join(run_dir, worker_mod.MEMORY_DB_NAME)


# ---------------------------------------------------------------------------
# Doubles (test-only): scripted LLM backend and a recall spy.
# ---------------------------------------------------------------------------
class ScriptedBackend(contracts.LLMBackend):
    """One scripted :class:`contracts.LLMResult` per call, in order."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def complete(self, *, role, role_version, schema_id, system_prompt, payload):
        self.calls.append({"schema_id": schema_id,
                           "payload": json.loads(json.dumps(payload, default=str))})
        if not self.script:
            raise AssertionError("ScriptedBackend exhausted (call %d)" % len(self.calls))
        return self.script.pop(0)


def llm_ok(data, *, n):
    text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return contracts.LLMResult(
        ok=True, raw=text, data=data, provider="fake", model="fake-orch",
        model_version_pinned="fake-orch-2026-01", temperature=0.0,
        tokens_in=100, cached_in=0, tokens_out=40, cost_usd=0.001,
        latency_ms=0,
        prompt_hash=hashlib.sha256(("prompt-%d" % n).encode()).hexdigest(),
        response_hash=hashlib.sha256(("response-%d" % n).encode()).hexdigest(),
        ts_utc="2023-03-11T12:00:00+00:00")


def plan_memory_recall_data(*, query="usdc", k=2):
    """A valid ``orvyren/orch/v1`` plan whose one task calls ``memory_recall``."""
    return {
        "$schema": "orvyren/orch/v1", "lacune_id": "L-1",
        "tache": {"question": "qu a-t-on deja observe sur la dispersion entre venues",
                  "outil": MEMORY_TOOL_NAME, "args": {"query": query, "k": k},
                  "critere_discriminant": "une reference deja memorisee revient",
                  "branches_concernees": ["HYP-1"], "cout_max": {}},
        "stop": False, "motif_stop": None, "non_recherche": [],
    }


def plan_stop_data():
    return {"$schema": "orvyren/orch/v1", "lacune_id": "L-1", "tache": None,
            "stop": True, "motif_stop": "plus de tache utile", "non_recherche": []}


def evaluation_data(refs):
    return {"claims": [{"enonce": "la memoire rend l observation reutilisable",
                        "refs": list(refs), "sens": "soutient",
                        "branches_concernees": ["HYP-1"]}],
            "reflexions": "", "insuffisance": "", "note": ""}


class SpyMemory:
    """Memory double counting recalls (proves a refused call never queries)."""

    def __init__(self):
        self.queries = []

    def recall(self, query, k=5):
        self.queries.append((query, k))
        return ()


# ---------------------------------------------------------------------------
# (a) Default behaviour is unchanged.
# ---------------------------------------------------------------------------
class TestDefaultIsUnchanged(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_mem_off_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_run_spec_carries_no_memory_key_by_default(self):
        run_dir, spec = make_run(self.tmp, memory=False)
        self.assertNotIn("memory", spec)
        with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as handle:
            raw = json.load(handle)
        self.assertNotIn("memory", raw)

    def test_registry_has_no_memory_tool_and_creates_no_database(self):
        run_dir, spec = make_run(self.tmp, memory=False)
        registry = worker_mod._build_tools(spec, AgentJournal(), run_dir=run_dir)
        self.assertNotIn(MEMORY_TOOL_NAME, registry.names())
        self.assertEqual(tuple(registry.names()), TOOL_NAMES)
        self.assertFalse(os.path.exists(memory_path(run_dir)))

    def test_build_registry_default_still_exposes_the_seven_v1_tools(self):
        """``build_registry(memory=None)`` is the historical fixture list."""
        registry = build_registry(mode="fixture", journal=AgentJournal(),
                                  fixtures=run_inputs()["tool_fixtures"])
        self.assertEqual(tuple(registry.names()), TOOL_NAMES)
        # ... and every registered object is the historical tool itself: no
        # remembering wrapper sneaks in when memory is absent.
        self.assertFalse(any(isinstance(registry.get(name), RememberingTool)
                             for name in registry.names()))


# ---------------------------------------------------------------------------
# (b) The flag turns the memory on.
# ---------------------------------------------------------------------------
class TestFlagOn(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_mem_on_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.run_dir, self.spec = make_run(self.tmp, memory=True)
        self.clock = worker_mod.VirtualClock("2023-03-11T12:00:00+00:00")
        self.journal = AgentJournal()
        self.registry = worker_mod._build_tools(
            self.spec, self.journal, run_dir=self.run_dir, clock=self.clock)

    # -- assembly ---------------------------------------------------------
    def test_database_is_created_in_the_run_directory(self):
        self.assertTrue(os.path.isfile(memory_path(self.run_dir)))
        self.assertTrue(self.spec.get("memory"))

    def test_memory_recall_is_registered_and_tools_are_wrapped(self):
        self.assertIn(MEMORY_TOOL_NAME, self.registry.names())
        self.assertIsInstance(self.registry.get(MEMORY_TOOL_NAME), MemoryRecallTool)
        self.assertIsInstance(self.registry.get("read_prices"), RememberingTool)
        # The run's own output sink and the recall tool are never wrapped:
        # journal_write is not an observation, a recall must not re-remember.
        self.assertNotIsInstance(self.registry.get("journal_write"), RememberingTool)
        self.assertNotIsInstance(self.registry.get(MEMORY_TOOL_NAME), RememberingTool)

    def test_tool_spec_is_a_closed_english_object(self):
        spec = tools_module.MEMORY_TOOL_SPEC["function"]
        self.assertEqual(spec["name"], MEMORY_TOOL_NAME)
        self.assertIn("Recall earlier observations", spec["description"])
        params = spec["parameters"]
        self.assertFalse(params["additionalProperties"])
        self.assertEqual(sorted(params["properties"]), ["k", "query"])
        self.assertEqual(params["properties"]["k"]["minimum"], MEMORY_K_MIN)
        self.assertEqual(params["properties"]["k"]["maximum"], MEMORY_K_MAX)
        self.assertEqual(params["properties"]["query"]["maxLength"],
                         MEMORY_QUERY_MAX_CHARS)

    # -- remember / recall -------------------------------------------------
    def test_every_successful_observation_is_remembered_with_its_refs(self):
        result = self.registry.get("read_prices").run(
            {"venue": "bitstamp", "symbol": "USDC-USD"})
        self.assertTrue(result.ok)
        memory = FTSMemory(memory_path(self.run_dir))
        self.assertEqual(memory.count(), 1)
        entry = memory.entries()[0]
        self.assertEqual(entry.refs, (PRICE_REF,))
        self.assertIn("bitstamp", entry.text)
        self.assertEqual(entry.memory_id,
                         observation_memory_id("orchestrator", self.spec["run_id"], 0))

    def test_a_failed_observation_is_not_remembered(self):
        result = self.registry.get("read_prices").run(
            {"venue": "venue-inconnue", "symbol": "USDC-USD"})
        self.assertFalse(result.ok)
        self.assertEqual(FTSMemory(memory_path(self.run_dir)).count(), 0)

    def test_recall_returns_the_remembered_entries(self):
        for args in ({"venue": "bitstamp", "symbol": "USDC-USD"},
                     {"venue": "kraken", "symbol": "USDC-USD"}):
            self.assertTrue(self.registry.get("read_prices").run(args).ok)
        self.assertTrue(self.registry.get("read_supply").run({"asset": "usdc"}).ok)
        recall = self.registry.get(MEMORY_TOOL_NAME)

        two = recall.run({"query": "usdc", "k": 2})
        self.assertTrue(two.ok)
        self.assertEqual(len(two.observations), 2)

        everything = recall.run({"query": "usdc", "k": MEMORY_K_MAX})
        self.assertTrue(everything.ok)
        self.assertEqual(len(everything.observations), 3)
        refs = {ref for item in everything.observations for ref in item["refs"]}
        self.assertEqual(refs, {PRICE_REF, KRAKEN_REF, SUPPLY_REF})
        for item in everything.observations:
            self.assertTrue(item["memory_id"])
            self.assertTrue(item["text"])

    def test_default_k_is_applied_when_omitted(self):
        recall = self.registry.get(MEMORY_TOOL_NAME)
        result = recall.run({"query": "usdc"})
        self.assertTrue(result.ok)

    # -- refusal contract --------------------------------------------------
    def test_out_of_bounds_arguments_are_refused_without_querying(self):
        spy = SpyMemory()
        tool = MemoryRecallTool(spy)
        too_long = "a" * (MEMORY_QUERY_MAX_CHARS + 1)
        cases = (
            ({"query": "usdc", "k": 0}, "E_TOOL_ARGS_RANGE:k"),
            ({"query": "usdc", "k": MEMORY_K_MAX + 1}, "E_TOOL_ARGS_RANGE:k"),
            ({"query": "usdc", "k": -1}, "E_TOOL_ARGS_RANGE:k"),
            ({"query": "usdc", "k": True}, "E_TOOL_ARGS_TYPE:k"),
            ({"query": ""}, "E_TOOL_ARGS_RANGE:query"),
            ({"query": "   "}, "E_TOOL_ARGS_RANGE:query"),
            ({"query": too_long}, "E_TOOL_ARGS_RANGE:query"),
            ({"query": 42}, "E_TOOL_ARGS_TYPE:query"),
            ({}, "E_TOOL_ARGS_REQUIRED:query"),
            ({"query": "usdc", "limit": 3}, "E_TOOL_ARGS_UNKNOWN:limit"),
        )
        for args, expected in cases:
            with self.subTest(args=args):
                result = tool.run(args)
                self.assertFalse(result.ok)
                self.assertEqual(result.status, "FAILED")
                self.assertIn(expected, result.error)
        # Never a silent execution: a refused call does not reach the memory.
        self.assertEqual(spy.queries, [])

    def test_recall_is_bounded_by_k(self):
        for venue in ("bitstamp", "kraken"):
            self.registry.get("read_prices").run(
                {"venue": venue, "symbol": "USDC-USD"})
        result = self.registry.get(MEMORY_TOOL_NAME).run({"query": "usdc", "k": 1})
        self.assertEqual(len(result.observations), 1)


# ---------------------------------------------------------------------------
# Determinism: same entries -> same ids (replay requirement).
# ---------------------------------------------------------------------------
class TestDeterminism(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_mem_det_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_memory_id_is_a_pure_function_of_role_run_and_step(self):
        first = observation_memory_id("orchestrator", "demo-usdc-2023-03", 0)
        second = observation_memory_id("orchestrator", "demo-usdc-2023-03", 0)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, observation_memory_id("orchestrator",
                                                         "demo-usdc-2023-03", 1))
        self.assertNotEqual(first, observation_memory_id("critic",
                                                         "demo-usdc-2023-03", 0))

    def _run_sequence(self, subdir):
        """Same spec, same call sequence, fresh run directory."""
        run_dir, spec = make_run(os.path.join(self.tmp, subdir), memory=True)
        registry = worker_mod._build_tools(
            spec, AgentJournal(), run_dir=run_dir,
            clock=worker_mod.VirtualClock("2023-03-11T12:00:00+00:00"))
        for args in ({"venue": "bitstamp", "symbol": "USDC-USD"},
                     {"venue": "kraken", "symbol": "USDC-USD"}):
            registry.get("read_prices").run(args)
        registry.get("read_supply").run({"asset": "usdc"})
        return FTSMemory(memory_path(run_dir)).entries()

    def test_two_runs_over_the_same_entries_produce_the_same_ids(self):
        first = self._run_sequence("a")
        second = self._run_sequence("b")
        self.assertEqual(len(first), 3)
        self.assertEqual([entry.memory_id for entry in first],
                         [entry.memory_id for entry in second])
        self.assertEqual([entry.refs for entry in first],
                         [entry.refs for entry in second])
        # Same id AND same text: the summary is canonical, the ts_utc comes
        # from the injected virtual clock (never the wall clock).
        self.assertEqual([entry.to_dict() for entry in first],
                         [entry.to_dict() for entry in second])


# ---------------------------------------------------------------------------
# The real loop path: journal line, refs, and the tool budget.
# ---------------------------------------------------------------------------
class TestLoopPath(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_mem_loop_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.run_dir, self.spec = make_run(self.tmp, memory=True)
        self.clock = worker_mod.VirtualClock("2023-03-11T12:00:00+00:00")
        self.journal = AgentJournal()
        self.registry = worker_mod._build_tools(
            self.spec, self.journal, run_dir=self.run_dir, clock=self.clock)
        # Seed one real observation through the registry (the memory path).
        self.assertTrue(self.registry.get("read_prices").run(
            {"venue": "bitstamp", "symbol": "USDC-USD"}).ok)

    def _loop(self, script, budget=None):
        backend = ScriptedBackend(script)
        loop = BoundedLoop(
            case_id=CASE, run_id=self.spec["run_id"], agent_id="orchestrator",
            backend=backend, tools=self.registry, journal=self.journal,
            budget=budget, clock=self.clock, prompt_version="orch-test",
            system_prompt="system", snapshot=self.spec["snapshot"],
            lacunes=self.spec["lacunes"], hypotheses=self.spec["hypotheses"])
        return loop, loop.run()

    def test_recall_call_journals_its_refs_and_no_prompt_text(self):
        script = [llm_ok(plan_memory_recall_data(), n=1),
                  llm_ok(evaluation_data([PRICE_REF]), n=2),
                  llm_ok(plan_stop_data(), n=3)]
        loop, outcome = self._loop(script)
        self.assertEqual(outcome.stop_condition, "ARRET-1")

        results = [entry for entry in self.journal.entries()
                   if entry.kind == "TOOL_RESULT" and entry.content.startswith(MEMORY_TOOL_NAME)]
        self.assertEqual(len(results), 1)
        line = results[0]
        self.assertEqual(line.content, "memory_recall status=OK error=-")
        self.assertIn(PRICE_REF, line.refs)
        # No prompt text / no recalled payload on the journal line.
        self.assertNotIn("bitstamp", line.content)
        self.assertNotIn("observations", line.content)
        self.assertEqual(line.refs, (PRICE_REF,))

        # SPEC §5: the recall is one tool call of the existing budget.
        self.assertEqual(loop.usage().tool_calls, 1)

    def test_zero_tool_budget_blocks_the_recall_call(self):
        budget = contracts.Budget(tool_calls=0)
        script = [llm_ok(plan_memory_recall_data(), n=1)]
        backend = ScriptedBackend(script)
        loop = BoundedLoop(
            case_id=CASE, run_id=self.spec["run_id"], agent_id="orchestrator",
            backend=backend, tools=self.registry, journal=self.journal,
            budget=budget, clock=self.clock, prompt_version="orch-test",
            system_prompt="system", snapshot=self.spec["snapshot"],
            lacunes=self.spec["lacunes"], hypotheses=self.spec["hypotheses"])
        outcome = loop.run()
        self.assertEqual(outcome.stop_condition, "ARRET-2")
        self.assertEqual(backend.calls, [])  # stopped before any spend
        self.assertFalse([entry for entry in self.journal.entries()
                          if entry.kind in ("TOOL_CALL", "TOOL_RESULT")])

    def test_rememberer_is_deterministic_inside_the_loop_too(self):
        """The entry id is the observation index, not a wall-clock value."""
        memory = FTSMemory(memory_path(self.run_dir))
        entries = memory.entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].memory_id,
                         observation_memory_id("orchestrator", self.spec["run_id"], 0))


if __name__ == "__main__":
    unittest.main()
