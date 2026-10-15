#!/usr/bin/env python
# W3-C — Sonde 4 : identité du pool vgUSDC/xUSD (GT + on-chain), tokens & decimals.
import json, time, urllib.request, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn=None):
    req = urllib.request.Request(url, headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=45); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    if fn: open(fn, 'wb').write(body)
    print(f"[{code}] {fn or url[:100]} ({len(body)} o)")
    try: return json.loads(body)
    except Exception: return None

RPC = "https://eth.drpc.org"
def eth_call(to, data):
    payload = {"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":to,"data":data},"latest"]}
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    r = urllib.request.urlopen(req, timeout=30)
    return json.loads(r.read()).get('result')

P1 = "0xae255db04ba78519f33871c557d8fd6bafdb83bd"
print("== GT pool details ==")
d = get(f"https://api.geckoterminal.com/api/v2/networks/eth/pools/{P1}", "gt_pool1_details.json")
if d:
    a = d['data']['attributes']; rel = d['data']['relationships']
    print("  name:", a.get('name'), "| dex:", rel.get('dex',{}).get('data',{}).get('id'))
    print("  base:", rel.get('base_token',{}).get('data',{}).get('id'))
    print("  quote:", rel.get('quote_token',{}).get('data',{}).get('id'))
    print("  base_token_price_usd:", a.get('base_token_price_usd'), "quote_token_price_usd:", a.get('quote_token_price_usd'))
    print("  fdv:", a.get('fdv_usd'), "| market_cap:", a.get('market_cap_usd'), "| reserve:", a.get('reserve_in_usd'))
    print("  créé:", a.get('pool_created_at'))

print("== on-chain : token0/token1/decimals ==")
t0 = eth_call(P1, "0x0dfe1681")  # token0()
t1 = eth_call(P1, "0xd21220a7")  # token1()
print("  token0:", t0, " token1:", t1)
tokens = {}
for t in [t0, t1]:
    if not t or t == '0x': continue
    addr = '0x' + t[-40:]
    dec = eth_call(addr, "0x313ce567")           # decimals()
    sym = eth_call(addr, "0x95d89b41")           # symbol()
    # décodage string ABI
    try:
        b = bytes.fromhex(sym[2:]); n = int.from_bytes(b[32:64], 'big'); s = b[64:64+n].decode()
    except Exception: s = sym
    tokens[addr] = (int(dec, 16), s)
    print(f"  {addr}  decimals={int(dec,16)} symbol={s}")
open('pool1_tokens.json','w').write(json.dumps(tokens, indent=1))
