#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — calibration CLI (W7; B7 §b.3, §b.4).

    python run_calibration.py                    # DEV set (frozen/forecasts_dev.jsonl)

Produces ``evidence/calibration_report.{json,md}`` following the imposed
structure (§b.4): scope + hashes, global table (BS/REL/RES/UNC/ECE + verdicts),
reliability curve, breakdown by family (N shown per cell), forecast annex.
The §b.3 cascade decides what is publishable — a report without a hash is an
unverifiable report, a table without N is not rendered.

Gates (refusal to write, exit 2):

* ``frozen/G1–G6`` freeze package absent, incomplete or non-matching;
* a code hash announced inside the Gx documents does not match the working
  tree (``orvyren.evaluation.harness.verify_code_hashes``).

G5 §b.3 cascade — applied to the **content actually computed** (the resolved
forecast↔outcome pairs), never to the verdict label alone
(``orvyren.evaluation.report.apply_cascade``):

======== ==========================================================
N < 5    nothing published (seuil D11)
5 ≤ N    BS, REL, RES, UNC, ȳ, list ; ECE **without claim**
30 ≤ N   + block-bootstrap CI, reliability curve + Wilson per bin
100 ≤ N  + BSS with lower bound + the 5 frozen conditions
======== ==========================================================
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from orvyren.evaluation import calibration as calibration_mod  # noqa: E402
from orvyren.evaluation import forecasts as forecasts_mod  # noqa: E402
from orvyren.evaluation import harness as harness_mod  # noqa: E402
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402
from orvyren.evaluation import report as report_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "evidence", "calibration_report")
DEFAULT_FROZEN = os.path.join(HERE, "frozen")
BANNER = "DEV"

