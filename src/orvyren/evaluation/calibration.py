#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — calibration de prévisions : C1–C7 (G5), stdlib pure.

Sources normatives : B7 §b.1 (formules et références), §b.2 (vecteur KAT
vérifié), §b.3 (cascade « quand peut-on dire calibré »), DOC2 §5.8.2.

Métriques :

======== ==========================================================
**C1**   score de Brier ``BS = (1/N) Σ (p_t − y_t)²`` (Brier 1950)
**C2**   décomposition de Murphy ``BS = REL − RES + UNC``, sur les
         **mêmes intervalles** que l'ECE (identité exacte, testable)
**C3**   ECE à **10 intervalles fixes** ``[b/10, (b+1)/10)`` gelés d'avance
**C4**   courbe de fiabilité par intervalle (``n_b``, ``conf_b``,
         ``acc_b``, IC de Wilson par intervalle)
**C5**   bornes de Wilson (z = 1,959964, Wilson 1927)
**C6**   bootstrap par blocs circulaire, 10 000 réplications, graine fixée
**C7**   compétence ``BSS = 1 − BS / (ȳ(1−ȳ))``
======== ==========================================================

Vecteur KAT (B7 §b.2, tolérance 1e-12) : ``p = [0,2 ×5 ; 0,8 ×5]``,
``y = [0,0,0,0,0, 1,1,0,1,1]`` → ``BS = REL − RES + UNC = 0,02 − 0,16 + 0,24
= 0,10``, ``ECE = 0,10``, ``ȳ = 0,40``.

Garde-fous appliqués ici : aucun intervalle re-découpé après avoir vu les
résultats ; les intervalles vides sont **affichés** (jamais silencieux) ;
« calibré » n'est jamais renvoyé comme verdict — seulement les libellés de la
cascade (``NON CALCULÉ`` / ``non conclusionnel`` / ``revendication possible``
sous les cinq conditions gelées).
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

# --- constantes gelées -------------------------------------------------------

#: z de l'intervalle de confiance à 95 % (B7 §b.1 C5 : z = 1,959964).
Z_95 = 1.959964

#: 10 intervalles fixes sur [0, 1] — gelés AVANT toute mesure (B7 §b.1 C3).
ECE_BINS = 10

#: Bootstrap C6 : 10 000 réplications, blocs 6–12 h, graine fixée.
BOOTSTRAP_REPLICATIONS = 10_000
BOOTSTRAP_BLOCK_HOURS = (6, 12)
BOOTSTRAP_SEED = 20261016

#: Seuils de la cascade (B7 §b.3).
N_MIN_PUBLISH = 5
N_NON_CONCLUSIVE_MAX = 99
N_CLAIM_MIN = 100
ECE_CLAIM_MAX = 0.05
ECE_CI_UPPER_MAX = 0.08
MAX_BIN_GAP_CLAIM = 0.10

VERDICT_NOT_COMPUTED = "NON CALCULÉ — N insuffisant"
VERDICT_NON_CONCLUSIVE = "non conclusionnel"
VERDICT_CLAIM_POSSIBLE = "revendication possible (5 conditions)"

#: Phrase obligatoire partout où un « 0 échec » apparaît (B7 §b.2, R3 §B.5-1).
PHRASE_ZERO_SUCCESS = (
    "0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % "
    "(borne supérieure de Wilson)"
)


class CalibrationError(ValueError):
    """Entrée invalide (p hors [0,1], listes de tailles différentes, N = 0…)."""


# --- validation --------------------------------------------------------------


def _check_vectors(p: Sequence[float], y: Sequence[int]) -> Tuple[List[float], List[int]]:
    ps = list(p)
    ys = list(y)
    if len(ps) != len(ys):
        raise CalibrationError(f"p et y de tailles différentes : {len(ps)} ≠ {len(ys)}")
    if not ps:
        raise CalibrationError("N = 0 : rien à calculer (publier « NON CALCULÉ »)")
    for value in ps:
        if not 0.0 <= value <= 1.0:
            raise CalibrationError(f"probabilité hors [0, 1] : {value!r}")
    for value in ys:
        if value not in (0, 1):
            raise CalibrationError(f"outcome hors {{0, 1}} : {value!r}")
    return ps, ys


