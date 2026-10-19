#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ORVYREN-Core — outcomes: deterministic resolver, chained formats.

Normative source: B7 §a.2 (three producers), §a.3 (windows and states),
§a.4 (JSON schema of the outcome), §a.5 (opposable rules), §a.7 (what is not
an outcome), DOC2 §5.8.1.

Three resolution rules, each frozen by identifier:

* ``sustained_depeg_v1`` — "sustained depeg" (R3 M2 / B7 §0.2): deviation
  ``> ecart_pct`` **persisting ≥ persistance_obs observations** of the grid,
  contiguity required (gap ≤ ``max_gap_minutes``). Parameters carried by the
  forecast (``y_definition``), not invented here;
* ``calm_window_v1`` — frozen CALM criterion (B7 §d.1): ``max|P_t − 1| < 0.5 %``
  over the whole window; failure → reclassified STRESS (the result is a failure
  of the statement, not an adjustment of the statement).

Code guards (tested):

* **``resolve_not_before``**: an outcome cannot be written before the
  resolution horizon (``ResolutionTooEarly``) — B7 §a.5.5;
* **digest binding**: ``forecast_hash`` must match the recomputed digest of the
  forecast on disk, otherwise the outcome is rejected;
* **append-only + ``prev_hash`` chaining** (same mechanics as the forecasts);
* **corrections**: new outcome with ``supersedes: <outcome_id>`` — both remain
  visible (B7 §a.5.3).

``resolution_time`` is the timestamp of the **resolution window** (not the job
execution time); ``written_at_utc`` is the actual write time; the two are
distinct and published.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

from orvyren.evaluation import forecasts as forecasts_mod
from orvyren.evaluation import windows as windows_mod

SCHEMA = "orvyren.outcome.v1"

RULE_SUSTAINED_DEPEG = "sustained_depeg_v1"
RULE_CALM_WINDOW = "calm_window_v1"
RULES = (RULE_SUSTAINED_DEPEG, RULE_CALM_WINDOW)

RESOLVER_MODE_DETERMINISTIC = "deterministic"
RESOLVER_VERSION = "outcomes-v1"

REQUIRED_FIELDS = (
    "schema",
    "outcome_id",
    "forecast_id",
    "forecast_hash",
    "horizon",
    "y",
    "observed",
    "resolution_rule_id",
    "resolver",
    "evidence_refs",
    "written_at_utc",
    "prev_hash",
    "supersedes",
)


class OutcomeError(ValueError):
    """Invalid outcome (fields, y, binding, chain)."""


class ResolutionTooEarly(RuntimeError):
    """Attempt to write an outcome before ``resolve_not_before``: refused."""


