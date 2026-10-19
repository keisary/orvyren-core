#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``reflexion`` — the ACH reflexive layer (matrice, réfutation).

Coverage (Heuer / EMR-ACH 2026 method, all code-side — no LLM anywhere):

- strict scoring: only ``COHERENT`` / ``INCOHERENT`` / ``NEUTRE`` are accepted,
  unknown hypotheses/evidences are refused;
- diagnosticity: an evidence that says the same thing everywhere has a weight
  of ~0 (neutral everywhere -> 0), a discriminating evidence is strong;
- refutation first: ``REFUTEE`` without an ``INCOHERENT`` cell is impossible,
  ranking is stable and deterministic (ties broken by id), best rival exposed;
- next discriminating test: the gap is the right (hypothesis, evidence) cell on
  a 3-hypothesis case (one counter-intuitive), unscored before ``NEUTRE``;
- reaction to change: dominant flip -> ``escalade`` (never silent), degraded
  dominant -> ``reviser``, weak incoherence -> ``retester``, otherwise ``aucune``;
- canonical serialisation round-trip (``schema_version``, stable sorts) and an
  empty matrix that stays honest ("no evidence");
- loop integration: claims (``branches_concernees`` x ``sens``) build the
  matrix, the outcome carries it, ONE ACH ``REFLECTION`` line and one
  ``BRANCH_UPDATE`` per revision are journaled — and the ACH line NEVER enters
  the frozen evidence packet (the critic payload is byte-identical, so the
  recorded responses of ``fixtures/agents/store_usdc-2023-03`` keep replaying).

The integration doubles (FakeClock / FakeBackend / scripted outputs) live in
this file, same shape as ``tests/test_agents_loop.py`` — that file is never
modified and its payloads are never touched.