def bin_index(p: float, n_bins: int = ECE_BINS) -> int:
    """Indice d'intervalle fixe : ``p`` tombe dans ``[b/n_bins, (b+1)/n_bins)``.

    ``p = 1`` tombe dans le dernier intervalle. Fonction gelée : les bornes ne
    dépendent ni des données ni des résultats.
    """
    if not 0.0 <= p <= 1.0:
        raise CalibrationError(f"probabilité hors [0, 1] : {p!r}")
    return min(n_bins - 1, int(p * n_bins))


def bin_bounds(b: int, n_bins: int = ECE_BINS) -> Tuple[float, float]:
    """Bornes ``[b/n_bins, (b+1)/n_bins)`` — demi-ouverte, documentée."""
    if not 0 <= b < n_bins:
        raise CalibrationError(f"indice d'intervalle hors [0, {n_bins}) : {b!r}")
    return b / n_bins, (b + 1) / n_bins


# --- C1 : Brier --------------------------------------------------------------


def brier_score(p: Sequence[float], y: Sequence[int]) -> float:
    """C1 — ``BS = (1/N) Σ (p_t − y_t)²`` (Brier 1950)."""
    ps, ys = _check_vectors(p, y)
    return sum((pt - yt) ** 2 for pt, yt in zip(ps, ys)) / len(ps)


def brier_contributions(p: Sequence[float], y: Sequence[int]) -> List[float]:
    """``(p_t − y_t)²`` prévision par prévision (recalculable, non autoritaire)."""
    ps, ys = _check_vectors(p, y)
    return [(pt - yt) ** 2 for pt, yt in zip(ps, ys)]


def climatology(y: Sequence[int]) -> float:
    """``ȳ = (1/N) Σ y_t`` — le taux de base est publié partout (B7 §b.3)."""
    ys = list(y)
    if not ys:
        raise CalibrationError("N = 0 : climatologie indéfinie")
    return sum(ys) / len(ys)


# --- C2 + C3 + C4 : décomposition, ECE, courbe de fiabilité ------------------


def reliability_table(p: Sequence[float], y: Sequence[int], n_bins: int = ECE_BINS) -> List[dict]:
    """C4 — une ligne par intervalle, **intervalles vides inclus**.

    Chaque ligne : ``bin``, ``n_b``, ``conf_b`` (moyenne des ``p``), ``acc_b``
    (fréquence observée, ``None`` si ``n_b = 0``), IC de Wilson de ``acc_b``.
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
    """C3 — ``ECE = Σ_b (n_b/N) · |acc_b − conf_b|`` (intervalles fixes)."""
    ps, ys = _check_vectors(p, y)
    rows = reliability_table(ps, ys, n_bins)
    n = len(ps)
    return sum(row["n_b"] / n * abs(row["acc_b"] - row["conf_b"]) for row in rows if row["n_b"])


def murphy_decomposition(p: Sequence[float], y: Sequence[int], n_bins: int = ECE_BINS) -> dict:
    """C2 — ``BS = REL − RES + UNC`` **sur les intervalles de l'ECE**.

    ``REL = Σ_b (n_b/N)(conf_b − acc_b)²``,
    ``RES = Σ_b (n_b/N)(acc_b − ȳ)²``,
    ``UNC = ȳ(1 − ȳ)``.

    L'identité classique n'est exacte que lorsque ``p`` est **constant par
    bin** (cas du KAT). En général il faut le **terme intra-bin** exact :

    ``BS = REL − RES + UNC + [Σa_i² + 2Σa_i·c_i]/N``,
    avec ``a_i = p_i − p̄_b`` et ``c_i = ȳ_b − y_i`` (terme nul si ``p`` est
    constant par bin). La fonction vérifie l'identité exacte et lève si
    l'écart dépasse 1e-9 — c'est le test d'identité de B7 §b.2 en
    fonctionnement normal (correctif W7 : le terme intra-bin manquait).
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
            f"identité exacte (REL − RES + UNC + intra-bin) cassée : {identity!r} ≠ BS {bs!r} "
            "(bug de binning)"
        )
    return {"bs": bs, "rel": rel, "res": res, "unc": unc, "ybar": ybar,
            "within_bin_term": within, "rel_minus_res_plus_unc": rel - res + unc,
            "exact_identity": identity}


# --- C5 : bornes de Wilson ---------------------------------------------------


def wilson_interval(successes: int, n: int, z: float = Z_95) -> Tuple[float, float]:
    """C5 — intervalle de Wilson (1927) pour une proportion.

    ``(p̂ + z²/2n ± z·√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)``, bornes croissantes.
    """
    if n <= 0:
        raise CalibrationError("n ≤ 0 : intervalle indéfini")
    if not 0 <= successes <= n:
        raise CalibrationError(f"succès hors [0, n] : {successes!r}/{n!r}")
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p_hat + z2 / (2.0 * n)
    spread = z * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))
    low = (centre - spread) / denom
    high = (centre + spread) / denom
    return (max(0.0, low), min(1.0, high))


