#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — fonction de perte « richesse + actions faisables » (G1).

Source normative : W2-D §B.1 (formulation corrigée), §B.6 (les six tests),
§E.2/§E.3 (lectures persona) ; B7 §e.1/e.3/e.4 (métriques persona). Le gel G1
fige exactement ces formules — toute modification postérieure à la première
exécution EVAL invalide l'évaluation (embargo de paramètres, B7 §d.2).

Formules gelées (convention terminale) ::

    W_T(conserver)   = C + q · P_T
    W_T(céder x)     = C + x · P_exec(x, t_action) − k + (q − x) · P_T
    L(a)             = W_t0 − W_T(a)                     [USD, ou bp de W_t0]
    R(a)             = L(a) − min_{b ∈ F} L(b)  ≥ 0      [USD ou bp de W_t0]

Deux conventions de valorisation, jamais mélangées (§B.0) :

* ``terminale``   : la position restante vaut ``P_T`` ;
* ``liquidation`` : la position restante vaut le prix qu'on obtiendrait en la
  liquidant à ``T`` (échelle de profondeur). Ce prix doit être **fourni** :
  la fonction refuse de retomber silencieusement sur ``P_T`` (honnêteté — une
  conversion non mesurée ne doit pas se faire passer pour une mesure).

Variantes persona (W2-D §B.3/B.4, B7 §e.3/e.4) :

* **DAO**  : pas de re-entrée dans l'épisode ; perte évitée **conditionnelle à
  l'obligation** ``E[perte] = P(oblig) · (perte | oblig) − (1 − P(oblig)) ·
  coût_aller_retour`` ; seconde lecture en **jours de runway** (``opex_ref``) ;
* **desk** : re-entrée modélisée dans la même fenêtre ; ΔP&L net
  ``x·(P_exec − P_T) − k`` ; agrégats Sharpe/Sortino/MaxDD.

Ce module ne contient que de l'arithmétique déterministe (stdlib pure).
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

# --- conventions et paramètres gelés ----------------------------------------

CONVENTION_TERMINALE = "terminale"
CONVENTION_LIQUIDATION = "liquidation"
CONVENTIONS = (CONVENTION_TERMINALE, CONVENTION_LIQUIDATION)

PERSONA_DAO = "dao"
PERSONA_DESK = "desk"
PERSONAS = (PERSONA_DAO, PERSONA_DESK)

#: Opex de référence (W2-D §A.1.1, §E.1) : ENS IPS 6.46 — 16,4 M$ de charges
#: 2025 ; conversion calculée 16 400 000 / 365 (le document affiche
#: « ≈ 44 932 $/jour »). Paramètre G6 ``opex_ref`` — valeur de référence
#: externe déclarée telle quelle, à re-signer pour ORVYREN (B7 Q13).
OPEX_REF_ANNUAL_USD = 16_400_000.0
OPEX_REF_USD_PER_DAY = round(OPEX_REF_ANNUAL_USD / 365.0)  # 44932 (arrondi)

#: Famille d'actions faisables par défaut (fractions de q), inclut x = 0
#: (« ne rien faire » appartient toujours à F, W2-D §B.0).
FEASIBLE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


class ValuationError(ValueError):
    """Argument de valorisation manquant ou incohérent (jamais comblé)."""


# --- richesse terminale ------------------------------------------------------


def wealth_keep(numeraire: float, quantity: float, p_terminal: float) -> float:
    """``W_T(conserver) = C + q · P_T`` (W2-D §B.1)."""
    return numeraire + quantity * p_terminal


