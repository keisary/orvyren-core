#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: hypothesis registry — record, lifecycle, 5 transition rules.

Covers B3_DECISION_ETUDE.md §a.3–§a.5 (archive 2026-10-15): the 12-field
record (mandatory R criterion, maintained proof lists, label-only ``p``), the
7-state lifecycle, and the 5 transition rules enforced by the registry —
including "ARCHIVED is never a deletion" and "an LLM never removes a
hypothesis" (same id, same history).

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.branches.hypotheses import (  # noqa: E402
    ALLOWED_TRANSITIONS,
    HYPOTHESIS_FIELD_GROUP_COUNT,
    HYPOTHESIS_FIELD_GROUPS,
    HYPOTHESIS_STATES,
    P_LABELS,
    RELATION_LINK_KINDS,
    Criterion,
    HistoryEntry,
    HypothesisRecord,
    HypothesisRegistry,
    record_from_dict,
    record_to_dict,
    validate_hypothesis,
)


def make_hypothesis(**overrides) -> HypothesisRecord:
    """A conform CREATED record (B3 §a.3 skeleton), then apply overrides."""
    values = dict(
        id="H-01TEST",
        case_id="rseth-2026-04",
        enonce="Le décrochage est un stress d'émetteur (rsETH non adossé), "
               "pas une perturbation de venue.",
        criteres=(
            Criterion(nom="soutien",
                      predicat="invariant_inter_chaines_viole == true",
                      seuil="écart > tolérance 0",
                      sources=("eth_getLogs OFT adapter", "totalSupply() par chaîne"),
                      fenetre="t-48h..t+24h"),
            Criterion(nom="refutation",
                      predicat="divergence_oracle_marche < 100 bps pendant >= 2 h",
                      seuil=">= 2 h ET isFrozen == 0",
                      sources=("Chainlink latestAnswer", "Pool.getReserveData"),
                      fenetre="t0..t0+6h"),
        ),
        preuves_pour=(),
        preuves_contre=(),
        inconnues=(),
        etat="CREATED",
        p=None,
        p_gel_ref="",
        histoire=(HistoryEntry(utc="2026-04-18T18:05:00Z", transition="CREATED",
                               raison="proposée par l'explorateur (faits: cap_ratio, oracle)",
                               refs=("evt:cap_ratio@18:00Z",)),),
        provenance={"auteur": "agent:explorateur v0", "modele": "à figer",
                    "date": "2026-04-18T18:05:00Z"},
        relations=(),
    )
    values.update(overrides)
    return HypothesisRecord(**values)


class RecordStructureTest(unittest.TestCase):
    """The record is exactly the 12 field groups of §a.3."""

    def test_field_group_count_is_12(self):
        self.assertEqual(len(HYPOTHESIS_FIELD_GROUPS), HYPOTHESIS_FIELD_GROUP_COUNT)
        self.assertEqual(HYPOTHESIS_FIELD_GROUP_COUNT, 12)

    def test_field_groups_cover_the_dataclass(self):
        grouped = [name for group in HYPOTHESIS_FIELD_GROUPS for name in group]
        self.assertEqual(sorted(grouped), sorted(f for f in HypothesisRecord.__dataclass_fields__))
        self.assertEqual(len(grouped), len(set(grouped)), "a field appears twice")

    def test_lifecycle_has_seven_states(self):
        self.assertEqual(len(HYPOTHESIS_STATES), 7, msg=f"measured {HYPOTHESIS_STATES}")
        self.assertEqual(set(ALLOWED_TRANSITIONS), set(HYPOTHESIS_STATES))
        for state, targets in ALLOWED_TRANSITIONS.items():
            with self.subTest(state=state):
                for target in targets:
                    self.assertIn(target, HYPOTHESIS_STATES)

    def test_transition_map_matches_the_diagram(self):
        self.assertEqual(ALLOWED_TRANSITIONS["CREATED"],
                         ("UNDER_TEST", "MERGED_INTO", "ARCHIVED"))
        self.assertEqual(set(ALLOWED_TRANSITIONS["UNDER_TEST"]),
                         {"SUPPORTED", "REFUTED", "INCONCLUSIVE", "MERGED_INTO", "ARCHIVED"})
        self.assertEqual(ALLOWED_TRANSITIONS["ARCHIVED"], ("UNDER_TEST",))
        # "tout état -> ARCHIVED" (ARCHIVED itself excluded: no self-transition).
        for state in HYPOTHESIS_STATES:
            if state != "ARCHIVED":
                self.assertIn("ARCHIVED", ALLOWED_TRANSITIONS[state])

    def test_p_is_a_label_never_a_number(self):
        self.assertEqual(set(P_LABELS), {"improbable", "possible", "probable"})


