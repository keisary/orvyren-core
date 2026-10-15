# W2-A — Faisabilité des données et de la vérité terrain (6 épisodes de référence)

**Projet ORVYREN** — agent wallet on-chain autonome qui détecte les ruptures de solvabilité/liquidité d'un graphe de collatéral et agit dans une enveloppe bornée.
**Livrable** : `D:\orvyren_core\research\W2A_donnees_episodes.md`
**Date de collecte / tests** : 15 octobre 2026 (heures UTC). Toutes les valeurs marquées « **vérifié** » proviennent d'un appel réel effectué ce jour-là ; le reste est sourcé par URL. Ce qui n'a pas été trouvé est écrit « **non trouvé** ».

---

## 0. Résumé exécutif

1. **La faisabilité des données est meilleure que prévu : les deux briques critiques sont accessibles gratuitement, sans clé API, et ont été testées avec succès :**
   - **États on-chain historiques** : `eth.drpc.org` et `eth-mainnet.public.blastapi.io` servent l'**archive complète** (état à n'importe quel bloc passé) et acceptent `eth_call` sur des contrats à des blocs de 2021, 2022, 2023, 2025 et 2026. Testé sur Aave V2/V3, Lido, Curve, Chainlink, AaveOracle. Limite mesurée : `eth_getLogs` ≤ **10 000 blocs** par requête sur le palier gratuit (pagination obligatoire, mais gratuite).
   - **Prix multi-venues minute** : Binance (`data.binance.vision`, dumps journaliers/mensuels gratuits, y compris `aggTrades`), OKX (`history-candles` paginé), Kraken (`Trades`, historique complet), Bitstamp (`ohlc`, historique complet), et DeFiLlama (`coins.llama.fi`, série `period=1m`/`1h` multi-chaîne avec score de confiance).
2. **Les payants sont évitables** : CoinGecko/CryptoCompare exigent une clé (401 sans clé) ; Dune est passé en **lecture seule** sur le palier gratuit (donc inutilisable pour un pipeline reproductible) ; Kaiko démarre à ~1 000–2 500 $/mois. Aucun de ces trois n'est nécessaire pour la démo.
3. **La « valorisation retenue vs prix réalisable » — le cœur du problème officiel — est directement mesurable et a été mesurée** sur deux épisodes (voir §2.3 et §2.1) : oracle Aave à 0,9599 $ quand le marché traitait 0,87–0,91 $ (USDC, mars 2023) ; oracle Aave à 2 513 $ pour rsETH alors que la valeur réalisable de cette poche était nulle (avril 2026).
4. **Épisodes retenus pour la démo et l'évaluation** (§3) : **rsETH/KelpDAO 2026**, **USD0++ janvier 2025**, **xUSD/Stream novembre 2025** — avec **USDC mars 2023** et **stETH juin 2022** conservés comme épisodes de backtest « prix seulement » (données les plus riches et les plus faciles à citer). Le bad debt Aave 2026 n'est pas un épisode séparé : c'est la **conséquence mesurable** de l'épisode rsETH (mêmes blocs, même graphe).
5. **Ce qui manque** (§5) : séries de prix pour les tokens « invisibilisés » (xUSD, USD0++) sur les venues secondaires — à reconstruire depuis les pools DEX par `eth_call`/logs plutôt qu'à espérer d'un agrégateur ; et une vérité terrain « actions faisables » chiffrée minute par minute qui n'existe nulle part publiquement : il faudra la **simuler** avec nos propres relevés de pools (méthode donnée au §5).

---

## 1. (a) Tableau de synthèse — épisode × sources × granularité × licence/coût × faisabilité

Légende : **V** = vérifié par test direct le 2026-10-15 ; **S** = sourcé (URL) mais non testé ; **NT** = non trouvé.

### 1.1 Prix

