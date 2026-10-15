"""Harness ORVYREN W2-B : appels RPC + decodage Chainlink. Sauvegarde brute JSON."""
import json, time, urllib.request, os

RPCS = ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io", "https://ethereum.publicnode.com"]
OUT = os.path.dirname(os.path.abspath(__file__))

def rpc(method, params, url=None, tries=2):
    urls = [url] if url else RPCS
    last = None
    for u in urls:
        for _ in range(tries):
            try:
                body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
                req = urllib.request.Request(u, data=body, headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0 (orvyren-research)"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    j = json.loads(r.read().decode())
                if "result" in j:
                    return j["result"], u
                last = j.get("error")
            except Exception as e:
                last = str(e)
            time.sleep(1)
        time.sleep(0.3)
    return None, last

def call(to, data, block="latest"):
    return rpc("eth_call", [{"to": to, "data": data}, block])

def block_ts(bn):
    r, _ = rpc("eth_getBlockByNumber", [hex(bn), False])
    return int(r["timestamp"], 16) if r else None

def chainlink(addr, block="latest"):
    r, u = call(addr, "0xfeaf968c", block)
    if not r:
        return None
    w = r[2:]
    words = [w[i*64:(i+1)*64] for i in range(5)]
    return {"roundId": int(words[0],16), "answer_raw": int(words[1],16),
            "startedAt": int(words[2],16), "updatedAt": int(words[3],16),
            "block": block, "rpc": u}

def feed_series(addr, blocks, decimals=8):
    out = []
    for b in blocks:
        c = chainlink(addr, hex(b) if isinstance(b,int) else b)
        if c:
            c["answer"] = c["answer_raw"]/10**decimals
            c["block_ts"] = block_ts(int(c["block"],16) if str(c["block"]).startswith("0x") else c["block"])
        out.append(c)
        time.sleep(0.15)
    return out

if __name__ == "__main__":
    print("chainId:", rpc("eth_chainId", [])[0])
    print("block:", int(rpc("eth_blockNumber", [])[0], 16))
    print("USDC/USD now:", chainlink("0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6"))
