#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — générateur du paquet de gel « Sprint 0 » (G1–G6 + prévisions).

Le paquet ``frozen/`` est **entièrement recalculable hors-ligne** : relancer ce
script rend des fichiers identiques au bit près (aucune horloge murale, aucune
source réseau, aucun aléa non ensemencé). Vérification :

    python scripts/verify_frozen.py

Contenu produit :

* ``G1_fonction_de_perte.md``   — formules, conventions, six tests (G1) ;
* ``G2_comparateurs.md``        — A0/A1/A2/B0/AX0/O, phrases gelées (G2) ;
* ``G3_fenetres.md``            — registre DEV/EVAL, embargos, NOT DONE (G3) ;
* ``G4_seuils.md``              — seuils persona SD/ST, statut PROPOSÉ (G4) ;
* ``G5_plan_analyse.md``        — cascade, tests statistiques, rapport (G5) ;
* ``G6_hypotheses_economiques.md`` + ``G6_FEUILLE_DE_SIGNATURE.md`` (G6) ;
* ``Gx.sha256``                 — manifestes sha256sum (vérifiables tels quels) ;
* ``forecasts_dev.jsonl``       — 9 prévisions DEV gelées, chaînées par hash ;
* ``outcomes_dev.jsonl``        — résolutions déterministes de ces prévisions ;
* ``forecasts_eval.jsonl``      — prévision EVAL de la fenêtre instrumentée (eval-usd0pp-2025-01) ;
* ``outcomes_eval.jsonl``       — résolution déterministe de cette prévision ;
* ``FORECASTS_DEV.md``          — lecture FR de chaque prévision + ȳ + Wilson ;
* ``README.md``                 — comment vérifier, ce qui est gelé, ce qui ne l'est pas.

Honnêteté : chaque ``p`` vient d'un **comptage empirique déterministe** sur le
corpus DEV figé (fenêtres de calibration, exclusion de la fenêtre cible — LOO),
jamais d'une intuition. Les fenêtres CALME EVAL 2025–2026 ne sont **pas**
inventées : elles restent NOT DONE (B7 Q6).
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, os.path.join(DEFAULT_REPO_ROOT, "src"))

from orvyren.evaluation import calibration as cal  # noqa: E402
from orvyren.evaluation import forecasts as forecasts_mod  # noqa: E402
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402
from orvyren.replay import corpus as corpus_mod  # noqa: E402

#: Date de gel v1 (Sprint 0). Constante du paquet : la reproductibilité
#: hors-ligne exige que l'horodatage d'écriture soit gelé, pas l'heure murale
#: du recalcul (l'heure réelle d'écriture n'est donc PAS portée par ces
#: artefacts ; elle est celle de la commande qui les recrée).
GEL_AT_UTC = "2026-10-16T00:00:00Z"
RUN_ID = "freeze-sprint0-2026-10-16"
# Signature électronique du chef d'équipe (validation explicite du 2026-10-17).
G6_SIGNED_AT = "2026-10-19"
G6_SIGNER = "AKUE-BITCHI Adote Jovanny"
G6_SIGNATURE_NOTE = ("re-sealed after translation + sensitivity, no parameter changed, "
                     "before first EVAL — electronic validation by the team lead, "
                     "explicit authorisation in the Hermes session of 2026-10-19")
SIGNED_BY = {"role": "gel-g6", "name": G6_SIGNER}

#: Chemins POSIX (stables entre plateformes — ils entrent dans le hash des records).
USDC_CORPUS_RELPATH = "corpus/usdc_observations.csv"
STETH_EVIDENCE_RELPATH = "evidence/episode_steth_2022-06.json"

HOUR = _dt.timedelta(hours=1)


# --------------------------------------------------------------------------- #
# Données figées (lecture seule)
# --------------------------------------------------------------------------- #


def _iso(step: _dt.datetime) -> str:
    return windows_mod.format_utc(step)


