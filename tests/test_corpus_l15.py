#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench L1.5 — fenêtres CALME + série USD0++ + manifeste corpus v1.

Contrat (DOC4 W1, lot L1.5) : les fenêtres CALME (contrôles DEV/EVAL) sont
archivées avec leurs bornes et comptes vérifiables hors-ligne ; la série
USD0++ (jan 2025) est importée avec sa provenance ; ``replay/corpus_v1.
manifest.json`` (contrat B7 §d.3) liste chaque fichier avec son sha256 et se
re-vérifie (``--check``).

Tout est hors-ligne (les données sont committées).

Execution: ``python -m pytest tests/test_corpus_l15.py -q``.
"""

import hashlib
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import build_corpus_v1_manifest as bcv  # noqa: E402

MIN_POINTS = 160


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as handle:
        return json.load(handle)


def _parse(ts_iso):
    import datetime as dt
    candidate = ts_iso.replace("Z", "+00:00").replace("+00:00", "+00:00")
    try:
        return dt.datetime.fromisoformat(candidate)
    except ValueError:
        return dt.datetime.fromisoformat(ts_iso)


class TestCalmWindows(unittest.TestCase):

    def setUp(self):
        self.series = _load("corpus/series/calm_windows.json")

    def test_windows_declared(self):
        self.assertEqual(self.series["schema"], "orvyren/calm-windows/v1")
        self.assertEqual(sorted(self.series["windows"]), ["calm_a", "calm_b"])
        self.assertIn("PROPOSITION B7", self.series["note"])

    def test_sources_and_bounds(self):
        for label, window in self.series["windows"].items():
            start, end = _parse(window["start"]), _parse(window["end"])
            # a source is either measured or explicitly declared unavailable —
            # never both, and an unavailability is always declared (status + note)
            self.assertEqual("binance" in window["unavailable"],
                             "binance" not in window["sources"], label)
            for name, entry in window["unavailable"].items():
                self.assertNotIn(name, window["sources"], (label, name))
                self.assertTrue(str(entry.get("status", "")).strip(), (label, name))
                self.assertTrue(str(entry.get("note", "")).strip(), (label, name))
            for name, source in window["sources"].items():
                self.assertGreaterEqual(source["records"], MIN_POINTS, (label, name))
                for observation in source["observations"]:
                    moment = _parse(observation["timestamp_utc"])
                    self.assertLessEqual(start, moment, (label, name))
                    self.assertLessEqual(moment, end, (label, name))

    def test_measured_unavailability_is_declared(self):
        manifest = _load("corpus/calm_manifest.json")
        entries = {(e["window"], e["source"]): e for e in manifest["sources"]}
        self.assertEqual(entries[("calm_a", "binance")]["status"],
                         "unavailable_measured")
        self.assertEqual(entries[("calm_b", "binance")]["status"], "ok")
        self.assertIn("2026-10-16", entries[("calm_a", "binance")]["note"])


class TestUsd0ppSeries(unittest.TestCase):

    def test_series_shape_and_provenance(self):
        series = _load("corpus/series/usd0pp_2025-01.json")
        self.assertEqual(series["points"], 635)
        self.assertEqual(len(series["observations"]), 635)
        self.assertIn("0x35D8949372D46B7a3D5A56006AE77B215fc69bC0", series["contract"])
        self.assertIn("W3-C", series["provenance"])
        unix = [o["unix"] for o in series["observations"]]
        self.assertEqual(unix, sorted(unix))
        for observation in series["observations"]:
            self.assertGreater(observation["price_usd"], 0.5)
            self.assertLess(observation["price_usd"], 1.1)
        # la dépeg de janvier 2025 est bien dans la série (creux < 0,95)
        self.assertLess(min(o["price_usd"] for o in series["observations"]), 0.95)


class TestCorpusV1Manifest(unittest.TestCase):

    def test_manifest_files_verify(self):
        manifest = _load("replay/corpus_v1.manifest.json")
        self.assertEqual(manifest["schema"], "orvyren/corpus-v1-manifest/v1")
        self.assertGreaterEqual(manifest["totals"]["files"], 8)
        self.assertEqual(len(manifest["manifest_sha256"]), 64)
        for entry in manifest["files"]:
            path = os.path.join(REPO_ROOT, entry["path"])
            self.assertTrue(os.path.exists(path), entry["path"])
            with open(path, "rb") as handle:
                self.assertEqual(hashlib.sha256(handle.read()).hexdigest(),
                                 entry["sha256"], entry["path"])
        self.assertIn("calm", manifest["windows"])
        self.assertIn("usd0pp_2025-01", manifest["windows"])
        # les pièces absentes sont déclarées, pas inventées
        self.assertTrue(manifest["missing_declared"])

    def test_manifest_is_rebuildable(self):
        rebuilt = bcv.build_manifest()
        on_disk = _load("replay/corpus_v1.manifest.json")
        rebuilt.pop("built_at", None)
        on_disk.pop("built_at", None)
        self.assertEqual(rebuilt, on_disk)

    def test_check_mode_passes(self):
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "scripts",
                                          "build_corpus_v1_manifest.py"), "--check"],
            capture_output=True, text=True, cwd=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
