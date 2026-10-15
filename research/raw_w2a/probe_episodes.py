#!/usr/bin/env python3
"""W2-A : sondes multi-episodes (stETH 2022, rsETH 2026, USD0++ 2025, xUSD 2025).
- Aave V3 getReserveData dump (config: LTV, seuil de liquidation, frozen) pour rsETH/WETH avant/apres gel.
- Utilisation : aToken totalSupply vs variableDebt totalSupply.
- Prix DeFiLlama minute pour USD0++, xUSD, rsETH.
"""
import json, subprocess, time

RPCS = ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"]
def rpc(method, params):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params})
    last=None
    for u in RPCS:
        try:
            p = subprocess.run(["curl","-sL","-m","25","-H","Content-Type: application/json","--data",payload,u],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            j=json.loads(p.stdout)
            if j.get("result") is not None: return j["result"]
            last=j
        except Exception as e: last=str(e)
    raise RuntimeError(str(last)[:150])

def words(h):
    h = h[2:] if h.startswith("0x") else h
    return [int(h[i:i+64],16) for i in range(0,len(h),64)]

def call(to,data,block): return words(rpc("eth_call",[{"to":to,"data":data},hex(block)]))

def cfg_decode(c):
    return {"LTV_bps": c & 0xFFFF, "seuil_liq_bps": (c>>16)&0xFFFF, "bonus_liq_bps": (c>>32)&0xFFFF,
            "decimals": (c>>48)&0xFF, "actif": (c>>56)&1, "gele": (c>>57)&1, "emprunt_actif": (c>>58)&1,
            "paused": (c>>60)&1, "frozen_bit": (c>>57)&1, "eMode_cat": (c>>168)&0xFF}

A = {"aave_v3_pool":"0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
     "rseth":"0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7",
     "weth":"0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
     "usdc":"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
     "aave_v3_oracle":"0x54586bE62E3c3580375aE3723C145253060Ca0C2"}
def topic(a): return a.lower().replace("0x","").rjust(64,"0")

print("========== AAVE V3 rsETH / WETH / USDC : parametres avant et apres le gel (2026-04-18) ==========")
dump = {}
for block, label in [(24908200,"AVANT 18/04 ~17:21 UTC"), (24908664,"AU GEL 18:52 UTC"), (24909000,"APRES gel ~18:57"),
                     (24909500,"APRES gel ~19:07"), (24917377,"20/04 00:00 UTC")]:
    for sym in ("rsETH","WETH","USDC"):
        asset = A["rseth"] if sym=="rsETH" else (A["weth"] if sym=="WETH" else A["usdc"])
        w = call(A["aave_v3_pool"], "0x35ea6a75"+topic(asset), block)
        d = cfg_decode(w[0])
        addr_atoken = "0x"+format(w[8],'040x')[-40:] if len(w)>8 else None
        addr_vdebt  = "0x"+format(w[10],'040x')[-40:] if len(w)>10 else None
        atok_sup = call(addr_atoken, "0x18160ddd", block)[0] if addr_atoken else None
        vdebt_sup = call(addr_vdebt, "0x18160ddd", block)[0] if addr_vdebt else None
        dec = 18 if sym in ("rsETH","WETH") else 6
        u = None
        if atok_sup and vdebt_sup and atok_sup>0: u = vdebt_sup/atok_sup
        try: oracle_price = call(A["aave_v3_oracle"], "0xb3596f07"+topic(asset), block)[0]/1e8
        except Exception as e: oracle_price = f"ERR {e}"
        key=f"{label}|{sym}"
        dump[key]={"block":block,"config":d,"aToken":addr_atoken,"vDebt":addr_vdebt,
                   "aToken_supply":(atok_sup/10**dec if atok_sup else None),
                   "vDebt_supply":(vdebt_sup/10**dec if vdebt_sup else None),
                   "utilisation":u,"prix_oracle_aave":oracle_price}
        print(f"{label:26s} {sym:5s} LTV={d['LTV_bps']:5d}pb seuilLiq={d['seuil_liq_bps']:5d}pb gele={d['gele']} "
              f"eMode={d['eMode_cat']:3d} aToken={atok_sup/10**dec if atok_sup else float('nan'):.2f} "
              f"vDebt={vdebt_sup/10**dec if vdebt_sup else float('nan'):.2f} util={u if u is None else round(u,4)} "
              f"oracle={oracle_price}", flush=True)
open("aave_v3_rseth_2026.json","w").write(json.dumps(dump, indent=1, default=str))

print()
print("========== Prix DeFiLlama minute (test de disponibilite) ==========")
TOK = {
 "USD0++":"ethereum:0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B",
 "USD0":"ethereum:0x73a15fed60bf67631dc6cd7bc5b6e8da8190acf5",
 "xUSD":"ethereum:0xda8263d8ce9b3b6f0e2ef3f1be6b0e0b3b4f1b0d",
 "rsETH":"ethereum:0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7",
 "weETH":"ethereum:0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee",
}
def dl(url):
    p=subprocess.run(["curl","-sL","-m","30",url],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return p.stdout
tests = {
 "USD0++ 2025-01-09..11 (1m)": "https://coins.llama.fi/chart/ethereum:0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B?start=1736380800&span=300&period=1m",
 "USD0++ 2025-01-11 (1m)": "https://coins.llama.fi/chart/ethereum:0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B?start=1736553600&span=60&period=1m",
 "rsETH 2026-04-18 (1m)": "https://coins.llama.fi/chart/ethereum:0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7?start=1776530000&span=120&period=1m",
 "USDC 2023-03-11 (1m)": "https://coins.llama.fi/chart/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48?start=1678492800&span=120&period=1m",
 "stETH 2022-06-09..16 (1h)": "https://coins.llama.fi/chart/ethereum:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84?start=1654732800&span=200&period=1h",
}
res={}
for k,url in tests.items():
    out = dl(url)
    res[k]=out[:1500]
    prices = []
    try:
        j=json.loads(out); c=j["coins"]; coin=list(c.values())[0]
        prices = coin.get("prices",[])
        print(f"{k:34s} n={len(prices)} premier={prices[0] if prices else None} dernier={prices[-1] if prices else None}")
    except Exception as e:
        print(f"{k:34s} ERREUR/VIDE: {out[:200]}")
open("defillama_prices_probes.json","w").write(json.dumps(res, ensure_ascii=False, indent=1))
print("OK -> aave_v3_rseth_2026.json, defillama_prices_probes.json")
