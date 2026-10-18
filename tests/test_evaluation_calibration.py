#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests de la calibration C1–C7 — KAT exacts de B7 §b.2 + bornes + cascade.

Vecteur KAT (B7 §b.2, raw_b7) : ``p = [0,2 ×5 ; 0,8 ×5]``,
``y = [0,0,0,0,0, 1,1,0,1,1]`` → BS = 0,10 ; REL = 0,02 ; RES = 0,16 ;
UNC = 0,24 ; ECE = 0,10 ; ȳ = 0,40. Tolérance 1e-12.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.evaluation import calibration as C  # noqa: E402

P_KAT = [0.2] * 5 + [0.8] * 5
Y_KAT = [0, 0, 0, 0, 0, 1, 1, 0, 1, 1]


class TestKnownAnswerVector(unittest.TestCase):
    """Le vecteur à réponse connue — test unitaire de référence de calibration.py."""

    def test_bs_rel_res_unc_ece_ybar_exacts(self):
        self.assertAlmostEqual(C.brier_score(P_KAT, Y_KAT), 0.10, delta=1e-12)
        decomposition = C.murphy_decomposition(P_KAT, Y_KAT)
        self.assertAlmostEqual(decomposition["rel"], 0.02, delta=1e-12)
        self.assertAlmostEqual(decomposition["res"], 0.16, delta=1e-12)
        self.assertAlmostEqual(decomposition["unc"], 0.24, delta=1e-12)
        self.assertAlmostEqual(decomposition["rel_minus_res_plus_unc"], 0.10, delta=1e-12)
        self.assertAlmostEqual(decomposition["ybar"], 0.40, delta=1e-12)
        self.assertAlmostEqual(C.ece(P_KAT, Y_KAT), 0.10, delta=1e-12)

    def test_bins_du_vecteur_kat(self):
        """Bin 2 : n=5, conf 0,2, acc 0,0 ; bin 8 : n=5, conf 0,8, acc 0,8 (B7 §b.2)."""
        rows = {row["bin"]: row for row in C.reliability_table(P_KAT, Y_KAT)}
        self.assertEqual(rows[2]["n_b"], 5)
        self.assertAlmostEqual(rows[2]["conf_b"], 0.2, delta=1e-12)
        self.assertAlmostEqual(rows[2]["acc_b"], 0.0, delta=1e-12)
        self.assertEqual(rows[8]["n_b"], 5)
        self.assertAlmostEqual(rows[8]["conf_b"], 0.8, delta=1e-12)
        self.assertAlmostEqual(rows[8]["acc_b"], 0.8, delta=1e-12)
        # aucun intervalle silencieux : les 10 intervalles sont présents
        self.assertEqual(len(rows), 10)

    def test_brier_contributions_somment_au_score(self):
        contribs = C.brier_contributions(P_KAT, Y_KAT)
        self.assertAlmostEqual(sum(contribs) / len(contribs), C.brier_score(P_KAT, Y_KAT), delta=1e-12)


class TestWilson(unittest.TestCase):
    """C5 — bornes de Wilson contre la table raw_b7 (±0,001, B7 §e.6)."""

    def test_zero_succes_sur_6_et_12(self):
        upper6 = C.wilson_upper_for_zero(6)
        upper12 = C.wilson_upper_for_zero(12)
        self.assertAlmostEqual(upper6, 0.390, delta=1e-3)   # 39,0 % (B7 §b.2)
        # 0/12 : valeur exacte 0,242494 (24,2494 %). B7 §b.2 imprime 24,2 % ; la
        # note de sprint imprime 24,3 % (arrondi z=1,96 → 24,2502 %). Les deux
        # impressions sont à moins de 1e-3 de la valeur calculée — aucune des
        # deux n'est recopiée comme si elle était exacte.
        self.assertAlmostEqual(upper12, 0.242494, delta=1e-6)
        self.assertLess(abs(upper12 - 0.242), 1e-3)
        self.assertLess(abs(upper12 - 0.243), 1e-3)

    def test_table_raw_b7_complete(self):
        """[3,0 % ; 56,4 %] pour 1/6 ; [4,7 % ; 44,8 %] pour 2/12 ; 9,6 % pour 0/36."""
        low, high = C.wilson_interval(1, 6)
        self.assertAlmostEqual(low, 0.030, delta=1e-3)
        self.assertAlmostEqual(high, 0.564, delta=1e-3)
        low, high = C.wilson_interval(2, 12)
        self.assertAlmostEqual(low, 0.047, delta=1e-3)
        self.assertAlmostEqual(high, 0.448, delta=1e-3)
        self.assertAlmostEqual(C.wilson_upper_for_zero(36), 0.096, delta=1e-3)
        self.assertAlmostEqual(C.wilson_upper_for_zero(100), 0.037, delta=1e-3)

    def test_bornes_dans_zero_un_et_erreurs(self):
        low, high = C.wilson_interval(0, 6)
        self.assertEqual(low, 0.0)
        self.assertLess(high, 1.0)
        with self.assertRaises(C.CalibrationError):
            C.wilson_interval(1, 0)
        with self.assertRaises(C.CalibrationError):
            C.wilson_interval(7, 6)


