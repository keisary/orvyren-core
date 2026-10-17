#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench — registration of the falsifiable hypotheses (W3 lot L3.1).

Contract (DOC4 W3 [DONE]): every registered hypothesis carries **mandatory
S/R criteria** (no silent ``p∅``); a number produced by an agent never
triggers a criterion — every criterion references an **instrumented
predicate**, and every piece of evidence cited by the verdicts points at a row
of the frozen corpus.

Execution: ``python -m pytest tests/test_decision_records.py -q``.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from orvyren.branches.hypotheses import HypothesisRegistry, validate_hypothesis  # noqa: E402
from orvyren.decision.predicates import BY_ID  # noqa: E402
from orvyren.decision.records import (CRITERION_PREDICATES,  # noqa: E402
                                      build_hypothesis_record,
                                      register_case_hypotheses)
from orvyren.decision.scenarios import classify_hypotheses, load_observations  # noqa: E402

REPO_ROOT = os.path.dirname(HERE)
CORPUS_ABS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")
MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")

CASE_ID = "usdc-2023-03"


def case_verdicts():
    """The frozen corpus verdicts (H1/H2/H3) — fresh copy each call."""
    observations = load_observations(CORPUS_ABS)
    return classify_hypotheses(observations, MAIN_WINDOW[0], MAIN_WINDOW[1])


class TestHypothesisRegistration(unittest.TestCase):

    def test_registers_three_falsifiable_hypotheses_in_the_w2_registry(self):
        registry = HypothesisRegistry()
        records = register_case_hypotheses(registry, CASE_ID, case_verdicts(),
                                           tuple(BY_ID))
        self.assertEqual(3, len(registry))
        self.assertEqual(3, len(records))
        for record in records:
            # The registry's own validator accepts every record.
            self.assertEqual((), validate_hypothesis(record), record.id)
            self.assertEqual("CREATED", record.etat)
            # p is never a number — and never a silent p∅.
            self.assertIsNone(record.p)
            sides = {criterion.nom for criterion in record.criteres}
            self.assertIn("soutien", sides)
            self.assertIn("refutation", sides)
        ids = [record.id for record in registry.all()]
        self.assertEqual(["HYP-USDC-2023-03-H1", "HYP-USDC-2023-03-H2",
                          "HYP-USDC-2023-03-H3"], ids)

    def test_missing_support_criterion_is_rejected(self):
        verdicts = case_verdicts()
        verdicts["H2"] = dict(verdicts["H2"], support_criterion="")
        registry = HypothesisRegistry()
        with self.assertRaises(ValueError) as caught:
            register_case_hypotheses(registry, CASE_ID, verdicts, tuple(BY_ID))
        self.assertIn("E_SPEC_NO_SUPPORT_CRITERION", str(caught.exception))

    def test_missing_refutation_criterion_is_rejected(self):
        verdicts = case_verdicts()
        verdicts["H3"] = dict(verdicts["H3"], refutation_criterion="")
        registry = HypothesisRegistry()
        with self.assertRaises(ValueError) as caught:
            register_case_hypotheses(registry, CASE_ID, verdicts, tuple(BY_ID))
        self.assertIn("E_SPEC_NO_REFUTATION_CRITERION", str(caught.exception))

    def test_no_agent_number_can_trigger_a_criterion(self):
        """No number produced by an agent can trigger a criterion.

        A criterion must be evaluable by an **instrumented predicate**: a
        "number reported by an agent" is not a catalogue predicate and is
        refused at registration time (fail-closed).
        """
        bad_map = dict(CRITERION_PREDICATES)
        bad_map["H2"] = {
            "soutien": ("AGENT-REPORTED-SUPPLY",),
            "refutation": CRITERION_PREDICATES["H2"]["refutation"],
        }
        with self.assertRaises(ValueError) as caught:
            build_hypothesis_record(case_verdicts()["H2"], CASE_ID, tuple(BY_ID),
                                    criteria_map=bad_map)
        self.assertIn("E_SPEC_UNREGISTERED_PREDICATE", str(caught.exception))
        self.assertIn("AGENT-REPORTED-SUPPLY", str(caught.exception))

    def test_verdict_evidence_points_at_frozen_corpus_rows_only(self):
        """Every piece of evidence cited by the verdicts comes from the frozen corpus."""
        observations = load_observations(CORPUS_ABS)
        corpus_keys = {(observation.venue, observation.timestamp_utc)
                       for observation in observations}
        for verdict in case_verdicts().values():
            for ref in verdict["evidence_refs"]:
                self.assertIn((ref["venue"], ref["timestamp_utc"]), corpus_keys,
                              "%s: reference outside the frozen corpus" % ref)


if __name__ == "__main__":
    unittest.main(verbosity=2)
