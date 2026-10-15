from orch import *
import json
bn = int(rpc("eth_blockNumber", [])[0],16)
print("bloc actuel:", bn, "ts:", block_ts(bn))
blocks = list(range(16_796_000, 16_813_000, 1_000))
ser = feed_series("0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6", blocks, decimals=8)
json.dump(ser, open("chainlink_usdcusd_mar2023.json","w"), indent=1)
n=0
for c in ser:
    if c:
        n+=1
        print(c["block"], c["block_ts"], c["updatedAt"], c["answer"])
print("points obtenus:", n, "/", len(blocks))
