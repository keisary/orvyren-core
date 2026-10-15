# RAW W2-B — Famille 1 : décote de peg — collecté 2026-10-15

## Ce qui a été testé et MARCHE (endpoints vérifiés le 2026-10-15)

| Source | URL exacte testée | Résultat |
|---|---|---|
| RPC Ethereum (archive) | `https://eth.drpc.org` (POST, `eth_call` à un bloc historique) | **OK** — renvoie l'état à un bloc passé (testé bloc 16 810 000 = mars 2023) |
| RPC Ethereum (archive) | `https://eth-mainnet.public.blastapi.io` | **OK** — idem |
| RPC Ethereum (archive) | `https://ethereum.publicnode.com` | REFUSÉ : `"Archive requests require a personal token"` |
| RPC Ethereum | `https://cloudflare-eth.com` | `eth_chainId` OK mais `eth_call` → `{"code":-32603,"message":"Internal error"}` (inutilisable) |
| RPC Ethereum | `https://1rpc.io/eth` | REFUSÉ (pas d'état historique) |
| RPC Ethereum | `https://rpc.flashbots.net` | REFUSÉ (`rpc method is not whitelisted` pour `eth_call`) |
| RPC L2 | `arb1.arbitrum.io/rpc` (0xa4b1), `mainnet.optimism.io` (0xa), `mainnet.base.org` (0x2105) | **OK** |
| RPC Polygon | `polygon-rpc.com` | REFUSÉ (`API key disabled, reason: tenant disabled`) |
| Prix agrégé | `https://coins.llama.fi/prices/current/<chain>:<addr>` | **OK** — renvoie decimals, symbol, price, timestamp, **confidence** |
| Prix agrégé historique | `https://coins.llama.fi/prices/historical/<ts>/ethereum:0xA0b8...EB48` | **OK** |
| Série historique | `https://coins.llama.fi/chart/ethereum:0xA0b8...EB48?start=<ts>&span=48&period=1h` | **OK** (points horaires) |
| Offre stablecoins | `https://stablecoins.llama.fi/stablecoins?includePrices=true` | **OK** (circulating, chainCirculating, prevDay/Week/Month) |
| Venue CEX | `https://api.binance.com/api/v3/klines?symbol=USDCUSDT&interval=1h&...` | **OK** (historique 2023 accessible) |
| Venue CEX | `https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=3600&limit=1000&start=..&end=..` | **OK** (`step=60` refusé HTTP 400) |
| Venue CEX | `https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1H&...` | **OK** |
| Venue CEX | `https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=<ts>` | partiel : renvoie max 1000 trades, pagination vers le passé peu fiable (`last` = ts actuel) |
| CoinGecko | `api.coingecko.com/api/v3/coins/usd-coin/history?date=11-03-2023` | REFUSÉ : API publique limitée à 365 jours (`error_code 10012`) |
| Coinbase Exchange | `api.exchange.coinbase.com/products/USDC-USD/candles` | `{"message":"NotFound"}` |

## Mesures réelles (fenêtre 10–12 mars 2023)

### (1) Oracle on-chain Chainlink USDC/USD (`0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6`, Ethereum, 8 décimales, `latestRoundData()` = `0xfeaf968c`)
Série reconstruite par `eth_call` sur blocs d'archive (fichier `chainlink_usdcusd_mar2023.json`) :

| updatedAt (UTC) | answer |
|---|---|
| 2023-03-10 06:00:59 | 1.00019000 |
| 2023-03-10 22:27:35 | 0.99755917 |
| 2023-03-11 02:50:11 | 0.99065000 |
| 2023-03-11 06:15:47 | 0.93266951 |
| 2023-03-11 09:28:59 | 0.91000000 |
| **2023-03-11 12:59:35** | **0.90687439  ← minimum on-chain** |
| 2023-03-11 15:51:47 | 0.92240000 |
| 2023-03-11 18:48:47 | 0.95100000 |
| 2023-03-11 22:38:59 | 0.95550000 |
| 2023-03-12 02:10:11 | 0.97543404 |
| 2023-03-12 11:55:35 | 0.95760273 |

### (2) Prix par plateforme, même fenêtre (minima mesurés)

| Plateforme | Minimum mesuré | Horodatage | Méthode | Fichier |
|---|---|---|---|---|
| Binance USDC/USDT | **0.8820** (bas 1h) ; clôture 0.9129 | 2023-03-11 14:00 UTC | `api.binance.com/api/v3/klines` 1h | `venues_usdc_mar2023.json` |
| Bitstamp USDC/USD | **0.80526** (bas 1h) | 2023-03-11 07:00 UTC | `bitstamp.net/api/v2/ohlc` 1h | `venues_usdc_mar2023.json` |
| OKX USDC/USDT | **0.8698** (bas 1h) | 2023-03-11 07:00 UTC | `okx.com/api/v5/market/history-candles` 1H | `venues_usdc_mar2023.json` |
| **Agrégat DefiLlama** | **0.876675** | 2023-03-11 07:57:53 UTC | `coins.llama.fi/chart` 1h | `defillama_chart_usdc.json` |
| Kraken USDC/USD | 0.9956 (échantillon non concluant : pagination Trades renvoie des trades récents) | 2023-03-10 21:30 UTC | `api.kraken.com/0/public/Trades` | `kraken_trades_meta.json` |
| Chainlink on-chain (oracle) | **0.90687439** | 2023-03-11 12:59 UTC | `eth_call` archive | `chainlink_usdcusd_mar2023.json` |

=> **La dispersion inter-plateformes au même moment est de ~8,7 cents (0.805 Bitstamp → 0.882 Binance → 0.9069 oracle Chainlink)**, et l'oracle on-chain **sous-estime** la décote réelle d'environ 3 à 10 cents selon la référence.
=> Le chiffre « Bitstamp 0,8627 » cité dans le brief n'a **pas** été reproduit tel quel : la mesure 1h donne 0,80526 au plus bas ; « non trouvé » pour la source exacte du 0,8627 à cette granularité.
=> Le chiffre « agrégat 0,8767 » est **reproduit exactement** : DefiLlama = 0,876675 à 07:57:53Z.

## Lecture pour ORVYREN
- Une référence de peg ne peut pas être un prix unique : il faut **une distribution** (médiane + dispersion inter-venues + profondeur pondérée par volume).
- L'oracle on-chain (Chainlink) est un signal **retardé et amorti** ; il ne doit pas servir de référence de décote, seulement de détecteur de désaccord (divergence oracle vs venues = information).
- Il faut **ignorer les impressions extrêmes** de venues illiquides (Bitstamp 0,805) ou les traiter comme des signaux séparés (« stress de venue »).
