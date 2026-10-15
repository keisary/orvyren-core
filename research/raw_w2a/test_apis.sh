#!/bin/bash
# W2-A tests d'accès API — 2026-10-15
OUT=tests_api_$(date +%Y%m%d_%H%M).log
t() { # nom, url, extra-curl
  echo "### $1" >> $OUT
  echo "URL: $2" >> $OUT
  code=$(curl -s -o /tmp/resp.txt -w "%{http_code}" -m 25 "$2" $3 2>/dev/null)
  echo "HTTP: $code" >> $OUT
  echo "BODY(400c): $(head -c 400 /tmp/resp.txt | tr '\n' ' ')" >> $OUT
  echo "" >> $OUT
}
# --- Prix : agrégateurs et CEX ---
t "DeFiLlama stablecoincharts USDC" "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2"
t "DeFiLlama coins historical USDC 2023-03-11" "https://coins.llama.fi/prices/historical/1678492800/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
t "Binance klines USDCUSDT 1m 2023-03-11" "https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1m&startTime=1678492800000&limit=3"
t "Coinbase candles USDC-USD 1m 2023-03-11" "https://api.exchange.coinbase.com/products/USDC-USD/candles?granularity=60&start=2023-03-11T00:00:00Z&end=2023-03-11T01:00:00Z"
t "Bitstamp OHLC usdcusd 1m" "https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=60&limit=3&start=1678492800"
t "Kraken Trades USDCUSD since 2023-03-11" "https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=1678492800"
t "CoinGecko free market_chart_range USDC 2023-03" "https://api.coingecko.com/api/v3/coins/usd-coin/market_chart/range?vs_currency=usd&from=1678406400&to=1678665600"
t "CryptoCompare histominute USDC no key" "https://min-api.cryptocompare.com/data/v2/histominute?fsym=USDC&tsym=USD&limit=5&toTs=1678492800"
t "Curve API pools ethereum" "https://api.curve.fi/api/getPools/ethereum/main"
# --- État on-chain ---
t "RPC PublicNode archive call Aave V2 (bloc 16800000)" "https://ethereum-rpc.publicnode.com"
t "RPC publicnode getBalance vieux bloc" "https://ethereum-rpc.publicnode.com"
t "Dune API sans clé" "https://api.dune.com/api/v1/query/1215383/results"
t "The Graph gateway sans clé" "https://gateway.thegraph.com/api/subgraphs/id/4xyUns7HTvYuU9Bw5Z83K7fcvyRSxTQFaEJVzzFTmn"
t "Allium docs" "https://api.allium.so/api/v1/developer/wallet/balances"
t "Flipside API sans clé" "https://api-v2.flipsidecrypto.xyz/json-rpc"
t "Etherscan v2 sans clé" "https://api.etherscan.io/v2/api?chainid=1&module=stats&action=ethsupply"
t "Blockscout eth token history (USDC transfers)" "https://eth.blockscout.com/api/v2/tokens/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48/transfers?type=ERC-20"
echo "== FIN TESTS ==" >> $OUT
cat $OUT
