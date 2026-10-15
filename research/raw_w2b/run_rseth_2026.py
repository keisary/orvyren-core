from orch import *
import json, time, datetime as dt

def ts_of(iso):
    return int(dt.datetime.strptime(iso,"%Y-%m-%dT%H:%M:%S").replace(tzinfo=dt.timezone.utc).timestamp())

bn = int(rpc("eth_blockNumber", [])[0],16)
ts_now = block_ts(bn)
target = ts_of("2026-04-18T17:35:00")
est = bn - int((ts_now-target)/12)
print("bloc actuel",bn,"ts",ts_now,"| cible",target,"| estimation bloc",est)
# affiner : trouver le bloc dont le ts est le plus proche
lo, hi = est-3000, est+3000
for _ in range(25):
    mid=(lo+hi)//2
    t=block_ts(mid)
    if t is None: break
    if t < target: lo=mid
    else: hi=mid
blk_incident = lo
t_inc = block_ts(blk_incident)
print("bloc incident:", blk_incident, dt.datetime.utcfromtimestamp(t_inc).isoformat()+"Z")

RS_ETH_ATOKEN="0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1"
RS_ETH="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
ORACLE="0x54586bE62E3c3580375aE3723C145253060Ca0C2"
WETH_ATOKEN="0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8"

def u256(x):
    return int(x,16) if x else None

rows=[]
# 33 points : toutes les 3 h du 16/04 00:00 au 20/04 12:00 UTC
start = ts_of("2026-04-16T00:00:00"); end = ts_of("2026-04-20T12:00:00")
step = (end-start)//32
for k in range(33):
    tgt = start + k*step
    # bloc approx par proportion depuis la fin de chaine
    b = bn - int((ts_now-tgt)/12)
    t=block_ts(b)
    if t is None: continue
    sup,_ = call(RS_ETH_ATOKEN,"0x18160ddd",hex(b))
    cash,_ = call(RS_ETH,"0x70a08231000000000000000000000000"+RS_ETH_ATOKEN[2:],hex(b))
    px,_  = call(ORACLE,"0xb3596f07"+"000000000000000000000000"+RS_ETH[2:],hex(b))
    wsup,_ = call(WETH_ATOKEN,"0x18160ddd",hex(b))
    if sup is None or cash is None: 
        print("manque",b); continue
    S=u256(sup)/1e18; C=u256(cash)/1e18; P=u256(px)/1e8 if px else None
    U = 1-(C/S) if S>0 else None
    rows.append({"block":b,"ts":t,"utc":dt.datetime.utcfromtimestamp(t).isoformat()+"Z",
                 "rsETH_supply":S,"rsETH_cash":C,"U":U,"oracle_px_rsETH":P,
                 "WETH_supply":u256(wsup)/1e18 if wsup else None})
    print(f"{rows[-1]['utc']} S={S:,.0f} cash={C:,.0f} U={U*100:.3f}% px={P}".replace(","," "))
    time.sleep(0.1)
json.dump({"blk_incident":blk_incident,"rows":rows}, open("aave_rseth_apr2026.json","w"), indent=1)
