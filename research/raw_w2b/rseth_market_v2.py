from orch import *
import json, datetime as dt
def ts_of(s): return int(dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
A_BLK,A_TS = 24908723, ts_of("2026-04-18T19:03:59")   # ancre VÉRIFIÉE (bloc/temps lus on-chain)
S_ANCH = 12.087  # secondes/bloc mesure (2023->2026)
blk = lambda ts: A_BLK + round((ts-A_TS)/S_ANCH)
# verification de l'ancre sur 2 points
for iso in ["2026-04-17T00:00:00","2026-04-20T00:00:00"]:
    b=blk(ts_of(iso)); print("verif",iso,"blk",b,"-> ts reel",dt.datetime.utcfromtimestamp(block_ts(b)).isoformat()+"Z")
RS_AT="0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1"; RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
ORACLE="0x54586bE62E3c3580375aE3723C145253060Ca0C2"
def u(x): return int(x,16) if x else None
rows=[]
for iso in ["2026-04-16T00:00:00","2026-04-17T00:00:00","2026-04-18T00:00:00","2026-04-18T06:00:00","2026-04-18T12:00:00","2026-04-18T18:00:00","2026-04-18T19:03:00","2026-04-18T19:04:30","2026-04-19T00:00:00","2026-04-19T12:00:00","2026-04-20T06:00:00","2026-04-21T00:00:00","2026-04-25T00:00:00"]:
    t=ts_of(iso); b=blk(t)
    s,_=call(RS_AT,"0x18160ddd",hex(b)); c,_=call(RS,"0x70a08231000000000000000000000000"+RS_AT[2:],hex(b))
    px,_=call(ORACLE,"0xb3596f07000000000000000000000000"+RS[2:],hex(b))
    if s is None: print("MISS",iso); continue
    S=u(s)/1e18; C=u(c)/1e18; P=u(px)/1e8 if px else None
    row={"utc":iso,"block":b,"rsETH_supply":S,"rsETH_cash":C,"U":1-C/S,"oracle_px_usd":P}
    rows.append(row); json.dump(rows,open("aave_rseth_apr2026_v2.json","w"),indent=1)
    print(f"{iso} blk={b} S={S:,.2f} cash={C:,.2f} U={100*(1-C/S):.4f}% px={P}")
