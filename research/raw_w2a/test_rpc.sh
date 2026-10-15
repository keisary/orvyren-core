#!/bin/bash
OUT=tests_rpc_20261015.log
: > $OUT
RPC="https://ethereum-rpc.publicnode.com"
call() { # url payload label
  echo "### $3 ($1)" >> $OUT
  curl -sL -m 30 -H "Content-Type: application/json" --data "$2" "$1" -o ./r.json -w "HTTP:%{http_code} " >> $OUT 2>/dev/null
  echo "RESP(300c): $(head -c 300 ./r.json | tr '\n' ' ')" >> $OUT
  echo "" >> $OUT
}
for U in https://ethereum-rpc.publicnode.com https://eth.llamarpc.com https://eth.drpc.org https://1rpc.io/eth https://eth-mainnet.public.blastapi.io https://rpc.flashbots.net https://ethereum.blockpi.network/v1/rpc/public; do
  call "$U" '{"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["0x00000000219ab540356cBB839Cbe05303d7705Fa","0xC00000"]}' "getBalance beacon-deposit @ bloc 12582912 (archive?)"
done
echo "=== Aave V2 getReserveData(USDC) @ bloc 16800000 (11 mars 2023) ===" >> $OUT
call "https://ethereum-rpc.publicnode.com" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9","data":"0x35ea6a75000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},"0x1004EC0"]}' "AaveV2 getReserveData USDC"
echo "=== stETH totalSupply @ bloc 14900000 (juin 2022) ===" >> $OUT
call "https://ethereum-rpc.publicnode.com" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84","data":"0x18160ddd"},"0xE33CB0"]}' "stETH totalSupply @14900000"
echo "=== eth_getLogs USDC Transfer, 1 bloc vieux (16800000) ===" >> $OUT
call "https://ethereum-rpc.publicnode.com" '{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":"0x1004E00","toBlock":"0x1004E02","address":"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48","topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]}]}' "getLogs USDC range 3 blocs 2023"
echo "=== eth_getLogs USDC Transfer, 2000 blocs (limite?) ===" >> $OUT
call "https://ethereum-rpc.publicnode.com" '{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":"0x1004E00","toBlock":"0x10055D0","address":"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48","topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]}]}' "getLogs USDC range 2000 blocs"
echo "=== eth_blockNumber + chainId ===" >> $OUT
call "https://ethereum-rpc.publicnode.com" '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' "blockNumber"
cat $OUT
