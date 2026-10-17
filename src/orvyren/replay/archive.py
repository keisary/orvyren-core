#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — REPLAY-ARCHIVE : recalcul sur données archivées (W7, mode 2).

Mode 2 (B7 §c.2, nom gelé ``REPLAY-ARCHIVE`` ; alias historique
``LIVE-REPLAY`` de B1 §6.3 conservé en traçabilité) : les **appels LLM sont
recalculés** sur le corpus figé et des blocs épinglés, versions de modèle
épinglées, temperature 0. Déterminisme **non garanti** : « même décision,
texte différent » — c'est un résultat à publiér (k ≥ 3 rejeux, distribution
des sorties), pas un échec.

Exigences opposables :

* un fournisseur LLM est **nécessaire** — sans clé, le mode refuse de tourner
  (jamais de recalcul simulé présenté comme réel) ;
* aucune lecture « live » : les entrées du run viennent de
  ``fixtures/agents/<case>/run_inputs.json`` (données archivées) et toute
  lecture chaîne éventuelle exige un bloc épinglé
  (:func:`orvyren.replay.corpus.require_pinned_block`) ;
* chaque passe écrit un **nouveau** journal (mode ``REPLAY-ARCHIVE``) —
  affichable côte à côte avec l'original.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from orvyren.replay import journal as journal_mod  # noqa: E402

MODE_LABEL = "REPLAY-ARCHIVE"
ALIAS = "LIVE-REPLAY (B1 §6.3)"
#: Clés d'environnement acceptées (processus seulement — jamais dans le dépôt).
KEY_ENV_VARS = ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
MIN_REPLAYS = 3  # B7 §c.7 mitigation 3 : k ≥ 3, on publie la distribution.


class ArchiveUnavailable(RuntimeError):
    """Mode archive impossible (clé absente) — l'échec est explicite, jamais simulé."""


def _keys_present(environ: Optional[Dict[str, str]] = None) -> List[str]:
    env = os.environ if environ is None else environ
    return [name for name in KEY_ENV_VARS if str(env.get(name, "")).strip()]


def replay_archive(case_id: str, work_root: str, *, k: int = MIN_REPLAYS,
                   environ: Optional[Dict[str, str]] = None,
                   quiet: bool = True) -> Dict[str, Any]:
    """k passes de recalcul (mode 2) ; exige un fournisseur LLM.

    Renvoie ``{"k", "run_dirs", "outcomes": [...], "identical": bool, "note"}``.
    ``identical`` porte honnêtement la distribution : ``False`` (textes
    différents) est un **résultat publié**, pas une erreur — la *décision*
    peut rester stable quand le texte diffère.
    """
    if k < MIN_REPLAYS:
        raise ArchiveUnavailable("le mode REPLAY-ARCHIVE exige k ≥ %d rejeux (B7 §c.7)"
                                 % MIN_REPLAYS)
    if not _keys_present(environ):
        raise ArchiveUnavailable(
            "E_LLM_NO_KEY: le mode REPLAY-ARCHIVE recalcule les appels LLM et exige un "
            "fournisseur (%s) dans l'environnement du processus — sans clé, utiliser le "
            "mode journal (déterministe, hors-ligne). Aucun recalcul simulé n'est présenté "
            "comme réel." % " / ".join(KEY_ENV_VARS))

    import run_agents

    results: List[Dict[str, Any]] = []
    for index in range(k):
        session = os.path.join(work_root, "archive_%02d" % index)
        os.makedirs(session, exist_ok=True)
        argv = ["--case", case_id, "--replay", "live", "--session", session]
        if quiet:
            with contextlib.redirect_stdout(io.StringIO()):
                code = run_agents.main(argv)
        else:
            code = run_agents.main(argv)
        if code != 0:
            raise ArchiveUnavailable("E_REPLAY_ARCHIVE: passe %d en échec (code %d)"
                                     % (index, code))
        run_dir = _find_live_run_dir(session, case_id)
        outcome_path = os.path.join(run_dir, "run_outcome.json")
        import json as _json
        with open(outcome_path, "r", encoding="utf-8") as handle:
            outcome = _json.load(handle)
        results.append({"run_dir": run_dir,
                        "stop_condition": (outcome.get("outcome") or {}).get("stop_condition"),
                        "inconclusive": bool((outcome.get("outcome") or {}).get("inconclusive")),
                        "verdict": (outcome.get("critique") or {}).get("verdict_lecture")})
    decisions = {(entry["stop_condition"], entry["inconclusive"]) for entry in results}
    return {"k": k, "case_id": case_id, "alias": ALIAS, "mode": MODE_LABEL,
            "run_dirs": [entry["run_dir"] for entry in results],
            "outcomes": results, "identical_decisions": len(decisions) <= 1,
            "note": ("« même décision, texte différent » est le résultat attendu et publié "
                     "(B7 §c.2) — la distribution des sorties est reportée telle quelle.")}


def _find_live_run_dir(session_dir: str, case_id: str) -> str:
    prefix = "%s_live_" % case_id.replace("/", "-")
    candidates = sorted(
        os.path.join(session_dir, name) for name in os.listdir(session_dir)
        if name.startswith(prefix) and os.path.isdir(os.path.join(session_dir, name)))
    if not candidates:
        raise ArchiveUnavailable("répertoire de run archive introuvable sous %s" % session_dir)
    return candidates[-1]
