"""Graph service: SQLite → Sigma payload, plus the Q1–Q8 read contract.

Wraps :mod:`orvyren.graph.api` (the single read contract of the store) for
the query panel, and builds the full graph payload for Sigma.js:

- ``nodes``: id, label, kind/class, degree, size, x/y (deterministic
  pre-layout, refined client-side by the ForceAtlas2 web worker);
- ``edges``: source/target/kind/sign/amount;
- ``graph_version``: content digest used as HTTP ``ETag``.

The database path is configurable (``ORVYREN_GRAPH_DB``) and the service
works against both the 16 174-node demo schema (``graph_v3.sqlite``, outside
the repo) and the small legacy ``evidence/graph.sqlite`` shipped in the repo —
the legacy schema simply lacks some columns and the service degrades openly
(``SCHEMA_LEGACY`` status) instead of failing.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Sequence, Tuple

from orvyren.api.config import Settings, load_settings, resolve_graph_db
from orvyren.graph.api import apply_read_pragmas


def _connect(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError("graph database not found: %s" % path)
    absolute = os.path.abspath(path).replace("\\", "/")
    uri = "file:%s?mode=ro" % urllib.parse.quote(absolute, safe="/:")
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    apply_read_pragmas(connection)
    return connection


def _columns(con: sqlite3.Connection, table: str) -> List[str]:
    try:
        return [row[1] for row in con.execute("PRAGMA table_info(%s)" % table)]
    except sqlite3.Error:
        return []


def _has_table(con: sqlite3.Connection, table: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _sha(*parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


class GraphService:
    """Read-only view over the ORVYREN graph database."""

    def __init__(self, db_path: Optional[str] = None,
                 settings: Optional[Settings] = None) -> None:
        self.settings = settings or load_settings()
        self.db_path = db_path or resolve_graph_db(self.settings.root)[0]
        self._payload: Optional[Dict[str, Any]] = None
        self._payload_key: Optional[Tuple[str, int]] = None

    # -- schema -----------------------------------------------------------

    def schema_info(self) -> Dict[str, Any]:
        con = _connect(self.db_path)
        try:
            tables = sorted(row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"))
            info = {"db": self.db_path, "db_rel": self.settings.rel(self.db_path),
                    "tables": tables}
            for table in ("nodes", "relations", "events", "relation_provenance"):
                if table in tables:
                    info[table] = {
                        "count": int(con.execute(
                            "SELECT COUNT(*) FROM %s" % table).fetchone()[0]),
                        "columns": _columns(con, table),
                    }
            info["schema"] = ("legacy" if "nodes" not in tables
                              or "lifecycle" not in _columns(con, "relations")
                              else "v3")
            return info
        finally:
            con.close()

    # -- full payload -------------------------------------------------------

    def _layout(self, ids: Sequence[str], kinds: Sequence[str],
                degrees: Sequence[int]) -> Dict[str, Tuple[float, float]]:
        """Deterministic pre-layout: one sector per node kind + hash jitter.

        Cheap and stable: the graph is always paintable instantly, and the
        ForceAtlas2 worker refines the positions client-side afterwards.
        """
        sectors: Dict[str, int] = {}
        for kind in kinds:
            sectors.setdefault(kind, len(sectors))
        counts: Dict[str, int] = {}
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
        seen: Dict[str, int] = {}
        positions: Dict[str, Tuple[float, float]] = {}
        total_sectors = max(1, len(sectors))
        for node_id, kind, degree in zip(ids, kinds, degrees):
            index = seen.get(kind, 0)
            seen[kind] = index + 1
            angle_base = 2.0 * math.pi * sectors[kind] / total_sectors
            spread = 2.0 * math.pi / total_sectors
            frac = (index + 0.5) / max(1, counts[kind])
            jitter = (int(_sha(node_id)[:8], 16) % 1000) / 1000.0
            radius = 26.0 + 18.0 * math.sqrt(max(1.0, float(degree))) + 6.0 * jitter
            angle = angle_base + spread * (0.08 + 0.84 * frac) + 0.12 * (jitter - 0.5)
            positions[node_id] = (radius * math.cos(angle), radius * math.sin(angle))
        return positions

    def full(self, refresh: bool = False) -> Dict[str, Any]:
        """Full Sigma payload with pre-computed layout positions."""
        try:
            key = (self.db_path, int(os.path.getmtime(self.db_path)))
        except OSError:
            key = (self.db_path, 0)
        if self._payload is not None and self._payload_key == key and not refresh:
            return self._payload
        started = time.perf_counter()
        con = _connect(self.db_path)
        try:
            schema = ("legacy" if not _has_table(con, "nodes") or
                      "lifecycle" not in _columns(con, "relations") else "v3")
            node_cols = _columns(con, "nodes") if _has_table(con, "nodes") else []
            rel_cols = _columns(con, "relations")

            nodes: Dict[str, Dict[str, Any]] = {}
            if _has_table(con, "nodes") and node_cols:
                select = ["node_id", "kind"]
                for optional in ("node_class", "label", "address", "canonical_key"):
                    if optional in node_cols:
                        select.append(optional)
                for row in con.execute("SELECT %s FROM nodes" % ", ".join(select)):
                    item = dict(row)
                    node_id = item["node_id"]
                    nodes[node_id] = {
                        "id": node_id,
                        "label": item.get("label") or node_id,
                        "kind": item.get("kind") or "UNKNOWN",
                        "cls": item.get("node_class") or item.get("kind") or "UNKNOWN",
                        "address": item.get("address") or "",
                    }
            edges: List[Dict[str, Any]] = []
            select = ["relation_id", "kind", "src", "dst"]
            for optional in ("family", "sign_prior", "payload", "epistemic_status"):
                if optional in rel_cols:
                    select.append(optional)
            for row in con.execute("SELECT %s FROM relations" % ", ".join(select)):
                item = dict(row)
                amount = None
                payload = item.get("payload")
                if payload:
                    try:
                        parsed = json.loads(payload)
                        amount = parsed.get("amount")
                    except (ValueError, TypeError):
                        amount = None
                edges.append({
                    "id": item.get("relation_id", ""),
                    "source": item["src"],
                    "target": item["dst"],
                    "kind": item.get("kind", ""),
                    "family": item.get("family", ""),
                    "sign": item.get("sign_prior", ""),
                    "amount": amount,
                })
            for edge in edges:
                for endpoint in (edge["source"], edge["target"]):
                    if endpoint not in nodes:
                        prefix = endpoint.split(":", 1)[0] if ":" in endpoint else "node"
                        nodes[endpoint] = {
                            "id": endpoint, "label": endpoint, "kind": prefix.upper(),
                            "cls": prefix.upper(), "address": "",
                        }
            degrees = {node_id: 0 for node_id in nodes}
            for edge in edges:
                degrees[edge["source"]] = degrees.get(edge["source"], 0) + 1
                degrees[edge["target"]] = degrees.get(edge["target"], 0) + 1
            ids = sorted(nodes)
            positions = self._layout(ids, [nodes[i]["kind"] for i in ids],
                                     [degrees[i] for i in ids])
            out_nodes = []
            classes: Dict[str, int] = {}
            for node_id in ids:
                node = nodes[node_id]
                degree = degrees[node_id]
                x, y = positions[node_id]
                classes[node["cls"]] = classes.get(node["cls"], 0) + 1
                out_nodes.append({
                    **node,
                    "degree": degree,
                    "size": round(2.0 + 1.8 * math.sqrt(max(1, degree)), 2),
                    "x": round(x, 3),
                    "y": round(y, 3),
                })
            counts = {"nodes": len(out_nodes), "edges": len(edges)}
            version = _sha(self.db_path, counts["nodes"], counts["edges"],
                           *(str(e["id"]) for e in edges[:64]))
            payload = {
                "graph_version": version,
                "db": self.settings.rel(self.db_path),
                "schema": schema,
                "counts": counts,
                "classes": classes,
                "nodes": out_nodes,
                "edges": edges,
                "layout": {"algorithm": "deterministic-ring+hash",
                           "refine": "forceatlas2-worker", "cached": True},
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            self._payload = payload
            self._payload_key = key
            return payload
        finally:
            con.close()

    # -- node detail ------------------------------------------------------

    def node_detail(self, node_id: str) -> Dict[str, Any]:
        con = _connect(self.db_path)
        try:
            rel_cols = _columns(con, "relations")
            detail: Dict[str, Any] = {"id": node_id, "found": False}
            if _has_table(con, "nodes"):
                cols = _columns(con, "nodes")
                select = [c for c in ("node_id", "kind", "node_class", "label",
                                      "address", "canonical_key", "status",
                                      "payload") if c in cols]
                row = con.execute("SELECT %s FROM nodes WHERE node_id=?" % ", ".join(select),
                                  (node_id,)).fetchone()
                if row:
                    detail.update(dict(row))
                    detail["found"] = True
            where = ["(src = ? OR dst = ?)"]
            sql = ("SELECT relation_id, kind, src, dst"
                   + (", family" if "family" in rel_cols else "")
                   + (", sign_prior" if "sign_prior" in rel_cols else "")
                   + " FROM relations WHERE " + " AND ".join(where) + " LIMIT 200")
            relations = [dict(r) for r in con.execute(sql, (node_id, node_id)).fetchall()]
            detail["relations"] = relations
            detail["relation_count"] = len(relations)
            detail.setdefault("label", node_id)
            return detail
        finally:
            con.close()

    def neighbors(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        depth = max(1, min(int(depth), 3))
        frontier = {node_id}
        seen_nodes = {node_id}
        edges: List[Dict[str, Any]] = []
        seen_edges = set()
        con = _connect(self.db_path)
        try:
            rel_cols = _columns(con, "relations")
            sql = ("SELECT relation_id, kind, src, dst"
                   + (", sign_prior" if "sign_prior" in rel_cols else "")
                   + " FROM relations WHERE src IN (%s) OR dst IN (%s)")
            for _ in range(depth):
                if not frontier:
                    break
                marks = ",".join("?" for _ in frontier)
                params = list(frontier) + list(frontier)
                rows = [dict(r) for r in con.execute(sql % (marks, marks), params)]
                next_frontier = set()
                for row in rows:
                    if row["relation_id"] in seen_edges:
                        continue
                    seen_edges.add(row["relation_id"])
                    edges.append(row)
                    for endpoint in (row["src"], row["dst"]):
                        if endpoint not in seen_nodes:
                            seen_nodes.add(endpoint)
                            next_frontier.add(endpoint)
                frontier = next_frontier
        finally:
            con.close()
        return {"root": node_id, "depth": depth, "nodes": sorted(seen_nodes),
                "edges": edges, "count_nodes": len(seen_nodes),
                "count_edges": len(edges)}

    # -- Q1–Q8 -----------------------------------------------------------

    def query(self, name: str, **params: Any) -> Dict[str, Any]:
        """Run one read-contract query; errors surface as honest statuses."""
        from orvyren.graph import api as graph_api

        dispatch = {
            "q1": lambda: graph_api.exposure(
                self.db_path, params.get("holder", ""),
                as_of=params.get("as_of"), as_of_block=params.get("as_of_block"),
                max_depth=int(params.get("max_depth", 3) or 3)),
            "q2": lambda: graph_api.dependency_paths(
                self.db_path, params.get("src", ""), params.get("dst", ""),
                kinds=tuple(params.get("kinds") or ()),
                max_depth=int(params.get("max_depth", 4) or 4),
                as_of=params.get("as_of"), as_of_block=params.get("as_of_block")),
            "q4": lambda: graph_api.pit(
                self.db_path, as_of=params.get("as_of"),
                as_of_block=params.get("as_of_block"),
                limit=int(params.get("limit", 100) or 100)),
            "q5": lambda: graph_api.timeline(
                self.db_path, as_of=params.get("as_of"),
                as_of_block=params.get("as_of_block"),
                limit=int(params.get("limit", 50) or 50)),
            "q6": lambda: graph_api.provenance(
                self.db_path, relation_id=params.get("relation_id", "")),
            "q7": lambda: graph_api.concentration(
                self.db_path, params.get("asset", ""),
                as_of=params.get("as_of"), as_of_block=params.get("as_of_block")),
            "q8": lambda: graph_api.permissions(
                self.db_path, params.get("subject", ""),
                as_of=params.get("as_of"), as_of_block=params.get("as_of_block")),
            "snapshot": lambda: graph_api.snapshot(
                self.db_path, as_of=params.get("as_of"),
                as_of_block=params.get("as_of_block")),
        }
        if name == "q3":
            return self._q3(params)
        handler = dispatch.get(name)
        if handler is None:
            return {"query": name, "status": "UNKNOWN_QUERY"}
        try:
            return handler()
        except sqlite3.OperationalError as exc:
            return {"query": name, "status": "SCHEMA_UNSUPPORTED",
                    "detail": str(exc), "db": self.settings.rel(self.db_path)}
        except FileNotFoundError as exc:
            return {"query": name, "status": "DB_NOT_FOUND", "detail": str(exc)}

    def _q3(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Q3 — open contradictions (unresolved CONTRADICTS pairs)."""
        started = time.perf_counter()
        con = _connect(self.db_path)
        try:
            rel_cols = _columns(con, "relations")
            sign = ", sign_prior" if "sign_prior" in rel_cols else ""
            rows = [dict(r) for r in con.execute(
                "SELECT relation_id, kind, src, dst%s FROM relations "
                "WHERE kind = 'CONTRADICTS' LIMIT 200" % sign).fetchall()]
        finally:
            con.close()
        return {"query": "Q3", "rows": rows, "count": len(rows),
                "status": "OK" if rows else "NO_OPEN_CONTRADICTIONS",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "mode": "LIVE"}

    def snapshot_counts(self) -> Dict[str, Any]:
        con = _connect(self.db_path)
        try:
            counts = {}
            for table in ("nodes", "relations", "events", "relation_provenance"):
                if _has_table(con, table):
                    counts[table] = int(con.execute(
                        "SELECT COUNT(*) FROM %s" % table).fetchone()[0])
            return {"db": self.settings.rel(self.db_path), "counts": counts,
                    "schema": self.schema_info()["schema"]}
        finally:
            con.close()
