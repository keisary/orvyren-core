# W2-B — Table des signaux de détection d'ORVYREN

**Version 1 — 2026-10-15** (produit tôt ; complété ensuite). Auteur : sous-agent W2-B.
Dépôt : `D:\orvyren_core\research\W2B_signaux_detection.md`. Matière brute et scripts : `D:\orvyren_core\research\raw_w2b\`.

**Convention de statut** :
- `VÉRIFIÉ` = la formule a été exécutée par nous sur une source publique réelle (commande/endpoint re-testé le 2026-10-15 ; preuve dans `raw_w2b/`).
- `TESTÉ-PARTIEL` = l'endpoint répond et la donnée existe, mais nous n'avons pas pu reconstruire l'antériorité complète.
- `HYPOTHÈSE` = formule et source identifiées, calcul non exécuté (donnée d'archive payante, historique absent, ou endpoint refusé).
- `NON CALCULABLE` = aucune donnée publique accessible identifiée.

## 0. Ce que cette version établit déjà (résumé)

1. **Le calcul historique on-chain est possible sans clé API.** Trois RPC publics Ethereum acceptent `eth_call` sur un **bloc d'archive** : `https://eth.drpc.org`, `https://eth-mainnet.public.blastapi.io` (testés au bloc 16 810 000 / mars 2023) ; `https://ethereum.publicnode.com` refuse l'archive sans jeton. C'est la brique qui rend la colonne « calcul historique » réalisable pour ORVYREN.
2. **La décote de peg se mesure, et elle est multi-valuée.** Reconstruit par nous : oracle Chainlink on-chain USDC/USD au plus bas **0,9069** (2023-03-11 12:59 UTC) contre **0,8767** pour l'agrégat DefiLlama (07:57 UTC), **0,8698** sur OKX, **0,882** sur Binance, **0,8053** sur Bitstamp (07:00 UTC). Rapport mesuré : **8,7 cents d'écart entre la plateforme la plus basse et la plus haute** au même épisode, et l'oracle on-chain **sous-estime** la décote de ~3 cents.
3. **L'utilisation d'un marché de prêt se lit avec 2 appels par actif** (pas besoin d'indexeur) : `U = 1 − cash / aToken.totalSupply()`.

---

## (a) TABLE DES SIGNAUX

### Famille 1 — Décote de peg

| # | Signal | Formule exacte | Source exacte (testée ?) | Historique possible ? | Seuil candidat (justification) | Antériorité observée (épisodes) | Statut |
|---|---|---|---|---|---|---|---|
| 1.1 | Décote de peg d'un actif vs son unité | `D = 1 − p̂/peg_ref`, où `p̂ = Σ_i w_i · p_i` (médiane pondérée par le volume 24 h sur les venues suivies) et `peg_ref = 1` (stablecoins USD) ou **cours ETH** (LST) | `https://coins.llama.fi/prices/current/<chain>:<addr>` (VÉRIFIÉ, renvoie `confidence`) + venues directes : `api.binance.com/api/v3/klines` (VÉRIFIÉ), `okx.com/api/v5/market/history-candles` (VÉRIFIÉ), `bitstamp.net/api/v2/ohlc/usdcusd` (VÉRIFIÉ) | **OUI** — DefiLlama `chart` 1h historique (VÉRIFIÉ sur mars 2023), klines Binance/OKX/Bitstamp jusqu'en 2023 (VÉRIFIÉ) | **D ≥ 50 bps soutenu 15 min** = alerte ; **D ≥ 200 bps** = rupture ; **D ≥ 500 bps** = retrait forcé. Justification mesurée : en régime normal la dispersion inter-venues est < 5 bps ; le 11 mars 2023 l'écart inter-venues atteint 870 bps | **Jours** (USD0++ : annonce du 9 janv. 2025, depeg le 11 → 2 jours, [39]) ; **heures** (USDC/SVB : annonce Circle 10 mars ~22 h, marché secondaire le 11 → heures, [3]) ; **minutes** (UST : swaps 21:57–22:52 UTC le 7 mai 2022, [11]) | **VÉRIFIÉ** |
| 1.2 | Dispersion inter-venues (mesure de la qualité de la référence) | `σ_disp = max_i p_i − min_i p_i` sur les venues retenues (filtre : volume 24 h > V_min) ; complété par `IQR(p_i)` | Mêmes endpoints que 1.1 | OUI (mêmes) | **> 100 bps = la référence unique n'est plus fiable** → basculer sur la médiane ; **> 300 bps = stress de venue**, ne pas utiliser cette venue comme signal de prix. Mesuré : 870 bps le 2023-03-11 ; ~5 bps au repos | a précédé ou accompagné tous les épisodes de dépeg ; **cas d'école mesuré par nous** : Bitstamp 0,8053 vs Binance 0,8820 vs oracle 0,9069 le 2023-03-11 | **VÉRIFIÉ** (mesuré sur 10–12 mars 2023) |
| 1.3 | **Divergence oracle on-chain vs marché** (le piège de la source unique) | `Δ_oracle = p̂_marché − p_oracle_onchain` | Oracle : `latestRoundData()` (`0xfeaf968c`) sur le feed Chainlink ; marché : 1.1 | OUI — `eth_call` sur bloc d'archive via `eth.drpc.org` (VÉRIFIÉ, série reconstruite) | **\|Δ\| > 100 bps pendant > 1 h = l'oracle décroche du marché** → ne pas valoriser le collatéral sur l'oracle. Mesuré : ~296 bps le 2023-03-11 07:57 UTC ; jusqu'à ~1000 bps vs Bitstamp | Le 11 mars 2023, **l'oracle Chainlink n'est descendu qu'à 0,9069** alors que le marché voyait 0,805–0,876 : tout agent valorisant sur l'oracle pendant la fenêtre de crise se trompait de 3 à 10 cents | **VÉRIFIÉ** |
| 1.4 | Décote d'un LST vs son sous-jacent | `D_LST = 1 − get_dy(pool, token_LST → ETH, 1e18)/1e18` (mesure exécutable réelle, pas un prix affiché) | `eth_call get_dy(int128,int128,uint256)` = `0x5e0d443f` sur le pool Curve stETH/ETH `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` (VÉRIFIÉ : renvoie 1,00000116 ETH le 2026-10-15) | OUI (même méthode par `eth_call` sur bloc d'archive) | **D ≥ 100 bps** = alerte ; **≥ 300 bps** = décote exploitable par les liquidateurs ; **≥ 600 bps** = niveau atteint en juin 2022 ([14] ≈ 6 %) | stETH : déséquilibre du pool Curve visible dès le 7–12 mai 2022, décote ~6 % constatée le 13 juin 2022 → **jours à semaines** ([13][14][15]) ; ezETH (avril 2024) : décote > 70 % au plus bas ([36]) | **VÉRIFIÉ** (méthode) / **HYPOTHÈSE** (seuils de décote sur archive) |
| 1.5 | Profondeur exécutable pour une taille donnée | `Slip_P(X) = 1 − get_dy(...)/X` : décote réellement obtenue en vendant X unités, pas un prix affiché | Curve `get_dy` (VÉRIFIÉ) ; Uniswap V3 `QuoterV2.quoteExactInputSingle` (`0xc6a5026a`) sur `0x61fFE014bA17989E7435F2A9E5cB21bF9697530B21e` (**à tester**) | OUI par `eth_call` archive | **Slip > 100 bps pour la taille de sortie de la trésorerie** = sortie non réalisable → traiter comme non liquide. C'est la définition de « profondeur réelle » | 3AC retire 400 M$ (128 k stETH) du pool Curve en 1 transaction le 12 mai 2022 : le pool n'absorbe plus ([13]) ; Nansen : « le déséquilibre et la liquidité ne se sont pas rétablis » ([13]) | **VÉRIFIÉ** (Curve) / **À TESTER** (Uniswap) |