Execution: ``python -m unittest tests.test_agents_reflexion``
"""

import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import reflexion  # noqa: E402
from orvyren.agents import worker as worker_mod  # noqa: E402
from orvyren.agents.journal import AgentJournal  # noqa: E402
from orvyren.agents.loop import BoundedLoop  # noqa: E402
from orvyren.agents.reflexion import (  # noqa: E402
    COHERENT,
    INCOHERENT,
    NEUTRE,
    EvidenceMatrix,
    matrix_from_claims,
    sens_to_verdict,
)

REF_PRICES = "observation:bitstamp/usdc-usd/2023-03-11T12:00Z"


# ---------------------------------------------------------------------------
# Matrix helpers.
# ---------------------------------------------------------------------------
def build(*hypotheses):
    """One matrix from ``(hyp_id, label[, counter_intuitive])`` tuples."""
    matrix = EvidenceMatrix()
    for spec in hypotheses:
        hyp_id, label = spec[0], spec[1]
        counter = bool(spec[2]) if len(spec) > 2 else False
        matrix.add_hypothesis(hyp_id, label, counter_intuitive=counter)
    return matrix


class VerdictValidationTest(unittest.TestCase):
    """Closed verdicts and closed identifiers: everything else is refused."""

    def test_verdicts_are_strictly_validated(self):
        matrix = build(("HYP-A", "a"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", COHERENT)
        matrix.score("HYP-A", "EV-1", INCOHERENT)  # re-scoring is allowed
        matrix.score("HYP-A", "EV-1", NEUTRE)
        self.assertEqual(matrix.scored_cells(), (("HYP-A", "EV-1", NEUTRE),))
        for bad in ("POUR", "pour", "", None, "COHERENT!", 3, "incoherent ",
                    "coherent", "NEUTRE "):
            with self.assertRaises(ValueError) as caught:
                matrix.score("HYP-A", "EV-1", bad)
            self.assertIn("E_ACH_VERDICT", str(caught.exception),
                          "verdict %r must be refused" % (bad,))

    def test_unknown_identifiers_are_refused(self):
        matrix = build(("HYP-A", "a"))
        matrix.add_evidence("EV-1", ["r:1"])
        with self.assertRaises(ValueError) as caught:
            matrix.score("HYP-B", "EV-1", COHERENT)
        self.assertIn("E_ACH_UNKNOWN_HYPOTHESIS", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            matrix.score("HYP-A", "EV-2", COHERENT)
        self.assertIn("E_ACH_UNKNOWN_EVIDENCE", str(caught.exception))
        with self.assertRaises(ValueError):
            matrix.diagnosticity("EV-2")
        with self.assertRaises(ValueError):
            matrix.reaction_to_change("HYP-A", "EV-2", INCOHERENT)

    def test_duplicates_and_bad_weights_are_refused(self):
        matrix = build(("HYP-A", "a"))
        matrix.add_evidence("EV-1", ["r:1"], weight=0.5)
        with self.assertRaises(ValueError) as caught:
            matrix.add_evidence("EV-1", ["r:2"])
        self.assertIn("E_ACH_DUPLICATE_EVIDENCE", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            matrix.add_hypothesis("HYP-A", "again")
        self.assertIn("E_ACH_DUPLICATE_HYPOTHESIS", str(caught.exception))
        for weight in (-1.0, float("nan"), float("inf"), "x"):
            with self.assertRaises(ValueError) as caught:
                matrix.add_evidence("EV-2", ["r:3"], weight=weight)
            self.assertIn("E_ACH_WEIGHT", str(caught.exception))


class DiagnosticityTest(unittest.TestCase):
    """The diagnostic weight: variance of the verdicts across hypotheses."""

    def test_neutral_evidence_everywhere_has_no_weight(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        matrix.add_evidence("EV-1", ["r:1"])
        for hyp in ("HYP-A", "HYP-B", "HYP-C"):
            matrix.score(hyp, "EV-1", NEUTRE)
        self.assertAlmostEqual(matrix.diagnosticity("EV-1"), 0.0)

    def test_an_evidence_saying_the_same_thing_everywhere_is_not_diagnostic(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        for evidence, verdict in (("EV-1", COHERENT), ("EV-2", INCOHERENT)):
            matrix.add_evidence(evidence, ["r:%s" % evidence])
            for hyp in ("HYP-A", "HYP-B", "HYP-C"):
                matrix.score(hyp, evidence, verdict)
        self.assertAlmostEqual(matrix.diagnosticity("EV-1"), 0.0,
                               "coherent with every hypothesis = weak")
        self.assertAlmostEqual(matrix.diagnosticity("EV-2"), 0.0,
                               "incoherent with every hypothesis discriminates nothing")

    def test_a_discriminating_evidence_is_strong(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", COHERENT)
        matrix.score("HYP-B", "EV-1", INCOHERENT)
        matrix.score("HYP-C", "EV-1", NEUTRE)
        self.assertGreater(matrix.diagnosticity("EV-1"), 0.5)

    def test_coherent_with_a_single_hypothesis_is_stronger_than_with_all(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-A", "EV-1", COHERENT)          # one hypothesis only
        matrix.score("HYP-A", "EV-2", COHERENT)
        matrix.score("HYP-B", "EV-2", COHERENT)          # every hypothesis
        self.assertGreater(matrix.diagnosticity("EV-1"), 0.0)
        self.assertAlmostEqual(matrix.diagnosticity("EV-2"), 0.0)

    def test_a_single_hypothesis_cannot_be_discriminated(self):
        matrix = build(("HYP-A", "a"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", INCOHERENT)
        self.assertAlmostEqual(matrix.diagnosticity("EV-1"), 0.0)


class RefutationRankTest(unittest.TestCase):
    """Refutation first: rank by weighted INCOHERENT cells, deterministically."""

    def test_refutation_without_incoherent_is_impossible(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"], weight=10.0)
        matrix.score("HYP-A", "EV-1", COHERENT)
        matrix.score("HYP-B", "EV-1", NEUTRE)
        for row in matrix.rank_hypotheses():
            self.assertNotEqual(row["etat"], "REFUTEE")
            self.assertEqual(row["nb_incoherent"], 0)
            self.assertEqual(row["score_refutation"], 0.0)

    def test_a_hypothesis_is_refuted_only_with_incoherent_cells(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-A", "EV-1", INCOHERENT)
        matrix.score("HYP-B", "EV-1", COHERENT)
        matrix.score("HYP-C", "EV-1", COHERENT)
        matrix.score("HYP-A", "EV-2", INCOHERENT)
        matrix.score("HYP-B", "EV-2", NEUTRE)
        matrix.score("HYP-C", "EV-2", NEUTRE)
        rows = {row["hyp_id"]: row for row in matrix.rank_hypotheses()}
        self.assertEqual(rows["HYP-A"]["etat"], "REFUTEE")
        self.assertGreaterEqual(rows["HYP-A"]["score_refutation"], 1.0)
        self.assertEqual(rows["HYP-B"]["etat"], "SOLIDE")
        self.assertEqual(rows["HYP-C"]["etat"], "SOLIDE")

    def test_one_weak_incoherence_only_fragilises(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", INCOHERENT)
        matrix.score("HYP-B", "EV-1", NEUTRE)
        rows = {row["hyp_id"]: row for row in matrix.rank_hypotheses()}
        self.assertEqual(rows["HYP-A"]["etat"], "FRAGILE")
        self.assertEqual(rows["HYP-B"]["etat"], "SOLIDE")
        self.assertLess(rows["HYP-A"]["score_refutation"], 1.0)

    def test_rank_is_stable_and_deterministic(self):
        matrix = build(("HYP-B", "b"), ("HYP-A", "a"), ("HYP-C", "c"))
        first = matrix.rank_hypotheses()
        self.assertEqual(first, matrix.rank_hypotheses())
        self.assertEqual([row["hyp_id"] for row in first],
                         ["HYP-A", "HYP-B", "HYP-C"])  # ties broken by id
        twin = build(("HYP-C", "c"), ("HYP-B", "b"), ("HYP-A", "a"))
        self.assertEqual([row["hyp_id"] for row in twin.rank_hypotheses()],
                         ["HYP-A", "HYP-B", "HYP-C"])  # insertion order free

    def test_meilleur_rival_is_the_most_competitive_alternative(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-A", "EV-1", INCOHERENT)   # HYP-A refuted a bit
        matrix.score("HYP-B", "EV-1", NEUTRE)
        matrix.score("HYP-C", "EV-1", NEUTRE)
        matrix.score("HYP-A", "EV-2", INCOHERENT)
        matrix.score("HYP-B", "EV-2", NEUTRE)
        matrix.score("HYP-C", "EV-2", INCOHERENT)   # HYP-C refuted too
        rows = {row["hyp_id"]: row for row in matrix.rank_hypotheses()}
        self.assertEqual(rows["HYP-A"]["meilleur_rival"], "HYP-B",
                         "the least refuted alternative is the best rival")


class DiscriminatingGapTest(unittest.TestCase):
    """The next test to buy: the most uncertain (hypothesis, evidence) cell."""

    def test_the_gap_is_the_right_cell_with_three_hypotheses(self):
        matrix = build(("HYP-A", "intuitive"), ("HYP-B", "second"),
                       ("HYP-C", "contre-intuitive", True))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-A", "EV-1", COHERENT)
        matrix.score("HYP-B", "EV-1", COHERENT)
        matrix.score("HYP-C", "EV-1", INCOHERENT)
        matrix.score("HYP-A", "EV-2", COHERENT)
        matrix.score("HYP-B", "EV-2", NEUTRE)
        # (HYP-C, EV-2) is the ONLY unscored cell of the matrix.
        gap = matrix.most_discriminating_gap()
        self.assertTrue(gap["found"])
        self.assertEqual((gap["hyp_id"], gap["evidence_id"]), ("HYP-C", "EV-2"))
        self.assertEqual(gap["kind"], "sans_verdict")
        self.assertEqual(gap["refs"], ["r:2"])
        self.assertIn("next discriminating test", gap["justification"])
        self.assertEqual(gap, matrix.most_discriminating_gap())  # deterministic

    def test_an_unscored_cell_is_more_uncertain_than_a_neutre_one(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-A", "EV-1", NEUTRE)
        matrix.score("HYP-B", "EV-1", NEUTRE)
        matrix.score("HYP-A", "EV-2", NEUTRE)   # (HYP-B, EV-2) unscored
        gap = matrix.most_discriminating_gap()
        self.assertEqual((gap["hyp_id"], gap["evidence_id"]), ("HYP-B", "EV-2"))
        self.assertEqual(gap["kind"], "sans_verdict")

    def test_a_fully_scored_matrix_falls_back_to_the_neutre_cells(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", NEUTRE)
        matrix.score("HYP-B", "EV-1", NEUTRE)
        gap = matrix.most_discriminating_gap()
        self.assertTrue(gap["found"])
        self.assertEqual(gap["kind"], "neutre")

    def test_a_fully_informative_matrix_reports_no_gap(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-A", "EV-1", COHERENT)
        matrix.score("HYP-B", "EV-1", INCOHERENT)
        gap = matrix.most_discriminating_gap()
        self.assertFalse(gap["found"])
        self.assertIn("no uncertain cell", gap["justification"])

    def test_most_discriminating_evidence_is_the_claim_with_most_weight(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"), ("HYP-C", "c"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2", "r:3"])
        matrix.score("HYP-A", "EV-1", NEUTRE)     # ~ no diagnosticity
        matrix.score("HYP-B", "EV-1", NEUTRE)
        matrix.score("HYP-C", "EV-1", NEUTRE)
        matrix.score("HYP-A", "EV-2", COHERENT)   # separates the hypotheses
        matrix.score("HYP-B", "EV-2", INCOHERENT)
        matrix.score("HYP-C", "EV-2", NEUTRE)
        best = matrix.most_discriminating_evidence()
        self.assertTrue(best["found"])
        self.assertEqual(best["evidence_id"], "EV-2")
        self.assertEqual(best["refs"], ["r:2", "r:3"])


class ReactionToChangeTest(unittest.TestCase):
    """A change is never silent: structured reactions, explicit flips."""

    def test_a_dominant_flip_is_always_escalade(self):
        matrix = build(("HYP-A", "dominant"), ("HYP-B", "rival"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.score("HYP-B", "EV-1", COHERENT)
        reaction = matrix.reaction_to_change("HYP-A", "EV-2", INCOHERENT)
        self.assertEqual(reaction["action"], "escalade")
        self.assertTrue(reaction["revision"])
        self.assertEqual(reaction["dominant_before"], "HYP-A")
        self.assertEqual(reaction["dominant_after"], "HYP-B")
        self.assertIn("never a silent flip", reaction["motif"])

    def test_a_degraded_dominant_asks_for_a_revision(self):
        matrix = build(("HYP-A", "dominant"), ("HYP-B", "rival"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.add_evidence("EV-2", ["r:2"])
        matrix.add_evidence("EV-3", ["r:3"])
        matrix.add_evidence("EV-4", ["r:4"])
        matrix.add_evidence("EV-5", ["r:5"])
        for evidence in ("EV-1", "EV-2", "EV-3"):   # build a strong refutation
            matrix.score("HYP-A", evidence, NEUTRE)  # of the rival first
            matrix.score("HYP-B", evidence, INCOHERENT)
        matrix.score("HYP-A", "EV-4", COHERENT)
        matrix.score("HYP-B", "EV-4", INCOHERENT)   # HYP-B: REFUTEE, still rival
        reaction = matrix.reaction_to_change("HYP-A", "EV-5", INCOHERENT)
        self.assertEqual(reaction["action"], "reviser")
        self.assertTrue(reaction["revision"])
        self.assertEqual(reaction["dominant_before"], "HYP-A")
        self.assertEqual(reaction["dominant_after"], "HYP-A")  # no silent flip
        self.assertEqual(reaction["etat_before"], "SOLIDE")
        self.assertEqual(reaction["etat_after"], "FRAGILE")

    def test_a_weak_incoherence_asks_for_a_retest(self):
        matrix = build(("HYP-A", "alone"))
        matrix.add_evidence("EV-1", ["r:1"])
        reaction = matrix.reaction_to_change("HYP-A", "EV-1", INCOHERENT)
        self.assertEqual(reaction["action"], "retester")
        self.assertFalse(reaction["revision"])
        self.assertEqual(reaction["etat_after"], "FRAGILE")
        # An evidence refuting EVERY hypothesis discriminates nothing: the
        # evidence itself is suspect -> retest, never a silent revision.
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.score("HYP-B", "EV-1", INCOHERENT)
        reaction = matrix.reaction_to_change("HYP-A", "EV-1", INCOHERENT)
        self.assertEqual(reaction["action"], "retester")
        self.assertEqual(reaction["dominant_before"], reaction["dominant_after"])

    def test_a_change_that_threatens_nothing_needs_no_reaction(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        reaction = matrix.reaction_to_change("HYP-A", "EV-1", COHERENT)
        self.assertEqual(reaction["action"], "aucune")
        self.assertFalse(reaction["revision"])
        self.assertEqual(reaction["dominant_before"], reaction["dominant_after"])

    def test_the_change_is_recorded_not_only_reported(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        matrix.add_evidence("EV-1", ["r:1"])
        matrix.reaction_to_change("HYP-A", "EV-1", INCOHERENT)
        self.assertEqual(matrix.scored_cells(), (("HYP-A", "EV-1", INCOHERENT),))


class CanonicalSerializationTest(unittest.TestCase):
    """``to_dict`` / ``from_dict``: canonical, stable, exact round-trip."""

    def _matrix(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b", True))
        matrix.add_evidence("EV-1", ["r:1", "r:2"], weight=2.5)
        matrix.add_evidence("EV-2", ["r:3"])
        matrix.score("HYP-A", "EV-1", INCOHERENT)
        matrix.score("HYP-B", "EV-1", COHERENT)
        matrix.score("HYP-A", "EV-2", NEUTRE)
        return matrix

    def test_round_trip_is_exact(self):
        matrix = self._matrix()
        data = matrix.to_dict()
        self.assertEqual(data["schema_version"], "orvyren/ach-matrix/v1")
        self.assertEqual(EvidenceMatrix.from_dict(data).to_dict(), data)
        self.assertEqual(matrix.to_dict(), data)  # to_dict is pure

    def test_the_canonical_order_is_stable(self):
        data = self._matrix().to_dict()
        self.assertEqual([cell for cell in data["cells"]],
                         [["HYP-A", "EV-1", INCOHERENT],
                          ["HYP-A", "EV-2", NEUTRE],
                          ["HYP-B", "EV-1", COHERENT]])
        self.assertEqual([row["hyp_id"] for row in data["hypotheses"]],
                         ["HYP-A", "HYP-B"])
        self.assertEqual([row["evidence_id"] for row in data["evidence"]],
                         ["EV-1", "EV-2"])

    def test_a_foreign_schema_is_refused(self):
        data = self._matrix().to_dict()
        with self.assertRaises(ValueError) as caught:
            EvidenceMatrix.from_dict(dict(data, schema_version="x/y/v9"))
        self.assertIn("E_ACH_SCHEMA", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            EvidenceMatrix.from_dict(dict(data, surprise=True))
        self.assertIn("E_ACH_SCHEMA_FIELDS", str(caught.exception))

    def test_a_tampered_view_never_survives_a_round_trip(self):
        data = self._matrix().to_dict()
        data["ranking"] = [{"hyp_id": "HYP-A", "etat": "SOLIDE"}]
        data["gap"] = {"found": False}
        rebuilt = EvidenceMatrix.from_dict(data).to_dict()
        self.assertEqual([row["hyp_id"] for row in rebuilt["ranking"]],
                         ["HYP-B", "HYP-A"],
                         "the least refuted hypothesis leads again")
        self.assertEqual(rebuilt["ranking"][1]["etat"], "REFUTEE")
        self.assertTrue(rebuilt["gap"]["found"])


class EmptyMatrixTest(unittest.TestCase):
    """An empty matrix stays honest: "no evidence", never an invented test."""

    def test_no_hypothesis_no_evidence(self):
        matrix = EvidenceMatrix()
        self.assertEqual(matrix.rank_hypotheses(), [])
        self.assertEqual(matrix.scored_cells(), ())
        data = matrix.to_dict()
        self.assertEqual(data["note"], "no evidence")
        self.assertEqual(data["cells"], [])
        gap = matrix.most_discriminating_gap()
        self.assertFalse(gap["found"])
        self.assertIn("no evidence", gap["justification"])

    def test_hypotheses_without_evidence(self):
        matrix = build(("HYP-A", "a"), ("HYP-B", "b"))
        rows = matrix.rank_hypotheses()
        self.assertEqual([row["etat"] for row in rows], ["SOLIDE", "SOLIDE"])
        self.assertEqual([row["nb_preuves"] for row in rows], [0, 0])
        gap = matrix.most_discriminating_gap()
        self.assertFalse(gap["found"])
        self.assertIn("no evidence", gap["justification"])
        self.assertEqual(matrix.to_dict()["note"], "no evidence")


class SensMappingTest(unittest.TestCase):
    """The claim ``sens`` vocabulary: closed mapping, honest default."""

    def test_the_mapping_is_closed_and_honest(self):
        self.assertEqual(sens_to_verdict("POUR"), COHERENT)
        self.assertEqual(sens_to_verdict("pour "), COHERENT)
        self.assertEqual(sens_to_verdict("CONTRE"), INCOHERENT)
        self.assertEqual(sens_to_verdict("NEUTRE"), NEUTRE)
        self.assertEqual(sens_to_verdict(""), NEUTRE)
        self.assertEqual(sens_to_verdict(None), NEUTRE)
        self.assertEqual(sens_to_verdict("POURQUOI"), NEUTRE)

    def test_matrix_from_claims_scores_branches_and_ignores_unknown_branches(self):
        hypotheses = [{"id": "HYP-001", "enonce": "lecture A"},
                      {"id": "HYP-002", "enonce": "lecture B"}]
        claims = [
            {"enonce": "a", "refs": ["r:1"], "sens": "POUR",
             "branches_concernees": ["HYP-002"]},
            {"enonce": "b", "refs": ["r:2"], "sens": "CONTRE",
             "branches_concernees": ["HYP-001"]},
            {"enonce": "c", "refs": ["r:3"], "sens": "NEUTRE",
             "branches_concernees": ["HYP-INCONNUE"]},   # never invents a branch
            {"enonce": "d", "refs": ["r:4"], "sens": "TRES_POUR",
             "branches_concernees": ["HYP-001"]},
        ]
        matrix, reactions = matrix_from_claims(hypotheses, claims)
        self.assertEqual(matrix.evidence_ids(), ("EV-001", "EV-002", "EV-003", "EV-004"))
        self.assertEqual(matrix.scored_cells(), (
            ("HYP-001", "EV-002", INCOHERENT),
            ("HYP-001", "EV-004", NEUTRE),
            ("HYP-002", "EV-001", COHERENT)))
        self.assertEqual(len(reactions), 3)  # one per scored branch, not per claim


# ---------------------------------------------------------------------------
# Loop integration (same doubles shape as tests/test_agents_loop.py).
# ---------------------------------------------------------------------------
class FakeClock:
    """Deterministic clock: a fixed step per read."""

    def __init__(self, step_seconds=0.02, base_iso="2023-03-11T12:00:00+00:00"):
        self._t = 0.0
        self._step = float(step_seconds)
        self._base = datetime.fromisoformat(base_iso)

    def monotonic(self):
        self._t += self._step
        return self._t

    def now_iso(self):
        return (self._base + timedelta(seconds=self._t)).isoformat()


class FakeBackend(contracts.LLMBackend):
    """Scripted backend: one LLMResult per call, every payload recorded."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def complete(self, *, role, role_version, schema_id, system_prompt, payload):
        self.calls.append({
            "role": role, "role_version": role_version, "schema_id": schema_id,
            "system_prompt": system_prompt,
            "payload": json.loads(json.dumps(payload, ensure_ascii=False, default=str)),
        })
        if not self.script:
            raise AssertionError("FakeBackend script exhausted (call %d)" % len(self.calls))
        return self.script.pop(0)


