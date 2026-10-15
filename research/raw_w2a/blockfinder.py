#!/usr/bin/env python3
"""W2-A : numero de bloc Ethereum pour un timestamp (binary search via RPC public, curl en sous-processus)."""
import json, time, subprocess, sys

RPCS = ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"]
def rpc(method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    last = None
    for u in RPCS:
        try:
            p = subprocess.run(["curl","-sL","-m","25","-H","Content-Type: application/json","--data",payload,u],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            j = json.loads(p.stdout)
            if j.get("result") is not None:
                return j["result"]
            last = j
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"RPC echec {method}: {str(last)[:200]}")

_cache = {}
def block_ts(bn):
    if bn in _cache: return _cache[bn]
    b = rpc("eth_getBlockByNumber", [hex(bn), False])
    _cache[bn] = int(b["timestamp"], 16)
    return _cache[bn]

def find_block(ts, lo=10000000, hi=None):
    if hi is None: hi = int(rpc("eth_blockNumber", []), 16)
    # elargir si besoin
    while block_ts(lo) > ts: lo -= 1000000
    while block_ts(hi) < ts: hi += 1000000
    while lo < hi:
        mid = (lo+hi+1)//2
        if block_ts(mid) <= ts: lo = mid
        else: hi = mid-1
    return lo

targets = {
 "USDC_2023-03-11_00:00Z": 1678492800,
 "USDC_2023-03-11_03:11Z_tweet_Circle": 1678504260,
 "USDC_2023-03-11_08:00Z": 1678521600,
 "stETH_2022-06-09_00:00Z": 1654732800,
 "stETH_2022-06-11_00:00Z": 1654905600,
 "stETH_2022-06-16_00:00Z": 1655337600,
 "USD0pp_2025-01-09_00:00Z": 1736380800,
 "USD0pp_2025-01-09_21:46Z": 1736459160,
 "USD0pp_2025-01-10_04:02Z": 1736481720,
 "USD0pp_2025-01-11_00:00Z": 1736553600,
 "xUSD_2025-11-03_00:00Z": 1762128000,
 "xUSD_2025-11-04_00:00Z": 1762214400,
 "rsETH_2026-04-18_17:35Z": 1776533700,
 "rsETH_2026-04-18_18:52Z": 1776538320,
 "rsETH_2026-04-20_00:00Z": 1776643200,
}
res = {}
latest = int(rpc("eth_blockNumber", []), 16)
print("dernier bloc:", latest, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(block_ts(latest))))
for name, ts in targets.items():
    try:
        bn = find_block(ts); real = block_ts(bn)
        res[name] = {"timestamp": ts, "block": bn, "block_ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(real)), "ecart_s": real-ts}
        print(f"{name:38s} -> bloc {bn}  heure_bloc={res[name]['block_ts_utc']}  ecart={real-ts}s")
    except Exception as e:
        res[name] = {"timestamp": ts, "erreur": str(e)}; print(name, "ERREUR", e)
    time.sleep(0.1)
open("blocs_episodes.json","w").write(json.dumps(res, indent=1))