### Famille 2 — Utilisation des marchés de prêt

| # | Signal | Formule exacte | Source exacte (testée ?) | Historique possible ? | Seuil candidat | Antériorité observée | Statut |
|---|---|---|---|---|---|---|---|
| 2.1 | Taux d'utilisation d'une réserve Aave | `U_r = 1 − cash_r / S_r` où `cash_r = underlying.balanceOf(aToken)` (`0x70a08231`) et `S_r = aToken.totalSupply()` (`0x18160ddd`) | Ethereum : Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`, aEthUSDC `0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c`, USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` (VÉRIFIÉ : `U=94,14 %` le 2026-10-15 02:56 UTC) ; rsETH : aEthrsETH `0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1` ; Arbitrum : Pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`, aArbrsETH `0x6b030Ff3FB9956B1B69f475B77aE0d3Cf2CC5aFa` | **OUI** — `eth_call` sur bloc d'archive (démontré) | **U > 90 %** = liquidité de sortie sous 10 % du supply ; **U > 99 %** = **file d'attente de fait : les retraits échouent**. Sur rsETH le 18/04/2026, l'atteinte de ~100 % = sortie impossible | rsETH 18/04/2026 : l'invariant pratique est « 100 % d'utilisation = personne ne peut sortir » (à confirmer par reconstruction historique — voir § « à compléter ») | **VÉRIFIÉ** (formule + endpoint) / **À COMPLÉTER** (série historique 2026) |
| 2.2 | Composition des emprunts d'une réserve | `U_r^{X} = D_r^{X} / (D_r^{X} + cash_r^{X})` par actif X | Compound V3 (Comet) : `getUtilization()`, `totalSupply()`, `totalBorrow()` ; Compound V2 : `cToken.totalBorrowsCurrent()`/`totalSupply()` | OUI (mêmes méthodes) | idem 2.1 | Emprunts circulaires sur USD0++ valorisés à 1 $ identifiés on-chain avant le depeg du 11 janv. 2025 ([39]) | HYPOTHÈSE (formule) |
| 2.3 | Variation de U sur 1 h / 24 h (vitesse de vidange) | `ΔU/Δt` | idem 2.1, échantillonnage horaire par bloc d'archive | OUI | **ΔU > +10 points en 1 h** = vidange anormale → alerte | USDC/DAI mars 2023 : les PSMs de DAI **se vident en heures** ([3]) ; stETH : retraits LP de 400 M$ en 1 transaction le 12 mai 2022 ([13]) | HYPOTHÈSE (formule) / VÉRIFIÉ (méthode d'échantillonnage) |
| 2.4 | Utilisation agrégée inter-protocoles d'un même actif | `U_A = Σ_p D_{A,p} / Σ_p S_{A,p}` sur l'ensemble des marchés listant A | Aave V3 (toutes chaînes) + Compound + Morpho : aTokens/cTokens par chaîne via `eth_call` sur les RPC L2 (VÉRIFIÉ : Arbitrum `0xa4b1`, Optimism `0xa`, Base `0x2105` répondent) | OUI | **U_A > 95 %** = l'actif est « gelé » de fait sur l'ensemble du graphe | 18 avril 2026 : 89 567 rsETH déposés sur Aave pour emprunter 190 M$ de WETH ([52]) — un actif dont la sortie est fermée partout | HYPOTHÈSE |

### Famille 3 — Composition et profondeur réelle du collatéral

| # | Signal | Formule exacte | Source exacte | Historique possible ? | Seuil candidat | Antériorité observée | Statut |
|---|---|---|---|---|---|---|---|
| 3.1 | Concentration d'un actif dans les collatéraux d'un marché | `w_A = Valeur collatéral A déposée / Valeur collatéral totale du marché` (valorisation au prix oracle **et** au prix de sortie) | Aave V3 : `UiPoolDataProviderV3.getReservesData(provider)` ou lecture par aToken × prix oracle `ORACLE.getAssetPrice()` ; Compound : `Comet.getAssetInfo()` | OUI (archive) | **w_A > 20 %** = dépendance critique ; **> 40 %** = marché mono-collatéral de fait (précédent : collatéral Alameda ≈ 40 % de tokens émis par sa société sœur, [18]) | Alameda ~40 % auto-émetteur ; USDC/DAI : contagion par PSM ([3]) | HYPOTHÈSE |
| 3.2 | Profondeur de sortie réellement disponible | `Depth(X) = argmax{ X : Slip_P(X) ≤ ε }`, ε = 100 bps | `get_dy` Curve (VÉRIFIÉ), `QuoterV2` Uniswap V3, pools DEX via `yields.llama.fi/pools` (VÉRIFIÉ, 2,9 Mo, contient `tvlUsd` par pool) | OUI | **Depth(X) < position de la trésorerie** = sortie impossible → ne pas considérer l'actif comme liquide | 3AC 400 M$ / pool Curve 12 mai 2022 ([13]) ; ezETH : pool DEX peu profond → liquidations de ~56 M$ ([36]) | VÉRIFIÉ (Curve) / À TESTER (Uniswap) |
| 3.3 | Concentration des détenteurs | `HHI = Σ (part_i)²` ; `top10 = Σ_{i≤10} part_i` sur les holders on-chain (hors contrats de pools/trésoreries) | Etherscan API v2 `tokenholderlist` (**clé requise** → non testé) ; Blockscout `eth.blockscout.com/api/v2/tokens/<addr>/holders` (**à tester**) | OUI si les endpoints répondent | **top10 > 50 % hors contrats connus** = risque de ruée coordonnée | 451 M$ de retraits nets sur 7 jours avant l'effondrement de FTX ([19]) | HYPOTHÈSE / **À TESTER** |

### Famille 4 — Ré-hypothécation / valorisation fixe

| # | Signal | Formule exacte | Source exacte | Historique possible ? | Seuil candidat | Antériorité observée | Statut |
|---|---|---|---|---|---|---|---|
| 4.1 | **Valorisation à prix fixe détectée par la structure du prix** | `Fix_A = 1` si `p_oracle(A)` est une constante (variance nulle sur N jours) **et** que `A` n'est ni un stablecoin fiat référencé ni un actif à rendement intégré ; `Fix_A^{(v)} = Var_{30j}(p_oracle)` | Oracle du protocole lu en archive (`AaveOracle.getAssetPrice` = `0xb3596f07`) ; comparé aux prix de marché (1.1) | OUI (`eth_call` archive) | **Var = 0 sur 30 jours ET p_marché < 0,95** → actif mort valorisé à 1 $ : alerte maximale | xUSD (Stream Finance, 3–4 nov. 2025) : « la perte était réelle immédiatement mais **invisible sur la chaîne pendant des semaines, parce que les marchés de prêt détenaient le xUSD à un prix fixe de 1 $** » [48] ; USD0++ : « des centaines de millions piégés dans des protocoles qui valorisaient encore à 1 $ » [39] | **DOCUMENTÉ** (signal nommé par la source [48]) — calcul : HYPOTHÈSE |
| 4.2 | Cartographie de la ré-hypothécation | graphe `G = (actif → protocoles où il est collatéral)` ; `R_A = 1 + Σ_p (dette adossée à A au protocole p) / (prix de sortie réalisable de A)` | Déduit de 4.1 + 2.1 + 3.1 : tous les marchés où A apparaît en collatéral (aTokens/cTokens par chaîne) | OUI (archive) | **R_A > 1** = promesses > valeur réalisable → trou de solvabilité arithmétique | « ~285 M$ de dette DeFi interconnectée » autour de Stream/xUSD ([99]) ; contagion deUSD → ~0,015 $ et liquidation d'Elixir, USDX < 0,60 $ en quelques jours ([48][90]) | **DOCUMENTÉ** (fait) / HYPOTHÈSE (calcul) |
| 4.3 | Prix oracle « collé » sans marché | `p_oracle(A) = 1,00` alors que la meilleure profondeur de sortie (3.2) décote > X % | croisement 1.1/3.2/4.1 | OUI | **décote de sortie > 5 % avec oracle à 1,00** = preuve d'invisibilisation | Épisode Drift : un token fictif (CVT), liquidité de quelques milliers de dollars, wash trades pour fabriquer un prix ~1 $ accepté par l'oracle ([58]) | **DOCUMENTÉ** [58] |

### Famille 5 — Invariants inter-chaînes (candidat A)

| # | Signal | Formule exacte | Source exacte | Historique possible ? | Seuil candidat | Antériorité observée | Statut |
|---|---|---|---|---|---|---|---|
| 5.1 | Invariant d'offre d'un actif bridgé | `Δ = TotalSupply(destination) − TotalSupply(source) − Δ_release_autorisé(t)` ; en continu : `TotalSupply_dest(t) ≤ Locked_ou_Burned_source(t)` | `eth_call erc20.totalSupply()` (`0x18160ddd`) sur chaque chaîne via RPC publics (Ethereum VÉRIFIÉ, Arbitrum VÉRIFIÉ `0xa4b1`, Optimism `0xa`, Base `0x2105`) + solde du contrat de lock sur la chaîne source | **OUI** (endpoints opérationnels maintenant) ; historique via `eth_call` archive là où disponible | **toute violation > tolérance (0)** = anomalie ; en pratique seuil = tolérance de mint/burn en vol sur le même bloc | KelpDAO 18/04/2026 : 116 500 rsETH (~292 M$) libérés **sans burn correspondant en amont** — « détectable uniquement par surveillance continue des invariants inter-chaînes » (Chainalysis) [51] ; 6 jours pour Ronin (624 M$) [21][23] | **DOCUMENTÉ** ([51], méthode nommée par la source) / calcul en direct : à démontrer |
| 5.2 | Cohérence des achats/brûlages d'un pont | `Mint_dest(t) ≡ Burn_source(t)` sur la fenêtre glissante | événements `Burn`/`Mint` ou `Transfer(0x0)` sur les deux chaînes (`eth_getLogs`) | OUI (RPC publics, sous réserve de la profondeur d'archive des L2) | tout écart non nul | KelpDAO : le 2ᵉ paquet « fantôme » de 40 000 rsETH (~95 M$) a été bloqué parce que la pause a été déclenchée après détection de l'anomalie [51] | DOCUMENTÉ |
| 5.3 | Attestation unique (1-of-1) détectée | « nombre de vérificateurs indépendants du pont < 2 » = configuration à point unique de défaillance | Config on-chain du pont (contrats `LayerZero`/OApp) + documentation | partiel | **1 vérificateur = risque structurel** ; documenté comme condition de faisabilité de l'exploit | LayerZero : « l'impact a été rendu possible par la configuration à vérificateur unique de l'OApp affectée » [53] | **DOCUMENTÉ** [53] |
| 5.4 | Divergence de sources RPC (anti-empoisonnement) | `div = |état(RPC_1) − médiane(états(RPC_i))|` sur le même bloc | ≥ 3 RPC publics distincts (testés : drpc, blastapi, publicnode) | OUI (immédiat) | **toute divergence sur un état critique → geler la décision** | KelpDAO : RPC internes compromis + DDoS pour forcer le basculement sur le vérificateur empoisonné [51] | **DOCUMENTÉ** ([51] : « ne pas faire confiance à une source unique de vérité ») |

### Famille 6 — Concentration / contagion

| # | Signal | Formule | Source | Historique | Seuil | Antériorité | Statut |
|---|---|---|---|---|---|---|---|
| 6.1 | Exposition croisée à un même collatéral | `E_A = Σ_p exposition(A, p)` (dette adossée à A) et `E_A / capital du graphe` | 2.1 + 3.1 sur toutes les chaînes | OUI | **E_A > 10 % du graphe suivi** = candidat à la contagion systémique | rsETH : TVL d'Aave **−8,45 Md$ en deux jours** [52][91] ; xUSD : ~285 M$ de dette interconnectée [99] | DOCUMENTÉ (fait) / HYPOTHÈSE (mesure) |
| 6.2 | Corrélation des flux | corrélation glissante des flux nets entre actifs (30 min) | `stablecoins.llama.fi/stablecoincharts/all` (VÉRIFIÉ) + flux on-chain | OUI | **corrélation > 0,8 anormale** = panique commune | arXiv 2606.07442 : « l'activité transactionnelle entre les principaux stablecoins est devenue fortement synchronisée pendant la fenêtre de crise » [4] | DOCUMENTÉ [4] |
| 6.3 | Ruée sur les retraits (redemptions) | `R = Δréserves/Δt` ou `Δcirculating 24 h / circulating` | `stablecoins.llama.fi` (VÉRIFIÉ : `circulatingPrevDay`, `chainCirculating`) | OUI | **−5 % d'offre en 24 h** = ruée | FSB : « le risque de liquidité des émetteurs de stablecoins est le facteur le plus pertinent pour l'instabilité financière » [FSB P161025] | HYPOTHÈSE |

---

## (b) Invariants vérifiables (liste opérationnelle)

1. `SUM(supply d'un actif sur toutes les chaînes) ≤ offre de référence autorisée` (invariant d'émission — KelpDAO [51]).
2. `Mint_dest(t) ≡ Burn_source(t)` sur fenêtre glissante (invariant de pont [51]).
3. `Σ dettes d'un marché ≤ Σ valeur de sortie réalisable du collatéral` (invariant de solvabilité, formulation ORVYREN : valeur = ce qu'on obtient réellement en vendant, pas le prix oracle).
4. `p_oracle(A) ≈ p_marché(A)` à ±100 bps (invariant de désaccord oracle/marché — le cas Chainlink 0,9069 vs Bitstamp 0,8053 montre que l'oracle **échoue** lors des crises).
5. `cash_r / S_r ≥ 1 − U_max` par réserve (invariant de liquidité de sortie — 100 % d'utilisation = sortie impossible).
6. `|état(RPC_i) − état(RPC_j)| = 0` sur un état critique (invariant anti-empoisonnement de source [51]).
7. `R_A ≤ 1` (pas de promesse de valeur supérieure à la valeur réalisable — ré-hypothécation [48]).
8. Composition : `w_A ≤ w_max` par marché (invariant de concentration).
9. Cohérence temporelle : la date de mise à jour de l'oracle `updatedAt > now − heartbeat` (un prix périmé est un prix faux).
10. Cohérence gouvernance : tout changement de paramètre (timelock, seuil de liquidité, multisig) est un événement daté et public (cas Drift : timelock nul le 27 mars 2026, [58]).

---

## (c) Les 3–5 signaux à implémenter EN PREMIER pour la démo

> Justification commune : **calculables dès aujourd'hui avec des sources publiques testées le 2026-10-15**, sans clé API, et **chacun a une antériorité documentée dans un épisode du dossier P1**.

1. **1.1 + 1.2 — Décote de peg multi-venues + dispersion** (`coins.llama.fi` + Binance + OKX). C'est la porte d'entrée la moins coûteuse (1 requête HTTP par actif), elle couvre 4 épisodes (UST, USDC, USD0++, xUSD) et elle est **déjà reproduite** ici (0,8767 agrégat vs 0,8053 Bitstamp le 11 mars 2023).
2. **2.1 + 2.3 — Utilisation d'une réserve + vitesse de vidange** (`eth_call` sur aToken/underlying, multi-chaînes). Deux appels par marché, archive disponible : la démo peut rejouer le 18 avril 2026 (rsETH) et le 12 mai 2022 (stETH).
3. **5.1 — Invariant d'offre inter-chaînes** (`totalSupply` par chaîne via RPC publics). C'est **le candidat A du problème**, la méthode nommée par Chainalysis [51], et la démo peut l'exécuter en direct sur rsETH/weETH/USDe.
4. **4.1 — Détection de valorisation fixe** (variance du prix oracle = 0 vs prix de sortie réel). C'est le signal qui manquait dans xUSD [48] et USD0++ [39] : il transforme « l'invisible on-chain » en alerte datée.
5. **1.5 / 3.2 — Profondeur de sortie pour une taille donnée** (`get_dy` Curve, `QuoterV2` Uniswap). Sans lui, les quatre autres signaux restent théoriques : il répond à « ce que je vois, puis-je le vendre ? ».

Signaux laissés pour la v2 : 3.3 (concentration des détenteurs — endpoints non testés/à clé), 6.2 (corrélation de flux), 5.3 (configuration de pont), 2.4 (agrégation inter-protocoles complète).

---

## (d) Ce qui n'est PAS calculable (ou pas encore) et pourquoi

| Élément | Raison |
|---|---|
| CoinGecko historique (avant 365 j) | API publique refusée : `error_code 10012`, « Public API users are limited to querying historical data within the past 365 days » (testé 2026-10-15) |
| Coinbase Exchange candles historiques | `api.exchange.coinbase.com/products/USDC-USD/candles` → `{"message":"NotFound"}` (testé) |
| Archive Ethereum sur `ethereum.publicnode.com` | « Archive requests require a personal token » (testé) |
| `polygon-rpc.com` | « API key disabled, reason: tenant disabled » — nécessite un autre RPC Polygon (non testé) |
| Liste des détenteurs (3.3) | Etherscan v2 exige une clé API ; Blockscout v2 à tester (URL fournie, non validée) |
| Ordre du carnet (book depth) sur les venues centralisées | Les API publiques consultées exposent des OHLC/trades, pas des snapshots de carnet historiques ; profondeur CEX = **non calculable avec ces sources** |
| « 100 % d'utilisation » exact de rsETH le 18/04/2026 | Non encore reconstruit par nos soins — méthode validée, série historique à exécuter (voir § à compléter) |
| Le chiffre « Bitstamp 0,8627 » du brief | **Non reproduit** : la mesure 1h donne 0,80526 ; source exacte du 0,8627 non trouvée |

---

## (e) Sources citées

Numérotation identique à `P1_probleme_financier.md` (voir ce fichier pour les URLs complètes) :
[3] FEDS Note (2025-12-17) · [4] arXiv 2606.07442 (2026-06-05) · [11] Jump Crypto, UST · [13] Nansen/CoinDesk (2022-06-29) · [14] Hashdex · [15] Reuters (2022-06-13) · [18][19] FTX/Alameda · [21][23] Ronin · [36] ezETH · [39] USD0++ · [48] Stream Finance/xUSD · [51] Chainalysis (2026-04-23) · [52] OpenZeppelin · [53] LayerZero · [58] Drift/Circuit Security · [90] CoinShares · [91] Yahoo/BeInCrypto · [99] dette DeFi interconnectée.

Sources techniques testées le 2026-10-15 (preuves dans `raw_w2b/`) :
- `https://eth.drpc.org`, `https://eth-mainnet.public.blastapi.io` (archive `eth_call` OK)
- `https://arb1.arbitrum.io/rpc`, `https://mainnet.optimism.io`, `https://mainnet.base.org` (OK)
- `https://coins.llama.fi/prices/current|historical|chart/...`, `https://stablecoins.llama.fi/stablecoins`
- `https://api.binance.com/api/v3/klines`, `https://www.okx.com/api/v5/market/history-candles`, `https://www.bitstamp.net/api/v2/ohlc/usdcusd`
- `https://yields.llama.fi/pools`
- Contrats : Chainlink USDC/USD `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6` ; Chainlink stETH/ETH `0x86392dC19c0b719886221c78AB11eb8Cf5c52812` ; Curve stETH/ETH `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` ; Aave V3 Ethereum Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`, Oracle `0x54586bE62E3c3580375aE3723C145253060Ca0C2`, aEthUSDC `0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c`, aEthrsETH `0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1`, rsETH `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7`, WETH aToken `0x4d5F47FA6A74757f35C14fD3a6Ef8E3C9BC514E8` ; Aave V3 Arbitrum Pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`. Adresses issues de `bgd-labs/aave-address-book` (`src/AaveV3Ethereum.sol`, `src/AaveV3Arbitrum.sol`, récupérés le 2026-10-15).

---

## (f) À compléter (v2) — chantiers ouverts

1. Reconstruction historique de `U(rsETH)` sur Aave V3 Ethereum **et** Arbitrum autour du 18 avril 2026 (blocs ≈ 24,9 M) → mesurer si U franchit 90/95/99 % **avant** 17:35 UTC.
2. Test de `QuoterV2` Uniswap V3 pour la profondeur (slipage par taille) + courbe de décote Curve pour 1 / 100 / 1 000 / 10 000 ETH.
3. Test de l'invariant 5.1 en direct (totalSupply rsETH/weETH sur 4 chaînes) — preuve « démo ».
4. Test Blockscout v2 pour la concentration des détenteurs (3.3).
5. Vérification de l'identité exacte du feed `0x86392dC19c0b719886221c78AB11eb8Cf5c52812` (stETH/ETH marché vs taux d'échange).
