#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for the two temporal defects of the 2026-10-18 review.

1. **Q5 must be point-in-time on both clocks.** ``api.timeline`` filtered
   ``as_of`` on ``event_time`` only, so a datum observed after the decision
   moment was admissible. An event is now admitted only when it is observable
   at ``as_of`` (``observation_time``) *and* dated at or before it
   (``event_time``).
2. **Timestamps compare as aware UTC instants, never as text.** Stored
   offsets are heterogeneous (``Z``, ``+02:00``, ``-05:00``): the world clock,
   the knowledge clock and the ``as_of`` bounds are all parsed to aware UTC
   datetimes (``datetime.fromisoformat(value.replace('Z', '+00:00'))``) before
   any comparison — in the pure queries (Q5 window and ordering), in the
   temporal layer, and in every SQL query (Q1/Q2/Q4/Q5/Q7/Q8/snapshot).

Also pinned: a relation revision published after ``as_of`` is never visible
at ``as_of`` (INV-PIT), and the Q1/Q2 SQL parameters bind each clock to its
own column when ``as_of`` and ``as_of_block`` are combined.

Execution: ``python -m unittest tests.test_graph_pit_fixes -v``
"""

import os
import sqlite3
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))
sys.path.insert(0, _HERE)

from test_graph_relations import make_record  # noqa: E402
from orvyren.graph import api  # noqa: E402
from orvyren.graph.queries import q5_episode_timeline  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402
from orvyren.graph.temporal import covers, pit_at  # noqa: E402

#: The replayed decision moment (rsETH episode: 2026-04-18 17:35 UTC).
T = "2026-04-18T17:35:00Z"

#: The additive PIT indexes (perf-only, ``CREATE INDEX IF NOT EXISTS``).
PIT_INDEXES = (
    "idx_events_evt_time", "idx_events_obs_time",
    "idx_events_time_jd", "idx_events_obs_jd",
    "idx_events_block_log", "idx_rel_block_valid",
)

#: Q5's read shape (``orvyren.graph.api.timeline``) verbatim.
_Q5_SHAPE = (
    "SELECT event_id, event_type FROM events WHERE "
    "(event_time IS NULL OR julianday(event_time) <= julianday(?)) "
    "AND (block_number IS NULL OR block_number <= ?) "
    "AND (observation_time IS NULL OR julianday(observation_time) <= julianday(?)) "
    "ORDER BY block_number DESC, log_index DESC LIMIT ?")

#: Q5's PIT filter without the ordering tail (the filter itself must not
#: degrade to a bare scan when no LIMIT-driven plan wins).
_Q5_FILTER_SHAPE = (
    "SELECT event_id FROM events WHERE "
    "(event_time IS NULL OR julianday(event_time) <= julianday(?)) "
    "AND (observation_time IS NULL OR julianday(observation_time) <= julianday(?))")

#: Q4's block-validity bounds (``_validity`` + ``_active``) verbatim.
_Q4_BLOCK_SHAPE = (
    "SELECT r.relation_id FROM relations r WHERE "
    "r.lifecycle = 'ACTIVE' AND r.validation_status = 'VALIDATED' "
    "AND (r.valid_from_block IS NULL OR r.valid_from_block <= ?) "
    "AND (r.valid_to_block IS NULL OR r.valid_to_block > ?)")


def _event(event_id, block, log_index, event_time, observation_time):
    return {
        "event_id": event_id, "event_type": "SUPPLY", "chain_id": 8453,
        "block_number": block, "tx_hash": "0x" + "ab" * 8, "log_index": log_index,
        "event_time": event_time, "observation_time": observation_time,
        "actors": [], "targets": [], "status": "CONFIRMED",
    }


class Q5ObservationTimePitTest(unittest.TestCase):
    """Q5 (``api.timeline``): admissible = observable at ``as_of`` AND event
    dated at or before ``as_of`` (review P1-2)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")
        with GraphStore(self.db) as store:
            # Both clocks before ``as_of``, in mixed offsets -> admissible at T.
            store.insert_event(_event(
                "ev-offset", 4, 1,
                "2026-04-18T19:00:00+02:00",      # 17:00Z
                "2026-04-18T12:10:00-05:00"))     # 17:10Z
            store.insert_event(_event(
                "ev-known", 3, 1,
                "2026-04-18T17:00:00+00:00",
                "2026-04-18T17:05:00+00:00"))
            # Event before T but observed after T -> not admissible at T.
            store.insert_event(_event(
                "ev-observed-late", 2, 1,
                "2026-04-18T17:10:00+00:00",
                "2026-04-18T21:00:00+02:00"))     # 19:00Z
            # Observed before its own event but the event is after T -> out.
            store.insert_event(_event(
                "ev-event-future", 1, 1,
                "2026-04-18T18:00:00+00:00",
                "2026-04-18T18:05:00+00:00"))

    def tearDown(self):
        self.tmp.cleanup()

    def _ids(self, result):
        return [row["event_id"] for row in result["rows"]]

    def test_observation_after_as_of_is_not_admissible(self):
        result = api.timeline(self.db, as_of=T)
        self.assertEqual(self._ids(result), ["ev-offset", "ev-known"])
        self.assertNotIn("ev-observed-late", self._ids(result))

    def test_observation_after_as_of_is_admissible_later(self):
        result = api.timeline(self.db, as_of="2026-04-18T20:00:00+00:00")
        self.assertEqual(self._ids(result),
                         ["ev-offset", "ev-known",
                          "ev-observed-late", "ev-event-future"])

    def test_event_time_after_as_of_is_not_admissible(self):
        result = api.timeline(self.db, as_of=T)
        self.assertNotIn("ev-event-future", self._ids(result))

    def test_mixed_offsets_compare_as_instants(self):
        # ev-offset reads '19:00+02:00' > '17:35Z' as text: a lexicographic
        # filter would drop an event that is one hour *older* than ``as_of``.
        result = api.timeline(self.db, as_of=T)
        self.assertIn("ev-offset", self._ids(result))

    def test_as_of_block_still_filters_on_the_block(self):
        result = api.timeline(self.db, as_of=T, as_of_block=3)
        self.assertEqual(self._ids(result), ["ev-known"])


