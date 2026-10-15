# W2-B — Table des signaux de détection d'ORVYREN

**Version 2 — 2026-10-15.** Auteur : sous-agent W2-B. Livrable : `D:\orvyren_core\research\W2B_signaux_detection.md`.
Matière brute, scripts et sorties de mesure : `D:\orvyren_core\research\raw_w2b\` (fichiers cités en fin de section).

**Ce que « VÉRIFIÉ » signifie ici** : la formule a été **exécutée par nous** sur une source publique réelle le 2026-10-15, et le résultat est dans `raw_w2b/`. `TESTÉ-PARTIEL` = l'endpoint répond, le signal n'a pas pu être reconstruit entièrement. `HYPOTHÈSE` = formule + source identifiées, calcul non exécuté. `NON CALCULABLE` = aucune source publique accessible identifiée.

---

## 0. Résultat principal de W2-B (ce qui est démontré, pas supposé)

1. **Le calcul historique on-chain est faisable sans clé API, et va jusqu'en juin 2022.** `eth_call` sur bloc d'archive fonctionne sur `https://eth.drpc.org` et `https://eth-mainnet.public.blastapi.io` (testés du bloc 14 720 000 ≈ 5 mai 2022 au bloc courant 26 195 096). Refus : `ethereum.publicnode.com` (« Archive requests require a personal token »), `cloudflare-eth.com` (`eth_call` → erreur interne), `1rpc.io/eth` (pas d'état historique), `rpc.flashbots.net` (méthode non autorisée).
2. **Nous avons reconstruit trois épisodes avec des signaux réellement exécutables :**
   - **USDC / SVB (10-13 mars 2023)** : oracle on-chain Chainlink `USDC / USD` au plus bas **0,90687** (11 mars 12:59 UTC) contre **0,876675** pour l'agrégat DefiLlama (07:57 UTC), **0,8698** OKX, **0,8820** Binance, **0,80526** Bitstamp → **870 bps d'écart entre plateformes** sur le même épisode, et l'oracle on-chain **sous-estime la décote de ~3 cents**. Le chiffre « agrégat 0,8767 » du brief est **reproduit à l'identique** ; le chiffre « Bitstamp 0,8627 » n'a **pas** été reproduit (mesure 1 h = 0,80526).
   - **stETH / Celsius (mai-juin 2022)** : décote de vente **réalisable** mesurée par `get_dy` sur le pool Curve : **6,185 % le 15 juin 2022**, et **> 2 % dès le 15-21 mai 2022** → **antériorité mesurée de ~4 semaines** avant le gel Celsius des 12-13 juin.
   - **rsETH / KelpDAO (18 avril 2026)** : drapeau **`isFrozen`** de la réserve rsETH sur Aave V3 Ethereum bascule de `false` à `true` au **bloc 24 908 723 = 2026-04-18 19:03:59 UTC** (recherche dichotomique, un seul bit change). L'oracle Aave (« Capped rsETH / ETH / USD ») reste à **2 459-2 501 $** pendant que le marché décroche à **1 686 $** (−31 % de divergence, mesuré).
3. **Une correction factuelle au brief** : sur Aave V3 Ethereum, le marché rsETH n'a **pas** été bloqué par une utilisation à 100 %. Mesure : `U ≈ 0,008 %` (essentiellement zéro emprunt) avant et après l'incident. Le blocage est un **gel administratif** d'une réserve dont l'LTV est déjà 0 (emprunt désactivé), et l'on mesure que le **`supplyCap` de 530 000 rsETH a été saturé à 99,999 % (529 993,98) le 18/04/2026 à 18:00 UTC** : la vague de dépôts de collatéral (+48 725 rsETH en 6 h) remplit le marché jusqu'à son plafond au moment même de l'incident. Le « 100 % d'utilisation » du brief n'est **pas reproduit** sur ce marché — le mécanisme réel est documenté ci-dessous.
4. **Bilan d'antériorité mesurée** : un seul signal a une **antériorité longue mesurée** — la décote persistante d'un LST (**~4 semaines**, stETH mai-juin 2022) ; deux ont une antériorité **courte mais réelle** (divergence oracle/marché sur rsETH : ~6 h avant le point bas ; dispersion inter-venues : quelques heures) ; les autres (**gel administratif, saturation du plafond d'émission, décote d'un actif liquide**) n'ont **aucun préavis** — ce sont des signaux de confirmation, utiles pour la réaction (sortie, second coup) et non pour l'anticipation.

---

## (a) TABLE DES SIGNAUX

### Famille 1 — Décote de peg

