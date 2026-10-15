#!/usr/bin/env python
# W3-C — Sonde 12 : Morpho API (marketId) + lecture on-chain market(id) + xUSD, et vérif adresse Morpho Blue.
import json, time, urllib.request, urllib.error
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
RPC = "https://eth.drpc.org"
def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()[:8]
def gql(query, fn=None, printtxt=False):
    req = urllib.request.Request("https://blue-api.morpho.org/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = urllib.request.urlopen(req, timeout=40); body = r.read(); code = r.status
    except urllib.error.HTTPError as e:
        body, code = e.read(), e.code
    if fn: open(fn,'wb').write(body)
    if printtxt: print(f"   [{code}] {body[:400]}")
    try: return json.loads(body)
    except Exception: return None
def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                                 headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=40).read()); return r.get('result'), r.get('error')
    except Exception as e: return None, str(e)

print("== 1) marchés Morpho (top par supply) ==")
r = gql("{ markets(first: 6, where: { chainId_in: [1] }, orderBy: SupplyAssetsUsd, orderDirection: Desc) { items { marketId lltv loanAsset { symbol address } collateralAsset { symbol address } state { borrowAssets supplyAssets utilization supplyAssetsUsd } } } }", "morpho_api_top.json")
if r and r.get('data'):
    items = r['data']['markets']['items']
    for m in items:
        st = m['state']
        print(f"   {m['marketId'][:18]}... {m['loanAsset']['symbol']}/{m['collateralAsset']['symbol']} util={st['utilization']:.6f} supply=${float(st['supplyAssetsUsd'] or 0):,.0f}")
    MID = items[0]['marketId']
else:
    print("   échec:", json.dumps(r)[:300]); MID = None
time.sleep(1)

print("== 2) marchés Morpho avec collatéral xUSD ==")
r2 = gql('{ markets(first: 10, where: { chainId_in: [1], collateralAssetAddress_in: ["0xe2fc85bfb48c4cf147921fbe110cf92ef9f26f94"] }) { items { marketId loanAsset { symbol } collateralAsset { symbol } state { borrowAssets supplyAssets utilization supplyAssetsUsd borrowAssetsUsd } } } }', "morpho_api_xusd.json")
if r2 is not None: print("   ->", json.dumps(r2)[:900])
time.sleep(1)

print("== 3) Morpho Blue adresse 0xBBBB... ==")
res, err = rpc("eth_getCode", ["0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb", "latest"])
print("   code len:", len(res) if res else res, "err:", err)

if MID:
    print("== 4) lecture on-chain market(id) ==")
    data = sel("market(bytes32)") + MID[2:]
    res, err = rpc("eth_call", [{"to": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb", "data": data}, "latest"])
    if res and res != '0x':
        h = res[2:]
        words = [int(h[i*64:(i+1)*64], 16) for i in range(6)]
        print("   mots:", words)
        tsA, tbA = words[0], words[2]
        if tsA: print(f"   utilisation on-chain = {tbA/tsA:.6%} (borrowAssets/supplyAssets)")
    else:
        print("   market(id):", res, err)
    print("== 5) idToMarketParams(id) ==")
    data2 = sel("idToMarketParams(bytes32)") + MID[2:]
    res2, err2 = rpc("eth_call", [{"to": "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb", "data": data2}, "latest"])
    if res2 and res2 != '0x':
        h = res2[2:]; ws = [h[i*64:(i+1)*64] for i in range(5)]
        print("   loanToken:", '0x'+ws[0][24:], "collateral:", '0x'+ws[1][24:], "lltv:", int(ws[4],16))
    else:
        print("   idToMarketParams:", res2, err2)
