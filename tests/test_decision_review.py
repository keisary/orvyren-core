#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Revue profonde 2026-10-17 — src/orvyren/decision/ + src/orvyren/policy/.

Tests de non-régression des corrections de la revue :
  * F-R1 bornes décimales exactes (plafond cumulé, plancher, exposition) ;
  * F-R2 plafonds non finis / non positifs — fail-closed (évaluation + chargement) ;
  * F-R3 `permission_expires_at` naïf ne crash plus (comparaison aware/naive) ;
  * F-R4 `floor_balance` non fini refusé (plus jamais ignoré silencieusement) ;
  * F-R5 `class_of` P-PERS : 12 h exact appartient à "<=12 h" (et l'injecteur
    contrefactuel "<=12 h" produit bien une classe "<=12 h") ;
  * F-R6 fourniture non positive : plus de ZeroDivisionError, H3 signale l'artefact ;
  * F-R7 NaN dans available_to_move / bounded_size => 0.0 (jamais fail-open) ;
  * F-R8 intent_id horodaté en UTC véridique (suffixe Z) ;
  * F-R9 montants hors grille de base units refusés (empreinte P10 non collisionnée) ;
  * F-R10 mini-YAML : flow style imbriqué refusé (comme documenté), `[]`/`{}` acceptés.

Run: python -m pytest tests/test_decision_review.py -q
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.decision.axes import authorization_via_policy  # noqa: E402
from orvyren.decision.catalog import bounded_size  # noqa: E402
from orvyren.decision.exposure import available_to_move  # noqa: E402
from orvyren.decision.predicates import BY_ID, inject_outcome  # noqa: E402
from orvyren.decision.predicates import evaluate_predicate  # noqa: E402
from orvyren.decision.scenarios import (SUPPLY_METRIC, SUPPLY_VENUE,  # noqa: E402
                                        Observation, classify_hypotheses)
from orvyren.policy import (ALLOWED_ASSET, ALLOWED_CHAIN_ID,  # noqa: E402
                            Intent, PolicyConfig, PolicyState,
                            default_config, evaluate, intent_fingerprint)
from orvyren.policy.miniyaml import MiniYamlError  # noqa: E402
from orvyren.policy.miniyaml import load as yaml_load  # noqa: E402
from orvyren.policy.miniyaml import load_file as yaml_load_file  # noqa: E402

RESERVE = "0x1111111111111111111111111111111111111111"
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def intent(**kw: Any) -> Intent:
    base = dict(intent_id="intent-r1", action="transfer", chain_id=ALLOWED_CHAIN_ID,
                asset=ALLOWED_ASSET, amount=100.0, recipient=RESERVE, created_at=NOW)
    base.update(kw)
    return Intent(**base)


def cfg(**over: Any) -> PolicyConfig:
    config = PolicyConfig(
        allowed_recipients=frozenset({RESERVE.lower()}),
        permission_expires_at=NOW + timedelta(hours=24),
    )
    for key, value in over.items():
        setattr(config, key, value)
    return config


