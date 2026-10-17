#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — CLI de calibration (W7 ; B7 §b.3, §b.4).

    python run_calibration.py                    # jeu DEV (frozen/forecasts_dev.jsonl)

Produit ``evidence/calibration_report.{json,md}`` selon la structure imposée
(§b.4) : périmètre + hashes, tableau global (BS/REL/RES/UNC/ECE + verdicts),
courbe de fiabilité, décomposition par famille (N affiché par cellule), annexe
des prévisions. La cascade §b.3 décide ce qui est publiable — un rapport sans
hash est un rapport non vérifiable, un tableau sans N n'est pas rendu.
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
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, "evidence", "calibration_report")
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
        description="ORVYREN — rapport de calibration DEV (Brier/Murphy/ECE/Wilson ; cascade §b.3)")
    parser.add_argument("--forecasts", default=os.path.join(HERE, "frozen", "forecasts_dev.jsonl"))
    parser.add_argument("--outcomes", default=os.path.join(HERE, "frozen", "outcomes_dev.jsonl"))
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    forecasts = forecasts_mod.load_forecasts(args.forecasts)
    outcomes = outcomes_mod.load_outcomes(args.outcomes)
    try:  # chaînes + liaison prévision ↔ outcome par empreinte (elles lèvent, jamais)
        forecasts_mod.verify_forecast_chain(forecasts, args.forecasts)
        outcomes_mod.verify_outcome_chain(outcomes, args.outcomes)
        by_id = {record["forecast_id"]: record for record in forecasts}
        for outcome in outcomes:
            outcomes_mod.check_link(by_id[outcome["forecast_id"]], outcome)
    except (forecasts_mod.ForecastError, outcomes_mod.OutcomeError) as exc:
        print("REFUS — %s" % exc, file=sys.stderr)
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

    report = calibration_mod.calibration_report(p_vector, y_vector)
    reliability = calibration_mod.reliability_table(p_vector, y_vector) if pairs else []
    by_episode = {}
    for pair in pairs:
        bucket = by_episode.setdefault(pair["episode_id"], {"n": 0, "p": [], "y": []})
        bucket["n"] += 1
        bucket["p"].append(pair["p"])
        bucket["y"].append(pair["y"])
    for episode, bucket in by_episode.items():
        bucket["brier"] = calibration_mod.brier_score(bucket["p"], bucket["y"])
        del bucket["p"], bucket["y"]

    document = {
        "schema": "orvyren.calibration-report/v1",
        "banner": BANNER,
        "set": "dev",
        "n": len(pairs),
        "unresolved": unresolved,
        "hashes": {"forecasts_file": _sha256_file(args.forecasts),
                   "outcomes_file": _sha256_file(args.outcomes),
                   "scoring_code": _sha256_file(calibration_mod.__file__),
                   "event_label": "calibration_report.dev"},
        "global": report,
        "reliability_curve": reliability,
        "by_episode": by_episode,
        "annex": [dict(pair, squared_error=(pair["p"] - pair["y"]) ** 2) for pair in pairs],
        "cascade_note": ("cascade §b.3 : N < 5 rien ; 5 ≤ N < 30 « non conclusionnel » ; "
                         "ECE non revendicable avant N ≥ 100 et les 5 conditions"),
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    md_path = args.out + ".md"
    json_path = args.out + ".json"
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    verdict = report.get("verdict") if isinstance(report, dict) else None
    lines = ["> **%s** — rapport de calibration — N = %d — %s" % (BANNER, len(pairs), verdict), ""]
    lines.append("# Calibration — jeu DEV (prévisions gelées `frozen/forecasts_dev.jsonl`)")
    lines.append("")
    lines.append("## 1. Périmètre et hashes")
    lines.append("")
    lines.append("- N = **%d** prévision(s) résolue(s) · non résolues : %d"
                 % (len(pairs), len(unresolved)))
    lines.append("- forecasts `%s` · outcomes `%s` · code `%s`"
                 % (document["hashes"]["forecasts_file"][:16],
                    document["hashes"]["outcomes_file"][:16],
                    document["hashes"]["scoring_code"][:16]))
    lines.append("")
    lines.append("## 2. Tableau global (N = %d)" % len(pairs))
    lines.append("")
    if isinstance(report, dict):
        for key in sorted(report):
            value = report[key]
            if isinstance(value, (int, float, str)) or value is None:
                lines.append("- **%s** : %s" % (key, value))
        for key, value in sorted(report.items()):
            if isinstance(value, dict):
                lines.append("- **%s** : %s" % (key, json.dumps(value, ensure_ascii=False)))
    else:
        lines.append("- %s" % report)
    lines.append("")
    lines.append("## 3. Courbe de fiabilité (bins, N affiché)")
    lines.append("")
    if reliability:
        lines.append("| bin | n_b | conf | acc | IC Wilson |")
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
        lines.append("- (aucun bin)")
    lines.append("")
    lines.append("## 4. Par famille (N par cellule)")
    lines.append("")
    for episode, bucket in sorted(by_episode.items()):
        lines.append("- **%s** — N = %d — Brier %.4f" % (episode, bucket["n"], bucket["brier"]))
    lines.append("")
    lines.append("## 5. Annexe des prévisions (N = %d)" % len(pairs))
    lines.append("")
    lines.append("| forecast_id | p | y | (p−y)² | horizon | règle |")
    lines.append("|---|---|---|---|---|---|")
    for pair in document["annex"]:
        lines.append("| `%s` | %.4f | %d | %.4f | %s | %s |"
                     % (pair["forecast_id"], pair["p"], pair["y"], pair["squared_error"],
                        pair["horizon_kind"], pair["resolution_rule_id"]))
    lines.append("")
    lines.append("> %s" % document["cascade_note"])
    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    print("calibration %s — N = %d — verdict : %s" % (BANNER, len(pairs), verdict))
    print("  rapport : %s" % md_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
