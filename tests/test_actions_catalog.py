#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench of the bounded action catalogues — 8 DAO + 4 desk (W3 lot L3.5).

Contract (DOC4 W3 [DONE]): "12 actions cataloguées". Every action carries its
template (epistemic trigger, economic trigger, bounds, cost, expected effect,
applicability) — B3 §d.2-d.4 — and the catalogue is versioned (INV-AUTH).

Execution: ``python -m pytest tests/test_actions_catalog.py -q``.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from orvyren.decision.catalog import (APPLICABILITY_DEFAULT,  # noqa: E402
                                      APPLICABILITY_ESCALATE,
                                      APPLICABILITY_ON_CHAIN,
                                      APPLICABILITY_SIMULATED, CATALOG,
                                      CATALOG_VERSION, DAO_ACTIONS, DESK_ACTIONS,
                                      bounded_size, catalog_for,
                                      records_as_dicts, validate_catalog)


class TestCatalogShape(unittest.TestCase):

    def test_twelve_actions_eight_dao_four_desk(self):
        self.assertEqual(len(CATALOG), 12)
        self.assertEqual(len(DAO_ACTIONS), 8)
        self.assertEqual(len(DESK_ACTIONS), 4)
        self.assertEqual({a.action_id for a in CATALOG},
                         {"A-D1", "A-D2", "A-D3", "A-D4", "A-D5", "A-D6", "A-D7", "A-D8",
                          "K-D1", "K-D2", "K-D3", "K-D4"})

    def test_template_completeness_and_versioning(self):
        self.assertEqual(validate_catalog(), [])
        for action in CATALOG:
            self.assertEqual(action.version, CATALOG_VERSION)
            self.assertTrue(action.epistemic_trigger.strip())
            self.assertTrue(action.economic_trigger.strip())
            self.assertTrue(action.bounds.strip())
            self.assertTrue(action.expected_effect.strip())
            self.assertTrue(action.precedent.strip())

    def test_applicability_honesty_labels(self):
        by_id = {a.action_id: a for a in CATALOG}
        # A-D6 is a governance proposal, not an agent action (ESCALATE)
        self.assertEqual(by_id["A-D6"].applicability, APPLICABILITY_ESCALATE)
        # K-D2 (hedge) is simulated in v1 — not in the Zodiac envelope
        self.assertEqual(by_id["K-D2"].applicability, APPLICABILITY_SIMULATED)
        # A-D1 (the v1 demonstration action) is executable on-chain
        self.assertEqual(by_id["A-D1"].applicability, APPLICABILITY_ON_CHAIN)
        # defaults are documented as such
        self.assertEqual(by_id["A-D7"].applicability, APPLICABILITY_DEFAULT)
        self.assertEqual(by_id["K-D4"].applicability, APPLICABILITY_DEFAULT)

    def test_records_serialisable_and_persona_filter(self):
        payload = records_as_dicts()
        json.dumps(payload, ensure_ascii=False)
        self.assertEqual(len(payload), 12)
        self.assertEqual([a.action_id for a in catalog_for("DAO")],
                         ["A-D%d" % i for i in range(1, 9)])
        self.assertEqual([a.action_id for a in catalog_for("desk")],
                         ["K-D%d" % i for i in range(1, 5)])
        with self.assertRaises(ValueError):
            catalog_for("inconnu")


class TestBoundedSize(unittest.TestCase):

    def test_x_star_is_the_minimum_of_the_three_bounds(self):
        # x* = min(x_max, Depth_eps, x_seuil) — B3 §d.1
        self.assertEqual(bounded_size(100.0, 80.0, 90.0), 80.0)
        self.assertEqual(bounded_size(100.0, 80.0, 50.0), 50.0)
        self.assertEqual(bounded_size(40.0, 80.0, 90.0), 40.0)

    def test_never_negative(self):
        self.assertEqual(bounded_size(100.0, -5.0, 90.0), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
