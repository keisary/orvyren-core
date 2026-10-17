# -*- coding: utf-8 -*-
"""W8 (L8.7) — règle 0 : les quatre documents finaux ne mentionnent jamais le nom
du système amont. Le contrôle est exécuté par la suite de tests (donc en CI) :
toute occurrence fait échouer la livraison."""

import os
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FINAL_DOCUMENTS = (
    "ORVYREN_DOC1_EXPLICATION_SIMPLE.md",
    "ORVYREN_DOC2_TECHNIQUE_COMPLET.md",
    "ORVYREN_DOC3_PROPOSITIONS_ET_ECARTES.md",
    "ORVYREN_DOC4_PLAN_IMPLEMENTATION.md",
)
FORBIDDEN_TERM = "mimir"  # règle 0 du gel : aucun nom propre du système amont


class ForbiddenTermTests(unittest.TestCase):
    def test_the_four_final_documents_are_clean(self):
        for name in FINAL_DOCUMENTS:
            path = os.path.join(_ROOT, name)
            self.assertTrue(os.path.isfile(path), f"document manquant : {name}")
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read().lower()
            self.assertNotIn(
                FORBIDDEN_TERM, text,
                f"{name} contient un nom propre interdit par la règle 0 (gel v2)")


if __name__ == "__main__":
    unittest.main()
