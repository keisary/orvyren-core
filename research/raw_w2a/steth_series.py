#!/usr/bin/env python3
"""W2-A : episode stETH juin 2022 — serie Curve/Lido + slippage REEL de sortie (get_dy).
Correction : n'appelle QUE des contrats qui existaient en juin 2022 (Curve stETH, Lido, Aave V2).
"""
import json, subprocess, datetime

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

def words(h):
    h=h[2:] if h.startswith("0x") else h
    return [int(h[i:i+64],16) for i in range(0,len(h),64)] if h else []

def call(to,data,block):
    r = rpc("eth_call",[{"to":to,"data":data},hex(block)])
    w = words(r)
    if not w: raise RuntimeError(f"reponse vide (contrat absent au bloc {block} ?) to={to}")
    return w

def i128(x): return hex(x)[2:].rjust(64,"0")
def u256(x): return hex(x)[2:].rjust(64,"0")

CURVE_STETH="0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"   # ETH(0)/stETH(1)
LIDO="0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
AAVE_V2="0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
USDC="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
def topic(a): return a.lower().replace("0x","").rjust(64,"0")

def snapshot(block):
    r={"block":block, "ts": int(rpc("eth_getBlockByNumber",[hex(block),False])["timestamp"],16)}
    r["curve_eth_bal"]  = call(CURVE_STETH,"0x4903b0d1"+"0"*63+"0",block)[0]/1e18
    r["curve_steth_bal"]= call(CURVE_STETH,"0x4903b0d1"+"0"*63+"1",block)[0]/1e18
    r["ratio_steth_eth"]= r["curve_steth_bal"]/r["curve_eth_bal"] if r["curve_eth_bal"] else None
    r["lido_pooled_ether"]= call(LIDO,"0x37cfdaca",block)[0]/1e18
    # slippage reel : get_dy(1=stETH -> 0=ETH) pour 3 tailles
    dy={}
    for size in (100, 1000, 10000, 100000):
        dx = int(size*1e18)
        try:
            out = call(CURVE_STETH,"0x5e0d443f"+i128(1)+i128(0)+u256(dx),block)[0]/1e18
            dy[size] = {"eth_out": out, "prix_moyen": out/size, "slippage_pct": (1-out/size)*100}
        except Exception as e: dy[size]={"erreur":str(e)}
    r["get_dy_sortie_stETH"]=dy
    v2 = call(AAVE_V2,"0x35ea6a75"+topic(USDC),block)
    r["v2_usdc_liquidityIndex"]=v2[1]/1e27
    r["v2_usdc_varBorrowIndex"]=v2[2]/1e27
    return r

out=[]
for b in [14900000, 14929561, 14941266, 14950000, 14960000, 14970303]:
    try:
        s=snapshot(b); out.append(s)
        t=datetime.datetime.utcfromtimestamp(s["ts"]).strftime("%Y-%m-%d %H:%M:%SZ")
        d=s["get_dy_sortie_stETH"]
        print(f"[{b} {t}] Curve: ETH={s['curve_eth_bal']:,.0f} stETH={s['curve_steth_bal']:,.0f} ratio={s['ratio_steth_eth']:.2f} "
              f"Lido={s['lido_pooled_ether']:,.0f} | sortie 10k stETH -> {d[10000]['prix_moyen']:.4f} ETH (slip {d[10000]['slippage_pct']:.2f}%) "
              f"| 100k -> {d[100000]['prix_moyen']:.4f} (slip {d[100000]['slippage_pct']:.2f}%)", flush=True)
    except Exception as e:
        print(b,"ERREUR",e, flush=True); out.append({"block":b,"erreur":str(e)})
    open("steth_2022_serie.json","w").write(json.dumps(out,indent=1))
print("OK -> steth_2022_serie.json")
