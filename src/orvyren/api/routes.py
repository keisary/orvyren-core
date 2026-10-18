"""REST routes for the ORVYREN frontend — imports FastAPI eagerly.

Only :mod:`orvyren.api.main` imports this module, and only when the app is
actually built (lazy boundary documented in :mod:`orvyren.api`).
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from orvyren.api import artifacts
from orvyren.api.config import Settings
from orvyren.api.graph_service import GraphService

API_VERSION = "orvyren/api/v1"

#: Volatile measurement fields excluded from the ETag hash: they change on
#: every call while the payload itself is identical, which would defeat any
#: conditional request (research 2026-10-18, axe 3 R14).
_VOLATILE_KEYS = ("latency_ms",)


def _condense(payload: Any) -> Any:
    """Copy of ``payload`` without the volatile measurement fields."""
    if isinstance(payload, dict):
        return {key: _condense(value) for key, value in payload.items()
                if key not in _VOLATILE_KEYS}
    if isinstance(payload, list):
        return [_condense(item) for item in payload]
    return payload


def _etag_for(payload: Any) -> str:
    """Stable strong ETag: sha256 of the canonical JSON, minus volatility.

    Keys are sorted and separators fixed, so two identical payloads hash
    identically no matter how the dicts were built.
    """
    body = json.dumps(_condense(payload), sort_keys=True, ensure_ascii=False,
                      default=str, separators=(",", ":"))
    return '"%s"' % hashlib.sha256(body.encode("utf-8")).hexdigest()


def _matches(if_none_match: str, etag: str) -> bool:
    """RFC 7232 ``If-None-Match`` check (list form and ``*`` supported)."""
    candidates = [item.strip().lstrip("W/") for item in if_none_match.split(",")]
    return etag.strip().lstrip("W/") in candidates or "*" in candidates


def _cached(request: Request, response: Response, payload: Any) -> Any:
    """Attach ETag/Cache-Control and answer 304 when the client is current.

    ``Cache-Control: no-cache`` keeps revalidation on every use: the client
    re-asks, but an unchanged payload costs one 304 without a body (the graph
    payload is megabytes; the 304 path is the whole point).
    """
    etag = _etag_for(payload)
    if _matches(request.headers.get("if-none-match", ""), etag):
        empty = Response(status_code=304)
        empty.headers["ETag"] = etag
        empty.headers["Cache-Control"] = "no-cache"
        return empty
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-cache"
    return payload


def build_router(settings: Settings, graph: GraphService) -> APIRouter:
    router = APIRouter()

    # -- meta -------------------------------------------------------------

    @router.get("/api/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "version": API_VERSION,
            "graph_db": settings.rel(graph.db_path),
            "graph_db_absent": not os.path.exists(graph.db_path),
            "frontend_dist": settings.rel(settings.frontend_dist),
            "frontend_built": os.path.isdir(settings.frontend_dist),
            "mode": "offline-demo",
        }

    # -- agent runs --------------------------------------------------------

    @router.get("/api/runs")
    def runs() -> Dict[str, Any]:
        items = artifacts.discover_runs(settings)
        for item in items:
            item.pop("abs_path", None)
        return {"runs": items, "count": len(items)}

    @router.get("/api/runs/{run_id}")
    def run_bundle(run_id: str) -> Dict[str, Any]:
        try:
            bundle = artifacts.load_run_bundle(run_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return bundle

    @router.get("/api/runs/{run_id}/journal")
    def run_journal(run_id: str,
                    agent: str = Query("orchestrator"),
                    after_seq: int = Query(0),
                    limit: int = Query(300)) -> Dict[str, Any]:
        try:
            rows = artifacts.load_journal(run_id, agent, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        window = [row for row in rows if row.get("seq", 0) >= after_seq][:limit]
        return {"run_id": run_id, "agent": agent, "total": len(rows),
                "returned": len(window), "entries": window}

    @router.get("/api/runs/{run_id}/events")
    def run_events(run_id: str, after_seq: int = Query(0),
                   limit: int = Query(300)) -> Dict[str, Any]:
        try:
            events = artifacts.build_run_events(run_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        window = [e for e in events if e.get("seq", 0) >= after_seq][:limit]
        return {"run_id": run_id, "total": len(events), "returned": len(window),
                "events": window,
                "has_more": (window[-1]["seq"] + 1 < len(events)) if window else False}

    @router.get("/api/runs/{run_id}/verify")
    def run_verify(run_id: str) -> Dict[str, Any]:
        try:
            return artifacts.verify_journal_chain(run_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    # -- graph -------------------------------------------------------------

    @router.get("/api/graph/info")
    def graph_info(request: Request, response: Response) -> Any:
        return _cached(request, response, graph.schema_info())

    @router.get("/api/graph/full")
    def graph_full(request: Request, response: Response) -> Any:
        return _cached(request, response, graph.full())

    @router.get("/api/graph/snapshot")
    def graph_snapshot(request: Request, response: Response,
                       as_of: Optional[str] = Query(None),
                       as_of_block: Optional[int] = Query(None)) -> Any:
        return _cached(request, response,
                       graph.query("snapshot", as_of=as_of,
                                   as_of_block=as_of_block))

    @router.get("/api/graph/neighbors/{node_id:path}")
    def graph_neighbors(request: Request, response: Response,
                        node_id: str, depth: int = Query(1)) -> Any:
        return _cached(request, response, graph.neighbors(node_id, depth))

    @router.get("/api/graph/node/{node_id:path}")
    def graph_node(request: Request, response: Response,
                   node_id: str) -> Any:
        return _cached(request, response, graph.node_detail(node_id))

    @router.get("/api/graph/query/{name}")
    def graph_query(name: str,
                    request: Request, response: Response,
                    holder: Optional[str] = Query(None),
                    src: Optional[str] = Query(None),
                    dst: Optional[str] = Query(None),
                    asset: Optional[str] = Query(None),
                    subject: Optional[str] = Query(None),
                    relation_id: Optional[str] = Query(None),
                    as_of: Optional[str] = Query(None),
                    as_of_block: Optional[int] = Query(None),
                    max_depth: Optional[int] = Query(None),
                    limit: Optional[int] = Query(None),
                    kinds: Optional[str] = Query(None)) -> Dict[str, Any]:
        key = name.lower()
        if key not in ("q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "snapshot"):
            raise HTTPException(status_code=404, detail="unknown query: %s" % name)
        params: Dict[str, Any] = {
            "holder": holder, "src": src, "dst": dst, "asset": asset,
            "subject": subject, "relation_id": relation_id, "as_of": as_of,
            "as_of_block": as_of_block, "max_depth": max_depth, "limit": limit,
            "kinds": [k for k in (kinds or "").split(",") if k],
        }
        return _cached(request, response, graph.query(key, **params))

    # -- markets -----------------------------------------------------------

    @router.get("/api/market/episodes")
    def market_episodes() -> Dict[str, Any]:
        items = artifacts.episodes_index(settings)
        return {"episodes": items, "count": len(items)}

    @router.get("/api/market/episodes/{episode_id}")
    def market_episode(episode_id: str) -> Dict[str, Any]:
        try:
            return artifacts.load_episode(episode_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/api/market/series")
    def market_series(episode: str = Query(...)) -> Dict[str, Any]:
        try:
            return artifacts.episode_series(episode, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/api/market/corpus")
    def market_corpus() -> Dict[str, Any]:
        return artifacts.corpus_index(settings)

    # -- decision + policy + execution --------------------------------------

    @router.get("/api/decision/cases")
    def decision_cases() -> Dict[str, Any]:
        return {"cases": artifacts.decision_cases(settings)}

    @router.get("/api/decision/{case_id}")
    def decision(case_id: str) -> Dict[str, Any]:
        try:
            return artifacts.decision_case(case_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/api/decision/{case_id}/record")
    def decision_rec(case_id: str) -> Dict[str, Any]:
        try:
            return artifacts.decision_record(case_id, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.get("/api/policy/verdicts")
    def policy_verdicts() -> Dict[str, Any]:
        return artifacts.policy_verdicts(settings)

    @router.get("/api/policy/effective")
    def policy_effective() -> Dict[str, Any]:
        return artifacts.policy_effective(settings)

    @router.get("/api/execution/intents")
    def execution_intents() -> Dict[str, Any]:
        demo = artifacts.policy_verdicts(settings)
        return {
            "cases": demo.get("cases", []),
            "guard_blocks": demo.get("guard_blocks", []),
            "execution_config": demo.get("execution_config", {}),
            "expected_verdicts": demo.get("verdict_check", {}).get("expected", {}),
        }

    @router.get("/api/execution/receipts")
    def execution_receipts() -> Dict[str, Any]:
        return artifacts.execution_receipts(settings)

    # -- audit ---------------------------------------------------------------

    @router.get("/api/audit/summary")
    def audit_summary() -> Dict[str, Any]:
        summary = artifacts.audit_summary(settings)
        summary["runs"] = [
            {"run_id": run["run_id"],
             "verify": artifacts.verify_journal_chain(run["run_id"], settings)}
            for run in artifacts.discover_runs(settings)
        ]
        return summary

    @router.get("/api/audit/stream")
    def audit_stream(name: str = Query("exec"),
                     after_seq: int = Query(0),
                     limit: int = Query(200)) -> Dict[str, Any]:
        try:
            return artifacts.audit_stream(name, after_seq, limit, settings)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return router
