#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core - root decision CLI (fully offline, stdlib only, replayable).

Replays the pilot case (FREEZE_V1 D1/D2) over the frozen corpus and writes the
audit evidence:

  * decision engine -> evidence/decision_<case>.json    (run_case output)
  * baseline A0     -> evidence/baseline_report.json    (rule + signals main/control)

Usage:
    python run_decision.py [--corpus PATH] [--out-dir DIR] [--case CASE_ID]

Defaults: corpus = <repo>/corpus/usdc_observations.csv (read-only),
          out-dir = <repo>/evidence,
          case    = usdc-2023-03,
          main window    = 2023-03-09T00:00:00Z -> 2023-03-15T00:00:00Z (D1),
          control window = 2023-02-15T00:00:00Z -> 2023-02-18T00:00:00Z (D2).
"""

import argparse
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from orvyren.decision.baseline import run_baseline   # noqa: E402
from orvyren.decision.axes import build_dossier       # noqa: E402
from orvyren.decision.engine import run_case         # noqa: E402
from orvyren.decision.scenarios import load_observations  # noqa: E402

DEFAULT_CORPUS = "corpus/usdc_observations.csv"
DEFAULT_OUT_DIR = "evidence"
DEFAULT_CASE = "usdc-2023-03"

# frozen windows (FREEZE_V1 D1/D2) -- inclusive bounds, UTC
MAIN_WINDOW = ("2023-03-09T00:00:00+00:00", "2023-03-15T00:00:00+00:00")
CONTROL_WINDOW = ("2023-02-15T00:00:00+00:00", "2023-02-18T00:00:00+00:00")


def write_json(path, payload):
    """Deterministic JSON writer: insertion order, 2-space indent, LF, trailing newline."""
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _resolve(path_arg, base=_REPO_ROOT):
    """Absolute path for CLI arguments; relative arguments resolve against the repo root."""
    return path_arg if os.path.isabs(path_arg) else os.path.join(base, path_arg)


def _display_path(absolute):
    """Repo-relative POSIX path when inside the repository, else the absolute path."""
    try:
        relative = os.path.relpath(absolute, _REPO_ROOT).replace(os.sep, "/")
    except ValueError:
        return absolute.replace(os.sep, "/")
    return absolute.replace(os.sep, "/") if relative.startswith("..") else relative


def _safe_case_token(case):
    """Filesystem-safe token for an evidence filename (never a path)."""
    token = str(case).replace("\\", "/").split("/")[-1]
    token = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in token)
    return token.strip("-.") or "case"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the ORVYREN-Core USDC 2023-03 decision case (offline, replayable)."
    )
    parser.add_argument("--corpus", default=DEFAULT_CORPUS,
                        help="corpus CSV, relative paths resolve against the repository root "
                             "(default: %(default)s)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help="evidence directory, relative paths resolve against the repository "
                             "root (default: %(default)s)")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help="case id used in the decision record and file name (default: %(default)s)")
    parser.add_argument("--no-rdof", action="store_true",
                        help="write the v0 record only (skip the RDOF v1 / 3-axes / "
                             "abstention enrichment of lot L3.2-L3.5)")
    parser.add_argument("--reserve-recipient", default=None,
                        help="reserve wallet address used to evaluate the authorization "
                             "axis through the policy service; omit to leave the axis "
                             "explicitly not evaluated (keeps runs byte-identical)")
    args = parser.parse_args(argv)

    corpus_abs = _resolve(args.corpus)
    if not os.path.exists(corpus_abs):
        parser.error(f"corpus not found: {corpus_abs}")
    corpus_ref = _display_path(corpus_abs)

    out_dir = _resolve(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)

    case = run_case(corpus_ref, MAIN_WINDOW[0], MAIN_WINDOW[1],
                    case_id=args.case, window_label="main")
    if not args.no_rdof:
        dossier = build_dossier(args.case, load_observations(corpus_abs),
                                MAIN_WINDOW[0], MAIN_WINDOW[1],
                                reserve_recipient=args.reserve_recipient)
        case.update(dossier)
    baseline = run_baseline(corpus_abs, MAIN_WINDOW, CONTROL_WINDOW)

    decision_path = os.path.join(out_dir, f"decision_{_safe_case_token(args.case)}.json")
    baseline_path = os.path.join(out_dir, "baseline_report.json")
    write_json(decision_path, case)
    write_json(baseline_path, baseline)

    verdicts = case["hypothesis_verdicts"]
    decision = case["decision"]
    action = decision["action"]
    exposure = case["inputs_summary"]["exposure_parameters"]

    lines = [
        f"ORVYREN-Core decision run - case {case['case']}",
        f"Window (main):    {case['window']['start']} -> {case['window']['end']}",
        f"Corpus:           {case['inputs_summary']['corpus']['path']} "
        f"({case['inputs_summary']['corpus']['observations_in_window']} observations in window, "
        f"sha256 {case['inputs_summary']['corpus']['sha256'][:12]}...)",
        "Hypothesis verdicts:",
        f"  H1 {verdicts['H1']['label']}: {verdicts['H1']['verdict']}",
        f"  H2 {verdicts['H2']['label']}: {verdicts['H2']['verdict']}",
        f"  H3 {verdicts['H3']['label']}: {verdicts['H3']['verdict']}",
    ]
    if action is not None:
        lines.append(
            f"Decision:         {decision['verdict']} - {action['type']} of {action['amount_usdc']} "
            f"{action['asset']} from wallet '{action['from_wallet']}' to wallet '{action['to_wallet']}'"
        )
    else:
        lines.append(f"Decision:         {decision['verdict']} - action: null")
    lines.append(
        f"Exposure envelope: exposure {exposure['exposure_usdc']} USDC, floor {exposure['floor_usdc']} USDC, "
        f"available_to_move {exposure['available_to_move_usdc']} USDC"
    )
    if decision["missing_inputs"]:
        lines.append("Missing inputs:   " + "; ".join(decision["missing_inputs"]))
    if not args.no_rdof:
        axes = case["axes"]
        rdof_payload = case["rdof"]
        lines.append(
            f"Axes (separate) : epistemic={axes['epistemic_verdict']} · "
            f"economic={axes['economic_action']} · "
            f"authorization={axes['authorization_verdict']}")
        lines.append(
            f"RDOF v1:          {len(rdof_payload['trace'])} search(es), "
            f"stop \"{rdof_payload['stop']}\", "
            f"cost {rdof_payload['budget']['consomme']['secondes']} s "
            f"({rdof_payload['budget']['consomme']['appels']} call(s))")
    lines.append(
        f"Baseline A0:      signals_main={len(baseline['signals_main'])}, "
        f"signals_control={len(baseline['signals_control'])}, "
        f"false_signals_control={baseline['false_signals_control']}"
    )
    for signal in baseline["signals_main"]:
        lines.append(
            f"  - signal {signal['triggered_at_utc']}: aggregator {signal['trigger_value']} "
            f"({signal['trigger_deviation_pct']}% below peg), episode "
            f"{signal['episode']['start_utc']} -> {signal['episode']['end_utc']} "
            f"({signal['episode']['observations']} obs) -> reduce exposure by "
            f"{signal['action']['amount_usdc']} USDC"
        )
    lines.append(f"Evidence:         {_display_path(decision_path)}")
    lines.append(f"Evidence:         {_display_path(baseline_path)}")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
