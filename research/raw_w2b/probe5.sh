echo "### A. Blockscout proxy eth_call archive (USDC/USD Chainlink @ block 16810000)"
curl -s -m 30 "https://eth.blockscout.com/api?module=proxy&action=eth_call&to=0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6&data=0xfeaf968c&tag=16810000" | head -c 400; echo
echo "### B. CoinGecko historique USDC 11-03-2023"
curl -s -m 25 "https://api.coingecko.com/api/v3/coins/usd-coin/history?date=11-03-2023&localization=false" | head -c 500; echo
echo "### C. CoinGecko simple price (multi-venues ?)"
curl -s -m 20 "https://api.coingecko.com/api/v3/simple/price?ids=usd-coin&vs_currencies=usd&include_last_updated_at=true"; echo
echo "### D. Kraken public trades USDCUSD 2023-03-11 (since=1678492800)"
curl -s -m 25 "https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=1678492800" | head -c 500; echo
echo "### E. Bitstamp OHLC USDCUSD 2023-03-11 (start=1678492800 end=1678665600 step=3600)"
curl -s -m 25 "https://www.bitstamp.net/api/v2/ohlc/usdcusd/?start=1678492800&end=1678665600&step=3600" | head -c 600; echo
echo "### F. Binance klines USDCUSDT 2023-03-11"
curl -s -m 25 "https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h&startTime=1678492800000&endTime=1678665600000&limit=5" | head -c 500; echo
echo "### G. Coinbase Exchange API candles USDC-USD 2023-03-11"
curl -s -m 25 "https://api.exchange.coinbase.com/products/USDC-USD/candles?granularity=3600&start=2023-03-11T00:00:00Z&end=2023-03-11T06:00:00Z" | head -c 400; echo
