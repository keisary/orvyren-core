#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: plan recovery on a form-only defect (gap G-18).

The measured gap: three live runs on ``rseth-2026-04`` ended
``ARRET-3`` / ``E_LOOP_OUTPUT_INVALID`` **on form, never on evidence** — a
plan without ``$schema`` after the re-prompt, a ``critere_discriminant``
holding a digit. The whole run was aborted for a defect a field-level re-ask
can fix.

What this bench pins:

- a plan refused for a digit in ``tache.critere_discriminant`` is quarantined
  **once**, re-asked once, and the run goes on when the second output is
  valid; the re-prompt payload carries ``erreurs_validation`` naming the
  field and the rule;
- a plan without ``$schema`` is repaired the same way;
- three invalid outputs still stop the run fail-closed
  (``ARRET-3`` / ``E_LOOP_OUTPUT_INVALID``) with every error listed — the
  extra attempt widens nothing;
- a budget ceiling that forbids the next call stops the run in ``ARRET-2``
  ("budget exhausted: … | plan invalid after N attempt(s)") instead of
  spending past it — the extra attempt is **bounded**, not free;
- a valid first output is never re-asked: one LLM call per step, with the
  historical payload (no ``erreurs_validation`` / ``sortie_precedente``), so
  the recorded success path stays byte-identical.

