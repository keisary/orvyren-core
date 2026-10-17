#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Review tests (2026-10-17, revue src/orvyren/graph/).

Locks the fixes of the review: the G5 guardrail contract (a propagatable edge
needs a sign — callers get ``ValueError``/``E_*``, never a leaked
``sqlite3.IntegrityError``), the G2 writer-boundary parity, atomic appends
(no partial write survives a refused insert), block-native PIT bounds in Q8,
timezone-stable fingerprints and current-revision reads in the SQL API.

Execution: ``python -m pytest tests/test_graph_review.py -q``.
"""

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))
sys.path.insert(0, _HERE)

from test_graph_relations import make_record  # noqa: E402
from orvyren.graph import api  # noqa: E402
from orvyren.graph.models import Relation, fingerprint  # noqa: E402
from orvyren.graph.queries import q8_permission_state  # noqa: E402
from orvyren.graph.record import record_from_dict, validate_relation_record  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402


class G5GuardrailContractTest(unittest.TestCase):
    """Piste G5: 'a propagatable edge needs a sign' — clean contract, all paths."""

    def test_validation_refuses_an_ambiguous_propagation_sign(self):
        for kind in ("DEPENDS_ON", "AFFECTS"):
            with self.subTest(kind=kind):
                record = make_record(kind, sign_prior="ambigu")
                self.assertIn("E_DEPENDENCY_SIGN_AMBIGUOUS",
                              validate_relation_record(record))

    def test_insert_raises_value_error_not_integrity_error(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(make_record("DEPENDS_ON",
                                                         sign_prior="ambigu"))
            self.assertIn("E_DEPENDENCY_SIGN_AMBIGUOUS", str(caught.exception))
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(make_record("AFFECTS",
                                                         sign_prior="ambigu"))
            self.assertIn("E_DEPENDENCY_SIGN_AMBIGUOUS", str(caught.exception))

    def test_signed_propagation_edges_still_insert(self):
        with GraphStore(":memory:") as store:
            for sign in ("+", "-"):
                row = store.insert_relation_record(
                    make_record("DEPENDS_ON", sign_prior=sign,
                                relation_id="rel-dep-%s" % sign))
                self.assertGreater(row, 0)

    def test_engine_backstop_still_refuses_direct_writes(self):
        # The SQL trigger remains the guard for writers that bypass Python.
        with GraphStore(":memory:") as store:
            with self.assertRaises(sqlite3.IntegrityError):
                store.connection.execute(
                    "INSERT INTO relations (relation_id, revision, kind, src, dst, "
                    "epistemic_status, sign_prior, inserted_at) "
                    "VALUES ('bad', 1, 'DEPENDS_ON', 'a', 'b', 'FACT', 'ambigu', 'x')")


class G2WriterParityTest(unittest.TestCase):
    """G2 (CORRELATES_WITH requires 'ambigu') is engine-only: the catalogue
    validator accepts any sign (test contract), so the writer boundary must
    translate the trigger into the documented ValueError/E_* contract."""

    def test_validator_still_accepts_a_signed_correlation(self):
        record = make_record("CORRELATES_WITH", sign_prior="+",
                             src="node-a", dst="node-b")
        self.assertEqual(validate_relation_record(record), ())

    def test_writer_refuses_a_signed_correlation_with_a_code(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(make_record(
                    "CORRELATES_WITH", sign_prior="+", src="node-a", dst="node-b"))
            self.assertIn("E_CORRELATION_SIGN_NOT_AMBIGUOUS", str(caught.exception))

    def test_ambiguous_correlation_inserts(self):
        with GraphStore(":memory:") as store:
            row = store.insert_relation_record(make_record(
                "CORRELATES_WITH", sign_prior="ambigu", src="node-a", dst="node-b"))
            self.assertGreater(row, 0)


class AtomicAppendTest(unittest.TestCase):
    """A refused insert leaves nothing behind — not even the helper nodes."""

    def test_failed_insert_leaks_no_partial_write(self):
        with GraphStore(":memory:") as store:
            bad = make_record("HOLDS", relation_id="rel-bad",
                              src="node:leak-src", dst="node:leak-dst",
                              payload={"log_index": object()})  # unbindable
            with self.assertRaises(sqlite3.Error):
                store.insert_relation_record(bad)
            # A later successful write commits its own transaction only.
            store.insert_relation_record(make_record("HOLDS", relation_id="rel-ok"))
            self.assertIsNone(store.node_by_id("node:leak-src"))
            self.assertIsNone(store.node_by_id("node:leak-dst"))
            self.assertIsNone(store.relation_record_by_id("rel-bad"))

    def test_legacy_writer_refuses_guardrail_kinds(self):
        with GraphStore(":memory:") as store:
            for kind in ("DEPENDS_ON", "AFFECTS", "CORRELATES_WITH"):
                with self.subTest(kind=kind):
                    with self.assertRaises(ValueError) as caught:
                        store.insert_relation(Relation(
                            id="rel-%s" % kind, src="a", dst="b", kind=kind))
                    self.assertIn("insert_relation_record", str(caught.exception))


class PitBlockBoundsTest(unittest.TestCase):
    """Q8 must honour the block-native PIT bounds (field 11b), like the API."""

    @staticmethod
    def _member(relation_id="rel-member"):
        return record_from_dict({
            "relation_id": relation_id, "family": "CONSTRAINT_PERMISSION",
            "kind": "MEMBER_OF", "src": "agent:0xe1", "dst": "role:AGENT",
            "src_kind": "ADRESSE", "dst_kind": "ROLE", "mechanism": "GOVERNANCE",
            "sign_prior": "+", "conditions": "measured", "regime_scope": "global",
            "horizon_scope": "episode", "epistemic_status": "FACT",
            "lifecycle": "ACTIVE", "validation_status": "VALIDATED",
            "valid_from": None, "valid_to": None,
            "valid_from_block": 100, "valid_to_block": 200,
            "inserted_at": "2026-10-17T00:00:00+00:00",
        })

    def test_half_open_block_interval(self):
        record = self._member()
        self.assertEqual(q8_permission_state((record,), "agent:0xe1",
                                             as_of_block=50)["roles"], [])
        self.assertEqual(len(q8_permission_state((record,), "agent:0xe1",
                                                 as_of_block=100)["roles"]), 1)
        self.assertEqual(len(q8_permission_state((record,), "agent:0xe1",
                                                 as_of_block=199)["roles"]), 1)
        self.assertEqual(q8_permission_state((record,), "agent:0xe1",
                                             as_of_block=200)["roles"], [])


class TimezoneStableFingerprintTest(unittest.TestCase):

    def test_naive_datetime_is_serialised_as_utc(self):
        # Project convention (record.parse_ts): naive = UTC. Without the fix
        # the fingerprint depended on the host timezone.
        self.assertEqual(fingerprint({"t": datetime(2026, 1, 1)}),
                         fingerprint({"t": "2026-01-01T00:00:00+00:00"}))
        shifted = datetime(2026, 1, 1, 2, 0, 0,
                           tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(fingerprint({"t": shifted}),
                         fingerprint({"t": "2026-01-01T00:00:00+00:00"}))


class CurrentRevisionReadsTest(unittest.TestCase):
    """The SQL API reads the current revision only (store design rule)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")
        holder = "addr:eip155:8453:0x00000000000000000000000000000000000000aa"
        asset = "asset:eip155:8453:0x00000000000000000000000000000000000000bb"
        with GraphStore(self.db) as store:
            for revision_amount in (10.0, 20.0):
                store.insert_relation_record(make_record(
                    "HOLDS", relation_id="rel-holds", src=holder, dst=asset,
                    payload={"amount": revision_amount, "unit": "USDC",
                             "as_of": "2026-01-01T00:00:00+00:00"},
                    valid_from_block=100))

    def tearDown(self):
        self.tmp.cleanup()

    def test_exposure_counts_the_current_revision_once(self):
        result = api.exposure(self.db,
                              "addr:eip155:8453:0x00000000000000000000000000000000000000aa")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["rows"][0]["amount"], 20.0)

    def test_pit_counts_the_current_revision_once(self):
        result = api.pit(self.db)
        self.assertEqual(result["count"], 1)

    def test_snapshot_slice_is_current_and_pit_filtered(self):
        current = api.snapshot(self.db)
        self.assertEqual(current["counts"]["relations"], 1)
        early = api.snapshot(self.db, as_of_block=50)   # before valid_from_block
        self.assertEqual(early["counts"]["relations"], 0)
        self.assertNotEqual(current["graph_hash"], early["graph_hash"])


if __name__ == "__main__":
    unittest.main()
