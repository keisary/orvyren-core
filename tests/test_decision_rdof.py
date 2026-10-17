#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench of RDOF v1 — the discriminating search (W3 lots L3.2/L3.3).

Contract (DOC4 W1/W3 [DONE]): "RDOF beats or matches the documented fixed
order on the T02/HYP-02R essai". The bench pins the B3 §b.2 micro-example
(USDC 11/03/2023): P-6.3 (24 h supply drop) is chosen first, its measured
outcome is the published figure -7.172196 %, H2 goes INCONCLUSIVE -> SUPPORTED,
and the run stops on the c1 invariance rule — with a full question -> predicate
-> cost -> effect trace.

Execution: ``python -m pytest tests/test_decision_rdof.py -q``.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.decision.predicates import BY_ID, CATALOG_V1, evaluate_predicate  # noqa: E402
from orvyren.decision.rdof import (DEFAULT_BUDGET, FROZEN_FIXED_ORDER,  # noqa: E402
                                   compare_rdof_vs_fixed_order, fixed_order_run,
                                   rdof_run, value_of_search)
from orvyren.decision.scenarios import load_observations  # noqa: E402

CORPUS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")
MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")

#: Published figure (evidence/decision_usdc-2023-03.json + B3 §g.1): supply
#: drop over 24 h, in percent. Pinned, and re-derived from the corpus below.
PUBLISHED_SUPPLY_DROP = -7.172196


def load():
    return load_observations(CORPUS)


class TestPredicateCatalogue(unittest.TestCase):

    def test_catalogue_ids_and_measured_costs(self):
        ids = [p.predicate_id for p in CATALOG_V1]
        self.assertEqual(ids, ["P-1.2", "P-1.3", "P-1.4", "P-2.2", "P-2.5",
                               "P-5.1", "P-6.3", "P-PERS"])
        # measured eth_call cost (B3 §b.2 "Costs", W3-A 2026-10-15)
        self.assertEqual(BY_ID["P-6.3"].cost_seconds, 0.65)
        self.assertEqual(BY_ID["P-6.3"].cost_queries, 1)
        # chain-backed predicates are declared not-offline, never invented
        for predicate_id in ("P-1.3", "P-1.4", "P-2.2", "P-2.5", "P-5.1"):
            self.assertFalse(BY_ID[predicate_id].offline_evaluable)
            self.assertTrue(BY_ID[predicate_id].offline_reason)

    def test_supply_drop_class_semantics(self):
        predicate = BY_ID["P-6.3"]
        self.assertEqual(predicate.class_of(-7.172196), ">=1 %")
        self.assertEqual(predicate.class_of(-0.2), "<1 %")
        # boundary is inclusive: exactly -1.00 % belongs to ">=1 %", just below does not
        self.assertEqual(predicate.class_of(-1.0), ">=1 %")
        self.assertEqual(predicate.class_of(-0.9999), "<1 %")

    def test_supply_drop_reproduces_the_published_figure(self):
        fact = evaluate_predicate("P-6.3", load(), MAIN_WINDOW[0], MAIN_WINDOW[1])
        self.assertEqual(fact["value"], PUBLISHED_SUPPLY_DROP)
        self.assertEqual(fact["class"], ">=1 %")
        self.assertEqual(len(fact["refs"]), 2)


