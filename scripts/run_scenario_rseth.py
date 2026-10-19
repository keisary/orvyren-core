#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — E2E demonstration scenario: rsETH / KelpDAO, April 2026.

One command chains the existing CLIs (never modified) under one run identity,
from the observed risk to a bounded dry-run execution. The case decision is the
one the reasoning agents actually produced — consumed through the
``orvyren.decision.agents_source`` bridge, never through a pilot replay:

  0. live-key gate   python scripts/inspect_env_masked.py --require-live-keys
                     (only when this invocation runs the agents live; a missing
                     LLM key stops the run honestly — rc 2, never a simulated
                     run);
  1. agents LIVE     python run_agents.py --case rseth-2026-04 --replay live
                     --record-live  (real LLM calls, keys read from the process
                     environment loaded from the git-ignored scripts/demo/.env).
                     Skipped when ``--agents-run <sealed dir>`` is given: the
                     sealed run is consumed as-is, no LLM call, no new spend;
  2. decision        ``build_decision_from_agents(<agents run>)`` reads run.json,
                     run_outcome.json and the hash-chained journals and writes a
                     DecisionRecord (schema ``orvyren-decision-record/v1``) to
                     ``decision/decision_agents_<case>.json``: hypotheses with
                     their agents state, critique verdict and findings, journal
                     chain heads, realised cost, and either a *declared* bounded
                     intent or an honest abstention (INCONCLUSIVE /
                     REQUIRE_APPROVAL / no economic action, no intent).
                     ``run_decision.py --no-rdof`` still runs, but only as a
                     pilot-scoped engine cross-check — never the case decision;
  3. execution       python run_executor.py --case rseth-2026-04 --ticks N
                     --dry-run --decision-source agents --agents-run <dir>
                     --run-id <scenario id> --parent-run-id <agent run id>
                     --json --journal ... --ledger ...
                     (the executor consumes the same bridge; an abstaining
                     record carries no intent, so the tick ends NO_ACTION with
                     no policy evaluation, no signature and no key read);
  4. verify+dossier  ``chain_verification.json`` compares the DecisionRecord's
                     axes (epistemic verdict, authorization verdict, economic
                     action, intent presence) with the executor's per-tick
                     ``decision_summary``, checks the chain run/parent ids and
                     records the journal chain heads recomputed by the bridge;
                     then evidence/scenario_rseth/: run.json, run_outcome.json,
                     evidence_packet.json, critique_report.json, decision/,
                     policy_verdicts.json, chain_verification.json, execution/
                     (tick journal + chain), scenario_run.json,
                     scenario_report.md.

``--decision-source corpus`` restores the LEGACY leg (the frozen USDC pilot
decision replayed under the rsETH run id, a declared substitution, with the
``E_WHAT_WOULD_CHANGE_REQUIRED`` case probe kept as evidence). It exists to
reproduce the superseded report; it is never the default and its report says so.

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
#: Decision sources of the execution leg. ``agents`` (default) consumes the
#: DecisionRecord built by ``orvyren.decision.agents_source`` from a sealed
#: agents run; ``corpus`` is the LEGACY pilot replay (declared substitution,
#: kept only to reproduce the superseded report).
DECISION_SOURCES = ("agents", "corpus")
#: The sealed run of this case (the one the packaged evidence cites).
AGENTS_RUN_ROOT = os.path.join("evidence", "demo_runs", "agents", CASE_ID)
SEALED_AGENTS_RUN = os.path.join(
    AGENTS_RUN_ROOT, "rseth-2026-04_live_20261018T200027592497Z")
#: Placeholder written by ``build_steps`` when the agents run of *this*
#: invocation is not known yet; ``run_pipeline`` rebuilds the step with the real
#: directory before executing it (never run as-is).
AGENTS_RUN_PLACEHOLDER = "<agents-run-dir>"
#: The DecisionRecord built from the agents run (schema-compatible with the
#: deterministic engine's record, so every consumer parses it the same way).
AGENTS_DECISION_FILENAME = "decision_agents_%s.json"
#: End-to-end verification artifact (decision -> policy -> execution chain).
VERIFICATION_FILENAME = "chain_verification.json"
#: The v1 decision dossier (RDOF + A1-A5 abstention) is only constructible for
#: the frozen pilot case: any other case id fails closed with
#: ``E_WHAT_WOULD_CHANGE_REQUIRED`` (measured, see the execution case probe of
#: the LEGACY corpus leg). The ``agents`` leg needs none of that: the executor
#: receives the DecisionRecord itself (``--decision-source agents``).
EXECUTION_CASE_ID = "usdc-2023-03"
EXECUTION_REFUSAL_SIGNATURE = "decision unavailable"
DEFAULT_OUT_DIR = os.path.join("evidence", "scenario_rseth")
ENV_FILE = os.path.join("scripts", "demo", ".env")
EPISODE_PATH = os.path.join("evidence", "episode_rseth_2026-04.json")
CORPUS_PATH = os.path.join("fixtures", "agents", CASE_ID, "corpus_rseth.csv")
FIXTURE_PATH = os.path.join("fixtures", "agents", CASE_ID, "run_inputs.json")

