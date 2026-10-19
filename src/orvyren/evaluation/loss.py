#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — "wealth + feasible actions" loss function (G1).

Normative source: W2-D §B.1 (corrected formulation), §B.6 (the six tests),
§E.2/§E.3 (persona readings); B7 §e.1/e.3/e.4 (persona metrics). Freeze G1
pins exactly these formulas — any modification after the first EVAL run
invalidates the evaluation (parameter embargo, B7 §d.2).

Frozen formulas (terminal convention)::

    W_T(keep)        = C + q · P_T
    W_T(sell x)      = C + x · P_exec(x, t_action) − k + (q − x) · P_T
    L(a)             = W_t0 − W_T(a)                      [USD, or bp of W_t0]
    R(a)             = L(a) − min_{b ∈ F} L(b)  ≥ 0       [USD or bp of W_t0]

Two valuation conventions, never mixed (§B.0):

* ``terminal``   : the remaining position is worth ``P_T``;
* ``liquidation``: the remaining position is worth the price it would fetch
  when liquidated at ``T`` (depth curve). That price must be **supplied**:
  the function refuses to fall back silently on ``P_T`` (honesty — an
  unmeasured conversion must not pass for a measurement).

Persona variants (W2-D §B.3/B.4, B7 §e.3/e.4):

* **DAO**  : no re-entry during the episode; avoided loss **conditional on
  the obligation** ``E[loss] = P(oblig) · (loss | oblig) − (1 − P(oblig)) ·
  roundtrip_cost``; second reading in **runway days** (``opex_ref``);
* **desk** : re-entry modelled inside the same window; net ΔP&L
  ``x·(P_exec − P_T) − k``; Sharpe/Sortino/MaxDD aggregates.

