#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — comparateurs du harnais : A0, A1, AX0, B0, O (G2).

Sources normatives : B7 §e.1 (table des comparateurs, résolution de la
collision d'étiquettes) ; W2-D §C.1 ; FREEZE_V2 §7 (G3 : A0/A1/A2/B0 (+ AX0)).

Étiquettes gelées (B7 §e.1 — la collision « A0 » de R3 est tranchée) :

* **A0** — NO-ACTION : l'adversaire décisif du regret, zéro action ;
* **A1** — règle de seuil : décote ``D ≥ 50 bp`` pendant 15 min → réduction
  bornée ``x* = min(x_max, Depth_ε, x_seuil)`` ; ``Depth_ε`` non mesurée ⇒ le
  plafond ``x_max`` est utilisé **et la substitution est écrite** ;
* **A2** — l'agent ORVYREN (rejoue le journal, sinon l'archive) : produit par
  les blocs A–E, pas par ce module (seule la forme des actions est définie ici) ;
* **B0** — placebo apparié : mêmes nombre et tailles d'actions que A2,
  horodatages tirés uniformément sur la grille horaire de la fenêtre,
  ``M ≥ 200`` tirages, **graine fixée** ; on publie la distribution complète ;
* **AX0** — règle gelée du dépôt (0,99 × 2 observations → réduction de
  100 USDC ; ``decision/baseline.py``, FREEZE_V1 D6) — déléguée, jamais
  réimplémentée (une seule source de vérité) ;
* **O** — oracle ex post **faisable** : ``min_{b ∈ F} L(b)``, borne inférieure
  du regret, pas une vérité terrain.

Deux phrases pré-écrites (gelées AVANT exécution, B7 §e.1) — si A2 ne bat pas
B0, la valeur n'est pas dans le **choix du moment** ; si A2 ne bat pas A1,
elle n'est pas dans la **délibération** : on l'écrit.
"""

from __future__ import annotations

import datetime as _dt
import random
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from orvyren.evaluation import loss as loss_mod

# --- constantes gelées -------------------------------------------------------

A0_LABEL = "A0"
A1_LABEL = "A1"
A2_LABEL = "A2"
B0_LABEL = "B0"
AX0_LABEL = "AX0"
ORACLE_LABEL = "O"

COMPARATOR_LABELS = (A0_LABEL, A1_LABEL, A2_LABEL, B0_LABEL, AX0_LABEL)

#: A1 — seuils issus de W2-B §1.1, à geler (G4) : décote ≥ 50 bp pendant 15 min.
A1_MIN_DISCOUNT_BP = 50.0
A1_PERSISTENCE_MINUTES = 15.0
A1_MIN_OBSERVATIONS = 2  # sur grille horaire, « ≥ 15 min » = 2 lectures consécutives

#: Plafond d'action de la démo (FREEZE_V2 §5 E2 : « Run ALLOW : 100 USDC » ;
#: repris de evidence/decision_usdc-2023-03.json, exposure_parameters).
X_MAX_USDC_DEMO = 100.0

#: B0 — placebo apparié : M ≥ 200 tirages, graine fixée (B7 §e.1).
B0_MIN_DRAWS = 200
B0_SEED = 20261016
B0_GRID_HOURS = 1

#: Phrases gelées (à publier telles quelles si le cas se présente).
PHRASE_IF_A2_BEATS_NOT_B0 = (
    "Si A2 ne bat pas B0, la valeur du système n'est pas dans le choix du moment — écrit tel quel."
)
PHRASE_IF_A2_BEATS_NOT_A1 = (
    "Si A2 ne bat pas A1, la valeur du système n'est pas dans la délibération — écrit tel quel."
)


class ComparatorError(ValueError):
    """Paramètres de comparateur invalides (jamais corrigés en silence)."""


# --- A0 : NO-ACTION ----------------------------------------------------------


def a0_actions(*_args, **_kwargs) -> Tuple[()]:
    """A0 — NO-ACTION sur toute la fenêtre : zéro action, coût nul."""
    return ()


# --- A1 : règle de seuil -----------------------------------------------------


def a1_signal_times(
    series: Sequence[Tuple[str, float]],
    peg: float = 1.0,
    min_discount_bp: float = A1_MIN_DISCOUNT_BP,
    persistence_minutes: float = A1_PERSISTENCE_MINUTES,
    max_gap_minutes: float = 90.0,
) -> List[str]:
    """Horodatages (ISO UTC) où la règle de seuil A1 déclenche.

    ``series`` : couples ``(timestamp_utc, prix)`` triés ; décote en bp
    ``D = (peg − prix)/peg · 10 000``. Un déclenchement exige ``D ≥ seuil``
    **soutenu** pendant ``persistence_minutes`` : sur une grille horaire,
    ``≥ 15 min`` se dégénère mécaniquement en **deux lectures consécutives**
    (gap ≤ ``max_gap_minutes``), règle documentée, jamais ajustée après coup.
    Le déclenchement est horodaté à la **deuxième** lecture ; un épisode
    persistant ne produit qu'un seul déclenchement (comme AX0).
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
    """Actions de A1 : réduction bornée ``x* = min(x_max, Depth_ε, x_seuil)``.

    ``Depth_ε`` (taille maximale sortable à ≤ ε d'impact, W2-D §A.1.6 D4) et
    ``x_seuil`` sont **mesurés ou fournis** ; tant qu'ils manquent, le plafond
    ``x_max`` s'applique et la note de substitution est attachée à l'action
    (aucune profondeur inventée).
    """
    notes: List[str] = []
    caps: List[float] = [x_max]
    if depth_epsilon is None:
        notes.append("Depth_ε non mesurée — plafond x_max utilisé (chantier W2-B §(f) 5)")
    else:
        caps.append(depth_epsilon)
    if x_seuil is None:
        notes.append("x_seuil non gelé — plafond x_max utilisé")
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


