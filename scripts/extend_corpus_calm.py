#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — L1.5: CALM windows (DEV/EVAL) — collection and archiving.

CALM windows serve as **controls** (the pipeline must NOT fire when nothing is
happening). Plan B7 designates them (CALM 2022-2023 for DEV, CALM 2025-2026 for
EVAL) — the exact bounds remain **to be frozen in G1**: the values below are the
**proposal** executed here, marked as such in the artefacts.

Collection per window (reuses the main collector's source contracts,
``collect_corpus.py``):
- DeFiLlama ``coins.llama.fi/chart`` (hourly USDC price, one batch request);
- Bitstamp hourly OHLC USDC/USD (public API, no key);
- Binance hourly USDCUSDT klines (independent source).

Writes under ``corpus/raw/<source>/..._<window>.json``, the unified
``corpus/series/calm_windows.json`` and ``corpus/calm_manifest.json``.
``--offline`` rebuilds the outputs from the raw cache (no network).

Usage::

    python scripts/extend_corpus_calm.py            # collection (network) + writes
    python scripts/extend_corpus_calm.py --offline  # rebuild from corpus/raw
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import collect_corpus as cc  # noqa: E402  (source contracts reused verbatim)

#: B7 proposal (to be frozen in G1) — bounds executed here.
CALM_WINDOWS = {
    "calm_a": ("2023-01-16T00:00:00Z", "2023-01-23T00:00:00Z"),  # 2022-2023 season
    "calm_b": ("2025-09-15T00:00:00Z", "2025-09-22T00:00:00Z"),  # 2025-2026 season
}

MIN_POINTS = 160  # 7 hourly days -> tolerance for marginal losses


