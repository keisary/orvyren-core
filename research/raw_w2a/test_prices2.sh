#!/bin/bash
OUT=tests_prices2_20261015.log
: > $OUT
t() { echo "### $1" >> $OUT; echo "URL: $2" >> $OUT; code=$(curl -sL -o ./p.json -w "%{http_code}" -m 40 "$2" $3 2>/dev/null); echo "HTTP: $code TAILLE: $(wc -c < ./p.json)" >> $OUT; echo "BODY(400c): $(head -c 400 ./p.json | tr '\n' ' ')" >> $OUT; echo "" >> $OUT; }
t "Binance Vision klines 1m USDCUSDT 2023-03-11 (dump)" "https://data.binance.vision/data/spot/daily/klines/USDCUSDT/1m/USDCUSDT-1m-2023-03-11.zip" "-I"
t "Binance Vision monthly trades 2022-06 stETH? (ETHUSDT check)" "https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1m/ETHUSDT-1m-2022-06.zip" "-I"
t "OKX history-candles USDC-USDT 1m 2023-03-11" "https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m&after=1678543300000&limit=3"
t "Bitfinex candles tUSDCUSD 1m 2023" "https://api-pub.bitfinex.com/v2/candles/trade:1m:tUSDCUSD/hist?start=1678479000000&limit=3"
t "Bitfinex candles tUSTUSD 1m 2023" "https://api-pub.bitfinex.com/v2/candles/trade:1m:tUSTUSD/hist?start=1678479000000&limit=3"
t "Coinbase products list (USDC)" "https://api.exchange.coinbase.com/products/USDC-USD"
t "Coinbase candles USDC-USDT 1m" "https://api.exchange.coinbase.com/products/USDC-USDT/candles?granularity=60&start=2023-03-11T00:00:00Z&end=2023-03-11T01:00:00Z"
t "GeckoTerminal OHLCV pool Curve 3pool (historique?)" "https://api.geckoterminal.com/api/v2/networks/eth/pools/0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7/ohlcv/minute?aggregate=1&limit=3"
t "DexScreener pool Curve 3pool" "https://api.dexscreener.com/latest/dex/pairs/ethereum/0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7"
t "The Graph gateway sans clé (Aave V3)" "https://gateway.thegraph.com/api/subgraphs/id/JCNWRypm7FYwV8fx5HhzZtQc8EzC9WvbU6wGtGUhiHcc"
t "CoinCap API history USDC" "https://api.coincap.io/v2/assets/usd-coin/history?interval=m1&start=1678492800000&end=1678496400000"
t "Messari API v1 asset metrics (sans clé)" "https://data.messari.io/api/v1/assets/usd-coin/metrics"
t "Etherscan v2 sans clé (gettokentx USDC)" "https://api.etherscan.io/v2/api?chainid=1&module=account&action=tokentx&contractaddress=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48&page=1&offset=2&startblock=16800000&endblock=16800010&sort=asc"
t "Blockscout transfers USDC (vieux)" "https://eth.blockscout.com/api/v2/tokens/0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48/transfers"
t "DefiLlama RPC proxy archive" "https://eth.llamarpc.com"
echo "== FIN ==" >> $OUT; cat $OUT
