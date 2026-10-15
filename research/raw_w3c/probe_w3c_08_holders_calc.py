#!/usr/bin/env python
# W3-C — Sonde 8 : calcul top-10 / HHI à partir de Blockscout v2 (pagination), rsETH & stETH & xUSD.
import json, time, urllib.request, urllib.parse, urllib.error

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
def get(url, fn=None):
    req = urllib.request.Request(url, headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=60); code, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        code, body = e.code, e.read()
    except Exception as e:
        print(f"[ERR] {e}"); return None
    if fn: open(fn, 'wb').write(body)
    print(f"[{code}] {fn} ({len(body)} o)")
    try: return json.loads(body)
    except Exception: return None

def fetch_holders(name, addr, pages=4):
    items = []
    url = f"https://eth.blockscout.com/api/v2/tokens/{addr}/holders"
    for i in range(pages):
        d = get(url, f"bs_{name}_holders_p{i+1}.json")
        if not d: break
        items.extend(d.get('items', []))
        np = d.get('next_page_params')
        if not np: break
        url = f"https://eth.blockscout.com/api/v2/tokens/{addr}/holders?" + urllib.parse.urlencode(np)
        time.sleep(2)
    return items

TOKENS = [
    ('rsETH', '0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7', 375972018863501156200044),
    ('stETH', '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84', 9678169137034072823352053),
    ('xUSD',  '0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94', 87670453213080),
]
res = {}
for name, addr, supply in TOKENS:
    print(f"===== {name} =====")
    items = fetch_holders(name, addr)
    vals = []
    for it in items:
        a = it.get('address') or {}
        lab = a.get('name') or ''
        tags = [t.get('meta', {}).get('projectName') for t in ((a.get('metadata') or {}).get('tags') or [])]
        tags = [t for t in tags if t]
        try: v = int(it.get('value', 0))
        except Exception: v = 0
        vals.append({'hash': a.get('hash'), 'value': v, 'is_contract': a.get('is_contract'), 'label': lab, 'tags': tags})
    vals = [v for v in vals if v['value'] > 0]
    tot = sum(v['value'] for v in vals)
    top10 = sum(sorted([v['value'] for v in vals], reverse=True)[:10])
    hhi = sum((v['value']/supply)**2 for v in vals) if supply else 0
    print(f"   {len(vals)} comptes récupérés (pages), cumul = {tot/supply:.4%} du supply")
    print(f"   top-10 = {top10/supply:.4%} du supply | HHI (sur {len(vals)} comptes) = {hhi:.5f}")
    print("   top-10 :")
    for v in sorted(vals, key=lambda x: -x['value'])[:10]:
        print(f"     {v['hash']}  part={v['value']/supply:.4%}  contrat={v['is_contract']}  label={v['label'][:40]}  tags={v['tags']}")
    res[name] = {'supply': str(supply), 'n_accounts': len(vals), 'top10_share': top10/supply, 'hhi': hhi,
                 'top10': [{'hash': v['hash'], 'share': v['value']/supply, 'label': v['label'], 'tags': v['tags']} for v in sorted(vals, key=lambda x: -x['value'])[:10]]}
    time.sleep(2)

json.dump(res, open('bs_concentration_resultats.json','w'), indent=1)
print("-> bs_concentration_resultats.json")
