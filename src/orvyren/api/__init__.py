"""ORVYREN API — FastAPI backend for the real frontend dashboard.

This package is **lazily** wired: importing :mod:`orvyren.api` or any of its
stdlib modules (:mod:`orvyren.api.config`, :mod:`orvyren.api.artifacts`,
:mod:`orvyren.api.graph_service`, :mod:`orvyren.api.live`) never imports
``fastapi``. Only :mod:`orvyren.api.routes` / :mod:`orvyren.api.main` (the app
factory) touch FastAPI, and only when the app is actually built — so the
unittest suite stays green in a clone where FastAPI is not installed.

Run the server with::

    python -m orvyren.api            # uvicorn on 127.0.0.1:8321
    python -m orvyren.api.main       # same entry point

Standard library only in this ``__init__``.
"""

from __future__ import annotations

__all__ = ["create_app", "run_server"]


def create_app(*args, **kwargs):
    """Build the FastAPI app (lazy import — requires fastapi installed)."""
    from orvyren.api.main import create_app as _create_app

    return _create_app(*args, **kwargs)


def run_server(host: str = "127.0.0.1", port: int = 8321, **kwargs) -> None:
    """Run uvicorn serving the app (lazy import — requires fastapi/uvicorn)."""
    from orvyren.api.main import run_server as _run_server

    _run_server(host=host, port=port, **kwargs)