class RevisionPublishedAfterAsOfTest(unittest.TestCase):
    """INV-PIT: a revision published after ``as_of`` never leaks into it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_later_revision_is_invisible_before_its_publication(self):
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-rev", dst="node-b-holds",
                valid_from="2026-04-18T17:00:00+00:00",
                inserted_at="2026-04-18T17:10:00+00:00"))
            # Published at 19:00Z, written with a non-UTC offset.
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-rev", dst="node-b-holds-v2",
                valid_from="2026-04-18T17:00:00+00:00",
                inserted_at="2026-04-18T21:00:00+02:00"))
        past = api.pit(self.db, as_of=T)
        self.assertEqual([row["dst"] for row in past["rows"]], ["node-b-holds"])
        later = api.pit(self.db, as_of="2026-04-18T20:00:00+00:00")
        self.assertEqual([row["dst"] for row in later["rows"]],
                         ["node-b-holds-v2"])

    def test_pit_at_excludes_a_revision_published_after_as_of(self):
        records = (
            make_record("HOLDS", relation_id="r", revision=1,
                        valid_from=None, valid_to=None,
                        inserted_at="2026-04-18T17:10:00+00:00"),
            make_record("HOLDS", relation_id="r", revision=2,
                        valid_from=None, valid_to=None,
                        inserted_at="2026-04-18T21:00:00+02:00"),  # 19:00Z
        )
        self.assertEqual(
            [(r.relation_id, r.revision) for r in pit_at(records, T)],
            [("r", 1)])


class SqlInstantComparisonTest(unittest.TestCase):
    """Q1/Q2/Q4 validity clauses compare aware UTC instants, not text."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_from_with_east_offset_is_visible(self):
        # valid_from 10:00+02:00 = 08:00Z: world-valid at 08:30Z, although
        # '10:00+02:00' sorts after '08:30Z' as text.
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-east",
                valid_from="2026-01-01T10:00:00+02:00",
                valid_to="2026-01-01T12:00:00+02:00",
                inserted_at="2026-01-01T07:50:00+00:00"))
        result = api.pit(self.db, as_of="2026-01-01T08:30:00Z")
        self.assertEqual([row["relation_id"] for row in result["rows"]],
                         ["rel-east"])

    def test_valid_to_with_west_offset_keeps_the_record_valid(self):
        # valid_to 07:00-02:00 = 09:00Z: still world-valid at 08:30Z, although
        # '07:00-02:00' sorts before '08:30Z' as text.
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-west",
                valid_from="2026-01-01T00:00:00+00:00",
                valid_to="2026-01-01T07:00:00-02:00",
                inserted_at="2026-01-01T00:00:00+00:00"))
        result = api.pit(self.db, as_of="2026-01-01T08:30:00Z")
        self.assertEqual([row["relation_id"] for row in result["rows"]],
                         ["rel-west"])

    def test_as_of_offset_is_normalised_to_utc(self):
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-open",
                valid_from="2026-01-01T08:00:00+00:00",
                valid_to="2026-01-01T10:00:00+00:00",
                inserted_at="2026-01-01T08:00:00+00:00"))
        # 10:30+02:00 = 08:30Z: inside. 02:30-05:00 = 07:30Z: before valid_from.
        self.assertEqual(
            api.pit(self.db, as_of="2026-01-01T10:30:00+02:00")["count"], 1)
        self.assertEqual(
            api.pit(self.db, as_of="2026-01-01T02:30:00-05:00")["count"], 0)

    def test_q1_binds_clock_and_block_params_to_their_own_columns(self):
        # Regression: with ``as_of`` and ``as_of_block`` combined, Q1 bound the
        # validity parameters in the wrong order, comparing ``valid_to_block``
        # against the timestamp — a record with a closed block bound was
        # silently dropped.
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-q1", src="addr:eip155:8453:0xaa",
                valid_from="2026-01-01T10:00:00+02:00",
                valid_to="2026-01-01T12:00:00+02:00",
                valid_from_block=50, valid_to_block=150,
                inserted_at="2026-01-01T07:50:00+00:00"))
        result = api.exposure(self.db, "addr:eip155:8453:0xaa",
                              as_of="2026-01-01T08:30:00Z", as_of_block=100)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["rows"][0]["asset"], "node-b-HOLDS")

    def test_q2_binds_clock_and_block_params_to_their_own_columns(self):
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "DEPENDS_ON", relation_id="rel-q2", src="node:x", dst="node:y",
                valid_from="2026-01-01T10:00:00+02:00",
                valid_to="2026-01-01T12:00:00+02:00",
                valid_from_block=50, valid_to_block=150,
                inserted_at="2026-01-01T07:50:00+00:00"))
        result = api.dependency_paths(
            self.db, "node:x", "node:y",
            as_of="2026-01-01T08:30:00Z", as_of_block=100, max_depth=2)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["count"], 1)

    def test_q1_rejects_a_future_as_of_with_mixed_offsets(self):
        with GraphStore(self.db) as store:
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-east", src="addr:eip155:8453:0xaa",
                valid_from="2026-01-01T10:00:00+02:00",
                inserted_at="2026-01-01T07:50:00+00:00"))
        result = api.exposure(self.db, "addr:eip155:8453:0xaa",
                              as_of="2026-01-01T09:30:00+02:00")  # 07:30Z
        self.assertEqual(result["count"], 0)


