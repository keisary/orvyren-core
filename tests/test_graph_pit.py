#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: bitemporal clocks + INV-PIT (ORVYREN-Core).

Covers B2_GRAPHE_ETUDE.md §1.3: the two formally distinct query modes —
"the world at T" (validity interval) and "what was known at T" (latest
revision inserted at or before T) — their intersection (the PIT decision
set), and the INV-PIT invariant: *changing the future, or a revision
published after ``as_of``, never changes a past decision*.

Execution: ``python -m unittest discover -s tests -v``
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "src"))
sys.path.insert(0, _HERE)

from test_graph_relations import make_record  # noqa: E402
from orvyren.graph.temporal import known_at, pit_at, world_at  # noqa: E402

#: The replayed decision moment (rsETH episode: 2026-04-18 17:35 UTC).
T = "2026-04-18T17:35:00+00:00"


def _ids(records):
    return sorted((r.relation_id, r.revision) for r in records)


class QueryModesTest(unittest.TestCase):
    """Mode 1 vs mode 2 vs mode 3 (B2 §1.3)."""

    def test_world_at_uses_the_validity_interval(self):
        records = (
            make_record("HOLDS", relation_id="r-open", valid_from=None, valid_to=None),
            make_record("HOLDS", relation_id="r-in",
                        valid_from="2026-04-18T17:00:00+00:00",
                        valid_to="2026-04-18T18:00:00+00:00"),
            make_record("HOLDS", relation_id="r-before",
                        valid_from="2026-04-18T16:00:00+00:00",
                        valid_to="2026-04-18T17:35:00+00:00"),  # T excluded
            make_record("HOLDS", relation_id="r-after",
                        valid_from="2026-04-18T17:36:00+00:00", valid_to=None),
        )
        self.assertEqual(_ids(world_at(records, T)),
                         [("r-in", 1), ("r-open", 1)])

    def test_known_at_keeps_the_latest_revision_known(self):
        records = (
            make_record("HOLDS", relation_id="r-1", revision=1,
                        inserted_at="2026-04-18T17:00:00+00:00"),
            make_record("HOLDS", relation_id="r-1", revision=2,
                        inserted_at="2026-04-18T19:00:00+00:00"),  # after T
            make_record("HOLDS", relation_id="r-2", revision=1,
                        inserted_at="2026-04-18T17:30:00+00:00"),
        )
        self.assertEqual(_ids(known_at(records, T)),
                         [("r-1", 1), ("r-2", 1)])

    def test_pit_at_is_the_intersection(self):
        records = (
            # Known at T, but no longer valid at T -> out.
            make_record("HOLDS", relation_id="r-stale",
                        valid_from="2026-04-18T16:00:00+00:00",
                        valid_to="2026-04-18T17:00:00+00:00",
                        inserted_at="2026-04-18T16:30:00+00:00"),
            # Valid at T, but published after T -> out.
            make_record("HOLDS", relation_id="r-late",
                        valid_from="2026-04-18T17:00:00+00:00",
                        valid_to="2026-04-18T18:00:00+00:00",
                        inserted_at="2026-04-18T20:00:00+00:00"),
            # Valid at T and known at T -> in.
            make_record("HOLDS", relation_id="r-both",
                        valid_from="2026-04-18T17:00:00+00:00",
                        valid_to="2026-04-18T18:00:00+00:00",
                        inserted_at="2026-04-18T17:10:00+00:00"),
        )
        self.assertEqual(_ids(pit_at(records, T)), [("r-both", 1)])

    def test_the_two_modes_are_formally_distinct(self):
        # A fact published later about the world at T: in the world set,
        # not in the knowledge set — the two modes must not be conflated.
        later_fact = make_record("HOLDS", relation_id="r-late",
                                 valid_from="2026-04-18T17:00:00+00:00",
                                 valid_to="2026-04-18T18:00:00+00:00",
                                 inserted_at="2026-04-18T20:00:00+00:00")
        self.assertEqual(_ids(world_at((later_fact,), T)), [("r-late", 1)])
        self.assertEqual(_ids(known_at((later_fact,), T)), [])

    def test_open_ends_are_open(self):
        # Null valid_from / valid_to = open or unknown (B2 §1.3).
        record = make_record("HOLDS", relation_id="r-open",
                             valid_from=None, valid_to=None,
                             inserted_at="2026-04-18T17:30:00+00:00")
        self.assertEqual(_ids(pit_at((record,), T)), [("r-open", 1)])


