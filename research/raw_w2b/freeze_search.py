from orch import *
import json, datetime as dt
POOL="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"; RS="0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
def frozen(b):
    r,_=call(POOL,"0x35ea6a75000000000000000000000000"+RS[2:],hex(b))
    if not r: return None
    w0=int(r[2:66],16); return bool((w0>>57)&1)
lo,hi=24900327,24911049
assert frozen(lo) is False, frozen(lo)
assert frozen(hi) is True, frozen(hi)
while hi-lo>1:
    mid=(lo+hi)//2
    f=frozen(mid)
    if f is None: print("miss",mid); break
    if f: hi=mid
    else: lo=mid
t_lo,t_hi=block_ts(lo),block_ts(hi)
print("dernier bloc NON gelé :",lo, dt.datetime.utcfromtimestamp(t_lo).isoformat()+"Z")
print("premier bloc GELÉ     :",hi, dt.datetime.utcfromtimestamp(t_hi).isoformat()+"Z")
json.dump({"last_unfrozen_block":lo,"last_unfrozen_utc":dt.datetime.utcfromtimestamp(t_lo).isoformat()+"Z",
           "first_frozen_block":hi,"first_frozen_utc":dt.datetime.utcfromtimestamp(t_hi).isoformat()+"Z"},
          open("aave_rseth_freeze_block.json","w"),indent=1)
