#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — dossier de rejeu : provenance, bannière, hash (W7, B7 §c.5).

Tout artefact de rejeu porte : (1) un bloc de provenance ``{mode, replay_id,
t_sim_start, t_sim_end, corpus_hash, code_hash, alias?}`` ; (2) une **bannière
obligatoire** ``REPLAY — données archivées — <mode> — <épisode> — t_sim=<…>``
(toute sortie sans bannière est un bug) ; (3) un nom de fichier suffixé
``_replay_<mode>_<replay_id>`` ; (4) un journal append-only
``replay/runs.jsonl`` (échecs inclus). Le hash du dossier est recalculable par
un tiers (T10) — champs d'exécution réels exclus.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_RUNS_LOG = os.path.join(REPO_ROOT, "replay", "runs.jsonl")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "evidence", "replay")

BANNER_TEMPLATE = "REPLAY — données archivées — {mode} — {episode} — t_sim={t0}→{t1}"

#: Champs d'exécution réels exclus du hash de contenu (audit vs contenu).
WALL_KEYS = ("ts_wall_utc", "duration_s", "generated_at", "run_dirs", "work_root")


class DossierError(RuntimeError):
    """Dossier de rejeu invalide (bannière absente, hash non concordant)."""


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _strip_wall(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _strip_wall(value) for key, value in payload.items()
                if key not in WALL_KEYS}
    if isinstance(payload, list):
        return [_strip_wall(item) for item in payload]
    return payload


def code_hash(extra_files: Optional[List[str]] = None) -> str:
    """Empreinte du code du moteur de rejeu (``src/orvyren/replay/`` + CLI)."""
    files: List[str] = []
    package_dir = os.path.join(REPO_ROOT, "src", "orvyren", "replay")
    for name in sorted(os.listdir(package_dir)):
        if name.endswith(".py"):
            files.append(os.path.join(package_dir, name))
    files.append(os.path.join(REPO_ROOT, "run_replay.py"))
    for path in (extra_files or []):
        files.append(path)
    digest = hashlib.sha256()
    for path in sorted(set(files)):
        digest.update(os.path.basename(path).encode("utf-8"))
        with open(path, "rb") as handle:
            digest.update(handle.read())
    return digest.hexdigest()


def new_replay_id(episode: str, mode_slug: str) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return "%s-%s-%s" % (episode, mode_slug, stamp)


