#!/usr/bin/env python3
"""W2-A : verification on-chain des adresses de tokens (symbol/name/decimals) + retest DeFiLlama."""
import json, subprocess

RPCS = ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"]
def rpc(method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    last=None
    for u in RPCS:
        try:
            p=subprocess.run(["curl","-sL","-m","25","-H","Content-Type: application/json","--data",payload,u],
                             capture_output=True,text=True,encoding="utf-8",errors="replace")
            j=json.loads(p.stdout)
            if j.get("result") is not None: return j["result"]
            last=j
        except Exception as e: last=str(e)
    raise RuntimeError(str(last)[:120])

def dec_str(h):
    if not h or h=="0x": return None
    b=bytes.fromhex(h[2:])
    if len(b)<64: return None
    off=int.from_bytes(b[0:32],"big"); ln=int.from_bytes(b[off:off+32],"big")
    return b[off+32:off+32+ln].decode("utf-8","replace")

CANDS = {
 "USD0++? (0x35D1b3F3...)": "0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B",
 "USD0 (0x73a15fed...)": "0x73a15fed60bf67631dc6cd7bc5b6e8da8190acf5",
 "rsETH (0xA1290d69...)": "0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7",
 "sUSDe (0x9D39A5DE...)": "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497",
 "wstETH (0x7f39C5...)": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",
}
print("=== symbol()/name()/decimals() on-chain (bloc courant) ===")
out={}
for label,addr in CANDS.items():
    try:
        sym=dec_str(rpc("eth_call",[{"to":addr,"data":"0x95d89b41"},"latest"]))
        nm=dec_str(rpc("eth_call",[{"to":addr,"data":"0x06fdde03"},"latest"]))
        dec=int(rpc("eth_call",[{"to":addr,"data":"0x313ce567"},"latest"]),16)
        out[label]={"addr":addr,"symbol":sym,"name":nm,"decimals":dec}
        print(f"{label:26s} symbol={sym!r} name={nm!r} decimals={dec}")
    except Exception as e:
        print(f"{label:26s} ERREUR {e}")

print()
print("=== retest DeFiLlama chart (plusieurs period/span) ===")
def dl(url):
    p=subprocess.run(["curl","-sL","-m","30",url],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return p.stdout
tests={
 "USD0++ 2025-01-10 1m": "https://coins.llama.fi/chart/ethereum:0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B?start=1736467200&span=200&period=1m",
 "USD0++ 2025-01-10 1h": "https://coins.llama.fi/chart/ethereum:0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B?start=1736380800&span=200&period=1h",
 "USD0 2025-01-10 1h": "https://coins.llama.fi/chart/ethereum:0x73a15fed60bf67631dc6cd7bc5b6e8da8190acf5?start=1736380800&span=200&period=1h",
 "rsETH 2026-04-18 1m": "https://coins.llama.fi/chart/ethereum:0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7?start=1776533700&span=200&period=1m",
 "rsETH 2026-04-18 1h": "https://coins.llama.fi/chart/ethereum:0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7?start=1776470400&span=200&period=1h",
 "rsETH 2026-04-19 1h": "https://coins.llama.fi/chart/ethereum:0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7?start=1776556800&span=200&period=1h",
}
res={}
for k,u in tests.items():
    o=dl(u); res[k]=o[:2000]
    try:
        j=json.loads(o); c=j.get("coins",{})
        if not c: print(f"{k:24s} VIDE {o[:120]}"); continue
        coin=list(c.values())[0]; pr=coin.get("prices",[])
        print(f"{k:24s} n={len(pr)} p1={pr[0] if pr else None} pN={pr[-1] if pr else None}")
    except Exception as e:
        print(f"{k:24s} ERR {e} {o[:150]}")
open("defillama_retest.json","w").write(json.dumps(res,ensure_ascii=False,indent=1))
print("OK")
