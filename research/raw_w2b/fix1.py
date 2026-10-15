from orch import *
import json
# 1) decoder description() correctement : [offset][len][data]
def sdecode(r):
    if not r or len(r)<194: return None
    try:
        off=int(r[2:66],16)
        start=2+off*2
        ln=int(r[start:start+64],16)
        return bytes.fromhex(r[start+64:start+64+ln*2]).decode('utf8','replace')
    except Exception as e: return f"ERR {e}"
for name,a in [("stETH/ETH","0x86392dC19c0b719886221c78AB11eb8Cf5c52812"),
               ("USDC/USD","0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6"),
               ("rsETH (feed Aave)","0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3")]:
    r,_=call(a,"0x7284e416")
    print(name,"->",repr(sdecode(r)))
# 2) stETH : mesure du sens VENTE (stETH->ETH) sur juin 2022
def w(x): return hex(x)[2:].rjust(64,'0')
POOL="0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"
rows=json.load(open("steth_juin2022.json"))
for rr in rows:
    b=rr["block"]; ladder={}
    for amt in [10**18,10**20,10**21]:
        r,_=call(POOL,"0x5e0d443f"+w(1)+w(0)+w(amt),hex(b))
        ladder[str(amt)]=int(r,16)/1e18 if r else None
    rr["prix_vente_1stETH"]=ladder[str(10**18)]
    rr["prix_vente_100stETH"]=ladder[str(10**20)]/100
    rr["prix_vente_1000stETH"]=ladder[str(10**21)]/1000
    rr["decote_vente_1_pct"]=round((1-ladder[str(10**18)])*100,3) if ladder[str(10**18)] else None
    rr["decote_vente_1000_pct"]=round((1-ladder[str(10**21)]/1000)*100,3) if ladder[str(10**21)] else None
    print(f"{rr['utc'][:16]} vente 1 stETH={rr['decote_vente_1_pct']}% | 1000 stETH={rr['decote_vente_1000_pct']}% | feed={rr['chainlink_stETHETH']}")
json.dump(rows,open("steth_juin2022.json","w"),indent=1)
