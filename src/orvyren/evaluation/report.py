#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — evaluation report rendering (W7; B7 §e.5, §b.4).

Opposable rules:

* **mandatory banner** at the top of every output (``DEV`` / ``EVAL`` /
  ``REPLAY-…``) — any output without a banner is a bug;
* **N displayed** everywhere; a table without ``N`` is not rendered;
* no single aggregate score; ``R⁻`` and ``R⁺`` are never averaged together;
* the content hash (real execution fields excluded) makes two identical
  executions comparable — a report without a hash is an unverifiable report;
* the G5 §b.3 cascade is applied to the **content actually computed** (which
  bootstrap CI / ECE / BSS may be published for N evaluated items), never to a
  result label alone — see :func:`cascade_gate` / :func:`apply_cascade`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List, Optional, Sequence

from orvyren.evaluation import calibration as calibration_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ALLOWED_BANNERS = ("DEV", "EVAL")


class ReportError(RuntimeError):
    """Invalid report (missing banner, missing N) — never rendered silently."""


def require_banner(banner: object) -> str:
    text = str(banner or "")
    if text in ALLOWED_BANNERS or text.startswith("REPLAY"):
        return text
    raise ReportError("mandatory banner missing or unknown (%r) — every evaluation "
                      "output carries DEV/EVAL/REPLAY-… (B7 §e.5)" % banner)


# --------------------------------------------------------------------------- #
# G5 §b.3 cascade applied to the CONTENT actually computed (B7 §b.3)
# --------------------------------------------------------------------------- #

#: G5 §b.3 row "30 ≤ N < 100 : + IC bootstrap, courbe de fiabilité + Wilson".
N_CI_MIN = 30

CASCADE_TIER_NOT_COMPUTED = "NOT_COMPUTED"
CASCADE_TIER_BASE = "BASE"
CASCADE_TIER_CI = "BASE_CI"
CASCADE_TIER_CLAIM = "CLAIM"

