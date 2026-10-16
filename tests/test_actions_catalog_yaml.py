#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench — catalogue d'actions v1 : `config/actions_v1.yaml` (W3 [DONE]).

Contrat (DOC4 W3 [DONE]) : le fichier ``config/actions_v1.yaml`` couvre
**12 actions** (8 DAO + 4 desk), chacune avec **son test d'applicabilité** ;
le chargeur est fail-closed (toute violation du gabarit lève).

Execution: ``python -m pytest tests/test_actions_catalog_yaml.py -q``.
"""

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from orvyren.policy.miniyaml import load_file  # noqa: E402
from orvyren.decision.catalog import (APPLICABILITY_DEFAULT,  # noqa: E402
                                      APPLICABILITY_ESCALATE,
                                      APPLICABILITY_LABELS,
                                      APPLICABILITY_ON_CHAIN,
                                      APPLICABILITY_SIMULATED, CATALOG,
                                      CATALOG_VERSION, DEFAULT_CATALOG_PATH,
                                      check_applicability, load_catalog,
                                      records_as_dicts, validate_catalog)

TEMPLATE_FIELDS = ("action_id", "persona", "name", "epistemic_trigger",
                   "economic_trigger", "bounds", "cost", "expected_effect",
                   "applicability", "precedent")

EXPECTED_IDS = {"A-D%d" % i for i in range(1, 9)} | {"K-D%d" % i for i in range(1, 5)}

_ENTRY = """  - action_id: "{action_id}"
    persona: "{persona}"
    name: "x"
    epistemic_trigger: "x"
    economic_trigger: "x"
    bounds: "x"
    cost: "x"
    expected_effect: "x"
    applicability: "{applicability}"
    precedent: "x"
"""


class TestCatalogYamlSource(unittest.TestCase):
    """`config/actions_v1.yaml` is the parameter source of truth."""

    def test_yaml_source_covers_twelve_actions(self):
        data = load_file(DEFAULT_CATALOG_PATH)
        self.assertEqual("orvyren-actions-catalog/v1", data["schema"])
        self.assertEqual(CATALOG_VERSION, data["catalog_version"])
        self.assertEqual(8, len(data["persona_dao"]))
        self.assertEqual(4, len(data["persona_desk"]))
        ids = [entry["action_id"] for entry in data["persona_dao"]]
        ids += [entry["action_id"] for entry in data["persona_desk"]]
        self.assertEqual(EXPECTED_IDS, set(ids))
        self.assertEqual(12, len(ids))

    def test_every_action_entry_carries_its_template_fields(self):
        data = load_file(DEFAULT_CATALOG_PATH)
        for section in ("persona_dao", "persona_desk"):
            for entry in data[section]:
                for field in TEMPLATE_FIELDS:
                    self.assertTrue(str(entry.get(field, "")).strip(),
                                    "%s: empty %s" % (entry["action_id"], field))
                self.assertIn(entry["applicability"], APPLICABILITY_LABELS)

    def test_loaded_catalog_matches_the_yaml_and_validates(self):
        self.assertEqual(12, len(CATALOG))
        self.assertEqual([], validate_catalog())
        for action in CATALOG:
            self.assertEqual(CATALOG_VERSION, action.version)
        payload = records_as_dicts()
        json.dumps(payload, ensure_ascii=False)  # serialisable
        self.assertEqual(len(payload), 12)


class TestPerActionApplicability(unittest.TestCase):
    """Chaque action porte son test d'applicabilité (12/12)."""

    def test_applicability_test_per_action(self):
        seen = 0
        for record in CATALOG:
            seen += 1
            with self.subTest(action=record.action_id):
                verdict = check_applicability(record)
                self.assertIn("applicable", verdict)
                self.assertIs(verdict["action"], record)
                if record.applicability == APPLICABILITY_ESCALATE:
                    # A governance proposal is never an agent action.
                    self.assertFalse(verdict["applicable"])
                    self.assertFalse(check_applicability(
                        record, {"allow_simulation": True})["applicable"])
                elif record.applicability == APPLICABILITY_SIMULATED:
                    # Simulated in v1 — never executed without an explicit opt-in.
                    self.assertFalse(verdict["applicable"])
                    self.assertTrue(check_applicability(
                        record, {"allow_simulation": True})["applicable"])
                elif record.applicability == APPLICABILITY_DEFAULT:
                    # The documented default state is always available.
                    self.assertTrue(verdict["applicable"])
                else:
                    self.assertEqual(APPLICABILITY_ON_CHAIN, record.applicability)
                    self.assertTrue(verdict["applicable"])
        self.assertEqual(12, seen)

    def test_on_chain_actions_are_blocked_by_active_abstention(self):
        for record in CATALOG:
            if record.applicability != APPLICABILITY_ON_CHAIN:
                continue
            with self.subTest(action=record.action_id):
                verdict = check_applicability(record, {"abstentions_actives": True})
                self.assertFalse(verdict["applicable"])

    def test_honesty_labels_are_the_expected_ones(self):
        by_id = {record.action_id: record for record in CATALOG}
        self.assertEqual(APPLICABILITY_ESCALATE, by_id["A-D6"].applicability)
        self.assertEqual(APPLICABILITY_ESCALATE, by_id["A-D8"].applicability)
        self.assertEqual(APPLICABILITY_ON_CHAIN, by_id["K-D1"].applicability)
        self.assertEqual(APPLICABILITY_SIMULATED, by_id["K-D2"].applicability)
        self.assertEqual(APPLICABILITY_ON_CHAIN, by_id["A-D1"].applicability)
        self.assertEqual(APPLICABILITY_DEFAULT, by_id["A-D7"].applicability)
        self.assertEqual(APPLICABILITY_DEFAULT, by_id["K-D4"].applicability)


