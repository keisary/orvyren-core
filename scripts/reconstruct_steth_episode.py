#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rebuild the **stETH / Celsius (May-July 2022)** episode into evidence JSON.

What it produces
----------------
``evidence/episode_steth_2022-06.json``: the **realisable** discount of stETH
measured on the Curve stETH/ETH pool (``0xDC24316b9AE028F1497c275EB9192a3Ea0f67022``)
by ``get_dy(1, 0, X)`` -- i.e. the ETH actually obtained for a real sale of 1,
100, 1 000 and 10 000 stETH:

* **daily** points from 2022-05-01 to 2022-07-31 (00:00 UTC);
* **hourly** points around the Celsius freeze, 2022-06-10T00:00Z -> 2022-06-17T00:00Z;
* Chainlink ``STETH / ETH`` answer and the pool balances (ETH / stETH) at the
  same blocks, so the composition drift of the pool is citable;
* the measured reference: **> 2 % from 21 May 2022**, **6.19 % on 15 June 2022**
  (block 14 970 000, 22:43:58Z), calm baseline 0.066 % on 2022-05-05.

Modes
-----
* default: archive RPC reads (``--workers`` parallel, ``--from-cache`` for the
  offline rebuild from ``fixtures/raw_w2b/steth_juin2022.json`` (18 measured
  points) and ``fixtures/raw_w2a/steth_2022_serie.json`` (6 points, sizes up to
  100 000 stETH));
* automatic fallback to the cache when the network is unavailable.

The output is written progressively (atomic replace after every point), so an
interrupted run resumes where it stopped (``--no-resume`` to start over).

Usage
-----
    python scripts/reconstruct_steth_episode.py                  # network, full run
    python scripts/reconstruct_steth_episode.py --from-cache      # offline rebuild
    python scripts/reconstruct_steth_episode.py --workers 8 --quiet
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recon_common import (EVIDENCE_DIR, RAW_W2A, RAW_W2B, dump_json_atomic, load_partial,  # noqa: E402
                          load_raw, merge_provenance, new_client, parallel_measure, resolve_blocks,
                          resolve_blocks_parallel, utc_now)

from orvyren.data import ChainlinkFeed, parse_utc, time_grid, utc_iso  # noqa: E402
from orvyren.data.chainlink import FEED_STETH_ETH  # noqa: E402
from orvyren.data.curve import (STETH_POOL_ETH_INDEX, STETH_POOL_STETH_INDEX,  # noqa: E402
                                steth_pool)

# --------------------------------------------------------------------------- #
# Episode constants
# --------------------------------------------------------------------------- #
GRID_START = "2022-05-01T00:00:00Z"
GRID_END = "2022-07-31T00:00:00Z"
GRID_STEP = 86_400                 # daily points over the whole episode
DETAIL_START = "2022-06-10T00:00:00Z"
DETAIL_END = "2022-06-17T00:00:00Z"
DETAIL_STEP = 3_600                # hourly zoom around the Celsius freeze

#: Sizes of the execution ladder, in stETH (the discount that matters is the one
#: of the size you actually have to sell).
SIZES = (1.0, 100.0, 1_000.0, 10_000.0)

#: Reference blocks measured by W2-B (``steth_juin2022.json``) -- kept as an
#: explicit cross-check of whatever this run measures.
REFERENCE_POINTS = (
    (14720000, "2022-05-05", "calm baseline, discount ~0.066 %"),
    (14820000, "2022-05-21", "first measured point above 2 % (2.57 %)"),
    (14940000, "2022-06-10", "Celsius withdrawals suspended on 12 June: 4.69 %"),
    (14970000, "2022-06-15", "worst measured discount of the episode: 6.19 %"),
    (15040000, "2022-06-28", "still 3.80 % two weeks later"),
)

EVENTS: Sequence[Dict[str, str]] = (
    {
        "utc": "2022-05-09T00:00:00Z",
        "ts": str(parse_utc("2022-05-09T00:00:00Z")),
        "label": "Terra/UST collapse drags the whole LST complex; stETH discount opens",
        "source": "https://www.nansen.ai/research/on-chain-forensics-demystifying-steth-depeg",
    },
    {
        "utc": "2022-06-12T00:00:00Z",
        "ts": str(parse_utc("2022-06-12T00:00:00Z")),
        "label": "Celsius suspends withdrawals (12-13 June); exit liquidity already gone",
        "source": "https://www.coindesk.com/business/2022/06/29/nansen-casts-blame-for-steth-de-peg-on-terra",
    },
    {
        "utc": "2022-06-15T00:00:00Z",
        "ts": str(parse_utc("2022-06-15T00:00:00Z")),
        "label": "worst of the episode: 6.19 % to sell 1 stETH on Curve (block 14 970 000)",
        "source": "research/W2B_signaux_detection.md (signal 1.4, measured on-chain)",
    },
)

