#!/usr/bin/env python
# W3-C — Sonde 14 : limite de plage eth_getLogs par RPC public (filtre adresse+topic0, fenêtre chargée janv. 2025).
import json, urllib.request, urllib.error, time
UA = {'User-Agent': 'Mozilla/5.0 Chrome/124', 'Content-Type': 'application/json'}
POOL = "0x00cc0523b7a2b97f1d52bea1b7a0c50027e0a706"
TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
# bloc ~2025-01-10 12:00 : on prend ~21 600 000 (à corriger) — on balaie 21 600 000..21 700 000 par tranches
RPCS = ["https://eth.drpc.org", "https://eth.merkle.io", "https://eth.llamarpc.com",
        "https://ethereum-rpc.publicnode.com", "https://eth-pokt.nodies.app", "https://rpc.mevblocker.io"]
def try_logs(rpc, frm, to):
    body = {"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":POOL,"topics":[TOPIC],"fromBlock":hex(frm),"toBlock":hex(to)}]}
    req = urllib.request.Request(rpc, data=json.dumps(body).encode(), headers=UA)
    try:
        r = urllib.request.urlopen(req, timeout=30); out = json.loads(r.read())
        if 'error' in out and out['error']: return f"ERR-JSON: {str(out['error'])[:90]}"
        return f"OK {len(out.get('result') or [])} logs"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read()[:90]}"
    except Exception as e:
        return f"EXC {str(e)[:90]}"

frm = 21_600_000
for rpc in RPCS:
    res = {}
    for span in [10, 100, 1000, 8000]:
        res[span] = try_logs(rpc, frm, frm+span-1)
        time.sleep(0.3)
    print(f"== {rpc}")
    for span, r in res.items():
        print(f"   plage {span:>5} blocs -> {r}")
