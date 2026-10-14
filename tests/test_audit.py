"""Tests for the ORVYREN-Core audit dossier builder and the stdlib UI server.

Run from the repository root::

    python -m unittest discover -s tests

Standard library only (unittest, tempfile, threading, urllib).
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from orvyren.audit import dossier  # noqa: E402
from orvyren.ui import server as ui_server  # noqa: E402


BUILD_TIME = "2026-01-01T00:00:00Z"

DECISION_FIXTURE = {
    "case": "usdc-2023-03",
    "window": {"start": "2023-03-01", "end": "2023-03-31"},
    "inputs_summary": {"sources": ["onchain transfers", "stablecoin flows"], "rows_processed": 18422},
    "hypothesis_verdicts": {
        "H1": {"verdict": "SUPPORTED", "evidence_refs": ["E1", "E2", "E3"]},
        "H2": {"verdict": "REJECTED", "evidence_refs": ["E4"]},
        "H3": {"verdict": "INCONCLUSIVE", "evidence_refs": []},
    },
    "decision": {
        "verdict": "ACTION_RECOMMENDED",
        "action": {
            "type": "transfer",
            "asset": "USDC",
            "amount_usdc": 25000,
            "from_wallet": "treasury_reserve",
            "to_wallet": "usdc_yield_vault",
        },
        "rationale": ["Inflow acceleration exceeded the A0 baseline threshold (E1)."],
        "conditions": ["Deploy in two tranches."],
        "limits": ["H3 has no supporting evidence in this window."],
        "provenance": ["E1 -> onchain_transfer_scan rows 1180-1244"],
    },
    "calibration": {"threshold_sigma": 2.0},
}

BASELINE_FIXTURE = {
    "rule": "A0 baseline: flag inflow acceleration above mean + 2 sigma of the control window",
    "signals_main": ["2023-03-11 inflow acceleration", "2023-03-19 inflow acceleration"],
    "signals_control": ["2023-02-27 inflow acceleration"],
    "false_signals_control": 1,
}


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class DossierBuildTests(unittest.TestCase):
    """Builder behaviour: fixture build, determinism, missing inputs, HTML."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_audit_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.decision_path = os.path.join(self.tmp, "decision_usdc-2023-03.json")
        _write_json(self.decision_path, DECISION_FIXTURE)
        self.out_dir = os.path.join(self.tmp, "evidence")

    def test_build_fixture_produces_both_files_with_verdict_and_evidence(self):
        result = dossier.build(self.decision_path, self.out_dir, generated_at=BUILD_TIME)
        self.assertTrue(os.path.exists(result["md_path"]))
        self.assertTrue(os.path.exists(result["html_path"]))
        md = _read_text(result["md_path"])
        self.assertIn("ACTION_RECOMMENDED", md)
        self.assertIn("## Evidence", md)
        self.assertIn(dossier.PRODUCED_CLAUSE, md)
        self.assertIn(dossier.sha256_file(self.decision_path), md)
        self.assertIn("25000 USDC", md)
        self.assertRegex(result["sha256"], r"^[0-9a-f]{64}$")

    def test_sha256_stable_between_identical_builds_and_self_reproducible(self):
        first = dossier.build(self.decision_path, self.out_dir, generated_at=BUILD_TIME)
        second = dossier.build(self.decision_path, self.out_dir, generated_at=BUILD_TIME)
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["sha256_html"], second["sha256_html"])
        self.assertEqual(_read_text(first["md_path"]), _read_text(second["md_path"]))
        # The embedded self-hash reproduces from the file with the field zeroed.
        md = _read_text(first["md_path"])
        zeroed = md.replace(first["sha256"], "0" * 64, 1)
        self.assertEqual(hashlib.sha256(zeroed.encode("utf-8")).hexdigest(), first["sha256"])
        html = _read_text(first["html_path"])
        zeroed_html = html.replace(first["sha256_html"], "0" * 64, 1)
        self.assertEqual(hashlib.sha256(zeroed_html.encode("utf-8")).hexdigest(), first["sha256_html"])

    def test_missing_decision_input_is_reported_and_does_not_raise(self):
        missing_path = os.path.join(self.tmp, "does_not_exist", "decision_nope.json")
        result = dossier.build(missing_path, self.out_dir)  # must not raise
        self.assertTrue(os.path.exists(result["md_path"]))
        self.assertTrue(os.path.exists(result["html_path"]))
        md = _read_text(result["md_path"])
        html = _read_text(result["html_path"])
        # The builder renders portable repo-agnostic paths with forward slashes
        # (platform-stable artefacts); the expectation must be normalised the
        # same way on Windows.
        expected = missing_path.replace(os.sep, "/")
        self.assertIn(f"Missing input: {expected}", md)
        self.assertIn("Missing input", html)
        self.assertIn("(not provided in source JSON)", md)
        self.assertRegex(result["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(result["inputs"][0]["status"], "missing")
        self.assertIsNone(result["inputs"][0]["sha256"])

    def test_html_is_self_contained_title_present_no_dual_placeholders(self):
        baseline_path = os.path.join(self.tmp, "baseline_report.json")
        _write_json(baseline_path, BASELINE_FIXTURE)
        result = dossier.build(
            self.decision_path,
            self.out_dir,
            extra_paths={"baseline_report": baseline_path},
            generated_at=BUILD_TIME,
        )
        html = _read_text(result["html_path"])
        lowered = html.lower()
        self.assertIn("<html", lowered)
        self.assertIn("<title>", lowered)
        self.assertIn("orvyren-core", lowered)
        self.assertNotIn("todo", lowered)
        self.assertNotIn("placeholder", lowered)
        self.assertNotIn("<script", lowered)
        self.assertNotIn("cdn.", lowered)
        self.assertNotIn('href="http', lowered)
        self.assertNotIn('src="http', lowered)
        self.assertIn("<style>", lowered)

    def test_baseline_extra_renders_main_vs_control_comparison(self):
        baseline_path = os.path.join(self.tmp, "baseline_report.json")
        _write_json(baseline_path, BASELINE_FIXTURE)
        result = dossier.build(
            self.decision_path,
            self.out_dir,
            extra_paths={"baseline_report": baseline_path},
            generated_at=BUILD_TIME,
        )
        md = _read_text(result["md_path"])
        self.assertIn("Baseline A0", md)
        self.assertIn("| Signals | 2 | 1 |", md)
        self.assertIn("2023-03-11 inflow acceleration", md)
        self.assertIn(dossier.sha256_file(baseline_path), md)
        html = _read_text(result["html_path"])
        self.assertIn("Baseline A0", html)
        self.assertIn("2023-03-11 inflow acceleration", html)

    def test_unknown_extra_label_is_still_hashed_and_listed(self):
        extra_path = os.path.join(self.tmp, "policy_execution_demo.json")
        _write_json(extra_path, {"dry_run": True, "action": "none"})
        result = dossier.build(
            self.decision_path,
            self.out_dir,
            extra_paths={"policy_execution_demo": extra_path},
            generated_at=BUILD_TIME,
        )
        md = _read_text(result["md_path"])
        self.assertIn("## Policy execution demo", md)
        self.assertIn(dossier.sha256_file(extra_path), md)


class UiServerTests(unittest.TestCase):
    """HTTP server behaviour: health, 503 robustness, dossier serving, shutdown."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_ui_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _start(self, evidence_dir):
        httpd = ui_server.make_server("127.0.0.1", 0, evidence_dir, quiet=True)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        return httpd, thread

    @staticmethod
    def _stop(httpd, thread):
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=10)
        return thread

    def test_health_endpoint_503_without_dossier_and_clean_shutdown(self):
        httpd, thread = self._start(self.tmp)
        try:
            port = httpd.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=10) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIs(payload.get("ok"), True)
            self.assertEqual(payload.get("version"), "0.1")

            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10)
            self.assertEqual(raised.exception.code, 503)
            body = raised.exception.read().decode("utf-8")
            self.assertIn("no dossier", body.lower())
        finally:
            thread = self._stop(httpd, thread)
        self.assertFalse(thread.is_alive())

    def test_serves_built_dossier_and_api_endpoint(self):
        decision_path = os.path.join(self.tmp, "decision_usdc-2023-03.json")
        _write_json(decision_path, DECISION_FIXTURE)
        result = dossier.build(decision_path, self.tmp, generated_at=BUILD_TIME)
        self.assertTrue(os.path.exists(result["html_path"]))

        httpd, thread = self._start(self.tmp)
        try:
            port = httpd.server_address[1]
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("text/html", response.headers.get("Content-Type", ""))
                body = response.read().decode("utf-8")
            self.assertIn("ORVYREN-Core", body)
            self.assertIn("ACTION_RECOMMENDED", body)

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/dossier", timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIs(payload.get("ok"), True)
            self.assertEqual(payload.get("source"), "dossier")
            self.assertEqual(payload.get("case"), "usdc-2023-03")
            self.assertEqual(payload.get("verdict"), "ACTION_RECOMMENDED")
            self.assertRegex(payload.get("sha256_html") or "", r"^[0-9a-f]{64}$")

            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/does-not-exist", timeout=10)
            self.assertEqual(raised.exception.code, 404)
        finally:
            thread = self._stop(httpd, thread)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