#: Report sections the audit narrative requires (risk -> hypotheses -> evidence
#: -> decision -> policy verdict -> execution -> chain verification, plus
#: explicit gaps and provenance).
REPORT_SECTIONS = (
    "## 1. Risk observed",
    "## 2. Hypotheses",
    "## 3. Evidence",
    "## 4. Decision",
    "## 5. Policy verdict",
    "## 6. Execution",
    "## 7. Chain verification",
    "## 8. Gaps and explicit lacunae",
    "## 9. Provenance and reproduction",
    "## 10. Raw step outputs",
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


def _display_path(path: str) -> str:
    """Repo-relative POSIX path when possible, absolute POSIX otherwise.

    ``os.path.relpath`` raises on Windows when the two paths sit on different
    drives (a temporary out-dir on C:, the repository on D:), so the fallback is
    explicit instead of a crash in the middle of a run.
    """
    if not path:
        return ""
    absolute = os.path.abspath(path)
    try:
        relative = os.path.relpath(absolute, REPO_ROOT)
    except ValueError:
        return absolute.replace("\\", "/")
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return absolute.replace("\\", "/")
    return relative.replace("\\", "/")


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
                parent_run_id: str = "", decision_source: str = "agents",
                agents_run_dir: str = "") -> list:
    """The CLI steps of the scenario (argv lists, repo-root relative).

    ``agents_run_dir`` empty means "run the agents live in this invocation":
    the key gate and the live agents step are then part of the chain and the
    execution step carries a placeholder agents directory that
    ``run_pipeline`` replaces once the run is sealed. Non-empty means the sealed
    run is consumed as-is (no LLM call at all).

    ``decision_source="corpus"`` is the LEGACY leg: it replays the frozen USDC
    pilot decision after a measured ``E_WHAT_WOULD_CHANGE_REQUIRED`` case probe
    — kept for reproducing the superseded report, never the default.
    """
    session_dir = os.path.join(out_dir, "agents_session")
    decision_dir = os.path.join(out_dir, "decision")
    execution_dir = os.path.join(out_dir, "execution")
    python = sys.executable
    steps = []
    if not agents_run_dir:
        steps.extend([
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
        ])
    # The deterministic engine record: a pilot-scoped cross-check of the same
    # case, kept in the dossier but never the case decision.
    steps.append({"name": "decision",
                  "argv": [python, "run_decision.py", "--case", case_id,
                           "--corpus", CORPUS_PATH, "--out-dir", decision_dir,
                           "--no-rdof"],
                  "timeout_s": 300})
    if decision_source == "corpus":
        steps.extend([
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
        ])
    else:
        steps.append({
            "name": "execution",
            "argv": [python, "run_executor.py", "--case", case_id,
                     "--ticks", str(ticks), "--dry-run",
                     "--decision-source", "agents",
                     "--agents-run", agents_run_dir or AGENTS_RUN_PLACEHOLDER,
                     "--run-id", run_id, "--parent-run-id", parent_run_id,
                     "--json",
                     "--journal", os.path.join(execution_dir, "journal.jsonl"),
                     "--ledger", os.path.join(execution_dir, "ledger.json")],
            "timeout_s": 300})
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
                    "executed": record.get("executed"),
                    "intent": record.get("intent"),
                    "decision_summary": record.get("decision_summary"),
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


class AgentsDecisionUnavailable(Exception):
    """The sealed agents run cannot yield a DecisionRecord (fail closed)."""


def _abs(path: str) -> str:
    """Repository-root relative path -> absolute (absolute paths untouched)."""
    text = str(path or "").strip()
    if not text:
        return text
    return os.path.normpath(text if os.path.isabs(text)
                            else os.path.join(REPO_ROOT, text))


def build_agents_decision(*, out_dir: str, agents_run_dir: str,
                          case_id: str) -> dict:
    """Build the case DecisionRecord from the sealed agents run (the bridge).

    ``orvyren.decision.agents_source`` reads only ``run.json``,
    ``run_outcome.json`` and the hash-chained journals, recomputes every chain
    head and never invents a figure. The record is written as-is to
    ``decision/decision_agents_<case>.json``: it *is* what the executor
    consumes, so the dossier and the execution leg cannot diverge.
    """
    if os.path.join(REPO_ROOT, "src") not in sys.path:
        sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    from orvyren.decision.agents_source import (AgentsSourceError,
                                                build_decision_from_agents)

    run_dir = _abs(agents_run_dir)
    try:
        record = build_decision_from_agents(run_dir, case_id=case_id)
    except AgentsSourceError as exc:
        raise AgentsDecisionUnavailable(str(exc))
    decision_dir = os.path.join(out_dir, "decision")
    os.makedirs(decision_dir, exist_ok=True)
    _write_json(os.path.join(decision_dir, AGENTS_DECISION_FILENAME % case_id),
                record)
    return record