class ValidationTest(unittest.TestCase):
    """§a.3 constraints + §a.5 falsifiability checklist."""

    def _assert_rejects(self, record, code):
        errors = validate_hypothesis(record)
        self.assertIn(code, errors, f"expected {code}, got {errors}")

    def test_conform_record_passes(self):
        self.assertEqual(validate_hypothesis(make_hypothesis()), ())

    def test_mandatory_refutation_criterion(self):
        only_support = (make_hypothesis().criteres[0],)
        self._assert_rejects(make_hypothesis(criteres=only_support),
                             "E_HYP_NO_REFUTATION_CRITERION")
        only_refute = (make_hypothesis().criteres[1],)
        self._assert_rejects(make_hypothesis(criteres=only_refute),
                             "E_HYP_NO_SUPPORT_CRITERION")

    def test_criterion_needs_predicate_threshold_sources_window(self):
        bad = (Criterion(nom="refutation", predicat="", seuil=">= 2 h",
                         sources=("Chainlink",), fenetre="t0..t0+6h"),)
        self._assert_rejects(make_hypothesis(criteres=make_hypothesis().criteres + bad),
                             "E_HYP_CRITERION_INCOMPLETE")

    def test_identity_and_statement(self):
        self._assert_rejects(make_hypothesis(id="  "), "E_HYP_ID_EMPTY")
        self._assert_rejects(make_hypothesis(case_id=""), "E_HYP_CASE_EMPTY")
        self._assert_rejects(make_hypothesis(enonce=""), "E_HYP_ENONCE_EMPTY")

    def test_state_is_closed(self):
        self._assert_rejects(make_hypothesis(etat="MAYBE"), "E_HYP_STATE_UNKNOWN")

    def test_p_is_never_a_number(self):
        self._assert_rejects(make_hypothesis(p=0.7), "E_HYP_P_NOT_LABEL")
        self._assert_rejects(make_hypothesis(p="certain"), "E_HYP_P_NOT_LABEL")
        self._assert_rejects(make_hypothesis(p="probable"), "E_HYP_P_NO_GEL_REF")
        self.assertEqual(
            validate_hypothesis(make_hypothesis(p="probable",
                                                p_gel_ref="gel:v2@2026-04-18")), ())

    def test_history_entries_are_complete(self):
        broken = HistoryEntry(utc="", transition="UNDER_TEST", raison="x",
                              refs=("obs:1",))
        self._assert_rejects(
            make_hypothesis(histoire=make_hypothesis().histoire + (broken,)),
            "E_HYP_HISTORY_INCOMPLETE")

    def test_provenance_needs_author_version_date(self):
        self._assert_rejects(make_hypothesis(provenance={"auteur": "agent:x"}),
                             "E_HYP_PROVENANCE_INCOMPLETE")

    def test_relation_links_are_controlled(self):
        self._assert_rejects(make_hypothesis(relations=("MINTS:H-9",)),
                             "E_HYP_RELATION_UNKNOWN")
        self._assert_rejects(make_hypothesis(relations=("SUPPORTS",)),
                             "E_HYP_RELATION_UNKNOWN")
        for kind in RELATION_LINK_KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(
                    validate_hypothesis(make_hypothesis(
                        relations=("%s:H-01OTHER" % kind,))), ())


