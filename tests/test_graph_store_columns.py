#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: store retroactive columns (lot L1.3, DOC4 W1).

``source_family_id`` and ``extract_method`` (B2 §3.0 fields 13–14) must be
persisted on every relation, read back unchanged, and older database files
must be migrated additively on open. A non-empty ``extract_method`` uses the
closed vocabulary of the catalogue.

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph.models import Relation  # noqa: E402
from orvyren.graph.store import SCHEMA_VERSION, GraphStore  # noqa: E402

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


class RetroactiveColumnsTest(unittest.TestCase):
    """L1.3: the two columns travel with every relation."""

    def test_columns_are_persisted_and_read_back(self):
        with GraphStore(":memory:") as store:
            store.insert_relation(Relation(
                id="rel-1", src="usdc", dst="aave_v3", kind="DEPOSITED_IN",
                source_family_id="SF-CHAIN-ARCHIVE", extract_method="ONCHAIN_READ"))
            relation = store.relation_by_id("rel-1")
            self.assertEqual(relation.source_family_id, "SF-CHAIN-ARCHIVE")
            self.assertEqual(relation.extract_method, "ONCHAIN_READ")

    def test_legacy_relation_defaults_are_empty(self):
        with GraphStore(":memory:") as store:
            store.insert_relation(Relation(id="rel-2", src="a", dst="b",
                                           kind="SUPPORTS"))
            relation = store.relation_by_id("rel-2")
            self.assertEqual(relation.source_family_id, "")
            self.assertEqual(relation.extract_method, "")

    def test_extract_method_vocabulary_is_closed(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError) as caught:
                store.insert_relation(Relation(
                    id="rel-3", src="a", dst="b", kind="SUPPORTS",
                    extract_method="VIBES"))
            self.assertIn("unknown extract_method", str(caught.exception))
            for method in ("RULE", "ONCHAIN_READ", "LLM_EXTRACT", "HUMAN"):
                store.insert_relation(Relation(
                    id="rel-3-%s" % method, src="a", dst="b", kind="SUPPORTS",
                    extract_method=method))

    def test_legacy_database_is_migrated_on_open(self):
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
                old = store.relation_by_id("rel-old")
                self.assertEqual(old.source_family_id, "")  # migrated default
                self.assertEqual(old.extract_method, "")
                store.insert_relation(Relation(
                    id="rel-new", src="x", dst="z", kind="OWES",
                    source_family_id="SF-CORPUS", extract_method="RULE"))
                self.assertEqual(store.relation_by_id("rel-new").source_family_id,
                                 "SF-CORPUS")

    def test_snapshot_rows_carry_the_columns(self):
        with GraphStore(":memory:") as store:
            store.insert_relation(Relation(
                id="rel-4", src="a", dst="b", kind="SUPPORTS",
                source_family_id="SF-1", extract_method="HUMAN"))
            rows = store._current_rows()
            relation_rows = [row for row in rows if row["_table"] == "relations"]
            self.assertEqual(relation_rows[0]["source_family_id"], "SF-1")
            self.assertEqual(relation_rows[0]["extract_method"], "HUMAN")

    def test_schema_version_is_3(self):
        self.assertEqual(SCHEMA_VERSION, 3)


if __name__ == "__main__":
    unittest.main()