class EpisodeTimelineInstantComparisonTest(unittest.TestCase):
    """Q5 (``q5_episode_timeline``): window bounds and ordering are instants."""

    def test_window_compares_instants_across_offsets(self):
        records = (
            # 10:00Z, inside [09:00Z, 10:30Z) despite the '+02:00' text.
            make_record("HOLDS", relation_id="r-in-east",
                        valid_from="2026-04-18T12:00:00+02:00",
                        inserted_at="2026-04-18T10:05:00+00:00"),
            # 14:30Z, outside the window although '09:30-05:00' reads inside
            # it as text (the tx clock is outside too).
            make_record("HOLDS", relation_id="r-fake-in",
                        valid_from="2026-04-18T09:30:00-05:00",
                        inserted_at="2026-04-18T14:35:00+00:00"),
            # Admitted by the tx clock only (10:15Z): the two clocks stay
            # formally separate.
            make_record("HOLDS", relation_id="r-in-tx",
                        valid_from="2026-04-18T20:00:00+00:00",
                        inserted_at="2026-04-18T09:15:00-01:00"),
        )
        entries = q5_episode_timeline(
            records, "2026-04-18T09:00:00Z", "2026-04-18T10:30:00Z")
        self.assertEqual([entry["relation_id"] for entry in entries],
                         ["r-in-east", "r-in-tx"])

    def test_ordering_is_by_instant_not_by_text(self):
        records = (
            # 10:00Z.
            make_record("HOLDS", relation_id="r-a",
                        valid_from="2026-04-18T12:00:00+02:00",
                        inserted_at="2026-04-18T10:05:00+00:00"),
            # 10:30Z: later as an instant, earlier as text ('05:30' < '12:00').
            make_record("HOLDS", relation_id="r-b",
                        valid_from="2026-04-18T05:30:00-05:00",
                        inserted_at="2026-04-18T10:35:00+00:00"),
        )
        entries = q5_episode_timeline(
            records, "2026-04-18T00:00:00Z", "2026-04-18T23:00:00Z")
        self.assertEqual([entry["relation_id"] for entry in entries],
                         ["r-a", "r-b"])