def _parse(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _fetch_json(url: str, retries: int = 3, pause: float = 1.5):
    """Light urllib fetch (collect_corpus.fetch_json contract: (data, retrieved))."""
    if urllib.parse.urlsplit(str(url)).scheme not in ("http", "https"):
        raise ValueError("unsupported HTTP(S) URL: %r" % (url,))
    last = None
    for _ in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "orvyren-core/1"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload, dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        except Exception as exc:  # noqa: BLE001 - bounded retries then fail closed
            last = exc
            time.sleep(pause)
    raise RuntimeError("E_FETCH: %s (%s)" % (url, last))


def _cached(sub: str, name: str, build):
    """Cache-first write like collect_corpus.cached_or_fetch (offline replay)."""
    path = os.path.join(REPO_ROOT, "corpus", "raw", sub, name)
    force = os.environ.get("ORVYREN_CALM_FORCE") == "1"
    if os.path.exists(path) and not force:
        with open(path, "r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if cached:  # an empty cache is treated as a miss (measured: Binance gap)
            return cached, True
    rows = build()
    if rows:  # never persist an empty result (it would poison later runs)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=1, sort_keys=True)
            handle.write("\n")
    return rows, False


def collect_defillama(label: str, start: dt.datetime, end: dt.datetime):
    hours = int((end - start).total_seconds() // 3600)

    def build():
        ts = int(start.timestamp())
        url = ("https://coins.llama.fi/chart/%s?start=%d&span=%d&period=1h"
               % (cc.USDC_TOKEN, ts, hours))
        data, retrieved = _fetch_json(url)
        coins = data.get("coins") or {}
        entry = next(iter(coins.values())) if coins else {}
        out = []
        for point in entry.get("prices") or []:
            out.append({"timestamp_utc": dt.datetime.fromtimestamp(
                int(point["timestamp"]), dt.timezone.utc).isoformat(timespec="seconds"),
                "price": point.get("price"), "retrieved_at": retrieved})
        return out

    return _cached("defillama", "usdc_prices_%s.json" % label, build)


def collect_bitstamp(label: str, start: dt.datetime, end: dt.datetime):
    def build():
        out, cursor = [], int(start.timestamp())
        while cursor <= int(end.timestamp()):
            url = ("https://www.bitstamp.net/api/v2/ohlc/usdcusd/"
                   "?step=3600&limit=1000&start=%d" % cursor)
            data, retrieved = _fetch_json(url)
            batch = ((data.get("data") or {}).get("ohlc") or [])
            if not batch:
                break
            for candle in batch:
                ts = int(candle["timestamp"])
                if ts > int(end.timestamp()):
                    continue
                out.append({"timestamp_utc": dt.datetime.fromtimestamp(
                    ts, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(candle["close"]), "low": float(candle["low"]),
                    "high": float(candle["high"]), "volume": float(candle["volume"]),
                    "retrieved_at": retrieved})
            last = int(batch[-1]["timestamp"])
            if last <= cursor or last >= int(end.timestamp()):
                break
            cursor = last + 3600
            time.sleep(0.7)
        return out

    return _cached("bitstamp", "usdcusd_ohlc_%s.json" % label, build)


def collect_binance(label: str, start: dt.datetime, end: dt.datetime):
    def build():
        out = []
        cursor = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        while cursor < end_ms:
            url = ("https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h"
                   "&startTime=%d&endTime=%d&limit=1000" % (cursor, end_ms))
            data, retrieved = _fetch_json(url)
            if not isinstance(data, list) or not data:
                break
            for k in data:
                out.append({"timestamp_utc": dt.datetime.fromtimestamp(
                    k[0] / 1000, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(k[4]), "low": float(k[3]), "high": float(k[2]),
                    "volume": float(k[5]), "retrieved_at": retrieved})
            cursor = int(data[-1][0]) + 3600 * 1000
            if len(data) < 1000:
                break
            time.sleep(0.5)
        return out

    return _cached("binance", "usdcusdt_klines_%s.json" % label, build)


def _check_bounds(label: str, rows, start: dt.datetime, end: dt.datetime):
    outside = [r for r in rows if not (start - dt.timedelta(hours=2)
                                       <= _parse(r["timestamp_utc"])
                                       <= end + dt.timedelta(hours=2))]
    if outside:
        raise SystemExit("E_WINDOW: %s outside window (%d rows)" % (label, len(outside)))
    if len(rows) < MIN_POINTS:
        raise SystemExit("E_WINDOW: %s too short (%d < %d points)"
                         % (label, len(rows), MIN_POINTS))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="extend_corpus_calm.py")
    parser.add_argument("--offline", action="store_true",
                        help="rebuild from corpus/raw (no network)")
    args = parser.parse_args(argv)
    if args.offline:
        os.environ["ORVYREN_CALM_FORCE"] = "0"

    unified = {"schema": "orvyren/calm-windows/v1",
               "note": "Bornes = PROPOSITION B7, à figer en G1 (FREEZE_V2 §limites). "
                       "Fenêtres de contrôle DEV (2022-23) et EVAL (2025-26).",
               "windows": {}}
    manifest_entries = []
    for label, (start_iso, end_iso) in CALM_WINDOWS.items():
        start, end = _parse(start_iso), _parse(end_iso)
        sources = {}
        unavailable = {}
        for name, collector in (("defillama", collect_defillama),
                                ("bitstamp", collect_bitstamp),
                                ("binance", collect_binance)):
            rows, reused = collector(label, start, end)
            if not rows:
                if name in ("defillama", "bitstamp"):
                    raise SystemExit("E_WINDOW: %s/%s empty (mandatory source)"
                                     % (label, name))
                # optional source: declared unavailable, never invented
                unavailable[name] = {
                    "status": "unavailable_measured",
                    "note": "mesuré le 2026-10-16 : api.binance.com et "
                            "data-api.binance.vision, intervalles 1h et 1d → "
                            "vides sur cette période (trou du symbole USDCUSDT)",
                }
                continue
            _check_bounds("%s/%s" % (label, name), rows, start, end)
            # strict [start, end] for the published series (DeFiLlama emits a
            # point at start-1s; raw cache keeps the untouched response)
            raw_count = len(rows)
            rows = [r for r in rows if start <= _parse(r["timestamp_utc"]) <= end]
            sources[name] = rows
            manifest_entries.append({
                "source": name, "window": label, "records": len(rows),
                "raw_records": raw_count,
                "status": "ok",
                "file": "corpus/raw/%s/%s" % (name, {
                    "defillama": "usdc_prices_%s.json" % label,
                    "bitstamp": "usdcusd_ohlc_%s.json" % label,
                    "binance": "usdcusdt_klines_%s.json" % label}[name]),
                "from_cache": reused,
                "bounds": [start_iso, end_iso],
                "note": "proposition B7 (à figer en G1)",
            })
        for name, info in unavailable.items():
            manifest_entries.append({"source": name, "window": label,
                                     "records": 0, **info,
                                     "bounds": [start_iso, end_iso],
                                     "note": info["note"] + " ; proposition B7 (à figer en G1)"})
        if len(sources) < 2:
            raise SystemExit("E_WINDOW: %s — fewer than 2 real sources" % label)
        unified["windows"][label] = {"start": start_iso, "end": end_iso,
                                     "sources": {name: {"records": len(rows),
                                                        "observations": rows}
                                                 for name, rows in sources.items()},
                                     "unavailable": unavailable}

    series_path = os.path.join(REPO_ROOT, "corpus", "series", "calm_windows.json")
    os.makedirs(os.path.dirname(series_path), exist_ok=True)
    with open(series_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(unified, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")

    manifest_path = os.path.join(REPO_ROOT, "corpus", "calm_manifest.json")
    payload = {"schema": "orvyren/corpus-calm-manifest/v1",
               "note": "Manifeste SÉPARÉ (le manifeste principal est rebâti par "
                       "collect_corpus.py — ne pas y écrire depuis ce script).",
               "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "windows": CALM_WINDOWS, "sources": manifest_entries}
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")

    for label, window in unified["windows"].items():
        summary = ", ".join("%s=%d" % (name, source["records"])
                            for name, source in sorted(window["sources"].items()))
        print("  [ok] %s (%s → %s) : %s" % (label, window["start"][:10],
                                            window["end"][:10], summary))
    print("  [ok] unified series : corpus/series/calm_windows.json")
    print("  [ok] manifest       : corpus/calm_manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
