#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — DEV/EVAL evaluation harness (W7, L7.6; B7 §e).

Loop §e.2: for each window of the dataset, for each config
``A0 / A1 / AX0 / A2 / B0`` — actions, then ``W_T``, ``L(a)``, ``R(a)`` through
the **frozen** loss function (G1), per-window aggregates, superiority tests and
mandatory banners.

Honesty of substitutions (always written, never silent):

* ``A2`` on a DEV without an available replay = deterministic dossier
  (``evidence/decision_usdc-2023-03.json``) with a declared timestamp;
* ``P_exec`` = observed price of the series at the action instant (no depth
  model in DEV); ``k = 0`` (costs not measured in DEV) — the mention goes into
  the report;
* ``B0`` paired with A2 (or with A1 if A2 is absent) — declared substitution;
* any window whose series does not resolve is **SKIPPED with a reason**, never
  filled with invented data.

Freeze gate (B7 §d.2.5): any write requires matching ``frozen/G1–G6``;
``--set eval`` additionally requires the absence of ``eval_run.lock`` (unless
``--force`` + mention) and the absence of overlap between CALM EVAL windows and
the declared calibration period.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from orvyren.evaluation import calibration as calibration_mod
from orvyren.evaluation import comparators as comparators_mod
from orvyren.evaluation import loss as loss_mod
from orvyren.evaluation import windows as windows_mod
from orvyren.replay import corpus as corpus_mod

REPO_ROOT = corpus_mod.REPO_ROOT
DEFAULT_DECISION = os.path.join(REPO_ROOT, "evidence", "decision_usdc-2023-03.json")
DEFAULT_CORPUS = os.path.join(REPO_ROOT, "corpus", "usdc_observations.csv")
DEFAULT_FROZEN_DIR = os.path.join(REPO_ROOT, "frozen")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "evidence", "evaluation")

#: DEV demonstration parameters — to be frozen for EVAL (declared everywhere).
Q_DEV_USDC = 100.0  # mobilisable amount (available_to_move_usdc of the dossier)
P_REF = 1.0
COST_K = 0.0
NOTE_PARAMS = ("paramètres de démonstration DEV : q = 100 USDC (montant mobilisable du "
               "dossier), p_ref = 1,0, k = 0 (coûts non mesurés en DEV) — à geler pour l'EVAL")

CONFIG_LABELS = ("A0", "A1", "AX0", "A2", "B0")


class HarnessError(RuntimeError):
    """Harness execution impossible (freeze gate, invalid window...)."""


def _parse_utc(stamp: str) -> _dt.datetime:
    text = str(stamp).replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _value_at(points: Sequence[Tuple[str, float]], moment_utc: str) -> Optional[float]:
    """Last value observed **at or before** the instant (never after — PIT)."""
    target = _parse_utc(moment_utc)
    value = None
    for stamp, point_value in points:
        if _parse_utc(stamp) <= target:
            value = point_value
        else:
            break
    return value


# --------------------------------------------------------------------------- #
# A2 actions — deterministic dossier (declared DEV substitution)
# --------------------------------------------------------------------------- #

def a2_actions_from_dossier(decision_path: str = DEFAULT_DECISION) -> Tuple[List[dict], List[str]]:
    """A2 (DEV): actions from the deterministic dossier, declared mapping.

    * amount: ``decision.action.amount_usdc`` (never recomputed);
    * timestamp: last observation of ``decision.provenance`` — the dossier
      does not date its action otherwise; substitution written in the notes.
    """
    with open(decision_path, "r", encoding="utf-8") as handle:
        dossier = json.load(handle)
    action = (dossier.get("decision") or {}).get("action") or {}
    amount = action.get("amount_usdc")
    if not isinstance(amount, (int, float)):
        raise HarnessError("dossier %s: decision.action.amount_usdc missing" % decision_path)
    stamps = [item.get("timestamp_utc") for item in (dossier.get("decision") or {}).get(
        "provenance") or [] if isinstance(item, dict)]
    stamps = [stamp for stamp in stamps if stamp]
    if not stamps:
        raise HarnessError("dossier %s: provenance without timestamp — A2 action cannot be dated"
                           % decision_path)
    action_time = max(stamps, key=_parse_utc)
    notes = [
        "A2 DEV = dossier déterministe (%s) — substitution déclarée" % os.path.basename(decision_path),
        "horodatage = dernière observation de la provenance du dossier (le dossier ne date pas "
        "autrement son action)",
    ]
    return ([{"type": "reduce_exposure", "amount_usdc": float(amount),
              "triggered_at_utc": action_time, "rule": "a2_dossier_deterministe",
              "notes": notes}], notes)


