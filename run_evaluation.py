#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — DEV/EVAL evaluation CLI (W7, L7.6; B7 §d.2.5, §e).

    python run_evaluation.py --set dev                     # full offline harness
    python run_evaluation.py --set eval [--force] [--calibration-periods 2025-01,2025-02]

Gates (refusal to write, code 2):

* ``frozen/G1–G6`` freeze absent, incomplete or non-matching — **both sets**;
* ``--set eval``: ``eval_run.lock`` present (second run forbidden without
  ``--force`` — an "evaluation re-run" mention is added to the report);
* ``--set eval``: a CALM EVAL window overlaps the declared calibration period
  (``--calibration-periods``).

Outputs (``--out-dir``, default ``evidence/evaluation/``):
``evaluation_report.{json,md}`` (mandatory banner + N), ``windows/<id>.json``,
``placebo_B0.json``, ``superiority_tests.json``, ``variants.log`` (failures included).
"""

from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from orvyren.evaluation import harness  # noqa: E402
from orvyren.evaluation import report as report_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402

EXIT_OK = 0
EXIT_REFUSED = 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_evaluation.py",
        description="ORVYREN — evaluation harness: A0/A1/AX0/A2/B0 loop per window, "
                    "freeze gate, mandatory banners (B7 §e).")
    parser.add_argument("--set", dest="set_label", choices=("dev", "eval"), default="dev")
    parser.add_argument("--out-dir", default=harness.DEFAULT_OUT_DIR)
    parser.add_argument("--frozen-dir", default=harness.DEFAULT_FROZEN_DIR)
    parser.add_argument("--b0-draws", type=int, default=200)
    parser.add_argument("--force", action="store_true",
                        help="allow an EVAL re-run (mandatory mention in the report)")
    parser.add_argument("--calibration-periods", default=None,
                        help="comma-separated YYYY-MM months (cross-calibration embargo)")
    parser.add_argument("--lock-path", default=None)
    args = parser.parse_args(argv)

    lock_path = args.lock_path or os.path.join(
        os.path.dirname(os.path.abspath(harness.DEFAULT_OUT_DIR)), "eval_run.lock")
    periods = [item.strip() for item in (args.calibration_periods or "").split(",")
               if item.strip()] or None
    variants_log = os.path.join(args.out_dir, "variants.log")

    try:
        result = harness.run_set(args.set_label, frozen_dir=args.frozen_dir,
                                 b0_draws=args.b0_draws,
                                 calibration_periods=periods, lock_path=lock_path,
                                 force=args.force)
    except (windows_mod.FreezeGateError, harness.HarnessError,
            windows_mod.WindowError) as exc:
        report_mod.append_variants_log(variants_log, {
            "set": args.set_label, "result": "REFUSED", "reason": str(exc)})
        print("REFUSED — %s" % exc, file=sys.stderr)
        return EXIT_REFUSED

    content = result["content"]
    paths = report_mod.render_evaluation_report(content=content, out_dir=args.out_dir)
    for detail in result["window_details"]:
        report_mod.render_window_detail(detail, out_dir=args.out_dir)
    side = report_mod.write_side_files(content=content,
                                       window_details=result["window_details"],
                                       out_dir=args.out_dir)

    lock_written = False
    if (args.set_label == "eval" and content["n_windows"] > 0
            and not os.path.exists(lock_path)):
        os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
        with open(lock_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("# first EVAL pass — the set is burned (B7 §d.2.5)\n%s\n"
                         % paths["content_sha256"])
        lock_written = True

    report_mod.append_variants_log(variants_log, {
        "set": args.set_label, "result": "OK", "n_windows": content["n_windows"],
        "content_sha256": paths["content_sha256"], "forced": bool(content.get("forced_mention"))})

    print("evaluation %s — N = %d window(s), %d skipped"
          % (content["banner"], content["n_windows"], content["n_windows_skipped"]))
    for label, aggregate in sorted((content.get("aggregates") or {}).items()):
        print("  %-4s n=%d · mean L %.4f · R⁺ %.4f · R⁻ %.4f"
              % (label, aggregate["n"], aggregate["mean_loss"],
                 aggregate["mean_R_plus"], aggregate["mean_R_minus"]))
    if content.get("forced_mention"):
        print("  !! %s" % content["forced_mention"])
    print("  report  : %s" % paths["md_path"])
    print("  hash    : %s" % paths["content_sha256"])
    print("  annexes : %s · %s" % (os.path.basename(side["placebo_B0"]),
                                   os.path.basename(side["superiority_tests"])))
    if lock_written:
        print("  EVAL lock written: %s (set burned)" % lock_path)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