def load_usdc_hourly_series(repo_root: str) -> List[Tuple[str, float]]:
    """Série horaire USDC = prix agrégé DeFiLlama du corpus figé.

    Le corpus (``corpus/usdc_observations.csv``, manifeste du 2026-10-14) est
    la source de vérité du jeu DEV : une seule série agrégée par heure, donc
    convention ``close`` assumée (le corpus n'archive pas les plus bas — elle
    n'est pas inventée pour autant).
    """
    path = os.path.join(repo_root, *USDC_CORPUS_RELPATH.split("/"))
    series: List[Tuple[str, float]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["venue"] == "defillama" and row["metric"] == "price_usd":
                series.append((_iso(windows_mod.parse_utc(row["timestamp_utc"])), float(row["value"])))
    series.sort()
    return series


def load_steth_series(repo_root: str) -> List[Tuple[str, float]]:
    """Série stETH = prix réalisable ``1 − décote get_dy(1 stETH)``.

    Source : ``evidence/episode_steth_2022-06.json`` (reconstruction on-chain,
    grille quotidienne + fenêtre horaire 10→17 juin). La décote enregistrée est
    celle réellement obtenue par une vente (frais et slippage inclus) : c'est
    le prix réalisable au sens de W2-D, pas un prix d'écran.
    """
    path = os.path.join(repo_root, *STETH_EVIDENCE_RELPATH.split("/"))
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    series: List[Tuple[str, float]] = []
    for stamp in sorted(payload["series"].keys()):
        point = payload["series"][stamp]
        discount_pct = point["discount"]["1"]["discount_pct"]
        series.append((_iso(windows_mod.parse_utc(stamp)), 1.0 - discount_pct / 100.0))
    return series


def _window_covered(
    series: Sequence[Tuple[str, float]],
    start: _dt.datetime,
    end: _dt.datetime,
    tolerance_minutes: float,
) -> bool:
    """Vrai si ``[start, end]`` est couvert par la série à ``tolerance`` près."""
    points = [windows_mod.parse_utc(stamp) for stamp, _ in series]
    inside = [moment for moment in points if start <= moment <= end]
    if not inside:
        return False
    tolerance = _dt.timedelta(minutes=tolerance_minutes)
    return inside[0] <= start + tolerance and inside[-1] >= end - tolerance


def base_rate_loo(
    series: Sequence[Tuple[str, float]],
    hours: float,
    event,
    exclude_start_utc: str,
    exclude_end_utc: str,
    tolerance_minutes: float,
) -> Dict:
    """Taux de base empirique (leave-one-out) des fenêtres de calibration.

    Principe (B7 §a.4 : « estimateur explicite — comptage empirique fenêtres de
    calibration ») : on énumère toutes les fenêtres de ``hours`` heures
    **couvertes** par la série, on exclut celles qui chevauchent la fenêtre
    cible (la fenêtre évaluée sort du comptage — LOO), et on compte celles où
    l'événement se produit. ``p = k / n``, les deux nombres sont publiés.
    """
    exclude_start = windows_mod.parse_utc(exclude_start_utc)
    exclude_end = windows_mod.parse_utc(exclude_end_utc)
    span = _dt.timedelta(hours=hours)
    n_windows = 0
    k_events = 0
    for stamp, _ in series:
        start = windows_mod.parse_utc(stamp)
        end = start + span
        if start < exclude_end and end > exclude_start:
            continue  # fenêtre de calibration chevauchant la cible : exclue (LOO)
        if not _window_covered(series, start, end, tolerance_minutes):
            continue
        n_windows += 1
        k_events += 1 if event(start, end) else 0
    if n_windows == 0:
        raise RuntimeError("taux de base incalculable : aucune fenêtre de calibration couverte")
    return {"n_windows": n_windows, "k_events": k_events, "p": k_events / n_windows}


def _depeg_event(series, ecart_pct, persistance_obs, max_gap_minutes):
    def event(start: _dt.datetime, end: _dt.datetime) -> bool:
        result = outcomes_mod.sustained_depeg_v1(
            series,
            _iso(start),
            _iso(end),
            ecart_pct=ecart_pct,
            persistance_obs=persistance_obs,
            max_gap_minutes=max_gap_minutes,
        )
        return result["y"] == 1

    return event


def _calm_event(series, tolerance_pct):
    def event(start: _dt.datetime, end: _dt.datetime) -> bool:
        result = outcomes_mod.calm_window_v1(series, _iso(start), _iso(end), tolerance_pct=tolerance_pct)
        return result["y"] == 1

    return event


def _origin(label: str, counts: Dict, extra: str = "") -> str:
    text = (
        f"explicit estimator — {label}: p = {counts['k_events']}/{counts['n_windows']} = "
        f"{counts['p']:.6f}"
    )
    return text + (f" ; {extra}" if extra else "")


# --------------------------------------------------------------------------- #
# Définition des prévisions DEV
# --------------------------------------------------------------------------- #


def _forecast_specs(usdc: Sequence[Tuple[str, float]], steth: Sequence[Tuple[str, float]]) -> List[Dict]:
    """The 8 DEV forecasts, in write order (deterministic chaining)."""

    def usdc_h6(t_frozen, ident, cas, counts, sous_ensemble="depeg"):
        return {
            "forecast_id": ident,
            "episode_id": "usdc-2023-03",
            "set": "dev",
            "persona": "dao",
            "sous_ensemble": sous_ensemble,
            "statement": (
                "A sustained USDC depeg (deviation > 1 % from the peg on ≥ 2 consecutive "
                "hourly observations of the aggregated DeFiLlama series) is observed "
                "within 6 h after t_frozen."
            ),
            "t_frozen": t_frozen,
            "resolve_not_before": _iso(windows_mod.parse_utc(t_frozen) + 6 * HOUR),
            "kind": "H_class",
            "hours": 6.0,
            "series_key": "usdc",
            "y_definition": {
                "ecart_pct": 1.0,
                "persistance_obs": 2,
                "max_gap_minutes": 90,
                "venues": ["defillama"],
                "convention": "close",
                "peg": 1.0,
            },
            "counts": counts,
            "cas": cas,
        }

    specs: List[Dict] = []

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-02-16T00:00:00Z", "2023-02-16T06:00:00Z", 90.0)
    specs.append(usdc_h6("2023-02-16T00:00:00Z", "dev-usdc-2023-03.h-calme-1", "USDC control window, 2023-02-16 00:00Z (calm in the \"no sustained depeg\" sense)", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-02-17T00:00:00Z", "2023-02-17T06:00:00Z", 90.0)
    specs.append(usdc_h6("2023-02-17T00:00:00Z", "dev-usdc-2023-03.h-calme-2", "USDC control window, 2023-02-17 00:00Z", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-10T12:00:00Z", "2023-03-10T18:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-10T12:00:00Z", "dev-usdc-2023-03.h-pre-crise", "USDC, eve of the depeg (2023-03-10 12:00Z)", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-11T04:00:00Z", "2023-03-11T10:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-11T04:00:00Z", "dev-usdc-2023-03.h-crise", "USDC, core of the crisis (2023-03-11 04:00Z)", counts))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-13T12:00:00Z", "2023-03-13T18:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-13T12:00:00Z", "dev-usdc-2023-03.h-post-crise", "USDC, return to parity (2023-03-13 12:00Z)", counts, sous_ensemble="absence_attendue"))

    # NOTE (honnêteté du comptage, LOO) : un forecast d'horizon T portant sur la
    # totalité d'un segment (fenêtre = segment) n'a AUCUNE fenêtre de calibration
    # restante après exclusion — le taux de base serait incalculable. Les
    # horizons T sont donc portés par la série stETH (fenêtres quotidiennes
    # nombreuses) et les horizons H_class par les deux séries.

    counts = base_rate_loo(steth, 72.0, _calm_event(steth, 0.5), "2022-05-05T00:00:00Z", "2022-05-08T00:00:00Z", 1560.0)
    specs.append(
        {
            "forecast_id": "dev-steth-2022-05.t-calme",
            "episode_id": "steth-2022-06",
            "set": "dev",
            "persona": "dao",
            "statement": (
                "The 05/05 → 08/05/2022 window holds the frozen CALM criterion (max |1 − realizable "
                "stETH price| < 0.5 %) on the get_dy 1 stETH series."
            ),
            "t_frozen": "2022-05-05T00:00:00Z",
            "resolve_not_before": "2022-05-08T00:00:00Z",
            "kind": "T",
            "hours": 72.0,
            "t_end": "2022-05-08T00:00:00Z",
            "series_key": "steth",
            "y_definition": {"tolerance_pct": 0.5, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, calm window (frozen CALM criterion)",
            "sous_ensemble": "calme_critere",
        }
    )

    counts = base_rate_loo(steth, 168.0, _depeg_event(steth, 1.0, 2, 1500), "2022-05-12T00:00:00Z", "2022-05-19T00:00:00Z", 1560.0)
    specs.append(
        {
            "forecast_id": "dev-steth-2022-05.t-rupture",
            "episode_id": "steth-2022-06",
            "set": "dev",
            "persona": "dao",
            "statement": (
                "The realizable stETH discount (get_dy for 1 stETH) exceeds 1 % on ≥ 2 consecutive "
                "grid observations during the 7 days following t_frozen."
            ),
            "t_frozen": "2022-05-12T00:00:00Z",
            "resolve_not_before": "2022-05-19T00:00:00Z",
            "kind": "T",
            "hours": 168.0,
            "t_end": "2022-05-19T00:00:00Z",
            "series_key": "steth",
            "y_definition": {"ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 1500, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, onset of the discount (13–21/05/2022)",
            "sous_ensemble": "depeg",
        }
    )

    counts = base_rate_loo(steth, 6.0, _depeg_event(steth, 1.0, 2, 90), "2022-06-13T00:00:00Z", "2022-06-13T06:00:00Z", 90.0)
    specs.append(
        {
            "forecast_id": "dev-steth-2022-06.h-crise",
            "episode_id": "steth-2022-06",
            "set": "dev",
            "persona": "dao",
            "statement": (
                "The realizable stETH discount stays above 1 % on ≥ 2 consecutive hourly "
                "observations within 6 h after t_frozen."
            ),
            "t_frozen": "2022-06-13T00:00:00Z",
            "resolve_not_before": "2022-06-13T06:00:00Z",
            "kind": "H_class",
            "hours": 6.0,
            "series_key": "steth",
            "y_definition": {"ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, hourly window 10→17/06/2022 (Celsius withdrawals freeze)",
            "sous_ensemble": "depeg",
        }
    )

    return specs


# --------------------------------------------------------------------------- #
# Rédaction des documents G1–G6
# --------------------------------------------------------------------------- #


def _hash(repo_root: str, relpath: str) -> str:
    return windows_mod.sha256_file(os.path.join(repo_root, relpath))


def doc_g1(repo_root: str) -> str:
    formulas = (
        "W_T(keep)        = C + q · P_T\n"
        "W_T(sell x)      = C + x · P_exec(x, t_action) − k + (q − x) · P_T\n"
        "L(a)             = W_t0 − W_T(a)                    [USD, or bp of W_t0]\n"
        "R(a)             = L(a) − min_{b ∈ F} L(b) ≥ 0     [USD]\n"
        "R⁻ / R⁺          = cost of the false positive / of the false negative vs A0 (published separately)"
    )
    return f"""# G1 — Loss function (freeze v1)

**Status: FROZEN v1** — {GEL_AT_UTC}. Normative source: W2-D §B.1 (corrected
formulation), §B.6 (six tests), B7 §e.1/e.3 (persona metrics). Frozen code:
`src/orvyren/evaluation/loss.py` — sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','loss.py'))}`.

## 1. Frozen formulas

```
{formulas}
```

## 2. Valuation conventions (never mixed)

| Convention | Definition | Frozen usage |
|---|---|---|
| `terminale` | the remaining position is worth `P_T` (price realizable at T) | desk: terminal + funding |
| `liquidation` | the remaining position is worth the liquidation price measured at T (depth ladder) | DAO (more conservative, W2-D §(f) 3 recommendation) |

The code **refuses** (`ValuationError`) the `liquidation` convention without a
provided depth ladder: no unmeasured conversion is passed off as a measurement.

## 3. Feasible action family F and cost k

* `F` = fractions of q `{{0 ; 0,25 ; 0,5 ; 0,75 ; 1}}`, `x = 0` always included;
  policy cap `x_max` applied by `min(x, x_max)` (demo: 100 USDC, FREEZE_V2 §E2) ;
* `k` = explicit costs **not already included** in `P_exec` (fees, gas, bridging, funding) ;
* `P_exec(x)` = average price obtained for size x, taken from the measured depth ladder —
  never a screen price. `Depth_ε` remains **to be measured** (work item W2-B §(f) 5): NOT DONE.

## 4. Personas

* **DAO** — no re-entry during the episode; conditional avoided loss
  `E[perte] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR` (both factors published);
  second reading in **runway days**, `opex_ref = 44 932 $/day` (G6).
* **desk** — re-entry modelled in the same window: `ΔP&L = x·(P_exec − P_T) − k − financement` ;
  Sharpe/Sortino/MaxDD aggregates (R_f = 0 by crypto convention; `None` when not computable).

## 5. The six tests (W2-D §B.6) — must pass before the freeze

| # | Test | Expected |
|---|---|---|
| T1 | Neutrality (P_exec = P_T, k = 0 ⇒ R = 0) | 0 exact (detects the double counting of §B.2) |
| T2 | Translation invariance | R unchanged to 1e-12 |
| T3 | Monotonicity in cost | L and R increasing |
| T4 | Sign consistency (P_exec > P_T) | R(act) = 0, R(do nothing) > 0 |
| T5 | Inventory additivity | linear in q and in x |
| T6 | Degenerate reference (P_t = 1) | all regrets 0 ; useless action = k |

Executable proof: `tests/test_evaluation_loss.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_loss.py'))}` ; command
`python -m pytest tests/test_evaluation_loss.py -q` (12 tests).

## 6. What is NOT frozen here (NOT DONE, written as is)

* `Depth_ε` (execution depth in crisis): not measured → x_max cap used and **noted** on every A1 action;
* `r_capital` (desk funding rate): no source — see G6;
* the historical `q(1 − P_T)` bug of the earlier formula (W2-D §B.2) is reproduced in a test for non-regression (displayed gap 20 against real gap 10).

## 7. Revision

Any modification of this file or of `loss.py` after the first EVAL run
**invalidates** the evaluation (parameter embargo, B7 §d.2.1): new dated
version + hash + entry in the variants log.
"""


def doc_g2(repo_root: str) -> str:
    return f"""# G2 — Comparators (freeze v1)

**Status: FROZEN v1** — {GEL_AT_UTC}. Sources: B7 §e.1 (table + resolved
label collision), W2-D §C.1. Frozen code: `src/orvyren/evaluation/comparators.py` —
sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','comparators.py'))}`.

## 1. Frozen labels (the R3/W2-D collision is resolved)

| Code | System | Operational definition | Cost |
|---|---|---|---|
| **A0** | NO-ACTION | do nothing over the whole window | 0 |
| **A1** | Threshold rule | discount D ≥ 50 bp for 15 min → bounded reduction x* = min(x_max, Depth_ε, x_seuil) | ~0 |
| **A2** | ORVYREN agent | corpus → graph → hypotheses → branch → critique → bounded policy (journal replay otherwise archive k=3) | capped, measured |
| **B0** | Matched placebo | same number and sizes of actions as A2, timestamps drawn uniformly over the hourly grid, M ≥ 200, fixed seed | ~0 |
| **AX0** | Frozen repository rule (ex-R3 "A0") | 0,99 × 2 consecutive obs → 100 USDC reduction ; delegated to `decision/baseline.py` | ~0 |
| **O** | Ex post feasible oracle | `min_{{b ∈ F}} L(b)` with the frozen loss function — lower bound of the regret, not ground truth | offline |

The frozen repository rule is written **AX0** in every competition report (the label
"A0-code" is forbidden: without that resolution, "A0 did better than A0" was written).

## 2. Frozen parameters

* A1: `min_discount_bp = 50`, `persistence_minutes = 15` (i.e. on the hourly grid, **two
  consecutive readings**, gap ≤ 90 min ; one episode = a single trigger) ;
* B0: `seed = {20261016}`, `M ≥ 200`, hourly grid, draws **reproducible** (same seed → same timestamps) ;
* demo action cap `x_max = 100 USDC` (FREEZE_V2 §E2 ; taken from
  `evidence/decision_usdc-2023-03.json`).

## 3. Pre-written sentences (frozen BEFORE execution, B7 §e.1)

> If A2 does not beat B0, the value of the system is not in the **choice of timing** — written as is.
>
> If A2 does not beat A1, the value of the system is not in the **deliberation** — written as is.

## 4. Executable verifications

`tests/test_evaluation_comparators.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_comparators.py'))}` :
A0 = 0 action ; A1 triggers/single-signal/gap breaks contiguity ; **AX0 reproduces
`evidence/baseline_report.json`** (2 signals main window, 0 on the control window) ;
B0 reproducible and M ≥ 200 required ; oracle = member of F.

## 5. NOT DONE

* A2: code produced by blocks A–E (agents, graph, policy) — outside Sprint 0 ; team API
  keys remain a blocker for `REPLAY-ARCHIVE` mode (B7 §0.11) ;
* `Depth_ε` and `x_seuil` of A1: not measured → x_max cap, substitution note on every action.
"""


def doc_g3(repo_root: str, calm_values: Dict[str, float]) -> str:
    dev_rows = "\n".join(
        f"| `{w.window_id}` | {w.kind} | {w.start_utc} → {w.end_utc} | {', '.join(w.sources)} |"
        for w in windows_mod.DEV_WINDOWS
    )
    eval_rows = "\n".join(
        f"| `{w.window_id}` | {w.kind} | {w.start_utc} → {w.end_utc} | {', '.join(w.sources)} |"
        for w in windows_mod.EVAL_WINDOWS
    )
    pending_rows = "\n".join(
        f"| {entry['window_id']} | {entry['status']} | {entry['reason']} |" for entry in windows_mod.PENDING_WINDOWS
    )
    return f"""# G3 — DEV/EVAL windows, embargoes (freeze v1)

**Status: FROZEN v1 (open proposals marked NOT DONE)** — {GEL_AT_UTC}.
Sources: B7 §d.1/§d.2, FREEZE_V2 §7, DOC2 §5.8.4. Frozen code:
`src/orvyren/evaluation/windows.py` — sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','windows.py'))}`.

## 1. Registry — DEVELOPMENT set

| Window | Type | UTC bounds | Sources |
|---|---|---|---|
{dev_rows}

## 2. Registry — EVALUATION set

| Window | Type | UTC bounds | Sources |
|---|---|---|---|
{eval_rows}

## 3. CALM criterion — mechanical application (the result is written, not adjusted)

Frozen criterion (B7 §d.1): `max|P_t − 1| < 0,5 %` over the whole window ; failure → reclassified STRESS.

* USDC control window 15–18/02/2023: measured maximum deviation **{calm_values['usdc_temoin_max_dev_pct']:.6f} %** ≥ 0,5 % → **reclassified STRESS** (but 0 sustained depeg: rule AX0 produces no signal there, cf. `evidence/baseline_report.json`) ;
* stETH calm window 01–08/05/2022: measured maximum deviation **{calm_values['steth_calme_max_dev_pct']:.6f} %** < 0,5 % → **CALM confirmed** (measurement on the realizable get_dy discount series).

## 4. NOT DONE — windows that cannot be derived (never invented)

| Window | Status | Reason |
|---|---|---|
{pending_rows}

## 5. The four embargoes (verifiers in `windows.py`)

1. **Parameters** — no constant of G1–G6 may be modified after the first EVAL run ; any
   modification invalidates the evaluation (new dated version + hash + variants log).
2. **Data (24 h)** — the band `[début EVAL − 24 h, début EVAL]` is removed from DEV
   (`data_embargo_violations`).
3. **Inspection** — before the freeze, no inspection of the EVAL windows beyond what is published ;
   after the first run, the set is burned.
4. **Cross-calibration** — the calibration months of the thresholds cannot overlap an
   EVAL CALM window (`cross_calibration_violations`) ; without this rule, calibration
   "sees" the evaluation set.

## 6. Freeze gate (mechanical verification, B7 §d.2.5)

* `verify_frozen_package(frozen_dir)`: `G1..G6.sha256` present, readable, matching — otherwise **refusal** ;
* `eval_run_gate(frozen_dir, lock_path, force)`: refusal of the 2nd EVAL run without `--force` ;
  with `--force`, mandatory mention: "evaluation re-executed (invalid for the claim)" ;
* the EVAL evaluation script must refuse to write if an EVAL CALM window overlaps the
  declared calibration period.

## 7. What remains open (written, non-blocking)

Exact list of the 2025–2026 CALM EVAL windows (B7 Q6) and remaining DEV calm windows
(R3 §C.8): they depend on a collection work item — assumed NOT DONE.
"""


def doc_g4(repo_root: str) -> str:
    return f"""# G4 — Per-persona thresholds (freeze v1, status VALIDATED)

**Status: VALIDATED — electronic validation by the team lead on {G6_SIGNED_AT}.** {GEL_AT_UTC}.
Signatory: **{G6_SIGNER}** — {G6_SIGNATURE_NOTE}. Sources: W2-D §C.4.1 (DAO), §C.4.2 (desk),
B7 §e.3/e.4 (metrics). The values below are **taken as is**
from the source documents and **validated**; they are not measured facts.

## 1. DAO persona (treasury)

| Code | Criterion | Formulation | Validated value |
|---|---|---|---|
| SD1 | Material avoided loss | `(L(A0) − L(A2)) / q` in % of the exposure, conditional on the obligation ; second display in runway days | ≥ 5 % |
| SD2 | Controlled friction | cumulative cost of A2 over CALM windows | ≤ 10 % of the crisis avoided loss |
| SD3 | Anticipation | lead time vs the low point of the realizable price ; reaction delay | ≥ 6 h on ≥ 1 EVAL episode ; ≤ 60 min |
| SD4 | Superiority | `R̄(A2) < R̄(A1)` and `< R̄(B0)`, with intervals, R⁻/R⁺ separate | strictly lower |
| SD5 | Traceability | provenance + hash on 100 % of actions ; 0 action outside the envelope | 100 % / 0 |
| SD6 | Honesty | "non-conclusive" everywhere power is missing ; avoided loss published as `P × conditionnel` | present/absent |

## 2. desk persona (P&L)

| Code | Criterion | Formulation | Validated value |
|---|---|---|---|
| ST1 | Cumulative net P&L | all costs included (fees, measured slippage, funding) + block bootstrap interval | > 0 |
| ST2 | Execution quality | realized slippage vs the `get_dy` ladder ; size ≤ Depth_100bp | ≤ 30 bp in stress |
| ST3 | Bounded risk | MaxDD of the decision series over the allocated capital | ≤ 20 % per episode |
| ST4 | Risk-adjusted | Sharpe/Sortino + DSR corrected for the number of variants | CI lower bound > 0 otherwise "non-conclusive" |
| ST5 | Superiority | `ΔP&L(A2) > ΔP&L(A1)` and `> ΔP&L(B0)` with intervals | strictly greater |
| ST6 | Declared asymmetry | agent described as a put ; `p_s` scenarios published | present/absent |

## 3. Common anti-optimism (mandatory devices)

B0 (M ≥ 200, full distribution) · CALM windows mandatory in both sets ·
`ȳ` published everywhere · Wilson on every proportion · block bootstrap (6–12 h, 10 000
replications, fixed seed) · DSR/variants log · separate R⁻/R⁺ + contingency table ·
contamination mention · "what we do not claim" ·
**a single scalar is forbidden** (metric vector + declared unmeasured axes).

## 4. Executable verification to come

The SD/ST thresholds are **not yet read by code** (harness §e.6 items 6–7 are not
built): this document freezes them as a **validated** declaration, the executable
verification will come with `harness.py`. Any modification after the first EVAL run
invalidates the evaluation (parameter embargo).
"""


def doc_g5(repo_root: str) -> str:
    return f"""# G5 — Analysis plan (freeze v1)

**Status: FROZEN v1** — {GEL_AT_UTC}. Sources: B7 §b.1–b.4, §e.2–e.5, DOC2 §5.8.2.
Frozen code: `calibration.py` sha256
`{_hash(repo_root, os.path.join('src','orvyren','evaluation','calibration.py'))}`,
`forecasts.py` sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','forecasts.py'))}`,
`outcomes.py` sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','outcomes.py'))}`.

## 1. Published metrics (C1–C7) and formulas

| Code | Metric | Formula |
|---|---|---|
| C1 | Brier score | `BS = (1/N) Σ (p_t − y_t)²` |
| C2 | Murphy decomposition | `BS = REL − RES + UNC`, evaluated on the **same bins as the ECE** (exact identity, tested) |
| C3 | ECE | `Σ_b (n_b/N)·|acc_b − conf_b|`, **10 fixed bins** `[b/10, (b+1)/10)`, frozen in advance |
| C4 | Reliability curve | per bin: `n_b`, `conf_b`, `acc_b`, Wilson CI (empty bins displayed) |
| C5 | Wilson | `z = 1,959964` ; upper bound of 0/n = `z²/(n+z²)` |
| C6 | Block bootstrap | circular, 6–12 h blocks, 10 000 replications, **fixed seed** ({20261016}), percentile 2,5–97,5 |
| C7 | Skill | `BSS = 1 − BS / (ȳ(1−ȳ))` ; `None` if the climatology is degenerate |

KAT vector (reference unit test, tolerance 1e-12): `p = [0,2×5 ; 0,8×5]`,
`y = [0,0,0,0,0, 1,1,0,1,1]` → BS 0,100 ; REL 0,020 ; RES 0,160 ; UNC 0,240 ; ECE 0,100 ; ȳ 0,400.

## 2. Cascade "when may we say calibrated" (applied mechanically)

| N (resolved frozen forecasts) | What is published | Label |
|---|---|---|
| N < 5 | nothing | "NOT COMPUTED — insufficient N" (D11 threshold) |
| 5 ≤ N < 30 | BS, REL, RES, UNC, ȳ, list ; ECE **without** any claim | "non-conclusive" |
| 30 ≤ N < 100 | + bootstrap CI, reliability curve + Wilson per bin | "non-conclusive" |
| N ≥ 100 | everything + BSS with lower bound | claim possible **under the 5 conditions** |

**The 5 conditions to write "calibrated"**: N ≥ 100 out of sample ; ECE ≤ 0,05 with CI
upper bound ≤ 0,08 ; no systematic deviation (sign test, `max_b |acc_b − conf_b| ≤ 0,10`) ;
BSS CI lower bound > 0 ; ≥ 2 disjoint episode families + declaration of non-tuning.
With N = 5–12, the default state is "non-conclusive" — **published as is**.

## 3. Comparison statistics

* Wilson on **all** proportions ; mandatory sentence for a "0 failure":
  « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » ;
* McNemar **exact** on discordant pairs (`p = 2·Σ C(n,k)/2^n`, bounded at 1 ; KAT 6-0 → 0,03125) ;
* block bootstrap (C6) on every series statistic — never i.i.d. CIs ;
* B0 placebo: full distribution + A2 percentile.

## 4. Imposed report structure (B7 §b.4, 8 sections)

1. scope and hashes (set, episodes, N, period, code_hash, data_hash, list of forecast_id) ;
2. global table (N, ȳ, BS + CI, REL/RES/UNC, ECE, BSS, verdict) ;
3. reliability curve (one line per bin) ;
4. decomposition by family (persona, type, episode — **N displayed per cell**) ;
5. forecast appendix (`forecast_id | p | y | (p−y)² | horizon | resolver`) ;
6. anomalies and corrections (`supersedes`, unresolved, quarantines) ;
7. limitations spelled out (contamination, non-exchangeability, sample sizes) ;
8. verdict in controlled language (never "calibrated" without the 5 conditions).

## 5. Frozen language rules

Every table carries its `N` and its validity ; never merge DEV and EVAL ; never
average R⁻ and R⁺ ; no single aggregate score ; a report without a hash is not verifiable ;
"calibrated" is a controlled word (5 conditions), below that it is "not established".

## 6. Executable verifications

`tests/test_evaluation_calibration.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_calibration.py'))}` : exact KATs,
Wilson vs raw_b7 table (± 0,001), deterministic bootstrap (2 identical runs), cascade.
"""


def doc_g6(repo_root: str) -> str:
    return f"""# G6 — Economic assumptions (freeze v1, status SIGNED)

**Status: SIGNED — electronic validation by the team lead on {G6_SIGNED_AT}.** {GEL_AT_UTC}.
Signatory: **{G6_SIGNER}** — {G6_SIGNATURE_NOTE}. The sheet
`G6_FEUILLE_DE_SIGNATURE.md` carries the validation ; the values below are
those on which the first EVAL runs.
Sources: W2-D §B.3/B.4, §E.2, §(f) 1–7 and 11–12 ; B7 §b.5, §e.3/e.4, Q1 ; FREEZE_V2 §C7.

## 1. Signed parameters and values

| Parameter | Signed value | Status | Source / justification |
|---|---|---|---|
| `opex_ref` (runway days) | **44 932 $/day** | VALIDATED (declared external reference) | ENS IPS 6.46: 16,4 M$/year of 2025 expenses ; computed conversion 16 400 000 ÷ 365 (W2-D §A.1.1, §E.1 ; B7 Q13) |
| `P(obligation)` — USDC DEV window (calculation example) | **0,20** | VALIDATED (unsourced assumption) | working value of W2-D §E.2(b) — « an assumption to be frozen, unsourced » ; no public frequency of forced sales exists |
| `P(obligation)` — EVAL windows | **0,20 per EVAL window** | SIGNED — unsourced working assumption | no public source (W2-D §Non trouvé 6) ; DEV value kept for all EVAL windows, with written justification and published `P*` sensitivity |
| desk scenarios `p_s` | **4 scenarios**: (i) realized, (ii) no re-establishment at 48 h, (iii) slow healing (5 d), (iv) single constrained venue (0,80526 — counterfactual) ; **p_s = 0,25 / 0,25 / 0,25 / 0,25** | SIGNED — list and uniform prior not calibrated | W2-D §(f) 7 ; no public distribution of depeg scenarios (W2-D §Non trouvé 4): the `p_s` are signed assumptions, published with the P&L and their sensitivity |
| `r_capital` (desk funding rate) | **0 %** (desk funded in cash) | SIGNED — working assumption | no source found (B7 Q16) ; "cash without funding" base, 5 % and 10 % sensitivities published with the P&L |
| desk round-trip cost (illustrative) | 20 bp (`k = 4 000 $` on 2 M$) | VALIDATED (illustration) | W2-D §E.3 — « hypothetical, to be measured for real » |

## 2. Attached rules (frozen)

* avoided loss is **never** published unconditionally:
  `E[perte évitée] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR`, both factors visible ;
* any modification of `P(obligation)`, of the `p_s` or of `r_capital` requires a **named re-signature**
  + justification + published sensitivity (B7 §f.2) ;
* a forecast `p` can **never** be produced by an LLM (forbidden by construction, B7 §a.5.5).

## 3. Required sensitivity

For every window where `P(obligation)` enters a verdict, publish the sensitivity of the
sign of `E[perte évitée]` to `P(obligation)`: the switch value is exactly computable
(`P* = coût_AR / (perte|oblig + coût_AR)`) — it must appear in the dossier.

## 4. Signature

Validated by **{G6_SIGNER}** on **{G6_SIGNED_AT}** — {G6_SIGNATURE_NOTE}.
A scanned handwritten copy may be attached to the submission ; the reference
electronic validation is this document and `G6_FEUILLE_DE_SIGNATURE.md`.
"""


def doc_g6_signature(repo_root: str) -> str:
    return f"""# G6 — Signature sheet for the economic assumptions

**Overall status: SIGNED — validated on {G6_SIGNED_AT}.** {GEL_AT_UTC}.
Protocol: FREEZE_V2 §C7 (« G6 signed by the team lead (default) + published sensitivity »).
Signatory: **{G6_SIGNER}** — {G6_SIGNATURE_NOTE}.

Instructions: the signatory ticks each validated parameter, fills in the values
marked `NOT DONE`, dates and signs. The values below are those of the
first EVAL ; any modification after that run requires a named re-signature
and re-labelling.

## Economic assumption parameters

| # | Parameter | Signed value | Source of the proposal | TICK |
|---|---|---|---|---|
| 1 | `opex_ref` (runway days) | 44 932 $/day | ENS IPS 6.46: 16,4 M$/year ÷ 365 (W2-D §A.1.1/E.1) | ☑ validated ☐ modified → …………… |
| 2 | `P(obligation)` — USDC DEV example | 0,20 | working value of W2-D §E.2(b), explicitly unsourced | ☑ validated ☐ modified → …………… |
| 3 | `P(obligation)` — per EVAL window | **0,20 per EVAL window** | no public source (W2-D §Non trouvé 6) ; signed working assumption | ☑ provided below |
| 4 | Desk scenarios (list) | realized · no re-establishment 48 h · slow healing 5 d · single constrained venue 0,80526 | W2-D §(f) 7 | ☑ validated ☐ modified → …………… |
| 5 | `p_s` (scenario probabilities) | **0,25 / 0,25 / 0,25 / 0,25** | no public distribution (W2-D §Non trouvé 4) ; signed uniform prior | ☑ provided below |
| 6 | `r_capital` (desk funding) | **0 %** (cash) | B7 Q16 — no source ; cash base without funding | ☑ provided below |
| 7 | Round-trip cost (desk illustration) | 20 bp | W2-D §E.3 (« hypothetical, to be measured ») | ☑ validated ☐ modified → …………… |

## Values to provide (where applicable)

* `P(obligation)` per EVAL window (written justification per window): **0,20 for each
  EVAL window** — unsourced working assumption, identical to the DEV value ; no
  public frequency of forced sales exists. The `P*` sensitivity is published with the P&L.
* `p_s` of the desk scenarios (with sensitivity): **0,25 / 0,25 / 0,25 / 0,25** — explicitly
  uncalibrated uniform prior ; sensitivity published with the P&L and the report.
* `r_capital` (source or written assumption): **0 %** — desk funded in cash, without funding ;
  the 5 % and 10 % sensitivity variants are published with the P&L.

## Signatures

| Role | Name | Date (UTC) | Signature / hash of the signing commit |
|---|---|---|---|
| Team lead (default, FREEZE_V2 §C7) | {G6_SIGNER} | {G6_SIGNED_AT} | {G6_SIGNATURE_NOTE} |
| Witness (optional) | | | |

**Embargo reminder**: after the first EVAL run, any modification of these
parameters **invalidates** the evaluation (re-labelling mandatory) — it does not "weaken" it (B7 §d.2.1).
"""


def doc_readme(frozen_hashes: Dict[str, str]) -> str:
    rows = "\n".join(f"| `{name}.sha256` | `{digest}` |" for name, digest in sorted(frozen_hashes.items()))
    return f"""# `frozen/` — "Sprint 0" freeze package (G1–G6 + DEV forecasts)

**Freeze date: {GEL_AT_UTC}** · Generated by `scripts/freeze_sprint0.py` · Verified by
`scripts/verify_frozen.py`.

## Contents

| File | Role |
|---|---|
| `G1_fonction_de_perte.md` | G1 — loss formulas, conventions, six tests |
| `G2_comparateurs.md` | G2 — A0/A1/A2/B0/AX0/O, parameters, frozen sentences |
| `G3_fenetres.md` | G3 — DEV/EVAL registry, embargoes, freeze gate |
| `G4_seuils.md` | G4 — persona thresholds (VALIDATED) |
| `G5_plan_analyse.md` | G5 — metrics, cascade, report |
| `G6_hypotheses_economiques.md` | G6 — economic assumptions (SIGNED) |
| `G6_FEUILLE_DE_SIGNATURE.md` | Team lead signature sheet |
| `Gx.sha256` | sha256sum manifests of the documents above |
| `forecasts_dev.jsonl` | Frozen DEV forecasts, chained by `prev_hash` |
| `outcomes_dev.jsonl` | Deterministic resolutions, chained |
| `FORECASTS_DEV.md` | Detailed reading of the forecasts (provenance, ȳ, Wilson) |
| `README.md` | This file (not self-referenced: see note) |

## Verify (2 minutes, offline)

```bash
# 1. Fingerprints of the freeze manifests
python scripts/verify_frozen.py          # everything: sha256 + chains + full recalculation
cd frozen && sha256sum -c G1.sha256      # (same for G2..G6 ; GNU coreutils)
# 2. Full recalculation of the package in a temporary directory and byte-for-byte comparison
python scripts/freeze_sprint0.py --out /tmp/frozen_recalc
```

## What is frozen, what is not

* **FROZEN**: the six documents, their fingerprints, the 9 DEV forecasts (chained hash) and their
  deterministic resolutions ;
* **VALIDATED / SIGNED on {G6_SIGNED_AT}**: G4 (persona thresholds, validated) and G6 (economic
  assumptions, signed by **{G6_SIGNER}**) — the EVAL can be claimed from this package ;
* **NOT DONE (never invented)**: 2025–2026 CALM EVAL windows (B7 Q6) and `Depth_ε` —
  see `G3_fenetres.md` §4 ; the previously missing G6 assumptions are now
  signed (P(obligation) EVAL = 0,20 ; uniform `p_s` ; `r_capital` = 0 %).

## Manifest fingerprints (copyable)

| Manifest | sha256 |
|---|---|
{rows}

*Note: `README.md` and `FORECASTS_DEV.md` do not appear in the Gx manifests (they are not
frozen documents in the sense of the protocol) ; their fingerprints are verified by `verify_frozen.py`
during the byte-for-byte recalculation.*

## Warning — when to regenerate

The G1, G2, G3, G5 documents carry the **code fingerprints** (`loss.py`, `comparators.py`,
`windows.py`, `calibration.py`, `forecasts.py`, `outcomes.py`): any modification of these
files **requires regenerating the package** (`python scripts/freeze_sprint0.py`), otherwise
`verify_frozen.py` reports the discrepancy — this is intended (a freeze that no longer matches
the code is no longer a freeze). After the first EVAL run, modifying anything in G1–G6
**invalidates** the evaluation (re-labelling mandatory).
"""


# --------------------------------------------------------------------------- #
# INDEX.md — index machine-readable du périmètre gelé
# --------------------------------------------------------------------------- #

#: Fichiers de code couverts par les empreintes sha256 annoncées dans les
#: documents G1–G6 (source de vérité : les lignes sha256 de ces documents).
#: Cette table alimente ``frozen/INDEX.md`` : l'index est GÉNÉRÉ avec le
#: paquet, jamais maintenu à la main — un index séparé dériverait du gel
#: qu'il décrit.
FROZEN_CODE_FILES: Tuple[Tuple[str, str, str], ...] = (
    ("src/orvyren/evaluation/loss.py", "G1_fonction_de_perte.md",
     "G1 loss function (W_T, L(a), R(a), regrets)"),
    ("tests/test_evaluation_loss.py", "G1_fonction_de_perte.md",
     "G1 executable proof (loss KAT)"),
    ("src/orvyren/evaluation/comparators.py", "G2_comparateurs.md",
     "G2 comparators (A0/A1/A2/B0/AX0/O, regret_pair)"),
    ("tests/test_evaluation_comparators.py", "G2_comparateurs.md",
     "G2 executable proof"),
    ("src/orvyren/evaluation/windows.py", "G3_fenetres.md",
     "G3 windows (DEV/EVAL registry, verify_frozen_package)"),
    ("src/orvyren/evaluation/calibration.py", "G5_plan_analyse.md",
     "G5 calibration (verdict_for_n, exact Mcnemar, BSS)"),
    ("src/orvyren/evaluation/forecasts.py", "G5_plan_analyse.md",
     "G5 forecasts (build_forecast, prev_hash chain)"),
    ("src/orvyren/evaluation/outcomes.py", "G5_plan_analyse.md",
     "G5 outcomes (resolution rules, chained outcomes)"),
    ("tests/test_evaluation_calibration.py", "G5_plan_analyse.md",
     "G5 executable proof (calibration KAT)"),
)


def doc_index(repo_root: str) -> str:
    """``INDEX.md`` — machine-readable index of the frozen perimeter (9 files).

    Recomputed byte for byte by ``scripts/verify_frozen.py`` with the rest of the
    package: this index therefore cannot drift from the freeze it describes.
    """
    rows = []
    machine: Dict[str, object] = {
        "schema": "orvyren/frozen-index/v1",
        "note": "generated by scripts/freeze_sprint0.py — never hand-edited",
        "files": {},
    }
    for relpath, doc, role in FROZEN_CODE_FILES:
        digest = _hash(repo_root, relpath)
        rows.append("| `%s` | `%s` | `%s` | %s |" % (relpath, digest, doc, role))
        machine["files"][relpath] = {"sha256": digest, "announced_in": doc, "role": role}
    block = json.dumps(machine, sort_keys=True, indent=1, ensure_ascii=False)
    return """# `frozen/INDEX.md` — frozen-perimeter index (G1–G6)

**Role.** Exact inventory of the code files covered by the sha256 fingerprints
announced in documents G1–G6: for each one, the declared hash, the document
that announces it and its role. Before modifying any of these 9 files, read
its row below — its hash is a tripwire: `scripts/verify_frozen.py`
(byte-for-byte recomputation of the package),
`orvyren.evaluation.harness.verify_code_hashes` (the EVAL freeze gate) and
`tests/test_evaluation_forecasts.py::test_recalcul_hors_ligne_identique`
turn red. The only procedure is the **visible re-sealing** (§3); never a
silent patch.

`G4_seuils.md` (persona thresholds) and `G6_hypotheses_economiques.md` (signed
economic hypotheses) announce **no** code hash;
`G6_FEUILLE_DE_SIGNATURE.md` is the signature sheet. The other files in
`frozen/` (README.md, FORECASTS_DEV.md, `forecasts_dev.jsonl`,
`outcomes_dev.jsonl`, `Gx.sha256` manifests) are covered by the byte-for-byte
recomputation, not by a fingerprint announced in a Gx document.

## 1. Files frozen by hash (9)

| file | declared sha256 | announced in | role |
|---|---|---|---|
""" + "\n".join(rows) + """

## 2. Machine block (canonical JSON)

```json
""" + block + """
```

## 3. Re-sealing recipe (4 commands)

Follow this AFTER any deliberate correction of one of the 9 files above; the
recomputation must become byte-identical again, which is the proof that the
freeze follows the code (the correction is never lost against the tripwire):

```bash
# 1. regenerate the whole package in a NEW directory (native path C:/...,
#    never a /c/... MSYS path that would be created in the wrong place)
python scripts/freeze_sprint0.py --out C:/Users/User/AppData/Local/Temp/frozen_check
# 2. visibly copy the regenerated package into frozen/ (Gx*.md + Gx*.sha256 +
#    README.md + INDEX.md + FORECASTS_DEV.md + forecasts_dev.jsonl(.sha256) +
#    outcomes_dev.jsonl(.sha256)) — a stale hash is fixed in the same commit
cp C:/Users/User/AppData/Local/Temp/frozen_check/* frozen/
# 3. the verification must end COMPLIANT (fingerprints + chains + recomputation)
python scripts/verify_frozen.py
# 4. the suite must stay green (including the package recomputation)
python -m unittest discover -s tests
```

## 4. Warning — a foreign file inside `frozen/` breaks the tripwire

The recomputation compares the **complete inventory** of `frozen/` with the
output of `scripts/freeze_sprint0.build_all`: any file added by hand is
reported (measured: `[KO] recalc: mismatches ['INDEX.md']` before this index
was generated by the builder itself), and `tests/test_evaluation_forecasts.py`
fails on `not rebuilt`. A new document in `frozen/` must therefore be
**produced by `build_all`** (deterministic content, no clock) or live outside
`frozen/` — never dropped in its place.

## 5. Related scope

* Scope registry (authority): `docs/SUBMISSION_SCOPE_AND_GAPS.md`.
* Detailed technical deviations: `docs/ECARTS_REGISTRE.md` (including the two
  frozen-test tautologies awaiting a visible G1/G5 re-seal).
* Critic-reference contract: `docs/decisions/ADR-0004-references-critique-namespaces.md`.
"""


# --------------------------------------------------------------------------- #
# Construction du paquet
# --------------------------------------------------------------------------- #


def _write_text(path: str, text: str) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return windows_mod.sha256_file(path)


def _write_manifest(frozen_dir: str, name: str, filenames: Sequence[str]) -> str:
    lines = []
    for filename in filenames:
        digest = windows_mod.sha256_file(os.path.join(frozen_dir, filename))
        lines.append(f"{digest}  {filename}")
    with open(os.path.join(frozen_dir, f"{name}.sha256"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
    return windows_mod.sha256_file(os.path.join(frozen_dir, f"{name}.sha256"))


# --------------------------------------------------------------------------- #
# EVAL forecasts/outcomes of the instrumented windows (same construction as DEV)
# --------------------------------------------------------------------------- #

#: Write stamp of the EVAL records = date of the G6 signature. Frozen constant:
#: the artefacts stay bit-identical when the package is rebuilt (no wall clock).
EVAL_SEAL_AT_UTC = "2026-10-19T00:00:00Z"
EVAL_RUN_ID = "eval-instrumentation-2026-10-19"

#: Signed G6 prior, taken as is (§1: « P(obligation) — EVAL windows = 0,20 per
#: EVAL window »). Never recomputed on EVAL data, never tuned (B7 §d.2.4).
P_OBLIGATION_EVAL = 0.20

#: Archived series of eval-usd0pp-2025-01 (W3-C probe, pinned by the corpus manifest).
USD0PP_SERIES_RELPATH = "corpus/series/usd0pp_2025-01.json"

EVAL_FORECASTS_NAME = "forecasts_eval.jsonl"
EVAL_OUTCOMES_NAME = "outcomes_eval.jsonl"


def eval_forecast_specs(repo_root: str) -> List[Dict]:
    """The EVAL forecasts, in write order (deterministic chaining).

    One forecast per **instrumented** EVAL window: the unit of the signed
    ``P(obligation)`` is the window, not a sub-interval. ``eval-rseth-2026-04``
    has no archived series — nothing is produced for it (it stays SKIPPED).
    """
    series_path = os.path.join(repo_root, *USD0PP_SERIES_RELPATH.split("/"))
    series_digest = windows_mod.sha256_file(series_path)
    window = next(w for w in windows_mod.EVAL_WINDOWS if w.window_id == "eval-usd0pp-2025-01")
    hours = (window.end - window.start).total_seconds() / 3600.0
    return [
        {
            "forecast_id": "eval-usd0pp-2025-01.t-obligation",
            "episode_id": window.episode_id,
            "set": windows_mod.SET_EVAL,
            "persona": "dao",
            "statement": (
                "Within the EVAL window 08/01 → 31/01/2025 (t_frozen → t_end), a sustained USD0++ "
                "depeg (deviation > 1 % from the $1 peg on ≥ 2 consecutive observations of the "
                "archived DeFiLlama hourly series, gap ≤ 90 min) is observed at least once."
            ),
            "t_frozen": window.start_utc,
            "resolve_not_before": window.end_utc,
            "kind": forecasts_mod.HORIZON_T,
            "hours": hours,
            "t_end": window.end_utc,
            "y_definition": {
                "ecart_pct": 1.0,
                "persistance_obs": 2,
                "max_gap_minutes": 90,
                "venues": ["defillama"],
                "convention": "close",
                "peg": 1.0,
            },
            "p": P_OBLIGATION_EVAL,
            "p_origin": (
                "documented prior — G6 §1 (SIGNED 2026-10-19): P(obligation) = 0.20 per EVAL window "
                "(unsourced working assumption, W2-D §E.2(b), kept for every EVAL window). "
                "No empirical count is computed on the EVAL series (that would read the target "
                "window, B7 §d.2.4); p is not produced by an LLM (G6 §2, B7 §a.5.5)."
            ),
            "observation_state_at_freeze": {
                "last_values": [],
                "notes": (
                    "Post-hoc instrumentation of a secondary EVAL window: written at the seal "
                    f"({EVAL_SEAL_AT_UTC}) on the series archived by the W3-C probe "
                    f"(retrieved_at 2026-10-15, sha256 {series_digest[:16]}…), whose bounds are the "
                    "registry window. Contamination acknowledged by the G3 registry "
                    "('likely contamination accepted' for eval-usd0pp-2025-01). No value is invented: "
                    "the resolution rule reads only the frozen series, gaps are reported and never filled."
                ),
            },
            "series_digest": series_digest,
            "series_relpath": USD0PP_SERIES_RELPATH,
        }
    ]


def write_eval_forecasts(target_dir: str, repo_root: Optional[str] = None) -> Dict:
    """Write ``forecasts_eval.jsonl`` / ``outcomes_eval.jsonl`` (chained).

    Same construction as the DEV block of :func:`build_all`: ``build_forecast`` →
    ``append_forecast`` → ``resolve_forecast`` → ``append_outcome`` under the
    freeze gate. Deterministic: a rebuild of the package reproduces the very
    same bytes (the ``frozen/`` inventory contract).
    """
    repo_root = repo_root or DEFAULT_REPO_ROOT
    windows_mod.verify_frozen_package(target_dir)
    specs = eval_forecast_specs(repo_root)
    series_by_relpath = {
        USD0PP_SERIES_RELPATH: corpus_mod.series_from_archived_series(
            os.path.join(repo_root, *USD0PP_SERIES_RELPATH.split("/"))),
    }

    forecasts_path = os.path.join(target_dir, EVAL_FORECASTS_NAME)
    outcomes_path = os.path.join(target_dir, EVAL_OUTCOMES_NAME)
    for path in (forecasts_path, outcomes_path):
        if os.path.exists(path):
            os.remove(path)

    written, resolved = [], []
    for spec in specs:
        record = forecasts_mod.build_forecast(
            forecast_id=spec["forecast_id"],
            run_id=EVAL_RUN_ID,
            episode_id=spec["episode_id"],
            set_label=spec["set"],
            persona=spec["persona"],
            statement=spec["statement"],
            resolution_rule_id=outcomes_mod.RULE_SUSTAINED_DEPEG
            if spec["y_definition"].get("ecart_pct") is not None
            else outcomes_mod.RULE_CALM_WINDOW,
            t_frozen_utc=spec["t_frozen"],
            resolve_not_before_utc=spec["resolve_not_before"],
            p=spec["p"],
            p_origin=spec["p_origin"],
            y_definition=spec["y_definition"],
            observation_state_at_freeze=spec["observation_state_at_freeze"],
            refs={"hypothesis_ids": [], "branch_ids": [], "observation_ids": []},
            signed_by=SIGNED_BY,
            horizon_kind=spec["kind"],
            horizon_hours=spec["hours"],
            t_end_utc=spec.get("t_end"),
        )
        record["p_origin"] = (
            record["p_origin"]
            + f" ; frozen series ({spec['series_relpath']}, sha256 {spec['series_digest']})"
        )
        record["sha256"] = forecasts_mod.record_hash(record)
        written.append(forecasts_mod.append_forecast(forecasts_path, record, frozen_dir=target_dir))

    for record, spec in zip(written, specs):
        outcome = outcomes_mod.resolve_forecast(
            record,
            series_by_relpath[spec["series_relpath"]],
            now_utc=EVAL_SEAL_AT_UTC,
            code_hash=windows_mod.sha256_file(os.path.join(repo_root, "src", "orvyren", "evaluation", "outcomes.py")),
        )
        resolved.append(outcomes_mod.append_outcome(outcomes_path, outcome, frozen_dir=target_dir))

    forecast_digest = windows_mod.sha256_file(forecasts_path)
    outcome_digest = windows_mod.sha256_file(outcomes_path)
    _write_text(os.path.join(target_dir, EVAL_FORECASTS_NAME + ".sha256"),
                f"{forecast_digest}  {EVAL_FORECASTS_NAME}\n")
    _write_text(os.path.join(target_dir, EVAL_OUTCOMES_NAME + ".sha256"),
                f"{outcome_digest}  {EVAL_OUTCOMES_NAME}\n")
    return {"forecasts": len(written), "outcomes": len(resolved),
            "forecasts_sha256": forecast_digest, "outcomes_sha256": outcome_digest,
            "ys": [outcome["y"] for outcome in resolved]}


def build_all(target_dir: str, repo_root: Optional[str] = None) -> Dict:
    """Construit tout `frozen/` dans ``target_dir`` (déterministe, hors-ligne)."""
    repo_root = repo_root or DEFAULT_REPO_ROOT
    os.makedirs(target_dir, exist_ok=True)

    usdc = load_usdc_hourly_series(repo_root)
    steth = load_steth_series(repo_root)

    # --- valeurs CALME calculées (G3) --------------------------------------
    usdc_temoin = outcomes_mod.calm_window_v1(usdc, "2023-02-15T00:00:00Z", "2023-02-18T00:00:00Z", tolerance_pct=0.5)
    steth_calme = outcomes_mod.calm_window_v1(steth, "2022-05-01T00:00:00Z", "2022-05-08T00:00:00Z", tolerance_pct=0.5)
    calm_values = {
        "usdc_temoin_max_dev_pct": usdc_temoin["observed"]["max_abs_deviation_pct"],
        "steth_calme_max_dev_pct": steth_calme["observed"]["max_abs_deviation_pct"],
    }

    # --- documents G1–G6 ----------------------------------------------------
    _write_text(os.path.join(target_dir, "G1_fonction_de_perte.md"), doc_g1(repo_root))
    _write_text(os.path.join(target_dir, "G2_comparateurs.md"), doc_g2(repo_root))
    _write_text(os.path.join(target_dir, "G3_fenetres.md"), doc_g3(repo_root, calm_values))
    _write_text(os.path.join(target_dir, "G4_seuils.md"), doc_g4(repo_root))
    _write_text(os.path.join(target_dir, "G5_plan_analyse.md"), doc_g5(repo_root))
    _write_text(os.path.join(target_dir, "G6_hypotheses_economiques.md"), doc_g6(repo_root))
    _write_text(os.path.join(target_dir, "G6_FEUILLE_DE_SIGNATURE.md"), doc_g6_signature(repo_root))

    manifests = {}
    manifests["G1"] = _write_manifest(target_dir, "G1", ["G1_fonction_de_perte.md"])
    manifests["G2"] = _write_manifest(target_dir, "G2", ["G2_comparateurs.md"])
    manifests["G3"] = _write_manifest(target_dir, "G3", ["G3_fenetres.md"])
    manifests["G4"] = _write_manifest(target_dir, "G4", ["G4_seuils.md"])
    manifests["G5"] = _write_manifest(target_dir, "G5", ["G5_plan_analyse.md"])
    manifests["G6"] = _write_manifest(
        target_dir, "G6", ["G6_hypotheses_economiques.md", "G6_FEUILLE_DE_SIGNATURE.md"]
    )

    # la porte de gel est active dès que les manifestes existent : les
    # prévisions et outcomes ci-dessous sont écrits SOUS cette porte.
    windows_mod.verify_frozen_package(target_dir)

    # --- prévisions DEV (chaînées) -----------------------------------------
    forecasts_path = os.path.join(target_dir, "forecasts_dev.jsonl")
    if os.path.exists(forecasts_path):
        os.remove(forecasts_path)
    specs = _forecast_specs(usdc, steth)
    series_by_key = {"usdc": usdc, "steth": steth}
    written = []
    for spec in specs:
        record = forecasts_mod.build_forecast(
            forecast_id=spec["forecast_id"],
            run_id=RUN_ID,
            episode_id=spec["episode_id"],
            set_label=spec["set"],
            persona=spec["persona"],
            statement=spec["statement"],
            resolution_rule_id=outcomes_mod.RULE_SUSTAINED_DEPEG
            if spec["y_definition"].get("ecart_pct") is not None
            else outcomes_mod.RULE_CALM_WINDOW,
            t_frozen_utc=spec["t_frozen"],
            resolve_not_before_utc=spec["resolve_not_before"],
            p=spec["counts"]["p"],
            p_origin=_origin(
                "empirical count of the DEV calibration windows with the same duration/grid, "
                "target window excluded (LOO) — B7 §a.4",
                spec["counts"],
            ),
            y_definition=spec["y_definition"],
            observation_state_at_freeze={
                "last_values": [],
                "notes": (
                    "DEV forecast pre-registered on already archived data (method demonstration; "
                    "contamination acknowledged, B7 §d.1). The observation state at t_frozen is carried "
                    "by the frozen corpus; no value after t_frozen is used by the resolution rule."
                ),
            },
            refs={"hypothesis_ids": [], "branch_ids": [], "observation_ids": []},
            signed_by=SIGNED_BY,
            horizon_kind=spec["kind"],
            horizon_hours=spec["hours"],
            t_end_utc=spec.get("t_end"),
        )
        record["p_origin"] = (
            record["p_origin"]
            + f" ; corpus figé ({USDC_CORPUS_RELPATH if spec['series_key'] == 'usdc' else STETH_EVIDENCE_RELPATH},"
            + f" sha256 {_hash(repo_root, USDC_CORPUS_RELPATH if spec['series_key'] == 'usdc' else STETH_EVIDENCE_RELPATH)[:16]}…)"
        )
        record["sha256"] = forecasts_mod.record_hash(record)
        written.append(forecasts_mod.append_forecast(forecasts_path, record, frozen_dir=target_dir))

    # --- outcomes (résolution déterministe, chaînée) ------------------------
    outcomes_path = os.path.join(target_dir, "outcomes_dev.jsonl")
    if os.path.exists(outcomes_path):
        os.remove(outcomes_path)
    resolved = []
    for record, spec in zip(written, specs):
        outcome = outcomes_mod.resolve_forecast(
            record,
            series_by_key[spec["series_key"]],
            now_utc=GEL_AT_UTC,
            code_hash=windows_mod.sha256_file(os.path.join(repo_root, "src", "orvyren", "evaluation", "outcomes.py")),
        )
        resolved.append(outcomes_mod.append_outcome(outcomes_path, outcome, frozen_dir=target_dir))

    # --- synthèse ȳ / Wilson (FORECASTS_DEV.md) ------------------------------
    # EVAL forecasts/outcomes of the instrumented windows — written by the same
    # builder so that `frozen/` stays byte-for-byte reproducible (no file may
    # live in frozen/ that build_all does not produce).
    eval_result = write_eval_forecasts(target_dir, repo_root)

    ys = [outcome["y"] for outcome in resolved]
    n = len(ys)
    ybar = sum(ys) / n
    k_ones = sum(ys)
    wilson_all = cal.wilson_interval(k_ones, n)
    quiet = [outcome for outcome, spec in zip(resolved, specs) if spec.get("sous_ensemble") == "absence_attendue"]
    quiet_k = sum(outcome["y"] for outcome in quiet)
    quiet_n = len(quiet)
    quiet_upper = (
        cal.wilson_upper_for_zero(quiet_n) if quiet_k == 0 else cal.wilson_interval(quiet_k, quiet_n)[1]
    )
    depeg_subset = [outcome for outcome, spec in zip(resolved, specs) if spec.get("sous_ensemble") == "depeg"]
    depeg_k = sum(outcome["y"] for outcome in depeg_subset)
    depeg_n = len(depeg_subset)

    lines = [
        "# Frozen DEV forecasts — detailed reading",
        "",
        f"**{n} forecasts frozen on {GEL_AT_UTC}**, chained by `prev_hash` in "
        "`frozen/forecasts_dev.jsonl`, resolved by the deterministic resolver "
        "(`frozen/outcomes_dev.jsonl`). **DEV** set exclusively: these forecasts "
        "demonstrate the **method** (falsifiability + resolution + scores), they claim "
        "**no** predictive performance — the 2022–2023 episodes are "
        "inside the training data of the 2026 models (B7 §d.1, DECLARED).",
        "",
        f"## Summary (N = {n}, cascade label: « {cal.verdict_for_n(n)} »)",
        "",
        f"* `ȳ` (DEV climatology) = **{ybar:.6f}** ({k_ones}/{n} forecasts resolved to 1) ;",
        f"* sustained-depeg proportion (`depeg` subset, {depeg_n} forecasts): "
        f"{depeg_k}/{depeg_n} ;",
        f"* proportion over the whole set: {k_ones}/{n}, Wilson 95 % CI = "
        f"[{wilson_all[0]:.4f} ; {wilson_all[1]:.4f}] ;",
        f"* `absence_attendue` subset ({quiet_n} forecasts: control windows + pre/post-crisis): "
        f"{quiet_k}/{quiet_n} observed depeg — Wilson upper bound = {quiet_upper:.4f} ;",
        f"* mandatory sentence (B7 §b.2): « {cal.PHRASE_ZERO_SUCCESS} » ; transposed here: "
        f"{quiet_k}/{quiet_n} does not mean a zero rate — a rate compatible with up to ≈ {quiet_upper*100:.1f} %.",
        "",
        f"`BS/REL/RES/UNC/ECE`: **not published in this file** — the official calibration report "
        "(`evidence/calibration_report_skeleton.md`) remains the N = 0 skeleton, and the cascade imposes "
        f"« {cal.verdict_for_n(n)} » as long as N < 30 (computable as soon as the harness publishes its scores).",
        "",
        "**Honesty observation on the `p` values**: the prior used is an LOO climatology count. "
        "Mechanically, excluding the target window removes crisis windows from the count of crisis "
        "forecasts: `p` can therefore be **lower in crisis than in calm** (e.g. h-crise 0,2437 against "
        "h-calme-1 0,2995). This is not a computation error, it is the limit of the prior — an estimator "
        "conditioned on the current state (rather than a global climatology) is an identified work item, outside v1.",
        "",
        "## Forecast details",
        "",
    ]
    for record, outcome, spec in zip(written, resolved, specs):
        lines += [
            f"### `{record['forecast_id']}` — {spec['cas']}",
            "",
            f"* **Statement**: {record['statement']}",
            f"* **Set**: {record['set']} · **persona**: {record['persona']} · **horizon**: "
            f"{record['horizon']['kind']} ({record['horizon']['hours']} h) · frozen: {record['horizon']['t_frozen_utc']}",
            f"* **p = {record['p']:.6f}** — origin: {record['p_origin']}",
            f"* **Resolution rule**: `{record['resolution_rule_id']}` · `resolve_not_before` = "
            f"{record['horizon']['resolve_not_before_utc']}",
            f"* **Resolution (deterministic)**: y = **{outcome['y']}** — "
            f"observed: {json.dumps(outcome['observed'], ensure_ascii=False)}",
            f"* **Provenance/hash**: sha256 `{record['sha256'][:32]}…` · prev_hash "
            f"`{record['prev_hash'][:16]}…` · outcome `{outcome['outcome_id']}`",
            "",
        ]
    lines += [
        "## What is NOT claimed",
        "",
        "* no superiority of agent A2 (the A0/A1/B0 harness is not built) ;",
        "* no calibration ('non-conclusive' at N < 30, 5-condition requirement at N ≥ 100) ;",
        "* the origin of each `p` is published with its counts (function `base_rate_loo`): "
        "the target window is excluded from the count, but the count remains a climatology prior "
        "— on crisis windows, a climatology prior mechanically underestimates risk (observation, not excuse).",
        "",
    ]
    _write_text(os.path.join(target_dir, "FORECASTS_DEV.md"), "\n".join(lines))

    # --- README + manifestes annexes ----------------------------------------
    forecast_digest = windows_mod.sha256_file(forecasts_path)
    outcome_digest = windows_mod.sha256_file(outcomes_path)
    _write_text(os.path.join(target_dir, "forecasts_dev.jsonl.sha256"), f"{forecast_digest}  forecasts_dev.jsonl\n")
    _write_text(os.path.join(target_dir, "outcomes_dev.jsonl.sha256"), f"{outcome_digest}  outcomes_dev.jsonl\n")
    _write_text(os.path.join(target_dir, "README.md"), doc_readme(manifests))
    # INDEX.md : index machine-readable du périmètre gelé (9 fichiers hashés).
    # Généré avec le paquet — tout fichier de frozen/ non recalculé est un
    # mismatch pour verify_frozen.py, l'index ne fait pas exception.
    _write_text(os.path.join(target_dir, "INDEX.md"), doc_index(repo_root))

    return {
        "forecasts": len(written),
        "outcomes": len(resolved),
        "ybar": ybar,
        "quiet_upper": quiet_upper,
        "hashes": manifests,
        "forecasts_sha256": forecast_digest,
        "outcomes_sha256": outcome_digest,
        "eval": eval_result,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Construit (ou recalcule) le paquet de gel frozen/.")
    parser.add_argument("--out", default=None, help="répertoire cible (défaut : <repo>/frozen)")
    parser.add_argument("--repo-root", default=None, help="racine du dépôt (défaut : parent de scripts/)")
    args = parser.parse_args(argv)
    repo_root = args.repo_root or DEFAULT_REPO_ROOT
    target = args.out or os.path.join(repo_root, "frozen")
    result = build_all(target, repo_root=repo_root)
    print(f"paquet de gel écrit dans {target}")
    print(f"  prévisions : {result['forecasts']} · outcomes : {result['outcomes']} · ȳ = {result['ybar']:.6f}")
    print(f"  forecasts_dev.jsonl sha256 : {result['forecasts_sha256']}")
    print(f"  outcomes_dev.jsonl  sha256 : {result['outcomes_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