#: Files archived by W2-A / W2-B, used by ``--from-cache``.
CACHE_FILES = ("steth_juin2022.json", "steth_2022_serie.json")

DEFAULT_OUTPUT = os.path.join(EVIDENCE_DIR, "episode_steth_2022-06.json")


# --------------------------------------------------------------------------- #
# Network collection
# --------------------------------------------------------------------------- #
def measure_point(client: Any, block: int) -> Dict[str, Any]:
    """Discount ladder + Chainlink answer + pool balances at ``block``."""
    pool = steth_pool(client)
    block_ts = client.block_timestamp(block)
    quotes: Dict[str, Any] = {}
    for size, quote in zip(SIZES, pool.ladder(STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, SIZES, block)):
        quotes[str(int(size)) if float(size).is_integer() else str(size)] = {
            "size_steth": size,
            "eth_out": quote.amount_out,
            "price_eth_per_steth": quote.price,
            "discount_bps": quote.discount_bps,
            "discount_pct": None if quote.discount_bps is None else quote.discount_bps / 100.0,
        }
    feed = ChainlinkFeed(client, FEED_STETH_ETH, name="steth_eth")
    try:
        oracle = feed.price(block, block_timestamp=block_ts)
    except Exception as exc:  # the ratio feed is optional context, never a blocker
        oracle = {"error": f"{type(exc).__name__}: {exc}"}
    balances = {
        "eth": pool.balances_whole(STETH_POOL_ETH_INDEX, block),
        "steth": pool.balances_whole(STETH_POOL_STETH_INDEX, block),
    }
    balances["ratio_steth_per_eth"] = (
        balances["steth"] / balances["eth"] if balances["eth"] else None
    )
    return {
        "block": block,
        "block_ts": block_ts,
        "curve_pool": pool.address,
        "discount": quotes,
        "chainlink_steth_eth": oracle,
        "pool_balances": balances,
    }


