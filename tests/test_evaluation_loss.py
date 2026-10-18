#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests de la fonction de perte G1 — les six propriétés de W2-D §B.6.

Chaque test porte le numéro T1–T6 du document. Le cas chiffré de W2-D §B.2
(« 20 » bugué contre « 10 » correct) est reproduit pour montrer que le
non-double-comptage est détecté en une exécution.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.evaluation import loss  # noqa: E402


class TestLossProperties(unittest.TestCase):
    """T1–T6 : les six tests de propriété exigés avant le gel G1."""

    def test_t1_neutralite_non_double_comptage(self):
        """T1 — P_exec = P_T, k = 0 ⇒ R(a) = 0 pour toute action (détecte §B.2)."""
        table = loss.regret_table(
            numeraire=0.0,
            quantity=100.0,
            p_t0=1.0,
            p_terminal=0.90,
            p_exec_by_size=lambda x: 0.90,
            cost=0.0,
        )
        for row in table["actions"]:
            self.assertAlmostEqual(row["regret_usd"], 0.0, places=12)

    def test_t2_invariance_par_translation(self):
        """T2 — ajouter la même constante m à toutes les richesses ⇒ R inchangé."""
        w_t0 = 100.0
        wealths = [90.0, 95.0, 100.0]  # conserver, céder la moitié, céder tout
        m = 1234.5
        base_losses = [loss.loss(w_t0, w) for w in wealths]
        base_floor = loss.min_feasible_loss(base_losses)
        base_regrets = [loss.regret(value, base_floor) for value in base_losses]
        shifted_losses = [loss.loss(w_t0 + m, w + m) for w in wealths]
        shifted_floor = loss.min_feasible_loss(shifted_losses)
        shifted_regrets = [loss.regret(value, shifted_floor) for value in shifted_losses]
        for original, moved in zip(base_regrets, shifted_regrets):
            self.assertAlmostEqual(original, moved, places=12)

    def test_t3_monotonie_en_cout(self):
        """T3 — k croissant ⇒ L(céder) et R(céder) croissants."""
        previous_loss = None
        previous_regret = None
        for cost in (0.0, 10.0, 50.0, 200.0):
            table = loss.regret_table(0.0, 100.0, 1.0, 0.90, lambda x: 1.00, cost=cost)
            sell_row = [row for row in table["actions"] if row["sold"] == 100.0][0]
            if previous_loss is not None:
                self.assertGreater(sell_row["loss_usd"], previous_loss)
                self.assertGreaterEqual(sell_row["regret_usd"], previous_regret)
            previous_loss = sell_row["loss_usd"]
            previous_regret = sell_row["regret_usd"]

    def test_t4_coherence_de_signe(self):
        """T4 — P_exec > P_T ⇒ agir a un regret nul, ne rien faire un regret positif."""
        table = loss.regret_table(0.0, 100.0, 1.0, 0.90, lambda x: 1.00, cost=0.0)
        sell = [row for row in table["actions"] if row["sold"] == 100.0][0]
        keep = [row for row in table["actions"] if row["sold"] == 0.0][0]
        self.assertAlmostEqual(sell["regret_usd"], 0.0, places=12)
        self.assertAlmostEqual(keep["regret_usd"], 10.0, places=12)
        # l'action de l'agent est la vente (a), A0 = conserver
        self.assertEqual(loss.regret_negative(sell["loss_usd"], keep["loss_usd"]), 0.0)
        self.assertAlmostEqual(loss.regret_positive(sell["loss_usd"], keep["loss_usd"]), 10.0, places=12)

    def test_t5_additivite_de_l_inventaire(self):
        """T5 — deux lots identiques ⇒ regret double ; lot partiel ⇒ linéaire en x."""
        ref = loss.regret_table(0.0, 100.0, 1.0, 0.90, lambda x: 1.00, cost=0.0)
        double = loss.regret_table(0.0, 200.0, 1.0, 0.90, lambda x: 1.00, cost=0.0)
        keep_ref = [row for row in ref["actions"] if row["sold"] == 0.0][0]["regret_usd"]
        keep_double = [row for row in double["actions"] if row["sold"] == 0.0][0]["regret_usd"]
        self.assertAlmostEqual(keep_double, 2.0 * keep_ref, places=9)
        # interpolation linéaire sur un lot partiel (pas de coût, écart de prix constant)
        rows = {row["sold"]: row for row in ref["actions"]}
        self.assertAlmostEqual(rows[25.0]["regret_usd"], 0.75 * keep_ref, places=9)
        self.assertAlmostEqual(rows[50.0]["regret_usd"], 0.50 * keep_ref, places=9)

    def test_t6_reference_degeneree(self):
        """T6 — décote nulle (P_t = 1) ⇒ tous les regrets = 0 ; l'action inutile coûte k."""
        table = loss.regret_table(0.0, 100.0, 1.0, 1.0, lambda x: 1.0, cost=0.0)
        for row in table["actions"]:
            self.assertAlmostEqual(row["regret_usd"], 0.0, places=12)
        costly = loss.regret_table(0.0, 100.0, 1.0, 1.0, lambda x: 1.0, cost=25.0)
        sell = [row for row in costly["actions"] if row["sold"] == 100.0][0]
        self.assertAlmostEqual(sell["loss_usd"], 25.0, places=12)
        self.assertAlmostEqual(sell["regret_usd"], 25.0, places=12)

    def test_exemple_w2d_b2_le_bug_affichait_vingt(self):
        """W2-D §B.2 : l'écart réel est q·(1−P_T) (l'ancienne formule affichait 20)."""
        # L'écart est mesuré depuis les deux pertes, dérivées des paramètres du
        # cas. L'identité numérique directe `20.0 - 10.0 == 100.0 * (1.0 - 0.90)`
        # était tautologique : vraie par construction, quel que soit le code
        # testé (re-scellement visible G1 du 2026-10-18, voir le journal des
        # variantes).
        q, p_terminal = 100.0, 0.90
        keep_loss = loss.loss(loss.wealth_keep(0.0, q, 1.0),
                              loss.wealth_keep(0.0, q, p_terminal))
        sell_loss = loss.loss(
            loss.wealth_keep(0.0, q, 1.0),
            loss.wealth_sell(0.0, q, q, p_exec=1.00, p_terminal=p_terminal,
                             cost=0.0),
        )
        self.assertAlmostEqual(keep_loss, q * (1.0 - p_terminal), places=12)
        self.assertAlmostEqual(sell_loss, 0.0, places=12)
        self.assertAlmostEqual(keep_loss - sell_loss, q * (1.0 - p_terminal),
                               places=12)


