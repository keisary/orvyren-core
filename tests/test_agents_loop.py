#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``loop`` — the bounded loop and its five stop conditions (L2.2).

Covers DOC2 §5.2.4-5.2.5 and B1_AGENTS_ETUDE.md §4:

- the frozen keyword-only signature and the state policy (``DONE`` for orderly
  stops, ``ABORTED`` for the fail-closed ARRET-3);
- the happy path: two tasks -> ``DONE`` / ``ARRET-1``, hash-chained journal,
  PLAN / TOOL_CALL / TOOL_RESULT / REFLECTION / STOP lines, promotions with
  LLM-origin weight 0;
- the four budget counters (``llm_calls``, ``tool_calls``, ``wall_seconds`` via
  an injected clock, ``cost_usd`` via scripted costs) -> ``ARRET-2``;
- ``ARRET-3`` on twice-invalid output (quarantine then fail-closed) and on a
  repeated LLM failure;
- a broken source: retry <= 2 then unavailable, the run continues and the
  forced-abstention rule marks the outcome ``inconclusive`` with the unsearched
  questions in ``non_recherche``;
- the ARRET-4 / ARRET-5 guard-rail hooks;
- the loop never reads real time and never touches policy or execution.

The backend is a scripted :class:`contracts.LLMBackend` living in this file
(deterministic hashes), the clock a deterministic fake with the same shape as
``worker.VirtualClock``.

