#!/usr/bin/env python
# W3-C — Sonde 13 : reconstruction DEX par logs (Uniswap v3 Swap events) sur blocs d'archive drpc.
#   1) USD0++/USDT pool 0x00cc0523 (créé 2024-08-28) — fenêtre 08->12 janv. 2025.
#   2) USDC/xUSD pool 0x7224d2ec (créé 2025-11-03 21:02) — fenêtre 03->05 nov. 2025.
import json, time, datetime, urllib.request, urllib.error
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
RPC = "https://eth.drpc.org"          # eth_call / blocs / lots
RPC_LOGS = "https://rpc.mevblocker.io"  # eth_getLogs archive (drpc limite les plages, blastapi 10 blocs, nodies 50)
def rpc_logs(params, retries=4):
    for a in range(retries):
        req = urllib.request.Request(RPC_LOGS, data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":params}).encode(),
                                     headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=90).read())
            if r.get('error'): err = r['error']
            else: return r.get('result') or [], None
        except Exception as e:
            err = str(e)[:150]
        time.sleep(1.5*(a+1))
    return None, err
def topic0(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()
SWAP = topic0("Swap(address,address,int256,int256,uint160,uint128,int24)")
print("topic0 Swap v3 =", SWAP)
assert SWAP == '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67', "signature inattendue"

def rpc(method, params, retries=4):
    for a in range(retries):
        req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                     headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if r.get('result') is not None or r.get('error') is None: return r.get('result'), r.get('error')
            err = r.get('error')
        except Exception as e:
            err = str(e)
        time.sleep(1.5*(a+1))
    return None, err

def rpc_batch(calls):
    req = urllib.request.Request(RPC, data=json.dumps([{"jsonrpc":"2.0","id":i,**c} for i,c in enumerate(calls)]).encode(),
                                 headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=90).read()); return {x['id']: x.get('result') for x in r}
    except Exception as e: return {}

def block_at(ts_target):
    hi = int(rpc("eth_blockNumber", [])[0], 16)
    lo = 14000000
    while hi - lo > 1:
        mid = (lo+hi)//2
        b, err = rpc("eth_getBlockByNumber", [hex(mid), False])
        if not b: raise RuntimeError(f"bloc {mid} illisible: {err}")
        if int(b['timestamp'],16) < ts_target: lo = mid
        else: hi = mid
    return hi

def call(to, data):
    res, err = rpc("eth_call", [{"to": to, "data": data}, "latest"]); return res

def word(hexstr, i): 
    h = hexstr[2:]; return int(h[i*64:(i+1)*64], 16)

def addr_word(hexstr, i):
    h = hexstr[2:]; return '0x' + h[i*64+24:(i+1)*64]

def get_logs(pool, fromB, toB, chunk=100000):
    logs = []
    b = fromB
    while b <= toB:
        e = min(b+chunk-1, toB)
        res, err = rpc_logs([{"address": pool, "topics": [SWAP], "fromBlock": hex(b), "toBlock": hex(e)}])
        if err:
            print(f"   getLogs err ({b}-{e}): {str(err)[:140]} -> réduction du chunk ({chunk}->{chunk//2})")
            if chunk > 1000: chunk //= 2
            else:
                print("   abandon sur ce segment"); b = e+1
            continue
        logs.extend(res or [])
        print(f"   logs {b}-{e}: +{len(res or [])} (total {len(logs)})")
        b = e+1
        time.sleep(0.4)
    return logs

def series_from_swaps(pool, logs, d0, d1, tok0, x_plus):
    """Retourne liste (block, ts, price_xusd_or_usd0pp_in_quote)."""
    print(f"   {len(logs)} swaps récupérés")
    # timestamps par blocs uniques
    blocks = sorted({int(l['blockNumber'],16) for l in logs})
    print(f"   {len(blocks)} blocs uniques -> timestamps par lots")
    ts_by_block = {}
    for i in range(0, len(blocks), 50):
        calls = [{"method":"eth_getBlockByNumber","params":[hex(b), False]} for b in blocks[i:i+50]]
        out = rpc_batch(calls)
        for j, b in enumerate(blocks[i:i+50]):
            r = out.get(j)
            if r: ts_by_block[b] = int(r['timestamp'],16)
        time.sleep(0.5)
    pts = []
    for l in logs:
        bn = int(l['blockNumber'],16); ts = ts_by_block.get(bn)
        data = l['data'][2:]
        w = [data[i*64:(i+1)*64] for i in range(5)]
        sqrtP = int(w[2],16); 
        if sqrtP == 0: continue
        raw = (sqrtP/(2**96))**2
        # prix du token0 en token1 (humain) = raw * 10^(d0-d1)
        p01 = raw * (10**(d0-d1))
        price = (1/p01 if (tok0 != x_plus) else p01)  # prix de x_plus en unité du quote
        if ts: pts.append((bn, ts, price))
    return pts

