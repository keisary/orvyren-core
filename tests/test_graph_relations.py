#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: 17-field relation record + conformance validator (ORVYREN-Core).

Covers B2_GRAPHE_ETUDE.md §3.0–§3.1: the record field groups (exactly 17) and
the rejection codes of :func:`validate_relation_record` — one code per golden
rule or closed enum. Every catalogue row is also proven constructible: a
conform record exists for each of the 34 kinds.

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sys
import unittest
from dataclasses import fields, replace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph.catalog import (  # noqa: E402
    FAMILY_PROOF,
    RELATION_CATALOG,
    NodeKind,
)
from orvyren.graph.record import (  # noqa: E402
    FIELD_GROUP_COUNT,
    RELATION_RECORD_FIELD_GROUPS,
    ChainRef,
    RelationRecord,
    record_as_dict,
    validate_relation_record,
)

#: Representative concrete kind for a subject/object token (the validator
#: matches tokens against kinds, so fixtures pick one concrete kind per token).
_REPRESENTATIVE = {
    "TOUT": NodeKind.SOCIETE,
    "ENTITE": NodeKind.SOCIETE,
    "SUJET": NodeKind.EOA,
    "CIBLE": NodeKind.POOL,
    "AUTORITE": NodeKind.DAO,
    "DROIT": NodeKind.PERMISSION,
    NodeKind.ORGANISATION: NodeKind.SOCIETE,
    NodeKind.ACTIF: NodeKind.STABLECOIN,
    NodeKind.CONTRAT: NodeKind.MARCHE,
    NodeKind.ADRESSE: NodeKind.EOA,
    NodeKind.PREUVE: NodeKind.CLAIM,
    NodeKind.DECISION: NodeKind.HYPOTHESE,
    NodeKind.GOUVERNANCE: NodeKind.ROLE,
}


def _rep(token: str) -> str:
    return _REPRESENTATIVE.get(token, token)


def make_record(kind: str, **overrides) -> RelationRecord:
    """A conform record for ``kind`` (B2 §3.2 row), then apply overrides."""
    spec = RELATION_CATALOG[kind]
    src_token = sorted(spec.subjects)[0]
    dst_token = sorted(spec.objects)[0]
    values = dict(
        relation_id=f"rel-{kind.lower()}",
        family=spec.family,
        kind=kind,
        src=f"node-a-{kind}",
        dst=f"node-b-{kind}",
        src_kind=_rep(src_token),
        dst_kind=_rep(dst_token),
        mechanism="LIQUIDITY",
        sign_prior="+",
        conditions="market_open",
        regime_scope="global",
        horizon_scope="1d",
        epistemic_status="STATISTICAL" if kind == "CORRELATES_WITH" else "FACT",
        lifecycle="ACTIVE",
        validation_status="VALIDATED",
        valid_from="2026-04-18T19:03:59+00:00",
        valid_to=None,
        revision=1,
        inserted_at="2026-04-18T19:05:00+00:00",
        superseded_by=None,
        provenance_refs=("obs-abc123",),
        source_family_id="SF-CHAIN-ARCHIVE",
        extract_method="RULE",
        model_version="",
        run_id="",
        chain_ref=ChainRef(chain_id=8453, block=24908723,
                           tx_hash="0x" + "ab" * 32) if kind == "MEMBER_OF" else None,
        confidence=0.8,
        payload={"note": "fixture"},
    )
    values.update(overrides)
    return RelationRecord(**values)


class RecordStructureTest(unittest.TestCase):
    """The record is exactly the 17 field groups of B2 §3.0."""

    def test_field_group_count_is_17(self):
        self.assertEqual(len(RELATION_RECORD_FIELD_GROUPS), FIELD_GROUP_COUNT)
        self.assertEqual(FIELD_GROUP_COUNT, 17)

    def test_field_groups_cover_the_dataclass(self):
        grouped = [name for group in RELATION_RECORD_FIELD_GROUPS for name in group]
        self.assertEqual(sorted(grouped), sorted(f.name for f in fields(RelationRecord)))
        self.assertEqual(len(grouped), len(set(grouped)), "a field appears twice")

    def test_record_as_dict_keeps_chain_ref_and_lists(self):
        record = make_record("MEMBER_OF")
        as_dict = record_as_dict(record)
        self.assertEqual(as_dict["chain_ref"]["block"], 24908723)
        self.assertEqual(as_dict["provenance_refs"], ["obs-abc123"])
        self.assertIsInstance(as_dict["payload"], dict)