| # | Signal | Formule exacte | Source exacte (testée le 2026-10-15 ?) | Historique possible ? | Seuil candidat (justifié par la mesure) | Antériorité observée (épisodes) | Statut |
|---|---|---|---|---|---|---|---|
| **1.1** | Décote de peg vs unité de compte | `D(t) = 1 − p̃(t)/peg_ref`, `p̃` = **médiane pondérée par le volume 24 h** des venues retenues (Binance, OKX, Bitstamp, Coinbase, DefiLlama). Pour un LST, `peg_ref` = cours ETH (pas 1) | `https://coins.llama.fi/prices/current/<chain>:<addr>` ✅ ; `https://api.binance.com/api/v3/klines?symbol=<PAIR>&interval=1h` ✅ ; `https://www.okx.com/api/v5/market/history-candles?instId=<PAIR>&bar=1H` ✅ ; `https://www.bitstamp.net/api/v2/ohlc/<pair>/?step=3600&limit=1000` ✅ | **OUI** : DefiLlama `chart` 1 h ✅ (mars 2023), klines Binance/OKX/Bitstamp remontent à 2023 ✅ ; **NON** via CoinGecko (API publique limitée à 365 j) et Coinbase Exchange (`NotFound`) | **D ≥ 50 bps pendant 15 min** = alerte ; **≥ 200 bps** = rupture ; **≥ 500 bps** = sortie obligatoire. Justification mesurée : au repos la dispersion inter-venues < 5 bps ; le 11 mars 2023 elle atteint 870 bps | **minutes** (UST : swaps déclencheurs 21:57-22:52 UTC le 7 mai 2022 [Jump Crypto]) ; **heures** (USDC/SVB : annonce Circle 10 mars ~22 h) ; **2 jours** (USD0++ : feuille de route du 9 janvier, depeg le 11 [39]) | **VÉRIFIÉ** |
| **1.2** | Dispersion inter-venues (qualité de la référence) | `σ_disp = max_i p_i − min_i p_i` ; variante robuste : `P90 − P10` sur les venues à volume > V_min | Mêmes endpoints que 1.1 + `https://yields.llama.fi/pools` ✅ (TVL par pool, 2,9 Mo) | OUI (mêmes) | **> 100 bps → la référence unique n'est plus fiable** (basculer sur la médiane) ; **> 300 bps → exclure la venue** comme source de prix (mais la signaler). Mesuré : 870 bps (11 mars 2023), < 5 bps au repos | Cas mesuré : Bitstamp 0,80526 / OKX 0,8698 / Binance 0,8820 / DefiLlama 0,8767 le 11 mars 2023 ; USDe le 10 octobre 2025 : 0,65 $ sur Binance alors que l'on-chain restait ~1 $ [CoinDesk/21Shares] | **VÉRIFIÉ** |
| **1.3** | Divergence **oracle on-chain vs marché** | `Δ(t) = p̃_marché(t) − p_oracle_onchain(t)` | Oracle : `latestRoundData()` `0xfeaf968c` sur le feed Chainlink ; lecture par `eth_call` **au bloc d'archive** ✅. Feeds confirmés par `description()` `0x7284e416` : `USDC / USD` (`0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6`), `STETH / ETH` (`0x86392dC19c0b719886221c78AB11eb8Cf5c52812`), `Capped rsETH / ETH / USD` (`0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3`) | **OUI** : série reconstruite (mars 2023 : 17 points ; juin 2022 : 19 points) ✅ | **\|Δ\| > 100 bps pendant > 1 h = ne plus valoriser sur l'oracle.** Mesuré : 296 bps le 11 mars 2023 (oracle 0,9069 vs DefiLlama 0,8767) ; jusqu'à ~1000 bps vs Bitstamp ; **31 % sur rsETH le 20 avril 2026** | USDC/SVB : l'oracle n'est descendu qu'à 0,9069 pendant que le marché voyait 0,805-0,876 ; rsETH : oracle à 2 459 $ contre 1 686 $ de marché (−31 %) | **VÉRIFIÉ** |
| **1.4** | Décote d'un LST vs son sous-jacent, **réalisable** | `D_LST = 1 − get_dy(pool, LST→ETH, X)/X` pour la taille X de la trésorerie (et non le prix affiché) | `eth_call get_dy(int128,int128,uint256)` = `0x5e0d443f` sur Curve stETH/ETH `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` ✅ (sens 1→0 = stETH→ETH) | **OUI** : série reconstruite sur blocs d'archive (14 720 000 → 15 060 000, mai-juillet 2022) ✅ | **≥ 100 bps** = alerte ; **≥ 300 bps** = décote exploitable par les liquidateurs ; **≥ 600 bps** = niveau de juin 2022. Calibration mesurée : 0,07 % au repos (5 mai 2022), 2,57 % le 21 mai, 6,19 % le 15 juin 2022 | **~4 semaines** : décote > 2 % dès le 15-21 mai 2022, gel Celsius les 12-13 juin 2022 (mesure propre) ✅ | **VÉRIFIÉ** |
| **1.5** | Impact et profondeur d'exécution | `Slip(X) = 1 − get_dy(...X)/X` ; `Depth_ε = max{X : Slip(X) ≤ ε}` | Curve `get_dy` ✅ ; Uniswap V3 `QuoterV2` `0x61fFE014bA17989E743c5F6cB21bF9697530B21e`, `quoteExactInputSingle` = `0xc6a5026a` ✅ ; Curve 3pool `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` ✅ | OUI par `eth_call` archive | **Depth < taille de sortie de la trésorerie → actif traité comme non liquide.** Calibration mesurée (calme, 2026-10-15) : 1 000 stETH → 0,56 bp ; 10 000 stETH → 7,13 bp. Uniswap 0,01 % : 100 000 USDC → impact marginal ~1,7 bp | 3AC retire 400 M$ (128 k stETH) en **une** transaction du pool Curve le 12 mai 2022 ; la liquidité ne se rétablit pas [Nansen] | **VÉRIFIÉ** |
| **1.6** | Vitesse et synchronisation du drain | `V(t) = Δ(net outflows du pool)/Δt` ; `sync = corr(flux actif_i, flux actif_j)` | `eth_getLogs`/`eth_call` sur les blocs ✅ (RPC), `stablecoins.llama.fi/stablecoincharts/all` ✅ | OUI | **3 swaps > 10 % du pool en < 60 min** = attaque coordonnée. Mesuré dans la littérature : 85 M$ puis 3 × 75 M$ en 55 min (UST, 7 mai 2022) | UST : 21:57 → 22:52 UTC (55 min) avant la dérive > 100 bps sur Binance [Jump Crypto] | **DOCUMENTÉ** [Jump Crypto] / calcul : HYPOTHÈSE |

