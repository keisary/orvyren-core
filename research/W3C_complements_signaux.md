# W3-C — Compléments à la table des signaux (W2-B) : séries de prix xUSD / USD0++, concentration, Compound/Morpho, plan de calibration

**Version 1 — 2026-10-15.** Auteur : sous-agent W3-C. Livrable : `D:\orvyren_core\research\W3C_complements_signaux.md`.
Matière brute, scripts et sorties : `D:\orvyren_core\research\raw_w3c\` (inventaire en fin de document). Aucun fichier existant modifié ; aucun commit git.

**Ce que « testé » signifie ici** : l'endpoint ou la méthode a été **réellement appelé le 2026-10-15** depuis l'hôte Windows (curl / Python `urllib`), et la réponse brute est sauvée dans `raw_w3c/`. `NON TROUVÉ` = testé, ne fournit pas la donnée. Les horodatages de marché sont UTC.

**Les 5 trous de W2-B traités** (§5 de `W2B_signaux_detection.md`, « Chantiers ouverts (v3) », points 3, 4, 5, 6, plus le repli USD0++) :
1. Série de prix xUSD (Stream Finance, nov. 2025) — §1.
2. Série de prix USD0++ (Usual, janv. 2025) — §2.
3. Endpoints de concentration (Blockscout v2, Etherscan v2) — §3.
4. Utilisation Compound / Morpho — §4.
5. Plan de calibration des seuils sur 12 mois — §5.

---

## §1. Trou n°1 — xUSD / Stream Finance (nov. 2025)

### 1.1 Chronologie de l'incident (sources datées, URLs complètes en §6)

| Date (2025, UTC) | Événement | Source |
|---|---|---|
| ~2 nov. | Le gestionnaire de fonds externe de Stream notifie une perte d'environ **93 M$** (« The team wrote that the fund manager notified them on Nov 2 ») | gncrypto.news |
| 3 nov. (journée) | Exploit multichaîne **Balancer** (>128 M$ retirés) ; Berachain procède à un *hard fork* d'urgence, Sonic gèle le portefeuille de l'attaquant ; Omer Goldberg (Chaos Labs), 3 nov. : « Stream Finance's xUSD began to depeg materially below its target range » | incrypted.com ; X/@omeragoldberg |
| 3 nov. | Stream **suspend dépôts et retraits** (« withdrawing all liquid assets ») ; annonce relayée ensuite avec mention du cabinet **Perkins Coie** (Keith Miller, Joseph Cutler) | bitget.com (statement du 3 nov.) ; incrypted.com (tweet du 4 nov.) |
| 4 nov. | Chute principale du marché (mesurée : §1.3) ; retraits toujours suspendus | donnée mesurée + sources ci-dessus |
| jours suivants | xUSD descend à ~0,07–0,14 $ « with almost no liquidity » ; ~**285 M$** de dette DeFi interconnectée ; ~**160 M$** de fonds utilisateurs gelés (Euler, Morpho, Silo, Gearbox) ; effondrement d'**Elixir deUSD** (65 % du backing prêté à Stream via vaults Morpho privés → deUSD ~0,015 $) ; pertes déclarées : TelosC **123,6 M$**, MEV Capital **25,4 M$** | onchainatlas.org/stream-finance/history ; cohérent avec [48][99] de P1 |
| 31 oct. (contexte) | Débat public Stream vs DefiLlama sur le TVL (« recursive looping » non compté comme TVL) ; retards de retrait signalés le week-end précédent | gncrypto.news |

**Divergence factuelle relevée (à intégrer)** : le brief et plusieurs articles parlent d'un « peg de 1,00 $ ». Or **les deux séries de marché mesurées (§1.2) cotent xUSD autour de 1,26 $ avant l'incident** (xUSD = « Staked Stream USD », version *stakée* à rendement — l'accrochage à 1 $ décrit le sous-jacent, pas le niveau de marché de xUSD). L'effondrement mesuré est de ~1,26 $ → ~0,24 $ le 4 nov., soit **−81 %**, cohérent avec « 70–90 % en quelques jours » (onchainatlas).

### 1.2 Ce qui a été testé (endpoint par endpoint) — xUSD `0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94` (Ethereum)

| Endpoint (testé le 2026-10-15) | Résultat | Verdict |
|---|---|---|
| GeckoTerminal `GET /networks/eth/tokens/<xUSD>` | 200, token reconnu (« Staked Stream USD », 6 déc.) — `gt_xusd_token.json` | ✅ |
| GeckoTerminal `GET /networks/eth/tokens/<xUSD>/pools` | 200, **20 pools** listés (Balancer v3, Uniswap v3 xUSD) — `gt_xusd_pools.json` | ✅ |
| GeckoTerminal OHLCV journalier (pool Balancer v3 `vgUSDC/xUSD` `0xae255db04ba78519f33871c557d8fd6bafdb83bd`, créé 18 sept. 2025) | 200 — **43 bougies du 26/09/2025 au 08/01/2026**, l'incident est couvert — `gt_xusd_p1_quote_day.json` | ✅ **journalier** |
| GeckoTerminal OHLCV horaire, même pool | 200 mais **1 seule bougie** (08/01/2026 11:00) ; le paramètre `before_timestamp` est refusé au-delà de **180 jours** : HTTP 401 « You can only access data from the past 180 days » (bornes testées : 01/05/2026 → 200 ; 01/03/2026 → 401) | ❌ pour nov. 2025 |
| GeckoTerminal, pools Uniswap **v4** « USDC/xUSD » créés pendant le crash (ids = PoolId 64 hex ; 7 pools 03–04/11/2025) — **erreur initiale corrigée** : mon premier test utilisait des ids tronqués (→ 404) ; avec l'id complet : 200 | ✅ **jour + heure** (v4a 3 % : 29 bougies 03/11→21/01 ; v4b 2,99 % et v4c 5 % : bougies du 04/11 05:00–06:00) — fichiers `gt_xusd_v4*_*.json` | ✅ (voir §1.3) |
| DEX Screener `GET /latest/dex/tokens/<xUSD>` | 200 mais `"pairs": null` — **aucune paire trouvée** — `ds_xusd.json` | ❌ NON TROUVÉ |
| DefiLlama `coins.llama.fi/prices/historical/<ts>/ethereum:<xUSD>` (05/11/2025) | 200 mais `{"coins":{}}` — **non suivi** — `ll_xusd_hist.json` | ❌ NON TROUVÉ |
| DefiLlama `coins.llama.fi/chart/ethereum:<xUSD>?...` (28/10→18/11/2025) | 0 point — `ll_xusd_chart_start_span.json` | ❌ NON TROUVÉ |
| DefiLlama `api.llama.fi/protocol/stream-finance` | 200, page protocole existe (chaînes : `['Ethereum']`, TVL actuel vide — protocole retiré) | ✅ (contexte) |
| **CoinGecko** `GET /coins/staked-stream-usd/market_chart/range?from=25/10&to=13/11/2025` | 200 — **457 points horaires** (25/10 00:00 → 13/11 00:00) — `cg_xusd_range_octnov.json` + CSV `cg_xusd_hourly_oct25_nov13_2025.csv` | ✅ **horaire** |
| CoinGecko `market_chart?days=365` | 200 — 236 points journaliers (15/10/2025 → 22/09/2026) — `cg_xusd_market_chart_365d.json` | ✅ |
| Reconstruction DEX par logs (pool Uniswap **v4** `USDC/xUSD` créé le 03/11/2025 21:02) | ✅ **exécutée** — 411 swaps → 41 heures actives ; 0,9518 le 03/11 21:00 vs 0,9511 CoinGecko (écart 0,07 %) — `recon_xusd_v4_hourly.csv` | ✅ (§1.4-B) |

**Course aux RPC pour `eth_getLogs` d'archive** (nécessaire à §1.4 et testé aussi pour W2-B §5) : `eth.drpc.org` plafonne les plages (400 au-delà de ~1000 blocs, message « ranges over 10000 blocks are not supported ») ; `eth-mainnet.public.blastapi.io` = **10 blocs max** ; `eth-pokt.nodies.app` = 50 blocs ; `ethereum-rpc.publicnode.com` = refuse l'archive sans jeton ; `eth.merkle.io` = 429 ; `eth.llamarpc.com` = HTTP 525 ; **`rpc.mevblocker.io` = fonctionne jusqu'à 100 000 blocs** (vérifié : 556 logs sur 100 000 blocs) — c'est le seul RPC public retenu pour les logs d'archive. Détails : `probe_w3c_14_sortie_2026-10-15.txt`.

### 1.3 Les séries réellement obtenues (chiffres mesurés)

**Série de référence — CoinGecko horaire (457 points)** ; extrait du crash (heure par heure, `raw_w3c/cg_xusd_hourly_oct25_nov13_2025.csv`) :

| Heure (UTC) | Prix xUSD ($) | Étape |
|---|---|---|
| 25/10→02/11 | 1,2600 – 1,2670 | état « normal » (aucune alerte) |
| 03/11 11:00 | 1,25266 | dernier point de calme |
| 03/11 12:00 | **1,09423** | première jambe (exploit Balancer relayé) |
| 03/11 17:00 | **0,91595** | plus bas de la journée 1 |
| 03/11 23:00 | 0,99330 | rebond partiel (+8 %) |
| 04/11 04:00 | 0,75282 | re-décrochage |
| 04/11 05:00–07:00 | 0,53557 / 0,53013 / 0,47237 | cascade |
| 04/11 08:00 | 0,27450 | −78 % vs 1,26 |
| 04/11 20:00–21:00 | **0,23926–0,23968** | plus bas du 4/11 |
| 05/11 00:00–12:00 | 0,20121–0,24483 | stabilisation basse |
| 06/11→09/11 | 0,0905–0,1765 | décote persistante |
| 10/11 | 0,0700 (min) | |
| 12/11 | 0,0669 | |
| 22/09/2026 (dernier point 365 j) | 0,02186 | effondrement quasi total (chiffre confirmé par la page CoinGecko : 0,02186 $) |

**Série de corroboration — GeckoTerminal journalier (pool Balancer v3 `vgUSDC/xUSD`)** : 03/11 close 1,18999 **low 0,84285** ; 04/11 close **0,43131** ; 09/11 0,16809 ; 13/11 0,17030 ; dernière bougie 08/01/2026 à 0,02879. Les niveaux diffèrent de CoinGecko (prix marginal du pool), **le timing de l'effondrement est identique**.

**Séries complémentaires — pools Uniswap v4 « USDC/xUSD » créés pendant le crash** (bougies GeckoTerminal, token=quote = prix xUSD en USDC ; fichiers `gt_xusd_v4*_*.json`) :
- `v4a` 3 % (PoolId `0x7224…a493`, créé 03/11 21:02) — 03/11 : o 1,02781, **l 0,44404**, c 0,86381 ; 04/11 : **l 0,14167**, c 0,24578 ; 05/11 : c 0,13895 ; puis 0,057–0,12 jusqu'au 21/01/2026.
- `v4b` 2,99 % (créé 04/11 05:19) — bougie unique du 04/11 : o 0,42331, h 0,50246, **l 0,12744**, c 0,46633 (vol 25 687 $) ; bougies horaires 05:00–06:00 (0,42→0,47).
- `v4c` 5 % (créé 04/11 05:34) — 04/11 : o 0,48950, h 0,57191, **l 0,25207**, c 0,44161 ; horaires 05:00–06:00.
- `v4d` 88 % (créé 03/11 16:00) — décroissance continue jusqu'à 0,0005–0,045 début 2026.
Convergence : ces pools post-crash cotent xUSD entre **0,13 et 0,57** le 04/11 selon la profondeur — même jour que le 0,24–0,33 de la série CoinGecko de référence.

**Critique W2-B reproduite ?** W2-B disait « aucune série de prix exploitable trouvée via les endpoints testés → non trouvé ». Conclusion W3-C : **trou comblé** — via **CoinGecko** (horaire, 11 mois après l'incident, fenêtre 365 j suffisante) et **GeckoTerminal** (journalier Balancer v3 + journalier/horaire Uniswap v4). DefiLlama et DEX Screener restent **non trouvés** pour ce token.

### 1.4 Reconstruction DEX par logs (méthode de repli testée réellement)

**Méthode commune** (`probe_w3c_13_reconstruction.py`, `probe_w3c_15_reconstruction2.py`) : lecture des événements `Swap` sur blocs d'archive, prix dérivé de `sqrtPriceX96`, horodatage par blocs (dichotomie `block_at`, ex. bloc **23 725 820 = 04/11/2025 12:00:11** ✓), agrégation horaire (dernier swap de l'heure). Sélecteurs calculés par keccak localement ; topic0 v3 vérifié contre la constante connue `0xc42079f9…bcca67`. **RPC retenu : `rpc.mevblocker.io`** — seul RPC public testé qui accepte de grandes plages de logs (100 000 blocs). Notes : `eth.drpc.org` plafonne les plages `eth_getLogs` et a en outre renvoyé des HTTP 500 intermittents sur les lots JSON-RPC (l'horodatage a été refait en séquentiel avec repli entre deux RPC) ; `eth-mainnet.public.blastapi.io` = 10 blocs max ; `eth-pokt.nodies.app` = 50 blocs ; `ethereum-rpc.publicnode.com` = archive refusée ; `eth.merkle.io` = 429 ; `eth.llamarpc.com` = 525.

**A) USD0++/USDT (Uniswap v3 `0x00cc0523…`, token0 = USD0++ 18 déc., token1 = USDT 6 déc.)** : **610 swaps** (blocs 21 576 036 → 21 608 271 = 08/01 00:00 → 12/01 12:00 UTC), **54 heures actives** → `recon_usd0pp_hourly.csv`. Validation croisée vs DefiLlama : **écart moyen 0,31 %, écart max 1,53 %** sur les 54 heures communes ; minimum reconstruit **0,90816 le 10/01 15:00** contre 0,90678 à 15:58 pour DefiLlama. Première heure négociée du pool : 10/01 01:00 à 0,94993 (avant, aucun swap sur ce pool — cohérent avec un décrochage qui s'amorce le 9 au soir sur d'autres venues).

**B) USDC/xUSD (Uniswap v4, PoolId `0x7224…a493`)** : les pools v4 ne s'écoutent pas sur un contrat de pool mais sur le **PoolManager** `0x000000000004444c5dc75cB358380D2e3dE08A90` (code présent, 48 020 octets) ; événement `Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)` filtré par `topics[1] = PoolId` → **411 swaps**, **41 heures actives** (03/11 21:00 → 05/11 23:00) → `recon_xusd_v4_hourly.csv`. Trajectoire : **0,9518 (03/11 21:00)** — vs 0,9511 CoinGecko à la même heure (écart 0,07 %) — → 0,8399 (22:00) → 1,0133 (04/11 02:00, rebond) → **0,4473 (04:00)** → 0,2910 (07:00) → 0,1889 (15:00) → 0,1344 (05/11 19:00). Niveaux plus volatils que l'agrégat CoinGecko (pool minuscule, ~2,9 k$ de liquidité) mais **même chronologie**.

**Leçon de production** : les lots JSON-RPC ne doivent jamais être « supposés OK » — les résultats incomplets doivent être comptés et alertés (un lot silencieusement vide avait produit une série vide au premier essai) ; c'est exactement le piège « un échec silencieux écrit un fichier vide » documenté dans les pratiques du projet.

---

## §2. Trou n°2 — USD0++ / Usual (janv. 2025)

### 2.1 Chronologie documentée (sources datées)

| Date (2025) | Événement | Source |
|---|---|---|
| 9–10 janv. | Usual modifie le code de USD0++ : la valeur de rachat passe de **0,995 à un plancher minimal de 0,87 $**, avec double mécanisme de sortie (« conditional exit » 1:1 contre renonciation aux récompenses ; « unconditional exit » au plancher 0,87 montant vers 1 sur 4 ans) | cointelegraph.com (« Jan. 9 » pour le mouvement de marché ; « earlier on Friday » pour la modification de code — l'article dit « Friday, Jan 11 » mais le vendredi était le 10/01) ; cryptonews.net (« On January 9… ~$0.937 ») |
| 10–11 janv. | Réaction communautaire ; Usual annonce l'activation anticipée du « revenue switch » (dès le **13 janv.**, ~5 M$/mois) et un « 1:1 Early Unstaking » la semaine suivante | cointelegraph.com (11 janv.) |
| Faits de marché (mesurés, nous) | premier passage < 0,99 le **08/01 18:57** (0,98965) ; journée du 09/01 ≈ 0,978–1,007 ; **décrochage principal le 10/01 (min 0,90678 à 15:58)** ; semaine du 13/01 stabilisée à ~0,91–0,94 puis **décote persistante** (~0,90–0,94 sur tout janvier) | série DefiLlama horaire (§2.3) |

**Correction de datation vs brief W2-B** (« dépeg du 11/01 ») : les données horaires situent le décrochage principal au **10/01** et le premier affaiblissement au **8–9/01** ; la réponse officielle (revenue switch) est du 11/01. Les articles se contredisent entre le 9 et le 10 pour la modification de code — nous rapportons les deux et la mesure.

### 2.2 Endpoints testés — USD0++ `0x35D8949372D46B7a3D5A56006AE77B215fc69bC0` (devenu bUSD0)

| Endpoint | Résultat | Verdict |
|---|---|---|
| DefiLlama `prices/historical/<ts>/ethereum:<USD0++>` | 200 — ex. 11/01/2025 12:00 → **0,913708** (confidence 0,99) — `ll_usd0pp_hist.json` | ✅ |
| DefiLlama `chart` horaire, fenêtres fusionnées (31/12/2024→02/02/2025) | 200 — **635 points horaires** (`ll_usd0pp_chart_*.json`, CSV `ll_usd0pp_hourly_jan2025.csv`). Plafond de `span` par appel : 500 OK (446 pts), 1000 → HTTP 400 | ✅ **horaire** |
| DefiLlama `chart` journalier `span=400` | 200 — 398 points (31/12/2024 → 03/02/2026) — `ll_usd0pp_chart_daily_400.json` | ✅ (12 mois+) |
| CoinGecko `market_chart/range` janv. 2025 | **HTTP 401 — error_code 10012** : « Public API users are limited to querying historical data within the past 365 days » — `cg_usd0pp_range_jan2025.json` | ❌ (hors fenêtre) |
| CoinGecko `market_chart?days=365` (état récent, id `usd0-liquid-bond`) | 200 — 363 points (15/10/2025→15/10/2026), 0,9292 → 0,9768 | ✅ (récent seulement) |
| GeckoTerminal OHLCV des pools historiques (Uniswap `USD0++/USD0` `0x1d08e7ad…` créé 26/07/2024 ; `USD0++/USDT` `0x00cc0523…` créé 28/08/2024) | 200 mais bougies limitées au « tail » récent (2026-02→2026-10 ; 2025-07→2026-01) — **pas de janvier 2025** (règle des 180 jours sur `before_timestamp`, cf. §1.2) | ❌ pour janv. 2025 |
| DEX Screener `latest/dex/tokens/<USD0++>` | 200, une paire Uniswap v3 courante (`0xABfC…8EcDa`, créée **avril 2025 — postérieure à l'incident**) — état courant seulement, pas d'historique — `ds_usd0pp.json` | ⚠️ partiel (aucun historique) |
| Reconstruction DEX par logs (pool `USD0++/USDT` `0x00cc0523…`) | ✅ **exécutée** — 610 swaps → 54 heures actives ; écart 0,31 % vs DefiLlama — `recon_usd0pp_hourly.csv` | ✅ (§1.4-A) |

### 2.3 La série mesurée (DefiLlama horaire, extraits)

| Jour (2025) | min | max | dernier |
|---|---|---|---|
| 01–07/01 | 0,9955 | 1,0030 | ~1,00 |
| 08/01 | **0,98965 (18:57)** | 1,0070 | 0,9974 |
| 09/01 | 0,97889 (23:56) | 1,0070 | 0,97889 |
| **10/01** | **0,90678 (15:58)** | 0,97921 | 0,92084 |
| 11/01 | 0,91369 | 0,93811 | 0,93679 |
| 12/01 | 0,93167 | 0,94332 | 0,93691 |
| 13/01 | 0,92787 | 0,93834 | 0,92891 |
| 14–31/01 | ~0,902–0,941 (min global de la fenêtre : **0,90230 le 20/01 15:58**) | | |
| 01/02 → 01/03 | 0,9328 | 0,9364 | décote persistante |
| 15/10/2026 (dernier point CG 365 j) | | | 0,9768 |

Points de contrôle datés (`ll_usd0pp_points_dates.json`) : 08/01 12:00 = **1,002** ; 09/01 18:00 = **1,001** ; 10/01 00:00 = **0,9789** ; 10/01 12:00 = **0,9180** ; 11/01 00:00 = **0,9208** ; 20/01 12:00 = 0,9095.

**Le chiffre de presse « plus bas 0,89 » n'est pas reproduit** par la série horaire (minimum horaire mesuré 0,90678 le 10/01 ; 0,90230 le 20/01). Écart plausible : creux intra-horaire non capté, ou arrondi journalistique — signalé comme tel, **non tranché**.

**Contrôle indépendant par reconstruction on-chain** (§1.4-A, `recon_usd0pp_hourly.csv`) : la série reconstruite depuis les 610 swaps du pool Uniswap v3 USD0++/USDT recoupe DefiLlama — écart moyen **0,31 %**, minimum reconstruit **0,90816 le 10/01 15:00** (vs 0,90678 à 15:58 côté DefiLlama).

---

## §3. Trou n°3 — Concentration des détenteurs : Blockscout v2 vs Etherscan v2

### 3.1 Tests réels et résultats

**Blockscout v2** — `https://eth.blockscout.com/api/v2/tokens/<adresse>/holders` — **fonctionne sans clé**. 50 détenteurs par page, pagination via `next_page_params` (coût ≈ 2 s/page). Chaque entrée porte `address.hash`, `address.name`, `address.is_contract`, `address.metadata.tags`, `address.implementations` — **de quoi identifier et exclure les contrats de venue**. Testé sur 3 tokens (4 pages chacun = top 200) :

