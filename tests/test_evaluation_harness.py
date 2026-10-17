#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests du harnais d'évaluation (W7, B7 §e ; [DONE] W7).

Couverture :

* run **DEV USDC complet hors-ligne** : 4 fenêtres, 0 sautée, schéma conforme ;
* déterminisme : deux exécutions ⇒ même ``content_hash`` ;
* ``A0 = 0 action`` : perte A0 = q·(1 − P_T) par fenêtre ;
* ``AX0`` reproduit ``baseline_report.json`` (2 signaux main, 0 contrôle) ;
* porte de gel : refus sans ``frozen/G1–G6`` ; refus de la 2ᵉ exécution EVAL
  sans ``--force`` ; refus si une fenêtre CALME EVAL chevauche la période de
  calibration (monkeypatch d'une fenêtre synthétique) ;
* mapping A2 du dossier déterministe (montant + horodatage déclaré).

Run: python -m pytest tests/test_evaluation_harness.py -q
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.evaluation import comparators as comparators_mod  # noqa: E402
from orvyren.evaluation import harness  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402

DECISION = os.path.join(ROOT, "evidence", "decision_usdc-2023-03.json")
BASELINE = os.path.join(ROOT, "evidence", "baseline_report.json")
CORPUS_CSV = os.path.join(ROOT, "corpus", "usdc_observations.csv")


class HarnessDevTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = harness.run_set("dev")
        cls.content = cls.result["content"]

    def test_dev_run_shape(self):
        content = self.content
        self.assertEqual(content["banner"], "DEV")
        self.assertEqual(content["n_windows"], 4)
        self.assertEqual(content["n_windows_skipped"], 0)
        self.assertIn("non conclusionnel", content["validity"])
        for label in ("A0", "A1"):
            self.assertIn(label, content["aggregates"])
            self.assertEqual(content["aggregates"][label]["n"], 4)
        self.assertEqual(content["schema"], "orvyren.evaluation-report/v1")

    def test_a0_is_zero_action(self):
        for detail in self.result["window_details"]:
            self.assertEqual(detail["configs"]["A0"]["actions"], [])
            expected = harness.Q_DEV_USDC * (1.0 - detail["p_terminal"])
            self.assertAlmostEqual(detail["configs"]["A0"]["loss"], expected, delta=1e-9)

    def test_determinism_two_runs_same_content_hash(self):
        second = harness.run_set("dev")
        self.assertEqual(harness.content_hash(self.content),
                         harness.content_hash(second["content"]))

    def test_freeze_gate_refuses_without_frozen(self):
        empty = tempfile.mkdtemp(prefix="orvyren_nofrozen_")
        self.addCleanup(shutil.rmtree, empty, True)
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.run_set("dev", frozen_dir=empty)

    def test_eval_lock_refuses_second_run(self):
        lock = os.path.join(tempfile.mkdtemp(prefix="orvyren_lock_"), "eval_run.lock")
        with open(lock, "w", encoding="utf-8") as handle:
            handle.write("# déjà exécuté\n")
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.run_set("eval", lock_path=lock, force=False)

    def test_cross_calibration_refusal_mechanism(self):
        from unittest import mock

        synthetic = windows_mod.Window(
            window_id="eval-calme-synthetique", episode_id="calme-test",
            set_label="eval", kind="calme",
            start_utc="2025-01-05T00:00:00Z", end_utc="2025-01-20T00:00:00Z",
            sources=("inexistant.json",), role="fenêtre de test (jamais utilisée en run réel)")
        with mock.patch.object(windows_mod, "EVAL_WINDOWS", (synthetic,)):
            with self.assertRaises(harness.HarnessError):
                harness.run_set("eval", calibration_periods=["2025-01"], lock_path=None)

    def test_a2_mapping_from_dossier(self):
        actions, notes = harness.a2_actions_from_dossier(DECISION)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["rule"], "a2_dossier_deterministe")
        self.assertEqual(action["amount_usdc"], 100.0)
        with open(DECISION, "r", encoding="utf-8") as handle:
            dossier = json.load(handle)
        stamps = [item["timestamp_utc"] for item in dossier["decision"]["provenance"]]
        self.assertEqual(action["triggered_at_utc"], max(stamps))
        self.assertGreaterEqual(len(notes), 2)

    def test_ax0_reproduces_baseline_report(self):
        with open(BASELINE, "r", encoding="utf-8") as handle:
            baseline = json.load(handle)
        with open(DECISION, "r", encoding="utf-8") as handle:
            dossier = json.load(handle)
        main = dossier["window"]
        main_signals = comparators_mod.ax0_signals(CORPUS_CSV, (main["start"], main["end"]))
        self.assertEqual(len(main_signals), len(baseline["signals_main"]))
        control_signals = comparators_mod.ax0_signals(
            CORPUS_CSV, ("2023-02-15T00:00:00+00:00", "2023-02-18T00:00:00+00:00"))
        self.assertEqual(len(control_signals), baseline["false_signals_control"])

    def test_b0_seed_reproducible(self):
        sizes = [100.0]
        first = comparators_mod.b0_draws(1, sizes, "2023-03-10T00:00:00Z",
                                         "2023-03-14T00:00:00Z", draws=200)
        second = comparators_mod.b0_draws(1, sizes, "2023-03-10T00:00:00Z",
                                          "2023-03-14T00:00:00Z", draws=200)
        self.assertEqual(first, second)
        other = comparators_mod.b0_draws(1, sizes, "2023-03-10T00:00:00Z",
                                         "2023-03-14T00:00:00Z", draws=200, seed=1)
        self.assertNotEqual(first, other)


if __name__ == "__main__":
    unittest.main()
