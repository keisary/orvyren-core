#!/bin/bash
OUT=tests_rpc2_20261015.log
: > $OUT
call() { echo "### $3" >> $OUT; curl -sL -m 40 -H "Content-Type: application/json" --data "$2" "$1" -o ./r.json -w "HTTP:%{http_code} " >> $OUT 2>/dev/null; echo "RESP(500c): $(head -c 500 ./r.json | tr '\n' ' ')" >> $OUT; echo "" >> $OUT; }
D=https://eth.drpc.org
B=https://eth-mainnet.public.blastapi.io
# Aave V2 getReserveData(USDC) @ bloc 16800000 (11 mars 2023)
call "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9","data":"0x35ea6a75000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},"0x1004EC0"]}' "DRPC AaveV2 getReserveData USDC @16800000"
call "$B" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9","data":"0x35ea6a75000000000000000000000000a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"},"0x1004EC0"]}' "BLAST AaveV2 getReserveData USDC @16800000"
# stETH totalSupply @14900000 (juin 2022)
call "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84","data":"0x18160ddd"},"0xE33CB0"]}' "DRPC stETH totalSupply @14900000"
# Curve stETH pool balances @14900000 : pool 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022, balances(uint256)
call "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0xDC24316b9AE028F1497c275EB9192a3Ea0f67022","data":"0x4903b0d10000000000000000000000000000000000000000000000000000000000000000"},"0xE33CB0"]}' "DRPC Curve stETH pool balances(0) @14900000"
# log range: USDC Transfer logs 2023 (10000 blocs) via getLogs
call "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"fromBlock":"0x1004E00","toBlock":"0x10075B0","address":"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48","topics":["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]}]}' "DRPC getLogs USDC 10 000 blocs 2023"
# bloc -> date: getBlockByNumber 16800000
call "$D" '{"jsonrpc":"2.0","id":1,"method":"eth_getBlockByNumber","params":["0x1004EC0",false]}' "DRPC getBlockByNumber 16800000"
call "$B" '{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}' "BLAST blockNumber (fraicheur)"
echo "== FIN ==" >> $OUT
cat $OUT