| Token (2026-10-15) | top-10 (part du supply) | HHI (sur 200 comptes) | comptes couverts / supply | 1er détenteur identifié |
|---|---|---|---|---|
| **rsETH** `0xA129…e5A7` | **97,9466 %** | **0,72636** | 99,695 % | `0x2D621092…d7b1` = **aEthrsETH (Aave)** 85,01 % |
| **stETH** `0xae7a…7fE84` | 62,7026 % | 0,22859 | 76,938 % | `0x7f39C581…E2Ca0` = **wstETH (Lido)** 47,31 % |
| **xUSD** `0xE2Fc…26F94` | 91,3954 % | 0,40511 | 99,996 % | `0x14bCD9d…4550` = SafeProxy 61,69 % (Pendle SY 1,86 %, StreamVault 1,83 %, Vault Balancer v3 1,40 %, marché Silo 1,36 %) |

Données brutes : `bs_<token>_info.json`, `bs_<token>_holders_p{1..4}.json`, agrégats `bs_concentration_resultats.json`.

**Etherscan v2** — `https://api.etherscan.io/v2/api?chainid=1&module=token&action=tokenholderlist…` — **HTTP 200 mais corps : `{"status":"0","message":"NOTOK","result":"Missing/Invalid API Key"}`** — identique avec ou sans paramètre `apikey` (même un jeton factice est refusé ; `tokenbalance` refusé pareil). Il faut une **clé gratuite** (inscription) pour l'utiliser : **NON UTILISABLE en l'état**. Fichiers : `es_v2_holders_nokey.json`, `es_v2_holders_dummykey.json`.