def llm_ok(data, *, n):
    """A successful scripted call carrying the response and its accounting."""
    return contracts.LLMResult(
        ok=True, raw=json.dumps(data, ensure_ascii=False, sort_keys=True), data=data,
        provider="fake", model="fake-orch", model_version_pinned="fake-orch-2026-01",
        temperature=0.0, tokens_in=100, cached_in=0, tokens_out=40, cost_usd=0.001,
        latency_ms=12,
        prompt_hash=hashlib.sha256(("prompt-%d" % n).encode()).hexdigest(),
        response_hash=hashlib.sha256(("response-%d" % n).encode()).hexdigest(),
        ts_utc="2023-03-11T12:00:00.000000+00:00")


def plan_task_data():
    """A valid ``orvyren/orch/v1`` plan holding exactly one task."""
    return {"$schema": "orvyren/orch/v1", "lacune_id": "L-1",
            "tache": {"question": QUESTION_PRICES, "outil": "read_prices",
                      "args": {"venue": "bitstamp", "symbol": "USDC-USD",
                               "from": "2023-03-01", "to": "2023-03-31"},
                      "critere_discriminant": "deux venues sous le pair",
                      "branches_concernees": ["HYP-001"], "cout_max": {}},
            "stop": False, "motif_stop": None, "non_recherche": []}


