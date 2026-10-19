#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — harness comparators: A0, A1, AX0, B0, O (G2).

Normative sources: B7 §e.1 (comparator table, label-collision resolution);
W2-D §C.1; FREEZE_V2 §7 (G3: A0/A1/A2/B0 (+ AX0)).

Frozen labels (B7 §e.1 — the "A0" collision of R3 is settled):

* **A0** — NO-ACTION: the decisive adversary of regret, zero action;
* **A1** — threshold rule: discount ``D ≥ 50 bp`` for 15 min → bounded
  reduction ``x* = min(x_max, Depth_ε, x_seuil)``; ``Depth_ε`` not measured ⇒
  the ``x_max`` cap is used **and the substitution is written**;
* **A2** — the ORVYREN agent (replays the journal, otherwise the archive):
  produced by blocks A–E, not by this module (only the shape of the actions is
  defined here);
* **B0** — paired placebo: same number and sizes of actions as A2, timestamps
  drawn uniformly on the hourly grid of the window, ``M ≥ 200`` draws,
  **fixed seed**; the complete distribution is published;
* **AX0** — the repository frozen rule (0.99 × 2 observations → 100 USDC
  reduction; ``decision/baseline.py``, FREEZE_V1 D6) — delegated, never
  re-implemented (a single source of truth);
* **O** — **feasible** ex post oracle: ``min_{b ∈ F} L(b)``, lower bound of the
  regret, not a ground truth.