### 3.2 Verdict pour la formule 3.3 de W2-B (`HHI = Σ part_i²`, top10 hors contrats)

- **Utilisable dès aujourd'hui sans clé : Blockscout v2.** Le calcul réel est démontré ci-dessus (top-10 + HHI). Deux réserves de méthode : (a) le HHI calculé sur les N premiers comptes est un **minorant** — paginer jusqu'au bout pour un HHI exact (les queues de distribution pèsent peu mais pas rien : ici 200 comptes ≈ 77–100 % du supply selon le token, le reste étant de la poussière) ; (b) la liste **mélange détenteurs économiques et contrats de venue** (aTokens, wrappers, pools, vaults) : le champ 3.3 (« hors contrats connus ») est faisable car Blockscout **nomme et tague** les contrats (`ATokenInstance`, Lido, Safe, Pendle…) — mais l'exclusion doit rester une liste blanche maintenue à la main.
- **Etherscan v2 : à écarter** pour ce projet tant qu'aucune clé n'est provisionnée (pas de clé = pas de données ; ce n'est pas un problème de quota mais d'authentification).
- **Coût par token** : 1 appel d'info + ~4 appels (top 200) ; prévoir 1–2 s entre pages (limite de débit). Vérifié en conditions réelles : 3 tokens × 5 appels sans blocage.