The backend is a scripted :class:`contracts.LLMBackend` living in this file
(deterministic hashes); the clock is deterministic. No network, no
``evidence/demo_runs/``, no ``fixtures/agents/**``: the sealed store never took the
re-prompt path (``grep -c erreurs_validation`` = 0), which is what allows the
re-prompt content to change without breaking the byte-for-byte replay.

Execution: ``python -m unittest tests.test_agents_plan_recovery -v``
"""

import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.loop import (  # noqa: E402
    MAX_OUTPUT_ATTEMPTS,
    PLAN_SCHEMA_ID,
    BoundedLoop,
)
from orvyren.agents.tools import build_v1_registry  # noqa: E402

QUESTION_PRICES = "la dispersion confirme-t-elle une dislocation realisable entre venues"
REF_PRICES = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"
REF_SUPPLY = "observation:circle/supply/2023-03-11T12:00Z"

#: Keys of the PLANNING payload before this change (no re-prompt keys).
HISTORICAL_PLAN_KEYS = [
    "budget_restant", "hypotheses", "lacunes", "outils_indisponibles",
    "snapshot", "snapshot_at", "sources_autorisees",
]


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

    Every call is recorded (payload deep-copied) so a test can assert what the
    loop asked for; an exhausted script is a test bug, never a silent call.
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


# ---------------------------------------------------------------------------
# Scripted model outputs.
# ---------------------------------------------------------------------------
def plan_task_data(*, question=QUESTION_PRICES, outil="read_prices", args=None,
                   critere="deux venues sous le pair", with_schema=True):
    """An ``orvyren/orch/v1`` plan holding exactly one task."""
    data = {"lacune_id": "L-1",
            "tache": {"question": question, "outil": outil,
                      "args": dict(args if args is not None
                                   else {"venue": "bitstamp", "symbol": "USDC-USD",
                                         "from": "2023-03-01", "to": "2023-03-31"}),
                      "critere_discriminant": critere,
                      "branches_concernees": ["HYP-001"], "cout_max": {}},
            "stop": False, "motif_stop": None, "non_recherche": []}
    if with_schema:
        data["$schema"] = PLAN_SCHEMA_ID
    return data


def plan_stop_data(*, motif="les lacunes restantes n'ont pas de valeur discriminante"):
    """A valid closing plan: no task left with positive value (ARRET-1)."""
    return {"$schema": PLAN_SCHEMA_ID, "lacune_id": "", "tache": None, "stop": True,
            "motif_stop": motif, "non_recherche": []}


def eval_data(*, enonce="la venue d'exchange se situe sous les deux agregateurs",
              refs=(REF_PRICES,)):
    """A valid free-schema evaluation with one referenced claim."""
    return {"claims": [{"enonce": enonce, "refs": list(refs)}],
            "reflexions": "lecture conforme au snapshot"}


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
    """Wire one loop on the frozen fixtures; returns (loop, journal, backend)."""
    data = fixtures()
    journal = AgentJournal()
    backend = FakeBackend(script)
    tools = build_v1_registry(fixtures=data, journal=journal)
    loop = BoundedLoop(
        case_id="usdc-2023-03", run_id="run-recovery", agent_id="orchestrator",
        backend=backend, tools=tools, journal=journal,
        budget=overrides.pop("budget", None), clock=FakeClock(),
        prompt_version="orch-p1.1.0", system_prompt="SYS-INJECTE",
        snapshot=data["snapshot"],
        lacunes=[{"lacune_id": "L-1", "question": QUESTION_PRICES}],
        hypotheses=[{"id": "HYP-001", "etat": "UNDER_TEST"}])
    if overrides:
        raise AssertionError("unknown overrides: %s" % sorted(overrides))
    return loop, journal, backend


def quarantined(journal):
    return [entry for entry in journal.entries() if entry.status == "QUARANTINED"]


def reprompt_lines(journal):
    return [entry for entry in journal.entries()
            if entry.kind == "REFLECTION" and "re-prompting" in entry.content]


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------
class PlanRecoveryTest(unittest.TestCase):
    """A form-only defect is repaired by one actionable, bounded re-ask."""

    def test_a_digit_in_the_criterion_is_repaired_by_one_actionable_reprompt(self):
        bad = plan_task_data(critere="le pair tient sous 0,80 pendant la seance")
        loop, journal, backend = make_scenario([
            llm_ok(bad, n=1),
            llm_ok(plan_task_data(), n=2),
            llm_ok(eval_data(), n=3),
            llm_ok(plan_stop_data(), n=4),
        ])
        outcome = loop.run()

        # the run continues: no ARRET-3, the probe is executed and evaluated
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertFalse(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], 4.0)
        self.assertEqual(outcome.budget_used["tool_calls"], 1.0)
        self.assertEqual(len(backend.script), 0)

        # exactly one quarantine line + exactly one re-prompt line
        self.assertEqual(len(quarantined(journal)), 1)
        self.assertEqual(quarantined(journal)[0].kind, "PLAN")
        self.assertEqual(len(reprompt_lines(journal)), 1)
        self.assertIn("attempt 2/%d" % MAX_OUTPUT_ATTEMPTS,
                      reprompt_lines(journal)[0].content)

        # the re-prompt payload names the field and states the rule
        payload = backend.calls[1]["payload"]
        self.assertIn("erreurs_validation", payload)
        self.assertEqual(payload["sortie_precedente"],
                         json.dumps(bad, ensure_ascii=False, sort_keys=True))
        message = " ".join(payload["erreurs_validation"])
        self.assertIn("tache.critere_discriminant", message)
        self.assertIn("no digit allowed", message)
        self.assertIn("figures come from refs", message)
        self.assertNotIn("tache.question", message)  # only the broken field
        # the first call carried no re-prompt key at all
        self.assertNotIn("erreurs_validation", backend.calls[0]["payload"])

        # the second (valid) plan is the one the run used, then the closing plan
        plan_lines = [entry for entry in journal.entries()
                      if entry.kind == "PLAN" and entry.status != "QUARANTINED"]
        self.assertEqual(len(plan_lines), 2)
        self.assertIn("read_prices", plan_lines[0].content)
        self.assertIn('"stop": true', plan_lines[1].content)

    def test_a_missing_schema_is_repaired_the_same_way(self):
        bad = plan_task_data(with_schema=False)
        loop, journal, backend = make_scenario([llm_ok(bad, n=1),
                                                llm_ok(plan_stop_data(), n=2)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(len(quarantined(journal)), 1)
        self.assertEqual(len(reprompt_lines(journal)), 1)
        messages = backend.calls[1]["payload"]["erreurs_validation"]
        self.assertTrue(any(m.startswith("$schema:") and PLAN_SCHEMA_ID in m
                            for m in messages), msg=messages)

    def test_three_invalid_plans_stop_fail_closed_with_every_error_listed(self):
        bad = plan_task_data(critere="le pair tient sous 0,80 pendant la seance")
        loop, journal, backend = make_scenario([llm_ok(bad, n=1), llm_ok(bad, n=2),
                                                llm_ok(bad, n=3)])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("ABORTED", "ARRET-3"))
        self.assertTrue(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], float(MAX_OUTPUT_ATTEMPTS))
        self.assertEqual(len(backend.calls), 3)   # never a 4th attempt
        self.assertEqual(len(backend.script), 0)
        self.assertIn("E_LOOP_OUTPUT_INVALID", outcome.motif)
        self.assertIn("after %d attempt(s)" % MAX_OUTPUT_ATTEMPTS, outcome.motif)
        self.assertIn("tache.critere_discriminant", outcome.motif)
        self.assertEqual(len(quarantined(journal)), 3)
        self.assertEqual(len(reprompt_lines(journal)), MAX_OUTPUT_ATTEMPTS - 1)
        stop_line = journal.entries()[-1]
        self.assertEqual(stop_line.kind, "STOP")
        self.assertIn("tache.critere_discriminant", stop_line.content)

    def test_a_budget_ceiling_blocks_the_extra_attempt_instead_of_spending(self):
        """Budget = 1 LLM call: the re-ask is refused, ARRET-2 not ARRET-3.

        The stop is ARRET-2 because the *cause* is a frozen ceiling, not the
        output: the plan was never given a second chance, so claiming
        ``E_LOOP_OUTPUT_INVALID`` would misreport the run. The motif keeps the
        plan errors, so the refusal stays demonstrable.
        """
        bad = plan_task_data(critere="le pair tient sous 0,80 pendant la seance")
        loop, journal, backend = make_scenario(
            [llm_ok(bad, n=1), llm_ok(plan_task_data(), n=2)],
            budget=contracts.Budget(llm_calls=1))
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-2"))
        self.assertTrue(outcome.inconclusive)
        self.assertEqual(outcome.budget_used["llm_calls"], 1.0)
        self.assertEqual(len(backend.calls), 1)     # no call past the ceiling
        self.assertEqual(len(backend.script), 1)    # the valid plan was never used
        self.assertIn("budget exhausted: llm_calls", outcome.motif)
        self.assertIn("plan invalid after 1 attempt(s)", outcome.motif)
        self.assertIn("tache.critere_discriminant", outcome.motif)
        self.assertEqual(len(quarantined(journal)), 1)
        self.assertEqual(reprompt_lines(journal), [])  # no re-prompt announced
        self.assertNotIn("E_LOOP_OUTPUT_INVALID", outcome.motif)

    def test_a_valid_first_plan_is_never_reprompted(self):
        loop, journal, backend = make_scenario([
            llm_ok(plan_task_data(), n=1),
            llm_ok(eval_data(), n=2),
            llm_ok(plan_stop_data(), n=3),
        ])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(outcome.budget_used["llm_calls"], 3.0)  # one call per step
        self.assertEqual(len(backend.calls), 3)
        self.assertEqual(quarantined(journal), [])
        self.assertEqual(reprompt_lines(journal), [])
        # the success payload is the historical one — no re-prompt keys
        self.assertEqual(sorted(backend.calls[0]["payload"]), HISTORICAL_PLAN_KEYS)
        for call in backend.calls:
            self.assertNotIn("erreurs_validation", call["payload"])
            self.assertNotIn("sortie_precedente", call["payload"])

    def test_the_evaluation_retry_follows_the_same_bounded_policy(self):
        no_refs = {"claims": [{"enonce": "claim sans aucune reference"}]}
        loop, journal, backend = make_scenario([
            llm_ok(plan_task_data(), n=1),
            llm_ok(no_refs, n=2),
            llm_ok(eval_data(), n=3),
            llm_ok(plan_stop_data(), n=4),
        ])
        outcome = loop.run()
        self.assertEqual((outcome.state, outcome.stop_condition), ("DONE", "ARRET-1"))
        self.assertEqual(outcome.budget_used["llm_calls"], 4.0)
        self.assertEqual(len(quarantined(journal)), 1)
        self.assertEqual(quarantined(journal)[0].kind, "REFLECTION")
        self.assertEqual(len(reprompt_lines(journal)), 1)
        messages = backend.calls[2]["payload"]["erreurs_validation"]
        self.assertTrue(any("claims[0].refs" in m for m in messages), msg=messages)


class ContractMessageTest(unittest.TestCase):
    """The validator itself: every error names a field and states the rule."""

    def test_each_planner_error_names_its_field(self):
        payload = {"$schema": "wrong", "stop": False, "non_recherche": "nope",
                   "lacune_id": "L-1",
                   "tache": {"question": "la dispersion atteint-elle 0,87 ?",
                             "outil": "", "args": [], "branches_concernees": "HYP-001",
                             "critere_discriminant": "sous 0,80",
                             "confiance": 0.9}}
        ok, errors = contracts.validate_orchestrator_output(payload)
        self.assertFalse(ok)
        joined = "\n".join(errors)
        for field in ("$schema", "non_recherche", "tache.question",
                      "tache.critere_discriminant", "tache.outil", "tache.args",
                      "tache.branches_concernee"):
            self.assertIn(field, joined)
        self.assertIn("tache.confiance: field not allowed", joined)

    def test_the_digit_rule_is_stated_qualitatively(self):
        ok, errors = contracts.validate_orchestrator_output(
            plan_task_data(critere="le pair tient sous 0,80"))
        self.assertFalse(ok)
        self.assertEqual(errors, [
            "tache.critere_discriminant: no digit allowed — state the criterion "
            "qualitatively, figures come from refs"])

    def test_a_missing_schema_is_named_explicitly(self):
        ok, errors = contracts.validate_orchestrator_output(plan_task_data(with_schema=False))
        self.assertFalse(ok)
        self.assertEqual(errors, ['$schema: expected exactly "%s"' % PLAN_SCHEMA_ID])

    def test_a_valid_plan_raises_no_error(self):
        ok, errors = contracts.validate_orchestrator_output(plan_task_data())
        self.assertTrue(ok, msg=errors)
        self.assertEqual(errors, [])

    def test_critique_errors_name_their_field_too(self):
        ok, errors = contracts.validate_critique_output(
            {"$schema": "orvyren/crit/v1", "verdict_lecture": "INCOHERENTE",
             "findings": [{"type": "incoherence_forme", "gravite": "majeure",
                           "enonce": "objection non sourcee", "refs": []}]})
        self.assertFalse(ok)
        joined = "\n".join(errors)
        self.assertIn("findings[0].refs: objection without refs is invalid", joined)


if __name__ == "__main__":
    unittest.main()
