# -*- coding: utf-8 -*-
"""``graph_tools`` — real graph tools for research agents (M7, 10 h slice).

Unlike the fixture-backed v1 registry (:mod:`orvyren.agents.tools`), these
three tools query the **real** read-only graph API of Hermes-A
(:mod:`orvyren.graph.api`, schema v3) — the arguments change the result, there
is no frozen snapshot behind them. The registry stays an allow-list and
``execute_intent`` stays out of it: research agents read, they never act.

CONTRACT.md (§ Outils agent):

- ``graph_query(query, holder|asset, as_of)`` → the API response (Q1/Q4/Q6/Q7/Q8);
- ``graph_path(src, dst, kinds, max_depth)`` → Q2 dependency paths + sign;
- ``graph_snapshot(as_of)`` → hash + counts.

Rules enforced here: strict args (unknown key refused, required key checked
per query), ``ToolResult`` of ``contracts`` as the single outcome type, and a
20 s deadline per call (``deadline_s``). Every failure is data
(``status="FAILED"``/``"UNAVAILABLE"``), never an exception.

Standard library only (the API opens SQLite read-only).
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from orvyren.agents import contracts
from orvyren.agents.llm import tool_spec

__all__ = [
    "GRAPH_TOOL_NAMES",
    "GRAPH_QUERIES",
    "GraphQueryTool",
    "GraphPathTool",
    "GraphSnapshotTool",
    "graph_tool_specs",
    "build_graph_registry",
    "NO_API_CODE",
]

#: The three graph tools of the contract (in contract order).
GRAPH_TOOL_NAMES: Tuple[str, ...] = (
    "graph_query", "graph_path", "graph_snapshot",
)

#: Query codes the API answers today (H2 handoff A → B).
GRAPH_QUERIES: Tuple[str, ...] = ("Q1", "Q4", "Q6", "Q7", "Q8")

#: Honest failure of a tool whose backing query is absent from the injected API.
NO_API_CODE = "E_TOOL_NO_API"

# --- execution bounds, imposed by CODE (P1-1) -------------------------------
#: A run may ask for anything; the tool imposes these ceilings — the model's
#: good will is never the budget. A negative ``limit`` would become
#: ``LIMIT -1`` in SQLite (i.e. unlimited) and a negative ``max_depth`` an
#: unbounded walk: both are refused as visible data. ``0`` stays a legal,
#: bounded value (empty result / no traversal) — an explicit argument is
#: forwarded, never silently replaced.
MAX_LIMIT: int = 500
MAX_DEPTH: int = 8
MAX_ASOF_BLOCK: int = 2 ** 63 - 1
#: Longest accepted deadline (the frozen ``wall_seconds`` budget cap).
MAX_DEADLINE_S: float = 600.0

#: Per-query required argument (the rest is optional cadrage).
_QUERY_REQUIRED: Mapping[str, Tuple[str, ...]] = {
    "Q1": ("holder",),
    "Q4": (),
    "Q6": ("relation_id",),
    "Q7": ("asset",),
    "Q8": ("subject",),
}

#: Every argument any query accepts (closed objects: nothing else passes).
_QUERY_ARGS: Tuple[str, ...] = (
    "query", "holder", "asset", "relation_id", "subject",
    "as_of", "as_of_block", "max_depth", "limit",
)


def _bad_args(errors: Sequence[str]) -> contracts.ToolResult:
    return contracts.ToolResult(ok=False, status="FAILED",
                                error=";".join(errors))


def _int_arg_errors(args: Mapping[str, Any], keys: Sequence[str]) -> List[str]:
    """Integer args must really be integers (bool excluded) when present."""
    errors: List[str] = []
    for key in keys:
        value = args.get(key)
        if value is not None and (isinstance(value, bool)
                                  or not isinstance(value, int)):
            errors.append("E_TOOL_ARGS_TYPE:%s" % key)
    return errors


def _range_arg_errors(args: Mapping[str, Any],
                      ranges: Sequence[Tuple[str, int, int]]) -> List[str]:
    """Closed numeric ranges enforced by the code itself (P1-1).

    Out-of-range values are refused (``E_TOOL_ARGS_RANGE``), never silently
    replaced by a default — an argument that changes the result is never
    rewritten behind the caller's back.
    """
    errors: List[str] = []
    for key, low, high in ranges:
        value = args.get(key)
        if value is None or isinstance(value, bool) or not isinstance(value, int):
            continue  # type errors are reported by _int_arg_errors
        if value < low or value > high:
            errors.append("E_TOOL_ARGS_RANGE:%s[%d..%d]" % (key, low, high))
    return errors


def _deadline_error(deadline_s: Any) -> Optional[str]:
    """Validate the caller's deadline (P1-1): finite, positive, capped."""
    if isinstance(deadline_s, bool) or not isinstance(deadline_s, (int, float)):
        return "E_TOOL_ARGS_TYPE:deadline_s"
    number = float(deadline_s)
    if not math.isfinite(number) or number <= 0.0 or number > MAX_DEADLINE_S:
        return "E_TOOL_ARGS_RANGE:deadline_s(0..%g]" % MAX_DEADLINE_S
    return None