This module contains deterministic arithmetic only (pure stdlib).
"""

from __future__ import annotations

import math
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

# --- frozen conventions and parameters ---------------------------------------

CONVENTION_TERMINALE = "terminale"
CONVENTION_LIQUIDATION = "liquidation"
CONVENTIONS = (CONVENTION_TERMINALE, CONVENTION_LIQUIDATION)

PERSONA_DAO = "dao"
PERSONA_DESK = "desk"
PERSONAS = (PERSONA_DAO, PERSONA_DESK)

#: Reference opex (W2-D §A.1.1, §E.1): ENS IPS 6.46 — 16.4 M$ of expenses in
#: 2025; computed conversion 16 400 000 / 365 (the document prints
#: "≈ 44 932 $/day"). G6 parameter ``opex_ref`` — external reference value
#: declared as is, to be re-signed for ORVYREN (B7 Q13).
OPEX_REF_ANNUAL_USD = 16_400_000.0
OPEX_REF_USD_PER_DAY = round(OPEX_REF_ANNUAL_USD / 365.0)  # 44932 (rounded)

#: Default feasible-action family (fractions of q), includes x = 0
#: ("do nothing" always belongs to F, W2-D §B.0).
FEASIBLE_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


class ValuationError(ValueError):
    """Missing or inconsistent valuation argument (never filled in)."""


# --- terminal wealth ---------------------------------------------------------


def wealth_keep(numeraire: float, quantity: float, p_terminal: float) -> float:
    """``W_T(keep) = C + q · P_T`` (W2-D §B.1)."""
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
    """``W_T(sell x)`` — DAO persona (no re-entry).

    ``p_exec`` is the **average** execution price obtained for the ``sold``
    size (measured depth curve, never a screen price); ``cost`` = ``k``
    (fees, gas, bridging, funding not already included in ``p_exec``).

    Under the ``liquidation`` convention, ``liquidation_price`` is a function
    ``remaining_quantity → liquidation price``: without it, the function
    **refuses** to compute (``ValuationError``) instead of assuming ``P_T``.
    """
    if convention not in CONVENTIONS:
        raise ValuationError(f"unknown convention: {convention!r} (expected {CONVENTIONS})")
    if sold < 0.0 or sold > quantity:
        raise ValuationError(f"sold quantity outside [0, q]: sold={sold!r}, q={quantity!r}")
    remaining = quantity - sold
    if convention == CONVENTION_LIQUIDATION:
        if liquidation_price is None:
            raise ValuationError(
                "convention 'liquidation' requires liquidation_price(remaining_q) — "
                "measure the depth curve, do not assume P_T (W2-D §B.0)"
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
    """Desk persona: cut ``sold`` at ``p_exec`` then re-enter at ``P_T``.

    The re-entry is part of the action (W2-D §B.4 point 2); the result
    simplifies to ``C + q·P_T + x·(P_exec − P_T) − k``, i.e. the ΔP&L
    formula of W2-D §E.3.
    """
    if sold < 0.0 or sold > quantity:
        raise ValuationError(f"sold quantity outside [0, q]: sold={sold!r}, q={quantity!r}")
    return numeraire + quantity * p_terminal + sold * (p_exec - p_terminal) - cost


def loss(wealth_t0: float, wealth_terminal: float) -> float:
    """``L(a) = W_t0 − W_T(a)`` (USD; positive = wealth lost)."""
    return wealth_t0 - wealth_terminal


def loss_bp(loss_usd: float, wealth_t0: float) -> float:
    """``L`` in basis points of ``W_t0`` (scale consistency, W2-D §B.1)."""
    if wealth_t0 == 0.0:
        raise ValuationError("W_t0 = 0: bp conversion is undefined")
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
    """Feasible-action family ``F``: sold quantities, ``x = 0`` included.

    ``x_max`` is the policy cap (E2: 100 USDC in the demo); fractions that
    exceed it are capped, never extrapolated.
    """
    if quantity < 0.0:
        raise ValuationError(f"negative quantity: {quantity!r}")
    out: List[float] = []
    for frac in fractions:
        if frac < 0.0 or frac > 1.0:
            raise ValuationError(f"fraction outside [0, 1]: {frac!r}")
        x = quantity * frac
        if x_max is not None:
            x = min(x, x_max)
        if x not in out:
            out.append(x)
    return tuple(out)


def min_feasible_loss(losses: Iterable[float]) -> float:
    """``min_{b ∈ F} L(b)`` — **feasible** oracle (lower bound of the regret)."""
    values = list(losses)
    if not values:
        raise ValuationError("empty action family: no feasible oracle")
    return min(values)


def regret_negative(loss_action: float, loss_no_action: float) -> float:
    """``R⁻``: cost of the false positive (the agent acts while doing nothing
    was better) — published separately from ``R⁺``, never averaged (W2-D §B.1/B.5 #8).
    """
    return max(0.0, loss_action - loss_no_action)


def regret_positive(loss_action: float, loss_no_action: float) -> float:
    """``R⁺``: cost of the false negative (not acting while acting was better)."""
    return max(0.0, loss_no_action - loss_action)


# --- evaluation of one action under both personas ----------------------------


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
    """Terminal wealth and loss of one action, under a given persona.

    * ``sold == 0`` → "keep" branch (the two personas do not differ);
    * persona ``desk`` → re-entry at ``P_T`` (no ``liquidation_price``);
    * persona ``dao``  → no re-entry; ``liquidation`` convention honoured.

    Returns ``{persona, sold, wealth_t0, wealth_terminal, loss_usd, loss_bp}``.
    """
    if persona not in PERSONAS:
        raise ValuationError(f"unknown persona: {persona!r} (expected {PERSONAS})")
    wealth_t0 = wealth_keep(numeraire, quantity, p_t0)
    if sold == 0.0:
        w_t = wealth_keep(numeraire, quantity, p_terminal)
    elif persona == PERSONA_DESK:
        if p_exec is None:
            raise ValuationError("desk persona: p_exec is required as soon as sold > 0")
        w_t = wealth_sell_reenter(numeraire, quantity, sold, p_exec, p_terminal, cost)
    else:
        if p_exec is None:
            raise ValuationError("dao persona: p_exec is required as soon as sold > 0")
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
    """Table ``action → loss → regret`` over the feasible family ``F``.

    ``p_exec_by_size(x)`` returns the **average** execution price for size
    ``x`` (depth curve); the feasible oracle is the minimum of the losses over
    ``F`` — same loss function, same family (W2-D §B.1).
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


# --- DAO persona: conditional avoided loss, runway days ---------------------


def dao_expected_avoided_loss(
    p_obligation: float,
    avoided_loss_given_obligation: float,
    roundtrip_cost: float,
) -> dict:
    """**Expected** avoided loss (DAO) — both factors published.

    ``E[avoided loss] = P(oblig) · (loss | oblig) − (1 − P(oblig)) · roundtrip_cost``
    (W2-D §B.3, §E.2(b)). ``p_obligation`` is a **signed hypothesis** (G6),
    never a calibrated estimate: the function requires it to be in
    [0, 1] and returns the two terms separately — an "unconditional"
    avoided loss is not an avoided loss (freeze rule).
    """
    if not 0.0 <= p_obligation <= 1.0:
        raise ValuationError(f"P(obligation) outside [0, 1]: {p_obligation!r}")
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
    """``runway days = USD / opex_per_day`` (W2-D §B.3, §E.1: 44 932 $/day)."""
    if opex_per_day <= 0.0:
        raise ValuationError("opex_per_day must be strictly positive")
    return amount_usd / opex_per_day


# --- desk persona: ΔP&L, Sharpe, Sortino, MaxDD ------------------------------


def delta_pnl_net(
    quantity: float,
    sold: float,
    p_exec: float,
    p_terminal: float,
    p_ref: float,
    cost: float = 0.0,
    funding: float = 0.0,
) -> float:
    """``ΔP&L_net(a) = [x·P_exec + (q−x)·P_T − q·P_ref] − k − funding``.

    W2-D §B.4 formula (with ``P_exec`` at the achievable price and
    ``funding = I_avg · r_capital · Δt`` supplied explicitly by G6).

    ``P_ref`` is the published valuation benchmark; to read the P&L **against
    inaction over the window**, take ``P_ref = P_T``: the formula then becomes
    exactly the W2-D §E.3 form ``x·(P_exec − P_T) − k``. The two readings are
    published separately, never averaged (one measures the inventory sold, the
    other the complete round trip).
    """
    return (sold * p_exec + (quantity - sold) * p_terminal - quantity * p_ref) - cost - funding


def pnl_bp(delta_pnl_usd: float, quantity: float, p_ref: float) -> float:
    """``ΔP&L`` in bp of ``q · P_ref`` (W2-D §B.4)."""
    base = quantity * p_ref
    if base == 0.0:
        raise ValuationError("q · P_ref = 0: bp conversion undefined")
    return delta_pnl_usd / base * 10_000.0


def sharpe_ratio(returns: Sequence[float], risk_free: float = 0.0) -> Optional[float]:
    """``(mean(r) − R_f) / σ(r)`` — ``R_f = 0`` by crypto convention.

    Returns ``None`` when σ = 0 (the ratio does not exist; it is not
    replaced by an arbitrary number).
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
    """``(mean − R_f) / σ_d``, ``σ_d`` = standard deviation of the negative
    returns only (or ``None`` if there is no negative return — not computable)."""
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
