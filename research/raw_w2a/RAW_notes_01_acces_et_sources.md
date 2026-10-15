# W2-A — Notes brutes #1 : accès aux données et sources (collecté 2026-10-15)

## 1. Tests d'accès réels (exécutés le 2026-10-15, ~03:00 UTC)

### Agregateurs de prix
| Source | Endpoint testé | Résultat | Granularité / profondeur | Clé requise |
|---|---|---|---|---|
| DeFiLlama stablecoins | `https://stablecoins.llama.fi/stablecoincharts/all?stablecoin=2` | HTTP 200, 395 Ko | Journalier, USDC depuis 2018-09-11 | NON |
| DeFiLlama coins (historique) | `https://coins.llama.fi/prices/historical/1678492800/ethereum:0xA0b86...eB48` | HTTP 200 → USDC = 0.9940720751648503 au 1678492828, `confidence: 0.99` | horodatage à la seconde, point unique | NON |
| DeFiLlama coins (série) | `https://coins.llama.fi/chart/ethereum:0xA0b86...eB48?start=1678320000&span=200&period=1m` | HTTP 200, série minute réelle (1678320474 → …) | minute (`period=1m`), jusqu'à 200 points par appel | NON |
| CoinGecko API sans clé | `https://api.coingecko.com/api/v3/coins/usd-coin/market_chart/range` | **HTTP 401** — clé obligatoire depuis 2023 | — | OUI (même Demo) |
| CryptoCompare sans clé | `https://min-api.cryptocompare.com/data/v2/histominute` | **HTTP 401** | — | OUI |
| CoinCap | `https://api.coincap.io/v2/assets/usd-coin/history` | Connexion morte (HTTP 000) | — | — |
| Messari data API | `https://data.messari.io/api/v1/assets/usd-coin/metrics` | HTTP 404 (v1 retiré) | — | OUI (v2) |

### CEX — APIs publiques de marché (testées)
| Bourse | Endpoint testé | Résultat | Notes |
|---|---|---|---|
| Binance spot | `/api/v3/klines?symbol=USDCUSDT&interval=1m&startTime=1678492800000` | HTTP 200 ; première bougie renvoyée = 1678543200000 (11/03 14:00 UTC), low 0.882 | pas de données avant ~1678543200 → vérifier date de cotation USDCUSDT |
| Binance dumps | `https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1m/ETHUSDT-1m-2022-06.zip` | HTTP 200, 2 056 565 octets, Last-Modified 2022-07-01 | **dumps mensuels 1m gratuits, tout l'historique** ; aussi daily, aggTrades, bookTicker |
| OKX | `/api/v5/market/history-candles?instId=USDC-USDT&bar=1m&after=1678543300000` | HTTP 200, bougies du 11/03/2023 14:01 UTC (prix 0.9108-0.914) | historique remontant loin via pagination (`after`) |
| Kraken | `/0/public/Trades?pair=USDCUSD&since=1678492800` | HTTP 200, 68 Ko de trades horodatés à la seconde (0.9982 puis 0.998…) | trades bruts → agrégation minute possible, historique complet |
| Bitstamp | `/api/v2/ohlc/usdcusd/?step=60&start=1678492800` | HTTP 200, OHLC 1 min 0.99773 | historique complet, mais volume 0 = marché très fin |
| Bitfinex | `/v2/candles/trade:1m:tUSDCUSD/hist` | HTTP 200 mais `[]` (paire absente/delistée) ; `tUSTUSD` fonctionne | — |
| Coinbase Exchange | `/products/USDC-USD` et `/products/USDC-USDT` | **HTTP 404** (produit introuvable) ; les bougies renvoient 404 | vérifier le catalogue `/products` ; probable retrait/délestage US |

### Données on-chain (DEX / pools)
| Source | Endpoint testé | Résultat |
|---|---|---|
| Curve API | `https://api.curve.finance/api/getPools/ethereum/main` | HTTP 200, état **courant** des pools (virtualPrice, soldes implicites) ; pas d'historique |
| GeckoTerminal | `/networks/eth/pools/0xbebc.../ohlcv/minute` | HTTP 200 mais seulement très récent (ts 1792031040 ≈ oct. 2026) |
| DexScreener | `/latest/dex/pairs/ethereum/0xbebc4478...` | HTTP 200, `pairs: null` (pool non indexé/non listé) |
| The Graph (décentralisé) | `https://gateway.thegraph.com/api/subgraphs/id/JCNWR...` | HTTP 200 avec `"auth error: missing authorization header"` → clé API requise (Studio gratuit) |