def plan_stop_data():
    """A valid closing plan: no task left with positive value (ARRET-1)."""
    return {"$schema": "orvyren/orch/v1", "lacune_id": "", "tache": None,
            "stop": True, "motif_stop": "plus aucune tache discriminante",
            "non_recherche": []}


QUESTION_PRICES = "la dispersion confirme-t-elle une dislocation realisable entre venues"


def eval_ach_data():
    """One evaluation whose claims score two competing hypotheses."""
    return {"claims": [
        {"enonce": "l'exchange independant confirme une decote plus profonde",
         "refs": [REF_PRICES], "sens": "POUR", "branches_concernees": ["HYP-002"]},
        {"enonce": "la profondeur d'execution realisee contredit la lecture",
         "refs": [REF_PRICES], "sens": "CONTRE", "branches_concernees": ["HYP-001"]}],
        "reflexions": "deux lectures concurrentes evaluees"}


def eval_plain_data():
    """One evaluation whose claims carry no ACH field at all."""
    return {"claims": [{"enonce": "la venue d'exchange se situe sous les deux agregateurs",
                        "refs": [REF_PRICES]}], "reflexions": "lecture conforme"}


def fixtures():
    """The frozen fixture schema (lookup keys) with the USDC/SVB subset."""
    return {
        "prices": {"bitstamp|USDC-USD": [
            {"venue": "bitstamp", "symbol": "USDC-USD", "ts": "2023-03-11T12:00:00Z",
             "value": 0.8053, "source_ref": REF_PRICES}]},
        "supply": {}, "chain": {}, "documents": {}, "signals": {},
        "snapshot": {"ref": "graph_snapshot:usdc-2023-03@2023-03-11T12:00:00Z",
                     "as_of": "2023-03-11T12:00:00Z", "refs": [REF_PRICES]},
    }


