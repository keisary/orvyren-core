#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — bounded action catalogues: 8 DAO + 4 desk (W3 lot L3.5).

Spec: B3_DECISION_ETUDE.md §d.2-d.4 (DOC2 §5.4.5). An action is never a free
order — it is a **bounded intent** (asset, amount, destination, function,
expiration) that the policy may refuse. Every action carries its template:
epistemic trigger, economic trigger, bounds, cost, expected effect and
on-chain applicability ("exécutable on-chain" or "simulée" — demonstration
honesty). The catalogue is versioned and executions cite the version
(INV-AUTH). No action opens new exposure during a stress episode (reduce /
convert / repay / withdraw only — the bound the policy service can verify).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

CATALOG_VERSION = "catalog/v1"

DAO_PERSONA = "DAO"
DESK_PERSONA = "desk"

APPLICABILITY_ON_CHAIN = "on-chain"
APPLICABILITY_SIMULATED = "simulated"
APPLICABILITY_ESCALATE = "escalate (pas une action de l'agent)"
APPLICABILITY_DEFAULT = "default (état par défaut)"


@dataclass(frozen=True)
class ActionRecord:
    """One bounded action of a persona catalogue (B3 §d.2/d.3 template)."""

    action_id: str
    persona: str
    name: str
    epistemic_trigger: str
    economic_trigger: str
    bounds: str
    cost: str
    expected_effect: str
    applicability: str
    precedent: str
    version: str = CATALOG_VERSION


# B3 §d.2 — catalogue trésorerie / protocole (DAO), 8 actions.
DAO_ACTIONS: Tuple[ActionRecord, ...] = (
    ActionRecord(
        "A-D1", DAO_PERSONA, "Pré-positionner / convertir",
        "H2 SUPPORTED (stress large) ou H1 SUPPORTED sans certitude de "
        "confinement, A1-A3 levées",
        "E[perte évitée] = P(obligation)·(L(A0)-L(a)) > coût ; sinon NO-ACTION",
        "x <= x_max ; venue au allowlist ; <= profondeur Depth_eps",
        "frais + slippage mesurés (get_dy) + gas",
        "réduit l'exposition conditionnelle ; paie une prime sinon "
        "(aller-retour ~ -4,0 % mesuré, W2-D §E.2b)",
        APPLICABILITY_ON_CHAIN,
        "Maker 11-13/03/2023 (PSM) ; Eco (>= 2 émetteurs) ; ENS IPS",
    ),
    ActionRecord(
        "A-D2", DAO_PERSONA, "Sortir d'un LST",
        "décote réalisable > seuil (>= 100/300/600 bps) ET non transitoire "
        "(persistance > 12 h)",
        "idem A-D1 ; justifiée si la décote peut se creuser ou redemption "
        "suspendable",
        "<= profondeur ; avant files de redemption",
        "slippage ladder mesuré (10 000 stETH -> 7,13 bp en calme ; 755 bp "
        "le 14/06/2022)",
        "évite la matérialisation d'une décote croissante",
        APPLICABILITY_ON_CHAIN,
        "stETH mai-juin 2022 (antériorité 30 j, W3-A §3)",
    ),
    ActionRecord(
        "A-D3", DAO_PERSONA, "Rembourser une dette / dé-leverer",
        "hausse de la probabilité de gel/liquidation de la venue de dette "
        "(isFrozen, LTV->0, utilisation ~ 100 %)",
        "coût du remboursement < perte attendue sous gel (blocked exit)",
        "x <= disponible + dette ; désendetter d'abord si collatéral verrouillé",
        "frais + gas",
        "réduit la surface de liquidation ; libère du collatéral si LTV imposé",
        APPLICABILITY_ON_CHAIN,
        "rsETH 18-20/04/2026 : WETH gelé, LTV -> 0 (MESURÉ)",
    ),
    ActionRecord(
        "A-D4", DAO_PERSONA, "Retirer la liquidité / ne pas en ajouter",
        "signal de gel ou saturation (cap_ratio >= 95 %, isFrozen, "
        "utilisation-cash >= 99 %, files de redemption)",
        "coût du retrait (gas) < valeur d'option de la sortie ; si la sortie "
        "est déjà fermée -> ESCALATE",
        "<= cash disponible ; priorité aux paniers les plus fermés",
        "gas + éventuels coûts de sortie",
        "convertit « valeur retenue » en « valeur disponible » (redeemability)",
        APPLICABILITY_ON_CHAIN,
        "KPK/ENS sort des positions Aave le 18/04/2026, reconstruit sans perte",
    ),
    ActionRecord(
        "A-D5", DAO_PERSONA, "Rapatrier vers le module de roulage",
        "buffer opérationnel sous cible, ou runway projeté proche du plancher",
        "arbitrage liquidité vs coût d'opportunité déclaré",
        "<= cible du module ; tranches standardisées (ex. 1 500/3 000 ETH)",
        "gas + coût d'opportunité",
        "maintient la contrainte dure (runway) ; sert la reddition de comptes",
        APPLICABILITY_ON_CHAIN,
        "ENS Registrar Manager + module Zodiac (~6 mois USDC)",
    ),
    ActionRecord(
        "A-D6", DAO_PERSONA, "Geler / réduire des dépenses",
        "stress prolongé, perte de valeur USD, décision de gouvernance",
        "n/a (décision politique)",
        "relève de la gouvernance — pas une action de l'agent",
        "—",
        "protège la trésorerie ; cadence longue",
        APPLICABILITY_ESCALATE,
        "Lido : utilisation EGG 22 % puis coupes ; Aave : buyback 50->30 M$",
    ),
    ActionRecord(
        "A-D7", DAO_PERSONA, "Ne rien faire (documenté)",
        "verdict conclusif sans action passant le seuil ; ou H1 SUPPORTED + "
        "H2 REFUTED (perturbation locale)",
        "coût d'une action >= gain conditionnel (friction SD2 <= 10 %)",
        "x = 0",
        "0 (coût d'opportunité si l'alerte se répète)",
        "évite la prime systématique ; conserve le risque (écrit)",
        APPLICABILITY_DEFAULT,
        "W2-D §B.4.1 ; moteur v0 règle 2",
    ),
    ActionRecord(
        "A-D8", DAO_PERSONA, "Escalader (comité / trésorier / gouvernance)",
        "A3/A4/A5 ou intégrité en échec (B3 §c.4)",
        "—",
        "—",
        "latence humaine",
        "décision tracée et responsable ; pas de blocage silencieux",
        APPLICABILITY_ESCALATE,
        "W2-C (flux REQUIRE_APPROVAL) ; Chaos Labs",
    ),
)