def _optional_int(args: Mapping[str, Any], key: str, default: int) -> int:
    """One optional integer arg, forwarded verbatim.

    ``0`` is a value, not a missing key: an explicit argument must never be
    silently replaced by its default (the args change the result).
    """
    value = args.get(key)
    return default if value is None else int(value)


def _observation(response: Mapping[str, Any], elapsed_s: float,
                 deadline_s: float) -> contracts.ToolResult:
    """One API response as one observation (the rows travel verbatim).

    The deadline is **enforced**, not decorative (P1-1): a result that arrived
    after its budget is dropped (``E_TOOL_DEADLINE``, fail-closed) instead of
    travelling as if timely. ``latency_ms`` is neutralised: it is volatile
    telemetry measured by the API, and a recorded tooled turn must replay
    bit-identically (it also feeds the finalisation prompt hash). The measured
    latency stays visible where it is displayed — the UI queries the API
    itself.
    """
    if elapsed_s > deadline_s:
        return contracts.ToolResult(
            ok=False, status="FAILED",
            error="E_TOOL_DEADLINE: %.3fs > %.3fs budget" % (elapsed_s, deadline_s))
    clean = dict(response)
    if "latency_ms" in clean:
        clean["latency_ms"] = None
    return contracts.ToolResult(ok=True, status="OK", observations=(clean,))


class GraphQueryTool:
    """``graph_query`` — one of Q1/Q4/Q6/Q7/Q8 from the real graph."""

    name = "graph_query"

    def __init__(self, db: Optional[str] = None, api: Any = None,
                 clock: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db
        self._clock = clock or time.monotonic

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        deadline_error = _deadline_error(deadline_s)
        if deadline_error:
            return _bad_args([deadline_error])
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(_QUERY_ARGS))]
        query = str(args.get("query", "") or "").strip()
        if query not in GRAPH_QUERIES:
            errors.append("E_TOOL_QUERY_UNKNOWN:%s" % query)
            return _bad_args(errors)
        for key in _QUERY_REQUIRED[query]:
            if not str(args.get(key, "") or "").strip():
                errors.append("E_TOOL_ARGS_REQUIRED:%s" % key)
        errors += _int_arg_errors(args, ("as_of_block", "max_depth", "limit"))
        errors += _range_arg_errors(args, (
            ("limit", 0, MAX_LIMIT), ("max_depth", 0, MAX_DEPTH),
            ("as_of_block", 0, MAX_ASOF_BLOCK)))
        if errors:
            return _bad_args(errors)
        started = self._clock()
        try:
            response = self._dispatch(query, args)
        except FileNotFoundError as exc:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE", error="E_TOOL_DB_UNAVAILABLE:%s" % exc)
        except Exception as exc:  # a query failure is data, never a crash
            return contracts.ToolResult(
                ok=False, status="FAILED", error="E_TOOL_QUERY_FAILED:%s" % type(exc).__name__)
        return _observation(response, self._clock() - started, float(deadline_s))

    def _dispatch(self, query: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
        as_of = args.get("as_of") or None
        block = args.get("as_of_block")
        block = int(block) if block is not None else None
        if query == "Q1":
            return self.api.exposure(
                self.db, str(args["holder"]), as_of=as_of, as_of_block=block,
                max_depth=_optional_int(args, "max_depth", 3))
        if query == "Q4":
            return self.api.pit(
                self.db, as_of=as_of, as_of_block=block,
                limit=_optional_int(args, "limit", 100))
        if query == "Q6":
            return self.api.provenance(self.db, str(args["relation_id"]))
        if query == "Q7":
            return self.api.concentration(
                self.db, str(args["asset"]), as_of=as_of, as_of_block=block)
        return self.api.permissions(
            self.db, str(args["subject"]), as_of=as_of, as_of_block=block)


class GraphPathTool:
    """``graph_path`` — bounded dependency paths (Q2)."""

    name = "graph_path"

    def __init__(self, db: Optional[str] = None, api: Any = None,
                 clock: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db
        self._q2 = getattr(api, "dependency_paths", None)
        self._clock = clock or time.monotonic

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        deadline_error = _deadline_error(deadline_s)
        if deadline_error:
            return _bad_args([deadline_error])
        allowed = ("src", "dst", "kinds", "max_depth")
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(allowed))]
        for key in ("src", "dst"):
            if not str(args.get(key, "") or "").strip():
                errors.append("E_TOOL_ARGS_REQUIRED:%s" % key)
        kinds = args.get("kinds")
        if kinds is not None and not isinstance(kinds, (list, tuple)):
            # A bare string would be iterated character by character.
            errors.append("E_TOOL_ARGS_TYPE:kinds")
        errors += _int_arg_errors(args, ("max_depth",))
        errors += _range_arg_errors(args, (("max_depth", 0, MAX_DEPTH),))
        if errors:
            return _bad_args(errors)
        if self._q2 is None:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE",
                error="%s:Q2 (injected API lacks dependency_paths)" % NO_API_CODE)
        started = self._clock()
        try:
            response = self._q2(
                self.db, str(args["src"]), str(args["dst"]),
                kinds=tuple(args.get("kinds") or ()),
                max_depth=_optional_int(args, "max_depth", 4))
        except FileNotFoundError as exc:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE",
                error="E_TOOL_DB_UNAVAILABLE:%s" % exc)
        except Exception as exc:
            return contracts.ToolResult(
                ok=False, status="FAILED",
                error="E_TOOL_QUERY_FAILED:%s" % type(exc).__name__)
        return _observation(response, self._clock() - started, float(deadline_s))


