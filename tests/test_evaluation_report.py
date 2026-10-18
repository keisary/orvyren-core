#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — report rendering + calibration regression tests (W7, B7 §e.5).

Coverage:

* **mandatory banner**: no banner / no N / no validity ⇒ refusal to render
  (any output without a banner is a bug);
* rendering: files written, first line = banner, ``N`` displayed, content hash
  stable across two renders;
* append-only ``variants.log`` (failures included);
* W7 fix regression: the **exact** Murphy identity includes the within-bin
  term on the real DEV vector (and stays exact on the KAT, zero term).

Run: python -m pytest tests/test_evaluation_report.py -q
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

from orvyren.evaluation import calibration as calibration_mod  # noqa: E402
from orvyren.evaluation import report as report_mod  # noqa: E402

FORECASTS = os.path.join(ROOT, "frozen", "forecasts_dev.jsonl")
OUTCOMES = os.path.join(ROOT, "frozen", "outcomes_dev.jsonl")


def _minimal_content(**overrides):
    content = {"schema": "orvyren.evaluation-report/v1", "banner": "DEV", "set": "dev",
               "n_windows": 1, "n_windows_skipped": 0,
               "validity": "non conclusionnel : N < 100 (cascade B7 §b.3)",
               "windows": [], "aggregates": {}, "superiority": {"status": "NON CALCULÉ"},
               "params": {"q": 100.0, "p_ref": 1.0, "k": 0.0, "b0_draws": 200, "note": "test"}}
    content.update(overrides)
    return content


class EvaluationReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_report_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_banner_mandatory(self):
        self.assertEqual(report_mod.require_banner("DEV"), "DEV")
        self.assertEqual(report_mod.require_banner("EVAL"), "EVAL")
        self.assertEqual(report_mod.require_banner("REPLAY-JOURNAL"), "REPLAY-JOURNAL")
        for bad in (None, "", "PROD", "dev"):
            with self.assertRaises(report_mod.ReportError):
                report_mod.require_banner(bad)

    def test_render_refuses_without_banner_or_n(self):
        with self.assertRaises(report_mod.ReportError):
            report_mod.render_evaluation_report(content=_minimal_content(banner="NOPE"),
                                                out_dir=self.tmp)
        with self.assertRaises(report_mod.ReportError):
            report_mod.render_evaluation_report(content=_minimal_content(n_windows=None),
                                                out_dir=self.tmp)
        with self.assertRaises(report_mod.ReportError):
            report_mod.render_evaluation_report(content=_minimal_content(validity=""),
                                                out_dir=self.tmp)

    def test_render_writes_banner_and_n(self):
        paths = report_mod.render_evaluation_report(content=_minimal_content(),
                                                    out_dir=self.tmp)
        self.assertTrue(os.path.isfile(paths["json_path"]))
        with open(paths["md_path"], "r", encoding="utf-8") as handle:
            first_line = handle.readline()
        self.assertTrue(first_line.startswith("> **DEV**"), first_line)
        self.assertIn("N = 1", first_line)
        second = report_mod.render_evaluation_report(content=_minimal_content(),
                                                     out_dir=self.tmp)
        self.assertEqual(paths["content_sha256"], second["content_sha256"])

    def test_variants_log_appends_failures(self):
        log = os.path.join(self.tmp, "variants.log")
        report_mod.append_variants_log(log, {"set": "dev", "result": "REFUSED",
                                             "reason": "freeze absent"})
        report_mod.append_variants_log(log, {"set": "dev", "result": "OK", "n_windows": 4})
        with open(log, "r", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual([entry["result"] for entry in lines], ["REFUSED", "OK"])

    def test_side_files_written(self):
        side = report_mod.write_side_files(content=_minimal_content(),
                                           window_details=[], out_dir=self.tmp)
        for path in side.values():
            self.assertTrue(os.path.isfile(path))


@unittest.skipUnless(os.path.isfile(FORECASTS) and os.path.isfile(OUTCOMES),
                     "DEV freeze absent")
class MurphyWithinBinRegressionTest(unittest.TestCase):
    def test_real_dev_vector_exact_identity(self):
        with open(FORECASTS, encoding="utf-8") as handle:
            forecasts = [json.loads(line) for line in handle if line.strip()]
        with open(OUTCOMES, encoding="utf-8") as handle:
            outcomes = {json.loads(line)["forecast_id"]: json.loads(line)
                        for line in handle if line.strip()}
        p = [record["p"] for record in forecasts]
        y = [outcomes[record["forecast_id"]]["y"] for record in forecasts]
        decomposition = calibration_mod.murphy_decomposition(p, y)
        self.assertLess(abs(decomposition["exact_identity"] - decomposition["bs"]), 1e-9)
        # p is NOT constant per bin on the real vector: the term exists.
        self.assertGreater(abs(decomposition["within_bin_term"]), 1e-6)

    def test_kat_still_exact_with_zero_within_term(self):
        decomposition = calibration_mod.murphy_decomposition(
            [0.2] * 5 + [0.8] * 5, [0, 0, 0, 0, 0, 1, 1, 0, 1, 1])
        self.assertAlmostEqual(decomposition["bs"], 0.10, delta=1e-12)
        self.assertAlmostEqual(decomposition["within_bin_term"], 0.0, delta=1e-12)
        self.assertAlmostEqual(decomposition["rel"], 0.02, delta=1e-12)
        self.assertAlmostEqual(decomposition["res"], 0.16, delta=1e-12)
        self.assertAlmostEqual(decomposition["unc"], 0.24, delta=1e-12)


if __name__ == "__main__":
    unittest.main()
