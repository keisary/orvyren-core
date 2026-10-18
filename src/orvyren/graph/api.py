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
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

DEFAULT_DB = os.environ.get(
    "ORVYREN_GRAPH_DB", r"D:/orvyren_10h_2026-10-17/graph_v3.sqlite")
CHAIN_ID = 8453


def _connect(path: Optional[str] = None) -> sqlite3.Connection:
    db = path or os.environ.get("ORVYREN_GRAPH_DB", DEFAULT_DB)
    if not os.path.exists(db):
        raise FileNotFoundError("graph database not found: %s" % db)
    absolute = os.path.abspath(db).replace("\\", "/")
    uri = "file:%s?mode=ro" % urllib.parse.quote(absolute, safe="/:")
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _node_id(value: str, prefix: str = "addr") -> str:
    if ":" in value:
        return value
    return f"{prefix}:eip155:{CHAIN_ID}:{value.lower()}"


def _any_node(value: str) -> str:
    """Resolve a raw address or a canonical node id (graph_path input)."""
    if ":" in value:
        return value
    if value.startswith("0x"):
        return _node_id(value, "addr")
    return _node_id(value, "asset")


def _ts(value: str) -> str:
    """Normalise a timestamp parameter to aware UTC text.

    Timestamps carry heterogeneous offsets (``Z``, ``+02:00``, ``-05:00``);
    comparing their text would order ``10:00+02:00`` after ``08:30Z``. The
    instant is parsed as an aware ``datetime`` (``Z`` accepted, naive = UTC)
    and normalised to UTC before it reaches SQL, where ``julianday`` applies
    the same instant semantics to the stored column values.
    """
    try:
        moment = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00").replace("z", "+00:00"))
    except ValueError:
        return value  # exotic input: leave it to SQLite's own parser
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def _validity(alias: str, as_of: Optional[str], as_of_block: Optional[int]) -> Tuple[List[str], List[Any]]:
    """World-validity clauses; instants compare as UTC instants.

    ``julianday`` on both sides makes the comparison offset-aware (a bare
    ``<=`` on the text would order offsets lexicographically).
    """
    clauses: List[str] = []
    params: List[Any] = []
    if as_of:
        clauses.append(f"({alias}.valid_from IS NULL OR "
                       f"julianday({alias}.valid_from) <= julianday(?))")
        params.append(_ts(as_of))
        clauses.append(f"({alias}.valid_to IS NULL OR "
                       f"julianday({alias}.valid_to) > julianday(?))")
        params.append(_ts(as_of))
    if as_of_block is not None:
        clauses.append(f"({alias}.valid_from_block IS NULL OR {alias}.valid_from_block <= ?)")
        params.append(int(as_of_block))
        clauses.append(f"({alias}.valid_to_block IS NULL OR {alias}.valid_to_block > ?)")
        params.append(int(as_of_block))
    return clauses, params


def _active(alias: str) -> List[str]:
    return [f"{alias}.lifecycle = 'ACTIVE'", f"{alias}.validation_status = 'VALIDATED'"]


#: Current revision of each relation, optionally restricted to revisions that
#: had already been published at ``as_of``. The store is append-only: a
#: correction inserts a new revision of the same ``relation_id``; a PIT read
#: must not use a revision published later.
_CURRENT = ("r.revision = (SELECT MAX(r2.revision) FROM relations r2 "
            "WHERE r2.relation_id = r.relation_id)")


def _current(as_of: Optional[str], con: Optional[sqlite3.Connection] = None) -> Tuple[str, List[Any]]:
    """Revision clause + params; ``as_of`` filters on publication time.

    Minimal fixture schemas may not carry ``inserted_at``: they keep the
    legacy revision semantics rather than failing the whole query.
    """
    if not as_of:
        return _CURRENT, []
    if con is None:
        return _CURRENT, []
    columns = {row[1] for row in con.execute("PRAGMA table_info(relations)")}
    if "inserted_at" not in columns:
        return _CURRENT, []
    clause = ("r.revision = (SELECT MAX(r2.revision) FROM relations r2 "
              "WHERE r2.relation_id = r.relation_id "
              "AND julianday(r2.inserted_at) <= julianday(?))")
    return clause, [_ts(as_of)]


