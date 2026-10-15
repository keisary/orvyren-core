#!/usr/bin/env python
# W3-C — Sonde 10 : Morpho API (corrigée), Morpho on-chain, Compound archive, helper block_at.
import json, time, urllib.request, urllib.error
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
RPC = "https://eth.drpc.org"

def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()[:8]

def rpc(method, params):
    payload = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=40).read())
        return r.get('result'), r.get('error')
    except Exception as e:
        return None, str(e)

def block_at(ts_target, lo=14000000, hi=None):
    if hi is None:
        n, err = rpc("eth_blockNumber", [])
        hi = int(n, 16)
    for _ in range(40):
        mid = (lo+hi)//2
        b, err = rpc("eth_getBlockByNumber", [hex(mid), False])
        if err or not b: return None
        t = int(b['timestamp'], 16)
        if t < ts_target: lo = mid
        else: hi = mid
        if hi - lo <= 1: break
    return hi

def call(to, data, block='latest'):
    res, err = rpc("eth_call", [{"to": to, "data": data}, block])
    return res if not err else f"ERR:{err}"

def word(hexstr, i):
    if not hexstr or hexstr == '0x' or str(hexstr).startswith('ERR'): return None
    h = hexstr[2:]
    return int(h[i*64:(i+1)*64], 16)

print("== block_at(2025-11-04 12:00) ==")
import datetime
ts_t = int(datetime.datetime(2025,11,4,12,0,tzinfo=datetime.timezone.utc).timestamp())
blk = block_at(ts_t)
print("   bloc:", blk)
if blk:
    b, _ = rpc("eth_getBlockByNumber", [hex(blk), False])
    print("   horodatage:", datetime.datetime.utcfromtimestamp(int(b['timestamp'],16)).isoformat())
    arch_ok = True
else:
    arch_ok = False

print("== Compound V2 cUSDC @ archive (2025-11-04) ==")
CUSDC = "0x39AA39c021dfbaE8faC545936693aC917d5E7563"
if blk:
    cash = word(call(CUSDC, sel("getCash()"), hex(blk)), 0)
    borr = word(call(CUSDC, sel("totalBorrows()"), hex(blk)), 0)
    print(f"   getCash={cash:,} totalBorrows={borr:,} -> U={borr/(cash+borr):.4%}" if cash and borr else "   échec archive")

print("== Morpho API (corrigée) ==")
def gql(query, fn):
    req = urllib.request.Request("https://blue-api.morpho.org/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = urllib.request.urlopen(req, timeout=40); body = r.read()
    except urllib.error.HTTPError as e:
        body = e.read(); print(f"   [HTTP {e.code}] corps: {body[:400]}")
        return None
    open(fn,'wb').write(body)
    print(f"   [200] {fn} ({len(body)} o)")
    return json.loads(body)

r = gql("{ markets(first: 3, where: { chainId_in: [1] }) { items { uniqueKey lltv loanAsset { address symbol } collateralAsset { address symbol } state { borrowAssets supplyAssets utilization } } } }", "morpho_api_min.json")
if r: print("   items:", json.dumps(r)[:500])
time.sleep(1)
r2 = gql("{ markets(first: 3, where: { chainId_in: [1] }, orderBy: SupplyAssetsUsd, orderDirection: Desc) { items { uniqueKey lltv loanAsset { symbol } collateralAsset { symbol } state { borrowAssets supplyAssets utilization } } } }", "morpho_api_top.json")
if r2: print("   items:", json.dumps(r2)[:500])
time.sleep(1)
r3 = gql('{ markets(first: 5, where: { chainId_in: [1], collateralAssetAddress_in: ["0xe2fc85bfb48c4cf147921fbe110cf92ef9f26f94"] }) { items { uniqueKey collateralAsset { symbol } loanAsset { symbol } state { borrowAssets supplyAssets utilization } } } }', "morpho_api_xusd.json")
if r3: print("   xUSD markets:", json.dumps(r3)[:800])
