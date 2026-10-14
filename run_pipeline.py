#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — end-to-end pipeline orchestrator.

Runs the four stages in the order fixed by ARCHITECTURE_V1.md, then assembles
and prints the evidence summary that the competition deliverables reference:

    1. quality   -> evidence/quality_report.json + evidence/graph.sqlite
    2. decision  -> evidence/decision_usdc-2023-03.json + evidence/baseline_report.json
    3. policy    -> evidence/policy_execution_demo.json (ALLOW / DENY / REQUIRE_APPROVAL)
    4. audit     -> evidence/dossier_usdc-2023-03.md / .html

Every stage runs as a subprocess of this same interpreter; a failing stage is
reported honestly (exit code + stderr tail) and never silently skipped.
Usage:
    python run_pipeline.py            # run all stages, then summarise
    python run_pipeline.py --summary  # summarise existing evidence only
    python run_pipeline.py --stage decision
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "evidence")
DECISION_JSON = os.path.join(EVIDENCE, "decision_usdc-2023-03.json")
BASELINE_JSON = os.path.join(EVIDENCE, "baseline_report.json")
QUALITY_JSON = os.path.join(EVIDENCE, "quality_report.json")
POLICY_JSON = os.path.join(EVIDENCE, "policy_execution_demo.json")
DOSSIER_MD = os.path.join(EVIDENCE, "dossier_usdc-2023-03.md")
DOSSIER_HTML = os.path.join(EVIDENCE, "dossier_usdc-2023-03.html")
SUMMARY_JSON = os.path.join(EVIDENCE, "pipeline_summary.json")

# Stage name -> (script, [args]) in execution order.
STAGES = [
    ("quality", "run_quality.py", []),
    ("decision", "run_decision.py", []),
    ("policy", "run_execution_demo.py", []),
    ("audit", "run_audit.py", []),
]


def sha256_file(path):
    """SHA-256 of a file over LF-normalised bytes, or None when absent.

    Line-ending normalisation keeps recorded digests identical on every
    platform (Windows checkouts rewrite text files with CRLF).
    """
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        raw = fh.read()
    digest = hashlib.sha256()
    digest.update(raw.replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        return {"_unreadable": str(exc)}


def run_stage(name, script, args):
    path = os.path.join(HERE, script)
    if not os.path.exists(path):
        return {"stage": name, "script": script, "status": "MISSING_SCRIPT"}
    started = dt.datetime.now(dt.timezone.utc)
    proc = subprocess.run(
        [sys.executable, path, *args],
        cwd=HERE, capture_output=True, text=True, timeout=900,
    )
    return {
        "stage": name,
        "script": script,
        "status": "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})",
        "seconds": round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 2),
        "stdout_tail": proc.stdout.strip().splitlines()[-12:],
        "stderr_tail": proc.stderr.strip().splitlines()[-8:] if proc.returncode else [],
    }


def summarise():
    decision = read_json(DECISION_JSON) or {}
    baseline = read_json(BASELINE_JSON) or {}
    policy = read_json(POLICY_JSON) or {}
    quality = read_json(QUALITY_JSON) or {}

    dec = decision.get("decision", {}) if isinstance(decision, dict) else {}
    verdicts = decision.get("hypothesis_verdicts", {}) if isinstance(decision, dict) else {}
    cases = policy.get("cases", []) if isinstance(policy, dict) else []
    norm = quality.get("normalization") or {}
    corpus = quality.get("corpus") or {}
    coverage = quality.get("coverage") or {}
    provenance = quality.get("provenance") or {}
    hours_by_venue_count = coverage.get("hours_by_independent_venue_count") or {}
    hours_two_plus = sum(
        count for key, count in hours_by_venue_count.items()
        if str(key).isdigit() and int(key) >= 2
    )

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "case": decision.get("case") or "usdc-2023-03",
        "inputs": {
            "corpus_observations": norm.get("total") or corpus.get("rows"),
            "corpus_rejected": len(norm.get("rejected") or []),
            "data_quality_coverage": {
                "hours_in_window": (coverage.get("window") or {}).get("hours"),
                "hours_with_two_plus_independent_venues": hours_two_plus or None,
                "per_venue_hours_covered": {
                    venue: entry.get("hours_covered")
                    for venue, entry in (coverage.get("per_venue") or {}).items()
                    if isinstance(entry, dict)
                },
            },
            "provenance": {
                "claims_checked": provenance.get("claims_checked"),
                "all_chains_ok": provenance.get("ok"),
            },
            "hypothesis_verdicts": {
                key: (val.get("verdict") if isinstance(val, dict) else None)
                for key, val in verdicts.items()
            },
            "decision_verdict": dec.get("verdict"),
            "decision_action": dec.get("action"),
            "baseline": {
                "signals_main": len(baseline.get("signals_main", []) or []),
                "signals_control": len(baseline.get("signals_control", []) or []),
                "false_signals_control": baseline.get("false_signals_control"),
            },
            "policy_cases": [
                {"intent_id": c.get("intent_id"), "verdict": c.get("verdict"),
                 "deny_codes": c.get("deny_codes", [])}
                for c in cases
            ],
        },
        "artifacts": {
            os.path.basename(path): sha256_file(path)
            for path in (DECISION_JSON, BASELINE_JSON, QUALITY_JSON, POLICY_JSON,
                         DOSSIER_MD, DOSSIER_HTML)
        },
    }
    return summary


