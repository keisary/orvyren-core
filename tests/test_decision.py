#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - decision engine, baseline and corpus test suite.

Covers, at minimum (per the frozen V1 work plan):
  (a) determinism      : two executions produce identical JSON;
  (b) baseline A0      : the real corpus yields at least one main-window signal;
  (c) engine on the real corpus: H2 SUPPORTED (or INCONCLUSIVE with missing
      inputs) and a decision consistent with the pre-registered rule;
  (d) INCONCLUSIVE path: a corpus without the supply series yields
      INCONCLUSIVE with a non-empty missing_inputs list.

Run: python -m unittest discover -s tests -v
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.decision.baseline import (  # noqa: E402
    BASELINE_THRESHOLD,
    CONSECUTIVE_OBSERVATIONS,
    REDUCTION_USDC,
    run_baseline,
)
from orvyren.decision.engine import (  # noqa: E402
    ACTION_RECOMMENDED,
    INCONCLUSIVE as DECISION_INCONCLUSIVE,
    NO_ACTION,
    run_case,
)
from orvyren.decision.exposure import (  # noqa: E402
    ACTION_USDC,
    EXPOSURE_USDC,
    FLOOR_USDC,
    Exposure,
    available_to_move,
)
from orvyren.decision.scenarios import (  # noqa: E402
    AGGREGATE_TOLERANCE_PCT,
    DEVIATION_ALERT_PCT,
    INCONCLUSIVE as VERDICT_INCONCLUSIVE,
    PERSISTENCE_HOURS_LIMIT,
    RECOVERY_HOURS_LIMIT,
    REFUTED,
    SUPPLY_DROP_PCT,
    SUPPLY_WINDOW_HOURS,
    SUPPORTED,
    deviation_exceeds,
    load_observations,
    within_tolerance,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = "corpus/usdc_observations.csv"
CORPUS_ABS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")
RUN_DECISION = os.path.join(REPO_ROOT, "run_decision.py")

MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")
CONTROL_WINDOW = ("2023-02-15T00:00:00+00:00", "2023-02-18T00:00:00+00:00")

SUPPLY_VENUES = {"defillama_supply_aggregate", "defillama_supply_ethereum"}


def canonical(payload):
    """Order-independent canonical JSON (used to compare two executions)."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def write_corpus_without_supply(target_path):
    """Copy the frozen corpus minus every supply row (used for the INCONCLUSIVE test)."""
    with open(CORPUS_ABS, newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames
        rows = [row for row in reader if row["venue"] not in SUPPLY_VENUES]
    with open(target_path, "w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestExposure(unittest.TestCase):
    """The demonstration exposure envelope and its pure availability function."""

    def test_available_to_move_matches_the_frozen_definition(self):
        cases = [
            (500.0, 350.0, 100.0, 100.0),
            (380.0, 350.0, 100.0, 30.0),    # capped by what remains above the floor
            (500.0, 350.0, 1000.0, 150.0),  # capped by the room above the floor
            (350.0, 350.0, 100.0, 0.0),     # exposure already at the floor
            (300.0, 350.0, 100.0, 0.0),     # below the floor -> never forced
            (500.0, 350.0, 0.0, 0.0),
        ]
        for exposure, floor, desired, expected in cases:
            with self.subTest(exposure=exposure, floor=floor, desired=desired):
                self.assertEqual(expected, available_to_move(exposure, floor, desired))

    def test_demonstration_parameters_are_frozen(self):
        self.assertEqual(500.0, EXPOSURE_USDC)
        self.assertEqual(350.0, FLOOR_USDC)
        self.assertEqual(100.0, ACTION_USDC)

    def test_exposure_envelope_defaults_and_serialisation(self):
        envelope = Exposure()
        self.assertEqual(100.0, envelope.available_to_move())
        self.assertEqual(50.0, Exposure(exposure_usdc=400.0).available_to_move())
        payload = envelope.as_dict()
        self.assertEqual(100.0, payload["available_to_move_usdc"])
        self.assertEqual(EXPOSURE_USDC, payload["exposure_usdc"])
        self.assertTrue(payload["note"])  # the demo disclaimer always travels with the numbers


class TestPreRegisteredConstants(unittest.TestCase):
    """Thresholds are pre-registered: they must not drift silently."""

    def test_scenario_thresholds(self):
        self.assertEqual(1.0, DEVIATION_ALERT_PCT)
        self.assertEqual(0.5, AGGREGATE_TOLERANCE_PCT)
        self.assertEqual(0.1, RECOVERY_HOURS_LIMIT / 120.0)
        self.assertEqual(12.0, RECOVERY_HOURS_LIMIT)
        self.assertEqual(12.0, PERSISTENCE_HOURS_LIMIT)
        self.assertEqual(1.0, SUPPLY_DROP_PCT)
        self.assertEqual(24.0, SUPPLY_WINDOW_HOURS)

    def test_baseline_thresholds(self):
        self.assertEqual(0.99, BASELINE_THRESHOLD)
        self.assertEqual(2, CONSECUTIVE_OBSERVATIONS)
        self.assertEqual(100.0, REDUCTION_USDC)


class TestCorpus(unittest.TestCase):
    """The frozen corpus loads, validates and contains what the case claims."""

    def test_corpus_loads_all_rows(self):
        observations = load_observations(CORPUS_ABS)
        # 520 rows = window-bounded archive (main 9-15/03 + control 15-18/02),
        # after the 2026-10-14 re-collection that removed 855 Bitstamp rows
        # which a stale pre-filter cache had let slip past 2023-03-15 (was 1375).
        self.assertEqual(520, len(observations))
        venues = {o.venue for o in observations}
        self.assertTrue(SUPPLY_VENUES.issubset(venues))
        self.assertTrue({"defillama", "bitstamp", "binance"}.issubset(venues))

    def test_measured_extrema_of_the_primary_window(self):
        observations = load_observations(CORPUS_ABS)
        in_window = [o for o in observations if MAIN_WINDOW[0] <= o.timestamp_utc <= MAIN_WINDOW[1]]
        bitstamp_min = min((o for o in in_window if o.venue == "bitstamp"), key=lambda o: o.value)
        self.assertEqual("2023-03-11T07:00:00+00:00", bitstamp_min.timestamp_utc)
        self.assertAlmostEqual(0.86267, bitstamp_min.value, places=5)
        binance_min = min((o for o in in_window if o.venue == "binance"), key=lambda o: o.value)
        self.assertEqual("2023-03-11T15:00:00+00:00", binance_min.timestamp_utc)
        self.assertAlmostEqual(0.9128, binance_min.value, places=4)


class TestBaselineA0(unittest.TestCase):
    """(b) Baseline A0 on the real corpus: main window and control window."""

    @classmethod
    def setUpClass(cls):
        cls.observations = load_observations(CORPUS_ABS)
        cls.report = run_baseline(CORPUS_ABS, MAIN_WINDOW, CONTROL_WINDOW, observations=cls.observations)

    def test_signals_main_at_least_one(self):
        signals = self.report["signals_main"]
        self.assertGreaterEqual(len(signals), 1, "the frozen A0 rule must fire on the March 2023 depeg")

    def test_every_signal_fires_on_two_consecutive_hours_below_threshold(self):
        for signal in self.report["signals_main"]:
            refs = signal["evidence_refs"]
            self.assertEqual(2, len(refs))
            self.assertTrue(all(ref["value"] < BASELINE_THRESHOLD for ref in refs))
            self.assertEqual(2, signal["consecutive_observations"])
            self.assertEqual("defillama", signal["venue"])
            self.assertEqual(REDUCTION_USDC, signal["action"]["amount_usdc"])

    def test_control_window_signals_are_false_signal_count(self):
        report = self.report
        self.assertEqual(len(report["signals_control"]), report["false_signals_control"])
        # Observed on the frozen corpus: the single one-hour dip of 16 Feb 2023
        # (0.988011) is filtered out by the two-consecutive-observations clause.
        self.assertEqual(0, report["false_signals_control"])

    def test_rule_text_states_the_frozen_rule(self):
        rule = self.report["rule"]
        self.assertIn("0.99", rule)
        self.assertIn("2 consecutive", rule)
        self.assertIn("100 USDC", rule)
        self.assertIn("NO-ACTION", rule)


class TestEngineRealCorpus(unittest.TestCase):
    """(c) Engine on the real corpus and consistency with the frozen decision rule."""

    @classmethod
    def setUpClass(cls):
        cls.case = run_case(CORPUS, MAIN_WINDOW[0], MAIN_WINDOW[1])

    def test_h2_supported_or_inconclusive_with_missing_inputs(self):
        h2 = self.case["hypothesis_verdicts"]["H2"]
        if h2["verdict"] == VERDICT_INCONCLUSIVE:
            self.assertTrue(h2["missing_inputs"], "an INCONCLUSIVE verdict must name the missing input")
        else:
            self.assertEqual(SUPPORTED, h2["verdict"])
            self.assertGreater(len(h2["evidence_refs"]), 0)

    def test_decision_follows_the_pre_registered_rule(self):
        verdicts = self.case["hypothesis_verdicts"]
        decision = self.case["decision"]
        available = self.case["inputs_summary"]["exposure_parameters"]["available_to_move_usdc"]
        h1, h2 = verdicts["H1"], verdicts["H2"]
        if h2["verdict"] == SUPPORTED and available > 0:
            expected = ACTION_RECOMMENDED
        elif h2["verdict"] == REFUTED:
            expected = NO_ACTION
        elif h2["verdict"] == VERDICT_INCONCLUSIVE and h2["missing_inputs"]:
            expected = DECISION_INCONCLUSIVE
        else:
            expected = DECISION_INCONCLUSIVE
        self.assertEqual(expected, decision["verdict"])
        if expected == ACTION_RECOMMENDED:
            self.assertIsNotNone(decision["action"])
            self.assertEqual([], decision["missing_inputs"])
        else:
            self.assertIsNone(decision["action"])

    def test_action_shape_when_recommended(self):
        action = self.case["decision"]["action"]
        if self.case["decision"]["verdict"] != ACTION_RECOMMENDED:
            self.skipTest("decision is not ACTION_RECOMMENDED on this corpus")
        self.assertEqual(
            {"type", "asset", "amount_usdc", "from_wallet", "to_wallet"}, set(action.keys())
        )
        self.assertEqual("transfer", action["type"])
        self.assertEqual("USDC (test)", action["asset"])
        self.assertEqual("treasury", action["from_wallet"])
        self.assertEqual("reserve", action["to_wallet"])
        self.assertEqual(ACTION_USDC, action["amount_usdc"])
        self.assertLessEqual(action["amount_usdc"], ACTION_USDC)

    def test_output_shape_and_calibration(self):
        self.assertEqual(
            {"case", "window", "inputs_summary", "hypothesis_verdicts", "decision", "calibration"},
            set(self.case.keys()),
        )
        self.assertIsNone(self.case["calibration"])
        self.assertEqual("usdc-2023-03", self.case["case"])
        self.assertEqual(MAIN_WINDOW[0], self.case["window"]["start"])
        self.assertEqual(MAIN_WINDOW[1], self.case["window"]["end"])

    def test_provenance_refs_are_complete_and_non_empty(self):
        provenance = self.case["decision"]["provenance"]
        self.assertGreater(len(provenance), 0)
        for ref in provenance:
            self.assertEqual({"timestamp_utc", "venue", "value"}, set(ref.keys()))
            self.assertIsInstance(ref["value"], float)

    def test_exposure_parameters_are_serialised(self):
        payload = self.case["inputs_summary"]["exposure_parameters"]
        self.assertEqual(EXPOSURE_USDC, payload["exposure_usdc"])
        self.assertEqual(FLOOR_USDC, payload["floor_usdc"])
        self.assertEqual(ACTION_USDC, payload["action_usdc"])
        self.assertEqual(100.0, payload["available_to_move_usdc"])

    def test_real_corpus_regression_values(self):
        """The verified outcome of the frozen corpus (documented in the evidence file).

        ``simultaneous_alert_hours`` is 34, not 36: two bitstamp observations sit
        at exactly 0.99 (2023-03-13T10:00/11:00), i.e. exactly 1.00% below peg,
        which "> 1%" excludes. Percentage arithmetic in float space would turn
        that into 1.0000000000000009% and wrongly count them; the module
        compares in value space for this reason (see deviation_exceeds) and the
        count is re-verified independently from the raw CSV in
        TestSimultaneousHoursIndependentCheck.
        """
        verdicts = self.case["hypothesis_verdicts"]
        self.assertEqual(REFUTED, verdicts["H1"]["verdict"])
        self.assertEqual(SUPPORTED, verdicts["H2"]["verdict"])
        self.assertEqual(REFUTED, verdicts["H3"]["verdict"])
        self.assertEqual(ACTION_RECOMMENDED, self.case["decision"]["verdict"])
        computed = verdicts["H2"]["criteria_evaluated"][0]["computed"]
        self.assertEqual(34, computed["simultaneous_alert_hours"])
        self.assertEqual("2023-03-11T14:00:00+00:00", computed["simultaneous_first_utc"])
        self.assertEqual("2023-03-13T08:00:00+00:00", computed["simultaneous_last_utc"])
        self.assertAlmostEqual(-7.1722, computed["max_24h_supply_drop_pct"], places=3)

    def test_window_bounds_are_inclusive_on_the_main_case(self):
        observations = load_observations(CORPUS_ABS)
        count = self.case["inputs_summary"]["corpus"]["observations_in_window"]
        expected = sum(1 for o in observations if MAIN_WINDOW[0] <= o.timestamp_utc <= MAIN_WINDOW[1])
        self.assertEqual(expected, count)


class TestInconclusivePath(unittest.TestCase):
    """(d) A corpus without the supply series yields INCONCLUSIVE, not a guess."""

    def test_missing_supply_yields_inconclusive_with_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corpus_without_supply = os.path.join(tmp_dir, "no_supply.csv")
            write_corpus_without_supply(corpus_without_supply)
            case = run_case(corpus_without_supply, MAIN_WINDOW[0], MAIN_WINDOW[1])

        h2 = case["hypothesis_verdicts"]["H2"]
        self.assertEqual(VERDICT_INCONCLUSIVE, h2["verdict"])
        self.assertTrue(h2["missing_inputs"])
        self.assertIn("supply", " ".join(h2["missing_inputs"]).lower())
        self.assertEqual(DECISION_INCONCLUSIVE, case["decision"]["verdict"])
        self.assertIsNone(case["decision"]["action"])
        self.assertTrue(case["decision"]["missing_inputs"])

        # the venue evidence is untouched: H1 stays decidable and refuted
        self.assertEqual(REFUTED, case["hypothesis_verdicts"]["H1"]["verdict"])


class TestAlertBoundarySemantics(unittest.TestCase):
    """Threshold boundaries are read literally: exactly 1.00% below is NOT "> 1%"."""

    def test_value_exactly_at_threshold_is_not_an_alert(self):
        self.assertFalse(deviation_exceeds(0.99, 1.0), "0.99 is exactly 1.00% below peg, not more")
        self.assertTrue(deviation_exceeds(0.98999, 1.0))
        self.assertTrue(deviation_exceeds(0.86267, 1.0))

    def test_tolerance_boundary_is_inclusive(self):
        self.assertTrue(within_tolerance(0.999, 0.1), "0.999 is exactly the +/-0.1% boundary")
        self.assertFalse(within_tolerance(0.9989, 0.1))


class TestSimultaneousHoursIndependentCheck(unittest.TestCase):
    """Independent recomputation of the simultaneous-alert hours from the raw CSV.

    No classification helper and no float percentage arithmetic is used here:
    each row is compared with Decimal against exactly "0.99". This verifies the
    engine's count (34) instead of assuming it; two bitstamp rows sit exactly on
    the boundary (0.99) and must not be counted as "> 1% below peg".
    """

    def test_simultaneous_alert_hours_from_raw_csv(self):
        threshold = Decimal("0.99")
        alerts = {"bitstamp": set(), "binance": set()}
        with open(CORPUS_ABS, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["venue"] not in alerts:
                    continue
                if not (MAIN_WINDOW[0] <= row["timestamp_utc"] <= MAIN_WINDOW[1]):
                    continue
                if Decimal(row["value"]) < threshold:
                    alerts[row["venue"]].add(row["timestamp_utc"])

        simultaneous = sorted(alerts["bitstamp"].intersection(alerts["binance"]))
        self.assertEqual(44, len(alerts["bitstamp"]))
        self.assertEqual(46, len(alerts["binance"]))
        self.assertEqual(34, len(simultaneous))
        self.assertEqual("2023-03-11T14:00:00+00:00", simultaneous[0])
        self.assertEqual("2023-03-13T08:00:00+00:00", simultaneous[-1])

        # the engine must agree with this independent count
        case = run_case(CORPUS, MAIN_WINDOW[0], MAIN_WINDOW[1])
        computed = case["hypothesis_verdicts"]["H2"]["criteria_evaluated"][0]["computed"]
        self.assertEqual(len(simultaneous), computed["simultaneous_alert_hours"])
        self.assertEqual(simultaneous[0], computed["simultaneous_first_utc"])
        self.assertEqual(simultaneous[-1], computed["simultaneous_last_utc"])

    def test_boundary_rows_are_present_in_the_corpus(self):
        """Guards the reason 34 != 36: exactly-two bitstamp rows sit at exactly 0.99."""
        boundary_rows = []
        with open(CORPUS_ABS, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["venue"] == "bitstamp" and MAIN_WINDOW[0] <= row["timestamp_utc"] <= MAIN_WINDOW[1]:
                    if Decimal(row["value"]) == Decimal("0.99"):
                        boundary_rows.append(row["timestamp_utc"])
        self.assertEqual(["2023-03-13T10:00:00+00:00", "2023-03-13T11:00:00+00:00"], sorted(boundary_rows))


class TestDeterminism(unittest.TestCase):
    """(a) Two executions produce identical JSON."""

    def test_two_engine_runs_produce_identical_json(self):
        first = canonical(run_case(CORPUS, MAIN_WINDOW[0], MAIN_WINDOW[1]))
        second = canonical(run_case(CORPUS, MAIN_WINDOW[0], MAIN_WINDOW[1]))
        self.assertEqual(first, second)

    def test_cli_writes_byte_identical_evidence_files_on_two_runs(self):
        if not os.path.exists(RUN_DECISION):
            self.skipTest("run_decision.py not present")
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dirs = [os.path.join(tmp_dir, "run1"), os.path.join(tmp_dir, "run2")]
            for out_dir in out_dirs:
                completed = subprocess.run(
                    [sys.executable, RUN_DECISION, "--out-dir", out_dir],
                    cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
            for name in ("decision_usdc-2023-03.json", "baseline_report.json"):
                with open(os.path.join(out_dirs[0], name), "rb") as handle:
                    first_bytes = handle.read()
                with open(os.path.join(out_dirs[1], name), "rb") as handle:
                    second_bytes = handle.read()
                self.assertEqual(first_bytes, second_bytes, f"{name} is not deterministic")
            # the CLI must also state the decision it wrote
            with open(os.path.join(out_dirs[0], "decision_usdc-2023-03.json"), encoding="utf-8") as handle:
                cli_case = json.load(handle)
            self.assertEqual(ACTION_RECOMMENDED, cli_case["decision"]["verdict"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
