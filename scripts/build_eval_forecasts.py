#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — EVAL forecasts/outcomes of the instrumented windows (W3-C).

Thin front-end over :func:`scripts.freeze_sprint0.write_eval_forecasts`, so the
EVAL records are produced by **the same builder** as the DEV package: anything
living in ``frozen/`` must be reproducible byte for byte by ``build_all``
(``frozen/INDEX.md`` §4). No second construction exists.

What is instrumented, and what is not:

* ``eval-usd0pp-2025-01`` — series archived in the repository
  (``corpus/series/usd0pp_2025-01.json``, W3-C probe, pinned by
  ``replay/corpus_v1.manifest.json``). One forecast per EVAL window: ``p`` is the
  **signed G6 prior** ``P(obligation) = 0,20 per EVAL window`` (G6 §1). No
  empirical count is computed on the EVAL series — that would read the target
  window (B7 §d.2.4) — and ``p`` is never produced by an LLM (G6 §2).
* ``eval-rseth-2026-04`` — **not** instrumented: no archived market series
  exists. Nothing is fabricated; the window stays ``SKIPPED``.

Append-only in practice: the files are written only when absent. If they exist,
the chain and the forecast↔outcome binding are verified and **nothing is
rewritten** (``--check`` forces this read-only mode).

    python scripts/build_eval_forecasts.py           # create what is missing
    python scripts/build_eval_forecasts.py --check   # verify only, no write
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, os.path.join(DEFAULT_REPO_ROOT, "src"))
sys.path.insert(0, SCRIPTS_DIR)

from orvyren.evaluation import forecasts as forecasts_mod  # noqa: E402
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402


def _builder():
    """``freeze_sprint0`` as a module (import only — ``build_all`` is not run)."""
    spec = importlib.util.spec_from_file_location(
        "freeze_sprint0", os.path.join(SCRIPTS_DIR, "freeze_sprint0.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_eval_forecasts.py",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT)
    parser.add_argument("--frozen-dir", default=None, help="default: <repo>/frozen")
    parser.add_argument("--check", action="store_true", help="verify only, write nothing")
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(args.repo_root)
    frozen_dir = args.frozen_dir or os.path.join(repo_root, "frozen")
    builder = _builder()
    forecasts_path = os.path.join(frozen_dir, builder.EVAL_FORECASTS_NAME)
    outcomes_path = os.path.join(frozen_dir, builder.EVAL_OUTCOMES_NAME)

    windows_mod.verify_frozen_package(frozen_dir)  # freeze first, always

    present = os.path.isfile(forecasts_path) and os.path.isfile(outcomes_path)
    if present or args.check:
        if not present:
            raise SystemExit("MISSING %s / %s — run without --check to create them"
                             % (builder.EVAL_FORECASTS_NAME, builder.EVAL_OUTCOMES_NAME))
        mode = "verified (no write — append-only)"
        result = None
    else:
        result = builder.write_eval_forecasts(frozen_dir, repo_root=repo_root)
        mode = "written"

    records = forecasts_mod.load_forecasts(forecasts_path)
    forecasts_mod.verify_forecast_chain(records, path=forecasts_path)
    outcomes = outcomes_mod.load_outcomes(outcomes_path)
    outcomes_mod.verify_outcome_chain(outcomes, path=outcomes_path)
    by_id = {record["forecast_id"]: record for record in records}
    for outcome in outcomes:
        outcomes_mod.check_link(by_id[outcome["forecast_id"]], outcome)

    print("frozen dir : %s" % frozen_dir)
    for record, outcome in zip(records, outcomes):
        print("forecast   : %s  set=%s  p=%.2f  rule=%s  sha256=%s…"
              % (record["forecast_id"], record["set"], record["p"],
                 record["resolution_rule_id"], record["sha256"][:16]))
        print("             t_frozen %s → resolve_not_before %s (%s, %.1f h)"
              % (record["horizon"]["t_frozen_utc"], record["horizon"]["resolve_not_before_utc"],
                 record["horizon"]["kind"], record["horizon"]["hours"]))
        print("             signed_by: %s" % record["signed_by"])
        print("outcome    : %s  y=%d  n_obs=%d  min=%.4f  max_discount=%.4f%%  runs=%d"
              % (outcome["outcome_id"], outcome["y"], outcome["observed"]["n_observations"],
                 outcome["observed"]["min_price"], outcome["observed"]["max_discount_pct"],
                 outcome["observed"]["sustained_runs"]))
        print("             written_at %s · forecast_hash %s…"
              % (outcome["written_at_utc"], outcome["forecast_hash"][:16]))
    print("chains     : OK (%d forecast(s), %d outcome(s)) · link OK · %s"
          % (len(records), len(outcomes), mode))
    if result:
        print("digests    : %s %s · %s %s"
              % (builder.EVAL_FORECASTS_NAME, result["forecasts_sha256"],
                 builder.EVAL_OUTCOMES_NAME, result["outcomes_sha256"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
