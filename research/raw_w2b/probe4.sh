RPC=https://ethereum.publicnode.com
call(){ curl -s -m 25 -X POST $RPC -H 'Content-Type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$1\",\"data\":\"$2\"},\"$3\"]}"; echo; }
echo "### A. Chainlink USDC/USD latestRoundData"
call 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6 0xfeaf968c latest
echo "### B. Chainlink stETH/ETH"
call 0x86392dC19c0b719886221c78AB11eb8Cf5c52812 0xfeaf968c latest
echo "### C. aEthUSDC totalSupply + USDC.balanceOf(aEthUSDC)"
call 0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c 0x18160ddd latest
call 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 0x70a0823100000000000000000000000098C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c latest
echo "### D. Curve stETH/ETH balances(0) + get_dy(0,1,1e18)"
call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 0x4903adff0000000000000000000000000000000000000000000000000000000000000000 latest
call 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022 0x5e0d443f000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000de0b6b3a7640000 latest
echo "### E. HISTORIQUE : archive ? (block 16 810 000 = 11 mars 2023)"
curl -s -m 25 -X POST $RPC -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6","data":"0xfeaf968c"},"0x10083B0"]}'; echo
echo "### F. Block 16 810 000 number check"
curl -s -m 20 -X POST $RPC -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0x10083B0",false]}' | head -c 400; echo
