#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: the UI maquette JSON (B0).

Locks the UI data contract (CONTRACT.md « Réponse type »): every query block
carries ``query`` / ``as_of`` / ``rows`` / ``count`` / ``latency_ms`` /
``provenance`` / ``mode``; the banner carries mode + block + hash + age;
Q1/Q4/Q6/Q7 are all present; every displayed row is backed by ``provenance``
(« pas de données inventées ») and an absent source renders
« SOURCE MANQUANTE ». Values come from the H2 seed — when that seed file is
present locally, the maquette rows are cross-checked verbatim against it.

Execution: ``python -m pytest tests/test_ui_maquette.py -q``
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

MAQUETTE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                             "src", "orvyren", "ui", "maquette.json")
SEED_PATH = os.path.join("D:" + os.sep, "orvyren_10h_2026-10-17", "handoff",
                         "ui_snapshot_seed.json")

RESPONSE_FIELDS = ("query", "as_of", "rows", "count", "latency_ms",
                   "provenance", "mode")
MODES = ("LIVE", "REPLAY", "FIXTURE", "SYNTHETIC")


def load_maquette():
    with open(MAQUETTE_PATH, encoding="utf-8") as handle:
        return json.load(handle)


class TestMaquette(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.maquette = load_maquette()

    def test_banner_carries_mode_block_hash_age(self):
        banner = self.maquette["banner"]
        self.assertIn(banner["mode"], MODES)
        self.assertIn("as_of_block", banner)
        self.assertIn("graph_hash", banner)
        self.assertIn("age", banner)

    def test_three_panels(self):
        self.assertEqual(sorted(self.maquette["panels"]),
                         ["decision", "graphe", "situation"])

    def test_graph_panel_shows_q1_q4_q6_q7(self):
        self.assertEqual(sorted(self.maquette["panels"]["graphe"]),
                         ["Q1", "Q4", "Q6", "Q7"])

    def test_query_blocks_follow_the_contract_response_type(self):
        for name, block in self.maquette["panels"]["graphe"].items():
            for field in RESPONSE_FIELDS:
                self.assertIn(field, block, "%s misses %s" % (name, field))
            self.assertIn(block["mode"], MODES)
            self.assertIsInstance(block["rows"], list)

    def test_every_row_is_backed_by_provenance(self):
        for name, block in self.maquette["panels"]["graphe"].items():
            self.assertTrue(block["provenance"], "%s has no provenance" % name)
            for ref in block["provenance"]:
                self.assertIn("ref", ref)

    def test_missing_source_spells_source_manquante(self):
        decision = self.maquette["panels"]["decision"]
        self.assertEqual(decision["statut"], "SOURCE MANQUANTE")
        self.assertEqual(self.maquette["regles_affichage"]["source_absente"],
                         "SOURCE MANQUANTE")

    def test_no_invented_value_when_seed_is_present(self):
        """Cross-check against the H2 seed (skipped off this machine)."""
        if not os.path.isfile(SEED_PATH):
            self.skipTest("seed H2 absent de cette machine")
        with open(SEED_PATH, encoding="utf-8") as handle:
            seed = json.load(handle)
        graph = self.maquette["panels"]["graphe"]
        self.assertEqual(seed["graph_hash"],
                         self.maquette["banner"]["graph_hash"])
        self.assertEqual(seed["counts"], self.maquette["panels"]["situation"]["counts"])
        for name in ("Q1", "Q4", "Q6", "Q7"):
            for row in graph[name]["rows"]:
                self.assertIn(row, seed[name.lower()]["rows"],
                              "%s row not found verbatim in the seed" % name)


if __name__ == "__main__":
    unittest.main()
