#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests des comparateurs G2 : A0, A1, AX0, B0, O (B7 §e.1, W2-D §C.1).

Rappels des contrats testés :

* A0 ne produit **aucune** action ;
* A1 déclenche sur décote ≥ 50 bp soutenue 15 min (deux lectures horaires
  consécutives) et produit une réduction bornée, un seul déclenchement par
  épisode ;
* AX0 **reproduit** `evidence/baseline_report.json` (2 signaux fenêtre
  principale, 0 sur la fenêtre témoin) — délégation, pas réimplémentation ;
* B0 est reproductible (même graine → mêmes horodatages), M ≥ 200 exigé ;
* O est un membre de la famille faisable et minore toutes les pertes.
"""

import json
import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.evaluation import calibration as C  # noqa: E402
from orvyren.evaluation import comparators as K  # noqa: E402
from orvyren.evaluation import loss  # noqa: E402

MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")
CONTROL_WINDOW = ("2023-02-15T00:00:00+00:00", "2023-02-18T00:00:00+00:00")


def hourly_series(prices):
    """Série horaire synthétique ``(timestamp ISO, prix)`` à partir de la 00:00 du 1er mars."""
    import datetime as dt

    start = dt.datetime(2023, 3, 1, tzinfo=dt.timezone.utc)
    return [((start + dt.timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"), price) for i, price in enumerate(prices)]


class TestA0(unittest.TestCase):
    def test_a0_aucune_action(self):
        self.assertEqual(K.a0_actions(), ())
        self.assertEqual(len(K.a0_actions(["peu importe"])), 0)


class TestA1(unittest.TestCase):
    def test_seuil_soutenu_declenche_une_fois(self):
        # décote 60 bp pendant 4 heures d'affilée → UN signal, à la 2e lecture
        series = hourly_series([1.0, 0.994, 0.994, 0.994, 0.994, 1.0])
        fired = K.a1_signal_times(series)
        self.assertEqual(len(fired), 1)
        self.assertEqual(fired[0], "2023-03-01T02:00:00Z")

    def test_sous_le_seuil_ne_declenche_pas(self):
        series = hourly_series([1.0, 0.997, 0.998, 0.999])  # 30 bp max < 50 bp
        self.assertEqual(K.a1_signal_times(series), [])

    def test_trou_horaire_casse_l_episode(self):
        series = [
            ("2023-03-01T00:00:00Z", 0.994),
            ("2023-03-01T03:00:00Z", 0.994),  # trou de 3 h : pas de contiguïté
        ]
        self.assertEqual(K.a1_signal_times(series), [])

    def test_action_bornee_et_notes_de_substitution(self):
        series = hourly_series([1.0, 0.994, 0.994, 1.0])
        actions = K.a1_actions(series)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["amount_usdc"], K.X_MAX_USDC_DEMO)
        self.assertIn("Depth_ε", " ".join(actions[0]["notes"]))
        capped = K.a1_actions(series, x_max=100.0, depth_epsilon=40.0, x_seuil=70.0)
        self.assertEqual(capped[0]["amount_usdc"], 40.0)


class TestAX0(unittest.TestCase):
    """AX0 doit reproduire baseline_report.json — délégation à decision/baseline.py."""

    def test_deux_signaux_principaux_zero_temoin(self):
        report_path = os.path.join(REPO_ROOT, "evidence", "baseline_report.json")
        with open(report_path, "r", encoding="utf-8") as handle:
            reference = json.load(handle)
        main = K.ax0_signals(os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv"), MAIN_WINDOW)
        control = K.ax0_signals(os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv"), CONTROL_WINDOW)
        self.assertEqual(len(main), len(reference["signals_main"]))
        self.assertEqual(len(main), 2)
        self.assertEqual(len(control), reference["false_signals_control"])
        self.assertEqual(len(control), 0)
        self.assertEqual(
            [signal["triggered_at_utc"] for signal in main],
            [signal["triggered_at_utc"] for signal in reference["signals_main"]],
        )

    def test_ax0_actions_avec_reduction_100(self):
        actions = K.ax0_actions(os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv"), MAIN_WINDOW)
        self.assertEqual(len(actions), 2)
        for action in actions:
            self.assertEqual(action["amount_usdc"], 100.0)
            self.assertEqual(action["rule"], "ax0_baseline_gelee")


class TestB0(unittest.TestCase):
    def test_reproductible_meme_graine(self):
        sizes = [100.0, 100.0, 50.0]
        first = K.b0_draws(3, sizes, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=200, seed=7)
        second = K.b0_draws(3, sizes, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=200, seed=7)
        self.assertEqual(first, second)

    def test_graine_differente_distribution_differente(self):
        sizes = [100.0, 100.0]
        first = K.b0_draws(2, sizes, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=200, seed=1)
        second = K.b0_draws(2, sizes, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=200, seed=2)
        self.assertNotEqual(first, second)

    def test_appariement_memes_nombre_et_tailles(self):
        sizes = [100.0, 40.0, 10.0]
        draws = K.b0_draws(3, sizes, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=200)
        for draw in draws:
            self.assertEqual(len(draw), 3)
            self.assertEqual(sorted(action["amount_usdc"] for action in draw), sorted(sizes))
            for action in draw:
                self.assertGreaterEqual(action["triggered_at_utc"], "2023-03-10T00:00:00Z")
                self.assertLess(action["triggered_at_utc"], "2023-03-14T00:00:00Z")

    def test_m_inferieur_a_200_refuse(self):
        with self.assertRaises(K.ComparatorError):
            K.b0_draws(1, [100.0], "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z", draws=199)
        with self.assertRaises(K.ComparatorError):
            K.b0_draws(2, [100.0], "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z")

    def test_distribution_complete_publiee(self):
        draws = K.b0_draws(1, [100.0], "2023-03-10T00:00:00Z", "2023-03-11T00:00:00Z", draws=200)
        distribution = K.b0_regret_distribution(draws, lambda actions: float(len(actions)))
        self.assertEqual(distribution["m"], 200)
        self.assertEqual(distribution["mean"], 1.0)
        self.assertEqual(len(distribution["values"]), 200)
        percentile = C.bootstrap_percentile(distribution["values"], 1.0)
        self.assertEqual(percentile, 100.0)


class TestOracle(unittest.TestCase):
    def test_oracle_faisable_minore(self):
        table = loss.regret_table(0.0, 100.0, 1.0, 0.90, lambda x: 1.00, cost=0.0)
        losses = [row["loss_usd"] for row in table["actions"]]
        oracle = K.oracle_min_loss(losses)
        self.assertEqual(oracle, min(losses))
        self.assertEqual(oracle, 0.0)  # la vente à 1,00 est faisable
        with self.assertRaises(loss.ValuationError):
            K.oracle_min_loss([])


if __name__ == "__main__":
    unittest.main()
