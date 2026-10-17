#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P0 hardening from the Astra review of 14/10/2026 (findings F03/F05/F07/F08).

Each test pins a defect reproduced the same evening, then fixed:

  * F07 — `NaN`/infinity/bool as an amount reached ALLOW; `nan` caps were
    accepted from the environment;
  * F03 — a missing required series CRASHED the engine instead of producing
    the INCONCLUSIVE abstention promised by its own rule 4;
  * F05 — the pipeline kept running dependent stages after a failure
    (policy/audit ran on stale inputs);
  * F08 — `.env` and other sensitive files entered the review ZIP;
    an identifier placed at the start of an RPC URL path leaked into the mask.

Run: python -m unittest discover -s tests -v
"""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for candidate in (os.path.join(REPO, "src"), REPO):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from orvyren.policy import default_config, evaluate  # noqa: E402
from orvyren.execution.intents import DEMO_CLOCK, build_demo_intents  # noqa: E402
from orvyren.execution.guard import (  # noqa: E402
    ConfigurationError,
    ExecutionConfig,
    mask_rpc_url,
)
from orvyren.decision.engine import run_case  # noqa: E402
import make_package  # noqa: E402

CORPUS_CSV = os.path.join(REPO, "corpus", "usdc_observations.csv")
MAIN_START = "2023-03-09T00:00:00+00:00"
MAIN_END = "2023-03-15T00:00:00+00:00"
FIELDS = ["timestamp_utc", "venue", "metric", "value", "extra", "retrieved_at"]


def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _corpus_rows():
    with open(CORPUS_CSV, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class TestPolicyRejectsNonFiniteNumbers(unittest.TestCase):
    """F07 — aucun montant non fini ne doit franchir la politique."""

    def setUp(self):
        self.intent = build_demo_intents()[0]
        self.config = default_config(self.intent.recipient, now=DEMO_CLOCK)

    def _verdict(self, amount):
        return evaluate(replace(self.intent, amount=amount), self.config, now=DEMO_CLOCK)

    def test_nan_amount_is_denied(self):
        decision = self._verdict(float("nan"))
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_NOT_FINITE", decision.reasons)

    def test_infinite_amount_is_denied(self):
        decision = self._verdict(float("inf"))
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_NOT_FINITE", decision.reasons)

    def test_boolean_amount_is_denied(self):
        decision = self._verdict(True)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_NOT_FINITE", decision.reasons)

    def test_negative_cumulative_is_denied(self):
        decision = evaluate(self.intent, self.config, now=DEMO_CLOCK,
                            cumulative_spent=-50.0)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("CUMULATIVE_INVALID", decision.reasons)

    def test_nominal_amount_still_allowed(self):
        decision = evaluate(self.intent, self.config, now=DEMO_CLOCK)
        self.assertEqual(decision.verdict, "ALLOW")

    def test_nan_and_infinite_caps_are_rejected(self):
        for value in ("nan", "inf"):
            with self.assertRaises(ConfigurationError):
                ExecutionConfig.from_env({"ORVYREN_MAX_PER_TX": value})
            with self.assertRaises(ConfigurationError):
                ExecutionConfig.from_env({"ORVYREN_MAX_CUMULATIVE": value})


class TestMissingSeriesAbstain(unittest.TestCase):
    """F03 — missing required series => explicit INCONCLUSIVE, never a crash."""

    def _case_without(self, drop_venue=None, keep_one_supply=False):
        rows = _corpus_rows()
        if drop_venue:
            rows = [row for row in rows if row["venue"] != drop_venue]
        if keep_one_supply:
            seen, kept = 0, []
            for row in rows:
                if row["venue"] == "defillama_supply_aggregate":
                    seen += 1
                    if seen > 1:
                        continue
                kept.append(row)
            rows = kept
        self._tmp = tempfile.TemporaryDirectory()
        path = os.path.join(self._tmp.name, "variant.csv")
        _write_csv(path, rows)
        return run_case(path, MAIN_START, MAIN_END)

    def tearDown(self):
        tmp = getattr(self, "_tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def _assert_abstains(self, case, needle):
        decision = case["decision"]
        self.assertEqual(decision["verdict"], "INCONCLUSIVE")
        self.assertIsNone(decision["action"])
        self.assertTrue(decision["rationale"], "rationale must not be empty")
        self.assertTrue(any(needle in item for item in decision["missing_inputs"]),
                        "missing_inputs must name %r, got %r"
                        % (needle, decision["missing_inputs"]))

    def test_missing_binance_abstains_without_crash(self):
        self._assert_abstains(self._case_without(drop_venue="binance"), "binance")

    def test_missing_bitstamp_abstains_without_crash(self):
        self._assert_abstains(self._case_without(drop_venue="bitstamp"), "bitstamp")

    def test_missing_aggregator_abstains_without_crash(self):
        # H2 could still be evaluated on the two exchanges alone; rule 4 must
        # take precedence and refuse an action on incomplete evidence.
        self._assert_abstains(self._case_without(drop_venue="defillama"), "defillama")

    def test_single_supply_observation_lists_missing_change(self):
        case = self._case_without(keep_one_supply=True)
        decision = case["decision"]
        self.assertEqual(decision["verdict"], "INCONCLUSIVE")
        self.assertTrue(any("24 h" in item for item in decision["missing_inputs"]),
                        "missing_inputs must name the uncomputable supply change, got %r"
                        % decision["missing_inputs"])

    def test_run_decision_cli_abstains_on_missing_binance(self):
        """The exact command of the video storyboard (derivative without Binance)."""
        with tempfile.TemporaryDirectory() as tmp:
            variant = os.path.join(tmp, "without-binance.csv")
            _write_csv(variant, [r for r in _corpus_rows() if r["venue"] != "binance"])
            out_dir = os.path.join(tmp, "out")
            proc = subprocess.run(
                [sys.executable, "run_decision.py", "--corpus", variant,
                 "--out-dir", out_dir],
                cwd=REPO, capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(out_dir, "decision_usdc-2023-03.json"),
                      encoding="utf-8") as handle:
                record = json.load(handle)
            self.assertEqual(record["decision"]["verdict"], "INCONCLUSIVE")
            self.assertIsNone(record["decision"]["action"])


class TestPipelineHaltsOnFailure(unittest.TestCase):
    """F05 — a failed stage stops the dependent stages."""

    def test_downstream_stages_skipped_after_quality_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "repo")
            shutil.copytree(
                REPO, copy,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "dist",
                                              ".pytest_cache", ".mypy_cache"))
            variant = [r for r in _corpus_rows() if r["venue"] != "binance"]
            _write_csv(os.path.join(copy, "corpus", "usdc_observations.csv"), variant)

            proc = subprocess.run([sys.executable, "run_pipeline.py"],
                                  cwd=copy, capture_output=True, text=True,
                                  timeout=180)
            self.assertNotEqual(proc.returncode, 0,
                                "a failing pipeline must not exit 0")
            with open(os.path.join(copy, "evidence", "pipeline_summary.json"),
                      encoding="utf-8") as handle:
                summary = json.load(handle)
            statuses = {stage["stage"]: stage["status"]
                        for stage in summary["stages"]}
            self.assertTrue(statuses["quality"].startswith("FAILED"),
                            "quality should fail loudly, got %r" % statuses["quality"])
            for stage in ("decision", "policy", "audit"):
                self.assertEqual(statuses[stage], "SKIPPED (upstream failure)",
                                 "%s must not run after an upstream failure, got %r"
                                 % (stage, statuses[stage]))


class TestPackagingAndMasking(unittest.TestCase):
    """F08 — pas de secrets dans le paquet ; masque RPC sans fuite."""

    def test_mask_hides_credentials_in_any_path_segment(self):
        leaked = mask_rpc_url("https://rpc.example/CANARY_SECRET/v1")
        self.assertNotIn("CANARY_SECRET", leaked)
        self.assertTrue(leaked.endswith("/v1"), leaked)
        alchemy = mask_rpc_url("https://base-sepolia.g.alchemy.com/v2/SUPERSECRETKEY")
        self.assertNotIn("SUPERSECRETKEY", alchemy)
        self.assertIn("/v2/", alchemy)

    def test_review_zip_excludes_secret_like_files(self):
        """The real make_package.py, executed in a fake tree."""
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(os.path.join(REPO, "make_package.py"),
                        os.path.join(tmp, "make_package.py"))
            for rel in ("plain.txt", "sub/mod.py", ".env", ".env.example",
                        "secrets/creds.json", "keys/id_rsa", "app.pem"):
                path = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write("CANARY_NOT_A_REAL_SECRET\n")

            proc = subprocess.run([sys.executable, "make_package.py"],
                                  cwd=tmp, capture_output=True, text=True,
                                  timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)

            import zipfile
            dist = os.path.join(tmp, "dist")
            zips = [os.path.join(dist, name) for name in os.listdir(dist)]
            self.assertEqual(1, len(zips))
            with zipfile.ZipFile(zips[0]) as archive:
                names = archive.namelist()
                manifest = archive.read("MANIFEST.sha256").decode("utf-8")
            self.assertIn("plain.txt", names)
            self.assertIn("sub/mod.py", names)
            self.assertIn(".env.example", names)
            for forbidden in (".env", "secrets/creds.json", "keys/id_rsa", "app.pem"):
                self.assertNotIn(forbidden, names,
                                 "%s must never enter the shared zip" % forbidden)
            self.assertNotIn(".env\n", manifest + "\n")
            self.assertNotIn("creds.json", manifest)


class TestForbiddenNameRules(unittest.TestCase):
    """The deny-list rules, tested directly."""

    def test_forbidden_and_allowed_names(self):
        for forbidden in (".env", ".env.local", "keys/id_ed25519",
                          "secrets/creds.json", "cert.pem", "wallet.key"):
            self.assertTrue(make_package.is_forbidden(forbidden), forbidden)
        for allowed in (".env.example", "README.md", "src/mod.py",
                        "docs/review.md"):
            self.assertFalse(make_package.is_forbidden(allowed), allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
