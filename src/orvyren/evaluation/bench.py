#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — mini-benchmark ``A0`` vs ``A2`` measurement and analysis (P0-5).

This module holds the measurable logic of the honest mini-benchmark mandated by
the consolidated audit (P0-5 / H48–H56): compare the deterministic engine alone
against the full agent system on the **same episodes and the same budgets**, and
report the comparison without ever claiming superiority at small N.

Label note (read before mixing vocabularies): in *this* module — as in P0-5 —
``A0`` is the **deterministic decision engine alone** (``run_decision.py``, no
agent search) and ``A2`` is the **full system** (``run_agents.py``: agents +
critic + fragility gate). That collides with the frozen evaluation harness
(``orvyren.evaluation.harness``) where ``A0`` is the NO-ACTION comparator
(ADR-0001, B7 §e.1). The two vocabularies are separate and never mixed here.

Honesty rules enforced mechanically, not by prose:

* every report carries the mandatory banner :data:`BANNER` — the renderer
  refuses to produce output without it;
* a superiority claim is **refused** below the G1 threshold N ≥ 100
  (:func:`require_superiority_threshold` raises); the report states the
  refusal instead of a ranking;
* a case where the agents add nothing, or degrade, is scored and rendered
  exactly like a success — :data:`SUPERIORITY_CLAIM_TERMS` are scanned for in
  the rendered markdown as a last-resort guard;
* every ground-truth figure in ``fixtures/benchmark/cases.json`` is checked
  against its declared source file/path (:func:`verify_ground_truth`) — a
  figure that cannot be resolved fails loudly instead of being published;
* synthetic (placebo) cases are labelled ``synthetic: true`` and are never
  presented as observations of the world.

The frozen evaluation modules (``loss`` / ``calibration`` / ``forecasts`` /
``outcomes``) are untouched by this module: it measures run outcomes, not the
G1 loss function.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import re
import uuid
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # run identifiers follow the run chain when it is importable (P0-5 spec)
    from orvyren.chain import new_run_id as _chain_new_run_id
except Exception:  # pragma: no cover - defensive fallback, never guessed
    _chain_new_run_id = None

