#!/usr/bin/env bash
# B5 — seconde passe : le USDC d'Aave v3 Base Sepolia != USDC Circle ; decimaux, symboles,
# pool Uniswap pour le token Aave, reserve Aave (aToken/vToken), quote de swap.
RPC=https://sepolia.base.org
USDC_CIRCLE=0x036CbD53842c5426634e7929541eC2318f3dCF7e
USDC_AAVE=0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f
WETH=0x4200000000000000000000000000000000000006
FACTORY=0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24
AAVE_POOL=0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27

pad(){ local h="${1#0x}"; printf '%064s' "$h" | tr ' ' 0; }
call(){ curl -s --max-time 30 "$RPC" -H 'content-type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$1\",\"data\":\"$2\"},\"latest\"]}"; }

echo "=== getCode [Aave test USDC, aToken, vDebtToken, PoolDataProvider, AAVE ORACLE] ==="
for A in 0xba50Cd2A20f6DA35D788639E581bca8d0B5d4D5f \
         0x10F1A9D11CDf50041f3f8cB7191CBE2f31750ACC \
         0xFB3e85601b7fEb3691bbb8779Ef0E1069E347204 \
         0xBc9f5b7E248451CdD7cA54e717a2BFe1F32b566b \
         0x943b0dE18d4abf4eF02A85912F8fc07684C141dF \
         0xE4C23309117Aa30342BFaae6c95c6478e0A4Ad00 ; do
  R=$(curl -s --max-time 30 "$RPC" -H 'content-type: application/json' \
      -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getCode\",\"params\":[\"$A\",\"latest\"]}")
  N=$(python -c "import json,sys;c=json.loads(sys.stdin.read()).get('result') or '0x';print(len(c[2:])//2)" <<<"$R")
  echo "getCode $A -> $N bytes"
done

echo "=== symbol/decimals des tokens ==="
for A in $USDC_CIRCLE $USDC_AAVE $WETH 0x0a215d8ba66387dca84b284d18c3b4ec3de6e54a 0x54114591963cf60ef3aa63befd6ec263d98145a4 0xd171b9694f7a2597ed006d41f7509aad4b485c4b 0x810d46f9a9027e28f9b01f75e2bdde839da61115 ; do
  echo "--- $A"
  echo -n "  symbol(): "; call $A 0x95d89b41; echo
  echo -n "  decimals(): "; call $A 0x313ce567; echo
done

echo "=== Uniswap getPool(AaveUSDC, WETH, 3000 / 500) ==="
call $FACTORY "0x1698ee82$(pad $USDC_AAVE)$(pad $WETH)$(printf '%064x' 3000)"; echo " <- 3000"
call $FACTORY "0x1698ee82$(pad $USDC_AAVE)$(pad $WETH)$(printf '%064x' 500)"; echo " <- 500"

echo "=== Aave getReserveData(AaveUSDC) ==="
call $AAVE_POOL "0x35ea6a75$(pad $USDC_AAVE)"; echo

echo "=== Aave getReserveData(WETH) ==="
call $AAVE_POOL "0x35ea6a75$(pad $WETH)"; echo

echo "=== done ==="
