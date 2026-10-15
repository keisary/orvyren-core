#!/usr/bin/env python
# W3-C — Sonde 9 : utilisation Compound V2 (cUSDC), Compound V3 (Comet USDC), Morpho Blue (API + on-chain).
# Sélecteurs calculés par keccak (pycryptodome vérifié sur le topic Transfer).
import json, time, urllib.request, urllib.error
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
RPC = "https://eth.drpc.org"

def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()[:8]
def topic(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()

def rpc(method, params):
    payload = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r.get('result'), r.get('error')
    except Exception as e:
        return None, str(e)

def call(to, data, block='latest'):
    res, err = rpc("eth_call", [{"to": to, "data": data}, block])
    if err: print("   RPC err:", err)
    return res

def word(hexstr, i):
    if not hexstr or hexstr == '0x': return None
    h = hexstr[2:]
    return int(h[i*64:(i+1)*64], 16)

print("== sélecteurs ==")
S = {s: sel(s) for s in ['getCash()','totalBorrows()','totalReserves()','totalSupply()','exchangeRateStored()',
                          'getUtilization()','totalBorrow()','market(bytes32)','idToMarketParams(bytes32)','underlying()','symbol()']}
for k,v in S.items(): print(f"   {k} = {v}")

print()
print("===== 1) Compound V2 cUSDC =====")
CUSDC = "0x39AA39c021dfbaE8faC545936693aC917d5E7563"
sym = call(CUSDC, S['symbol()'])
try:
    b = bytes.fromhex(sym[2:]); n = int.from_bytes(b[32:64],'big'); sym_s = b[64:64+n].decode()
except Exception: sym_s = sym
print("   symbol:", sym_s)
cash = word(call(CUSDC, S['getCash()']), 0)
borr = word(call(CUSDC, S['totalBorrows()']), 0)
resc = word(call(CUSDC, S['totalReserves()']), 0)
supp = word(call(CUSDC, S['totalSupply()']), 0)
print(f"   getCash={cash:,} totalBorrows={borr:,} totalReserves={resc:,} totalSupply(cTokens)={supp:,}")
if cash is not None and borr:
    U1 = borr/(cash+borr)
    U2 = borr/(cash+borr-resc) if (cash+borr-resc)>0 else None
    print(f"   U (borrows/(cash+borrows)) = {U1:.4%} | U (avec réserves) = {U2:.4%}")
print("   coût: 5 eth_call (1 marché, 1 instant)")

print()
print("===== 2) Compound V3 Comet USDC =====")
COMET = "0xc3d688B66703497DAA19211EEdff47f25384cdc3"
u = word(call(COMET, S['getUtilization()']), 0)
ts = word(call(COMET, S['totalSupply()']), 0)
tb = word(call(COMET, S['totalBorrow()']), 0)
print(f"   getUtilization() = {u/1e18:.4%}" if u is not None else "   getUtilization: None")
print(f"   totalSupply={ts:,} totalBorrow={tb:,}" if ts is not None else "   totals: None")
if ts and tb: print(f"   recalcul borrow/supply = {tb/ts:.4%}")
print("   coût: 3 eth_call")

print()
print("===== 3) Morpho Blue — API =====")
q = {"query": "{ markets(first: 5, where: { chainId_in: [1] }, orderBy: SupplyAssetsUsd, orderDirection: Desc) { items { uniqueKey lltv collateralAsset { address symbol } loanAsset { address symbol } state { borrowAssets supplyAssets utilization } } } }"}
req = urllib.request.Request("https://blue-api.morpho.org/graphql", data=json.dumps(q).encode(),
                             headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=40).read())
    open('morpho_api_top_markets.json','w').write(json.dumps(r, indent=1))
    items = (r.get('data') or {}).get('markets', {}).get('items', [])
    print("   API OK, marchés:", len(items))
    for m in items[:5]:
        st = m.get('state') or {}
        print(f"   {m.get('uniqueKey','')[:20]}... loan={ (m.get('loanAsset') or {}).get('symbol')} coll={(m.get('collateralAsset') or {}).get('symbol')} util={st.get('utilization')} supply={st.get('supplyAssets')} borrow={st.get('borrowAssets')}")
    MID = items[0]['uniqueKey'] if items else None
except Exception as e:
    print("   API ERR:", e); MID = None
time.sleep(1)

if MID:
    print()
    print("===== 4) Morpho Blue — lecture on-chain du marché (id API) =====")
    MB = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
    data = S['market(bytes32)'] + MID[2:] if MID.startswith('0x') else S['market(bytes32)'] + MID
    res = call(MB, data)
    if res and res != '0x':
        ws = [(i, word(res, i)) for i in range(6)]
        print("   market(id) mots:", [w for _, w in ws])
        tsA, tbA = ws[0][1], ws[2][1]
        if tsA: print(f"   utilisation recalculée on-chain = {tbA/tsA:.4%}")
    else:
        print("   market(id): réponse vide", res)
    data2 = S['idToMarketParams(bytes32)'] + MID[2:]
    res2 = call(MB, data2)
    print("   idToMarketParams ->", (res2 or 'vide')[:200])
    print("   coût: 2 eth_call")

print()
print("===== 5) Morpho : marchés/manoirs liés à xUSD (Stream) =====")
q2 = {"query": "{ markets(first: 10, where: { chainId_in: [1], collateralAssetAddress_in: [\"0xe2fc85bfb48c4cf147921fbe110cf92ef9f26f94\"] }) { items { uniqueKey collateralAsset { symbol } loanAsset { symbol } state { borrowAssets supplyAssets utilization collateralAssetsUsd } } } }"}
req = urllib.request.Request("https://blue-api.morpho.org/graphql", data=json.dumps(q2).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=40).read())
    open('morpho_api_xusd_markets.json','w').write(json.dumps(r, indent=1))
    print("   réponse:", json.dumps(r)[:800])
except Exception as e:
    print("   ERR:", e)
