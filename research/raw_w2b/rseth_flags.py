from orch import *
import json, datetime as dt
def ts_of(s): return int(dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
BN,TSN,BK0,TS0 = 26195096,1792033379,16796000,1678430087
slope=(BN-BK0)/(TSN-TS0); blk=lambda ts: BK0+int((ts-TS0)*slope)
POOL="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
def flags(b):
    r,_=call(POOL,"0x3e150141000000000000000000000000"+RS[2:],hex(b))
    if not r: return None
    w=[r[2:][i*64:(i+1)*64] for i in range(11)]
    cfg=int(w[0],16)
    return {"ltv":int(w[1],16)/1e4,"liq_threshold":int(w[2],16)/1e4,"liq_bonus":int(w[3],16)/1e4,
            "decimals":int(w[4],16),"reserve_factor":int(w[5],16)/1e4,
            "usage_as_collateral":bool(int(w[6],16)),"borrowing_enabled":bool(int(w[7],16)),
            "stable_borrow_enabled":bool(int(w[8],16)),"is_active":bool(int(w[9],16)),
            "is_frozen":bool(int(w[10],16)),"cfg_raw":hex(cfg)}
out=[]
for iso in ["2026-04-17T00:00:00","2026-04-18T00:00:00","2026-04-18T18:00:00","2026-04-19T00:00:00","2026-04-20T00:00:00","2026-04-25T00:00:00","2026-05-15T00:00:00","2026-10-14T00:00:00"]:
    t=ts_of(iso); b=blk(t); f=flags(b)
    print(iso, "blk",b, f)
    out.append({"utc":iso,"block":b,"flags":f})
json.dump(out,open("aave_rseth_flags.json","w"),indent=1)
print("### USDC Aave V3 : utilisation pendant le week-end SVB (mars 2023)")
USDC_AT="0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c"; USDC="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
def u(x): return int(x,16) if x else None
ser=[]
for t in range(ts_of("2023-03-09T00:00:00"), ts_of("2023-03-14T00:00:00"), 6*3600):
    b=blk(t)
    s,_=call(USDC_AT,"0x18160ddd",hex(b)); c,_=call(USDC,"0x70a08231000000000000000000000000"+USDC_AT[2:],hex(b))
    if s is None: continue
    S=u(s)/1e6; C=u(c)/1e6
    ser.append({"utc":dt.datetime.utcfromtimestamp(t).isoformat()+"Z","block":b,"supply":S,"cash":C,"U":1-C/S})
    print(f"{ser[-1]['utc'][:16]} S={S:,.0f} cash={C:,.0f} U={100*(1-C/S):.3f}%")
json.dump(ser,open("aave_usdc_util_mar2023.json","w"),indent=1)
