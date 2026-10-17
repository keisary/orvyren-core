#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — corpus collector (pilot case USDC / SVB, March 2023).

Collects, timestamps and archives the observations required by the case:
  1. DeFiLlama  — USDC price (aggregator) hour by hour, one request per timestamp
                  (`prices/historical` endpoint: the only one that answers for
                   history; `chart` returns 0 points — finding of 2026-10-14).
  2. Bitstamp   — hourly USDC/USD OHLC (independent exchange source).
  3. Binance    — hourly USDC/USDT klines (second exchange source).
  4. DeFiLlama  — USDC circulating supply per chain (daily, aggregate + Ethereum).
  5. Documentary reference — Circle statement of 12-13/03/2023 (metadata, not scraped).

Outputs (under corpus/):
  raw/<source>/*.json   timestamped raw responses
  manifest.json         source manifest: url, collection time, record count, limits
  usdc_observations.csv unified observations (timestamp_utc, venue, type, value)
  README.md             provenance and limits note

Window contract: every series is re-checked against its declared bounds
before writing (`validate_archived_windows`); an out-of-window row makes the
collection fail (exit 2) instead of silently entering the archive.
This guard exists because a cache predating the window filter was once reused
and shipped 855 out-of-window Bitstamp rows (finding of 2026-10-14).

Usage:
  python collect_corpus.py                # full collection (≈ 4 min, network required)
  python collect_corpus.py --offline      # replays the archived corpus only
Dependencies: stdlib only.
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(BASE, "corpus")
RAW = os.path.join(CORPUS, "raw")
UA = {"user-agent": "curl/8.5.0", "accept": "application/json"}

# Main window: USDC depeg (SVB) — 9 to 15 March 2023, hourly step.
MAIN_START = dt.datetime(2023, 3, 9, 0, 0, tzinfo=dt.timezone.utc)
MAIN_END = dt.datetime(2023, 3, 15, 0, 0, tzinfo=dt.timezone.utc)
# Control window (outside the crisis): 15-18 February 2023.
CTRL_START = dt.datetime(2023, 2, 15, 0, 0, tzinfo=dt.timezone.utc)
CTRL_END = dt.datetime(2023, 2, 18, 0, 0, tzinfo=dt.timezone.utc)

USDC_TOKEN = "ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
CIRCLE_STATEMENT = {
    "source": "Circle",
    "title": "USDC reserves and Silicon Valley Bank — statement",
    "url": "https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes",
    "publication_date": "2023-03-12",
    "usage": "Primary issuer source: information announced on a given date (documentary fact).",
    "limit": "An issuer statement does not settle risk hypotheses on its own; corroborate it.",
    "note": "Manually recorded metadata: the statement text must be read and quoted, not scraped automatically.",
}


def fetch_json(url, retries=3, pause=1.5):
    """GET JSON with retries; returns (data, collection_time_iso) or raises."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as fh:
                raw = fh.read()
            return json.loads(raw.decode("utf-8", "replace")), dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(pause * (attempt + 1))
    raise RuntimeError(f"failed after {retries} attempts: {url} ({last})")


FORCE = False  # set to True by --force: ignore the cache and re-collect everything


def cached_or_fetch(sub, name, url, builder):
    """Collection idempotence: if the raw file already exists and --force is not
    requested, re-read it instead of repeating the network calls (expensive: ~1 s/call).
    `builder()` must return the list of records built from the response."""
    path = os.path.join(RAW, sub, name)
    if os.path.exists(path) and not FORCE:
        rows = json.load(open(path, encoding="utf-8"))
        if rows:  # an empty cache (failed collection) must never be reused
            print(f"  {sub}/{name}: {len(rows)} records (reused from cache)")
            return rows, True
        print(f"  {sub}/{name}: empty cache → new network attempt")
    rows = builder()
    save_raw(sub, name, rows)
    print(f"  {sub}/{name}: {len(rows)} records (collected)")
    return rows, False


def ensure_dirs():
    for sub in ("defillama", "bitstamp", "binance", "circle", "supply"):
        os.makedirs(os.path.join(RAW, sub), exist_ok=True)


def save_raw(sub, name, payload):
    path = os.path.join(RAW, sub, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    return os.path.relpath(path, BASE)


def hours(start, end):
    t, out = start, []
    while t <= end:
        out.append(int(t.timestamp()))
        t += dt.timedelta(hours=1)
    return out


def parse_iso(value):
    """Parse the ISO-8601 strings this module writes (``Z`` suffix accepted)."""
    text = str(value).strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    return dt.datetime.fromisoformat(text)


def validate_archived_windows(prices, bitstamp, binance, supply):
    """Refuse a collection whose rows fall outside their declared windows.

    Every series is re-checked against its declared bounds *after* collection,
    before anything is written: a cache that predates the window filter (the
    855-row Bitstamp incident of 2026-10-14) must fail loudly here instead of
    slipping into the archive. Returns the list of violations (empty = OK).
    """
    problems = []

    def check(label, rows, start, end, field="timestamp_utc"):
        for row in rows:
            when = parse_iso(row[field])
            if not (start <= when <= end):
                problems.append(
                    "%s: %s outside [%s, %s]"
                    % (label, row[field], start.isoformat(), end.isoformat()))
                return

    for label, window in (("main", (MAIN_START, MAIN_END)), ("control", (CTRL_START, CTRL_END))):
        check("defillama %s" % label, prices.get(label, []), *window)
    check("bitstamp main", bitstamp, MAIN_START, MAIN_END)
    check("binance main", binance, MAIN_START, MAIN_END)
    supply_start = MAIN_START - dt.timedelta(days=15)
    supply_end = MAIN_END + dt.timedelta(days=15)
    for label, rows in supply.items():
        check("supply %s" % label, rows, supply_start, supply_end, field="date_utc")
    return problems


def collect_defillama_prices(manifest, sleep=1.1):
    """Hourly USDC price via the prices/historical endpoint (one request per point)."""
    series = {}
    for label, (start, end) in (("main", (MAIN_START, MAIN_END)), ("control", (CTRL_START, CTRL_END))):
        def build(start=start, end=end):
            out = []
            for ts in hours(start, end):
                url = f"https://coins.llama.fi/prices/historical/{ts}/{USDC_TOKEN}"
                data, retrieved = fetch_json(url)
                entry = data.get("coins", {}).get(USDC_TOKEN, {})
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds"),
                    "price": entry.get("price"),
                    "confidence": entry.get("confidence"),
                    "retrieved_at": retrieved,
                })
                time.sleep(sleep)
            return out
        rows, reused = cached_or_fetch("defillama", f"usdc_prices_{label}.json", None, build)
        series[label] = rows
        manifest.append({
            "source": "DeFiLlama", "endpoint": "coins.llama.fi/prices/historical/{ts}/{coin}",
            "window": label, "records": len(rows),
            "file": f"corpus/raw/defillama/usdc_prices_{label}.json", "from_cache": reused,
            "limits": "Aggregator: multi-venue median price; lag and coverage must be checked; public quota not guaranteed (see API docs).",
        })
    return series


def collect_bitstamp(manifest):
    """Hourly USDC/USD OHLC on Bitstamp, from 9 March 2023 (public API, no key)."""
    def build():
        out, start = [], int(MAIN_START.timestamp())
        while True:
            url = f"https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start={start}"
            data, retrieved = fetch_json(url)
            batch = data.get("data", {}).get("ohlc", [])
            if not batch:
                break
            for candle in batch:
                ts = int(candle["timestamp"])
                if ts > int(MAIN_END.timestamp()):
                    continue
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(candle["close"]), "low": float(candle["low"]),
                    "high": float(candle["high"]), "volume": float(candle["volume"]),
                    "retrieved_at": retrieved,
                })
            last = int(batch[-1]["timestamp"])
            if last <= start or last >= int(MAIN_END.timestamp()):
                break
            start = last + 3600
            time.sleep(0.7)
        return out
    rows, reused = cached_or_fetch("bitstamp", "usdcusd_ohlc.json", None, build)
    manifest.append({
        "source": "Bitstamp", "endpoint": "www.bitstamp.net/api/v2/ohlc/usdcusd/",
        "window": "main", "records": len(rows), "file": "corpus/raw/bitstamp/usdcusd_ohlc.json",
        "from_cache": reused,
        "limits": "Single marketplace: local depth and spreads; the observed dislocation may be venue-specific.",
    })
    return rows


def collect_binance(manifest):
    """Hourly USDC/USDT klines (exchange source independent of Bitstamp)."""
    def build():
        out = []
        start = int(MAIN_START.timestamp() * 1000)
        end = int(MAIN_END.timestamp() * 1000)
        while start < end:
            url = ("https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h"
                   f"&startTime={start}&endTime={end}&limit=1000")
            data, retrieved = fetch_json(url)
            if not isinstance(data, list) or not data:
                break
            for k in data:
                out.append({
                    "timestamp_utc": dt.datetime.fromtimestamp(k[0] / 1000, dt.timezone.utc).isoformat(timespec="seconds"),
                    "close": float(k[4]), "low": float(k[3]), "high": float(k[2]), "volume": float(k[5]),
                    "retrieved_at": retrieved,
                })
            start = int(data[-1][0]) + 3600 * 1000
            if len(data) < 1000:
                break
            time.sleep(0.5)
        return out
    rows, reused = cached_or_fetch("binance", "usdcusdt_klines.json", None, build)
    manifest.append({
        "source": "Binance", "endpoint": "api.binance.com/api/v3/klines", "window": "main",
        "records": len(rows), "file": "corpus/raw/binance/usdcusdt_klines.json", "from_cache": reused,
        "limits": "USDC/USDT market: measures one pair against another stablecoin, hence a relative dislocation, not an absolute one.",
    })
    return rows


def collect_supply(manifest):
    """USDC circulating supply (daily) — aggregate and Ethereum."""
    out = {}
    # Wider window: the crisis ± 15 days, so a nearby calm period can be compared.
    lo = (MAIN_START - dt.timedelta(days=15)).timestamp()
    hi = (MAIN_END + dt.timedelta(days=15)).timestamp()

    def parse_ts(value):
        """The endpoint returns the date in three possible forms:
        numeric epoch (int/float), epoch encoded as a string ("1678320000"), or ISO ("2023-03-09").
        Finding of 2026-10-14: stablecoincharts returns a STRING containing the epoch."""
        if isinstance(value, (int, float)):
            return dt.datetime.fromtimestamp(float(value), dt.timezone.utc)
        text = str(value).strip()
        if text.isdigit():
            return dt.datetime.fromtimestamp(float(text), dt.timezone.utc)
        text = text.replace("Z", "+00:00")
        if "T" not in text and len(text) == 10:
            text += "T00:00:00+00:00"
        return dt.datetime.fromisoformat(text)

    for label, url in (
        ("aggregate", "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2"),
        ("ethereum", "https://stablecoins.llama.fi/stablecoincharts/Ethereum?stablecoin=2"),
    ):
        def build(url=url):
            data, retrieved = fetch_json(url)
            rows = []
            for point in (data if isinstance(data, list) else []):
                raw_date = point.get("date")
                if raw_date is None:
                    continue
                try:
                    when = parse_ts(raw_date)
                except (ValueError, TypeError):
                    continue
                if not (lo <= when.timestamp() <= hi):
                    continue
                usd = (point.get("totalCirculatingUSD") or {}).get("peggedUSD")
                if usd is None:
                    usd = (point.get("totalCirculating") or {}).get("peggedUSD")
                rows.append({
                    "date_utc": when.isoformat(timespec="seconds"),
                    "circulating_usd": usd,
                    "retrieved_at": retrieved,
                })
            return rows
        try:
            rows, reused = cached_or_fetch("supply", f"usdc_circulating_{label}.json", url, build)
        except Exception as exc:  # source unavailable: record it, never invent anything
            print(f"  supply {label}: FAILED ({exc})")
            manifest.append({"source": "DeFiLlama", "endpoint": url, "window": "crisis ±15 d",
                             "records": 0, "file": None, "from_cache": False,
                             "limits": f"Unavailable at collection time: {exc}"})
            continue
        out[label] = rows
        manifest.append({"source": "DeFiLlama", "endpoint": url, "window": "crisis ±15 d",
                         "records": len(rows),
                         "file": f"corpus/raw/supply/usdc_circulating_{label}.json",
                         "from_cache": reused,
                         "limits": "Daily series, coarse granularity; covers observable on-chain supply only."})
    save_raw("circle", "circle_statement_reference.json", CIRCLE_STATEMENT)
    manifest.append({"source": "Circle", "endpoint": CIRCLE_STATEMENT["url"], "window": "12/03/2023",
                     "records": 1, "file": "corpus/raw/circle/circle_statement_reference.json", "from_cache": False,
                     "limits": CIRCLE_STATEMENT["limit"]})
    return out


def write_csv(prices, bitstamp, binance, supply):
    path = os.path.join(CORPUS, "usdc_observations.csv")
    n = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        # explicit lineterminator: the csv module default is '\r\n', which would
        # make the file depend on the writing style and break the direct
        # sha256sum <-> recorded digest comparison (LF everywhere).
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["timestamp_utc", "venue", "metric", "value", "extra", "retrieved_at"])
        for label, rows in prices.items():
            for r in rows:
                if r["price"] is None:
                    continue
                w.writerow([r["timestamp_utc"], "defillama", "price_usd", r["price"],
                            f"confidence={r['confidence']}", r["retrieved_at"]]); n += 1
        for r in bitstamp:
            w.writerow([r["timestamp_utc"], "bitstamp", "close_usd", r["close"],
                        f"low={r['low']}", r["retrieved_at"]]); n += 1
        for r in binance:
            w.writerow([r["timestamp_utc"], "binance", "close_usdcusdt", r["close"],
                        f"low={r['low']}", r["retrieved_at"]]); n += 1
        for label, rows in supply.items():
            for r in rows:
                if r["circulating_usd"] is None:
                    continue
                w.writerow([r["date_utc"], f"defillama_supply_{label}", "circulating_usd",
                            r["circulating_usd"], "", r["retrieved_at"]]); n += 1
    print(f"  CSV: {n} observations → {os.path.relpath(path, BASE)}")
    return n


def write_readme(manifest, n_obs):
    path = os.path.join(CORPUS, "README.md")
    lines = [
        "# USDC corpus — ORVYREN pilot case (SVB episode, March 2023)",
        "",
        "Reproducible collection: `python collect_corpus.py` (network) or `--offline` (archive replay).",
        f"Last collection: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        f"Unified observations: **{n_obs}** (see `usdc_observations.csv`).",
        "",
        "## Windows",
        f"- main (depeg): {MAIN_START.date()} → {MAIN_END.date()}, hourly step;",
        f"- control (outside the crisis): {CTRL_START.date()} → {CTRL_END.date()}, hourly step.",
        "",
        "## Sources and limits",
        "",
        "| Source | Endpoint | Records | Limit to display |",
        "|---|---|---|---|",
    ]
    for m in manifest:
        lines.append(f"| {m['source']} | `{m['endpoint']}` | {m['records']} | {m['limits']} |")
    lines += [
        "",
        "## Rules of use",
        "1. Testnet prices are **never** used as decision context (V0.2 §3.5).",
        "2. Any historical analysis uses only the information available at the simulated instant (point-in-time).",
        "3. An aggregator price and an exchange price are not two independent proofs by construction;",
        "   the Bitstamp / Binance / DeFiLlama comparison is kept to measure the gaps **between venues**.",
        "4. The issuer statement is recorded as a documentary reference: it must be read and quoted,",
        "   never reworded automatically.",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  README → {os.path.relpath(path, BASE)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="replay the archive without network")
    parser.add_argument("--force", action="store_true", help="re-collect everything, ignore the local cache")
    args = parser.parse_args()
    ensure_dirs()
    manifest_path = os.path.join(CORPUS, "manifest.json")

    global FORCE
    FORCE = bool(args.force)

    if args.offline:
        if not os.path.exists(manifest_path):
            print("No archived corpus. Run an online collection first."); sys.exit(1)
        data = json.load(open(manifest_path, encoding="utf-8"))
        print(f"REPLAY — corpus of {data['collected_at']}: {sum(m['records'] for m in data['sources'])} records.")
        return

    if os.path.exists(manifest_path):
        print("A corpus already exists (one collection per day is enough); it will be overwritten.\n")
    manifest = []
    print("Collecting the USDC corpus (March 2023)…")
    prices = collect_defillama_prices(manifest)
    bitstamp = collect_bitstamp(manifest)
    binance = collect_binance(manifest)
    supply = collect_supply(manifest)
    problems = validate_archived_windows(prices, bitstamp, binance, supply)
    if problems:
        print("WINDOW CONTRACT VIOLATED — corpus write refused:")
        for problem in problems[:10]:
            print("  " + problem)
        sys.exit(2)
    n_obs = write_csv(prices, bitstamp, binance, supply)
    write_readme(manifest, n_obs)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump({"collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "windows": {"main": [MAIN_START.isoformat(), MAIN_END.isoformat()],
                               "control": [CTRL_START.isoformat(), CTRL_END.isoformat()]},
                   "observations": n_obs, "sources": manifest}, fh, ensure_ascii=False, indent=1)
    print(f"Manifest → {os.path.relpath(manifest_path, BASE)}")


if __name__ == "__main__":
    main()