def wealth_sell(
    numeraire: float,
    quantity: float,
    sold: float,
    p_exec: float,
    p_terminal: float,
    cost: float = 0.0,
    convention: str = CONVENTION_TERMINALE,
    liquidation_price: Optional[Callable[[float], float]] = None,
) -> float:
    """``W_T(céder x)`` — persona DAO (pas de re-entrée).

    ``p_exec`` est le prix d'exécution **moyen** obtenu pour la taille ``sold``
    (échelle de profondeur mesurée, jamais un prix d'écran) ; ``cost`` = ``k``
    (frais, gas, pontage, financement non déjà inclus dans ``p_exec``).

    En convention ``liquidation``, ``liquidation_price`` est une fonction
    ``quantité_restante → prix de liquidation`` : sans elle, la fonction
    **refuse** de calculer (``ValuationError``) au lieu de supposer ``P_T``.
    """
    if convention not in CONVENTIONS:
        raise ValuationError(f"convention inconnue : {convention!r} (attendu {CONVENTIONS})")
    if sold < 0.0 or sold > quantity:
        raise ValuationError(f"quantité cédée hors [0, q] : sold={sold!r}, q={quantity!r}")
    remaining = quantity - sold
    if convention == CONVENTION_LIQUIDATION:
        if liquidation_price is None:
            raise ValuationError(
                "convention 'liquidation' exige liquidation_price(q_restant) — "
                "mesurer l'échelle de profondeur, ne pas supposer P_T (W2-D §B.0)"
            )
        residual = liquidation_price(remaining)
    else:
        residual = p_terminal
    return numeraire + sold * p_exec - cost + remaining * residual


def wealth_sell_reenter(
    numeraire: float,
    quantity: float,
    sold: float,
    p_exec: float,
    p_terminal: float,
    cost: float = 0.0,
) -> float:
    """Persona desk : coupe ``sold`` à ``p_exec`` puis re-entre à ``P_T``.

    La re-entrée fait partie de l'action (W2-D §B.4 point 2) ; le résultat se
    simplifie en ``C + q·P_T + x·(P_exec − P_T) − k``, c'est-à-dire la formule
    ΔP&L de W2-D §E.3.
    """
    if sold < 0.0 or sold > quantity:
        raise ValuationError(f"quantité cédée hors [0, q] : sold={sold!r}, q={quantity!r}")
    return numeraire + quantity * p_terminal + sold * (p_exec - p_terminal) - cost


def loss(wealth_t0: float, wealth_terminal: float) -> float:
    """``L(a) = W_t0 − W_T(a)`` (USD ; positif = richesse perdue)."""
    return wealth_t0 - wealth_terminal


def loss_bp(loss_usd: float, wealth_t0: float) -> float:
    """``L`` en points de base de ``W_t0`` (cohérence d'échelle, W2-D §B.1)."""
    if wealth_t0 == 0.0:
        raise ValuationError("W_t0 = 0 : la conversion en bp est indéfinie")
    return loss_usd / wealth_t0 * 10_000.0


# --- regret ------------------------------------------------------------------


def regret(loss_value: float, min_feasible_loss: float) -> float:
    """``R(a) = L(a) − min_{b ∈ F} L(b) ≥ 0`` (W2-D §B.1)."""
    return loss_value - min_feasible_loss


def feasible_actions(
    quantity: float,
    fractions: Sequence[float] = FEASIBLE_FRACTIONS,
    x_max: Optional[float] = None,
) -> Tuple[float, ...]:
    """Famille d'actions faisables ``F`` : quantités cédées, ``x = 0`` inclus.

    ``x_max`` est le plafond de politique (E2 : 100 USDC dans la démo) ; les
    fractions qui le dépassent sont plafonnées, jamais extrapolées.
    """
    if quantity < 0.0:
        raise ValuationError(f"quantité négative : {quantity!r}")
    out: List[float] = []
    for frac in fractions:
        if frac < 0.0 or frac > 1.0:
            raise ValuationError(f"fraction hors [0, 1] : {frac!r}")
        x = quantity * frac
        if x_max is not None:
            x = min(x, x_max)
        if x not in out:
            out.append(x)
    return tuple(out)


def min_feasible_loss(losses: Iterable[float]) -> float:
    """``min_{b ∈ F} L(b)`` — oracle **faisable** (borne inférieure du regret)."""
    values = list(losses)
    if not values:
        raise ValuationError("famille d'actions vide : pas d'oracle faisable")
    return min(values)


def regret_negative(loss_action: float, loss_no_action: float) -> float:
    """``R⁻`` : coût du faux positif (l'agent agit alors que ne rien faire était
    meilleur) — publié séparément de ``R⁺``, jamais moyenné (W2-D §B.1/B.5 #8).
    """
    return max(0.0, loss_action - loss_no_action)


def regret_positive(loss_action: float, loss_no_action: float) -> float:
    """``R⁺`` : coût du faux négatif (ne pas agir alors qu'agir était meilleur)."""
    return max(0.0, loss_no_action - loss_action)


