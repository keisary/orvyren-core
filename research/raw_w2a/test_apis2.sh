#!/bin/bash
OUT=tests_api_20261015.log
: > $OUT
t() { # nom, url, extra
  echo "### $1" >> $OUT
  echo "URL: $2" >> $OUT
  code=$(curl -sL -o ./resp.json -w "%{http_code}" -m 30 "$2" $3 2>/dev/null)
  echo "HTTP: $code  TAILLE: $(wc -c < ./resp.json)" >> $OUT
  echo "BODY(600c): $(head -c 600 ./resp.json | tr '\n' ' ')" >> $OUT
  echo "" >> $OUT
}
t "DeFiLlama stablecoincharts USDC(id2) all" "https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2"
t "DeFiLlama coins historical USDC 2023-03-11" "https://coins.llama.fi/prices/historical/1678492800/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
t "DeFiLlama coins chart USDC 2023-03-09..14 (minute)" "https://coins.llama.fi/chart/ethereum:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48?start=1678320000&span=200&period=1m"
t "Binance klines USDCUSDT 1m 2023-03-11" "https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1m&startTime=1678492800000&limit=3"
t "Coinbase candles USDC-USD 1m 2023-03-11" "https://api.exchange.coinbase.com/products/USDC-USD/candles?granularity=60&start=2023-03-11T00:00:00Z&end=2023-03-11T01:00:00Z"
t "Bitstamp OHLC usdcusd 1m" "https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=60&limit=3&start=1678492800"
t "Kraken Trades USDCUSD since 2023-03-11" "https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=1678492800"
t "Curve API pools ethereum (getPools)" "https://api.curve.finance/api/getPools/ethereum/main"
echo "== FIN ==" >> $OUT
cat $OUT
