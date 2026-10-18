#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: quality layer + evidence graph (ORVYREN-Core).

The corpus is never assumed: where a count matters, this bench measures it
from the archived CSV and compares it with what the modules return, and the
failure message carries the measured value.

Execution: ``python -m unittest discover -s tests -v``
"""

import csv
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph import models  # noqa: E402
from orvyren.graph.models import Claim, Hypothesis, Relation, Source  # noqa: E402
from orvyren.graph.provenance import verify_all, verify_chain  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402
from orvyren.quality import checks, normalize  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_CSV = os.path.join(ROOT, "corpus", "usdc_observations.csv")

#: Row count contract of the archived corpus (corpus/manifest.json).
#: 520 after the 2026-10-14 window-bounded re-collection; was 1375, of which
#: 855 Bitstamp rows from a stale pre-filter cache sat beyond 2023-03-15.
EXPECTED_ROWS = 520

MAIN_START = datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc)
MAIN_END = datetime(2023, 3, 15, 0, 0, tzinfo=timezone.utc)

_CORPUS_CACHE = {}


def read_corpus_rows():
    """Raw corpus rows, with a local ISO parser (independent of the modules)."""
    with open(CORPUS_CSV, "r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    parsed = []
    for row in rows:
        parsed.append({
            "venue": row["venue"],
            "metric": row["metric"],
            "value": float(row["value"]),
            "ts": datetime.fromisoformat(row["timestamp_utc"]),
        })
    return parsed


def local_hour_floor(ts):
    """Floor to the UTC hour without using ``orvyren.quality.checks``."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)  # naive = UTC (project convention)
    return ts.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def measured_hours(rows, venue, start=MAIN_START, end=MAIN_END):
    """Hours covered by ``venue`` in [start, end], measured from raw rows."""
    return {local_hour_floor(row["ts"]) for row in rows
            if row["venue"] == venue and start <= row["ts"] <= end}


def real_corpus():
    """Load the real corpus once per test session."""
    if "loaded" not in _CORPUS_CACHE:
        _CORPUS_CACHE["loaded"] = normalize.load_observations(CORPUS_CSV)
        _CORPUS_CACHE["rows"] = read_corpus_rows()
    return _CORPUS_CACHE["loaded"]


def source_stub(source_id="defillama"):
    return Source(id=source_id, name="test source", endpoint="test://endpoint",
                  retrieved_at="2026-10-14T12:28:50+00:00", limits="test limits")


class TestRealCorpusLoad(unittest.TestCase):
    """(a) The real corpus loads with its real row count."""

    def test_loaded_count_matches_the_file(self):
        observations, report = real_corpus()
        rows = read_corpus_rows()
        self.assertEqual(len(rows), EXPECTED_ROWS,
                         "corpus changed: %d data rows measured, %d documented"
                         % (len(rows), EXPECTED_ROWS))
        self.assertEqual(report["total"], len(rows),
                         "report total %d != %d physical data rows"
                         % (report["total"], len(rows)))
        self.assertEqual(len(observations), EXPECTED_ROWS,
                         "loaded %d observations, expected %d"
                         % (len(observations), EXPECTED_ROWS))
        self.assertEqual(report["kept"], EXPECTED_ROWS)
        self.assertEqual(len(report["rejected"]), 0,
                         "rejections on the archived corpus: %s" % report["rejected"])
        self.assertEqual(sum(report["counts_by_venue"].values()), EXPECTED_ROWS)
        self.assertEqual(sum(report["counts_by_metric"].values()), EXPECTED_ROWS)
        self.assertEqual(report["total"],
                         report["kept"] + len(report["rejected"]))

    def test_counts_by_venue_match_the_file(self):
        _, report = real_corpus()
        measured = {}
        for row in read_corpus_rows():
            measured[row["venue"]] = measured.get(row["venue"], 0) + 1
        self.assertEqual(report["counts_by_venue"], dict(sorted(measured.items())))

    def test_every_observation_resolves_to_a_declared_source(self):
        observations, _ = real_corpus()
        unknown = sorted({obs.venue for obs in observations
                          if obs.venue not in normalize.VENUE_SOURCES})
        self.assertEqual(unknown, [], "venues without a source mapping: %s" % unknown)
        missing_units = sorted({obs.metric for obs in observations
                                if obs.metric not in normalize.METRIC_UNITS})
        self.assertEqual(missing_units, [])


