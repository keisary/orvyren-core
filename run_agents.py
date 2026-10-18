#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — ``run_agents.py``: binary MA-B coordinator (W2 lot L2.7).

Spawns **two separate processes** (orchestrator then critic — see
``src/orvyren/agents/worker.py``), collects their serialisable outputs,
applies the fragility rule (B1 §5.3: a ``FRAGILE``/``INCOHERENTE`` verdict is
never cancelled — it pushes towards ``REQUIRE_APPROVAL`` / abstention), checks
the hash chains of both journals and prints the run summary (including the
**cumulative LLM cost**).

Modes:
- ``--replay journal``: offline replay from the recorded response store
  (deterministic — the demo never depends on the network, B1 §6.3);
- ``--replay live``: real calls (requires keys in environment variables —
  never in the repository; ``config/models.json`` pins the IDs).

Note: the budget is part of the RECORDED PROMPT (``budget_restant`` key) —
a replay with a budget different from the recordings fails cleanly
(``E_LLM_NOT_RECORDED`` → ``ARRET-3`` abstention), never improvisation.

Examples::

    python run_agents.py --case usdc-2023-03 --replay journal
    python run_agents.py --case usdc-2023-03 --replay journal --budget-llm 10
    python run_agents.py --case usdc-2023-03 --replay live   # keys required

Outputs: ``evidence/demo_runs/agents/<case>/<run_id>/`` (spec, JSONL journals, exchanges,
``run_outcome.json``). Stdlib only; this script imports neither policy nor
execution (W2 boundary rule).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents import worker as worker_mod  # noqa: E402

__all__ = ["main", "prepare_run", "collect_and_finish", "apply_fragility_rule",
           "default_tool_mode"]