### Données on-chain (état historique) — TEST DÉCISIF
| Fournisseur | Méthode | Résultat |
|---|---|---|
| **eth.drpc.org** (sans clé) | `eth_getBalance` @ bloc 12 582 912 (2021) | **HTTP 200, résultat 0x46a5954da03e864455045 (≈20,8 ETH)** → nœud ARCHIVE gratuit |
| **eth-mainnet.public.blastapi.io** (sans clé) | idem | **HTTP 200, résultat identique** |
| eth.drpc.org | `eth_call` Aave V2 `getReserveData(USDC)` @ bloc 16 800 000 (10/03/2023) | **HTTP 200** — 7 mots renvoyés, décodables (LTV 0x1F40 = 80 %, liquidityIndex 1,084, variableBorrowIndex 1,125, taux d'offre 1,44 %) |
| eth-mainnet.public.blastapi.io | idem | HTTP 200, résultat identique (cohérence inter-fournisseurs) |
| eth.drpc.org | `eth_call` stETH `totalSupply()` @ bloc 14 900 000 (juin 2022) | HTTP 200 → 4 209 818,83 stETH |
| eth.drpc.org | `eth_call` Curve stETH `balances(0)` @ bloc 14 900 000 | HTTP 200 → 303 419,75 ETH |
| eth.drpc.org | `eth_getBlockByNumber(16800000)` | HTTP 200 (hash, baseFee…) |
| eth.drpc.org | `eth_getLogs` USDC sur 10 000 blocs (2023) | **HTTP 400 « ranges over 10000 blocks are not supported on free plan »** → limiter à ≤10 000 blocs/appel |
| ethereum-rpc.publicnode.com, 1rpc.io | états historiques | HTTP 403 : « Archive requests require a personal token » |
| rpc.flashbots.net | états historiques | HTTP 200 mais `state at block ... is pruned` |
| ethereum.blockpi.network | tous | HTTP 503 « Apikey not found » |
| Etherscan v2 API | `tokentx` | HTTP 200 `{"status":"0","message":"NOTOK","result":"Missing/Invalid API Key"}` |
| Blockscout (eth.blockscout.com) | `/api/v2/tokens/…/transfers` | HTTP 200, 127 Ko JSON (transfers récents) |
| Dune API | `/api/v1/query/.../results` sans clé | HTTP 401 |
| Allium | `/api/v1/developer/...` | HTTP 403 |
| Flipside | `https://api-v2.flipsidecrypto.xyz/json-rpc` | Connexion échouée (HTTP 000) |

**Conclusion technique n°1 (vérifiée) : la reconstruction d'états historiques arbitraires est possible SANS AUCUNE CLÉ**, via eth.drpc.org / blastapi (archive + `eth_call` à un bloc ancien), avec `eth_getLogs` plafonné à 10 000 blocs par requête (donc pagination obligatoire, mais gratuite).
**Conclusion technique n°2 (vérifiée) : les séries de prix minute multi-venues sont accessibles gratuitement** : OKX (API publique paginée), Kraken (trades bruts), Bitstamp (OHLC complet), Binance (dumps mensuels/journaux + klines depuis la cotation), DeFiLlama (minute, multi-chaîne, avec score de confiance).

## 2. Coûts et licences (pages officielles consultées le 2026-10-15)
- **Dune** (https://dune.com/pricing) : Free = **lecture seule** (voir/copier dashboards et requêtes, PAS d'exécution, PAS d'API, PAS d'export) ; Analyst 65 $/mois (4 000 crédits/mois, 3 sièges) ; Plus 349 $/mois (25 000 crédits) ; Enterprise sur devis. → Dune **n'est pas utilisable gratuitement pour un pipeline reproductible**.
- **Alchemy** (https://www.alchemy.com/pricing) : Free = 30 M CU/mois, 15 req/s, toutes mainnets ; Pay-as-you-go = 0,525 $/1 M CU ; plages `eth_getLogs()` étendues réservées à l'offre Enterprise.
- **Infura** (https://docs.infura.io/concepts/archive-data/) : l'accès aux données d'archive est **activé automatiquement** sur Ethereum/Sepolia/Optimism/Arbitrum/Polygon/Celo/Sei ; « requests for archive data currently cost the same as non-archive data » (plan à crédits). Plan gratuit : quota de requêtes quotidien.
- **CoinGecko** (https://www.coingecko.com/en/api/pricing) : Demo gratuit = 10 000 appels/mois, 100/min, 1 an d'historique ; Basic 35 $/mois (2 ans d'historique, 100 k appels) ; Analyst 129 $/mois (**10 ans d'historique**) ; Lite 499 $/mois ; Pro 999 $/mois.
- **Kaiko** (https://www.kaiko.com/products/l1-l2-data) : données tick par tick CeFi/DeFi, **à partir de 1 000–2 500 $/mois** — hors budget.
- **Flipside** : palier gratuit limité (métriques), Plus ≈ 399 $/mois (source secondaire eco.com, à confirmer).
- **Allium** : entreprise, tarification « sales-led » (source : sqd.dev compare, 2026-06).

## 3. Chronologies et vérité terrain (sources primaires à horodater)

### USDC — mars 2023
- **2023-03-10 19:11 heure de la côte ouest = 2023-03-11 03:11 UTC** : tweet de Circle — https://x.com/circle/status/1634391505988206592 : « were not yet processed, $3.3 billion of the ~40 billion of USDC reserves remain at SVB ».
- Reuters 2023-03-11 : https://www.reuters.com/business/crypto-firm-circle-reveals-33-bln-exposure-silicon-valley-bank-2023-03-11/
- CNBC 2023-03-11 : https://www.cnbc.com/2023/03/11/stablecoin-usdc-breaks-dollar-peg-after-firm-reveals-it-has-3point3-billion-in-svb-exposure.html
- Circle (communiqué de sortie de crise) : https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes
- Données vérifiées : USDC sur Binance USDCUSDT touche **0,8820 $** sur la bougie 1 min ouverte à 1678543200000 (2023-03-11 14:00 UTC), volume 7,42 M ; OKX USDC-USDT ≈ 0,9108 à 14:01 UTC ; DeFiLlama USDC = 0,9941 à 03:08 UTC le 11/03.

### stETH — juin 2022
- Nansen, 2022-06-29 (rapport forensique) : https://www.nansen.ai/research/on-chain-forensics-demystifying-steth-depeg ; reprise CoinDesk : https://www.coindesk.com/business/2022/06/29/nansen-casts-blame-for-steth-de-peg-on-terra
- HTX Research (Medium) : « il ne restait qu'environ 132 000 stETH dans le pool de liquidité Curve » (relevé du 11 juin 2022).
- Données on-chain mesurées : stETH totalSupply @14 900 000 = 4 209 818,83 ; Curve stETH pool `balances(0)` @14 900 000 = 303 419,75 ETH (à confirmer sur plusieurs blocs).

### USD0++ — janvier 2025
- **Gauntlet VaultBook** (https://vaultbook.gauntlet.xyz/resources/market-volatility) : « On Jan 9, 2025, Usual Money announced… a 0.87 price floor » ; « Within 5 minutes of Usual's updated terms announcement… », puis « **Between 9:46pm on 2025-01-09 and 4:02am on 2025-01-10, we executed a series of nine transactions that withdrew all funds from the affected markets** ». → Vérité terrain d'action chiffrée, horodatée, par un acteur réel (Gauntlet).
- Blockworks : https://blockworks.com/news/usual-depeg-spurs-defi-instability ; Rekt : https://rekt.news/unusual-money (« Morpho markets crowned USD0++ king, hardcoding its value at $1. Users could borrow up to 86 % ») ; Cointelegraph via TradingView : « On Jan. 9, USD0++ dropped as low as $0.89 before reaching $0.92 ».
- Annonce Usual (source primaire) : https://usual.money/blog/usual-s-next-leap-solidifying-a-4-year-horizon-for-sustainable-growth

### xUSD / Stream Finance — novembre 2025
- Pharos Watch (https://pharos.watch/learn/case-studies/stream-elixir-contagion-2025/) : « The loss was real immediately but invisible on-chain for weeks, because the lending markets holding xUSD priced it at a fixed $1. »
- BlockEden (https://blockeden.xyz/blog/2025/11/08/m-defi-contagion/) : « Omer Goldberg, founder of Chaos Labs, observed xUSD beginning to slip from its $1.00 peg and warned his followers » ; « borrowers using xUSD collateral couldn't be liquidated due to oracle hardcoding ».
- Forum Arbitrum (2025-11-05 env.) : https://forum.arbitrum.foundation/t/update-stream-finance-xusd-situation-and-impact-assessment/30206 — exposition des marchés Morpho, Euler, Silo.
- CoinDesk 2025-11-04 : https://www.coindesk.com/markets/2025/11/04/stream-finance-faces-usd93-million-loss-launches-legal-investigation

### rsETH / KelpDAO — 18 avril 2026
- Messari (https://messari.io/report/aave-cracks-in-the-monolithic-thesis) : « After the exploit at **17:35 UTC**, the attacker borrowed WETH against unbacked rsETH… From **17:35 UTC to 19:56 UTC**, WETH deposits fell by 294k WETH, pushing the market to **100 % utilization** ».
- Galaxy (https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi) : « the 5-of-9 Protocol Emergency Guardian froze rsETH and wrsETH markets across all deployments at **18:52 UTC (77 minutes after the drain)** » ; « primary stablecoin markets reached 100 % utilization » ; « 89 567 rsETH… (53 400 sur Ethereum, 36 167 sur Arbitrum) » ; « bad debt 123,7 M$ (socialisation uniforme) ou 230,1 M$ (isolement L2) ».
- Aave Governance (rapport d'incident 2026-04-20) : https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580 — tableaux de bad debt par chaîne/réserve (Ethereum WETH 91,79 M$ ; Arbitrum 10,30 M$ ; Base 6,12 M$ ; etc.).
- Forbes 2026-04-18 : https://www.forbes.com/sites/digital-assets/2026/04/18/withdraw-now-inside-aaves-sudden-200m-bad-debt-crisis/ ; Chainalysis 2026-04-23 : https://www.chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/ ; OpenZeppelin : https://www.openzeppelin.com/news/lessons-from-kelpdao-hack ; YHackers/Yahoo 2026-04-18 : https://finance.yahoo.com/markets/crypto/articles/hackers-target-defi-protocol-kelp-205525995.html

## 4. Fichiers de tests bruts (ce dossier)
- `tests_api_20261015.log`, `tests_api_20261015_0305.log` (ou équivalents), `tests_rpc2_20261015.log`, `tests_prices2_20261015.log`, `blocs_episodes.json`.
