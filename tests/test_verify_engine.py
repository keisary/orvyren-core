#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests W6 : vérificateur tiers T10 de bout en bout.

Chaîne réelle de bout en bout, **hors ligne** : le paquet v2 est assemblé par
``scripts/build_audit_packet.py`` à partir de la session rseth réellement
exécutée (preuves versionnées), puis vérifié par le moteur du dépôt ET par le
vérificateur gelé embarqué dans le paquet :

* verdict ``OFFLINE_PASS``, zéro contrôle en échec, ligne B SKIPPED ;
* mutation-test intégré : 6/6 mutations détectées ;
* altération du journal → A1 en échec ; reçu supprimé → A3/A8 en échec ;
* le lanceur gelé ``verify/orvyren_verify.py`` s'exécute seul (imports gelés).

Les tests se sautent proprement si les entrées de session ne sont pas présentes.

Run: python -m pytest tests/test_verify_engine.py -q
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.verify.engine import verify_packet  # noqa: E402

# Micro-chaîne PUBLIQUE versionnée (extrait de la session rseth réelle) : elle
# rend ces tests exécutables sur un clone, où evidence/demo_runs/ est git-ignoré.
SESSION_DIR = os.path.join(ROOT, "evidence", "demo_chain", "rseth")
EVIDENCE_DIR = os.path.join(ROOT, "evidence")
CORPUS = os.path.join(ROOT, "corpus", "usdc_observations.csv")
BUILDER = os.path.join(ROOT, "scripts", "build_audit_packet.py")

INPUTS_PRESENT = (
    os.path.isfile(os.path.join(SESSION_DIR, "audit.jsonl"))
    and os.path.isfile(os.path.join(EVIDENCE_DIR, "decision_usdc-2023-03.json"))
    and os.path.isfile(CORPUS)
)


@unittest.skipUnless(INPUTS_PRESENT, "entrées de session absentes (evidence/demo_chain/rseth)")
class VerifyEngineEndToEndTest(unittest.TestCase):
    packet_dir = None
    build_stdout = ""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="orvyren_packet_")
        result = subprocess.run(
            [sys.executable, BUILDER, "--session", SESSION_DIR, "--case", "rseth",
             "--out-dir", cls.tmp],
            cwd=ROOT, capture_output=True, text=True, timeout=600)
        cls.build_stdout = result.stdout + result.stderr
        if result.returncode != 0:
            raise AssertionError("build_audit_packet.py a échoué :\n%s" % cls.build_stdout)
        matches = sorted(glob.glob(os.path.join(cls.tmp, "audit_packet_*")))
        dirs = [path for path in matches if os.path.isdir(path)]
        if not dirs:
            raise AssertionError("paquet introuvable dans %s" % cls.tmp)
        cls.packet_dir = dirs[0]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _copy_packet(self):
        target = tempfile.mkdtemp(prefix="orvyren_tamper_")
        self.addCleanup(shutil.rmtree, target, True)
        return shutil.copytree(self.packet_dir, os.path.join(target, "packet"))

    def test_offline_pass_with_b_skipped(self):
        report = verify_packet(self.packet_dir)
        self.assertEqual(report["verdict"], "OFFLINE_PASS", report.get("checks"))
        self.assertEqual(report["summary"]["failed"], 0)
        b_rows = [check for check in report["checks"] if check["class"] == "B"]
        self.assertEqual(len(b_rows), 1)
        self.assertEqual(b_rows[0]["status"], "SKIPPED")

    def test_mutations_all_detected(self):
        report = verify_packet(self.packet_dir, with_mutations=True)
        mutations = report.get("mutations", [])
        self.assertEqual(len(mutations), 6)
        self.assertTrue(all(entry["detected"] for entry in mutations),
                        [entry for entry in mutations if not entry["detected"]])

    def test_tampered_journal_line_fails_a1(self):
        packet = self._copy_packet()
        journal = os.path.join(packet, "audit.jsonl")
        with open(journal, "r", encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        index = next((pos for pos, line in enumerate(lines) if '"mode":"LIVE"' in line), None)
        self.assertIsNotNone(index, "aucune ligne LIVE dans le journal")
        lines[index] = lines[index].replace('"mode":"LIVE"', '"mode":"LIVF"', 1)
        with open(journal, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))
        report = verify_packet(packet)
        self.assertEqual(report["verdict"], "FAIL")
        failed_ids = {check["id"] for check in report["checks"] if not check["ok"]}
        self.assertIn("A1.exec.chain", failed_ids)

    def test_deleted_receipt_fails(self):
        packet = self._copy_packet()
        receipts = glob.glob(os.path.join(packet, "receipts", "*.json"))
        self.assertTrue(receipts)
        os.unlink(receipts[0])
        report = verify_packet(packet)
        self.assertEqual(report["verdict"], "FAIL")
        failed_ids = {check["id"] for check in report["checks"] if not check["ok"]}
        self.assertTrue({"A3.packet.sha256", "A8.receipts.cross"} & failed_ids, failed_ids)

    def test_frozen_verifier_runs_standalone(self):
        launcher = os.path.join(self.packet_dir, "verify", "orvyren_verify.py")
        self.assertTrue(os.path.isfile(launcher))
        result = subprocess.run([sys.executable, launcher, "."],
                                cwd=self.packet_dir, capture_output=True, text=True,
                                timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OFFLINE_PASS", result.stdout)
        self.assertFalse(os.path.isdir(os.path.join(self.packet_dir, "verify",
                                                    "_orvyren", "__pycache__")),
                         "le lanceur ne doit pas écrire de bytecode dans le paquet")

    def test_module_invocation_with_pythonpath(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"))
        result = subprocess.run([sys.executable, "-m", "orvyren.verify", self.packet_dir],
                                cwd=ROOT, capture_output=True, text=True, timeout=300,
                                env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OFFLINE_PASS", result.stdout)

    def test_root_runner_invocation(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "run_verify.py"),
                                 self.packet_dir],
                                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OFFLINE_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
