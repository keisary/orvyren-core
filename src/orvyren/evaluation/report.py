#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — evaluation report rendering (W7; B7 §e.5, §b.4).

Opposable rules:

* **mandatory banner** at the top of every output (``DEV`` / ``EVAL`` /
  ``REPLAY-…``) — any output without a banner is a bug;
* **N displayed** everywhere; a table without ``N`` is not rendered;
* no single aggregate score; ``R⁻`` and ``R⁺`` are never averaged together;
* the content hash (real execution fields excluded) makes two identical
  executions comparable — a report without a hash is an unverifiable report.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List, Optional

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
