from orch import *
import json
def w(x): return x[2:].rjust(64,'0') if x.startswith('0x') else hex(x)[2:].rjust(64,'0')
USDC="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"; USDT="0xdAC17F958D2ee523a2206206994597C13D831ec7"
print("### Uniswap V3 QuoterV2 0x61fFE014bA17989E743c5F6cB21bF9697530B21e — quoteExactInputSingle (USDC->USDT)")
for amt,label in [(1_000_000,"1 USDC"),(1_000_000_000,"1 000 USDC"),(10_000_000_000,"10 000 USDC"),(100_000_000_000,"100 000 USDC")]:
    data="0xc6a5026a"+w(USDC)+w(USDT)+w(hex(amt))+w(hex(100))+w(hex(0))
    r,u=call("0x61fFE014bA17989E743c5F6cB21bF9697530B21e",data)
    if r and len(r)>130:
        out=int(r[2:66],16); print(f"  {label}: out={out/1e6:.4f} USDT -> slip={(1-out/amt)*1e4:.2f} bps")
    else: print(f"  {label}: ECHEC {str(r)[:120]}")
print("### Curve stETH/ETH 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 — get_dy(0,1,X) [stETH->ETH]")
for amt,label in [(10**18,"1 ETH"),(10**20,"100 ETH"),(10**21,"1 000 ETH"),(10**22,"10 000 ETH")]:
    r,u=call("0xDC24316b9AE028F1497c275EB9192a3Ea0f67022","0x5e0d443f"+w(hex(0))+w(hex(1))+w(hex(amt)))
    if r: 
        out=int(r,16); print(f"  {label}: out={out/1e18:.6f} ETH -> slip={(1-out/amt)*1e4:.2f} bps")
    else: print(f"  {label}: ECHEC {str(r)[:120]}")
print("### Curve 3pool 0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7 — get_dy(1,2,X) [USDC->USDT]")
for amt,label in [(1_000_000,"1 USDC"),(10_000_000_000,"10 000 USDC"),(100_000_000_000,"100 000 USDC")]:
    r,u=call("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7","0x5e0d443f"+w(hex(1))+w(hex(2))+w(hex(amt)))
    if r:
        out=int(r,16); print(f"  {label}: out={out/1e6:.4f} USDT -> slip={(1-out/amt)*1e4:.2f} bps")
    else: print(f"  {label}: ECHEC {str(r)[:120]}")