class TemporalInstantGuardTest(unittest.TestCase):
    """Guards on the temporal layer (already instant-based, kept pinned)."""

    def test_covers_treats_offsets_as_instants(self):
        record = make_record(
            "HOLDS", relation_id="r-b",
            valid_from="2026-04-18T17:00:00+00:00",
            valid_to="2026-04-18T19:35:00+02:00")   # 17:35Z = T, excluded
        self.assertFalse(covers(record, T))
        twin = make_record(
            "HOLDS", relation_id="r-b",
            valid_from="2026-04-18T17:00:00+00:00",
            valid_to="2026-04-18T12:35:00-05:00")   # same instant as T
        self.assertFalse(covers(twin, T))
        open_record = make_record(
            "HOLDS", relation_id="r-b",
            valid_from="2026-04-18T17:00:00+00:00",
            valid_to="2026-04-18T12:36:00-05:00")   # 17:36Z
        self.assertTrue(covers(open_record, T))


class PitIndexContractTest(unittest.TestCase):
    """Additive PIT index migration + ``EXPLAIN QUERY PLAN`` contract.

    The query shapes below mirror :mod:`orvyren.graph.api` (Q5 timeline and
    the Q4 block-validity bounds) verbatim: SQLite does no algebra, so a
    rewritten clause would silently stop matching its index. The migration
    itself is additive and idempotent (``CREATE INDEX IF NOT EXISTS``): a
    fresh v3 database and a migrated legacy one converge to the same indexes.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")
        with GraphStore(self.db) as store:
            store.insert_event(_event("ev-idx", 7, 1,
                                      "2026-04-18T17:00:00+00:00",
                                      "2026-04-18T17:05:00+00:00"))
            store.insert_relation_record(make_record(
                "HOLDS", relation_id="rel-idx",
                valid_from="2026-04-18T17:00:00+00:00",
                valid_from_block=10, valid_to_block=20,
                inserted_at="2026-04-18T17:10:00+00:00"))
            # Bulk rows so the query planner plans against a populated table
            # (with ANALYZE statistics, as after ``PRAGMA optimize`` on a real
            # database): on a 2-row table a full scan is genuinely cheapest
            # and the plan says nothing about production behaviour.
            store.connection.executemany(
                "INSERT INTO events (event_id, event_type, chain_id,"
                " block_number, tx_hash, log_index, event_time, observation_time)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [("ev-bulk-%03d" % i, "SUPPLY", 8453, i, "0x" + "ab" * 8,
                  i % 7, "2026-04-18T%02d:%02d:00+00:00" % (i % 24, i % 60),
                  "2026-04-18T%02d:%02d:00+00:00" % (i % 24, (i + 3) % 60))
                 for i in range(300)])
            store.connection.executemany(
                "INSERT INTO relations (relation_id, revision, inserted_at,"
                " src, dst, kind, sign_prior, lifecycle, validation_status,"
                " valid_from, valid_from_block, valid_to_block)"
                " VALUES (?, ?, ?, ?, ?, ?, '+', 'ACTIVE', 'VALIDATED',"
                " '2026-04-18T17:00:00+00:00', ?, ?)",
                [("rel-bulk-%03d" % i, 1, "2026-04-18T17:10:00+00:00",
                  "node-a-%d" % (i % 50), "node-b-%d" % (i % 37), "HOLDS",
                  None if i % 3 == 0 else i,
                  None if i % 4 == 0 else i + 100)
                 for i in range(300)])
            store.connection.commit()
            store.connection.execute("ANALYZE")

    def tearDown(self):
        self.tmp.cleanup()

    def _index_names(self):
        con = sqlite3.connect(self.db)
        try:
            return {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")}
        finally:
            con.close()

    def _plan(self, sql, params):
        con = sqlite3.connect(self.db)
        try:
            return [row[3] for row in con.execute(
                "EXPLAIN QUERY PLAN " + sql, params)]
        finally:
            con.close()

    def test_pit_indexes_exist(self):
        names = self._index_names()
        for index in PIT_INDEXES:
            self.assertIn(index, names)

    def test_migration_is_idempotent_on_reopen(self):
        # Re-opening replays the additive migration on a populated database.
        with GraphStore(self.db) as store:
            store.insert_event(_event("ev-idx-2", 8, 1,
                                      "2026-04-18T17:20:00+00:00",
                                      "2026-04-18T17:21:00+00:00"))
        con = sqlite3.connect(self.db)
        try:
            rows = con.execute(
                "SELECT name, COUNT(*) FROM sqlite_master "
                "WHERE type='index' GROUP BY name HAVING COUNT(*) > 1").fetchall()
        finally:
            con.close()
        self.assertEqual(rows, [])
        for index in PIT_INDEXES:
            self.assertIn(index, self._index_names())

    def test_q5_ordered_plan_uses_block_log_index(self):
        # Q5's "ORDER BY block_number DESC, log_index DESC LIMIT n" reads the
        # index in order: no temp B-tree for the sort.
        plan = "\n".join(self._plan(_Q5_SHAPE, ("x", 1, "x", 5)))
        self.assertIn("idx_events_block_log", plan)
        self.assertNotIn("TEMP B-TREE", plan)

    def test_q5_pit_filter_plan_uses_the_pit_indexes(self):
        # OR-wrapped PIT predicates ("col IS NULL OR julianday(col) <= ...")
        # resolve through the plain + julianday() index pair, never a bare
        # full scan of events.
        plan = "\n".join(self._plan(_Q5_FILTER_SHAPE, ("x", "x")))
        self.assertIn("USING INDEX", plan)
        self.assertNotIn("\nSCAN events\n", "\n" + plan + "\n")
        self.assertTrue("idx_events_time_jd" in plan
                        or "idx_events_evt_time" in plan, plan)

    def test_block_validity_plan_uses_block_index(self):
        plan = "\n".join(self._plan(_Q4_BLOCK_SHAPE, (10, 20)))
        self.assertIn("idx_rel_block_valid", plan)

    def test_indexes_do_not_change_query_results(self):
        # Perf-only: the PIT answers are unchanged with the indexes present
        # (the exhaustive non-regression lives in the PIT tests above).
        result = api.timeline(self.db, as_of=T, limit=500)
        ids = [row["event_id"] for row in result["rows"]]
        self.assertIn("ev-idx", ids)
        result = api.pit(self.db, as_of=T, as_of_block=15, limit=500)
        self.assertIn("rel-idx", [row["relation_id"] for row in result["rows"]])


if __name__ == "__main__":
    unittest.main()
