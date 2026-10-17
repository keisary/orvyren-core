#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — REPLAY-ARCHIVE: recomputation on archived data (W7, mode 2).

Mode 2 (B7 §c.2, frozen name ``REPLAY-ARCHIVE``; historical alias
``LIVE-REPLAY`` from B1 §6.3 kept for traceability): **LLM calls are
recomputed** on the frozen corpus and pinned blocks, with pinned model
versions and temperature 0. Determinism is **not guaranteed**: "same decision,
different text" — this is a result to publish (k ≥ 3 replays, distribution of
outputs), not a failure.

Opposable requirements:

* an LLM provider is **required** — without a key, the mode refuses to run
  (never a simulated recomputation presented as real);
* no "live" read: run inputs come from
  ``fixtures/agents/<case>/run_inputs.json`` (archived data) and any chain read
  requires a pinned block
  (:func:`orvyren.replay.corpus.require_pinned_block`);
* each pass writes a **new** journal (mode ``REPLAY-ARCHIVE``) — displayable
  side by side with the original.
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
#: Accepted environment keys (process only — never in the repository).
KEY_ENV_VARS = ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
MIN_REPLAYS = 3  # B7 §c.7 mitigation 3: k ≥ 3, the distribution is published.


class ArchiveUnavailable(RuntimeError):
    """Archive mode impossible (missing key) — the failure is explicit, never simulated."""


def _keys_present(environ: Optional[Dict[str, str]] = None) -> List[str]:
    env = os.environ if environ is None else environ
    return [name for name in KEY_ENV_VARS if str(env.get(name, "")).strip()]


def replay_archive(case_id: str, work_root: str, *, k: int = MIN_REPLAYS,
                   environ: Optional[Dict[str, str]] = None,
                   quiet: bool = True) -> Dict[str, Any]:
    """k recomputation passes (mode 2); requires an LLM provider.

    Returns ``{"k", "run_dirs", "outcomes": [...], "identical": bool, "note"}``.
    ``identical`` honestly carries the distribution: ``False`` (different
    texts) is a **published result**, not an error — the *decision* may stay
    stable while the text differs.
    """
    if k < MIN_REPLAYS:
        raise ArchiveUnavailable("REPLAY-ARCHIVE mode requires k ≥ %d replays (B7 §c.7)"
                                 % MIN_REPLAYS)
    if not _keys_present(environ):
        raise ArchiveUnavailable(
            "E_LLM_NO_KEY: REPLAY-ARCHIVE mode recomputes LLM calls and requires a "
            "provider (%s) in the process environment — without a key, use the "
            "journal mode (deterministic, offline). No simulated recomputation is "
            "presented as real." % " / ".join(KEY_ENV_VARS))

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
            raise ArchiveUnavailable("E_REPLAY_ARCHIVE: pass %d failed (exit code %d)"
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
        raise ArchiveUnavailable("archive run directory not found under %s" % session_dir)
    return candidates[-1]
