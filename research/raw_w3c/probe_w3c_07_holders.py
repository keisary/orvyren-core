#!/usr/bin/env python
# W3-C — Sonde 7 : concentration des détenteurs. Blockscout v2 (rsETH, stETH, xUSD) + Etherscan v2 (sans clé).
import json, time, urllib.request, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn=None):
    req = urllib.request.Request(url, headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=60); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {fn}: {e}"); return None, b''
    if fn: open(fn, 'wb').write(body)
    print(f"[{code}] {fn or url[:120]} ({len(body)} o)")
    try: return json.loads(body), body
    except Exception: return None, body

TOKENS = {
    'rsETH': '0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7',
    'stETH': '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
    'xUSD':  '0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94',
}
for name, addr in TOKENS.items():
    print(f"===== Blockscout v2 holders {name} =====")
    info, _ = get(f"https://eth.blockscout.com/api/v2/tokens/{addr}", f"bs_{name}_info.json")
    if info:
        print("   token:", info.get('name'), "| supply:", info.get('total_supply'), "| holders:", info.get('holders'), "| decimals:", info.get('decimals'))
    time.sleep(1.5)
    d, body = get(f"https://eth.blockscout.com/api/v2/tokens/{addr}/holders", f"bs_{name}_holders_p1.json")
    if d:
        items = d.get('items', [])
        print("   holders page 1:", len(items), "éléments; next_page_params:", bool(d.get('next_page_params')))
        if items:
            print("   exemple item0:", json.dumps(items[0])[:220])
            # top-10 brut (value = unités brutes)
            vals = []
            for it in items:
                try: vals.append(int(it.get('value', 0)))
                except Exception: pass
            tot_p1 = sum(vals)
            if tot_p1 > 0 and info and info.get('total_supply'):
                sup = int(info['total_supply'])
                top10 = sum(sorted(vals, reverse=True)[:10])
                print(f"   page1: {len(vals)} comptes, valeur cumulée page1/supply = {tot_p1/sup:.4%}")
            # décodage des champs pour un item
            if items:
                print("   clés item:", sorted(items[0].keys()))
    time.sleep(2)

print("===== Etherscan v2 (tokenholderlist) sans clé =====")
d, body = get("https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenholderlist&contractaddress=0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7&page=1&offset=100", "es_v2_holders_nokey.json")
print("   corps:", body[:300])
time.sleep(2)
d, body = get("https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenholderlist&contractaddress=0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7&page=1&offset=100&apikey=YourApiKeyToken", "es_v2_holders_dummykey.json")
print("   corps:", body[:300])
time.sleep(2)
d, body = get("https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenbalance&contractaddress=0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7&address=0x0000000000000000000000000000000000000000&tag=latest", "es_v2_tokenbalance_nokey.json")
print("   corps (tokenbalance):", body[:300])