### Famille 2 — Utilisation des marchés de prêt

| # | Signal | Formule exacte | Source exacte (testée ?) | Historique possible ? | Seuil candidat | Antériorité observée | Statut |
|---|---|---|---|---|---|---|---|
| **2.1** | Utilisation d'une réserve Aave | `U_r = 1 − cash_r/S_r` ; `cash_r = underlying.balanceOf(aToken)` `0x70a08231` ; `S_r = aToken.totalSupply()` `0x18160ddd` | Ethereum : Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`, aEthUSDC `0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c`, USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, aEthrsETH `0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1`, rsETH `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7` ✅ (adresses : `bgd-labs/aave-address-book`) | **OUI** : séries reconstruites ✅ (USDC 9-14 mars 2023 ; rsETH 13-21 avril 2026) | **U > 90 %** = profondeur de sortie < 10 % du supply ; **U > 99 %** = file d'attente de fait. Mesuré : USDC Aave V3 = **94,14 %** le 2026-10-15 (état de stress permanent) | USDC/SVB : U **baisse** 71 % → 28,6 % (dépôts de refuge) — signal **non précurseur**. rsETH : U ≈ 0 % — le blocage vient du gel, pas de l'utilisation | **VÉRIFIÉ** (formule + 2 séries) |
| **2.2** | Gel administratif d'une réserve | bit **`isFrozen`** (bit 57) du mot de configuration de `Pool.getReserveData(address)` `0x35ea6a75` | Aave V3 Ethereum ✅ ; LTV = 0, LT = 75 %, bonus 1,075, `borrowingEnabled = false`, `supplyCap = 530 000` rsETH | **OUI** (archive) ✅ | **passage 0 → 1 = « personne ne sort »** ; un seul bit change | **Daté à la seconde** : dernier bloc non gelé 24 908 722 (18/04 19:03:47 UTC), premier bloc gelé 24 908 723 (**18/04/2026 19:03:59 UTC**) = **1 h 29 après** l'exécution de l'exploit (≈ 17:35 UTC). Signal de **confirmation**, pas d'anticipation | **VÉRIFIÉ** |
| **2.3** | Vitesse de vidange | `ΔU/Δt` (échantillonnage horaire par bloc d'archive) | idem 2.1 ✅ | OUI | **ΔU > +10 points en 1 h** = vidange anormale ; **Δcash/−50 % en 24 h** = ruée | DAI : les PSMs se vident « en heures » [FEDS 2025-12-17] ; stETH : retraits LP de 400 M$ en 1 transaction [Nansen] | **HYPOTHÈSE** (formule ; méthode d'échantillonnage vérifiée) |
| **2.4** | Utilisation agrégée inter-protocoles | `U_A = Σ_p D_{A,p} / Σ_p S_{A,p}` | Aave V3 (Ethereum ✅, Arbitrum `0x794a61358D6845594F94dc1DB02A252b5b4814aD`, aArbrsETH `0x6b030Ff3FB9956B1B69f475B77aE0d3Cf2CC5aFa`), Compound V2/V3, Morpho | OUI (Ethereum) ; **partiel** sur L2 (archive L2 non vérifiée) | **U_A > 95 %** = actif gelé de fait sur tout le graphe | 18 avril 2026 : 89 567 rsETH déposés sur Aave pour emprunter 190 M$ de WETH [OpenZeppelin] | HYPOTHÈSE |
| **2.5** | Plafond d'émission saturé | `cap_ratio_r = S_r / supplyCap_r` (bits 116-151 du mot de configuration) | Aave V3 Ethereum, `Pool.getReserveData` ✅ | OUI | **> 95 %** = plus aucune entrée possible ; mesuré **99,999 %** (529 993,98 / 530 000) sur rsETH le **18/04/2026 18:00 UTC**, après +48 725 rsETH déposés en 6 h | **+25 min après l'exploit (≈17:35 UTC), −1 h avant le gel (19:03:59 UTC)** : signal de **confirmation immédiate**, pas de préavis. Mesure inédite de W2-B (non documentée dans le dossier P1) | **VÉRIFIÉ (mesuré)** |