Execution: ``python -m pytest tests/test_agents_loop.py -q``
"""

import ast
import hashlib
import inspect
import json
import os
import sys
import unittest
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import loop as loop_module  # noqa: E402
from orvyren.agents import tools as tools_module  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.loop import (  # noqa: E402
    EVAL_SCHEMA_ID,
    MAX_LLM_ATTEMPTS,
    MAX_TOOL_ATTEMPTS,
    PLAN_SCHEMA_ID,
    BoundedLoop,
)
from orvyren.agents.tools import (  # noqa: E402
    FailingTool,
    ToolRegistry,
    build_v1_registry,
)

#: Questions of the scripted plans (no digit — the schema forbids it).
QUESTION_PRICES = "la dispersion confirme-t-elle une dislocation realisable entre venues"
QUESTION_SUPPLY = "l'offre en circulation confirme-t-elle la lecture de stress"
REF_PRICES = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"
REF_SUPPLY = "observation:circle/supply/2023-03-11T12:00Z"


# ---------------------------------------------------------------------------
# Doubles: clock and backend.
# ---------------------------------------------------------------------------
class FakeClock:
    """Deterministic clock: a fixed step per read (worker.VirtualClock shape)."""

    def __init__(self, step_seconds=0.02, base_iso="2023-03-11T12:00:00+00:00"):
        self._t = 0.0
        self._step = float(step_seconds)
        self._base = datetime.fromisoformat(base_iso)

    def monotonic(self):
        self._t += self._step
        return self._t

    def now_iso(self):
        return (self._base + timedelta(seconds=self._t)).isoformat()


class FakeBackend(contracts.LLMBackend):
    """Scripted backend: one :class:`contracts.LLMResult` per call.

    Records every call (role, version, schema, prompt, payload) so a test can
    assert what the loop asked for — the payload is deep-copied to freeze it.
    """

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def complete(self, *, role, role_version, schema_id, system_prompt, payload):
        self.calls.append({
            "role": role, "role_version": role_version, "schema_id": schema_id,
            "system_prompt": system_prompt,
            "payload": json.loads(json.dumps(payload, ensure_ascii=False, default=str)),
        })
        if not self.script:
            raise AssertionError("FakeBackend script exhausted (call %d)" % len(self.calls))
        return self.script.pop(0)


def _hashes(n):
    return (hashlib.sha256(("prompt-%d" % n).encode()).hexdigest(),
            hashlib.sha256(("response-%d" % n).encode()).hexdigest())


def llm_ok(data, *, n, cost=0.001, tokens_in=100, tokens_out=40):
    """A successful scripted call carrying the response and its accounting."""
    prompt_hash, response_hash = _hashes(n)
    return contracts.LLMResult(
        ok=True, raw=json.dumps(data, ensure_ascii=False, sort_keys=True), data=data,
        provider="fake", model="fake-orch", model_version_pinned="fake-orch-2026-01",
        temperature=0.0, tokens_in=tokens_in, cached_in=0, tokens_out=tokens_out,
        cost_usd=cost, latency_ms=12, prompt_hash=prompt_hash,
        response_hash=response_hash, ts_utc="2023-03-11T12:00:00.000000+00:00")


def llm_error(n, *, error="E_LLM_TIMEOUT", cost=0.0005):
    """A failed scripted call (transport class, no response at all)."""
    return contracts.LLMResult(
        ok=False, raw="", data=None, error=error, provider="fake", model="fake-orch",
        model_version_pinned="fake-orch-2026-01", temperature=0.0, tokens_in=0,
        cached_in=0, tokens_out=0, cost_usd=cost, latency_ms=0, prompt_hash="",
        response_hash="", ts_utc="2023-03-11T12:00:00.000000+00:00")


# ---------------------------------------------------------------------------
# Scripted model outputs.
# ---------------------------------------------------------------------------
def plan_task_data(*, question=QUESTION_PRICES, outil="read_prices", args=None,
                   lacune_id="L-1",
                   critere="deux venues sous le pair", non_recherche=()):
    """A valid ``orvyren/orch/v1`` plan holding exactly one task."""
    return {"$schema": "orvyren/orch/v1", "lacune_id": lacune_id,
            "tache": {"question": question, "outil": outil,
                      "args": dict(args if args is not None
                                   else {"venue": "bitstamp", "symbol": "USDC-USD",
                                         "from": "2023-03-01", "to": "2023-03-31"}),
                      "critere_discriminant": critere,
                      "branches_concernees": ["HYP-001"], "cout_max": {}},
            "stop": False, "motif_stop": None, "non_recherche": list(non_recherche)}


def plan_stop_data(*, motif="les lacunes restantes n'ont pas de valeur discriminante",
                   non_recherche=()):
    """A valid closing plan: no task left with positive value (ARRET-1)."""
    return {"$schema": "orvyren/orch/v1", "lacune_id": "", "tache": None, "stop": True,
            "motif_stop": motif, "non_recherche": list(non_recherche)}


def eval_data(*, enonce="la venue d'exchange se situe sous les deux agregateurs",
              refs=(REF_PRICES,), reflexions="lecture conforme au snapshot"):
    """A valid free-schema evaluation with one referenced claim."""
    return {"claims": [{"enonce": enonce, "refs": list(refs)}], "reflexions": reflexions}


def eval_empty_data(*, reflexions="aucun claim exploitable sur cette observation"):
    """A valid evaluation with no claim at all."""
    return {"claims": [], "reflexions": reflexions}


def fixtures():
    """The frozen fixture schema (lookup keys) with the USDC/SVB subset."""
    return {
        "prices": {"bitstamp|USDC-USD": [
            {"venue": "bitstamp", "symbol": "USDC-USD", "ts": "2023-03-11T12:00:00Z",
             "value": 0.8053, "source_ref": REF_PRICES}]},
        "supply": {"usdc": [
            {"asset": "usdc", "ts": "2023-03-11T12:00:00Z", "value": 41000000000,
             "source_ref": REF_SUPPLY}]},
        "chain": {},
        "documents": {"https://example.org/note": "Note archivee, aucune instruction."},
        "signals": {"venue_dispersion_bps": {"value": 870, "unit": "bps",
                                             "method_ref": "compute_signal:venue_dispersion_bps/v1"}},
        "snapshot": {"ref": "graph_snapshot:usdc-2023-03@2023-03-11T12:00:00Z",
                     "as_of": "2023-03-11T12:00:00Z",
                     "refs": [REF_PRICES]},
    }


def make_scenario(script, **overrides):
    """Wire one loop on the frozen fixtures; returns (loop, journal, backend, tools)."""
    data = fixtures()
    journal = overrides.pop("journal", None) or AgentJournal()
    backend = FakeBackend(script)
    tools = overrides.pop("tools", None) or build_v1_registry(fixtures=data, journal=journal)
    loop = BoundedLoop(
        case_id="usdc-2023-03", run_id="run-test", agent_id="orchestrator",
        backend=backend, tools=tools, journal=journal,
        budget=overrides.pop("budget", None),
        clock=overrides.pop("clock", None) or FakeClock(),
        prompt_version="orch-p1.0.0",
        system_prompt=overrides.pop("system_prompt", "SYS-INJECTE"),
        snapshot=overrides.pop("snapshot", data["snapshot"]),
        lacunes=overrides.pop("lacunes", [{"lacune_id": "L-1", "question": QUESTION_PRICES}]),
        hypotheses=overrides.pop("hypotheses", [{"id": "HYP-001", "etat": "UNDER_TEST"}]),
        on_promotion=overrides.pop("on_promotion", None),
        sufficient_evidence=overrides.pop("sufficient_evidence", None),
        net_voi=overrides.pop("net_voi", None))
    if overrides:
        raise AssertionError("unknown overrides: %s" % sorted(overrides))
    return loop, journal, backend, tools


def promotion_refs(groups):
    """Flatten the promotions collected by an ``on_promotion`` callback."""
    return [promotion.ref for group in groups for promotion in group]


class InterfaceTest(unittest.TestCase):
    """The frozen L2.2 interface (worker.py calls it verbatim)."""

    def test_constructor_signature_is_frozen(self):
        parameters = inspect.signature(BoundedLoop.__init__).parameters
        self.assertEqual(list(parameters), [
            "self", "case_id", "run_id", "agent_id", "backend", "tools", "journal",
            "budget", "clock", "prompt_version", "system_prompt", "snapshot", "lacunes",
            "hypotheses", "on_promotion", "sufficient_evidence", "net_voi"])
        for name in list(parameters)[1:]:
            self.assertEqual(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY, name)
        self.assertEqual(parameters["agent_id"].default, "orchestrator")
        self.assertEqual(parameters["prompt_version"].default, "orch-p1.0.0")
        for name in ("budget", "clock", "system_prompt", "on_promotion",
                     "sufficient_evidence", "net_voi"):
            self.assertIsNone(parameters[name].default, name)
        for name in ("case_id", "run_id", "backend", "tools", "journal", "snapshot",
                     "lacunes", "hypotheses"):
            self.assertIs(parameters[name].default, inspect.Parameter.empty, name)

    def test_run_takes_no_argument(self):
        self.assertEqual(list(inspect.signature(BoundedLoop.run).parameters), ["self"])

    def test_the_loop_imports_neither_policy_nor_execution(self):
        tree = ast.parse(inspect.getsource(loop_module))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for forbidden in ("orvyren.policy", "orvyren.execution"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".")
                                 for name in imported),
                             "%s imported by loop.py" % forbidden)

    def test_a_widened_budget_is_refused(self):
        for field in ("llm_calls", "tool_calls", "wall_seconds", "cost_usd"):
            with self.assertRaises(ValueError) as caught:
                BoundedLoop(case_id="c", run_id="r", backend=FakeBackend([]),
                            tools=ToolRegistry(), journal=AgentJournal(),
                            budget=contracts.Budget(**{field: 10 ** 6}), snapshot={},
                            lacunes=(), hypotheses=())
            self.assertIn("E_BUDGET_WIDENED", str(caught.exception))

    def test_every_call_uses_the_orchestrator_role_and_the_injected_prompt(self):
        loop, journal, backend, _ = make_scenario([llm_ok(plan_stop_data(), n=1)])
        loop.run()
        self.assertEqual(backend.calls[0]["role"], "orchestrator")
        self.assertEqual(backend.calls[0]["role_version"], "orch-p1.0.0")
        self.assertEqual(backend.calls[0]["system_prompt"], "SYS-INJECTE")

    def test_the_default_system_prompt_is_never_empty(self):
        loop, journal, backend, _ = make_scenario([llm_ok(plan_stop_data(), n=1)],
                                                  system_prompt=None)
        loop.run()
        self.assertTrue(str(backend.calls[0]["system_prompt"]).strip())


class HappyPathTest(unittest.TestCase):
    """Two tasks then a clean stop: the full journal of a bounded run."""

    def setUp(self):
        self.promotions = []
        self.script = [
            llm_ok(plan_task_data(), n=1),
            llm_ok(eval_data(), n=2),
            llm_ok(plan_task_data(question=QUESTION_SUPPLY, outil="read_supply",
                                  args={"asset": "usdc"}, lacune_id="L-2",
                                  critere="l'offre confirme la lecture de stress"), n=3),
            llm_ok(eval_data(enonce="l'offre en circulation soutient la lecture de stress",
                             refs=(REF_SUPPLY,)), n=4),
            llm_ok(plan_stop_data(
                non_recherche=("la profondeur d'execution aux tailles de tresorerie",)), n=5),
        ]
        self.loop, self.journal, self.backend, self.tools = make_scenario(
            self.script, on_promotion=self.promotions.append)
        self.outcome = self.loop.run()
        self.entries = self.journal.entries()

    def test_the_run_ends_done_after_a_closing_plan(self):
        self.assertEqual(self.outcome.state, "DONE")
        self.assertEqual(self.outcome.stop_condition, "ARRET-1")
        self.assertFalse(self.outcome.inconclusive)
        self.assertEqual(self.outcome.critique_verdict, "")

    def test_the_budget_usage_is_reported(self):
        self.assertEqual(self.outcome.budget_used["llm_calls"], 5.0)
        self.assertEqual(self.outcome.budget_used["tool_calls"], 2.0)
        self.assertAlmostEqual(self.outcome.budget_used["cost_usd"], 0.005)
        self.assertGreater(self.outcome.budget_used["wall_seconds"], 0.0)
        self.assertLess(self.outcome.budget_used["wall_seconds"], 600.0)

    def test_the_journal_chain_verifies_and_the_steps_are_increasing(self):
        ok, motif = self.journal.verify_chain()
        self.assertTrue(ok, motif)
        self.assertEqual([entry.step_index for entry in self.entries],
                         list(range(len(self.entries))))

    def test_the_expected_kinds_are_journaled(self):
        self.assertEqual(Counter(entry.kind for entry in self.entries),
                         Counter({"PLAN": 3, "TOOL_CALL": 2, "TOOL_RESULT": 2,
                                  "REFLECTION": 3, "STOP": 1}))
        self.assertEqual(self.entries[-1].kind, "STOP")
        self.assertIn("ARRET-1", self.entries[-1].content)

    def test_every_line_is_proposed_and_lives_in_one_run(self):
        self.assertTrue(all(entry.status == "PROPOSED" for entry in self.entries))
        self.assertTrue(all(entry.run_id == "run-test" for entry in self.entries))
        self.assertTrue(all(entry.agent_id == "orchestrator" for entry in self.entries))
        self.assertTrue(all(entry.episode_id == "usdc-2023-03" for entry in self.entries))

    def test_plan_lines_pin_the_llm_provenance_and_the_accounting(self):
        plan = self.entries[0]
        self.assertEqual(plan.kind, "PLAN")
        self.assertEqual(plan.llm, {"provider": "fake", "model": "fake-orch",
                                    "model_version_pinned": "fake-orch-2026-01",
                                    "temperature": 0.0})
        self.assertEqual(len(plan.prompt_hash), 64)
        self.assertEqual(len(plan.response_hash), 64)
        self.assertEqual((plan.tokens_in, plan.tokens_out), (100, 40))
        self.assertEqual(plan.cost_usd, 0.001)
        self.assertEqual(plan.latency_ms, 12)
        # the tokens/cost of one call ride on exactly one line (no double count)
        self.assertEqual(sum(entry.cost_usd for entry in self.entries), 0.005)

    def test_the_schemas_are_the_frozen_ones(self):
        self.assertEqual([call["schema_id"] for call in self.backend.calls],
                         [PLAN_SCHEMA_ID, EVAL_SCHEMA_ID, PLAN_SCHEMA_ID,
                          EVAL_SCHEMA_ID, PLAN_SCHEMA_ID])
        self.assertEqual((PLAN_SCHEMA_ID, EVAL_SCHEMA_ID), ("orvyren/orch/v1", ""))

    def test_the_planning_payload_carries_the_frozen_keys(self):
        payload = self.backend.calls[0]["payload"]
        for key in ("snapshot_at", "lacunes", "hypotheses", "budget_restant",
                    "sources_autorisees"):
            self.assertIn(key, payload)
        self.assertEqual(payload["snapshot_at"], "2023-03-11T12:00:00Z")
        self.assertEqual(payload["budget_restant"]["llm_calls"], 30.0)
        self.assertEqual(payload["budget_restant"]["tool_calls"], 12.0)
        self.assertEqual(set(payload["sources_autorisees"]), set(tools_module.TOOL_NAMES))
        self.assertNotIn(tools_module.FORBIDDEN_TOOL, payload["sources_autorisees"])
        self.assertEqual(payload["hypotheses"][0]["id"], "HYP-001")

    def test_the_remaining_budget_shrinks_between_cycles(self):
        self.assertEqual(self.backend.calls[2]["payload"]["budget_restant"]["llm_calls"], 28.0)
        self.assertEqual(self.backend.calls[2]["payload"]["outils_indisponibles"], [])

    def test_the_observation_refs_become_promotion_candidates(self):
        self.assertEqual(promotion_refs(self.promotions), [REF_PRICES, REF_SUPPLY])
        weights = {promotion.weight for group in self.promotions for promotion in group}
        self.assertEqual(weights, {0.0})  # LLM-origin: zero weight (B3 R1)
        self.assertEqual({promotion.agent_id for group in self.promotions
                          for promotion in group}, {"orchestrator"})

    def test_the_voi_fallback_is_journaled_once(self):
        noted = [entry for entry in self.entries if "VOI_NOT_ESTIMABLE" in entry.content]
        self.assertEqual(len(noted), 1)

    def test_the_unsearched_items_of_the_closing_plan_are_reported(self):
        self.assertEqual(self.outcome.non_recherche,
                         ("la profondeur d'execution aux tailles de tresorerie",))

    def test_timestamps_and_wall_time_come_from_the_injected_clock(self):
        for entry in self.entries:
            self.assertTrue(entry.ts_utc.startswith("2023-03-11T12:00:00"), entry.ts_utc)
            self.assertNotIn("2026", entry.ts_utc)
        stamps = [entry.ts_utc for entry in self.entries]
        self.assertEqual(stamps, sorted(stamps))  # monotone: virtual clock
        self.assertGreater(self.outcome.budget_used["wall_seconds"], 0.0)


class StopConditionsTest(unittest.TestCase):
    """The five stop conditions (B1 §4.2)."""

    def test_arret_1_a_plan_without_task_stops_cleanly(self):
        loop, journal, backend, _ = make_scenario([llm_ok(plan_stop_data(), n=1)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertTrue(outcome.inconclusive)  # no claim at all -> abstention
        self.assertEqual(outcome.budget_used["llm_calls"], 1.0)
        self.assertEqual(outcome.budget_used["tool_calls"], 0.0)
        self.assertEqual(journal.entries()[-1].kind, "STOP")

    def test_arret_2_llm_calls_counter(self):
        script = [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2)]
        loop, journal, backend, _ = make_scenario(script,
                                                  budget=contracts.Budget(llm_calls=2))
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-2"))
        self.assertIn("llm_calls", outcome.motif)
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)
        self.assertEqual(len(backend.script), 0)  # no third call was attempted
        self.assertTrue(outcome.inconclusive)

    def test_arret_2_tool_calls_counter(self):
        script = [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2)]
        loop, journal, backend, _ = make_scenario(script,
                                                  budget=contracts.Budget(tool_calls=1))
        outcome = loop.run()
        self.assertEqual(outcome.stop_condition, "ARRET-2")
        self.assertIn("tool_calls", outcome.motif)
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)

    def test_arret_2_wall_seconds_counter(self):
        clock = FakeClock(step_seconds=700.0)
        loop, journal, backend, _ = make_scenario([llm_ok(plan_task_data(), n=1)],
                                                  clock=clock)
        outcome = loop.run()
        self.assertEqual(outcome.stop_condition, "ARRET-2")
        self.assertIn("wall_seconds", outcome.motif)
        self.assertEqual(outcome.budget_used["wall_seconds"], 700.0)
        self.assertEqual(outcome.budget_used["tool_calls"], 0.0)
        self.assertEqual(len(backend.script), 0)  # only the planning call ran

    def test_arret_2_cost_usd_counter(self):
        script = [llm_ok(plan_task_data(), n=1, cost=0.006),
                  llm_ok(eval_data(), n=2, cost=0.006)]
        loop, journal, backend, _ = make_scenario(script,
                                                  budget=contracts.Budget(cost_usd=0.01))
        outcome = loop.run()
        self.assertEqual(outcome.stop_condition, "ARRET-2")
        self.assertIn("cost_usd", outcome.motif)
        self.assertAlmostEqual(outcome.budget_used["cost_usd"], 0.012)

    def test_forced_abstention_when_the_budget_runs_out_with_a_task_pending(self):
        script = [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2),
                  llm_ok(plan_task_data(question=QUESTION_SUPPLY, outil="read_supply",
                                        args={"asset": "usdc"}, lacune_id="L-2",
                                        critere="l'offre confirme la lecture de stress"), n=3)]
        loop, journal, backend, _ = make_scenario(script,
                                                  budget=contracts.Budget(llm_calls=3))
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-2"))
        self.assertTrue(outcome.inconclusive)
        self.assertIn(QUESTION_SUPPLY, outcome.non_recherche)
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)
        self.assertEqual(len(backend.script), 0)
        stop_line = journal.entries()[-1]
        self.assertEqual(stop_line.kind, "STOP")
        self.assertIn(QUESTION_SUPPLY, stop_line.content)

    def test_arret_4_the_sufficient_evidence_hook_forces_a_conclusive_stop(self):
        seen = []

        def enough(claims):
            seen.append(claims)
            return bool(claims)

        script = [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2)]
        loop, journal, backend, _ = make_scenario(script, sufficient_evidence=enough)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-4"))
        self.assertFalse(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)
        self.assertTrue(seen[0] and isinstance(seen[0][0], dict))
        self.assertIn("refs", seen[0][0])
        self.assertEqual(len(backend.script), 0)  # no second planning call

    def test_arret_5_the_net_voi_hook_refuses_a_search_not_worth_its_cost(self):
        seen = []

        def voi(tasks):
            seen.append(tasks)
            return 0.0

        loop, journal, backend, _ = make_scenario([llm_ok(plan_task_data(), n=1)],
                                                  net_voi=voi)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-5"))
        self.assertTrue(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["tool_calls"], 0.0)
        self.assertIn(QUESTION_PRICES, outcome.non_recherche)
        self.assertEqual(seen[0][0]["outil"], "read_prices")
        self.assertFalse(any("VOI_NOT_ESTIMABLE" in entry.content
                             for entry in journal.entries()))
        self.assertEqual(len(backend.script), 0)

    def test_arret_5_lets_a_worthwhile_search_through(self):
        loop, journal, backend, _ = make_scenario(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2),
             llm_ok(plan_stop_data(), n=3)],
            net_voi=lambda tasks: 0.02)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)

    def test_a_broken_hook_is_journaled_and_never_blocks_the_run(self):
        def broken_hook(claims):
            raise RuntimeError("hook on fire")

        loop, journal, backend, _ = make_scenario(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2),
             llm_ok(plan_stop_data(), n=3)],
            sufficient_evidence=broken_hook)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertTrue(any("E_LOOP_HOOK" in entry.content for entry in journal.entries()))


class FailurePathTest(unittest.TestCase):
    """Recovery by class (B1 §4.4) and the fail-closed policy."""

    def test_arret_3_after_two_invalid_plans(self):
        bad = plan_task_data(question="le prix est-il sous le pair a 0,80 ?")
        loop, journal, backend, _ = make_scenario([llm_ok(bad, n=1), llm_ok(bad, n=2)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("ABORTED", "ARRET-3"))
        self.assertTrue(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)
        quarantined = [entry for entry in journal.entries()
                       if entry.status == "QUARANTINED"]
        self.assertEqual(len(quarantined), 2)
        self.assertTrue(all(entry.kind == "PLAN" for entry in quarantined))
        self.assertTrue(all("contains a digit" in entry.content for entry in quarantined))
        self.assertTrue(all("quarantine_reason" in entry.validation.get("motif", "")
                            for entry in quarantined))
        self.assertIn("erreurs_validation", backend.calls[1]["payload"])
        self.assertIn("contains a digit",
                      " ".join(backend.calls[1]["payload"]["erreurs_validation"]))
        with self.assertRaises(ValueError) as caught:
            journal.promote(quarantined[0])  # a quarantined line is never usable
        self.assertIn("E_JOURNAL_PROMOTION", str(caught.exception))

    def test_one_invalid_plan_then_a_valid_one_continues(self):
        bad = plan_task_data(question="la dispersion atteint-elle 0,87 ?")
        loop, journal, backend, _ = make_scenario([llm_ok(bad, n=1),
                                                   llm_ok(plan_stop_data(), n=2)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)
        self.assertEqual(len([entry for entry in journal.entries()
                              if entry.status == "QUARANTINED"]), 1)
        self.assertTrue(any(entry.kind == "REFLECTION" and "re-prompting once" in entry.content
                            for entry in journal.entries()))

    def test_a_forbidden_tool_is_treated_as_an_invalid_output(self):
        bad = plan_task_data(outil=tools_module.FORBIDDEN_TOOL, args={})
        loop, journal, backend, _ = make_scenario([llm_ok(bad, n=1),
                                                   llm_ok(plan_stop_data(), n=2)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        quarantined = [entry for entry in journal.entries()
                       if entry.status == "QUARANTINED"]
        self.assertEqual(len(quarantined), 1)
        self.assertIn("E_TOOL_UNKNOWN", quarantined[0].content)
        self.assertIn(tools_module.FORBIDDEN_TOOL, quarantined[0].content)
        self.assertEqual(outcome.budget_used["tool_calls"], 0.0)

    def test_arret_3_after_two_invalid_evaluations(self):
        bad = {"claims": [{"enonce": "claim sans aucune reference"}]}
        loop, journal, backend, _ = make_scenario(
            [llm_ok(plan_task_data(), n=1), llm_ok(bad, n=2), llm_ok(bad, n=3)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("ABORTED", "ARRET-3"))
        self.assertEqual(outcome.budget_used["llm_calls"], 3.0)
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)
        quarantined = [entry for entry in journal.entries()
                       if entry.status == "QUARANTINED"]
        self.assertEqual(len(quarantined), 2)
        self.assertTrue(all(entry.kind == "REFLECTION" for entry in quarantined))
        self.assertTrue(all("refs missing" in entry.content for entry in quarantined))

    def test_llm_transport_failure_is_retried_then_the_run_goes_on(self):
        loop, journal, backend, _ = make_scenario([llm_error(n=1),
                                                   llm_ok(plan_stop_data(), n=2)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(outcome.budget_used["llm_calls"], 2.0)
        errors = [entry for entry in journal.entries() if entry.kind == "ERROR"]
        self.assertEqual(len(errors), 1)
        self.assertIn("E_LLM_CALL_FAILED", errors[0].content)
        self.assertIn("E_LLM_TIMEOUT", errors[0].content)
        self.assertEqual(errors[0].status, "PROPOSED")

    def test_llm_unavailable_after_the_retries_aborts_fail_closed(self):
        loop, journal, backend, _ = make_scenario([llm_error(n=1), llm_error(n=2),
                                                   llm_error(n=3)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("ABORTED", "ARRET-3"))
        self.assertTrue(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], MAX_LLM_ATTEMPTS)
        self.assertEqual(len([entry for entry in journal.entries()
                              if entry.kind == "ERROR"]), MAX_LLM_ATTEMPTS)
        self.assertEqual(len(backend.script), 0)

    def test_a_broken_source_is_retried_twice_then_marked_unavailable(self):
        broken = FailingTool("read_prices")
        registry = ToolRegistry()
        registry.register("read_prices", broken)
        script = [llm_ok(plan_task_data(), n=1),
                  llm_ok(plan_stop_data(motif="la source de prix est indisponible"), n=2)]
        loop, journal, backend, _ = make_scenario(script, tools=registry)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(broken.calls, MAX_TOOL_ATTEMPTS)
        self.assertEqual(outcome.budget_used["tool_calls"], 3.0)
        self.assertTrue(outcome.inconclusive)  # no decisive evidence at all
        self.assertIn(QUESTION_PRICES, outcome.non_recherche)
        results = [entry for entry in journal.entries() if entry.kind == "TOOL_RESULT"]
        self.assertEqual(len(results), MAX_TOOL_ATTEMPTS)
        self.assertTrue(all("status=FAILED" in entry.content for entry in results))
        self.assertTrue(any("E_TOOL_UNAVAILABLE" in entry.content
                            for entry in journal.entries()))
        self.assertEqual(backend.calls[1]["payload"]["outils_indisponibles"],
                         ["read_prices"])

    def test_an_unavailable_source_is_refused_without_a_new_tool_call(self):
        broken = FailingTool("read_prices")
        registry = ToolRegistry()
        registry.register("read_prices", broken)
        script = [llm_ok(plan_task_data(), n=1),      # fails: source marked down
                  llm_ok(plan_task_data(), n=2),      # same tool proposed again
                  llm_ok(plan_stop_data(), n=3)]
        loop, journal, backend, _ = make_scenario(script, tools=registry)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(broken.calls, MAX_TOOL_ATTEMPTS)
        self.assertEqual(outcome.budget_used["tool_calls"], 3.0)
        self.assertIn(QUESTION_PRICES, outcome.non_recherche)

    def test_a_source_that_fails_once_is_retried_and_the_run_continues(self):
        broken = FailingTool("read_prices", fail_times=1)
        registry = ToolRegistry()
        registry.register("read_prices", broken)
        script = [llm_ok(plan_task_data(), n=1), llm_ok(eval_data(), n=2),
                  llm_ok(plan_stop_data(), n=3)]
        loop, journal, backend, _ = make_scenario(script, tools=registry)
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(broken.calls, 2)
        self.assertEqual(outcome.budget_used["tool_calls"], 2.0)
        self.assertFalse(outcome.inconclusive)
        results = [entry for entry in journal.entries() if entry.kind == "TOOL_RESULT"]
        self.assertEqual([entry.refs for entry in results],
                         [(), ("observation:read_prices",)])

    def test_a_valid_evaluation_without_claim_is_declared_inconclusive(self):
        loop, journal, backend, _ = make_scenario(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_empty_data(), n=2),
             llm_ok(plan_stop_data(), n=3)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertTrue(outcome.inconclusive)
        reflections = [entry for entry in journal.entries() if entry.kind == "REFLECTION"]
        self.assertEqual(len(reflections), 2)  # VOI fallback + the empty evaluation
        self.assertTrue(any("aucun claim exploitable" in entry.content
                            for entry in reflections))
        # no line with refs -> no promotion candidate was ever emitted
        self.assertTrue(all(not entry.refs for entry in reflections))


if __name__ == "__main__":
    unittest.main()
