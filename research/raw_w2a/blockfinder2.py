#!/usr/bin/env python3
"""W2-A : blocs Ethereum pour timestamps cles — methode d'ancrage convergente (rapide)."""
import json, time, subprocess

RPCS = ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"]
def rpc(method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    last=None
    for u in RPCS:
        try:
            p = subprocess.run(["curl","-sL","-m","20","-H","Content-Type: application/json","--data",payload,u],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            j = json.loads(p.stdout)
            if j.get("result") is not None: return j["result"]
            last=j
        except Exception as e: last=str(e)
    raise RuntimeError(str(last)[:150])

C = {}
def ts_of(bn):
    if bn in C: return C[bn]
    C[bn] = int(rpc("eth_getBlockByNumber",[hex(int(bn)),False])["timestamp"],16); return C[bn]

ANCH = {1663224179: 15537394}  # The Merge 2022-09-15 06:42:59Z, bloc 15537394
for b in (16800000, 14900000):
    ANCH[ts_of(b)] = b
print("ancres:", ANCH, flush=True)

def find(ts):
    a_ts = min(ANCH, key=lambda t: abs(t-ts)); a_bn = ANCH[a_ts]
    step = 12.0 if ts > 1663224179 else 13.35
    est = a_bn + (ts - a_ts)/step
    for i in range(12):
        b = int(est); real = ts_of(b); d = real - ts
        if abs(d) <= 12: return b, real, i+1
        est = b - d/(12.0 if b > 15537394 else 13.35)
    return int(est), ts_of(int(est)), 99

targets = {
 "USDC_2023-03-11_00:00Z": 1678492800, "USDC_2023-03-11_03:11Z_tweet_Circle": 1678504260,
 "USDC_2023-03-11_08:00Z": 1678521600, "USDC_2023-03-13_00:00Z": 1678665600,
 "stETH_2022-06-09_00:00Z": 1654732800, "stETH_2022-06-11_00:00Z": 1654905600,
 "stETH_2022-06-16_00:00Z": 1655337600,
 "USD0pp_2025-01-09_00:00Z": 1736380800, "USD0pp_2025-01-09_21:46Z": 1736459160,
 "USD0pp_2025-01-10_04:02Z": 1736481720, "USD0pp_2025-01-11_00:00Z": 1736553600,
 "xUSD_2025-11-03_00:00Z": 1762128000, "xUSD_2025-11-04_00:00Z": 1762214400,
 "rsETH_2026-04-18_17:35Z": 1776533700, "rsETH_2026-04-18_18:52Z": 1776538320,
 "rsETH_2026-04-20_00:00Z": 1776643200,
}
res = {}
print("dernier bloc:", int(rpc("eth_blockNumber",[]),16), flush=True)
for name, ts in targets.items():
    try:
        b, real, it = find(ts)
        res[name] = {"timestamp": ts, "block": b, "block_ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(real)), "ecart_s": real-ts, "iterations": it}
        print(f"{name:36s} bloc={b} ts_bloc={res[name]['block_ts_utc']} ecart={real-ts}s (it={it})", flush=True)
    except Exception as e:
        res[name] = {"timestamp": ts, "erreur": str(e)}; print(name, "ERREUR", e, flush=True)
    open("blocs_episodes.json","w").write(json.dumps(res, indent=1))
print("TERMINE", flush=True)
