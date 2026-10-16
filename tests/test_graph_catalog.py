#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: relation catalogue enum (ORVYREN-Core).

Covers B2_GRAPHE_ETUDE.md §3.1–§3.3 (archive 2026-10-15): the machine-verifiable
catalogue — 34 kinds in 4 families, allowed subject/object tokens, direction,
transitivity, origins 14 M / 13 D / 7 N — and the golden rules of the four
families as far as they are expressible on the enum itself.

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph.catalog import (  # noqa: E402
    DIRECTED,
    FAMILIES,
    FAMILY_CONSTRAINT,
    FAMILY_MECHANISM,
    FAMILY_PROOF,
    FAMILY_STRUCTURE,
    KIND_CLASS,
    NODE_KINDS,
    RELATION_CATALOG,
    ROLE_SETS,
    SYMMETRIC,
    WILDCARDS,
    NodeKind,
    catalog_stats,
    token_matches,
)


class CatalogStructureTest(unittest.TestCase):
    """The enum itself is machine-verifiable (B2 §3.2 counts and columns)."""

    def test_catalogue_has_exactly_34_kinds(self):
        self.assertEqual(len(RELATION_CATALOG), 34, msg=f"measured {len(RELATION_CATALOG)}")

    def test_family_counts_match_the_catalogue(self):
        measured = catalog_stats()
        self.assertEqual(measured[FAMILY_PROOF], 8, msg=f"measured {measured}")
        self.assertEqual(measured[FAMILY_STRUCTURE], 15, msg=f"measured {measured}")
        self.assertEqual(measured[FAMILY_MECHANISM], 3, msg=f"measured {measured}")
        self.assertEqual(measured[FAMILY_CONSTRAINT], 8, msg=f"measured {measured}")
        self.assertEqual(sum(measured.values()), 34)

    def test_refs_cover_the_catalogue_rows(self):
        refs = [spec.ref for spec in RELATION_CATALOG.values()]
        expected = ([f"1.{i}" for i in range(1, 9)] +
                    [f"2.{i}" for i in range(1, 16)] +
                    [f"3.{i}" for i in range(1, 4)] +
                    [f"4.{i}" for i in range(1, 9)])
        self.assertEqual(len(refs), 34, msg=f"measured {len(refs)}")
        self.assertEqual(set(refs), set(expected))

    def test_origins_split_is_14_13_7(self):
        counts = {"M": 0, "D": 0, "N": 0}
        for spec in RELATION_CATALOG.values():
            counts[spec.origin] += 1
        self.assertEqual(counts, {"M": 14, "D": 13, "N": 7}, msg=f"measured {counts}")

    def test_every_spec_is_well_formed(self):
        for kind, spec in RELATION_CATALOG.items():
            with self.subTest(kind=kind):
                self.assertIn(spec.family, FAMILIES)
                self.assertIn(spec.direction, (DIRECTED, SYMMETRIC))
                self.assertIn(spec.transitivity, ("N", "T", "Q"))
                self.assertTrue(spec.subjects, "no allowed subject")
                self.assertTrue(spec.objects, "no allowed object")
                self.assertTrue(spec.semantics.strip(), "empty semantics")
                self.assertTrue(spec.origin_detail.strip(), "empty origin cell")
                self.assertEqual(kind, kind.upper())

    def test_every_token_resolves(self):
        known = NODE_KINDS | WILDCARDS | frozenset(ROLE_SETS)
        for kind, spec in RELATION_CATALOG.items():
            for token in spec.subjects | spec.objects:
                with self.subTest(kind=kind, token=token):
                    self.assertIn(token, known, f"unresolvable token {token}")

    def test_kind_classes_are_total(self):
        self.assertEqual(set(KIND_CLASS), set(NODE_KINDS))
        for kind, cls in KIND_CLASS.items():
            with self.subTest(kind=kind):
                self.assertIn(cls, NODE_KINDS)
        for cls in (NodeKind.ORGANISATION, NodeKind.ACTIF, NodeKind.CONTRAT,
                    NodeKind.ADRESSE, NodeKind.PREUVE, NodeKind.DECISION,
                    NodeKind.GOUVERNANCE, NodeKind.CHAINE, NodeKind.UNITE):
            self.assertEqual(KIND_CLASS[cls], cls)

    def test_token_matching_rules(self):
        # Class token accepts every member.
        self.assertTrue(token_matches(NodeKind.ACTIF, NodeKind.STABLECOIN))
        self.assertTrue(token_matches(NodeKind.CONTRAT, NodeKind.SAFE))
        # Wildcards accept anything.
        self.assertTrue(token_matches("TOUT", NodeKind.HYPOTHESE))
        self.assertTrue(token_matches("SUJET", NodeKind.TIMELOCK))
        # ENTITE = economic entity of the world layer.
        self.assertTrue(token_matches("ENTITE", NodeKind.LST))
        self.assertTrue(token_matches("ENTITE", NodeKind.MULTISIG))
        # Role sets.
        self.assertTrue(token_matches("AUTORITE", NodeKind.DAO))
        self.assertTrue(token_matches("AUTORITE", NodeKind.MULTISIG))
        self.assertTrue(token_matches("DROIT", NodeKind.PERMISSION))
        # Strictness: a stablecoin is not a contract, a role is not a droit,
        # a claim is not an economic entity.
        self.assertFalse(token_matches(NodeKind.CONTRAT, NodeKind.STABLECOIN))
        self.assertFalse(token_matches("DROIT", NodeKind.TIMELOCK))
        self.assertFalse(token_matches(NodeKind.CLAIM, NodeKind.HYPOTHESE))
        self.assertFalse(token_matches("ENTITE", NodeKind.CLAIM))
        self.assertFalse(token_matches("ENTITE", NodeKind.HYPOTHESE))

    def test_family_golden_rules_on_the_enum(self):
        # SUPPORTS/REFUTES: Claim -> Hypothesis only, never transitive.
        for kind in ("SUPPORTS", "REFUTES"):
            spec = RELATION_CATALOG[kind]
            self.assertEqual(spec.subjects, frozenset({NodeKind.CLAIM}))
            self.assertEqual(spec.objects, frozenset({NodeKind.HYPOTHESE}))
            self.assertEqual(spec.transitivity, "N")
        # CORRELATES_WITH: symmetric, never chained.
        spec = RELATION_CATALOG["CORRELATES_WITH"]
        self.assertEqual(spec.direction, SYMMETRIC)
        self.assertEqual(spec.transitivity, "N")
        # Quasi-transitive kinds are the two bounded-propagation ones.
        quasi = sorted(k for k, s in RELATION_CATALOG.items() if s.transitivity == "Q")
        self.assertEqual(quasi, ["AFFECTS", "DEPENDS_ON"])
        # Transitive kinds: SUPERSEDES chain + the two closures of §6.3.
        transitive = sorted(k for k, s in RELATION_CATALOG.items() if s.transitivity == "T")
        self.assertEqual(transitive, ["IS_A", "PART_OF", "SUPERSEDES"])
        # Symmetric kinds (§3.2 "Sens").
        symmetric = sorted(k for k, s in RELATION_CATALOG.items() if s.direction == SYMMETRIC)
        self.assertEqual(symmetric, ["CONTRADICTS", "CORRELATES_WITH", "SAME_AS"])


if __name__ == "__main__":
    unittest.main()
