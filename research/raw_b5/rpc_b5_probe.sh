#!/usr/bin/env bash
# B5 — sondes RPC Base Sepolia (lecture seule) pour la faisabilité des actions v1.
# Usage : bash rpc_b5_probe.sh   (sortie : stdout, à rediriger vers un fichier brut)
RPC=https://sepolia.base.org
USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e
WETH=0x4200000000000000000000000000000000000006

pad(){ local h="${1#0x}"; printf '%064s' "$h" | tr ' ' 0; }
jcall(){ # jcall <method> <json-params>
  curl -s --max-time 30 "$RPC" -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"$1\",\"params\":$2}"
}
eth_getCode(){ jcall eth_getCode "[\"$1\",\"latest\"]"; }

echo "=== chainId ==="; jcall eth_chainId "[]"; echo
echo "=== blockNumber ==="; jcall eth_blockNumber "[]"; echo

for A in \
  0x036CbD53842c5426634e7929541eC2318f3dCF7e \
  0x4200000000000000000000000000000000000006 \
  0x94cC0AaC535CCDB3C01d6787D6413C739ae12bc4 \
  0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24 \
  0xC5290058841028F1614F3A6F0F5816cAd0df5E27 \
  0x492E6456D9528771018DeB9E87ef7750EF184104 \
  0x27F971cb582BF9E50F397e4d29a5C7A34f11faA2 \
  0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5 \
  0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27 \
  0xE4C2330912aae4f84dfd0f6bc8de73e7d1d1b52d ; do
  CODE=$(eth_getCode "$A")
  N=$(python -c "import json,sys;c=json.loads(sys.stdin.read()).get('result') or '0x';print(len(c[2:])//2)" <<<"$CODE")
  echo "getCode $A -> $N bytes"
done

echo "=== Uniswap V3 factory getPool(USDC,WETH,3000) ==="
jcall eth_call "[{\"to\":\"0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24\",\"data\":\"0x1698ee82$(pad $USDC)$(pad $WETH)$(printf '%064x' 3000)\"},\"latest\"]"; echo
echo "=== Uniswap V3 factory getPool(USDC,WETH,500) ==="
jcall eth_call "[{\"to\":\"0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24\",\"data\":\"0x1698ee82$(pad $USDC)$(pad $WETH)$(printf '%064x' 500)\"},\"latest\"]"; echo

echo "=== Pool USDC/WETH 3000 : liquidity() + slot0() + token0/token1 ==="
POOL=$(jcall eth_call "[{\"to\":\"0x4752ba5DBc23f44D87826276BF6Fd6b1C372aD24\",\"data\":\"0x1698ee82$(pad $USDC)$(pad $WETH)$(printf '%064x' 3000)\"},\"latest\"]" | python -c "import json,sys;r=json.loads(sys.stdin.read())['result'];print('0x'+r[26:66] if len(r)>=66 else 'NONE')")
echo "pool=$POOL"
if [ "$POOL" != "0x0000000000000000000000000000000000000000" ] && [ "$POOL" != "NONE" ]; then
  jcall eth_call "[{\"to\":\"$POOL\",\"data\":\"0x1a686502\"},\"latest\"]"; echo " <- liquidity()"
  jcall eth_call "[{\"to\":\"$POOL\",\"data\":\"0x3850c7bd\"},\"latest\"]"; echo " <- slot0()"
  jcall eth_call "[{\"to\":\"$POOL\",\"data\":\"0x0dfe1681\"},\"latest\"]"; echo " <- token0()"
  jcall eth_call "[{\"to\":\"$POOL\",\"data\":\"0xd21220a7\"},\"latest\"]"; echo " <- token1()"
fi

echo "=== Aave v3 Pool candidat getReservesList() ==="
jcall eth_call "[{\"to\":\"0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27\",\"data\":\"0xd1946dbc\"},\"latest\"]"; echo
echo "=== Aave v3 Pool getReserveData(USDC) ==="
jcall eth_call "[{\"to\":\"0x8bAB6d1b75f19e9eD9fCe8b9BD338844fF79aE27\",\"data\":\"0x35ea6a75$(pad $USDC)\"},\"latest\"]"; echo

echo "=== QuoterV2 Base Sepolia: quoteExactInputSingle(USDC->WETH, 50e6, fee 3000) ==="
# quoteExactInputSingle((address,address,uint256,uint24,uint160)) selector 0xc6a5026a
jcall eth_call "[{\"to\":\"0xC5290058841028F1614F3A6F0F5816cAd0df5E27\",\"data\":\"0xc6a5026a$(pad $USDC)$(pad $WETH)$(pad 0x$(printf '%x' 50000000))$(printf '%064x' 3000)0000000000000000000000000000000000000000000000000000000000000000\"},\"latest\"]"; echo
echo "=== done ==="
