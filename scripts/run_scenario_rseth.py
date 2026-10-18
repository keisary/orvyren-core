#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — E2E demonstration scenario: rsETH / KelpDAO, April 2026.

One command chains the existing CLIs (never modified) under one run identity,
from the observed risk to a verified dry-run execution:

  0. live-key gate   python scripts/inspect_env_masked.py --require-live-keys
                     (a missing LLM key stops the run honestly — rc 2, never a
                     simulated run);
  1. agents LIVE     python run_agents.py --case rseth-2026-04 --replay live
                     --record-live  (real LLM calls, keys read from the process
                     environment loaded from the git-ignored scripts/demo/.env);
  2. decision        python run_decision.py --case rseth-2026-04 --corpus
                     fixtures/agents/rseth-2026-04/corpus_rseth.csv --out-dir
                     evidence/scenario_rseth/decision --no-rdof
                     (declared substitution: the v1 deterministic decision
                     engine is wired to the frozen USDC pilot windows/peg
                     hypotheses — see the report gaps; the case decision is the
                     LIVE agent outcome);
  3. execution       python run_executor.py --case rseth-2026-04 --ticks N
                     --dry-run --run-id <scenario id> --parent-run-id <agent
                     run id> --json --journal ... --ledger ...
                     (dry-run only: no signature, no key read; the run chain
                     `orvyren.chain` carries the explicit run_id);
  4. collect         evidence/scenario_rseth/: run.json, run_outcome.json,
                     evidence_packet.json, critique_report.json, decision/,
                     policy_verdicts.json, execution/ (tick journal + chain),
                     scenario_run.json, scenario_report.md.

Also: ``--materialize-corpus`` writes fixtures/agents/rseth-2026-04/corpus_rseth.csv
(hourly rsETH oracle readings, each row carrying its source_ref) derived from
evidence/episode_rseth_2026-04.json — the corpus is derived data, and
tests/test_fixtures_rseth_inputs.py re-derives it from the episode at runtime.

Stdlib only. No secret is ever printed: the environment file is loaded into the
child processes and only presence/length is reported.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASE_ID = "rseth-2026-04"
#: The v1 decision dossier (RDOF + A1-A5 abstention) is only constructible for
#: the frozen pilot case: any other case id fails closed with
#: ``E_WHAT_WOULD_CHANGE_REQUIRED`` (measured, see the execution case probe of
#: the scenario). The executor CLI replays ``build_decision_record`` per tick
#: with no provider override, so the policy/execution leg runs on the pilot
#: decision as a **declared substitution** (the rsETH case decision is the
#: LIVE agent chain outcome, and the probe keeps the refusal as evidence).
EXECUTION_CASE_ID = "usdc-2023-03"
EXECUTION_REFUSAL_SIGNATURE = "decision unavailable"
DEFAULT_OUT_DIR = os.path.join("evidence", "scenario_rseth")
ENV_FILE = os.path.join("scripts", "demo", ".env")
EPISODE_PATH = os.path.join("evidence", "episode_rseth_2026-04.json")
CORPUS_PATH = os.path.join("fixtures", "agents", CASE_ID, "corpus_rseth.csv")
FIXTURE_PATH = os.path.join("fixtures", "agents", CASE_ID, "run_inputs.json")

#: Report sections the audit narrative requires (risk -> hypotheses -> evidence
#: -> decision -> policy verdict -> execution, plus explicit gaps).
REPORT_SECTIONS = (
    "## 1. Risk observed",
    "## 2. Hypotheses",
    "## 3. Evidence",
    "## 4. Decision",
    "## 5. Policy verdict",
    "## 6. Execution",
    "## 7. Gaps and explicit lacunae",
    "## 8. Provenance and reproduction",
    "## 9. Raw step outputs",
)

