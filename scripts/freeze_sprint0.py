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

#: Date de gel v1 (Sprint 0). Constante du paquet : la reproductibilité
#: hors-ligne exige que l'horodatage d'écriture soit gelé, pas l'heure murale
#: du recalcul (l'heure réelle d'écriture n'est donc PAS portée par ces
#: artefacts ; elle est celle de la commande qui les recrée).
GEL_AT_UTC = "2026-10-16T00:00:00Z"
RUN_ID = "freeze-sprint0-2026-10-16"
SIGNED_BY = {"role": "gel-g6", "name": "<à signer — chef d'équipe>"}

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
        f"estimateur explicite — {label} : p = {counts['k_events']}/{counts['n_windows']} = "
        f"{counts['p']:.6f}"
    )
    return text + (f" ; {extra}" if extra else "")


# --------------------------------------------------------------------------- #
# Définition des prévisions DEV
# --------------------------------------------------------------------------- #


def _forecast_specs(usdc: Sequence[Tuple[str, float]], steth: Sequence[Tuple[str, float]]) -> List[Dict]:
    """Les 8 prévisions DEV, dans l'ordre d'écriture (chaînage déterministe)."""

    def usdc_h6(t_frozen, ident, cas, counts, sous_ensemble="depeg"):
        return {
            "forecast_id": ident,
            "episode_id": "usdc-2023-03",
            "set": "dev",
            "persona": "dao",
            "sous_ensemble": sous_ensemble,
            "statement": (
                "Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires "
                "consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen."
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
    specs.append(usdc_h6("2023-02-16T00:00:00Z", "dev-usdc-2023-03.h-calme-1", "Fenêtre témoin USDC, 16/02/2023 00:00Z (calme dans le sens « aucun dépeg soutenu »)", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-02-17T00:00:00Z", "2023-02-17T06:00:00Z", 90.0)
    specs.append(usdc_h6("2023-02-17T00:00:00Z", "dev-usdc-2023-03.h-calme-2", "Fenêtre témoin USDC, 17/02/2023 00:00Z", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-10T12:00:00Z", "2023-03-10T18:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-10T12:00:00Z", "dev-usdc-2023-03.h-pre-crise", "USDC, veille du dépeg (10/03/2023 12:00Z)", counts, sous_ensemble="absence_attendue"))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-11T04:00:00Z", "2023-03-11T10:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-11T04:00:00Z", "dev-usdc-2023-03.h-crise", "USDC, cœur de crise (11/03/2023 04:00Z)", counts))

    counts = base_rate_loo(usdc, 6.0, _depeg_event(usdc, 1.0, 2, 90), "2023-03-13T12:00:00Z", "2023-03-13T18:00:00Z", 90.0)
    specs.append(usdc_h6("2023-03-13T12:00:00Z", "dev-usdc-2023-03.h-post-crise", "USDC, retour vers la parité (13/03/2023 12:00Z)", counts, sous_ensemble="absence_attendue"))

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
                "La fenêtre 05/05 → 08/05/2022 tient le critère CALME gelé (max |1 − prix réalisable "
                "stETH| < 0,5 %) sur la série get_dy 1 stETH."
            ),
            "t_frozen": "2022-05-05T00:00:00Z",
            "resolve_not_before": "2022-05-08T00:00:00Z",
            "kind": "T",
            "hours": 72.0,
            "t_end": "2022-05-08T00:00:00Z",
            "series_key": "steth",
            "y_definition": {"tolerance_pct": 0.5, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, fenêtre calme (critère CALME gelé)",
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
                "La décote réalisable stETH (get_dy pour 1 stETH) dépasse 1 % sur ≥ 2 observations "
                "consécutives de la grille pendant les 7 jours suivant t_frozen."
            ),
            "t_frozen": "2022-05-12T00:00:00Z",
            "resolve_not_before": "2022-05-19T00:00:00Z",
            "kind": "T",
            "hours": 168.0,
            "t_end": "2022-05-19T00:00:00Z",
            "series_key": "steth",
            "y_definition": {"ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 1500, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, ouverture de la décote (13–21/05/2022)",
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
                "La décote réalisable stETH reste au-dessus de 1 % sur ≥ 2 observations horaires "
                "consécutives dans les 6 h suivant t_frozen."
            ),
            "t_frozen": "2022-06-13T00:00:00Z",
            "resolve_not_before": "2022-06-13T06:00:00Z",
            "kind": "H_class",
            "hours": 6.0,
            "series_key": "steth",
            "y_definition": {"ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "venues": ["curve_get_dy_1steth"], "convention": "realisable", "peg": 1.0},
            "counts": counts,
            "cas": "stETH, fenêtre horaire 10→17/06/2022 (gel des retraits Celsius)",
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
        "W_T(conserver)   = C + q · P_T\n"
        "W_T(céder x)     = C + x · P_exec(x, t_action) − k + (q − x) · P_T\n"
        "L(a)             = W_t0 − W_T(a)                    [USD, ou bp de W_t0]\n"
        "R(a)             = L(a) − min_{b ∈ F} L(b) ≥ 0     [USD]\n"
        "R⁻ / R⁺          = coûts du faux positif / du faux négatif vs A0 (publiés séparément)"
    )
    return f"""# G1 — Fonction de perte (gel v1)

**Statut : GELÉ v1** — {GEL_AT_UTC}. Source normative : W2-D §B.1 (formulation
corrigée), §B.6 (six tests), B7 §e.1/e.3 (métriques persona). Code gelé :
`src/orvyren/evaluation/loss.py` — sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','loss.py'))}`.

## 1. Formules gelées

```
{formulas}
```

## 2. Conventions de valorisation (jamais mélangées)

| Convention | Définition | Usage gelé |
|---|---|---|
| `terminale` | la position restante vaut `P_T` (prix réalisable en T) | desk : terminale + financement |
| `liquidation` | la position restante vaut le prix de liquidation mesuré à T (échelle de profondeur) | DAO (plus prudente, recommandation W2-D §(f) 3) |

Le code **refuse** (`ValuationError`) la convention `liquidation` sans échelle de
profondeur fournie : aucune conversion non mesurée ne se fait passer pour une mesure.

## 3. Famille d'actions faisables F et coût k

* `F` = fractions de q `{{0 ; 0,25 ; 0,5 ; 0,75 ; 1}}`, `x = 0` toujours inclus ;
  plafond de politique `x_max` appliqué par `min(x, x_max)` (démo : 100 USDC, FREEZE_V2 §E2) ;
* `k` = coûts explicites **non déjà inclus** dans `P_exec` (frais, gas, pontage, financement) ;
* `P_exec(x)` = prix moyen obtenu pour la taille x, issu de l'échelle de profondeur mesurée —
  jamais un prix d'écran. `Depth_ε` reste **à mesurer** (chantier W2-B §(f) 5) : NOT DONE.

## 4. Personas

* **DAO** — pas de re-entrée dans l'épisode ; perte évitée conditionnelle
  `E[perte] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR` (les deux facteurs publiés) ;
  seconde lecture en **jours de runway**, `opex_ref = 44 932 $/j` (G6).
* **desk** — re-entrée modélisée dans la même fenêtre : `ΔP&L = x·(P_exec − P_T) − k − financement` ;
  agrégats Sharpe/Sortino/MaxDD (R_f = 0 par convention crypto ; `None` quand non calculable).

## 5. Les six tests (W2-D §B.6) — doivent passer avant le gel

| # | Test | Attendu |
|---|---|---|
| T1 | Neutralité (P_exec = P_T, k = 0 ⇒ R = 0) | 0 exact (détecte le double comptage §B.2) |
| T2 | Invariance par translation | R inchangé à 1e-12 |
| T3 | Monotonie en coût | L et R croissants |
| T4 | Cohérence de signe (P_exec > P_T) | R(agir) = 0, R(ne rien faire) > 0 |
| T5 | Additivité de l'inventaire | linéaire en q et en x |
| T6 | Référence dégénérée (P_t = 1) | tous les regrets 0 ; action inutile = k |

Preuve exécutable : `tests/test_evaluation_loss.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_loss.py'))}` ; commande
`python -m pytest tests/test_evaluation_loss.py -q` (12 tests).

## 6. Ce qui n'est PAS gelé ici (NOT DONE, écrit tel quel)

* `Depth_ε` (profondeur d'exécution en crise) : non mesurée → plafond x_max utilisé et **noté** sur chaque action A1 ;
* `r_capital` (taux de financement desk) : aucune source — voir G6 ;
* le bug historique `q(1 − P_T)` de la formule antérieure (W2-D §B.2) est reproduit en test pour non-régression (écart affiché 20 contre écart réel 10).

## 7. Révision

Toute modification de ce fichier ou de `loss.py` après la première exécution
EVAL **invalide** l'évaluation (embargo de paramètres, B7 §d.2.1) : nouvelle
version datée + hash + entrée au journal des variantes.
"""


def doc_g2(repo_root: str) -> str:
    return f"""# G2 — Comparateurs (gel v1)

**Statut : GELÉ v1** — {GEL_AT_UTC}. Sources : B7 §e.1 (table + collision
d'étiquettes tranchée), W2-D §C.1. Code gelé : `src/orvyren/evaluation/comparators.py` —
sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','comparators.py'))}`.

## 1. Étiquettes gelées (la collision R3/W2-D est tranchée)

| Code | Système | Définition opérationnelle | Coût |
|---|---|---|---|
| **A0** | NO-ACTION | ne rien faire sur toute la fenêtre | 0 |
| **A1** | Règle de seuil | décote D ≥ 50 bp pendant 15 min → réduction bornée x* = min(x_max, Depth_ε, x_seuil) | ~0 |
| **A2** | Agent ORVYREN | corpus → graphe → hypothèses → branche → critique → politique bornée (rejeu journal sinon archive k=3) | plafonné, mesuré |
| **B0** | Placebo apparié | mêmes nombre et tailles d'actions que A2, horodatages tirés uniformément sur la grille horaire, M ≥ 200, graine fixée | ~0 |
| **AX0** | Règle gelée du dépôt (ex-« A0 » de R3) | 0,99 × 2 obs consécutives → réduction de 100 USDC ; déléguée à `decision/baseline.py` | ~0 |
| **O** | Oracle ex post faisable | `min_{{b ∈ F}} L(b)` avec la fonction de perte gelée — borne inférieure du regret, pas une vérité terrain | hors ligne |

La règle gelée du dépôt s'écrit **AX0** dans tous les rapports du concours (l'étiquette
« A0-code » est interdite : sans cette résolution, « A0 a fait mieux que A0 » était écrit).

## 2. Paramètres gelés

* A1 : `min_discount_bp = 50`, `persistence_minutes = 15` (soit, sur grille horaire, **deux
  lectures consécutives**, gap ≤ 90 min ; un épisode = un seul déclenchement) ;
* B0 : `seed = {20261016}`, `M ≥ 200`, grille horaire, tirages **reproductibles** (même graine → mêmes horodatages) ;
* plafond d'action démo `x_max = 100 USDC` (FREEZE_V2 §E2 ; repris de
  `evidence/decision_usdc-2023-03.json`).

## 3. Phrases pré-écrites (gelées AVANT exécution, B7 §e.1)

> Si A2 ne bat pas B0, la valeur du système n'est pas dans le **choix du moment** — écrit tel quel.
>
> Si A2 ne bat pas A1, la valeur du système n'est pas dans la **délibération** — écrit tel quel.

## 4. Vérifications exécutables

`tests/test_evaluation_comparators.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_comparators.py'))}` :
A0 = 0 action ; A1 déclenche/un-seul-signal/trou casse la contiguïté ; **AX0 reproduit
`evidence/baseline_report.json`** (2 signaux fenêtre principale, 0 sur la fenêtre témoin) ;
B0 reproductible et M ≥ 200 exigé ; oracle = membre de F.

## 5. NOT DONE

* A2 : code produit par les blocs A–E (agents, graphe, politique) — hors Sprint 0 ; les clés API
  d'équipe restent un bloquant du mode `REPLAY-ARCHIVE` (B7 §0.11) ;
* `Depth_ε` et `x_seuil` d'A1 : non mesurés → plafond x_max, note de substitution sur chaque action.
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
    return f"""# G3 — Fenêtres DEV/EVAL, embargos (gel v1)

**Statut : GELÉ v1 (propositions ouvertes marquées NOT DONE)** — {GEL_AT_UTC}.
Sources : B7 §d.1/§d.2, FREEZE_V2 §7, DOC2 §5.8.4. Code gelé :
`src/orvyren/evaluation/windows.py` — sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','windows.py'))}`.

## 1. Registre — jeu DÉVELOPPEMENT

| Fenêtre | Type | Bornes UTC | Sources |
|---|---|---|---|
{dev_rows}

## 2. Registre — jeu ÉVALUATION

| Fenêtre | Type | Bornes UTC | Sources |
|---|---|---|---|
{eval_rows}

## 3. Critère CALME — application mécanique (le résultat s'écrit, il ne s'ajuste pas)

Critère gelé (B7 §d.1) : `max|P_t − 1| < 0,5 %` sur toute la fenêtre ; échec → reclassée STRESS.

* fenêtre témoin USDC 15–18/02/2023 : écart maximal mesuré **{calm_values['usdc_temoin_max_dev_pct']:.6f} %** ≥ 0,5 % → **reclassée STRESS** (mais 0 dépeg soutenu : la règle AX0 n'y produit aucun signal, cf. `evidence/baseline_report.json`) ;
* fenêtre calme stETH 01–08/05/2022 : écart maximal mesuré **{calm_values['steth_calme_max_dev_pct']:.6f} %** < 0,5 % → **CALME confirmée** (mesure sur la série de décote réalisable get_dy).

## 4. NOT DONE — fenêtres non dérivables (jamais inventées)

| Fenêtre | Statut | Motif |
|---|---|---|
{pending_rows}

## 5. Les quatre embargos (vérificateurs dans `windows.py`)

1. **Paramètres** — aucune constante de G1–G6 modifiable après la première exécution EVAL ; toute
   modification invalide l'évaluation (nouvelle version datée + hash + journal des variantes).
2. **Données (24 h)** — la bande `[début EVAL − 24 h, début EVAL]` est retirée du DEV
   (`data_embargo_violations`).
3. **Inspection** — avant le gel, aucune inspection des fenêtres EVAL au-delà du publié ;
   après la première exécution, le jeu est brûlé.
4. **Calibration croisée** — les mois de calibration des seuils ne peuvent chevaucher une
   fenêtre CALME EVAL (`cross_calibration_violations`) ; sans cette règle, la calibration
   « voit » le jeu d'évaluation.

## 6. Porte de gel (vérification mécanique, B7 §d.2.5)

* `verify_frozen_package(frozen_dir)` : `G1..G6.sha256` présents, lisibles, concordants — sinon **refus** ;
* `eval_run_gate(frozen_dir, lock_path, force)` : refus de la 2ᵉ exécution EVAL sans `--force` ;
  avec `--force`, mention obligatoire : « évaluation ré-exécutée (invalide pour la revendication) » ;
* le script d'évaluation EVAL doit refuser d'écrire si une fenêtre CALME EVAL chevauche la
  période de calibration déclarée.

## 7. Ce qui reste ouvert (écrit, non bloquant)

Liste exacte des fenêtres CALME EVAL 2025–2026 (B7 Q6) et fenêtres calmes DEV restantes
(R3 §C.8) : dépendent d'un chantier de collecte — NOT DONE assumé.
"""


def doc_g4(repo_root: str) -> str:
    return f"""# G4 — Seuils par persona (gel v1, statut PROPOSÉ)

**Statut : PROPOSÉ — à valider avant la première exécution EVAL** — {GEL_AT_UTC}.
Sources : W2-D §C.4.1 (DAO), §C.4.2 (desk), B7 §e.3/e.4 (métriques). Les valeurs
ci-dessous sont **reprises telles quelles** des documents sources, qui les
marquent explicitement « propositions à valider, pas des faits ».

## 1. Persona DAO (trésorerie)

| Code | Critère | Formulation | Valeur proposée |
|---|---|---|---|
| SD1 | Perte évitée matérielle | `(L(A0) − L(A2)) / q` en % de l'exposition, conditionnellement à l'obligation ; second affichage en jours de runway | ≥ 5 % |
| SD2 | Friction maîtrisée | coût cumulé de A2 sur fenêtres CALME | ≤ 10 % de la perte évitée de crise |
| SD3 | Anticipation | antériorité vs point bas du prix réalisable ; délai de réaction | ≥ 6 h sur ≥ 1 épisode EVAL ; ≤ 60 min |
| SD4 | Supériorité | `R̄(A2) < R̄(A1)` et `< R̄(B0)`, avec intervalles, R⁻/R⁺ séparés | strictement inférieur |
| SD5 | Traçabilité | provenance + hash sur 100 % des actions ; 0 action hors enveloppe | 100 % / 0 |
| SD6 | Honnêteté | « non conclusionnel » partout où la puissance manque ; perte évitée publiée `P × conditionnel` | présent/absent |

## 2. Persona desk (P&L)

| Code | Critère | Formulation | Valeur proposée |
|---|---|---|---|
| ST1 | P&L net cumulé | tous coûts inclus (frais, slippage mesuré, financement) + intervalle bootstrap par blocs | > 0 |
| ST2 | Qualité d'exécution | slippage réalisé vs échelle `get_dy` ; taille ≤ Depth_100bp | ≤ 30 bp en stress |
| ST3 | Risque borné | MaxDD de la série de décisions sur le capital alloué | ≤ 20 % par épisode |
| ST4 | Risque ajusté | Sharpe/Sortino + DSR corrigé du nombre de variantes | borne basse d'IC > 0 sinon « non conclusionnel » |
| ST5 | Supériorité | `ΔP&L(A2) > ΔP&L(A1)` et `> ΔP&L(B0)` avec intervalles | strictement supérieur |
| ST6 | Asymétrie déclarée | agent décrit comme un put ; scénarios `p_s` publiés | présent/absent |

## 3. Anti-optimisme commun (dispositifs obligatoires)

B0 (M ≥ 200, distribution complète) · fenêtres CALME obligatoires dans les deux jeux ·
`ȳ` publié partout · Wilson sur toute proportion · bootstrap par blocs (6–12 h, 10 000
réplications, graine fixée) · DSR/journal des variantes · R⁻/R⁺ séparés + table de
contingence · mention de contamination · « ce que nous ne revendiquons pas » ·
**un scalaire est interdit** (vecteur de métriques + axes non mesurés déclarés).

## 4. NOT DONE

Les seuils SD/ST ne sont **pas encore lus par du code** (le harnais §e.6 items 6–7 n'est pas
construit) : ce document les gèle en tant que déclaration, la vérification exécutable
viendra avec `harness.py`. Toute modification après la première exécution EVAL invalide
l'évaluation (embargo de paramètres).
"""


def doc_g5(repo_root: str) -> str:
    return f"""# G5 — Plan d'analyse (gel v1)

**Statut : GELÉ v1** — {GEL_AT_UTC}. Sources : B7 §b.1–b.4, §e.2–e.5, DOC2 §5.8.2.
Code gelé : `calibration.py` sha256
`{_hash(repo_root, os.path.join('src','orvyren','evaluation','calibration.py'))}`,
`forecasts.py` sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','forecasts.py'))}`,
`outcomes.py` sha256 `{_hash(repo_root, os.path.join('src','orvyren','evaluation','outcomes.py'))}`.

## 1. Métriques publiées (C1–C7) et formules

| Code | Métrique | Formule |
|---|---|---|
| C1 | Score de Brier | `BS = (1/N) Σ (p_t − y_t)²` |
| C2 | Décomposition de Murphy | `BS = REL − RES + UNC`, évaluée sur les **mêmes intervalles que l'ECE** (identité exacte, testée) |
| C3 | ECE | `Σ_b (n_b/N)·|acc_b − conf_b|`, **10 intervalles fixes** `[b/10, (b+1)/10)`, gelés d'avance |
| C4 | Courbe de fiabilité | par intervalle : `n_b`, `conf_b`, `acc_b`, IC de Wilson (intervalles vides affichés) |
| C5 | Wilson | `z = 1,959964` ; borne sup. de 0/n = `z²/(n+z²)` |
| C6 | Bootstrap par blocs | circulaire, blocs 6–12 h, 10 000 réplications, **graine fixée** ({20261016}), percentile 2,5–97,5 |
| C7 | Compétence | `BSS = 1 − BS / (ȳ(1−ȳ))` ; `None` si climatologie dégénérée |

Vecteur KAT (test unitaire de référence, tolérance 1e-12) : `p = [0,2×5 ; 0,8×5]`,
`y = [0,0,0,0,0, 1,1,0,1,1]` → BS 0,100 ; REL 0,020 ; RES 0,160 ; UNC 0,240 ; ECE 0,100 ; ȳ 0,400.

## 2. Cascade « quand peut-on dire calibré » (applicée mécaniquement)

| N (prévisions gelées résolues) | Ce qui est publié | Libellé |
|---|---|---|
| N < 5 | rien | « NON CALCULÉ — N insuffisant » (seuil D11) |
| 5 ≤ N < 30 | BS, REL, RES, UNC, ȳ, liste ; ECE **sans** revendication | « non conclusionnel » |
| 30 ≤ N < 100 | + IC bootstrap, courbe de fiabilité + Wilson par intervalle | « non conclusionnel » |
| N ≥ 100 | tout + BSS avec borne basse | revendication possible **sous les 5 conditions** |

**Les 5 conditions pour écrire « calibré »** : N ≥ 100 hors échantillon ; ECE ≤ 0,05 avec borne
haute d'IC ≤ 0,08 ; pas de déviation systématique (test du signe, `max_b |acc_b − conf_b| ≤ 0,10`) ;
borne basse de l'IC de BSS > 0 ; ≥ 2 familles d'épisodes disjointes + déclaration de non-réglage.
Avec N = 5–12, l'état par défaut est « non conclusionnel » — **publié tel quel**.

## 3. Statistiques de comparaison

* Wilson sur **toutes** les proportions ; phrase obligatoire pour un « 0 échec » :
  « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » ;
* McNemar **exact** sur les paires discordantes (`p = 2·Σ C(n,k)/2^n`, borné à 1 ; KAT 6-0 → 0,03125) ;
* bootstrap par blocs (C6) sur toute statistique de série — jamais d'IC i.i.d. ;
* placebo B0 : distribution complète + percentile de A2.

## 4. Structure imposée du rapport (B7 §b.4, 8 sections)

1. périmètre et hashes (jeu, épisodes, N, période, code_hash, data_hash, liste des forecast_id) ;
2. tableau global (N, ȳ, BS + IC, REL/RES/UNC, ECE, BSS, verdict) ;
3. courbe de fiabilité (une ligne par intervalle) ;
4. décomposition par famille (persona, type, épisode — **N affiché par cellule**) ;
5. annexe des prévisions (`forecast_id | p | y | (p−y)² | horizon | résolveur`) ;
6. anomalies et corrections (`supersedes`, non résolues, quarantaines) ;
7. limites en toutes lettres (contamination, non-échangeabilité, tailles) ;
8. verdict en langage contrôlé (jamais « calibré » sans les 5 conditions).

## 5. Règles de langage gelées

Tout tableau porte son `N` et sa validité ; ne jamais fusionner DEV et EVAL ; ne jamais
moyenner R⁻ et R⁺ ; aucun score agrégé unique ; un rapport sans hash n'est pas vérifiable ;
« calibré » est un mot contrôlé (5 conditions), en dessous c'est « non établi ».

## 6. Vérifications exécutables

`tests/test_evaluation_calibration.py` — sha256
`{_hash(repo_root, os.path.join('tests','test_evaluation_calibration.py'))}` : KAT exacts,
Wilson vs table raw_b7 (± 0,001), bootstrap déterministe (2 exécutions identiques), cascade.
"""


def doc_g6(repo_root: str) -> str:
    return f"""# G6 — Hypothèses économiques (gel v1, statut PROPOSÉ — en attente de signature)

**Statut : PROPOSÉ — non signé.** {GEL_AT_UTC}. Tant que la feuille
`G6_FEUILLE_DE_SIGNATURE.md` n'est pas signée, ces hypothèses restent des
propositions : aucune revendication EVAL ne peut s'appuyer dessus.
Sources : W2-D §B.3/B.4, §E.2, §(f) 1–7 et 11–12 ; B7 §b.5, §e.3/e.4, Q1 ; FREEZE_V2 §C7.

## 1. Paramètres et valeurs proposées

| Paramètre | Valeur proposée | Statut | Source / justification |
|---|---|---|---|
| `opex_ref` (jours de runway) | **44 932 $/jour** | PROPOSÉ (référence externe déclarée) | ENS IPS 6.46 : 16,4 M$/an de charges 2025 ; conversion calculée 16 400 000 ÷ 365 (W2-D §A.1.1, §E.1 ; B7 Q13) |
| `P(obligation)` — fenêtre USDC DEV (exemple de calcul) | **0,20** | HYPOTHÈSE non sourcée | valeur de travail de W2-D §E.2(b) — « hypothèse à figer, non sourcée » ; aucune fréquence publique de ventes forcées n'existe |
| `P(obligation)` — fenêtres EVAL | **NOT DONE — à proposer par le signataire** | à signer | aucune source publique (W2-D §Non trouvé 6) ; le signataire doit fournir une justification écrite par fenêtre |
| Scénarios desk `p_s` | **4 scénarios** : (i) réalisé, (ii) non-rétablissement à 48 h, (iii) guérison lente (5 j), (iv) venue unique contrainte (0,80526 — contrefactuel) | liste PROPOSÉE ; **probabilités NOT DONE** | W2-D §(f) 7 ; aucune distribution publique de scénarios de dépeg (W2-D §Non trouvé 4) : les `p_s` seront des hypothèses signées, publiées avec le P&L |
| `r_capital` (taux de financement desk) | **NOT DONE — à proposer** | à signer | aucune source trouvée (B7 Q16) ; les deux P&L (hors et avec financement) sont publiés pour que la différence reste visible (W2-D §(f) 11) |
| Coût d'aller-retour desk (illustratif) | 20 bp (`k = 4 000 $` sur 2 M$) | PROPOSÉ (illustration) | W2-D §E.3 — « hypothétique, à mesurer réellement » |

## 2. Règles attachées (gelées)

* la perte évitée n'est **jamais** publiée inconditionnellement :
  `E[perte évitée] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR`, les deux facteurs visibles ;
* toute modification de `P(obligation)`, des `p_s` ou de `r_capital` exige une **re-signature nommée**
  + justification + sensibilité publiée (B7 §f.2) ;
* une prévision `p` ne peut **jamais** être produite par un LLM (interdit par construction, B7 §a.5.5).

## 3. Sensibilité exigée

Pour chaque fenêtre où `P(obligation)` entre dans un verdict, publier la sensibilité du
signe de `E[perte évitée]` à `P(obligation)` : la valeur de bascule est calculable
exactement (`P* = coût_AR / (perte|oblig + coût_AR)`) — elle doit figurer au dossier.
"""


def doc_g6_signature(repo_root: str) -> str:
    return f"""# G6 — Feuille de signature des hypothèses économiques

**Statut global : PROPOSÉ — en attente de signature.** {GEL_AT_UTC}.
Protocole : FREEZE_V2 §C7 (« G6 signé par le chef d'équipe (défaut) + sensibilité publiée »).

Instructions : le signataire **coche** chaque paramètre qu'il valide, remplace les valeurs
marquées `NOT DONE` par ses propres valeurs (avec justification écrite), puis date et signe.
Tant que la feuille n'est pas signée, aucun résultat EVAL ne peut être revendiqué.

## Paramètres d'hypothèses économiques

| # | Paramètre | Valeur PROPOSÉE | Source de la proposition | COCHER |
|---|---|---|---|---|
| 1 | `opex_ref` (jours de runway) | 44 932 $/jour | ENS IPS 6.46 : 16,4 M$/an ÷ 365 (W2-D §A.1.1/E.1) | ☐ validé ☐ modifié → …………… |
| 2 | `P(obligation)` — exemple DEV USDC | 0,20 | valeur de travail de W2-D §E.2(b), explicitement non sourcée | ☐ validé ☐ modifié → …………… |
| 3 | `P(obligation)` — par fenêtre EVAL | NOT DONE (à fournir) | aucune source publique (W2-D §Non trouvé 6) | ☐ fourni ci-dessous |
| 4 | Scénarios desk (liste) | réalisé · non-rétablissement 48 h · guérison lente 5 j · venue unique contrainte 0,80526 | W2-D §(f) 7 | ☐ validé ☐ modifié → …………… |
| 5 | `p_s` (probabilités des scénarios) | NOT DONE (à fournir) | aucune distribution publique (W2-D §Non trouvé 4) | ☐ fourni ci-dessous |
| 6 | `r_capital` (financement desk) | NOT DONE (à fournir) | B7 Q16 — non trouvé | ☐ fourni ci-dessous |
| 7 | Coût d'aller-retour (illustration desk) | 20 bp | W2-D §E.3 (« hypothétique, à mesurer ») | ☐ validé ☐ modifié → …………… |

## Valeurs à fournir (le cas échéant)

* `P(obligation)` par fenêtre EVAL (justification écrite par fenêtre) :
* `p_s` des scénarios desk (avec sensibilité) :
* `r_capital` (source ou hypothèse écrite) :

## Signatures

| Rôle | Nom | Date (UTC) | Signature / hash du commit de signature |
|---|---|---|---|
| Chef d'équipe (défaut, FREEZE_V2 §C7) | | | |
| Témoin (optionnel) | | | |

**Rappel d'embargo** : après la première exécution EVAL, toute modification de ces
paramètres **invalide** l'évaluation (re-étiquetage obligatoire) — pas « affaiblit » (B7 §d.2.1).
"""


def doc_readme(frozen_hashes: Dict[str, str]) -> str:
    rows = "\n".join(f"| `{name}.sha256` | `{digest}` |" for name, digest in sorted(frozen_hashes.items()))
    return f"""# `frozen/` — paquet de gel « Sprint 0 » (G1–G6 + prévisions DEV)

**Date de gel : {GEL_AT_UTC}** · Généré par `scripts/freeze_sprint0.py` · Vérifié par
`scripts/verify_frozen.py`.

## Contenu

| Fichier | Rôle |
|---|---|
| `G1_fonction_de_perte.md` | G1 — formules de perte, conventions, six tests |
| `G2_comparateurs.md` | G2 — A0/A1/A2/B0/AX0/O, paramètres, phrases gelées |
| `G3_fenetres.md` | G3 — registre DEV/EVAL, embargos, porte de gel |
| `G4_seuils.md` | G4 — seuils persona (PROPOSÉ) |
| `G5_plan_analyse.md` | G5 — métriques, cascade, rapport |
| `G6_hypotheses_economiques.md` | G6 — hypothèses économiques (PROPOSÉ) |
| `G6_FEUILLE_DE_SIGNATURE.md` | Feuille de signature du chef d'équipe |
| `Gx.sha256` | Manifestes sha256sum des documents ci-dessus |
| `forecasts_dev.jsonl` | Prévisions DEV gelées, chaînées par `prev_hash` |
| `outcomes_dev.jsonl` | Résolutions déterministes, chaînées |
| `FORECASTS_DEV.md` | Lecture FR des prévisions (provenance, ȳ, Wilson) |
| `README.md` | Ce fichier (non auto-référencé : voir note) |

## Vérifier (2 minutes, hors-ligne)

```bash
# 1. Empreintes des manifestes de gel
python scripts/verify_frozen.py          # tout : sha256 + chaînes + recalcul complet
cd frozen && sha256sum -c G1.sha256      # (idem G2..G6 ; GNU coreutils)
# 2. Recalcul intégral du paquet dans un répertoire temporaire et comparaison octet à octet
python scripts/freeze_sprint0.py --out /tmp/frozen_recalc
```

## Ce qui est gelé, ce qui ne l'est pas

* **GELÉ** : les six documents, leurs empreintes, les 9 prévisions DEV (hash chaîné) et leurs
  résolutions déterministes ;
* **PROPOSÉ (en attente de signature)** : G4 (seuils persona) et G6 (hypothèses économiques) —
  marqués tels quels ; l'évaluation EVAL ne peut pas être revendiquée avant signature ;
* **NOT DONE (jamais inventé)** : fenêtres CALME EVAL 2025–2026 (B7 Q6), `Depth_ε`, `r_capital`,
  `P(obligation)` EVAL, `p_s` desk — voir `G3_fenetres.md` §4 et `G6` §1.

## Empreintes des manifestes (recopiables)

| Manifeste | sha256 |
|---|---|
{rows}

*Note : `README.md` et `FORECASTS_DEV.md` ne figurent pas dans les manifestes Gx (ils ne sont pas
des documents gelés au sens du protocole) ; leurs empreintes sont vérifiées par `verify_frozen.py`
lors du recalcul octet à octet.*

## Attention — quand régénérer

Les documents G1, G2, G3, G5 portent les **empreintes du code** (`loss.py`, `comparators.py`,
`windows.py`, `calibration.py`, `forecasts.py`, `outcomes.py`) : toute modification de ces
fichiers **oblige à régénérer le paquet** (`python scripts/freeze_sprint0.py`), sinon
`verify_frozen.py` signale l'écart — c'est voulu (un gel qui ne correspond plus au code
n'est plus un gel). Après la première exécution EVAL, modifier quoi que ce soit dans G1–G6
**invalide** l'évaluation (re-étiquetage obligatoire).
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
                "comptage empirique des fenêtres de calibration DEV de même durée/grille, "
                "fenêtre cible exclue (LOO) — B7 §a.4",
                spec["counts"],
            ),
            y_definition=spec["y_definition"],
            observation_state_at_freeze={
                "last_values": [],
                "notes": (
                    "Prévision DEV pré-enregistrée sur données déjà archivées (démonstration de méthode ; "
                    "contamination assumée, B7 §d.1). L'état d'observation à t_frozen est porté par le corpus figé ; "
                    "aucune valeur postérieure à t_frozen n'est utilisée par la règle de résolution."
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
        "# Prévisions DEV gelées — lecture détaillée (FR)",
        "",
        f"**{n} prévisions gelées le {GEL_AT_UTC}**, chaînées par `prev_hash` dans "
        "`frozen/forecasts_dev.jsonl`, résolues par le résolveur déterministe "
        "(`frozen/outcomes_dev.jsonl`). Jeu **DEV** exclusivement : ces prévisions "
        "démontrent la **méthode** (falsifiabilité + résolution + scores), elles ne "
        "revendiquent **aucune** performance prédictive — les épisodes 2022–2023 sont "
        "dans les données d'entraînement des modèles 2026 (B7 §d.1, DECLARÉ).",
        "",
        f"## Synthèse (N = {n}, libellé de la cascade : « {cal.verdict_for_n(n)} »)",
        "",
        f"* `ȳ` (climatologie DEV) = **{ybar:.6f}** ({k_ones}/{n} prévisions résolues à 1) ;",
        f"* proportion de dépeg soutenu (sous-ensemble `depeg`, {depeg_n} prévisions) : "
        f"{depeg_k}/{depeg_n} ;",
        f"* proportion sur l'ensemble : {k_ones}/{n}, IC de Wilson 95 % = "
        f"[{wilson_all[0]:.4f} ; {wilson_all[1]:.4f}] ;",
        f"* sous-ensemble `absence_attendue` ({quiet_n} prévisions : fenêtres témoin + pré/post-crise) : "
        f"{quiet_k}/{quiet_n} dépeg observé — borne supérieure de Wilson = {quiet_upper:.4f} ;",
        f"* phrase obligatoire (B7 §b.2) : « {cal.PHRASE_ZERO_SUCCESS} » ; transposée ici : "
        f"{quiet_k}/{quiet_n} ne signifie pas taux nul — taux compatible avec jusqu'à ≈ {quiet_upper*100:.1f} %.",
        "",
        f"`BS/REL/RES/UNC/ECE` : **non publiés dans ce fichier** — le rapport de calibration officiel "
        "(`evidence/calibration_report_skeleton.md`) reste le squelette N = 0, et la cascade impose "
        f"« {cal.verdict_for_n(n)} » tant que N < 30 (sera calculable dès que le harnais publiera ses scores).",
        "",
        "**Constat d'honnêteté sur les `p`** : le prior employé est un comptage de climatologie LOO. "
        "Mécaniquement, exclure la fenêtre cible retire des fenêtres de crise du comptage des prévisions "
        "de crise : `p` peut donc être **plus bas en crise qu'en calme** (ex. h-crise 0,2437 contre "
        "h-calme-1 0,2995). Ce n'est pas une erreur de calcul, c'est la limite du prior — un estimateur "
        "conditionnel à l'état courant (et non une climatologie globale) est un chantier identifié, hors v1.",
        "",
        "## Détail des prévisions",
        "",
    ]
    for record, outcome, spec in zip(written, resolved, specs):
        lines += [
            f"### `{record['forecast_id']}` — {spec['cas']}",
            "",
            f"* **Énoncé** : {record['statement']}",
            f"* **Jeu** : {record['set']} · **persona** : {record['persona']} · **horizon** : "
            f"{record['horizon']['kind']} ({record['horizon']['hours']} h) · gelée : {record['horizon']['t_frozen_utc']}",
            f"* **p = {record['p']:.6f}** — origine : {record['p_origin']}",
            f"* **Règle de résolution** : `{record['resolution_rule_id']}` · `resolve_not_before` = "
            f"{record['horizon']['resolve_not_before_utc']}",
            f"* **Résolution (déterministe)** : y = **{outcome['y']}** — "
            f"observé : {json.dumps(outcome['observed'], ensure_ascii=False)}",
            f"* **Provenance/hash** : sha256 `{record['sha256'][:32]}…` · prev_hash "
            f"`{record['prev_hash'][:16]}…` · outcome `{outcome['outcome_id']}`",
            "",
        ]
    lines += [
        "## Ce qui n'est PAS revendiqué",
        "",
        "* aucune supériorité de l'agent A2 (le harnais A0/A1/B0 n'est pas construit) ;",
        "* aucune calibration (« non conclusionnel » à N < 30, exigence des 5 conditions à N ≥ 100) ;",
        "* l'origine de chaque `p` est publiée avec ses effectifs (fonction `base_rate_loo`) : "
        "la fenêtre cible est exclue du comptage, mais le comptage reste un prior de climatologie "
        "— sur des fenêtres de crise, un prior de climatologie sous-estime mécaniquement le risque (constat, pas excuse).",
        "",
    ]
    _write_text(os.path.join(target_dir, "FORECASTS_DEV.md"), "\n".join(lines))

    # --- README + manifestes annexes ----------------------------------------
    forecast_digest = windows_mod.sha256_file(forecasts_path)
    outcome_digest = windows_mod.sha256_file(outcomes_path)
    _write_text(os.path.join(target_dir, "forecasts_dev.jsonl.sha256"), f"{forecast_digest}  forecasts_dev.jsonl\n")
    _write_text(os.path.join(target_dir, "outcomes_dev.jsonl.sha256"), f"{outcome_digest}  outcomes_dev.jsonl\n")
    _write_text(os.path.join(target_dir, "README.md"), doc_readme(manifests))

    return {
        "forecasts": len(written),
        "outcomes": len(resolved),
        "ybar": ybar,
        "quiet_upper": quiet_upper,
        "hashes": manifests,
        "forecasts_sha256": forecast_digest,
        "outcomes_sha256": outcome_digest,
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
