# U2 — ORGANISATIONS / GESTION BASÉE SUR LA DEFI
## Cible d'un agent wallet on-chain autonome : trésoreries de protocoles, DAOs, fonds — et équipes de trading crypto

**Projet ORVYREN** — agent wallet on-chain autonome (concours FinTech Shenzhen 2026, thème F : exécution on-chain autonome d'opérations d'actifs, d'exécution et de contrôle du risque dans une enveloppe bornée).
**Synthèse** établie le **15 octobre 2026** à partir de la matière brute collectée les 14–15 octobre 2026 (`raw_u2/digest_batches.txt`, `raw_u2/pages/*`, `raw_u2/batch{1,2,3}.json`) et de 4 recherches web complémentaires (15 octobre 2026).
**Règle appliquée** : aucun chiffre ni source inventés ; « non trouvé » lorsque l'information manquait dans la matière disponible. Chaque chiffre est suivi de sa source et de sa date.

---

## 0. Résumé exécutif

- Les trésoreries on-chain des grandes DAOs se situent entre **~$60 M et ~$1,6 Md** fin 2025–2026 (Lido : 157,5 M$ fin 2025 → 121,0 M$ fin avril 2026 ; ENS Endowment : 101,6 M$ en janvier → 67,7 M$ en juin 2026 ; Aave DAO : ~140–181 M$ ; Optimism : ~1,57 Md$ de valeur sécurisée au 31 août 2026 ; Sky : buffer > 80 M$ + 2,1 Md$ de RWA tokenisés). Toutes **baissent en valeur USD** sur la période, principalement par effet prix ETH.
- La gestion est **déléguée à des prestataires humains et à des outils paramétrables** : managers de mandats (kpk pour ENS, 0,50 %/an), risk providers (Chaos Labs, LlamaRisk, Gauntlet), curateurs de vaults (Block Analitica, Steakhouse), exécution sous permissions on-chain (Safe + Zodiac Roles, CoW Swap) et comités (TMC de Lido, MetaGov d'ENS). L'exécution y est déjà **automatisée et bornée** — mais la décision reste humaine et gouvernée.
- **Douleur n°1 — le risk management est fragile et sous-financé** : Chaos Labs, risk provider principal d'Aave pendant 3 ans (zéro bad debt matériel), a quitté le protocole le **6 avril 2026** en refusant un budget de 5 M$ qu'il jugeait insuffisant (minimum estimé : 8 M$, soit 5,6 % des revenus ; les banques allouent 6–10 %) — troisième départ d'un contributeur cœur en deux mois.
- **Douleur n°2 — les incidents infra, pas les bugs** : l'exploit rsETH de KelpDAO via le bridge LayerZero (**18 avril 2026, ~$290–292 M**, config DVN 1-of-1, empoisonnement RPC) a provoqué **123,7 M$ à 230,1 M$ de bad debt estimé sur Aave**, ~13 Md$ de TVL évaporée en 48 h, des marchés figés à 100 % d'utilisation, et une sortie préventive des positions Aave de l'Endowment ENS (sans perte) ; Lido a versé 2 500 stETH (5,74 M$) au fonds DeFi United.
- **L'outillage existant couvre le monitoring, la simulation, la curation et l'automation simple** (DeFi Saver 0,25–0,30 % ; Tenderly freemium ; Safe/Zodiac open source ; Defender en fin de vie au 1er juillet 2026) **mais pas l'exécution discrétionnaire bornée en 24/7** — c'est précisément l'espace d'un agent autonome, à condition d'accepter l'enveloppe : caps, whitelist de venues, delay/council, audit trail.
- **Verdict provisoire** : segment **crédible mais étroit et sous pression budgétaire**. Les acheteurs réalistes en 2026 sont les managers de mandats, les desks d'exécution et les fonds — pas les DAOs en direct ; les conditions sont détaillées en §F.

---

## A. Qui gère des trésoreries on-chain — ordres de grandeur sourcés

### A.1 Lido DAO — la plus documentée

| Indicateur | Valeur | Source, date |
|---|---|---|
| Total DAO Treasury | **157,5 M$ au 31 déc. 2025 → 121,0 M$ au 30 avr. 2026** (−36,5 M$), dont **(31,6) M$ d'effet prix stETH** | `research.lido.fi/t/lido-financial-report-for-q1-2026/11623` — posté le 4 juin 2026 |
| Clôture H1 2026 | Trésorerie **88,3 M$** (contre 157,5 M$) ; revenu net DAO H1 **15,9 M$** vs dépenses Fondations **14,3 M$** | X @LidoFinance — août 2026 (post récapitulatif tokenholders) |
| P&L Q1 2026 | Revenu net DAO **9,42 M$** ; dépenses Fondations **6,44 M$** ; **surplus de trésorerie 2,98 M$** ("surplus au niveau du protocole cœur") | rapport Q1'2026 ci-dessus |
| Pertes/coûts liés à l'incident rsETH | Don de **2 500 stETH (5,74 M$)** à l'initiative DeFi United (avril 2026) + **144 ETH (0,32 M$)** de "First Loss Protection" en mai 2026 | idem + `research.lido.fi/t/lido-dao-contribution-to-coordinated-rsETH-relief-effort/11483` et `/t/authorise-loss-coverage-below-the-1-threshold-for-the-kelp-incident/11527` |
| Discipline budgétaire | Utilisation de la grant EGG 2026 : **22 %** en 4 mois, « ⅓ en dessous » d'une trajectoire linéaire ; décision de couper les dépenses après le repli de février | rapport Q1'2026 ci-dessus |
| Revenus 2025 | **Gross revenue −18,2 % en glissement annuel** (−17,4 % en ETH) | `research.lido.fi/t/goose-2025-eggs-2025-final-report/11304` (date exacte non précisée dans la source) |
| Trésorerie en stETH | 41 753,7 → 43 833,9 stETH (31 déc. → 31 mars), puis **40 428,3 stETH au 30 avr.** après le don rsETH (−3,1 % vs 31 déc.) | rapport Q1'2026 |
| Gestion quotidienne | **Treasury Management Committee** (conversions stables → **sUSDS**), soldes opérationnels de BORG (stables passés de 7,0 à 14,2 M$ temporairement pour exécution), **market makers** mandatés pour le trade stETH/LDO | rapport Q1'2026 (liens TMC et stETH/LDO trade) |

**Lecture** : un trésor de taille moyenne (~100–160 M$), en contraction en USD, géré par un mélange de comités, BORGs (entités juridiques DAO), multisigs (TRP Committee, Growth Committee) et prestataires. C'est un marché solvable mais **sous régime de restriction budgétaire**.

### A.2 ENS DAO — le cas le plus proche d'un "agent borné" déjà en place

| Indicateur | Valeur | Source, date |
|---|---|---|
| Endowment (actifs) | **101,6 M$ en janvier → 67,7 M$ fin juin 2026** (« presqu'entièrement l'effet de prix ETH sur l'allocation 60 % ETH ») ; perte de juin : −17,8 M$ dont −18,8 M$ de mark-to-market ETH | `discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358` — 14 août 2026 |
| Performance | Rendement DeFi brut H1 : **1,37 M$** ; net **1,15 M$** ; APY brut 3,12 % (net 2,62 %) vs benchmark IPS 2,80 % ; **+9,9 M$ de rendement cumulé depuis mars 2023, sans perte de principal** | idem |
| Frais du manager | **221 275 $ au H1 (~0,50 % annualisé), sans performance fee** | idem |
| Trésorerie DAO (hors Endowment) | **88 M$ fin juin** (50,0 M$ ETH + 36,7 M$ USDC), contre 148 M$ un an plus tôt ; **runway 71 mois** (burn normalisé 1,24 M$/mois ; ~65 mois selon les sorties projetées à 1,36 M$/mois) | idem |
| Contraintes de mandat | 60/40 ETH/stables ; cap 30 % par protocole ; pas de LST > 20 % du consensus ; jusqu'à 10 % en modéré-risque ; jusqu'à **5 % RWA tokenisés** (IPS 2026) | idem + `discuss.ens.domains/t/6-46-social-2026-endowment-investment-policy-update/22106` |
| Automatisation on-chain déjà live | **Registrar Manager (EP 6.39), live avril 2026** : les revenus .eth (~**1 M$ non capturés depuis janvier 2024** selon la proposition) arrivent directement à l'Endowment via un `withdraw()` permissionless ; un **module Zodiac** maintient ~6 mois de runway USDC dans le timelock, rebalancé trimestriellement **sans proposition par transfert** | revue KPK H1 2026 (14 août 2026) |
| Outils d'exécution | **Zodiac Roles v2** (politique de permissions mise à jour 2× en 2026 : Update #8 et #9), **CoW Swap** pour le routing (GHO, FLUID, weETH/eETH), multisigs "Avatar Safe" | idem |
| En cours | **Overlay d'options on-chain** (covered calls / cash-secured puts) proposé pour H2 2026 ; phasage d'un sleeve RWA | idem |

**Lecture** : ENS est le cas d'école d'une trésorerie qui a **déjà industrialisé l'exécution sous permissions pré-approuvées** (Zodiac Roles + Delay, module de runway, Registrar Manager) tout en gardant la décision (IPS, cap, venues) au niveau gouvernance. Les "Updates #8/#9" montrent aussi la **dette opérationnelle** : chaque nouvelle venue stratégique nécessite une mise à jour de permissions gouvernée.

### A.3 Aave DAO — le plus gros budget de gestion, sous tension

- Trésorerie DAO : **140 M$** (post Chaos Labs du 6 avril 2026, `governance.aave.com/t/chaos-labs-is-leaving-aave/24386`) ; **181 M$** fin avril selon Galaxy Research (62 M$ ETH-correlés, 54 M$ AAVE, 52 M$ stables) — les deux périmètres/dates diffèrent, conserver les deux avec leurs sources.
- **Buybacks** : 42 M$ déployés pour acquérir **205 000 AAVE** en 10 mois depuis le 9 avril 2025 (`governance.aave.com/t/aave-dao-funding-insights/24192`) ; budget buyback **réduit de ~50 M$ à 30 M$** (`governance.aave.com/t/arfc-buyback-program-budget-adjustment/24229`).
- Revenue policy : vote du **13 avril 2026** renvoyant **100 % des revenus applicatifs et produits vers les détenteurs d'AAVE** (CoinDesk, 13 avril 2026, `/tech/2026/04/13/aave-passes-landmark-vote...`).
- Dépenses d'incitations 2025 : **101 M$** au total (**21,2 M$** trésorerie DAO + **80 M$** partenaires externes), pilotées par ACI (`governance.aave.com/t/aci-full-transparency-report/24085`).
- Marché RWA institutionnel : **Aave Horizon**, lancé en août 2025 (Token Terminal, rapport Aave juillet 2026 — post X).
- Safety module "Umbrella" : couverture automatisée du bad debt par slashing d'aTokens en temps réel ; **~54 M$ de couverture aWETH sur Ethereum L1 uniquement, pas de couverture L2** (Galaxy Research, 22 avril 2026 ; `aave.com/docs/aave-v3/umbrella`).

### A.4 Sky (ex-MakerDAO)

- **Surplus buffer > 80 M$** (Eco, fiche USDS vs DAI 2026) ; **66 M$ de net protocol surplus cumulé 2026 sur cinq mois**, déjà au-dessus du total 2025 (MilkRoad). Plan : **500 M SKY** dirigés vers la trésorerie, buybacks quotidiens portés à **300 000 USDS/jour** (Blockworks). **2,1 Md$ de positions RWA tokenisées** détenues par Sky seul (Eco, article "DAO Treasury Management").

### A.5 Optimism Collective

- **~1,57 Md$ de valeur sécurisée par OP Mainnet au 31 août 2026** (~585 M$ en ETH et dérivés, 443 M$ en stables, reste en autres actifs) (`optimism.io/blog/optimism-governance-sequencer-enterprise-facts`).
- **~21,5 K ETH** en trésorerie ("ETH n'est pas qu'une réserve, c'est un outil stratégique") (X @OptimismGov).
- Allocation initiale : 25 % à la Fondation, 5 % à la Citizens' House (Eco, rétroplanning des allocations : Uniswap 43 %, **ENS 50 %**, Optimism 25 %+5 %).

### A.6 Métriques transversales utiles

- **La plupart des DAOs détiennent 60–90 % de leur trésorerie dans leur token natif** (Eco) : c'est ce qui explique la sensibilité extrême des NAV aux marchés (Endowment ENS : 60 % ETH par mandat, d'où −33,9 M$ au H1).
- Les trésoreries paient déjà pour : reporting comptable (**Steakhouse** pour ENS, dashboards Dune), risk reviews (**Sentralis** — teardown indépendant sur le livre de juin, depuis mai·juin 2026 : stablecoins vendables en semaine de crise **23,4 M$**, plus gros protocole **~22,7 %**, probabilité de finir l'année au-dessus du plancher de 49,34 M$ entre **49 % et 90 %** selon le modèle — estimations de modèle, pas des faits, `discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358/3`, 17 août 2026).

---

## B. Douleurs documentées (montants + dates)

### B.1 Chaos Labs quitte Aave (6 avril 2026) — le signal de fragilité du risk management

Source primaire : `governance.aave.com/t/chaos-labs-is-leaving-aave/24386` (post d'Omer Goldberg, 6 avril 2026) ; couverture : CoinDesk 6 avril 2026, The Defiant (2e départ/3e contributeur en deux mois), Yahoo Finance.

- Chaos Labs a opéré le risk management d'Aave depuis **novembre 2022** : « zero material bad debt » ; Aave est passé de **5,2 Md$ à plus de 26 Md$ de TVL**, 2,5 T$ de volume cumulé de dépôts, 2 Md$+ de liquidations ; l'infrastructure **Risk Oracles** maintient 250+ marchés sur 19 chaînes avec des centaines de mises à jour de paramètres/mois.
- **Raisons du départ** : (1) départs de contributeurs cœur → charge et risque opérationnel accrus ; (2) **V4 change l'architecture** → nouveau code, nouveaux modes de défaillance, le scope risque double pendant la transition V3→V4 ; (3) **économie de l'engagement insoutenable**.
- **Chiffres** : budget 2025 = **3 M$/an, soit ~2 % des 142 M$ de revenus d'Aave** ; Aave Labs a soutenu une hausse à **5 M$**, insuffisante ; minimum estimé par Chaos : **8 M$ (5,6 %)** ; référence : les banques allouent **6–10 % des revenus** au risk/compliance. Trésorerie DAO citée : **140 M$**, plus 50 M$ d'auto-financement Aave Labs.
- **Externalités non couvertes** : responsabilité légale du risk manager/curateur « fondamentalement indéfinie » (pas de safe harbor), et coût cyber/subi.
- LlamaRisk a pris la suite (post "Ensuring Continuity of Aave's Risk Management", 6 avril 2026 ; renouvellement "epoch 4" débattu en mai 2026, `governance.aave.com/t/arfc-renew-llamarisk-as-risk-service-provider-epoch-4/24446`) — **prix du renouvellement : non trouvé dans la matière**.

**Pourquoi c'est un signal pour ORVYREN** : le marché du risk management on-chain a des **coûts réels non compressibles**, une **volonté de payer sous tension** (V4 + baisse des revenus applicatifs + buybacks coupés de 50 à 30 M$) et une **offre fragmentée** (3 départs en 2 mois). Un agent borné ne remplace pas Chaos Labs ; il peut en revanche reprendre des tâches de surveillance/exécution dont le coût humain est refusé.

### B.2 Incident rsETH / KelpDAO–LayerZero (18 avril 2026) — le scénario de stress de référence

Sources : Galaxy Research, « KelpDAO/LayerZero Exploit Drains $290m, Freezes DeFi Markets », 22 avril 2026 (`galaxy.com/insights/research/kelpdao-layerzero-exploit-defi`) ; Chainalysis, 23 avril 2026 ; OpenZeppelin « $292 Million Lost, Zero Bugs Found ».

- **18 avril 2026, 17:35 UTC** : un attaquant (préliminairement attribué au groupe Lazarus/TraderTraitor de la RPDC) délivre un paquet LayerZero forgé (fausse origine Unichain) au bridge OFT de rsETH et **libère 116 500 rsETH (~$292 M, plus grand exploit DeFi de 2026)**. Mécanisme : **empoisonnement RPC + DDoS de failover** contre la config **DVN 1-of-1** (LayerZero Labs seul vérifieur) ; ni clé ni bug de contrat compromis. KelpDAO pause les contrats **46 minutes** après le drain ; Aave gèle rsETH/wrsETH en **77 minutes** (18:52 UTC) via le Guardian 5-of-9.
- **Contagion** : collatéral déposé sur Aave/Compound/Euler, emprunts estimés à **236 M$ de WETH/wstETH** ; **TVL DeFi −13 Md$ en 48 h** (~99,5 → 86,3 Md$) ; Aave −8,45 Md$ (26,4 → 17,9 Md$, perd sa place de n°1) ; **WETH et stables à 100 % d'utilisation** (retraits bloqués), ~5,4 Md$ d'ETH/WETH sortis en un week-end ; bad debt Aave estimé : **123,7 M$ (socialisation uniforme, haircut 15,12 %)** ou **230,1 M$ (pertes isolées aux L2 rsETH)**.
- **Réponse** : **Arbitrum Security Council (12 membres, vote 9-of-12)** gèle **30 766 ETH (~71 M$)** transférés vers un wallet gelé — mécanisme qui démontre qu'un conseil peut modifier les contrats du bridge sans délai (Galaxy) ; SparkLend, Fluid, Upshift gèlent leurs marchés rsETH ; **Lido pause les dépôts d'earnETH** ; Ethena, Curve, BitGo, Pendle, Yearn, Beefy, Lombard prennent des mesures préventives. **Morpho : exposition totale ~$1 M** (architecture isolée par marché) — contraste parfait avec Aave, dont la décision de janvier 2026 d'élever le LTV rsETH en E-Mode **de 72 % à 93 %** a amplifié la perte.
- **Ripple interne** : l'Endowment ENS (manager kpk) **sort préventivement de ses positions Aave le 18 avril et les reconstruit en mai, sans perte** (lending ENS : 15,8 M$ en mars → **67 $** en avril → 15,6 M$ en mai — `discuss.ens.domains/.../22358`) ; Lido contribue **2 500 stETH (5,74 M$)** au dispositif DeFi United et constate **144 ETH (0,32 M$)** de first-loss ; LayerZero annonce **ne plus signer de messages pour toute app en config DVN 1-of-1**.
- **Métrique d'attaque globale** : Lazarus est lié au Drift exploit (**1er avril 2026, 285 M$**) et à KelpDAO (**18 avril, 292 M$**) = **~575 M$ drainés en 18 jours par une seule unité étatique**, via deux vecteurs structurellement différents, **sans aucun bug de smart contract** (Galaxy, 22 avril 2026). KelpDAO est le plus gros exploit crypto **depuis Bybit ($1,4–1,5 Md, 21 février 2025)**.

### B.3 Les précédents qui pèsent (à citer dans tout pitch)

| Incident | Montant | Date | Enseignement pour la thèse |
|---|---|---|---|
| Crash du 10 octobre 2025 | **> 19 Md$ de liquidations en ~1 jour, 1,6 M de comptes** (BTC −14 %, XRP −37 % en 1 h) | 10 oct. 2025 | FTI Consulting, CoinDesk, CoinGecko : le tail risk de levier est **systémique** ; les desks et trésoreries ont besoin de coupe-circuits automatiques |
| Bybit (cold wallet) | ~1,5 Md$ (FBI : RPDC) | 21 fév. 2025 | FBI.gov ; la clé/UI humaine reste le maillon faible |
| WazirX (multisig) | **~230–235 M$** | 18 juil. 2024 | Wikipedia/Elliptic/The Record : un multisig mal configuré ne protège pas |
| Radiant Capital | **~50–53 M$** (Mandiant : RPDC) | 16 oct. 2024 | Medium post-mortem Radiant : malware sur poste dev, "3 signatures sur des tx que personne ne lisait" |
| Beanstalk (gouvernance) | **182 M$** (profit attaquant ~76–80 M$) | 17 avr. 2022 | Merkle/Certik : une **attaque de gouvernance par flash loan** — vecteur direct contre toute automatisation de trésorerie |
| rsETH/KelpDAO | ~290–292 M$ | 18 avr. 2026 | §B.2 |

### B.4 La douleur structurelle : trésoreries en baisse, budgets sous pression

- Lido : −36,5 M$ en 4 mois (dont −31,6 M$ d'effet stETH) ; clamp sur les grants (22 % d'utilisation) ; contribution forcée de 6,06 M$ aux secours rsETH.
- ENS : −33,9 M$ sur le H1 pour l'Endowment, réserves DAO divisées par ~1,7 en un an ; le budget de fonctionnement dépend à **~31 %** du yield DeFi du H1 (1,37 M$ de yield pour ~4,42 M$ de revenu brut DAO).
- Aave : buyback coupé de 50 → 30 M$ ; budget risk refusé à 3 M$ puis 5 M$ et provider parti.
- Générique : **60–90 % de la trésorerie en token natif** (Eco) → toute baisse prolongée du marché réduit mécaniquement la capacité à payer des prestataires.
- Conclusion opérationnelle : **le budget "alpha/optimisation" recule ; le budget "sécurité/risque/urgence" tient mieux** — mais il est lui aussi contesté (cf. Chaos). Un nouveau produit doit donc viser un **coût par tâche exécutée** faible et une valeur démontrable en premier lieu sur **l'urgence et l'ops**, pas sur le rendement.

---

## C. Tableau de l'outillage — fait | ne fait pas | prix

Sources principales : batch2 + pages brutes (`raw_u2`), complétées le 15 octobre 2026 par `tenderly.co/pricing`, `milkroad.com/reviews/defi-saver/` et les recherches Hypernative/Coinshift.

| Outil | Fait | Ne fait pas | Prix (si public) |
|---|---|---|---|
| **Chaos Labs** | Risk oracles 24/7 : modèle chaque prêt, simulations, MAJ de paramètres temps réel (250+ marchés / 19 chaînes) ; due diligence institutionnelle (Horizon) | Ne prend pas de clés, n'exécute pas la stratégie ; ne gère pas la trésorerie. **Quitte Aave le 6 avr. 2026** | Aave 2025 : **3 M$/an (~2 % des revenus)** ; proposition 5 M$ refusée ; minimum estimé 8 M$ (5,6 %). Public : non (sur devis) |
| **Gauntlet** (+ **Aera**) | Recherche éco + risk params ; **Aera** = protocole de gestion de trésorerie on-chain "autonome" non-custodial, les *guardians* exécutent les opérations une fois le vault alloué (Xai Foundation, Seamless/Aerodrome, temperature check Compound) | Non-custodial : pas de garde de clés ; pas de discrétion hors stratégie définie | Tour de table **8 M$** mené par Bain Capital Crypto (PRNewswire). Prix d'engagement : **non trouvé** |
| **Hypernative** | Détection/prévention en temps réel : alertes prédictives (liquidations, de-peg), threat detection, **réponse automatisée** ; clients institutions/asset managers (ex. Hardcore Labs) | Ne fait pas d'exécution de trades ni de gestion de portefeuille | Non public (sur devis). Financement : **$40 M Série B juin 2025** (Ten Eleven + Ballistic), Série A 11 M$ (avr. 2024), seed 8,35 M$ (2022) |
| **Block Analitica** | Curateur de vaults MetaMorpho (flagship ETH/USDC/USDT avec B.Protocol depuis nov. 2023) ; advisory risk (Sky, Spark) ; dashboards | Pas d'exécution détenue : les paramètres passent par gouvernance ; pas de custody | Non public ; **couverture ~17 Md$** de dashboards/curation (fiche Alchemy) |
| **Credora (by RedStone)** | Notations de crédit DeFi **A+→D** pour vaults/marchés/actifs/emprunteurs, **100 000 simulations Monte-Carlo par marché** ; Consensus Ratings lancés fév. 2025 | Pas d'exécution, pas de monitoring temps réel de marché | Non public. Acquis par **RedStone (4 sept. 2025)** (CoinDesk) |
| **Coinshift** | Plateforme treasury ops : paiements, payroll, accounting, insights, vaults (csUSDL backé USDL/Paxos International, The Defiant) | Pas de risk management de marché ni de mandats d'allocation | Non public. Repère général du reporting institutionnel : **15–50 k$/mois** (article Eco, périmètre plus large que Coinshift) |
| **Enzyme** | Asset management on-chain : création de vaults "Vault-as-a-Service", frais paramétrables par le manager, comptabilité on-chain transparente | Ne décide pas la stratégie (le manager la fournit) ; échelle minuscule | Frais : framework flexible manager-défini (docs.enzyme.finance). **Revenus protocole 2026 : 6,83 k$ Q1 / 36,51 k$ Q2 / 26,06 k$ Q3*** (DefiLlama) |
| **DeFi Saver** | Automation de positions : protection liquidation, gestion du levier, stop loss/take profit, trailing stop ; **non-custodial** ; simulation | Pas de gestion de trésorerie multi-venues ; EVM limité (Ethereum, Arbitrum, Base, Optimism) ; pas de custody | **0,25–0,30 % sur actions avancées et automation** (Milk Road review 2026) ; sinon gratuit |
| **Safe + Zodiac** | Safe = smart wallet multisig standard des trésoreries DAO ; **Zodiac** = modules composables (**Roles v2**, Delay, Governor) pour permissions par rôle et exécutions différées ; utilisé par l'Endowment ENS avec CoW Swap | Ne décide rien : les rôles/permissions sont fixés par gouvernance ; pas de monitoring | **Open source / gratuit** (GitHub gnosisguild/zodiac ; docs.safe.global) |
| **OZ Defender** | Monitoring (Sentinels), relayers, automation, advisories | — | **Sunset acté : arrêt définitif le 1er juillet 2026** ; SDK déprécié ; pivot OpenZeppelin vers l'open source (openzeppelin.com/news ; github.com/OpenZeppelin/defender-sdk) |
| **Tenderly** | Simulation/forking (Simulator), debugger, monitoring multicanal + Web3 Actions de réponse automatisée, RPC ; utilisé par Aave, Morpho, Safe, Sky, Uniswap (logos site) | Pas de gestion de portefeuille ni de stratégie ; pas d'exécution autonome (les Web3 Actions sont déclenchées par règles) | **Free** (individus, sans API) ; Console équipes **sur devis** : "capacity, support and chain count are sized in conversation" (tenderly.co/pricing, consulté le 15 oct. 2026) |
| **kpk (ex-karpatkey)** — *manager, pas outil, mais ancrage de prix* | Gestion de mandat : exécution, monitoring de positions, gestion des permissions Zodiac, reporting mensuel, négociation de termes avec contreparties | Ne modifie pas le mandat (les changements passent par gouvernance : PUR #11 à venir options) | **0,50 % annualisé sur actifs, sans performance fee** (221 275 $ au H1 2026 pour ~44 M$ moyens) |
| **LlamaRisk / Steakhouse / Sentralis** | Risk reviews + modélisation de scénarios (LlamaRisk : rapport d'incident rsETH du 20 avr. 2026, scénarios 123,7/230,1 M$) ; comptabilité et reporting (Steakhouse : decks mensuels ENS) ; teardown risque indépendant (Sentralis) | Pas d'exécution on-chain | **Prix : non trouvé** |

**Lecture outillage (pour le pitch)** :
1. La chaîne "décision" (Chaos, Gauntlet, BA, Credora, kpk) est humaine/cher et non-scalable ; la chaîne "exécution mécanique" (DeFi Saver, Zodiac, Tenderly) est bon marché ou gratuite. **L'espace laissé vide est l'exécution décisionnelle bornée en 24/7 avec auditabilité** — exactement le produit ORVYREN.
2. Le départ d'OZ Defender (1er juillet 2026) laisse un **vide de migration** pour les équipes qui l'utilisaient pour relais/monitoring : opportunité de positionnement "successeur borné et open".
3. Les prix publics ancrent le budget : 0,25–0,30 % par action automatisée (DeFi Saver), 0,50 %/an pour un mandat complet géré par des humains (kpk), 3–8 M$/an pour un risk provider d'un top protocole (Chaos sur Aave). Un agent autonome doit se vendre **sous le coût humain par tâche**, pas au niveau d'un mandat complet.

---

## D. Ce qu'ils délégueraient (et ne délégueraient pas)

### D.1 Déjà délégué — avec preuves

| Tâche déléguée | À qui/quoi | Preuve |
|---|---|---|
| Exécution quotidienne sous permissions | kpk via **Zodiac Roles v2** pour l'Endowment ENS, mises à jour de politique par gouvernance (EP 6.38/6.41) | revue KPK H1 2026, 14 août 2026 |
| Flux de revenus → trésorerie, sans vote par transfert | **Registrar Manager** (Blockful) + module Zodiac de runway (~6 mois USDC rebalancés par trimestre) | idem |
| Réquilibrages/transactions | tranches standard 1 500 ETH, tranche d'urgence 3 000 ETH (IPS 2026) | idem |
| Conversions stables → sUSDS, exécution du cash management | **Treasury Management Committee** de Lido + BORGs + multisigs | rapport Q1'2026 Lido |
| Market making des avoirs du DAO | **market makers** mandatés (mandat stETH/LDO de Lido, exécution par des mains externes) | rapport Q1'2026 Lido |
| Reporting mensuel, comptabilité, benchmark | Steakhouse (ENS), dashboards Dune/Syncrone | revue KPK H1 2026 |
| Risk params, garde des marchés | Chaos Labs (jusqu'avril 2026), LlamaRisk (depuis), Umbrella (automatique) | governance.aave.com ; Galaxy 22 avr. 2026 |
| Sorties préventives en crise | Exécution **humaine rapide** (kpk sort de Aave le 18 avril ; Aave gèle en 77 min ; Kelp pause en 46 min) | idem |

### D.2 Défendablement délégable à un agent borné (les candidats)

- **Réquilibrage mécanique dans une bande** : maintenir 60/40 (ou tout mandat) avec tranches bornées, après événements de marché — humain : IPS/caps, agent : calcul et exécution.
- **Ops de vault et de positions** : rollovers, claims de rewards, conversions programmées (sUSDS/BUIDL/RWA sleeve), gestion de runway.
- **Playbooks d'urgence pré-approuvés** : unwind des positions risquées (comme kpk en avril), rapatriement vers prêts/stables, avec kill-switch conseil ; valeur mesurée en minutes (fenêtre de gel à 100 % d'utilisation).
- **Monitoring + alerte + action bornée** : détecter de-peg/incident (Hypernative-like) et n'exécuter que le sous-ensemble d'actions pré-autorisées.
- **Exécution de flow pour desks** : DeFi leg des opérations (DEX, vaults, perps on-chain) sous limites d'exposition strictes.
- **Reporting automatique auditable** : produire les rapports mensuels/benchmarks (aujourd'hui manuels : Dune, Syncrone, Steakhouse).

### D.3 Ce qu'ils ne délégueraient PAS (freins objectifs)

- **Custody et clés** : tout ce qui touche timelock, Security Council, upgrade de contrats (le précédent Arbitrum : pouvoir d'upgrade 9/12 sans délai, utilisé pour récupérer des fonds — et critiqué pour la même raison). L'agent devra rester **sous multisig/timelock avec caps et delay**, jamais porteur de clés souveraines.
- **Décision d'allocation stratégique** : IPS, caps, whitelist de venues (chaque nouvelle venue = proposition gouvernée ; ENS l'illustre avec ses Updates #8/#9).
- **Responsabilité légale** : « fondamentalement indéfinie » selon Chaos Labs — les DAOs ne peuvent pas s'appuyer sur un agent comme bouc émissaire ; il faut une structure porteuse (BORG-like) et des clauses.
- **Risk management de marché intégral** : pas remplaçable par un agent en 2026 ; c'est un métier (modèles, simulations, paramétrage V4).
- **Décisions de dernière extrémité** : récupération de fonds, votes d'urgence, négociations.

---

## E. Équipes de trading crypto — cible secondaire

### E.1 Paysage des market makers / desks (les cibles "fonds")

| Firme | Profil (sourcé) | Pertinence ORVYREN |
|---|---|---|
| **Wintermute** | Firme de trading algorithmique, liquidité sur CEX, DEX et OTC (wintermute.com ; MarketsWiki) | Exécution on-chain native (DEX/OTC), 24/7 |
| **GSR** | "Trading solutions, market making, and risk management" ; interviews publiques sur régulation et risque (Josh Riezman, CoinDesk 8 mai 2025) ; partenariat TP ICAP | Institutionnel ; sensible à la conformité et au reporting |
| **Amber Group** | Market maker depuis 2017, stratégies quantitatives, risk management & compliance mis en avant ; valorisation 1 Md$ après levée 100 M$ (ambergroup.io/news/id/353) | Idem ; gère trésorerie et produits structurés |
| **Keyrock** | Fondé à Bruxelles en 2017 ; license **MiCA** ; market making, options, OTC, liquidité DEX ; le poste de **Head of Risk** précise : "full oversight of risk across **trading (spot and derivatives), treasury and investments, including exposures across CeFi and DeFi environments**" ; un "risk engine" dédié surveille l'exposition et fait respecter des limites (article Medium tiers) | **Le meilleur descripteur du besoin** : le risk engine existant chez les desks est exactement l'enveloppe d'un agent borné (limites, kill-switch, agrégation multi-venues) |
| **Prop firms crypto** (Spencer Logic, Spotware, Bitrates) | Modèle "évaluation" avec capital simulé, splits de profits ; **API de trading pour bots** ; KYC/fraude/automatisation de risque côté plateforme | Marché adjacent, plus retail ; l'automatisation y est déjà la norme (API + bots) — peu de traction pour un agent on-chain "wallet" |

### E.2 Ce que ces équipes demandent techniquement

- **Surveillance d'exposition et limites temps réel** : cf. Keyrock ("risk engine continuously monitors exposure and enforces limits"; "Head of Risk" co-conçoit "data, analytics and real-time risk aggregation").
- **Exécution 24/7 sans interruption** : le crash du 10 octobre 2025 (**19 Md$ liquidés, 1,6 M de comptes**) et les épisodes de 100 % d'utilisation (Aave, avril 2026) sont les scénarios de référence.
- **Opérations DeFi natives** : liquidité DEX, vaults, collatéral, funding — la "jambe on-chain" est précisément ce qu'un agent wallet peut porter.
- **Hedge et neutralité** : protection de possessions (options, perps), rebalancing entre CEX/DEX.

### E.3 Verdict du segment trading

Les grandes desks (Wintermute, GSR, Amber, Keyrock) **construisent en interne** (Keyrock recrute un Head of Risk et un PM "Risk & Rapid Response" pour *construire et scaler* leurs systèmes de gestion du risque — offre d'emploi Keyrock). La cible réaliste n'est donc **pas la vente d'un cerveau de trading** à ces firmes, mais :
1. **l'infrastructure d'exécution bornée on-chain** (API/agent) comme brique, pour les desks qui n'ont pas cette couche, et
2. **les fonds/desks plus petits** (crypto funds, family offices, prop collectifs) qui n'ont pas d'équipe risk-engine. « Non trouvé » : aucun chiffre public de budget d'un desk pour ce type d'outil dans la matière collectée.

---

## F. Trois cas d'usage défendables + verdict honnête

### F.1 Cas 1 — « Exécutant de mandat borné » pour une trésorerie DAO (rééquilibrage + ops de vault)

- **Énoncé** : un agent qui exécute le sous-ensemble *mécanique* d'un mandat de trésorerie (bandes de rééquilibrage du type 1 500 ETH, conversions programmées, claims, maintien de runway, déploiement du sleeve RWA) sous permissions pré-approuvées (Safe + Zodiac Roles v2, caps par protocole, delay module), avec rapport mensuel auditable.
- **Preuves que le besoin existe** : ENS a dû voter 2 mises à jour de permissions en 6 mois (Updates #8/#9) et a "récupéré" ~1 M$ de revenus grâce à l'automation du flux (Registrar Manager) ; kpk facture 0,50 %/an pour ce travail ; les tranches de rééquilibrage sont standardisées (1 500 / 3 000 ETH d'urgence) — donc automatisables sans discrétion.
- **Ce qui rend le cas défendable** : le ROI se mesure en coûts évités + réactivité, pas en alpha ; l'enveloppe bornée est native (permissions on-chain existantes) ; acheteur identifiable (managers type kpk, DAOs avec Endowment > 50 M$).
- **Risque** : cycle budgétaire baissier (trésoreries −20/−35 % en un semestre) ; les DAOs exigent des processus de changement lourds.

### F.2 Cas 2 — Playbook d'urgence « de-risking » exécuté en secondes

- **Énoncé** : en cas d'incident (de-peg, exploit, gel de marché), l'agent applique un playbook pré-approuvé **à périmètre fermé** — sortir des positions à risque, rapatrier vers stables, ne jamais ouvrir de nouvelle exposition — avec kill-switch gouvernance et post-mortem automatique.
- **Preuves** : rsETH 18 avril 2026 — Kelp a mis **46 min** pour pauser, Aave **77 min** pour geler, et la fenêtre de gel a bloqué ~5,4 Md$ de retraits ; kpk a dû sortir manuellement ses positions Aave et reconstruire ensuite (sans perte) ; Sentralis calcule qu'en semaine de crise ~23,4 M$ de stables ENS sont vendables — un agent qui exécute ce qui est déjà répétable réduit la fenêtre d'exposition.
- **Ce qui rend le cas défendable** : les protocoles **déploient déjà** des réponses automatiques bornées (Umbrella d'Aave : slashing temps réel ; Zodiac Delay ; timelocks) ; un agent "sortie d'urgence" s'insère dans ce cadre sans discrétion.
- **Risque** : faux positifs (déclencher une sortie coûteuse) ; il faut des oracles de sûreté de très grande qualité (ex. Hypernative) et des seuils communiqués à l'avance ; en cas d'erreur, la responsabilité (indéfinie, cf. Chaos) explose.

### F.3 Cas 3 — Couche d'exécution on-chain pour desks de trading / fonds

- **Énoncé** : agent-wallet qui exécute la "jambe DeFi" des desks (rééquilibrages DEX, hedge perps on-chain, opérations de vaults, settlement) sous limites d'exposition codées (style Keyrock risk engine), en 24/7, avec journal d'audit.
- **Preuves** : Keyrock décrit exactement ce périmètre (risque sur "trading, treasury, investments, CeFi ET DeFi") ; les MM majeurs promettent de la "risk management" (GSR, Amber) ; l'incident 10/10/2025 (19 Md$) et les marchés à 100 % d'utilisation (avril 2026) démontrent que la vitesse d'exécution est la variable critique.
- **Ce qui rend le cas défendable** : acheteurs multiples (desks sans équipe risk-engine, fonds, prop collectifs) ; modèle de vente B2B plus rapide que le cycle de gouvernance DAO.
- **Risque** : concurrence interne (les grandes firmes construisent) ; P&L invisible (coût vs alpha) ; conformité (MiCA chez Keyrock) impose un cadre que l'agent doit documenter.

### F.4 Verdict honnête — ce segment est-il crédible pour un agent on-chain autonome en 2026 ?

**Crédible, mais étroit, et uniquement sous trois conditions strictes.**

1. **Positionnement = exécutant, pas gérant.** Toute la matière converge : ce que ces organisations paient déjà (kpk 0,50 %, DeFi Saver 0,25–0,30 %, Zodiac gratuit, Aera "guardians") est de l'**exécution sous règles**. Ce qu'elles refusent de payer cher en 2026, c'est la décision non auditable — et le cas Chaos Labs montre même qu'elles contestent le prix du risk management humain. Un agent "gestionnaire discrétionnaire" ne trouvera pas d'acheteur DAO ; un agent "exécution bornée, auditée, à coût unitaire faible" en trouvera.
2. **Enveloppe bornée **native** et vérifiable** : caps par transaction/jour, whitelist de contrats/venues, delay + multisig + kill-switch conseil, simulation pré-exécution (Tenderly-like), journal on-chain. C'est aussi la thèse du concours (thème F : "enveloppe bornée") — les cas ENS (Zodiac Roles) et Lido (comités/BORGs) fournissent des **gabarits d'autorisation déjà acceptés par la gouvernance**.
3. **Priorité urgence + ops avant rendement** : les deux seuls "moments de vérité" documentés où une machine battrait l'humain sont la **fenêtre d'incident** (46–77 minutes, gel à 100 %) et l'**exécution mécanique répétitive** (rééquilibrages, flux, reporting). Le gain de rendement (alpha) n'est pas la douleur — la douleur est le coût, la lenteur, et le risque opérationnel.

**À l'inverse, trois raisons de prudence** : (a) le segment est en contraction budgétaire (trésoreries −20/−35 % au dernier semestre, buybacks coupés) ; (b) les incidents de 2026 sont **infra** (RPC poisoning, DVN 1-of-1, LTV 93 %, clés/multisigs) — un agent on-chain ne corrige pas la cause racine et peut même ajouter une surface d'attaque ; (c) la responsabilité du risk management on-chain est « fondamentalement indéfinie » (Chaos Labs) — la structure juridique du produit devra être pensée dès le pitch (entité, assurances, limitation de mandat).

**Pour le concours Shenzhen 2026 (thème F)** : le segment U2 fournit la meilleure démonstration de "enveloppe bornée" parce que les **primitives d'autorisation existent déjà** (Safe + Zodiac Roles, timelocks, caps) et que les **cas chiffrés sont abondants** (Lido 157,5→121 M$, ENS 101,6→67,7 M$, rsETH 292 M$, bad debt 123,7–230,1 M$, 19 Md$ le 10/10/2025). La démo crédible : un agent qui exécute un playbook de rééquilibrage/urgence sur un fork (Tenderly) sous permissions Zodiac, avec refus de toute action hors enveloppe — pas un fonds autonome.

---

## Annexe 1 — Sources (URL + date)

**Primaires locales (pages intégrales dans `raw_u2/pages/`)** :
- `research.lido.fi/t/lido-financial-report-for-q1-2026/11623` — Lido Financial Report Q1'2026, posté **4 juin 2026** (données au 30 avril 2026).
- `governance.aave.com/t/chaos-labs-is-leaving-aave/24386` — post **6 avril 2026** (Omer Goldberg).
- `discuss.ens.domains/t/kpk-h1-2026-review-for-the-ens-endowment/22358` — **14 août 2026** (+ commentaire Sentralis du **17 août 2026**).
- `galaxy.com/insights/research/kelpdao-layerzero-exploit-defi` — Galaxy Research, **22 avril 2026**.
- (Page extraite vide : `governance.aave.com/t/rseth-incident-report-april-20-2026/24580` — 0 octet ; le rapport d'incident LlamaRisk est cité à travers Galaxy.)

**Digest (snippets datés)** : `raw_u2/digest_batches.txt` — 25 requêtes couvrant Lido, Optimism, ENS, Sky, Aave, crash 10/10/2025, Bybit, KelpDAO, Chaos Labs, Gauntlet/Aera, Block Analitica, Credora, Coinshift, Enzyme, DeFi Saver, Safe/Zodiac, OZ Defender, GSR, Amber, Keyrock, prop desks, Umbrella, WazirX, Radiant, Beanstalk.

**Compléments du 15 octobre 2026 (4 recherches + 2 extractions)** :
- `wintermute.com` ; `marketswiki.com/wiki/Wintermute` — tradedesk algo.
- `hypernative.io` (+ `/insights/blog/hypernative-raises-40m-series-b...` Série B juin 2025 ; `startupintros.com/orgs/hypernative` pour seed/Série A).
- `tenderly.co/pricing` — consulté 15 octobre 2026 (Free + Console sur devis).
- `milkroad.com/reviews/defi-saver/` — review 2026 (frais 0,25–0,30 %).
- Coinshift : `coinshift.xyz` ; `thedefiant.io` (csUSDL) — prix non public.
- Divers déjà dans le digest : `openzeppelin.com/news/doubling-down-on-open-source-and-phasing-out-defender` (sunset 1er juillet 2026) ; `github.com/gnosisguild/zodiac` ; `docs.safe.global` ; `aera.finance` ; `prnewswire.com` (Aera, 8 M$ Bain) ; `comp.xyz` ; `credora.network` ; `coindesk.com` (RedStone/Credora, 4 sept. 2025) ; `keyrock.com` + `jobs.ashbyhq.com/keyrock` (Head of Risk) ; `gsr.io` ; `ambergroup.io` ; `governance.aave.com/t/aave-dao-funding-insights/24192` ; `governance.aave.com/t/arfc-buyback-program-budget-adjustment/24229` ; `coindesk.com/tech/2026/04/13/aave-passes-landmark-vote...` ; `optimism.io/blog/optimism-governance-sequencer-enterprise-facts` ; `milkroad.com/news/skys-record-surplus...` ; `blockworks.com/news/sky-pivots-beyond-treasuries` ; `eco.com/support/en/articles/14799687-dao-treasury-management...` ; `fticonsulting.com/insights/articles/crypto-crash-october-2025...` ; `coingecko.com/learn/october-10-crypto-crash-explained` ; `fbi.gov/investigate/cyber/alerts/2025/north-korea-responsible-for-1-5-billion-bybit-hack` ; `chainalysis.com/blog/kelpdao-bridge-exploit-april-2026/` (23 avril 2026) ; `openzeppelin.com/news/lessons-from-kelpdao-hack` ; `merklescience.com` et `certik.com` (Beanstalk) ; `medium.com/@RadiantCapital/radiant-post-mortem...` ; `aave.com/docs/aave-v3/umbrella` ; `blockworks.com/news/umbrella-reshapes-aave-staking`.

## Annexe 2 — Ce que cette synthèse n'a PAS pu établir (« non trouvé »)

- Prix publics de Chaos Labs, Gauntlet/Aera, Hypernative, Block Analitica, Credora, Coinshift, LlamaRisk, Steakhouse : **non publics** (sur devis) dans toute la matière.
- Montant du renouvellement LlamaRisk « epoch 4 » chez Aave : non trouvé.
- Budgets internes des desks de trading (GSR, Amber, Keyrock, Wintermute) pour l'outillage risque/exécution : non trouvés.
- Contenu du rapport d'incident rsETH d'Aave (`governance.aave.com/t/rseth-incident-report...`) : page extraite vide (0 octet) — à re-tenter si besoin.
- Wintermute : aucune donnée chiffrée de risque/exécution trouvée (uniquement la description "algorithmic trading firm" et liquidité CEX/DEX/OTC).

## Annexe 3 — Matière brute réutilisée

- `raw_u2/digest_batches.txt` (70 Ko, 25 requêtes) — lu en entier, source de la majorité des chiffres datés.
- `raw_u2/pages/` : 4 pages en texte intégral réutilisées (Lido Q1'2026 ; Chaos/Aave ; KPK/ENS ; Galaxy/KelpDAO) ; 1 page vide (rsETH incident report).
- `raw_u2/batch{1,2,3}.json` : vérification de couverture (les 25 requêtes du digest = les 25 clés des batchs).
- 4 recherches web complémentaires + 2 extractions (15 octobre 2026) pour : Wintermute, Hypernative, Tenderly, DeFi Saver, Coinshift.
