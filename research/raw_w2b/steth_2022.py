from orch import *
import json, datetime as dt
def w(x): return hex(x)[2:].rjust(64,'0')
POOL="0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"
FEED="0x86392dC19c0b719886221c78AB11eb8Cf5c52812"
# 2022-06-01 -> 2022-06-20 : blocs ~ 14 720 000 -> 15 100 000
rows=[]
for b in [14720000,14750000,14780000,14800000,14820000,14840000,14860000,14880000,14900000,14920000,14940000,14950000,14960000,14970000,14980000,15000000,15020000,15040000,15060000]:
    ladders={}
    for amt in [10**18,10**20,10**21]:
        r,_=call(POOL,"0x5e0d443f"+w(0)+w(1)+w(amt),hex(b))
        ladders[amt]=int(r,16)/1e18 if r else None
    c=chainlink(FEED, hex(b))
    ts=block_ts(b)
    rows.append({"block":b,"utc":dt.datetime.utcfromtimestamp(ts).isoformat()+"Z" if ts else None,
                 "get_dy_1ETH":ladders[10**18],"get_dy_100ETH":ladders[10**20],"get_dy_1000ETH":ladders[10**21],
                 "decote_1ETH_bps":(1-ladders[10**18])*1e4 if ladders[10**18] else None,
                 "decote_1000ETH_bps":(1-ladders[10**21])*1e4 if ladders[10**21] else None,
                 "chainlink_stETHETH":(c["answer_raw"]/1e18) if c else None})
    print(rows[-1])
json.dump(rows,open("steth_juin2022.json","w"),indent=1)
