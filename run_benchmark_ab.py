#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — ``run_benchmark_ab.py``: honest mini-benchmark A0 vs A2 (P0-5).

Runs both modes on the **same episodes and the same declared budgets**, several
times per case, and writes a comparison report that never claims superiority at
small N:

* ``A0`` — deterministic decision engine alone: ``python run_decision.py``
  (no agent search, no LLM; cost 0 by construction);
* ``A2`` — full system: ``python run_agents.py --replay journal`` (agents +
  critic + fragility gate, deterministic offline replay of recorded responses).

Both commands are invoked as **subprocesses and never modified**. Measured per
run: decision verdict (ALLOW/DENY/REQUIRE_APPROVAL/NO_ACTION/abstention),
quality vs the declared expectation, abstentions, cost USD, latency, LLM/tool
calls, and claims rejected by the provenance validation.

Usage::

    python run_benchmark_ab.py --cases usdc-2023-03 placebo-calm-2023-03 \
        --runs 3 --out-dir evidence/benchmark_ab

Outputs (under ``--out-dir``): ``report.json`` (schema_version, run_id per
execution via ``orvyren.chain.new_run_id``, raw results per run) and
``report.md`` (comparative table + mandatory honesty banner + "when the agents
help / add nothing / must abstain" sections), plus the raw artefacts of every
run under ``raw/``.

Honesty contract (mechanical, see ``orvyren.evaluation.bench``): the banner
"small-N diagnostic run — no superiority claim (G1 threshold N>=100 not
reached)" is mandatory in every report; a superiority claim is refused below
N>=100; a failed or missing leg is reported as missing, never inferred.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Mapping, Optional

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from orvyren.evaluation import bench  # noqa: E402

DEFAULT_CASES_FILE = "fixtures/benchmark/cases.json"
DEFAULT_OUT_DIR = "evidence/benchmark_ab"
DEFAULT_RUNS = 2
DEFAULT_TIMEOUT_S = 600.0


def _resolve(path_arg: str) -> str:
    """Absolute path; relative arguments resolve against the repository root."""
    return path_arg if os.path.isabs(path_arg) else os.path.join(_REPO_ROOT, path_arg)


def _display(path: str) -> str:
    """Repo-relative POSIX path when inside the repository."""
    try:
        relative = os.path.relpath(path, _REPO_ROOT).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")
    return relative if not relative.startswith("..") else path.replace(os.sep, "/")