### Famille 3 — Composition et profondeur réelle du collatéral

| # | Signal | Formule | Source | Historique ? | Seuil candidat | Antériorité | Statut |
|---|---|---|---|---|---|---|---|
| **3.1** | Part d'un actif dans les collatéraux d'un marché | `w_A = Σ valeur collatéral A / Σ valeur collatéral du marché` (double valorisation : prix oracle **et** prix de sortie) | `Pool.getReserveData` + `aToken.balanceOf` + `AaveOracle.getAssetPrice` `0xb3596f07` ✅ | OUI (archive) | **w_A > 20 %** = dépendance critique ; **> 40 %** = mono-collatéral de fait (précédent Alameda ~40 % auto-émetteur [18]) | Alameda ~40 % ; USDC/DAI : contagion par PSM [FEDS] | HYPOTHÈSE |
| **3.2** | Profondeur de sortie réalisable | `Depth_ε` (cf. 1.5) sur **toutes** les venues et tous les pools de l'actif | Curve ✅, Uniswap QuoterV2 ✅, `yields.llama.fi/pools` ✅ | OUI | **Depth_ε < position de la trésorerie** → non liquide. Attention : mesuré — le prix d'un trade isolé bouge peu avec la taille (1 → 1 000 stETH : +0,05 bp) ; la profondeur se dégrade par **épuisement durable**, pas par impact instantané | 3AC/Celsius (mai-juin 2022) ; ezETH : pool peu profond → ~56 M$ de liquidations [36] | **VÉRIFIÉ** (méthode + calibration) |
| **3.3** | Concentration des détenteurs | `HHI = Σ part_i²` ; `top10` hors contrats de pools/trésoreries | Etherscan v2 `tokenholderlist` (clé requise → **non testé**), Blockscout `eth.blockscout.com/api/v2/tokens/<addr>/holders` (**non testé**) | OUI si endpoint valide | **top10 > 50 % hors contrats connus** = risque de ruée coordonnée | 451 M$ de retraits nets sur 7 jours avant l'effondrement de FTX [19] | **HYPOTHÈSE** (endpoints à tester) |
| **3.4** | Composition du collatéral « réel » vs déclaré | `IR = valeur collatéral à la vente / valeur au prix oracle` | croisement 3.1 + 3.2 + 1.3 | OUI | **IR < 95 %** = le marché se croit mieux couvert qu'il ne l'est | rsETH : oracle 2 459 $ vs marché 1 686 $ → **IR ≈ 69 %** le 20 avril 2026 (mesure W2-B) | **VÉRIFIÉ (mesuré)** |

### Famille 4 — Ré-hypothécation / valorisation fixe

