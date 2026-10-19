"""Tests for the G6 §3 break-even sensitivity (``loss`` + audit dossier).

Covers the switch probability ``P* = cost / (loss|obligation + cost)``, its
degenerate conventions, the sign of ``E[avoided loss]`` over a
``P(obligation)`` sweep, the three ``r_capital`` funding variants, and the
publication of that sensitivity in the decision dossier.

The dossier tests cross-check the rendered table against ``loss.py``
recomputed independently: no expected value is copied from the dossier.

Run from the repository root::

    python -m unittest tests.test_evaluation_sensitivity -v

Standard library only (unittest, tempfile, json, re); no network.
"""

import json
import math
import os
import re
import shutil
import sys
import tempfile
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from orvyren.audit import dossier  # noqa: E402
from orvyren.evaluation import loss  # noqa: E402


BUILD_TIME = "2026-01-01T00:00:00Z"
COMMITTED_DOSSIER = os.path.join(_REPO_ROOT, "evidence", "dossier_usdc-2023-03.md")

# Controlled case: 100 USDC protected at the peg, deepest measured print 0.90,
# 20 bp round-trip cost, a 6-day window. Avoided loss = 10 USD, cost = 0.2 USD.
DECISION_FIXTURE = {
    "case": "sensitivity-fixture",
    "window": {"start": "2023-03-09T00:00:00+00:00", "end": "2023-03-15T00:00:00+00:00"},
    "axes": {"x_star_usdc": 100.0},
    "inputs_summary": {
        "peg_reference_usd": 1.0,
        "exposure_parameters": {"action_usdc": 100.0},
        "sources": [
            {"venue": "venue_a", "metric": "close_usd", "min_value": 0.90, "max_value": 1.0},
            {"venue": "venue_a", "metric": "circulating_usd", "min_value": 1_000_000.0},
        ],
    },
    "hypothesis_verdicts": {"H2": {"verdict": "SUPPORTED", "evidence_refs": ["E1"]}},
    "decision": {
        "verdict": "ACTION_RECOMMENDED",
        "action": {"type": "transfer", "asset": "USDC", "amount_usdc": 100.0},
        "rationale": ["fixture"],
        "conditions": [],
        "limits": [],
        "provenance": [],
    },
    "calibration": None,
}


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _sign(value):
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


class TestBreakEvenProbability(unittest.TestCase):
    """P* on known cases and every documented degenerate corner."""

    def test_known_case_loss_1000_cost_100(self):
        self.assertAlmostEqual(loss.break_even_probability(1000.0, 100.0), 100.0 / 1100.0, places=15)
        self.assertAlmostEqual(loss.break_even_probability(1000.0, 100.0), 0.09090909090909091, places=15)

    def test_switch_makes_expected_avoided_loss_zero(self):
        p_star = loss.break_even_probability(1000.0, 100.0)
        reading = loss.dao_expected_avoided_loss(p_star, 1000.0, 100.0)
        self.assertAlmostEqual(reading["expected_avoided_loss_usd"], 0.0, places=9)

    def test_zero_cost_with_positive_loss_breaks_even_at_zero(self):
        # E(p) = p·L is strictly positive for any p > 0: the switch is p = 0.
        self.assertEqual(loss.break_even_probability(1000.0, 0.0), 0.0)

    def test_zero_loss_with_positive_cost_breaks_even_at_one(self):
        # E(p) = -(1 - p)·c is negative below certainty: the switch is p = 1.
        self.assertEqual(loss.break_even_probability(0.0, 100.0), 1.0)

    def test_zero_loss_and_zero_cost_has_no_switch(self):
        # E ≡ 0: every probability is a break-even, so no single value exists.
        self.assertIsNone(loss.break_even_probability(0.0, 0.0))

    def test_negative_avoided_loss_never_breaks_even(self):
        self.assertIsNone(loss.break_even_probability(-1000.0, 100.0))
        self.assertIsNone(loss.break_even_probability(-1000.0, 0.0))

    def test_negative_cost_is_rejected(self):
        with self.assertRaises(loss.ValuationError):
            loss.break_even_probability(1000.0, -1.0)
        with self.assertRaises(loss.ValuationError):
            loss.break_even_probability(1000.0, -1e-12)

    def test_non_finite_arguments_are_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(loss.ValuationError):
                loss.break_even_probability(bad, 10.0)
            with self.assertRaises(loss.ValuationError):
                loss.break_even_probability(10.0, bad)

    def test_break_even_is_inside_unit_interval_for_positive_terms(self):
        p_star = loss.break_even_probability(13.733, 0.2)
        self.assertGreater(p_star, 0.0)
        self.assertLess(p_star, 1.0)