def _configure_stdio() -> None:
    """Force UTF-8 on stdout/stderr: a Windows cp1252 console must never
    make the orchestrator fail on a non-representable character."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # stream cannot be reconfigured (test capture, pipe)
            pass


def _utc_stamp() -> str:
    # Microsecond precision: two runs launched within the same second must
    # never collide on the same run directory (each run owns its artifacts).
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _write_json(path: str, payload) -> None:
    # Atomic write (same pattern as worker._write_json): a crash must never
    # leave a truncated run_outcome.json behind.
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def _safe_case(case_id: str) -> str:
    """Filesystem-safe case token (never a path separator)."""
    token = str(case_id).replace("\\", "/").split("/")[-1]
    token = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in token)
    return token.strip("-.") or "case"


def load_case_inputs(case_id: str) -> dict:
    """Load the pinned run inputs of a case (fixtures/agents/<case>/run_inputs.json)."""
    path = os.path.join(REPO_ROOT, "fixtures", "agents", _safe_case(case_id), "run_inputs.json")
    if not os.path.exists(path):
        raise SystemExit(
            "E_CASE_UNKNOWN: %s missing — record the case first "
            "(python scripts/agents_seed_demo.py --case %s)" % (path, case_id))
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def default_tool_mode(replay_mode: str) -> str:
    """Tool providers per run mode (P0-1): journal/scripted runs stay on the
    frozen fixtures (byte-identical replays), a real run is ``live``."""
    return "fixture" if str(replay_mode) in ("journal", "scripted") else "live"


def prepare_run(*, case_id: str, mode: str, session_dir: str, inputs: dict,
                store_dir: str, budget: dict, record_live: bool = False,
                tool_mode: str = "fixture", graph_db: str = None,
                tool_store: str = None, record_tools: str = None,
                memory: bool = False) -> str:
    """Create the run directory + ``run.json``; returns the run directory.

    ``memory=True`` (``--memory``) is written into the spec as ``"memory":
    true``; the default writes **no** such key, so a run without the flag keeps
    the historical ``run.json`` and the historical prompts (the sealed store
    keeps replaying bit for bit).
    """
    stamp = _utc_stamp()
    # Journal mode: the run_id is PINNED ("demo-<case>") so the journal
    # content — and the evidence packet the critic receives — is byte-identical
    # across replays (k=10 criterion, B1 §6.2); the run DIRECTORY stays
    # timestamped so successive runs never overwrite each other. The seed
    # recording uses the SAME pinned id so replay finds every recorded call.
    run_id = ("demo-%s" % case_id) if mode == "journal" \
        else "%s_%s_%s" % (case_id.replace("/", "-"), mode, stamp)
    run_dir = os.path.join(session_dir,
                           "%s_%s_%s" % (_safe_case(case_id), mode, stamp))
    os.makedirs(os.path.join(run_dir, "exchanges"), exist_ok=True)
    created_at = inputs.get("pinned_created_at") if mode == "journal" else None
    if not created_at:
        created_at = datetime.now(timezone.utc).isoformat()
    spec = {
        "schema": "orvyren/agent-run/v1",
        "run_id": run_id,
        "case_id": case_id,
        "mode": mode,
        "budget": budget,
        "snapshot": inputs["snapshot"],
        "lacunes": inputs["lacunes"],
        "hypotheses": inputs["hypotheses"],
        "tool_fixtures": inputs["tool_fixtures"],
        "tool_mode": str(tool_mode or "fixture"),
        "graph_db": str(graph_db or "evidence/graph.sqlite"),
        "store_dir": os.path.abspath(store_dir),
        "created_at": created_at,
    }
    if tool_store:
        spec["tool_store"] = os.path.abspath(tool_store)
    if record_tools:
        spec["record_tools"] = os.path.abspath(record_tools)
    if record_live:
        spec["record_live"] = True
    if memory:
        # OFF by default: the key is absent unless --memory was given, so a
        # default run writes exactly the historical spec (no database, no
        # ``memory_recall`` in the planning payload).
        spec["memory"] = True
    _write_json(os.path.join(run_dir, "run.json"), spec)
    return run_dir


def _spawn(role: str, run_dir: str, timeout_s: float) -> int:
    """Spawn one worker process; echo its output; return its exit code."""
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    # The parent decodes worker output as UTF-8: force it even when the outer
    # console declares cp1252 (Windows), otherwise a non-cp1252 dash becomes
    # U+FFFD in the captured output.
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, "-m", "orvyren.agents.worker",
           "--role", role, "--run-dir", run_dir]
    try:
        completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        # A hung worker is a failed worker: report it like one (the caller
        # raises E_WORKER_<ROLE>) instead of crashing with a raw traceback.
        for line in ((exc.stdout or "") if isinstance(exc.stdout, str)
                     else (exc.stdout or b"").decode("utf-8", "replace")).splitlines():
            print("    %s" % line)
        print("    [stderr] worker %s exceeded --timeout-s %.0fs" % (role, timeout_s))
        return 124
    for line in (completed.stdout or "").splitlines():
        print("    %s" % line)
    if completed.returncode != 0:
        for line in (completed.stderr or "").splitlines()[-8:]:
            print("    [stderr] %s" % line)
    return completed.returncode


def apply_fragility_rule(outcome: dict, critique: dict) -> dict:
    """Map the critique verdict onto the run outcome (B1 §5.3).

    ``INCOHERENTE`` or any ``BLOQUANT`` finding forces the abstention; any
    ``FRAGILE``/``INCOHERENTE`` verdict requires human approval before action.
    """
    verdict = str((critique or {}).get("verdict_lecture", ""))
    findings = (critique or {}).get("findings") or []
    quarantined = str((critique or {}).get("$status", "")) == "QUARANTINED"
    bloquant = any(str(f.get("gravite", "")) == "BLOQUANT" for f in findings
                   if isinstance(f, dict))
    escalation = None
    if quarantined:
        outcome = dict(outcome, inconclusive=True)
        return {"outcome": outcome, "escalation": "REQUIRE_APPROVAL",
                "verdict": verdict or "ABSENTE"}
    if verdict in ("FRAGILE", "INCOHERENTE") or bloquant:
        escalation = "REQUIRE_APPROVAL"
    if verdict == "INCOHERENTE" or bloquant:
        outcome = dict(outcome, inconclusive=True)
    return {"outcome": outcome, "escalation": escalation, "verdict": verdict or "ABSENTE"}


def collect_and_finish(*, run_dir: str, case_id: str, mode: str) -> dict:
    """Read both journals + reports, verify chains, write run_outcome.json."""
    journals = {}
    for role in ("orchestrator", "critic"):
        path = os.path.join(run_dir, "journal_%s.jsonl" % role)
        if not os.path.exists(path):
            raise SystemExit("E_RUN_INCOMPLETE: journal %s missing" % role)
        entries = worker_mod.load_journal(path)
        ok, message = worker_mod.verify_exported_chain(entries)
        if not ok:
            raise SystemExit("E_JOURNAL_CHAIN: %s — %s" % (role, message))
        journals[role] = {
            "lines": len(entries),
            "chain_head": worker_mod.entry_hash(entries[-1]) if entries else "0" * 64,
            "agent_ids": sorted({entry.agent_id for entry in entries}),
        }
    with open(os.path.join(run_dir, "outcome_orchestrator.json"), encoding="utf-8") as handle:
        outcome = json.load(handle)
    critique = {}
    critique_path = os.path.join(run_dir, "exchanges", "002_critique_report.json")
    if os.path.exists(critique_path):
        with open(critique_path, encoding="utf-8") as handle:
            critique = json.load(handle)
    applied = apply_fragility_rule(outcome, critique)
    final = {
        "schema": "orvyren/agent-run-outcome/v1",
        "case_id": case_id, "mode": mode, "run_dir": run_dir,
        "outcome": applied["outcome"], "critique": critique,
        "escalation": applied["escalation"],
        "journals": journals,
    }
    _write_json(os.path.join(run_dir, "run_outcome.json"), final)
    return final


def _print_summary(final: dict, budget: dict = None) -> None:
    outcome = final["outcome"]
    budgets = outcome.get("budget_used", {})
    caps = budget or {}
    print()
    print("  ==== run summary %s (%s) ====" % (final["case_id"], final["mode"]))
    for role, info in final["journals"].items():
        print("    %-13s %3d lines — agent_id:%s — chain %s"
              % (role, info["lines"], ",".join(info["agent_ids"]) or "-", "OK"))
    print("    stop           : %s %s" % (outcome.get("stop_condition") or "-",
                                         ("(abstention)" if outcome.get("inconclusive") else "")))
    # Ceilings shown are the ones this run was actually bounded by (--budget-*),
    # not the frozen maxima (A5) — otherwise a --budget-llm 10 run would print /30.
    print("    budget         : llm %.0f/%.0f · tools %.0f/%.0f · %.0fs/%.0fs · $%.4f/$%.2f"
          % (budgets.get("llm_calls", 0), caps.get("llm_calls", 30),
             budgets.get("tool_calls", 0), caps.get("tool_calls", 12),
             budgets.get("wall_seconds", 0), caps.get("wall_seconds", 600),
             budgets.get("cost_usd", 0.0), caps.get("cost_usd", 0.10)))
    verdict = (final.get("critique") or {}).get("verdict_lecture", "—")
    print("    critique       : %s" % verdict)
    if final.get("escalation"):
        print("    escalation     : %s (the critic never cancels — it brakes)" % final["escalation"])
    if outcome.get("non_recherche"):
        print("    not searched   : %s" % " · ".join(outcome["non_recherche"][:4]))
    print("    cumulative LLM cost: $%.4f" % budgets.get("cost_usd", 0.0))
    print("    artifacts      : %s" % final["run_dir"])


def main(argv=None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        prog="run_agents.py",
        description="ORVYREN — MA-B coordinator: orchestrator + critic in separate processes "
                    "(offline journal replay by default, cost displayed)")
    parser.add_argument("--case", required=True, help="case (e.g. usdc-2023-03)")
    parser.add_argument("--replay", choices=("journal", "live"), default="journal")
    parser.add_argument("--session", default=None,
                        help="session directory (default: evidence/demo_runs/agents/<case>)")
    parser.add_argument("--store", default=None,
                        help="response store (default: fixtures/agents/store_<case>)")
    parser.add_argument("--record-live", action="store_true",
                        help="record LIVE responses under <run_dir>/store_live "
                             "(sealed by hash; later bit-for-bit replay via --store)")
    parser.add_argument("--tool-mode", choices=("fixture", "live", "replay"),
                        default=None,
                        help="tool data providers (P0-1; default: fixture for "
                             "--replay journal/scripted, live otherwise)")
    parser.add_argument("--graph-db", default=os.path.join("evidence", "graph.sqlite"),
                        help="graph SQLite behind the LIVE tools "
                             "(default: evidence/graph.sqlite)")
    parser.add_argument("--tool-store", default=None,
                        help="recorded tool-response store for --tool-mode replay")
    parser.add_argument("--record-tools", default=None,
                        help="record every LIVE tool response into this directory "
                             "(tool_responses.jsonl; later bit-identical REPLAY)")
    parser.add_argument("--memory", action="store_true",
                        help="attach the FTS memory of the run "
                             "(<run_dir>/memory.sqlite + a memory_recall tool). "
                             "OFF by default: the allow-list and the recorded "
                             "prompts stay unchanged, so the sealed store keeps "
                             "replaying bit for bit; a memory-enabled run needs "
                             "its own recording (the planning payload lists the "
                             "extra tool)")
    parser.add_argument("--budget-llm", type=float, default=30)
    parser.add_argument("--budget-tools", type=float, default=12)
    parser.add_argument("--budget-wall", type=float, default=600)
    parser.add_argument("--budget-usd", type=float, default=0.10)
    parser.add_argument("--timeout-s", type=float, default=None,
                        help="maximum wait per worker process (default: the "
                             "wall budget + 120 s — a healthy worker is never "
                             "killed by an incoherent cap)")
    args = parser.parse_args(argv)

    for name, value, ceiling in (("llm", args.budget_llm, 30), ("tools", args.budget_tools, 12),
                                 ("wall", args.budget_wall, 600), ("usd", args.budget_usd, 0.10)):
        if not math.isfinite(value) or value <= 0 or value > ceiling:
            raise SystemExit("E_BUDGET: --budget-%s must be within ]0, %s] (A5 frozen ceilings)"
                             % (name, ceiling))

    # Worker timeout: it must outlive the worker's own wall budget, or a
    # healthy run would be killed mid-flight (a spawn killed by its cap is a
    # failed run, never a completed one — rc 124 below).
    timeout_s = args.timeout_s
    if timeout_s is None:
        timeout_s = max(300.0, float(args.budget_wall) + 120.0)
    elif not math.isfinite(timeout_s) or timeout_s <= 0:
        raise SystemExit("E_TIMEOUT: --timeout-s must be within ]0, +inf[")

    if args.replay == "live":
        keys = [var for var in ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
                if os.environ.get(var)]
        if not keys:
            raise SystemExit("E_LLM_NO_KEY: live mode without a key — set ORVYREN_DEEPSEEK_API_KEY / "
                             "ORVYREN_MIMO_API_KEY in the environment (never in the repository); "
                             "without a key, use --replay journal (deterministic, offline).")

    inputs = load_case_inputs(args.case)
    # Default paths use the SAFE case token: a case id carrying path segments
    # must never steer the session/store directories outside their roots.
    session = args.session or os.path.join(REPO_ROOT, "evidence", "demo_runs",
                                          "agents", _safe_case(args.case))
    store = args.store or os.path.join(REPO_ROOT, "fixtures", "agents",
                                      "store_%s" % _safe_case(args.case))
    budget = {"llm_calls": args.budget_llm, "tool_calls": args.budget_tools,
              "wall_seconds": args.budget_wall, "cost_usd": args.budget_usd}
    tool_mode = args.tool_mode or default_tool_mode(args.replay)
    if tool_mode == "replay" and not args.tool_store:
        raise SystemExit("E_TOOL_STORE: --tool-mode replay needs --tool-store <dir> "
                         "(recorded tool responses — a replay never simulates)")
    run_dir = prepare_run(case_id=args.case, mode=args.replay, session_dir=session,
                          inputs=inputs, store_dir=store, budget=budget,
                          record_live=args.record_live, tool_mode=tool_mode,
                          graph_db=args.graph_db, tool_store=args.tool_store,
                          record_tools=args.record_tools, memory=args.memory)
    print("ORVYREN — run_agents · %s · mode %s" % (args.case, args.replay))
    print("  run       : %s" % run_dir)
    if args.record_live:
        print("  store live: %s" % os.path.join(run_dir, "store_live"))
    if args.memory:
        print("  memory    : %s" % os.path.join(run_dir, "memory.sqlite"))

    for role in ("orchestrator", "critic"):
        print("  [%s] process started…" % role)
        code = _spawn(role, run_dir, timeout_s)
        if code != 0:
            raise SystemExit("E_WORKER_%s: code %d — see the output above" % (role.upper(), code))

    final = collect_and_finish(run_dir=run_dir, case_id=args.case, mode=args.replay)
    _print_summary(final, budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