---

## §4. Trou n°4 — Utilisation Compound / Morpho (méthode + coût, testé)

Tous les tests ci-dessous ont été exécutés le 2026-10-15 sur `eth.drpc.org` (archive vérifiée par ailleurs dans W2-B). Les sélecteurs ont été **recalculés par keccak** localement (vérifiés contre des constantes connues) — pas de valeur de mémoire.

### 4.1 Compound V2 (marché cToken `cUSDC` `0x39AA39c021dfbaE8faC545936693aC917d5E7563`)

- Formule : `U = totalBorrows / (getCash + totalBorrows)` ; variante avec réserves : `U' = totalBorrows / (getCash + totalBorrows − totalReserves)`.
- Sélecteurs : `getCash()=0x3b1d21a2`, `totalBorrows()=0x47bd3718`, `totalReserves()=0x8f840ddd`, `totalSupply()=0x18160ddd`, `exchangeRateStored()=0x182df0f5`.
- **Mesure directe (2026-10-15)** : getCash = 3 009 334,18 USDC ; totalBorrows = 4 678 403,80 USDC ; totalReserves = 177,61 USDC → **U = 60,86 %** (62,29 % avec la variante réserves).
- **Mesure en archive (bloc 23 725 820 = 2025-11-04 12:00:11)** : getCash = 18 967 767,19 ; totalBorrows = 23 065 777,76 → **U = 54,87 %**. → l'archive fonctionne identiquement pour Compound.
- **Coût : 5 `eth_call` par marché et par instant** (les 4 premiers suffisent pour U ; `exchangeRateStored` en option).