class InvPitTest(unittest.TestCase):
    """INV-PIT: a past decision is immune to future changes (B2 §1.3)."""

    def _state(self):
        return [
            make_record("HOLDS", relation_id="r-1", revision=1,
                        valid_from="2026-04-18T17:00:00+00:00",
                        valid_to="2026-04-18T18:00:00+00:00",
                        inserted_at="2026-04-18T17:10:00+00:00"),
            make_record("HOLDS", relation_id="r-2", revision=1,
                        valid_from=None, valid_to=None,
                        inserted_at="2026-04-18T17:20:00+00:00"),
        ]

    def _mutations(self, base):
        return base + [
            # A fact about the future.
            make_record("HOLDS", relation_id="r-future", revision=1,
                        valid_from="2026-05-01T00:00:00+00:00",
                        valid_to=None,
                        inserted_at="2026-04-20T00:00:00+00:00"),
            # A corrected revision of an existing relation, published after T.
            make_record("HOLDS", relation_id="r-1", revision=2,
                        valid_from=None, valid_to=None,
                        inserted_at="2026-04-19T00:00:00+00:00"),
            # A new relation discovered later, about an open-ended state.
            make_record("HOLDS", relation_id="r-3", revision=1,
                        valid_from=None, valid_to=None,
                        inserted_at="2026-04-19T06:00:00+00:00"),
        ]

    def test_future_changes_do_not_change_a_past_decision(self):
        base = self._state()
        before = _ids(pit_at(base, T))
        after = _ids(pit_at(self._mutations(base), T))
        self.assertEqual(before, after, "INV-PIT broken by future changes")
        self.assertEqual(before, [("r-1", 1), ("r-2", 1)])

    def test_a_later_revision_is_visible_after_its_publication(self):
        # The replay moves forward: at T+1 day the revision IS the decision
        # input (r-1 rev 2 replaces rev 1) — INV-PIT hides the future from
        # the past, not the present.
        base = self._mutations(self._state())
        later = "2026-04-19T01:00:00+00:00"
        self.assertEqual(_ids(pit_at(base, later)), [("r-1", 2), ("r-2", 1)])

    def test_a_correction_on_an_expired_interval_never_enters_pit(self):
        # Retrospective correction of a fact whose validity has ended: it is
        # known from its publication on, but the PIT set is the intersection —
        # no moment exists where it is both known and world-valid.
        corrected = make_record("HOLDS", relation_id="r-1", revision=2,
                                valid_from="2026-04-18T17:00:00+00:00",
                                valid_to="2026-04-18T18:00:00+00:00",
                                inserted_at="2026-04-19T00:00:00+00:00")
        state = self._state() + [corrected]
        self.assertEqual(_ids(known_at(state, "2026-04-19T01:00:00+00:00")),
                         [("r-1", 2), ("r-2", 1)])
        self.assertEqual(_ids(pit_at(state, "2026-04-19T01:00:00+00:00")),
                         [("r-2", 1)])

    def test_snapshot_is_input_order_independent(self):
        base = self._state()
        reversed_state = list(reversed(base))
        self.assertEqual(_ids(pit_at(base, T)), _ids(pit_at(reversed_state, T)))
        self.assertEqual(_ids(world_at(base, T)), _ids(world_at(reversed_state, T)))


if __name__ == "__main__":
    unittest.main()