def canonical_bytes(record: Dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --- resolution: the rules --------------------------------------------------


def _series_in_window(series: Sequence[Tuple[str, float]], start: _dt.datetime, end: _dt.datetime):
    points = []
    for stamp, price in series:
        moment = windows_mod.parse_utc(stamp)
        if start <= moment <= end:
            points.append((moment, float(price)))
    points.sort(key=lambda pair: pair[0])
    return points


def sustained_depeg_v1(
    series: Sequence[Tuple[str, float]],
    t_from_utc: str,
    t_to_utc: str,
    ecart_pct: float = 1.0,
    persistance_obs: int = 2,
    max_gap_minutes: float = 90.0,
    peg: float = 1.0,
) -> dict:
    """Rule ``sustained_depeg_v1``: ``y = 1`` iff a sustained depeg is observed.

    A "sustained depeg" = ``persistance_obs`` **consecutive** observations
    (gap ≤ ``max_gap_minutes``) with deviation ``(peg − price)/peg · 100 > ecart_pct``,
    inside the window ``[t_from, t_to]``. Deterministic: the same corpus gives
    the same result, bit for bit.
    """
    if persistance_obs < 2:
        raise OutcomeError("persistance_obs ≥ 2 required (\"sustained\" = at least two observations)")
    start, end = windows_mod.parse_utc(t_from_utc), windows_mod.parse_utc(t_to_utc)
    if end < start:
        raise OutcomeError("inverted resolution window")
    points = _series_in_window(series, start, end)
    if not points:
        raise OutcomeError(f"no observation in the window {t_from_utc} → {t_to_utc}: not resolvable")
    worst_utc, worst_price = min(points, key=lambda pair: pair[1])
    max_discount_pct = (peg - worst_price) / peg * 100.0
    gaps = _dt.timedelta(minutes=max_gap_minutes)
    runs: List[List[Tuple[_dt.datetime, float]]] = []
    current: List[Tuple[_dt.datetime, float]] = []
    previous: Optional[_dt.datetime] = None
    for moment, price in points:
        discount = (peg - price) / peg * 100.0
        contiguous = previous is not None and (moment - previous) <= gaps
        if discount > ecart_pct and (not current or contiguous):
            current.append((moment, price))
        elif discount > ecart_pct:
            if len(current) >= persistance_obs:
                runs.append(current)
            current = [(moment, price)]
        else:
            if len(current) >= persistance_obs:
                runs.append(current)
            current = []
        previous = moment
    if len(current) >= persistance_obs:
        runs.append(current)
    y = 1 if runs else 0
    first = runs[0] if runs else None
    return {
        "y": y,
        "resolution_rule_id": RULE_SUSTAINED_DEPEG,
        "observed": {
            "rule": RULE_SUSTAINED_DEPEG,
            "ecart_pct": ecart_pct,
            "persistance_obs": persistance_obs,
            "max_gap_minutes": max_gap_minutes,
            "n_observations": len(points),
            "min_price": worst_price,
            "max_discount_pct": round(max_discount_pct, 6),
            "first_violation_utc": windows_mod.format_utc(worst_utc),
            "sustained_runs": len(runs),
            "longest_run_obs": max((len(run) for run in runs), default=0),
            "first_sustained_utc": windows_mod.format_utc(first[-1][0]) if first else None,
        },
        "evidence_refs": [f"observation:{windows_mod.format_utc(moment)}" for moment, _ in points],
    }


def calm_window_v1(
    series: Sequence[Tuple[str, float]],
    t_from_utc: str,
    t_to_utc: str,
    tolerance_pct: float = 0.5,
    peg: float = 1.0,
) -> dict:
    """Rule ``calm_window_v1``: frozen CALM criterion ``max|P_t − 1| < 0.5 %``.

    ``y = 1`` iff the window is **entirely** calm in the sense of the criterion
    (failure → STRESS reclassification, result published as is — never a
    retroactive adjustment of the criterion).
    """
    start, end = windows_mod.parse_utc(t_from_utc), windows_mod.parse_utc(t_to_utc)
    if end < start:
        raise OutcomeError("inverted resolution window")
    points = _series_in_window(series, start, end)
    if not points:
        raise OutcomeError(f"no observation in the window {t_from_utc} → {t_to_utc}: not resolvable")
    worst_moment, worst_price = max(points, key=lambda pair: abs(pair[1] - peg))
    max_dev_pct = abs(worst_price - peg) / peg * 100.0
    return {
        "y": 1 if max_dev_pct < tolerance_pct else 0,
        "resolution_rule_id": RULE_CALM_WINDOW,
        "observed": {
            "rule": RULE_CALM_WINDOW,
            "tolerance_pct": tolerance_pct,
            "n_observations": len(points),
            "max_abs_deviation_pct": round(max_dev_pct, 6),
            "worst_observation_utc": windows_mod.format_utc(worst_moment),
            "worst_price": worst_price,
        },
        "evidence_refs": [f"observation:{windows_mod.format_utc(moment)}" for moment, _ in points],
    }


_RESOLVERS = {
    RULE_SUSTAINED_DEPEG: sustained_depeg_v1,
    RULE_CALM_WINDOW: calm_window_v1,
}


# --- resolution of a forecast ------------------------------------------------


def resolve_forecast(
    forecast: Dict,
    series: Sequence[Tuple[str, float]],
    now_utc: Optional[str] = None,
    code_hash: Optional[str] = None,
    supersedes: Optional[str] = None,
) -> Dict:
    """Resolve a frozen forecast → outcome (not yet chained).

    Refusals: mismatched forecast digest; ``now`` earlier than
    ``resolve_not_before_utc``; unknown rule; window without observation.
    """
    expected_hash = forecasts_mod.record_hash(forecast)
    if forecast.get("sha256") != expected_hash:
        raise OutcomeError(
            f"forecast {forecast.get('forecast_id')}: mismatched digest "
            f"({forecast.get('sha256')} ≠ {expected_hash}) — digest binding broken"
        )
    horizon = forecast["horizon"]
    resolve_not_before = windows_mod.parse_utc(horizon["resolve_not_before_utc"])
    reference_now = windows_mod.parse_utc(now_utc) if now_utc else _dt.datetime.now(_dt.timezone.utc)
    if reference_now < resolve_not_before:
        raise ResolutionTooEarly(
            f"forecast {forecast['forecast_id']}: resolve_not_before = "
            f"{horizon['resolve_not_before_utc']} > {windows_mod.format_utc(reference_now)} — "
            "an outcome is never written before the horizon (code guard, B7 §a.5.5)"
        )
    rule_id = forecast["resolution_rule_id"]
    resolver = _RESOLVERS.get(rule_id)
    if resolver is None:
        raise OutcomeError(f"unknown resolution rule: {rule_id!r} (known: {RULES})")
    definition = forecast.get("y_definition", {})
    kwargs = {"peg": definition.get("peg", 1.0)}
    for key in ("ecart_pct", "persistance_obs", "max_gap_minutes", "tolerance_pct"):
        if key in definition:
            kwargs[key] = definition[key]
    t_frozen = horizon["t_frozen_utc"]
    if horizon["kind"] == forecasts_mod.HORIZON_T:
        t_to = horizon.get("t_end_utc") or horizon["resolve_not_before_utc"]
    else:
        t_to = horizon["resolve_not_before_utc"]
    outcome_of_rule = resolver(series, t_frozen, t_to, **kwargs)
    outcome = {
        "schema": SCHEMA,
        "outcome_id": f"{forecast['forecast_id']}.{horizon['kind'].lower()}",
        "forecast_id": forecast["forecast_id"],
        "forecast_hash": forecast["sha256"],
        "horizon": {
            "kind": horizon["kind"],
            "t_resolution_window_utc": horizon["resolve_not_before_utc"],
            "t_from_utc": t_frozen,
            "t_to_utc": t_to,
        },
        "y": outcome_of_rule["y"],
        "observed": outcome_of_rule["observed"],
        "resolution_rule_id": rule_id,
        "resolver": {
            "mode": RESOLVER_MODE_DETERMINISTIC,
            "version": RESOLVER_VERSION,
            "code_hash": code_hash,
        },
        "evidence_refs": outcome_of_rule["evidence_refs"],
        "written_at_utc": windows_mod.format_utc(reference_now),
        "prev_hash": forecasts_mod.GENESIS_HASH,
        "supersedes": supersedes,
    }
    return outcome


def outcome_hash(record: Dict) -> str:
    """Digest of an outcome (the ``signature`` field excludes itself)."""
    body = {key: value for key, value in record.items() if key != "signature"}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def load_outcomes(path: str) -> List[Dict]:
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
            except json.JSONDecodeError as exc:
                raise OutcomeError(f"{path}:{line_number} : JSON illisible ({exc})") from exc
    return records


def verify_outcome_chain(records: Sequence[Dict], path: str = "<memory>") -> List[str]:
    """Verify the ``prev_hash`` chaining of the outcomes (an outcome digest is
    the digest of its JSONL content, recomputable by a third party)."""
    previous = forecasts_mod.GENESIS_HASH
    ids: List[str] = []
    for index, record in enumerate(records, start=1):
        if record.get("prev_hash") != previous:
            raise OutcomeError(
                f"{path} line {index}: broken chain (prev_hash {record.get('prev_hash')} ≠ {previous})"
            )
        previous = outcome_hash(record)
        if record.get("signature") and record["signature"] != previous:
            raise OutcomeError(
                f"{path} line {index}: mismatched outcome signature")
        ids.append(record["outcome_id"])
    return ids


def _validate_outcome(record: Dict) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise OutcomeError(f"missing required fields: {missing}")
    if record["schema"] != SCHEMA:
        raise OutcomeError(f"expected schema {SCHEMA!r}, got {record['schema']!r}")
    if record["y"] not in (0, 1):
        raise OutcomeError(f"y outside {{0, 1}}: {record['y']!r}")
    if not record["evidence_refs"]:
        raise OutcomeError("empty evidence_refs: an outcome without evidence is not admissible")
    forecast_hash = record.get("forecast_hash")
    if not isinstance(forecast_hash, str) or len(forecast_hash) != 64 or any(
            ch not in "0123456789abcdef" for ch in forecast_hash):
        raise OutcomeError("invalid forecast_hash (sha256 hex expected)")
    horizon = record.get("horizon")
    if not isinstance(horizon, dict) or not horizon.get("t_resolution_window_utc"):
        raise OutcomeError("horizon.t_resolution_window_utc missing: undated resolution")
    if record["resolver"].get("mode") != RESOLVER_MODE_DETERMINISTIC:
        raise OutcomeError(
            "non-deterministic resolution mode: 'operator' outcomes are published separately (B7 §a.2)"
        )


def check_link(forecast: Dict, outcome: Dict) -> None:
    """Forecast ↔ outcome binding by digest (B7 §a.5.1) — rejected if broken."""
    fresh = forecasts_mod.record_hash(forecast)
    if forecast.get("sha256") != fresh:
        raise OutcomeError(f"forecast {forecast.get('forecast_id')}: mismatched digest (disk)")
    if outcome["forecast_id"] != forecast["forecast_id"]:
        raise OutcomeError("different forecast identifiers")
    if outcome["forecast_hash"] != forecast["sha256"]:
        raise OutcomeError(
            f"mismatched forecast_hash: {outcome['forecast_hash']} ≠ {forecast['sha256']} — outcome rejected"
        )


def append_outcome(
    path: str,
    outcome: Dict,
    frozen_dir: Optional[str] = None,
    require_frozen: bool = True,
) -> Dict:
    """Write an outcome at the end of the file (``prev_hash`` chaining).

    As for the forecasts: append-only, explicit refusals; the freeze package is
    verified when ``require_frozen`` (default — an evaluation outcome recorded
    after a modified freeze would be an invalid result).
    """
    if require_frozen:
        windows_mod.verify_frozen_package(frozen_dir or forecasts_mod.default_frozen_dir())
    _validate_outcome(outcome)
    horizon = outcome.get("horizon") if isinstance(outcome.get("horizon"), dict) else {}
    resolution_window = horizon.get("t_resolution_window_utc")
    written_at = outcome.get("written_at_utc")
    try:
        resolution_moment = windows_mod.parse_utc(resolution_window) if resolution_window else None
        written_moment = windows_mod.parse_utc(written_at) if written_at else None
    except (TypeError, ValueError) as exc:
        raise OutcomeError("unreadable horizon/written_at: %s" % exc) from exc
    if resolution_moment is not None and written_moment is not None:
        if written_moment < resolution_moment:
            raise ResolutionTooEarly(
                "outcome written before resolve_not_before: written_at=%s, horizon=%s"
                % (written_at, resolution_window))
    existing = load_outcomes(path)
    verify_outcome_chain(existing, path=path)
    if any(prior["outcome_id"] == outcome["outcome_id"] for prior in existing):
        raise OutcomeError(f"outcome already written: {outcome['outcome_id']} (append-only; use supersedes)")
    if outcome.get("supersedes"):
        known = {prior["outcome_id"] for prior in existing}
        if outcome["supersedes"] not in known:
            raise OutcomeError(f"supersedes references an unknown outcome: {outcome['supersedes']}")
    final = dict(outcome)
    final["prev_hash"] = outcome_hash(existing[-1]) if existing else forecasts_mod.GENESIS_HASH
    final["signature"] = outcome_hash(final)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(final, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return final


def build_superseding_outcome(
    previous: Dict,
    forecast: Dict,
    series: Sequence[Tuple[str, float]],
    now_utc: Optional[str] = None,
    code_hash: Optional[str] = None,
) -> Dict:
    """Correction: new outcome referencing ``supersedes`` (B7 §a.5.3)."""
    corrected = resolve_forecast(forecast, series, now_utc=now_utc, code_hash=code_hash, supersedes=previous["outcome_id"])
    corrected["outcome_id"] = f"{previous['outcome_id']}.correction"
    return corrected
