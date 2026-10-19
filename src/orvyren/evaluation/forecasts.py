#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ORVYREN-Core — frozen forecasts: format, hashing, chaining (G1/G6).

Normative source: B7 §a.4 (JSON schema of the forecast), §a.5 (opposable
rules), §a.6 (append-only storage), DOC2 §5.8.1.

Opposable rules implemented:

* **append-only**: a forecast is never rewritten nor deleted; the JSONL file
  is chained by ``prev_hash`` (same mechanics as ``audit.jsonl`` and the agent
  journal);
* **digest**: self-carried ``sha256``, recomputed on every verification;
* **modification of ``p`` forbidden after the freeze**: an identifier that
  already exists cannot be re-registered with different content — the write is
  refused (and not silently replaced);
* **freeze first**: the write requires a ``frozen/G1..G6.sha256`` package that
  is present and matching (gate :func:`orvyren.evaluation.windows.verify_frozen_package`);
* **``p`` is never produced by an LLM**: the ``p_origin`` field must describe
  the deterministic computation or the documented prior (cited source).
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Dict, List, Optional, Sequence

from orvyren.evaluation import windows as windows_mod

SCHEMA = "orvyren.forecast.v1"
GENESIS_HASH = "0" * 64

HORIZON_H_CLASS = "H_class"
HORIZON_T = "T"
HORIZON_KINDS = (HORIZON_H_CLASS, HORIZON_T)

REQUIRED_FIELDS = (
    "schema",
    "forecast_id",
    "run_id",
    "episode_id",
    "set",
    "persona",
    "statement",
    "resolution_rule_id",
    "horizon",
    "p",
    "p_origin",
    "y_definition",
    "observation_state_at_freeze",
    "refs",
    "signed_by",
    "sha256",
    "prev_hash",
)

#: Canonical location of the freeze package (B7 §c.4: ``frozen/Gx.sha256``).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class ForecastError(ValueError):
    """Invalid or duplicated forecast, or forbidden modification."""


def default_frozen_dir() -> str:
    return os.path.join(REPO_ROOT, "frozen")


