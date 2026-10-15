#!/usr/bin/env bash
# B5 — troisième passe : tags de bloc safe/finalized, gaz, quote Aave-USDC->WETH, quote direction retour.
RPC=https://sepolia.base.org
USDC_AAVE=0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f
USDC_CIRCLE=0x036CbD53842c5426634e7929541eC2318f3dCF7e
WETH=0x4200000000000000000000000000000000000006
QUOTER=0xC5290058841028F1614F3A6F0F5816cAd0df5E27

pad(){ local h="${1#0x}"; printf '%064s' "$h" | tr ' ' 0; }
jcall(){ curl -s --max-time 30 "$RPC" -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$1\",\"params\":$2}"; }

echo "=== eth_getBlockByNumber(\"finalized\") ==="
jcall eth_getBlockByNumber "[\"finalized\",false]" | head -c 400; echo
echo "=== eth_getBlockByNumber(\"safe\") ==="
jcall eth_getBlockByNumber "[\"safe\",false]" | head -c 400; echo
echo "=== eth_getBlockByNumber(\"latest\") ==="
jcall eth_getBlockByNumber "[\"latest\",false]" | python -c "import json,sys;b=json.loads(sys.stdin.read())['result'];print({k:b[k] for k in ('number','hash','timestamp','gasUsed','gasLimit','baseFeePerGas')})"
echo "=== eth_gasPrice ==="
jcall eth_gasPrice "[]"; echo
echo "=== eth_maxPriorityFeePerGas ==="
jcall eth_maxPriorityFeePerGas "[]"; echo
echo "=== slot0 du pool AaveUSDC/WETH fee 3000 ==="
jcall eth_call "[{\"to\":\"0x92266210facf124f190fbad79aa230dfb85926ce\",\"data\":\"0x3850c7bd\"},\"latest\"]"; echo
echo "=== liquidity() pool AaveUSDC/WETH 3000 ==="
jcall eth_call "[{\"to\":\"0x92266210facf124f190fbad79aa230dfb85926ce\",\"data\":\"0x1a686502\"},\"latest\"]"; echo
echo "=== QuoterV2 AaveUSDC(50e6)->WETH fee 3000 ==="
jcall eth_call "[{\"to\":\"$QUOTER\",\"data\":\"0xc6a5026a$(pad $USDC_AAVE)$(pad $WETH)$(pad 0x$(printf '%x' 50000000))$(printf '%064x' 3000)0000000000000000000000000000000000000000000000000000000000000000\"},\"latest\"]"; echo
echo "=== QuoterV2 CircleUSDC(50e6)->WETH fee 500 ==="
jcall eth_call "[{\"to\":\"$QUOTER\",\"data\":\"0xc6a5026a$(pad $USDC_CIRCLE)$(pad $WETH)$(pad 0x$(printf '%x' 50000000))$(printf '%064x' 500)0000000000000000000000000000000000000000000000000000000000000000\"},\"latest\"]"; echo
echo "=== EAS predeploy 0x42..0021 getCode ==="
jcall eth_getCode "[\"0x4200000000000000000000000000000000000021\",\"latest\"]" | head -c 80; echo
echo "=== done ==="