class TestLoaderFailClosed(unittest.TestCase):

    def _write(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                             encoding="utf-8", newline="\n")
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_missing_template_field_is_rejected(self):
        path = self._write(
            "schema: \"orvyren-actions-catalog/v1\"\n"
            "catalog_version: \"catalog/v1\"\n"
            "persona_dao:\n"
            "  - action_id: \"A-D1\"\n"
            "    persona: \"DAO\"\n"
            "    name: \"x\"\n"
            "    epistemic_trigger: \"x\"\n"
            "    economic_trigger: \"x\"\n"
            "    bounds: \"x\"\n"
            "    cost: \"x\"\n"
            "    expected_effect: \"x\"\n"
            "    applicability: \"on-chain\"\n"
            "persona_desk: []\n")
        with self.assertRaises(ValueError) as caught:
            load_catalog(path)
        self.assertIn("E_CATALOG_FIELD_MISSING", str(caught.exception))

    def test_unknown_applicability_is_rejected(self):
        path = self._write(
            "schema: \"orvyren-actions-catalog/v1\"\n"
            "catalog_version: \"catalog/v1\"\n"
            "persona_dao:\n"
            + "".join(_ENTRY.format(action_id="A-D%d" % i, persona="DAO",
                                   applicability="magique")
                      for i in range(1, 9))
            + "persona_desk:\n"
            + "".join(_ENTRY.format(action_id="K-D%d" % i, persona="desk",
                                   applicability="on-chain")
                      for i in range(1, 5)))
        with self.assertRaises(ValueError) as caught:
            load_catalog(path)
        self.assertIn("E_CATALOG_APPLICABILITY", str(caught.exception))

    def test_broken_counts_are_rejected(self):
        path = self._write(
            "schema: \"orvyren-actions-catalog/v1\"\n"
            "catalog_version: \"catalog/v1\"\n"
            "persona_dao:\n"
            + _ENTRY.format(action_id="A-D1", persona="DAO",
                            applicability="on-chain")
            + "persona_desk:\n"
            + "".join(_ENTRY.format(action_id="K-D%d" % i, persona="desk",
                                   applicability="on-chain")
                      for i in range(1, 5)))
        with self.assertRaises(ValueError) as caught:
            load_catalog(path)
        self.assertIn("E_CATALOG_COUNTS", str(caught.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