class TestSensitivitySweep(unittest.TestCase):
    """Sign of E[avoided loss] across (P, r_capital) couples."""

    def test_sign_switches_around_p_star(self):
        loss_given, cost = 1000.0, 100.0
        p_star = loss.break_even_probability(loss_given, cost)
        sweep = loss.sensitivity_sweep(
            loss_given, cost, (0.02, p_star / 2.0, p_star, (1.0 + p_star) / 2.0, 0.9),
            r_capital_values=(0.0,), funding_notional_usd=0.0,
        )
        signs = [row["sign"] for row in sweep["rows"]]
        self.assertEqual(signs[0], -1)
        self.assertEqual(signs[1], -1)
        self.assertEqual(signs[2], 0)
        self.assertEqual(signs[3], 1)
        self.assertEqual(signs[4], 1)

    def test_sign_is_monotone_in_p_for_each_variant(self):
        sweep = loss.sensitivity_sweep(
            500.0, 50.0, [i / 100.0 for i in range(0, 61, 5)],
            funding_notional_usd=1000.0, funding_days=30.0,
        )
        for rate in loss.R_CAPITAL_VALUES:
            signs = [row["sign"] for row in sweep["rows"] if row["r_capital"] == rate]
            self.assertEqual(signs, sorted(signs), msg=f"sign not monotone at r_capital={rate}")

    def test_rows_match_the_frozen_formula(self):
        loss_given, cost = 250.0, 40.0
        probabilities = [0.0, 0.05, 0.2, 0.5, 1.0]
        sweep = loss.sensitivity_sweep(
            loss_given, cost, probabilities,
            funding_notional_usd=1000.0, funding_days=12.0,
        )
        self.assertEqual(len(sweep["rows"]), len(probabilities) * 3)
        for row in sweep["rows"]:
            variant = next(v for v in sweep["variants"] if v["r_capital"] == row["r_capital"])
            expected = (
                row["p_obligation"] * loss_given
                - (1.0 - row["p_obligation"]) * variant["total_cost_usd"]
            )
            self.assertAlmostEqual(row["expected_avoided_loss_usd"], expected, places=10)
            self.assertEqual(row["sign"], _sign(expected))
            self.assertEqual(row["sign_text"], {1: "+", 0: "0", -1: "-"}[row["sign"]])

    def test_three_r_capital_variants_publish_funding_and_switch(self):
        notional, days = 100.0, 6.0
        sweep = loss.sensitivity_sweep(
            10.0, 0.2, [0.05, 0.2], funding_notional_usd=notional, funding_days=days,
        )
        self.assertEqual([v["r_capital"] for v in sweep["variants"]], [0.0, 0.05, 0.10])
        previous = None
        for variant in sweep["variants"]:
            expected_funding = notional * variant["r_capital"] * (days / 365.0)
            self.assertAlmostEqual(variant["funding_cost_usd"], expected_funding, places=12)
            self.assertAlmostEqual(variant["total_cost_usd"], 0.2 + expected_funding, places=12)
            self.assertAlmostEqual(
                variant["break_even_probability"],
                loss.break_even_probability(10.0, 0.2 + expected_funding),
                places=12,
            )
            if previous is not None:
                # A larger funding rate can only raise the break-even probability.
                self.assertGreater(variant["break_even_probability"], previous)
            previous = variant["break_even_probability"]

    def test_zero_rate_reproduces_the_signed_reading(self):
        sweep = loss.sensitivity_sweep(
            10.0, 0.2, [0.2], funding_notional_usd=100.0, funding_days=6.0,
        )
        base = sweep["variants"][0]
        self.assertEqual(base["r_capital"], 0.0)
        self.assertEqual(base["funding_cost_usd"], 0.0)
        self.assertEqual(base["total_cost_usd"], 0.2)
        signed = loss.dao_expected_avoided_loss(0.2, 10.0, 0.2)
        self.assertAlmostEqual(
            sweep["rows"][0]["expected_avoided_loss_usd"],
            signed["expected_avoided_loss_usd"],
            places=12,
        )

    def test_nonzero_rate_requires_the_funding_notional(self):
        with self.assertRaises(loss.ValuationError):
            loss.sensitivity_sweep(10.0, 0.2, [0.2])
        # Zero-only rates do not need it (funding is identically zero).
        sweep = loss.sensitivity_sweep(10.0, 0.2, [0.2], r_capital_values=(0.0,))
        self.assertEqual(sweep["variants"][0]["funding_cost_usd"], 0.0)

    def test_out_of_bounds_and_empty_inputs_are_rejected(self):
        for bad_p in (-0.01, 1.01, float("nan")):
            with self.assertRaises(loss.ValuationError):
                loss.sensitivity_sweep(10.0, 0.2, [bad_p], r_capital_values=(0.0,))
        with self.assertRaises(loss.ValuationError):
            loss.sensitivity_sweep(10.0, 0.2, [])
        with self.assertRaises(loss.ValuationError):
            loss.sensitivity_sweep(10.0, 0.2, [0.2], r_capital_values=())
        with self.assertRaises(loss.ValuationError):
            loss.sensitivity_sweep(10.0, 0.2, [0.2], r_capital_values=(-0.05,))
        with self.assertRaises(loss.ValuationError):
            loss.sensitivity_sweep(10.0, -0.2, [0.2], r_capital_values=(0.0,))