def collect_network(output_path: str, *, workers: int, resume: bool, log) -> Dict[str, Any]:
    """Full network run; returns the evidence payload."""
    grid = sorted(
        set(time_grid(GRID_START, GRID_END, GRID_STEP))
        | set(time_grid(DETAIL_START, DETAIL_END, DETAIL_STEP))
    )
    grid_key = f"{GRID_START}..{GRID_END}/{GRID_STEP}s + {DETAIL_START}..{DETAIL_END}/{DETAIL_STEP}s"
    payload: Dict[str, Any] = load_partial(output_path, mode="rpc", grid_key=grid_key) if resume else {}
    series: Dict[str, Any] = payload.get("series") or {}
    done_ts = {parse_utc(utc) for utc, point in series.items() if not point.get("error")}
    todo = [ts for ts in grid if ts not in done_ts]
    worker_clients: List[Any] = []

    log(f"grid: {len(grid)} points ({len(done_ts)} already measured, {len(todo)} to go)")
    client = new_client(0)
    known_blocks: Dict[int, Dict[str, Any]] = {}
    for utc, saved in (payload.get("blocks") or {}).items():
        if saved.get("block"):
            known_blocks[parse_utc(utc)] = {"block": saved["block"], "block_ts": saved.get("block_ts")}
    for utc, point in series.items():
        if point.get("block"):
            known_blocks.setdefault(parse_utc(utc), {"block": point["block"], "block_ts": point.get("block_ts")})
    pending = [ts for ts in todo if ts not in known_blocks]
    blocks: Dict[int, Dict[str, Any]] = {}
    if pending:
        log(f"resolving {len(pending)} blocks (sliding window, checked floor)...")
        blocks = resolve_blocks_parallel(pending, workers=workers, log=log,
                                      client_factory=new_client)
        # Persist the block grid straight away: it is the slowest phase of a run, and an
        # interrupted run must not have to search it again.
        merged = dict(known_blocks)
        merged.update(blocks)
        payload["blocks"] = {utc_iso(ts): merged[ts] for ts in grid if ts in merged}
        payload["meta"] = dict(payload.get("meta") or {}, mode="rpc", grid_key=grid_key,
                               generated_utc=utc_now(), complete=False,
                               points_done=len(series), points_expected=len(grid))
        dump_json_atomic(output_path, payload)
    blocks.update(known_blocks)

    block_to_ts = {blocks[ts]["block"]: ts for ts in grid}

    def worker(worker_client: Any, block: int) -> Dict[str, Any]:
        return measure_point(worker_client, block)

    def on_result(block: int, point: Dict[str, Any]) -> None:
        series[utc_iso(block_to_ts[block])] = dict(point, ts=block_to_ts[block])
        payload["series"] = dict(sorted(series.items()))
        payload["meta"] = {
            "episode": "stETH / Celsius -- Curve stETH/ETH realisable discount",
            "mode": "rpc",
            "grid_key": grid_key,
            "generated_utc": utc_now(),
            "complete": False,
            "points_done": len(payload["series"]),
            "points_expected": len(grid),
        }
        dump_json_atomic(output_path, payload)

    if todo:
        log(f"measuring {len(todo)} points with {workers} workers (4 sizes + feed + balances)...")
        started = time.time()
        parallel_measure([blocks[ts]["block"] for ts in todo], worker, workers=workers, log=log,
                         on_result=on_result, clients_out=worker_clients)
        log(f"measured in {time.time() - started:.0f}s")

    for ts in grid:
        utc = utc_iso(ts)
        if utc not in series:
            series[utc] = {"ts": ts, "block": blocks[ts]["block"], "block_ts": blocks[ts]["block_ts"], "error": "not measured"}

    payload.update(
        {
            "series": dict(sorted(series.items(), key=lambda item: item[1].get("ts", 0))),
            "events": [dict(event) for event in EVENTS],
            "reference_points": [
                {"block": block, "utc": label, "note": note} for block, label, note in REFERENCE_POINTS
            ],
            "rpc_provenance": merge_provenance(client, worker_clients),
            "meta": dict(
                payload.get("meta") or {},
                mode="rpc",
                grid_key=grid_key,
                generated_utc=utc_now(),
                complete=True,
                curve_pool="0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
                direction="get_dy(1, 0, X) = sell stETH (coin 1) for ETH (coin 0)",
                sizes_steth=list(SIZES),
                reads_per_point="7 eth_call per point (4 get_dy + 2 balances + 1 Chainlink), "
                                "plus 2-3 eth_getBlockByNumber for the block floor",
                scope="Curve stETH/ETH pool; discount = 1 - ETH obtained / stETH sold, fees and "
                      "slippage included; the 'price' is what a sale realises, not what a screen shows",
            ),
        }
    )
    return payload


