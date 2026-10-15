#!/usr/bin/env python
# W3-C — Sonde 11 : introspection schéma Morpho API + requête marché + lecture on-chain.
import json, time, urllib.request, urllib.error
from Crypto.Hash import keccak

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36', 'Accept': 'application/json'}
RPC = "https://eth.drpc.org"
def sel(sig):
    k = keccak.new(digest_bits=256); k.update(sig.encode()); return '0x' + k.hexdigest()[:8]
def gql(query, fn=None, printtxt=True):
    req = urllib.request.Request("https://blue-api.morpho.org/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = urllib.request.urlopen(req, timeout=40); body = r.read(); code = r.status
    except urllib.error.HTTPError as e:
        body, code = e.read(), e.code
    if fn: open(fn,'wb').write(body)
    if printtxt: print(f"   [{code}] {fn} {body[:600]}")
    try: return json.loads(body)
    except Exception: return None

def rpc(method, params):
    payload = {"jsonrpc":"2.0","id":1,"method":method,"params":params}
    req = urllib.request.Request(RPC, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','User-Agent':UA['User-Agent']})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=40).read()); return r.get('result'), r.get('error')
    except Exception as e: return None, str(e)

print("== introspection type Market ==")
r = gql('{ __type(name: "Market") { fields { name } } }', "morpho_api_schema_market.json", printtxt=False)
if r:
    fields = [f['name'] for f in (r.get('data',{}).get('__type',{}) or {}).get('fields',[])]
    print("   champs Market:", fields)
print()
print("== introspection type MarketState ==")
r = gql('{ __type(name: "MarketState") { fields { name } } }', "morpho_api_schema_state.json", printtxt=False)
if r:
    fields = [f['name'] for f in (r.get('data',{}).get('__type',{}) or {}).get('fields',[])]
    print("   champs MarketState:", fields)
time.sleep(1)
