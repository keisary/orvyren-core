#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v1 loader tests: strict mini-YAML + `load_policy(policy_v1.yaml)`.

The loader refuses more than it accepts (fail-closed); the bundle carries
a version + YAML fingerprint + code fingerprint, and every policy verdict
carries them (DOC2 §5.5.3). Run: python -m unittest discover -s tests -v
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.policy import (  # noqa: E402
    EVAL_MODE_SIMULATION, Intent, evaluate, load_policy,
)
from orvyren.policy.miniyaml import MiniYamlError  # noqa: E402
from orvyren.policy.miniyaml import load as yaml_load  # noqa: E402
from orvyren.policy.miniyaml import load_file as yaml_load_file  # noqa: E402

POLICY_PATH = os.path.join(ROOT, "policy_v1.yaml")
RECIPIENTS = {"B": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
              "C": "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)


class TestMiniYaml(unittest.TestCase):
    """The strict YAML subset: what it accepts, what it refuses."""

    def test_mapping_simple_et_types(self):
        data = yaml_load("a: 1\nb: deux\nc: true\nd: null\ne: \"100.0\"\nf: -3\ng: 1.5\n")
        self.assertEqual(data, {"a": 1, "b": "deux", "c": True, "d": None,
                                "e": "100.0", "f": -3, "g": 1.5})

    def test_imbrique_et_listes(self):
        text = ("racine:\n"
                "  enfant: valeur\n"
                "  nombre: 42\n"
                "liste:\n"
                "  - un\n"
                "  - deux\n"
                "objets:\n"
                "  - operation: transfer\n"
                "    target: \"0xabc\"\n"
                "  - operation: swap\n"
                "    target: \"0xdef\"\n")
        data = yaml_load(text)
        self.assertEqual(data["racine"], {"enfant": "valeur", "nombre": 42})
        self.assertEqual(data["liste"], ["un", "deux"])
        self.assertEqual(data["objets"][0], {"operation": "transfer", "target": "0xabc"})
        self.assertEqual(data["objets"][1]["operation"], "swap")

    def test_commentaires_et_guillemets(self):
        text = ("# commentaire entier\n"
                "cle: valeur # commentaire de fin\n"
                "avec_diese: \"a # b\"\n"
                "simple: 'x # y'\n")
        self.assertEqual(yaml_load(text),
                         {"cle": "valeur", "avec_diese": "a # b", "simple": "x # y"})

    def test_flow_vide_supporté(self):
        self.assertEqual(yaml_load("a: []\nb: {}\n"), {"a": [], "b": {}})

    def test_refus_tabulation(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("a:\n\tb: 1\n")

    def test_refus_cle_dupliquee(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("a: 1\na: 2\n")

    def test_refus_ancres_et_tags(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("a: &ancre 1\n")
        with self.assertRaises(MiniYamlError):
            yaml_load("a: !tag 1\n")

    def test_refus_indentation_incoherente(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("a:\n  b: 1\n   c: 2\n")

    def test_refus_valeur_manquante(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("a:\n")

    def test_refus_guillemet_non_ferme(self):
        with self.assertRaises(MiniYamlError):
            yaml_load('a: "ouvre\n')


class TestPolicyV1Bundle(unittest.TestCase):
    """`policy_v1.yaml`: parameters, version, fingerprints."""

    def test_charge_les_parametres(self):
        bundle = load_policy(POLICY_PATH, RECIPIENTS)
        cfg = bundle.config
        self.assertEqual(bundle.version, "v1.0")
        self.assertEqual(cfg.allowed_chain_ids, frozenset({84532}))
        self.assertIn("0x036cbd53842c5426634e7929541ec2318f3dcf7e", cfg.allowed_assets)
        self.assertEqual(cfg.max_per_tx, 100.0)
        self.assertEqual(cfg.max_cumulative, 300.0)
        self.assertEqual(cfg.intent_ttl, timedelta(minutes=15))
        self.assertEqual(cfg.clock_skew, timedelta(seconds=60))
        self.assertEqual(cfg.asset_decimals, 6)
        self.assertEqual(cfg.allowed_operations, frozenset({"transfer"}))
        self.assertIn(("0x036cbd53842c5426634e7929541ec2318f3dcf7e", "0xa9059cbb"),
                      cfg.allowed_functions)
        self.assertEqual(cfg.allowed_recipients,
                         frozenset({RECIPIENTS["B"].lower(), RECIPIENTS["C"].lower()}))

    def test_empreintes_coherentes(self):
        bundle = load_policy(POLICY_PATH, RECIPIENTS)
        self.assertEqual(len(bundle.yaml_sha256), 64)
        self.assertEqual(len(bundle.code_sha256), 64)
        expected = hashlib.sha256(
            (bundle.yaml_sha256 + ":" + bundle.code_sha256).encode("utf-8")).hexdigest()
        self.assertEqual(bundle.policy_hash, expected)
        self.assertEqual(bundle.config.policy_hash, expected)

    def test_verdict_porte_version_et_empreinte(self):
        bundle = load_policy(POLICY_PATH, RECIPIENTS)
        cfg = bundle.config
        cfg.permission_expires_at = NOW + timedelta(hours=24)
        intent = Intent(intent_id="i-1", action="transfer", chain_id=84532,
                        asset="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                        amount=50.0, recipient=RECIPIENTS["B"], created_at=NOW)
        decision = evaluate(intent, cfg, now=NOW, mode=EVAL_MODE_SIMULATION)
        self.assertEqual(decision.verdict, "ALLOW")
        self.assertEqual(decision.policy_version, "v1.0")
        self.assertEqual(decision.policy_hash, bundle.policy_hash)
        self.assertEqual(decision.as_dict()["policy_hash"], bundle.policy_hash)

    def test_destinataire_non_resolu_est_liste(self):
        bundle = load_policy(POLICY_PATH, {"B": RECIPIENTS["B"]})
        self.assertEqual(bundle.data.get("_unresolved_recipients"), ["C"])
        self.assertEqual(bundle.config.allowed_recipients, frozenset({RECIPIENTS["B"].lower()}))

    def test_yaml_modifie_change_empreinte(self):
        bundle = load_policy(POLICY_PATH, RECIPIENTS)
        text = open(POLICY_PATH, encoding="utf-8").read()
        with tempfile.TemporaryDirectory() as tmp:
            tampered = os.path.join(tmp, "policy_v1.yaml")
            with open(tampered, "w", encoding="utf-8") as handle:
                handle.write(text.replace('max_per_tx: "100.0"', 'max_per_tx: "150.0"'))
            modified = load_policy(tampered, RECIPIENTS)
        self.assertNotEqual(bundle.yaml_sha256, modified.yaml_sha256)
        self.assertNotEqual(bundle.policy_hash, modified.policy_hash)
        self.assertEqual(modified.config.max_per_tx, 150.0)

    def test_champs_manquants_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = os.path.join(tmp, "policy_v1.yaml")
            with open(broken, "w", encoding="utf-8") as handle:
                handle.write("chain_id: 84532\nasset: \"0xabc\"\n")
            with self.assertRaises(MiniYamlError):
                load_policy(broken)

    def test_le_fichier_du_depot_se_charge(self):
        data = yaml_load_file(POLICY_PATH)
        self.assertEqual(data["schema"], "orvyren-policy/v1")
        self.assertEqual(data["role_key"],
                         "0x4147454e54000000000000000000000000000000000000000000000000000000")
        self.assertEqual(data["envelope_fixture"], "fixtures/roles_agent_config.json")
        self.assertEqual(json.dumps(data)[:1], "{")


if __name__ == "__main__":
    unittest.main(verbosity=2)
