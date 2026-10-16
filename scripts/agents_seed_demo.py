#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — enregistrement du cas de démonstration des agents (W2/L2.6).

Écrit ``fixtures/agents/store_<case>/`` en **rejouant des réponses scriptées**
via le chemin d'enregistrement réel de ``LiveBackend`` (aucune clé, aucun
réseau) : le magasin obtenu rend ``run_agents.py --replay journal`` déterministe
et **hors-ligne** (B1 §6.3 : « rejouer les réponses enregistrées est
déterministe par construction — c'est le seul mode qu'on peut garantir devant
un jury »). Un manifeste ``SEED.json`` déclare l'origine scriptée — jamais
présentée comme un enregistrement live ; une vraie session live (avec clés)
remplace le magasin :

    python run_agents.py --case usdc-2023-03 --replay live

Usage ::

    python scripts/agents_seed_demo.py --case usdc-2023-03 [--force] [--session DIR]

Refuse d'écraser un magasin existant sans ``--force`` (protection d'un
enregistrement réel). Stdlib uniquement.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if os.path.join(REPO_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import run_agents  # noqa: E402

# ---------------------------------------------------------------------------
# Le scénario scripté (déterministe) — mêmes schémas que les validateurs gelés.
# ---------------------------------------------------------------------------
_ORCHESTRATOR = [
    {"content": {
        "$schema": "orvyren/orch/v1", "lacune_id": "L-1",
        "tache": {"question": "La source oracle confirme-t-elle la décote du pair USDC/USD ?",
                  "outil": "read_prices",
                  "args": {"venue": "chainlink", "symbol": "USDC-USD"},
                  "critere_discriminant": "si l'oracle confirme, la dislocation est partagée ; "
                                          "sinon elle est propre à une venue",
                  "branches_concernees": ["HYP-001", "HYP-002"],
                  "cout_max": {"appels_llm": 2, "secondes": 30}},
        "stop": False, "motif_stop": None, "non_recherche": []},
     "prompt_tokens": 1400, "completion_tokens": 260},
    {"content": {
        "claims": [{"enonce": "la source oracle confirme une décote du pair par rapport au pair",
                    "refs": ["observation:chainlink/usdc-usd/2023-03-11T12:00Z"],
                    "sens": "POUR", "branches_concernees": ["HYP-001"]}],
        "reflexions": ["la décote est confirmée par la première source"],
        "insuffisance": [], "note": ""},
     "prompt_tokens": 1500, "completion_tokens": 190},
    {"content": {
        "$schema": "orvyren/orch/v1", "lacune_id": "L-2",
        "tache": {"question": "La source d'exchange indépendante confirme-t-elle la décote réalisable ?",
                  "outil": "read_prices",
                  "args": {"venue": "bitstamp", "symbol": "USDC-USD"},
                  "critere_discriminant": "une décote plus profonde sur l'exchange indépendant "
                                          "confirme la dislocation réalisable",
                  "branches_concernees": ["HYP-001", "HYP-002"],
                  "cout_max": {"appels_llm": 2, "secondes": 30}},
        "stop": False, "motif_stop": None, "non_recherche": []},
     "prompt_tokens": 1650, "completion_tokens": 250},
    {"content": {
        "claims": [{"enonce": "l'exchange indépendant confirme une décote plus profonde",
                    "refs": ["observation:bitstamp/usdc-usd/2023-03-11T12:00Z"],
                    "sens": "POUR", "branches_concernees": ["HYP-001"]}],
        "reflexions": ["deux sources indépendantes concordent"],
        "insuffisance": ["profondeur d'exécution réalisable non mesurée"],
        "note": ""},
     "prompt_tokens": 1800, "completion_tokens": 200},
    {"content": {
        "$schema": "orvyren/orch/v1", "lacune_id": "", "tache": None,
        "stop": True, "motif_stop": "plus aucune tâche à valeur positive dans le plan",
        "non_recherche": ["profondeur d'exécution réalisable non mesurée"]},
     "prompt_tokens": 1750, "completion_tokens": 120},
]

_CRITIC = [
    {"content": {
        "$schema": "orvyren/crit/v1", "verdict_lecture": "FRAGILE",
        "findings": [{"type": "DEPENDANCE", "gravite": "MAJEUR",
                      "enonce": "les agrégateurs peuvent partager la même venue sous-jacente — "
                                "l'indépendance des sources n'est pas démontrée",
                      "refs": ["observation:defillama/usdc-usd/2023-03-11T12:00Z"],
                      "test_discriminant": "vérifier la méthodologie d'agrégation de chaque source"}],
        "preuves_manquantes": ["indépendance des méthodes d'agrégation"],
        "note": ""},
     "prompt_tokens": 900, "completion_tokens": 220},
]


def _write_json(path: str, payload) -> None:
    # newline="\n": LF-stable on Windows (this writes a committed fixture)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agents_seed_demo.py")
    parser.add_argument("--case", default="usdc-2023-03")
    parser.add_argument("--session", default=None,
                        help="répertoire des sorties de seed (défaut demo_runs/agents_seed/<case>)")
    parser.add_argument("--force", action="store_true",
                        help="écraser un magasin existant (protection d'un enregistrement réel)")
    args = parser.parse_args(argv)

    inputs = run_agents.load_case_inputs(args.case)
    store_dir = os.path.join(REPO_ROOT, "fixtures", "agents", "store_%s" % args.case)
    calls_path = os.path.join(store_dir, "calls.jsonl")
    if os.path.exists(calls_path) and not args.force:
        raise SystemExit("E_SEED_EXISTS: %s existe déjà — refus d'écraser un magasin "
                         "(un enregistrement live? utiliser --force si c'est bien un seed scripté)"
                         % calls_path)

    session = args.session or os.path.join(REPO_ROOT, "demo_runs", "agents_seed", args.case)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = os.path.join(session, "%s_seed_%s" % (args.case, stamp))
    os.makedirs(os.path.join(run_dir, "exchanges"), exist_ok=True)

    spec = {
        "schema": "orvyren/agent-run/v1",
        "run_id": "demo-%s" % args.case,
        "case_id": args.case,
        "mode": "journal",            # horloge virtuelle (déterminisme)
        "backend": "scripted",        # transport scripté -> enregistrement réel dans le magasin
        "budget": {"llm_calls": 30, "tool_calls": 12, "wall_seconds": 600, "cost_usd": 0.10},
        "snapshot": inputs["snapshot"],
        "lacunes": inputs["lacunes"],
        "hypotheses": inputs["hypotheses"],
        "tool_fixtures": inputs["tool_fixtures"],
        "store_dir": os.path.abspath(store_dir),
        "created_at": inputs.get("pinned_created_at")
                      or datetime.now(timezone.utc).isoformat(),
    }
    _write_json(os.path.join(run_dir, "run.json"), spec)
    _write_json(os.path.join(run_dir, "scripted_responses.json"),
                {"orchestrator": _ORCHESTRATOR, "critic": _CRITIC})

    print("ORVYREN — seed scripté du cas %s" % args.case)
    print("  magasin cible : %s" % store_dir)
    print("  run de seed   : %s" % run_dir)
    for role in ("orchestrator", "critic"):
        print("  [%s] processus lancé…" % role)
        code = run_agents._spawn(role, run_dir, 180.0)
        if code != 0:
            raise SystemExit("E_SEED_WORKER_%s: code %d" % (role.upper(), code))

    final = run_agents.collect_and_finish(run_dir=run_dir, case_id=args.case, mode="journal")
    run_agents._print_summary(final)

    records = 0
    if os.path.exists(calls_path):
        with open(calls_path, "r", encoding="utf-8") as handle:
            records = sum(1 for line in handle if line.strip())
    _write_json(os.path.join(store_dir, "SEED.json"),
                {"kind": "scripted-demo", "case": args.case,
                 "created_at": datetime.now(timezone.utc).isoformat(), "records": records,
                 "note": "Réponses SCRIPTÉES (démo hors-ligne) enregistrées par le chemin "
                         "LiveBackend réel. Remplacer par une session live quand les clés "
                         "existent : python run_agents.py --case %s --replay live" % args.case})
    print()
    print("  [ok] magasin enregistré : %d appels — %s" % (records, store_dir))
    print("  [ok] manifeste SEED.json écrit (origine scriptée déclarée)")
    print("  → rejeu hors-ligne : python run_agents.py --case %s --replay journal" % args.case)
    return 0


if __name__ == "__main__":
    sys.exit(main())