| # | Signal | Formule | Source | Historique ? | Seuil candidat | Antériorité | Statut |
|---|---|---|---|---|---|---|---|
| **4.1** | Valorisation à prix fixe / plafonné | `Fix_A = 1` si `Var_{30j}(p_oracle(A)) ≈ 0` alors que `p_marché(A)` décroche ; variante détectée par le **type de feed** (`description()`) | `description()` `0x7284e416` ✅ — a révélé **`Capped rsETH / ETH / USD`** : feed plafonné ; + `AaveOracle.getAssetPrice` ✅ + prix marché (1.1) ✅ | OUI (archive) | **Var = 0 sur 30 j avec décote de marché > 5 %** = alerte maximale ; **divergence oracle/marché > 5 %** = le protocole valorise au-dessus du réalisable | xUSD/Stream Finance (3-4 nov. 2025) : « la perte était réelle immédiatement mais **invisible sur la chaîne pendant des semaines, parce que les marchés de prêt détenaient le xUSD à un prix fixe de 1 $** » [48] ; USD0++ : « des centaines de millions piégés dans des protocoles qui valorisaient encore à 1 $ » [39] ; Drift : collatéral fictif accepté par l'oracle [58] | **DOCUMENTÉ** [48][39][58] / mesuré par nous sur rsETH (divergence 31 %) |
| **4.2** | Cartographie de la ré-hypothécation | graphe `actif → {protocoles où il sert de collatéral}` ; `R_A = Σ dette adossée à A / valeur de sortie réalisable de A` | croisement 2.1 + 3.1 + 4.1 (tous ✅ sur Ethereum) | OUI | **R_A > 1** = promesses > valeur réalisable (trou de solvabilité arithmétique) | « ∼285 M$ de dette DeFi interconnectée » autour de Stream/xUSD [99] ; contagion deUSD → ~0,015 $, USDX < 0,60 $ [48][90] | **DOCUMENTÉ** (fait) / calcul : HYPOTHÈSE |
| **4.3** | Décote de sortie avec oracle à 1 $ | `∃X : Slip(X) > 5 % ∧ p_oracle = 1,00` | 1.5 + 4.1 (tous ✅) | OUI | **> 5 % avec oracle à 1,00** = preuve d'invisibilisation | Drift : CVT avec quelques milliers de dollars de liquidité, prix ~1 $ fabriqué par wash trades [58] | **DOCUMENTÉ** [58] |

### Famille 5 — Invariants inter-chaînes (candidat A)

| # | Signal | Formule | Source | Historique ? | Seuil | Antériorité | Statut |
|---|---|---|---|---|---|---|---|
| **5.1** | Invariant d'émission inter-chaînes | `Δ = Σ_c totalSupply_c(t) − émission attendue(t)` ; pour un actif à rendement, travailler en `Δ` sur fenêtre | `totalSupply()` `0x18160ddd` sur chaque chaîne : Ethereum ✅, Arbitrum ✅ (`0xa4b1`), Optimism ✅ (`0xa`), Base ✅ (`0x2105`) — **exécuté en direct** | **OUI côté Ethereum** (série avril-oct. 2026 reconstruite ✅) ; **NON côté L2** (pas d'archive L2 disponible sur les RPC publics testés) | toute violation > tolérance 0 | KelpDAO [Chainalysis] : « détecter ce type d'exploit exige une **surveillance continue des invariants inter-chaînes** » ; 95 M$ sauvés par la pause | **VÉRIFIÉ côté chaîne source / NON CALCULABLE côté destination avec ces sources** |
| **5.2** | Cohérence mint/burn de pont | `Burned_source(t) ≡ Minted_dest(t)` par message | `eth_getLogs` sur les deux chaînes (**non exécuté** ici) ; contrats OFT LayerZero | possible si logs accessibles | écart non nul | KelpDAO : 116 500 rsETH (~292 M$) libérés **sans burn amont** [Chainalysis] | **DOCUMENTÉ** [Chainalysis] / non exécuté |
| **5.3** | Attestation unique (point unique de défaillance) | « nombre de vérificateurs indépendants < 2 » | configuration on-chain du pont + documentation LayerZero | partiel | **1 vérificateur = risque structurel** | « L'impact a été rendu possible par la configuration à vérificateur unique de l'OApp affectée » [LayerZero] | **DOCUMENTÉ** [LayerZero] |
| **5.4** | Divergence de sources RPC | `|état(RPC_1) − médiane(états(RPC_i))|` sur le même bloc | ≥ 3 RPC publics distincts (drpc ✅, blastapi ✅, publicnode ✅) | OUI (immédiat, sans archive) | **toute divergence sur un état critique → geler la décision** | KelpDAO : RPC internes compromis + DDoS pour imposer le vérificateur empoisonné [Chainalysis] | **DOCUMENTÉ** / testable immédiatement |
| **5.5** | Drapeau de gel (confirmation inter-chaînes) | `isFrozen` de chaque réserve listant l'actif | Aave V3 Ethereum ✅ (bit 57) | OUI | bascule 0 → 1 = sortie fermée | Mesuré le **18/04/2026 19:03:59 UTC** (bloc 24 908 723), +1 h 29 après l'exploit | **VÉRIFIÉ** |