class TestMcNemar(unittest.TestCase):
    """McNemar exact : 6-0 → 0,03125 (B7 §e.5 / note de sprint)."""

    def test_six_zero(self):
        self.assertAlmostEqual(C.mcnemar_exact(6, 0), 0.03125, delta=1e-12)

    def test_symetrie_et_equilibre(self):
        self.assertAlmostEqual(C.mcnemar_exact(0, 6), 0.03125, delta=1e-12)
        self.assertAlmostEqual(C.mcnemar_exact(1, 1), 1.0, delta=1e-12)
        # monotone STRICT en déséquilibre : (6,0) < (5,1) < (4,2) — le `+ 1.0`
        # rendait l'assertion tautologique (0,21875 < 1,6875 toujours vrai).
        # Re-scellement visible G5 du 2026-10-18 (journal des variantes).
        self.assertLess(C.mcnemar_exact(6, 0), C.mcnemar_exact(5, 1))
        self.assertLess(C.mcnemar_exact(5, 1), C.mcnemar_exact(4, 2))
        with self.assertRaises(C.CalibrationError):
            C.mcnemar_exact(0, 0)


class TestBootstrap(unittest.TestCase):
    """C6 — bootstrap par blocs déterministe (graine fixée)."""

    def test_determinisme_meme_graine(self):
        values = C.brier_contributions(P_KAT, Y_KAT)
        first = C.block_bootstrap_ci(values, block_size=6, n_reps=2000, seed=42)
        second = C.block_bootstrap_ci(values, block_size=6, n_reps=2000, seed=42)
        self.assertEqual(first, second)

    def test_graines_differentes_changent_le_resultat(self):
        values = [i / 100.0 for i in range(80)]
        first = C.block_bootstrap_ci(values, block_size=6, n_reps=1000, seed=1)
        second = C.block_bootstrap_ci(values, block_size=6, n_reps=1000, seed=2)
        self.assertNotEqual((first["ci_low"], first["ci_high"]), (second["ci_low"], second["ci_high"]))

    def test_ci_encadre_la_moyenne_et_bornes(self):
        values = [0.0] * 20 + [1.0] * 20
        result = C.block_bootstrap_ci(values, block_size=6, n_reps=1000, seed=7)
        self.assertLessEqual(result["ci_low"], result["mean"])
        self.assertLessEqual(result["mean"], result["ci_high"])
        self.assertAlmostEqual(result["mean"], 0.5, delta=1e-12)
        with self.assertRaises(C.CalibrationError):
            C.block_bootstrap_ci([], seed=1)

    def test_percentile(self):
        self.assertAlmostEqual(C.bootstrap_percentile([0.0, 1.0, 2.0, 3.0], 1.5), 50.0, delta=1e-12)


class TestCascadeEtGardeFous(unittest.TestCase):
    """Cascade §b.3, compétence C7, refus explicites."""

    def test_libelles_de_la_cascade(self):
        self.assertEqual(C.verdict_for_n(0), C.VERDICT_NOT_COMPUTED)
        self.assertEqual(C.verdict_for_n(4), C.VERDICT_NOT_COMPUTED)
        self.assertEqual(C.verdict_for_n(5), C.VERDICT_NON_CONCLUSIVE)
        self.assertEqual(C.verdict_for_n(99), C.VERDICT_NON_CONCLUSIVE)
        self.assertEqual(C.verdict_for_n(100), C.VERDICT_CLAIM_POSSIBLE)

    def test_rapport_refuse_n_inferieur_5(self):
        with self.assertRaises(C.CalibrationError):
            C.calibration_report([0.5] * 4, [0, 1, 0, 1])

    def test_rapport_complet_et_non_conclusionnel(self):
        report = C.calibration_report(P_KAT, Y_KAT)
        self.assertEqual(report["n"], 10)
        self.assertEqual(report["verdict"], C.VERDICT_NON_CONCLUSIVE)
        self.assertAlmostEqual(report["bs"], 0.10, delta=1e-12)
        self.assertAlmostEqual(report["bss"], 1 - 0.10 / 0.24, delta=1e-12)
        self.assertEqual(report["bins"], 10)
        self.assertIn("bs_bootstrap_ci", report)

    def test_bss_none_si_climatologie_degeneree(self):
        self.assertIsNone(C.brier_skill_score(0.1, 0.0))
        self.assertIsNone(C.brier_skill_score(0.1, 1.0))
        self.assertAlmostEqual(C.brier_skill_score(0.1, 0.4), 1 - 0.1 / 0.24, delta=1e-12)

    def test_phrase_obligatoire_zero_echec(self):
        self.assertIn("0/6", C.PHRASE_ZERO_SUCCESS)
        self.assertIn("39", C.PHRASE_ZERO_SUCCESS)

    def test_validation_entrees(self):
        with self.assertRaises(C.CalibrationError):
            C.brier_score([0.5], [0, 1])
        with self.assertRaises(C.CalibrationError):
            C.brier_score([1.2], [1])
        with self.assertRaises(C.CalibrationError):
            C.brier_score([0.5], [2])


if __name__ == "__main__":
    unittest.main()
