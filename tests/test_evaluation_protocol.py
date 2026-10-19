#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests — 2026-10-18 evaluation-protocol review findings.

One class per finding:

* **F1** — the G5 §b.3 cascade is applied to the **content actually computed**
  (bootstrap CI / ECE / BSS published per N evaluated items), never to the
  result label alone; the verdict label follows the content;
* **F2** — the freeze gate really verifies the code hashes **announced inside
  the Gx documents** against the working tree;
* **F3** — the cross-calibration embargo is **mandatory**: an omitted
  ``--calibration-periods`` is an explicit refusal, never a silent skip.

Run: python -m unittest tests.test_evaluation_protocol
"""

import importlib.util
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

from orvyren.evaluation import calibration as calibration_mod  # noqa: E402
from orvyren.evaluation import harness  # noqa: E402
from orvyren.evaluation import report as report_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402

FORECASTS = os.path.join(ROOT, "frozen", "forecasts_dev.jsonl")
OUTCOMES = os.path.join(ROOT, "frozen", "outcomes_dev.jsonl")
FROZEN_DIR = os.path.join(ROOT, "frozen")
DEV_PERIODS = ["2023-02", "2023-03"]

P_KAT = [0.2] * 5 + [0.8] * 5
Y_KAT = [0, 0, 0, 0, 0, 1, 1, 0, 1, 1]


def _load_cli(filename):
    spec = importlib.util.spec_from_file_location(
        os.path.splitext(filename)[0], os.path.join(ROOT, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_computed(n, verdict):
    """Shape of ``calibration_mod.calibration_report`` for cascade tests."""
    return {"n": n, "ybar": 0.4, "bs": 0.1, "rel": 0.02, "res": 0.16, "unc": 0.24,
            "ece": 0.1, "bss": 1.0 - 0.1 / 0.24,
            "bs_bootstrap_ci": [0.05, 0.15],
            "reliability": [{"bin": 2, "n_b": 5, "conf_b": 0.2, "acc_b": 0.0},
                            {"bin": 8, "n_b": 5, "conf_b": 0.8, "acc_b": 0.8}],
            "verdict": verdict, "bins": 10,
            "bootstrap": {"block_size": 6, "n_reps": 10000, "seed": 20261016}}


def _fake_window_detail(window_id, losses):
    configs = {}
    for label in harness.CONFIG_LABELS:
        if label in losses:
            configs[label] = {"loss": losses[label], "regret": {"R": 0.0}}
        else:
            configs[label] = {"actions": None, "status": "DECLARED"}
    return {"window_id": window_id, "status": "OK", "notes": [], "configs": configs}


def _fake_freeze_package(root, docs):
    """``frozen/Gx.sha256``-shaped package in ``root/frozen`` (self-consistent)."""
    frozen = os.path.join(root, "frozen")
    os.makedirs(frozen, exist_ok=True)
    for name in windows_mod.FROZEN_FILES:
        document = os.path.join(frozen, "%s_doc.md" % name)
        with open(document, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(docs.get(name, "# %s\n" % name))
        with open(os.path.join(frozen, "%s.sha256" % name), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write("%s  %s\n" % (windows_mod.sha256_file(document),
                                       os.path.basename(document)))
    return frozen


class TestF1CascadeOnContent(unittest.TestCase):
    """F1 — G5 §b.3 cascade gates the computed content, not the label."""

    def test_cascade_gate_boundaries(self):
        for n in (0, 4):
            gate = report_mod.cascade_gate(n)
            self.assertEqual(gate["tier"], report_mod.CASCADE_TIER_NOT_COMPUTED)
            self.assertEqual(gate["label"], calibration_mod.VERDICT_NOT_COMPUTED)
            self.assertFalse(any(gate["publish"].values()))
        for n in (5, 29):
            gate = report_mod.cascade_gate(n)
            self.assertEqual(gate["tier"], report_mod.CASCADE_TIER_BASE)
            self.assertEqual(gate["label"], calibration_mod.VERDICT_NON_CONCLUSIVE)
            self.assertTrue(gate["publish"]["base"])
            self.assertFalse(gate["publish"]["bootstrap_ci"])
            self.assertFalse(gate["publish"]["reliability_wilson"])
            self.assertFalse(gate["publish"]["bss"])
            self.assertFalse(gate["publish"]["ece_claimable"])
        for n in (30, 99):
            gate = report_mod.cascade_gate(n)
            self.assertEqual(gate["tier"], report_mod.CASCADE_TIER_CI)
            self.assertTrue(gate["publish"]["bootstrap_ci"])
            self.assertTrue(gate["publish"]["reliability_wilson"])
            self.assertFalse(gate["publish"]["bss"])
            self.assertFalse(gate["publish"]["ece_claimable"])
        gate = report_mod.cascade_gate(100)
        self.assertEqual(gate["tier"], report_mod.CASCADE_TIER_CLAIM)
        self.assertEqual(gate["label"], calibration_mod.VERDICT_CLAIM_POSSIBLE)
        self.assertTrue(gate["publish"]["bootstrap_ci"])
        self.assertTrue(gate["publish"]["bss"])
        self.assertTrue(gate["publish"]["ece_claimable"])

    def test_base_tier_publishes_no_bootstrap_ci_nor_bss(self):
        published = report_mod.apply_cascade(
            _fake_computed(10, calibration_mod.VERDICT_NON_CONCLUSIVE), 10)
        self.assertIn("bs", published)
        self.assertIn("ece", published)
        self.assertFalse(published["ece_claimable"])
        self.assertIn("ece_claim_note", published)
        self.assertNotIn("bs_bootstrap_ci", published)
        self.assertNotIn("bootstrap", published)
        self.assertNotIn("bss", published)
        self.assertNotIn("bss_ci", published)

    def test_ci_tier_publishes_bootstrap_ci_still_no_bss(self):
        published = report_mod.apply_cascade(
            _fake_computed(35, calibration_mod.VERDICT_NON_CONCLUSIVE), 35)
        self.assertEqual(published["bs_bootstrap_ci"], [0.05, 0.15])
        self.assertIn("bootstrap", published)
        self.assertNotIn("bss", published)
        self.assertFalse(published["ece_claimable"])

    def test_claim_tier_publishes_bss_with_lower_bound_and_conditions(self):
        published = report_mod.apply_cascade(
            _fake_computed(120, calibration_mod.VERDICT_CLAIM_POSSIBLE), 120,
            families=("ep-a", "ep-b"))
        self.assertTrue(published["ece_claimable"])
        self.assertAlmostEqual(published["bss"], 1.0 - 0.1 / 0.24, delta=1e-12)
        clim = 0.4 * 0.6
        self.assertAlmostEqual(published["bss_ci"][0], 1.0 - 0.15 / clim, delta=1e-12)
        self.assertAlmostEqual(published["bss_ci"][1], 1.0 - 0.05 / clim, delta=1e-12)
        self.assertGreater(published["bss_ci"][0], published["bss_ci"][1] - 1.0)
        conditions = published["claim_conditions"]
        self.assertEqual(len(conditions), 5)
        by_id = {item["id"]: item for item in conditions}
        # fake content: max bin gap = |0.0 − 0.2| = 0.2 > 0.10 → condition 3 fails
        self.assertAlmostEqual(by_id[3]["computed"], 0.2, delta=1e-12)
        self.assertFalse(by_id[3]["ok"])
        self.assertTrue(by_id[1]["ok"])    # N = 120 ≥ 100
        self.assertTrue(by_id[4]["ok"])    # BSS CI lower bound > 0
        self.assertTrue(by_id[5]["ok"])    # 2 disjoint families
        # « calibré » is a controlled word: never emitted by the code.
        self.assertNotIn("calibré", json.dumps(published, ensure_ascii=False))

    def test_label_content_divergence_is_refused(self):
        with self.assertRaises(report_mod.ReportError):
            report_mod.apply_cascade(
                _fake_computed(9, calibration_mod.VERDICT_NON_CONCLUSIVE), 10)
        with self.assertRaises(report_mod.ReportError):
            report_mod.apply_cascade(_fake_computed(10, "calibré"), 10)
        with self.assertRaises(report_mod.ReportError):
            report_mod.apply_cascade(None, 10)

    def test_nothing_published_below_5(self):
        published = report_mod.apply_cascade(None, 3)
        self.assertEqual(published["verdict"], calibration_mod.VERDICT_NOT_COMPUTED)
        for key in ("bs", "rel", "res", "unc", "ece", "bss", "bs_bootstrap_ci"):
            self.assertNotIn(key, published)

    def test_real_kat_report_goes_through_cascade(self):
        computed = calibration_mod.calibration_report(P_KAT, Y_KAT)  # N = 10
        published = report_mod.apply_cascade(computed, 10, families=("kat",))
        self.assertEqual(published["verdict"], computed["verdict"])
        self.assertNotIn("bs_bootstrap_ci", published)  # 10 < 30
        self.assertNotIn("bss", published)              # 10 < 100


class TestF1BisSuperiorityContent(unittest.TestCase):
    """F1 — the harness superiority status follows the computed content."""

    def test_not_computed_below_100(self):
        details = [_fake_window_detail("w%d" % i, {"A0": 1.0, "A2": 0.5})
                   for i in range(4)]
        block = harness.paired_superiority(details, bootstrap_reps=100)
        self.assertIn("NOT COMPUTED", block["status"])
        self.assertIsNone(block["tests"])
        self.assertIsNone(block["mcnemar"])

    def test_computed_at_100_with_real_tests(self):
        details = [_fake_window_detail("w%d" % i,
                                       {"A0": 1.0, "A2": 0.5 if i % 2 else 1.5})
                   for i in range(100)]
        block = harness.paired_superiority(details, bootstrap_reps=200)
        self.assertTrue(block["status"].startswith("COMPUTED"), block["status"])
        self.assertIn("A0_vs_A2", block["tests"])
        entry = block["tests"]["A0_vs_A2"]
        self.assertEqual(entry["n_paired"], 100)
        self.assertEqual(entry["wins_first"] + entry["wins_second"] + entry["ties"], 100)
        self.assertAlmostEqual(entry["mcnemar_exact_p"], 1.0, delta=1e-12)
        low, high = entry["wilson_win_share_first"]
        self.assertTrue(0.0 <= low <= high <= 1.0)
        ci = entry["paired_loss_diff_bootstrap"]
        self.assertLessEqual(ci["ci_low"], ci["mean"])
        self.assertLessEqual(ci["mean"], ci["ci_high"])
        self.assertEqual(block["mcnemar"]["A0_vs_A2"], entry["mcnemar_exact_p"])

    def test_label_never_claims_calculated_without_content(self):
        details = [_fake_window_detail("w%d" % i, {}) for i in range(100)]
        block = harness.paired_superiority(details, bootstrap_reps=50)
        self.assertFalse(block["status"].startswith("COMPUTED"))
        self.assertIsNone(block["tests"])

    def test_run_set_label_follows_content_end_to_end(self):
        details = [_fake_window_detail("w%d" % i, {"A0": 1.0, "A2": 0.5})
                   for i in range(100)]
        with mock.patch.object(harness, "runs_for_set", return_value=[object()] * 100), \
                mock.patch.object(harness, "run_window", side_effect=list(details)):
            result = harness.run_set("dev", b0_draws=1, calibration_periods=DEV_PERIODS)
        superiority = result["content"]["superiority"]
        self.assertEqual(result["content"]["n_windows"], 100)
        self.assertTrue(superiority["status"].startswith("COMPUTED"))
        self.assertTrue(superiority["tests"])
        self.assertEqual(result["content"]["validity"],
                         "N ≥ 100 — claim possible under conditions")


class TestF2FreezeGateCodeHashes(unittest.TestCase):
    """F2 — the freeze gate verifies the code hashes announced in the Gx docs."""

    EXPECTED = {
        "src/orvyren/evaluation/loss.py",
        "src/orvyren/evaluation/comparators.py",
        "src/orvyren/evaluation/windows.py",
        "src/orvyren/evaluation/calibration.py",
        "src/orvyren/evaluation/forecasts.py",
        "src/orvyren/evaluation/outcomes.py",
        "tests/test_evaluation_loss.py",
        "tests/test_evaluation_comparators.py",
        "tests/test_evaluation_calibration.py",
    }

    def test_real_package_announced_code_hashes_are_verified(self):
        digests = harness.verify_code_hashes(FROZEN_DIR, repo_root=ROOT)
        self.assertEqual(set(digests), self.EXPECTED)
        for digest in digests.values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_modified_code_file_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_codehash_")
        self.addCleanup(shutil.rmtree, tmp, True)
        code = os.path.join(tmp, "code.py")
        with open(code, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("X = 1\n")
        frozen = _fake_freeze_package(
            tmp, {"G1": "Code gelé : `code.py` — sha256 `%s`.\n" % windows_mod.sha256_file(code)})
        digests = harness.verify_code_hashes(frozen, repo_root=tmp)
        self.assertEqual(digests, {"code.py": windows_mod.sha256_file(code)})
        with open(code, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("X = 2\n")
        with self.assertRaises(windows_mod.FreezeGateError) as caught:
            harness.verify_code_hashes(frozen, repo_root=tmp)
        self.assertIn("code.py", str(caught.exception))

    def test_stale_announced_hash_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_codehash_")
        self.addCleanup(shutil.rmtree, tmp, True)
        code = os.path.join(tmp, "code.py")
        with open(code, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("X = 1\n")
        frozen = _fake_freeze_package(
            tmp, {"G3": "`code.py` — sha256 `%s`.\n" % ("0" * 64)})
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.verify_code_hashes(frozen, repo_root=tmp)

    def test_announced_missing_file_is_refused(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_codehash_")
        self.addCleanup(shutil.rmtree, tmp, True)
        frozen = _fake_freeze_package(
            tmp, {"G5": "`absent.py` — sha256 `%s`.\n" % ("0" * 64)})
        with self.assertRaises(windows_mod.FreezeGateError) as caught:
            harness.verify_code_hashes(frozen, repo_root=tmp)
        self.assertIn("absent.py", str(caught.exception))

    def test_multi_line_g5_announcement_format_parsed(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_codehash_")
        self.addCleanup(shutil.rmtree, tmp, True)
        package = os.path.join(tmp, "src", "orvyren", "evaluation")
        os.makedirs(package)
        first = os.path.join(package, "alpha.py")
        second = os.path.join(package, "beta.py")
        with open(first, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("A = 1\n")
        with open(second, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("B = 1\n")
        # Exactly the G5 "Code gelé" layout: digest on the NEXT line.
        document = ("Code gelé : `alpha.py` sha256\n`%s`,\n`beta.py` sha256 `%s`.\n"
                    % (windows_mod.sha256_file(first), windows_mod.sha256_file(second)))
        frozen = _fake_freeze_package(tmp, {"G5": document})
        digests = harness.verify_code_hashes(frozen, repo_root=tmp)
        self.assertEqual(set(digests), {"src/orvyren/evaluation/alpha.py",
                                        "src/orvyren/evaluation/beta.py"})

    def test_run_set_refuses_on_stale_announced_code_hash(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_codehash_")
        self.addCleanup(shutil.rmtree, tmp, True)
        frozen = _fake_freeze_package(
            tmp, {"G1": "`src/orvyren/evaluation/loss.py` — sha256 `%s`.\n" % ("0" * 64)})
        with self.assertRaises(windows_mod.FreezeGateError):
            harness.run_set("dev", frozen_dir=frozen, calibration_periods=DEV_PERIODS)


class TestF3MandatoryCalibrationEmbargo(unittest.TestCase):
    """F3 — the cross-calibration embargo is mandatory (explicit refusal)."""

    def test_run_set_dev_refuses_without_periods(self):
        with self.assertRaises(harness.HarnessError) as caught:
            harness.run_set("dev", calibration_periods=None)
        self.assertIn("calibration", str(caught.exception))
        self.assertIn("MANDATORY", str(caught.exception))

    def test_run_set_eval_refuses_without_periods(self):
        lock = os.path.join(tempfile.mkdtemp(prefix="orvyren_embargo_"), "absent.lock")
        with self.assertRaises(harness.HarnessError) as caught:
            harness.run_set("eval", lock_path=lock, calibration_periods=None)
        self.assertIn("calibration", str(caught.exception))

    def test_run_set_accepts_declared_periods(self):
        result = harness.run_set("dev", calibration_periods=DEV_PERIODS, b0_draws=200)
        self.assertEqual(result["content"]["params"]["calibration_periods"], DEV_PERIODS)

    def test_run_set_eval_accepts_declared_periods(self):
        lock = os.path.join(tempfile.mkdtemp(prefix="orvyren_embargo_"), "absent.lock")
        result = harness.run_set("eval", calibration_periods=["2030-01"], lock_path=lock)
        content = result["content"]
        self.assertEqual(content["banner"], "EVAL")
        self.assertEqual(content["params"]["calibration_periods"], ["2030-01"])
        self.assertFalse(os.path.exists(lock))  # run_set never writes the lock

    def test_cli_refuses_without_periods_and_logs_it(self):
        cli = _load_cli("run_evaluation.py")
        out_dir = tempfile.mkdtemp(prefix="orvyren_cli_")
        self.addCleanup(shutil.rmtree, out_dir, True)
        code = cli.main(["--set", "dev", "--out-dir", out_dir, "--frozen-dir", FROZEN_DIR])
        self.assertEqual(code, cli.EXIT_REFUSED)
        with open(os.path.join(out_dir, "variants.log"), "r", encoding="utf-8") as handle:
            entries = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(entries[-1]["result"], "REFUSED")
        self.assertIn("calibration", entries[-1]["reason"])

    def test_cli_accepts_declared_periods(self):
        cli = _load_cli("run_evaluation.py")
        out_dir = tempfile.mkdtemp(prefix="orvyren_cli_")
        self.addCleanup(shutil.rmtree, out_dir, True)
        code = cli.main(["--set", "dev", "--calibration-periods", "2023-02,2023-03",
                         "--out-dir", out_dir, "--frozen-dir", FROZEN_DIR])
        self.assertEqual(code, cli.EXIT_OK)
        with open(os.path.join(out_dir, "evaluation_report.json"), "r",
                  encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(document["params"]["calibration_periods"], DEV_PERIODS)


class TestF1CalibrationCliCascade(unittest.TestCase):
    """F1 — run_calibration publishes only what the cascade allows."""

    @unittest.skipUnless(os.path.isfile(FORECASTS) and os.path.isfile(OUTCOMES),
                         "DEV freeze absent")
    def test_real_dev_report_is_content_gated(self):
        cli = _load_cli("run_calibration.py")
        out = os.path.join(tempfile.mkdtemp(prefix="orvyren_cal_"), "cal")
        self.addCleanup(shutil.rmtree, os.path.dirname(out), True)
        code = cli.main(["--forecasts", FORECASTS, "--outcomes", OUTCOMES, "--out", out])
        self.assertEqual(code, 0)
        with open(out + ".json", "r", encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(document["n"], 8)
        self.assertEqual(document["cascade"]["tier"], report_mod.CASCADE_TIER_BASE)
        global_table = document["global"]
        self.assertIn("bs", global_table)
        self.assertIn("ece", global_table)
        self.assertFalse(global_table["ece_claimable"])
        # 8 < 30 : no bootstrap CI, no reliability curve, no BSS in the content.
        self.assertNotIn("bs_bootstrap_ci", global_table)
        self.assertNotIn("bss", global_table)
        self.assertEqual(document["reliability_curve"], [])
        self.assertEqual(len(document["annex"]), 8)
        self.assertEqual(global_table["verdict"], calibration_mod.VERDICT_NON_CONCLUSIVE)
        with open(out + ".md", "r", encoding="utf-8") as handle:
            markdown = handle.read()
        self.assertIn(calibration_mod.VERDICT_NON_CONCLUSIVE, markdown)
        self.assertIn("§b.3 cascade: N < 30", markdown)

    @unittest.skipUnless(os.path.isfile(FORECASTS) and os.path.isfile(OUTCOMES),
                         "DEV freeze absent")
    def test_below_5_publishes_nothing_instead_of_crashing(self):
        tmp = tempfile.mkdtemp(prefix="orvyren_cal_")
        self.addCleanup(shutil.rmtree, tmp, True)
        forecasts = os.path.join(tmp, "forecasts.jsonl")
        outcomes = os.path.join(tmp, "outcomes.jsonl")
        shutil.copyfile(FORECASTS, forecasts)
        with open(OUTCOMES, "r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()][:2]
        with open(outcomes, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(lines))
        cli = _load_cli("run_calibration.py")
        out = os.path.join(tmp, "cal")
        code = cli.main(["--forecasts", forecasts, "--outcomes", outcomes, "--out", out])
        self.assertEqual(code, 0)  # N = 2 < 5 → nothing published, no traceback
        with open(out + ".json", "r", encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(document["n"], 2)
        self.assertEqual(document["cascade"]["tier"], report_mod.CASCADE_TIER_NOT_COMPUTED)
        for key in ("bs", "rel", "res", "unc", "ece", "bss"):
            self.assertNotIn(key, document["global"])
        self.assertEqual(document["annex"], [])
        self.assertEqual(document["global"]["verdict"],
                         calibration_mod.VERDICT_NOT_COMPUTED)

    def test_calibration_cli_refuses_without_freeze(self):
        cli = _load_cli("run_calibration.py")
        tmp = tempfile.mkdtemp(prefix="orvyren_cal_")
        self.addCleanup(shutil.rmtree, tmp, True)
        empty_frozen = os.path.join(tmp, "no_frozen")
        os.makedirs(empty_frozen)
        code = cli.main(["--forecasts", FORECASTS, "--outcomes", OUTCOMES,
                         "--out", os.path.join(tmp, "cal"), "--frozen-dir", empty_frozen])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