def print_summary(summary):
    inputs = summary["inputs"]
    print("=" * 78)
    print(f"ORVYREN-Core pipeline summary — {summary['generated_at']}")
    print(f"case: {summary['case']}")
    print("-" * 78)
    print(f"corpus observations : {inputs['corpus_observations']} "
          f"(rejected: {inputs.get('corpus_rejected')})")
    prov = inputs.get("provenance") or {}
    cov = inputs.get("data_quality_coverage") or {}
    print(f"provenance          : {prov.get('claims_checked')} claim(s) checked, "
          f"all chains ok = {prov.get('all_chains_ok')}")
    print(f"coverage            : {cov.get('hours_with_two_plus_independent_venues')} h "
          f"with >=2 independent price venues (window {cov.get('hours_in_window')} h)")
    for key, val in inputs["hypothesis_verdicts"].items():
        print(f"  {key} verdict       : {val}")
    print(f"decision            : {inputs['decision_verdict']}")
    action = inputs["decision_action"]
    if action:
        print(f"  action            : {action.get('type')} {action.get('amount_usdc')} "
              f"{action.get('asset')} {action.get('from_wallet')} -> {action.get('to_wallet')}")
    base = inputs["baseline"]
    print(f"baseline A0         : {base['signals_main']} signal(s) in crisis window, "
          f"{base['signals_control']} in control window "
          f"(false signals: {base['false_signals_control']})")
    print("policy cases        :")
    for case in inputs["policy_cases"]:
        codes = f" {case['deny_codes']}" if case.get("deny_codes") else ""
        print(f"  {case['intent_id']}: {case['verdict']}{codes}")
    print("-" * 78)
    print("artifacts (sha256):")
    for name, digest in summary["artifacts"].items():
        state = digest[:16] + "…" if digest else "MISSING"
        print(f"  {name:38s} {state}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="summarise existing evidence only")
    parser.add_argument("--stage", choices=[name for name, _, _ in STAGES],
                        help="run a single stage")
    args = parser.parse_args()

    os.makedirs(EVIDENCE, exist_ok=True)
    stages_run = []
    if not args.summary:
        wanted = [s for s in STAGES if args.stage is None or s[0] == args.stage]
        for index, (name, script, extra) in enumerate(wanted):
            print(f"--- stage: {name} ({script}) ---")
            result = run_stage(name, script, extra)
            stages_run.append(result)
            print(f"    {result['status']}"
                  + (f" in {result['seconds']}s" if "seconds" in result else ""))
            for line in result.get("stdout_tail", [])[-3:]:
                print(f"    | {line}")
            for line in result.get("stderr_tail", [])[-3:]:
                print(f"    ! {line}")
            if result["status"] != "OK":
                # A failed stage poisons the artefacts built from its output:
                # dependent stages are skipped, never run on stale inputs
                # (Astra review F05: policy/audit used to run after a
                # quality+decision failure).
                for skipped_name, skipped_script, _ in wanted[index + 1:]:
                    stages_run.append({
                        "stage": skipped_name,
                        "script": skipped_script,
                        "status": "SKIPPED (upstream failure)",
                    })
                    print(f"--- stage: {skipped_name} ({skipped_script}) ---")
                    print("    SKIPPED (upstream failure)")
                break

    summary = summarise()
    if stages_run:
        summary["stages"] = stages_run
    with open(SUMMARY_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print_summary(summary)
    print(f"\nsummary -> {SUMMARY_JSON}")

    failed = [s for s in stages_run if s["status"] != "OK"]
    if failed:
        print(f"WARNING: {len(failed)} stage(s) did not complete: "
              + ", ".join(f"{s['stage']} ({s['status']})" for s in failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