class TestNormaliseRules(unittest.TestCase):
    """Each validation rule produces a finding; nothing is dropped silently."""

    HEADER = "timestamp_utc,venue,metric,value,extra,retrieved_at\n"

    def _load(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "synthetic.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self.HEADER + body)
            return normalize.load_observations(path)

    def test_rules_flag_or_reject_each_bad_row(self):
        observations, report = self._load(
            "2023-03-09T00:00:00+00:00,defillama,price_usd,1.0,confidence=0.99,2026-10-14T12:28:50+00:00\n"
            "2023-03-09T01:00:00+00:00,defillama,price_usd,abc,confidence=0.99,2026-10-14T12:28:51+00:00\n"
            "2023-03-09T02:00:00+00:00,defillama,mystery_metric,1.0,,2026-10-14T12:28:52+00:00\n"
            "2023-03-09T03:00:00+00:00,bitstamp,close_usd,1.75,low=1.0,2026-10-14T12:28:53+00:00\n"
            "2023-03-09T00:00:00+00:00,defillama,price_usd,1.0,confidence=0.99,2026-10-14T12:28:54+00:00\n"
            "2023-03-09T05:00:00+00:00,binance,close_usdcusdt,,,2026-10-14T12:28:55+00:00\n"
            "2023-03-09T06:00:00+00:00,defillama_supply_aggregate,circulating_usd,43489028917,,2026-10-14T12:28:56+00:00\n"
            "not-a-date,binance,close_usdcusdt,1.0,,2026-10-14T12:28:57+00:00\n"
            "2023-03-09T08:00:00+00:00,,price_usd,1.0,,2026-10-14T12:28:58+00:00\n"
        )
        self.assertEqual(report["total"], 9)
        self.assertEqual(len(observations), 4, "kept rows must exclude rejected ones")
        self.assertEqual(report["kept"], 4)
        reasons = {item["reason"] for item in report["rejected"]}
        self.assertEqual(reasons, {
            "non_numeric_value:abc",
            "unknown_metric_unit:mystery_metric",
            "missing_value",
            "invalid_timestamp:not-a-date",
            "missing_field:venue",
        })
        self.assertEqual([item["row"] for item in report["rejected"]], [3, 4, 7, 9, 10])
        flags = [item["flag"] for item in report["flagged"]]
        self.assertEqual(flags, [normalize.FLAG_PRICE_RANGE, normalize.FLAG_DUPLICATE])
        self.assertEqual([item["row"] for item in report["flagged"]], [5, 6])
        # The outlier and the duplicate stay in the list: flagged, not deleted.
        self.assertIn(1.75, [obs.value for obs in observations])
        # A supply value outside the price band is neither flagged nor rejected.
        self.assertNotIn(8, {item["row"] for item in report["flagged"]})

    def test_price_band_bounds_are_inclusive(self):
        observations, report = self._load(
            "2023-03-09T00:00:00+00:00,bitstamp,close_usd,0.50,low=0.5,2026-10-14T12:28:50+00:00\n"
            "2023-03-09T01:00:00+00:00,bitstamp,close_usd,1.50,low=1.5,2026-10-14T12:28:51+00:00\n"
            "2023-03-09T02:00:00+00:00,bitstamp,close_usd,0.49,low=0.4,2026-10-14T12:28:52+00:00\n"
        )
        self.assertEqual(len(report["flagged"]), 1)
        self.assertEqual(report["flagged"][0]["row"], 4)
        self.assertEqual(len(observations), 3)


class TestRealCorpusCoverage(unittest.TestCase):
    """(d) Coverage figures come from the measured rows, not from guesswork."""

    @classmethod
    def setUpClass(cls):
        cls.observations, _ = real_corpus()
        cls.rows = read_corpus_rows()
        cls.coverage = checks.hourly_coverage(cls.observations)

    def test_window_slots_are_measured(self):
        expected_slots = int((MAIN_END - MAIN_START).total_seconds() // 3600) + 1
        self.assertEqual(self.coverage["window"]["hours"], expected_slots,
                         "window holds %d slots, module says %d"
                         % (expected_slots, self.coverage["window"]["hours"]))

    def test_binance_and_bitstamp_hours_match_their_rows(self):
        for venue in ("binance", "bitstamp", "defillama"):
            expected = len(measured_hours(self.rows, venue))
            reported = self.coverage["per_venue"][venue]["hours_covered"]
            self.assertEqual(reported, expected,
                             "%s: module reports %d covered hours, the corpus "
                             "holds %d" % (venue, reported, expected))
        self.assertEqual(self.coverage["per_venue"]["binance"]["hours_covered"], 83,
                         "Binance covered hours measured: %d"
                         % self.coverage["per_venue"]["binance"]["hours_covered"])
        self.assertEqual(self.coverage["per_venue"]["bitstamp"]["hours_covered"], 145,
                         "Bitstamp covered hours measured: %d"
                         % self.coverage["per_venue"]["bitstamp"]["hours_covered"])

    def test_two_plus_venue_hours_match_the_measurement(self):
        multi = set()
        for hour in checks.window_hours():
            present = 0
            for venue in checks.INDEPENDENT_PRICE_VENUES:
                if hour in measured_hours(self.rows, venue):
                    present += 1
            if present >= checks.MIN_INDEPENDENT_VENUES:
                multi.add(hour)
        self.assertEqual(
            self.coverage["hours_with_two_plus_independent_venues"], len(multi),
            "measured %d hours with >= 2 independent venues, module says %d"
            % (len(multi), self.coverage["hours_with_two_plus_independent_venues"]))

    def test_data_gate_reads_the_corpus(self):
        hour = datetime(2023, 3, 11, 15, 0, tzinfo=timezone.utc)
        present = sorted({venue for venue in checks.INDEPENDENT_PRICE_VENUES
                          if hour in measured_hours(self.rows, venue)})
        gate = checks.data_gate(self.observations, hour)
        self.assertEqual(present, ["binance", "bitstamp", "defillama"],
                         "measured venues at %s: %s" % (hour, present))
        self.assertEqual(gate["status"], "OK")
        self.assertEqual(gate["missing"], [])
        self.assertEqual(gate["venues_present"], present)

    def test_data_gate_reports_insufficient_and_missing(self):
        early = checks.data_gate(self.observations,
                                 datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(early["status"], "OK")
        self.assertEqual(early["missing"], ["binance"])

        alone_hour = datetime(2023, 3, 16, 0, 0, tzinfo=timezone.utc)
        measured = sorted(venue for venue in checks.INDEPENDENT_PRICE_VENUES
                          if alone_hour in measured_hours(self.rows, venue,
                                                          alone_hour, alone_hour))
        self.assertEqual(measured, [],
                         "measured venues at %s: %s (the archive is window-bounded "
                         "since the 2026-10-14 re-collection: nothing exists past "
                         "the main window)" % (alone_hour, measured))
        expected = [venue for venue in checks.INDEPENDENT_PRICE_VENUES
                    if venue not in measured]
        alone = checks.data_gate(self.observations, alone_hour)
        self.assertEqual(alone["status"], "INSUFFICIENT")
        self.assertEqual(alone["missing"], expected)
        self.assertEqual(alone["venues_present"], measured)

    def test_gate_is_hour_floored(self):
        late = checks.data_gate(self.observations,
                                datetime(2023, 3, 11, 15, 42, tzinfo=timezone.utc))
        self.assertEqual(late["hour"], "2023-03-11T15:00:00+00:00")
        self.assertEqual(late["status"], "OK")


class TestRealCorpusCoverageOfTheFileItself(unittest.TestCase):
    """The corpus must contain the hours the bench just asserted."""

    def test_expected_scenarios_exist_in_the_archive(self):
        rows = read_corpus_rows()
        binance_hours = measured_hours(rows, "binance")
        self.assertTrue(binance_hours, "no Binance hours measured in the window")
        self.assertEqual(min(binance_hours),
                         datetime(2023, 3, 11, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(max(binance_hours),
                         datetime(2023, 3, 15, 0, 0, tzinfo=timezone.utc))
        bitstamp_low = min(row["value"] for row in rows
                           if row["venue"] == "bitstamp"
                           and MAIN_START <= row["ts"] <= MAIN_END)
        self.assertLess(bitstamp_low, 0.95,
                        "Bitstamp low measured in the window: %s" % bitstamp_low)


class TestStoreAppendOnly(unittest.TestCase):
    """(c) A new revision inserts a row; the previous row stays intact."""

    def test_two_revisions_keep_the_first_row(self):
        with GraphStore(":memory:") as store:
            store.insert_source(source_stub())
            first = Claim(id="claim-1", text="first version", refs=["obs-a"],
                          created_at="2026-10-14T12:00:00+00:00", fingerprint="")
            second = Claim(id="claim-1", text="second version", refs=["obs-a"],
                           created_at="2026-10-14T12:05:00+00:00", fingerprint="")
            first_row = store.insert_claim(first)
            second_row = store.insert_claim(second)
            self.assertGreater(second_row, first_row)

            rows = store.connection.execute(
                "SELECT revision, text, row_id FROM claims WHERE claim_id = ? "
                "ORDER BY revision", ("claim-1",)).fetchall()
            self.assertEqual(len(rows), 2, "both revisions must exist")
            self.assertEqual([row["revision"] for row in rows], [1, 2])
            self.assertEqual(rows[0]["text"], "first version",
                             "revision 1 was modified: %s" % rows[0]["text"])
            self.assertEqual(rows[1]["text"], "second version")
            self.assertEqual(store.claim_by_id("claim-1").text, "second version")
            self.assertEqual(store.current_row_count("claims"), 1)
            self.assertEqual(store.snapshot()["rows_total"]["claims"], 2)

    def test_update_and_delete_are_refused(self):
        observations, _ = real_corpus()
        observation = observations[0]
        observation_id = models.observation_fingerprint(observation)
        with GraphStore(":memory:") as store:
            store.insert_source(source_stub(observation.source_id))
            store.insert_observation(observation)
            store.insert_claim(Claim(id="claim-1", text="text", refs=[observation_id],
                                     created_at="2026-10-14T12:00:00+00:00"))
            for statement in (
                "UPDATE claims SET text = 'rewritten' WHERE claim_id = 'claim-1'",
                "DELETE FROM claims WHERE claim_id = 'claim-1'",
                "UPDATE sources SET name = 'rewritten' WHERE source_id = 'defillama'",
                "DELETE FROM observations WHERE observation_id = '%s'" % observation_id,
                "UPDATE observations SET value = 0.0 WHERE observation_id = '%s'"
                % observation_id,
            ):
                with self.assertRaises(sqlite3.DatabaseError) as caught:
                    store.connection.execute(statement)
                self.assertIn("append-only", str(caught.exception))
            # Nothing moved: the rows are still as inserted.
            self.assertEqual(store.claim_by_id("claim-1").text, "text")
            self.assertEqual(store.observation_by_id(observation_id).value,
                             observation.value)
            self.assertEqual(store.source_by_id("defillama").name, "test source")

    def test_claim_without_observation_is_refused(self):
        with GraphStore(":memory:") as store:
            with self.assertRaises(ValueError):
                store.insert_claim(Claim(id="claim-empty", text="no refs",
                                         refs=[], created_at="2026-10-14T12:00:00+00:00"))

    def test_schema_version_is_recorded(self):
        with GraphStore(":memory:") as store:
            row = store.connection.execute(
                "SELECT version FROM schema_version ORDER BY version").fetchone()
            # v3 (graph-v2 schema): nodes/events + the 17-field relation record.
            self.assertEqual(row["version"], 3)


class TestProvenance(unittest.TestCase):
    """(b) verify_chain succeeds on a real claim and fails on a broken ref."""

    @classmethod
    def setUpClass(cls):
        cls.observations, _ = real_corpus()

    def _store_with_real_observation(self):
        store = GraphStore(":memory:")
        observation = self.observations[0]
        store.insert_source(source_stub(observation.source_id))
        store.insert_observation(observation)
        return store, observation

    def test_chain_resolves_for_a_real_claim(self):
        store, observation = self._store_with_real_observation()
        with store:
            observation_id = models.observation_fingerprint(observation)
            claim = models.make_claim(
                "claim-real", "a real measurement", [observation_id],
                "2026-10-14T12:00:00+00:00")
            store.insert_claim(claim)
            result = verify_chain("claim-real", store)
            self.assertTrue(result["ok"], "unresolved refs: %s" % result["missing"])
            self.assertEqual(result["missing"], [])
            self.assertEqual(result["checked"], 1)
            self.assertEqual([obs.value for obs in store.observations_for_claim("claim-real")],
                             [observation.value])

    def test_chain_fails_on_a_missing_ref(self):
        store, observation = self._store_with_real_observation()
        with store:
            good = models.observation_fingerprint(observation)
            claim = models.make_claim(
                "claim-broken", "partly traceable", [good, "obs-does-not-exist"],
                "2026-10-14T12:00:00+00:00")
            store.insert_claim(claim)
            result = verify_chain("claim-broken", store)
            self.assertFalse(result["ok"])
            self.assertEqual(result["missing"], ["obs-does-not-exist"])
            self.assertEqual(result["checked"], 2)
            self.assertEqual(len(store.observations_for_claim("claim-broken")), 1)

    def test_chain_fails_when_the_source_is_absent(self):
        store = GraphStore(":memory:")
        with store:
            observation = self.observations[0]
            # no source row inserted for this observation
            store.insert_observation(observation)
            observation_id = models.observation_fingerprint(observation)
            store.insert_claim(models.make_claim(
                "claim-orphan", "source missing", [observation_id],
                "2026-10-14T12:00:00+00:00"))
            result = verify_chain("claim-orphan", store)
            self.assertFalse(result["ok"])
            self.assertEqual(result["missing"], [observation_id])

    def test_unknown_claim_is_reported(self):
        with GraphStore(":memory:") as store:
            result = verify_chain("claim-unknown", store)
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "claim_not_found")

    def test_verify_all_summarises(self):
        store, observation = self._store_with_real_observation()
        with store:
            observation_id = models.observation_fingerprint(observation)
            store.insert_claim(models.make_claim(
                "claim-good", "traceable", [observation_id],
                "2026-10-14T12:00:00+00:00"))
            store.insert_claim(models.make_claim(
                "claim-broken", "not traceable", ["obs-unknown"],
                "2026-10-14T12:00:00+00:00"))
            summary = verify_all(store)
            self.assertFalse(summary["ok"])
            self.assertEqual(summary["claims_checked"], 2)
            self.assertEqual(summary["claims_failed"], 1)


class TestSnapshotAndFingerprints(unittest.TestCase):
    """(e) Same content -> same fingerprint and same snapshot hash."""

    def _store_with_one_claim(self, text="identical content"):
        store = GraphStore(":memory:")
        store.insert_source(source_stub())
        store.insert_claim(Claim(id="claim-1", text=text, refs=["obs-a"],
                                 created_at="2026-10-14T12:00:00+00:00"))
        return store

    def test_fingerprint_is_stable_and_order_independent(self):
        first = models.fingerprint({"b": 1, "a": [1, 2, 3]})
        second = models.fingerprint({"a": [1, 2, 3], "b": 1})
        self.assertEqual(first, second)
        self.assertEqual(len(first), models.FINGERPRINT_LENGTH)
        int(first, 16)  # hex only
        self.assertNotEqual(first, models.fingerprint({"a": [1, 2, 3], "b": 2}))

    def test_claim_fingerprint_is_reproducible(self):
        first = models.make_claim("claim-1", "text", ["b", "a"], "2026-10-14T12:00:00+00:00")
        second = models.make_claim("claim-1", "text", ["b", "a"], "2026-10-14T12:00:00+00:00")
        self.assertEqual(first.fingerprint, second.fingerprint)
        other = models.make_claim("claim-1", "other text", ["b", "a"],
                                  "2026-10-14T12:00:00+00:00")
        self.assertNotEqual(first.fingerprint, other.fingerprint)

    def test_observation_fingerprint_is_stable(self):
        observations, _ = real_corpus()
        observation = observations[0]

        def build(**overrides):
            fields = {"venue": observation.venue, "metric": observation.metric,
                      "ts_event": observation.ts_event, "value": observation.value,
                      "extra": observation.extra,
                      "retrieved_at": observation.retrieved_at,
                      "source_id": observation.source_id}
            fields.update(overrides)
            return normalize.Observation(**fields)

        # A separately built observation with the same field values carries the
        # same content id (a deepcopy of the same object compared the
        # fingerprint with itself and proved nothing).
        self.assertEqual(models.observation_fingerprint(observation),
                         models.observation_fingerprint(build()))
        # Every field is part of the content id: changing any single one
        # changes the fingerprint.
        for field, changed in (
                ("venue", {"venue": observation.venue + "#2"}),
                ("metric", {"metric": observation.metric + "#2"}),
                ("ts_event", {"ts_event": observation.ts_event + timedelta(hours=1)}),
                ("value", {"value": observation.value + 1.0}),
                ("extra", {"extra": (observation.extra or "") + "#2"}),
                ("retrieved_at", {"retrieved_at": observation.retrieved_at + "#2"}),
                ("source_id", {"source_id": observation.source_id + "#2"}),
        ):
            self.assertNotEqual(
                models.observation_fingerprint(observation),
                models.observation_fingerprint(build(**changed)),
                "field %s must be part of the observation fingerprint" % field)

    def test_snapshot_hash_is_stable_across_stores(self):
        with self._store_with_one_claim() as first, self._store_with_one_claim() as second:
            self.assertEqual(first.snapshot()["hash"], second.snapshot()["hash"])
            self.assertEqual(first.snapshot()["counts"]["claims"], 1)
        with self._store_with_one_claim("other content") as other:
            with self._store_with_one_claim() as reference:
                self.assertNotEqual(reference.snapshot()["hash"],
                                    other.snapshot()["hash"])


class TestRelationsAndHypotheses(unittest.TestCase):
    """Claims attach to a hypothesis through relations, not by convention."""

    def test_claims_for_hypothesis_and_observations_for_claim(self):
        observations, _ = real_corpus()
        observation = observations[0]
        observation_id = models.observation_fingerprint(observation)
        with GraphStore(":memory:") as store:
            store.insert_source(source_stub(observation.source_id))
            store.insert_observation(observation)
            for claim_id in ("claim-a", "claim-b", "claim-c"):
                store.insert_claim(models.make_claim(
                    claim_id, "text of %s" % claim_id, [observation_id],
                    "2026-10-14T12:00:00+00:00"))
            store.insert_hypothesis(Hypothesis(
                id="H1", statement="statement", state="UNDER_TEST",
                criteria_support=["s"], criteria_refute=["r"]))
            for claim_id in ("claim-a", "claim-c"):
                store.insert_relation(Relation(
                    id="rel-%s" % claim_id, src=claim_id, dst="H1",
                    kind="supports"))
            linked = [claim.id for claim in store.claims_for_hypothesis("H1")]
            self.assertEqual(linked, ["claim-a", "claim-c"])
            self.assertEqual(
                [obs.value for obs in store.observations_for_claim("claim-b")],
                [observation.value])
            self.assertEqual(store.hypothesis_by_id("H1").state, "UNDER_TEST")
            self.assertEqual(store.claims_for_hypothesis("H2"), [])


if __name__ == "__main__":
    unittest.main()