def verify_chain(*, out_dir: str, run_id: str, agents_run_id: str,
                 agents_run_dir: str, decision_source: str,
                 case_id: str = CASE_ID) -> dict:
    """Prove the chain decision -> policy -> execution from the artifacts.

    Compares the axes of the DecisionRecord built by the bridge with the
    executor's per-tick ``decision_summary``, checks the chain run/parent ids and
    the chain verification flag, and records the identifiers of every stage.
    A mismatch is a FAILURE (the dossier must not ship a chain that does not
    hold) — never smoothed over.
    """
    payload = {
        "schema": "orvyren/scenario-chain-verification/v1",
        "case_id": case_id,
        "run_id": run_id,
        "agents_run_id": agents_run_id,
        "agents_run_dir": str(agents_run_dir or "").replace("\\", "/"),
        "decision_source": decision_source,
        "status": "UNVERIFIED",
        "failures": [],
        "checks": {},
        "citations": {},
        "ticks": [],
    }
    path = os.path.join(out_dir, VERIFICATION_FILENAME)

    def fail(message):
        payload["failures"].append(message)

    if decision_source != "agents":
        payload["status"] = "NOT_APPLICABLE"
        payload["reason"] = (
            "legacy corpus leg: the per-tick decision is the frozen USDC pilot "
            "replay (declared substitution), not an agents DecisionRecord — "
            "nothing to verify against an agents run")
        _write_json(path, payload)
        return payload

    record_path = os.path.join(out_dir, "decision",
                               AGENTS_DECISION_FILENAME % case_id)
    record = {}
    if not os.path.isfile(record_path):
        fail("decision record missing: %s" % record_path)
    else:
        record = _read_json(record_path)
        payload["citations"]["decision_record"] = {
            "path": os.path.relpath(record_path, out_dir).replace("\\", "/"),
            "sha256": _sha256(record_path),
            "schema": record.get("schema"),
        }
    if record.get("schema") != "orvyren-decision-record/v1":
        fail("decision record schema is %r, expected "
             "'orvyren-decision-record/v1'" % record.get("schema"))

    source = record.get("source") or {}
    payload["citations"]["agents_run"] = {
        "run_dir": source.get("run_dir"),
        "run_id": source.get("run_id"),
        "mode": source.get("mode"),
        "chain_heads": source.get("chain_heads") or {},
        "journal_lines": source.get("journal_lines") or {},
        "journals_verified": source.get("journals_verified") or {},
        "replayable": source.get("replayable"),
    }
    if source.get("run_id") != agents_run_id:
        fail("the decision record cites run %r, the scenario chains %r"
             % (source.get("run_id"), agents_run_id))
    if source.get("chain_heads") and not all(
            (source.get("journals_verified") or {}).values()):
        fail("at least one journal chain head was not verified by the bridge")

    payload["checks"]["decision_axes"] = {
        "epistemic_verdict": record.get("epistemic_verdict"),
        "economic_action": record.get("economic_action"),
        "authorization_verdict": record.get("authorization_verdict"),
        "intent_present": record.get("intent") is not None,
        "escalation": record.get("escalation"),
        "stop_condition": record.get("stop_condition"),
        "what_would_change_entries": len(record.get("what_would_change") or []),
    }

    # Stages before the decision: the collected evidence packet + critique.
    packet_path = os.path.join(out_dir, "evidence_packet.json")
    if os.path.isfile(packet_path):
        packet = _read_json(packet_path)
        payload["citations"]["evidence_packet"] = {
            "path": "evidence_packet.json",
            "packet_id": packet.get("packet_id"),
            "snapshot_ref": packet.get("snapshot_ref"),
            "refs_count": len(packet.get("refs") or []),
            "claims_count": len(packet.get("claims") or []),
        }
    critique_path = os.path.join(out_dir, "critique_report.json")
    if os.path.isfile(critique_path):
        critique = _read_json(critique_path)
        payload["citations"]["critique"] = {
            "path": "critique_report.json",
            "verdict": critique.get("verdict_lecture")
                       or (record.get("critique") or {}).get("verdict"),
            "findings_count": len(critique.get("findings") or []),
        }

    policy_path = os.path.join(out_dir, "policy_verdicts.json")
    policy = {}
    if not os.path.isfile(policy_path):
        fail("policy_verdicts.json missing: no tick journal was collected")
    else:
        policy = _read_json(policy_path)
        payload["citations"]["execution"] = {
            "journal": "execution/journal.jsonl",
            "journal_records_total": policy.get("journal_records_total"),
            "chain_root": "",
            "events_head": "",
            "verify_ok": None,
        }
    ticks = policy.get("ticks") or []
    if not ticks:
        fail("the execution leg recorded no tick for run_id %r "
             "(the scenario produced no policy/execution evidence)" % run_id)
    for tick in ticks:
        summary = tick.get("decision_summary") or {}
        chain = tick.get("chain") or {}
        checks = {
            "decision_summary_present": bool(summary),
            "epistemic_verdict_matches":
                summary.get("epistemic_verdict") == record.get("epistemic_verdict"),
            "authorization_verdict_matches":
                summary.get("authorization_verdict")
                == record.get("authorization_verdict"),
            "economic_action_matches":
                summary.get("economic_action") == record.get("economic_action"),
            "intent_absence_consistent":
                (tick.get("intent") is None) == (record.get("intent") is None),
            "chain_run_id_matches": chain.get("run_id") == run_id,
            "chain_parent_matches": chain.get("parent_run_id") == agents_run_id,
            "chain_verified": chain.get("verify_ok") is True,
            "not_executed": tick.get("executed") is False,
        }
        failed = sorted(name for name, ok in checks.items() if not ok)
        if failed:
            fail("tick %s: %s" % (tick.get("tick"), ", ".join(failed)))
        payload["ticks"].append({
            "tick": tick.get("tick"),
            "outcome": tick.get("outcome"),
            "verdict": tick.get("verdict"),
            "policy_verdict": tick.get("policy_verdict"),
            "reasons": tick.get("reasons") or [],
            "chain_run_id": chain.get("run_id"),
            "chain_parent_run_id": chain.get("parent_run_id"),
            "chain_events_head": chain.get("events_head"),
            "checks": checks,
        })
        if payload["citations"].get("execution") is not None:
            payload["citations"]["execution"]["chain_root"] = chain.get("root_dir")
            payload["citations"]["execution"]["events_head"] = chain.get("events_head")
            payload["citations"]["execution"]["verify_ok"] = chain.get("verify_ok")

    # -- the event chain itself: what the executor really recorded ----------
    chain_events = []
    chain_root = (payload["citations"].get("execution") or {}).get("chain_root") or ""
    events_path = os.path.join(str(chain_root), "events.jsonl") if chain_root else ""
    if events_path and os.path.isfile(events_path):
        with open(events_path, "r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    fail("unreadable line in the chain events")
                    continue
                chain_events.append(str(event.get("event") or ""))
        payload["citations"]["execution"]["events"] = chain_events
        named = [event for event in chain_events if event]
        if named and record.get("intent") is None:
            if "NO_ACTIONABLE_INTENT" not in named:
                fail("the chain never recorded NO_ACTIONABLE_INTENT although "
                     "the DecisionRecord carries no intent")
            forbidden = [event for event in named
                         if event.startswith("POLICY_") or event in
                         ("EXECUTED", "SIGNED", "DRY_RUN_EXECUTED")]
            if forbidden:
                fail("the chain recorded %s although the DecisionRecord carries "
                     "no intent" % ", ".join(sorted(set(forbidden))))
    elif chain_root:
        fail("chain events.jsonl not found under %s" % chain_root)

    payload["citations"]["dossier"] = {
        "manifest": "scenario_run.json",
        "report": "scenario_report.md",
        "verification": VERIFICATION_FILENAME,
    }
    payload["status"] = "FAIL" if payload["failures"] else "PASS"
    _write_json(path, payload)
    return payload


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
                  collected: dict, steps: list,
                  decision_source: str = "agents") -> str:
    """The audit narrative: risk -> hypotheses -> evidence -> decision ->
    policy verdict -> execution -> chain verification, with the explicit gaps.

    ``decision_source`` selects the narrative of the decision leg: ``agents``
    reads the DecisionRecord written by the bridge, ``corpus`` describes the
    legacy pilot substitution (kept to reproduce the superseded dossier).
    """

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
        "  - tick %s: outcome `%s`, verdict `%s`, policy `%s`, reasons: %s — "
        "chain run_id %s verify_ok=%s" % (
            tick.get("tick"), tick.get("outcome"), tick.get("verdict"),
            tick.get("policy_verdict") or "not evaluated",
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

    decision_source = decision_source or "agents"
    agents_record = {}
    record_path = os.path.join(out_dir, "decision",
                               AGENTS_DECISION_FILENAME % CASE_ID)
    if os.path.isfile(record_path):
        agents_record = _read_json(record_path)
    verification = {}
    verification_path = os.path.join(out_dir, VERIFICATION_FILENAME)
    if os.path.isfile(verification_path):
        verification = _read_json(verification_path)

    def _clean(value):
        if isinstance(value, float) and value.is_integer():
            return "%d" % int(value)
        return "%s" % value

    def _money(value):
        try:
            return "%.6f" % float(value)
        except (TypeError, ValueError):
            return "unavailable"

    def _seconds(value):
        try:
            return "%.2f" % float(value)
        except (TypeError, ValueError):
            return "unavailable"

    ticks = policy.get("ticks") or []
    intents = [tick for tick in ticks if tick.get("intent")]
    signatures = sum(1 for tick in ticks if tick.get("executed") is True)

    # -- section 4: the case decision (mode aware) --------------------------
    if decision_source == "agents" and agents_record:
        src = agents_record.get("source") or {}
        crit = agents_record.get("critique") or {}
        cost = (agents_record.get("research_cost") or {}).get("budget") or {}
        caps = (agents_record.get("research_cost") or {}).get("budget_declared") or {}
        hyps = agents_record.get("hypotheses") or []
        decision_lines = [
            "Case decision = the **DecisionRecord built from the sealed agents "
            "run** by `src/orvyren/decision/agents_source.py` "
            "(`build_decision_from_agents`), written unchanged to "
            "`decision/decision_agents_%s.json` (schema `%s`). This is the exact "
            "record the executor consumes — nothing is re-derived from the pilot "
            "corpus." % (CASE_ID, agents_record.get("schema")),
            "",
            "  - source run: `%s` (mode `%s`, %s journal line(s); chain heads "
            "recomputed from the journals: %s)" % (
                src.get("run_id"), src.get("mode"),
                _clean(sum((src.get("journal_lines") or {}).values())),
                ", ".join("%s `%s`" % (role, head) for role, head in
                          sorted((src.get("chain_heads") or {}).items()))),
            "  - epistemic verdict `%s` · economic action `%s` · intent `%s` · "
            "authorization `%s`" % (
                agents_record.get("epistemic_verdict"),
                _clean(agents_record.get("economic_action") or "null"),
                "null" if agents_record.get("intent") is None else "declared",
                agents_record.get("authorization_verdict")),
            "  - escalation `%s`, outcome state `%s`, stop condition `%s` — "
            "motif: %s" % (
                agents_record.get("escalation"),
                agents_record.get("outcome_state"),
                agents_record.get("stop_condition"),
                agents_record.get("outcome_motif")),
            "  - critic: `%s`, %s finding(s), types %s, gravities %s" % (
                crit.get("verdict"), _clean(crit.get("findings_count")),
                ", ".join(crit.get("finding_types") or []) or "-",
                ", ".join(crit.get("gravities") or []) or "-"),
            "  - hypotheses: %s — every agents state is `%s` and the record's "
            "decision slot stays `%s`: the bridge never upgrades an agents state "
            "into a REFUTED/SUPPORTED verdict." % (
                ", ".join("%s (%s)" % (h.get("id"), h.get("agent_state"))
                          for h in hyps) or "-",
                ", ".join(sorted({str(h.get("agent_state")) for h in hyps})) or "-",
                ", ".join(sorted({str((agents_record.get("verdicts") or {}).get(
                    h.get("id"), {}).get("verdict")) for h in hyps})) or "-"),
            "  - realised research cost: %s USD · %s LLM call(s) · %s tool "
            "call(s) · %s s (declared caps: %s USD / %s calls / %s s), read from "
            "`run_outcome.json`" % (
                _money(cost.get("cost_usd")), _clean(cost.get("llm_calls")),
                _clean(cost.get("tool_calls")), _seconds(cost.get("wall_seconds")),
                _clean(caps.get("cost_usd")), _clean(caps.get("llm_calls")),
                _clean(caps.get("wall_seconds"))),
            "  - what_would_change: %s entr(ies) — the bridge copies "
            "`outcome.non_recherche` verbatim; the sealed run stopped at `%s` "
            "before enumerating one, so the list is empty. Declared gap, never "
            "filled by hand." % (
                _clean(len(agents_record.get("what_would_change") or [])),
                agents_record.get("stop_condition")),
            "",
            "Case decision — A1-A5 abstention, **complement** (the research plan "
            "`decision/abstention_%s.json`, built from the case fixture and the "
            "critic findings through `orvyren.decision.abstention`, never a "
            "forced decision). It produces no intent and no economic action, and "
            "it is not the DecisionRecord:" % CASE_ID,
            abstention_block,
            "",
            "Cross-check only — deterministic decision engine "
            "(`run_decision.py --no-rdof`). The v1 engine is wired to the frozen "
            "USDC pilot windows (FREEZE_V1 D1/D2) and peg hypotheses; its record "
            "`decision/decision_%s.json` is kept as a pilot-scoped cross-check, "
            "**not** as the case conclusion:" % CASE_ID,
            verdict_lines,
            "",
        ]
    else:
        decision_lines = [
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
        ]

    # -- section 5: policy verdict (mode aware) ----------------------------
    if decision_source == "agents":
        first = ticks[0] if ticks else {}
        policy_lines = [
            "**No policy verdict was produced, and none is invented.** The "
            "DecisionRecord carries `economic_action: null` and `intent: null` "
            "with `authorization_verdict: REQUIRE_APPROVAL`, so the executor "
            "records `NO_ACTIONABLE_INTENT` and stops before `policy.evaluate`: "
            "the policy axis is *not evaluated* — not ALLOW, not DENY.",
            "",
            "`policy_v1.yaml` was loaded (version `%s`, hash `%s`) and no rule "
            "was applied, because there is nothing to authorise:" % (
                first.get("policy_version") or "unavailable",
                str(first.get("policy_hash") or "unavailable")),
            ticks_line,
            "",
            "`REQUIRE_APPROVAL` is the record's own brake: an agents run never "
            "evaluates the policy, and with no intent there is no transition "
            "decision -> policy in the chain.",
            "",
        ]
    else:
        policy_lines = [
            "Policy evaluated on the execution leg (real `policy_v1.yaml`, real "
            "state, fail-closed resolvers):",
            ticks_line,
            "",
        ]

    # -- section 6: execution (mode aware) ---------------------------------
    if decision_source == "agents":
        execution_lines = [
            "Dry-run only (no signature, no key read), on the case's **own** "
            "decision: `--case %s --decision-source agents --agents-run <sealed "
            "run>`. The historical pilot replay (`--case %s`) is gone from this "
            "leg: it produced a USDC intent under the rsETH run id, which is "
            "exactly the substitution this dossier removes." % (
                CASE_ID, EXECUTION_CASE_ID),
            "",
            steps_line,
            "",
            "  - chain events head: `%s`" % chain_head,
            "  - chain root `execution/chain/%s/`; tick journal "
            "`execution/journal.jsonl` (append-only, chained; "
            "`policy_verdicts.json` extracts this run's ticks)" % run_id,
            "  - outcome of the leg: %s tick(s), %s intent(s), %s signature(s), "
            "0 transfer — an abstention that stops before the policy is the "
            "expected result, not a failed execution." % (
                _clean(len(ticks)), _clean(len(intents)), _clean(signatures)),
            "",
        ]
    else:
        execution_lines = [
            "Execution is always dry-run (no signature, no key read), chained "
            "under one run identity (`orvyren.chain`). The execution case probe "
            "(`%s` case, measured live in this run) ended `%s`: the v1 decision "
            "dossier is only constructible for the pilot case id and the "
            "executor CLI has no decision-provider override, so the "
            "policy/execution leg runs the pilot decision replay as a declared "
            "substitution (`--case %s`), chained under this scenario run id and "
            "parented to the agents run id:" % (
                CASE_ID, probe_verdict, EXECUTION_CASE_ID),
            steps_line,
            "  - chain events head: %s" % chain_head,
            "  - tick journal: `execution/journal.jsonl` (chained JSONL, "
            "append-only; `policy_verdicts.json` extracts this run's ticks), "
            "chain root `execution/chain/%s/`; the probe journal and chain are "
            "kept under `execution/case_attempt/`" % run_id,
            "",
        ]

    # -- section 7: chain verification -------------------------------------
    verification_lines = []
    if verification:
        status = verification.get("status")
        citations = verification.get("citations") or {}
        rec = citations.get("decision_record") or {}
        agents_cite = citations.get("agents_run") or {}
        packet = citations.get("evidence_packet") or {}
        crit_cite = citations.get("critique") or {}
        exec_cite = citations.get("execution") or {}
        verification_lines.append(
            "`%s` (status `%s`) compares the DecisionRecord with what the "
            "executor actually recorded:" % (VERIFICATION_FILENAME, status))
        verification_lines.append("")
        if rec:
            verification_lines.append(
                "  - decision record `%s` sha256 `%s`" % (
                    rec.get("path"), rec.get("sha256")))
        if agents_cite:
            verification_lines.append(
                "  - agents run `%s` (mode `%s`), chain heads %s — recomputed "
                "from the journals, declared replayable=%s" % (
                    agents_cite.get("run_id"), agents_cite.get("mode"),
                    ", ".join("%s `%s`" % (role, head) for role, head in
                              sorted((agents_cite.get("chain_heads") or {}).items()))
                    or "-",
                    agents_cite.get("replayable")))
        for tick in verification.get("ticks") or []:
            checks = tick.get("checks") or {}
            passed = sum(1 for ok in checks.values() if ok)
            verification_lines.append(
                "  - tick %s: outcome `%s`, verdict `%s`, policy `%s`, reasons "
                "%s — %s/%s checks passed, chain run `%s` parent `%s`" % (
                    tick.get("tick"), tick.get("outcome"), tick.get("verdict"),
                    tick.get("policy_verdict") or "not evaluated",
                    ", ".join(str(r) for r in (tick.get("reasons") or [])) or "-",
                    passed, len(checks), tick.get("chain_run_id"),
                    tick.get("chain_parent_run_id")))
        events = exec_cite.get("events") or []
        if events:
            verification_lines.append(
                "  - chain events (in order): %s" % " -> ".join(
                    "`%s`" % event if event else "(unnamed)"
                    for event in events))
            if not any((tick.get("checks") or {}).get("intent_absence_consistent")
                       is False for tick in verification.get("ticks") or []):
                verification_lines.append(
                    "  - no `POLICY_DECIDED` and no execution event exists: with "
                    "no intent the chain stops after `NO_ACTIONABLE_INTENT`")
        if status == "PASS":
            verification_lines.extend([
                "",
                "Status `PASS`: the record the executor consumed is the record "
                "in the dossier — same epistemic verdict, same authorization "
                "verdict, same (null) economic action, same intent absence, "
                "chain ids chained to the agents run, chain verified, 0 "
                "executed.",
            ])
        elif status == "FAIL":
            verification_lines.append("")
            for failure in verification.get("failures") or []:
                verification_lines.append("  - FAILURE: %s" % failure)
        elif verification.get("reason"):
            verification_lines.append("")
            verification_lines.append("  - %s" % verification.get("reason"))
        if decision_source == "agents":
            verification_lines.extend([
                "",
                "Chain of identifiers, each read from its artifact:",
                "  1. risk observed — `evidence/episode_rseth_2026-04.json` "
                "(§1; fixture `%s`)" % rel(FIXTURE_PATH),
                "  2. hypotheses — `run.json` (HYP-001..HYP-004, state "
                "`UNDER_TEST`) (§2)",
                "  3. evidence — `evidence_packet.json` packet `%s`, snapshot "
                "`%s`, %s ref(s) (§3)" % (
                    packet.get("packet_id"), packet.get("snapshot_ref"),
                    packet.get("refs_count")),
                "  4. critique — `critique_report.json` `%s`, %s finding(s) "
                "(§3/§4)" % (crit_cite.get("verdict"),
                             crit_cite.get("findings_count")),
                "  5. decision — `decision/decision_agents_%s.json` (sha256 "
                "`%s`), from run `%s` (§4)" % (
                    CASE_ID, str(rec.get("sha256") or "")[:16],
                    agents_cite.get("run_id")),
                "  6. policy — not evaluated (no intent), tick outcome "
                "`%s` (§5)" % ((ticks[0].get("outcome") if ticks else "-")),
                "  7. execution — `execution/journal.jsonl`, chain `%s`, "
                "events head `%s` (§6)" % (
                    run_id, str(exec_cite.get("events_head") or chain_head)[:16]),
                "  8. dossier — `scenario_run.json` + this report, run_id `%s`" %
                run_id,
            ])
    else:
        verification_lines.append(
            "`%s` was not produced for this run." % VERIFICATION_FILENAME)

    # -- section 8: gaps ----------------------------------------------------
    if decision_source == "agents":
        gaps_lines = [
            "Explicit lacunae of the case fixture:",
            lacunes_line,
            "",
            "Declared gaps of this dossier (none of them is a conclusion):",
            "  - `what_would_change` is empty in the DecisionRecord: the bridge "
            "copies `outcome.non_recherche` verbatim and the sealed run stopped "
            "at `%s` before enumerating a research plan. The A1-A5 complement "
            "(`decision/abstention_%s.json`, %s entr(ies)) lists the sourced "
            "next observations; it is a complement, not a second decision." % (
                (agents_record.get("stop_condition") or "an early stop"),
                CASE_ID, _clean(len(abstention.get("what_would_change") or []))),
            "  - the deterministic engine record `decision/decision_%s.json` is "
            "pilot-scoped (frozen USDC windows + peg hypotheses): it is a "
            "cross-check of the decision stage, never an rsETH conclusion." %
            CASE_ID,
            "  - the live run is not bit-replayable (wall-time and realised cost "
            "enter its payloads): `source.replayable=false`, declared by the "
            "bridge. An offline replay needs a recorded response store, absent "
            "for this case — never simulated.",
            "  - the agents' hypotheses stayed `UNDER_TEST`: the record declares "
            "no hypothesis REFUTED or SUPPORTED. The critic's BLOQUANT finding "
            "(the packet carried no rsETH observation) is why the run stopped "
            "instead of concluding.",
            "  - the market price and the ~-31 % divergence remain documentation "
            "figures (ORVYREN_DOC2_TECHNIQUE_COMPLET.md, measurement 2), not an "
            "archived market series.",
            "",
        ]
    else:
        gaps_lines = [
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
        ]


    text = "\n".join([
        "# Scenario report — rsETH / KelpDAO, April 2026 (E2E demonstration)",
        "",
        "Case `%s` · scenario run_id `%s` · agents run_id `%s` · executor "
        "run_id `%s` (parent `%s`)." % (CASE_ID, run_id, parent_run_id or "-",
                                        run_id, parent_run_id or "-"),
        "Decision source of the execution leg: **`%s`** — %s" % (
            decision_source,
            "the per-tick DecisionRecord is built from the sealed agents run by "
            "`src/orvyren/decision/agents_source.py` (no pilot replay)."
            if decision_source == "agents" else
            "LEGACY path: the per-tick decision is the frozen USDC pilot replay "
            "(declared substitution, reproduce-only)."),
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
        "The agents of the run observed the tools of the case (real LLM calls at "
        "run time). The sourced figures of the fixture and their sources:",
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
    ] + decision_lines + [
        REPORT_SECTIONS[4],
        "",
    ] + policy_lines + [
        REPORT_SECTIONS[5],
        "",
    ] + execution_lines + [
        REPORT_SECTIONS[6],
        "",
    ] + verification_lines + [
        "",
        REPORT_SECTIONS[7],
        "",
    ] + gaps_lines + [
        REPORT_SECTIONS[8],
        "",
        "Reproduce, sealed run (no LLM call, no new spend — the packaged mode):",
        "```",
        "python scripts/run_scenario_rseth.py --agents-run %s \\"
        % rel(SEALED_AGENTS_RUN),
        "    --run-id %s --out-dir evidence/scenario_rseth" % run_id,
        "```",
        "Reproduce, live agents (real LLM calls, keys from `%s`; a new agents "
        "run and a new scenario run id):" % rel(ENV_FILE),
        "```",
        "(set -a; source %s; set +a)" % rel(ENV_FILE),
        "python %s --out-dir evidence/scenario_rseth"
        % rel(os.path.join("scripts", "run_scenario_rseth.py")),
        "```",
        "Legacy leg (reproduce the superseded dossier only): add "
        "`--decision-source corpus`.",
        "",
        "The bridge record `decision/decision_agents_%s.json` is the artifact to "
        "cite; `%s` states whether the executor consumed it (and with which "
        "chain ids). Fixture: `%s`. Derived corpus: `%s` (re-derived and "
        "compared by `tests/test_fixtures_rseth_inputs.py`). Targeted tests: "
        "`python -m unittest tests.test_fixtures_rseth_inputs "
        "tests.test_scenario_rseth`. No key or secret is stored in any artifact "
        "of this directory." % (
            CASE_ID, VERIFICATION_FILENAME, rel(FIXTURE_PATH), rel(CORPUS_PATH)),
        "",
    ])
    text += "\n" + "\n".join([REPORT_SECTIONS[9], ""] + raw_blocks)
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
    decision_source = str(previous.get("decision_source")
                          or args.decision_source or "agents")
    agents_run_dir = ""
    previous_run_dir = str(previous.get("agents_run_dir") or "").strip()
    if previous_run_dir and os.path.isdir(_abs(previous_run_dir)):
        agents_run_dir = _abs(previous_run_dir)
    if not agents_run_dir:
        agents_run_dir = _find_agents_run_dir(
            os.path.join(out_dir, "agents_session"))
    if not agents_run_dir:
        print("E_SCENARIO_COLLECT: no agents run directory recorded in "
              "scenario_run.json nor found under %s/agents_session" % out_dir)
        return EXIT_STEP_FAILED
    if decision_source == "agents":
        try:
            build_agents_decision(out_dir=out_dir, agents_run_dir=agents_run_dir,
                                  case_id=args.case)
        except AgentsDecisionUnavailable as exc:
            print("E_SCENARIO_COLLECT: the agents run cannot yield a "
                  "DecisionRecord — %s" % exc)
            return EXIT_STEP_FAILED
    build_case_abstention(out_dir=out_dir, agents_run_dir=agents_run_dir,
                          case_id=args.case)
    collected = collect_artifacts(out_dir=out_dir, agents_run_dir=agents_run_dir,
                                  run_id=run_id, parent_run_id=agent_run_id)
    verification = verify_chain(out_dir=out_dir, run_id=run_id,
                                agents_run_id=agent_run_id,
                                agents_run_dir=agents_run_dir,
                                decision_source=decision_source,
                                case_id=args.case)
    collected[VERIFICATION_FILENAME] = os.path.join(out_dir, VERIFICATION_FILENAME)
    steps = previous.get("steps") or []
    report = render_report(out_dir=out_dir, run_id=run_id,
                           parent_run_id=agent_run_id, collected=collected,
                           steps=steps, decision_source=decision_source)
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
        "decision_source": decision_source,
        "agents_run_id": agent_run_id,
        "agents_run_dir": _display_path(agents_run_dir),
        "executor_run_id": run_id,
        "executor_parent_run_id": agent_run_id,
        "verification_status": verification.get("status"),
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
    parser.add_argument("--decision-source", choices=DECISION_SOURCES,
                        default="agents",
                        help="per-tick DecisionRecord of the execution leg: "
                             "`agents` (default) builds it from the sealed "
                             "agents run via orvyren.decision.agents_source; "
                             "`corpus` is the LEGACY pilot replay (declared "
                             "substitution, reproduce-only)")
    parser.add_argument("--agents-run", default=None,
                        help="directory of a sealed agents run to consume "
                             "(run.json + run_outcome.json + journals). Skips "
                             "the live agents stage entirely: no LLM call, no "
                             "new spend")
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

    # A sealed agents run given on the command line is consumed as-is: the key
    # gate and the live agents stage are skipped (no LLM call, no new spend).
    sealed_run_dir = ""
    if args.agents_run:
        sealed_run_dir = _abs(args.agents_run)
        if not os.path.isdir(sealed_run_dir):
            print("E_SCENARIO_AGENTS_RUN: --agents-run is not a directory: %s"
                  % sealed_run_dir)
            return EXIT_STEP_FAILED
        if not os.path.isfile(os.path.join(sealed_run_dir, "run_outcome.json")):
            print("E_SCENARIO_AGENTS_RUN: run_outcome.json missing in %s"
                  % sealed_run_dir)
            return EXIT_STEP_FAILED
        if args.decision_source != "agents":
            print("E_SCENARIO_AGENTS_RUN: --agents-run is only meaningful with "
                  "--decision-source agents (got %r)" % args.decision_source)
            return EXIT_STEP_FAILED

    if args.collect_only:
        return _collect_only(args, out_dir)

    child_env = dict(os.environ if env is None else env)
    loaded = load_env_file(os.path.join(REPO_ROOT, ENV_FILE), child_env)

    # The derived corpus must exist before the decision leg (derived data,
    # re-verified against its source by the crossing test).
    if not os.path.isfile(os.path.join(REPO_ROOT, CORPUS_PATH)):
        materialize_corpus()

    agent_run_id = ""
    agents_run_dir = sealed_run_dir
    if sealed_run_dir:
        spec = {}
        for name in ("run.json", "run_outcome.json"):
            candidate = os.path.join(sealed_run_dir, name)
            if os.path.isfile(candidate):
                spec = _read_json(candidate)
                if str(spec.get("run_id") or "").strip():
                    break
        agent_run_id = str(spec.get("run_id") or "").strip()
        if not agent_run_id:
            print("E_SCENARIO_AGENTS_RUN: no run_id in the sealed run %s"
                  % sealed_run_dir)
            return EXIT_STEP_FAILED
        if agent_run_id == run_id:
            print("E_SCENARIO_AGENTS_RUN: the scenario run_id must differ from "
                  "the agents run_id (identifiers are never reused)")
            return EXIT_STEP_FAILED
    steps = build_steps(case_id=args.case, out_dir=args.out_dir,
                        run_id=run_id, ticks=args.ticks,
                        parent_run_id=(agent_run_id or "PENDING_AGENT_RUN_ID"),
                        decision_source=args.decision_source,
                        agents_run_dir=sealed_run_dir)
    results = []
    exec_runner = runner or _run_command
    print("ORVYREN — E2E scenario %s · run_id %s · decision source %s"
          % (args.case, run_id, args.decision_source))
    if sealed_run_dir:
        print("  agents run   : %s (sealed, reused — no LLM call)"
              % _display_path(sealed_run_dir))
    print("  env file     : %s (%d variable(s) loaded into child processes, "
          "values never printed)" % (ENV_FILE, loaded))

    for index, step in enumerate(steps):
        if step["name"] in ("execution_case_probe", "execution") and agent_run_id:
            # Rebuild the step with the real agents run id as chain parent
            # (and the real agents directory once the live run is sealed).
            rebuilt = {row["name"]: row for row in build_steps(
                case_id=args.case, out_dir=args.out_dir, run_id=run_id,
                ticks=args.ticks, parent_run_id=agent_run_id,
                decision_source=args.decision_source,
                agents_run_dir=(agents_run_dir or sealed_run_dir))}
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
            if args.decision_source == "agents":
                # The case decision IS the bridge record: built from the sealed
                # run, written as-is, and consumed by the executor below.
                try:
                    record = build_agents_decision(
                        out_dir=out_dir, agents_run_dir=agents_run_dir,
                        case_id=args.case)
                except AgentsDecisionUnavailable as exc:
                    print("  E_SCENARIO_DECISION: the agents run cannot yield a "
                          "DecisionRecord — %s" % exc)
                    _write_json(os.path.join(out_dir, "scenario_run.json"), {
                        "schema": "orvyren/scenario-run/v1",
                        "case_id": args.case,
                        "run_id": run_id,
                        "status": "FAILED",
                        "failed_step": "decision_agents_source",
                        "error": str(exc),
                        "generated_utc": _now_iso(),
                        "steps": [{k: s.get(k) for k in
                                   ("name", "argv", "rc", "verdict",
                                    "stdout_tail", "stderr_tail")}
                                  for s in results],
                    })
                    return EXIT_STEP_FAILED
                refs = record.get("evidence_refs") or []
                results.append({
                    "name": "decision_agents_source",
                    "argv": ["<in-process>",
                             "orvyren.decision.agents_source."
                             "build_decision_from_agents %s"
                             % _display_path(agents_run_dir)],
                    "rc": 0,
                    "verdict": str(record.get("authorization_verdict") or "-"),
                    "stdout_tail": (
                        "DecisionRecord %s · epistemic %s · economic_action %s "
                        "· intent %s · authorization %s · escalation %s · "
                        "evidence_refs %s" % (
                            record.get("schema"),
                            record.get("epistemic_verdict"),
                            record.get("economic_action"), record.get("intent"),
                            record.get("authorization_verdict"),
                            record.get("escalation"),
                            ", ".join("%s=%s" % (ref.get("source"),
                                                 str(ref.get("value"))[:12])
                                      for ref in refs) or "-")),
                    "stderr_tail": "",
                })
                print("    DecisionRecord: %s · %s · %s (intent %s)"
                      % (record.get("schema"), record.get("epistemic_verdict"),
                         record.get("authorization_verdict"),
                         "null" if record.get("intent") is None else "declared"))
            # The A1-A5 abstention is the research-plan complement (never a
            # forced decision): what_would_change is mandatory for an
            # INCONCLUSIVE outcome (B3 §c.3).
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
    if not agent_run_id and agents_run_dir:
        spec = _read_json(os.path.join(agents_run_dir, "run.json"))
        agent_run_id = str(spec.get("run_id") or "")
    build_case_abstention(out_dir=out_dir, agents_run_dir=agents_run_dir,
                          case_id=args.case)
    collected = collect_artifacts(out_dir=out_dir,
                                  agents_run_dir=agents_run_dir,
                                  run_id=run_id,
                                  parent_run_id=agent_run_id)
    verification = verify_chain(out_dir=out_dir, run_id=run_id,
                                agents_run_id=agent_run_id,
                                agents_run_dir=agents_run_dir,
                                decision_source=args.decision_source,
                                case_id=args.case)
    if verification.get("status") == "FAIL":
        print("  E_SCENARIO_VERIFY: the decision -> policy -> execution chain "
              "does not hold — no dossier is published:")
        for failure in verification.get("failures") or []:
            print("    - %s" % failure)
        _write_json(os.path.join(out_dir, "scenario_run.json"), {
            "schema": "orvyren/scenario-run/v1",
            "case_id": args.case,
            "run_id": run_id,
            "status": "FAILED",
            "failed_step": "chain_verification",
            "verification_status": verification.get("status"),
            "verification_failures": verification.get("failures") or [],
            "generated_utc": _now_iso(),
            "steps": [{k: s.get(k) for k in
                       ("name", "argv", "rc", "verdict", "stdout_tail",
                        "stderr_tail")} for s in results],
        })
        return EXIT_STEP_FAILED
    collected[VERIFICATION_FILENAME] = os.path.join(out_dir, VERIFICATION_FILENAME)
    report = render_report(out_dir=out_dir, run_id=run_id,
                           parent_run_id=agent_run_id, collected=collected,
                           steps=results, decision_source=args.decision_source)
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
        "decision_source": args.decision_source,
        "agents_run_id": agent_run_id,
        "agents_run_dir": _display_path(agents_run_dir),
        "agents_run_reused": bool(sealed_run_dir),
        "executor_run_id": run_id,
        "executor_parent_run_id": agent_run_id,
        "verification_status": verification.get("status"),
        "generated_utc": _now_iso(),
        "steps": [{k: s.get(k) for k in
                   ("name", "argv", "rc", "verdict", "stdout_tail", "stderr_tail")}
                  for s in results],
        "artifacts": artifacts,
    })
    print("  verification : %s" % verification.get("status"))
    print("  artifacts    : %s (%d file(s))" % (out_dir, len(artifacts) + 2))
    print("  report       : %s" % os.path.join(out_dir, "scenario_report.md"))
    return EXIT_OK


main = run_pipeline


if __name__ == "__main__":
    sys.exit(run_pipeline())