class TestBornesDecimales(unittest.TestCase):
    """F-R1 — les limites d'argent se comparent en espace décimal, pas en flottant."""

    def test_cumul_frontiere_exacte_autorisee(self):
        # 0.1 + 0.2 vaut 0.30000000000000004 en flottant : l'ancien `>` refusait
        # une frontière exactement atteinte (faux DENY).
        decision = evaluate(intent(amount=0.2), cfg(max_cumulative=0.3),
                            now=NOW, cumulative_spent=0.1)
        self.assertEqual(decision.verdict, "ALLOW", decision.reasons)

    def test_cumul_au_dessus_refuse(self):
        decision = evaluate(intent(amount=0.2001), cfg(max_cumulative=0.3),
                            now=NOW, cumulative_spent=0.1)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_PERIOD_CAP", decision.reasons)

    def test_plancher_frontiere_exacte_non_franchie(self):
        # 0.3 - 0.1 vaut 0.19999999999999998 en flottant : l'ancien `<`
        # déclenchait un FLOOR_BREACH faux sur la frontière.
        state = PolicyState(paused=False, agent_member=True, envelope_status="PASS",
                            available_balance=0.3, floor_balance=0.2)
        decision = evaluate(intent(amount=0.1), cfg(asset_decimals=None),
                            now=NOW, state=state)
        self.assertNotIn("FLOOR_BREACH", decision.reasons)
        self.assertEqual(decision.verdict, "ALLOW", decision.reasons)

    def test_plancher_reellement_franchi_refuse(self):
        state = PolicyState(paused=False, agent_member=True, envelope_status="PASS",
                            available_balance=0.3, floor_balance=0.25)
        decision = evaluate(intent(amount=0.1), cfg(asset_decimals=None),
                            now=NOW, state=state)
        self.assertIn("FLOOR_BREACH", decision.reasons)

    def test_exposition_frontiere_exacte_autorisee(self):
        state = PolicyState(paused=False, agent_member=True, envelope_status="PASS",
                            available_balance=1.0, exposure=0.2, exposure_cap=0.3)
        decision = evaluate(intent(amount=0.1), cfg(asset_decimals=None),
                            now=NOW, state=state)
        self.assertNotIn("EXPOSURE_ABOVE_CAP", decision.reasons)
        self.assertEqual(decision.verdict, "ALLOW", decision.reasons)

    def test_budget_frontiere_atteinte_refusee(self):
        state = PolicyState(paused=False, agent_member=True, envelope_status="PASS",
                            available_balance=500.0, budget_spent=0.10, budget_cap=0.10)
        decision = evaluate(intent(), cfg(), now=NOW, state=state)
        self.assertIn("BUDGET_EXCEEDED", decision.reasons)