EXIT_OK = 0
EXIT_KEYS_MISSING = 2
EXIT_STEP_FAILED = 5


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _configure_stdio() -> None:
    """Force UTF-8 on stdout/stderr (Windows cp1252 consoles)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_env_file(path: str, env: dict) -> int:
    """Merge KEY=VALUE lines into ``env`` (values are never printed).

    Returns the number of variables loaded; a missing file loads nothing.
    """
    loaded = 0
    if not os.path.isfile(path):
        return loaded
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            if text.startswith("export "):
                text = text[len("export "):]
            key, _, value = text.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key:
                env[key] = value
                loaded += 1
    return loaded


def _run_command(argv, env, cwd, timeout_s):
    """Run one CLI as a subprocess (module level: tests swap this out)."""
    completed = subprocess.run(list(argv), cwd=cwd, env=env,
                               capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=timeout_s)
    return {"rc": completed.returncode,
            "stdout": completed.stdout or "",
            "stderr": completed.stderr or ""}


def _dump_stream(label: str, text: str) -> None:
    """Echo a subprocess stream in full (a swallowed stderr is a blind spot)."""
    text = str(text or "")
    if not text.strip():
        return
    print("    ---- %s ----" % label)
    for line in text.rstrip("\n").splitlines():
        print("    | %s" % line)


# ---------------------------------------------------------------------------
# Derived corpus (fixtures/agents/rseth-2026-04/corpus_rseth.csv)
# ---------------------------------------------------------------------------
def corpus_rows(episode: dict) -> list:
    """Hourly rsETH oracle readings of the episode, one sourced CSV row each."""
    generated = str(episode.get("meta", {}).get("generated_utc") or "")
    retrieved = generated.replace("Z", "+00:00")
    rows = []
    for key in sorted(episode.get("series", {})):
        state = (episode["series"].get(key) or {}).get("rsETH") or {}
        price = state.get("oracle_price")
        if price is None:
            continue
        rows.append({
            "timestamp_utc": str(key).replace("Z", "+00:00"),
            "venue": "aave_oracle",
            "metric": "price_usd",
            "value": repr(float(price)),
            "extra": ("source_ref=evidence/episode_rseth_2026-04.json"
                      "#series[\"%s\"].rsETH.oracle_price" % key),
            "retrieved_at": retrieved,
        })
    return rows


def materialize_corpus(episode_path: str = None, out_path: str = None) -> int:
    """Write the derived corpus CSV; returns the number of rows written."""
    episode_path = episode_path or os.path.join(REPO_ROOT, EPISODE_PATH)
    out_path = out_path or os.path.join(REPO_ROOT, CORPUS_PATH)
    episode = _read_json(episode_path)
    rows = corpus_rows(episode)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp_utc", "venue", "metric", "value", "extra",
                        "retrieved_at"],
            lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def build_steps(*, case_id: str, out_dir: str, run_id: str, ticks: int,
                parent_run_id: str = "") -> list:
    """The four CLI steps of the scenario (argv lists, repo-root relative)."""
    session_dir = os.path.join(out_dir, "agents_session")
    decision_dir = os.path.join(out_dir, "decision")
    execution_dir = os.path.join(out_dir, "execution")
    python = sys.executable
    steps = [
        {"name": "keys",
         "argv": [python, os.path.join("scripts", "inspect_env_masked.py"),
                  "--require-live-keys"],
         "timeout_s": 60},
        {"name": "agents",
         "argv": [python, "run_agents.py", "--case", case_id,
                  "--replay", "live", "--record-live",
                  "--session", session_dir,
                  # the live critic can outgrow the default 300 s per worker
                  "--timeout-s", "900"],
         "timeout_s": 1800},
        {"name": "decision",
         "argv": [python, "run_decision.py", "--case", case_id,
                  "--corpus", CORPUS_PATH, "--out-dir", decision_dir,
                  "--no-rdof"],
         "timeout_s": 300},
        {"name": "execution_case_probe",
         "argv": [python, "run_executor.py", "--case", case_id,
                  "--ticks", str(ticks), "--dry-run",
                  "--run-id", "%s-case-probe" % run_id,
                  "--parent-run-id", parent_run_id,
                  "--json",
                  "--journal", os.path.join(execution_dir, "case_attempt",
                                            "journal.jsonl"),
                  "--ledger", os.path.join(execution_dir, "case_attempt",
                                           "ledger.json")],
         "timeout_s": 300},
        {"name": "execution",
         "argv": [python, "run_executor.py", "--case", EXECUTION_CASE_ID,
                  "--ticks", str(ticks), "--dry-run",
                  "--run-id", run_id, "--parent-run-id", parent_run_id,
                  "--json",
                  "--journal", os.path.join(execution_dir, "journal.jsonl"),
                  "--ledger", os.path.join(execution_dir, "ledger.json")],
         "timeout_s": 300},
    ]
    return steps


def _list_run_dirs(session_dir: str) -> list:
    """Run directories of the session (directories holding run.json)."""
    if not os.path.isdir(session_dir):
        return []
    candidates = []
    for name in os.listdir(session_dir):
        path = os.path.join(session_dir, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, "run.json")):
            candidates.append(path)
    candidates.sort()
    return candidates


def _find_agents_run_dir(session_dir: str, known=()) -> str:
    """The run directory created by this invocation (newest of the new ones)."""
    candidates = _list_run_dirs(session_dir)
    fresh = [path for path in candidates if path not in set(known or ())]
    pool = fresh or candidates
    return pool[-1] if pool else ""


def _copy_into(src: str, dst: str) -> str:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def collect_artifacts(*, out_dir: str, agents_run_dir: str, run_id: str,
                      parent_run_id: str) -> dict:
    """Copy the run artifacts under evidence/scenario_rseth/ and index them."""
    collected = {}
    mapping = [
        ("run.json", os.path.join(agents_run_dir, "run.json")),
        ("run_outcome.json", os.path.join(agents_run_dir, "run_outcome.json")),
        ("outcome_orchestrator.json",
         os.path.join(agents_run_dir, "outcome_orchestrator.json")),
        ("evidence_packet.json",
         os.path.join(agents_run_dir, "exchanges", "001_evidence_packet.json")),
        ("critique_report.json",
         os.path.join(agents_run_dir, "exchanges", "002_critique_report.json")),
        ("journal_orchestrator.jsonl",
         os.path.join(agents_run_dir, "journal_orchestrator.jsonl")),
        ("journal_critic.jsonl",
         os.path.join(agents_run_dir, "journal_critic.jsonl")),
    ]
    for name, src in mapping:
        if os.path.isfile(src):
            collected[name] = _copy_into(src, os.path.join(out_dir, name))

    execution_dir = os.path.join(out_dir, "execution")
    if os.path.isdir(execution_dir):
        for dirpath, dirnames, filenames in os.walk(execution_dir):
            dirnames.sort()
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, out_dir).replace(os.sep, "/")
                collected[rel] = path

    decision_dir = os.path.join(out_dir, "decision")
    if os.path.isdir(decision_dir):
        for name in sorted(os.listdir(decision_dir)):
            path = os.path.join(decision_dir, name)
            if os.path.isfile(path):
                collected["decision/" + name] = path

    # Policy verdicts: rebuilt from the tick journal (file-based, robust).
    # The journal is append-only across runs: only this run's ticks enter the
    # verdict extract (the full journal stays available as its own artifact).
    journal_path = os.path.join(execution_dir, "journal.jsonl")
    ticks = []
    journal_records = 0
    if os.path.isfile(journal_path):
        with open(journal_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                journal_records += 1
                if str(record.get("run_id") or "") != str(run_id):
                    continue
                ticks.append({
                    "tick": record.get("tick"),
                    "case": record.get("case"),
                    "run_id": record.get("run_id"),
                    "verdict": record.get("verdict"),
                    "policy_verdict": record.get("policy_verdict"),
                    "outcome": record.get("outcome"),
                    "reasons": record.get("reasons"),
                    "rules_evaluated": record.get("rules_evaluated"),
                    "skipped_rules": record.get("skipped_rules"),
                    "policy_version": record.get("policy_version"),
                    "policy_hash": record.get("policy_hash"),
                    "chain": record.get("chain"),
                })
    policy_verdicts = {
        "schema": "orvyren/scenario-policy-verdicts/v1",
        "case_id": CASE_ID,
        "run_id": run_id,
        "parent_run_id": parent_run_id,
        "journal_records_total": journal_records,
        "ticks": ticks,
    }
    path = os.path.join(out_dir, "policy_verdicts.json")
    _write_json(path, policy_verdicts)
    collected["policy_verdicts.json"] = path
    return collected


#: The case's missing facts that would change the verdicts — the research plan
#: of the abstention (each entry names the fact, where to buy it and its cost).
CASE_PREDICATES = (
    {"predicate_id": "RSETH-P-MARKET-SERIES",
     "name": "an archived rsETH market/exit series over 2026-04-18..20 (L-1)",
     "source": "market archives (DeFiLlama/Binance) — absent from the measured corpus",
     "cost_queries": 2, "cost_seconds": 0.65},
    {"predicate_id": "RSETH-P-ORACLE-FRESHNESS",
     "name": "the oracle updatedAt at the freeze — latestRoundData() reverts on the capped feed (L-2)",
     "source": "eth_call on the capped rsETH/ETH/USD feed",
     "cost_queries": 1, "cost_seconds": 0.65},
    {"predicate_id": "RSETH-P-CAP-RATIO-WINDOW",
     "name": "a dense cap_ratio series between 2026-04-18T18:00:00Z and 2026-04-18T19:03:59Z",
     "source": "evidence/episode_rseth_2026-04.json key points + RPC archive (critic PIT finding)",
     "cost_queries": 1, "cost_seconds": 0.65},
    {"predicate_id": "RSETH-P-BAD-DEBT-LEDGER",
     "name": "the per-account debt ledger behind the 123.7 / 230.1 M USD bad debt (L-3)",
     "source": "Aave per-account data",
     "cost_queries": 3, "cost_seconds": 0.65},
    {"predicate_id": "RSETH-P-RSETH-TOOL-OBS",
     "name": "a discriminating rsETH tool observation in the run refs (critic BLOQUANT: the packet carried USDC series)",
     "source": "an rsETH series in the measured corpus (corpus/ not populated for rsETH)",
     "cost_queries": 1, "cost_seconds": 0.65},
)

#: Utilisation of the rsETH reserve at the freeze — the measurement that
#: refutes the counter-intuitive competitor (no hand figure: the record cites
#: its source_ref and the crossing test verifies it).
REFUTING_REF = ("evidence:episode_rseth_2026-04.json"
                "#series[\"2026-04-18T19:03:59Z\"].rsETH.utilisation")


def build_case_abstention(*, out_dir: str, agents_run_dir: str,
                          case_id: str) -> dict:
    """Build the case decision as a documented abstention (A1-A5, B3 §c).

    The v1 decision dossier can only enumerate ``what_would_change`` from
    predicates scoped to the pilot case (``E_WHAT_WOULD_CHANGE_REQUIRED`` for
    any other case id — measured live in ``execution/case_attempt/``). Rather
    than forcing a decision, this stage produces the case decision through the
    documented abstention path (``orvyren.decision.abstention``:
    ``detect_conditions`` -> ``what_would_change_entries`` ->
    ``escalate_vs_no_action`` -> ``build_inconclusive``) with the case's own
    missing facts as the research plan.
    """
    if os.path.join(REPO_ROOT, "src") not in sys.path:
        sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    from orvyren.decision import abstention as abstention_mod

    fixture = _read_json(os.path.join(REPO_ROOT, FIXTURE_PATH))
    lacunes = {row.get("lacune_id"): row.get("question")
               for row in fixture.get("lacunes", [])}
    outcome, spec, run_outcome = {}, {}, {}
    if agents_run_dir:
        for name, target in (("outcome_orchestrator.json", "outcome"),
                             ("run.json", "spec"),
                             ("run_outcome.json", "run_outcome")):
            path = os.path.join(agents_run_dir, name)
            if os.path.isfile(path):
                payload = _read_json(path)
                if target == "outcome":
                    outcome = payload
                elif target == "spec":
                    spec = payload
                else:
                    run_outcome = payload
    budget_used = outcome.get("budget_used") or {}
    budget_caps = spec.get("budget") or {}
    stop = str(outcome.get("stop_condition") or "")

    missing_by_hypothesis = {
        "HYP-001": ["the run's tool refs carry no rsETH observation (critic "
                    "BLOQUANT finding) — a discriminating tool observation of "
                    "the freeze is still missing"],
        "HYP-002": ["L-1: %s" % lacunes.get("L-1", ""),
                    "L-2: %s" % lacunes.get("L-2", "")],
        "HYP-003": ["a dense cap_ratio series between 2026-04-18T18:00:00Z "
                    "and 2026-04-18T19:03:59Z (critic PIT finding)"],
        "HYP-004": [],
    }
    verdicts = {}
    for row in fixture.get("hypotheses", []):
        counter = bool(row.get("counter_intuitive"))
        verdicts[row.get("id")] = {
            "verdict": "REFUTED" if counter else "INCONCLUSIVE",
            "enonce": row.get("enonce"),
            "missing_inputs": list(missing_by_hypothesis.get(row.get("id"), [])),
            "basis": (REFUTING_REF if counter else ""),
        }

    conditions = abstention_mod.detect_conditions(
        verdicts, integrity_flags=(), rdof_result=None,
        policy_verdict=None, convention_ambiguous=False)
    entries = abstention_mod.what_would_change_entries(CASE_PREDICATES, verdicts)
    escalade = abstention_mod.escalate_vs_no_action(
        conclusive=False,
        bounded_potential_loss=False,
        budget_exhausted=False,
        survivors_opposite_costly=True,
        integrity_ok=True)
    abstention_payload = abstention_mod.build_inconclusive(
        verdicts, conditions, entries,
        decision_delta={
            "si_H1_soutenue": "no autonomous transfer is even possible: the "
                              "reserve is frozen — document and escalate",
            "si_H2_soutenue": "reduce the rsETH exposure off the oracle "
                              "valuation (bounded x*) once an archived market "
                              "series confirms the decoupling",
            "si_H3_soutenue": "the supply-cap constraint is the binding "
                              "mechanism: no new rsETH deposits, monitor the "
                              "cap and the freeze bit",
            "si_H4_soutenue": "a liquidity squeeze would call for a cash "
                              "buffer on the WETH side instead of an rsETH "
                              "action (refuted by the measured utilisation)",
        },
        budget={
            "consomme": {"appels": budget_used.get("llm_calls", 0),
                         "secondes": budget_used.get("wall_seconds", 0),
                         "cout_usd": budget_used.get("cost_usd", 0.0)},
            "limites": {"appels": budget_caps.get("llm_calls"),
                        "secondes": budget_caps.get("wall_seconds"),
                        "cout_usd": budget_caps.get("cost_usd")},
            "reste": {"recherches": 0},
            "raison_arret": stop,
        },
        escalade=escalade if escalade.get("sortie") == "ESCALATE" else None)

    critique = run_outcome.get("critique") or {}
    record = {
        "schema": "orvyren/scenario-decision/v1",
        "case_id": case_id,
        "mode": "live",
        "epistemic_verdict": "INCONCLUSIVE",
        "action": None,
        "abstention": abstention_payload,
        "verdicts": verdicts,
        "what_would_change": entries,
        "escalade": escalade,
        "engine_record": "decision/decision_%s.json" % case_id,
        "engine_record_note": (
            "v0 deterministic engine record of the same run — the v1 engine is "
            "wired to the pilot case (frozen windows + peg hypotheses); this "
            "abstention is the case decision"),
        "agent_run_id": spec.get("run_id"),
        "agent_stop_condition": stop,
        "agent_escalation": run_outcome.get("escalation"),
        "agent_critique_verdict": critique.get("verdict_lecture"),
        "sources": {
            "fixture": FIXTURE_PATH,
            "hypotheses": [row.get("id") for row in fixture.get("hypotheses", [])],
            "refuting_measurement": REFUTING_REF,
            "abstention_module": "src/orvyren/decision/abstention.py",
        },
    }
    decision_dir = os.path.join(out_dir, "decision")
    os.makedirs(decision_dir, exist_ok=True)
    path = os.path.join(decision_dir, "abstention_%s.json" % case_id)
    _write_json(path, record)
    return record


def _fixture_figures() -> dict:
    """Figures of the fixture, measured from the fixture at runtime."""
    fixture = _read_json(os.path.join(REPO_ROOT, FIXTURE_PATH))
    return {"fixture": fixture,
            "facts": fixture.get("snapshot", {}).get("facts", {}),
            "hypotheses": fixture.get("hypotheses", []),
            "lacunes": fixture.get("lacunes", [])}


def figure_index(fixture: dict) -> dict:
    """Named figures measured from the fixture rows (never hand-copied)."""
    figures = {}
    buckets = fixture.get("tool_fixtures", {})
    for row in (buckets.get("prices", {}).get("chainlink|rsETH-USD") or []):
        figures["oracle_at_" + str(row.get("ts"))] = row.get("value")
    for row in (buckets.get("prices", {}).get("market|rsETH-USD") or []):
        figures["market_price_usd"] = row.get("value")
    for row in (buckets.get("supply", {}).get("rseth") or []):
        figures["supply_at_" + str(row.get("ts"))] = row.get("value")
    for rows in (buckets.get("chain", {}) or {}).values():
        for row in rows or ():
            figures[str(row.get("param"))] = row.get("value")
    for signal_id, row in (buckets.get("signals", {}) or {}).items():
        figures[str(signal_id)] = row.get("value")
    for key, value in (fixture.get("snapshot", {}).get("facts", {}) or {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            figures.setdefault(str(key), value)
    return figures


def render_report(*, out_dir: str, run_id: str, parent_run_id: str,
                  collected: dict, steps: list) -> str:
    """The audit narrative: risk -> hypotheses -> evidence -> decision ->
    policy verdict -> execution, with the explicit gaps."""

    def rel(path):
        return str(path).replace("\\", "/")

    figures = _fixture_figures()
    figs = figure_index(figures["fixture"])
    facts = figures["facts"]
    outcome = {}
    critique = {}
    if os.path.isfile(os.path.join(out_dir, "run_outcome.json")):
        outcome = _read_json(os.path.join(out_dir, "run_outcome.json"))
    if os.path.isfile(os.path.join(out_dir, "critique_report.json")):
        critique = _read_json(os.path.join(out_dir, "critique_report.json"))
    verdicts = {}
    decision_payload = {}
    decision_path = os.path.join(out_dir, "decision",
                                "decision_%s.json" % CASE_ID)
    if os.path.isfile(decision_path):
        decision_payload = _read_json(decision_path)
        verdicts = decision_payload.get("hypothesis_verdicts", {})
    abstention = {}
    abstention_path = os.path.join(out_dir, "decision",
                                   "abstention_%s.json" % CASE_ID)
    if os.path.isfile(abstention_path):
        abstention = _read_json(abstention_path)
    policy = _read_json(os.path.join(out_dir, "policy_verdicts.json"))

    steps_line = "\n".join(
        "  - `%s` -> rc %s%s" % (step.get("name"), step.get("rc"),
                                (" (%s)" % step["verdict"])
                                if step.get("verdict") else "")
        for step in steps)
    probe = [step for step in steps if step.get("name") == "execution_case_probe"]
    probe_verdict = (probe[0].get("verdict") or "not run") if probe else "not run"
    ticks_line = "\n".join(
        "  - tick %s: verdict `%s` (policy `%s`, reasons: %s) — chain run_id "
        "%s verify_ok=%s" % (
            tick.get("tick"), tick.get("verdict"), tick.get("policy_verdict"),
            ", ".join(str(r) for r in (tick.get("reasons") or [])) or "-",
            (tick.get("chain") or {}).get("run_id"),
            (tick.get("chain") or {}).get("verify_ok"))
        for tick in policy.get("ticks", [])) or "  - (no tick recorded)"
    hypotheses_line = "\n".join(
        "  - %s%s [%s] — %s" % (
            h.get("id"),
            " (counter-intuitive)" if h.get("counter_intuitive") else "",
            h.get("etat"), h.get("enonce"))
        for h in figures["hypotheses"])
    lacunes_line = "\n".join(
        "  - %s — %s" % (row.get("lacune_id"), row.get("question"))
        for row in figures["lacunes"])
    verdict_lines = "\n".join(
        "  - %s %s (%s)" % (key, (verdicts.get(key) or {}).get("verdict"),
                           (verdicts.get(key) or {}).get("label"))
        for key in ("H1", "H2", "H3") if key in verdicts) or \
        "  - (deterministic engine record not found)"
    chain_rows = []
    for tick in policy.get("ticks", []):
        chain = tick.get("chain") or {}
        if chain:
            chain_rows.append(chain)
    chain_head = chain_rows[-1].get("events_head") if chain_rows else "-"

    text = "\n".join([
        "# Scenario report — rsETH / KelpDAO, April 2026 (E2E demonstration)",
        "",
        "Case `%s` · scenario run_id `%s` · agents run_id `%s` · executor "
        "run_id `%s` (parent `%s`)." % (CASE_ID, run_id, parent_run_id or "-",
                                        run_id, parent_run_id or "-"),
        "Every figure below is read from the sourced fixture "
        "(`%s`) at report time; each fixture figure points to its source and "
        "`tests/test_fixtures_rseth_inputs.py` crosses fixture against source "
        "at runtime." % rel(FIXTURE_PATH),
        "",
        REPORT_SECTIONS[0],
        "",
        "Observed risk (Aave v3 Ethereum Core, rsETH reserve, KelpDAO "
        "collateral): the reserve saturated its supply cap at %s (cap ratio "
        "%s, %s rsETH against a %s rsETH cap) and was administratively frozen "
        "at %s (isFrozen 0 -> 1, block %s; last unfrozen block %s). The "
        "oracle retained %s USD at the freeze (%s USD at the exploit instant "
        "2026-04-18T17:35:00Z, %s USD on 2026-04-20T00:00:00Z) while the "
        "market price is documented at %s USD — a documented divergence of "
        "%s %% — and the market itself was frozen (no realisable exit). The "
        "documented exploit posted %s rsETH as collateral against roughly %s "
        "USD of WETH borrowed." % (
            facts.get("supply_cap_saturation_utc"),
            figs.get("supply_cap_saturation_ratio"),
            figs.get("a_token_supply_at_cap_max"), figs.get("supply_cap"),
            facts.get("freeze_first_frozen_utc"),
            facts.get("freeze_first_frozen_block"),
            figs.get("isFrozen_last_unfrozen_block"),
            facts.get("oracle_at_freeze_usd"),
            figs.get("oracle_at_2026-04-18T17:35:00Z"),
            figs.get("oracle_at_2026-04-20T00:00:00Z"),
            facts.get("market_price_usd"),
            facts.get("oracle_market_divergence_pct"),
            facts.get("collateral_rseth_at_exploit"),
            facts.get("weth_borrowed_usd_at_exploit")),
        "",
        REPORT_SECTIONS[1],
        "",
        "Concurrent hypotheses (ACH-style, frozen before the run; one "
        "counter-intuitive competitor kept alive on purpose):",
        hypotheses_line,
        "",
        REPORT_SECTIONS[2],
        "",
        "The LIVE agents observed the tools of the run (real LLM calls). The "
        "sourced figures of the fixture and their sources:",
    ])

    rows = []
    fixtures = figures["fixture"].get("tool_fixtures", {})
    for bucket in ("prices", "supply", "chain", "signals"):
        for key in sorted(fixtures.get(bucket, {}) or {}):
            entries = fixtures[bucket][key]
            if isinstance(entries, dict):
                entries = [entries]
            for entry in entries:
                if not isinstance(entry, dict) or "value" not in entry:
                    continue
                rows.append("  - [%s|%s] %s = %s (%s)" % (
                    bucket, key, entry.get("param") or entry.get("ts")
                    or entry.get("window_label") or entry.get("method_ref"),
                    entry.get("value"), entry.get("source_ref")))
    text += "\n" + "\n".join(rows)

    abstention_block = "  - (abstention record not found)"
    if abstention:
        payload = abstention.get("abstention") or {}
        entries = abstention.get("what_would_change") or []
        escalade = abstention.get("escalade") or {}
        lines = [
            "  - epistemic verdict: %s (conditions: %s)" % (
                abstention.get("epistemic_verdict"),
                ", ".join(payload.get("conditions_declenchees", []) or []) or "-"),
            "  - action: %s — no autonomous transfer while the market is "
            "frozen and the evidence is inconclusive" % abstention.get("action"),
            "  - escalation: %s — %s" % (escalade.get("sortie"),
                                         escalade.get("motif")),
            "  - decision_delta: %s" % "; ".join(
                "%s -> %s" % item for item in
                sorted((payload.get("decision_delta") or {}).items())),
            "  - what_would_change (%d research entries):" % len(entries),
        ]
        for entry in entries:
            lines.append(
                "    - [%s] %s — cible: %s (%s; affects %s)" % (
                    entry.get("predicat"), entry.get("fait"),
                    entry.get("cible"), entry.get("cout_estime"),
                    ", ".join(entry.get("hypotheses_affectees") or [])))
        lines.append("  - verdicts: %s" % "; ".join(
            "%s %s" % (key, value.get("verdict"))
            for key, value in sorted((abstention.get("verdicts") or {}).items())))
        abstention_block = "\n".join(lines)

    raw_blocks = []
    for step in steps:
        raw_blocks.append("### step `%s` (rc %s)" % (step.get("name"),
                                                    step.get("rc")))
        for label in ("stdout_tail", "stderr_tail"):
            body = str(step.get(label) or "").rstrip("\n")
            raw_blocks.append("%s:" % label.replace("_tail", ""))
            raw_blocks.append("```")
            raw_blocks.extend(body.splitlines() or ["(empty)"])
            raw_blocks.append("```")
        raw_blocks.append("")

    text += "\n" + "\n".join([
        "",
        "Agent outcome (`run_outcome.json`): stop `%s`, inconclusive=%s, "
        "critique verdict `%s`, escalation `%s`." % (
            (outcome.get("outcome") or {}).get("stop_condition"),
            (outcome.get("outcome") or {}).get("inconclusive"),
            critique.get("verdict_lecture") or outcome.get("critique", {}).get(
                "verdict_lecture"),
            outcome.get("escalation")),
        "",
        REPORT_SECTIONS[3],
        "",
        "Case decision (LIVE agent chain): the run above — its outcome, "
        "evidence packet and critic verdict are the case-specific decision "
        "artifacts (`run_outcome.json`, `evidence_packet.json`, "
        "`critique_report.json`).",
        "",
        "Case decision — abstention built through the documented A1-A5 path "
        "(`orvyren.decision.abstention`: detect_conditions -> "
        "what_would_change_entries -> escalate_vs_no_action -> "
        "build_inconclusive), never a forced decision:",
        abstention_block,
        "",
        "Deterministic decision engine (`run_decision.py`, declared "
        "substitution): the v1 engine is wired to the frozen USDC pilot "
        "windows (FREEZE_V1 D1/D2) and peg hypotheses; on this case it "
        "records its own verdicts and missing inputs in "
        "`decision/decision_%s.json`:" % CASE_ID,
        verdict_lines,
        "",
        REPORT_SECTIONS[4],
        "",
        "Policy evaluated on the execution leg (real `policy_v1.yaml`, real "
        "state, fail-closed resolvers):",
        ticks_line,
        "",
        REPORT_SECTIONS[5],
        "",
        "Execution is always dry-run (no signature, no key read), chained "
        "under one run identity (`orvyren.chain`). The execution case probe "
        "(`%s` case, measured live in this run) ended `%s`: the v1 decision "
        "dossier is only constructible for the pilot case id and the executor "
        "CLI has no decision-provider override, so the policy/execution leg "
        "runs the pilot decision replay as a declared substitution "
        "(`--case %s`), chained under this scenario run id and parented to "
        "the agents run id:" % (CASE_ID, probe_verdict, EXECUTION_CASE_ID),
        steps_line,
        "  - chain events head: %s" % chain_head,
        "  - tick journal: `execution/journal.jsonl` (chained JSONL, "
        "append-only; `policy_verdicts.json` extracts this run's ticks), "
        "chain root `execution/chain/%s/`; the probe journal and chain are "
        "kept under `execution/case_attempt/`" % run_id,
        "",
        REPORT_SECTIONS[6],
        "",
        "Explicit lacunae of the case fixture:",
        lacunes_line,
        "",
        "Declared substitutions and limitations:",
        "  - the deterministic decision engine of v1 is wired to the USDC "
        "pilot (frozen windows + peg hypotheses, `python -m orvyren.decide` "
        "refuses other case ids): its record is chained evidence of the "
        "decision stage mechanics, not an rsETH conclusion;",
        "  - the v1 decision dossier (RDOF + A1-A5 abstention) is only "
        "constructible for the pilot case id: the execution case probe "
        "(`--case %s`) is kept under `execution/case_attempt/` with the "
        "measured refusal (`E_WHAT_WOULD_CHANGE_REQUIRED`); the executor tick "
        "decision therefore replays the pilot decision and the rsETH-specific "
        "conclusion is the agent chain's — with a frozen market the coherent "
        "action is no autonomous transfer;" % CASE_ID,
        "  - no recorded response store exists for this case yet: only the "
        "LIVE run is executed; an offline `--replay journal` replay needs a "
        "recorded store first (never simulated);",
        "  - the market price and the ~-31 % divergence are documentation "
        "figures (ORVYREN_DOC2_TECHNIQUE_COMPLET.md measurement 2), not "
        "archived market series (episode limitations).",
        "",
        REPORT_SECTIONS[7],
        "",
        "Reproduce: `(set -a; source %s; set +a; python %s)` then inspect "
        "`%s/`. Fixture: `%s`. Derived corpus: `%s` (re-derived and compared "
        "by `tests/test_fixtures_rseth_inputs.py`). Targeted tests: "
        "`python -m unittest tests.test_fixtures_rseth_inputs "
        "tests.test_scenario_rseth`. No key or secret is stored in any "
        "artifact of this directory." % (
            rel(ENV_FILE), rel(os.path.join("scripts", "run_scenario_rseth.py")),
            rel(DEFAULT_OUT_DIR), rel(FIXTURE_PATH), rel(CORPUS_PATH)),
        "",
    ])
    text += "\n" + "\n".join([REPORT_SECTIONS[8], ""] + raw_blocks)
    return text


def _collect_only(args, out_dir: str) -> int:
    """Re-render the artifacts/report of an existing run (replay of the
    collection stage: no CLI step is executed, nothing is regenerated beyond
    what the recorded artifacts carry)."""
    previous = {}
    manifest_path = os.path.join(out_dir, "scenario_run.json")
    if os.path.isfile(manifest_path):
        previous = _read_json(manifest_path)
    run_id = (args.run_id or "").strip() or str(previous.get("run_id") or "")
    if not run_id:
        print("E_SCENARIO_COLLECT: --collect-only needs --run-id or an "
              "existing scenario_run.json")
        return EXIT_STEP_FAILED
    agent_run_id = str(previous.get("agents_run_id")
                       or previous.get("executor_parent_run_id") or "")
    agents_run_dir = _find_agents_run_dir(
        os.path.join(out_dir, "agents_session"))
    if not agents_run_dir:
        print("E_SCENARIO_COLLECT: no agents run directory under %s/agents_session"
              % out_dir)
        return EXIT_STEP_FAILED
    build_case_abstention(out_dir=out_dir, agents_run_dir=agents_run_dir,
                          case_id=args.case)
    collected = collect_artifacts(out_dir=out_dir, agents_run_dir=agents_run_dir,
                                  run_id=run_id, parent_run_id=agent_run_id)
    steps = previous.get("steps") or []
    report = render_report(out_dir=out_dir, run_id=run_id,
                           parent_run_id=agent_run_id, collected=collected,
                           steps=steps)
    _write_text(os.path.join(out_dir, "scenario_report.md"), report)
    artifacts = {name: {"sha256": _sha256(path),
                        "bytes": os.path.getsize(path)}
                 for name, path in sorted(collected.items())}
    manifest = dict(previous)
    manifest.update({
        "schema": "orvyren/scenario-run/v1",
        "case_id": args.case,
        "run_id": run_id,
        "status": previous.get("status") or "OK",
        "agents_run_id": agent_run_id,
        "executor_run_id": run_id,
        "executor_parent_run_id": agent_run_id,
        "generated_utc": _now_iso(),
        "steps": steps,
        "artifacts": artifacts,
        "recollected_only": True,
    })
    _write_json(manifest_path, manifest)
    print("ORVYREN — collect-only %s · run_id %s" % (args.case, run_id))
    print("  artifacts    : %s (%d file(s))" % (out_dir, len(artifacts) + 2))
    print("  report       : %s" % os.path.join(out_dir, "scenario_report.md"))
    return EXIT_OK


def run_pipeline(argv=None, *, runner=None, env=None) -> int:
    """Run the whole scenario; returns the process exit code."""
    _configure_stdio()
    parser = argparse.ArgumentParser(
        prog="run_scenario_rseth.py",
        description="ORVYREN — E2E demonstration scenario rsETH/KelpDAO "
                    "April 2026 (agents LIVE -> decision -> policy -> dry-run "
                    "execution under one run_id).")
    parser.add_argument("--case", default=CASE_ID)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                        help="artifact directory (default: %(default)s)")
    parser.add_argument("--run-id", default=None,
                        help="explicit scenario run id (default: generated)")
    parser.add_argument("--ticks", type=int, default=1,
                        help="executor dry-run ticks (default: %(default)s)")
    parser.add_argument("--materialize-corpus", action="store_true",
                        help="only write the derived corpus CSV and exit")
    parser.add_argument("--collect-only", action="store_true",
                        help="re-render the artifacts and report of an "
                             "existing run from its recorded files (no CLI "
                             "step is executed)")
    args = parser.parse_args(argv)

    if args.materialize_corpus:
        count = materialize_corpus()
        print("corpus written: %s (%d rows)" % (CORPUS_PATH, count))
        return EXIT_OK

    run_id = (args.run_id or "").strip() or ("scenario-%s-%s" %
                                             (args.case, _utc_stamp()))
    out_dir = args.out_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(REPO_ROOT, out_dir)
    os.makedirs(out_dir, exist_ok=True)

    if args.collect_only:
        return _collect_only(args, out_dir)

    child_env = dict(os.environ if env is None else env)
    loaded = load_env_file(os.path.join(REPO_ROOT, ENV_FILE), child_env)

    # The derived corpus must exist before the decision leg (derived data,
    # re-verified against its source by the crossing test).
    if not os.path.isfile(os.path.join(REPO_ROOT, CORPUS_PATH)):
        materialize_corpus()

    agent_run_id = ""
    agents_run_dir = ""
    steps = build_steps(case_id=args.case, out_dir=args.out_dir,
                        run_id=run_id, ticks=args.ticks,
                        parent_run_id="PENDING_AGENT_RUN_ID")
    results = []
    exec_runner = runner or _run_command
    print("ORVYREN — E2E scenario %s · run_id %s" % (args.case, run_id))
    print("  env file     : %s (%d variable(s) loaded into child processes, "
          "values never printed)" % (ENV_FILE, loaded))

    for index, step in enumerate(steps):
        if step["name"] in ("execution_case_probe", "execution") and agent_run_id:
            # Rebuild the step with the real agents run id as chain parent.
            rebuilt = {row["name"]: row for row in build_steps(
                case_id=args.case, out_dir=args.out_dir, run_id=run_id,
                ticks=args.ticks, parent_run_id=agent_run_id)}
            steps[index] = rebuilt[step["name"]]
            step = steps[index]
        print("  [%s] %s" % (step["name"], " ".join(step["argv"][1:])))
        known_runs = ()
        if step["name"] == "agents":
            known_runs = _list_run_dirs(os.path.join(out_dir, "agents_session"))
        try:
            result = exec_runner(step["argv"], child_env, REPO_ROOT,
                                 step["timeout_s"])
        except subprocess.TimeoutExpired:
            result = {"rc": 124, "stdout": "",
                      "stderr": "timeout after %ss" % step["timeout_s"]}
        rc = int(result.get("rc", 1))
        step["rc"] = rc
        out_text = str(result.get("stdout") or "")
        err_text = str(result.get("stderr") or "")
        # Full streams, never truncated away: a swallowed stderr is a blind
        # spot (the keys step is the only place where values could appear, and
        # that script prints presence/length only).
        step["stdout_tail"] = out_text
        step["stderr_tail"] = err_text
        _dump_stream("stdout %s" % step["name"], out_text)
        _dump_stream("stderr %s" % step["name"], err_text)
        results.append(step)

        if step["name"] == "keys" and rc != 0:
            # Honest stop: a missing live key is never simulated.
            message = ("E_SCENARIO_KEYS: live LLM keys are not all present "
                       "(scripts/inspect_env_masked.py --require-live-keys "
                       "rc=%d) — stopping before any LLM call; no simulated "
                       "run is produced." % rc)
            print("  " + message)
            _write_json(os.path.join(out_dir, "scenario_run.json"), {
                "schema": "orvyren/scenario-run/v1",
                "case_id": args.case,
                "run_id": run_id,
                "status": "ABORTED_KEYS_MISSING",
                "error": message,
                "generated_utc": _now_iso(),
                "steps": [{k: s.get(k) for k in
                           ("name", "argv", "rc", "verdict", "stdout_tail", "stderr_tail")}
                          for s in results],
            })
            return EXIT_KEYS_MISSING
        if step["name"] == "execution_case_probe":
            combined = ((step.get("stdout_tail") or "")
                        + (step.get("stderr_tail") or ""))
            if rc == 0:
                step["verdict"] = "CASE_DECISION_REPLAY_OK"
                print("    case decision replay: OK")
            elif rc == 5 and (EXECUTION_REFUSAL_SIGNATURE in combined
                              or "E_WHAT_WOULD_CHANGE_REQUIRED" in combined):
                step["verdict"] = "REFUSED_E_WHAT_WOULD_CHANGE_REQUIRED"
                print("    case decision replay: REFUSED "
                      "(E_WHAT_WOULD_CHANGE_REQUIRED) — measured and kept as "
                      "evidence; the execution leg runs the pilot substitution")
            else:
                print("  E_SCENARIO_STEP: execution case probe ended with rc %d "
                      "and no measured refusal signature — stopping honestly."
                      % rc)
                _write_json(os.path.join(out_dir, "scenario_run.json"), {
                    "schema": "orvyren/scenario-run/v1",
                    "case_id": args.case,
                    "run_id": run_id,
                    "status": "FAILED",
                    "failed_step": step["name"],
                    "generated_utc": _now_iso(),
                    "steps": [{k: s.get(k) for k in
                               ("name", "argv", "rc", "verdict", "stdout_tail",
                                "stderr_tail")} for s in results],
                })
                return EXIT_STEP_FAILED
            continue
        if rc != 0:
            print("  E_SCENARIO_STEP: step %s failed with rc %d — stopping "
                  "honestly (no fabricated artifact)." % (step["name"], rc))
            _write_json(os.path.join(out_dir, "scenario_run.json"), {
                "schema": "orvyren/scenario-run/v1",
                "case_id": args.case,
                "run_id": run_id,
                "status": "FAILED",
                "failed_step": step["name"],
                "generated_utc": _now_iso(),
                "steps": [{k: s.get(k) for k in
                           ("name", "argv", "rc", "verdict", "stdout_tail", "stderr_tail")}
                          for s in results],
            })
            return EXIT_STEP_FAILED

        if step["name"] == "agents":
            run_dir = _find_agents_run_dir(
                os.path.join(out_dir, "agents_session"), known_runs)
            if not run_dir:
                print("  E_SCENARIO_COLLECT: agents run directory not found "
                      "under %s/agents_session" % out_dir)
                return EXIT_STEP_FAILED
            agents_run_dir = run_dir
            spec = _read_json(os.path.join(run_dir, "run.json"))
            agent_run_id = str(spec.get("run_id") or "")
            print("    agents run_id: %s" % agent_run_id)

        if step["name"] == "decision":
            # The case decision is an abstention built through the documented
            # A1-A5 path (never a forced decision): what_would_change is
            # mandatory for an INCONCLUSIVE outcome (B3 §c.3).
            abstention = build_case_abstention(
                out_dir=out_dir, agents_run_dir=agents_run_dir,
                case_id=args.case)
            entries = abstention.get("what_would_change") or []
            conditions = (abstention.get("abstention") or {}).get(
                "conditions_declenchees") or []
            sortie = (abstention.get("escalade") or {}).get("sortie") or "-"
            results.append({
                "name": "decision_abstention",
                "argv": ["<in-process>",
                         "orvyren.decision.abstention A1-A5 "
                         "(detect_conditions -> what_would_change_entries -> "
                         "escalate_vs_no_action -> build_inconclusive)"],
                "rc": 0,
                "verdict": sortie,
                "stdout_tail": ("abstention %s — action null; %d "
                                "what_would_change entr(ies); conditions %s"
                                % (sortie, len(entries),
                                   ",".join(conditions) or "-")),
                "stderr_tail": "",
            })
            print("    abstention  : %s — action null (%d what_would_change "
                  "entries)" % (sortie, len(entries)))

    if not agents_run_dir:
        agents_run_dir = _find_agents_run_dir(
            os.path.join(out_dir, "agents_session"))
    build_case_abstention(out_dir=out_dir, agents_run_dir=agents_run_dir,
                          case_id=args.case)
    collected = collect_artifacts(out_dir=out_dir,
                                  agents_run_dir=agents_run_dir,
                                  run_id=run_id,
                                  parent_run_id=agent_run_id)
    report = render_report(out_dir=out_dir, run_id=run_id,
                           parent_run_id=agent_run_id, collected=collected,
                           steps=results)
    _write_text(os.path.join(out_dir, "scenario_report.md"), report)

    artifacts = {}
    for name in sorted(collected):
        path = collected[name]
        artifacts[name] = {"sha256": _sha256(path), "bytes": os.path.getsize(path)}
    _write_json(os.path.join(out_dir, "scenario_run.json"), {
        "schema": "orvyren/scenario-run/v1",
        "case_id": args.case,
        "run_id": run_id,
        "status": "OK",
        "agents_run_id": agent_run_id,
        "executor_run_id": run_id,
        "executor_parent_run_id": agent_run_id,
        "generated_utc": _now_iso(),
        "steps": [{k: s.get(k) for k in
                   ("name", "argv", "rc", "verdict", "stdout_tail", "stderr_tail")}
                  for s in results],
        "artifacts": artifacts,
    })
    print("  artifacts    : %s (%d file(s))" % (out_dir, len(artifacts) + 2))
    print("  report       : %s" % os.path.join(out_dir, "scenario_report.md"))
    return EXIT_OK


main = run_pipeline


if __name__ == "__main__":
    sys.exit(run_pipeline())
