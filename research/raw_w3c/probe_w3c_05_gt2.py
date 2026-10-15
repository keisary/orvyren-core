#!/usr/bin/env python
# W3-C — Sonde 5b : GT séries complémentaires xUSD (pool Balancer du 04/11 + pools Uniswap créés pendant le crash).
import json, time, urllib.request, urllib.error, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn):
    req = urllib.request.Request(url, headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=60); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {fn}: {e}"); return None
    open(fn, 'wb').write(body)
    print(f"[{code}] {fn} ({len(body)} o)")
    try: return json.loads(body)
    except Exception: return None

def ts(s): return int(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=datetime.timezone.utc).timestamp())
def ohlcv(pool, tf, before, token, fn):
    d = get(f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}/ohlcv/{tf}?aggregate=1&limit=1000&before_timestamp={before}&currency=usd&token={token}", fn)
    rows = ((d or {}).get('data') or {}).get('attributes', {}).get('ohlcv_list') or []
    if rows:
        print(f"   {fn}: {len(rows)} bougies de {datetime.datetime.utcfromtimestamp(rows[-1][0]).isoformat()} à {datetime.datetime.utcfromtimestamp(rows[0][0]).isoformat()}")
    return rows

NOW = ts('2026-10-15 00:00')
jobs = [
    ("0x923433f293796ae4fa478193878949409c23ccfbfc2f5acafcdecc4f0b9231d8", 'quote', 'gt_xusd_p2_bal_quote_day.json'),   # Balancer USDT/xUSD créé 04/11/2025
    ("0x7224d2ec8c91db1a3e62943a7ec660181f86c018", 'quote', 'gt_xusd_p3_uni_quote_day.json'),   # Uniswap USDC/xUSD 3% créé 03/11/2025
    ("0x64dfcf0b86e291483511abd396927407217e3b292", 'quote', 'gt_xusd_p4_uni_quote_day.json'),   # Uniswap USDC/xUSD 2.99% créé 04/11/2025
    ("0x0b5f7d1d0e10846429e3981aa99a04126931d90e", 'quote', 'gt_xusd_p5_uni_quote_day.json'),    # Uniswap USDC/xUSD 10% créé 04/11/2025
]
for pool, token, fn in jobs:
    ohlcv(pool, 'day', NOW, token, fn)
    time.sleep(8)
