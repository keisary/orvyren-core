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


if __name__ == "__main__":
    unittest.main()
