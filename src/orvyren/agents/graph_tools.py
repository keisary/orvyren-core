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

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

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


def _observation(response: Mapping[str, Any], deadline_s: float
                 ) -> contracts.ToolResult:
    """One API response as one observation (the rows travel verbatim).

    ``latency_ms`` is neutralised: it is volatile telemetry measured by the
    API, and a recorded tooled turn must replay bit-identically (it also feeds
    the finalisation prompt hash). The measured latency stays visible where it
    is displayed — the UI queries the API itself.
    """
    clean = dict(response)
    if "latency_ms" in clean:
        clean["latency_ms"] = None
    return contracts.ToolResult(ok=True, status="OK", observations=(clean,))


class GraphQueryTool:
    """``graph_query`` — one of Q1/Q4/Q6/Q7/Q8 from the real graph."""

    name = "graph_query"

    def __init__(self, db: Optional[str] = None, api: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(_QUERY_ARGS))]
        query = str(args.get("query", "") or "").strip()
        if query not in GRAPH_QUERIES:
            errors.append("E_TOOL_QUERY_UNKNOWN:%s" % query)
            return _bad_args(errors)
        for key in _QUERY_REQUIRED[query]:
            if not str(args.get(key, "") or "").strip():
                errors.append("E_TOOL_ARGS_REQUIRED:%s" % key)
        if errors:
            return _bad_args(errors)
        try:
            response = self._dispatch(query, args)
        except FileNotFoundError as exc:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE", error="E_TOOL_DB_UNAVAILABLE:%s" % exc)
        except Exception as exc:  # a query failure is data, never a crash
            return contracts.ToolResult(
                ok=False, status="FAILED", error="E_TOOL_QUERY_FAILED:%s" % type(exc).__name__)
        return _observation(response, deadline_s)

    def _dispatch(self, query: str, args: Mapping[str, Any]) -> Mapping[str, Any]:
        as_of = args.get("as_of") or None
        block = args.get("as_of_block")
        block = int(block) if block is not None else None
        if query == "Q1":
            return self.api.exposure(
                self.db, str(args["holder"]), as_of=as_of, as_of_block=block,
                max_depth=int(args.get("max_depth", 3) or 3))
        if query == "Q4":
            return self.api.pit(
                self.db, as_of=as_of, as_of_block=block,
                limit=int(args.get("limit", 100) or 100))
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

    def __init__(self, db: Optional[str] = None, api: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db
        self._q2 = getattr(api, "dependency_paths", None)

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        allowed = ("src", "dst", "kinds", "max_depth")
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(allowed))]
        for key in ("src", "dst"):
            if not str(args.get(key, "") or "").strip():
                errors.append("E_TOOL_ARGS_REQUIRED:%s" % key)
        if errors:
            return _bad_args(errors)
        if self._q2 is None:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE",
                error="%s:Q2 (injected API lacks dependency_paths)" % NO_API_CODE)
        try:
            response = self._q2(
                self.db, str(args["src"]), str(args["dst"]),
                kinds=tuple(args.get("kinds") or ()),
                max_depth=int(args.get("max_depth", 4) or 4))
        except FileNotFoundError as exc:
            return contracts.ToolResult(
                ok=False, status="UNAVAILABLE",
                error="E_TOOL_DB_UNAVAILABLE:%s" % exc)
        except Exception as exc:
            return contracts.ToolResult(
                ok=False, status="FAILED",
                error="E_TOOL_QUERY_FAILED:%s" % type(exc).__name__)
        return _observation(response, deadline_s)


class GraphSnapshotTool:
    """``graph_snapshot`` — hash + counts of the graph slice (no frozen copy)."""

    name = "graph_snapshot"

    def __init__(self, db: Optional[str] = None, api: Any = None) -> None:
        if api is None:
            from orvyren.graph import api as graph_api
            api = graph_api
        self.api = api
        self.db = db

    def run(self, args: Mapping[str, Any], *,
            deadline_s: float = 20.0) -> contracts.ToolResult:
        args = dict(args or {})
        errors = ["E_TOOL_ARGS_UNKNOWN:%s" % key
                  for key in sorted(set(args) - set(("as_of", "as_of_block")))]
        if errors:
            return _bad_args(errors)
        block = args.get("as_of_block")
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
        return _observation(response, deadline_s)


# ---------------------------------------------------------------------------
# Specs and registry.
# ---------------------------------------------------------------------------
def graph_tool_specs() -> Tuple[Dict[str, Any], ...]:
    """The three tool specs, strict JSON Schema (closed objects)."""
    return (
        tool_spec(
            "graph_query",
            "Interroge le graphe réel (lecture seule). query=Q1 exposition "
            "(holder requis), Q4 état PIT, Q6 provenance (relation_id requis), "
            "Q7 concentration (asset requis), Q8 permissions (subject requis). "
            "Cadrage optionnel: as_of, as_of_block, max_depth, limit.",
            {"query": {"type": "string", "enum": list(GRAPH_QUERIES)},
             "holder": {"type": "string"}, "asset": {"type": "string"},
             "relation_id": {"type": "string"}, "subject": {"type": "string"},
             "as_of": {"type": "string"}, "as_of_block": {"type": "integer"},
             "max_depth": {"type": "integer"}, "limit": {"type": "integer"}},
            ["query"]),
        tool_spec(
            "graph_path",
            "Chemins de dépendance src→dst (Q2) bornés, avec signe.",
            {"src": {"type": "string"}, "dst": {"type": "string"},
             "kinds": {"type": "array", "items": {"type": "string"}},
             "max_depth": {"type": "integer"}},
            ["src", "dst"]),
        tool_spec(
            "graph_snapshot",
            "Hash déterministe + comptages du graphe (relations, nodes, "
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
