RPC=https://cloudflare-eth.com
call(){ curl -s -m 20 -X POST $RPC -H 'Content-Type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$1\",\"data\":\"$2\"},\"latest\"]}"; echo; }
echo "=== A. Chainlink USDC/USD (0x8fFf...18f6) latestRoundData ==="
call 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6 0xfeaf968c
echo "=== B. Chainlink stETH/ETH (0x86392dC19c0b719886221c78AB11eb8Cf5c52812) ==="
call 0x86392dC19c0b719886221c78AB11eb8Cf5c52812 0xfeaf968c
echo "=== C. Aave V3 Pool getReserveData(USDC) ==="
call 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2 0x35ea6a75000000000000000000000000A0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 | head -c 300
echo
echo "=== D. aEthUSDC totalSupply (0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c) ==="
call 0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c 0x18160ddd
echo "=== E. USDC.balanceOf(aEthUSDC) [liquidité dispo] ==="
call 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 0x70a0823100000000000000000000000098C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c
echo "=== F. Curve stETH/ETH pool balances(0) (0xDC24316b9AE028F1497c275EB9192a3Ea0f67022) ==="
call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 0x4903adff0000000000000000000000000000000000000000000000000000000000000000
echo "=== G. Curve stETH/ETH get_dy(0,1,1e18) ==="
call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 0x5e0d443f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000de0b6b3a7640000
echo "=== H. DefiLlama historique USDC 2023-03-11 12:00 UTC (ts 1678536000) ==="
curl -s -m 25 "https://coins.llama.fi/prices/historical/1678536000/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
echo
echo "=== I. Chainlink feed registry USDC 2023-03-11 (historique : nécessite archive node) ==="
curl -s -m 20 -X POST https://ethereum.publicnode.com -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
echo