# ---------- 1) USD0++ / USDT ----------
print("===== 1) USD0++/USDT pool 0x00cc0523 (janv. 2025) =====")
POOL1 = "0x00cc0523b7a2b97f1d52bea1b7a0c50027e0a706"
t0 = call(POOL1, "0x0dfe1681"); t1 = call(POOL1, "0xd21220a7")
tok0, tok1 = addr_word(t0,0), addr_word(t1,0)
d0 = word(call(tok0, "0x313ce567"),0); d1 = word(call(tok1, "0x313ce567"),0)
print(f"   token0={tok0} (dec {d0}) | token1={tok1} (dec {d1})")
fromB = block_at(int(datetime.datetime(2025,1,8,0,0,tzinfo=datetime.timezone.utc).timestamp()))
toB = block_at(int(datetime.datetime(2025,1,12,12,0,tzinfo=datetime.timezone.utc).timestamp()))
print(f"   blocs {fromB} -> {toB}")
logs1 = get_logs(POOL1, fromB, toB)
json.dump(logs1, open('logs_usd0pp_usdt_jan2025.json','w'))
pts1 = series_from_swaps(POOL1, logs1, d0, d1, tok0, "0x35d8949372d46b7a3d5a56006ae77b215fc69bc0")
if pts1:
    # agrégation horaire (dernier swap de l'heure)
    import collections
    byh = collections.OrderedDict()
    for bn, ts, p in sorted(pts1, key=lambda x: x[1]):
        h = ts - ts % 3600
        byh[h] = p
    with open('recon_usd0pp_hourly.csv','w', newline='') as f:
        f.write('ts_utc_iso,unix,price_usd0pp_in_usdt,close\n')
        for h, p in byh.items():
            f.write(f"{datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%dT%H:%M:%SZ')},{h},{p}\n")
    print(f"   série horaire: {len(byh)} heures; exemple premières/dernières:")
    ks = list(byh.items())
    for h, p in ks[:3] + ks[-3:]:
        print(f"     {datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%d %H:%M')}  {p:.5f}")

# ---------- 2) USDC / xUSD ----------
print("===== 2) USDC/xUSD pool 0x7224d2ec (nov. 2025) =====")
POOL2 = "0x7224d2ec8c91db1a3e62943a7ec660181f86c018"
t0 = call(POOL2, "0x0dfe1681"); t1 = call(POOL2, "0xd21220a7")
if t0 and t0 != '0x':
    tok0, tok1 = addr_word(t0,0), addr_word(t1,0)
    d0 = word(call(tok0, "0x313ce567"),0); d1 = word(call(tok1, "0x313ce567"),0)
    print(f"   token0={tok0} (dec {d0}) | token1={tok1} (dec {d1})")
    fromB = block_at(int(datetime.datetime(2025,11,3,19,0,tzinfo=datetime.timezone.utc).timestamp()))
    toB = block_at(int(datetime.datetime(2025,11,5,12,0,tzinfo=datetime.timezone.utc).timestamp()))
    print(f"   blocs {fromB} -> {toB}")
    logs2 = get_logs(POOL2, fromB, toB)
    json.dump(logs2, open('logs_usdc_xusd_nov2025.json','w'))
    pts2 = series_from_swaps(POOL2, logs2, d0, d1, tok0, "0xe2fc85bfb48c4cf147921fbe110cf92ef9f26f94")
    if pts2:
        import collections
        byh = collections.OrderedDict()
        for bn, ts, p in sorted(pts2, key=lambda x: x[1]):
            h = ts - ts % 3600
            byh[h] = p
        with open('recon_xusd_hourly.csv','w', newline='') as f:
            f.write('ts_utc_iso,unix,price_xusd_in_usdc,close\n')
            for h, p in byh.items():
                f.write(f"{datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%dT%H:%M:%SZ')},{h},{p}\n")
        print(f"   série horaire: {len(byh)} heures:")
        for h, p in list(byh.items()):
            print(f"     {datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%d %H:%M')}  {p:.5f}")
else:
    print("   pool introuvable/déployé après la fenêtre:", t0)