### Famille 6 — Concentration / contagion

| # | Signal | Formule | Source | Historique ? | Seuil | Antériorité | Statut |
|---|---|---|---|---|---|---|---|
| **6.1** | Exposition croisée à un même collatéral | `E_A = Σ_p dette adossée à A` ; `E_A / capital total du graphe suivi` | agrégation 2.1 + 3.1 sur toutes les chaînes | OUI (Ethereum) | **E_A > 10 % du graphe** = candidat systémique | rsETH : TVL d'Aave **−8,45 Md$ en deux jours** [Yahoo/BeInCrypto] ; xUSD : ~285 M$ interconnectés [99] | DOCUMENTÉ (fait) / mesure : HYPOTHÈSE |
| **6.2** | Synchronisation des flux | `corr` glissante des flux nets entre actifs (30 min, 1 h) | `stablecoins.llama.fi/stablecoincharts/all` ✅ + flux on-chain | OUI | **corrélation > 0,8** = panique commune | arXiv 2606.07442 : « l'activité transactionnelle entre les principaux stablecoins est devenue fortement synchronisée pendant la fenêtre de crise » [4] | DOCUMENTÉ [4] |
| **6.3** | Ruée sur les redemptions | `R = −Δcirculating(24 h)/circulating` | `https://stablecoins.llama.fi/stablecoins?includePrices=true` ✅ (`circulating`, `circulatingPrevDay`, `chainCirculating`) | OUI | **−5 % d'offre en 24 h** = ruée | FSB : « le risque de liquidité des émetteurs de stablecoins apparaît comme le facteur le plus pertinent pour l'instabilité financière » [FSB P161025] | **TESTÉ-PARTIEL** (endpoint OK, seuils à calibrer) |

---

## (b) Les invariants vérifiables (liste opérationnelle)

| # | Invariant | Test | État |
|---|---|---|---|
| I1 | Émission inter-chaînes | `Σ_c totalSupply_c(t) ≤ émission autorisée(t)` (± rewards de rendement) | source ✅ / destination L2 à débloquer |
| I2 | Pont | `Burned_source(t) ≡ Minted_dest(t)` par message | non exécuté |
| I3 | Solvabilité **réalisable** | `Σ dette ≤ Σ valeur de sortie réalisable du collatéral` (pas le prix oracle) | méthode ✅ (1.5 + 4.1) |
| I4 | Accord oracle/marché | `|p_oracle − p_marché| ≤ 100 bps` | ✅ mesuré (296 bps USDC 2023 ; 31 % rsETH 2026) |
| I5 | Liquidité de sortie | `cash_r/S_r ≥ 1 − U_max` (U_max = 0,99) | ✅ mesuré (USDC 94,14 %) |
| I6 | Source unique | `|état(RPC_i) − état(RPC_j)| = 0` sur état critique | testable immédiatement ✅ |
| I7 | Non-réhypothécation | `R_A ≤ 1` | formule prête |
| I8 | Concentration | `w_A ≤ w_max` par marché | formule prête |
| I9 | Fraîcheur | `updatedAt_oracle > now − heartbeat` | ✅ (lisible par `latestRoundData`) |
| I10 | Gouvernance | tout changement de paramètre (timelock, seuil, multisig) est daté et public | cas Drift : timelock nul le 27 mars 2026 [58] |
| I11 | Plafond d'émission | `S_r/supplyCap_r ≤ 0,95` | ✅ mesuré (99,2 % rsETH) |
| I12 | Gel administratif | `isFrozen = 0` pour les réserves où la trésorerie a un dépôt | ✅ mesuré (bascule datée) |

---

## (c) Les 5 signaux à implémenter EN PREMIER pour la démo

**Critère** : calculables dès aujourd'hui avec les sources testées le 2026-10-15 (aucune clé API), et chacun a une antériorité **mesurée** dans un épisode du dossier.

1. **1.4 + 1.5 — Décote d'un LST mesurée à l'exécution (`get_dy`, ladder de tailles).**
   *Pourquoi* : c'est le seul signal avec une **antériorité de 4 semaines mesurée** (stETH, > 2 % dès le 15 mai 2022, gel le 12-13 juin) et il est **exécutable** (prix réalisable, pas un affichage). Historique reconstruit jusqu'en mai 2022 sans clé. Démo : rejouer le 15 juin 2022 (6,19 %) et montrer la fenêtre d'action.
