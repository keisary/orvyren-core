#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORVYREN — W3-B: autonomous reconstruction of the USDC March 2023 (SVB) episode.

Purpose
-------
Rebuild, hour by hour (2023-03-10 00:00Z -> 2023-03-14 00:00Z), the complete
evidence of the March 2023 USDC/USD depeg:

  (a) multi-venue prices: Binance USDCUSDT (1 h klines), OKX USDC-USDT
      (history-candles), Bitstamp usdcusd (ohlc), DeFiLlama chart 1 h
      (Ethereum USDC 0xA0b8...eB48) — low / high / last / volume;
  (b) Chainlink USDC/USD oracle (0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6),
      latestRoundData() read at an hourly archive block — the block is found by
      a local block <-> timestamp binary search (BlockIndex);
  (c) Aave V3 Ethereum USDC: supply (aEthUSDC totalSupply), cash
      (USDC.balanceOf(aEthUSDC)) and utilisation U = 1 - cash/supply, per hour;
  (d) derived signals: discount D(t), cross-venue dispersion sigma_disp,
      oracle/market divergence delta — plus the key facts of W2-B
      (DeFiLlama aggregate 0.876675; Bitstamp 0.80526; oracle 0.90687439;
      dispersion ~870 bps).

Constraints (decided by the project, not for convenience)
----------------------------------------------------------
 * **standard library only** (urllib/json/datetime/...; no `src/` import);
 * **rerunnable**: `--from-cache` rebuilds everything from the raw JSON already
   measured in `fixtures/raw_w2b/` when the network fails or is not wanted;
 * **deterministic**: sorted, rounded JSON output, no invented value — every
   number in `evidence/episode_usdc_2023-03.json` is measured here, and points
   coming from the cache are marked `source: cache`.

Usage
-----
    python scripts/reconstruct_usdc2023_episode.py                # network
    python scripts/reconstruct_usdc2023_episode.py --from-cache   # offline
    python scripts/reconstruct_usdc2023_episode.py --out evidence/episode_usdc_2023-03.json

Methods reproduced from W2-A / W2-B (do not reinvent):
 * archive RPC without a key: eth.drpc.org, eth-mainnet.public.blastapi.io;
 * Chainlink latestRoundData() = 0xfeaf968c (8 decimals);
 * Aave: aToken.totalSupply() = 0x18160ddd; ERC20 balanceOf = 0x70a08231;
 * venues: api.binance.com/api/v3/klines, okx.com/api/v5/market/history-candles,
 *         bitstamp.net/api/v2/ohlc, coins.llama.fi/chart (period=1h).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from statistics import median

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "evidence", "episode_usdc_2023-03.json")
RAW_W2B = os.path.join(ROOT, "fixtures", "raw_w2b")

WINDOW_START_TS = 1678406400  # 2023-03-10T00:00:00Z
WINDOW_END_TS = 1678752000    # 2023-03-14T00:00:00Z
STEP_S = 3600

USER_AGENT = "Mozilla/5.0 (orvyren-research; W3-B reconstruction)"

RPC_ENDPOINTS = [
    "https://eth-mainnet.public.blastapi.io",
    "https://eth.drpc.org",
]
#: Only blastapi accepts batched JSON-RPC requests (tested 2026-10-15;
#: drpc returns HTTP 500 on an array). Batched probes = ~0.13 s/block.
BATCH_ENDPOINTS = ["https://eth-mainnet.public.blastapi.io"]

CHAINLINK_USDC_USD = "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6"
SEL_LATEST_ROUND_DATA = "0xfeaf968c"
CHAINLINK_DECIMALS = 8

AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
AAVE_A_USDC = "0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c"
USDC_ETHEREUM = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
SEL_TOTAL_SUPPLY = "0x18160ddd"
SEL_BALANCE_OF = "0x70a08231"
USDC_DECIMALS = 6

LLAMA_USDC_COIN = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

#: Key facts published in W2-B (research/W2B_signaux_detection.md + notes_01_peg.md),
#: against which the reconstruction checks itself.
W2B_EXPECTED = {
    "defillama_min": 0.876675,
    "bitstamp_min": 0.80526,
    "okx_min": 0.8698,
    "binance_min": 0.882,
    "oracle_min": 0.90687439,
    "dispersion_bps": 870.07,
}

VENUES = ("binance", "okx", "bitstamp", "defillama")


# --------------------------------------------------------------------------
# Small utilities (testable, no network)
# --------------------------------------------------------------------------

