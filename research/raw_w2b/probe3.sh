echo "=== Chain IDs multi-chaînes ==="
for u in "https://arb1.arbitrum.io/rpc|arbitrum" "https://mainnet.optimism.io|optimism" "https://mainnet.base.org|base" "https://polygon-rpc.com|polygon" "https://ethereum.publicnode.com|ethereum-publicnode" "https://rpc.ankr.com/eth|ankr-eth" "https://eth.drpc.org|drpc-eth"; do
  url="${u%%|*}"; name="${u##*|}"
  r=$(curl -s -m 15 -X POST "$url" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}')
  echo "$name -> $r"
done
echo
echo "=== Aave Address Book (GitHub raw) ==="
curl -s -m 25 -o aave_addrbook_v3.json -w "HTTP %{http_code} size=%{size_download}\n" "https://raw.githubusercontent.com/bgd-labs/aave-address-book/main/scripts/configs/networks/ethereum.json" 
head -c 400 aave_addrbook_v3.json 2>/dev/null
echo
echo "=== Blockscout public API test ==="
curl -s -m 20 "https://eth.blockscout.com/api/v2/stats" | head -c 300
echo
echo "=== DefiLlama protocol Aave ==="
curl -s -m 25 "https://api.llama.fi/protocol/aave" | head -c 400
echo
