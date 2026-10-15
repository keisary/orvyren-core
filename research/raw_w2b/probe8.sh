RPC=https://eth.drpc.org
echo "### Chainlink USDC/USD @ blocks 2023-03-11 (archive)"
for b in 0x1006580 0x1007000 0x10079a0 0x1008300 0x1008c60 0x10095c0 0x100a000; do
  r=$(curl -s -m 20 -X POST $RPC -H 'Content-Type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6\",\"data\":\"0xfeaf968c\"},\"$b\"]}")
  echo "$b -> $r"
done
echo "### stETH/ETH feed @ blocks juin 2022 (block 14900000 = 2022-06-11)"
for b in 0xE36B780 0xE400000 0xE4A0000; do
  r=$(curl -s -m 20 -X POST $RPC -H 'Content-Type: application/json' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x86392dC19c0b719886221c78AB11eb8Cf5c52812\",\"data\":\"0xfeaf968c\"},\"$b\"]}")
  echo "$b -> ${r:0:200}"
done
