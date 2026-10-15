from orch import *
import json, datetime as dt
def ts_of(s): return int(dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
# ancre exacte mesuree : bloc 24 908 723 = 2026-04-18T19:03:59Z
A_BLK, A_TS = 24908723, ts_of("2026-04-18T19:03:59")
slope = 0.08274  # blocs/s (calibre sur 2023-2026)
blk = lambda ts: A_BLK + round((ts-A_TS)*slope)
RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
ARB_RS="0x4186BFC76E2E237523CBC30FD220FE055156b41F"
def u(x): return int(x,16) if x else None
rows=[]
for iso in ["2026-04-01T00:00:00","2026-04-10T00:00:00","2026-04-17T00:00:00","2026-04-18T12:00:00","2026-04-18T18:00:00","2026-04-19T00:00:00","2026-04-20T00:00:00","2026-04-22T00:00:00","2026-04-25T00:00:00","2026-05-15T00:00:00","2026-10-14T00:00:00"]:
    t=ts_of(iso); b=blk(t)
    s,_=call(RS,"0x18160ddd",hex(b))
    rows.append({"utc":iso,"block":b,"rsETH_totalSupply_eth":u(s)/1e18 if s else None})
    print(iso,"blk",b,"supply ETH:",round(rows[-1]["rsETH_totalSupply_eth"],2) if s else None)
json.dump(rows,open("rseth_supply_eth_2026.json","w"),indent=1)
# multi-chaines (bloc courant)
print("### supply actuel multi-chaines (bloc courant) ###")
cur={}
for name,url,addr,dec in [("ethereum",None,RS,1e18),
                          ("arbitrum","https://arb1.arbitrum.io/rpc",ARB_RS,1e18),
                          ("optimism","https://mainnet.optimism.io",ARB_RS,1e18),
                          ("base","https://mainnet.base.org",ARB_RS,1e18)]:
    if url is None:
        r,_=call(addr,"0x18160ddd"); 
    else:
        r,_=rpc("eth_call",[{"to":addr,"data":"0x18160ddd"},"latest"],url)
    cur[name]=u(r)/dec if r else None
    print(name, addr, cur[name])
json.dump(cur,open("rseth_supply_multi_now.json","w"),indent=1)