def iso_utc(ts):
    """Timestamp (s) -> '2023-03-11T07:00:00Z'."""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_utc(text):
    """'2023-03-11T07:00:00Z' -> timestamp (s)."""
    return int(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def discount_bps(price, peg=1.0):
    """Peg discount in basis points: (peg - price)/peg * 10000."""
    if price is None:
        return None
    return (peg - price) / peg * 10000.0


def dispersion_bps(prices):
    """Cross-venue dispersion: (max - min)/max * 10000 (W2-B convention).

    This is the convention that reproduces the "870 bps" figure of W2-B
    ((0.8820 - 0.80526)/0.8820 = 870.07 bps).
    """
    vals = [p for p in prices if p is not None]
    if len(vals) < 2:
        return None
    vmax, vmin = max(vals), min(vals)
    if vmax <= 0:
        return None
    return (vmax - vmin) / vmax * 10000.0


def divergence_bps(market_price, oracle_price):
    """Oracle/market divergence (W2-B convention): (market - oracle) * 10000."""
    if market_price is None or oracle_price is None:
        return None
    return (market_price - oracle_price) * 10000.0


def decode_uint256(hex_data):
    """Decode an ABI uint256 return (hex '0x...') into an integer."""
    if not hex_data or not isinstance(hex_data, str):
        raise ValueError("empty ABI return")
    raw = hex_data[2:] if hex_data.startswith("0x") else hex_data
    if not raw:
        raise ValueError("empty ABI return")
    return int(raw[:64], 16)


def decode_latest_round_data(hex_data, decimals=CHAINLINK_DECIMALS):
    """Decode Chainlink `latestRoundData()` -> dict (roundId, answer_raw, ...).

    Expected return: 5 ABI words (roundId, answer, startedAt, updatedAt, answeredInRound).
    """
    if not hex_data or not isinstance(hex_data, str):
        raise ValueError("empty Chainlink return")
    raw = hex_data[2:] if hex_data.startswith("0x") else hex_data
    words = [raw[i * 64:(i + 1) * 64] for i in range(5)]
    if any(len(w) < 64 for w in words):
        raise ValueError("Chainlink return too short for latestRoundData()")
    round_id = int(words[0], 16)
    answer_raw = int(words[1], 16)
    return {
        "roundId": round_id,
        "answer_raw": answer_raw,
        "answer": answer_raw / (10 ** decimals),
        "startedAt": int(words[2], 16),
        "updatedAt": int(words[3], 16),
    }


def aave_row_from_raw(supply_raw, cash_raw, decimals=USDC_DECIMALS):
    """Aave utilisation: U = 1 - cash/supply (USDC units)."""
    supply = supply_raw / (10 ** decimals)
    cash = cash_raw / (10 ** decimals)
    utilisation = 1.0 - cash / supply if supply else None
    return {"supply_usdc": supply, "cash_usdc": cash, "utilisation": utilisation}


# --------------------------------------------------------------------------
# Venue parsers (local fixtures -> normalised series)
# Normalised points: {"ts": s, "low": f, "high": f, "last": f, "volume": f|None}
# --------------------------------------------------------------------------

def parse_binance_klines(rows):
    """rows = [[openTime_ms, o, h, l, c, volume, ...], ...] -> points."""
    out = []
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        out.append({
            "ts": int(row[0]) // 1000,
            "high": float(row[2]),
            "low": float(row[3]),
            "last": float(row[4]),
            "volume": float(row[5]),
        })
    return sorted(out, key=lambda p: p["ts"])


def parse_okx_candles(rows):
    """OKX rows (most recent first) -> points sorted ascending.

    Fields: [ts_ms, open, high, low, close, vol(base), volCcy, volCcyQuote, confirm].
    """
    out = []
    for row in rows or []:
        if not isinstance(row, (list, tuple)) or len(row) < 6:
            continue
        out.append({
            "ts": int(row[0]) // 1000,
            "high": float(row[2]),
            "low": float(row[3]),
            "last": float(row[4]),
            "volume": float(row[5]),
        })
    return sorted(out, key=lambda p: p["ts"])


def parse_bitstamp_ohlc(rows):
    """rows = [{"timestamp": "1678406400", "high": ..., "low": ...}, ...]."""
    out = []
    for row in rows or []:
        try:
            out.append({
                "ts": int(row["timestamp"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "last": float(row["close"]),
                "volume": float(row.get("volume") or 0.0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda p: p["ts"])


def parse_llama_chart(payload, coin_id=LLAMA_USDC_COIN):
    """payload = {"coins": {coin_id: {"prices": [{"timestamp": s, "price": f}]}}}."""
    try:
        prices = payload["coins"][coin_id]["prices"]
    except (KeyError, TypeError):
        return []
    out = []
    for pt in prices or []:
        try:
            price = float(pt["price"])
            ts = int(pt["timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        out.append({"ts": ts, "low": price, "high": price, "last": price, "volume": None})
    return sorted(out, key=lambda p: p["ts"])


def filter_window(points, start_ts=WINDOW_START_TS, end_ts=WINDOW_END_TS + STEP_S):
    """Keep only the points in [start, end (exclusive))."""
    return [p for p in points if start_ts <= p["ts"] < end_ts]


# --------------------------------------------------------------------------
# Hourly aggregation + derived signals
# --------------------------------------------------------------------------

def bucket_by_hour(points, hour_starts):
    """Group points by full hour. Return {hour_ts: aggregate}.

    - low  = lowest of the hour (the "stress" price),
    - high = highest of the hour,
    - last = last observation of the hour,
    - volume = sum of the hour's volumes (None if no venue publishes it).
    """
    hours = set(hour_starts)
    out = {}
    for p in points:
        hour = (p["ts"] // STEP_S) * STEP_S
        if hour not in hours:
            continue
        agg = out.setdefault(hour, {"low": None, "high": None, "last": None,
                                    "last_ts": None, "volume": None, "n": 0})
        agg["low"] = p["low"] if agg["low"] is None else min(agg["low"], p["low"])
        agg["high"] = p["high"] if agg["high"] is None else max(agg["high"], p["high"])
        if agg["last_ts"] is None or p["ts"] >= agg["last_ts"]:
            agg["last_ts"] = p["ts"]
            agg["last"] = p["last"]
        if p["volume"] is not None:
            agg["volume"] = (agg["volume"] or 0.0) + p["volume"]
        agg["n"] += 1
    return out


def assemble_hourly(hours, venue_series, oracle_by_hour, aave_by_hour):
    """Build the full hourly table (venues + oracle + Aave + signals)."""
    buckets = {v: bucket_by_hour(pts, hours) for v, pts in venue_series.items()}
    rows = []
    for h in hours:
        venues_row = {}
        lows = []
        lowest_venue = None
        for v in VENUES:
            agg = buckets.get(v, {}).get(h)
            if not agg:
                continue
            venues_row[v] = {
                "low": round(agg["low"], 8),
                "high": round(agg["high"], 8),
                "last": round(agg["last"], 8),
                "volume": round(agg["volume"], 4) if agg["volume"] is not None else None,
                "n": agg["n"],
            }
            lows.append(agg["low"])
            if lowest_venue is None or agg["low"] < venues_row[lowest_venue]["low"]:
                lowest_venue = v
        market = {"n": len(lows), "min": None, "max": None, "median": None,
                  "lowest_venue": None}
        if lows:
            market["min"] = round(min(lows), 8)
            market["max"] = round(max(lows), 8)
            market["median"] = round(median(lows), 8)
            market["lowest_venue"] = lowest_venue

        oracle_row = oracle_by_hour.get(h)
        aave_row = aave_by_hour.get(h)

        signals = {
            "decote_min_bps": _r1(discount_bps(market["min"])),
            "decote_median_bps": _r1(discount_bps(market["median"])),
            "sigma_disp_bps": _r1(dispersion_bps(lows)),
            "divergence_bps": None,
            "divergence_defillama_bps": None,
        }
        if oracle_row and oracle_row.get("price") is not None:
            signals["divergence_bps"] = _r1(divergence_bps(market["median"], oracle_row["price"]))
            if "defillama" in venues_row:
                signals["divergence_defillama_bps"] = _r1(
                    divergence_bps(venues_row["defillama"]["low"], oracle_row["price"]))

        row = {
            "utc": iso_utc(h),
            "ts": h,
            "venues": venues_row,
            "market": market,
            "signals": signals,
            "oracle": oracle_row,
            "aave": aave_row,
        }
        rows.append(row)
    return rows


def compute_facts(hourly, venue_series, oracle_points, blocks_meta=None):
    """Window facts: per-venue minima, dispersion, divergences, Aave."""
    facts = {"minima": {}, "signals": {}}

    for v in VENUES:
        pts = venue_series.get(v) or []
        if not pts:
            continue
        p = min(pts, key=lambda q: q["low"])
        facts["minima"][v] = {
            "low": round(p["low"], 8),
            "utc": iso_utc(p["ts"]),
            "decote_bps": _r1(discount_bps(p["low"])),
        }

    # Oracle: window minimum
    if oracle_points:
        o = min(oracle_points, key=lambda q: q["price"])
        facts["minima"]["oracle_chainlink"] = {
            "answer": round(o["price"], 8),
            "updated_at": iso_utc(o["updatedAt"]),
            "block": o.get("block"),
            "stale_s": int(o.get("sample_ts", o["updatedAt"]) - o["updatedAt"])
            if o.get("sample_ts") else None,
        }

    # Window dispersion (W2-B convention: max/min of the venue minima)
    vals = {v: m["low"] for v, m in facts["minima"].items()
            if v in VENUES and m["low"] is not None}
    if len(vals) >= 2:
        vmax = max(vals, key=vals.get)
        vmin = min(vals, key=vals.get)
        facts["signals"]["dispersion_window_bps"] = {
            "value_bps": round(dispersion_bps(list(vals.values())), 2),
            "method": "(max(minima_venues) - min(minima_venues)) / max(minima_venues) * 10000",
            "max_venue": vmax,
            "min_venue": vmin,
        }

    # Maximum dispersion within a single hour
    best = None
    for row in hourly:
        s = row["signals"]["sigma_disp_bps"]
        if s is not None and (best is None or s > best["value_bps"]):
            best = {"value_bps": s, "utc": row["utc"],
                    "venues": {v: d["low"] for v, d in row["venues"].items()}}
    if best:
        facts["signals"]["max_hourly_dispersion"] = best

    # Oracle/market divergences
    divs = [(row["signals"].get("divergence_bps"), row) for row in hourly]
    divs = [(v, row) for v, row in divs if v is not None]
    if divs:
        vmax, rowmax = max(divs, key=lambda t: t[0])
        vmin, rowmin = min(divs, key=lambda t: t[0])
        vabs, rowabs = max(divs, key=lambda t: abs(t[0]))
        facts["signals"]["divergence_same_hour"] = {
            "max_bps": _r1(vmax), "max_utc": rowmax["utc"],
            "min_bps": _r1(vmin), "min_utc": rowmin["utc"],
            "largest_gap_bps": _r1(vabs), "largest_gap_utc": rowabs["utc"],
            "method": ("(mediane_inter_venues(plus bas horaire) - oracle) * 10000 ; "
                       "negatif = oracle au-dessus du marche (survalorisation retenue) ; "
                       "largest_gap = plus grand ecart en valeur absolue (signe conserve)"),
        }
        # Oracle gap vs window minima (what W2-B says: ~300 bps vs DefiLlama)
        gap = {}
        oracle_min = facts["minima"].get("oracle_chainlink", {}).get("answer")
        for v, m in facts["minima"].items():
            if v in VENUES and oracle_min is not None:
                gap[v] = _r1((oracle_min - m["low"]) * 10000)
        facts["signals"]["oracle_min_minus_venue_min_bps"] = gap

    # Aave: utilisation over the window
    u_rows = [(row["ts"], row["aave"]["utilisation"]) for row in hourly
              if row.get("aave") and row["aave"].get("utilisation") is not None]
    if u_rows:
        u_min = min(u_rows, key=lambda t: t[1])
        u_max = max(u_rows, key=lambda t: t[1])
        facts["signals"]["aave_usdc_utilisation"] = {
            "start": round(u_rows[0][1], 6), "start_utc": iso_utc(u_rows[0][0]),
            "end": round(u_rows[-1][1], 6), "end_utc": iso_utc(u_rows[-1][0]),
            "min": round(u_min[1], 6), "min_utc": iso_utc(u_min[0]),
            "max": round(u_max[1], 6), "max_utc": iso_utc(u_max[0]),
            "n": len(u_rows),
        }

    if blocks_meta:
        facts["blocks"] = blocks_meta
    return facts


def compare_w2b(facts, oracle_points=None):
    """Compare the measured facts with the figures published in W2-B.

    Oracle special case: W2-B sampled every 1000 blocks (~3.35 h). The hourly
    reconstruction is denser, so we check (1) that the value published by W2-B
    is indeed present in the series, and (2) the minimum reached by the dense
    sampling (W3 correction).
    """
    mins = facts["minima"]
    got = {
        "defillama_min": mins.get("defillama", {}).get("low"),
        "bitstamp_min": mins.get("bitstamp", {}).get("low"),
        "okx_min": mins.get("okx", {}).get("low"),
        "binance_min": mins.get("binance", {}).get("low"),
        "dispersion_bps": facts["signals"].get("dispersion_window_bps", {}).get("value_bps"),
    }
    comparison = {}
    for key in ("defillama_min", "bitstamp_min", "okx_min", "binance_min", "dispersion_bps"):
        expected = W2B_EXPECTED[key]
        measured = got.get(key)
        tol = 0.5 if key == "dispersion_bps" else 1e-9
        ok = measured is not None and abs(measured - expected) <= tol
        comparison[key] = {
            "w2b": expected,
            "measured": measured,
            "delta": None if measured is None else round(measured - expected, 8),
            "reproduced": bool(ok),
        }

    # Oracle: is the W2-B value in the series? what is the dense minimum?
    series = [rec for rec in (oracle_points or []) if rec and rec.get("price") is not None]
    w2b_val = W2B_EXPECTED["oracle_min"]
    hit = None
    for rec in series:
        if abs(rec["price"] - w2b_val) < 1e-12:
            hit = rec
            break
    dense = mins.get("oracle_chainlink", {})
    dense_min = dense.get("answer")
    comparison["oracle_min"] = {
        "w2b": w2b_val,
        "w2b_value_present_in_series": hit is not None,
        "w2b_value_utc": (hit or {}).get("updated_at"),
        "dense_min": dense_min,
        "dense_min_utc": dense.get("updated_at"),
        "delta_dense_vs_w2b_bps": (None if dense_min is None
                                   else round((dense_min - w2b_val) * 10000, 2)),
        "reproduced": hit is not None,
        "note": ("Correction W3 : W2-B echantillonnait tous ~1000 blocs (17 points) ; "
                 "l'echantillonnage horaire (97 points) trouve un minimum d'oracle plus bas, "
                 "invisible dans la grille de W2-B (voir research/W3_reconstruction_usdc2023.md)."),
    }
    return comparison


def _r1(x, nd=1):
    return None if x is None else round(x, nd)


# --------------------------------------------------------------------------
# Network (HTTP)
# --------------------------------------------------------------------------

def http_get_json(url, timeout=45, tries=4):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - log the network failure
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def http_post_json(url, payload, timeout=90):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def rpc_single(method, params):
    """Single JSON-RPC call with endpoint failover (W2-B method)."""
    last = None
    for url in RPC_ENDPOINTS:
        for _ in range(2):
            try:
                j = http_post_json(url, {"jsonrpc": "2.0", "id": 1,
                                         "method": method, "params": params})
                if isinstance(j, dict) and "result" in j:
                    return j["result"]
                last = (j or {}).get("error") if isinstance(j, dict) else j
            except Exception as exc:  # noqa: BLE001
                last = exc
            time.sleep(0.4)
    raise RuntimeError(f"rpc {method} failed: {last}")


def rpc_batch(calls, chunk=90, batch_endpoints=None):
    """Batched JSON-RPC calls. calls = [(method, params), ...] -> [result|None].

    Batches only work on blastapi (tested); if the whole batch fails, fall back
    to single calls (drpc included). Never silent: a failed call is None, never
    an invented value.
    """
    endpoints = batch_endpoints or BATCH_ENDPOINTS
    out = []
    for i in range(0, len(calls), chunk):
        part = calls[i:i + chunk]
        payload = [{"jsonrpc": "2.0", "id": j, "method": m, "params": p}
                   for j, (m, p) in enumerate(part)]
        got = False
        for url in endpoints:
            try:
                j = http_post_json(url, payload)
                if isinstance(j, list):
                    by_id = {item.get("id"): item for item in j if isinstance(item, dict)}
                    out.extend([by_id.get(k, {}).get("result") for k in range(len(part))])
                    got = True
                    break
            except Exception:  # noqa: BLE001
                continue
        if not got:
            for (m, p) in part:
                try:
                    out.append(rpc_single(m, p))
                except Exception:  # noqa: BLE001
                    out.append(None)
    return out


# --------------------------------------------------------------------------
# Block <-> timestamp binary search (local, with cache and batched probes)
# --------------------------------------------------------------------------

class BlockIndex:
    """Largest block b such that ts(b) <= target, by local binary search.

    - cache {block: ts} shared by all searches (the probes of one hour serve the
      neighbouring hours);
    - `local_search`: bracketing by an expanding window then interpolated
      bisection — converges even if the block rate drifts;
    - `resolve_hours`: batched refinement (one HTTP request for ~90 probes),
      checked batch by batch after convergence.

    Injectable dependencies (`call`, `batch`) for the offline tests.
    """

    #: (block, ts) pairs measured in fixtures/raw_w2b/aave_usdc_util_mar2023.json
    SEED = ((16794041, 1678406400),    # 2023-03-10 00:00:00Z
            (16820846, 1678730400))    # 2023-03-13 18:00:00Z

    def __init__(self, call=None, batch=None, seed=None):
        self.cache = {}
        self.probes_single = 0
        self.probes_batch = 0
        self._call = call or (lambda method, params: rpc_single(method, params))
        self._batch = batch or (lambda calls: rpc_batch(calls))
        for b, t in (BlockIndex.SEED if seed is None else seed):
            self.cache[b] = t

    # -- probes -------------------------------------------------------------
    def ts(self, block):
        """Block timestamp (cache, else a single call). None on failure."""
        if block in self.cache and self.cache[block] is not None:
            return self.cache[block]
        res = self._call("eth_getBlockByNumber", [hex(block), False])
        self.probes_single += 1
        ts = int(res["timestamp"], 16) if res else None
        self.cache[block] = ts
        return ts

    def probe_many(self, blocks):
        """Probe a list of blocks in batches (cached)."""
        todo, seen = [], set()
        for b in blocks:
            if b in seen:
                continue
            seen.add(b)
            if b not in self.cache or self.cache[b] is None:
                todo.append(b)
        if not todo:
            return
        for i in range(0, len(todo), 90):
            part = todo[i:i + 90]
            res = self._batch([("eth_getBlockByNumber", [hex(b), False]) for b in part])
            self.probes_batch += len(part)
            for b, r in zip(part, res):
                self.cache[b] = int(r["timestamp"], 16) if r else None

    # -- model --------------------------------------------------------------
    def rate(self):
        """Seconds per block, calibrated on the bracketing probes of the cache."""
        pts = sorted((b, t) for b, t in self.cache.items() if t)
        if len(pts) >= 2:
            (b0, t0), (b1, t1) = pts[0], pts[-1]
            if b1 > b0 and t1 > t0:
                return (t1 - t0) / (b1 - b0)
        return 12.0

    def estimate_block(self, target):
        """Linear interpolation estimate between bracketing probes."""
        pts = sorted((t, b) for b, t in self.cache.items() if t)
        lo = None
        hi = None
        for t, b in pts:
            if t <= target:
                lo = (t, b)
            elif hi is None:
                hi = (t, b)
        if lo and hi and hi[1] > lo[1]:
            f = (target - lo[0]) / (hi[0] - lo[0])
            return lo[1] + int(round(f * (hi[1] - lo[1])))
        base = lo or hi or (WINDOW_START_TS, BlockIndex.SEED[0][0])
        return base[1] + int(round((target - base[0]) / self.rate()))

    # -- local binary search ------------------------------------------------
    def local_search(self, target, max_steps=64):
        """Largest block b such that ts(b) <= target (local binary search).

        Bracketing by a one-sided expanding search (step doubling), then
        interpolated bisection. Converges even if the block rate drifts
        strongly between the anchor and the target.
        """
        b = self.estimate_block(target)
        tb = self.ts(b)
        if tb is None:
            raise RuntimeError(f"block probe unavailable around {target}")
        if tb <= target:  # search the upper bound upwards
            lo, hi, step = b, b + 1, 1
            for _ in range(max_steps):
                th = self.ts(hi)
                if th is None:
                    raise RuntimeError(f"block probe unavailable around {target}")
                if th > target:
                    break
                lo, hi = hi, hi + step
                step *= 2
            else:
                raise RuntimeError(f"local window not bracketed for {target}")
        else:             # search the lower bound downwards
            hi, lo, step = b, b - 1, 1
            for _ in range(max_steps):
                tl = self.ts(lo)
                if tl is None:
                    raise RuntimeError(f"block probe unavailable around {target}")
                if tl <= target:
                    break
                hi, lo = lo, lo - step
                step *= 2
            else:
                raise RuntimeError(f"local window not bracketed for {target}")
        while hi - lo > 1:
            tl, th = self.ts(lo), self.ts(hi)
            span = th - tl
            mid = (lo + hi) // 2 if span <= 0 else lo + int(round((target - tl) * (hi - lo) / span))
            mid = max(lo + 1, min(hi - 1, mid))
            if self.ts(mid) <= target:
                lo = mid
            else:
                hi = mid
        return lo

    # -- batched refinement (all hours at once) -----------------------------
    def resolve_hours(self, hours, max_rounds=8):
        """Resolve each hour's block; verify the final bracketing."""
        pending = {h: self.estimate_block(h) for h in hours}
        resolved = {}
        rounds = 0
        for _ in range(max_rounds):
            rounds += 1
            need = []
            for b in pending.values():
                for cand in (b, b + 1):
                    if cand not in self.cache or self.cache[cand] is None:
                        need.append(cand)
            if need:
                self.probe_many(need)
            still = {}
            rate = self.rate()
            for h, b in pending.items():
                tb, tb1 = self.cache.get(b), self.cache.get(b + 1)
                if tb is None or tb1 is None:
                    still[h] = b
                elif tb <= h < tb1:
                    resolved[h] = b
                elif tb > h:
                    still[h] = b - max(1, int(round((tb - h) / rate)))
                else:
                    still[h] = b + max(1, int(round((h - tb1) / rate)))
            pending = still
            if not pending:
                break
        # Fallback: local bisection for the recalcitrant hours
        for h in list(pending):
            resolved[h] = self.local_search(h)
        # Final check: each block must bracket its hour in the cache
        fresh = [b for h, b in resolved.items()
                 if b not in self.cache or self.cache.get(b + 1) is None]
        if fresh:
            self.probe_many([b for h, b in resolved.items() for b in (b, b + 1)])
        for h, b in resolved.items():
            tb, tb1 = self.cache.get(b), self.cache.get(b + 1)
            if tb is None or tb1 is None or not (tb <= h < tb1):
                raise RuntimeError(f"invalid block resolution for ts={h}")
        self.rounds = rounds
        return dict(sorted(resolved.items()))


# --------------------------------------------------------------------------
# Network collectors per source
# --------------------------------------------------------------------------

def fetch_binance():
    url = ("https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h"
           f"&startTime={WINDOW_START_TS * 1000}&endTime={WINDOW_END_TS * 1000}&limit=1000")
    return parse_binance_klines(http_get_json(url))


def fetch_okx():
    base = "https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1H"
    pts, after, seen = [], (WINDOW_END_TS + STEP_S) * 1000, set()
    for _ in range(10):
        payload = http_get_json(f"{base}&after={after}&limit=100")
        rows = parse_okx_candles(payload.get("data") or [])
        rows = [p for p in rows if p["ts"] not in seen]
        if not rows:
            break
        pts.extend(rows)
        seen.update(p["ts"] for p in rows)
        oldest = min(p["ts"] for p in rows)
        if oldest <= WINDOW_START_TS:
            break
        after = oldest * 1000
    return sorted(pts, key=lambda p: p["ts"])


def fetch_bitstamp():
    url = ("https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000"
           f"&start={WINDOW_START_TS}&end={WINDOW_END_TS}")
    payload = http_get_json(url)
    rows = (payload.get("data") or {}).get("ohlc") or []
    return parse_bitstamp_ohlc(rows)


def fetch_defillama():
    url = (f"https://coins.llama.fi/chart/{LLAMA_USDC_COIN}"
           f"?start={WINDOW_START_TS}&span=97&period=1h")
    return parse_llama_chart(http_get_json(url))


def fetch_chainlink(blocks_by_hour):
    """latestRoundData() at each hourly block -> {hour_ts: measurement}."""
    hours = sorted(blocks_by_hour)
    calls = [("eth_call", [{"to": CHAINLINK_USDC_USD, "data": SEL_LATEST_ROUND_DATA},
                           hex(blocks_by_hour[h])]) for h in hours]
    results = rpc_batch(calls)
    out = {}
    for h, res in zip(hours, results):
        if not res:
            out[h] = None
            continue
        d = decode_latest_round_data(res)
        out[h] = {
            "price": round(d["answer"], 8),
            "roundId": d["roundId"],
            "updated_at": iso_utc(d["updatedAt"]),
            "updatedAt": d["updatedAt"],
            "block": blocks_by_hour[h],
            "sample_ts": h,
            "source": "network",
        }
    return out


def sel_balance_of(holder):
    """ERC20 balanceOf(address) calldata = 0x70a08231 + address padded to 32 bytes."""
    return SEL_BALANCE_OF + holder[2:].lower().zfill(64)


def fetch_aave(blocks_by_hour):
    """totalSupply(aEthUSDC) and balanceOf(USDC) at each hourly block."""
    hours = sorted(blocks_by_hour)
    calls, meta = [], []
    for h in hours:
        b = hex(blocks_by_hour[h])
        calls.append(("eth_call", [{"to": AAVE_A_USDC, "data": SEL_TOTAL_SUPPLY}, b]))
        meta.append((h, "supply"))
        calls.append(("eth_call", [{"to": USDC_ETHEREUM,
                                    "data": sel_balance_of(AAVE_A_USDC)}, b]))
        meta.append((h, "cash"))
    results = rpc_batch(calls)
    acc = {}
    for (h, kind), res in zip(meta, results):
        rec = acc.setdefault(h, {})
        try:
            val = decode_uint256(res)
        except ValueError:
            val = None
        if kind == "supply":
            rec["supply_raw"] = val
        else:
            rec["cash_raw"] = val
    out = {}
    for h, rec in acc.items():
        if rec.get("supply_raw") is None or rec.get("cash_raw") is None:
            out[h] = None
            continue
        row = aave_row_from_raw(rec["supply_raw"], rec["cash_raw"])
        row.update({"block": blocks_by_hour[h], "sample_ts": h, "source": "network"})
        out[h] = row
    return out


# --------------------------------------------------------------------------
# Cache mode (offline): re-read the raw JSON of fixtures/raw_w2b/
# --------------------------------------------------------------------------

def load_cache_venues(raw_dir):
    """Venues from raw_w2b: venues_usdc_mar2023.json + defillama_chart_usdc.json."""
    series = {}
    path = os.path.join(raw_dir, "venues_usdc_mar2023.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    series["binance"] = filter_window(parse_binance_klines(raw.get("binance_USDCUSDT_klines")))
    series["bitstamp"] = filter_window(parse_bitstamp_ohlc(
        ((raw.get("bitstamp_usdcusd") or {}).get("data") or {}).get("ohlc") or []))
    series["okx"] = filter_window(parse_okx_candles(
        (raw.get("okx_usdcusdt") or {}).get("data") or []))
    llama_path = os.path.join(raw_dir, "defillama_chart_usdc.json")
    with open(llama_path, "r", encoding="utf-8") as fh:
        series["defillama"] = filter_window(parse_llama_chart(json.load(fh)))
    return series


def load_cache_oracle(raw_dir):
    """Oracle from raw_w2b/chainlink_usdcusd_mar2023.json (probe ~3.35 h)."""
    path = os.path.join(raw_dir, "chainlink_usdcusd_mar2023.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    out = {}
    for rec in raw:
        if not rec or rec.get("answer") is None:
            continue
        out[rec["block_ts"]] = {
            "price": round(rec["answer"], 8),
            "roundId": rec["roundId"],
            "updated_at": iso_utc(rec["updatedAt"]),
            "updatedAt": rec["updatedAt"],
            "block": int(rec["block"], 16) if isinstance(rec["block"], str) else rec["block"],
            "sample_ts": rec["block_ts"],
            "source": "cache",
        }
    return out


def load_cache_aave(raw_dir):
    """Aave from raw_w2b/aave_usdc_util_mar2023.json (6 h step)."""
    path = os.path.join(raw_dir, "aave_usdc_util_mar2023.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    out = {}
    for rec in raw:
        ts = parse_iso_utc(rec["utc"])
        out[ts] = {
            "supply_usdc": rec["supply"],
            "cash_usdc": rec["cash"],
            "utilisation": rec["U"],
            "block": rec["block"],
            "sample_ts": ts,
            "source": "cache",
        }
    return out


def align_series_to_hours(hours, sparse):
    """Carry each point measurement forward onto the current hour.

    For hour h, keep the last measurement whose timestamp is <= h
    (propagation), marking `aligned` = (measurement within hour h).
    `sparse` may be a dict {ts: measurement} or a list of measurements with 'sample_ts'.
    """
    if isinstance(sparse, dict):
        items = sorted((ts, rec) for ts, rec in sparse.items() if rec)
    else:
        items = sorted((rec["sample_ts"], rec) for rec in sparse if rec)
    out = {}
    cursor = -1
    for h in sorted(hours):
        while cursor + 1 < len(items) and items[cursor + 1][0] <= h:
            cursor += 1
        if cursor < 0:
            continue
        ts, rec = items[cursor]
        rec = dict(rec)
        rec["aligned"] = ts == h
        rec["sample_utc"] = iso_utc(ts)
        out[h] = rec
    return out


# Evidence assembly
# Evidence assembly
# --------------------------------------------------------------------------

def build_evidence(from_cache=False, raw_dir=RAW_W2B, out_path=DEFAULT_OUT,
                   verbose=True):
    """Build the complete evidence dictionary (network, or offline cache)."""
    hours = list(range(WINDOW_START_TS, WINDOW_END_TS + 1, STEP_S))  # 97 points
    say = (lambda m: print(m, flush=True)) if verbose else (lambda m: None)

    sources = {}
    blocks_meta = None

    if from_cache:
        mode = "from-cache"
        say("[cache] reading the raw JSON of fixtures/raw_w2b/ ...")
        venues = load_cache_venues(raw_dir)
        oracle_sparse = load_cache_oracle(raw_dir)
        aave_sparse = load_cache_aave(raw_dir)
        oracle_by_hour = align_series_to_hours(hours, oracle_sparse)
        aave_by_hour = align_series_to_hours(hours, aave_sparse)
        for v in VENUES:
            sources[v] = {"mode": "cache", "points": len(venues.get(v) or []),
                          "files": ["fixtures/raw_w2b/venues_usdc_mar2023.json",
                                    "fixtures/raw_w2b/defillama_chart_usdc.json"]}
        sources["chainlink"] = {"mode": "cache", "points": len(oracle_sparse),
                                "file": "fixtures/raw_w2b/chainlink_usdcusd_mar2023.json"}
        sources["aave"] = {"mode": "cache", "points": len(aave_sparse),
                           "file": "fixtures/raw_w2b/aave_usdc_util_mar2023.json"}
    else:
        mode = "network"
        fetchers = {
            "binance": (fetch_binance, "https://api.binance.com/api/v3/klines (USDCUSDT, 1h)"),
            "okx": (fetch_okx, "https://www.okx.com/api/v5/market/history-candles (USDC-USDT, 1H)"),
            "bitstamp": (fetch_bitstamp, "https://www.bitstamp.net/api/v2/ohlc/usdcusd (3600 s)"),
            "defillama": (fetch_defillama, "https://coins.llama.fi/chart (USDC ETH, period=1h)"),
        }
        venues = {}
        for name in VENUES:
            fn, endpoint = fetchers[name]
            try:
                pts = filter_window(fn())
                say(f"[network] {name}: {len(pts)} points")
                sources[name] = {"mode": "network", "endpoint": endpoint, "points": len(pts)}
            except Exception as exc:  # noqa: BLE001 - explicit cache fallback
                say(f"[network] {name} FAILED ({exc}) -> raw_w2b/ cache fallback")
                cache = load_cache_venues(raw_dir)
                pts = filter_window(cache.get(name) or [])
                venues[name] = pts
                sources[name] = {"mode": "cache-fallback", "endpoint": endpoint,
                                 "points": len(pts), "error": str(exc)}
                continue
            venues[name] = pts

        say("[network] block <-> timestamp binary search (97 hours)...")
        idx = BlockIndex()
        block_by_hour = idx.resolve_hours(hours)
        blocks_meta = {
            "method": "recherche dichotomique locale (fenêtre interpolée) + affinage par lots JSON-RPC",
            "rounds": getattr(idx, "rounds", None),
            "probes_single": idx.probes_single,
            "probes_batch": idx.probes_batch,
            "endpoints_single": RPC_ENDPOINTS,
            "endpoints_batch": BATCH_ENDPOINTS,
            "seeds": [{"block": b, "ts": t, "utc": iso_utc(t)} for b, t in BlockIndex.SEED],
            "verified": "ts(bloc) <= heure < ts(bloc+1) pour chaque heure",
        }
        say(f"[network] blocks resolved (probes: {idx.probes_single} single, "
            f"{idx.probes_batch} batched)")
        say("[network] Chainlink latestRoundData() ...")
        oracle_net = fetch_chainlink(block_by_hour)
        oracle_sparse = {h: r for h, r in oracle_net.items() if r}
        oracle_by_hour = oracle_sparse
        sources["chainlink"] = {"mode": "network", "endpoint": "eth_call latestRoundData()",
                                "contract": CHAINLINK_USDC_USD, "points": len(oracle_sparse)}
        say("[network] Aave V3 USDC (supply / cash) ...")
        aave_net = fetch_aave(block_by_hour)
        aave_sparse = {h: r for h, r in aave_net.items() if r}
        aave_by_hour = aave_sparse
        sources["aave"] = {"mode": "network",
                           "endpoint": "eth_call aEthUSDC.totalSupply() + USDC.balanceOf(aEthUSDC)",
                           "pool": AAVE_V3_POOL, "a_token": AAVE_A_USDC, "points": len(aave_sparse)}

    say("[output] hourly assembly + derived signals ...")
    hourly = assemble_hourly(hours, venues, oracle_by_hour, aave_by_hour)
    facts = compute_facts(hourly, venues, list(oracle_sparse.values()), blocks_meta)
    comparison = compare_w2b(facts, list(oracle_sparse.values()))

    document = {
        "schema": "orvyren.evidence.episode-usdc-2023-03.v1",
        "case": "usdc-2023-03",
        "episode": "Decrochage USDC/USD (exposition SVB), 10-14 mars 2023",
        "generated_at": iso_utc(int(time.time())),
        "generated_by": "scripts/reconstruct_usdc2023_episode.py",
        "mode": mode,
        "window": {
            "start_utc": iso_utc(WINDOW_START_TS),
            "end_utc": iso_utc(WINDOW_END_TS),
            "step_s": STEP_S,
            "n_points": len(hours),
        },
        "sources": sources,
        "facts": facts,
        "w2b_comparison": comparison,
        "hourly": hourly,
        "notes": [
            "Prix horaire « stress » = plus bas de l'heure par venue (low), plus haut, "
            "dernier et volume inclus quand la source les publie.",
            "Decote D(t) = 1 - prix (peg_ref = 1,00 USD), en points de base.",
            "Dispersion sigma_disp = (max - min)/max des plus bas horaires inter-venues "
            "(convention W2-B ; reproduit les ~870 bps).",
            "Divergence delta = prix_marche - oracle Chainlink, en points de base "
            "(positif = oracle au-dessus du marche).",
            "Aucune valeur inventee : chaque mesure vient de l'API appelée ou du fichier "
            "de cache cite en mode from-cache.",
        ],
    }
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(document, fh, indent=1, sort_keys=False, ensure_ascii=False)
            fh.write("\n")
        say(f"[output] written: {out_path}")
    return document


def print_summary(document):
    facts = document["facts"]
    mins = facts["minima"]
    say = print
    say("")
    say("=== Key facts (reconstruction vs W2-B) ===")
    for key, comp in document["w2b_comparison"].items():
        if key == "oracle_min":
            mark = "OK " if comp["reproduced"] else "GAP"
            say(f"  [{mark}] oracle_min       w2b={comp['w2b']} present in the series="
                f"{comp['w2b_value_present_in_series']} ({comp['w2b_value_utc']}) ; "
                f"dense min={comp['dense_min']} ({comp['dense_min_utc']})")
            continue
        mark = "OK " if comp["reproduced"] else "GAP"
        say(f"  [{mark}] {key:16s} w2b={comp['w2b']}  measured={comp['measured']}")
    disp = facts["signals"].get("dispersion_window_bps")
    if disp:
        say(f"  window dispersion : {disp['value_bps']} bps "
            f"({disp['min_venue']} {mins[disp['min_venue']]['low']} -> "
            f"{disp['max_venue']} {mins[disp['max_venue']]['low']})")
    div = facts["signals"].get("divergence_same_hour")
    if div:
        say(f"  same-hour divergence : max {div['max_bps']} bps @ {div['max_utc']}")
    gap = facts["signals"].get("oracle_min_minus_venue_min_bps")
    if gap:
        say(f"  oracle_min - venue min gap (bps) : {gap}")
    u = facts["signals"].get("aave_usdc_utilisation")
    if u:
        say(f"  Aave USDC utilisation : {u['start']} -> {u['end']} "
            f"(min {u['min']} @ {u['min_utc']})")
    say("")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from-cache", action="store_true",
                        help="rebuild offline from fixtures/raw_w2b/")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output JSON file")
    parser.add_argument("--raw-dir", default=RAW_W2B,
                        help="directory of the raw JSON files (cache mode)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    document = build_evidence(from_cache=args.from_cache, raw_dir=args.raw_dir,
                              out_path=args.out, verbose=not args.quiet)
    if not args.quiet:
        print_summary(document)
    n_ok = sum(1 for c in document["w2b_comparison"].values() if c["reproduced"])
    print(f"W2-B facts reproduced: {n_ok}/{len(document['w2b_comparison'])}")
    return 0 if n_ok == len(document["w2b_comparison"]) else 1


if __name__ == "__main__":
    sys.exit(main())
