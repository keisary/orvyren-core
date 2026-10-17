#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Graph v2 schema tests: full 17-field relation record, nodes, events, PIT-ish.

These tests exercise the additive schema v3 on top of the legacy store. They
do not touch the network and do not change the frozen evaluation modules.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph.queries import load_fixture_records  # noqa: E402
from orvyren.graph.record import RelationRecord  # noqa: E402
from orvyren.graph.store import SCHEMA_VERSION, GraphStore  # noqa: E402


def _holds_record(relation_id="rel-holds-1", **overrides):
    data = dict(
        relation_id=relation_id,
        family="STRUCTURE_EXPOSURE",
        kind="HOLDS",
        src="addr:eip155:8453:0x00000000000000000000000000000000000000aa",
        dst="asset:eip155:8453:0x00000000000000000000000000000000000000bb",
        src_kind="ADRESSE",
        dst_kind="STABLECOIN",
        mechanism="CUSTODY",
        sign_prior="+",
        conditions="",
        regime_scope="",
        horizon_scope="",
        epistemic_status="FACT",
        lifecycle="ACTIVE",
        validation_status="VALIDATED",
        valid_from="2026-01-01T00:00:00+00:00",
        valid_to=None,
        revision=1,
        inserted_at="2026-10-17T00:00:00+00:00",
        provenance_refs=("obs:abcdef0123456789",),
        source_family_id="SF-BASE-RPC",
        extract_method="ONCHAIN_READ",
        confidence=0.9,
        payload={"amount": 100.0, "unit": "USDC",
                 "as_of": "2026-01-01T00:00:00+00:00"},
    )
    data.update(overrides)
    return RelationRecord(**data)


_LEGACY_SCHEMA = """
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE sources (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
    revision INTEGER NOT NULL, name TEXT NOT NULL, endpoint TEXT NOT NULL,
    retrieved_at TEXT NOT NULL, limits TEXT NOT NULL, inserted_at TEXT NOT NULL);
CREATE TABLE observations (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, observation_id TEXT NOT NULL,
    revision INTEGER NOT NULL, venue TEXT NOT NULL, metric TEXT NOT NULL,
    ts_event TEXT NOT NULL, value REAL NOT NULL, extra TEXT NOT NULL,
    retrieved_at TEXT NOT NULL, source_id TEXT NOT NULL, inserted_at TEXT NOT NULL);
CREATE TABLE claims (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, claim_id TEXT NOT NULL,
    revision INTEGER NOT NULL, text TEXT NOT NULL, refs TEXT NOT NULL,
    created_at TEXT NOT NULL, fingerprint TEXT NOT NULL, inserted_at TEXT NOT NULL);
CREATE TABLE relations (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, relation_id TEXT NOT NULL,
    revision INTEGER NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL,
    kind TEXT NOT NULL, inserted_at TEXT NOT NULL);
CREATE TABLE hypotheses (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id TEXT NOT NULL,
    revision INTEGER NOT NULL, statement TEXT NOT NULL, state TEXT NOT NULL,
    criteria_support TEXT NOT NULL, criteria_refute TEXT NOT NULL,
    inserted_at TEXT NOT NULL);
CREATE TABLE decision_nodes (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT NOT NULL,
    revision INTEGER NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
    refs TEXT NOT NULL, inserted_at TEXT NOT NULL);
"""