# --- évaluation d'une action sous les deux personas --------------------------


def evaluate_action(
    numeraire: float,
    quantity: float,
    sold: float,
    p_t0: float,
    p_terminal: float,
    p_exec: Optional[float] = None,
    cost: float = 0.0,
    persona: str = PERSONA_DAO,
    convention: str = CONVENTION_TERMINALE,
    liquidation_price: Optional[Callable[[float], float]] = None,
) -> dict:
    """Richesse terminale et perte d'une action, sous une persona donnée.

    * ``sold == 0`` → branche « conserver » (les deux personas ne diffèrent pas) ;
    * persona ``desk`` → re-entrée à ``P_T`` (pas de ``liquidation_price``) ;
    * persona ``dao``  → pas de re-entrée ; convention ``liquidation`` honorée.

    Renvoie ``{persona, sold, wealth_t0, wealth_terminal, loss_usd, loss_bp}``.
    """
    if persona not in PERSONAS:
        raise ValuationError(f"persona inconnue : {persona!r} (attendu {PERSONAS})")
    wealth_t0 = wealth_keep(numeraire, quantity, p_t0)
    if sold == 0.0:
        w_t = wealth_keep(numeraire, quantity, p_terminal)
    elif persona == PERSONA_DESK:
        if p_exec is None:
            raise ValuationError("persona desk : p_exec est requis dès que sold > 0")
        w_t = wealth_sell_reenter(numeraire, quantity, sold, p_exec, p_terminal, cost)
    else:
        if p_exec is None:
            raise ValuationError("persona dao : p_exec est requis dès que sold > 0")
        w_t = wealth_sell(
            numeraire,
            quantity,
            sold,
            p_exec,
            p_terminal,
            cost,
            convention=convention,
            liquidation_price=liquidation_price,
        )
    l = loss(wealth_t0, w_t)
    return {
        "persona": persona,
        "sold": sold,
        "wealth_t0": wealth_t0,
        "wealth_terminal": w_t,
        "loss_usd": l,
        "loss_bp": loss_bp(l, wealth_t0) if wealth_t0 != 0.0 else None,
    }


def regret_table(
    numeraire: float,
    quantity: float,
    p_t0: float,
    p_terminal: float,
    p_exec_by_size: Callable[[float], float],
    cost: float = 0.0,
    persona: str = PERSONA_DAO,
    fractions: Sequence[float] = FEASIBLE_FRACTIONS,
    x_max: Optional[float] = None,
) -> dict:
    """Table ``action → perte → regret`` sur la famille faisable ``F``.

    ``p_exec_by_size(x)`` rend le prix d'exécution **moyen** pour la taille
    ``x`` (échelle de profondeur) ; l'oracle faisable est le minimum des pertes
    de ``F`` — même fonction de perte, même famille (W2-D §B.1).
    """
    rows = []
    for x in feasible_actions(quantity, fractions=fractions, x_max=x_max):
        p_exec = None if x == 0.0 else p_exec_by_size(x)
        row = evaluate_action(
            numeraire,
            quantity,
            x,
            p_t0,
            p_terminal,
            p_exec=p_exec,
            cost=cost,
            persona=persona,
        )
        rows.append(row)
    floor = min_feasible_loss(row["loss_usd"] for row in rows)
    for row in rows:
        row["regret_usd"] = regret(row["loss_usd"], floor)
        row["regret_bp"] = None if row["wealth_t0"] == 0.0 else loss_bp(row["regret_usd"], row["wealth_t0"])
    return {
        "persona": persona,
        "quantity": quantity,
        "min_feasible_loss_usd": floor,
        "actions": rows,
    }


# --- persona DAO : perte évitée conditionnelle, jours de runway --------------


