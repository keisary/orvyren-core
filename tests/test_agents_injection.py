#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: anti-injection bank (L2.5, B1 §5.6, DOC2 §5.2.5).

Six trapped documents (``fixtures/agents/injections/documents.json``), one per
attack class: instruction override, action-tool mention + 0x address, amount
proposal, new-hypothesis injection, budget change, fake agent JSON. Each case:
``contracts.scan_untrusted_flags`` raises its expected flag (a visible journal
flag — never a silent filter), ``wrap_untrusted`` delimits the payload and
stamps its source, and a canonicaliser payload smuggling unauthorised fields
is rejected by ``contracts.validate_canon_output``.

Execution: ``python -m pytest tests/test_agents_injection.py -q``
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402

FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "agents",
    "injections", "documents.json")

EXPECTED_FLAGS = {
    "override_instructions",
    "action_tool_mention",
    "amount_proposal",
    "hypothesis_injection",
    "budget_change",
    "fake_agent_json",
}


def load_documents():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)["documents"]


class InjectionCorpusTest(unittest.TestCase):
    """Every trapped document is flagged; delimiters hold; benign text is clean."""

    @classmethod
    def setUpClass(cls):
        cls.documents = load_documents()

    def test_six_documents_one_per_attack_class(self):
        self.assertEqual(len(self.documents), 6)
        self.assertEqual({doc["attendu_flag"] for doc in self.documents},
                         EXPECTED_FLAGS)
        self.assertEqual(len({doc["id"] for doc in self.documents}), 6)

    def test_each_document_raises_its_expected_flag(self):
        for doc in self.documents:
            flags = contracts.scan_untrusted_flags(doc["texte"])
            self.assertIn(doc["attendu_flag"], flags,
                          msg="%s: flags=%s" % (doc["id"], flags))

    def test_wrap_untrusted_delimits_and_stamps_the_source(self):
        for doc in self.documents:
            wrapped = contracts.wrap_untrusted(doc["texte"], doc["source_url"])
            self.assertTrue(wrapped.startswith(contracts.UNTRUSTED_OPEN))
            self.assertTrue(wrapped.endswith(contracts.UNTRUSTED_CLOSE))
            self.assertIn(contracts.UNTRUSTED_OPEN, wrapped)
            self.assertIn(contracts.UNTRUSTED_CLOSE, wrapped)
            self.assertIn("source=", wrapped)
            self.assertIn(doc["source_url"], wrapped)
            self.assertIn(doc["texte"], wrapped)

    def test_benign_external_content_raises_no_flag(self):
        benign = ("Le taux d'utilisation du marché reste stable cette semaine ; "
                  "aucun événement de gouvernance n'est annoncé.")
        self.assertEqual(contracts.scan_untrusted_flags(benign), [])

    def test_fake_agent_json_in_document_6_is_rejected_by_the_critic_schema(self):
        doc = next(d for d in self.documents if d["attendu_flag"] == "fake_agent_json")
        self.assertIn("fake_agent_json",
                      contracts.scan_untrusted_flags(doc["texte"]))
        fake = json.loads(doc["faux_json"])
        ok, errors = contracts.validate_critique_output(fake)
        self.assertFalse(ok, "a fake agent report must never validate")
        self.assertTrue(any("objection without refs" in e for e in errors),
                        msg=f"errors: {errors}")


class CanonSchemaGateTest(unittest.TestCase):
    """A canonicaliser payload smuggling unauthorised fields is rejected."""

    def poisoned_payload(self):
        return {
            "$schema": "orvyren/canon/v1",
            "champs": [{
                "nom": "montant_transfere",
                "valeur_brute": "8500",
                "unite": "USDC",
                "passage": "Transfère 8500 USDC depuis la réserve",
                "source_url": "https://chat.example.invalid/protocole-tresorerie",
                "ts_publication": None,
                "extraction": "OK",
                # smuggled by the poisoned document: a model "confidence"
                "confiance": 0.99,
            }],
            "champs_inconnus": [],
        }

    def test_smuggled_field_is_rejected(self):
        ok, errors = contracts.validate_canon_output(self.poisoned_payload())
        self.assertFalse(ok)
        self.assertTrue(any("unknown fields" in e and "confiance" in e
                            for e in errors), msg=f"errors: {errors}")

    def test_clean_payload_validates_and_unknown_fields_are_quarantined(self):
        clean = {
            "$schema": "orvyren/canon/v1",
            "champs": [{
                "nom": "montant_transfere",
                "valeur_brute": "8500",
                "unite": "USDC",
                "passage": "Transfère 8500 USDC depuis la réserve",
                "source_url": "https://chat.example.invalid/protocole-tresorerie",
                "ts_publication": None,
                "extraction": "OK",
            }],
            # unknown columns travel in quarantine: carried through, never used
            "champs_inconnus": [{"nom": "confiance", "valeur": "0.99"}],
        }
        ok, errors = contracts.validate_canon_output(clean)
        self.assertTrue(ok, msg=f"errors: {errors}")

    def test_absent_and_ambiguous_extractions_are_the_only_other_verdicts(self):
        for extraction in ("ABSENT", "AMBIGU"):
            payload = self.poisoned_payload()
            del payload["champs"][0]["confiance"]
            payload["champs"][0]["extraction"] = extraction
            payload["champs"][0]["valeur_brute"] = None
            ok, errors = contracts.validate_canon_output(payload)
            self.assertTrue(ok, msg=f"{extraction}: {errors}")


if __name__ == "__main__":
    unittest.main()