class ConformanceTest(unittest.TestCase):
    """Every catalogue row is constructible and validates clean."""

    def test_every_kind_has_a_conform_record(self):
        for kind in RELATION_CATALOG:
            with self.subTest(kind=kind):
                errors = validate_relation_record(make_record(kind))
                self.assertEqual(errors, (), f"{kind} rejected: {errors}")

    def test_three_attributes_stay_independent(self):
        # An ACTIVE relation may remain hypothetical (B2 §3.0).
        record = make_record("AFFECTS", epistemic_status="CAUSAL-HYPOTHESIS",
                             lifecycle="ACTIVE", validation_status="VALIDATED")
        self.assertEqual(validate_relation_record(record), ())


class RejectionTest(unittest.TestCase):
    """One rejection code per golden rule / constraint (B2 §3.1–§3.2)."""

    def _assert_rejects(self, record, code):
        errors = validate_relation_record(record)
        self.assertIn(code, errors, f"expected {code}, got {errors}")

    def test_unknown_kind(self):
        record = replace(make_record("HOLDS"), kind="MINTS")
        self._assert_rejects(record, "E_KIND_UNKNOWN")

    def test_family_mismatch(self):
        self._assert_rejects(make_record("HOLDS", family=FAMILY_PROOF),
                             "E_FAMILY_MISMATCH")

    def test_unknown_endpoint_kinds(self):
        self._assert_rejects(make_record("HOLDS", src_kind="SPACESHIP"),
                             "E_SRC_KIND_UNKNOWN")
        self._assert_rejects(make_record("HOLDS", dst_kind="SPACESHIP"),
                             "E_DST_KIND_UNKNOWN")

    def test_disallowed_endpoint_kinds(self):
        # HOLDS: Adresse/Entité -> Actif ; a claim is neither.
        self._assert_rejects(make_record("HOLDS", src_kind=NodeKind.CLAIM),
                             "E_SRC_KIND_NOT_ALLOWED")
        self._assert_rejects(make_record("HOLDS", dst_kind=NodeKind.POOL),
                             "E_DST_KIND_NOT_ALLOWED")
        # SUPPORTS: Claim -> Hypothesis only.
        self._assert_rejects(make_record("SUPPORTS", src_kind=NodeKind.OBSERVATION),
                             "E_SRC_KIND_NOT_ALLOWED")
        self._assert_rejects(make_record("SUPPORTS", dst_kind=NodeKind.CLAIM),
                             "E_DST_KIND_NOT_ALLOWED")

    def test_supersedes_keeps_the_same_type(self):
        self._assert_rejects(
            make_record("SUPERSEDES", src_kind=NodeKind.SOCIETE, dst_kind=NodeKind.STABLECOIN),
            "E_SUPERSEDES_KIND_MISMATCH")

    def test_enum_fields_are_closed(self):
        self._assert_rejects(make_record("HOLDS", sign_prior="++"), "E_SIGN_PRIOR_UNKNOWN")
        self._assert_rejects(make_record("HOLDS", epistemic_status="TRUTH"),
                             "E_EPISTEMIC_STATUS_UNKNOWN")
        self._assert_rejects(make_record("HOLDS", lifecycle="DONE"), "E_LIFECYCLE_UNKNOWN")
        self._assert_rejects(make_record("HOLDS", validation_status="OK"),
                             "E_VALIDATION_STATUS_UNKNOWN")
        self._assert_rejects(make_record("HOLDS", extract_method="VIBES"),
                             "E_EXTRACT_METHOD_UNKNOWN")

    def test_llm_extraction_is_versioned(self):
        self._assert_rejects(make_record("HOLDS", extract_method="LLM_EXTRACT"),
                             "E_LLM_EXTRACT_UNVERSIONED")
        self.assertEqual(
            validate_relation_record(make_record(
                "HOLDS", extract_method="LLM_EXTRACT",
                model_version="mimo-v2.6-pro", run_id="run-42")), ())

    def test_mechanism_label_is_required(self):
        self._assert_rejects(make_record("HOLDS", mechanism=""), "E_MECHANISM_LABEL")
        self._assert_rejects(make_record("HOLDS", mechanism="liquidity"),
                             "E_MECHANISM_LABEL")

    def test_mechanism_family_needs_conditions_and_horizon(self):
        self._assert_rejects(make_record("AFFECTS", conditions=""),
                             "E_MECHANISM_CONDITIONS_MISSING")
        self._assert_rejects(make_record("DEPENDS_ON", horizon_scope=""),
                             "E_MECHANISM_HORIZON_MISSING")

    def test_correlation_is_statistical_only(self):
        self._assert_rejects(make_record("CORRELATES_WITH", epistemic_status="FACT"),
                             "E_CORRELATION_NOT_STATISTICAL")

    def test_quantity_needs_unit_and_date(self):
        self._assert_rejects(make_record("HOLDS", payload={"amount": 100}),
                             "E_QUANTITY_NO_UNIT")
        self._assert_rejects(make_record("HOLDS", payload={"amount": 100, "unit": "USDC"},
                                         valid_from=None),
                             "E_QUANTITY_NO_DATE")
        self.assertEqual(
            validate_relation_record(make_record(
                "HOLDS", payload={"amount": 100, "unit": "USDC",
                                  "as_of": "2026-04-18"})), ())

    def test_family4_needs_the_grant_proof(self):
        for kind in ("AUTHORIZES", "REVOKES", "MEMBER_OF", "ALLOWS"):
            with self.subTest(kind=kind):
                record = make_record(kind, provenance_refs=(), chain_ref=None)
                self._assert_rejects(record, "E_NO_GRANT_PROOF")

    def test_onchain_fact_needs_chain_ref(self):
        self._assert_rejects(make_record("MEMBER_OF", chain_ref=None,
                                         provenance_refs=("evt-1",)),
                             "E_ONCHAIN_NO_CHAIN_REF")

    def test_confidence_range(self):
        self._assert_rejects(make_record("HOLDS", confidence=1.5), "E_CONFIDENCE_RANGE")
        self._assert_rejects(make_record("HOLDS", confidence=-0.1), "E_CONFIDENCE_RANGE")

    def test_identity_and_system_time(self):
        self._assert_rejects(make_record("HOLDS", relation_id="  "), "E_RELATION_ID_EMPTY")
        self._assert_rejects(make_record("HOLDS", revision=0), "E_REVISION_RANGE")
        self._assert_rejects(make_record("HOLDS", inserted_at=""), "E_INSERTED_AT_EMPTY")
        self._assert_rejects(make_record("HOLDS", inserted_at="noon"),
                             "E_INSERTED_AT_UNPARSABLE")

    def test_clocks_are_parseable_and_ordered(self):
        self._assert_rejects(make_record("HOLDS", valid_from="18/04/2026"),
                             "E_VALID_FROM_UNPARSABLE")
        self._assert_rejects(make_record("HOLDS", valid_to="yesterday"),
                             "E_VALID_TO_UNPARSABLE")
        self._assert_rejects(
            make_record("HOLDS", valid_from="2026-04-18T18:00:00+00:00",
                        valid_to="2026-04-18T17:00:00+00:00"),
            "E_VALIDITY_ORDER")
        # An empty interval never contains any T: refused as well.
        self._assert_rejects(
            make_record("HOLDS", valid_from="2026-04-18T17:00:00+00:00",
                        valid_to="2026-04-18T17:00:00+00:00"),
            "E_VALIDITY_ORDER")
        self.assertEqual(
            validate_relation_record(make_record(
                "HOLDS", valid_from="2026-04-18T17:00:00+00:00",
                valid_to="2026-04-18T18:00:00+00:00")), ())

    def test_symmetric_pairs_are_canonical(self):
        # Contradiction between two claims: stored once per unordered pair.
        self._assert_rejects(make_record("CONTRADICTS", src="claim-b", dst="claim-a"),
                             "E_SYMMETRIC_ORDER")
        self.assertEqual(
            validate_relation_record(make_record("CONTRADICTS",
                                                 src="claim-a", dst="claim-b")), ())


if __name__ == "__main__":
    unittest.main()