def build_replay_dossier(*, episode: str, mode: str, mode_slug: str, run_id: str,
                         t_sim_start_utc: str, t_sim_end_utc: str,
                         corpus_manifest: dict, clock_audit: dict,
                         transcript: Optional[dict] = None, k_report: Optional[dict] = None,
                         archive_report: Optional[dict] = None,
                         replay_id: Optional[str] = None,
                         out_dir: str = DEFAULT_OUT_DIR,
                         runs_log: str = DEFAULT_RUNS_LOG,
                         duration_s: Optional[float] = None) -> Dict[str, Any]:
    """Assemble le dossier de rejeu (JSON + MD), hash, et journalise le run."""
    replay_id = replay_id or new_replay_id(episode, mode_slug)
    banner = BANNER_TEMPLATE.format(mode=mode, episode=episode,
                                    t0=t_sim_start_utc, t1=t_sim_end_utc)
    provenance = {"mode": mode, "replay_id": replay_id,
                  "t_sim_start": t_sim_start_utc, "t_sim_end": t_sim_end_utc,
                  "corpus_hash": corpus_manifest.get("manifest_sha256"),
                  "code_hash": code_hash(),
                  "alias": "LIVE-REPLAY (B1 §6.3)" if mode == "REPLAY-ARCHIVE" else None}
    content = {"schema": "orvyren.replay-dossier/v1",
               "banner": banner, "provenance": provenance,
               "run_id": run_id, "clock_audit": clock_audit}
    if transcript is not None:
        import orvyren.replay.journal as journal_mod
        content["transcript_hash"] = journal_mod.transcript_hash(transcript)
        content["journals"] = {role: {"lines": info["lines"], "chain_head": info["chain_head"]}
                               for role, info in transcript["journals"].items()}
    if k_report is not None:
        content["k_report"] = k_report
    if archive_report is not None:
        content["archive_report"] = archive_report
    content_sha = hashlib.sha256(canonical_json(_strip_wall(content)).encode("utf-8")).hexdigest()

    os.makedirs(out_dir, exist_ok=True)
    base = "%s_replay_%s_%s" % (episode, mode_slug, replay_id)
    json_path = os.path.join(out_dir, base + ".json")
    md_path = os.path.join(out_dir, base + ".md")
    document = dict(content, content_sha256=content_sha,
                    ts_wall_utc=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    duration_s=duration_s)
    with open(json_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Dossier de rejeu — %s\n\n> **%s**\n\n" % (episode, banner))
        handle.write("| Champ | Valeur |\n|---|---|\n")
        table_values = {"run_id": document.get("run_id"),
                        "mode": provenance.get("mode"),
                        "replay_id": provenance.get("replay_id"),
                        "corpus_hash": provenance.get("corpus_hash"),
                        "code_hash": provenance.get("code_hash"),
                        "content_sha256": content_sha,
                        "ts_wall_utc": document.get("ts_wall_utc")}
        for key in ("run_id", "mode", "replay_id", "corpus_hash", "code_hash",
                    "content_sha256", "ts_wall_utc"):
            handle.write("| `%s` | `%s` |\n" % (key, table_values.get(key)))
        if transcript is not None:
            handle.write("\n## Journaux rejoués (bit-à-bit)\n\n")
            for role, info in content["journals"].items():
                handle.write("- **%s** — %d lignes — tête de chaîne `%s`\n"
                             % (role, info["lines"], info["chain_head"]))
        if k_report is not None:
            handle.write("\n## Déterminisme (k rejeux)\n\n- k = %d — hash %s : `%s`\n"
                         % (k_report["k"], "IDENTIQUE" if k_report["identical"] else "DIVERGENT",
                            k_report["hash"]))
        if archive_report is not None:
            handle.write("\n## Distribution des passes REPLAY-ARCHIVE\n\n")
            for entry in archive_report["outcomes"]:
                handle.write("- `%s` — arrêt %s%s\n"
                             % (os.path.basename(entry["run_dir"]), entry["stop_condition"],
                                " (abstention)" if entry["inconclusive"] else ""))
        handle.write("\n*Aucune signature, aucune transaction émise (B7 §c.5-4). "
                     "Intégrité, pas vérité : voir README_AUDIT.*\n")

    _append_runs_log(runs_log, {
        "replay_id": replay_id, "mode": mode, "episode": episode, "run_id": run_id,
        "t_sim_start": t_sim_start_utc, "t_sim_end": t_sim_end_utc,
        "corpus_hash": provenance["corpus_hash"], "code_hash": provenance["code_hash"],
        "content_sha256": content_sha, "result": "OK", "duration_s": duration_s,
        "ts_wall_utc": document["ts_wall_utc"]})
    return {"replay_id": replay_id, "banner": banner, "json_path": json_path,
            "md_path": md_path, "content_sha256": content_sha, "provenance": provenance}


def _append_runs_log(runs_log: str, entry: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(runs_log)), exist_ok=True)
    with open(runs_log, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(entry) + "\n")


def require_banner(document: dict) -> str:
    """Toute sortie de rejeu sans bannière est un bug (B7 §c.5-2)."""
    banner = str(document.get("banner") or "")
    if "REPLAY" not in banner:
        raise DossierError("marquage REPLAY obligatoire absent : toute sortie de rejeu "
                           "doit porter sa bannière (B7 §c.5)")
    return banner


def verify_replay_dossier(path: str, *, runs_log: str = DEFAULT_RUNS_LOG) -> Dict[str, Any]:
    """T10 : recalcule le hash de contenu et compare au journal des rejeux.

    Fail-closed : un dossier dont le ``replay_id`` n'apparaît **pas** dans
    ``runs.jsonl`` est déclaré ``NOT_REGISTERED`` avec une erreur explicite —
    jamais ``OK``. Un dossier isolé ne prouve pas qu'un rejeu a eu lieu ; seul
    le journal append-only atteste de son existence.
    """
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    banner = require_banner(document)
    stored = document.get("content_sha256")
    stripped = {key: value for key, value in document.items()
                if key not in ("content_sha256", "ts_wall_utc", "duration_s")}
    computed = hashlib.sha256(canonical_json(_strip_wall(stripped)).encode("utf-8")).hexdigest()
    replay_id = document.get("provenance", {}).get("replay_id")
    logged = None
    registered = False
    if os.path.isfile(runs_log):
        with open(runs_log, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("replay_id") == replay_id:
                    registered = True
                    logged = entry.get("content_sha256")
                    break
    error = None
    if not registered:
        verdict = "NOT_REGISTERED"
        error = ("replay_id %r absent de %s — dossier non journalisé : aucun rejeu "
                 "ne l'atteste" % (replay_id, runs_log))
    elif computed != stored:
        verdict = "MISMATCH"
        error = "content_sha256 recalculé != content_sha256 stocké"
    elif logged != stored:
        verdict = "MISMATCH"
        error = "content_sha256 journalisé != content_sha256 stocké"
    else:
        verdict = "OK"
    return {"banner": banner, "stored": stored, "computed": computed,
            "logged": logged, "registered": registered,
            "verdict": verdict, "error": error}