class TestRdofMicroExample(unittest.TestCase):
    """The B3 §b.2 micro-example must be reproduced exactly."""

    def setUp(self):
        self.result = rdof_run(load(), MAIN_WINDOW[0], MAIN_WINDOW[1])

    def test_one_research_chosen_supply_drop(self):
        self.assertEqual(len(self.result["trace"]), 1)
        step = self.result["trace"][0]
        self.assertEqual(step["chosen"], "P-6.3")
        self.assertEqual(step["outcome"]["value"], PUBLISHED_SUPPLY_DROP)
        self.assertEqual(step["outcome"]["class"], ">=1 %")
        # rule (ii): the criterion carrying the opposite decision becomes evaluable
        self.assertTrue(any("rule (ii)" in item for item in step["why"]))
        # question -> predicate -> cost -> effect (the dossier trace contract)
        self.assertEqual(step["cost"]["queries"], 1)
        self.assertEqual(step["cost"]["seconds"], 0.65)

    def test_verdict_transition_and_stop(self):
        step = self.result["trace"][0]
        self.assertEqual(step["verdicts_before"]["H2"], "INCONCLUSIVE")
        self.assertEqual(step["verdicts_after"]["H2"], "SUPPORTED")
        self.assertEqual(self.result["stop_rule"], "c1")
        self.assertIn("stable decision", self.result["stop"])
        self.assertEqual(self.result["budget"]["consomme"],
                         {"recherches": 1, "appels": 1, "secondes": 0.65})

    def test_final_state_matches_the_v0_engine(self):
        self.assertEqual(self.result["final_verdicts"],
                         {"H1": "REFUTED", "H2": "SUPPORTED", "H3": "REFUTED"})
        self.assertEqual(self.result["final_action_candidate"]["kind"],
                         "ACTION_RECOMMENDED")
        self.assertEqual(self.result["final_action_candidate"]["catalog"], "A-D1")

    def test_never_bought_predicates_are_declared(self):
        not_searched = {entry["predicate_id"]: entry
                        for entry in self.result["not_searched"]}
        self.assertIn("P-PERS", not_searched)
        self.assertTrue(not_searched["P-PERS"]["action_invariant"])
        excluded = {entry["predicate_id"] for entry in self.result["excluded"]}
        for predicate_id in ("P-1.3", "P-2.2", "P-2.5", "P-1.4", "P-5.1"):
            self.assertIn(predicate_id, excluded)

    def test_determinism(self):
        again = rdof_run(load(), MAIN_WINDOW[0], MAIN_WINDOW[1])
        self.assertEqual(json.dumps(self.result, sort_keys=True),
                         json.dumps(again, sort_keys=True))

    def test_voi_interface_never_a_failure_point(self):
        self.assertEqual(value_of_search("P-6.3", {})["status"], "VOI_NOT_ESTIMABLE")
        with_voi = rdof_run(load(), MAIN_WINDOW[0], MAIN_WINDOW[1],
                            voi_fn=value_of_search)
        self.assertEqual(json.dumps(with_voi, sort_keys=True),
                         json.dumps(self.result, sort_keys=True))


class TestBudgetStop(unittest.TestCase):

    def test_zero_budget_stops_c2_and_declares_what_was_not_searched(self):
        result = rdof_run(load(), MAIN_WINDOW[0], MAIN_WINDOW[1],
                          budget={"recherches": 0, "appels": 10, "secondes": 60.0})
        self.assertEqual(result["trace"], [])
        self.assertEqual(result["stop_rule"], "c2")
        not_searched = {entry["predicate_id"]: entry
                        for entry in result["not_searched"]}
        self.assertIn("P-6.3", not_searched)
        self.assertIsNotNone(not_searched["P-6.3"]["possible_effect"])

    def test_default_budget_frozen(self):
        self.assertEqual(DEFAULT_BUDGET,
                         {"recherches": 3, "appels": 10, "secondes": 60.0})


class TestFixedOrderEssai(unittest.TestCase):
    """T02/HYP-02R: RDOF must beat or match the documented fixed order."""

    def test_rdof_beats_the_fixed_order(self):
        comparison = compare_rdof_vs_fixed_order(load(), MAIN_WINDOW[0],
                                                 MAIN_WINDOW[1])
        self.assertEqual(comparison["essai"], "T02/HYP-02R")
        self.assertTrue(comparison["verdicts_equal"],
                        "the mechanism may change the PATH, never the ANSWER")
        self.assertTrue(comparison["action_equal"])
        self.assertLessEqual(comparison["rdof"]["purchases"],
                             comparison["fixed_order"]["purchases"])
        self.assertEqual(comparison["rdof"]["unnecessary_purchases"], 0)
        self.assertGreaterEqual(comparison["fixed_order"]["unnecessary_purchases"], 1)
        self.assertTrue(comparison["rdof_not_worse"])

    def test_fixed_order_is_the_frozen_documented_repli(self):
        fixed = fixed_order_run(load(), MAIN_WINDOW[0], MAIN_WINDOW[1])
        self.assertEqual(fixed["frozen_order"], list(FROZEN_FIXED_ORDER))
        # the fixed order buys past the invariance point: that is the measured difference
        self.assertEqual(fixed["purchases"], ["P-6.3", "P-PERS"])
        self.assertEqual(fixed["unnecessary_purchases"], 1)
        self.assertEqual(fixed["final_verdicts"],
                         {"H1": "REFUTED", "H2": "SUPPORTED", "H3": "REFUTED"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
