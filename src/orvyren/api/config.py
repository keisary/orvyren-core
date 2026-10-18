"""Settings for the ORVYREN API — stdlib only, env-overridable.

Everything is resolved against the repository root so the same code serves a
checkout at any path. The demo graph database lives **outside** the repo (it
is 50 MB) at ``D:/orvyren_10h_2026-10-17/graph_v3.sqlite``; the API accepts
any SQLite path through ``ORVYREN_GRAPH_DB`` and falls back to the in-repo
``evidence/graph.sqlite`` (small legacy schema) when the big one is absent.

Standard library only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

#: Default location of the 16 174-node demo database (outside the repo).
DEFAULT_GRAPH_DB = os.environ.get(
    "ORVYREN_DEFAULT_GRAPH_DB", "D:/orvyren_10h_2026-10-17/graph_v3.sqlite")

#: Fallback database shipped in the repository (legacy v2-shaped schema).
FALLBACK_GRAPH_DB = "evidence/graph.sqlite"


def repo_root() -> str:
    """Repository root: ``ORVYREN_API_ROOT`` or derived from this file."""
    env = os.environ.get("ORVYREN_API_ROOT")
    if env:
        return os.path.abspath(env)
    here = os.path.abspath(os.path.dirname(__file__))          # src/orvyren/api
    return os.path.abspath(os.path.join(here, "..", "..", ".."))  # repo root


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings (pure data, no I/O beyond env)."""

    root: str
    graph_db: str
    graph_db_is_fallback: bool
    frontend_dist: str
    host: str = "127.0.0.1"
    port: int = 8321
    ws_tick_seconds: float = 0.6
    ws_heartbeat_seconds: float = 25.0
    #: Per-client send budget: a slow client is dropped instead of stalling
    #: the whole fan-out (backpressure).
    ws_send_timeout_seconds: float = 5.0
    ring_size: int = 512

    @property
    def evidence_dir(self) -> str:
        return os.path.join(self.root, "evidence")

    @property
    def demo_runs_dir(self) -> str:
        """Demo sessions live with the other evidence (tracked submission proofs)."""
        return os.path.join(self.root, "evidence", "demo_runs")

    @property
    def corpus_dir(self) -> str:
        return os.path.join(self.root, "corpus")

    def rel(self, path: str) -> str:
        """Repo-relative POSIX path for display (absolute paths pass through)."""
        try:
            relp = os.path.relpath(path, self.root)
        except ValueError:  # different drive on Windows
            return path.replace("\\", "/")
        return relp.replace("\\", "/")


def resolve_graph_db(root: Optional[str] = None) -> Tuple[str, bool]:
    """Return ``(db_path, is_fallback)`` honouring ``ORVYREN_GRAPH_DB``."""
    root = root or repo_root()
    env = os.environ.get("ORVYREN_GRAPH_DB")
    if env:
        return env, False
    if os.path.exists(DEFAULT_GRAPH_DB):
        return DEFAULT_GRAPH_DB, False
    return os.path.join(root, FALLBACK_GRAPH_DB), True


def load_settings() -> Settings:
    """Resolve all settings from env + filesystem layout."""
    root = repo_root()
    db, is_fallback = resolve_graph_db(root)
    dist = os.environ.get("ORVYREN_FRONTEND_DIST") or os.path.join(
        root, "frontend", "dist")
    return Settings(
        root=root,
        graph_db=db,
        graph_db_is_fallback=is_fallback,
        frontend_dist=dist,
        host=os.environ.get("ORVYREN_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("ORVYREN_API_PORT", "8321")),
    )
