"""FastAPI app factory: REST + WebSocket + static SPA serving.

Registered in this order (the ``app.mount("/")`` trap is avoided entirely — no
mount at root): API routes first, then the WebSocket endpoint, then a catch-all
that serves ``frontend/dist`` files and falls back to ``index.html`` for SPA
routes. The demo is fully offline: every asset is bundled in ``dist/``.

This module is the lazy FastAPI boundary: importing it requires fastapi.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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


def run_server(host: str = "127.0.0.1", port: int = 8321, **kwargs: Any) -> None:
    """Run uvicorn on the app (Windows: SelectorEventLoop for WS stability)."""
    import asyncio
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, log_level="info", **kwargs)


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