class GraphV2SchemaTest(unittest.TestCase):
    def test_v2_tables_exist(self):
        with GraphStore(":memory:") as store:
            names = {row[0] for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for table in ("nodes", "node_aliases", "events", "event_observations",
                          "relation_provenance", "source_families",
                          "ingestion_watermarks", "graph_snapshots"):
                self.assertIn(table, names)

    def test_full_record_roundtrip_and_nodes(self):
        with GraphStore(":memory:") as store:
            store.insert_relation_record(_holds_record())
            record = store.relation_record_by_id("rel-holds-1")
            self.assertIsNotNone(record)
            self.assertEqual(record.family, "STRUCTURE_EXPOSURE")
            self.assertEqual(record.src_kind, "ADRESSE")
            self.assertEqual(record.dst_kind, "STABLECOIN")
            self.assertEqual(record.mechanism, "CUSTODY")
            self.assertEqual(record.epistemic_status, "FACT")
            self.assertEqual(record.lifecycle, "ACTIVE")
            self.assertEqual(record.validation_status, "VALIDATED")
            self.assertEqual(record.payload["unit"], "USDC")
            self.assertEqual(record.provenance_refs, ("obs:abcdef0123456789",))
            self.assertIsNotNone(store.node_by_id(record.src))
            self.assertIsNotNone(store.node_by_id(record.dst))
            self.assertEqual(store.graph_counts()["relations"], 1)
            self.assertEqual(store.graph_counts()["nodes"], 2)

    def test_provenance_rows_are_written(self):
        with GraphStore(":memory:") as store:
            store.insert_relation_record(_holds_record())
            rows = [tuple(row) for row in store.connection.execute(
                "SELECT ref_id, ref_kind, source_family_id FROM relation_provenance")]
            self.assertEqual(rows, [("obs:abcdef0123456789", "OBSERVATION", "SF-BASE-RPC")])

    def test_block_bounds_are_first_class_and_persisted(self):
        with GraphStore(":memory:") as store:
            store.insert_relation_record(_holds_record(
                valid_from_block=100, valid_to_block=200))
            record = store.relation_record_by_id("rel-holds-1")
            self.assertEqual(record.valid_from_block, 100)
            self.assertEqual(record.valid_to_block, 200)
            row = store.connection.execute(
                "SELECT valid_from_block, valid_to_block, finality FROM relations "
                "WHERE relation_id='rel-holds-1'").fetchone()
            self.assertEqual(row["valid_from_block"], 100)
            self.assertEqual(row["valid_to_block"], 200)
            self.assertEqual(row["finality"], "PENDING")

    def test_invalid_block_bounds_are_rejected(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(_holds_record(
                    valid_from_block=200, valid_to_block=100))
            self.assertIn("E_BLOCK_ORDER", str(caught.exception))

    def test_storage_guardrails_refuse_invalid_direct_writes(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(sqlite3.IntegrityError):
                store.connection.execute(
                    "INSERT INTO relations (relation_id, revision, kind, src, dst, "
                    "epistemic_status, sign_prior, inserted_at) "
                    "VALUES ('bad','1','CORRELATES_WITH','a','b','FACT','ambigu','x')")
            with self.assertRaises(sqlite3.IntegrityError):
                store.connection.execute(
                    "INSERT INTO relations (relation_id, revision, kind, src, dst, "
                    "epistemic_status, sign_prior, inserted_at) "
                    "VALUES ('bad2','1','DEPENDS_ON','a','b','FACT','ambigu','x')")

    def test_propagation_views_exist(self):
        with GraphStore(":memory:") as store:
            views = {row[0] for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='view'")}
            self.assertIn("prop_edge", views)
            self.assertIn("prop_step", views)

    def test_invalid_record_is_rejected(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(_holds_record(family="PROOF_DERIVATION"))
            self.assertIn("E_FAMILY_MISMATCH", str(caught.exception))

    def test_quantity_without_unit_is_rejected(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation_record(_holds_record(
                    payload={"amount": 100.0,
                             "as_of": "2026-01-01T00:00:00+00:00"}))
            self.assertIn("E_QUANTITY_NO_UNIT", str(caught.exception))

    def test_node_revision_is_append_only(self):
        with GraphStore(":memory:") as store:
            store.insert_node("addr:eip155:8453:0xabc", "ADRESSE", label="treasury")
            store.insert_node("addr:eip155:8453:0xabc", "ADRESSE", label="treasury-v2")
            node = store.node_by_id("addr:eip155:8453:0xabc")
            self.assertEqual(node["revision"], 2)
            self.assertEqual(node["label"], "treasury-v2")
            with self.assertRaises(sqlite3.DatabaseError):
                store.connection.execute(
                    "UPDATE nodes SET label='x' WHERE node_id=?",
                    ("addr:eip155:8453:0xabc",))

    def test_event_roundtrip(self):
        with GraphStore(":memory:") as store:
            store.insert_event({
                "event_id": "event:eip155:8453:0xdead:3",
                "event_type": "SUPPLY",
                "chain_id": 8453,
                "block_number": 123,
                "tx_hash": "0xdead",
                "log_index": 3,
                "event_time": "2026-01-01T00:00:00+00:00",
                "observation_time": "2026-01-01T00:00:01+00:00",
                "actors": ["0xuser"],
                "targets": ["0xpool"],
                "actual": 100.0,
                "payload": {"reserve": "0xusdc"},
            })
            event = store.event_by_id("event:eip155:8453:0xdead:3")
            self.assertEqual(event["event_type"], "SUPPLY")
            self.assertEqual(event["block_number"], 123)
            self.assertIn("0xuser", event["actors"])

    def test_watermark_upsert(self):
        with GraphStore(":memory:") as store:
            store.set_watermark("base-aave", 100, "0xhash", "2026-10-17T00:00:00+00:00")
            store.set_watermark("base-aave", 200, "0xhash2", "2026-10-17T00:01:00+00:00")
            row = store.connection.execute(
                "SELECT last_block, last_block_hash FROM ingestion_watermarks "
                "WHERE source_id='base-aave'").fetchone()
            self.assertEqual(row["last_block"], 200)
            self.assertEqual(row["last_block_hash"], "0xhash2")

    def test_snapshot_reference_is_recorded(self):
        with GraphStore(":memory:") as store:
            store.insert_relation_record(_holds_record())
            store.record_graph_snapshot("snap-1", as_of="2026-10-17T00:00:00+00:00",
                                        as_of_block=123)
            row = store.connection.execute(
                "SELECT graph_hash, counts FROM graph_snapshots WHERE snapshot_id='snap-1'"
            ).fetchone()
            self.assertTrue(row["graph_hash"])
            self.assertIn('"relations": 1', row["counts"])

    def test_snapshot_v2_is_stable_and_includes_world_layer(self):
        with GraphStore(":memory:") as store:
            store.insert_relation_record(_holds_record())
            store.insert_event({
                "event_id": "event:eip155:8453:0xdead:1",
                "event_type": "SUPPLY",
                "observation_time": "2026-10-17T00:00:00+00:00",
            })
            first = store.snapshot_v2()
            second = store.snapshot_v2()
            self.assertEqual(first["hash"], second["hash"])
            self.assertEqual(first["counts"]["nodes"], 2)
            self.assertEqual(first["counts"]["events"], 1)

    def test_fixture_records_are_accepted(self):
        graphs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "fixtures", "graphs")
        with GraphStore(":memory:") as store:
            total = 0
            for name in ("usdc_2023-03", "steth_2022-06", "rseth_2026-04"):
                for record in load_fixture_records(os.path.join(graphs_dir, "%s.json" % name)):
                    store.insert_relation_record(record)
                    total += 1
            self.assertEqual(total, 20)
            self.assertEqual(store.graph_counts()["relations"], 20)

    def test_legacy_database_is_migrated_to_v3(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.sqlite")
            connection = sqlite3.connect(path)
            connection.executescript(_LEGACY_SCHEMA)
            connection.execute(
                "INSERT INTO relations (relation_id, revision, src, dst, kind, "
                "inserted_at) VALUES ('rel-old', 1, 'x', 'y', 'HOLDS', "
                "'2026-10-14T12:00:00+00:00')")
            connection.commit()
            connection.close()

            with GraphStore(path) as store:
                columns = {row["name"] for row in store.connection.execute(
                    "PRAGMA table_info(relations)")}
                for column in ("family", "src_kind", "epistemic_status",
                               "valid_from", "payload", "confidence"):
                    self.assertIn(column, columns)
                version = store.connection.execute(
                    "SELECT MAX(version) FROM schema_version").fetchone()[0]
                self.assertEqual(version, SCHEMA_VERSION)
                store.insert_relation_record(_holds_record("rel-new"))
                self.assertIsNotNone(store.relation_record_by_id("rel-new"))


if __name__ == "__main__":
    unittest.main()