### 4.2 Compound V3 « Comet » (USDC `0xc3d688B66703497DAA19211EEdff47f25384cdc3`)

- Le Comet expose directement `getUtilization() = 0x7eb71131`.
- **Mesure (2026-10-15)** : `getUtilization() = 90,5647 %`, identique au recalcul `totalBorrow()/totalSupply()` (0x8285ef40 / 0x18160ddd). **Coût : 1 appel** (3 si on veut recouper).

### 4.3 Morpho Blue (`0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` — code présent, 31 248 octets)

- **API publique `https://blue-api.morpho.org/graphql`** (POST GraphQL, **sans clé**). ⚠️ Le schéma a changé : le champ `uniqueKey` **n'existe plus** (HTTP 400 `GRAPHQL_VALIDATION_FAILED`) — le champ actuel est **`marketId`** (introspection : `morpho_api_schema_market.json`). `MarketState` expose `utilization`, `borrowAssets`, `supplyAssets`, `supplyApy`, `liquidityAssets`…
- **Lecture on-chain** : `market(bytes32)` (`0x5c60e39a`) sur l'id renvoyé par l'API → 6 mots = (totalSupplyAssets, totalSupplyShares, totalBorrowAssets, totalBorrowShares, lastUpdate, fee). Exemple vérifié : marché `0x8eaf7b29…` (USDC/PAXG, lltv 0,915 — params relus par `idToMarketParams(bytes32)` `0x2c3c9157` : loan USDC `0xa0b8…`, collatéral PAXG `0x4580…`) → **utilisation on-chain = 100,0000 %** = valeur API (1,000000). **Coût : 1–2 `eth_call`.**
- **Marchés de xUSD (lien direct avec l'épisode §1)** : l'API ne remonte que **2 marchés à collatéral xUSD** sur Ethereum — `0xc05394d0…` (supply 0,101 $ ; util 0 %) et `0x39fe55e5…` (borrow 101 072 / supply 112 109 unités ; util **90,16 %** ; **valeur totale ~0,11 $**). Autrement dit : les marchés Morpho publics adossés à xUSD ne contiennent plus que des **poussières** (l'exposition Stream passait par des vaults privés, hors marché public) — cohérent avec la narration [48][99].
- **Mises en garde mesurées** : la liste « top par supply » de l'API inclut des marchés au collatéral douteux/exotique **à 100 % d'utilisation** (sdeUSD, BONDUSD) et des tailles USD invraisemblables — **filtrer par collatéraux vérifiés + plancher de TVL** avant tout usage de signal ; l'API expose aussi un champ `historicalState` (historique de marché) — **non testé ici**, identifié comme piste pour la calibration.

### 4.4 Tableau récapitulatif (méthode, coût, archive)

| Protocole | Lecture | Sélecteurs | Coût / marché / instant | Archive testée ? |
|---|---|---|---|---|
| Aave V3 (rappel W2-B) | aToken/cash + config | 4 | 4 `eth_call` | ✅ (jusqu'à juin 2022) |
| Compound V2 | getCash, totalBorrows, totalReserves, totalSupply | 5 | 5 `eth_call` | ✅ (bloc 23 725 820 vérifié) |
| Compound V3 (Comet) | getUtilization | 1–3 | 1 `eth_call` | à tester (méthode identique) |
| Morpho Blue | API (utilization) puis `market(id)` on-chain | 1–2 | 1 POST + 1–2 `eth_call` | à tester (idem) |

**Verdict §4 : l'extension des mesures d'utilisation (2.1) à Compound V2/V3 et Morpho est faisable sans clé API** ; ce qui change n'est pas la faisabilité mais le **coût par marché** (1 à 5 appels) et la **qualité de données Morpho** (filtrer).

---

## §5. Trou n°5 — Plan de calibration des seuils sur 12 mois

**Objectif** : remplacer les seuils « justifiés par les épisodes » de W2-B par des seuils **validés sur distribution** (12 mois de calme) **et** sur le rappel des épisodes connus. Principe : un seuil = un **quantile extrême** (P99 / P99,9) de la série du signal en régime calme, puis **contre-validation** sur les 6 épisodes du dossier (UST 05/2022, stETH 06/2022, USDC 03/2023, USD0++ 01/2025, xUSD 11/2025, rsETH 04/2026) : il doit (a) franchir **avant** le point de rupture de référence, (b) ne pas déclencher sur la période de contrôle.

### 5.1 Séries à produire, par signal (scripts précis)

| Signal (W2-B) | Série 12 mois | Sources (testées ici) | Script proposé | Volume d'appels |
|---|---|---|---|---|
| 1.1 Décote de peg `D(t)` | horaire, par actif (stable/LST) | Binance klines (1000/req), Bitstamp OHLC, OKX history-candles, DefiLlama chart (`span≤500`), CoinGecko 365 j glissant | `collect_prices_1y.py` (JSONL, `retrieved_at` par lot, reprise sur trou) | ~9 + 9 + 88 + 18 req/actif/an |
| 1.2 Dispersion `σ_disp` | dérivée de 1.1 (même collecte) | idem | idem | 0 (dérivé) |
| 1.3 Divergence oracle/marché `Δ` | quotidien + horaire sur fenêtres de stress | `latestRoundData()` par `eth_call` archive (feeds liste blanche) + série marché 1.1 | `collect_oracles_1y.py` (échantillonnage sur table d'ancrages de blocs, `block_at` dérivée) | 365 × feeds (ex. 10) ≈ 3,7 k |
| 1.4/1.5 Décote LST & profondeur `Slip(X)` | quotidien (365 blocs) × 3 tailles × pools | `get_dy` Curve, `quoteExactInputSingle` Uniswap QuoterV2 (archive OK) | `collect_liquidity_1y.py` | 365 × 3 × (1–3) ≈ 1–3 k |
| 2.1/2.2/2.3/2.5 `U`, `isFrozen`, `S/supplyCap`, `ΔU/Δt` | **échantillonnage hiérarchique** : quotidien 12 mois + horaire ±30 j autour des alertes | Aave V3 (4 appels), Compound V2 (5), Comet (1), Morpho (1–2) — cf. §4 | `collect_reserves_1y.py` (quotidien) puis `collect_reserves_hourly.py` (escalade) | quotidien : 365 × 8 marchés × ~3 appels ≈ 8,8 k ; escalade horaire ponctuelle |
| 3.3 Concentration | hebdomadaire (top 200 suffit si queue négligée, sinon complet) | Blockscout v2 (§3) | `collect_holders_weekly.py` | 52 × (4–6) ≈ 250/token/an |

**Règle d'échantillonnage** (budget) : commencer **quotidien** ; escalade automatique en horaire quand un pré-seuil journalier est franchi (ex. |ΔU| > 5 pts/jour, D > 25 bps/jour) ± 30 jours autour — c'est la seule façon de tenir 12 mois sur un RPC public (sinon ~280 k appels pour U horaire seul). Les blocs sont retrouvés par une **table d'ancrages** (1 ancre/jour par dichotomie ≈ 365 × 20 appels, mise en cache) + interpolation locale ±100 blocs.

### 5.2 Statistique et décision

1. Construire pour chaque signal la distribution empirique (calme) sur les 12 mois ; tronquer aux heures actives (liquidité > 0) ; consigner les trous (pas d'imputation silencieuse).
2. Seuils candidats : **P99, P99,9** (et moyenne + k·σ robuste, MAD, en contrôle) → 3 niveaux : *alerte* (P99), *rupture* (P99,9), *sortie* (niveau épisode). 
3. **Validation croisée épisodes** : pour chaque épisode, calculer l'instant de franchissement de chaque seuil et l'**antériorité** par rapport au point de rupture (mesuré dans W2-B : gel rsETH, gel Celsius, annonce Circle…). Objectif : au moins 1 signal par famille avec antériorité > 0 ; consigner les faux négatifs.
4. **Période de contrôle** : les 12 mois hors épisodes ; compter les fausses alertes ; cible initiale < 1 % des heures pour l'alerte, < 0,1 % pour la rupture (ajustable).
5. **Pièges de méthode (déjà douloureux ailleurs)** : comparer en **espace valeur** (pas en % flottants — `0.99` vs `1.0000000000000009 %`) ; **geler les comptes de franchissements attendus** en test de régression ; parser les trois formes de dates des fournisseurs (epoch numérique, chaîne de chiffres, ISO — DefiLlama envoie l'epoch en chaîne sur ses endpoints stablecoins).
6. **Livrables** : `calibration/thresholds_v1.json` (signal × actif → {alerte, rupture, sortie, n_obs, rappel épisodes}) ; `calibration/rapport_validation.md` (matrice épisode × signal : franchi ? antériorité ? faux positifs) ; corpus brut rejouable (`retrieved_at` par ligne).
7. **Coût total estimé** pour 12 mois : ~15–25 k appels RPC (avec escalade ponctuelle) + ~130 req/actif/an pour les prix CEX + ~250 req/token/an pour la concentration — soit, à 2–5 req/s, **10–20 h de collecte en tâche de fond** ; compressible en réduisant les marchés suivis ou en passant au quotidien strict pour les signaux 2.x (au prix de la résolution des alertes).

---

## §6. Sources (URLs testées et documents cités)

**Documents (consultés le 2026-10-15)** :
- incrypted.com/en/stream-finance-platform-suspends-operations-after-93-million-loss (X/@StreamDefi 04/11/2025 ; O. Goldberg 03/11/2025 ; CoinGecko low $0.26)
- gncrypto.news/news/stream-finance-freezes-withdrawals-93m-loss-xusd-slumps-51-cents (notification 02/11 ; baseline TVL 31/10)
- onchainatlas.org/stream-finance/history ($285 M ; $160 M ; deUSD ; TelosC $123,6 M ; MEV Capital $25,4 M)
- bitget.com/amp/news/detail/12560605047540 ; bitcoinethereumnews.com (mêmes faits, 03/11)
- cointelegraph.com/news/usd0-stablecoin-depeg-revenue-switch (plancher 0,87 ; revenue switch 13/01 ; early unstaking)
- cryptonews.net/news/altcoins/30352082 (–7 % ; double exit ; ~0,937 le 09/01)
- docs.usual.money …/usd0 (contrats USD0/bUSD0 — ancien USD0++), coingecko.com/en/coins/staked-stream-usd
- etherscan.io/token/0xE2Fc85BfB48C4cF147921fBE110cf92Ef9f26F94 (« Staked Stream USD », contrat StreamVault, 6 déc.) ; ethereum.atomicwallet.io (le coffre détient aussi ~381,39 M de « Stream USD »/streamUSD)

**Endpoints réellement appelés le 2026-10-15** (fichiers bruts dans `raw_w3c/`) :
- `api.geckoterminal.com/api/v2` (tokens, pools, ohlcv day/hour/minute, search) — OK/partiel/401 selon cas (§1.2, §2.2)
- `api.dexscreener.com/latest/dex/…` — état courant seulement ; xUSD : `pairs:null`
- `coins.llama.fi` (prices/historical, chart, batchHistorical) ; `stablecoins.llama.fi/stablecoins` ; `api.llama.fi/protocol/stream-finance`
- `api.coingecko.com/api/v3` (search, market_chart, market_chart/range) — la clé de lecture de xUSD
- `eth.blockscout.com/api/v2/tokens/<addr>/holders` — OK (concentration)
- `api.etherscan.io/v2/api?module=token…` — refusé (clé manquante)
- `blue-api.morpho.org/graphql` — OK (schéma `marketId` ; introspection sauvegardée)
- RPC : `eth.drpc.org` (eth_call/archive ✅, getLogs plage limitée), `rpc.mevblocker.io` (getLogs archive ✅ ≤100 k blocs), `eth-mainnet.public.blastapi.io` (logs ≤10 blocs), `eth-pokt.nodies.app` (≤50), `ethereum-rpc.publicnode.com` (archive refusée), `eth.merkle.io` (429), `eth.llamarpc.com` (525)

---

## §7. État final des trous W2-B

| Trou (W2-B §5) | État W3-C | Preuve |
|---|---|---|
| Série de prix xUSD (nov. 2025) | ✅ **comblé** — CoinGecko horaire (457 pts) + GT (journalier Balancer v3, journalier/horaire Uniswap v4) + reconstruction par logs (411 swaps) ; DefiLlama/DEX Screener : **non trouvé** (documenté) | §1, `cg_xusd_hourly_oct25_nov13_2025.csv`, `recon_xusd_v4_hourly.csv` |
| Série de prix USD0++ (janv. 2025) | ✅ **comblé** — DefiLlama horaire (635 pts fusionnés) ; CG refusé (401 > 365 j) ; GT indisponible pour la période | §2, `ll_usd0pp_hourly_jan2025.csv` |
| Endpoints de concentration | ✅ **tranché** — Blockscout v2 utilisable sans clé (top-10/HHI mesurés) ; Etherscan v2 non utilisable sans clé (erreur exacte capturée) | §3, `bs_concentration_resultats.json` |
| Compound / Morpho | ✅ **testé** — Compound V2 (5 appels, archive OK), Comet (1 appel), Morpho (API + on-chain, 2 appels) ; filtre qualité requis sur Morpho | §4 |
| Calibration 12 mois | 📋 **plan détaillé** (§5), non exécuté (chantier de collecte 10–20 h) | §5 |
| (Hors périmètre W3-C) Archive L2, blocs L2, ponts | non traités ici | chantiers W2-B restants |

## §8. Inventaire des fichiers produits (`research/raw_w3c/` — 126 fichiers, ~2,9 Mo, aucun fichier existant modifié)

**Scripts (16)** : `probe_w3c_01_prix.sh`, `probe_w3c_02_series.py`, `probe_w3c_03_gt.py`, `probe_w3c_04_identite_pool.py`, `probe_w3c_05_cg.py`, `probe_w3c_05_gt2.py`, `probe_w3c_06_usd0.py`, `probe_w3c_07_holders.py`, `probe_w3c_08_holders_calc.py`, `probe_w3c_09_compound_morpho.py`, `probe_w3c_10_morpho2.py`, `probe_w3c_11_schema.py`, `probe_w3c_12_morpho3.py`, `probe_w3c_13_reconstruction.py`, `probe_w3c_14_rpc_logs.py`, `probe_w3c_15_reconstruction2.py`.
**Sorties texte (15)** : `probe_w3c_*_sortie_2026-10-15.txt`.
**CSV propres** : `cg_xusd_hourly_oct25_nov13_2025.csv` (457 h), `ll_usd0pp_hourly_jan2025.csv` (635 h), `recon_usd0pp_hourly.csv` (54 h), `recon_xusd_v4_hourly.csv` (41 h).
**JSON bruts** : `gt_*` (35 fichiers — tokens, pools, OHLCV, recherche), `ds_*` (3), `ll_*` (15), `cg_*` (5), `bs_*` (17 — holders + info), `es_*` (3 — refus Etherscan), `morpho_*` (4 — API, introspection), `logs_*` (2 — swaps bruts 610 + 411), `pool1_tokens.json`, `bs_concentration_resultats.json`, `ll_usd0pp_points_dates.json`, `defillama_stablecoins_2026-10-15.json`.
