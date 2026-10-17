#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add deterministic structural relations derived from the ingested slice.

The event ingestion writes the four event-level relations (HOLDS, DEPOSITED_IN,
OWES, COLLATERALIZES). This script adds the world-layer edges that make the
graph answer structural questions without inventing facts:

* ``PART_OF``        market -> pool
* ``DEPLOYED_ON``    market -> chain
* ``IS_A``           asset -> asset class
* ``CONSTRAINS``     reserve parameter -> market (latest ReserveDataUpdated)

Every row keeps its provenance event and its block. Running the script twice
is a no-op because the relation ids are deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.graph.record import ChainRef, RelationRecord  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402

CHAIN_ID = 8453
POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
SOURCE_FAMILY = "SF-AAVE-BASE-RPC"
DEFAULT_DB = r"D:/orvyren_10h_2026-10-17/graph_v3.sqlite"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def record(*, rid: str, kind: str, family: str, src: str, src_kind: str,
           dst: str, dst_kind: str, block: int, timestamp: int,
           event: str, payload: Optional[Dict[str, Any]] = None) -> RelationRecord:
    return RelationRecord(
        relation_id=rid, family=family, kind=kind,
        src=src, dst=dst, src_kind=src_kind, dst_kind=dst_kind,
        mechanism="LIQUIDITY", sign_prior="+",
        conditions="", regime_scope="base-mainnet", horizon_scope="block",
        epistemic_status="FACT", lifecycle="ACTIVE", validation_status="VALIDATED",
        valid_from=iso(timestamp), valid_to=None,
        valid_from_block=block, valid_to_block=None,
        revision=1, inserted_at=now_iso(),
        provenance_refs=(event,), source_family_id=SOURCE_FAMILY,
        extract_method="ONCHAIN_READ", model_version="", run_id="",
        chain_ref=ChainRef(chain_id=CHAIN_ID, block=block, tx_hash=event),
        confidence=1.0, payload=dict(payload or {}),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args(argv)
    store = GraphStore(args.db)
    try:
        src = store.connection.execute(
            "SELECT node_id, kind FROM nodes WHERE node_id LIKE 'asset:eip155:8453:%' "
            "AND row_id IN (SELECT MAX(row_id) FROM nodes GROUP BY node_id)"
        ).fetchall()
        markets = store.connection.execute(
            "SELECT node_id, kind FROM nodes WHERE node_id LIKE 'market:eip155:8453:%' "
            "AND row_id IN (SELECT MAX(row_id) FROM nodes GROUP BY node_id)"
        ).fetchall()
        chain = f"chain:eip155:{CHAIN_ID}"
        pool = f"pool:eip155:{CHAIN_ID}:{POOL.lower()}"
        if store.node_by_id(chain) is None:
            store.insert_node(chain, "CHAINE", label="Base")
        if store.node_by_id(pool) is None:
            store.insert_node(pool, "POOL", label="Aave v3 Pool (Base)")

        # Latest block/time for structural anchors (same event row for both, so
        # block and timestamp cannot come from two different events).
        row = store.connection.execute(
            "SELECT block_number AS block, event_time AS ts FROM events "
            "ORDER BY block_number DESC LIMIT 1").fetchone()
        block = int(row["block"] or 0) if row else 0
        timestamp = 0
        if row and row["ts"]:
            timestamp = int(datetime.fromisoformat(row["ts"]).timestamp())
        if block <= 0 or timestamp <= 0:
            raise RuntimeError(
                "structural backfill needs at least one timestamped event "
                "(block=%s, timestamp=%s)" % (block, timestamp))

        for market in markets:
            market_id = market["node_id"]
            for kind, dst, dst_kind, suffix in (
                ("PART_OF", pool, "POOL", "part-of"),
                ("DEPLOYED_ON", chain, "CHAINE", "deployed-on"),
            ):
                rid = f"struct:{suffix}:{market_id}"
                if store.relation_record_by_id(rid) is not None:
                    continue
                store.insert_relation_record(record(
                    rid=rid, kind=kind, family="STRUCTURE_EXPOSURE",
                    src=market_id, src_kind="MARCHE",
                    dst=dst, dst_kind=dst_kind, block=block, timestamp=timestamp,
                    event=f"struct:{suffix}",
                    payload={"as_of": iso(timestamp)}))

        for asset in src:
            asset_id, asset_kind = asset["node_id"], asset["kind"]
            class_id = f"class:eip155:{CHAIN_ID}:{asset_kind}"
            if store.node_by_id(class_id) is None:
                store.insert_node(class_id, "CLASSE", label=asset_kind)
            rid = f"struct:is-a:{asset_id}"
            if store.relation_record_by_id(rid) is None:
                store.insert_relation_record(record(
                    rid=rid, kind="IS_A", family="STRUCTURE_EXPOSURE",
                    src=asset_id, src_kind=asset_kind,
                    dst=class_id, dst_kind="CLASSE", block=block,
                    timestamp=timestamp, event="struct:is-a",
                    payload={"as_of": iso(timestamp)}))

        # Latest ReserveDataUpdated per reserve -> a queryable parameter plane.
        rows = store.connection.execute(
            "SELECT event_id, block_number, event_time, payload FROM events "
            "WHERE event_type='RESERVE_DATA_UPDATED' ORDER BY block_number DESC, event_id"
        ).fetchall()
        # "Latest" per reserve = highest (block, log_index) — event_id is
        # ``event:eip155:<chain>:<tx>:<log_index>`` and its lexicographic order
        # follows the tx hash, not the log order, so sort explicitly here.
        def _log_order(event_id: str) -> int:
            try:
                return int(event_id.rsplit(":", 1)[1])
            except (IndexError, ValueError):
                return -1
        rows = sorted(rows, key=lambda r: (int(r["block_number"]), _log_order(r["event_id"])),
                      reverse=True)
        seen = set()
        for row in rows:
            payload = json.loads(row["payload"] or "{}")
            reserve = payload.get("reserve")
            if not reserve or reserve.lower() in seen:
                continue
            seen.add(reserve.lower())
            market_id = f"market:eip155:{CHAIN_ID}:{POOL.lower()}:{reserve.lower()}"
            if store.node_by_id(market_id) is None:
                continue
            param_id = f"param:eip155:{CHAIN_ID}:{POOL.lower()}:{reserve.lower()}:liquidity_rate"
            if store.node_by_id(param_id) is None:
                store.insert_node(param_id, "PARAMETRE",
                                  label="Aave liquidity rate")
            rid = f"struct:constrains:{reserve.lower()}"
            if store.relation_record_by_id(rid) is not None:
                continue
            raw = payload.get("liquidity_rate_raw")
            try:
                value = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                value = 0.0
            if row["event_time"]:
                ts = int(datetime.fromisoformat(row["event_time"]).timestamp())
            else:
                ts = 0
            store.insert_relation_record(record(
                rid=rid, kind="CONSTRAINS", family="CONSTRAINT_PERMISSION",
                src=param_id, src_kind="PARAMETRE", dst=market_id, dst_kind="MARCHE",
                block=int(row["block_number"]), timestamp=ts, event=row["event_id"],
                payload={"value": value, "unit": "ray", "as_of": iso(ts),
                         "block": int(row["block_number"]),
                         "event_id": row["event_id"]}))
    finally:
        store.close()
    with GraphStore(args.db) as store:
        print(json.dumps({"counts": store.graph_counts(),
                          "kinds": [row[0] for row in store.connection.execute(
                              "SELECT DISTINCT kind FROM relations ORDER BY kind")]},
                         indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
