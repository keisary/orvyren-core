#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Garde-fous d'intégrité et de reproductibilité (revue du 2026-10-14).

Chaque classe ici épingle un défaut réel trouvé pendant la revue, pour qu'il
ne puisse pas revenir sans faire échouer la suite :

  * des empreintes dépendantes de la plateforme (CRLF vs LF) : le sha256 du
    corpus enregistré dans les preuves ne correspondait pas au fichier du
    dépôt sur toute machine autre que celle qui l'avait produit ;
  * des chemins absolus (``D:\\orvyren_core\\...``) gravés dans le dossier
    d'audit, donc non portables et différents d'une machine à l'autre ;
  * un cache de collecte d'avant le filtre de fenêtre qui avait expédié
    855 lignes Bitstamp hors fenêtre dans l'archive ;
  * une sémantique « au moins deux venues » implémentée par intersection,
    qui aurait exigé *toutes* les venues à partir de trois séries ;
  * une démo d'exécution dont les horodatages internes changeaient à chaque
    exécution alors que la conception promet un contenu reproductible.

Exécution : python -m unittest discover -s tests -v
"""

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "src")
for candidate in (SRC, REPO):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from orvyren.audit import dossier  # noqa: E402
from orvyren.decision import scenarios  # noqa: E402

CORPUS_CSV = os.path.join(REPO, "corpus", "usdc_observations.csv")
RAW_BITSTAMP = os.path.join(REPO, "corpus", "raw", "bitstamp", "usdcusd_ohlc.json")
EVIDENCE_DIR = os.path.join(REPO, "evidence")
DECISION_JSON = os.path.join(EVIDENCE_DIR, "decision_usdc-2023-03.json")

MAIN_START = dt.datetime(2023, 3, 9, 0, 0, tzinfo=dt.timezone.utc)
MAIN_END = dt.datetime(2023, 3, 15, 0, 0, tzinfo=dt.timezone.utc)


def _write(path, content, newline=None):
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(content)


class TestTextDigestsArePlatformStable(unittest.TestCase):
    """CRLF et LF doivent produire la même empreinte (Windows vs Unix)."""

    SAMPLE = ("timestamp_utc,venue,metric,value,extra,retrieved_at\n"
              "2023-03-09T00:00:00+00:00,defillama,price_usd,1.0,,x\n"
              "2023-03-09T01:00:00+00:00,defillama,price_usd,0.9995,,x\n")

    def test_corpus_sha256_is_same_for_crlf_and_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            lf = os.path.join(tmp, "lf.csv")
            crlf = os.path.join(tmp, "crlf.csv")
            _write(lf, self.SAMPLE, newline="")
            with open(crlf, "wb") as handle:
                handle.write(self.SAMPLE.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(scenarios.corpus_sha256(lf),
                             scenarios.corpus_sha256(crlf))

    def test_dossier_sha256_file_is_same_for_crlf_and_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            lf = os.path.join(tmp, "lf.json")
            crlf = os.path.join(tmp, "crlf.json")
            payload = '{"case": "x"}\n'
            _write(lf, payload, newline="")
            _write(crlf, payload.replace("\n", "\r\n"), newline="")
            self.assertEqual(dossier.sha256_file(lf), dossier.sha256_file(crlf))

    def test_recorded_corpus_digest_matches_the_repository_copy(self):
        """Le sha enregistré dans les preuves doit se recalculer depuis le dépôt."""
        if not os.path.exists(DECISION_JSON):
            self.skipTest("evidence/decision JSON not built yet")
        recorded = json.load(open(DECISION_JSON, encoding="utf-8"))[
            "inputs_summary"]["corpus"]["sha256"]
        computed = scenarios.corpus_sha256(CORPUS_CSV)
        self.assertEqual(
            recorded, computed,
            "recorded corpus sha256 %s != sha256 of the repository copy %s "
            "(a reviewer cannot reproduce the provenance record)"
            % (recorded[:12], computed[:12]))


class TestDossierPathsArePortable(unittest.TestCase):
    """Aucun chemin absolu ne doit entrer dans un dossier d'audit haché."""

    def test_repo_inputs_display_repo_relative_paths(self):
        if not os.path.exists(DECISION_JSON):
            self.skipTest("evidence/decision JSON not built yet")
        with tempfile.TemporaryDirectory() as tmp:
            result = dossier.build(DECISION_JSON, tmp,
                                   generated_at="2026-10-14T00:00:00Z")
            paths = [record["path"] for record in result["inputs"]]
            self.assertIn("evidence/decision_usdc-2023-03.json", paths)
            for path in paths:
                self.assertFalse(path.startswith("/"), path)
                self.assertNotIn(":\\", path)
                self.assertNotIn("\\", path)

    def test_external_paths_are_reported_unabridged(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = os.path.join(tmp, "decision_ext.json")
            _write(external, '{"case": "ext", "decision": {"verdict": "NO_ACTION"}}\n',
                   newline="")
            result = dossier.build(external, os.path.join(tmp, "out"),
                                   generated_at="2026-10-14T00:00:00Z")
            recorded = result["inputs"][0]["path"]
            self.assertEqual(external.replace(os.sep, "/"), recorded)

    def test_committed_dossier_has_no_absolute_paths(self):
        md_path = os.path.join(EVIDENCE_DIR, "dossier_usdc-2023-03.md")
        if not os.path.exists(md_path):
            self.skipTest("dossier not built yet")
        text = open(md_path, encoding="utf-8").read()
        self.assertNotIn("D:\\", text)
        self.assertNotIn("D:/", text)
        self.assertNotIn("/home/", text)
        self.assertNotIn("/Users/", text)


class TestPinnedBuildIsReproducible(unittest.TestCase):
    """Avec les mêmes entrées, la même date gelée et la même destination,
    le dossier est octet à octet identique."""

    def test_two_builds_with_same_generated_at_are_byte_identical(self):
        if not os.path.exists(DECISION_JSON):
            self.skipTest("evidence/decision JSON not built yet")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "out")
            first = dossier.build(DECISION_JSON, out_dir,
                                  generated_at="2026-10-14T00:00:00Z")
            with open(first["md_path"], "rb") as handle:
                bytes_a = handle.read()
            second = dossier.build(DECISION_JSON, out_dir,
                                   generated_at="2026-10-14T00:00:00Z")
            with open(second["md_path"], "rb") as handle:
                bytes_b = handle.read()
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual(first["sha256_html"], second["sha256_html"])
            self.assertEqual(bytes_a, bytes_b)

    def test_run_audit_cli_generated_at_flag(self):
        if not os.path.exists(DECISION_JSON):
            self.skipTest("evidence/decision JSON not built yet")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "out")
            snapshots = []
            for _ in range(2):
                proc = subprocess.run(
                    [sys.executable, "run_audit.py", "--out-dir", out_dir,
                     "--generated-at", "2026-10-14T00:00:00Z"],
                    cwd=REPO, capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                with open(os.path.join(out_dir, "dossier_usdc-2023-03.md"), "rb") as handle:
                    snapshots.append(handle.read())
            self.assertEqual(snapshots[0], snapshots[1],
                             "pinned rebuilds must be byte-identical")
            self.assertIn(b"2026-10-14T00:00:00Z", snapshots[0])

    def test_committed_dossier_self_hash_recomputes(self):
        """Le self-hash du dossier committé doit se recalculer à la main."""
        import hashlib
        import re
        md_path = os.path.join(EVIDENCE_DIR, "dossier_usdc-2023-03.md")
        if not os.path.exists(md_path):
            self.skipTest("dossier not built yet")
        text = open(md_path, encoding="utf-8").read()
        match = re.search(r"dossier \(self, md\) \| [^|]+ \| `([0-9a-f]{64})`", text)
        self.assertIsNotNone(match, "self-hash row not found in the dossier")
        digest = match.group(1)
        recomputed = hashlib.sha256(
            text.replace(digest, "0" * 64, 1).encode("utf-8")).hexdigest()
        self.assertEqual(digest, recomputed,
                         "the committed dossier's self-hash does not recompute")


class TestCorpusWindowContract(unittest.TestCase):
    """L'archive ne contient que les fenêtres déclarées (D1/D2)."""

    def _rows(self):
        import csv
        with open(CORPUS_CSV, encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_all_rows_stay_inside_declared_windows(self):
        rows = self._rows()
        self.assertEqual(520, len(rows), "window-bounded corpus row count")
        control_start = dt.datetime(2023, 2, 15, 0, 0, tzinfo=dt.timezone.utc)
        control_end = dt.datetime(2023, 2, 18, 0, 0, tzinfo=dt.timezone.utc)
        bitstamp = 0
        for row in rows:
            when = dt.datetime.fromisoformat(row["timestamp_utc"])
            venue = row["venue"]
            if venue == "defillama":
                in_main = MAIN_START <= when <= MAIN_END
                in_control = control_start <= when <= control_end
                self.assertTrue(in_main or in_control,
                                "defillama row at %s outside main and control" % when)
            elif venue in ("bitstamp", "binance"):
                self.assertTrue(MAIN_START <= when <= MAIN_END,
                                "%s row at %s outside the main window" % (venue, when))
                if venue == "bitstamp":
                    bitstamp += 1
            elif venue in ("defillama_supply_aggregate", "defillama_supply_ethereum"):
                self.assertTrue(MAIN_START - dt.timedelta(days=15) <= when
                                <= MAIN_END + dt.timedelta(days=15),
                                "supply row at %s outside crisis +/-15d" % when)
            else:
                self.fail("unexpected venue in archive: %r" % venue)
        self.assertEqual(145, bitstamp, "Bitstamp covers the full main window only")

    def test_raw_bitstamp_payload_is_window_bounded(self):
        rows = json.load(open(RAW_BITSTAMP, encoding="utf-8"))
        self.assertEqual(145, len(rows))
        for row in rows:
            when = dt.datetime.fromisoformat(row["timestamp_utc"])
            self.assertTrue(MAIN_START <= when <= MAIN_END,
                            "raw payload row at %s outside the main window" % when)

    def test_collector_window_validator_catches_the_incident(self):
        import collect_corpus
        incident = [{"timestamp_utc": "2023-04-19T15:00:00+00:00"}]
        problems = collect_corpus.validate_archived_windows(
            {"main": [], "control": []}, incident, [], {})
        self.assertTrue(problems, "the 855-row incident sample must be refused")
        healthy = [{"timestamp_utc": "2023-03-10T00:00:00+00:00"}]
        self.assertEqual([],
                         collect_corpus.validate_archived_windows(
                             {"main": [], "control": []}, healthy, [], {}))


class TestSimultaneousAlertSemantics(unittest.TestCase):
    """« Au moins deux venues » = comptage par heure, pas intersection totale."""

    @staticmethod
    def _obs(venue, when, value):
        return scenarios.Observation(
            timestamp_utc=when, ts=dt.datetime.fromisoformat(when),
            venue=venue, metric="close_usd", value=value)

    def test_three_venues_count_hours_with_two_alerts(self):
        t1 = "2023-03-11T00:00:00+00:00"
        t2 = "2023-03-11T01:00:00+00:00"
        t3 = "2023-03-11T02:00:00+00:00"
        series = {
            "a": [self._obs("a", t1, 0.98), self._obs("a", t2, 0.98), self._obs("a", t3, 0.98)],
            "b": [self._obs("b", t1, 0.98), self._obs("b", t2, 1.00), self._obs("b", t3, 0.98)],
            "c": [self._obs("c", t1, 1.00), self._obs("c", t2, 1.00), self._obs("c", t3, 0.98)],
        }
        hours, alert_sets = scenarios._simultaneous_alert_hours(series)
        # t1 : a+b ; t2 : seule a alerte ; t3 : a+b+c.
        self.assertEqual([t1, t3], [hour.isoformat() for hour in hours])
        self.assertEqual({"a", "b", "c"}, set(alert_sets))

    def test_two_venues_behaviour_is_unchanged(self):
        t1 = "2023-03-11T00:00:00+00:00"
        t2 = "2023-03-11T01:00:00+00:00"
        series = {
            "a": [self._obs("a", t1, 0.98), self._obs("a", t2, 1.00)],
            "b": [self._obs("b", t1, 0.98), self._obs("b", t2, 0.98)],
        }
        hours, _ = scenarios._simultaneous_alert_hours(series)
        self.assertEqual([t1], [hour.isoformat() for hour in hours])


class TestExecutionDemoClock(unittest.TestCase):
    """Le contenu de la démo d'exécution ne dépend pas de l'heure du run."""

    def _report(self, when):
        import run_execution_demo
        from orvyren.execution.guard import ExecutionConfig
        config = ExecutionConfig.from_env(env={})
        return run_execution_demo.build_report(
            config, dt.datetime.fromisoformat(when))

    def test_verdict_content_is_stable_across_wall_clocks(self):
        morning = self._report("2026-10-14T08:00:00+00:00")
        evening = self._report("2026-10-14T23:30:00+00:00")
        self.assertEqual(json.dumps(morning["cases"], sort_keys=True),
                         json.dumps(evening["cases"], sort_keys=True))
        self.assertEqual(morning["guard_blocks"], evening["guard_blocks"])
        self.assertNotEqual(morning["generated_at"], evening["generated_at"],
                            "the run time is still recorded, and honestly differs")

    def test_permission_rule_note_uses_the_frozen_demo_clock(self):
        report = self._report("2026-10-14T08:00:00+00:00")
        for case in report["cases"]:
            notes = [rule.get("note") for rule in case["rules_evaluated"]
                     if rule.get("rule") == "P8-permission"]
            self.assertEqual(["2026-10-15T12:00:00+00:00"], notes,
                             "P8 expiry must be DEMO_CLOCK + 24 h, not run time")


if __name__ == "__main__":
    unittest.main(verbosity=2)
