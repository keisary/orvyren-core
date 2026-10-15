#!/usr/bin/env python
# W3-C — Sonde 3 : GT OHLCV ciblé (token=quote pour xUSD) + recherche multi-chaînes + CoinGecko.
# Exécuté le 2026-10-15. Throttle : 8 s entre appels GT (429 rencontrés à ~4 appels serrés).
import json, time, urllib.request, urllib.parse, urllib.error, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': 'application/json'}
def get(url, fn, hdr=None):
    req = urllib.request.Request(url, headers=hdr or UA)
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

def ohlcv(pool, tf, before, token, fn, agg=1, limit=1000):
    url = f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}/ohlcv/{tf}?aggregate={agg}&limit={limit}&before_timestamp={before}&currency=usd&token={token}"
    d = get(url, fn)
    rows = ((d or {}).get('data') or {}).get('attributes', {}).get('ohlcv_list') or []
    if rows:
        print(f"   {fn}: {len(rows)} bougies, plus ancienne={datetime.datetime.utcfromtimestamp(rows[-1][0]).isoformat()} plus récente={datetime.datetime.utcfromtimestamp(rows[0][0]).isoformat()}")
    return rows

P1 = "0xae255db04ba78519f33871c557d8fd6bafdb83bd"   # vgUSDC/xUSD (créé 2025-09-18)
NOW = ts('2026-10-15 00:00')
print("===== A. xUSD pool1, token=quote (le prix xUSD) =====")
ohlcv(P1, 'day', NOW, 'quote', 'gt_xusd_p1_quote_day.json'); time.sleep(8)
ohlcv(P1, 'hour', NOW, 'quote', 'gt_xusd_p1_quote_hour.json'); time.sleep(8)

print("===== B. pools USD0++ créés en 2024 (jours, token=base) =====")
ohlcv("0x1d08e7adc263cfc70b1babe6dc5bb339c16eec52", 'day', NOW, 'base', 'gt_usd0pp_u1_day_life.json'); time.sleep(8)
ohlcv("0x00cc0523b7a2b97f1d52bea1b7a0c50027e0a706", 'day', NOW, 'base', 'gt_usd0pp_u2_day_life.json'); time.sleep(8)

print("===== C. recherche de pools xUSD toutes chaînes =====")
d = get("https://api.geckoterminal.com/api/v2/search/pools?query=xUSD&page=1", "gt_search_xusd.json")
if d:
    for p in (d.get('data') or [])[:15]:
        a = p['attributes']; net = (p.get('relationships',{}).get('network',{}).get('data',{}) or {}).get('id','?')
        print(f"   [{net}] {str(a.get('name'))[:40]:40s} liq=${a.get('reserve_in_usd')} vol24=${a.get('volume_usd',{}).get('h24')} créé={str(a.get('pool_created_at'))[:10]} prix_base={str(a.get('base_token_price_usd'))[:10]}")
time.sleep(8)
d = get("https://api.geckoterminal.com/api/v2/search/pools?query=Staked+Stream&page=1", "gt_search_stakedstream.json")
if d:
    for p in (d.get('data') or [])[:15]:
        a = p['attributes']; net = (p.get('relationships',{}).get('network',{}).get('data',{}) or {}).get('id','?')
        print(f"   [{net}] {str(a.get('name'))[:40]:40s} liq=${a.get('reserve_in_usd')} vol24=${a.get('volume_usd',{}).get('h24')} créé={str(a.get('pool_created_at'))[:10]}")
