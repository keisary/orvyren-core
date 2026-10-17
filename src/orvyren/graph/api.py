"""Read-only SQL API over the ORVYREN graph (schema v3).

The agent and the UI must not import ``GraphStore`` directly: this module is the
single read contract. It opens the database read-only, so a query cannot trigger
the lazy v2 -> v3 migration or create a write transaction.

Usage (from the repository root)::

    PYTHONPATH=src python -m orvyren.graph.api --db ... q1 --holder 0x...
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

DEFAULT_DB = os.environ.get(
    "ORVYREN_GRAPH_DB", r"D:/orvyren_10h_2026-10-17/graph_v3.sqlite")
CHAIN_ID = 8453


def _connect(path: Optional[str] = None) -> sqlite3.Connection:
    db = path or os.environ.get("ORVYREN_GRAPH_DB", DEFAULT_DB)
    if not os.path.exists(db):
        raise FileNotFoundError("graph database not found: %s" % db)
    connection = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _node_id(value: str, prefix: str = "addr") -> str:
    if ":" in value:
        return value
    return f"{prefix}:eip155:{CHAIN_ID}:{value.lower()}"


def _validity(alias: str, as_of: Optional[str], as_of_block: Optional[int]) -> Tuple[List[str], List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []
    if as_of:
        clauses.append(f"({alias}.valid_from IS NULL OR {alias}.valid_from <= ?)")
        params.append(as_of)
        clauses.append(f"({alias}.valid_to IS NULL OR {alias}.valid_to > ?)")
        params.append(as_of)
    if as_of_block is not None:
        clauses.append(f"({alias}.valid_from_block IS NULL OR {alias}.valid_from_block <= ?)")
        params.append(int(as_of_block))
        clauses.append(f"({alias}.valid_to_block IS NULL OR {alias}.valid_to_block > ?)")
        params.append(int(as_of_block))
    return clauses, params


def _active(alias: str) -> List[str]:
    return [f"{alias}.lifecycle = 'ACTIVE'", f"{alias}.validation_status = 'VALIDATED'"]


def exposure(db: Optional[str] = None, holder: str = "", *,
             as_of: Optional[str] = None, as_of_block: Optional[int] = None,
             max_depth: int = 3) -> Dict[str, Any]:
    """Q1 — consolidated direct and indirect exposure of a holder."""
    holder_id = _node_id(holder, "addr")
    started = time.perf_counter()
    valid, vparams = _validity("r", as_of, as_of_block)
    direct_where = ["r.src = ?", "r.kind = 'HOLDS'"] + _active("r") + valid
    walk_valid, walk_params = _validity("r", as_of, as_of_block)
    sql = f"""
        WITH RECURSIVE direct(asset, amount, unit) AS (
            SELECT r.dst,
                   COALESCE(CAST(json_extract(r.payload, '$.amount') AS REAL), 0.0),
                   COALESCE(json_extract(r.payload, '$.unit'), '')
            FROM relations r
            WHERE {' AND '.join(direct_where)}
        ),
        walk(asset, depth) AS (
            SELECT asset, 0 FROM direct
            UNION
            SELECT r.dst, w.depth + 1
            FROM walk w
            JOIN relations r ON r.src = w.asset
            WHERE w.depth < ?
              AND r.kind IN ('DEPOSITED_IN', 'COLLATERALIZES', 'REHYPOTHECATED_TO')
              AND {' AND '.join(_active('r') + walk_valid)}
        )
        SELECT w.asset, MIN(w.depth) AS depth,
               COALESCE(SUM(d.amount), 0.0) AS amount,
               COALESCE(MAX(d.unit), '') AS unit
        FROM walk w
        LEFT JOIN direct d ON d.asset = w.asset
        GROUP BY w.asset
        ORDER BY depth, w.asset
    """
    params: List[Any] = [holder_id] + vparams + [max_depth] + walk_params
    con = _connect(db)
    try:
        rows = [dict(row) for row in con.execute(sql, params).fetchall()]
    finally:
        con.close()
    return {"query": "Q1", "holder": holder_id, "as_of": as_of,
            "as_of_block": as_of_block, "rows": rows, "count": len(rows),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def pit(db: Optional[str] = None, *, as_of: Optional[str] = None,
        as_of_block: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    """Q4 — facts true and known at a point in time."""
    started = time.perf_counter()
    valid, params = _validity("r", as_of, as_of_block)
    where = _active("r") + valid
    con = _connect(db)
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM relations r WHERE " + " AND ".join(where),
            params).fetchone()[0]
        rows = [dict(row) for row in con.execute(
            "SELECT r.relation_id, r.kind, r.src, r.dst, r.valid_from, r.valid_to, "
            "r.valid_from_block, r.valid_to_block, r.epistemic_status, "
            "r.source_family_id FROM relations r WHERE " + " AND ".join(where) +
            " ORDER BY r.relation_id LIMIT ?", params + [int(limit)]).fetchall()]
    finally:
        con.close()
    return {"query": "Q4", "as_of": as_of, "as_of_block": as_of_block,
            "count": int(count), "rows": rows,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def provenance(db: Optional[str] = None, relation_id: str = "") -> Dict[str, Any]:
    """Q6 — provenance refs of a relation (one hop to the source family)."""
    started = time.perf_counter()
    con = _connect(db)
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT relation_id, revision, ref_id, ref_kind, source_family_id, "
            "extract_method, run_id FROM relation_provenance WHERE relation_id = ? "
            "ORDER BY revision, ref_id", (relation_id,)).fetchall()]
    finally:
        con.close()
    return {"query": "Q6", "relation_id": relation_id, "rows": rows,
            "count": len(rows),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def timeline(db: Optional[str] = None, *, as_of: Optional[str] = None,
             as_of_block: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
    """Q5 — recent first-class events, newest block first."""
    started = time.perf_counter()
    clauses: List[str] = []
    params: List[Any] = []
    if as_of:
        clauses.append("(event_time IS NULL OR event_time <= ?)")
        params.append(as_of)
    if as_of_block is not None:
        clauses.append("(block_number IS NULL OR block_number <= ?)")
        params.append(int(as_of_block))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    con = _connect(db)
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT event_id, event_type, chain_id, block_number, tx_hash, "
            "log_index, event_time, status, actors, targets FROM events" + where +
            " ORDER BY block_number DESC, log_index DESC LIMIT ?",
            params + [int(limit)]).fetchall()]
    finally:
        con.close()
    return {"query": "Q5", "as_of": as_of, "as_of_block": as_of_block,
            "rows": rows, "count": len(rows),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def concentration(db: Optional[str] = None, asset: str = "", *,
                  as_of: Optional[str] = None,
                  as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Q7 — counterparty concentration for a debt/collateral asset."""
    asset_id = _node_id(asset, "asset")
    started = time.perf_counter()
    valid, params = _validity("r", as_of, as_of_block)
    where = ["r.dst = ?", "r.kind IN ('OWES', 'COLLATERALIZES')"] + _active("r") + valid
    con = _connect(db)
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT r.src, COALESCE(SUM(CAST(json_extract(r.payload, '$.amount') AS REAL)), 0.0) AS amount "
            "FROM relations r WHERE " + " AND ".join(where) +
            " GROUP BY r.src ORDER BY amount DESC", [asset_id] + params).fetchall()]
    finally:
        con.close()
    total = sum(abs(float(row["amount"])) for row in rows)
    shares = [abs(float(row["amount"])) / total for row in rows] if total else []
    hhi = sum(share * share for share in shares)
    return {"query": "Q7", "asset": asset_id, "as_of": as_of,
            "as_of_block": as_of_block, "counterparties": len(rows),
            "total": total, "hhi": hhi, "rows": rows,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def permissions(db: Optional[str] = None, subject: str = "", *,
                as_of: Optional[str] = None,
                as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Q8 — permission facts as-of a block (empty means NOT INGESTED)."""
    subject_id = _node_id(subject, "addr")
    started = time.perf_counter()
    valid, params = _validity("r", as_of, as_of_block)
    where = ["(r.src = ? OR r.dst = ?)",
             "r.kind IN ('MEMBER_OF', 'ALLOWS', 'REVOKES')"] + _active("r") + valid
    con = _connect(db)
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT r.relation_id, r.kind, r.src, r.dst, r.valid_from, "
            "r.valid_to, r.valid_from_block, r.valid_to_block FROM relations r "
            "WHERE " + " AND ".join(where) + " ORDER BY r.kind, r.src, r.dst",
            [subject_id, subject_id] + params).fetchall()]
    finally:
        con.close()
    return {"query": "Q8", "subject": subject_id, "as_of": as_of,
            "as_of_block": as_of_block, "rows": rows, "count": len(rows),
            "status": "OK" if rows else "NOT_INGESTED",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def snapshot(db: Optional[str] = None, *, as_of: Optional[str] = None,
             as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Counts and a deterministic hash of the current graph slice."""
    started = time.perf_counter()
    con = _connect(db)
    try:
        counts = {
            table: con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            for table in ("relations", "nodes", "events", "relation_provenance")
        }
        rows = con.execute(
            "SELECT relation_id, revision, kind, src, dst FROM relations "
            "ORDER BY relation_id, revision").fetchall()
        digest = hashlib.sha256()
        for row in rows:
            digest.update(("|".join(str(row[key]) for key in row.keys()) + "\n").encode())
    finally:
        con.close()
    return {"query": "snapshot", "as_of": as_of, "as_of_block": as_of_block,
            "counts": counts, "graph_hash": digest.hexdigest(),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    p1 = sub.add_parser("q1")
    p1.add_argument("--holder", required=True)
    p1.add_argument("--as-of", default=None)
    p1.add_argument("--block", type=int, default=None)
    p1.add_argument("--depth", type=int, default=3)
    p4 = sub.add_parser("q4")
    p4.add_argument("--as-of", default=None)
    p4.add_argument("--block", type=int, default=None)
    p6 = sub.add_parser("q6")
    p6.add_argument("--relation-id", required=True)
    p5 = sub.add_parser("q5")
    p5.add_argument("--as-of", default=None)
    p5.add_argument("--block", type=int, default=None)
    p5.add_argument("--limit", type=int, default=50)
    p7 = sub.add_parser("q7")
    p7.add_argument("--asset", required=True)
    p7.add_argument("--as-of", default=None)
    p7.add_argument("--block", type=int, default=None)
    p8 = sub.add_parser("q8")
    p8.add_argument("--subject", required=True)
    p8.add_argument("--as-of", default=None)
    p8.add_argument("--block", type=int, default=None)
    ps = sub.add_parser("snapshot")
    ps.add_argument("--as-of", default=None)
    ps.add_argument("--block", type=int, default=None)
    args = parser.parse_args(argv)
    if args.command == "q1":
        result = exposure(args.db, args.holder, as_of=args.as_of,
                          as_of_block=args.block, max_depth=args.depth)
    elif args.command == "q4":
        result = pit(args.db, as_of=args.as_of, as_of_block=args.block)
    elif args.command == "q6":
        result = provenance(args.db, args.relation_id)
    elif args.command == "q5":
        result = timeline(args.db, as_of=args.as_of, as_of_block=args.block,
                          limit=args.limit)
    elif args.command == "q7":
        result = concentration(args.db, args.asset, as_of=args.as_of,
                               as_of_block=args.block)
    elif args.command == "q8":
        result = permissions(args.db, args.subject, as_of=args.as_of,
                             as_of_block=args.block)
    else:
        result = snapshot(args.db, as_of=args.as_of, as_of_block=args.block)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