# --------------------------------------------------------------------------- #
# Cache rebuild (no network)
# --------------------------------------------------------------------------- #
def collect_from_cache(log) -> Dict[str, Any]:
    """Rebuild the ladder from the points archived by W2-A / W2-B (offline)."""
    series: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}

    def entry_for(ts: int, block: Optional[int] = None) -> Dict[str, Any]:
        utc = utc_iso(ts)
        point = series.setdefault(utc, {"ts": ts, "block": block})
        if block is not None:
            point["block"] = block
        return point

    try:
        rows = load_raw("steth_juin2022.json", RAW_W2B)
        provenance["steth_juin2022.json"] = f"{len(rows)} points (sizes 1/100/1000)"
        for row in rows:
            ts = parse_utc(row["utc"])
            point = entry_for(ts, row.get("block"))
            point["block_ts"] = ts
            discount = point.setdefault("discount", {})
            for size in (1.0, 100.0, 1_000.0):
                key = str(int(size))
                price = row.get(f"prix_vente_{key}stETH")
                if price is None:
                    continue
                discount[key] = {
                    "size_steth": size,
                    "eth_out": price * size,
                    "price_eth_per_steth": price,
                    "discount_bps": (1.0 - price) * 10_000.0,
                    "discount_pct": (1.0 - price) * 100.0,
                }
            if row.get("chainlink_stETHETH") is not None:
                point["chainlink_steth_eth"] = {
                    "price": row["chainlink_stETHETH"],
                    "method": "latestRoundData",
                    "name": "steth_eth",
                }
            point["source"] = "cache:steth_juin2022.json"
    except FileNotFoundError as exc:
        provenance["steth_juin2022.json"] = f"missing: {exc}"

    try:
        rows = load_raw("steth_2022_serie.json", RAW_W2A)
        provenance["steth_2022_serie.json"] = f"{len(rows)} points (sizes 100/1000/10000/100000)"
        for row in rows:
            ts = int(row["ts"])
            point = entry_for(ts, row.get("block"))
            point["block_ts"] = ts
            discount = point.setdefault("discount", {})
            for size, payload in (row.get("get_dy_sortie_stETH") or {}).items():
                price = payload.get("prix_moyen")
                if price is None:
                    continue
                discount[str(int(float(size)))] = {
                    "size_steth": float(size),
                    "eth_out": payload.get("eth_out"),
                    "price_eth_per_steth": price,
                    "discount_bps": (1.0 - price) * 10_000.0,
                    "discount_pct": (1.0 - price) * 100.0,
                }
            balances = point.setdefault("pool_balances", {})
            balances.setdefault("eth", row.get("curve_eth_bal"))
            balances.setdefault("steth", row.get("curve_steth_bal"))
            if row.get("curve_eth_bal"):
                balances.setdefault("ratio_steth_per_eth", row["curve_steth_bal"] / row["curve_eth_bal"])
            point["source"] = "cache:steth_2022_serie.json"
    except FileNotFoundError as exc:
        provenance["steth_2022_serie.json"] = f"missing: {exc}"

    log(f"cache rebuild: {len(series)} points from {len(provenance)} candidate files")
    return {
        "series": dict(sorted(series.items(), key=lambda item: item[1].get("ts") or 0)),
        "events": [dict(event) for event in EVENTS],
        "reference_points": [
            {"block": block, "utc": label, "note": note} for block, label, note in REFERENCE_POINTS
        ],
        "cache_provenance": provenance,
        "meta": {
            "episode": "stETH / Celsius -- Curve stETH/ETH realisable discount",
            "mode": "cache",
            "grid_key": "cache:w2a+w2b",
            "generated_utc": utc_now(),
            "complete": True,
            "curve_pool": "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
            "direction": "get_dy(1, 0, X) = sell stETH (coin 1) for ETH (coin 0)",
            "scope": "points archived by W2-A/W2-B only (18 + 6 measured blocks)",
            "note": "offline rebuild from fixtures/raw_w2a + fixtures/raw_w2b (no network call)",
            "cache_files": list(CACHE_FILES),
        },
    }


# --------------------------------------------------------------------------- #
# Headline metrics
# --------------------------------------------------------------------------- #
def _discount_entry(point: Dict[str, Any], size: float) -> Optional[Dict[str, Any]]:
    return (point.get("discount") or {}).get(str(int(size)))


