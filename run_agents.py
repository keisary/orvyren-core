#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — ``run_agents.py`` : coordinateur MA-B binaire (W2 lot L2.7).

Lance **deux processus séparés** (orchestrateur puis critique — voir
``src/orvyren/agents/worker.py``), collecte leurs sorties sérialisables,
applique la règle de fragilité (B1 §5.3 : un verdict ``FRAGILE``/``INCOHERENTE``
ne s'annule pas — il pousse vers ``REQUIRE_APPROVAL`` / abstention), vérifie
les chaînes de hash des deux journaux et affiche le bilan (dont le **coût LLM
cumulé**).

Modes :
- ``--replay journal`` : rejeu hors-ligne depuis le magasin de réponses
  enregistrées (déterministe — la démo ne dépend jamais du réseau, B1 §6.3) ;
- ``--replay live`` : appels réels (exige les clés en variables
  d'environnement — jamais dans le dépôt ; ``config/models.json`` fige les IDs).

Note : le budget fait partie du PROMPT enregistré (clé ``budget_restant``) —
un rejeu avec un budget différent des enregistrements échoue proprement
(``E_LLM_NOT_RECORDED`` → abstention ``ARRET-3``), jamais d'improvisation.

Exemples ::

    python run_agents.py --case usdc-2023-03 --replay journal
    python run_agents.py --case usdc-2023-03 --replay journal --budget-llm 10
    python run_agents.py --case usdc-2023-03 --replay live   # clés requises

Sorties : ``demo_runs/agents/<case>/<run_id>/`` (spec, journaux JSONL, échanges,
``run_outcome.json``). Stdlib uniquement ; ce script n'importe ni policy ni
execution (règle de frontière W2).
"""

from __future__ import annotations

import argparse
import json
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

__all__ = ["main", "prepare_run", "collect_and_finish", "apply_fragility_rule"]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)


def load_case_inputs(case_id: str) -> dict:
    """Load the pinned run inputs of a case (fixtures/agents/<case>/run_inputs.json)."""
    path = os.path.join(REPO_ROOT, "fixtures", "agents", case_id, "run_inputs.json")
    if not os.path.exists(path):
        raise SystemExit(
            "E_CASE_UNKNOWN: %s absent — enregistrer d'abord le cas "
            "(python scripts/agents_seed_demo.py --case %s)" % (path, case_id))
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def prepare_run(*, case_id: str, mode: str, session_dir: str, inputs: dict,
                store_dir: str, budget: dict, record_live: bool = False) -> str:
    """Create the run directory + ``run.json``; returns the run directory."""
    stamp = _utc_stamp()
    # Journal mode: the run_id is PINNED ("demo-<case>") so the journal
    # content — and the evidence packet the critic receives — is byte-identical
    # across replays (k=10 criterion, B1 §6.2); the run DIRECTORY stays
    # timestamped so successive runs never overwrite each other. The seed
    # recording uses the SAME pinned id so replay finds every recorded call.
    run_id = ("demo-%s" % case_id) if mode == "journal" \
        else "%s_%s_%s" % (case_id.replace("/", "-"), mode, stamp)
    run_dir = os.path.join(session_dir,
                           "%s_%s_%s" % (case_id.replace("/", "-"), mode, stamp))
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
        "store_dir": os.path.abspath(store_dir),
        "created_at": created_at,
    }
    if record_live:
        spec["record_live"] = True
    _write_json(os.path.join(run_dir, "run.json"), spec)
    return run_dir


def _spawn(role: str, run_dir: str, timeout_s: float) -> int:
    """Spawn one worker process; echo its output; return its exit code."""
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    cmd = [sys.executable, "-m", "orvyren.agents.worker",
           "--role", role, "--run-dir", run_dir]
    completed = subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=timeout_s)
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
    bloquant = any(str(f.get("gravite", "")) == "BLOQUANT" for f in findings
                   if isinstance(f, dict))
    escalation = None
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
            raise SystemExit("E_RUN_INCOMPLETE: journal %s manquant" % role)
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


def _print_summary(final: dict) -> None:
    outcome = final["outcome"]
    budgets = outcome.get("budget_used", {})
    print()
    print("  ════ bilan du run %s (%s) ════" % (final["case_id"], final["mode"]))
    for role, info in final["journals"].items():
        print("    %-13s %3d lignes — agent_id:%s — chaîne %s"
              % (role, info["lines"], ",".join(info["agent_ids"]) or "-", "OK"))
    print("    arrêt          : %s %s" % (outcome.get("stop_condition") or "-",
                                         ("(abstention)" if outcome.get("inconclusive") else "")))
    print("    budget         : llm %.0f/30 · outils %.0f/12 · %.0fs/600 · $%.4f/0.10"
          % (budgets.get("llm_calls", 0), budgets.get("tool_calls", 0),
             budgets.get("wall_seconds", 0), budgets.get("cost_usd", 0.0)))
    verdict = (final.get("critique") or {}).get("verdict_lecture", "—")
    print("    critique       : %s" % verdict)
    if final.get("escalation"):
        print("    escalade       : %s (le critique n'annule pas — il freine)" % final["escalation"])
    if outcome.get("non_recherche"):
        print("    non recherché  : %s" % " · ".join(outcome["non_recherche"][:4]))
    print("    coût LLM cumulé: $%.4f" % budgets.get("cost_usd", 0.0))
    print("    artefacts      : %s" % final["run_dir"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_agents.py",
        description="ORVYREN — coordinateur MA-B : orchestrateur + critique en processus séparés "
                    "(rejeu journal hors-ligne par défaut, coût affiché)")
    parser.add_argument("--case", required=True, help="cas (ex. usdc-2023-03)")
    parser.add_argument("--replay", choices=("journal", "live"), default="journal")
    parser.add_argument("--session", default=None,
                        help="répertoire de session (défaut : demo_runs/agents/<case>)")
    parser.add_argument("--store", default=None,
                        help="magasin de réponses (défaut : fixtures/agents/store_<case>)")
    parser.add_argument("--record-live", action="store_true",
                        help="enregistre les réponses LIVE dans <run_dir>/store_live "
                             "(scellées par hash ; rejeu bit-à-bit ultérieur via --store)")
    parser.add_argument("--budget-llm", type=float, default=30)
    parser.add_argument("--budget-tools", type=float, default=12)
    parser.add_argument("--budget-wall", type=float, default=600)
    parser.add_argument("--budget-usd", type=float, default=0.10)
    parser.add_argument("--timeout-s", type=float, default=300.0,
                        help="attente maximale par processus worker")
    args = parser.parse_args(argv)

    for name, value, ceiling in (("llm", args.budget_llm, 30), ("tools", args.budget_tools, 12),
                                 ("wall", args.budget_wall, 600), ("usd", args.budget_usd, 0.10)):
        if value <= 0 or value > ceiling:
            raise SystemExit("E_BUDGET: --budget-%s doit être dans ]0, %s] (plafonds gelés A5)"
                             % (name, ceiling))

    if args.replay == "live":
        keys = [var for var in ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
                if os.environ.get(var)]
        if not keys:
            raise SystemExit("E_LLM_NO_KEY: mode live sans clé — poser ORVYREN_DEEPSEEK_API_KEY / "
                             "ORVYREN_MIMO_API_KEY dans l'environnement (jamais dans le dépôt) ; "
                             "sans clé, utiliser --replay journal (déterministe, hors-ligne).")

    inputs = load_case_inputs(args.case)
    session = args.session or os.path.join(REPO_ROOT, "demo_runs", "agents", args.case)
    store = args.store or os.path.join(REPO_ROOT, "fixtures", "agents", "store_%s" % args.case)
    budget = {"llm_calls": args.budget_llm, "tool_calls": args.budget_tools,
              "wall_seconds": args.budget_wall, "cost_usd": args.budget_usd}
    run_dir = prepare_run(case_id=args.case, mode=args.replay, session_dir=session,
                          inputs=inputs, store_dir=store, budget=budget,
                          record_live=args.record_live)
    print("ORVYREN — run_agents · %s · mode %s" % (args.case, args.replay))
    print("  run       : %s" % run_dir)
    if args.record_live:
        print("  store live: %s" % os.path.join(run_dir, "store_live"))

    for role in ("orchestrator", "critic"):
        print("  [%s] processus lancé…" % role)
        code = _spawn(role, run_dir, args.timeout_s)
        if code != 0:
            raise SystemExit("E_WORKER_%s: code %d — voir la sortie ci-dessus" % (role.upper(), code))

    final = collect_and_finish(run_dir=run_dir, case_id=args.case, mode=args.replay)
    _print_summary(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
