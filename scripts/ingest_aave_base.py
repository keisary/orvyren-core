#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ingest Aave v3 Pool logs on Base into the ORVYREN graph (schema v3).

What it writes
--------------
* a raw, immutable JSONL.gz store plus a hashed manifest;
* ``events`` rows for every decoded Pool log;
* ``nodes`` for addresses, assets, markets, positions, debts and events;
* 8 relation kinds (``HOLDS``, ``DEPOSITED_IN``, ``OWES``, ``COLLATERALIZES``,
  ``LIQUIDATED_IN`` and their signed variants) with provenance refs;
* an ``ingestion_watermarks`` row after every committed chunk.

Design rules
------------
* stdlib + the project's :class:`ArchiveRpc` only;
* idempotent: ``event_id`` is ``event:eip155:8453:<tx>:<log>`` and relation ids
  are per event, so a rerun cannot create a second logical fact;
* the block is authoritative for PIT; the timestamp is fetched from the block;
* no private key, no transaction, no network write beyond read-only RPC.

Usage
-----
    python scripts/ingest_aave_base.py --blocks 30000 --max-events 15000
    python scripts/ingest_aave_base.py --from-block 52700000 --to-block 52725279

The default DB is external to the repository:
``D:/orvyren_10h_2026-10-17/graph_v3.sqlite``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.data.rpc import ArchiveRpc, RpcError, decode_words  # noqa: E402
from orvyren.graph.record import ChainRef, RelationRecord  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402

CHAIN_ID = 8453
POOL = "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5"
RPC = "https://base.gateway.tenderly.co"
SOURCE_ID = "base-aave-v3-pool"
SOURCE_FAMILY = "SF-AAVE-BASE-RPC"
DEFAULT_DB = r"D:/orvyren_10h_2026-10-17/graph_v3.sqlite"
DEFAULT_RAW = r"D:/orvyren_10h_2026-10-17/raw"

# keccak256 of the Aave v3 Pool event signatures (computed 2026-10-17).
TOPIC_SUPPLY = "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
TOPIC_WITHDRAW = "0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7"
TOPIC_BORROW = "0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0"
TOPIC_REPAY = "0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051"
TOPIC_LIQUIDATION = "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286"
TOPIC_RESERVE_DATA = "0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a"
TOPIC_COLLATERAL_ENABLED = "0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2"
TOPIC_COLLATERAL_DISABLED = "0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd"

EVENT_TYPES = {
    TOPIC_SUPPLY: "SUPPLY",
    TOPIC_WITHDRAW: "WITHDRAW",
    TOPIC_BORROW: "BORROW",
    TOPIC_REPAY: "REPAY",
    TOPIC_LIQUIDATION: "LIQUIDATION",
    TOPIC_RESERVE_DATA: "RESERVE_DATA_UPDATED",
    TOPIC_COLLATERAL_ENABLED: "COLLATERAL_ENABLED",
    TOPIC_COLLATERAL_DISABLED: "COLLATERAL_DISABLED",
}

# Known Base Aave reserves; unknown reserves are read on-chain and default to
# ACTIF/18 decimals. Keeping the map makes the first slice deterministic.
KNOWN_RESERVES: Dict[str, Tuple[str, int, str]] = {
    "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": ("USDC", 6, "STABLECOIN"),
    "0x4200000000000000000000000000000000000006": ("WETH", 18, "ACTIF"),
    "0xc1cba3fcea344f92d9239c08c0568f6f2f0ee452": ("wstETH", 18, "LST"),
    "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22": ("cbETH", 18, "LST"),
    "0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42": ("EURC", 6, "STABLECOIN"),
    "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": ("USDbC", 6, "STABLECOIN"),
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf": ("cbBTC", 8, "ACTIF"),
}