def compute_headline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The citable figures of the episode, measured on the produced series."""
    points: List[Dict[str, Any]] = [
        dict(point, utc=utc)
        for utc, point in (payload.get("series") or {}).items()
        if isinstance(point, dict) and point.get("discount")
    ]
    headline: Dict[str, Any] = {}
    if not points:
        return headline

    # 1. when did the > 2 % (200 bps) regime start, on the 1 stETH and 1 000 stETH sizes?
    for size, key in ((1.0, "first_above_200bps_1stETH"), (1_000.0, "first_above_200bps_1000stETH")):
        ordered = sorted(
            ((point["ts"], point) for point in points if _discount_entry(point, size)),
            key=lambda item: item[0],
        )
        above = [(ts, point) for ts, point in ordered if (_discount_entry(point, size) or {}).get("discount_bps", 0) > 200]
        if above:
            ts, point = above[0]
            previous = [item for item in ordered if item[0] < ts]
            headline[key] = {
                "utc": point["utc"],
                "ts": ts,
                "discount_bps": _discount_entry(point, size)["discount_bps"],
                "previous_point_utc": previous[-1][1]["utc"] if previous else None,
                "previous_point_discount_bps": (
                    _discount_entry(previous[-1][1], size) or {}).get("discount_bps") if previous else None,
                "block": point.get("block"),
            }

    # 2. the June-2022 peak, with the exact time it was reached
    june = [point for point in points if point["utc"].startswith("2022-06-1")]
    for size, key in ((1.0, "worst_1stETH"), (1_000.0, "worst_1000stETH")):
        candidates = [point for point in points if _discount_entry(point, size)]
        if candidates:
            worst = max(candidates, key=lambda point: _discount_entry(point, size)["discount_bps"])
            headline[key] = {
                "utc": worst["utc"],
                "discount_bps": _discount_entry(worst, size)["discount_bps"],
                "discount_pct": _discount_entry(worst, size)["discount_pct"],
                "block": worst.get("block"),
            }
        in_june = [point for point in june if _discount_entry(point, size)]
        if in_june:
            worst_june = max(in_june, key=lambda point: _discount_entry(point, size)["discount_bps"])
            key = "worst_in_june_1stETH" if size == 1.0 else "worst_in_june_1000stETH"
            headline[key] = {
                "utc": worst_june["utc"],
                "discount_bps": _discount_entry(worst_june, size)["discount_bps"],
                "block": worst_june.get("block"),
            }

    # 3. calm baseline and the daily profile of 15 June 2022
    first = min(points, key=lambda point: point["ts"])
    if _discount_entry(first, 1.0):
        headline["baseline"] = {
            "utc": first["utc"],
            "discount_bps_1stETH": _discount_entry(first, 1.0)["discount_bps"],
            "discount_bps_1000stETH": (_discount_entry(first, 1_000.0) or {}).get("discount_bps"),
        }
    series = payload.get("series") or {}
    for utc in ("2022-06-15T00:00:00Z", "2022-06-15T22:00:00Z"):
        point = series.get(utc)
        if point and _discount_entry(point, 1.0):
            headline[f"discount_at_{utc}"] = {
                "discount_bps_1stETH": _discount_entry(point, 1.0)["discount_bps"],
                "discount_bps_1000stETH": (_discount_entry(point, 1_000.0) or {}).get("discount_bps"),
                "discount_bps_10000stETH": (_discount_entry(point, 10_000.0) or {}).get("discount_bps"),
                "block": point.get("block"),
            }
    return headline


def summarise(payload: Dict[str, Any], output_path: str) -> str:
    """Readable run summary."""
    series = payload.get("series") or {}
    headline = payload.get("headline") or {}
    errors = [utc for utc, point in series.items() if point.get("error")]
    lines = [
        f"episode stETH 2022-06 -- mode {payload['meta']['mode']} -- {len(series)} points -> {output_path}",
        f"  plancher (calme)      : {headline.get('baseline')}",
        f"  > 200 bps (1 stETH)   : {headline.get('first_above_200bps_1stETH')}",
        f"  pire point 1 stETH    : {headline.get('worst_1stETH')}",
        f"  pire point 1000 stETH : {headline.get('worst_1000stETH')}",
        f"  15/06 00:00Z          : {headline.get('discount_at_2022-06-15T00:00:00Z')}",
        f"  15/06 22:00Z          : {headline.get('discount_at_2022-06-15T22:00:00Z')}",
    ]
    if errors:
        lines.append(f"  points en erreur      : {len(errors)} ({errors[:3]}...)")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the stETH / Celsius 2022 Curve discount into evidence JSON.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="output evidence file")
    parser.add_argument("--from-cache", action="store_true", help="rebuild from fixtures/raw_w2* without any network call")
    parser.add_argument("--workers", type=int, default=6, help="parallel workers for the RPC phase (default 6)")
    parser.add_argument("--no-resume", action="store_true", help="ignore points already present in the output file")
    parser.add_argument("--quiet", action="store_true", help="only print the final summary")
    args = parser.parse_args(argv)

    def log(message: str) -> None:
        if not args.quiet:
            print(message, flush=True)

    if args.from_cache:
        payload = collect_from_cache(log)
    else:
        try:
            payload = collect_network(args.out, workers=args.workers, resume=not args.no_resume, log=log)
        except Exception as exc:
            print(f"[steth] network run failed ({type(exc).__name__}: {exc}) -- falling back to --from-cache",
                  file=sys.stderr, flush=True)
            payload = collect_from_cache(log)

    payload["headline"] = compute_headline(payload)
    payload["limitations"] = [
        "Curve get_dy is a quote, not a fill: it assumes the pool state at that block and ignores "
        "gas, and it does not model the CEX exits that were also available in June 2022.",
        "The Chainlink STETH / ETH feed answered with an 18-decimal ratio whose last update can be "
        "hours old; age_seconds is recorded for every point where latestRoundData is available.",
        "Lido's redemption was not open in 2022 (withdrawals came with Shapella, April 2023): the "
        "Curve pool was the only on-chain exit, which is exactly what makes this discount the "
        "realisable price.",
    ]
    dump_json_atomic(args.out, payload)
    print(summarise(payload, args.out), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