def make_scenario(script, **overrides):
    """Wire one loop on the frozen fixtures; returns (loop, journal, backend)."""
    from orvyren.agents.tools import build_v1_registry

    data = fixtures()
    journal = overrides.pop("journal", None) or AgentJournal()
    backend = FakeBackend(script)
    tools = overrides.pop("tools", None) or build_v1_registry(fixtures=data, journal=journal)
    loop = BoundedLoop(
        case_id="usdc-2023-03", run_id="run-test", agent_id="orchestrator",
        backend=backend, tools=tools, journal=journal, clock=FakeClock(),
        prompt_version="orch-p1.1.0", system_prompt="SYS-INJECTE",
        snapshot=overrides.pop("snapshot", data["snapshot"]),
        lacunes=overrides.pop("lacunes", [{"lacune_id": "L-1", "question": QUESTION_PRICES}]),
        hypotheses=overrides.pop("hypotheses", [
            {"id": "HYP-001", "enonce": "la dislocation est realisable",
             "etat": "UNDER_TEST"},
            {"id": "HYP-002", "enonce": "la decote n'est pas realisable",
             "etat": "UNDER_TEST", "counter_intuitive": True}]),
        net_voi=overrides.pop("net_voi", None))
    if overrides:
        raise AssertionError("unknown overrides: %s" % sorted(overrides))
    return loop, journal, backend