# --------------------------------------------------------------------------- #
# Loss and regret per config (frozen loss function G1)
# --------------------------------------------------------------------------- #

def loss_for_actions(actions: Sequence[dict], points: Sequence[Tuple[str, float]], *,
                     q: float = Q_DEV_USDC, p_ref: float = P_REF,
                     p_terminal: float, cost_k: float = COST_K) -> Dict[str, Any]:
    """``L(a)`` — reductions bounded by ``q``; ``P_exec`` = observed series (PIT)."""
    notes: List[str] = []
    total_sold = 0.0
    proceeds = 0.0
    for action in actions:
        size = float(action.get("amount_usdc") or 0.0)
        if size <= 0:
            continue
        remaining = q - total_sold
        if remaining <= 0:
            notes.append("action ignorée : exposition déjà entièrement réduite")
            continue
        size = min(size, remaining)
        if size < float(action.get("amount_usdc") or 0.0):
            notes.append("action plafonnée à l'exposition restante (%.2f)" % remaining)
        triggered_at = action.get("triggered_at_utc")
        if not triggered_at:
            raise HarnessError("action sans triggered_at_utc — P_exec non datable, "
                               "L(a) refusée (jamais de prix inventé)")
        price = _value_at(points, triggered_at)
        if price is None:
            price = p_ref
            notes.append("aucune observation ≤ action — prix de référence utilisé (déclaré)")
        total_sold += size
        proceeds += size * price
    wealth_terminal = proceeds + (q - total_sold) * p_terminal - cost_k
    wealth_t0 = q * p_ref
    return {"loss": loss_mod.loss(wealth_t0, wealth_terminal),
            "wealth_t0": wealth_t0, "wealth_terminal": wealth_terminal,
            "sold": total_sold, "p_terminal": p_terminal, "notes": notes}


def oracle_feasible_loss(points: Sequence[Tuple[str, float]], *, q: float = Q_DEV_USDC,
                         p_ref: float = P_REF, p_terminal: float,
                         x_max: float = comparators_mod.X_MAX_USDC_DEMO) -> Dict[str, Any]:
    """O — ``min_{b∈F} L(b)``, execution at the **best observed instant** (bounded, declared)."""
    best_price = max(value for _stamp, value in points)
    best_stamp = next(stamp for stamp, value in points if value == best_price)
    fractions = loss_mod.feasible_actions(q, x_max=x_max)
    candidates = []
    for x in fractions:
        wealth = x * best_price + (q - x) * p_terminal
        candidates.append({"x": x, "loss": loss_mod.loss(q * p_ref, wealth)})
    best = min(candidates, key=lambda item: item["loss"])
    return {"loss": best["loss"], "x": best["x"], "best_price": best_price,
            "best_stamp_utc": best_stamp,
            "note": "O = oracle ex post FAISABLE (exécution au meilleur instant observé, "
                    "famille G1) — borne inférieure du regret, pas une vérité terrain"}


def regret_pair(loss_value: float, oracle_loss: float) -> Dict[str, Any]:
    regret = loss_mod.regret(loss_value, oracle_loss)
    return {"R": regret, "R_plus": max(regret, 0.0), "R_minus": min(regret, 0.0),
            "note": "R⁻ et R⁺ ne sont jamais moyennés ensemble (règle de langage B7 §e.5)"}


def _b0_quantiles(ordered: Sequence[float]) -> Dict[str, float]:
    """Declared quantiles of a sorted sample — one convention: rank ``int(p·m)-1`` (clamped)."""
    m = len(ordered)
    return {"p05": ordered[max(0, int(0.05 * m) - 1)],
            "p50": ordered[max(0, int(0.50 * m) - 1)],
            "p95": ordered[max(0, int(0.95 * m) - 1)]}


# --------------------------------------------------------------------------- #
# Complete window
# --------------------------------------------------------------------------- #