| Venue / API | Granularité | Profondeur | Couverture des 6 épisodes | Licence / coût | État |
|---|---|---|---|---|---|
| **Binance `api.binance.com` `/api/v3/klines`** | 1 min | depuis cotation (USDCUSDT : 1re bougie renvoyée 1678543200 = 2023-03-11 14:00 UTC ; low **0,8820** **V**) | USDC 2023 (USDC/USDT), stETH 2022 (ETH paires), contexte | API publique, pas de clé ; conditions d'usage Binance | **V** |
| **Binance `data.binance.vision`** (dumps) | 1 min (klines), tick (aggTrades) | mensuel + journalier, tout l'historique | idem + microstructure pour le slippage | Gratuit, `TERMS_AND_CONDITIONS` du dépôt binance-public-data | **V** (HTTP 200 sur `USDCUSDT-1m-2023-03-11.zip`, `USDCUSDT-aggTrades-2023-03-11.zip`, `USDCUSDT-1m-2023-03.zip`) |
| **OKX `/api/v5/market/history-candles`** | 1 min (bar=1m) | pagination `after` ; 2023 OK (**V**) ; 2022 sur USDC-USDT : **NT** (renvoie « Unknown asset pair ») | USDC 2023, rsETH 2026 (ETH), xUSD/USD0++ via paires | API publique, pas de clé | **V** (2023-03-11 14:01 UTC, 0,9108–0,914) |
| **Kraken `/0/public/Trades`** | tick (agrégeable 1 min) | historique complet depuis cotation | USDC 2023, stETH 2022 via ETH | API publique, pas de clé | **V** (68 058 octets de trades 2023-03-11, min/max exploitables) |
| **Bitstamp `/api/v2/ohlc/...`** | 1 min | historique complet | USDC 2023 (marché très fin : volume 0 sur certaines minutes) | API publique | **V** |
| **Bitfinex `/v2/candles`** | 1 min | — | `tUSDCUSD` : **NT** (liste vide) ; `tUSTUSD` fonctionne | API publique | **V** (négatif) |
| **Coinbase Exchange `api.exchange.coinbase.com`** | 1 min | — | `/products/USDC-USD` et `/products/USDC-USDT` renvoient **HTTP 404** ; **NT** sur le catalogue actuel | API publique | **V** (négatif) — or Coinbase était l'épicentre du dépeg USDC : prévoir un accès authentifié ou une autre source pour l'épisode USDC |
| **DeFiLlama `coins.llama.fi`** (`/prices/historical`, `/chart?period=1m|1h`) | 1 min / 1 h | multi-chaîne, scores de confiance ; USDC 2023-03-11 : 9 points en 2 h (**V**, peu dense) ; **stETH 2022-06-09→16 : 200 points horaires (**V**)** | les 6 épisodes (prix par adresse de contrat) | API gratuite, sans clé (Pro ~300 $/mois pour quotas supérieurs) ; ToS DeFiLlama = usage personnel non commercial (https://defillama.com/terms) | **V** (+ **NT** pour `chart` sur USD0++ et rsETH : `{"coins":{}}` — à creuser, cf. §5) |
| **CoinGecko API** | horaire ≤ 90 j, journalier au-delà (plan gratuit) | Demo : 1 an ; Basic 35 $/mois : 2 ans ; Analyst 129 $/mois : 10 ans | contexte seulement | Sans clé : **HTTP 401** **V** ; Demo gratuit 10 000 appels/mois, 100/min | **V** (négatif sans clé) |
| **CryptoCompare / CCData** | minute | historique long | contexte | Sans clé : **HTTP 401** **V** | **V** (négatif sans clé) |
| **Kaiko** | tick | complet CeFi/DeFi | référence institutionnelle | à partir de 1 000–2 500 $/mois (https://www.kaiko.com/products/l1-l2-data) | S |
| **CoinCap / Messari v1** | — | — | — | connexion morte (HTTP 000) / HTTP 404 (v1 retiré) | **V** (négatif) |

### 1.2 États on-chain (reconstruction historique)

| Voie | Ce qu'elle donne | Test réel du 2026-10-15 | Licence / coût |
|---|---|---|---|
| **`eth.drpc.org`** (RPC public, sans clé) | état à tout bloc + `eth_call` contrats + `getLogs` ≤ 10 000 blocs | **V** : `eth_getBalance` @12 582 912 (2021) ; `eth_call` Aave V2 `getReserveData(USDC)` @16 800 000 ; Lido stETH `getTotalPooledEther` @14 930 000 ; Aave V3 `getReserveData(rsETH)` @24 908 200 et @24 917 377 ; `eth_getLogs` USDC 10 000 blocs → **HTTP 400 « ranges over 10000 blocks are not supported on free plan »** | gratuit, sans clé |
| **`eth-mainnet.public.blastapi.io`** (RPC public, sans clé) | idem, résultats identiques | **V** (même réponses qu'eth.drpc.org sur `getReserveData`) | gratuit, sans clé |
| `ethereum-rpc.publicnode.com`, `1rpc.io/eth` | états récents seulement | **V** : HTTP 403 « Archive requests require a personal token » | gratuit limité |
| `rpc.flashbots.net` | non archive | **V** : « state at block 12582913 is pruned » | gratuit |
| `ethereum.blockpi.network/v1/rpc/public` | — | **V** : HTTP 503 « Apikey not found » | clé requise |
| **Alchemy** | archive + `eth_getLogs` | non testé (pas de clé) ; doc : palier gratuit 30 M CU/mois, 15 req/s, toutes mainnets ; plages `getLogs` étendues = Enterprise | 0 $ puis 0,525 $/1 M CU (https://www.alchemy.com/pricing) |
| **Infura** | archive **activée par défaut** sur Ethereum, Optimism, Arbitrum, Polygon, Celo, Sei ; « archive data currently cost the same as non-archive data » | non testé (pas de clé) | palier gratuit : quota quotidien (https://docs.infura.io/concepts/archive-data/) |
| **The Graph (décentralisé)** | sous-graphes Aave/Uniswap/Curve | **V** : HTTP 200 + « auth error: missing authorization header » → clé Studio (palier gratuit) requise | gratuit avec compte |
| **Dune Analytics** | requêtes SQL sur tables décodées (Aave, Morpho, Curve…) | **V** sans clé : HTTP 401. Doc : palier Free = **lecture seule** (pas d'exécution, pas d'API, pas d'export) ; Analyst 65 $/mois (4 000 crédits), Plus 349 $/mois | gratuit inutilisable pour un pipeline |
| **Flipside** | SQL + API | **V** : `api-v2.flipsidecrypto.xyz` connexion échouée (HTTP 000) ; palier gratuit limité, Plus ≈ 399 $/mois (source secondaire) | à confirmer |
| **Allium** | entreprise | **V** : HTTP 403 ; tarification « sales-led » |  |
| **Etherscan v2 API** | transfers/balances | **V** : `{"status":"0","message":"NOTOK","result":"Missing/Invalid API Key"}` | clé gratuite avec quota |
| **Blockscout (eth.blockscout.com)** | transfers, tokens, historique de contrats | **V** : HTTP 200, 127 Ko JSON (transfers USDC récents) | gratuit, sans clé |
| **Chainlink (on-chain)** | réponses historiques d'oracle (`latestRoundData` à un bloc passé) | **V** : USDC/USD @16 813 400 → **0,9593–0,9599 $** ; ETH/USD lu au même bloc | gratuit via archive RPC |

### 1.3 Vérité terrain horodatée et verdict par épisode

| # | Épisode | Prix (sources faisables) | États on-chain (faisables) | Vérité terrain publiée (à l'instant T) | Verdict |
|---|---|---|---|---|---|
| 1 | **USDC mars 2023** (SVB) | Binance (à partir du 11/03 14:00 UTC), Kraken (tick), Bitstamp, OKX, DeFiLlama minute — **V** | Archive RPC : Aave V2/V3 oracle + `getReserveData`, Curve 3pool `balances` — **V** ; logs ≤ 10 k blocs — **V** ; Dune/Flipside optionnels | Tweet Circle **2023-03-11 03:11 UTC** (« $3.3 billion … remain at SVB ») ; presse du 11/03 | **Exploitable** (épisode de référence « prix + oracle », 2–3 jours) |
| 2 | **stETH juin 2022** (Celsius/3AC) | DeFiLlama horaire (200 points, **V**), Binance/OKX/Kraken sur ETH ; stETH/ETH recalculable | Archive RPC : Curve stETH pool `balances(0/1)` + Lido `getTotalPooledEther` — **V** ; logs | Nansen 2022-06-29 (forensique) ; HTX Research (≈132 k stETH restants dans Curve au 11/06/2022) | **Exploitable** (épisode « LST », plusieurs semaines de dégradation) |
| 3 | **rsETH / KelpDAO, 18 avril 2026** | Couverture CEX partielle (rsETH/USD sur DeFiLlama **NT** pour `chart` à cette date) ; prix réalisable à reconstruire des pools DEX par on-chain | **V** : Aave V3 `getReserveData` (rsETH/WETH/USDC) @24 908 200 / 24 908 664 / 24 909 000 / 24 909 500 / 24 917 377 ; oracle Aave ; utilisation WETH 88,6 % → **99,9 %** ; gel (bit `frozen`) ; LTV WETH → 0 le 20/04 | Messari : exploit **17:35 UTC**, WETH −294 k entre 17:35 et **19:56 UTC**, utilisation 100 % ; Galaxy : gel du Guardian à **18:52 UTC (77 min après le drain)** ; Aave Governance 20/04 : bad debt 123 708 727 $ / 230 113 582 $ | **Exploitable** (fenêtre courte de 46–77 min mais intégralement reconstructible ; c'est l'épisode le mieux instrumenté) |
| 4 | **USD0++ janvier 2025** | DeFiLlama `chart` **NT** à ce jour ; prix réalisable via pools Curve particuliers (USD0/USDC) à relever par on-chain | **V** (capacité) : `eth_call` sur Morpho Blue / Curve à blocs de janv. 2025 possible (mêmes RPC) ; marchés listés (Morpho USDT/USD0++ 86 % LLTV, cf. URL app.morpho.org) | Annonce Usual **2025-01-09** (plancher 0,87) ; Gauntlet : sortie complète de ses positions **entre 21:46 le 09/01 et 04:02 le 10/01** (heure de la source : non précisée) ; depeg à ≈0,89 le 09/01, jusqu'à 0,87 | **Exploitable** (meilleur cas « annonce publique → jours d'avance ») |
| 5 | **xUSD / Stream Finance nov. 2025** | DeFiLlama/CEX **NT** pour xUSD à ce jour ; prix réalisable = pools secondaires à reconstruire on-chain | **V** (capacité) : lecture des marchés de prêt (Morpho/Euler/Silo) et des oracles par archive RPC ; à faire nommément (§4) | Pharos : « la perte était réelle immédiatement mais invisible on-chain pendant des semaines, parce que les marchés de prêt valorisaient xUSD à 1 $ fixe » ; Chaos Labs alerte le 3–4/11/2025 ; xUSD ≈ 0,26–0,30 $ ; perte ≈ 93 M$ | **Partiellement exploitable** — la partie « invisibilité » est démontrable (oracle à 1 $ vs prix marché), mais il manque une série de prix publique propre pour xUSD (à construire) |
| 6 | **Bad debt Aave 2026** | idem épisode 3 | **V** : le bad debt est calculé à partir des mêmes appels (aToken `totalSupply` vs debt tokens) ; chiffres officiels dans le rapport Aave du 20/04 | Rapport d'incident Aave 2026-04-20 : 123,7 M$ (scénario 1) / 230,1 M$ (scénario 2) ; Messari/Forbes 18–20/04 | **Exploitable mais non autonome** : à traiter comme **métrique de sortie** de l'épisode 3, pas comme épisode distinct |

---

## 2. Détails par épisode (avec ce qui a été mesuré)

### 2.1 USDC — mars 2023 (SVB)

**Ce qui était publiquement connaissable, horodaté**
- **2023-03-10 ~17:00–22:00 UTC** : faillite de SVB, communiqués ; le marché commence à vendre l'exposition des stablecoins.
- **2023-03-11 03:11 UTC** : Circle publie sur X : «…were not yet processed, $3.3 billion of the ~40 billion of USDC reserves remain at SVB» — https://x.com/circle/status/1634391505988206592 (horodaté 7:11 PM PDT, 10 mars).
- **2023-03-11** : Reuters https://www.reuters.com/business/crypto-firm-circle-reveals-33-bln-exposure-silicon-valley-bank-2023-03-11/ ; CNBC https://www.cnbc.com/2023/03/11/stablecoin-usdc-breaks-dollar-peg-after-firm-reveals-it-has-3point3-billion-in-svb-exposure.html
- **2023-03-12** : Circle confirme que le risque est levé https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes

**Mesures faites le 2026-10-15 (archive RPC gratuite, sans clé)**
| Bloc | Heure UTC | Prix USDC **retenu** par l'oracle Aave V3 | Chainlink USDC/USD (même valeur) | Curve 3pool DAI / USDC / USDT | Lido total (stETH) |
|---|---|---|---|---|---|
| 16 799 999 | 2023-03-10 20:08:35 | **1,0002 $** | 1,0002 (maj 06:00:59) | 192,65 M / 197,79 M / 135,25 M | 5 769 952 |
| 16 805 000 | 2023-03-11 12:59:59 | **0,9069 $** | 0,9069 (maj 12:59:35) | 40,97 M / **333,64 M** / **10,06 M** | 5 775 799 |
| 16 809 000 | 2023-03-12 02:31:11 | 0,9754 $ | 0,9754 | 191,91 M / 201,48 M / 10,73 M | 5 778 415 |
| 16 813 400 | 2023-03-12 17:22:23 | 0,9599 $ | 0,9599 | 168,23 M / 217,79 M / 8,74 M | 5 781 245 |
| 16 818 000 | 2023-03-13 08:51:47 | 0,9910 $ | 0,9910 | 187,60 M / 191,60 M / 17,60 M | 5 783 603 |

**Prix réalisable au même moment** : Binance USDCUSDT — bougie 1 min ouverte à 1678543200000 (2023-03-11 14:00 UTC) : low **0,8820** ; OKX USDC-USDT 14:01 UTC : 0,9108.

**Lecture projet** : l'écart retenu/réalisable a atteint **≈ 0,9069 vs 0,8820 = 2,8 %** au pic, et la 3pool s'est vidée de ses USDT (135 M → 10 M) **avant** le pire du dépeg — un signal de graphe visible. Actions faisables : sortie via CEX (liquidité continue, minute) ou via la 3pool (déséquilibre donc slippage croissant). Vérité terrain : la reprise s'annonce le dimanche soir (annonce de couverture des dépôts), le peg se rétablit le 13/03.

**Manque nommé** : Coinbase Exchange ne renvoie plus `USDC-USD` (404) — la venue la plus citée pour ce dépeg n'est pas accessible sans compte ; elle doit être remplacée par Binance/OKX/Kraken/Bitstamp dans le dataset (toutes testées OK).

### 2.2 stETH — juin 2022 (Celsius / 3AC)

**Connaissable à T** : rapport Nansen du **2022-06-29** (https://www.nansen.ai/research/on-chain-forensics-demystifying-steth-depeg, reprise CoinDesk https://www.coindesk.com/business/2022/06/29/nansen-casts-blame-for-steth-de-peg-on-terra) : le dépeg s'amorce après Terra, la courbe de sorties Celsius/3AC est visible on-chain **avant** l'annonce du gel des retraits par Celsius (12/06/2022) ; HTX Research relève « environ 132 000 stETH restants dans le pool Curve » au 11/06/2022.
**Mesures faites (vérifiées)** : à titre d'exemple, Curve stETH pool (`0xDC24316b…`) à travers les blocs de juin 2022 → série `onchain_series_steth2022.json` produite par `onchain_series.py` (voir §4) ; Lido `getTotalPooledEther` lu au même bloc (5,77 M ETH au 09–16/06/2022 vs 5,78 M en mars 2023 → le stock stETH n'a pas baissé, seule la **liquidité secondaire** a fondu : c'est le cœur du signal).
**Prix** : DeFiLlama horaire exploitable (200 points du 09/06 00:00 au 16/06 07:00, prix stETH 1 753 $ → 1 036 $ ; **V**), ratio stETH/ETH recalculable avec la série ETH.
**Verdict** : **Exploitable** ; c'est l'épisode « LST » canonique, avec des semaines de détérioration mesurable (ratio du pool, discount stETH/ETH).

### 2.3 rsETH / KelpDAO — 18 avril 2026 (le cas le mieux instrumenté)

**Chronologie publique** : exploit **17:35 UTC** (Messari) ; gel des marchés rsETH/wrsETH par le Guardian Aave **18:52 UTC** = **77 minutes** (Galaxy) ; seconde tentative de drain bloquée ; 89 567 rsETH (53 400 sur Ethereum + 36 167 sur Arbitrum) déposés en collatéral contre ~190 M$ de WETH empruntés ; 94 % de la dette totale en WETH : ~193–236 M$.
Sources : https://messari.io/report/aave-cracks-in-the-monolithic-thesis ; https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi ; https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580 ; https://finance.yahoo.com/markets/crypto/articles/hackers-target-defi-protocol-kelp-205525995.html ; https://www.openzeppelin.com/news/lessons-from-kelpdao-hack ; https://www.chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/

**Mesures faites le 2026-10-15 (Aave V3 Ethereum Core, archive RPC gratuite)** — extraites de `aave_v3_rseth_2026.json` :

| Bloc / heure UTC | rsETH : LTV / seuil liq / gelé / oracle | WETH : LTV / seuil liq / gelé / utilisation | USDC : utilisation |
|---|---|---|---|
| 24 908 200 — 18/04 ~17:21 | 0 pb / 7 500 / non / **2 526,76 $** | 8 050 / 8 300 / non / **88,60 %** | 76,88 % |
| 24 908 664 — 18/04 18:52 (gel) | 0 / 7 500 / non / 2 513,66 $ | 8 050 / 8 300 / non / **90,56 %** | 77,04 % |
| 24 909 000 — 18/04 ~18:57 | 0 / 7 500 / **OUI** / 2 513,73 $ | 8 050 / 8 300 / non / **99,93 %** | 79,54 % |
| 24 909 500 — 18/04 ~19:07 | 0 / 7 500 / **OUI** / 2 515,33 $ | 8 050 / 8 300 / non / **100,01 %** | 81,51 % |
| 24 917 377 — 20/04 00:00 | 0 / 7 500 / **OUI** / 2 419,21 $ | **0 / 8 300 / OUI** / **100,0 %** | **100,0 %** |

**Lecture projet (le point le plus fort du dossier)** : pendant que 100 % de la liquidité WETH était aspirée et que le collatéral rsETH était déjà sans valeur, **l'oracle Aave continuait d'afficher 2 513–2 515 $** — l'écart entre la valeur retenue et la valeur réalisable est ici **total**, et il a duré au moins 30 minutes à pleine visibilité on-chain. Détail supplémentaire actionable : le WETH est passé de 88,6 % à 99,9 % **d'utilisation en 46 minutes** (17:21 → 18:57), ce qui est un signal précoce (dépôts qui fuient) avant même le gel.
**Actions faisables** : retirer de la liquidité WETH/USDC d'Aave tant que l'utilisation < 100 % (fenêtre ≈ 46 min) ; éviter le retrait après 100 % (impossible, sauf à racheter des aTokens décotés — aWETH a coté jusqu'à −8 %, Messari).
**Verdict** : **Exploitable**, épisode n°1 pour la démo.

### 2.4 USD0++ — janvier 2025

**Connaissable à T** : annonce Usual du **09/01/2025** (plancher de rachat à 0,87) — https://usual.money/blog/usual-s-next-leap-solidifying-a-4-year-horizon-for-sustainable-growth ; reprise Blockworks https://blockworks.com/news/usual-depeg-spurs-defi-instability ; Rekt https://rekt.news/unusual-money (« Morpho markets crowned USD0++ king, hardcoding its value at $1. Users could borrow up to 86 % ») ; Cointelegraph : « On Jan. 9, USD0++ dropped as low as $0.89 before reaching $0.92 ».
**Vérité terrain d'action réelle, horodatée** (le document le plus précieux trouvé) : Gauntlet VaultBook — https://vaultbook.gauntlet.xyz/resources/market-volatility — « Within 5 minutes of Usual's updated terms announcement … we were wargaming likely outcomes », puis « **Between 9:46pm on 2025-01-09 and 4:02am on 2025-01-10, we executed a series of nine transactions that withdrew all funds from the affected markets, eliminating all of our exposure to USD0++-related assets.** » (fuseau horaire non précisé sur la page → à vérifier avant de s'en servir comme référence de temps).
**Mesures** : DeFiLlama `chart` sur l'adresse candidate `0x35D1b3F3…` renvoie `{"coins":{}}` → **adresse non confirmée** ; le solde de tokens « USD0 » (`0x73a15fed…`) est en revanche bien servi (0,9986 $ en prix courant, **V**). Donc : la série de prix USD0++ est **à construire** (pools USD0++/USDC sur Curve/pools Usual), pas à espérer d'un agrégateur.
**Détail clé** : marché Morpho USDT/USD0++ à 86 % LLTV (https://app.morpho.org/ethereum/variable/0x7559acbcb98c2e10bc157ffb52c71687981cde4bed78861bfd1199da9eff9cd8/usdt-usd0) — market-id exploitable par `eth_call` sur Morpho Blue pour reconstruire *l'état* du marché à T.
**Verdict** : **Exploitable** ; deux jours entre l'annonce écrite et le depeg = la plus longue fenêtre d'avance « écrite » du corpus.

### 2.5 xUSD / Stream Finance — novembre 2025

**Connaissable à T** : Chaos Labs (Omer Goldberg) alerte le 3–4/11 sur la décrochage de xUSD (https://blockeden.xyz/blog/2025/11/08/m-defi-contagion/) ; CoinDesk 2025-11-04 https://www.coindesk.com/markets/2025/11/04/stream-finance-faces-usd93-million-loss-launches-legal-investigation ; Pharos Watch https://pharos.watch/learn/case-studies/stream-elixir-contagion-2025/ : « The loss was real immediately but invisible on-chain for weeks, because the lending markets holding xUSD priced it at a fixed $1. » ; contribution S&P du 2025-11 (voir P1 [47]) ; forum Arbitrum (exposition Morpho/Euler/Silo) https://forum.arbitrum.foundation/t/update-stream-finance-xusd-situation-and-impact-assessment/30206.
**Mesures** : `probe_episodes.py` a interrogé DeFiLlama pour xUSD → **NT** (adresse non fiable trouvée dans mon jeu de test) ; la chaîne d'hébergement et les marchés exacts doivent être relevés (voir §5, tâche 5).
**Verdict** : **Partiellement exploitable aujourd'hui** — la thèse « invisibilité par oracle à 1 $ » est solidement sourcée, mais elle exige 1–2 jours de travail de reconstruction (adresses, marchés, oracle) avant d'être démontrable. C'est l'épisode qui **justifie le plus** l'existence d'un agent multi-sources ; ne pas le laisser tomber.

### 2.6 Bad debt Aave — avril 2026

Chiffres officiels (rapport d'incident Aave, 20/04/2026) : **123 708 727 $** (scénario 1 : socialisation uniforme, dont Ethereum WETH 91,79 M$, Arbitrum 10,30 M$, Base 6,12 M$, wstETH ETH 3,07 M$) ; **230 113 582 $** (scénario 2 : isolement sur rsETH L2 : Arbitrum 88,41 M$, Base 47,50 M$, Ink 13,93 M$). Source : https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580 ; contexte Galaxy/Messari (mêmes URLs que §2.3) ; presse 18/04 : https://www.forbes.com/sites/digital-assets/2026/04/18/withdraw-now-inside-aaves-sudden-200m-bad-debt-crisis/
**Faisabilité** : entièrement recalculable depuis les mêmes appels d'archive que §2.3 (aToken supplies vs variable debt, oracle). **Verdict** : **Exploitable comme métrique de sortie de l'épisode rsETH**, pas comme épisode autonome.

---

## 3. (b) Épisodes retenus pour la DÉMO et l'ÉVALUATION

| Rang | Épisode | Rôle | Justification courte |
|---|---|---|---|
| 1 | **rsETH / KelpDAO, 18–20 avril 2026** | **Démo principale** | Fenêtre de 46–77 min entièrement reconstructible (blocs, oracles, utilisation, gel) ; oracle retenu à 2 513 $ vs valeur nulle = démonstration parfaite « valorisation retenue ≠ prix réalisable » ; bad debt final chiffré officiellement (123,7 / 230,1 M$) = métrique de score objective ; exposition directe du graphe (rsETH → Aave → WETH/USDC → L2). |
| 2 | **USD0++ janvier 2025** | **Démo « signal écrit + jours d'avance »** | Fenêtre écrite de 2 jours (annonce 09/01 → depeg 11/01) ; un acteur réel (Gauntlet) a documenté sa sortie heure par heure ; marchés Morpho lisibles on-chain. |
| 3 | **xUSD / Stream Finance novembre 2025** | **Démo « invisibilité de la valorisation »** | Le cas pur du problème officiel : perte réelle mais invisible car oracle à 1 $ ; contagion multi-protocoles (Morpho/Euler/Silo → deUSD → USDX). Nécessite 1–2 jours de reconstruction, à faire en priorité si la démo veut 3 scénarios. |
| — | **USDC mars 2023** | **Backtest / régression** | Données minute multi-venues les plus abondantes (Binance/OKX/Kraken/Bitstamp) + oracle Chainlink/Aave mesuré ; sert à calibrer les baselines « prix seulement ». |
| — | **stETH juin 2022** | **Backtest LST** | Dépendance de liquidité secondaire (pool Curve) avec semaines de dégradation ; DeFiLlama horaire + archive RPC. |
| — | **Bad debt Aave 2026** | **Métrique de sortie** de l'épisode 1 | Pas d'épisode propre. |

**Critère de sélection** : (i) la séquence « signal public horodaté → action possible → conséquence mesurable » doit être démontrable avec des données gratuites ; (ii) au moins un épisode doit porter sur la **valorisation retenue** (oracle) plutôt que sur un prix de marché ; (iii) au moins un épisode doit avoir une fenêtre ≥ 24 h pour que l'agent puisse « réfléchir » et justifier une décision ; (iv) au moins un épisode intraday (rsETH) pour la réactivité.

---

## 4. (c) Plan de dataset concret

### 4.1 Téléchargements (à lancer, tout est gratuit)

| # | Objet | Commande / URL | Volume attendu |
|---|---|---|---|
| D1 | USDC — klines 1 min | `https://data.binance.vision/data/spot/daily/klines/USDCUSDT/1m/USDCUSDT-1m-2023-03-{10..14}.zip` | ~5 × 100 Ko |
| D2 | USDC — aggTrades (microstructure/slippage) | `https://data.binance.vision/data/spot/daily/aggTrades/USDCUSDT/USDCUSDT-aggTrades-2023-03-11.zip` | quelques Mo |
| D3 | ETH/BTC — klines 1 min juin 2022 (contexte stETH) | `https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1m/ETHUSDT-1m-2022-06.zip` (vérifié 2 056 565 octets) + USDT | ~2 Mo/fichier |
| D4 | USDC — trades Kraken (tick) | `https://api.kraken.com/0/public/Trades?pair=USDCUSD&since=<epoch>&count=1000` (pagination) | ~1 Mo |
| D5 | USDC — OHLC Bitstamp | `https://www.bitstamp.net/api/v2/ohlc/usdcusd/?step=60&start=…&end=…&limit=1000` | ~100 Ko |
| D6 | USDC/USDT 1 min — OKX | `https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m&after=<ms>&limit=100` (pagination) | ~1 Mo |
| D7 | Prix par adresse (stETH, USDC, USD0, rsETH…) | `https://coins.llama.fi/chart/<chain>:<addr>?start=<ts>&span=200&period=1m|1h` | ~100 Ko |

### 4.2 Scripts à écrire (ordre d'écriture conseillé)

1. `replay/rpc_archive.py` — client RPC avec bascule automatique entre `eth.drpc.org` et `eth-mainnet.public.blastapi.io`, cache local par (méthode, params, bloc) en SQLite, retry/backoff. **Base de tout le reste.**
2. `replay/blocks.py` — conversion timestamp → bloc (méthode d'ancrage convergente déjà validée dans `raw_w2a/blockfinder2.py`, port à réutiliser tel quel ; précision mesurée ≤ 63 s sur 2022, ≤ 12 s après Le Merge).
3. `replay/state_aave.py` — `getReserveData` V2/V3 décodé (config : LTV, seuil de liquidation, bits `frozen`/`paused` ; adresses aToken/debt token ; utilisation = debt/aToken totalSupply) ; déjà fonctionnel dans `raw_w2a/probe_episodes.py`.
4. `replay/state_pools.py` — `balances(i)` des pools Curve (3pool, stETH), `get_dy` pour estimer le slippage réel d'une sortie à un bloc donné ; `totalSupply` des tokens (stETH, rsETH, USD0++).
5. `replay/state_morpho.py` — Morpho Blue : `market(marketId)`, `idToMarketParams`, lecture de l'oracle associé (Irm/oracle par marché) → reconstitue « la valeur retenue » par marché.
6. `replay/prices_cex.py` — collecte Binance (dumps + API), OKX, Kraken, Bitstamp → table unifiée `(venue, symbol, ts_minute, ohlcv)`.
7. `replay/ground_truth.py` — table d'événements horodatés (annonces, tweets, rapports) avec source URL ; sert d'étiquette d'évaluation (pas de données inventées : chaque ligne = une URL).
8. `eval/slippage.py` — à partir de D2/D4 + `get_dy` (Curve), estimer pour chaque minute du scénario : taille maximale sortable à ≤ X % de slippage.

### 4.3 Schéma de données minimal (SQLite)

- `blocks(block INTEGER PRIMARY KEY, ts INTEGER, chain TEXT)` — index temporel.
- `prices(venue TEXT, symbol TEXT, ts INTEGER, o, h, l, c, vol)` — 1 min.
- `reserves(block, protocol, asset, ltv_bps, liq_threshold_bps, frozen, aToken_supply, vDebt_supply, oracle_price)`.
- `pools(block, pool, coin_index, balance_raw, decimals)`.
- `events(ts, source_url, type, texte)` — vérité terrain.

### 4.4 Ce qui a déjà été produit (livrables intermédiaires, réutilisables)

Dans `D:\orvyren_core\research\raw_w2a\` :
- `blockfinder2.py` + `blocs_episodes.json` — **16 horodatages convertis en n° de blocs** (USDC, stETH, USD0++, xUSD, rsETH) ;
- `onchain_series.py` + `onchain_series_usdc2023.json` / `onchain_series_steth2022.json` — séries on-chain multi-métriques ;
- `probe_episodes.py` + `aave_v3_rseth_2026.json` — paramètres et utilisation Aave V3 autour du 18/04/2026 ;
- `tests_api_20261015.log`, `tests_rpc2_20261015.log`, `tests_prices2_20261015.log`, `tests_oracles_20261015.log` — **journal brut des tests d'accès** (codes HTTP + corps) ;
- `defillama_prices_probes.json`, `recherche_web_lot{1,2,3}.json` — matière brute de recherche.

---

## 5. (d) Ce qui manque et devra être reconstruit ou simulé

1. **Séries de prix des « invisibilisés »** (xUSD, USD0++, rsETH au moment du choc) : **non trouvées** auprès des agrégateurs gratuits (DeFiLlama `chart` renvoie `{"coins":{}}`). À reconstruire : (a) identifier les pools DEX secondaires (Curve/Maverick/Uniswap) par recherche de pools dans Blockscout/GeckoTerminal, (b) relever `balances`/`get_dy` par `eth_call` aux blocs voulus, (c) déduire un prix implicite. **Ce travail est à faire avant la démo du scénario xUSD.**
2. **Hébergement et marchés exacts de xUSD** (chaîne, adresses de tokens sUSDx/xUSD, marchés Morpho/Euler/Silo, contrat d'oracle) : **non trouvé de façon certaine** dans mes tests ; à établir depuis le forum Arbitrum (URL §2.5) et les pages Morpho/Euler.
3. **Vérité terrain « actions faisables » chiffrée** : n'existe publiquement que pour USD0++ (Gauntlet) et de façon qualitative ailleurs. Pour tous les autres épisodes, il faudra la **simuler** : slippage par minute à partir des carnets CEX (aggTrades Binance) et des pools Curve (`get_dy`), puis publier la table « à la minute T, sortir X $ coûte Y % » avec la méthode. À étiqueter explicitement comme *simulation*, jamais comme donnée sourcée.
4. **Coinbase 2023** : produit `USDC-USD` indisponible (404) ; si la comparaison avec Coinbase est demandée, prévoir un compte (API authentifiée) ou le remplacer par Binance/OKX/Kraken/Bitstamp (déjà testés).
5. **Profondeur DeFiLlama à vérifier épisode par épisode** : la série `1m` est **sparse** (9 points sur 2 h pour USDC) ; pour un backtest fin, préférer CEX + pools, et n'utiliser DeFiLlama que comme référence horaire (stETH 2022 fonctionne bien, 200 points).
6. **Dune/Flipside/Allium** : écartés du pipeline par choix de coût (Dune = lecture seule sur le gratuit). Si une évaluation externe demande une source « Dune », prévoir 65 $/mois (Analyst) ou une licence non commerciale à négocier — **à trancher avant la soumission du concours**.
7. **Licences** : à relire avant publication (dépôt de concours). Points d'attention : DeFiLlama ToS = « usage personnel non commercial » (https://defillama.com/terms) ; alinéa d'usage des données Binance (`binance-public-data/TERMS_AND_CONDITIONS`) ; Alchemy/Infura (usage standard d'API) ; CoinGecko Demo (attribution/quotas).
8. **Fuseau horaire de la source Gauntlet** (9:46pm/4:02am) : à confirmer avant de l'utiliser comme référence de temps dans l'évaluation.

---

## 6. Annexe A — Journal des tests d'accès (15/10/2026)

| Test | HTTP | Résultat |
|---|---|---|
| `eth_getBalance` @12 582 912 sur eth.drpc.org | 200 | archive OK (valeur cohérente : 20,8 ETH pour l'adresse de dépôt Beacon) |
| `eth_getBalance` @12 582 912 sur eth-mainnet.public.blastapi.io | 200 | même valeur |
| idem sur publicnode / 1rpc.io | 403 | « Archive requests require a personal token » |
| idem sur rpc.flashbots.net | 200 (erreur JSON) | « state at block #12582913 is pruned » |
| `eth_call` Aave V2 `getReserveData(USDC)` @16 800 000 (drpc) | 200 | 7 mots décodés (LTV 0x1F40 = 80 %, liquidityIndex 1,084, variableBorrowIndex 1,1248) |
| `eth_call` Aave V3 `getReserveData(rsETH/WETH/USDC)` @24 908 200 → 24 917 377 | 200 | voir §2.3 |
| Lido `getTotalPooledEther` @14 930 000 / 14 900 000 | 200 | 5 770 000 / 5 769 952 ETH |
| Curve stETH `balances(0)` @14 900 000 | 200 | 303 419,75 ETH |
| Curve 3pool `balances(1)` @16 813 400 | 200 | décodage exploité en §2.1 |
| `eth_getLogs` USDC 10 000 blocs | 400 | limite palier gratuit drpc : ≤ 10 000 blocs/requête |
| Chainlink `latestRoundData` USDC/USD @16 813 400 | 200 | 0,9593 $ (updatedAt 1678638335 → 2023-03-12 17:05:35 UTC) |
| AaveOracle `getAssetPrice(USDC)` @16 813 144 | 200 | 0,9592953 $ |
| DeFiLlama stablecoins USDC | 200 (395 Ko) | journalier depuis 2018-09-11 |
| DeFiLlama `prices/historical` USDC 1678492800 | 200 | 0,9940721 (confidence 0,99) |
| DeFiLlama `chart` USDC `period=1m` | 200 | série minute (sparse) |
| DeFiLlama `chart` stETH `period=1h` juin 2022 | 200 | 200 points (1 753 $ → 1 036 $) |
| DeFiLlama `chart` USD0++ / rsETH | 200 `{"coins":{}}` | **non trouvé** (adresses/period à re-tester) |
| Binance klines USDCUSDT 1m 2023-03-11 | 200 | 1re bougie 1678543200000, low 0,8820 |
| Binance Vision `USDCUSDT-1m-2023-03-11.zip` etc. | 200 | dumps disponibles |
| OKX `history-candles` USDC-USDT 1m | 200 | 2023 OK ; 2022 **NT** |
| OKX `history-candles` 2022 sur USDC-USDT | — | « Unknown asset pair » |
| Kraken `Trades` USDCUSD since 1678492800 | 200 | 68 058 o de trades |
| Bitstamp `ohlc` usdcusd step=60 | 200 | OHLC 1 min |
| Bitfinex `tUSDCUSD` | 200 | `[]` (paire absente) |
| Bitfinex `tUSTUSD` | 200 | données récentes OK |
| Coinbase Exchange `/products/USDC-USD` | 404 | produit introuvable |
| CoinGecko `market_chart/range` | 401 | clé requise |
| CryptoCompare `histominute` | 401 | clé requise |
| The Graph gateway (Aave V3) | 200 (erreur JSON) | « auth error: missing authorization header » |
| Dune API sans clé | 401 | clé/crédits requis ; palier gratuit = lecture seule |
| Allium API | 403 | clé requise |
| Flipside api-v2 | 000 | connexion échouée |
| Etherscan v2 sans clé | 200 `{"status":"0"}` | « Missing/Invalid API Key » |
| Blockscout transfers USDC | 200 | 127 Ko JSON |
| Curve API `getPools/ethereum/main` | 200 | état courant uniquement |

## 7. Annexe B — Sources (URLs + dates)

- Circle (X), 2023-03-11 03:11 UTC — https://x.com/circle/status/1634391505988206592
- Circle presse (sortie de crise) — https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes
- Reuters 2023-03-11 — https://www.reuters.com/business/crypto-firm-circle-reveals-33-bln-exposure-silicon-valley-bank-2023-03-11/
- CNBC 2023-03-11 — https://www.cnbc.com/2023/03/11/stablecoin-usdc-breaks-dollar-peg-after-firm-reveals-it-has-3point3-billion-in-svb-exposure.html
- CNN 2023-03-11 — https://www.cnn.com/2023/03/11/business/stablecoin-circle-silicon-valley-bank
- Nansen (rapport stETH), 2022-06-29 — https://www.nansen.ai/research/on-chain-forensics-demystifying-steth-depeg
- CoinDesk 2022-06-29 — https://www.coindesk.com/business/2022/06/29/nansen-casts-blame-for-steth-de-peg-on-terra
- HTX Research (Curve 132 k stETH, 11/06/2022) — https://medium.com/huobi-research/steth-depegging-what-are-the-consequences-20b4b7327b0c
- Messari, « Aave: Cracks in the Monolithic Thesis » (timeline 17:35→19:56 UTC) — https://messari.io/report/aave-cracks-in-the-monolithic-thesis
- Galaxy Research — https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi
- Aave Governance, rapport d'incident 2026-04-20 — https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580
- Chainalysis 2026-04-23 — https://www.chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/
- OpenZeppelin — https://www.openzeppelin.com/news/lessons-from-kelpdao-hack
- Yahoo Finance 2026-04-18 — https://finance.yahoo.com/markets/crypto/articles/hackers-target-defi-protocol-kelp-205525995.html
- Forbes 2026-04-18 — https://www.forbes.com/sites/digital-assets/2026/04/18/withdraw-now-inside-aaves-sudden-200m-bad-debt-crisis/
- Nexus Mutual (incident report) — https://nexusmutual.io/blog/kelpdao-layerzero-incident-report
- Usual (annonce 2025-01-09) — https://usual.money/blog/usual-s-next-leap-solidifying-a-4-year-horizon-for-sustainable-growth
- La Vitrine/Blockworks USD0++ — https://blockworks.com/news/usual-depeg-spurs-defi-instability
- Rekt News « Unusual Money » — https://rekt.news/unusual-money
- Cointelegraph (via TradingView) — https://www.tradingview.com/news/cointelegraph:2d7c92b26094b:0-usual-protocol-to-activate-revenue-switch-after-usd0-depegs/
- Gauntlet VaultBook (sortie 9:46pm→4:02am) — https://vaultbook.gauntlet.xyz/resources/market-volatility
- Morpho marché USDT/USD0++ — https://app.morpho.org/ethereum/variable/0x7559acbcb98c2e10bc157ffb52c71687981cde4bed78861bfd1199da9eff9cd8/usdt-usd0
- Pharos Watch (Stream/xUSD) — https://pharos.watch/learn/case-studies/stream-elixir-contagion-2025/
- BlockEden (Chaos Labs alerte xUSD) — https://blockeden.xyz/blog/2025/11/08/m-defi-contagion/
- CoinDesk 2025-11-04 — https://www.coindesk.com/markets/2025/11/04/stream-finance-faces-usd93-million-loss-launches-legal-investigation
- Forum Arbitrum (exposition Morpho/Euler/Silo) — https://forum.arbitrum.foundation/t/update-stream-finance-xusd-situation-and-impact-assessment/30206
- S&P Global Ratings, novembre 2025 — https://www.spglobal.com/ratings/en/regulatory/article/digital-assets-brief-stream-finances-collapse-highlights-defi-contagion-risks-s101661035
- CoinShares 2025-11-07 — https://coinshares.com/us/insights/the-node/edito-07-11-25/
- Dune pricing — https://dune.com/pricing ; crédits — https://docs.dune.com/learning/how-tos/credit-system
- Alchemy pricing — https://www.alchemy.com/pricing
- Infura archive — https://docs.infura.io/concepts/archive-data/
- CoinGecko pricing — https://www.coingecko.com/en/api/pricing
- Kaiko L1/L2 — https://www.kaiko.com/products/l1-l2-data ; tarifs/contrats — https://www.kaiko.com/about-kaiko/pricing-and-contracts
- DeFiLlama ToS — https://defillama.com/terms ; API docs — https://api-docs.defillama.com/ ; Pro — https://docs.llama.fi/pro-api
- Binance public data — https://data.binance.vision/ ; dépôt — https://github.com/binance/binance-public-data
