#!/usr/bin/env python3
"""W2-A : serie temporelle on-chain 'valorisation retenue vs prix realisable'.
Appels eth_call a des blocs historiques via RPC public gratuit (eth.drpc.org / blastapi).
Sortie : onchain_series.json + table lisible.
"""
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
            if j.get("result") is not None: return j["result"]
            last = j
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"{method}: {str(last)[:150]}")

def words(hexstr):
    h = hexstr[2:] if hexstr.startswith("0x") else hexstr
    return [int(h[i:i+64], 16) for i in range(0, len(h), 64)]

def call(to, data, block):
    return words(rpc("eth_call", [{"to": to, "data": data}, hex(block)]))

def blk_ts(b):
    return int(rpc("eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)

A = {
 "aave_v3_oracle": "0x54586bE62E3c3580375aE3723C145253060Ca0C2",
 "chainlink_usdc_usd": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
 "chainlink_eth_usd": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
 "curve_3pool": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
 "curve_steth": "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022",
 "lido_steth": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",
 "aave_v2_pool": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
 "aave_v3_pool": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
 "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
 "dai": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
}
SEL = {"getAssetPrice":"0xb3596f07","latestRoundData":"0xfeaf968c","balances":"0x4903b0d1",
       "totalSupply":"0x18160ddd","getTotalPooledEther":"0x37cfdaca","getReserveData":"0x35ea6a75",
       "getReserveNormalizedIncome":"0xbf92857c"}

def addr_topic(a): return a.lower().replace("0x","").rjust(64,"0")

def snapshot(block):
    r = {"block": block}
    r["ts"] = blk_ts(block)
    # Aave V3 oracle : USDC, DAI, WETH (WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2)
    r["aave_oracle_usdc"] = call(A["aave_v3_oracle"], SEL["getAssetPrice"]+addr_topic(A["usdc"]), block)[0]/1e8
    r["aave_oracle_dai"]  = call(A["aave_v3_oracle"], SEL["getAssetPrice"]+addr_topic(A["dai"]), block)[0]/1e8
    # Chainlink USDC/USD : (roundId, answer, startedAt, updatedAt, answeredInRound)
    w = call(A["chainlink_usdc_usd"], SEL["latestRoundData"], block)
    r["cl_usdc_answer"] = w[1]/1e8; r["cl_usdc_updatedAt"] = w[3]; r["cl_usdc_round"] = w[0] & ((1<<64)-1)
    w = call(A["chainlink_eth_usd"], SEL["latestRoundData"], block)
    r["cl_eth_answer"] = w[1]/1e8; r["cl_eth_updatedAt"] = w[3]
    # Curve 3pool : balances(0 DAI, 1 USDC, 2 USDT) 18/6/6 dec
    b0 = call(A["curve_3pool"], SEL["balances"]+"0"*63+"0", block)[0]/1e18
    b1 = call(A["curve_3pool"], SEL["balances"]+"0"*63+"1", block)[0]/1e6
    b2 = call(A["curve_3pool"], SEL["balances"]+"0"*63+"2", block)[0]/1e6
    r["curve3_dai"], r["curve3_usdc"], r["curve3_usdt"] = b0, b1, b2
    # Curve stETH : balances(0 ETH, 1 stETH) 18 dec
    s0 = call(A["curve_steth"], SEL["balances"]+"0"*63+"0", block)[0]/1e18
    s1 = call(A["curve_steth"], SEL["balances"]+"0"*63+"1", block)[0]/1e18
    r["curve_steth_eth"], r["curve_steth_steth"] = s0, s1
    r["curve_steth_ratio"] = s1/s0 if s0 else None
    r["lido_total_pooled_ether"] = call(A["lido_steth"], SEL["getTotalPooledEther"], block)[0]/1e18
    # Aave V3 aToken USDC totalSupply (liquidite fournie) et V2 getReserveData USDC (index liquidite)
    r["aethusdc_totalSupply"] = call("0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c", SEL["totalSupply"], block)[0]/1e6
    v2 = call(A["aave_v2_pool"], SEL["getReserveData"]+addr_topic(A["usdc"]), block)
    r["v2_usdc_liquidityIndex"] = v2[1]/1e27
    r["v2_usdc_varBorrowIndex"] = v2[2]/1e27
    return r

if __name__ == "__main__":
    blocks = [int(x) for x in sys.argv[1:]]
    out = []
    for b in blocks:
        try:
            s = snapshot(b); out.append(s)
            import datetime
            t = datetime.datetime.utcfromtimestamp(s["ts"]).strftime("%Y-%m-%d %H:%M:%SZ")
            print(f"[{b} {t}] oracleUSDC={s['aave_oracle_usdc']:.4f} CL_USDC={s['cl_usdc_answer']:.4f}(maj {s['cl_usdc_updatedAt']}) "
                  f"3pool DAI={s['curve3_dai']/1e6:.2f}M USDC={s['curve3_usdc']/1e6:.2f}M USDT={s['curve3_usdt']/1e6:.2f}M "
                  f"| stETHpool ETH={s['curve_steth_eth']:.0f} stETH={s['curve_steth_steth']:.0f} ratio={s['curve_steth_ratio']:.2f} "
                  f"| Lido={s['lido_total_pooled_ether']:.0f}", flush=True)
        except Exception as e:
            print(b, "ERREUR", e, flush=True); out.append({"block": b, "erreur": str(e)})
        open("onchain_series.json","w").write(json.dumps(out, indent=1))
    print("OK -> onchain_series.json", flush=True)
