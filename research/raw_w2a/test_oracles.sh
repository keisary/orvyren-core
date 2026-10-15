#!/bin/bash
OUT=tests_oracles_20261015.log
: > $OUT
c() { echo "### $3" >> $OUT; curl -sL -m 30 -H "Content-Type: application/json" --data "$2" "$1" -o ./o.json -w "HTTP:%{http_code} " >> $OUT 2>/dev/null; echo "R: $(head -c 260 ./o.json|tr '\n' ' ')" >> $OUT; echo "" >> $OUT; }
D=https://eth.drpc.org
# Aave V3 Oracle getAssetPrice(USDC) @ bloc 16813400 (11/03/2023 ~03:20 UTC) — la "valorisation retenue"
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x54586bE62E3c3580375aE3723C145253060Ca0C2","data":"0xb3596f07000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},"0x1008C58"]}' "AaveV3 Oracle getAssetPrice(USDC) @16813400"
# Chainlink ETH/USD latestRoundData @ bloc 16813400
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419","data":"0xfeaf968c"},"0x1008C58"]}' "Chainlink ETH/USD latestRoundData @16813400"
# Chainlink USDC/USD @ bloc 16813400 (feed 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6)
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6","data":"0xfeaf968c"},"0x1008C58"]}' "Chainlink USDC/USD latestRoundData @16813400"
# aUSDC (Aave V3) totalSupply @ bloc 16813400
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c","data":"0x18160ddd"},"0x1008C58"]}' "aEthUSDC totalSupply @16813400"
# Bloc 16813400 -> timestamp
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0x1008C58",false]}' "bloc 16813400 (verif date)"
# Curve 3pool balances(1)=USDC @ bloc 16813400
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7","data":"0x4903b0d10000000000000000000000000000000000000000000000000000000000000001"},"0x1008C58"]}' "Curve 3pool balances(1) USDC @16813400"
# Curve stETH pool balances(0),(1) @ bloc 14930000 (juin 2022)
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xDC24316b9AE028F1497c275EB9192a3Ea0f67022","data":"0x4903b0d10000000000000000000000000000000000000000000000000000000000000001"},"0xE3D4A0"]}' "Curve stETH balances(1) @14930000"
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0xE3D4A0",false]}' "bloc 14930000 (verif date)"
# Lido stETH getTotalPooledEther @14930000
c "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84","data":"0x37cfdaca"},"0xE3D4A0"]}' "Lido getTotalPooledEther @14930000"
echo "== FIN ==" >> $OUT; cat $OUT