def _run_subprocess(cmd: List[str], timeout_s: float) -> Dict[str, Any]:
    """Run one CLI subprocess; never raises on a non-zero exit (reported raw)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    started = time.monotonic()
    try:
        completed = subprocess.run(cmd, cwd=_REPO_ROOT, env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "wall_seconds": time.monotonic() - started,
                "stdout_tail": "", "stderr_tail": "subprocess exceeded --timeout-s %.0fs" % timeout_s}
    tail = lambda text: (text or "")[-2000:]  # noqa: E731
    return {"exit_code": completed.returncode,
            "wall_seconds": time.monotonic() - started,
            "stdout_tail": tail(completed.stdout),
            "stderr_tail": tail(completed.stderr)}


def _read_json(path: str) -> Optional[Mapping[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _read_journal(path: str) -> List[Mapping[str, Any]]:
    entries: List[Mapping[str, Any]] = []
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, Mapping):
                entries.append(entry)
    return entries


def runner_a0(case: Mapping[str, Any], run_dir: str, run_index: int,
              timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    """Real A0 runner: ``python run_decision.py`` (subprocess, unmodified)."""
    os.makedirs(run_dir, exist_ok=True)
    case_id = str(case["case_id"])
    corpus = case.get("corpus")
    if corpus:
        corpus_arg = _resolve(str(corpus))
    else:
        if not case.get("synthetic"):
            raise bench.CasesError("case %r has no corpus and is not synthetic" % case_id)
        corpus_arg = os.path.join(run_dir, "corpus.csv")
        bench.materialize_synthetic_corpus(case, corpus_arg)
    cmd = [sys.executable, "run_decision.py", "--case", case_id,
           "--corpus", corpus_arg, "--out-dir", run_dir]
    if not case.get("a0_rdof", True):
        # Declared substitution: the RDOF/axes enrichment is scoped to case
        # 'usdc-2023-03' (predicate.case_scope) — other cases run the v0 engine.
        cmd.append("--no-rdof")
    proc = _run_subprocess(cmd, timeout_s)
    payload: Dict[str, Any] = {"exit_code": proc["exit_code"],
                               "wall_seconds": proc["wall_seconds"],
                               "output_tail": proc["stdout_tail"] or proc["stderr_tail"]}
    if proc["exit_code"] != 0:
        payload["status"] = "error"
        payload["error"] = (proc["stderr_tail"] or proc["stdout_tail"]).strip().splitlines()[-1:] or ["exit %d" % proc["exit_code"]]
        payload["error"] = payload["error"][0]
        return payload
    record = None
    for name in sorted(os.listdir(run_dir)):
        if name.startswith("decision_") and name.endswith(".json"):
            record = _read_json(os.path.join(run_dir, name))
    if record is None:
        payload["status"] = "error"
        payload["error"] = "no decision_*.json written under %s" % _display(run_dir)
        return payload
    payload["status"] = "ok"
    payload["decision_record"] = record
    return payload


def runner_a2(case: Mapping[str, Any], run_dir: str, run_index: int,
              budget: Optional[Mapping[str, Any]] = None,
              timeout_s: float = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    """Real A2 runner: ``python run_agents.py --replay journal`` (subprocess).

    A case without recorded agent inputs has no legal A2 leg (a replay may only
    consume recorded responses): the subprocess is still attempted and its
    refusal (e.g. ``E_CASE_UNKNOWN``) is recorded verbatim as ``not_executed``.
    """
    os.makedirs(run_dir, exist_ok=True)
    agent_case = str(case.get("a2_case_id") or case["case_id"])
    cmd = [sys.executable, "run_agents.py", "--case", agent_case,
           "--replay", "journal", "--session", run_dir]
    budget = budget or {}
    for flag, key in (("--budget-llm", "llm_calls"), ("--budget-tools", "tool_calls"),
                      ("--budget-wall", "wall_seconds"), ("--budget-usd", "cost_usd")):
        if key in budget:
            cmd.extend([flag, str(budget[key])])
    proc = _run_subprocess(cmd, timeout_s)
    payload: Dict[str, Any] = {"exit_code": proc["exit_code"],
                               "wall_seconds": proc["wall_seconds"],
                               "output_tail": proc["stdout_tail"] or proc["stderr_tail"]}
    if proc["exit_code"] != 0:
        message = (proc["stderr_tail"] or proc["stdout_tail"]).strip().splitlines()
        payload["status"] = "not_executed" if any("E_CASE_UNKNOWN" in line for line in message) else "error"
        payload["error"] = message[-1] if message else "exit %d" % proc["exit_code"]
        return payload

    newest: Optional[str] = None
    for current, _dirs, files in os.walk(run_dir):
        if "run_outcome.json" in files:
            candidate = os.path.join(current, "run_outcome.json")
            if newest is None or candidate > newest:
                newest = candidate
    run_outcome = _read_json(newest) if newest else None
    if run_outcome is None:
        payload["status"] = "error"
        payload["error"] = "no run_outcome.json under %s" % _display(run_dir)
        return payload
    journal_entries: List[Mapping[str, Any]] = []
    run_artifact_dir = os.path.dirname(newest)
    for role in ("orchestrator", "critic"):
        journal_entries.extend(_read_journal(os.path.join(run_artifact_dir, "journal_%s.jsonl" % role)))
    payload["status"] = "ok"
    payload["run_outcome"] = run_outcome
    payload["journal_entries"] = journal_entries
    return payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_benchmark_ab.py",
        description="Honest mini-benchmark A0 (deterministic engine) vs A2 (full agents) "
                    "on the same episodes and budgets (P0-5). Small-N diagnostic run — "
                    "no superiority claim.")
    parser.add_argument("--cases", nargs="*", default=None,
                        help="case ids from the fixture (default: every case in the fixture)")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                        help="runs k per mode per case (default: %(default)s)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help="output directory for report.json/report.md/raw artefacts "
                             "(default: %(default)s)")
    parser.add_argument("--cases-file", default=DEFAULT_CASES_FILE,
                        help="case fixture with declared expectations (default: %(default)s)")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S,
                        help="per-subprocess timeout in seconds (default: %(default)s)")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    cases_path = _resolve(args.cases_file)
    out_dir = _resolve(args.out_dir)
    cases_payload = bench.load_cases(cases_path)
    budget = cases_payload.get("budget") or {}

    # Every ground-truth figure is verified against its source BEFORE running:
    # a figure that cannot be traced fails the benchmark instead of being
    # published (honesty contract of fixtures/benchmark/cases.json).
    mismatches = bench.verify_ground_truth(cases_payload, _REPO_ROOT)
    if mismatches:
        print("E_GROUND_TRUTH: %d figure(s) do not resolve to their declared source:" % len(mismatches))
        for row in mismatches:
            print("  - %s / %s: expected %r found %r (%s)" % (
                row.get("case_id"), row.get("claim"), row.get("expected"),
                row.get("found"), row.get("error")))
        return 2

    def _a0(case: Mapping[str, Any], run_dir: str, run_index: int) -> Mapping[str, Any]:
        return runner_a0(case, run_dir, run_index, timeout_s=args.timeout_s)

    def _a2(case: Mapping[str, Any], run_dir: str, run_index: int) -> Mapping[str, Any]:
        return runner_a2(case, run_dir, run_index, budget=budget, timeout_s=args.timeout_s)

    print("ORVYREN mini-benchmark A0 vs A2 — %s" % bench.BANNER)
    print("  cases   : %s" % ", ".join(args.cases or [case["case_id"] for case in cases_payload["cases"]]))
    print("  runs    : %d per mode per case" % args.runs)
    print("  budget  : %s (identical for both modes)" % json.dumps(budget, sort_keys=True))
    report = bench.run_benchmark(cases_payload, args.cases or [], args.runs, out_dir,
                                 _a0, _a2, budget=budget)

    for case in report.get("cases", []):
        for mode in bench.MODES:
            agg = case["aggregates"][mode]
            print("  %-22s %s: N=%d scored/%d runs · verdicts %s · match %s · abstentions %d · "
                  "cost $%s · claims rejected %s" % (
                      case["case_id"], mode, agg["n_scored"], agg["n_runs"],
                      agg["verdict_counts"] or "{}",
                      agg["quality_counts"].get(bench.QUALITY_MATCH, 0),
                      agg["abstentions"],
                      "%.4f" % agg["cost_usd_total"] if agg["cost_usd_total"] is not None else "—",
                      agg["claims_rejected_provenance_total"]))
    print("  artifacts : %s" % _display(out_dir))
    print("  report    : %s" % _display(os.path.join(out_dir, "report.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
