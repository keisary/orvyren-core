for u in https://eth.drpc.org https://eth-mainnet.public.blastapi.io; do
echo "=== $u ==="
for b in 0xE4E1C0 0xE4E1C1 0xE9E6E0 0xF00000 0x1000000 0x1130000 0x1000000; do
 r=$(curl -s -m 15 -X POST $u -H 'Content-Type: application/json' -H 'User-Agent: Mozilla/5.0' -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6\",\"data\":\"0xfeaf968c\"},\"$b\"]}")
 echo "  $b -> ${r:0:110}"
done
done
