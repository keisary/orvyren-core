#!/usr/bin/env python
# W3-C — Sonde 15 : reconstruction v2.
#   A) USD0++/USDT (Uniswap v3, logs déjà sauvés) -> horodatage robuste + série horaire.
#   B) USDC/xUSD (Uniswap v4 : PoolManager + PoolId) -> série horaire 03-05/11/2025.
import json, time, datetime, urllib.request, urllib.error, collections
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 Chrome/124', 'Content-Type': 'application/json'}
RPC = "https://eth.drpc.org"
RPC_LOGS = "https://rpc.mevblocker.io"
def topic0(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()

def rpc(method, params, retries=4):
    for a in range(retries):
        req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers=UA)
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if r.get('error') is None: return r.get('result'), None
            err = r['error']
        except Exception as e: err = str(e)[:120]
        time.sleep(1.2*(a+1))
    return None, err

def rpc_logs(params, retries=4):
    for a in range(retries):
        req = urllib.request.Request(RPC_LOGS, data=json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":params}).encode(), headers=UA)
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=90).read())
            if r.get('error') is None: return r.get('result') or [], None
            err = r['error']
        except Exception as e: err = str(e)[:150]
        time.sleep(1.5*(a+1))
    return None, err

def rpc_at(endpoint, method, params, timeout=45):
    req = urllib.request.Request(endpoint, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(), headers=UA)
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        if r.get('error') is None: return r.get('result'), None
        return None, r['error']
    except Exception as e:
        return None, str(e)[:120]

def rpc_batch(calls, size=10):
    out = {}
    for i in range(0, len(calls), size):
        grp = calls[i:i+size]
        req = urllib.request.Request(RPC, data=json.dumps([{"jsonrpc":"2.0","id":j,**c} for j,c in enumerate(grp)]).encode(), headers=UA)
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if isinstance(r, list):
                for x in r: out[i + x.get('id', 0)] = x.get('result')
        except Exception as e:
            print("   batch err:", str(e)[:100])
        time.sleep(0.3)
    return out

def block_at(ts_target):
    hi = int(rpc("eth_blockNumber", [])[0], 16); lo = 14000000
    while hi - lo > 1:
        mid = (lo+hi)//2
        b, err = rpc("eth_getBlockByNumber", [hex(mid), False])
        if not b: raise RuntimeError(f"bloc {mid}: {err}")
        if int(b['timestamp'],16) < ts_target: lo = mid
        else: hi = mid
    return hi

def ts_for_blocks(blocks):
    ts = {}
    t0 = time.time()
    for n, b in enumerate(blocks):
        got = None
        for attempt in range(5):
            for ep in (RPC_LOGS, RPC):
                res, err = rpc_at(ep, "eth_getBlockByNumber", [hex(b), False])
                if res and res.get('timestamp'):
                    got = int(res['timestamp'],16); break
            if got: break
            time.sleep(0.8*(attempt+1))
        if not got:
            raise RuntimeError(f"bloc {b} non résolu")
        ts[b] = got
        if n % 100 == 0 and n: print(f"   ...{n}/{len(blocks)} ({time.time()-t0:.0f} s)")
    print(f"   timestamps: {len(ts)}/{len(blocks)} blocs résolus en {time.time()-t0:.0f} s")
    return ts

def word(data, i):
    return data[i*64:(i+1)*64]

def signed(w):
    v = int(w, 16)
    return v - (1<<256) if v >= (1<<255) else v

def priced(sqrtP, d0, d1):
    raw = (sqrtP/(2**96))**2
    return raw * (10**(d0-d1))   # prix du token0 en token1

