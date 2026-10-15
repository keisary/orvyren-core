echo "### A. Archive candidates (eth_call @ block 16810000, Chainlink USDC/USD)"
for u in "https://eth.drpc.org" "https://1rpc.io/eth" "https://eth.merkle.io" "https://rpc.flashbots.net" "https://eth-mainnet.public.blastapi.io" "https://api.securerpc.com/v1"; do
 r=$(curl -s -m 15 -X POST "$u" -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6","data":"0xfeaf968c"},"0x10083B0"]}')
 echo "$u -> ${r:0:160}"
done
echo "### B. Bitstamp avec limit"
curl -s -m 25 "https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=100&start=1678492800&end=1678665600" | head -c 700; echo
echo "### C. Coinbase USDC-USD candles (format alternatif)"
curl -s -m 25 "https://api.exchange.coinbase.com/products/USDC-USD/candles?granularity=3600" | head -c 300; echo
echo "### D. Kraken USDCUSD 11-03-2023 entier (since=1678492800, 1 pas)"
curl -s -m 25 "https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=1678500000&count=1000" -o kraken_usdc_1678500000.json -w "HTTP %{http_code} size=%{size_download}\n"