def _sha256_file(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()

def _read_jsonl(path: str):
    records = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_calibration.py",
        description="ORVYREN — DEV calibration report (Brier/Murphy/ECE/Wilson; §b.3 cascade)")
    parser.add_argument("--forecasts", default=os.path.join(HERE, "frozen", "forecasts_dev.jsonl"))
    parser.add_argument("--outcomes", default=os.path.join(HERE, "frozen", "outcomes_dev.jsonl"))
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--frozen-dir", default=DEFAULT_FROZEN)
    args = parser.parse_args(argv)

    try:  # freeze gate: package + code hashes announced by the Gx documents
        windows_mod.verify_frozen_package(args.frozen_dir)
        harness_mod.verify_code_hashes(args.frozen_dir, repo_root=HERE)
    except windows_mod.FreezeGateError as exc:
        print("REFUSED — %s" % exc, file=sys.stderr)
        return 2

    forecasts = forecasts_mod.load_forecasts(args.forecasts)
    outcomes = outcomes_mod.load_outcomes(args.outcomes)
    try:  # chains + forecast ↔ outcome linking by fingerprint (raise, never return errors)
        forecasts_mod.verify_forecast_chain(forecasts, args.forecasts)
        outcomes_mod.verify_outcome_chain(outcomes, args.outcomes)
        by_id = {record["forecast_id"]: record for record in forecasts}
        for outcome in outcomes:
            linked = by_id.get(outcome.get("forecast_id"))
            if linked is None:  # an outcome naming an unknown forecast is a refusal, not a crash
                raise outcomes_mod.OutcomeError(
                    "outcome %s: unknown forecast %r (absent from the forecasts file)"
                    % (outcome.get("outcome_id"), outcome.get("forecast_id")))
            outcomes_mod.check_link(linked, outcome)
    except (forecasts_mod.ForecastError, outcomes_mod.OutcomeError) as exc:
        print("REFUSED — %s" % exc, file=sys.stderr)
        return 2

    outcomes_by_forecast = {item["forecast_id"]: item for item in outcomes}
    pairs = []
    unresolved = []
    for forecast in forecasts:
        outcome = outcomes_by_forecast.get(forecast["forecast_id"])
        y = (outcome or {}).get("y")
        if outcome is None or y not in (0, 1):
            unresolved.append(forecast["forecast_id"])
            continue
        pairs.append({"forecast_id": forecast["forecast_id"],
                      "episode_id": forecast.get("episode_id"),
                      "p": float(forecast["p"]), "y": int(y),
                      "horizon_kind": (forecast.get("horizon") or {}).get("kind"),
                      "resolution_rule_id": forecast.get("resolution_rule_id")})
    p_vector = [pair["p"] for pair in pairs]
    y_vector = [pair["y"] for pair in pairs]

    # G5 §b.3 cascade on the CONTENT actually evaluated (resolved pairs), not
    # on the verdict label: the label is derived from the same content.
    n_content = len(pairs)
    gate = report_mod.cascade_gate(n_content)
    computed = None
    if gate["publish"]["base"]:
        computed = calibration_mod.calibration_report(p_vector, y_vector)
    families = [pair["episode_id"] for pair in pairs]
    global_table = report_mod.apply_cascade(computed, n_content, families=families)
    reliability = ((computed or {}).get("reliability") or []
                   if gate["publish"]["reliability_wilson"] else [])

    by_episode = {}
    if gate["publish"]["base"]:
        for pair in pairs:
            bucket = by_episode.setdefault(pair["episode_id"], {"n": 0, "p": [], "y": []})
            bucket["n"] += 1
            bucket["p"].append(pair["p"])
            bucket["y"].append(pair["y"])
        for episode, bucket in by_episode.items():
            bucket["brier"] = calibration_mod.brier_score(bucket["p"], bucket["y"])
            del bucket["p"], bucket["y"]

    annex = ([dict(pair, squared_error=(pair["p"] - pair["y"]) ** 2) for pair in pairs]
             if gate["publish"]["base"] else [])

    document = {
        "schema": "orvyren.calibration-report/v1",
        "banner": BANNER,
        "set": "dev",
        "n": n_content,
        "unresolved": unresolved,
        "hashes": {"forecasts_file": _sha256_file(args.forecasts),
                   "outcomes_file": _sha256_file(args.outcomes),
                   "scoring_code": _sha256_file(calibration_mod.__file__),
                   "event_label": "calibration_report.dev"},
        "cascade": gate,
        "global": global_table,
        "reliability_curve": reliability,
        "by_episode": by_episode,
        "annex": annex,
        "cascade_note": ("§b.3 cascade: N < 5 nothing; 5 ≤ N < 30 \"%s\" "
                         "(not conclusive); ECE not claimable before N ≥ 100 and the 5 conditions"
                         % calibration_mod.VERDICT_NON_CONCLUSIVE),
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    md_path = args.out + ".md"
    json_path = args.out + ".json"
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    verdict = global_table.get("verdict")
    lines = ["> **%s** — calibration report — N = %d — %s" % (BANNER, n_content, verdict), ""]
    lines.append("# Calibration — DEV set (frozen forecasts `frozen/forecasts_dev.jsonl`)")
    lines.append("")
    lines.append("## 1. Scope and hashes")
    lines.append("")
    lines.append("- N = **%d** resolved forecast(s) · unresolved: %d"
                 % (n_content, len(unresolved)))
    lines.append("- forecasts `%s` · outcomes `%s` · code `%s`"
                 % (document["hashes"]["forecasts_file"][:16],
                    document["hashes"]["outcomes_file"][:16],
                    document["hashes"]["scoring_code"][:16]))
    lines.append("")
    lines.append("## 2. Global table (N = %d)" % n_content)
    lines.append("")
    if global_table:
        for key in sorted(global_table):
            value = global_table[key]
            if isinstance(value, bool) or isinstance(value, (int, float, str)) or value is None:
                lines.append("- **%s** : %s" % (key, value))
            else:
                lines.append("- **%s** : %s" % (key, json.dumps(value, ensure_ascii=False)))
    else:
        lines.append("- (nothing published)")
    lines.append("")
    lines.append("## 3. Reliability curve (bins, N shown)")
    lines.append("")
    if reliability:
        lines.append("| bin | n_b | conf | acc | Wilson CI |")
        lines.append("|---|---|---|---|---|")
        for row in reliability:
            low, high = row.get("wilson_low"), row.get("wilson_high")
            wilson = ("%.4f–%.4f" % (low, high)) if isinstance(low, (int, float)) and \
                isinstance(high, (int, float)) else "—"
            conf = row.get("conf_b")
            acc = row.get("acc_b")
            lines.append("| %s | %s | %s | %s | %s |"
                         % (row.get("bin"), row.get("n_b"),
                            ("%.4f" % conf) if isinstance(conf, (int, float)) else "—",
                            ("%.4f" % acc) if isinstance(acc, (int, float)) else "—",
                            wilson))
    else:
        lines.append("- (not published — §b.3 cascade: N < 30)")
    lines.append("")
    lines.append("## 4. By family (N per cell)")
    lines.append("")
    if by_episode:
        for episode, bucket in sorted(by_episode.items(), key=lambda kv: str(kv[0])):
            lines.append("- **%s** — N = %d — Brier %.4f" % (episode, bucket["n"], bucket["brier"]))
    else:
        lines.append("- (nothing published)")
    lines.append("")
    lines.append("## 5. Forecast annex (N = %d)" % n_content)
    lines.append("")
    if annex:
        lines.append("| forecast_id | p | y | (p−y)² | horizon | rule |")
        lines.append("|---|---|---|---|---|---|")
        for pair in annex:
            lines.append("| `%s` | %.4f | %d | %.4f | %s | %s |"
                         % (pair["forecast_id"], pair["p"], pair["y"], pair["squared_error"],
                            pair["horizon_kind"], pair["resolution_rule_id"]))
    else:
        lines.append("- (nothing published)")
    lines.append("")
    lines.append("> %s" % document["cascade_note"])
    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    print("calibration %s — N = %d — verdict: %s" % (BANNER, n_content, verdict))
    print("  cascade: %s (content-gated publication)" % gate["tier"])
    print("  report  : %s" % md_path)
    return 0

if __name__ == "__main__":
    sys.exit(main())
