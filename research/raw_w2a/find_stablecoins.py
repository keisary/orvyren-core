#!/usr/bin/env python3
"""W2-A : trouve les adresses/ids des stablecoins (USD0++, xUSD, deUSD, USDX) via l'API DeFiLlama,
puis teste la disponibilite de leurs series de prix."""
import json, subprocess

def get(url):
    p=subprocess.run(["curl","-sL","-m","40",url],capture_output=True,text=True,encoding="utf-8",errors="replace")
    return p.stdout

print("=== 1) Registre des stablecoins DeFiLlama : recherche par symbole ===")
raw = get("https://stablecoins.llama.fi/stablecoins?includePrices=true")
try:
    j=json.loads(raw); arr=j.get("peggedAssets",[])
    print("nb stablecoins:", len(arr))
    cibles = ["USD0","XUSD","DEUSD","USDX","USR","SUSDX","USUAL"]
    found=[]
    for a in arr:
        sym=(a.get("symbol") or "").upper()
        if any(c in sym for c in cibles):
            chain_contracts = [{"chain":k, "addr":v} for k,v in (a.get("address") or {}).items()]
            found.append({"id":a.get("id"),"symbol":a.get("symbol"),"name":a.get("name"),"chains":a.get("chains"),
                          "price":a.get("price"),"pegType":a.get("pegType"),"addresses":chain_contracts[:6]})
    for f in found:
        print(json.dumps(f, ensure_ascii=False)[:400])
    open("defillama_stablecoin_registry.json","w").write(json.dumps(found,ensure_ascii=False,indent=1))
except Exception as e:
    print("ERREUR parsing:", e, raw[:300])

print()
print("=== 2) Endpoints RPC gratuits supplementaires : test archive @bloc 12 582 912 ===")
payload='{"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["0x00000000219ab540356cBB839Cbe05303d7705Fa","0xC00000"]}'
for url in ["https://rpc.ankr.com/eth","https://eth.merkle.io","https://rpc.mevblocker.io","https://eth-pokt.nodies.app","https://rpc.payload.de","https://api.securerpc.com/v1","https://eth.rpc.blxrbdn.com"]:
    p=subprocess.run(["curl","-sL","-m","20","-H","Content-Type: application/json","--data",payload,url],
                     capture_output=True,text=True,encoding="utf-8",errors="replace")
    body=(p.stdout or "")[:180].replace("\n"," ")
    print(f"{url:42s} -> {body}")