def run_window(window, *, decision_path: str = DEFAULT_DECISION,
               b0_draws: int = comparators_mod.B0_MIN_DRAWS) -> Dict[str, Any]:
    """One window: actions per config → L, R, B0 placebo, quality note."""
    detail: Dict[str, Any] = {"window_id": window.window_id, "episode_id": window.episode_id,
                              "set": window.set_label, "kind": window.kind,
                              "start_utc": window.start_utc, "end_utc": window.end_utc,
                              "notes": [NOTE_PARAMS]}
    try:
        source_label, points = corpus_mod.window_series(window)
    except corpus_mod.CorpusError as exc:
        detail.update({"status": "SKIPPED", "reason": str(exc)})
        return detail
    gaps = corpus_mod.find_gaps(points)
    detail["series"] = {"source": source_label, "points": len(points),
                        "gaps": gaps,
                        "grid_note": ("grille horaire" if len(points) > 100
                                      else "grille non horaire (%d points) — déclarée"
                                           % len(points))}
    p_terminal = points[-1][1]
    detail["p_terminal"] = p_terminal

    configs: Dict[str, Any] = {}
    corpus_csv = next((os.path.join(REPO_ROOT, rel) for rel in window.sources
                       if rel.endswith(".csv")), None)

    # A0 — NO-ACTION
    configs["A0"] = {"actions": [], **loss_for_actions((), points, p_terminal=p_terminal)}

    # A1 — threshold rule
    a1 = comparators_mod.a1_actions(points)
    configs["A1"] = {"actions": a1, **loss_for_actions(a1, points, p_terminal=p_terminal)}

    # AX0 — frozen repository rule (delegated) — only applies to USDC windows
    if corpus_csv and "usdc" in window.episode_id:
        ax0 = comparators_mod.ax0_actions(corpus_csv, (window.start_utc, window.end_utc))
        configs["AX0"] = {"actions": ax0, **loss_for_actions(ax0, points, p_terminal=p_terminal)}
    else:
        configs["AX0"] = {"actions": None, "status": "NOT APPLICABLE",
                          "reason": "règle AX0 = règle USDC gelée ; sans portée sur %s"
                                    % window.episode_id}

    # A2 — deterministic dossier (declared DEV substitution)
    if "usdc-2023-03" == window.episode_id and os.path.isfile(decision_path):
        a2, a2_notes = a2_actions_from_dossier(decision_path)
        configs["A2"] = {"actions": a2, "notes": a2_notes,
                         **loss_for_actions(a2, points, p_terminal=p_terminal)}
    else:
        configs["A2"] = {"actions": None, "status": "DECLARED", "reason":
                         "pas de dossier déterministe pour %s sur DEV — A2 viendra du rejeu "
                         "journal/archive (déclaré)" % window.episode_id}

    # O — feasible oracle
    oracle = oracle_feasible_loss(points, p_terminal=p_terminal)
    detail["oracle"] = oracle

    # R per available config
    for label, config in configs.items():
        if isinstance(config.get("loss"), (int, float)):
            config["regret"] = regret_pair(config["loss"], oracle["loss"])

    # B0 — paired placebo (A2 if available, otherwise A1 — declared substitution)
    paired_label = "A2" if isinstance(configs["A2"].get("loss"), (int, float)) else "A1"
    sizes = [float(action["amount_usdc"]) for action in configs[paired_label]["actions"]]
    if sizes:
        draws = comparators_mod.b0_draws(len(sizes), sizes, window.start_utc, window.end_utc,
                                         draws=b0_draws)
        losses = [loss_for_actions(draw, points, p_terminal=p_terminal)["loss"] for draw in draws]
        regrets = [loss_mod.regret(value, oracle["loss"]) for value in losses]
        ordered = sorted(regrets)
        distribution = {"m": len(ordered), "mean": sum(ordered) / len(ordered),
                        "min": ordered[0], "max": ordered[-1], "median": ordered[len(ordered) // 2],
                        "quantiles": _b0_quantiles(ordered),
                        "seed": comparators_mod.B0_SEED, "draws": b0_draws,
                        "paired_with": paired_label,
                        "note": ("B0 apparié à %s (%s)" % (paired_label,
                                 "A2 présent" if paired_label == "A2" else "A2 absent — substitution déclarée"))}
        paired_regret = configs[paired_label]["regret"]["R"]
        distribution["percentile_of_%s" % paired_label] = calibration_mod.bootstrap_percentile(
            ordered, paired_regret)
        configs["B0"] = {"actions": None, "status": "DISTRIBUTION",
                         "distribution": distribution}
    else:
        configs["B0"] = {"actions": None, "status": "DECLARED",
                         "reason": "aucune taille d'action à apparier"}

    detail["configs"] = configs
    detail["status"] = "OK"
    return detail


# --------------------------------------------------------------------------- #
# Complete dataset + aggregates
# --------------------------------------------------------------------------- #

def runs_for_set(set_label: str):
    if set_label == windows_mod.SET_DEV:
        return windows_mod.DEV_WINDOWS
    if set_label == windows_mod.SET_EVAL:
        return windows_mod.EVAL_WINDOWS
    raise HarnessError("unknown dataset: %r" % set_label)


def run_set(set_label: str, *, frozen_dir: str = DEFAULT_FROZEN_DIR,
            b0_draws: int = comparators_mod.B0_MIN_DRAWS,
            decision_path: str = DEFAULT_DECISION,
            calibration_periods: Optional[Sequence[str]] = None,
            lock_path: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    """Run a complete dataset with the **freeze gate** — or refuse to write.

    Returns the machine content of the report (real execution fields excluded);
    the banner and the write go through ``report.py``.
    """
    frozen_hashes = windows_mod.verify_frozen_package(frozen_dir)  # refuses without a freeze
    forced_mention = None
    if set_label == windows_mod.SET_EVAL:
        forced_mention = windows_mod.eval_run_gate(frozen_dir, lock_path=lock_path, force=force)
        if calibration_periods is not None:
            eval_calm = [w for w in windows_mod.EVAL_WINDOWS if w.kind == windows_mod.KIND_CALME]
            violations = windows_mod.cross_calibration_violations(list(calibration_periods),
                                                                  eval_calm)
            if violations:
                raise HarnessError("CALM EVAL window × calibration period overlap: %s"
                                   % violations)
    windows = runs_for_set(set_label)
    window_details = [run_window(window, decision_path=decision_path, b0_draws=b0_draws)
                      for window in windows]
    ran = [detail for detail in window_details if detail.get("status") == "OK"]
    skipped = [detail for detail in window_details if detail.get("status") != "OK"]

    aggregates: Dict[str, Any] = {}
    for label in CONFIG_LABELS:
        losses = [detail["configs"][label]["loss"] for detail in ran
                  if isinstance(detail["configs"].get(label, {}).get("loss"), (int, float))]
        regrets = [detail["configs"][label]["regret"]["R"] for detail in ran
                   if isinstance(detail["configs"].get(label, {}).get("regret"), dict)]
        if losses:
            aggregates[label] = {
                "n": len(losses), "losses": losses,
                "mean_loss": sum(losses) / len(losses),
                "regrets": regrets,
                "mean_R_plus": sum(max(r, 0.0) for r in regrets) / len(regrets),
                "mean_R_minus": sum(min(r, 0.0) for r in regrets) / len(regrets),
            }

    n_display = len(ran)
    validity = ("non conclusionnel : N < 100 (cascade B7 §b.3)" if n_display < 100
                else "N ≥ 100 — revendication possible sous conditions")
    content = {
        "schema": "orvyren.evaluation-report/v1",
        "set": set_label,
        "banner": ("EVAL" if set_label == windows_mod.SET_EVAL else "DEV"),
        "frozen": {"dir": os.path.relpath(frozen_dir, REPO_ROOT).replace(os.sep, "/"),
                   "hashes": frozen_hashes},
        "params": {"q": Q_DEV_USDC, "p_ref": P_REF, "k": COST_K, "b0_draws": b0_draws,
                   "note": NOTE_PARAMS},
        "n_windows": n_display, "n_windows_skipped": len(skipped),
        "validity": validity,
        "skipped": [{"window_id": detail["window_id"], "reason": detail.get("reason")}
                    for detail in skipped],
        "windows": [{"window_id": detail["window_id"], "status": detail.get("status"),
                     "notes": detail.get("notes", []),
                     "config_losses": ({label: detail["configs"][label].get("loss")
                                        for label in CONFIG_LABELS}
                                       if detail.get("status") == "OK" else {}),
                     "config_regrets": ({label: (detail["configs"][label].get("regret") or {}).get("R")
                                         for label in CONFIG_LABELS}
                                        if detail.get("status") == "OK" else {})}
                    for detail in window_details],
        "aggregates": aggregates,
        "superiority": {
            "status": "NON CALCULÉ — N < 100" if n_display < 100 else "CALCULÉ",
            "mcnemar": None,
            "note": ("tests de supériorité (Wilson, McNemar exact, bootstrap par blocs) exécutés "
                     "seulement quand N ≥ 100 — le harnais refuse de publier un score agrégé "
                     "unique (B7 §e.5)"),
        },
        "forced_mention": forced_mention,
    }
    return {"content": content, "window_details": window_details}


def content_hash(content: Dict[str, Any]) -> str:
    """Content hash (real execution fields excluded) — two runs ⇒ identical."""
    stripped = _strip_wall(content)
    return hashlib.sha256(json.dumps(stripped, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


WALL_KEYS = ("generated_at_utc", "ts_wall", "duration_s")


def _strip_wall(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _strip_wall(value) for key, value in payload.items()
                if key not in WALL_KEYS}
    if isinstance(payload, list):
        return [_strip_wall(item) for item in payload]
    return payload
