#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests du registre des fenêtres et des embargos G3 (B7 §d.2, DOC2 §5.8.4).

Contrats testés : détection de chevauchement, refus d'écriture EVAL sans gel,
embargo de données (bande de 24 h), embargo de calibration croisée, et
validité du paquet de gel réellement présent dans ``frozen/``.
"""

import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.evaluation import windows as W  # noqa: E402


def make_window(window_id, set_label, start, end, kind=W.KIND_STRESS):
    return W.Window(
        window_id=window_id,
        episode_id="synthetique",
        set_label=set_label,
        kind=kind,
        start_utc=start,
        end_utc=end,
        sources=("test",),
        role="fenêtre synthétique de test",
    )


class TestRegistre(unittest.TestCase):
    def test_registre_dev_sans_chevauchement(self):
        W.check_no_overlap(W.DEV_WINDOWS)  # ne lève pas
        W.check_no_overlap(W.EVAL_WINDOWS)

    def test_fenetres_enregistrees_tracees(self):
        for window in W.DEV_WINDOWS + W.EVAL_WINDOWS:
            self.assertTrue(window.sources, f"{window.window_id} sans source")
            self.assertGreater(window.duration_hours(), 0.0)

    def test_fenetres_non_derivables_ecrites_not_done(self):
        statuses = {entry["status"] for entry in W.PENDING_WINDOWS}
        self.assertIn("NOT DONE", statuses)
        for entry in W.PENDING_WINDOWS:
            self.assertTrue(entry["reason"].strip(), "un NOT DONE sans motif n'est pas acceptable")

    def test_fenetre_invalide_refusee(self):
        with self.assertRaises(W.WindowError):
            make_window("x", "prod", "2023-01-01T00:00:00Z", "2023-01-02T00:00:00Z")
        with self.assertRaises(W.WindowError):
            make_window("x", W.SET_DEV, "2023-01-02T00:00:00Z", "2023-01-01T00:00:00Z")

    def test_chevauchement_detecte_et_leve(self):
        left = make_window("a", W.SET_DEV, "2023-03-10T00:00:00Z", "2023-03-14T00:00:00Z")
        right = make_window("b", W.SET_DEV, "2023-03-13T00:00:00Z", "2023-03-16T00:00:00Z")
        self.assertEqual(W.overlap_violations([left, right]), [("a", "b")])
        with self.assertRaises(W.WindowError):
            W.check_no_overlap([left, right])


class TestEmbargoDonnees(unittest.TestCase):
    def test_bande_24h_croisee_detectee(self):
        dev = make_window("dev", W.SET_DEV, "2026-04-16T12:00:00Z", "2026-04-16T18:00:00Z")
        ev = make_window("eval", W.SET_EVAL, "2026-04-17T00:00:00Z", "2026-04-21T00:00:00Z")
        violations = W.data_embargo_violations([dev], [ev])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["dev_window"], "dev")
        self.assertEqual(violations[0]["eval_window"], "eval")

    def test_dev_antérieur_a_la_bande_accepte(self):
        dev = make_window("dev", W.SET_DEV, "2026-04-15T00:00:00Z", "2026-04-15T12:00:00Z")
        ev = make_window("eval", W.SET_EVAL, "2026-04-17T00:00:00Z", "2026-04-21T00:00:00Z")
        self.assertEqual(W.data_embargo_violations([dev], [ev]), [])

    def test_registre_reel_sans_violation(self):
        self.assertEqual(W.data_embargo_violations(W.DEV_WINDOWS, W.EVAL_WINDOWS), [])


class TestCalibrationCroisee(unittest.TestCase):
    def test_chevauchement_de_mois_refuse(self):
        calm = make_window("calme-eval", W.SET_EVAL, "2025-01-12T00:00:00Z", "2025-01-15T00:00:00Z", kind=W.KIND_CALME)
        violations = W.cross_calibration_violations(["2025-01"], [calm])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["calibration_period"], "2025-01")

    def test_mois_disjoints_acceptes(self):
        calm = make_window("calme-eval", W.SET_EVAL, "2025-06-12T00:00:00Z", "2025-06-15T00:00:00Z", kind=W.KIND_CALME)
        self.assertEqual(W.cross_calibration_violations(["2023-04", "2023-05"], [calm]), [])

    def test_format_de_periode_valide(self):
        with self.assertRaises(W.WindowError):
            W.cross_calibration_violations(["2025"], [])


class TestPorteDeGel(unittest.TestCase):
    def test_paquet_reel_verifie(self):
        hashes = W.verify_frozen_package(os.path.join(REPO_ROOT, "frozen"))
        self.assertEqual(set(hashes), set(W.FROZEN_FILES))

    def test_gel_absent_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(W.FreezeGateError):
                W.verify_frozen_package(tmp)
            with self.assertRaises(W.FreezeGateError):
                W.eval_run_gate(tmp)

    def test_gel_non_concordant_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "G1_fonction_de_perte.md")
            with open(target, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("contenu\n")
            with open(os.path.join(tmp, "G1.sha256"), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(f"{W.sha256_file(target)}  G1_fonction_de_perte.md\n")
            # paquet incomplet (G2..G6 absents) → refus
            with self.assertRaises(W.FreezeGateError):
                W.verify_frozen_package(tmp)
            for name in ("G2", "G3", "G4", "G5", "G6"):
                document = os.path.join(tmp, f"{name}_doc.md")
                with open(document, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("contenu\n")
                with open(os.path.join(tmp, f"{name}.sha256"), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(f"{W.sha256_file(document)}  {name}_doc.md\n")
            self.assertEqual(len(W.verify_frozen_package(tmp)), 6)
            # fichier modifié après coup → refus
            with open(target, "a", encoding="utf-8", newline="\n") as handle:
                handle.write("ligne ajoutée\n")
            with self.assertRaises(W.FreezeGateError):
                W.verify_frozen_package(tmp)

    def test_verrou_de_reexecution(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = os.path.join(tmp, "eval_run.lock")
            with open(lock, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("premiere execution\n")
            with self.assertRaises(W.FreezeGateError):
                W.eval_run_gate(os.path.join(REPO_ROOT, "frozen"), lock_path=lock, force=False)
            mention = W.eval_run_gate(os.path.join(REPO_ROOT, "frozen"), lock_path=lock, force=True)
            self.assertEqual(mention, W.FORCED_RERUN_MENTION)
            self.assertIn("invalide pour la revendication", mention)
            # sans verrou ni forcage : première exécution permise (None)
            self.assertIsNone(W.eval_run_gate(os.path.join(REPO_ROOT, "frozen"), lock_path=os.path.join(tmp, "absent.lock")))


if __name__ == "__main__":
    unittest.main()