class TestPlafondsNonFinis(unittest.TestCase):
    """F-R2 — un plafond illisible désactiveait silencieusement la limite (NaN)."""

    def test_max_per_tx_nan_fail_closed(self):
        decision = evaluate(intent(), cfg(max_per_tx=float("nan")), now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_TX_CAP", decision.reasons)

    def test_max_cumulative_inf_fail_closed(self):
        decision = evaluate(intent(), cfg(max_cumulative=float("inf")), now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_PERIOD_CAP", decision.reasons)

    def test_max_per_tx_negatif_fail_closed(self):
        decision = evaluate(intent(), cfg(max_per_tx=-1.0), now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_TX_CAP", decision.reasons)

    def _mini_policy(self, cap_line: str) -> str:
        return (
            "schema: orvyren-policy/v1\n"
            "policy_version: v1.0\n"
            "chain_id: 84532\n"
            "asset: \"0x036cbd53842c5426634e7929541ec2318f3dcf7e\"\n"
            + cap_line +
            "recipients:\n"
            "  - 0x1111111111111111111111111111111111111111\n"
        )

    def _load(self, cap_line: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "policy_v1.yaml")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self._mini_policy(cap_line))
            yaml_load_file(path)  # le YAML lui-même doit se charger
            from orvyren.policy import load_policy
            load_policy(path)

    def test_load_policy_refuse_plafond_nan(self):
        with self.assertRaises(MiniYamlError):
            self._load("max_per_tx: nan\n")

    def test_load_policy_refuse_plafond_infini(self):
        with self.assertRaises(MiniYamlError):
            self._load("max_cumulative_24h: inf\n")

    def test_load_policy_refuse_plafond_non_positif(self):
        with self.assertRaises(MiniYamlError):
            self._load("max_per_tx: \"-1.0\"\n")

    def test_load_policy_refuse_decimales_negatives(self):
        with self.assertRaises(MiniYamlError):
            self._load("max_per_tx: \"100.0\"\nasset_decimals: -1\n")

    def test_load_policy_accepte_un_bundle_normal(self):
        self._load("max_per_tx: \"100.0\"\nmax_cumulative_24h: \"300.0\"\n")


class TestPermissionNaive(unittest.TestCase):
    """F-R3 — une expiration naïve levait un TypeError (aware vs naive)."""

    def test_expiration_naive_valide_passe(self):
        config = default_config(RESERVE, ttl_hours=24,
                                now=datetime(2026, 10, 14, 12, 0))  # naïf = UTC
        decision = evaluate(intent(), config, now=NOW)
        self.assertEqual(decision.verdict, "ALLOW", decision.reasons)

    def test_expiration_naive_depassee_refusee(self):
        config = default_config(RESERVE, ttl_hours=1,
                                now=datetime(2026, 10, 14, 10, 0))  # expire à 11:00
        decision = evaluate(intent(), config, now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("PERMISSION_EXPIRED", decision.reasons)

    def test_expiration_naive_directe_ne_crash_pas(self):
        config = cfg(permission_expires_at=datetime(2026, 10, 13, 12, 0))
        decision = evaluate(intent(), config, now=NOW)
        self.assertIn("PERMISSION_EXPIRED", decision.reasons)


class TestFloorIllisible(unittest.TestCase):
    """F-R4 — un floor_balance NaN était ignoré silencieusement (fail-open)."""

    def test_floor_nan_refuse(self):
        state = PolicyState(paused=False, agent_member=True, envelope_status="PASS",
                            available_balance=100.0, floor_balance=float("nan"))
        decision = evaluate(intent(amount=50.0), cfg(), now=NOW, state=state)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("BALANCE_UNREADABLE", decision.reasons)


class TestClassePpers(unittest.TestCase):
    """F-R5 — la frontière 12 h de P-PERS doit coller aux libellés enregistrés."""

    def test_frontiere_12h_dans_la_premiere_classe(self):
        predicate = BY_ID["P-PERS"]
        self.assertEqual(predicate.class_of(12.0), "<=12 h")
        self.assertEqual(predicate.class_of(11.999), "<=12 h")
        self.assertEqual(predicate.class_of(12.0001), ">12 h")

    def test_injecteur_12h_coherent_avec_la_classe(self):
        # un épisode d'alerte de 20 h, injecté en "<=12 h", est rabattu à une
        # emprise de 12 h exacte : la classe doit être "<=12 h", pas ">12 h"
        start = datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc)
        rows = []
        for hour in range(20):
            moment = start + timedelta(hours=hour)
            rows.append(Observation(timestamp_utc=moment.isoformat(), ts=moment,
                                    venue="bitstamp", metric="price_usd",
                                    value=0.90, extra="", retrieved_at=""))
        rows.append(Observation(timestamp_utc=start.isoformat(), ts=start,
                                venue="binance", metric="price_usd",
                                value=1.0, extra="", retrieved_at=""))
        end = start + timedelta(hours=24)
        injected = inject_outcome("P-PERS", "<=12 h", rows, start, end, end)
        fact = evaluate_predicate("P-PERS", injected, start, end)
        self.assertEqual(fact["class"], "<=12 h", fact)

    def test_injecteur_12h_plus_long_classe_persistant(self):
        start = datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc)
        rows = []
        for hour in range(20):
            moment = start + timedelta(hours=hour)
            rows.append(Observation(timestamp_utc=moment.isoformat(), ts=moment,
                                    venue="bitstamp", metric="price_usd",
                                    value=0.90, extra="", retrieved_at=""))
        end = start + timedelta(hours=48)
        injected = inject_outcome("P-PERS", ">12 h", rows, start, end, end)
        fact = evaluate_predicate("P-PERS", injected, start, end)
        self.assertEqual(fact["class"], ">12 h", fact)


def _obs(moment: datetime, venue: str, metric: str, value: float) -> Observation:
    return Observation(timestamp_utc=moment.isoformat(), ts=moment, venue=venue,
                       metric=metric, value=value, extra="", retrieved_at="")


class TestFournitureNonPositive(unittest.TestCase):
    """F-R6 — une valeur nulle crashait (division par zéro) au lieu de H3."""

    def test_zero_dans_la_fourniture_ne_crash_pas(self):
        start = datetime(2023, 3, 9, 0, 0, tzinfo=timezone.utc)
        rows = [
            _obs(start, SUPPLY_VENUE, SUPPLY_METRIC, 4.2e10),
            _obs(start + timedelta(hours=24), SUPPLY_VENUE, SUPPLY_METRIC, 0.0),
            _obs(start + timedelta(hours=48), SUPPLY_VENUE, SUPPLY_METRIC, 4.1e10),
            _obs(start, "bitstamp", "price_usd", 1.0),
            _obs(start, "binance", "price_usd", 1.0),
            _obs(start, "defillama", "price_usd", 1.0),
        ]
        verdicts = classify_hypotheses(rows, start, start + timedelta(hours=48))
        flags = verdicts["H3"]["criteria_evaluated"][0]["computed"]["structural_flags"]
        self.assertTrue(any(f["type"] == "non_positive_value" for f in flags), flags)
        self.assertEqual(verdicts["H3"]["verdict"], "SUPPORTED")


class TestNanFailSafe(unittest.TestCase):
    """F-R7 — NaN dans les calculs d'enveloppe => 0.0, jamais fail-open."""

    def test_available_to_move_nan(self):
        self.assertEqual(available_to_move(float("nan"), 350.0, 100.0), 0.0)
        self.assertEqual(available_to_move(500.0, float("nan"), 100.0), 0.0)
        self.assertEqual(available_to_move(500.0, 350.0, float("nan")), 0.0)
        self.assertEqual(available_to_move(500.0, 350.0, 100.0), 100.0)

    def test_bounded_size_nan(self):
        self.assertEqual(bounded_size(100.0, float("nan"), 100.0), 0.0)
        self.assertEqual(bounded_size(100.0, 50.0, float("inf")), 0.0)
        self.assertEqual(bounded_size(100.0, 50.0, 80.0), 50.0)


class TestIntentIdUtc(unittest.TestCase):
    """F-R8 — le suffixe Z de l'intent_id doit horodater en UTC réel."""

    def test_intent_id_normalise_en_utc(self):
        moment = datetime(2026, 10, 16, 12, 0, tzinfo=timezone(timedelta(hours=2)))
        outcome = authorization_via_policy(50.0, RESERVE, created_at=moment, now=moment)
        self.assertTrue(outcome["evaluated"])
        self.assertEqual(outcome["intent_id"], "decision-20261016T100000Z")


class TestHorsGrille(unittest.TestCase):
    """F-R9 — un montant hors grille de base units doit être refusé (P5)."""

    def test_montant_hors_grille_refuse(self):
        config = cfg(asset_decimals=6)
        decision = evaluate(intent(amount=100.00000000000001), config, now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_INVALID", decision.reasons)

    def test_empreintes_non_collisionnees(self):
        # deux montants distincts ne partagent plus une empreinte de base units
        fp_grid = intent_fingerprint(intent(amount=100.0), decimals=6)
        fp_off = intent_fingerprint(intent(amount=100.00000000000001), decimals=6)
        self.assertNotEqual(fp_grid, fp_off)

    def test_montant_sur_grille_accepte(self):
        decision = evaluate(intent(amount=0.000001), cfg(asset_decimals=6),
                            now=NOW)
        self.assertEqual(decision.verdict, "ALLOW", decision.reasons)


class TestMiniYamlFlow(unittest.TestCase):
    """F-R10 — le flow style imbriqué doit être refusé (docstring du lecteur)."""

    def test_flow_imbrique_refuse(self):
        with self.assertRaises(MiniYamlError):
            yaml_load("chain_ids: [84532]\n")
        with self.assertRaises(MiniYamlError):
            yaml_load("a: {x: 1}\n")

    def test_flow_vide_toujours_accepte(self):
        self.assertEqual(yaml_load("a: []\nb: {}\n"), {"a": [], "b": {}})

    def test_guillemets_preserves(self):
        self.assertEqual(yaml_load('a: "[x]"\n'), {"a": "[x]"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
