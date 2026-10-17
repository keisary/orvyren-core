#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — REPLAY-JOURNAL : relecture bit-à-bit du journal d'agents (W7).

Mode 1 (B7 §c.2, nom gelé ``REPLAY-JOURNAL``) : on relit le journal d'agents et
le magasin de réponses (prompts/réponses bruts adressés par hash) — **rien
n'est recalculé** ; le chaînage ``prev_hash`` est vérifié à la lecture, ligne
par ligne, avant toute restitution. La reproductibilité **bit-à-bit est une
propriété de ce mode** et de lui seul.

Le rejeu réutilise le coordinateur W2 tel quel (``run_agents.py --replay
journal`` — identifiant de run épinglé ``demo-<case>``, réponses
enregistrées) : un rejeu k fois doit produire des **transcripts de hash
identiques** (critère k=10, B1 §6.2). Un run de rejeu **ne signe jamais** et
n'émet aucune transaction.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as _dt
import hashlib
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from orvyren.agents import worker as worker_mod  # noqa: E402

MODE_LABEL = "REPLAY-JOURNAL"
GENESIS_HASH = "0" * 64
#: Champs volatils jamais inclus dans le hash du transcript (audit d'exécution).
VOLATILE_KEYS = ("run_dir", "session_dir", "ts_wall", "wall_seconds", "duration_s")


class ReplayJournalError(RuntimeError):
    """Rejeu journal impossible (cas absent, journal incomplet, chaîne cassée)."""


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip_volatile(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _strip_volatile(value) for key, value in payload.items()
                if key not in VOLATILE_KEYS}
    if isinstance(payload, list):
        return [_strip_volatile(item) for item in payload]
    return payload


def _find_run_dir(session_dir: str, case_id: str) -> str:
    prefix = "%s_journal_" % case_id.replace("/", "-")
    candidates = sorted(
        os.path.join(session_dir, name) for name in os.listdir(session_dir)
        if name.startswith(prefix) and os.path.isdir(os.path.join(session_dir, name)))
    if not candidates:
        raise ReplayJournalError("aucun répertoire de run sous %s" % session_dir)
    return candidates[-1]


def replay_once(case_id: str, session_dir: str, *, quiet: bool = False) -> str:
    """Un rejeu journal (in-process, coordinateur W2 inchangé) → ``run_dir``."""
    import run_agents  # racine du dépôt (script coordinateur W2)

    os.makedirs(session_dir, exist_ok=True)
    argv = ["--case", case_id, "--replay", "journal", "--session", session_dir]
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            code = run_agents.main(argv)
    else:
        code = run_agents.main(argv)
    if code != 0:
        raise ReplayJournalError("E_REPLAY_RUN: code %d pour %s" % (code, case_id))
    return _find_run_dir(session_dir, case_id)


def load_transcript(run_dir: str) -> Dict[str, Any]:
    """Charge les deux journaux d'un run, vérifie les chaînes, rend le transcript.

    La vérification du chaînage est **bloquante** (B7 §c.4) : une ligne
    modifiée ⇒ refus de restituer.
    """
    outcome_path = os.path.join(run_dir, "run_outcome.json")
    if not os.path.isfile(outcome_path):
        raise ReplayJournalError("E_REPLAY_INCOMPLETE: run_outcome.json absent")
    with open(outcome_path, "r", encoding="utf-8") as handle:
        outcome = json.load(handle)
    journals: Dict[str, Any] = {}
    run_id = outcome.get("run_id")
    for role in ("orchestrator", "critic"):
        path = os.path.join(run_dir, "journal_%s.jsonl" % role)
        if not os.path.isfile(path):
            raise ReplayJournalError("E_REPLAY_INCOMPLETE: journal %s absent" % role)
        entries = worker_mod.load_journal(path)
        ok, message = worker_mod.verify_exported_chain(entries)
        if not ok:
            raise ReplayJournalError("E_REPLAY_CHAIN: %s — %s" % (role, message))
        if run_id is None and entries:
            run_id = getattr(entries[0], "run_id", None) or None
        journals[role] = {
            "lines": len(entries),
            "chain_head": worker_mod.entry_hash(entries[-1]) if entries else GENESIS_HASH,
            "entries": [dataclasses.asdict(entry) for entry in entries],
        }
    return {"schema": "orvyren.replay-transcript/v1",
            "case_id": outcome.get("case_id"), "run_id": run_id,
            "mode": MODE_LABEL,
            "journals": journals,
            "outcome": _strip_volatile(outcome)}


def transcript_hash(transcript: Dict[str, Any]) -> str:
    """SHA-256 canonique du transcript (champs volatils exclus)."""
    return hashlib.sha256(canonical_json(_strip_volatile(transcript)).encode("utf-8")).hexdigest()


def replay_k(case_id: str, work_root: str, *, k: int = 10,
             quiet: bool = True) -> Dict[str, Any]:
    """k rejeux journal indépendants → comparaison des hashes de transcript.

    Critère gelé B1 §6.2 / [DONE] W7 : ``k = 10`` rejeux ⇒ hash identique.
    Chaque rejeu vit dans sa propre session (``<work_root>/run_<i>/``) : aucun
    état partagé entre rejeux.
    """
    if k < 1:
        raise ReplayJournalError("k doit être ≥ 1")
    hashes: List[str] = []
    run_dirs: List[str] = []
    for index in range(k):
        session = os.path.join(work_root, "run_%02d" % index)
        run_dir = replay_once(case_id, session, quiet=quiet)
        transcript = load_transcript(run_dir)
        hashes.append(transcript_hash(transcript))
        run_dirs.append(run_dir)
    return {"k": k, "case_id": case_id, "hashes": hashes,
            "identical": len(set(hashes)) == 1,
            "hash": hashes[0], "run_dirs": run_dirs}


def verify_run(run_dir: str, *, expected_hash: Optional[str] = None) -> Dict[str, Any]:
    """T10 : recalcule le transcript d'un run et compare (journal identique)."""
    transcript = load_transcript(run_dir)
    computed = transcript_hash(transcript)
    verdict = "OK" if (expected_hash is None or expected_hash == computed) else "MISMATCH"
    return {"run_dir": run_dir, "transcript_hash": computed,
            "expected_hash": expected_hash, "verdict": verdict,
            "journals": {role: {"lines": info["lines"], "chain_head": info["chain_head"]}
                         for role, info in transcript["journals"].items()}}