class RegistryRulesTest(unittest.TestCase):
    """The 5 transition rules of §a.4, enforced by the registry."""

    def setUp(self):
        self.registry = HypothesisRegistry()
        self.registry.create(make_hypothesis())

    def test_ids_are_never_reused(self):
        with self.assertRaises(ValueError) as caught:
            self.registry.create(make_hypothesis())
        self.assertIn("E_HYP_ID_TAKEN", str(caught.exception))

    def test_create_refuses_invalid_or_non_created(self):
        with self.assertRaises(ValueError):
            self.registry.create(make_hypothesis(id="H-BAD", enonce=""))
        with self.assertRaises(ValueError) as caught:
            self.registry.create(make_hypothesis(id="H-LATE", etat="UNDER_TEST"))
        self.assertIn("E_HYP_CREATE_STATE", str(caught.exception))

    # -- rule 1 ------------------------------------------------------------
    def test_supported_needs_a_satisfied_s_criterion(self):
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
            self.registry.transition("H-01TEST", "SUPPORTED", "par défaut", ("obs:2",))
        self.assertIn("E_HYP_SUPPORTED_WITHOUT_S_CRITERION", str(caught.exception))

    def test_refuted_needs_a_satisfied_r_criterion(self):
        self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "REFUTED", "par défaut", ("obs:2",))
        self.assertIn("E_HYP_REFUTED_WITHOUT_R_CRITERION", str(caught.exception))

    def test_inconclusive_needs_no_criterion(self):
        self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        updated = self.registry.transition("H-01TEST", "INCONCLUSIVE",
                                           "critères non franchis", ("obs:2",))
        self.assertEqual(updated.etat, "INCONCLUSIVE")

    def test_verdicts_need_the_matching_criterion(self):
        self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        supported = self.registry.transition(
            "H-01TEST", "SUPPORTED", "invariant violé", ("obs:2",),
            criteres_satisfaits=("soutien",))
        self.assertEqual(supported.etat, "SUPPORTED")

    def test_forbidden_transitions_are_refused(self):
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "SUPPORTED", "saut", ("obs:1",),
                                     criteres_satisfaits=("soutien",))
        self.assertIn("E_HYP_TRANSITION_FORBIDDEN", str(caught.exception))

    # -- rule 2 ------------------------------------------------------------
    def test_every_transition_is_journalised_with_refs(self):
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ())
        self.assertIn("E_HYP_TRANSITION_NO_REFS", str(caught.exception))
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "UNDER_TEST", "", ("obs:1",))
        self.assertIn("E_HYP_TRANSITION_NO_RAISON", str(caught.exception))

    def test_one_transition_per_observation_ref(self):
        self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        with self.assertRaises(ValueError) as caught:
            self.registry.transition("H-01TEST", "INCONCLUSIVE", "reprise", ("obs:1",))
        self.assertIn("E_HYP_HISTORY_REF_REUSED", str(caught.exception))

    def test_no_silent_update_history_only_grows(self):
        created = self.registry.get("H-01TEST")
        self.registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        updated = self.registry.get("H-01TEST")
        self.assertEqual(len(updated.histoire), len(created.histoire) + 1)
        self.assertEqual(updated.histoire[0], created.histoire[0])  # untouched

    # -- rule 3 ------------------------------------------------------------
    def test_archived_is_a_state_not_a_deletion(self):
        self.registry.archive("H-01TEST", "épisode clos", ("evt:close",))
        record = self.registry.get("H-01TEST")          # still retrievable
        self.assertEqual(record.etat, "ARCHIVED")
        self.assertGreaterEqual(len(record.histoire), 2)  # trace kept
        # Wake-up: same id, same history.
        woken = self.registry.wake("H-01TEST", "nouvelle preuve", ("obs:9",))
        self.assertEqual(woken.id, "H-01TEST")
        self.assertEqual(woken.etat, "UNDER_TEST")
        self.assertEqual(woken.histoire[:-1], record.histoire)
        self.assertEqual(len(self.registry), 1)

    def test_wake_only_from_archived(self):
        with self.assertRaises(ValueError) as caught:
            self.registry.wake("H-01TEST", "réveil", ("obs:9",))
        self.assertIn("E_HYP_WAKE_NOT_ARCHIVED", str(caught.exception))

    # -- rule 4 ------------------------------------------------------------
    def test_merge_needs_equivalent_statements(self):
        self.registry.create(make_hypothesis(id="H-01OTHER", enonce="Tout autre énoncé."))
        with self.assertRaises(ValueError) as caught:
            self.registry.merge("H-01OTHER", "H-01TEST", "dédup", ("obs:3",))
        self.assertIn("E_HYP_MERGE_NOT_EQUIVALENT", str(caught.exception))

    def test_contradictory_records_never_merge(self):
        self.registry.create(make_hypothesis(
            id="H-01OTHER",
            relations=("CONTRADICTS:H-01TEST",)))
        with self.assertRaises(ValueError) as caught:
            self.registry.merge("H-01OTHER", "H-01TEST", "lissage", ("obs:3",))
        self.assertIn("E_HYP_MERGE_CONTRADICTION", str(caught.exception))

    def test_merge_keeps_the_trace_and_points_to_the_retained(self):
        self.registry.create(make_hypothesis(id="H-01DUP"))
        merged = self.registry.merge("H-01DUP", "H-01TEST", "dédup exacte", ("obs:3",))
        self.assertEqual(merged.etat, "MERGED_INTO")
        self.assertIn("MERGED_INTO:H-01TEST", merged.relations)   # pointer
        self.assertGreaterEqual(len(merged.histoire), 2)          # trace kept
        self.assertEqual(self.registry.get("H-01TEST").etat, "CREATED")

    # -- rule 5 ------------------------------------------------------------
    def test_archived_never_satisfies_a_mandatory_proof(self):
        self.assertTrue(self.registry.can_satisfy_proof("H-01TEST"))
        self.registry.archive("H-01TEST", "épisode clos", ("evt:close",))
        self.assertFalse(self.registry.can_satisfy_proof("H-01TEST"))


