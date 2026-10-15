#!/usr/bin/env python
# W3-C — Sonde 2 : OHLCV historique GeckoTerminal + DefiLlama (chart corrigé, batchHistorical)
# Exécuté le 2026-10-15. Réponses brutes sauvées dans raw_w3c/.
import json, time, urllib.request, urllib.parse, urllib.error, datetime

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      'Accept': 'application/json'}
def get(url, fn):
    req = urllib.request.Request(url, headers=UA)
    code, body = None, b''
    try:
        r = urllib.request.urlopen(req, timeout=60); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {fn}: {e} {url[:150]}"); return None
    open(fn, 'wb').write(body)
    print(f"[{code}] {fn} ({len(body)} o) {url[:170]}")
    try: return json.loads(body)
    except Exception: return None

def ts(s): return int(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=datetime.timezone.utc).timestamp())

def ohlcv_span(pool, tf, before, label, fn):
    url = f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{pool}/ohlcv/{tf}?aggregate=1&limit=1000&before_timestamp={before}&currency=usd&token=base"
    d = get(url, fn)
    rows = ((d or {}).get('data') or {}).get('attributes', {}).get('ohlcv_list') or []
    if rows:
        f_, l_ = rows[-1][0], rows[0][0]
        print(f"   {label}: {len(rows)} bougies, plus ancienne={datetime.datetime.utcfromtimestamp(f_).isoformat()} plus récente={datetime.datetime.utcfromtimestamp(l_).isoformat()}")
    else:
        print(f"   {label}: 0 bougie")
    return rows

print("========== GECKOTERMINAL OHLCV ==========")
# xUSD : pool vgUSDC/xUSD (creé 2025-09-18, plus grosse liquidité restante) et pool USDT/xUSD Balancer creé 2025-11-04
xusd_pool1 = "0xae255db04ba78519f33871c557d8fd6bafdb83bd"
xusd_pool2 = "0x923433f293796ae4fa478193878949409c23ccfbfc2f5acafcdecc4f0b9231d8".replace("0x","0x")[:66]
# le pool Balancer v3 : identifiant = id complet vu dans la liste, re-lire depuis le fichier
d = json.load(open('gt_xusd_pools.json', encoding='utf-8'))
bal = [p for p in d['data'] if 'USDT / xUSD 50%' in str(p['attributes'].get('name'))]
xusd_pool2 = bal[0]['attributes']['address'] if bal else None
print("pool2 xUSD USDT 50% =", xusd_pool2)

for tf, before, lab in [('day', ts('2026-10-15 00:00'), 'xUSD p1 day (maintenant)'),
                        ('day', ts('2025-11-20 00:00'), 'xUSD p1 day (avant 2025-11-20)'),
                        ('hour', ts('2025-11-10 00:00'), 'xUSD p1 hour (avant 2025-11-10)'),
                        ('minute', ts('2025-11-10 00:00'), 'xUSD p1 minute (avant 2025-11-10)')]:
    ohlcv_span(xusd_pool1, tf, before, lab, f"gt_xusd_p1_{tf}_{lab.split('(')[1][:-1].replace(' ','_')}.json")
    time.sleep(2)

if xusd_pool2:
    for tf, before, lab in [('day', ts('2025-11-20 00:00'), 'xUSD p2 balancer day avant 2025-11-20'),
                            ('hour', ts('2025-11-10 00:00'), 'xUSD p2 balancer hour avant 2025-11-10'),
                            ('minute', ts('2025-11-06 00:00'), 'xUSD p2 balancer minute avant 2025-11-06')]:
        ohlcv_span(xusd_pool2, tf, before, lab, f"gt_xusd_p2_{tf}.json")
        time.sleep(2)

# USD0++ : pools de janv. 2025 (crees 2024-07 et 2024-08) et le gros Uniswap v3
d = json.load(open('gt_usd0pp_pools.json', encoding='utf-8'))
for addr, tag in [("0x1d08e7adc263cfc70b1babe6dc5bb339c16eec52", "u1"), ("0x00cc0523b7a2b97f1d52bea1b7a0c50027e0a706", "u2"), ("0xabfca96716cf2911bbb50a4cdbcbaffa2ef8ecda", "u3")]:
    for tf, before, lab in [('hour', ts('2025-01-16 00:00'), f'USD0++ {tag} hour avant 2025-01-16'),
                            ('day', ts('2025-01-16 00:00'), f'USD0++ {tag} day avant 2025-01-16')]:
        ohlcv_span(addr, tf, before, lab, f"gt_usd0pp_{tag}_{tf}.json")
        time.sleep(2)

print()
print("========== DEFILLAMA CHART ==========")
USD0PP = "0x35D8949372D46B7a3D5A56006AE77B215fc69bC0"
XUSD = "0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94"
# chart avec start+span (pas end)
d = get(f"https://coins.llama.fi/chart/ethereum:{USD0PP}?start={ts('2025-01-06 00:00')}&span=300&period=1h", "ll_usd0pp_chart_start_span.json")
if d: print("   points:", len(d.get('coins', {}).get(f'ethereum:{USD0PP}', {}).get('prices', []) or []))
time.sleep(2)
d = get(f"https://coins.llama.fi/chart/ethereum:{USD0PP}?end={ts('2025-01-16 00:00')}&span=300&period=1h", "ll_usd0pp_chart_end_span.json")
if d: print("   points:", len(d.get('coins', {}).get(f'ethereum:{USD0PP}', {}).get('prices', []) or []))
time.sleep(2)
d = get(f"https://coins.llama.fi/chart/ethereum:{XUSD}?start={ts('2025-11-01 00:00')}&span=300&period=1h", "ll_xusd_chart_start_span.json")
if d: print("   points xUSD:", len(d.get('coins', {}).get(f'ethereum:{XUSD}', {}).get('prices', []) or []))

print()
print("========== DEFILLAMA BATCHHISTORICAL ==========")
# 8 points de test sur USD0++ autour du 9-11 janv. 2025
pts = [ts('2025-01-08 12:00') + i*3600 for i in range(0, 80, 10)]
coins = json.dumps([{f"ethereum:{USD0PP}": pts}], separators=(',', ':'))
url = "https://coins.llama.fi/batchHistorical?coins=" + urllib.parse.quote(coins) + "&searchWidth=1h"
d = get(url, "ll_usd0pp_batchhist_test.json")
print(json.dumps(d)[:600] if d else "pas de réponse")
