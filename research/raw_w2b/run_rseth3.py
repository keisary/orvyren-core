from orch import *
import json, datetime as dt
def ts_of(s): return int(dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
BN, TSN = 26195096, 1792033379
BK0, TS0 = 16796000, 1678430087   # ancre basse verifiee (mars 2023)
slope=(BN-BK0)/(TSN-TS0)
def blk(ts): return BK0+int((ts-TS0)*slope)
print("blocs/s =",round(slope,5),"soit",round(1/slope,3),"s/bloc")
print("bloc pour 2026-04-18T17:35Z =", blk(ts_of("2026-04-18T17:35:00")))
RS_AT="0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1"; RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
ORACLE="0x54586bE62E3c3580375aE3723C145253060Ca0C2"
def u(x): return int(x,16) if x else None
rows=[]; start=ts_of("2026-04-13T00:00:00"); end=ts_of("2026-04-21T00:00:00")
for k in range(17):
    t=start+k*(end-start)//16; b=blk(t)
    sup,_=call(RS_AT,"0x18160ddd",hex(b)); cash,_=call(RS,"0x70a08231000000000000000000000000"+RS_AT[2:],hex(b))
    px,_=call(ORACLE,"0xb3596f07000000000000000000000000"+RS[2:],hex(b))
    if sup is None or cash is None: print("MISS",b); continue
    S=u(sup)/1e18; C=u(cash)/1e18; P=u(px)/1e8 if px else None
    row={"ts":t,"utc":dt.datetime.utcfromtimestamp(t).isoformat()+"Z","block":b,"rsETH_supply":S,"rsETH_cash":C,
         "U":1-(C/S) if S>0 else None,"oracle_px":P,
         "oracle_ts":None}
    rows.append(row); print(f"{row['utc'][:16]} blk={b} S={S:,.0f} cash={C:,.0f} U={100*(row['U'] or 0):.4f}% px={P}")
    json.dump({"rows":rows},open("aave_rseth_apr2026.json","w"),indent=1)
print("n rows:",len(rows))
