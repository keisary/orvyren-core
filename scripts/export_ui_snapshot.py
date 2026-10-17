#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export a compact, UI-ready JSON snapshot from the read-only graph API.

The UI and Hermes-B consume this file; they never open ``GraphStore``. The
snapshot is deliberately small and stable: counts, Q1/Q4/Q7 for the busiest
holder/asset, one Q6 provenance walk, and the latest block/time.
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

from orvyren.graph import api  # noqa: E402

DEFAULT_DB = r"D:/orvyren_10h_2026-10-17/graph_v3.sqlite"
DEFAULT_OUT = r"D:/orvyren_10h_2026-10-17/ui_snapshot.json"


def _connect(db: str) -> sqlite3.Connection:
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    con.row_factory = sqlite3.Row
    return con


def _latest(db: str) -> Dict[str, Any]:
    con = _connect(db)
    try:
        row = con.execute(
            "SELECT MAX(block_number) AS block, MAX(valid_from) AS as_of "
            "FROM relations").fetchone()
        holder = con.execute(
            "SELECT src, COUNT(*) AS n FROM relations WHERE kind='HOLDS' "
            "GROUP BY src ORDER BY n DESC, src LIMIT 1").fetchone()
        asset = con.execute(
            "SELECT dst, COUNT(*) AS n FROM relations WHERE kind='HOLDS' "
            "GROUP BY dst ORDER BY n DESC, dst LIMIT 1").fetchone()
        debt_asset = con.execute(
            "SELECT dst, COUNT(*) AS n FROM relations WHERE kind='OWES' "
            "GROUP BY dst ORDER BY n DESC, dst LIMIT 1").fetchone()
        relation = con.execute(
            "SELECT relation_id FROM relations ORDER BY row_id DESC LIMIT 1").fetchone()
    finally:
        con.close()
    return {
        "block": int(row["block"]) if row and row["block"] is not None else None,
        "as_of": row["as_of"] if row else None,
        "holder": holder["src"] if holder else None,
        "asset": asset["dst"] if asset else None,
        "debt_asset": debt_asset["dst"] if debt_asset else None,
        "relation_id": relation["relation_id"] if relation else None,
    }


def build(db: str, *, holder: Optional[str] = None,
          asset: Optional[str] = None) -> Dict[str, Any]:
    latest = _latest(db)
    holder = holder or latest["holder"]
    asset = asset or latest["asset"]
    q7_asset = latest.get("debt_asset") or asset
    as_of = latest["as_of"]
    as_of_block = latest["block"]
    snap = api.snapshot(db, as_of=as_of, as_of_block=as_of_block)
    q1 = api.exposure(db, holder, as_of=as_of, as_of_block=as_of_block) if holder else None
    q4 = api.pit(db, as_of=as_of, as_of_block=as_of_block, limit=50)
    q7 = api.concentration(db, q7_asset, as_of=as_of, as_of_block=as_of_block) if q7_asset else None
    q6 = api.provenance(db, latest["relation_id"]) if latest["relation_id"] else None
    return {
        "schema": "orvyren-ui-snapshot/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": os.environ.get("ORVYREN_MODE", "LIVE"),
        "db": db,
        "as_of": as_of,
        "as_of_block": as_of_block,
        "holder": holder,
        "asset": asset,
        "q7_asset": q7_asset,
        "counts": snap["counts"],
        "graph_hash": snap["graph_hash"],
        "q1": q1,
        "q4": q4,
        "q6": q6,
        "q7": q7,
        "limits": [
            "event times are interpolated between two exact block timestamps",
            "Q8 is NOT_INGESTED unless Safe/Zodiac permissions were ingested",
            "the snapshot is read-only; no private key is involved",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--holder", default=None)
    parser.add_argument("--asset", default=None)
    args = parser.parse_args(argv)
    data = build(args.db, holder=args.holder, asset=args.asset)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, args.out)
    print(json.dumps({"out": args.out, "counts": data["counts"],
                      "graph_hash": data["graph_hash"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