def dao_expected_avoided_loss(
    p_obligation: float,
    avoided_loss_given_obligation: float,
    roundtrip_cost: float,
) -> dict:
    """Perte évitée **attendue** (DAO) — les deux facteurs publiés.

    ``E[perte évitée] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR``
    (W2-D §B.3, §E.2(b)). ``p_obligation`` est une **hypothèse signée** (G6),
    jamais une estimation calibrée : la fonction exige qu'elle soit dans
    [0, 1] et renvoie les deux termes séparément — une perte évitée
    « inconditionnelle » n'est pas une perte évitée (règle du gel).
    """
    if not 0.0 <= p_obligation <= 1.0:
        raise ValuationError(f"P(obligation) hors [0, 1] : {p_obligation!r}")
    conditional_term = p_obligation * avoided_loss_given_obligation
    premium_term = (1.0 - p_obligation) * roundtrip_cost
    return {
        "p_obligation": p_obligation,
        "avoided_loss_given_obligation_usd": avoided_loss_given_obligation,
        "roundtrip_cost_usd": roundtrip_cost,
        "conditional_term_usd": conditional_term,
        "premium_term_usd": premium_term,
        "expected_avoided_loss_usd": conditional_term - premium_term,
    }


def runway_days(amount_usd: float, opex_per_day: float = OPEX_REF_USD_PER_DAY) -> float:
    """``jours de runway = USD / opex_jour`` (W2-D §B.3, §E.1 : 44 932 $/j)."""
    if opex_per_day <= 0.0:
        raise ValuationError("opex_per_day doit être strictement positif")
    return amount_usd / opex_per_day


# --- persona desk : ΔP&L, Sharpe, Sortino, MaxDD -----------------------------


def delta_pnl_net(
    quantity: float,
    sold: float,
    p_exec: float,
    p_terminal: float,
    p_ref: float,
    cost: float = 0.0,
    funding: float = 0.0,
) -> float:
    """``ΔP&L_net(a) = [x·P_exec + (q−x)·P_T − q·P_ref] − k − financement``.

    Formule W2-D §B.4 (avec ``P_exec`` au prix réalisable et
    ``financement = I_moy · r_capital · Δt`` fourni explicitement par G6).

    ``P_ref`` est le repère de valorisation publié ; pour lire le P&L **contre
    l'inaction sur la fenêtre**, on prend ``P_ref = P_T`` : la formule devient
    alors exactement la forme W2-D §E.3 ``x·(P_exec − P_T) − k``. Les deux
    lectures se publient séparément, jamais moyennées (l'une mesure l'inventaire
    vendu, l'autre l'aller-retour complet).
    """
    return (sold * p_exec + (quantity - sold) * p_terminal - quantity * p_ref) - cost - funding


def pnl_bp(delta_pnl_usd: float, quantity: float, p_ref: float) -> float:
    """``ΔP&L`` en bp de ``q · P_ref`` (W2-D §B.4)."""
    base = quantity * p_ref
    if base == 0.0:
        raise ValuationError("q · P_ref = 0 : conversion en bp indéfinie")
    return delta_pnl_usd / base * 10_000.0


def sharpe_ratio(returns: Sequence[float], risk_free: float = 0.0) -> Optional[float]:
    """``(moyenne(r) − R_f) / σ(r)`` — ``R_f = 0`` par convention crypto.

    Renvoie ``None`` quand σ = 0 (le ratio n'existe pas ; il n'est pas
    remplacé par un chiffre arbitraire).
    """
    xs = list(returns)
    if len(xs) < 2:
        return None
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)
    sigma = math.sqrt(var)
    if sigma == 0.0:
        return None
    return (mean - risk_free) / sigma


def sortino_ratio(returns: Sequence[float], risk_free: float = 0.0) -> Optional[float]:
    """``(moyenne − R_f) / σ_d``, ``σ_d`` = écart-type des seuls rendements
    négatifs (ou ``None`` si aucun rendement négatif — non calculable)."""
    xs = list(returns)
    downs = [x for x in xs if x < 0.0]
    if len(downs) < 2:
        return None
    mean = sum(xs) / len(xs)
    mean_d = sum(downs) / len(downs)
    var_d = sum((x - mean_d) ** 2 for x in downs) / (len(downs) - 1)
    sigma_d = math.sqrt(var_d)
    if sigma_d == 0.0:
        return None
    return (mean - risk_free) / sigma_d


def max_drawdown(equity: Sequence[float]) -> Optional[float]:
    """``MaxDD = min_t ( Equity_t / max_{u≤t} Equity_u − 1 )`` (W2-D §A.2.2)."""
    xs = list(equity)
    if not xs:
        return None
    peak = xs[0]
    worst = 0.0
    for value in xs:
        if value > peak:
            peak = value
        if peak > 0.0:
            drawdown = value / peak - 1.0
            worst = min(worst, drawdown)
    return worst
