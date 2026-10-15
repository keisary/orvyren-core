#!/usr/bin/env python
# W3-C — Sonde 5a : CoinGecko (xUSD, USD0++), DefiLlama protocol stream, on-chain decimals & Vault Balancer v3.
import json, time, urllib.request, urllib.parse, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn=None, hdr=None):
    req = urllib.request.Request(url, headers=hdr or UA)
    try:
        r = urllib.request.urlopen(req, timeout=45); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {fn}: {e}"); return None, b''
    if fn: open(fn, 'wb').write(body)
    print(f"[{code}] {fn or url[:110]} ({len(body)} o)")
    try: return json.loads(body), body
    except Exception: return None, body

# --- 0. briques keccak dispo ?
for mod in ('Crypto.Hash.keccak', 'eth_hash.auto', 'sha3', 'web3'):
    try:
        __import__(mod); print("dispo:", mod)
    except Exception as e:
        print("absent:", mod)

# --- 1. CoinGecko : recherche des ids
d, _ = get("https://api.coingecko.com/api/v3/search?query=staked%20stream", "cg_search_xusd.json")
if d:
    for c in d.get('coins', [])[:8]:
        print("   CG xUSD candidat:", c.get('id'), '|', c.get('name'), '|', c.get('symbol'))
time.sleep(4)
d, _ = get("https://api.coingecko.com/api/v3/search?query=USD0", "cg_search_usd0.json")
if d:
    for c in d.get('coins', [])[:10]:
        print("   CG USD0 candidat:", c.get('id'), '|', c.get('name'), '|', c.get('symbol'))
time.sleep(4)

# --- 2. market_chart xUSD 365 j (granularité auto) + range 2-90 j pour tester l'horaire
d, _ = get("https://api.coingecko.com/api/v3/coins/staked-stream-usd/market_chart?vs_currency=usd&days=365", "cg_xusd_market_chart_365d.json")
if d:
    prices = d.get('prices', [])
    print("   xUSD market_chart 365j:", len(prices), "points; premier:", prices[0] if prices else None, "; dernier:", prices[-1] if prices else None)
time.sleep(6)
d, _ = get("https://api.coingecko.com/api/v3/coins/staked-stream-usd/market_chart/range?vs_currency=usd&from=1761350400&to=1762992000", "cg_xusd_range_octnov.json")
if d:
    prices = d.get('prices', [])
    print("   xUSD range 25/10->12/11:", len(prices), "points; exemples:", prices[:2], prices[-2:] if prices else None)
time.sleep(6)

# --- 3. DefiLlama : fiche protocole stream (chaînes)
d, _ = get("https://api.llama.fi/protocol/stream-finance", "ll_protocol_streamfinance.json")
if d:
    print("   LL stream-finance: chains =", d.get('chains'), "| tvl actuel =", d.get('currentChainTvls'))
time.sleep(2)

# --- 4. on-chain : decimals vgUSDC, symbol ; code du Vault Balancer v3 candidat
RPC = "https://eth.drpc.org"
def rpc(method, params, tag=''):
    payload = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return r.get('result'), r.get('error')
    except Exception as e:
        return None, str(e)

def decode_string(hexstr):
    try:
        b = bytes.fromhex(hexstr[2:]); n = int.from_bytes(b[32:64], 'big'); return b[64:64+n].decode()
    except Exception: return hexstr

for addr, tag in [("0x8399c8fc273bd165c346af74a02e65f10e4fd78f","vgUSDC?"), ("0xe2fc85bfb48c4cf147921fbe110cf92ef9f26f94","xUSD")]:
    dec, err = rpc("eth_call", [{"to": addr, "data": "0x313ce567"}, "latest"])
    sym, _ = rpc("eth_call", [{"to": addr, "data": "0x95d89b41"}, "latest"])
    print(f"   {tag} {addr}: decimals={int(dec,16) if dec and dec!='0x' else dec} symbol={decode_string(sym) if sym else sym} err={err}")
    time.sleep(1)

res, err = rpc("eth_getCode", ["0xbA1333333333a1BA1108E8412f11850A5C319bA9", "latest"])
print("   Vault Balancer v3 0xbA13...9bA9 : code len =", len(res) if res else res, "err =", err)
