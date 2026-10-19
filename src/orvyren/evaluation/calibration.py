#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — forecast calibration: C1–C7 (G5), pure stdlib.

Normative sources: B7 §b.1 (formulas and references), §b.2 (verified KAT
vector), §b.3 (cascade "when can we say calibrated"), DOC2 §5.8.2.

Metrics:

======== ==========================================================
**C1**   Brier score ``BS = (1/N) Σ (p_t − y_t)²`` (Brier 1950)
**C2**   Murphy decomposition ``BS = REL − RES + UNC``, over the
         **same bins** as the ECE (exact identity, testable)
**C3**   ECE over **10 fixed bins** ``[b/10, (b+1)/10)`` frozen in advance
**C4**   reliability curve per bin (``n_b``, ``conf_b``,
         ``acc_b``, Wilson CI per bin)
**C5**   Wilson bounds (z = 1.959964, Wilson 1927)
**C6**   circular block bootstrap, 10 000 replications, fixed seed
**C7**   skill ``BSS = 1 − BS / (ȳ(1−ȳ))``
======== ==========================================================

KAT vector (B7 §b.2, tolerance 1e-12): ``p = [0.2 ×5 ; 0.8 ×5]``,
``y = [0,0,0,0,0, 1,1,0,1,1]`` → ``BS = REL − RES + UNC = 0.02 − 0.16 + 0.24
= 0.10``, ``ECE = 0.10``, ``ȳ = 0.40``.

Guards applied here: no bin re-cut after seeing the results; empty bins are
**displayed** (never silent); "calibrated" is never returned as a verdict —
only the labels of the cascade (``NOT COMPUTED`` / ``non-conclusive`` /
``claim possible`` under the five frozen conditions).
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

# --- frozen constants --------------------------------------------------------

#: z of the 95 % confidence interval (B7 §b.1 C5: z = 1.959964).
Z_95 = 1.959964

#: 10 fixed bins over [0, 1] — frozen BEFORE any measurement (B7 §b.1 C3).
ECE_BINS = 10

#: C6 bootstrap: 10 000 replications, 6–12 h blocks, fixed seed.
BOOTSTRAP_REPLICATIONS = 10_000
BOOTSTRAP_BLOCK_HOURS = (6, 12)
BOOTSTRAP_SEED = 20261016

#: Cascade thresholds (B7 §b.3).
N_MIN_PUBLISH = 5
N_NON_CONCLUSIVE_MAX = 99
N_CLAIM_MIN = 100
ECE_CLAIM_MAX = 0.05
ECE_CI_UPPER_MAX = 0.08
MAX_BIN_GAP_CLAIM = 0.10

VERDICT_NOT_COMPUTED = "NOT COMPUTED — insufficient N"
VERDICT_NON_CONCLUSIVE = "non-conclusive"
VERDICT_CLAIM_POSSIBLE = "claim possible (5 conditions)"

#: Mandatory sentence wherever a "0 failure" appears (B7 §b.2, R3 §B.5-1).
PHRASE_ZERO_SUCCESS = (
    "0/6 does not mean a zero rate, but a rate compatible with up to ≈ 39 % "
    "(Wilson upper bound)"
)


class CalibrationError(ValueError):
    """Invalid input (p outside [0,1], lists of different sizes, N = 0…)."""


# --- validation -------------------------------------------------------------


def _check_vectors(p: Sequence[float], y: Sequence[int]) -> Tuple[List[float], List[int]]:
    ps = list(p)
    ys = list(y)
    if len(ps) != len(ys):
        raise CalibrationError(f"p and y of different sizes: {len(ps)} ≠ {len(ys)}")
    if not ps:
        raise CalibrationError("N = 0: nothing to compute (publish 'NOT COMPUTED')")
    for value in ps:
        if not 0.0 <= value <= 1.0:
            raise CalibrationError(f"probability outside [0, 1]: {value!r}")
    for value in ys:
        if value not in (0, 1):
            raise CalibrationError(f"outcome outside {{0, 1}}: {value!r}")
    return ps, ys


