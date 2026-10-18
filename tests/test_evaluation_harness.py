#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — evaluation harness tests (W7, B7 §e; [DONE] W7).

Coverage:

* complete **DEV USDC run offline**: 4 windows, 0 skipped, schema compliant;
* determinism: two executions ⇒ same ``content_hash``;
* ``A0 = 0 action``: A0 loss = q·(1 − P_T) per window;
* ``AX0`` reproduces ``baseline_report.json`` (2 main signals, 0 control);
* freeze gate: refusal without ``frozen/G1–G6``; refusal of the 2nd EVAL
  execution without ``--force``; refusal if a CALM EVAL window overlaps the
  calibration period (monkeypatch of a synthetic window);
* A2 mapping from the deterministic dossier (amount + declared timestamp).

Run: python -m pytest tests/test_evaluation_harness.py -q
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.evaluation import comparators as comparators_mod  # noqa: E402
from orvyren.evaluation import harness  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402

DECISION = os.path.join(ROOT, "evidence", "decision_usdc-2023-03.json")
BASELINE = os.path.join(ROOT, "evidence", "baseline_report.json")
CORPUS_CSV = os.path.join(ROOT, "corpus", "usdc_observations.csv")

#: Threshold-calibration months declared by the DEV harness runs (mandatory
#: cross-calibration embargo, B7 §d.2.4).
DEV_PERIODS = ["2023-02", "2023-03"]


class HarnessDevTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = harness.run_set("dev", calibration_periods=DEV_PERIODS)
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
        second = harness.run_set("dev", calibration_periods=DEV_PERIODS)
        self.assertEqual(harness.content_hash(self.content),
                         harness.content_hash(second["content"]))

    def test_skipped_window_is_rendered_without_configs(self):
        """A skipped EVAL window has no ``configs``; report content must survive."""
        ok_detail = {"window_id": "ok", "status": "OK", "notes": [],
                     "configs": {label: {"loss": 1.0, "regret": {"R": 0.0}}
                                 for label in harness.CONFIG_LABELS}}
        skipped_detail = {"window_id": "skip", "status": "SKIPPED",
                          "reason": "no series", "notes": []}
        with mock.patch.object(harness, "runs_for_set", return_value=[object(), object()]), \
                mock.patch.object(harness, "run_window",
                                  side_effect=[ok_detail, skipped_detail]), \
                mock.patch.object(windows_mod, "verify_frozen_package",
                                  return_value={"G1": "x"}):
            result = harness.run_set("dev", b0_draws=1, calibration_periods=DEV_PERIODS)
        content = result["content"]
        self.assertEqual(1, content["n_windows"])
        self.assertEqual(1, content["n_windows_skipped"])
        self.assertEqual({}, content["windows"][1]["config_losses"])
        self.assertEqual({}, content["windows"][1]["config_regrets"])

    def test_freeze_gate_refuses_without_frozen(self):
        empty = tempfile.mkdtemp(prefix="orvyren_nofrozen_")
        self.addCleanup(shutil.rmtree, empty, True)
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.run_set("dev", frozen_dir=empty)

    def test_eval_lock_refuses_second_run(self):
        lock_dir = tempfile.mkdtemp(prefix="orvyren_lock_")
        self.addCleanup(shutil.rmtree, lock_dir, True)
        lock = os.path.join(lock_dir, "eval_run.lock")
        with open(lock, "w", encoding="utf-8") as handle:
            handle.write("# already executed\n")
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.run_set("eval", lock_path=lock, force=False)

    def test_cross_calibration_refusal_mechanism(self):
        from unittest import mock

        synthetic = windows_mod.Window(
            window_id="eval-calme-synthetique", episode_id="calme-test",
            set_label="eval", kind="calme",
            start_utc="2025-01-05T00:00:00Z", end_utc="2025-01-20T00:00:00Z",
            sources=("inexistant.json",), role="test window (never used in a real run)")
        lock_dir = tempfile.mkdtemp(prefix="orvyren_xcal_")
        self.addCleanup(shutil.rmtree, lock_dir, True)
        lock = os.path.join(lock_dir, "absent.lock")
        with mock.patch.object(windows_mod, "EVAL_WINDOWS", (synthetic,)):
            with self.assertRaises(harness.HarnessError) as caught:
                harness.run_set("eval", calibration_periods=["2025-01"], lock_path=lock)
        self.assertIn("overlap", str(caught.exception))

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