def canonical_bytes(record: Dict) -> bytes:
    """Canonical serialisation: sorted keys, compact separators, UTF-8, LF."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def record_hash(record: Dict) -> str:
    """Self-carried digest: SHA-256 of the record, ``sha256`` field zeroed."""
    clone = dict(record)
    clone["sha256"] = GENESIS_HASH
    return hashlib.sha256(canonical_bytes(clone)).hexdigest()


def _validate(record: Dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ForecastError(f"missing required fields: {missing}")
    if record["schema"] != SCHEMA:
        raise ForecastError(f"expected schema {SCHEMA!r}, got {record['schema']!r}")
    if not isinstance(record["p"], (int, float)) or not 0.0 <= float(record["p"]) <= 1.0:
        raise ForecastError(f"p outside [0, 1]: {record['p']!r}")
    if not str(record["statement"]).strip():
        raise ForecastError("empty statement: a forecast without a statement is not falsifiable")
    if not str(record["p_origin"]).strip():
        raise ForecastError("empty p_origin: the origin of p must be written (computation or cited prior)")
    if not str(record["resolution_rule_id"]).strip():
        raise ForecastError("empty resolution_rule_id")
    horizon = record["horizon"]
    if horizon.get("kind") not in HORIZON_KINDS:
        raise ForecastError(f"horizon.kind expected in {HORIZON_KINDS}, got {horizon.get('kind')!r}")
    for key in ("t_frozen_utc", "resolve_not_before_utc"):
        if not horizon.get(key):
            raise ForecastError(f"horizon.{key} missing")
    if windows_mod.parse_utc(horizon["resolve_not_before_utc"]) <= windows_mod.parse_utc(horizon["t_frozen_utc"]):
        raise ForecastError("resolve_not_before_utc must be later than t_frozen_utc")
    if record["set"] not in windows_mod.SETS:
        raise ForecastError(f"set expected in {windows_mod.SETS}, got {record['set']!r}")
    signed = record["signed_by"]
    if not isinstance(signed, dict) or not signed.get("role"):
        raise ForecastError("signed_by.role missing: an unsigned forecast is not frozen")


def build_forecast(
    forecast_id: str,
    run_id: str,
    episode_id: str,
    set_label: str,
    persona: str,
    statement: str,
    resolution_rule_id: str,
    t_frozen_utc: str,
    resolve_not_before_utc: str,
    p: float,
    p_origin: str,
    y_definition: Dict,
    observation_state_at_freeze: Dict,
    refs: Optional[Dict] = None,
    signed_by: Optional[Dict] = None,
    horizon_kind: str = HORIZON_H_CLASS,
    horizon_hours: Optional[float] = None,
    t_end_utc: Optional[str] = None,
) -> Dict:
    """Build a complete forecast (``sha256`` computed, ``prev_hash`` at GENESIS).

    ``prev_hash`` and ``sha256`` are set here to their initial value; it is
    :func:`append_forecast` that sets the real chaining at write time.
    ``t_end_utc`` is required only for the ``T`` horizon (end of window).
    """
    horizon = {
        "kind": horizon_kind,
        "hours": horizon_hours,
        "t_frozen_utc": t_frozen_utc,
        "resolve_not_before_utc": resolve_not_before_utc,
    }
    if t_end_utc is not None:
        horizon["t_end_utc"] = t_end_utc
    record = {
        "schema": SCHEMA,
        "forecast_id": forecast_id,
        "run_id": run_id,
        "episode_id": episode_id,
        "set": set_label,
        "persona": persona,
        "statement": statement,
        "resolution_rule_id": resolution_rule_id,
        "horizon": horizon,
        "p": float(p),
        "p_origin": p_origin,
        "y_definition": y_definition,
        "observation_state_at_freeze": observation_state_at_freeze,
        "refs": refs or {"hypothesis_ids": [], "branch_ids": [], "observation_ids": []},
        "signed_by": signed_by or {"role": "gel-g6", "name": "<to be signed>"},
        "sha256": GENESIS_HASH,
        "prev_hash": GENESIS_HASH,
    }
    _validate(record)
    record["sha256"] = record_hash(record)
    return record


def load_forecasts(path: str) -> List[Dict]:
    """Load a JSONL forecast file (blank lines ignored)."""
    if not os.path.isfile(path):
        return []
    records: List[Dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as exc:  # corrupted line = explicit refusal
                raise ForecastError(f"{path}:{line_number}: unreadable JSON ({exc})") from exc
    return records


def verify_forecast_chain(records: Sequence[Dict], path: str = "<memory>") -> List[str]:
    """Verify chaining + digests; return the list of identifiers.

    A single divergence is enough to raise: a forecast file whose chain is
    broken is not usable (B7 §a.5).
    """
    previous = GENESIS_HASH
    ids: List[str] = []
    for index, record in enumerate(records, start=1):
        expected = record_hash(record)
        if record.get("sha256") != expected:
            raise ForecastError(
                f"{path} line {index}: mismatched digest "
                f"({record.get('sha256')} ≠ {expected}) — file modified?"
            )
        if record.get("prev_hash") != previous:
            raise ForecastError(
                f"{path} line {index}: broken chain (prev_hash {record.get('prev_hash')} ≠ {previous})"
            )
        previous = record["sha256"]
        ids.append(record["forecast_id"])
    return ids


def append_forecast(
    path: str,
    record: Dict,
    frozen_dir: Optional[str] = None,
    require_frozen: bool = True,
) -> Dict:
    """Write a forecast at the end of the file, after the freeze and chain checks.

    Explicit refusals: freeze package absent/mismatched, invalid fields,
    identifier already frozen (append-only: ``p`` is never modified), existing
    chain broken.
    """
    if require_frozen:
        windows_mod.verify_frozen_package(frozen_dir or default_frozen_dir())
    _validate(record)
    existing = load_forecasts(path)
    verify_forecast_chain(existing, path=path)
    for prior in existing:
        if prior["forecast_id"] == record["forecast_id"]:
            if prior["sha256"] == record_hash(record):
                raise ForecastError(f"forecast already frozen (identical): {record['forecast_id']}")
            raise ForecastError(
                f"modification forbidden: forecast {record['forecast_id']} already exists "
                "with a different content (p is never modified after the freeze)"
            )
    final = dict(record)
    final["prev_hash"] = existing[-1]["sha256"] if existing else GENESIS_HASH
    final["sha256"] = record_hash(final)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(final, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return final


def find_forecast(records: Sequence[Dict], forecast_id: str) -> Dict:
    for record in records:
        if record["forecast_id"] == forecast_id:
            return record
    raise ForecastError(f"unknown forecast: {forecast_id}")