def bin_index(p: float, n_bins: int = ECE_BINS) -> int:
    """Fixed bin index: ``p`` falls into ``[b/n_bins, (b+1)/n_bins)``.

    ``p = 1`` falls into the last bin. Frozen function: the bounds depend on
    neither the data nor the results.
    """
    if not 0.0 <= p <= 1.0:
        raise CalibrationError(f"probability outside [0, 1]: {p!r}")
    return min(n_bins - 1, int(p * n_bins))


def bin_bounds(b: int, n_bins: int = ECE_BINS) -> Tuple[float, float]:
    """Bounds ``[b/n_bins, (b+1)/n_bins)`` — half-open, documented."""
    if not 0 <= b < n_bins:
        raise CalibrationError(f"bin index outside [0, {n_bins}): {b!r}")
    return b / n_bins, (b + 1) / n_bins


# --- C1: Brier --------------------------------------------------------------


def brier_score(p: Sequence[float], y: Sequence[int]) -> float:
    """C1 — ``BS = (1/N) Σ (p_t − y_t)²`` (Brier 1950)."""
    ps, ys = _check_vectors(p, y)
    return sum((pt - yt) ** 2 for pt, yt in zip(ps, ys)) / len(ps)


def brier_contributions(p: Sequence[float], y: Sequence[int]) -> List[float]:
    """``(p_t − y_t)²`` forecast by forecast (recomputable, non-authoritative)."""
    ps, ys = _check_vectors(p, y)
    return [(pt - yt) ** 2 for pt, yt in zip(ps, ys)]


def climatology(y: Sequence[int]) -> float:
    """``ȳ = (1/N) Σ y_t`` — the base rate is published everywhere (B7 §b.3)."""
    ys = list(y)
    if not ys:
        raise CalibrationError("N = 0: undefined climatology")
    return sum(ys) / len(ys)


# --- C2 + C3 + C4: decomposition, ECE, reliability curve ---------------------


def reliability_table(p: Sequence[float], y: Sequence[int], n_bins: int = ECE_BINS) -> List[dict]:
    """C4 — one row per bin, **empty bins included**.

    Each row: ``bin``, ``n_b``, ``conf_b`` (mean of ``p``), ``acc_b``
    (observed frequency, ``None`` if ``n_b = 0``), Wilson CI of ``acc_b``.
    """
    ps, ys = _check_vectors(p, y)
    buckets: List[List[Tuple[float, int]]] = [[] for _ in range(n_bins)]
    for pt, yt in zip(ps, ys):
        buckets[bin_index(pt, n_bins)].append((pt, yt))
    rows = []
    for b, bucket in enumerate(buckets):
        n_b = len(bucket)
        conf = sum(pt for pt, _ in bucket) / n_b if n_b else None
        acc = sum(yt for _, yt in bucket) / n_b if n_b else None
        if n_b:
            low, high = wilson_interval(sum(yt for _, yt in bucket), n_b)
        else:
            low = high = None
        rows.append(
            {
                "bin": b,
                "bounds": bin_bounds(b, n_bins),
                "n_b": n_b,
                "conf_b": conf,
                "acc_b": acc,
                "wilson_low": low,
                "wilson_high": high,
            }
        )
    return rows


def ece(p: Sequence[float], y: Sequence[int], n_bins: int = ECE_BINS) -> float:
    """C3 — ``ECE = Σ_b (n_b/N) · |acc_b − conf_b|`` (fixed bins)."""
    ps, ys = _check_vectors(p, y)
    rows = reliability_table(ps, ys, n_bins)
    n = len(ps)
    return sum(row["n_b"] / n * abs(row["acc_b"] - row["conf_b"]) for row in rows if row["n_b"])


