#!/usr/bin/env python
# W3-C — Sonde 6 : série USD0++ (DefiLlama chart + points historiques + test CoinGecko).
import json, time, urllib.request, urllib.parse, urllib.error, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn=None):
    req = urllib.request.Request(url, headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=60); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {fn}: {e}"); return None
    if fn: open(fn, 'wb').write(body)
    print(f"[{code}] {fn or url[:120]} ({len(body)} o)")
    try: return json.loads(body)
    except Exception: return None

def ts(s): return int(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=datetime.timezone.utc).timestamp())

USD0PP = "0x35D8949372D46B7a3D5A56006AE77B215fc69bC0"
COIN = f"ethereum:{USD0PP}"

print("== A. CoinGecko usd0-liquid-bond : test janv. 2025 hors fenêtre 365 j ==")
d = get("https://api.coingecko.com/api/v3/coins/usd0-liquid-bond/market_chart/range?vs_currency=usd&from=1736200000&to=1737100000", "cg_usd0pp_range_jan2025.json")
if d is not None: print("   réponse:", str(d)[:200])
time.sleep(5)
d = get("https://api.coingecko.com/api/v3/coins/usd0-liquid-bond/market_chart?vs_currency=usd&days=365", "cg_usd0pp_market_chart_365d.json")
if d is not None:
    pr = d.get('prices', [])
    print("   365 j points:", len(pr), "| premier:", pr[0] if pr else None, "| dernier:", pr[-1] if pr else None)
time.sleep(5)

print("== B. DefiLlama chart USD0++ : fenêtres et plafond de span ==")
d = get(f"https://coins.llama.fi/chart/{COIN}?start={ts('2025-01-01 00:00')}&period=1h&span=1000", "ll_usd0pp_chart_jan_full.json")
if d:
    pts = d.get('coins', {}).get(COIN, {}).get('prices', [])
    print("   start 01/01 + span=1000 ->", len(pts), "points")
    if pts: print("   premier:", datetime.datetime.utcfromtimestamp(pts[0]['timestamp']).isoformat(), pts[0]['price'], "| dernier:", datetime.datetime.utcfromtimestamp(pts[-1]['timestamp']).isoformat(), pts[-1]['price'])
time.sleep(3)
d = get(f"https://coins.llama.fi/chart/{COIN}?start={ts('2025-01-16 00:00')}&period=1h&span=1000", "ll_usd0pp_chart_fev.json")
if d:
    pts = d.get('coins', {}).get(COIN, {}).get('prices', [])
    print("   start 16/01 + span=1000 ->", len(pts), "points")
    if pts: print("   dernier:", datetime.datetime.utcfromtimestamp(pts[-1]['timestamp']).isoformat(), pts[-1]['price'])
time.sleep(3)
d = get(f"https://coins.llama.fi/chart/{COIN}?start={ts('2025-01-01 00:00')}&period=1d&span=400", "ll_usd0pp_chart_daily_400.json")
if d:
    pts = d.get('coins', {}).get(COIN, {}).get('prices', [])
    print("   daily span=400 ->", len(pts), "points")
    if pts: print("   premier:", datetime.datetime.utcfromtimestamp(pts[0]['timestamp']).isoformat(), "| dernier:", datetime.datetime.utcfromtimestamp(pts[-1]['timestamp']).isoformat())

print("== C. points historiques datés USD0++ ==")
key_ts = {
 '2025-01-08 12:00': ts('2025-01-08 12:00'), '2025-01-09 06:00': ts('2025-01-09 06:00'),
 '2025-01-09 12:00': ts('2025-01-09 12:00'), '2025-01-09 18:00': ts('2025-01-09 18:00'),
 '2025-01-10 00:00': ts('2025-01-10 00:00'), '2025-01-10 12:00': ts('2025-01-10 12:00'),
 '2025-01-11 00:00': ts('2025-01-11 00:00'), '2025-01-12 12:00': ts('2025-01-12 12:00'),
 '2025-01-13 12:00': ts('2025-01-13 12:00'), '2025-01-20 12:00': ts('2025-01-20 12:00'),
 '2025-02-01 12:00': ts('2025-02-01 12:00'), '2025-03-01 12:00': ts('2025-03-01 12:00'),
}
out = {}
for label, t in key_ts.items():
    d = get(f"https://coins.llama.fi/prices/historical/{t}/{COIN}", None)
    if d:
        c = d.get('coins', {}).get(COIN)
        out[label] = c
        print(f"   {label} -> {c}")
    time.sleep(1.5)
json.dump(out, open('ll_usd0pp_points_dates.json','w'), indent=1)
