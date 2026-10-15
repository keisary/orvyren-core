from orch import *
import json, datetime as dt
def ts_of(s): return int(dt.datetime.strptime(s,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())
BN,TSN,BK0,TS0 = 26195096,1792033379,16796000,1678430087
slope=(BN-BK0)/(TSN-TS0); blk=lambda ts: BK0+int((ts-TS0)*slope)
POOL="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"; RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
def cfg_of(b, pool=POOL, asset=RS):
    # Pool.getReserveData(address) selector 0x35ea6a75 -> 1er mot = configuration
    r,_=call(pool,"0x35ea6a75000000000000000000000000"+asset[2:],hex(b))
    if not r: return None
    w0=int(r[2:66],16)
    get=lambda s,n: (w0>>s)&((1<<n)-1)
    return {"raw":hex(w0),"ltv":get(0,16)/1e4,"lt_thr":get(16,16)/1e4,"liq_bonus":get(32,16)/1e4,
            "decimals":get(48,8),"isActive":bool(get(56,1)),"isFrozen":bool(get(57,1)),
            "borrowingEnabled":bool(get(58,1)),"stableBorrow":bool(get(59,1)),
            "reserveFactor":get(64,16)/1e4,"borrowCap":get(80,36),"supplyCap":get(116,36),
            "eMode":get(168,8),"isPaused":bool(get(60,1)) }
out=[]
for iso in ["2026-04-17T00:00:00","2026-04-18T12:00:00","2026-04-18T20:00:00","2026-04-19T00:00:00","2026-04-20T00:00:00","2026-04-25T00:00:00","2026-06-01T00:00:00","2026-10-14T00:00:00"]:
    b=blk(ts_of(iso)); c=cfg_of(b); print(iso,"blk",b,c); out.append({"utc":iso,"block":b,"config":c})
json.dump(out,open("aave_rseth_reserveconfig.json","w"),indent=1)
print("### Arbitrum rsETH ###")
ARB_POOL="0x794a61358D6845594F94dc1DB02A252b5b4814aD"; ARB_RS="0x4186BFC76E2E237523CBC30FD220FE055156b41F"; ARB_AT="0x6b030Ff3FB9956B1B69f475B77aE0d3Cf2CC5aFa"
def u(x): return int(x,16) if x else None
for iso in ["2026-04-17T00:00:00","2026-04-18T20:00:00","2026-04-20T00:00:00","2026-10-14T00:00:00"]:
    b=blk(ts_of(iso))
    s,_=rpc("eth_call",[{"to":ARB_AT,"data":"0x18160ddd"},hex(b)],"https://arb1.arbitrum.io/rpc")
    c,_=rpc("eth_call",[{"to":ARB_RS,"data":"0x70a08231000000000000000000000000"+ARB_AT[2:]},hex(b)],"https://arb1.arbitrum.io/rpc")
    cf=cfg_of(b, ARB_POOL, ARB_RS)
    S=u(s)/1e18 if s else None; C=u(c)/1e18 if c else None
    print(iso,"blk",b,"S=",S,"cash=",C,"U=",(1-C/S) if S else None, cf)