def murphy_decomposition(p: Sequence[float], y: Sequence[int], n_bins: int = ECE_BINS) -> dict:
    """C2 — ``BS = REL − RES + UNC`` **over the ECE bins**.

    ``REL = Σ_b (n_b/N)(conf_b − acc_b)²``,
    ``RES = Σ_b (n_b/N)(acc_b − ȳ)²``,
    ``UNC = ȳ(1 − ȳ)``.

    The classical identity is exact only when ``p`` is **constant per bin**
    (the KAT case). In general the exact **within-bin term** is required:

    ``BS = REL − RES + UNC + [Σa_i² + 2Σa_i·c_i]/N``,
    with ``a_i = p_i − p̄_b`` and ``c_i = ȳ_b − y_i`` (a null term when ``p`` is
    constant per bin). The function checks the exact identity and raises if
    the gap exceeds 1e-9 — this is the identity test of B7 §b.2 in normal
    operation (W7 fix: the within-bin term was missing).
    """
    ps, ys = _check_vectors(p, y)
    n = len(ps)
    ybar = climatology(ys)
    rows = reliability_table(ps, ys, n_bins)
    rel = sum(row["n_b"] / n * (row["conf_b"] - row["acc_b"]) ** 2 for row in rows if row["n_b"])
    res = sum(row["n_b"] / n * (row["acc_b"] - ybar) ** 2 for row in rows if row["n_b"])
    unc = ybar * (1.0 - ybar)
    bs = brier_score(ps, ys)
    by_bin: dict = {}
    for pi, yi in zip(ps, ys):
        by_bin.setdefault(bin_index(pi, n_bins), []).append((pi, yi))
    within = 0.0
    for items in by_bin.values():
        p_bar = sum(pi for pi, _yi in items) / len(items)
        y_bar = sum(yi for _pi, yi in items) / len(items)
        for pi, yi in items:
            a = pi - p_bar
            within += a * a + 2.0 * a * (y_bar - yi)
    within /= n
    identity = rel - res + unc + within
    if abs(identity - bs) > 1e-9:
        raise CalibrationError(
            f"exact identity (REL − RES + UNC + within-bin) broken: {identity!r} ≠ BS {bs!r} "
            "(binning bug)"
        )
    return {"bs": bs, "rel": rel, "res": res, "unc": unc, "ybar": ybar,
            "within_bin_term": within, "rel_minus_res_plus_unc": rel - res + unc,
            "exact_identity": identity}


# --- C5: Wilson bounds -------------------------------------------------------


def wilson_interval(successes: int, n: int, z: float = Z_95) -> Tuple[float, float]:
    """C5 — Wilson interval (1927) for a proportion.

    ``(p̂ + z²/2n ± z·√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)``, increasing bounds.
    """
    if n <= 0:
        raise CalibrationError("n ≤ 0: undefined interval")
    if not 0 <= successes <= n:
        raise CalibrationError(f"successes outside [0, n]: {successes!r}/{n!r}")
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    spread = z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))
    low = (centre - spread) / denom
    high = (centre + spread) / denom
    return (max(0.0, low), min(1.0, high))


def wilson_upper_for_zero(n: int, z: float = Z_95) -> float:
    """Wilson upper bound for ``0 success out of n``: ``z²/(n + z²)``.

    KAT: n = 6 → 0.390334 (39.0 %) ; n = 12 → 0.242494 (24.2494 % — B7 §b.2
    prints 24.2 %, rounding at z = 1.96 prints 24.3 % ; the exact value is
    24.2494 %, neither printed figure is "wrong" to within 1e-3).
    """
    if n <= 0:
        raise CalibrationError("n ≤ 0: undefined bound")
    z2 = z * z
    return z2 / (n + z2)


# --- C6: block bootstrap (deterministic) -------------------------------------


def block_bootstrap_indices(n: int, block_size: int, rng: random.Random) -> List[int]:
    """Indices of a **circular block** resampling of fixed size."""
    if block_size <= 0:
        raise CalibrationError("block size ≤ 0")
    out: List[int] = []
    while len(out) < n:
        start = rng.randrange(n)
        for offset in range(block_size):
            out.append((start + offset) % n)
    return out[:n]