class LoopIntegrationTest(unittest.TestCase):
    """The ACH layer wired into the bounded loop, payloads untouched."""

    def _run(self, script, **overrides):
        loop, journal, backend = make_scenario(script, **overrides)
        outcome = loop.run()
        return loop, journal, backend, outcome

    def test_the_outcome_carries_the_matrix_and_the_journal_the_ach_line(self):
        loop, journal, backend, outcome = self._run(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_ach_data(), n=2),
             llm_ok(plan_stop_data(), n=3)])
        # -- the matrix travels on the outcome (and thus outcome_orchestrator.json)
        matrix = outcome.reflexion
        self.assertEqual(matrix["schema_version"], "orvyren/ach-matrix/v1")
        self.assertEqual(len(matrix["cells"]), 2)
        self.assertEqual(matrix["ranking"][0]["hyp_id"], "HYP-002")
        self.assertEqual(matrix["ranking"][1]["etat"], "FRAGILE")
        self.assertTrue(matrix["gap"]["found"])
        self.assertEqual(outcome.to_dict()["reflexion"], matrix)
        self.assertEqual(contracts.LoopOutcome.from_dict(
            outcome.to_dict()).to_dict(), outcome.to_dict())
        # -- ONE deterministic ACH REFLECTION line, refs of the most
        #    discriminating claim, plus one BRANCH_UPDATE for the revision.
        ach_lines = [entry for entry in journal.entries()
                     if "ACH matrix:" in entry.content]
        self.assertEqual(len(ach_lines), 1)
        line = ach_lines[0]
        self.assertEqual(line.kind, "REFLECTION")
        self.assertIn("ACH matrix: HYP-002 remains SOLIDE, next discriminating test:",
                      line.content)
        self.assertEqual(line.refs, (REF_PRICES,))
        self.assertEqual(line.ts_utc[:10], "2023-03-11")  # injected clock
        updates = [entry for entry in journal.entries() if entry.kind == "BRANCH_UPDATE"]
        self.assertEqual(len(updates), 1)
        self.assertIn("action escalade", updates[0].content)
        self.assertFalse(any(ch.isdigit() for ch in updates[0].content),
                         "a BRANCH_UPDATE proposal carries no figure (B3 R1)")
        self.assertEqual(updates[0].status, "PROPOSED")
        self.assertTrue(journal.verify_chain()[0])

    def test_the_ach_reflection_never_becomes_a_critic_claim(self):
        """The frozen evidence packet keeps its claims: the replay is preserved."""
        loop, journal, backend, outcome = self._run(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_ach_data(), n=2),
             llm_ok(plan_stop_data(), n=3)])
        packet = worker_mod.build_evidence_packet(
            journal, loop.observed_refs, run_id="run-test", case_id="usdc-2023-03",
            snapshot_ref="graph_snapshot:usdc-2023-03@2023-03-11T12:00:00Z")
        texts = [claim["text"] for claim in packet.claims]
        self.assertEqual(texts, [
            "VOI_NOT_ESTIMABLE: no NetVoI estimator injected — fixed bounded "
            "order kept (documented fallback)",
            "l'exchange independant confirme une decote plus profonde",
            "la profondeur d'execution realisee contredit la lecture"])
        self.assertEqual(packet.refs, (REF_PRICES,))
        self.assertTrue(all("ACH matrix:" not in text for text in texts))
        self.assertTrue(all("ACH revision:" not in text for text in texts))

    def test_the_llm_payloads_are_untouched(self):
        loop, journal, backend, outcome = self._run(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_ach_data(), n=2),
             llm_ok(plan_stop_data(), n=3)])
        self.assertEqual([call["schema_id"] for call in backend.calls],
                         ["orvyren/orch/v1", "", "orvyren/orch/v1"])
        self.assertEqual(sorted(backend.calls[0]["payload"]),
                         sorted(["snapshot_at", "lacunes", "hypotheses",
                                 "budget_restant", "sources_autorisees",
                                 "snapshot", "outils_indisponibles"]))
        self.assertEqual(sorted(backend.calls[1]["payload"]),
                         sorted(["snapshot_at", "tache", "tool_status",
                                 "observations", "budget_restant", "consigne"]))

    def test_no_ach_line_without_a_scored_cell(self):
        loop, journal, backend, outcome = self._run(
            [llm_ok(plan_task_data(), n=1), llm_ok(eval_plain_data(), n=2),
             llm_ok(plan_stop_data(), n=3)])
        self.assertFalse(any("ACH matrix:" in entry.content
                             for entry in journal.entries()))
        self.assertFalse(any(entry.kind == "BRANCH_UPDATE"
                             for entry in journal.entries()))
        self.assertEqual(outcome.reflexion["cells"], [])

    def test_an_empty_matrix_stays_honest_in_the_outcome(self):
        loop, journal, backend, outcome = self._run(
            [llm_ok(plan_task_data(), n=1),
             llm_ok({"claims": [], "insuffisance": "rien d'exploitable"}, n=2),
             llm_ok(plan_stop_data(), n=3)])
        self.assertEqual(outcome.reflexion["note"], "no evidence")
        self.assertFalse(outcome.reflexion["gap"]["found"])
        self.assertIn("no evidence", outcome.reflexion["gap"]["justification"])
        self.assertFalse(any("ACH matrix:" in entry.content
                             for entry in journal.entries()))

    def test_the_ach_lines_are_deterministic_across_replays(self):
        script = lambda: [llm_ok(plan_task_data(), n=1), llm_ok(eval_ach_data(), n=2),
                          llm_ok(plan_stop_data(), n=3)]
        _, journal_a, _, outcome_a = self._run(script())
        _, journal_b, _, outcome_b = self._run(script())
        self.assertEqual(outcome_a.reflexion, outcome_b.reflexion)
        self.assertEqual([entry.content for entry in journal_a.entries()],
                         [entry.content for entry in journal_b.entries()])


if __name__ == "__main__":
    unittest.main()
