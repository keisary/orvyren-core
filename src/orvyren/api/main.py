"""FastAPI app factory: REST + WebSocket + static SPA serving.

Registered in this order (the ``app.mount("/")`` trap is avoided entirely — no
mount at root): API routes first, then the WebSocket endpoint, then a catch-all
that serves ``frontend/dist`` files and falls back to ``index.html`` for SPA
routes. The demo is fully offline: every asset is bundled in ``dist/``.

This module is the lazy FastAPI boundary: importing it requires fastapi.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse

from orvyren.api.config import Settings, load_settings
from orvyren.api.graph_service import GraphService
from orvyren.api.live import LiveHub
from orvyren.api.routes import build_router

API_VERSION = "orvyren/api/v1"


def create_app(settings: Optional[Settings] = None,
               graph: Optional[GraphService] = None) -> FastAPI:
    settings = settings or load_settings()
    graph = graph or GraphService(settings=settings)
    hub = LiveHub(settings)

    app = FastAPI(title="ORVYREN Live Dashboard API", version=API_VERSION,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.state.settings = settings
    app.state.graph = graph
    app.state.live_hub = hub

    # gzip the JSON bodies (the graph payload is megabytes and compresses
    # several-fold). Level 6 is the speed/size balance: level 9 (the Starlette
    # default) spends CPU on a payload the demo serves repeatedly. A client
    # that does not send ``Accept-Encoding: gzip`` gets the plain body.
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

    # API routes BEFORE any static handling (mount-at-root would shadow them).
    app.include_router(build_router(settings, graph))

    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket) -> None:
        await websocket.accept()
        await hub.register(websocket)
        hello = hub.envelope("run.status", {
            "phase": "hello",
            "run_id": hub.current_run or "",
            "since_hint": hub.seq,
            "api": API_VERSION,
        })
        await websocket.send_text(_dumps(hello))
        try:
            while True:
                raw = await websocket.receive_text()
                await hub.handle_client_message(raw)
        except WebSocketDisconnect:
            pass
        finally:
            await hub.unregister(websocket)

    dist = settings.frontend_dist

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> Any:
        """Serve the built SPA: real files first, then index.html (SPA routes)."""
        if not os.path.isdir(dist):
            return JSONResponse(
                {"error": "frontend build not found",
                 "expected": settings.rel(dist),
                 "hint": "run `npm ci && npm run build` in frontend/"},
                status_code=503)
        if full_path and not full_path.startswith("api/"):
            candidate = os.path.normpath(os.path.join(dist, full_path))
            if candidate.startswith(os.path.normpath(dist)) and os.path.isfile(candidate):
                return FileResponse(candidate)
        index = os.path.join(dist, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return JSONResponse({"error": "index.html missing in dist"},
                            status_code=503)

    return app


def _dumps(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)


def _uvicorn_kwargs(host: str = "127.0.0.1", port: int = 8321,
                   **kwargs: Any) -> Dict[str, Any]:
    """uvicorn options for the offline demo (single testable contract).

    ``ws_per_message_deflate`` (RFC 7692) is uvicorn's default today; it is
    pinned explicitly so a future default flip cannot silently drop WebSocket
    frame compression (research 2026-10-18, axe 3 R17).
    """
    options: Dict[str, Any] = {"host": host, "port": port, "log_level": "info",
                               "ws_per_message_deflate": True}
    options.update(kwargs)
    return options


def run_server(host: str = "127.0.0.1", port: int = 8321, **kwargs: Any) -> None:
    """Run uvicorn on the app (Windows: SelectorEventLoop for WS stability)."""
    import asyncio
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import uvicorn

    uvicorn.run(create_app(), **_uvicorn_kwargs(host, port, **kwargs))


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute: ``app`` is built on first access.

    There is deliberately no module-level ``app = None``: the attribute must
    stay absent so ``uvicorn orvyren.api.main:app`` triggers this factory and
    only then imports FastAPI's app object.
    """
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