class TestLossPersonas(unittest.TestCase):
    """Variantes persona DAO/desk et conventions de valorisation."""

    def test_liquidation_exige_un_prix_mesure(self):
        """Convention « liquidation » sans échelle de profondeur : refus explicite."""
        with self.assertRaises(loss.ValuationError):
            loss.wealth_sell(0.0, 100.0, 50.0, 0.95, 0.90, convention=loss.CONVENTION_LIQUIDATION)
        # avec un prix de liquidation mesuré, le calcul est plus prudent que P_T
        w = loss.wealth_sell(
            0.0,
            100.0,
            50.0,
            0.95,
            0.90,
            convention=loss.CONVENTION_LIQUIDATION,
            liquidation_price=lambda remaining: 0.85,
        )
        self.assertAlmostEqual(w, 50.0 * 0.95 + 50.0 * 0.85, places=12)

    def test_desk_reentree_formule_w2d_e3(self):
        """Desk : ΔP&L = q(P_exec − P_T) − k (cas « coupe tardive » : −4,20 %).

        Le repère du P&L contre l'inaction est P_ref = P_T (forme W2-D §E.3) ;
        avec le repère d'inventaire P_ref = 1,00 la lecture est différente et
        doit être publiée séparément (jamais moyennée).
        """
        w_t = loss.wealth_sell_reenter(0.0, 2_000_000.0, 2_000_000.0, 0.95, 0.99, cost=4000.0)
        self.assertAlmostEqual(w_t, 2_000_000.0 * 0.99 - 84_000.0, places=6)
        pnl_vs_inaction = loss.delta_pnl_net(2_000_000.0, 2_000_000.0, 0.95, 0.99, 0.99, cost=4000.0)
        self.assertAlmostEqual(pnl_vs_inaction, -84_000.0, places=6)
        self.assertAlmostEqual(pnl_vs_inaction, 2_000_000.0 * (0.95 - 0.99) - 4000.0, places=6)
        pnl_vs_pair = loss.delta_pnl_net(2_000_000.0, 2_000_000.0, 0.95, 0.99, 1.0, cost=4000.0)
        self.assertAlmostEqual(pnl_vs_pair, -104_000.0, places=6)
        self.assertAlmostEqual(loss.pnl_bp(pnl_vs_inaction, 2_000_000.0, 1.0), -420.0, places=6)
        self.assertAlmostEqual(pnl_vs_inaction / (2_000_000.0 * 1.0), -0.042, places=6)

    def test_dao_perte_evitee_conditionnelle(self):
        """DAO : E[perte] = P·conditionnel − (1−P)·coût AR, les deux facteurs visibles."""
        result = loss.dao_expected_avoided_loss(0.2, 110_912.0, 800_000.0)
        self.assertAlmostEqual(result["conditional_term_usd"], 22_182.4, places=6)
        self.assertAlmostEqual(result["premium_term_usd"], 640_000.0, places=6)
        self.assertAlmostEqual(result["expected_avoided_loss_usd"], -617_817.6, places=6)
        with self.assertRaises(loss.ValuationError):
            loss.dao_expected_avoided_loss(1.5, 1.0, 1.0)

    def test_runway_reference_ens(self):
        """Jours de runway : référence 44 932 $/j (ENS IPS, 16,4 M$/an ÷ 365)."""
        self.assertEqual(loss.OPEX_REF_USD_PER_DAY, 44932)
        self.assertAlmostEqual(loss.runway_days(100_000.0), 100_000.0 / 44_932.0, places=9)
        self.assertAlmostEqual(loss.runway_days(2_500_000.0), 55.64, places=2)

    def test_agregats_desk(self):
        """Sharpe/Sortino/MaxDD : None quand non calculables, jamais de chiffre inventé."""
        self.assertIsNone(loss.sharpe_ratio([0.01]))
        self.assertIsNone(loss.sharpe_ratio([0.01, 0.01]))
        value = loss.sharpe_ratio([0.01, -0.005, 0.02])
        self.assertIsNotNone(value)
        self.assertIsNone(loss.max_drawdown([]))
        self.assertAlmostEqual(loss.max_drawdown([1.0, 1.2, 0.9, 1.1]), 0.9 / 1.2 - 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