class GraphSnapshotTool:
    """``graph_snapshot`` — hash + counts of the graph slice (no frozen copy)."""

    name = "graph_snapshot"

    def __init__(self, db: Optional[str] = None, api: Any = None,
                 clock: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db
        self._clock = clock or time.monotonic

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        deadline_error = _deadline_error(deadline_s)
        if deadline_error:
            return _bad_args([deadline_error])
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(("as_of", "as_of_block")))]
        errors += _int_arg_errors(args, ("as_of_block",))
        errors += _range_arg_errors(args, (("as_of_block", 0, MAX_ASOF_BLOCK),))
        if errors:
            return _bad_args(errors)
        block = args.get("as_of_block")
        started = self._clock()
        try:
            response = self.api.snapshot(
                self.db, as_of=args.get("as_of") or None,
                as_of_block=int(block) if block is not None else None)
        except FileNotFoundError as exc:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE",
                error="E_TOOL_DB_UNAVAILABLE:%s" % exc)
        except Exception as exc:
            return contracts.ToolResult(
                ok=False, status="FAILED",
                error="E_TOOL_QUERY_FAILED:%s" % type(exc).__name__)
        return _observation(response, self._clock() - started, float(deadline_s))


# ---------------------------------------------------------------------------
# Specs and registry.
# ---------------------------------------------------------------------------
def graph_tool_specs() -> Tuple[Dict[str, Any], ...]:
    """The three tool specs, strict JSON Schema (closed objects)."""
    return (
        tool_spec(
            "graph_query",
            "Query the real graph (read-only). query=Q1 exposure "
            "(holder required), Q4 PIT state, Q6 provenance (relation_id required), "
            "Q7 concentration (asset required), Q8 permissions (subject required). "
            "Optional framing: as_of, as_of_block, max_depth, limit.",
            {"query": {"type": "string", "enum": list(GRAPH_QUERIES)},
             "holder": {"type": "string"}, "asset": {"type": "string"},
             "relation_id": {"type": "string"}, "subject": {"type": "string"},
             "as_of": {"type": "string"}, "as_of_block": {"type": "integer"},
             "max_depth": {"type": "integer"}, "limit": {"type": "integer"}},
            ["query"]),
        tool_spec(
            "graph_path",
            "Bounded src→dst dependency paths (Q2), with sign.",
            {"src": {"type": "string"}, "dst": {"type": "string"},
             "kinds": {"type": "array", "items": {"type": "string"}},
             "max_depth": {"type": "integer"}},
            ["src", "dst"]),
        tool_spec(
            "graph_snapshot",
            "Deterministic hash + counts of the graph (relations, nodes, "
            "events, relation_provenance).",
            {"as_of": {"type": "string"}, "as_of_block": {"type": "integer"}},
            []),
    )


def build_graph_registry(db: Optional[str] = None, api: Any = None
                         ) -> Any:
    """Allow-list registry with the three real graph tools.

    ``execute_intent`` is absent by construction (and refused by
    :class:`orvyren.agents.tools.ToolRegistry` if anyone tries).
    """
    from orvyren.agents.tools import ToolRegistry
    registry = ToolRegistry()
    registry.register("graph_query", GraphQueryTool(db=db, api=api))
    registry.register("graph_path", GraphPathTool(db=db, api=api))
    registry.register("graph_snapshot", GraphSnapshotTool(db=db, api=api))
    return registry