class JsonRoundTripTest(unittest.TestCase):
    """§a.3 JSON skeleton: keys exact, both proof lists mandatory."""

    def test_skeleton_keys_and_round_trip(self):
        record = make_hypothesis()
        data = record_to_dict(record)
        self.assertEqual(
            set(data),
            {"id", "case_id", "enonce", "criteres", "preuves_pour", "preuves_contre",
             "inconnues", "etat", "p", "p_gel_ref", "histoire", "provenance",
             "relations"})
        again = record_from_dict(data)
        self.assertEqual(record_to_dict(again), data)

    def test_a_proof_list_cannot_be_left_out(self):
        data = record_to_dict(make_hypothesis())
        del data["preuves_contre"]
        with self.assertRaises(ValueError) as caught:
            record_from_dict(data)
        self.assertIn("E_HYP_PROOF_LIST_MISSING", str(caught.exception))

    def test_jsonl_round_trip(self):
        registry = HypothesisRegistry()
        registry.create(make_hypothesis())
        registry.transition("H-01TEST", "UNDER_TEST", "évaluation", ("obs:1",))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "hypotheses.jsonl")
            registry.dump_jsonl(path)
            loaded = HypothesisRegistry.load_jsonl(path)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(record_to_dict(loaded.get("H-01TEST")),
                         record_to_dict(registry.get("H-01TEST")))


if __name__ == "__main__":
    unittest.main()
