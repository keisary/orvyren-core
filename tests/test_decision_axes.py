#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench of the three separated axes + double price convention (W3:
generalized rule, L3.6).

Contract (DOC4 W3 [DONE]): 3 separate axes (epistemic != economic !=
authorization), INCONCLUSIVE on missing input, and the double price convention
(alert on low; decision on close + low — FREEZE_V2 C5) exposed as ONE
parameter and tested.

Execution: ``python -m pytest tests/test_decision_axes.py -q``.
"""

import datetime as dt
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.decision.abstention import detect_conditions  # noqa: E402
from orvyren.decision.axes import (FROZEN_CONVENTION_APPLIES, PRICE_CONVENTION,  # noqa: E402
                                   authorization_via_policy, build_dossier,
                                   convention_divergence_bps,
                                   verdicts_under_conventions)
from orvyren.decision.scenarios import (SUPPLY_VENUE, load_observations,  # noqa: E402
                                        parse_window_bound)

CORPUS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")
MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")
FIXED_NOW = dt.datetime(2026, 10, 16, 12, 0, 0, tzinfo=dt.timezone.utc)
RESERVE = "0xD438eE8b50D02A43c7d54372362CA238C352dF91"


def load():
    return load_observations(CORPUS)


class TestAxesSeparation(unittest.TestCase):

    def setUp(self):
        self.dossier = build_dossier("usdc-2023-03", load(), MAIN_WINDOW[0],
                                     MAIN_WINDOW[1])

    def test_three_axes_present_and_typed(self):
        axes = self.dossier["axes"]
        self.assertEqual(axes["epistemic_verdict"], "CONCLUANT")
        self.assertEqual(axes["economic_action"], "CONVERTIR/TRANSFÉRER")
        self.assertIsNone(axes["authorization_verdict"])  # no recipient configured
        self.assertFalse(axes["authorization_detail"]["evaluated"])
        self.assertIn("never fused", axes["separation_note"])

    def test_x_star_is_bounded(self):
        # x* = min(x_max=100, depth=available, x_seuil=100) -> 100 USDC (A-D1)
        self.assertEqual(self.dossier["axes"]["x_star_usdc"], 100.0)

    def test_authorization_allow_through_the_policy_service(self):
        outcome = authorization_via_policy(100.0, RESERVE, created_at=FIXED_NOW,
                                           now=FIXED_NOW)
        self.assertTrue(outcome["evaluated"])
        self.assertEqual(outcome["verdict"], "ALLOW")

    def test_authorization_deny_is_an_axis3_fact_never_an_epistemic_one(self):
        denied = authorization_via_policy(150.0, RESERVE, created_at=FIXED_NOW,
                                          now=FIXED_NOW)
        self.assertEqual(denied["verdict"], "DENY")
        # A4 fires on the authorization axis, not as an epistemic failure
        conditions = detect_conditions(
            {"H2": {"verdict": "SUPPORTED", "missing_inputs": [],
                    "criteria_evaluated": []}},
            policy_verdict="DENY")
        self.assertEqual(conditions["conditions"], ["A4"])
        self.assertIn("A4", " ".join(conditions["labels"]))

    def test_dossier_conditions_exclude_a5_thanks_to_the_frozen_convention(self):
        self.assertTrue(FROZEN_CONVENTION_APPLIES)
        self.assertNotIn("A5", self.dossier["axes"]["conditions_declenchees"])


class TestInconclusivePath(unittest.TestCase):

    def test_missing_supply_yields_enriched_inconclusive(self):
        observations = [o for o in load() if o.venue != SUPPLY_VENUE]
        dossier = build_dossier("usdc-2023-03", observations, MAIN_WINDOW[0],
                                MAIN_WINDOW[1])
        axes = dossier["axes"]
        self.assertEqual(axes["epistemic_verdict"], "INCONCLUSIVE")
        self.assertIsNone(axes["economic_action"])
        payload = dossier["abstention"]
        self.assertIsNotNone(payload)
        self.assertEqual(payload["epistemic_verdict"], "INCONCLUSIVE")
        self.assertIn("A1", payload["conditions_declenchees"])
        # what_would_change is MANDATORY and is a research plan, not prose
        self.assertTrue(payload["what_would_change_the_verdict"])
        for entry in payload["what_would_change_the_verdict"]:
            self.assertIn("predicat", entry)
            self.assertIn("cout_estime", entry)
        # decision_delta shows both decisions (makes abstention useful)
        self.assertEqual(set(payload["decision_delta"]),
                         {"si_H2_soutenue", "si_H2_refutee"})
        self.assertIsNone(payload["action"])
        self.assertIn("raison_arret", payload["budget"])
        # the enriched format is JSON-serialisable (dossier artefact contract)
        json.dumps(dossier, ensure_ascii=False)


class TestDoublePriceConvention(unittest.TestCase):

    def test_convention_is_one_frozen_parameter(self):
        self.assertEqual(PRICE_CONVENTION["alert_reading"], "low")
        self.assertEqual(PRICE_CONVENTION["decision_readings"], ("close", "low"))
        self.assertIn("C5", PRICE_CONVENTION["ref"])

    def test_measured_gap_between_conventions(self):
        gap = convention_divergence_bps(load(), MAIN_WINDOW[0], MAIN_WINDOW[1])
        self.assertEqual(gap["venue"], "bitstamp")
        self.assertEqual(gap["gap_bps"], 1151.52)
        # recomputed straight from the corpus row (source of truth)
        close, low = gap["close"], gap["low"]
        self.assertAlmostEqual((close - low) / low * 10000.0, gap["gap_bps"], places=2)

    def test_readings_reported_and_verdicts_compared(self):
        comparison = verdicts_under_conventions(load(), MAIN_WINDOW[0], MAIN_WINDOW[1])
        self.assertEqual(set(comparison["per_hypothesis"]), {"H1", "H2", "H3"})
        for entry in comparison["per_hypothesis"].values():
            self.assertEqual(set(entry), {"close", "low"})
        self.assertIsInstance(comparison["ambiguous"], bool)


if __name__ == "__main__":
    unittest.main(verbosity=2)