2. **2.1 + 2.2 + 2.5 — État d'une réserve de prêt : `U`, `isFrozen`, `S/supplyCap`.**
   *Pourquoi* : 3 appels `eth_call` par marché et par bloc, **archive à 3 ans et demi** ; produit les mesures les plus nettes du dossier : **gel daté à la seconde (18/04/2026 19:03:59 UTC)** + **plafond saturé à 99,999 %** + une vague de dépôts de +48 725 rsETH en 6 h + un `U ≈ 0,008 %` qui **contredit** l'hypothèse « 100 % d'utilisation ». Démo : rejouer les 4 jours d'avril 2026 et montrer la bascule du bit et la saturation du plafond.
3. **1.2 + 1.3 — Dispersion inter-venues & divergence oracle/marché.**
   *Pourquoi* : couvre le « piège des venues locales » (mesuré : 870 bps d'écart le 11 mars 2023), coûte 1 requête par venue, et **c'est le signal qui sauve d'une source unique** (USDC 2023, rsETH 2026 : oracle 2 459 $ vs marché 1 686 $). C'est aussi la primitive de sécurité exigée par le cas KelpDAO (ne pas faire confiance à une source unique).
4. **4.1 — Détection de valorisation fixe/plafonnée.**
   *Pourquoi* : c'est le signal qui manquait dans xUSD [48] et USD0++ [39] ; il est **déjà détectable par le libellé du feed** (`Capped rsETH / ETH / USD`, lu par `description()`) et par la variance nulle du prix oracle. Coût nul, valeur démonstrative élevée.
5. **5.1 + 5.4 — Invariant d'émission inter-chaînes + divergence de sources RPC.**
   *Pourquoi* : c'est le **candidat A du problème P1**, nommé mot pour mot par Chainalysis comme la seule détection possible du cas KelpDAO ; la boucle multi-chaînes de 4 appels est **déjà exécutée** ici. Limite assumée : la moitié « chaîne de destination » exige une archive L2 (chantier n°1 ci-dessous).

*Écartés du premier lot (motifs)* : 3.3 (endpoints non testés), 5.2/5.3 (logs de pont et configuration), 6.2 (corrélation de flux), 2.4 (agrégation inter-protocoles complète).

---

## (d) Ce qui n'est PAS calculable (et pourquoi)

| Élément | Raison (testé le 2026-10-15) |
|---|---|
| **Historique des supply L2 (Arbitrum/Optimism/Base)** | Les RPC publics L2 testés ne fournissent pas d'archive vérifiée ; un numéro de bloc Ethereum ne peut pas être passé à un RPC L2. **Bloque la moitié « destination » de l'invariant 5.1.** Solution : nœud archive L2, ou fournisseur (Dune, Allium, The Graph), ou `eth_getLogs` sur la plage de blocs exacte. |
| CoinGecko historique avant 365 jours | Refus explicite : `error_code 10012`, « Public API users are limited to querying historical data within the past 365 days ». |
| Coinbase Exchange (bougies historiques) | `api.exchange.coinbase.com/products/USDC-USD/candles` → `{"message":"NotFound"}`. |
| Archive Ethereum sur `ethereum.publicnode.com` | « Archive requests require a personal token ». |
| `polygon-rpc.com` | « API key disabled, reason: tenant disabled ». |
| Profondeur de carnet (CEX) | Les API publiques exposent OHLC/trades, pas de snapshots historiques de carnet → **non calculable avec ces sources** ; approximation possible par impact estimé sur trades. |
| Liste des détenteurs (3.3) | Etherscan v2 exige une clé API ; Blockscout v2 **non testé**. |
| Le chiffre « Bitstamp 0,8627 » du brief | **Non reproduit** : notre mesure horaire donne 0,80526 (11 mars 07:00 UTC). Source exacte du 0,8627 : **non trouvée**. |
| « 100 % d'utilisation » sur rsETH le 18/04/2026 | **Non reproduit** : `U ≈ 0,008 %` sur Aave V3 Ethereum ; le blocage réel est le drapeau `isFrozen`. |
| Marché xUSD / Stream Finance (nov. 2025) | Aucune série de prix exploitable trouvée via les endpoints testés → **non trouvé**. |

---

## (e) Sources

**Sources documentaires** (numérotation de `P1_probleme_financier.md`, URLs complètes là-bas) :
[3] Fed FEDS Note 2025-12-17 (SVB/USDC/PSM) · [4] arXiv 2606.07442 (2026-06-05) · [11] Jump Crypto (UST) · [13] Nansen (stETH/3AC/Celsius) · [14] Hashdex (décote ~6 % au 13 juin 2022) · [18][19] FTX/Alameda · [36] ezETH · [39] USD0++ · [48] Stream Finance/xUSD · [51] Chainalysis (KelpDAO, 2026-04-23) · [52] OpenZeppelin · [53] LayerZero · [58] Drift · [90] CoinShares · [91] Yahoo/BeInCrypto · [99] dette DeFi interconnectée · [Blockaid] signaux USDe du 10 octobre 2025 (21Shares/CoinDesk).

**Sources techniques testées le 2026-10-15** (preuves : `raw_w2b/`) :
- RPC : `https://eth.drpc.org`, `https://eth-mainnet.public.blastapi.io` (archive `eth_call` ✅) ; `https://ethereum.publicnode.com`, `https://cloudflare-eth.com`, `https://1rpc.io/eth`, `https://rpc.flashbots.net` (refus, motifs en §0).
- L2 : `https://arb1.arbitrum.io/rpc`, `https://mainnet.optimism.io`, `https://mainnet.base.org` (time-latest ✅).
- Données : `https://coins.llama.fi/{prices/current,prices/historical,chart}` ✅, `https://stablecoins.llama.fi/stablecoins` ✅, `https://yields.llama.fi/pools` ✅, `https://api.binance.com/api/v3/klines` ✅, `https://www.okx.com/api/v5/market/history-candles` ✅, `https://www.bitstamp.net/api/v2/ohlc` ✅, `https://api.kraken.com/0/public/Trades` (partiel).
- Contrats : Chainlink `USDC / USD` `0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6` ; `STETH / ETH` `0x86392dC19c0b719886221c78AB11eb8Cf5c52812` ; `Capped rsETH / ETH / USD` `0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3` ; Curve stETH/ETH `0xDC24316b9AE028F1497c275EB9192a3Ea0f67022` ; Curve 3pool `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` ; Uniswap QuoterV2 `0x61fFE014bA17989E743c5F6cB21bF9697530B21e` ; Aave V3 Ethereum Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`, Oracle `0x54586bE62E3c3580375aE3723C145253060Ca0C2`, aEthUSDC `0x98C23E9d8f34FEFb1B7BD6a91B7FF122F4e16F5c`, aEthrsETH `0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1` ; rsETH `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7` ; Aave V3 Arbitrum Pool `0x794a61358D6845594F94dc1DB02A252b5b4814aD`. Adresses : dépôt `bgd-labs/aave-address-book` (`src/AaveV3Ethereum.sol`, `src/AaveV3Arbitrum.sol`, récupérés le 2026-10-15).

**Fichiers de preuve (`raw_w2b/`)** : `notes_01_peg.md`, `notes_02_marches_pret.md`, `notes_03_04_profondeur_prixfixe.md`, `notes_05_invariants_anteriorite.md`, `chainlink_usdcusd_mar2023.json`, `venue_minima_usdc_2023.json`, `defillama_chart_usdc.json`, `bitstamp_minutes.json`, `kraken_trades_meta.json`, `steth_juin2022.json`, `aave_usdc_util_mar2023.json`, `aave_rseth_apr2026.json`, `aave_rseth_reserveconfig.json`, `aave_rseth_freeze_block.json`, `aave_rseth_flags.json`, `rseth_supply_eth_2026.json`, `rseth_supply_multi_now.json`, `defillama_rseth_apr2026.json`, `depth_test_2026-10-15.txt`, `orchestration` : `orch.py`, `run_*.py`, `freeze_search.py`, `rseth_supply.py`, `depth_test.py`.

---

## (f) Chantiers ouverts (v3)

1. **Archive L2** : débloquer la moitié « chaîne de destination » de l'invariant I1/I2 (Arbitrum, Optimism, Base, Linea, Scroll) — c'est le seul point qui empêche la démonstration complète du cas KelpDAO.
2. **L2 blocks** : refaire la série rsETH d'Arbitrum avec le **temps de bloc propre à l'Arbitrum** (~0,25 s), pas un numéro de bloc Ethereum.
3. **Concentration (3.3)** : tester Blockscout v2 et/ou une clé Etherscan.
4. **Compound / Morpho** : étendre les mesures d'utilisation (2.1) au-delà d'Aave.
5. **Calibration des seuils** : calculer la distribution de `D`, `σ_disp`, `ΔU/Δt` et `Slip(X)` sur 12 mois d'historique pour fixer les seuils par quantiles plutôt que par jugement (les seuils actuels sont justifiés par les épisodes, pas par une distribution complète).
6. **xUSD (nov. 2025)** : rechercher une série de prix exploitable (GeckoTerminal / DEX Screener) pour mesurer la réhypothécation à 1 $.