def block_bootstrap_ci(
    values: Sequence[float],
    block_size: int = BOOTSTRAP_BLOCK_HOURS[0],
    n_reps: int = BOOTSTRAP_REPLICATIONS,
    seed: int = BOOTSTRAP_SEED,
    alpha: float = 0.05,
) -> dict:
    """C6 — percentile CI (2.5–97.5) of the mean, circular block bootstrap,
    **fixed seed** (``random.Random(seed)`` ⇒ bit-identical reproducibility,
    tested).

    ``block_size`` in observations (6–12 h on an hourly grid, B7 §b.1).
    """
    xs = list(values)
    if not xs:
        raise CalibrationError("empty series: undefined bootstrap")
    if n_reps <= 0:
        raise CalibrationError("n_reps ≤ 0")
    rng = random.Random(seed)
    n = len(xs)
    means: List[float] = []
    for _ in range(n_reps):
        idx = block_bootstrap_indices(n, block_size, rng)
        means.append(sum(xs[i] for i in idx) / n)
    means.sort()
    lo_idx = int(math.floor((alpha / 2.0) * n_reps))
    hi_idx = min(n_reps - 1, int(math.ceil((1.0 - alpha / 2.0) * n_reps)) - 1)
    return {
        "mean": sum(xs) / n,
        "ci_low": means[lo_idx],
        "ci_high": means[hi_idx],
        "block_size": block_size,
        "n_reps": n_reps,
        "seed": seed,
        "alpha": alpha,
    }


def bootstrap_percentile(sorted_values: Sequence[float], value: float) -> float:
    """Percentile (0–100) of ``value`` in a sorted distribution — used to
    locate A2 inside the B0 placebo distribution (B7 §e.1)."""
    xs = list(sorted_values)
    if not xs:
        raise CalibrationError("empty distribution")
    below = sum(1 for x in xs if x <= value)
    return 100.0 * below / len(xs)


# --- C7: skill ---------------------------------------------------------------


def brier_skill_score(bs: float, ybar: float) -> Optional[float]:
    """C7 — ``BSS = 1 − BS / BS_clim``, ``BS_clim = ȳ(1 − ȳ)``.

    ``None`` when ``ȳ ∈ {0, 1}``: the climatology is degenerate, the skill
    score does not exist (no invented number).
    """
    clim = ybar * (1.0 - ybar)
    if clim == 0.0:
        return None
    return 1.0 - bs / clim


# --- Exact McNemar -----------------------------------------------------------


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar test (two discordant outcomes ``b`` and ``c``).

    ``p = 2 · Σ_{k=0}^{min(b,c)} C(n,k) / 2^n``, bounded to 1 (n = b + c).
    KAT : ``b = 6, c = 0`` → ``2 · (1/64) = 0,03125``.
    """
    if b < 0 or c < 0:
        raise CalibrationError("negative discordant counts")
    n = b + c
    if n == 0:
        raise CalibrationError("no discordant pair: undefined test")
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


# --- cascade and report ------------------------------------------------------


def verdict_for_n(n: int) -> str:
    """Cascade label (B7 §b.3) for a given ``N``."""
    if n < N_MIN_PUBLISH:
        return VERDICT_NOT_COMPUTED
    if n <= N_NON_CONCLUSIVE_MAX:
        return VERDICT_NON_CONCLUSIVE
    return VERDICT_CLAIM_POSSIBLE


def calibration_report(p: Sequence[float], y: Sequence[int]) -> dict:
    """Machine report (B7 §b.4 items 2–3 structure), label included.

    Refuses ``N < 5`` by raising: the N = 0 skeleton is published by the
    dedicated report (``evidence/calibration_report_skeleton.md``), not by a
    function that would produce silent zeros.
    """
    ps, ys = _check_vectors(p, y)
    n = len(ps)
    if n < N_MIN_PUBLISH:
        raise CalibrationError(
            f"N = {n} < {N_MIN_PUBLISH}: nothing is published (D11 threshold) — "
            "expected label: " + VERDICT_NOT_COMPUTED
        )
    dec = murphy_decomposition(ps, ys)
    bs_ci = block_bootstrap_ci(brier_contributions(ps, ys))
    result = {
        "n": n,
        "ybar": dec["ybar"],
        "bs": dec["bs"],
        "rel": dec["rel"],
        "res": dec["res"],
        "unc": dec["unc"],
        "ece": ece(ps, ys),
        "bss": brier_skill_score(dec["bs"], dec["ybar"]),
        "bs_bootstrap_ci": [bs_ci["ci_low"], bs_ci["ci_high"]],
        "reliability": reliability_table(ps, ys),
        "verdict": verdict_for_n(n),
        "bins": ECE_BINS,
        "bootstrap": {"block_size": bs_ci["block_size"], "n_reps": bs_ci["n_reps"], "seed": bs_ci["seed"]},
    }
    return result