# B3 §d.3 — catalogue desk (rentabilité), 4 actions.
DESK_ACTIONS: Tuple[ActionRecord, ...] = (
    ActionRecord(
        "K-D1", DESK_PERSONA, "Réduire / sortir une position d'inventaire",
        "signal de rupture (D >= 200 bps, dispersion >= 300 bps)",
        "x·(P_T - P_exec) > k_aller-retour + financement ; coûte si le peg se "
        "rétablit (put payé : -4,2 % sur l'exemple USDC)",
        "x <= min(x_max, Depth_eps) ; plan de retour inclus ou déclaré",
        "frais + slippage + financement",
        "réduit la perte de queue",
        APPLICABILITY_ON_CHAIN,
        "W2-D §E.3 ; DeFi Saver (stop-loss automation 0,25-0,30 %)",
    ),
    ActionRecord(
        "K-D2", DESK_PERSONA, "Hedger (short perp / option de depeg)",
        "exposition résiduelle à un actif dont la décote est possible",
        "coût du hedge < perte conditionnelle",
        "notionnel <= exposition ; marge pré-financée ; venue au allowlist",
        "funding + prime d'option",
        "neutralise la queue sans vendre le spot",
        APPLICABILITY_SIMULATED,
        "depegwatch 19/09/2025 ; Ethena (delta-neutral)",
    ),
    ActionRecord(
        "K-D3", DESK_PERSONA, "Dimensionner (sizing)",
        "toujours, avant toute action",
        "publication du slippage réalisé vs budget (ST2 <= 30 bp)",
        "x = min(x_max, Depth_eps, x*)",
        "—",
        "évite d'exécuter une « perte évitée » plus petite que le coût",
        APPLICABILITY_ON_CHAIN,
        "W2-D §A.2.5/T4",
    ),
    ActionRecord(
        "K-D4", DESK_PERSONA, "Ne rien faire / attendre",
        "le seuil n'est pas franchi ; incertitude symétrique et coût "
        "d'aller-retour prohibitif",
        "le coût décide du signe (churn)",
        "x = 0",
        "0",
        "évite le churn (Miller/DSR — Bailey & López de Prado 2014)",
        APPLICABILITY_DEFAULT,
        "W2-D §B.4",
    ),
)

CATALOG: Tuple[ActionRecord, ...] = DAO_ACTIONS + DESK_ACTIONS


def catalog_for(persona: str) -> Tuple[ActionRecord, ...]:
    if persona == DAO_PERSONA:
        return DAO_ACTIONS
    if persona == DESK_PERSONA:
        return DESK_ACTIONS
    raise ValueError("E_PERSONA_UNKNOWN: %r" % persona)


def bounded_size(x_max: float, depth_eps: float, x_threshold: float) -> float:
    """x* = min(x_max_rôle, profondeur d'exécution mesurée, taille au seuil
    économique) — B3 §d.1. Never negative."""
    return max(0.0, min(x_max, depth_eps, x_threshold))


def validate_catalog(catalog: Sequence[ActionRecord] = CATALOG) -> List[str]:
    """Template completeness (used by the test bench): every field present."""
    problems = []
    required = ("action_id", "persona", "name", "epistemic_trigger",
                "economic_trigger", "bounds", "cost", "expected_effect",
                "applicability", "precedent")
    for action in catalog:
        for field_name in required:
            if not str(getattr(action, field_name)).strip():
                problems.append("%s: empty %s" % (action.action_id, field_name))
        if action.version != CATALOG_VERSION:
            problems.append("%s: version mismatch %s" % (action.action_id, action.version))
    return problems


def records_as_dicts(catalog: Sequence[ActionRecord] = CATALOG) -> List[Dict]:
    return [
        {"action_id": a.action_id, "persona": a.persona, "name": a.name,
         "epistemic_trigger": a.epistemic_trigger,
         "economic_trigger": a.economic_trigger, "bounds": a.bounds,
         "cost": a.cost, "expected_effect": a.expected_effect,
         "applicability": a.applicability, "precedent": a.precedent,
         "version": a.version}
        for a in catalog
    ]