__all__ = [
    "BANNER",
    "CASES_SCHEMA_VERSION",
    "SCHEMA_VERSION",
    "SUPERIORITY_N_MIN",
    "SUPERIORITY_CLAIM_TERMS",
    "MODE_A0",
    "MODE_A2",
    "MODES",
    "VERDICTS",
    "ABSTENTION",
    "ALLOW",
    "DENY",
    "REQUIRE_APPROVAL",
    "NO_ACTION",
    "UNKNOWN",
    "BenchError",
    "CasesError",
    "ReportError",
    "SuperiorityClaimRefused",
    "new_run_id",
    "resolve_json_path",
    "load_cases",
    "validate_cases",
    "verify_ground_truth",
    "materialize_synthetic_corpus",
    "normalize_a0",
    "normalize_a2",
    "count_provenance_rejections",
    "measure_a0",
    "measure_a2",
    "score_verdict",
    "aggregate",
    "delta_tag",
    "superiority_block",
    "require_superiority_threshold",
    "contains_superiority_claim",
    "build_report",
    "render_report_md",
    "write_reports",
    "run_benchmark",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Mandatory honesty banner. Its exact wording is contractual (P0-5).
BANNER = "small-N diagnostic run — no superiority claim (G1 threshold N>=100 not reached)"

#: Report schema version (``report.json``).
SCHEMA_VERSION = "orvyren/benchmark-report/v1"

#: Accepted schema version of ``fixtures/benchmark/cases.json``.
CASES_SCHEMA_VERSION = "orvyren/benchmark-cases/v1"

#: G1 superiority threshold: claims are refused below this N.
SUPERIORITY_N_MIN = 100

#: Last-resort guard: terms that would read as a superiority claim. The banner
#: itself contains "superiority claim" as a *refusal*, which is why the terms
#: are claim-shaped ("outperforms", "better than", ...) and not bare nouns.
SUPERIORITY_CLAIM_TERMS = (
    "outperform",
    "out-perform",
    "better than",
    "strictly better",
    "beats the",
    "dominates the",
    "meilleur que",
    "meilleurs que",
    "plus performant",
    "surpasse",
    "démontre la supériorité",
    "demonstrates superiority",
    "proves superiority",
    "prouve la supériorité",
)

MODE_A0 = "A0"
MODE_A2 = "A2"
MODES = (MODE_A0, MODE_A2)

ALLOW = "ALLOW"
DENY = "DENY"
REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
NO_ACTION = "NO_ACTION"
ABSTENTION = "abstention"
UNKNOWN = "unknown"

#: Normalised decision-verdict space of the benchmark.
VERDICTS = (ALLOW, DENY, REQUIRE_APPROVAL, NO_ACTION, ABSTENTION, UNKNOWN)

#: Declared semantics of each verdict per mode — rendered in every report so
#: the table is never read as a policy authorization it does not encode.
VERDICT_SEMANTICS = {
    MODE_A0: ("decision verdict of run_decision.py crossed with the "
              "authorization axis when evaluated (ACTION_RECOMMENDED -> ALLOW "
              "unless the axis says DENY/REQUIRE_APPROVAL; NO_ACTION -> "
              "NO_ACTION; INCONCLUSIVE -> abstention)"),
    MODE_A2: ("fragility gate of run_agents.py (run_outcome.json): "
              "inconclusive -> abstention; FRAGILE/INCOHERENTE escalation -> "
              "REQUIRE_APPROVAL; otherwise the agent layer did not brake -> "
              "ALLOW. ALLOW here is NOT a policy authorization and NOT an "
              "executed action."),
}

QUALITY_MATCH = "match"
QUALITY_MISS = "miss"
QUALITY_OTHER = "other"
QUALITY_NOT_SCORED = "not_scored"

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_NOT_EXECUTED = "not_executed"


class BenchError(RuntimeError):
    """Base error of the benchmark layer."""


class CasesError(BenchError):
    """Invalid or unverifiable benchmark case fixture."""


class ReportError(BenchError):
    """Invalid report (missing banner, missing N) — never rendered silently."""


class SuperiorityClaimRefused(BenchError):
    """A superiority claim was requested below the G1 threshold (N >= 100)."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def new_run_id(prefix: str = "bench") -> str:
    """One run identifier per execution.

    Uses :func:`orvyren.chain.new_run_id` when the chain package is importable
    (sortable UTC stamp + cryptographic hex), otherwise a ``uuid4`` hex — never
    a guess, never a recycled value.
    """
    if _chain_new_run_id is not None:
        return _chain_new_run_id(prefix)
    return "%s-%s" % (prefix, uuid.uuid4().hex)


def load_json(path: str) -> Any:
    """Read one JSON file (UTF-8) and return the parsed payload."""
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")


def resolve_json_path(data: Any, path: str) -> Any:
    """Resolve a dotted JSON path against ``data``.

    Supported segments (chosen so every fixture reference is machine-checkable):

    * ``key``                      — mapping key;
    * ``key[0]``                   — list index;
    * ``key[field=value]``         — first list item whose ``field`` equals
      ``value`` (string comparison on the JSON value);
    * ``key["weird key"]``         — mapping key containing dots/pipes
      (single- or double-quoted).

    Raises :class:`CasesError` when the path cannot be resolved — a ground-truth
    figure that cannot be found is an error, never a silent ``None``.
    """
    if not isinstance(path, str) or not path.strip():
        raise CasesError("empty JSON path")
    tokens: List[Any] = []
    buffer = ""
    index = 0
    length = len(path)
    while index < length:
        char = path[index]
        if char == ".":
            if buffer:
                tokens.append(("key", buffer))
            buffer = ""
            index += 1
        elif char == "[":
            if buffer:
                tokens.append(("key", buffer))
            buffer = ""
            closing = path.find("]", index)
            if closing < 0:
                raise CasesError("unclosed '[' in JSON path: %r" % path)
            inner = path[index + 1:closing]
            index = closing + 1
            if not inner:
                raise CasesError("empty [] segment in JSON path: %r" % path)
            if inner[0] in "\"'" and inner[-1] == inner[0] and len(inner) >= 2:
                tokens.append(("key", inner[1:-1]))
            elif "=" in inner:
                field, _, value = inner.partition("=")
                tokens.append(("match", field, value))
            else:
                tokens.append(("index", int(inner)))
        else:
            buffer += char
            index += 1
    if buffer:
        tokens.append(("key", buffer))

    node = data
    for token in tokens:
        kind = token[0]
        if kind == "key":
            if not isinstance(node, Mapping) or token[1] not in node:
                raise CasesError("JSON path segment %r not found in %r" % (token[1], path))
            node = node[token[1]]
        elif kind == "index":
            if not isinstance(node, list) or not -len(node) <= token[1] < len(node):
                raise CasesError("list index %r out of range in %r" % (token[1], path))
            node = node[token[1]]
        else:
            field, value = token[1], token[2]
            if not isinstance(node, list):
                raise CasesError("match segment on a non-list in %r" % path)
            found = None
            for item in node:
                if isinstance(item, Mapping) and str(item.get(field, "")) == value:
                    found = item
                    break
            if found is None:
                raise CasesError("no list item with %s=%s in %r" % (field, value, path))
            node = found
    return node


# ---------------------------------------------------------------------------
# Case fixture
# ---------------------------------------------------------------------------

def load_cases(path: str) -> Dict[str, Any]:
    """Load ``fixtures/benchmark/cases.json`` and validate its shape."""
    payload = load_json(path)
    validate_cases(payload)
    return payload


def validate_cases(payload: Any) -> None:
    """Structural validation of the case fixture (raises :class:`CasesError`)."""
    if not isinstance(payload, Mapping):
        raise CasesError("cases fixture must be an object")
    if payload.get("schema_version") != CASES_SCHEMA_VERSION:
        raise CasesError("cases fixture schema_version must be %r" % CASES_SCHEMA_VERSION)
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CasesError("cases fixture must carry a non-empty 'cases' list")
    seen = set()
    for case in cases:
        if not isinstance(case, Mapping):
            raise CasesError("each case must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise CasesError("each case needs a non-empty 'case_id'")
        if case_id in seen:
            raise CasesError("duplicate case_id %r" % case_id)
        seen.add(case_id)
        if not isinstance(case.get("synthetic"), bool):
            raise CasesError("case %r needs an explicit boolean 'synthetic' flag "
                             "(never inferred)" % case_id)
        expectation = case.get("expectation")
        if not isinstance(expectation, Mapping):
            raise CasesError("case %r needs an 'expectation' object" % case_id)
        for key in ("acceptable_verdicts", "miss_verdicts"):
            values = expectation.get(key)
            if not isinstance(values, list) or not values:
                raise CasesError("case %r: expectation.%s must be a non-empty list" % (case_id, key))
            for value in values:
                if value not in VERDICTS:
                    raise CasesError("case %r: %r is not a verdict of %s" % (case_id, value, VERDICTS))
        overlap = set(expectation["acceptable_verdicts"]) & set(expectation["miss_verdicts"])
        if overlap:
            raise CasesError("case %r: verdicts both acceptable and wrong: %s" % (case_id, sorted(overlap)))
        ground_truth = case.get("ground_truth")
        if not isinstance(ground_truth, list) or not ground_truth:
            raise CasesError("case %r needs a non-empty 'ground_truth' list" % case_id)
        for row in ground_truth:
            if not isinstance(row, Mapping):
                raise CasesError("case %r: ground_truth rows must be objects" % case_id)
            for key in ("claim", "value", "source_file", "source_json_path"):
                if key not in row:
                    raise CasesError("case %r: ground_truth row missing %r" % (case_id, key))
        if case.get("synthetic"):
            for row in ground_truth:
                if not row.get("synthetic"):
                    raise CasesError(
                        "case %r: synthetic case rows must be tagged 'synthetic: true' "
                        "(a fabricated figure is never presented as real)" % case_id)
            if "synthetic_corpus" not in case:
                raise CasesError("synthetic case %r needs a 'synthetic_corpus' spec" % case_id)


def verify_ground_truth(payload: Mapping[str, Any], repo_root: str) -> List[Dict[str, Any]]:
    """Check every ground-truth figure against its declared source.

    Returns the list of mismatches (empty = every figure resolves to the exact
    value recorded in its source file). A missing source file is a mismatch —
    the benchmark never publishes a figure it cannot trace.
    """
    mismatches: List[Dict[str, Any]] = []
    for case in payload.get("cases", []):
        for row in case.get("ground_truth", []):
            entry = {"case_id": case.get("case_id"), "claim": row.get("claim"),
                     "source_file": row.get("source_file"), "source_json_path": row.get("source_json_path")}
            source_abs = os.path.join(repo_root, str(row.get("source_file", "")).replace("/", os.sep))
            if not os.path.exists(source_abs):
                mismatches.append(dict(entry, expected=row.get("value"), found=None,
                                       error="source file missing"))
                continue
            try:
                data = load_json(source_abs)
                found = resolve_json_path(data, str(row.get("source_json_path", "")))
            except (CasesError, ValueError, OSError) as exc:
                mismatches.append(dict(entry, expected=row.get("value"), found=None,
                                       error=str(exc)))
                continue
            if found != row.get("value"):
                mismatches.append(dict(entry, expected=row.get("value"), found=found,
                                       error="value mismatch"))
    return mismatches


# ---------------------------------------------------------------------------
# Synthetic (placebo) corpus materialisation
# ---------------------------------------------------------------------------

def materialize_synthetic_corpus(case: Mapping[str, Any], out_csv: str) -> Dict[str, Any]:
    """Write the fabricated calm series of a ``synthetic: true`` case to CSV.

    The series is generated from the case's ``synthetic_corpus`` spec with a
    deterministic wiggle (no randomness, no clock) so two materialisations are
    byte-identical. The output is never real market data: the case fixture
    declares it fabricated and this function stamps ``synthetic=true`` in every
    row's ``extra`` column.
    """
    spec = case.get("synthetic_corpus")
    if not isinstance(spec, Mapping):
        raise CasesError("case %r has no 'synthetic_corpus' spec" % case.get("case_id"))

    def _bound(key: str) -> dt.datetime:
        value = spec.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise CasesError("synthetic_corpus.%s must be [start, end]" % key)
        try:
            start = dt.datetime.fromisoformat(str(value[0]))
            end = dt.datetime.fromisoformat(str(value[1]))
        except ValueError as exc:
            raise CasesError("synthetic_corpus.%s: %s" % (key, exc))
        if start.tzinfo is None or end.tzinfo is None:
            raise CasesError("synthetic_corpus.%s bounds must be timezone-aware" % key)
        return start, end

    step_minutes = int(spec.get("step_minutes", 60))
    if step_minutes <= 0:
        raise CasesError("synthetic_corpus.step_minutes must be > 0")
    price_venues = list(spec.get("price_venues") or [])
    supply_venues = list(spec.get("supply_venues") or [])
    if not price_venues or not supply_venues:
        raise CasesError("synthetic_corpus needs price_venues and supply_venues")
    price_metric = str(spec.get("price_metric", "price_usd"))
    price_base = float(spec.get("price_base", 1.0))
    price_wiggle = float(spec.get("price_wiggle", 0.0))
    supply_metric = str(spec.get("supply_metric", "circulating_usd"))
    supply_value = float(spec.get("supply_value", 0.0))
    supply_step_hours = float(spec.get("supply_step_hours", 24))
    extra = "synthetic=true;fabricated-for-benchmark"
    retrieved_at = str(spec.get("retrieved_at", "2026-10-18T00:00:00+00:00"))

    rows: List[List[Any]] = []
    step = dt.timedelta(minutes=step_minutes)
    for window_key in ("main_window", "control_window"):
        window_start, window_end = _bound(window_key)
        index = 0
        moment = window_start
        while moment < window_end:
            wiggle = price_wiggle * ((index % 5) - 2) / 2.0
            for venue in price_venues:
                rows.append([moment.isoformat(), venue, price_metric,
                             "%.6f" % (price_base + wiggle), extra, retrieved_at])
            index += 1
            moment = moment + step
        supply_step = dt.timedelta(hours=supply_step_hours)
        if supply_step_hours > 0:
            supply_moment = window_start
            while supply_moment <= window_end:
                for venue in supply_venues:
                    rows.append([supply_moment.isoformat(), venue, supply_metric,
                                 "%d" % int(supply_value), extra, retrieved_at])
                supply_moment = supply_moment + supply_step

    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    out_dir = os.path.dirname(os.path.abspath(out_csv))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="\n") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp_utc", "venue", "metric", "value", "extra", "retrieved_at"])
        writer.writerows(rows)
    with open(out_csv, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    return {"path": out_csv, "rows": len(rows), "sha256": digest,
            "synthetic": True,
            "note": "fabricated calm series — not real market data"}


# ---------------------------------------------------------------------------
# Verdict normalisation (one mapping per mode, declared in the report)
# ---------------------------------------------------------------------------

def normalize_a0(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalise a ``run_decision.py`` decision record to the verdict space.

    * ``INCONCLUSIVE``           -> ``abstention``;
    * ``NO_ACTION``              -> ``NO_ACTION``;
    * ``ACTION_RECOMMENDED``     -> ``DENY`` / ``REQUIRE_APPROVAL`` when the
      evaluated authorization axis says so, otherwise ``ALLOW``;
    * anything else (or a missing record) -> ``unknown`` (never guessed).
    """
    decision = (record or {}).get("decision") or {}
    axes = (record or {}).get("axes") or {}
    raw = str(decision.get("verdict") or "")
    authorization = axes.get("authorization_verdict")
    if raw == "INCONCLUSIVE":
        verdict = ABSTENTION
    elif raw == "NO_ACTION":
        verdict = NO_ACTION
    elif raw == "ACTION_RECOMMENDED":
        verdict = authorization if authorization in (DENY, REQUIRE_APPROVAL) else ALLOW
    else:
        verdict = UNKNOWN
    return {"verdict": verdict, "raw_verdict": raw or None,
            "authorization_verdict": authorization,
            "abstained": verdict == ABSTENTION,
            "mode": MODE_A0, "semantics": VERDICT_SEMANTICS[MODE_A0]}


def normalize_a2(run_outcome: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalise a ``run_agents.py`` ``run_outcome.json`` to the verdict space.

    Priority order (the fragility rule never cancels, it brakes — B1 §5.3):

    * ``inconclusive`` (INCOHERENTE / BLOQUANT / quarantined / fail-closed)
      -> ``abstention``;
    * ``escalation == REQUIRE_APPROVAL`` (FRAGILE) -> ``REQUIRE_APPROVAL``;
    * a conclusive run the critic did not brake -> ``ALLOW`` in the *agent-gate*
      sense documented in :data:`VERDICT_SEMANTICS` — not a policy authorization;
    * an empty/unreadable outcome -> ``unknown`` (never guessed).
    """
    outcome = (run_outcome or {}).get("outcome") or {}
    escalation = (run_outcome or {}).get("escalation")
    critique = (run_outcome or {}).get("critique") or {}
    inconclusive = bool(outcome.get("inconclusive"))
    if not outcome and not escalation:
        verdict = UNKNOWN
    elif inconclusive:
        verdict = ABSTENTION
    elif escalation == "REQUIRE_APPROVAL":
        verdict = REQUIRE_APPROVAL
    else:
        verdict = ALLOW
    return {"verdict": verdict,
            "raw_verdict": {
                "state": outcome.get("state"),
                "stop_condition": outcome.get("stop_condition"),
                "inconclusive": inconclusive,
                "escalation": escalation,
                "critique_verdict": critique.get("verdict_lecture"),
            },
            "abstained": verdict == ABSTENTION,
            "braked": escalation == "REQUIRE_APPROVAL",
            "mode": MODE_A2, "semantics": VERDICT_SEMANTICS[MODE_A2]}


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

def count_provenance_rejections(journal_entries: Iterable[Mapping[str, Any]]) -> int:
    """Claims rejected by the provenance validation, from journal lines.

    The journal keeps every refused claim visible (``validation.provenance_ok``
    is ``False`` and the motif names the refusal) — counting those lines is the
    only claim-rejection figure this benchmark reports; it is never estimated.
    """
    rejected = 0
    for entry in journal_entries or ():
        validation = entry.get("validation") if isinstance(entry, Mapping) else None
        if isinstance(validation, Mapping) and validation.get("provenance_ok") is False:
            rejected += 1
    return rejected


def _base_measurement(mode: str, case_id: str, run_index: int, status: str,
                      wall_seconds: Optional[float]) -> Dict[str, Any]:
    return {
        "run_id": new_run_id("bench"),
        "mode": mode,
        "case_id": case_id,
        "run_index": run_index,
        "status": status,
        "verdict": None,
        "raw_verdict": None,
        "abstained": None,
        "quality": QUALITY_NOT_SCORED,
        "cost_usd": None,
        "latency_seconds": wall_seconds,
        "llm_calls": None,
        "tool_calls": None,
        "claims_rejected_provenance": None,
        "detail": {},
        "notes": [],
    }


def measure_a0(case_id: str, run_index: int, payload: Mapping[str, Any],
               expectation: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Build one raw A0 measurement from a runner payload.

    The deterministic path calls no LLM and no external tool: ``cost_usd``,
    ``llm_calls`` and ``tool_calls`` are **0 by construction** (recorded as
    such, never estimated). ``latency_seconds`` is the harness-measured wall
    time of the subprocess.
    """
    status = str(payload.get("status") or STATUS_ERROR)
    wall = payload.get("wall_seconds")
    measurement = _base_measurement(MODE_A0, case_id, run_index, status, wall)
    if status != STATUS_OK or not isinstance(payload.get("decision_record"), Mapping):
        measurement["notes"].append(str(payload.get("error") or payload.get("output_tail") or "no decision record"))
        measurement["detail"] = {"exit_code": payload.get("exit_code")}
        return measurement

    record = payload["decision_record"]
    norm = normalize_a0(record)
    hypotheses = record.get("hypothesis_verdicts") or {}
    decision = record.get("decision") or {}
    axes = record.get("axes") or {}
    rdof = record.get("rdof") or {}
    budget = rdof.get("budget") or {}
    consumed = budget.get("consomme") or {}
    measurement.update({
        "verdict": norm["verdict"],
        "raw_verdict": norm["raw_verdict"],
        "abstained": norm["abstained"],
        "cost_usd": 0.0,
        "llm_calls": 0.0,
        "tool_calls": 0.0,
        "claims_rejected_provenance": 0,
        "detail": {
            "semantics": norm["semantics"],
            "authorization_verdict": norm["authorization_verdict"],
            "hypothesis_verdicts": {key: (value or {}).get("verdict")
                                    for key, value in hypotheses.items() if isinstance(value, Mapping)},
            "action": decision.get("action"),
            "missing_inputs": decision.get("missing_inputs"),
            "epistemic_verdict": axes.get("epistemic_verdict"),
            "rdof_searches": consumed.get("recherches") or consumed.get("appels"),
            "rdof_seconds": consumed.get("secondes"),
            "rdof_stop": rdof.get("stop"),
            "corpus": (record.get("inputs_summary") or {}).get("corpus"),
            "a0_rdof": payload.get("a0_rdof"),
            "deterministic": True,
        },
    })
    if expectation:
        measurement["quality"] = score_verdict(measurement["verdict"], expectation)
    return measurement


def measure_a2(case_id: str, run_index: int, payload: Mapping[str, Any],
               expectation: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Build one raw A2 measurement from a runner payload.

    ``cost_usd`` / ``llm_calls`` / ``tool_calls`` are the **recorded** budget of
    the deterministic offline replay (``--replay journal`` copies the recorded
    tokens/cost/latency) — they are real recorded spend, not a live re-spend and
    not an estimate. ``latency_seconds`` is the harness-measured wall time of
    the subprocess. ``claims_rejected_provenance`` counts the journal lines the
    provenance validation refused.
    """
    status = str(payload.get("status") or STATUS_ERROR)
    wall = payload.get("wall_seconds")
    measurement = _base_measurement(MODE_A2, case_id, run_index, status, wall)
    if status != STATUS_OK or not isinstance(payload.get("run_outcome"), Mapping):
        measurement["notes"].append(str(payload.get("error") or payload.get("output_tail") or "no run outcome"))
        measurement["detail"] = {"exit_code": payload.get("exit_code")}
        return measurement

    run_outcome = payload["run_outcome"]
    norm = normalize_a2(run_outcome)
    outcome = run_outcome.get("outcome") or {}
    budgets = outcome.get("budget_used") or {}
    journals = payload.get("journal_entries") or []
    measurement.update({
        "verdict": norm["verdict"],
        "raw_verdict": norm["raw_verdict"],
        "abstained": norm["abstained"],
        "cost_usd": float(budgets.get("cost_usd") or 0.0),
        "llm_calls": float(budgets.get("llm_calls") or 0.0),
        "tool_calls": float(budgets.get("tool_calls") or 0.0),
        "claims_rejected_provenance": count_provenance_rejections(journals),
        "detail": {
            "semantics": norm["semantics"],
            "braked": norm["braked"],
            "critique_verdict": (run_outcome.get("critique") or {}).get("verdict_lecture"),
            "stop_condition": outcome.get("stop_condition"),
            "state": outcome.get("state"),
            "motif": outcome.get("motif"),
            "non_recherche": outcome.get("non_recherche"),
            "recorded_wall_seconds": budgets.get("wall_seconds"),
            "journals": run_outcome.get("journals"),
            "cost_note": "recorded offline replay (journal mode) — recorded per-call spend, not a live re-spend",
        },
    })
    if expectation:
        measurement["quality"] = score_verdict(measurement["verdict"], expectation)
    return measurement


def score_verdict(verdict: Optional[str], expectation: Mapping[str, Any]) -> str:
    """Score one normalised verdict against the declared expectation.

    ``match`` when the verdict is in ``acceptable_verdicts``; ``miss`` when it
    is in ``miss_verdicts`` (a wrong call or a false positive); ``other`` for
    anything the declaration leaves unranked — reported, never folded into a
    success.
    """
    if verdict is None:
        return QUALITY_NOT_SCORED
    if verdict in list(expectation.get("acceptable_verdicts") or []):
        return QUALITY_MATCH
    if verdict in list(expectation.get("miss_verdicts") or []):
        return QUALITY_MISS
    return QUALITY_OTHER


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _mean(values: Sequence[float]) -> Optional[float]:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def aggregate(measurements: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate raw measurements (one mode x one case, or a whole mode)."""
    rows = list(measurements or [])
    ok_rows = [row for row in rows if row.get("status") == STATUS_OK]
    verdict_counts: Dict[str, int] = {}
    for row in ok_rows:
        key = str(row.get("verdict"))
        verdict_counts[key] = verdict_counts.get(key, 0) + 1
    quality_counts = {QUALITY_MATCH: 0, QUALITY_MISS: 0, QUALITY_OTHER: 0}
    for row in rows:
        quality = row.get("quality")
        if quality in quality_counts:
            quality_counts[quality] += 1
    scored = sum(quality_counts.values())
    costs = [row.get("cost_usd") for row in ok_rows if isinstance(row.get("cost_usd"), (int, float))]
    return {
        "n_runs": len(rows),
        "n_ok": len(ok_rows),
        "n_not_executed": sum(1 for row in rows if row.get("status") == STATUS_NOT_EXECUTED),
        "n_error": sum(1 for row in rows if row.get("status") == STATUS_ERROR),
        "n_scored": scored,
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "distinct_verdicts": len(verdict_counts),
        "quality_counts": quality_counts,
        "match_rate": (quality_counts[QUALITY_MATCH] / scored) if scored else None,
        "miss_rate": (quality_counts[QUALITY_MISS] / scored) if scored else None,
        "other_rate": (quality_counts[QUALITY_OTHER] / scored) if scored else None,
        "abstentions": sum(1 for row in ok_rows if row.get("abstained")),
        "abstention_rate": (sum(1 for row in ok_rows if row.get("abstained")) / len(ok_rows)) if ok_rows else None,
        "cost_usd_total": sum(costs) if costs else (0.0 if ok_rows else None),
        "cost_usd_mean": _mean(costs),
        "latency_seconds_mean": _mean([row.get("latency_seconds") for row in rows]),
        "llm_calls_total": sum(row.get("llm_calls") or 0.0 for row in ok_rows),
        "tool_calls_total": sum(row.get("tool_calls") or 0.0 for row in ok_rows),
        "claims_rejected_provenance_total": sum(row.get("claims_rejected_provenance") or 0
                                                for row in ok_rows),
    }


def delta_tag(a0_rows: Sequence[Mapping[str, Any]],
              a2_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Qualitative A0-vs-A2 delta for one case, from measured rows only.

    Tags (mutually exclusive, first match wins):

    * ``a2_not_executed``  — the A2 leg produced no measurement;
    * ``a0_not_executed``  — the A0 leg produced no measurement;
    * ``agents_miss_a0_match`` — the agents are wrong where the engine is not;
    * ``agents_match_a0_miss`` — the agents are right where the engine is not;
    * ``agents_abstain_where_engine_acts`` — the agent layer brakes/abstains
      while the engine recommends acting;
    * ``same_call`` — both modes landed on the same normalised verdict;
    * ``different_calls`` — both ran and disagree without a declared winner.
    """
    a0_ok = [row for row in a0_rows if row.get("status") == STATUS_OK]
    a2_ok = [row for row in a2_rows if row.get("status") == STATUS_OK]
    if not a2_ok:
        return {"tag": "a2_not_executed",
                "note": "no A2 measurement on this case — nothing is inferred"}
    if not a0_ok:
        return {"tag": "a0_not_executed",
                "note": "no A0 measurement on this case — nothing is inferred"}
    a0_verdicts = sorted({row.get("verdict") for row in a0_ok})
    a2_verdicts = sorted({row.get("verdict") for row in a2_ok})
    a0_quality = sorted({row.get("quality") for row in a0_ok})
    a2_quality = sorted({row.get("quality") for row in a2_ok})
    if a2_quality == [QUALITY_MISS] and a0_quality == [QUALITY_MATCH]:
        return {"tag": "agents_miss_a0_match",
                "note": "the agent layer is wrong on this case where the engine is not — measured, kept visible"}
    if a2_quality == [QUALITY_MATCH] and a0_quality == [QUALITY_MISS]:
        return {"tag": "agents_match_a0_miss",
                "note": "the agent layer is right on this case where the engine is not — one case is not a trend"}
    if a2_verdicts == a0_verdicts:
        return {"tag": "same_call",
                "note": "both modes land on the same verdict — no decision-quality delta measured on this case"}
    a2_abstains = all(row.get("abstained") or row.get("verdict") == REQUIRE_APPROVAL for row in a2_ok)
    a0_acts = any(row.get("verdict") == ALLOW for row in a0_ok)
    if a2_abstains and a0_acts:
        return {"tag": "agents_abstain_where_engine_acts",
                "note": "the agent layer brakes/abstains while the engine recommends acting"}
    return {"tag": "different_calls",
            "note": "the two modes disagree on this case — the declaration ranks neither (N too small)"}


# ---------------------------------------------------------------------------
# Superiority gate
# ---------------------------------------------------------------------------

def require_superiority_threshold(n: int) -> int:
    """Refuse any superiority claim below the G1 threshold (N ≥ 100).

    Raises :class:`SuperiorityClaimRefused` for ``n < 100``; returns ``n`` when
    the threshold is reached (a paired test is still required before claiming
    anything — this gate only checks the sample size).
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("n must be an int (counted runs) : %r" % (n,))
    if n < 0:
        raise ValueError("negative n : %r" % (n,))
    if n < SUPERIORITY_N_MIN:
        raise SuperiorityClaimRefused(
            "N=%d < %d (G1 threshold) — superiority claims are refused; "
            "this benchmark is a small-N diagnostic run" % (n, SUPERIORITY_N_MIN))
    return n


def superiority_block(n: int) -> Dict[str, Any]:
    """The report's superiority block: threshold, N, and the refusal itself."""
    claimable = n >= SUPERIORITY_N_MIN
    return {
        "n": n,
        "threshold": SUPERIORITY_N_MIN,
        "claimable": claimable,
        "statement": (
            "threshold reached on sample size only — a paired statistical test "
            "is still required before any superiority claim"
            if claimable else
            "refused: N=%d < %d (G1 threshold) — no superiority claim is made "
            "or implied anywhere in this report" % (n, SUPERIORITY_N_MIN)),
        "banner": BANNER,
    }


def contains_superiority_claim(text: str) -> List[str]:
    """Return the claim-shaped terms found in ``text`` (empty = none).

    Last-resort guard on the rendered markdown: the banner's own wording ("no
    superiority claim …") is a refusal and is not claim-shaped, so it does not
    trigger this scan.
    """
    haystack = str(text or "").lower()
    return [term for term in SUPERIORITY_CLAIM_TERMS if term.lower() in haystack]


# ---------------------------------------------------------------------------
# Report assembly + rendering
# ---------------------------------------------------------------------------

def build_report(cases_payload: Mapping[str, Any], measurements: Sequence[Mapping[str, Any]],
                 *, run_id: Optional[str] = None,
                 budget: Optional[Mapping[str, Any]] = None,
                 extra_notes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Assemble ``report.json`` content: raw runs + per-case aggregates."""
    rows = list(measurements or [])
    n_scored = sum(1 for row in rows if row.get("quality") != QUALITY_NOT_SCORED)
    case_expectations = {case.get("case_id"): case for case in cases_payload.get("cases", [])}
    per_case: List[Dict[str, Any]] = []
    for case_id, case in case_expectations.items():
        case_rows = [row for row in rows if row.get("case_id") == case_id]
        a0_rows = [row for row in case_rows if row.get("mode") == MODE_A0]
        a2_rows = [row for row in case_rows if row.get("mode") == MODE_A2]
        per_case.append({
            "case_id": case_id,
            "synthetic": bool(case.get("synthetic")),
            "expectation": case.get("expectation"),
            "n_runs": len(case_rows),
            "aggregates": {MODE_A0: aggregate(a0_rows), MODE_A2: aggregate(a2_rows)},
            "delta": delta_tag(a0_rows, a2_rows),
        })
    report = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id or new_run_id("bench"),
        "banner": BANNER,
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "modes": list(MODES),
        "verdict_space": list(VERDICTS),
        "verdict_semantics": dict(VERDICT_SEMANTICS),
        "budget": dict(budget or {}),
        "n_scored_runs": n_scored,
        "n_runs": len(rows),
        "aggregates": {
            MODE_A0: aggregate([row for row in rows if row.get("mode") == MODE_A0]),
            MODE_A2: aggregate([row for row in rows if row.get("mode") == MODE_A2]),
        },
        "cases": per_case,
        "runs": rows,
        "superiority": superiority_block(n_scored),
        "notes": list(extra_notes or []),
        "limitations": _limitations(rows, n_scored),
    }
    return report


def _limitations(rows: Sequence[Mapping[str, Any]], n_scored: int) -> List[str]:
    """Fixed honesty notes, always rendered — no report without them."""
    not_executed = [row for row in rows if row.get("status") == STATUS_NOT_EXECUTED]
    limitations = [
        "N=%d scored run(s) — far below the G1 superiority threshold (N>=100); "
        "no ranking of A0 vs A2 is claimed or implied." % n_scored,
        "Journal-mode A2 runs are deterministic offline replays of recorded "
        "responses (pinned run_id): repeated runs demonstrate replay "
        "determinism, NOT independent samples. N counts runs and must not be "
        "read as independent evidence.",
        "A2 cost/latency figures are the recorded per-call spend of the replay "
        "(real recorded cost) plus harness-measured wall time; A0 is "
        "deterministic and spends nothing (0 by construction).",
        "The RDOF/axes enrichment of run_decision.py is scoped to case "
        "'usdc-2023-03'; other case ids run the v0 deterministic engine "
        "(--no-rdof) — a declared substitution, recorded per run.",
    ]
    for row in not_executed:
        limitations.append(
            "A2 was NOT executed for case %r (run %s): %s — the missing leg is "
            "reported as missing, never inferred." % (
                row.get("case_id"), row.get("run_index"), (row.get("notes") or ["no reason recorded"])[0]))
    return limitations


def render_report_md(report: Mapping[str, Any]) -> str:
    """Render ``report.md``. The banner is mandatory; missing banner = error.

    The comparative table always carries N, and the three honesty sections
    (when the agents help / add nothing or degrade / must abstain) are built
    from measured rows — a section with no measured evidence says so in one
    line instead of staying silent.
    """
    banner = str(report.get("banner") or "")
    if banner != BANNER:
        raise ReportError("mandatory banner missing or altered — a benchmark "
                          "report without %r is never rendered" % BANNER)
    if not isinstance(report.get("n_runs"), int):
        raise ReportError("report must carry an integer n_runs (N is displayed everywhere)")

    lines: List[str] = []
    lines.append("# ORVYREN mini-benchmark — A0 (deterministic engine) vs A2 (full agents)")
    lines.append("")
    lines.append("> **%s**" % BANNER)
    lines.append("")
    lines.append("- run_id: `%s`" % report.get("run_id"))
    lines.append("- N scored runs: **%d** (total runs: %d)" % (report["n_scored_runs"], report["n_runs"]))
    lines.append("- modes: %s — same episodes, same declared budgets" % ", ".join(report.get("modes", [])))
    budget = report.get("budget") or {}
    if budget:
        lines.append("- declared budget (identical for both modes): %s" % json.dumps(budget, sort_keys=True))
    lines.append("")
    lines.append("## Verdict mapping (read this before the table)")
    lines.append("")
    for mode in report.get("modes", []):
        lines.append("- **%s** — %s" % (mode, VERDICT_SEMANTICS.get(mode, "")))
    lines.append("")

    lines.append("## Comparative table")
    lines.append("")
    lines.append("| case | synthetic | mode | N runs | verdicts (counts) | match | miss | other | abstentions | cost USD (total) | latency s (mean) | LLM calls | tool calls | claims rejected (provenance) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for case in report.get("cases", []):
        for mode in report.get("modes", []):
            agg = (case.get("aggregates") or {}).get(mode) or {}
            verdicts = ", ".join("%s:%d" % (key, value)
                                 for key, value in (agg.get("verdict_counts") or {}).items()) or "—"
            match_rate = agg.get("match_rate")
            lines.append("| %s | %s | %s | %d | %s | %d | %d | %d | %s | %s | %s | %s | %s | %s |" % (
                case.get("case_id"), "yes" if case.get("synthetic") else "no", mode,
                agg.get("n_runs", 0), verdicts,
                (agg.get("quality_counts") or {}).get(QUALITY_MATCH, 0),
                (agg.get("quality_counts") or {}).get(QUALITY_MISS, 0),
                (agg.get("quality_counts") or {}).get(QUALITY_OTHER, 0),
                agg.get("abstentions", 0),
                _fmt(agg.get("cost_usd_total")), _fmt(agg.get("latency_seconds_mean")),
                _fmt(agg.get("llm_calls_total")), _fmt(agg.get("tool_calls_total")),
                agg.get("claims_rejected_provenance_total", 0),
            ))
    lines.append("")
    lines.append("N per mode — A0: %d scored / %d runs · A2: %d scored / %d runs." % (
        (report.get("aggregates", {}).get(MODE_A0, {}) or {}).get("n_scored", 0),
        (report.get("aggregates", {}).get(MODE_A0, {}) or {}).get("n_runs", 0),
        (report.get("aggregates", {}).get(MODE_A2, {}) or {}).get("n_scored", 0),
        (report.get("aggregates", {}).get(MODE_A2, {}) or {}).get("n_runs", 0),
    ))
    lines.append("")

    lines.append("## Per-case reading (declared expectations, measured outcomes)")
    lines.append("")
    for case in report.get("cases", []):
        expectation = case.get("expectation") or {}
        delta = case.get("delta") or {}
        lines.append("### %s%s" % (case.get("case_id"), " — SYNTHETIC PLACEBO (fabricated, not real data)"
                                   if case.get("synthetic") else ""))
        lines.append("")
        lines.append("- declared: %s" % expectation.get("declared", "—"))
        lines.append("- acceptable calls: %s · wrong calls: %s" % (
            ", ".join(expectation.get("acceptable_verdicts") or []) or "—",
            ", ".join(expectation.get("miss_verdicts") or []) or "—"))
        if expectation.get("expect_agents_note"):
            lines.append("- declared agent expectation: %s" % expectation["expect_agents_note"])
        lines.append("- measured delta: `%s` — %s" % (delta.get("tag", "—"), delta.get("note", "")))
        lines.append("")

    lines.append("## When the agents help / add nothing / must abstain")
    lines.append("")
    tags = [(case.get("case_id"), (case.get("delta") or {}).get("tag")) for case in report.get("cases", [])]

    helped = [case_id for case_id, tag in tags if tag == "agents_match_a0_miss"]
    braked = [case_id for case_id, tag in tags if tag == "agents_abstain_where_engine_acts"]
    lines.append("### When the agents help")
    lines.append("")
    if helped:
        lines.append("- measured: %s — the agent layer matched the declared expectation "
                     "where the deterministic engine missed it. One case is a lead, not a trend."
                     % ", ".join(helped))
    else:
        lines.append("- measured: **none** in this sample (N=%d). No case shows the agent "
                     "layer matching the declared expectation where the engine missed it."
                     % report["n_scored_runs"])
    if braked:
        lines.append("- measured: %s — the agent layer brakes/abstains where the engine "
                     "recommends acting. This is a difference in caution (audit trail, "
                     "escalation, what was NOT searched); it is NOT ranked as better — the "
                     "declared expectation accepts both calls." % ", ".join(braked))
    else:
        lines.append("- measured: no brake/abstention divergence between the modes in this sample.")
    lines.append("")

    nothing = [case_id for case_id, tag in tags if tag == "same_call"]
    degraded = [case_id for case_id, tag in tags if tag == "agents_miss_a0_match"]
    diverged = [case_id for case_id, tag in tags if tag == "different_calls"]
    lines.append("### When the agents add nothing — or degrade")
    lines.append("")
    if nothing:
        lines.append("- add nothing (same normalised call as the engine): %s"
                     % ", ".join(nothing))
    else:
        lines.append("- add nothing: none measured in this sample.")
    if degraded:
        lines.append("- **degrade** (wrong where the engine is right): %s — kept as visible as any success."
                     % ", ".join(degraded))
    else:
        lines.append("- degrade: none measured in this sample.")
    if diverged:
        lines.append("- disagree without a declared winner: %s (the declaration ranks neither)."
                     % ", ".join(diverged))
    lines.append("")

    abstained_cases = [case.get("case_id") for case in report.get("cases", [])
                       if (case.get("aggregates") or {}).get(MODE_A2, {}).get("abstentions", 0)
                       or (case.get("delta") or {}).get("tag") == "a2_not_executed"]
    lines.append("### When the agents must abstain")
    lines.append("")
    lines.append("- declared rule (B1 §5.3): a FRAGILE/INCOHERENTE reading never cancels — it "
                 "brakes towards REQUIRE_APPROVAL / abstention. On a no-signal (placebo) case "
                 "the agents must find nothing decisive and abstain or conclude nothing.")
    if abstained_cases:
        lines.append("- measured: abstained or not executed (declared as missing) on: %s"
                     % ", ".join(abstained_cases))
    else:
        lines.append("- measured: no abstention recorded in this sample.")
    lines.append("")

    lines.append("## Raw runs")
    lines.append("")
    lines.append("| run_id | case | mode | run | status | verdict | quality | abstained | cost USD | latency s | LLM | tools | claims rejected |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in report.get("runs", []):
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row.get("run_id"), row.get("case_id"), row.get("mode"), row.get("run_index"),
            row.get("status"), row.get("verdict") or "—", row.get("quality"),
            "—" if row.get("abstained") is None else str(row.get("abstained")),
            _fmt(row.get("cost_usd")), _fmt(row.get("latency_seconds")),
            _fmt(row.get("llm_calls")), _fmt(row.get("tool_calls")),
            row.get("claims_rejected_provenance") if row.get("claims_rejected_provenance") is not None else "—",
        ))
    lines.append("")

    lines.append("## Superiority")
    lines.append("")
    superiority = report.get("superiority") or {}
    lines.append("- N=%s · G1 threshold N>=%d · claimable: %s" % (
        superiority.get("n"), superiority.get("threshold", SUPERIORITY_N_MIN),
        "yes" if superiority.get("claimable") else "no"))
    lines.append("- %s" % superiority.get("statement", BANNER))
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    for note in report.get("limitations") or []:
        lines.append("- %s" % note)
    for note in report.get("notes") or []:
        lines.append("- %s" % note)
    lines.append("")

    text = "\n".join(lines)
    if BANNER not in text:
        raise ReportError("mandatory banner missing from rendered markdown")
    offenders = contains_superiority_claim(text)
    if offenders:
        raise ReportError("rendered markdown contains superiority-claim wording %s — "
                          "rewrite as measured observations" % offenders)
    return text


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return "%.4f" % value
    return str(value)


def write_reports(report: Mapping[str, Any], out_dir: str) -> Dict[str, str]:
    """Write ``report.json`` + ``report.md`` under ``out_dir``; return paths."""
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "report.json")
    md_path = os.path.join(out_dir, "report.md")
    _write_json(json_path, report)
    markdown = render_report_md(report)
    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)
        handle.write("\n")
    return {"report_json": json_path, "report_md": md_path}


# ---------------------------------------------------------------------------
# Driver (runners injected — subprocesses in production, doubles in tests)
# ---------------------------------------------------------------------------

Runner = Callable[[Mapping[str, Any], str, int], Mapping[str, Any]]


def run_benchmark(cases_payload: Mapping[str, Any], case_ids: Sequence[str], runs: int,
                  out_dir: str, runner_a0: Runner, runner_a2: Runner,
                  *, budget: Optional[Mapping[str, Any]] = None,
                  run_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute both modes on every selected case and build the report.

    ``runner_a0(case, run_dir, run_index)`` and ``runner_a2(case, run_dir,
    run_index)`` return the raw payload consumed by :func:`measure_a0` /
    :func:`measure_a2` (status, parsed artefacts, measured wall time). Real
    runners shell out to ``run_decision.py`` / ``run_agents.py``; tests inject
    doubles and never call an LLM.
    """
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 1:
        raise BenchError("runs must be an int >= 1 : %r" % (runs,))
    validate_cases(cases_payload)
    known = {case.get("case_id"): case for case in cases_payload.get("cases", [])}
    selected = list(case_ids) if case_ids else list(known)
    unknown = [case_id for case_id in selected if case_id not in known]
    if unknown:
        raise CasesError("unknown case id(s): %s (known: %s)" % (unknown, sorted(known)))

    measurements: List[Dict[str, Any]] = []
    for case_id in selected:
        case = known[case_id]
        expectation = case.get("expectation") or {}
        for run_index in range(1, runs + 1):
            a0_dir = os.path.join(out_dir, "raw", case_id, MODE_A0, "run_%d" % run_index)
            payload_a0 = runner_a0(case, a0_dir, run_index)
            measurements.append(measure_a0(case_id, run_index, payload_a0, expectation))
            a2_dir = os.path.join(out_dir, "raw", case_id, MODE_A2, "run_%d" % run_index)
            payload_a2 = runner_a2(case, a2_dir, run_index)
            measurements.append(measure_a2(case_id, run_index, payload_a2, expectation))

    report = build_report(cases_payload, measurements, run_id=run_id, budget=budget)
    write_reports(report, out_dir)
    return report