def exposure(db: Optional[str] = None, holder: str = "", *,
             as_of: Optional[str] = None, as_of_block: Optional[int] = None,
             max_depth: int = 3) -> Dict[str, Any]:
    """Q1 — consolidated direct and indirect exposure of a holder."""
    holder_id = _node_id(holder, "addr")
    started = time.perf_counter()
    con = _connect(db)
    valid, vparams = _validity("r", as_of, as_of_block)
    current, cparams = _current(as_of, con)
    direct_where = ["r.src = ?", "r.kind = 'HOLDS'"] + _active("r") + [current] + valid
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
              AND {' AND '.join(_active('r') + [current] + walk_valid)}
        )
        SELECT w.asset, MIN(w.depth) AS depth,
               COALESCE(SUM(CASE WHEN w.depth = 0 THEN d.amount ELSE 0.0 END), 0.0) AS amount,
               COALESCE(MAX(d.unit), '') AS unit
        FROM walk w
        LEFT JOIN direct d ON d.asset = w.asset
        GROUP BY w.asset
        ORDER BY depth, w.asset
    """
    params: List[Any] = ([holder_id] + cparams + vparams +
                         [max_depth] + cparams + walk_params)
    try:
        rows = [dict(row) for row in con.execute(sql, params).fetchall()]
    finally:
        con.close()
    return {"query": "Q1", "holder": holder_id, "as_of": as_of,
            "as_of_block": as_of_block, "rows": rows, "count": len(rows),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def dependency_paths(db: Optional[str] = None, src: str = "", dst: str = "",
                     *, kinds: Sequence[str] = (),
                     max_depth: int = 4,
                     as_of: Optional[str] = None,
                     as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Q2 — bounded dependency paths from ``src`` to ``dst`` with sign.

    Only ``DEPENDS_ON`` and ``AFFECTS`` are traversed: correlations never
    propagate, and a cycle is impossible because the path string is checked.
    ``rows`` is empty when the graph has no such edges; that is an honest
    answer, not an unavailable tool.
    """
    src_id, dst_id = _any_node(src), _any_node(dst)
    allowed = ("DEPENDS_ON", "AFFECTS")
    requested = tuple(k for k in kinds if k in allowed)
    if kinds and not requested:
        return {"query": "Q2", "src": src_id, "dst": dst_id, "rows": [],
                "count": 0, "status": "INVALID_KINDS",
                "latency_ms": 0.0,
                "mode": os.environ.get("ORVYREN_MODE", "LIVE")}
    selected = requested or allowed
    depth = max(1, min(int(max_depth), 8))
    started = time.perf_counter()
    con = _connect(db)
    valid, vparams = _validity("r", as_of, as_of_block)
    current, cparams = _current(as_of, con)
    kind_clause = "r.kind IN (%s)" % ", ".join("?" for _ in selected)
    initial = (["r.src = ?", kind_clause] + _active("r") + [current] + valid)
    recursive = (["w.depth < ?", kind_clause] + _active("r") + [current] + valid +
                 ["instr(w.path, '/' || r.dst || '/') = 0"])
    sql = f"""
        WITH RECURSIVE walk(node, depth, negative, ambiguous, path) AS (
            SELECT r.dst, 1,
                   CASE WHEN r.sign_prior = '-' THEN 1 ELSE 0 END,
                   CASE WHEN r.sign_prior = 'ambigu' THEN 1 ELSE 0 END,
                   '/' || r.src || '/' || r.dst || '/'
            FROM relations r
            WHERE {' AND '.join(initial)}
            UNION ALL
            SELECT r.dst, w.depth + 1,
                   (w.negative + CASE WHEN r.sign_prior = '-' THEN 1 ELSE 0 END) % 2,
                   CASE WHEN w.ambiguous = 1 OR r.sign_prior = 'ambigu'
                        THEN 1 ELSE 0 END,
                   w.path || r.dst || '/'
            FROM walk w
            JOIN relations r ON r.src = w.node
            WHERE {' AND '.join(recursive)}
        )
        SELECT node, depth, negative, ambiguous, path
        FROM walk
        WHERE node = ?
        ORDER BY depth, path
        LIMIT 50
    """
    params: List[Any] = ([src_id] + list(selected) + cparams + vparams +
                         [depth] + list(selected) + cparams + vparams + [dst_id])
    try:
        rows = []
        for row in con.execute(sql, params).fetchall():
            item = dict(row)
            item["sign"] = "ambigu" if item.pop("ambiguous") else (
                "-" if item.pop("negative") else "+")
            rows.append(item)
    finally:
        con.close()
    return {"query": "Q2", "src": src_id, "dst": dst_id, "rows": rows,
            "count": len(rows), "status": "OK",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def pit(db: Optional[str] = None, *, as_of: Optional[str] = None,
        as_of_block: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
    """Q4 — facts true and known at a point in time."""
    started = time.perf_counter()
    con = _connect(db)
    valid, params = _validity("r", as_of, as_of_block)
    current, cparams = _current(as_of, con)
    where = _active("r") + [current] + valid
    try:
        count = con.execute(
            "SELECT COUNT(*) FROM relations r WHERE " + " AND ".join(where),
            cparams + params).fetchone()[0]
        rows = [dict(row) for row in con.execute(
            "SELECT r.relation_id, r.kind, r.src, r.dst, r.valid_from, r.valid_to, "
            "r.valid_from_block, r.valid_to_block, r.epistemic_status, "
            "r.source_family_id FROM relations r WHERE " + " AND ".join(where) +
            " ORDER BY r.relation_id LIMIT ?", cparams + params + [int(limit)]).fetchall()]
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
            "extract_method, run_id FROM relation_provenance p "
            "WHERE p.relation_id = ? AND p.revision = ("
            "SELECT MAX(p2.revision) FROM relation_provenance p2 "
            "WHERE p2.relation_id = p.relation_id) "
            "ORDER BY revision, ref_id", (relation_id,)).fetchall()]
    finally:
        con.close()
    return {"query": "Q6", "relation_id": relation_id, "rows": rows,
            "count": len(rows),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def timeline(db: Optional[str] = None, *, as_of: Optional[str] = None,
             as_of_block: Optional[int] = None, limit: int = 50) -> Dict[str, Any]:
    """Q5 — recent first-class events, newest block first.

    Point-in-time on both clocks: an event is admissible at ``as_of`` only
    when it is observable at ``as_of`` (``observation_time``) **and** dated at
    or before it (``event_time``). Filtering on ``event_time`` alone admits a
    datum observed after the decision moment, which breaks INV-PIT on replay.
    """
    started = time.perf_counter()
    clauses: List[str] = []
    params: List[Any] = []
    if as_of:
        clauses.append("(event_time IS NULL OR "
                       "julianday(event_time) <= julianday(?))")
        params.append(_ts(as_of))
    if as_of_block is not None:
        clauses.append("(block_number IS NULL OR block_number <= ?)")
        params.append(int(as_of_block))
    con = _connect(db)
    try:
        if as_of:
            columns = {row[1] for row in con.execute("PRAGMA table_info(events)")}
            if "observation_time" in columns:
                clauses.append("(observation_time IS NULL OR "
                               "julianday(observation_time) <= julianday(?))")
                params.append(_ts(as_of))
            # Minimal fixture schemas without ``observation_time`` keep the
            # legacy single-clock filter (same fallback as ``_current``).
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
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
    con = _connect(db)
    valid, params = _validity("r", as_of, as_of_block)
    current, cparams = _current(as_of, con)
    where = ["((r.kind = 'OWES' AND r.dst = ?) OR "
             "(r.kind = 'COLLATERALIZES' AND r.src = ?))",
             "r.kind IN ('OWES', 'COLLATERALIZES')"] \
        + _active("r") + [current] + valid
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT CASE WHEN r.kind = 'COLLATERALIZES' THEN r.dst ELSE r.src END AS src, "
            "COALESCE(SUM(CAST(json_extract(r.payload, '$.amount') AS REAL)), 0.0) AS amount "
            "FROM relations r WHERE " + " AND ".join(where) +
            " GROUP BY 1 ORDER BY amount DESC",
            [asset_id, asset_id] + cparams + params).fetchall()]
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
    con = _connect(db)
    valid, params = _validity("r", as_of, as_of_block)
    current, cparams = _current(as_of, con)
    where = ["(r.src = ? OR r.dst = ?)",
             "r.kind IN ('MEMBER_OF', 'ALLOWS', 'REVOKES')"] \
        + _active("r") + [current] + valid
    try:
        rows = [dict(row) for row in con.execute(
            "SELECT r.relation_id, r.kind, r.src, r.dst, r.valid_from, "
            "r.valid_to, r.valid_from_block, r.valid_to_block FROM relations r "
            "WHERE " + " AND ".join(where) + " ORDER BY r.kind, r.src, r.dst",
            [subject_id, subject_id] + cparams + params).fetchall()]
    finally:
        con.close()
    return {"query": "Q8", "subject": subject_id, "as_of": as_of,
            "as_of_block": as_of_block, "rows": rows, "count": len(rows),
            "status": "OK" if rows else "NOT_INGESTED",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "mode": os.environ.get("ORVYREN_MODE", "LIVE")}