def wilson_upper_for_zero(n: int, z: float = Z_95) -> float:
    """Borne supérieure de Wilson pour ``0 réussite sur n`` : ``z²/(n + z²)``.

    KAT : n = 6 → 0,390334 (39,0 %) ; n = 12 → 0,242494 (24,2494 % — B7 §b.2
    imprime 24,2 %, l'arrondi à z = 1,96 imprime 24,3 % ; la valeur exacte est
    24,2494 %, aucune des deux impressions n'est « fausse » à 1e-3 près).
    """
    if n <= 0:
        raise CalibrationError("n ≤ 0 : borne indéfinie")
    z2 = z * z
    return z2 / (n + z2)


# --- C6 : bootstrap par blocs (déterministe) ---------------------------------


def block_bootstrap_indices(n: int, block_size: int, rng: random.Random) -> List[int]:
    """Indices d'un rééchantillonnage **circulaire par blocs** de taille fixe."""
    if block_size <= 0:
        raise CalibrationError("taille de bloc ≤ 0")
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
    """C6 — IC percentile (2,5–97,5) de la moyenne, bootstrap circulaire par
    blocs, **graine fixée** (``random.Random(seed)`` ⇒ reproductible à
    l'identique, testé).

    ``block_size`` en observations (6–12 h sur une grille horaire, B7 §b.1).
    """
    xs = list(values)
    if not xs:
        raise CalibrationError("série vide : bootstrap indéfini")
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
    """Percentile (0–100) de ``value`` dans une distribution triée — utilisé
    pour situer A2 dans la distribution placebo B0 (B7 §e.1)."""
    xs = list(sorted_values)
    if not xs:
        raise CalibrationError("distribution vide")
    below = sum(1 for x in xs if x <= value)
    return 100.0 * below / len(xs)


# --- C7 : compétence ---------------------------------------------------------


def brier_skill_score(bs: float, ybar: float) -> Optional[float]:
    """C7 — ``BSS = 1 − BS / BS_clim``, ``BS_clim = ȳ(1 − ȳ)``.

    ``None`` quand ``ȳ ∈ {0, 1}`` : la climatologie est dégénérée, le score de
    compétence n'existe pas (aucun chiffre inventé).
    """
    clim = ybar * (1.0 - ybar)
    if clim == 0.0:
        return None
    return 1.0 - bs / clim


# --- McNemar exact -----------------------------------------------------------


def mcnemar_exact(b: int, c: int) -> float:
    """Test exact de McNemar (deux issues discordantes ``b`` et ``c``).

    ``p = 2 · Σ_{k=0}^{min(b,c)} C(n,k) / 2^n``, borné à 1 (n = b + c).
    KAT : ``b = 6, c = 0`` → ``2 · (1/64) = 0,03125``.
    """
    if b < 0 or c < 0:
        raise CalibrationError("comptes discordants négatifs")
    n = b + c
    if n == 0:
        raise CalibrationError("aucune paire discordante : test indéfini")
    tail = sum(math.comb(n, k) for k in range(0, min(b, c) + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


# --- cascade et rapport ------------------------------------------------------


def verdict_for_n(n: int) -> str:
    """Libellé de la cascade B7 §b.3 pour un effectif ``N`` donné."""
    if n < N_MIN_PUBLISH:
        return VERDICT_NOT_COMPUTED
    if n <= N_NON_CONCLUSIVE_MAX:
        return VERDICT_NON_CONCLUSIVE
    return VERDICT_CLAIM_POSSIBLE


def calibration_report(p: Sequence[float], y: Sequence[int]) -> dict:
    """Rapport machine (structure B7 §b.4 items 2–3), libellé inclus.

    Refuse ``N < 5`` en levant : le squelette N = 0 est publié par le rapport
    dédié (``evidence/calibration_report_skeleton.md``), pas par une fonction
    qui produirait des zéros silencieux.
    """
    ps, ys = _check_vectors(p, y)
    n = len(ps)
    if n < N_MIN_PUBLISH:
        raise CalibrationError(
            f"N = {n} < {N_MIN_PUBLISH} : rien n'est publié (seuil D11) — "
            "libellé attendu : " + VERDICT_NOT_COMPUTED
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