# --- AX0 : règle gelée du dépôt (délégation) ---------------------------------


def ax0_signals(corpus_path: str, window: Sequence[str]) -> List[dict]:
    """AX0 — délègue à ``orvyren.decision.baseline.detect_signals``.

    Aucune réimplémentation : la règle gelée n'existe qu'à un seul endroit
    (une divergence entre deux copies serait un bug de mesure).
    """
    from orvyren.decision import baseline

    observations = baseline.load_observations(corpus_path)
    return baseline.detect_signals(observations, window[0], window[1])


def ax0_actions(corpus_path: str, window: Sequence[str]) -> List[dict]:
    """AX0 sous la forme commune d'actions (une réduction de 100 USDC par signal)."""
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


# --- B0 : placebo apparié ----------------------------------------------------


def b0_draws(
    count: int,
    sizes: Sequence[float],
    window_start_utc: str,
    window_end_utc: str,
    grid_hours: int = B0_GRID_HOURS,
    draws: int = B0_MIN_DRAWS,
    seed: int = B0_SEED,
) -> List[List[dict]]:
    """B0 — ``draws`` tirages d'un jeu d'actions apparié à A2.

    Contrat gelé (B7 §e.1) : **même nombre** d'actions, **mêmes tailles**,
    horodatages **tirés uniformément** sur la grille horaire de la fenêtre,
    **M ≥ 200**, graine fixée. Le tirage est reproductible : deux appels avec
    la même graine rendent des horodatages identiques (testé).
    """
    if draws < B0_MIN_DRAWS:
        raise ComparatorError(f"B0 exige M ≥ {B0_MIN_DRAWS} tirages (reçu {draws}) — règle gelée")
    if count != len(sizes):
        raise ComparatorError(f"appariement invalide : {count} actions pour {len(sizes)} tailles")
    start = _parse(window_start_utc)
    end = _parse(window_end_utc)
    if end <= start:
        raise ComparatorError("fenêtre B0 vide ou inversée")
    grid: List[str] = []
    cursor = start
    while cursor < end:
        grid.append(cursor.strftime("%Y-%m-%dT%H:%M:%SZ"))
        cursor = cursor + _dt.timedelta(hours=grid_hours)
    if not grid:
        raise ComparatorError("grille horaire vide")
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
    """Distribution complète des regrets des tirages B0 (jamais une moyenne seule).

    ``regret_of(actions)`` est le calcul de regret (loss.py gelé) appliqué au
    jeu d'actions tiré ; le harnais fournit la fermeture.
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


# --- O : oracle ex post faisable ---------------------------------------------


def oracle_min_loss(losses: Iterable[float]) -> float:
    """O — ``min_{b ∈ F} L(b)`` sur la famille **faisable** (W2-D §B.1).

    Alias explicite de :func:`orvyren.evaluation.loss.min_feasible_loss`, pour
    que le harnais nomme l'oracle O sans ambiguïté (ce n'est pas un oracle
    omniscient sur les prix futurs).
    """
    return loss_mod.min_feasible_loss(losses)