def snapshot(db: Optional[str] = None, *, as_of: Optional[str] = None,
             as_of_block: Optional[int] = None) -> Dict[str, Any]:
    """Counts and a deterministic hash of the current graph slice.

    The relations slice is the current revision of every relation, PIT-filtered
    when ``as_of`` / ``as_of_block`` are given (the args change the result).
    ``nodes`` / ``events`` / ``relation_provenance`` counts stay whole-table:
    those tables carry no superseded revisions here.
    """
    started = time.perf_counter()
    con = _connect(db)
    try:
        valid, vparams = _validity("r", as_of, as_of_block)
        current, cparams = _current(as_of, con)
        where = [current] + valid
        slice_from = " FROM relations r WHERE " + " AND ".join(where)
        counts = {
            "relations": int(con.execute(
                "SELECT COUNT(*)" + slice_from, cparams + vparams).fetchone()[0]),
            "nodes": int(con.execute(
                "SELECT COUNT(DISTINCT node_id) FROM nodes").fetchone()[0]),
            **{table: con.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
               for table in ("events", "relation_provenance")},
        }
        rows = con.execute(
            "SELECT *" + slice_from + " ORDER BY r.relation_id, r.revision",
            cparams + vparams).fetchall()
        digest = hashlib.sha256()
        for row in rows:
            payload = {key: row[key] for key in row.keys()
                       if key not in ("row_id", "inserted_at")}
            digest.update(json.dumps(payload, sort_keys=True, default=str,
                                     ensure_ascii=False).encode("utf-8") + b"\n")
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
    p2 = sub.add_parser("q2")
    p2.add_argument("--src", required=True)
    p2.add_argument("--dst", required=True)
    p2.add_argument("--kinds", nargs="*", default=None)
    p2.add_argument("--depth", type=int, default=4)
    p2.add_argument("--as-of", default=None)
    p2.add_argument("--block", type=int, default=None)
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
    elif args.command == "q2":
        result = dependency_paths(
            args.db, args.src, args.dst, kinds=tuple(args.kinds or ()),
            max_depth=args.depth, as_of=args.as_of, as_of_block=args.block)
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