def cascade_gate(n: int) -> Dict[str, Any]:
    """G5 §b.3 cascade for ``n`` **evaluated** items (content, not label).

    Decides what content may be published for the given effectif:

    ============== ====================================================
    ``N < 5``      nothing (seuil D11)
    ``5 ≤ N < 30`` BS, REL, RES, UNC, ȳ, list ; ECE **without** claim
    ``30 ≤ N``     + block-bootstrap CI, reliability curve + Wilson
    ``100 ≤ N``    + BSS (with lower bound), ECE claimable under the
                   five frozen conditions
    ============== ====================================================

    The label returned here is derived from ``n`` — it is only ever a
    *consequence* of the evaluated content, never its driver.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise ReportError("N must be an int (evaluated content) : %r" % (n,))
    if n < 0:
        raise ReportError("negative N : %r" % (n,))
    if n < calibration_mod.N_MIN_PUBLISH:
        tier = CASCADE_TIER_NOT_COMPUTED
        label = calibration_mod.VERDICT_NOT_COMPUTED
    elif n < N_CI_MIN:
        tier = CASCADE_TIER_BASE
        label = calibration_mod.VERDICT_NON_CONCLUSIVE
    elif n < calibration_mod.N_CLAIM_MIN:
        tier = CASCADE_TIER_CI
        label = calibration_mod.VERDICT_NON_CONCLUSIVE
    else:
        tier = CASCADE_TIER_CLAIM
        label = calibration_mod.VERDICT_CLAIM_POSSIBLE
    publish = {
        "base": tier != CASCADE_TIER_NOT_COMPUTED,
        "ece": tier != CASCADE_TIER_NOT_COMPUTED,
        "ece_claimable": tier == CASCADE_TIER_CLAIM,
        "bootstrap_ci": tier in (CASCADE_TIER_CI, CASCADE_TIER_CLAIM),
        "reliability_wilson": tier in (CASCADE_TIER_CI, CASCADE_TIER_CLAIM),
        "bss": tier == CASCADE_TIER_CLAIM,
    }
    return {"n": n, "tier": tier, "label": label, "publish": publish}

def _claim_conditions(computed: Dict[str, Any], bss_ci: Optional[List[float]],
                      families: Sequence[str]) -> List[dict]:
    """The five frozen conditions (B7 §b.3) — computed where derivable from the
    evaluated content, ``NOT COMPUTED`` / ``DECLARATION REQUIRED`` otherwise.

    The controlled word « calibré » is never emitted by this code: only the
    conditions and their status are published.
    """
    rows = [row for row in (computed.get("reliability") or []) if row.get("n_b")]
    max_gap = max((abs(row["acc_b"] - row["conf_b"]) for row in rows), default=None)
    ece = computed.get("ece")
    n = computed.get("n") or 0
    bss_low = bss_ci[0] if bss_ci else None
    n_families = len({str(family) for family in families})
    return [
        {"id": 1, "condition": "N ≥ 100 out-of-sample",
         "computed": n, "ok": n >= calibration_mod.N_CLAIM_MIN,
         "declaration_required": "out-of-sample part: declared by the EVAL run"},
        {"id": 2,
         "condition": "ECE ≤ %.2f with CI upper bound ≤ %.2f"
                      % (calibration_mod.ECE_CLAIM_MAX, calibration_mod.ECE_CI_UPPER_MAX),
         "computed": {"ece": ece, "ece_ci_upper": None},
         "ok": bool(ece is not None and ece <= calibration_mod.ECE_CLAIM_MAX),
         "declaration_required": ("ECE CI upper bound: NOT COMPUTED (the frozen code computes "
                                  "no ECE confidence interval) — declaration required")},
        {"id": 3, "condition": "max_b |acc_b − conf_b| ≤ %.2f" % calibration_mod.MAX_BIN_GAP_CLAIM,
         "computed": max_gap,
         "ok": bool(max_gap is not None and max_gap <= calibration_mod.MAX_BIN_GAP_CLAIM),
         "declaration_required": None},
        {"id": 4, "condition": "BSS CI lower bound > 0",
         "computed": bss_low,
         "ok": bool(bss_low is not None and bss_low > 0),
         "declaration_required": None},
        {"id": 5, "condition": "≥ 2 disjoint episode families + no-tuning declaration",
         "computed": n_families,
         "ok": bool(n_families >= 2),
         "declaration_required": "no-tuning declaration"},
    ]

def apply_cascade(computed: Optional[Dict[str, Any]], n_content: int,
                  families: Sequence[str] = ()) -> Dict[str, Any]:
    """Apply the G5 §b.3 cascade to the content **actually computed**.

    ``computed`` is the machine report of the frozen calibration module (or
    ``None`` below the publication threshold); ``n_content`` is the number of
    items actually evaluated. The cascade gates the published content —
    block-bootstrap CI and reliability curve (``N ≥ 30``), ECE claim and BSS
    with its lower bound (``N ≥ 100``) — and the verdict label is derived from
    that same content. A label that diverges from the evaluated content is
    refused (:class:`ReportError`), never silently preferred.

    The reliability curve is published in its own section
    (``reliability_curve``), gated by ``publish["reliability_wilson"]``.
    """
    gate = cascade_gate(n_content)
    if gate["tier"] == CASCADE_TIER_NOT_COMPUTED:
        return {"n": n_content, "verdict": gate["label"], "ece_claimable": False,
                "note": "nothing published: N < %d (seuil D11)"
                        % calibration_mod.N_MIN_PUBLISH}
    if not isinstance(computed, dict):
        raise ReportError("computed content missing for N = %d ≥ %d"
                          % (n_content, calibration_mod.N_MIN_PUBLISH))
    if computed.get("n") != n_content:
        raise ReportError(
            "label N = %r diverges from the evaluated content (N = %d) — the cascade follows the content"
            % (computed.get("n"), n_content))
    if computed.get("verdict") != gate["label"]:
        raise ReportError(
            "verdict label %r diverges from the cascade on the evaluated content (%r)"
            % (computed.get("verdict"), gate["label"]))
    published: Dict[str, Any] = {
        "n": n_content,
        "ybar": computed["ybar"], "bs": computed["bs"],
        "rel": computed["rel"], "res": computed["res"], "unc": computed["unc"],
        "bins": computed.get("bins"),
        "ece": computed["ece"],
        "ece_claimable": gate["publish"]["ece_claimable"],
        "verdict": gate["label"],
    }
    for key in ("within_bin_term", "rel_minus_res_plus_unc", "exact_identity"):
        if key in computed:
            published[key] = computed[key]
    if not gate["publish"]["ece_claimable"]:
        published["ece_claim_note"] = (
            "ECE without claim — the 5 conditions (B7 §b.3) are not established for N < %d"
            % calibration_mod.N_CLAIM_MIN)
    if gate["publish"]["bootstrap_ci"]:
        published["bs_bootstrap_ci"] = computed["bs_bootstrap_ci"]
        published["bootstrap"] = computed.get("bootstrap")
    if gate["publish"]["bss"]:
        ybar = computed["ybar"]
        clim = ybar * (1.0 - ybar)
        bss_ci = None
        ci = computed.get("bs_bootstrap_ci")
        if clim > 0.0 and isinstance(ci, (list, tuple)) and len(ci) == 2:
            # BSS is decreasing in BS: the BS bootstrap CI maps to a BSS CI.
            bss_ci = [1.0 - ci[1] / clim, 1.0 - ci[0] / clim]
        published["bss"] = computed["bss"]
        published["bss_ci"] = bss_ci
        published["claim_conditions"] = _claim_conditions(computed, bss_ci, families)
    return published


def _write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def render_evaluation_report(*, content: Dict[str, Any], out_dir: str) -> Dict[str, str]:
    """Write ``evaluation_report.json`` + ``.md``; return the paths + the hash."""
    from orvyren.evaluation import harness  # late import (avoids the cycle)

    banner = require_banner(content.get("banner"))
    n_windows = content.get("n_windows")
    if not isinstance(n_windows, int):
        raise ReportError("N (n_windows) missing from the report — a table without N is not rendered")
    validity = str(content.get("validity") or "")
    if not validity:
        raise ReportError("validity mention missing (non-conclusive when N < 100)")
    content_sha = harness.content_hash(content)
    generated_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    json_path = os.path.join(out_dir, "evaluation_report.json")
    md_path = os.path.join(out_dir, "evaluation_report.md")
    document = dict(content, content_sha256=content_sha, generated_at_utc=generated_at)
    _write_json(json_path, document)

    lines: List[str] = []
    lines.append("> **%s** — rapport d'évaluation — jeu `%s` — N = %d — %s"
                 % (banner, content.get("set"), n_windows, validity))
    lines.append("")
    lines.append("# Rapport d'évaluation ORVYREN — %s" % banner)
    lines.append("")
    if content.get("forced_mention"):
        lines.append("> ⚠ **%s**" % content["forced_mention"])
        lines.append("")
    lines.append("*hash de contenu* : `%s` · *généré* : %s · *fenêtres sautées* : %d"
                 % (content_sha, generated_at, content.get("n_windows_skipped", 0)))
    lines.append("")
    params = content.get("params") or {}
    lines.append("**Paramètres** : q = %s · p_ref = %s · k = %s · tirages B0 = %s"
                 % (params.get("q"), params.get("p_ref"), params.get("k"), params.get("b0_draws")))
    lines.append("")
    lines.append("> %s" % params.get("note", ""))
    lines.append("")

    lines.append("## Fenêtres (N = %d)" % n_windows)
    lines.append("")
    lines.append("| Fenêtre | Statut | L(A0) | L(A1) | L(AX0) | L(A2) | R(A2) |")
    lines.append("|---|---|---|---|---|---|---|")

    def _fmt(value: Any) -> str:
        return "—" if value is None else ("%.4f" % value if isinstance(value, (int, float)) else str(value))

    for window in content.get("windows") or []:
        losses = window.get("config_losses") or {}
        regrets = window.get("config_regrets") or {}
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s |"
                     % (window.get("window_id"), window.get("status"),
                        _fmt(losses.get("A0")), _fmt(losses.get("A1")), _fmt(losses.get("AX0")),
                        _fmt(losses.get("A2")), _fmt(regrets.get("A2"))))
    lines.append("")

    aggregates = content.get("aggregates") or {}
    if aggregates:
        lines.append("## Agrégats par config (N affiché par ligne ; R⁻ ≠ R⁺, jamais moyennés ensemble)")
        lines.append("")
        lines.append("| Config | N | L moyen | R⁺ moyen | R⁻ moyen |")
        lines.append("|---|---|---|---|---|")
        for label in ("A0", "A1", "AX0", "A2", "B0"):
            entry = aggregates.get(label)
            if not entry:
                continue
            lines.append("| %s | %d | %.4f | %.4f | %.4f |"
                         % (label, entry["n"], entry["mean_loss"], entry["mean_R_plus"],
                            entry["mean_R_minus"]))
        lines.append("")

    superiority = content.get("superiority") or {}
    lines.append("## Supériorité & placebo")
    lines.append("")
    lines.append("- Statut des tests de supériorité : **%s** — %s"
                 % (superiority.get("status"), superiority.get("note", "")))
    lines.append("")

    lines.append("## Limites (écrites avant lecture)")
    lines.append("")
    lines.append("- Aucun score agrégé unique ; regrets R⁻/R⁺ publiés séparément (W2-D piège n°8).")
    lines.append("- O = borne inférieure du regret (exécution au meilleur instant observé) — "
                 "pas une vérité terrain.")
    lines.append("- Substitutions DEV (P_exec = prix observé, k = 0, A2 = dossier déterministe) "
                 "déclarées dans chaque fenêtre.")
    lines.append("")
    lines.append("*Rapport reproductible : hash de contenu `%s` (champs d'exécution réels exclus).*"
                 % content_sha)
    _write_text(md_path, "\n".join(lines))
    return {"json_path": json_path, "md_path": md_path, "content_sha256": content_sha}


def render_window_detail(detail: Dict[str, Any], *, out_dir: str) -> str:
    path = os.path.join(out_dir, "windows", "%s.json" % detail.get("window_id"))
    _write_json(path, detail)
    return path


def write_side_files(*, content: Dict[str, Any], window_details: List[Dict[str, Any]],
                     out_dir: str) -> Dict[str, str]:
    """``placebo_B0.json`` + ``superiority_tests.json`` (B7 §e.5 structure)."""
    placebo: Dict[str, Any] = {"schema": "orvyren.evaluation-placebo/v1",
                               "note": "distribution complète des tirages B0 (graine fixée) + "
                                       "percentile de la config appariée"}
    for detail in window_details:
        config = (detail.get("configs") or {}).get("B0") or {}
        if config.get("status") == "DISTRIBUTION":
            placebo[detail["window_id"]] = config["distribution"]
    placebo_path = os.path.join(out_dir, "placebo_B0.json")
    _write_json(placebo_path, placebo)

    superiority = dict(content.get("superiority") or {})
    superiority["window_level"] = [
        {"window_id": detail["window_id"],
         "percentile_paired": {key: value for key, value in
                               ((detail.get("configs") or {}).get("B0") or {})
                               .get("distribution", {}).items()
                               if key.startswith("percentile_of_")}}
        for detail in window_details if detail.get("status") == "OK"]
    superiority_path = os.path.join(out_dir, "superiority_tests.json")
    _write_json(superiority_path, superiority)
    return {"placebo_B0": placebo_path, "superiority_tests": superiority_path}


def append_variants_log(log_path: str, entry: Dict[str, Any]) -> None:
    """Append-only ``variants.log`` — one line per execution, **failures included**."""
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    line = dict(entry)
    line.setdefault("ts_wall_utc",
                    _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    with open(log_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