Two pre-written sentences (frozen BEFORE execution, B7 §e.1) — if A2 does not
beat B0, the value is not in the **choice of timing**; if A2 does not beat A1,
it is not in the **deliberation**: we write it down.
"""

from __future__ import annotations

import datetime as _dt
import random
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from orvyren.evaluation import loss as loss_mod

# --- frozen constants --------------------------------------------------------

A0_LABEL = "A0"
A1_LABEL = "A1"
A2_LABEL = "A2"
B0_LABEL = "B0"
AX0_LABEL = "AX0"
ORACLE_LABEL = "O"

COMPARATOR_LABELS = (A0_LABEL, A1_LABEL, A2_LABEL, B0_LABEL, AX0_LABEL)

#: A1 — thresholds from W2-B §1.1, to be frozen (G4): discount ≥ 50 bp for 15 min.
A1_MIN_DISCOUNT_BP = 50.0
A1_PERSISTENCE_MINUTES = 15.0
A1_MIN_OBSERVATIONS = 2  # on an hourly grid, "≥ 15 min" = 2 consecutive readings

#: Demo action cap (FREEZE_V2 §5 E2: "Run ALLOW: 100 USDC";
#: taken from evidence/decision_usdc-2023-03.json, exposure_parameters).
X_MAX_USDC_DEMO = 100.0

#: B0 — paired placebo: M ≥ 200 draws, fixed seed (B7 §e.1).
B0_MIN_DRAWS = 200
B0_SEED = 20261016
B0_GRID_HOURS = 1

#: Frozen sentences (to publish as is if the case arises).
PHRASE_IF_A2_BEATS_NOT_B0 = (
    "If A2 does not beat B0, the value of the system is not in the choice of timing — written as is."
)
PHRASE_IF_A2_BEATS_NOT_A1 = (
    "If A2 does not beat A1, the value of the system is not in the deliberation — written as is."
)


class ComparatorError(ValueError):
    """Invalid comparator parameters (never silently corrected)."""


# --- A0 : NO-ACTION ----------------------------------------------------------


def a0_actions(*_args, **_kwargs) -> Tuple[()]:
    """A0 — NO-ACTION over the whole window: zero action, zero cost."""
    return ()


# --- A1: threshold rule ------------------------------------------------------


def a1_signal_times(
    series: Sequence[Tuple[str, float]],
    peg: float = 1.0,
    min_discount_bp: float = A1_MIN_DISCOUNT_BP,
    persistence_minutes: float = A1_PERSISTENCE_MINUTES,
    max_gap_minutes: float = 90.0,
) -> List[str]:
    """Timestamps (ISO UTC) at which the A1 threshold rule fires.

    ``series``: sorted ``(timestamp_utc, price)`` pairs; discount in bp
    ``D = (peg − price)/peg · 10 000``. A firing requires ``D ≥ threshold``
    **sustained** for ``persistence_minutes``: on an hourly grid,
    ``≥ 15 min`` mechanically degenerates into **two consecutive readings**
    (gap ≤ ``max_gap_minutes``), a documented rule, never adjusted afterwards.
    The firing is timestamped at the **second** reading; one persistent
    episode produces a single firing (like AX0).
    """
    fired: List[str] = []
    run_start: Optional[_dt.datetime] = None
    previous: Optional[_dt.datetime] = None
    last_run: List[str] = []
    for stamp, price in series:
        ts = _parse(stamp)
        discount_bp = (peg - price) / peg * 10_000.0
        contiguous = previous is not None and (ts - previous) <= _dt.timedelta(minutes=max_gap_minutes)
        if discount_bp >= min_discount_bp and contiguous:
            run = last_run
            run.append(stamp)
        else:
            if discount_bp >= min_discount_bp:
                run = [stamp]
            else:
                run = []
        if len(run) == A1_MIN_OBSERVATIONS and _span_minutes(run) >= persistence_minutes:
            fired.append(run[-1])
        last_run = run
        previous = ts
    return fired


def _span_minutes(stamps: Sequence[str]) -> float:
    if len(stamps) < 2:
        return 0.0
    return (_parse(stamps[-1]) - _parse(stamps[0])).total_seconds() / 60.0


def _parse(stamp: str) -> _dt.datetime:
    text = stamp.replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def a1_actions(
    series: Sequence[Tuple[str, float]],
    x_max: float = X_MAX_USDC_DEMO,
    depth_epsilon: Optional[float] = None,
    x_seuil: Optional[float] = None,
    **kwargs,
) -> List[dict]:
    """A1 actions: bounded reduction ``x* = min(x_max, Depth_ε, x_seuil)``.

    ``Depth_ε`` (largest size sellable at ≤ ε of impact, W2-D §A.1.6 D4) and
    ``x_seuil`` are **measured or supplied**; while they are missing, the
    ``x_max`` cap applies and the substitution note is attached to the action
    (no invented depth).
    """
    notes: List[str] = []
    caps: List[float] = [x_max]
    if depth_epsilon is None:
        notes.append("Depth_ε not measured — x_max cap used (W2-B §(f) 5 work item)")
    else:
        caps.append(depth_epsilon)
    if x_seuil is None:
        notes.append("x_seuil not frozen — x_max cap used")
    else:
        caps.append(x_seuil)
    size = min(caps)
    actions = []
    for stamp in a1_signal_times(series, **kwargs):
        action = {"type": "reduce_exposure", "amount_usdc": size, "triggered_at_utc": stamp, "rule": "a1_seuil_v1"}
        if notes:
            action["notes"] = list(notes)
        actions.append(action)
    return actions


# --- AX0: repository frozen rule (delegation) --------------------------------


def ax0_signals(corpus_path: str, window: Sequence[str]) -> List[dict]:
    """AX0 — delegates to ``orvyren.decision.baseline.detect_signals``.

    No re-implementation: the frozen rule exists in a single place
    (a divergence between two copies would be a measurement bug).
    """
    from orvyren.decision import baseline

    observations = baseline.load_observations(corpus_path)
    return baseline.detect_signals(observations, window[0], window[1])


def ax0_actions(corpus_path: str, window: Sequence[str]) -> List[dict]:
    """AX0 in the common action shape (one 100 USDC reduction per signal)."""
    from orvyren.decision import baseline

    actions = []
    for signal in ax0_signals(corpus_path, window):
        actions.append(
            {
                "type": "reduce_exposure",
                "amount_usdc": signal["action"]["amount_usdc"],
                "triggered_at_utc": signal["triggered_at_utc"],
                "rule": "ax0_baseline_gelee",
                "evidence_refs": signal["evidence_refs"],
            }
        )
    return actions


# --- B0: paired placebo ------------------------------------------------------


def b0_draws(
    count: int,
    sizes: Sequence[float],
    window_start_utc: str,
    window_end_utc: str,
    grid_hours: int = B0_GRID_HOURS,
    draws: int = B0_MIN_DRAWS,
    seed: int = B0_SEED,
) -> List[List[dict]]:
    """B0 — ``draws`` draws of an action set paired with A2.

    Frozen contract (B7 §e.1): **same number** of actions, **same sizes**,
    timestamps **drawn uniformly** on the hourly grid of the window,
    **M ≥ 200**, fixed seed. The draw is reproducible: two calls with the same
    seed return identical timestamps (tested).
    """
    if draws < B0_MIN_DRAWS:
        raise ComparatorError(f"B0 requires M ≥ {B0_MIN_DRAWS} draws (got {draws}) — frozen rule")
    if count != len(sizes):
        raise ComparatorError(f"invalid pairing: {count} actions for {len(sizes)} sizes")
    start = _parse(window_start_utc)
    end = _parse(window_end_utc)
    if end <= start:
        raise ComparatorError("empty or inverted B0 window")
    grid: List[str] = []
    cursor = start
    while cursor < end:
        grid.append(cursor.strftime("%Y-%m-%dT%H:%M:%SZ"))
        cursor = cursor + _dt.timedelta(hours=grid_hours)
    if not grid:
        raise ComparatorError("empty hourly grid")
    rng = random.Random(seed)
    result: List[List[dict]] = []
    for _ in range(draws):
        draw = []
        for size in sizes:
            stamp = grid[rng.randrange(len(grid))]
            draw.append({"type": "reduce_exposure", "amount_usdc": size, "triggered_at_utc": stamp, "rule": "b0_placebo"})
        draw.sort(key=lambda action: action["triggered_at_utc"])
        result.append(draw)
    return result


def b0_regret_distribution(draws: Sequence[Sequence[dict]], regret_of: Callable[[Sequence[dict]], float]) -> dict:
    """Complete regret distribution of the B0 draws (never a mean alone).

    ``regret_of(actions)`` is the regret computation (frozen loss.py) applied
    to the drawn action set; the harness supplies the closure.
    """
    values = [regret_of(draw) for draw in draws]
    ordered = sorted(values)
    n = len(ordered)
    return {
        "m": n,
        "mean": sum(values) / n if n else None,
        "min": ordered[0] if n else None,
        "max": ordered[-1] if n else None,
        "median": ordered[n // 2] if n else None,
        "quantiles": {
            "p05": ordered[min(n - 1, int(0.05 * n))] if n else None,
            "p50": ordered[min(n - 1, int(0.50 * n))] if n else None,
            "p95": ordered[min(n - 1, int(0.95 * n))] if n else None,
        },
        "values": values,
    }


# --- O: feasible ex post oracle ----------------------------------------------


def oracle_min_loss(losses: Iterable[float]) -> float:
    """O — ``min_{b ∈ F} L(b)`` over the **feasible** family (W2-D §B.1).

    Explicit alias of :func:`orvyren.evaluation.loss.min_feasible_loss`, so
    that the harness names the oracle O unambiguously (it is not an omniscient
    oracle over future prices).
    """
    return loss_mod.min_feasible_loss(losses)
