#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — regression tests for the 2026-10-17 evaluation/quality review.

Each test pins one fixed finding (see
D:/orvyren_10h_2026-10-17/review/evaluation_quality.md). Stdlib only.

Run: python -m pytest tests/test_evaluation_review.py -q
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from orvyren.evaluation import harness  # noqa: E402
from orvyren.quality import checks, normalize  # noqa: E402

HEADER = "timestamp_utc,venue,metric,value,extra,retrieved_at\n"


def _load_rows(body: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "synthetic.csv")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(HEADER + body)
        return normalize.load_observations(path)


class TestNonFiniteValuesRejected(unittest.TestCase):
    """Finding 1 — nan/inf rows are REJECTED, never kept as observations."""

    def test_non_finite_values_rejected(self):
        observations, report = _load_rows(
            "2023-03-09T00:00:00+00:00,defillama,price_usd,nan,,2026-10-14T12:00:00+00:00\n"
            "2023-03-09T01:00:00+00:00,defillama,price_usd,inf,,2026-10-14T12:00:01+00:00\n"
            "2023-03-09T02:00:00+00:00,defillama,price_usd,-inf,,2026-10-14T12:00:02+00:00\n"
            "2023-03-09T03:00:00+00:00,defillama,price_usd,1.0,,2026-10-14T12:00:03+00:00\n"
        )
        self.assertEqual(len(observations), 1, "only the finite row is kept")
        self.assertEqual(observations[0].value, 1.0)
        self.assertEqual(report["total"], 4)
        self.assertEqual(report["kept"], 1)
        self.assertEqual(len(report["rejected"]), 3)
        reasons = {item["reason"] for item in report["rejected"]}
        self.assertEqual(reasons, {"non_finite_value:nan", "non_finite_value:inf",
                                   "non_finite_value:-inf"})
        # a nan price must not be kept *and* flagged as price-range any more
        self.assertEqual(report["flagged"], [])

    def test_total_still_balances(self):
        _, report = _load_rows(
            "2023-03-09T00:00:00+00:00,defillama,price_usd,NaN,,2026-10-14T12:00:00+00:00\n"
        )
        self.assertEqual(report["total"], report["kept"] + len(report["rejected"]))


class TestHourFloorNaiveIsUtc(unittest.TestCase):
    """Finding 2 — a naive timestamp is read as UTC, never as local wall time."""

    def test_hour_floor_naive_is_utc(self):
        naive = datetime(2023, 3, 9, 5, 30, 15)
        aware = datetime(2023, 3, 9, 5, 30, 15, tzinfo=timezone.utc)
        self.assertEqual(checks.hour_floor(naive), checks.hour_floor(aware))
        self.assertEqual(checks.hour_floor(naive),
                         datetime(2023, 3, 9, 5, 0, tzinfo=timezone.utc))

    def test_hour_floor_offset_aware_still_converted(self):
        # Offset à demi-heure : l'assertion est discriminante. Arrondir dans le
        # fuseau local donnerait 01:30 UTC, convertir d'abord donne 02:00 UTC —
        # avec un offset entier les deux coïncidaient (identité tautologique).
        offset = datetime(2023, 3, 9, 7, 45,
                          tzinfo=timezone(timedelta(hours=5, minutes=30)))
        floored = checks.hour_floor(offset)
        self.assertEqual(floored, datetime(2023, 3, 9, 2, 0, tzinfo=timezone.utc))
        self.assertEqual(floored.utcoffset(), timedelta(0))  # normalisé en UTC


class TestB0QuantileConvention(unittest.TestCase):
    """Finding 4 — p05/p50/p95 share one rank convention: int(p*m)-1 (clamped)."""

    def test_p95_rank_is_not_one_toohigh(self):
        ordered = [float(i) for i in range(20)]
        quantiles = harness._b0_quantiles(ordered)
        self.assertEqual(quantiles["p05"], 0.0)    # rank int(1.0)-1 = 0
        self.assertEqual(quantiles["p50"], 9.0)    # rank int(10.0)-1 = 9
        self.assertEqual(quantiles["p95"], 18.0)   # rank int(19.0)-1 = 18 (was 19)
        self.assertLess(quantiles["p95"], ordered[-1])

    def test_small_samples_clamp_without_crash(self):
        for m in (1, 2, 3, 20, 100):
            ordered = [float(i) for i in range(m)]
            quantiles = harness._b0_quantiles(ordered)
            self.assertEqual(set(quantiles), {"p05", "p50", "p95"})
            self.assertTrue(0.0 <= quantiles["p05"] <= quantiles["p50"]
                            <= quantiles["p95"] <= ordered[-1])


class TestUndatedActionRefused(unittest.TestCase):
    """Finding 5 — an action without triggered_at_utc raises, never invents P_exec."""

    def test_missing_timestamp_raises_harness_error(self):
        points = [("2023-03-09T00:00:00+00:00", 1.0), ("2023-03-09T05:00:00+00:00", 0.9)]
        with self.assertRaises(harness.HarnessError):
            harness.loss_for_actions([{"amount_usdc": 10.0}], points, p_terminal=0.9)

    def test_dated_action_still_computes(self):
        points = [("2023-03-09T00:00:00+00:00", 1.0), ("2023-03-09T05:00:00+00:00", 0.9)]
        result = harness.loss_for_actions(
            [{"amount_usdc": 10.0, "triggered_at_utc": "2023-03-09T00:00:00+00:00"}],
            points, p_terminal=0.9)
        self.assertEqual(result["sold"], 10.0)
        self.assertEqual(result["wealth_terminal"], 10.0 * 1.0 + 90.0 * 0.9)


if __name__ == "__main__":
    unittest.main()