# ---------- A) USD0++ / USDT (v3) ----------
print("===== A) USD0++/USDT (Uniswap v3) =====")
logs = json.load(open('logs_usd0pp_usdt_jan2025.json'))
print("   logs:", len(logs))
blocks = sorted({int(l['blockNumber'],16) for l in logs})
tsb = ts_for_blocks(blocks)
D0, D1 = 18, 6   # token0 = USD0++ (18), token1 = USDT (6)
byh = {}
for l in sorted(logs, key=lambda x: int(x['blockNumber'],16)):
    bn = int(l['blockNumber'],16); ts = tsb[bn]
    data = l['data'][2:]
    sqrtP = int(word(data,2),16)
    if sqrtP == 0: continue
    p = priced(sqrtP, D0, D1)   # USD0++ en USDT
    byh[ts - ts % 3600] = p
print(f"   heures: {len(byh)}")
assert len(byh) > 50, "série horaire trop courte"
with open('recon_usd0pp_hourly.csv','w', newline='') as f:
    f.write('ts_utc_iso,unix,price_usd0pp_in_usdt\n')
    for h, p in sorted(byh.items()):
        f.write(f"{datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%dT%H:%M:%SZ')},{h},{p}\n")
for h, p in list(sorted(byh.items()))[:4] + list(sorted(byh.items()))[-4:]:
    print(f"     {datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%d %H:%M')}  {p:.5f}")
mn = min(byh.items(), key=lambda x: x[1])
print("   minimum:", datetime.datetime.utcfromtimestamp(mn[0]).strftime('%Y-%m-%d %H:%M'), f"{mn[1]:.5f}")

# ---------- B) USDC/xUSD (Uniswap v4) ----------
print("===== B) USDC/xUSD (Uniswap v4) =====")
POOLID = "0x7224d2ec8c91db1a3e62943a7ec660181f86c018177ad43ced0a3abbda01a493"
PM = "0x000000000004444c5dc75cB358380D2e3dE08A90"
code, err = rpc("eth_getCode", [PM, "latest"])
print("   PoolManager code len:", len(code) if code else code, err or '')
SIGS = ["Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)",
        "Swap(bytes32,address,int256,int256,uint160,uint128,int24,uint24)"]
fromB = block_at(int(datetime.datetime(2025,11,3,18,0,tzinfo=datetime.timezone.utc).timestamp()))
toB   = block_at(int(datetime.datetime(2025,11,6,0,0,tzinfo=datetime.timezone.utc).timestamp()))
print(f"   blocs {fromB} -> {toB}")
logs4, used = [], None
for sig in SIGS:
    t0 = topic0(sig)
    res, err = rpc_logs([{"address": PM, "topics": [t0, POOLID], "fromBlock": hex(fromB), "toBlock": hex(toB)}])
    print(f"   signature {sig[:44]}... -> {len(res or [])} logs" + (f" (err {err})" if err else ""))
    if res:
        logs4, used = res, sig; break
if logs4:
    json.dump(logs4, open('logs_usdc_xusd_v4_nov2025.json','w'))
    blocks4 = sorted({int(l['blockNumber'],16) for l in logs4})
    tsb4 = ts_for_blocks(blocks4)
    byh4 = {}
    for l in sorted(logs4, key=lambda x: int(x['blockNumber'],16)):
        bn = int(l['blockNumber'],16); ts = tsb4[bn]
        data = l['data'][2:]
        sqrtP = int(word(data,2),16)
        if sqrtP == 0: continue
        # currency0 < currency1 par adresse : USDC (0xa0b8..) < xUSD (0xe2fc..) ; decimals 6/6
        p_xusd_in_usdc = 1/priced(sqrtP, 6, 6)
        byh4[ts - ts % 3600] = p_xusd_in_usdc
    print(f"   heures: {len(byh4)}")
    with open('recon_xusd_v4_hourly.csv','w', newline='') as f:
        f.write('ts_utc_iso,unix,price_xusd_in_usdc\n')
        for h, p in sorted(byh4.items()):
            f.write(f"{datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%dT%H:%M:%SZ')},{h},{p}\n")
    for h, p in sorted(byh4.items()):
        print(f"     {datetime.datetime.utcfromtimestamp(h).strftime('%Y-%m-%d %H:%M')}  {p:.5f}")
else:
    print("   aucun log v4 trouvé — signatures testées:", SIGS)