class TestFundingCost(unittest.TestCase):
    """``I_avg · r_capital · Δt`` — the term the 5 % / 10 % variants add."""

    def test_known_value(self):
        self.assertAlmostEqual(loss.funding_cost(100.0, 0.10, 365.0), 10.0, places=12)
        self.assertAlmostEqual(loss.funding_cost(100.0, 0.05, 73.0), 1.0, places=12)

    def test_zero_rate_is_zero(self):
        self.assertEqual(loss.funding_cost(1_000_000.0, 0.0, 365.0), 0.0)

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(loss.ValuationError):
            loss.funding_cost(-1.0, 0.05, 1.0)
        with self.assertRaises(loss.ValuationError):
            loss.funding_cost(100.0, -0.05, 1.0)
        with self.assertRaises(loss.ValuationError):
            loss.funding_cost(100.0, 0.05, -1.0)
        with self.assertRaises(loss.ValuationError):
            loss.funding_cost(100.0, 0.05, 1.0, day_basis=0.0)
        with self.assertRaises(loss.ValuationError):
            loss.funding_cost(math.nan, 0.05, 1.0)


class TestDossierSensitivitySection(unittest.TestCase):
    """Publication: section present, table consistent with ``loss.py``."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_sensitivity_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.decision_path = os.path.join(self.tmp, "decision_sensitivity-fixture.json")
        _write_json(self.decision_path, DECISION_FIXTURE)
        self.out_dir = os.path.join(self.tmp, "evidence")

    def _build(self, payload=None):
        if payload is not None:
            _write_json(self.decision_path, payload)
        return dossier.build(self.decision_path, self.out_dir, generated_at=BUILD_TIME)

    @staticmethod
    def _variant_costs(md):
        rows = re.findall(r"^\| ([\d.]+) % \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) % \|$", md, re.MULTILINE)
        return [(float(rate), float(funding), float(total), float(p_star)) for rate, funding, total, p_star in rows]

    @staticmethod
    def _matrix(md):
        rows = re.findall(r"^\| (\d\.\d\d) \| ([-+0]) \| ([-+0]) \| ([-+0]) \|$", md, re.MULTILINE)
        return [(float(p), s0, s5, s10) for p, s0, s5, s10 in rows]

    @staticmethod
    def _terms(md):
        avoided = re.search(r"Avoided loss given obligation:\*\* ([\d.]+) USD", md)
        cost = re.search(r"Round-trip cost:\*\* ([\d.]+) USD", md)
        p_star = re.search(r"Break-even probability \(`P\*`\):\*\* ([\d.]+) %", md)
        return float(avoided.group(1)), float(cost.group(1)), float(p_star.group(1))

    def test_section_is_published_with_both_terms_and_formula(self):
        md = _read_text(self._build()["md_path"])
        self.assertIn("## Sensitivity", md)
        self.assertIn("loss.break_even_probability", md)
        self.assertIn("loss.sensitivity_sweep", md)
        self.assertIn("loss.dao_expected_avoided_loss", md)
        self.assertIn("Avoided loss given obligation", md)
        self.assertIn("Round-trip cost", md)

    def test_terms_match_the_loss_module(self):
        md = _read_text(self._build()["md_path"])
        avoided, cost, p_star_pct = self._terms(md)
        # Independent recomputation from the fixture's measured fields.
        quantity, peg, stress = 100.0, 1.0, 0.90
        keep = loss.evaluate_action(0.0, quantity, 0.0, peg, stress)
        protect = loss.evaluate_action(0.0, quantity, quantity, peg, stress, p_exec=peg, cost=0.0)
        expected_avoided = keep["loss_usd"] - protect["loss_usd"]
        expected_cost = quantity * dossier.ROUNDTRIP_COST_BP / 10_000.0
        self.assertAlmostEqual(avoided, expected_avoided, places=3)
        self.assertAlmostEqual(cost, expected_cost, places=4)
        self.assertAlmostEqual(
            p_star_pct,
            loss.break_even_probability(expected_avoided, expected_cost) * 100.0,
            places=3,
        )

    def test_three_r_capital_variants_are_published(self):
        md = _read_text(self._build()["md_path"])
        costs = self._variant_costs(md)
        self.assertEqual([rate for rate, _, _, _ in costs], [0.0, 5.0, 10.0])
        for rate, funding, total, p_star in costs:
            expected_funding = 100.0 * (rate / 100.0) * (6.0 / 365.0)
            self.assertAlmostEqual(funding, expected_funding, places=3)
            self.assertAlmostEqual(total, 0.2 + expected_funding, places=3)
            self.assertAlmostEqual(
                p_star / 100.0,
                loss.break_even_probability(10.0, 0.2 + expected_funding),
                places=4,
            )

    def test_rendered_table_matches_the_loss_module_row_by_row(self):
        md = _read_text(self._build()["md_path"])
        avoided, _cost, _p_star = self._terms(md)
        costs = [total for _rate, _funding, total, _p in self._variant_costs(md)]
        matrix = self._matrix(md)
        self.assertEqual(len(matrix), len(dossier.SENSITIVITY_P_VALUES))
        for index, (p, *signs) in enumerate(matrix):
            self.assertAlmostEqual(p, dossier.SENSITIVITY_P_VALUES[index], places=6)
            for column, total_cost in enumerate(costs):
                expected = loss.dao_expected_avoided_loss(p, avoided, total_cost)
                self.assertEqual(
                    signs[column],
                    {1: "+", 0: "0", -1: "-"}[_sign(expected["expected_avoided_loss_usd"])],
                    msg=f"sign mismatch at P={p}, r_capital column {column}",
                )
        # The switch is visible: negative at P = 0, positive at the signed 20 %.
        self.assertEqual(matrix[0][1:], ("-", "-", "-"))
        signed_row = next(row for row in matrix if abs(row[0] - dossier.P_OBLIGATION_SIGNED) < 1e-9)
        self.assertEqual(signed_row[1:], ("+", "+", "+"))

    def test_missing_terms_are_reported_never_invented(self):
        payload = dict(DECISION_FIXTURE)
        summary = dict(payload["inputs_summary"])
        summary.pop("peg_reference_usd")
        payload["inputs_summary"] = summary
        md = _read_text(self._build(payload)["md_path"])
        self.assertIn("## Sensitivity", md)
        self.assertIn("Sensitivity unavailable", md)
        self.assertIn("No value is inferred", md)
        self.assertNotIn("Break-even probability", md)

    def test_dossier_stays_deterministic_with_the_section(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(
            _read_text(first["md_path"]),
            _read_text(second["md_path"]),
        )


class TestCommittedDossier(unittest.TestCase):
    """The dossier committed in ``evidence/`` really carries the sensitivity."""

    def test_committed_dossier_publishes_p_star_and_sign_table(self):
        if not os.path.exists(COMMITTED_DOSSIER):
            self.skipTest("committed dossier not built yet")
        md = _read_text(COMMITTED_DOSSIER)
        self.assertIn("## Sensitivity", md)
        self.assertIn("loss.break_even_probability", md)
        self.assertIn("loss.sensitivity_sweep", md)
        avoided = re.search(r"Avoided loss given obligation:\*\* ([\d.]+) USD", md)
        p_star = re.search(r"Break-even probability \(`P\*`\):\*\* ([\d.]+) %", md)
        self.assertIsNotNone(avoided, "the avoided-loss term is not published")
        self.assertIsNotNone(p_star, "P* is not published")
        rows = re.findall(
            r"^\| ([\d.]+) % \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) % \|$", md, re.MULTILINE
        )
        self.assertEqual([float(rate) for rate, _, _, _ in rows], [0.0, 5.0, 10.0])
        matrix = re.findall(
            r"^\| (\d\.\d\d) \| ([-+0]) \| ([-+0]) \| ([-+0]) \|$", md, re.MULTILINE
        )
        self.assertEqual(len(matrix), len(dossier.SENSITIVITY_P_VALUES))
        # Cross-check the artefact against the formula, using only values it
        # publishes itself (no expected value is copied from the document).
        base_cost = float(rows[0][2])
        self.assertAlmostEqual(
            float(p_star.group(1)) / 100.0,
            loss.break_even_probability(float(avoided.group(1)), base_cost),
            places=3,
        )
        for p, *signs in matrix:
            p_value = float(p)
            for column, row in enumerate(rows):
                expected = p_value * float(avoided.group(1)) - (1.0 - p_value) * float(row[2])
                self.assertEqual(
                    signs[column],
                    {1: "+", 0: "0", -1: "-"}[_sign(expected)],
                    msg=f"sign mismatch at P={p}, r_capital column {column}",
                )


if __name__ == "__main__":
    unittest.main()