_TS_CACHE: Dict[int, int] = {}
_META_CACHE: Dict[str, Tuple[str, int, str]] = dict(KNOWN_RESERVES)


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def topic_addr(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def data_words(data: str) -> List[int]:
    return decode_words(data) if data and data != "0x" else []


def addr_id(address: str) -> str:
    return f"addr:eip155:{CHAIN_ID}:{address.lower()}"


def asset_id(address: str) -> str:
    return f"asset:eip155:{CHAIN_ID}:{address.lower()}"


def market_id(reserve: str) -> str:
    return f"market:eip155:{CHAIN_ID}:{POOL.lower()}:{reserve.lower()}"


def position_id(user: str, reserve: str) -> str:
    return f"position:eip155:{CHAIN_ID}:{user.lower()}:{reserve.lower()}"


def debt_id(reserve: str) -> str:
    return f"debt:eip155:{CHAIN_ID}:{POOL.lower()}:{reserve.lower()}"


def event_id(tx: str, log_index: int) -> str:
    return f"event:eip155:{CHAIN_ID}:{tx.lower()}:{log_index}"


def reserve_meta(rpc: ArchiveRpc, reserve: str, block: int) -> Tuple[str, int, str]:
    """(symbol, decimals, node kind) — known map first, then read-only calls."""
    key = reserve.lower()
    if key in _META_CACHE:
        return _META_CACHE[key]
    symbol, decimals, kind = "UNKNOWN", 18, "ACTIF"
    symbol_ok = decimals_ok = False
    try:
        raw = rpc.eth_call(reserve, "0x95d89b41", block)  # symbol()
        if raw and raw != "0x":
            # ABI string: offset, length, bytes.
            words = decode_words(raw)
            if len(words) >= 2:
                offset = words[0]
                length = words[1]
                start = 2 + offset * 2 + 64
                body = raw[start:start + length * 2]
                symbol = bytes.fromhex(body).decode("utf-8", "replace") or symbol
                if not symbol.isprintable():
                    symbol = "UNKNOWN"
                symbol_ok = symbol != "UNKNOWN"
    except Exception:
        pass
    try:
        raw = rpc.eth_call(reserve, "0x313ce567", block)  # decimals()
        if raw and raw != "0x":
            decimals = decode_words(raw)[0]
            decimals_ok = True
    except Exception:
        pass
    if not symbol_ok or not decimals_ok:
        # An unknown reserve with guessed metadata would silently mis-scale
        # every amount. Refuse instead of fabricating decimals/symbol.
        raise RuntimeError(
            "reserve metadata unavailable for %s at block %s (symbol_ok=%s, decimals_ok=%s)"
            % (reserve, block, symbol_ok, decimals_ok))
    _META_CACHE[key] = (symbol, int(decimals), kind)
    return _META_CACHE[key]


def block_times(rpc: ArchiveRpc, blocks: Sequence[int],
                from_block: int, to_block: int) -> Dict[int, int]:
    """Timestamps for the observed blocks.

    Tenderly rejects JSON-RPC batches and a per-block call would cost thousands
    of requests for a 30 k-block slice. The block number remains authoritative
    for PIT; event timestamps are linearly interpolated between the two exact
    chunk endpoints, and the payload says so (``chunk_interpolated``).
    """
    out: Dict[int, int] = {}
    unique = sorted(set(int(b) for b in blocks))
    if not unique:
        return out
    try:
        start_ts = rpc.block_timestamp(from_block)
        end_ts = rpc.block_timestamp(to_block)
    except Exception as exc:
        # Never substitute wall-clock time for a block timestamp: a fabricated
        # event time would silently corrupt PIT and provenance. Stop instead.
        raise RuntimeError(
            "block timestamp unavailable for chunk %s..%s: %s"
            % (from_block, to_block, exc)) from exc
    if int(start_ts) <= 0 or int(end_ts) <= 0:
        raise RuntimeError(
            "non-positive block timestamp for chunk %s..%s" % (from_block, to_block))
    span_blocks = max(1, int(to_block) - int(from_block))
    span_ts = int(end_ts) - int(start_ts)
    for block in unique:
        if block in _TS_CACHE:
            out[block] = _TS_CACHE[block]
            continue
        if span_ts > 0:
            ratio = (block - int(from_block)) / span_blocks
            stamp = int(start_ts + ratio * span_ts)
        else:
            stamp = int(start_ts)
        _TS_CACHE[block] = stamp
        out[block] = stamp
    return out


def decode_log(log: Mapping[str, Any], block_ts: int) -> Dict[str, Any]:
    topics = list(log.get("topics") or [])
    if not topics:
        return {"event_type": "UNKNOWN", "payload": {}}
    topic0 = topics[0].lower()
    event_type = EVENT_TYPES.get(topic0, "UNKNOWN")
    data = data_words(log.get("data", "0x"))
    payload: Dict[str, Any] = {
        "topic0": topic0,
        "data_words": len(data),
        "block_time_source": "block",
    }
    if event_type == "SUPPLY" and len(topics) >= 3 and len(data) >= 2:
        payload.update(reserve=topic_addr(topics[1]),
                       on_behalf_of=topic_addr(topics[2]),
                       user="0x" + f"{data[0]:040x}",
                       amount_raw=str(data[1]))
    elif event_type == "WITHDRAW" and len(topics) >= 4 and data:
        payload.update(reserve=topic_addr(topics[1]),
                       user=topic_addr(topics[2]),
                       to=topic_addr(topics[3]),
                       amount_raw=str(data[0]))
    elif event_type == "BORROW" and len(topics) >= 3 and len(data) >= 4:
        payload.update(reserve=topic_addr(topics[1]),
                       on_behalf_of=topic_addr(topics[2]),
                       user="0x" + f"{data[0]:040x}",
                       amount_raw=str(data[1]),
                       interest_rate_mode=data[2],
                       borrow_rate_raw=str(data[3]))
    elif event_type == "REPAY" and len(topics) >= 4 and len(data) >= 2:
        payload.update(reserve=topic_addr(topics[1]),
                       user=topic_addr(topics[2]),
                       repayer=topic_addr(topics[3]),
                       amount_raw=str(data[0]),
                       use_atokens=bool(data[1]))
    elif event_type == "LIQUIDATION" and len(topics) >= 4 and len(data) >= 4:
        payload.update(collateral_asset=topic_addr(topics[1]),
                       debt_asset=topic_addr(topics[2]),
                       user=topic_addr(topics[3]),
                       debt_to_cover_raw=str(data[0]),
                       collateral_amount_raw=str(data[1]),
                       liquidator="0x" + f"{data[2]:040x}",
                       receive_atoken=bool(data[3]))
    elif event_type == "RESERVE_DATA_UPDATED" and len(topics) >= 2 and len(data) >= 5:
        payload.update(reserve=topic_addr(topics[1]),
                       liquidity_rate_raw=str(data[0]),
                       stable_borrow_rate_raw=str(data[1]),
                       variable_borrow_rate_raw=str(data[2]),
                       liquidity_index_raw=str(data[3]),
                       variable_borrow_index_raw=str(data[4]))
    elif event_type in ("COLLATERAL_ENABLED", "COLLATERAL_DISABLED") and len(topics) >= 3:
        payload.update(reserve=topic_addr(topics[1]), user=topic_addr(topics[2]))
    return {"event_type": event_type, "payload": payload}


def relation_record(
    *,
    relation_id: str,
    kind: str,
    src: str,
    src_kind: str,
    dst: str,
    dst_kind: str,
    block: int,
    tx: str,
    timestamp: int,
    event: str,
    payload: Mapping[str, Any],
    sign: str = "+",
) -> RelationRecord:
    body = dict(payload)
    body.setdefault("as_of", iso(timestamp))
    body.setdefault("block", block)
    body.setdefault("event_id", event)
    return RelationRecord(
        relation_id=relation_id,
        family="STRUCTURE_EXPOSURE",
        kind=kind,
        src=src,
        dst=dst,
        src_kind=src_kind,
        dst_kind=dst_kind,
        mechanism="LIQUIDITY",
        sign_prior=sign,
        conditions="",
        regime_scope="base-mainnet",
        horizon_scope="block",
        epistemic_status="FACT",
        lifecycle="ACTIVE",
        validation_status="VALIDATED",
        valid_from=iso(timestamp),
        valid_to=None,
        valid_from_block=block,
        valid_to_block=None,
        revision=1,
        inserted_at=now_iso(),
        provenance_refs=(event,),
        source_family_id=SOURCE_FAMILY,
        extract_method="ONCHAIN_READ",
        model_version="",
        run_id="",
        chain_ref=ChainRef(chain_id=CHAIN_ID, block=block, tx_hash=tx),
        confidence=1.0,
        payload=body,
    )


def decode_and_write(
    store: GraphStore,
    rpc: ArchiveRpc,
    logs: Sequence[Mapping[str, Any]],
    timestamps: Mapping[int, int],
    *,
    max_events: Optional[int] = None,
    written: int = 0,
) -> Tuple[int, Optional[int]]:
    """Decode ``logs`` into events/relations; returns ``(written, cut_block)``.

    ``cut_block`` is ``None`` when the whole chunk was processed. On a
    ``--max-events`` cut it is the block of the first skipped log: the caller
    must never advance the ingestion watermark past it, or a later ``--resume``
    would silently skip the unprocessed tail of the chunk. Re-processing a
    block is safe (event/relation ids are deterministic).
    """
    cut_block: Optional[int] = None
    last_seen_block: Optional[int] = None
    for log in logs:
        if max_events is not None and written >= max_events:
            try:
                cut_block = int(log.get("blockNumber", "0x0"), 16)
            except (TypeError, ValueError):
                # Unknown position: stay conservative, re-run from the last
                # block actually seen (idempotent) instead of skipping ahead.
                cut_block = (last_seen_block + 1) if last_seen_block is not None else 0
            break
        topics = log.get("topics") or []
        if not topics:
            continue
        tx = str(log.get("transactionHash", "")).lower()
        try:
            log_index = int(log.get("logIndex", "0x0"), 16)
            block = int(log.get("blockNumber", "0x0"), 16)
        except (TypeError, ValueError):
            continue
        last_seen_block = block
        if not tx:
            continue
        timestamp = int(timestamps.get(block, 0))
        if timestamp <= 0:
            # A missing timestamp is a provenance failure, not a reason to
            # stamp the event with the ingestion wall clock.
            raise RuntimeError("missing block timestamp for block %s" % block)
        eid = event_id(tx, log_index)
        decoded = decode_log(log, timestamp)
        event_type = decoded["event_type"]
        payload = dict(decoded["payload"])
        payload["block_time_source"] = "chunk_interpolated"
        # LIQUIDATION carries no "reserve": its structural asset is the
        # collateral. Without this the guard below skipped every liquidation
        # and the LIQUIDATED_IN branch was unreachable dead code.
        reserve = payload.get("reserve") or payload.get("collateral_asset")
        user = payload.get("user") or payload.get("on_behalf_of")
        event_node = eid

        # Event row is the low-level fact; every log is kept, decoded or not.
        try:
            store.insert_event({
                "event_id": eid,
                "event_type": event_type,
                "chain_id": CHAIN_ID,
                "block_number": block,
                "block_hash": log.get("blockHash"),
                "tx_hash": tx,
                "log_index": log_index,
                "event_time": iso(timestamp),
                "observation_time": now_iso(),
                "effective_time": iso(timestamp),
                "valid_from": iso(timestamp),
                "actors": [user] if user else [],
                "targets": [POOL],
                "actual": None,
                "payload": payload,
                "status": "CONFIRMED",
            })
        except sqlite3.IntegrityError:
            pass
        # Event node makes the event visible to graph queries.
        if store.node_by_id(event_node) is None:
            store.insert_node(event_node, "EVENT", label=event_type,
                              payload={"event_type": event_type, "block": block})

        if not reserve or not user:
            written += 1
            continue
        symbol, decimals, asset_kind = reserve_meta(rpc, reserve, block)
        raw_amount = payload.get("amount_raw") or payload.get("debt_to_cover_raw")
        try:
            amount = int(raw_amount) / (10 ** decimals) if raw_amount is not None else 0.0
        except Exception:
            amount = 0.0
        unit = symbol
        common = {
            "amount": amount,
            "raw_amount": raw_amount,
            "decimals": decimals,
            "unit": unit,
            "event_type": event_type,
        }

        def write(kind: str, src: str, src_kind: str, dst: str, dst_kind: str,
                  suffix: str, sign: str = "+", extra: Optional[Mapping[str, Any]] = None):
            rid = f"rel:{tx}:{log_index}:{suffix}"
            if store.relation_record_by_id(rid) is not None:
                return
            body = dict(common)
            if extra:
                body.update(extra)
            rec = relation_record(
                relation_id=rid, kind=kind, src=src, src_kind=src_kind,
                dst=dst, dst_kind=dst_kind, block=block, tx=tx,
                timestamp=timestamp, event=event_node, payload=body, sign=sign)
            store.insert_relation_record(rec)

        if event_type == "SUPPLY":
            write("HOLDS", addr_id(user), "ADRESSE", asset_id(reserve), asset_kind,
                  "holds", "+")
            write("DEPOSITED_IN", asset_id(reserve), asset_kind, market_id(reserve),
                  "MARCHE", "deposit", "+")
        elif event_type == "WITHDRAW":
            write("HOLDS", addr_id(user), "ADRESSE", asset_id(reserve), asset_kind,
                  "holds", "-")
            write("DEPOSITED_IN", asset_id(reserve), asset_kind, market_id(reserve),
                  "MARCHE", "deposit", "-")
        elif event_type == "BORROW":
            write("OWES", position_id(user, reserve), "POSITION", debt_id(reserve),
                  "DETTE", "debt", "+", {"reserve": reserve})
        elif event_type == "REPAY":
            write("OWES", position_id(user, reserve), "POSITION", debt_id(reserve),
                  "DETTE", "debt", "-", {"reserve": reserve})
        elif event_type == "COLLATERAL_ENABLED":
            write("COLLATERALIZES", asset_id(reserve), asset_kind, market_id(reserve),
                  "MARCHE", "collateral", "+")
        elif event_type == "COLLATERAL_DISABLED":
            write("COLLATERALIZES", asset_id(reserve), asset_kind, market_id(reserve),
                  "MARCHE", "collateral", "-")
        elif event_type == "LIQUIDATION":
            debt_asset = payload.get("debt_asset")
            if debt_asset:
                debt_symbol, debt_decimals, _ = reserve_meta(rpc, debt_asset, block)
                try:
                    debt_amount = int(payload.get("debt_to_cover_raw", "0")) / (10 ** debt_decimals)
                except Exception:
                    debt_amount = 0.0
                write("LIQUIDATED_IN", addr_id(user), "ADRESSE", market_id(reserve),
                      "MARCHE", "liquidation", "-",
                      {"debt_asset": debt_asset, "debt_symbol": debt_symbol,
                       "amount": debt_amount, "unit": debt_symbol,
                       "decimals": debt_decimals,
                       "liquidator": payload.get("liquidator"),
                       "collateral_asset": reserve,
                       "collateral_amount_raw": payload.get("collateral_amount_raw")})
        written += 1
    return written, cut_block


def write_raw(raw_dir: str, from_block: int, to_block: int,
              logs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    directory = os.path.join(raw_dir, SOURCE_ID, day)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{from_block}-{to_block}.jsonl.gz")
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for log in logs:
            handle.write(json.dumps(log, sort_keys=True, separators=(",", ":")) + "\n")
    with open(path, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    return {"path": path, "sha256": digest, "count": len(logs)}


def read_manifest(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return list(json.load(handle))


def write_manifest(path: str, entries: Sequence[Mapping[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(list(entries), handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--raw-dir", default=DEFAULT_RAW)
    parser.add_argument("--rpc", default=RPC)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--blocks", type=int, default=30_000,
                        help="number of blocks ending at head (ignored with --from-block)")
    parser.add_argument("--from-block", type=int, default=None)
    parser.add_argument("--to-block", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=15_000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--no-raw", action="store_true")
    args = parser.parse_args(argv)

    if args.chunk_size <= 0 or args.chunk_size > 1000:
        parser.error("--chunk-size must be in 1..1000 for the free Tenderly endpoint")
    os.makedirs(args.raw_dir, exist_ok=True)
    manifest_path = os.path.join(args.raw_dir, SOURCE_ID, "manifest.json")
    manifest = read_manifest(manifest_path)

    rpc = ArchiveRpc(urls=[args.rpc], timeout=30, retries=2)
    head = rpc.eth_block_number()
    to_block = args.to_block if args.to_block is not None else head
    if args.from_block is not None:
        from_block = args.from_block
    else:
        from_block = max(0, to_block - args.blocks + 1)
    if from_block > to_block:
        parser.error("from-block is greater than to-block")

    started = time.time()
    total_events = 0
    total_logs = 0
    with GraphStore(args.db) as store:
        store.insert_source_family(SOURCE_FAMILY,
                                   "Aave v3 Pool logs read from Base JSON-RPC",
                                   "PRIMARY")
        if args.resume:
            row = store.connection.execute(
                "SELECT last_block FROM ingestion_watermarks WHERE source_id=?",
                (SOURCE_ID,)).fetchone()
            if row and row["last_block"] is not None:
                from_block = max(from_block, int(row["last_block"]) + 1)
        cursor = from_block
        while cursor <= to_block and total_events < args.max_events:
            stop = min(cursor + args.chunk_size - 1, to_block)
            logs = rpc.get_logs(from_block=cursor, to_block=stop,
                                address=POOL, chunk_size=args.chunk_size)
            total_logs += len(logs)
            blocks = []
            for log in logs:
                try:
                    blocks.append(int(log.get("blockNumber", "0x0"), 16))
                except (TypeError, ValueError):
                    pass
            timestamps = block_times(rpc, blocks, cursor, stop)
            if not args.no_raw:
                entry = write_raw(args.raw_dir, cursor, stop, logs)
                entry.update({"source_id": SOURCE_ID, "endpoint": args.rpc,
                              "from_block": cursor, "to_block": stop,
                              "retrieved_at": now_iso()})
                manifest.append(entry)
                write_manifest(manifest_path, manifest)
            total_events, cut_block = decode_and_write(
                store, rpc, logs, timestamps,
                max_events=args.max_events, written=total_events)
            last_hash = None
            if logs and cut_block is None:
                last_hash = logs[-1].get("blockHash")
            # On an --max-events cut the watermark stops at the last fully
            # ingested block so --resume cannot skip the tail of this chunk.
            watermark_block = (stop if cut_block is None
                               else max(cursor - 1, min(stop, cut_block - 1)))
            store.set_watermark(SOURCE_ID, watermark_block, last_hash, now_iso())
            print(f"[{cursor}-{stop}] logs={len(logs)} events_total={total_events} "
                  f"elapsed={time.time() - started:.1f}s", flush=True)
            cursor = stop + 1

    counts = {}
    with GraphStore(args.db) as store:
        counts = store.graph_counts()
    print(json.dumps({
        "db": args.db,
        "from_block": from_block,
        "to_block": to_block,
        "logs": total_logs,
        "events_written": total_events,
        "counts": counts,
        "elapsed_s": round(time.time() - started, 1),
        "rpc": rpc.provenance(),
        "manifest": manifest_path,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
