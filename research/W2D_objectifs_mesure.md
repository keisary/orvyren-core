# W2-D — Objectifs et fonctions de mesure, par persona

**Projet ORVYREN** — agent wallet on-chain autonome (concours FinTech Shenzhen 2026, thème F).
**Livrable** : `D:\orvyren_core\research\W2D_objectifs_mesure.md`
**Date de rédaction** : 15 octobre 2026. **Matière brute réutilisée** : `D:\orvyren_core\research\raw_w2d\` (`web_lot1.json`, `web_lot2.json`, `web_lot3.json`, `pages\`, `calculs_w2d.json`) — collecte antérieure, complétée par **3 recherches ciblées** le 15/10/2026 (§C de `web_lot3.json`) et par les livrables pairs `W2A_donnees_episodes.md` et `W2B_signaux_detection.md`.
**Décision d'équipe rappelée** : **deux personas, deux objectifs distincts** — (1) trésoreries de DAO/protocole : **prévision du risque et anticipation** ; (2) équipes de trading crypto / desks : **rentabilité**.

**Étiquettes utilisées dans tout le document** (à conserver telles quelles si des passages sont recopiés) :

| Étiquette | Signification |
|---|---|
| **FAIT SOURCÉ** | affirmé par une source publique citée (URL + date), non re-vérifié par nous numériquement |
| **MESURÉ (interne)** | valeur produite par une mesure ORVYREN antérieure, traçable dans `W2A`/`W2B` ou dans `raw_w2d\calculs_w2d.json` |
| **CONCEPTION** | proposition d'ORVYREN, non sourcée, à geler par l'équipe |
| **NON TROUVÉ** | absence de source publique, écrite telle quelle plutôt que comblée par une invention |

---

## 0. Résumé exécutif (dix points)

1. **Les deux personas n'optimisent pas la même chose, et ce n'est pas un détail marketing.** Le document de politique de l'ENS (IPS 6.46, adopté en 2026) définit le risque de la trésorerie comme **« la probabilité de ne pas honorer une obligation de liquidité ou de trésorerie » et « la probabilité de perdre le principal »** — pas comme une variance de P&L. Un desk, à l'inverse, est jugé sur un **P&L net** et sur sa **performance ajustée du risque** (Sharpe/Sortino), sous contraintes d'inventaire, de coût de capital et de capacité. **FAIT SOURCÉ** (ENS IPS ; Keyrock ; DWF Labs ; littérature de métriques).
2. **L'unité de compte diffère.** Pour la DAO, l'unité naturelle est le **jour de runway** (opex ENS 2025 = 16,4 M$/an → ≈ 44 932 $/jour ; plancher de 3 ans = 49,34 M$). Pour le desk, c'est le **bp de P&L net** sur l'inventaire exposé. Une même perte de 100 k$ vaut ≈ 2,2 jours de runway et, sur un inventaire de 2 M$, 500 bp. **CONCEPTION** (calcul : `calculs_w2d.json`).
3. **La fonction de perte antérieure était arithmétiquement fausse.** Elle soustrayait le drawdown évité à l'action RÉDUIRE **et** le chargeait à NO-ACTION : pour une position de 100 dont la richesse réelle variait de 10, elle affichait un écart de **20**. Identité démontrée : `écart_bugué − écart_vrai = q·(1 − P_T)` — la décote subie est comptée deux fois. **MESURÉ (interne)**.
4. **La formulation correcte est « richesse + actions faisables »** : `W_T(conserver) = C + q·P_T` ; `W_T(céder x) = C + x·P_exec − k + (q−x)·P_T` ; `L(a) = W_t − W_T(a)` ; `R(a) = L(a) − min_{b ∈ F} L(b)`. Elle est neutre (ajouter une constante ne change rien), sans double comptage, et dégénère correctement vers zéro quand agir et ne rien faire ont la même richesse terminale. **CONCEPTION** (formules + tests de cohérence §B.6).
5. **Le coût doit être dans la perte, pas à côté.** Le prix d'exécution `P_exec` doit être **réalisable** (mesuré au `get_dy`/carnet pour la taille de la trésorerie), et `k` regroupe frais + gas + slippage résiduel. Sans cela, on fabrique du gain (piège déjà identifié dans `R3` §(d) n°8).
6. **L'exemple USDC/SVB lu deux fois donne deux conclusions opposées, et c'est le résultat le plus utile du document.** Pour une DAO qui **devait** convertir 1,37 M$ de charges pendant la crise, pré-positionner à 0,95 puis convertir évitait **≈ 111 k$ (≈ 2,5 jours de runway)** face à une conversion à 0,8820 (plus bas Binance mesuré) — et **≈ 259 k$ (≈ 5,8 jours)** si l'exécution tombait sur la venue la plus décotée (0,80526, mesurée chez Bitstamp). Pour un détenteur **sans obligation**, le même aller-retour (sortie 0,95, re-entrée 0,99) **coûtait** 4,0 % — la « perte évitée » y est **négative**. Un desk qui coupe et rentre sur 20 bp subit −4,2 % sur son inventaire (2 M$) dans ce scénario réalisé, mais +10,8 % dans le scénario où la parité ne se rétablit pas. **MESURÉ (interne)** pour les prix, **CONCEPTION** pour la position et le prix d'exécution hypothétique.
7. **Conséquence de méthode : l'agent est un put, pas une alpha directionnelle.** On ne peut pas l'évaluer sur un seul chemin réalisé (USDC a guéri). Il faut une **fonction d'objectif par fenêtre (regret)** *et* une **évaluation en espérance sur un jeu de scénarios pondérés**, publiées séparément et jamais fusionnées en un score unique. **CONCEPTION**.
8. **Protocole prêt à geler** (§C) : comparateurs **A0** (rien faire), **A1** (règle de seuil), **A2** (agent), **B0** (placebo apparié : même nombre d'actions, horodatages tirés au hasard, graine fixée, M ≥ 200), plus **O** (oracle ex post dans la même famille d'actions), **séparation développement/évaluation**, **embargo**, **journal des variantes** (obligatoire pour le Deflated Sharpe Ratio), **seuils de succès par persona**, et un calendrier de gel avec empreintes SHA-256.
9. **Anti-optimisme** : placebo B0 ; fenêtres témoins obligatoires ; regrets positif et négatif publiés séparément (jamais moyennés) ; intervalles de Wilson sur les proportions ; bootstrap par blocs sur les séries ; DSR/multiplicité ; mention « non conclusionnel » quand la puissance manque (≈ 93 fenêtres par groupe pour un effet modéré, cf. `R3` §B.5) ; aveu explicite que USDC mars 2023 est dans les données d'entraînement des modèles de 2026.
10. **Ce qu'un prototype peut mesurer vs ce qui exige du forward** : mesurables aujourd'hui — richesse/regret rejoués, coût d'exécution par échelle (`get_dy`), déterminisme (hash), provenance, calibrage, couverture conformal, attaques de politique. Non mesurables sans paper trading — impact de **nos** ordres sur le marché, latence réelle, coût de capital et de financement, comportement du marché face à un acteur répété. **NON TROUVÉ** : aucune cible chiffrée publiée (Sharpe cible, budget de drawdown, tolérance de slippage) par un desk crypto nommé (Wintermute, GSR, Keyrock, Amber) — voir §NON TROUVÉ.

---

## (a) Objectifs réels par persona, sourcés

### A.1 — Persona 1 : trésorerie de DAO / protocole — « prévision du risque et anticipation »

#### A.1.1 — Le document de politique : ce que la DAO s'impose (le cas ENS 6.46)

**FAIT SOURCÉ** — ENS DAO, *[6.46] [Social] 2026 Endowment Investment Policy Update*, forum `discuss.ens.domains/t/.../22106`, posté par KPK le **8 mai 2026**, passé au vote social, thread fermé le **11 août 2026** ; version ratifiée épinglée sur IPFS. L'IPS définit « les objectifs d'investissement, les paramètres de risque, les contraintes et les mécanismes de gouvernance » dans lesquels le gestionnaire opère. Éléments directement exploitables par ORVYREN :

| Élément de l'IPS | Valeur (telle que citée dans le document) | Traduction pour un agent |
|---|---|---|
| Objectif **primaire** | « long-term capital preservation and real return generation sufficient to support ENS's operating expenses **without eroding principal** » | ce n'est pas un objectif de rendement maximal ; c'est **survivre + servir les charges** |
| Objectif secondaire | croître la dotation jusqu'à ce que le DAO vive de ses revenus | horizon lointain, sans effet sur la décision à court terme |
| Horizon | moyen terme 0–5 ans (croissance + déploiement), long terme 5+ ans (préservation dominante, appétit de risque **décroissant**) | définir si l'agent raisonne à l'échelle de l'épisode ou du mandat |
| **Définition du risque** | (1) « la probabilité de ne pas satisfaire les exigences de liquidité ou les obligations de trésorerie » ; (2) « la probabilité de perdre le principal » | le risque est une **probabilité d'événement**, pas une volatilité |
| **Contrainte de liquidité** | Runway minimum **≈ 49,34 M$ = 3 ans de charges** ; « Runway priority: **Unconditional. Supersedes the 60/40 target in all circumstances** » ; revue annuelle | **contrainte dure, prioritaire sur toute allocation** |
| Charges de référence | **16,4 M$ de charges d'exploitation 2025** (rapport Steakhouse) | fournit l'unité « jour de runway » (≈ 44 932 $/j) |
| Seconde couche de liquidité | buffer opérationnel en USDC de **6 mois** dans le timelock, réalimenté par KPK chaque trimestre | deux niveaux de runway à ne pas confondre |
| Benchmarks | **60/40 ETH-USD** sur les taux de référence on-chain : composante ETH = APY moyen pondéré par TVL des **5 plus grands** vaults/pools de staking ; composante USD = APY moyen pondéré par TVL des **5 plus grands** vaults/pools de prêt stablecoin ; moyenne glissante 30 j, recalculée le 1er jour ouvré du mois | le « score » de la DAO est un **écart à un benchmark de taux**, pas un P&L |
| Tolérance de risque | « moderate-to-low » ; **faible risque ≥ 90 %** (track record > 12 mois, contrats audités, **redeemable within 7 days**) ; **risque modéré ≤ 10 %** (réversible ≤ 30 jours), chaque position divulguée mensuellement | contraintes de **redeemability**, directement liées à la vitesse de sortie en crise |
| Interdits | pas de trading spéculatif (hors rebalancement ETH/stablecoins), pas de venues à haut risque | borne ce qu'un agent a le droit de faire |
| Suivi **par type de risque** | marché → **mark-to-market quotidien + rapport de drawdown mensuel** ; smart contract → **alertes temps réel Hypernative** + protocole de war-room ; liquidité → **contrôle hebdomadaire du runway** contre le plancher 3 ans ; gouvernance → veto du Security Council ; opérationnel → **Zodiac Roles Modifier v2**, permissions scénarisées, multi-sig | **c'est la cadence réelle d'anticipation attendue par une DAO** : hebdomadaire pour le runway, temps réel pour les alertes |
| Concentration | **≤ 30 % par protocole** ; rapport de concentration mensuel ; RWA ≤ 5 % (instruments MMF/obligations tokenisées uniquement) ; EURC ≤ 5 % du stablecoin ; LSD : pas plus de 20 % du consensus (25 % avec DVT majoritaire) ; pas d'ETH via CEX ; **mainnet Ethereum seulement** | grille de contraintes pour l'enveloppe de l'agent |
| Déclencheurs de revue | « **material underperformance relative to benchmark for two consecutive quarters** » ; changement de situation financière ; changement de gestionnaire | le seuil de « ça va mal » côté DAO est **long** (2 trimestres) |
| Reddition de comptes | reporting **mensuel** sur le forum + réunions MetaGov ; **dashboard public temps réel** (allocation, respect des contraintes, performance vs benchmark) ; disclosure des changements matériels | un agent doit produire des **artefacts auditables**, pas des scores |

#### A.1.2 — Ce que l'opérateur met en avant dans ses rapports (ce qu'une DAO regarde vraiment)

**FAIT SOURCÉ** — KPK, *Monthly Treasury Report: June 2026* (`kpk.io/blog/monthly-treasury-report-june-2026`, publié le **27 juillet 2026**). Structure et vocabulaire du rapport, sur 5 mandats (≈ 135,6 M$ gérés, 282 936 $ de résultats DeFi sur le mois) :

- **séparation stricte entre « strategy yield » et « mark-to-market »** : ENS « a gagné 175 236 $ de rendement de stratégie **pendant que sa dotation suivait l'ETH à la baisse** » ; CoW : rendement +62 686 $ contre mark-to-market ≈ −1,7 M$ ; Balancer : +25 121 $ contre −342 k$ ; Nexus Mutual : +15 087 $ contre −843 k$. **La DAO lit deux chiffres séparés, jamais un « P&L » net agrégé.**
- **capital utilisation** affichée comme un KPI de premier plan : ENS « full capital utilisation » (≈ 99 %), dYdX 79,73 %, Balancer ≈ 95 %, Nexus Mutual ≈ 97 %.
- **déploiement** (liquid balances vs positions DeFi) : CoW ≈ 77 % déployé.
- **concentration par protocole**, systématiquement donnée (ENS : 7 protocoles, aucun au-dessus de 30 % ; plus gros postes StakeWise 24,1 %, Stader 23,3 %, Aave 16,2 %, EtherFi 13,3 %).
- **preuve de conservation du principal** : « over $8bn deployed onchain, more than 16 000 transactions and **zero funds lost** ».
- **rembobinage de l'agenda** : chaque mois, un post dans le forum de chaque DAO.

**Lecture ORVYREN** : la trésorerie de DAO ne se mesure pas en P&L mais en **(i) revenu de stratégie, (ii) préservation/trajectoire du principal, (iii) liquidité disponible (utilisation, déploiement, redeemability), (iv) concentration, (v) traçabilité**. Un agent qui « gagne 200 bp » mais dégrade (iii) ou (v) est un mauvais agent pour ce persona. **CONCEPTION** (interprétation).

#### A.1.3 — Ce que les appels d'offres de DAO exigent d'un gestionnaire

**FAIT SOURCÉ** — Compound DAO, *RFP: Compound DAO Treasury Management Program* (`comp.xyz/t/.../7867`, page consultée le 15/10/2026 ; **date de publication non affichée dans l'extrait disponible**) : le format de soumission impose « **Risk framework and at least one stress scenario** » ; une section « **Mandate Constraints** » exige de décrire « the liquidity profile of their proposed strategy — including any lockup periods, withdrawal notice requirements, unstaking periods, or redemption windows that could constrain the DAO's ability to move capital quickly » ; les critères d'évaluation sont pondérés (structure de frais 10 %…). **Le gestionnaire de risque (Gauntlet) évalue le risque des stratégies de rendement** en amont de la sélection.

**Lecture ORVYREN** : « scenario de stress » et « profil de liquidité » sont des **livrables contractuels**, pas des options. Notre fonction d'objectif doit produire exactement ces deux objets. **CONCEPTION**.

#### A.1.4 — Ce que les guides de trésorerie stablecoin normalisent

**FAIT SOURCÉ** — Eco, *Stablecoin Treasury Management: 2026 Best Practices* (`eco.com/support/en/articles/14799675-…`, page mise à jour il y a plus d'un mois au 15/10/2026) : les composants d'une politique = **allocation policy, asset whitelist, chain whitelist, custody model, yield strategy, reporting cadence** + flux opérationnels (receive/sweep, pay out, allocate to yield) ; plages de rendement annoncées **4,1 %–11,8 % APY** sur 3–7 chaînes ; catégories de risque explicitées.
**FAIT SOURCÉ** — Eco, *Stablecoin Depeg: What Causes It and How to Spot Risk* (`…/15182160-…`) : six causes de dépeg (perte de réserve, ruée bancaire, échec algorithmique, arrêt réglementaire, trous de liquidité DEX, gels spécifiques à une plateforme) ; défenses pratiques : **diversifier sur ≥ 2 émetteurs aux structures de réserve différentes** (« l'épisode USDC-SVB de 2023 a frappé USDC **et** DAI ensemble ; USDT et PYUSD n'ont pas bougé »), et **surveiller quotidiennement la composition de la Curve 3pool** (si la part d'un stablecoin dépasse ~70 %, décote attendue).
**FAIT SOURCÉ** — Bank Policy Institute, *Stablecoin Risks: Some Warning Bells* (`bpi.com/stablecoin-risks-some-warning-bells/`) : le run sur USDC « a commencé le 9 mars », USDC est descendu jusqu'à **0,87 $**, des échanges majeurs (Binance, Coinbase) **ont suspendu les conversions USDC→USD**, et le run ne s'est arrêté qu'après l'annonce FDIC/Trésor/Fed protégeant tous les déposants de SVB ; second exemple : **USDe à 0,65 $ le 10 octobre 2025**.
**FAIT SOURCÉ** — Federal Reserve, *FEDS Notes*, « In the Shadow of Bank Runs… » (**17 décembre 2025**, Du, Sonawane, Watsky) : SVB a subi **plus de 40 Md$ de retraits en une seule journée (vendredi 10 mars)** ; **à 22 h le vendredi**, Circle annonce ne pas pouvoir retirer **3,3 Md$** (≈ 8 % de ses réserves) ; les **Peg Stability Modules du DAI se sont vidés « rapidement »** pendant le week-end et **DAI a lui aussi perdu sa parité** ; la résolution annoncée par FDIC/Trésor/Fed a éteint la pression **avant la réouverture du marché primaire de Circle**.
**Lecture ORVYREN** : la chaîne causale d'un risque de trésorerie est **« annonce → fermeture du marché primaire → drainage des PSM/pools → contagion aux voisins non exposés → guérison par intervention »**. Un agent de persona DAO doit donc anticiper **avant** la fermeture primaire (l'annonce) et savoir que **le week-end ne pardonne pas** (les marchés secondaires price le risque sans filet de redemption). **CONCEPTION**.

#### A.1.5 — Le regard critique indépendant (à citer pour ne pas paraître naïf)

**FAIT SOURCÉ** — ENS DAO forum, *ENS Endowment: Independent Risk Teardown* (utilisateur `riskypete`, équipe Sentralis, **14 juillet 2026**, analyse non commanditée, 7 sections dont « **3. Exit liquidity in two regimes** » et « **7. What the proposed options mandate would add** »). Le teardown modélise la liquidité de sortie dans deux régimes, indique explicitement que « **les files d'attente de redemption sont le point qui compte quand tout le monde tire en même temps** », et chiffre le coût d'un mandat d'options à **≈ 70 k$/an par million** — ce qui est exactement le prix d'une assurance avec lequel la DAO doit arbitrer.

**Lecture ORVYREN** : la valeur d'un agent d'anticipation pour une DAO est **une prime d'assurance** : un coût certain (frictions, coût d'opportunité, bruit politique) contre une perte rare et bornée. Toute revendication de « gain » qui ne mentionne pas la prime payée sera attaquée. **CONCEPTION**.

#### A.1.6 — Synthèse persona 1 : les cinq dimensions objectivables

**CONCEPTION** (construite sur A.1.1–A.1.5) :

| # | Dimension | Mesure proposée | Seuil/espoir côté DAO |
|---|---|---|---|
| D1 | **Probabilité de manquer l'obligation** | `P(runway < 3 ans)` estimée par scénario ; ou, par épisode, la perte en **jours de runway** | cible : ≥ 0 en toutes circonstances ; toute perte > 0 doit être justifiée |
| D2 | **Préservation du principal** | écart au benchmark 60/40 de taux de référence, et valeur réalisable (pas oracle) | ≥ 0 sur le mandat ; « underperformance 2 trimestres » = déclencheur de revue |
| D3 | **Drawdown** | max drawdown sur la valeur **réalisable** + rapport mensuel (exigé par l'IPS) | doit être rapporté mensuellement ; pas de budget chiffré publié → **NON TROUVÉ** |
| D4 | **Liquidité de sortie** | `Depth_ε(x)` : taille maximale sortable à ≤ ε d'impact ; délai de sortie (jours) | ≥ 90 % du portefeuille **redeemable sous 7 jours** (IPS) |
| D5 | **Reddition de comptes** | latence d'alerte, journal des décisions, preuve, cadence | temps réel pour les alertes, mensuel pour les rapports |

Et « **anticipation** », opérationnalisée : **antériorité** (heures entre la première alerte et le point bas du prix réalisable mesuré) **× taux d'alerte fausse** (coût des frictions sur fenêtres calmes) **× délai de réaction** (temps entre alerte et action effectivement exécutée). **CONCEPTION**.

---

### A.2 — Persona 2 : desk de trading crypto — « rentabilité »

#### A.2.1 — Ce qu'un desk met en avant de lui-même

**FAIT SOURCÉ** — Keyrock, *What is Crypto market making? A guide* (`keyrock.com/knowledge-hub/guide-crypto-market-making/`, page consultée le 15/10/2026, **aucune date de publication affichée**) : la valeur d'un MM est son **capital** (« The amount of capital that is available to a market maker goes hand in hand with how much potential market depth they're able to… ») ; ses engagements sont **stabilité, « mitigating arbitrage », spread resserré**, et surtout **« we commit to maintaining delta-neutral strategies »** (« Nous maintenons des stratégies delta-neutres… nous préférons prendre des risques calculés en équilibrant l'exposition aux mouvements de prix plutôt que de courir après des incitations de prix »). Le spread resserré est présenté comme l'indicateur de qualité de service.
**FAIT SOURCÉ** — DWF Labs, *How to Choose a Crypto Market Maker: 10 Key Criteria* (publié le **13 septembre 2024**, mis à jour le **5 septembre 2025**) : 10 critères dont (1) **profondeur de liquidité et force de capital** — « le capital disponible limite directement la profondeur qu'un MM peut fournir » ; (2) **uptime et fiabilité** — « éviter tout prestataire qui s'engage à moins de **95 % d'uptime** » (renvoi à Outlier Ventures) et « la liquidité ne vaut rien si l'infrastructure tombe pendant un stress de marché » ; (5) **transparence** — « reporting clair et piloté par les données, **métriques hebdomadaires** partagées avec le client » ; (9) **SLA 24/7 et dashboards temps réel**.

#### A.2.2 — Les métriques et formules que la profession utilise

**FAIT SOURCÉ** — Thèse *Backtesting Market Making Strategies in Crypto Landscapes* (diva-portal, `his.diva-portal.org/smash/get/diva2:1972292/FULLTEXT01.pdf`) : évaluation d'un MM sur **Sharpe ratio en priorité**, puis variance de la valeur du portefeuille, avec `S = (R_p − R_f)/σ_p` et **`R_f` fixé à 0** par convention (« en l'absence de taux sans risque consensuel en crypto ») ; métriques secondaires : valeur terminale, P&L, nombre de trades, inventaire moyen (§3.3 et §1.1).
**FAIT SOURCÉ** — IBKR Quant Campus, *Equity Market-Neutral Trading…* (page consultée le 15/10/2026, portion datée 2026-03 dans les assets) : définitions opérationnelles — `Drawdown_t = Equity_t / max_{u≤t}(Equity_u) − 1`, `MaxDD = min(Drawdown_t)` ; **« Max drawdown captures path risk… particulièrement important pour les stratégies à effet de levier ou contraintes en capacité, parce qu'un drawdown suffisamment profond peut déclencher une déleveraging forcé »** ; Sortino annualisé, information ratio calculé sur les rendements actifs (`IR = 0,98` dans leur exemple).
**FAIT SOURCÉ** — *Investment portfolio optimization with supervised learning…* (ScienceDirect, `S1110866525002324`) : formules `SoR = (R_p − R_f)/σ_d` (σ_d = écart-type des seuls rendements négatifs), `MDD = max_t(…)`, `IR = (R_p − R_b)/TE` ; comparaison de MDD 9,4 % (modèle) contre « 20–30 % des méthodes traditionnelles en période de stress ».
**FAIT SOURCÉ (snippet, non ouvert)** — JKP Factors, *Problem Set 3* : « le portefeuille tourne 1,8 fois son capital par mois, donc les coûts comptent : **à 10 bp par dollar échangé**, le ratio de Sharpe est de 1,86 » — illustration du fait que **le coût de transaction décide du signe** d'un Sharpe.
**FAIT SOURCÉ (snippet)** — NeH Capital, *Electronic Market Making: Spread Capture and Inventory Risk* (**2 octobre 2026**) : diagnostics qu'un desk quantitatif doit mesurer — « **realised spread, inventory duration, markout after fills, losses during volatility** ».
**FAIT SOURCÉ (snippet)** — XR Academy, *Economics of Market Making* : décomposition complète du P&L d'un MM —
`Net P&L = V·S (spread) + V·R (rebates) − V·AS (sélection adverse) − V·EC (coûts d'exécution) − I·HC·T (coût de portage de l'inventaire) − OC (coûts opérationnels) − K·CC (coût du capital)`.

#### A.2.3 — Le piège de mesure propre aux desks : la multiplicité

**FAIT SOURCÉ** — Bailey & López de Prado, *The Deflated Sharpe Ratio* (Journal of Portfolio Management 40(5), p. 94-107, 2014 ; PDF `davidhbailey.com/dhbpapers/deflated-sharpe.pdf`) : le DSR corrige **le biais de sélection sous tests multiples et la non-normalité** ; conséquence énoncée dans *The False Strategy Theorem* (American Mathematical Monthly, 2021, même binôme) : « **il n'existe aucun seuil de ratio de Sharpe au-delà duquel on peut rejeter l'hypothèse qu'une stratégie est fausse** — avec assez d'essais, une stratégie fausse peut atteindre n'importe quel Sharpe demandé ». La correction pratique exige de **consigner tous les essais** et de regrouper les essais effectivement indépendants.

#### A.2.4 — Ce que nous n'avons pas trouvé (et qu'il ne faut pas inventer)

**NON TROUVÉ (15/10/2026)** : aucune **interview publique** de Wintermute, GSR, Keyrock ou Amber Group exposant des **cibles chiffrées** (Sharpe visé, budget de drawdown, tolérance de slippage en bp, coût du capital interne, ratio capacité/ADV). Les sources trouvées sont soit des pages de recrutement, soit des guides commerciaux, soit des définitions académiques génériques. Ce qui suit (A.2.5) est donc une reconstruction **par métriques de la profession**, pas une citation d'objectif interne.

#### A.2.5 — Synthèse persona 2 : les cinq dimensions objectivables

**CONCEPTION** :

| # | Dimension | Mesure | Remarque |
|---|---|---|---|
| T1 | **P&L net** | `ΔP&L = Σ (flux nets d'inventaire valorisés au prix réalisable) − frais − gas − financement` | la seule mesure que le desk « encaisse » |
| T2 | **Performance ajustée du risque** | Sharpe/Sortino de la **série de décisions** (pas d'un seul épisode) ; DSR si plusieurs variantes testées | N trop petit → publier l'intervalle, pas le point |
| T3 | **Drawdown** | `MaxDD = min_t(Equity_t/max_{u≤t} Equity_u − 1)` sur le capital alloué, **plus** le seuil de déleveraging forcé | contrainte de survie, pas confort |
| T4 | **Capacité et coût d'exécution** | `Slip(x)` réalisé vs budget (bp), `Depth_ε`, part de l'ADV | borne la taille de l'action : une « perte évitée » plus petite que le coût d'exécution n'existe pas |
| T5 | **Disponibilité et SLA** | uptime (≥ 95 % cité comme plancher), latence de réaction, 24/7 | une alerte non exécutée en stress ne vaut rien |

### A.3 — Les deux personas en une table (à recopier dans la doc technique)

| Axe | **DAO / protocole** | **Desk de trading** |
|---|---|---|
| Ce qui est maximisé | préservation + service des charges, écart au benchmark de taux | P&L net ajusté du risque |
| Ce qui est une faute grave | **manquer une obligation** (runway), perdre le principal | drawdown au-delà du budget, coût d'exécution hors budget, arrêt de service |
| Unité naturelle | **jour de runway**, % du principal, délai de sortie (jours) | **bp** de P&L net, Sharpe/Sortino, bp de slippage |
| Horizon de jugement | mensuel/trimestriel (revue annuelle de l'IPS) | par épisode et par mois, avec série longue |
| Tolérance au faux positif | faible à modérée (coût = frais + justification politique) | dépend du coût d'aller-retour / du signal de flux |
| Tolérance au faux négatif | **très faible** (une obligation manquée peut être terminale pour le mandat) | dépend de la position (un put qui ne sert jamais est un put payé) |
| Vitesse d'alerte attendue | temps réel (« Hypernative alert ») ; contrôle de runway **hebdomadaire** | temps réel/par tick, SLA 24/7 |
| Preuve attendue | rapport mensuel, dashboard public, journal des décisions | séries de P&L, markout, attribution de performance |

---

## (b) Fonctions d'objectif candidates : formules complètes et pièges

### B.0 — Notations et convention de valorisation (à geler)

Indices : `t0` = origine de la fenêtre `w` (instant de décision), `T` = fin de la fenêtre d'évaluation, `t_action` = instant d'exécution de l'action.

- `C` : encaisse/numéraire (stablecoin traité comme tel) ;
- `q` : quantité de l'actif risqué exposé (unités), `q ≥ 0` ;
- `P_t` : **prix réalisable** (pas le prix affiché, pas le prix oracle) — médiane pondérée par le volume des venues retenues, ou `get_dy` pour la taille exacte ;
- `x ∈ [0, q]` : quantité cédée (variable de décision), éventuellement bornée par l'enveloppe (`x ≤ x_max`) ;
- `P_exec(x, t_action)` : prix d'exécution **moyen** obtenu pour la taille `x` (issu de l'échelle de profondeur mesurée) ;
- `k` : coûts explicites (frais, gas, pontage, financement) **non déjà inclus** dans `P_exec` ;
- `W_t = C_t + q·P_t` : **richesse réalisable** à `t` ;
- `F` : ensemble des **actions faisables** (y compris `x = 0`, et bornées par les contraintes de politique) ;
- `A` : le système évalué (`A0`, `A1`, `A2`, `B0` — §C.1).

**Convention de valorisation** (à écrire noir sur blanc dans le gel) : deux conventions sont acceptables, **jamais mélangées** :
1. **convention terminale** : tout est valorisé au prix réalisable en `T` (`P_T`) — mesure la richesse effectivement conservée ;
2. **convention de liquidation** : la position restante est valorisée au prix qu'on obtiendrait en la liquidant à `T` (échelle de profondeur) — plus prudente, plus coûteuse à produire.
**CONCEPTION**. Toute fonction de perte qui valorise une branche au **minimum de la fenêtre** et l'autre à l'instant d'action mélange les deux conventions : c'est l'origine du bug §B.2.

### B.1 — Le noyau correct : richesse + actions faisables

**CONCEPTION** — formulation à geler (les trois lignes se lisent ensemble) :

```
W_T(conserver)   = C + q · P_T
W_T(céder x)     = C + x · P_exec(x, t_action) − k + (q − x) · P_T
L(a)             = W_t0 − W_T(a)                      [en USD, ou en bp de W_t0]
R_w(a)           = L(a) − min_{b ∈ F} L(b)            [regret ≥ 0]
```

Propriétés utiles (vérifiées, cf. tests §B.6) :

- **Invariance par translation** : ajouter une constante à toutes les `W_T` ne change aucun `R_w`.
- **Neutralité** : si `P_exec = P_T` et `k = 0`, alors `L(conserver) = L(céder x)` pour tout `x` → `R_w = 0` partout. C'est le **test de non-double-comptage** : aucune action ne peut « gagner » sans un écart de prix ou un coût réel.
- **Monotonie en coût** : `k ↑ ⇒ L(céder) ↑` et `R_w(céder) ↑`.
- **Cohérence d'échelle** : `R_w` est proportionnel à `W_t0` ; on publie donc `R_w` **en bp de `W_t0`** pour comparer des positions de tailles différentes.
- **Oracle de la même famille** : `min_{b ∈ F} L(b)` est calculé sur les actions **faisables** évaluées avec la même fonction de perte gelée — ce n'est pas un oracle omniscient sur les prix futurs (`R3` §B.1).
- **Deux regrets, jamais un seul** : `R⁻` = coût du **faux positif** (l'agent agit et ne rien faire était meilleur) ; `R⁺` = coût du **faux négatif** (l'agent n'agit pas et agir était meilleur). On publie la distribution par branche et la table de contingence, jamais la moyenne des deux (elle s'annule et masque tout).

### B.2 — Le piège du double comptage : démonstration chiffrée et identité exacte

**Le bug (formule antérieure, `R3` §B.1 M1)** :

```
L(NO-ACTION) = E · max(0, 1 − min_{t∈w} P_t) + 0
L(RÉDUIRE)   = c + E · max(0, 1 − P_{t_action}) − E · max(0, 1 − min_{t∈w} P_t)
```

Trois défauts s'empilent : (i) NO-ACTION est chargée de **la décote subie**, (ii) RÉDUIRE reçoit cette même décote **en crédit** (« drawdown évité »), (iii) la perte subie **avant** l'action (`1 − P_{t_action}`) est chargée à RÉDUIRE comme si elle avait été causée par l'action — alors qu'elle est **sunk** et présente dans les deux branches.

**Exemple minimal reproductible** (calculé, `calculs_w2d.json`) : `E = q = 100` unités, exposition intégralement risquée (`C = 0`), sortie exécutée à `P_exec = 1,00` sans coût (`k = 0`), prix terminal et plus bas de la fenêtre confondus à `P_T = 0,90`.

| Grandeur | Formule antérieure (buguée) | Formulation richesse (corrigée) |
|---|---|---|
| L(NO-ACTION) | 100 × (1 − 0,90) = **10,00** | 100,00 − (0 + 100 × 0,90) = **10,00** |
| L(RÉDUIRE) | 0 + 100 × (1 − 1,00) − 100 × (1 − 0,90) = **−10,00** | 100,00 − (0 + 100 × 1,00 − 0) = **0,00** |
| Écart affiché entre agir et ne rien faire | **20,00** | **10,00** |

**La richesse réellement en jeu est 10 ; la formule antérieure affichait 20.** **MESURÉ (interne)**.

**Identité générale (à recopier telle quelle)** — avec la convention terminale et `min_{t∈w} P_t = P_T` (le cas le plus favorable au bug) :

```
écart_bugué − écart_vrai = q · (1 − P_T)
```

Autrement dit : **la décote subie est comptée exactement une fois de trop**, parce que le même terme `q·(1 − P_T)` est à la fois débité de NO-ACTION et crédité à RÉDUIRE. Numériquement : `20 − 10 = 10 = 100 × (1 − 0,90)`. **MESURÉ (interne)**.
Second défaut mesurable : la formule buguée utilise le **minimum de la fenêtre** (`min_t P_t`) au lieu du prix terminal, ce qui autorise une action à « gagner » sans que la richesse terminale ait bougé, et rend le résultat sensible à la granularité d'échantillonnage (un tick plus bas suffit à changer le signe).

**Règle ORVYREN** : *une fonction de perte ne contient jamais deux fois la même perte.* Toute relecture doit passer les six tests de §B.6 ; le test de neutralité (`P_exec = P_T`, `k = 0` → tous les regrets nuls) détecte ce bug en une ligne de code.

### B.3 — Objectif persona DAO

**CONCEPTION** — la DAO n'a pas un objectif scalaire mais un **objectif contraint**. On propose de geler :

```
maximiser   E[ RealReturn_T − Benchmark_T ]        sur le mandat   (B.3.1)
sous        P( Runway_t < Runway_min ) ≤ ε          pour tout t     (B.3.2)
            MaxDD(valeur réalisable) ≤ D_max                        (B.3.3)
            Redeemable(7 j) ≥ 90 % du portefeuille                   (B.3.4)
            w_protocole ≤ 30 % ;  w_modéré ≤ 10 % ;  w_RWA ≤ 5 %     (B.3.5)
```

Avec, au niveau de la **décision dans un épisode** — c'est-à-dire au niveau où l'agent est évalué dans ce dossier — la même mesure de richesse que §B.1, mais **lue en unités de DAO** :

```
Perte évitée (DAO)      = L(A0) − L(A)                      [USD]
Perte évitée en runway  = ( L(A0) − L(A) ) / (opex annuel/365)      [jours de runway]
Coût de l'action        = L(A) − L(min_faisable)  ≥ 0        [USD, = regret]
Ratio de justification  = Perte évitée / Coût total des actions non déclenchées en période calme
```

et une mesure d'**anticipation** propre à ce persona :

```
Antériorité(w)   = t0_alerte − t_min(P_t)        [heures, si l'alerte précède le point bas]
Délai_réaction   = t_action − t0_alerte          [minutes]
Taux de fausses alertes = #{alertes sur fenêtres CALME} / #{fenêtres CALME}
```

Le point important, et contre-intuitif : **la DAO n'a pas à gagner de l'argent avec cet agent ; elle doit acheter une réduction de la probabilité d'un événement qui met le mandat en danger.** La bonne lecture d'une action de type « sortir de USDC » est donc **« une prime d'assurance »**, pas un trade. La perte évitée ne se réalise que **conditionnellement à une obligation** (payer des charges, honorer un appel de marge, respecter une redemption) ; sinon la sortie est un coût pur, et le gain n'est que la disparition d'un risque — exactement ce que la DAO valorise, mais que la comptabilité du P&L ne voit pas. D'où la règle de reporting :

> **Une perte évitée « inconditionnelle » n'est pas une perte évitée.** Elle doit être publiée comme `E[perte évitée] = P(obligation dans la fenêtre) × (perte évitée | obligation)`, avec les deux facteurs visibles et l'hypothèse sur `P(obligation)` figée avant l'exécution.

### B.4 — Objectif persona desk

**CONCEPTION** — le desk maximise un P&L net ; l'agent ORVYREN y intervient comme **composant d'une politique d'inventaire**. En reprenant la décomposition praticienne (§A.2.2) et en gardant la compatibilité avec §B.1 :

```
ΔP&L_net(a) = [ x·P_exec(x,t) + (q−x)·P_T − q·P_ref ]                        (terme de valorisation)
              − frais − gas                                            (k)
              − financement / coût de portage : I_moy · r_capital · Δt
              − (coûts opérationnels imputés)

P&L_net en bp = ΔP&L_net(a) / (q · P_ref) · 10 000
```

puis les agrégats **sur la série de décisions** (pas sur un épisode) :

```
Sharpe  = ( moyenne(rendements nets) − R_f ) / écart-type(rendements nets)     [R_f = 0 par convention crypto]
Sortino = ( moyenne − R_f ) / σ_d ,  σ_d = écart-type des seuls rendements négatifs
MaxDD   = min_t ( Equity_t / max_{u≤t} Equity_u − 1 )
```

**Trois différences structurelles avec la DAO, à écrire dans le dossier :**

1. **Le coût d'exécution conditionne l'existence de la décision.** Pour le desk, si `Perte évitée < (coût d'aller-retour)`, la décision correcte est de ne rien faire. Le seuil d'action à figer est donc `x·(P_T − P_exec) > k_aller-retour + financement`, et non un seuil sur la décote seule.
2. **La re-entrée fait partie de l'action.** Pour un desk, couper sans planifier le retour n'est pas une décision, c'est la moitié d'une décision ; l'aller-retour doit être évalué dans la même fenêtre (ou explicitement exclu, avec la mention « horizon court : pas de re-entrée modélisée »).
3. **L'agent est valorisé comme un put, donc en espérance sur un jeu de scénarios.** Un seul chemin réalisé (USDC guéri) ne peut pas trancher. On publie donc :
   - le **regret par fenêtre** (§B.1) — mesure honnête, indépendante du scénario réalisé ;
   - et une **évaluation en espérance** `E[ΔP&L] = Σ_s p_s · ΔP&L(s)` sur un jeu de scénarios **explicitement pondérés et datés** (scénario réalisé + scénarios contrefactuels étiquetés comme tels), avec les probabilités `p_s` gelées avant l'exécution. **NON TROUVÉ** : aucune source publique ne fournit une distribution de probabilité de scénarios de dépeg ; les `p_s` seront donc **nos hypothèses**, à déclarer comme telles.

### B.5 — Les autres pièges (au-delà du double comptage)

| # | Piège | Formulation du piège | Parade |
|---|---|---|---|
| 1 | **Compter deux fois une même perte** (§B.2) | « drawdown évité » crédité à l'action **et** débité à NO-ACTION | formulation richesse §B.1 + test de neutralité |
| 2 | **Charger une perte déjà subie (sunk)** | facturer à l'action la décote `1 − P_{t_action}` antérieure à l'exécution | `W_t0` est commun aux branches ; seule la richesse **terminale** diffère |
| 3 | **Valoriser au minimum de la fenêtre** | utiliser `min_t P_t` comme valeur de la position | convention de valorisation **figée** : `P_T` ou prix de liquidation à `T` |
| 4 | **Oublier le coût** | gain de 20 bp qui coûte 30 bp de frais/slippage/gas | `k` explicite + `P_exec` mesuré à la taille réelle (`R3` §(d) n°8) |
| 5 | **Comparer à un oracle omniscient** | « si on avait vendu au plus haut » | oracle **dans la famille d'actions faisables**, avec la même fonction de perte |
| 6 | **Compter les heures comme des preuves indépendantes** | 1 375 observations ≠ 1 375 tirages | unité d'analyse = **la fenêtre** (`R3` §B.0 règle 3) |
| 7 | **Ignorer le taux de base** | « 1 alerte sur 12 fenêtres » sans dire combien de fenêtres de crise existent | publier `ȳ` (climatologie) et la table de contingence |
| 8 | **Moyenner `R⁻` et `R⁺`** | un système nerveux et un système inerte s'annulent | publier séparément, par branche de décision |
| 9 | **Confondre dépeg temporaire et perte** | traiter un prix de 0,88 comme une perte alors que le détenteur n'a **rien vendu** | perte évitée **conditionnelle à l'obligation** (§B.3) |
| 10 | **Oublier la re-entrée** | « sorti à 0,95 » sans dire qu'on est resté en cash | horizon de la fenêtre explicite ; si pas de re-entrée, l'écrire |
| 11 | **Confondre trésorerie et desk** | appliquer un objectif de P&L à une DAO, ou un objectif de runway à un desk | **un seuil de succès par persona** (§C.4) |
| 12 | **Ne pas contrôler la multiplicité** | tester 40 variantes et publier la meilleure | journal des variantes + DSR (§C.3) |
| 13 | **Contamination de l'épisode** | USDC mars 2023 est dans les données d'entraînement de tout modèle de 2026 | « démonstration de méthode, pas prédiction » (`R3` §(d) n°1) |
| 14 | **Un prix d'agrégateur et un exchange comptés comme deux preuves** | médiane multi-venues et ses venues constitutives ne sont pas indépendantes | compter les **sources indépendantes réelles** (ici ≈ 2 : exchanges + émetteur) |
| 15 | **Publier un scalaire** | un score unique invite à l'optimiser | **vecteur** de métriques + axes non mesurés déclarés |

### B.6 — Les six tests à faire passer à toute fonction de perte candidate

**CONCEPTION** — script de test (`evaluation/loss_tests.py`), à exécuter avant le gel :

| # | Test | Formulation | Résultat attendu |
|---|---|---|---|
| T1 | **Neutralité / non-double-comptage** | `P_exec = P_T`, `k = 0` → `R(a) = 0` pour tout `a` | exactement 0 (détecte le bug §B.2) |
| T2 | **Invariance par translation** | `W_T += m` partout → `R` inchangé | égal à la tolérance machine près |
| T3 | **Monotonie en coût** | `k` croissant → `L(céder)` et `R(céder)` croissants | monotone |
| T4 | **Cohérence de signe** | si `P_exec > P_T`, agir doit avoir un regret nul et ne rien faire un regret positif | signes corrects |
| T5 | **Additivité de l'inventaire** | deux lots identiques → regret double ; un lot partiel `x` → regret interpolé linéairement | linéaire en `q` |
| T6 | **Référence dégénérée** | décote nulle sur toute la fenêtre (`P_t = 1`) → tous les regrets = 0 (et le coût d'une action inutile = `k`) | 0 + `k` |

---

## (c) Protocole de pré-enregistrement prêt à geler

Cette section étend le protocole de `R3_evaluation_benchmark.md` §B.0–B.7 (règles, comparateurs, design, ablations) avec ce qui manque pour **deux personas** : comparateur placebo, séparation développement/évaluation, embargo, journal des variantes, seuils de succès par persona, calendrier de gel.

### C.1 — Les comparateurs (identiques pour les deux personas, seuils différents)

| Code | Système | Rôle | Coût | Statut |
|---|---|---|---|---|
| **O** | Oracle ex post **dans la famille d'actions faisables** | borne inférieure du regret (pas une vérité terrain) | hors ligne | CONCEPTION |
| **A0** | **Rien faire** (NO-ACTION sur toute la fenêtre) | l'adversaire à battre le plus souvent | 0 | CONCEPTION |
| **A1** | **Règle de seuil** : décote `D ≥ 50 bp` pendant 15 min → action de réduction bornée | règle simple, « l'humain raisonnable » | ~0 | CONCEPTION (seuils repris de `W2B` §1.1, à figer) |
| **A2** | **Agent ORVYREN** (corpus → graphe → hypothèses → branche → critique → politique bornée) | le système revendiqué | budget plafonné et mesuré | CONCEPTION |
| **B0** | **Placebo apparié** : **même nombre total d'actions** que A2, aux **mêmes tailles**, déclenchées à des **horodatages tirés au hasard** dans la même fenêtre ; graine fixée ; **M ≥ 200 tirages** ; on publie la distribution des regrets | sépare « **savoir quand** » de « **bouger** » | ~0 | CONCEPTION (repris de `R3` §B.2) |
| **A−x** | Ablations de A2 (graphe, critique, hypothèses, multi-venues, plafond) | attribution des composants | budget identique | CONCEPTION (`R3` §B.4) |

**Règle** : si A2 ne bat pas **B0**, la valeur du système n'est pas dans le choix du moment — l'écrire. Si A2 ne bat pas **A1**, la valeur n'est pas dans la délibération — l'écrire aussi. Les deux phrases doivent être pré-écrites **avant** de lancer (c'est le pré-enregistrement).

### C.2 — Fenêtres, séparation développement / évaluation, embargo

**CONCEPTION** — s'appuie sur les épisodes de `W2A_donnees_episodes.md` §3 et les signaux mesurés de `W2B_signaux_detection.md` :

| Jeu | Épisodes | Usage | Pourquoi |
|---|---|---|---|
| **DÉVELOPPEMENT** | **USDC mars 2023** ; **stETH juin 2022** ; fenêtres CALME 2022–2023 (≥ 6) | régler seuils, calibrer, déboguer, mesurer les coûts | ce sont les épisodes déjà largement publiés (donc « brûlés » pour une revendication de nouveauté, mais parfaits pour régler) — `W2A` les classe « prix seulement », exploitables |
| **ÉVALUATION** | **rsETH / KelpDAO avril 2026** ; **USD0++ janvier 2025** ; fenêtres CALME 2025–2026 (≥ 6) | exécution **une fois**, sans retouche, après gel | `W2A` : mieux instrumentés, postérieurs à la plupart des dates de coupe de modèles ; `rsETH` = « l'épisode le mieux instrumenté » |
| **EXCLU** | **xUSD / Stream nov. 2025** | hors évaluation tant qu'il manque une série de prix | `W2A`/`W2B` : **aucune série de prix publique exploitable trouvée** → ne pas l'utiliser pour une mesure de perte évitée (l'utiliser seulement comme cas qualitatif d'« invisibilisation ») |

**Embargo** (au sens de la séparation temporelle stricte) :

1. **Embargo de paramètres** : aucune constante (seuils `D`, tailles `x`, horizon `H`, `P(obligation)`, coûts `k`) ne peut être modifiée après la première exécution sur le jeu d'évaluation. Toute modification **invalide** l'évaluation (pas « l'affaiblit ») et doit être écrite comme telle.
2. **Embargo de données** : la bande de 24 h précédant l'ouverture de chaque fenêtre d'évaluation est **retirée** du développement (elle sert uniquement à l'initialisation), pour éviter qu'un réglage s'appuie sur la veille d'une crise.
3. **Embargo d'inspection** : avant le gel, l'équipe s'engage à ne **pas** inspecter les fenêtres d'évaluation au-delà de ce que `W2A`/`W2B` ont déjà publié ; après ouverture, le jeu d'évaluation est **brûlé** — on ne peut plus le réutiliser comme argument de nouveauté.
4. **Horodatage** : le gel est un commit signé (hash SHA-256 du fichier de perte, du fichier de seuils et du fichier de fenêtres) ; il doit exister **avant** la première exécution sur le jeu d'évaluation.

### C.3 — Journal des variantes (obligatoire, et pourquoi)

**CONCEPTION, exigé par une source** : le DSR (§A.2.3) n'est calculable que si l'on connaît le **nombre d'essais**. On tient donc un fichier `variants.log` (une ligne par exécution) :

```
horodatage | commit | persona | jeu (dev/eval) | comparateur | seuils actifs | métrique principale | résultat | décision prise ensuite
```

Sans ce journal, toute performance publiée est **indéfendable** devant un jury informé (« il n'existe aucun seuil de Sharpe au-delà duquel on peut rejeter qu'une stratégie est fausse »). Le journal doit inclure **les échecs**, pas seulement les succès.

### C.4 — Seuils de succès par persona (à figer avant l'ouverture du jeu d'évaluation)

**Les deux personas ne partagent pas les mêmes critères.** Proposition **CONCEPTION** (chiffres à valider par l'équipe, cf. §f) :

#### C.4.1 — Persona DAO (trésorerie)

| Code | Critère | Formulation exacte | Seuil proposé |
|---|---|---|---|
| **SD1** | Perte évitée matérielle | `(L(A0) − L(A2)) / q` en % de l'exposition **conditionnellement à une obligation** dans la fenêtre | **≥ 5 %** de l'exposition exposée (sinon l'action n'est pas économiquement justifiable) |
| **SD2** | Friction maîtrisée | coût cumulé des actions A2 sur les **fenêtres CALME** | **≤ 10 %** de la perte évitée mesurée sur la fenêtre de crise (en USD) |
| **SD3** | Anticipation réelle | antériorité ≥ **6 h** avant le point bas du prix réalisable, sur **≥ 1** épisode d'évaluation ; délai de réaction ≤ **60 min** après alerte | oui/non, publié tel quel |
| **SD4** | Supériorité sur les comparateurs | `R̄(A2) < R̄(A1)` et `R̄(A2) < R̄(B0)` en agrégé sur les fenêtres d'évaluation | strictement inférieur, **avec intervalle** |
| **SD5** | Traçabilité | 100 % des actions avec provenance et hash ; 0 action hors enveloppe | 100 % / 0 |
| **SD6** | Honnêteté | mention « non conclusionnel » présente partout où la puissance manque ; perte évitée publiée comme `P × conditionnel` | présent / absent |

#### C.4.2 — Persona desk

| Code | Critère | Formulation exacte | Seuil proposé |
|---|---|---|---|
| **ST1** | P&L net positif | `ΔP&L_net` cumulé sur les fenêtres d'évaluation, **tous coûts inclus** (frais, slippage mesuré, financement) | **> 0**, publié avec intervalle bootstrap par blocs |
| **ST2** | Qualité d'exécution | slippage réalisé vs échelle de profondeur mesurée (`get_dy`), et taille ≤ `Depth_100bp` | **≤ 30 bp** sur une sortie de stablecoin en stress ; taille ≤ profondeur disponible |
| **ST3** | Risque borné | `MaxDD` de la série de décisions sur le capital alloué | **≤ 20 %** du capital alloué par épisode |
| **ST4** | Risque ajusté | Sharpe/Sortino de la série **et** DSR corrigé du nombre de variantes du journal | Sharpe > 0 avec borne inférieure d'IC > 0, sinon **« non conclusionnel »** |
| **ST5** | Supériorité sur les comparateurs | `ΔP&L(A2) > ΔP&L(A1)` et `> ΔP&L(B0)` | strictement supérieur, **avec intervalle** |
| **ST6** | Asymétrie déclarée | l'agent est décrit comme un **put** : coût certain, gain conditionnel ; jeu de scénarios pondérés publié | présent / absent |

#### C.4.3 — Anti-optimisme (commun, dispositifs obligatoires)

1. **Placebo B0** avec M ≥ 200 tirages, graine fixée, et publication de **la distribution complète** des regrets du placebo (pas seulement sa moyenne).
2. **Fenêtres CALME obligatoires** dans les deux jeux, appariées en durée et horaires (`R3` §B.3).
3. **Taux de base** publié partout (`ȳ`, nombre de fenêtres de crise vs calmes).
4. **Intervalles de Wilson** sur toutes les proportions ; « 0 échec sur 6 » doit être écrit avec sa borne supérieure (≈ 39 % à 95 %, `R3` §B.5).
5. **Bootstrap par blocs** (6–12 h, 10 000 réplications, graine fixée) sur toute statistique de série ; jamais d'IC i.i.d.
6. **DSR / journal des variantes** (§C.3).
7. **Regrets séparés** `R⁻` / `R⁺` + table de contingence complète (`R3` §B.5, McNemar).
8. **Mention de contamination** : les épisodes 2022–2023 sont dans les données d'entraînement ; le dossier démontre la **méthode**, pas une capacité prédictive.
9. **« Ce que nous ne revendiquons pas »** : recopier `R3` §B.7 tel quel, et y ajouter la version persona (« aucun gain de P&L démontré statistiquement », « aucune conformité réglementaire », « aucune garantie de performance future »).
10. **Un scalaire interdit** : score = vecteur + axes non mesurés.

### C.5 — Ce qui se gèle, et quand

**CONCEPTION** — calendrier proposé (J0 = date de gel ; proposition : **J0 = 2026-10-16**, veille du lot d'exécution), à ajuster d'un commun accord :

| Gel | Contenu | Empreinte | Quand |
|---|---|---|---|
| **G1 — fonction de perte** | `evaluation/loss.py` : formules §B.1, convention de valorisation, `F` (actions faisables), `k` ; **plus** les six tests §B.6 qui passent | SHA-256 du fichier + sortie des tests | **J0 (avant toute exécution)** |
| **G2 — comparateurs** | code de A0, A1, B0 (graine, M) ; code de l'oracle O | SHA-256 | J0 |
| **G3 — fenêtres et embargo** | liste des fenêtres DEV/EVAL, bornes temporelles, bande d'embargo 24 h | SHA-256 + horodatage | J0 |
| **G4 — seuils par persona** | tableaux §C.4.1 et §C.4.2, y compris les chiffres (5 %, 10 %, 6 h, 30 bp, 20 %) | SHA-256 | **avant la première exécution EVAL**, en tout cas ≤ J0+2 |
| **G5 — plan d'analyse** | métriques publiées, tests statistiques, formulations (« non conclusionnel »), tableaux de sortie | SHA-256 | avant la première exécution EVAL |
| **G6 — hypothèses économiques** | `P(obligation)` par fenêtre ; jeu de scénarios contrefactuels et probabilités `p_s` (persona desk) | SHA-256 | avant la première exécution EVAL |
| **G7 — journal** | `variants.log` ouvert, jamais réécrit (ajout uniquement) | — | continu |

### C.6 — Ce qui invalide l'évaluation

Une évaluation est **invalide** (et doit être réétiquetée) si : (1) une constante de G1–G6 change après la première exécution EVAL ; (2) une fenêtre d'évaluation est utilisée pour régler quoi que ce soit ; (3) le journal des variantes est incomplet ; (4) le comparateur A0/A1/B0 est modifié après la mesure de A2 ; (5) le placebo B0 n'a pas le même nombre d'actions que A2 ; (6) un résultat est présenté comme une supériorité statistique alors que l'intervalle contient zéro.

---

## (d) Mesurable-prototype vs forward (paper trading)

| Objet de mesure | Méthode | Statut au 15/10/2026 | Ce qu'on ne peut PAS dire |
|---|---|---|---|
| **Richesse / regret rejoués** (par fenêtre, par persona) | rejeu sur corpus archivé + fonction de perte gelée | **MESURABLE** (les prix et l'oracle sont déjà reconstruits dans `W2A`/`W2B`) | ce n'est pas une prédiction ; contamination des modèles |
| **Coût d'exécution par échelle** | `get_dy` Curve, QuoterV2 Uniswap, échelle 1 → 10 000 unités | **MESURÉ** pour les LST (`W2B` §1.5 : 1 000 stETH → 0,56 bp ; 10 000 stETH → 7,13 bp) ; **à faire** pour les stablecoins en stress | le coût mesuré aujourd'hui n'est pas le coût **pendant** la crise (la profondeur s'effondre : 3pool USDT 135 M → 10 M) |
| **Antériorité des signaux** | horodatage premier franchissement de seuil vs point bas du prix réalisable | **MESURÉ** (`W2B`) : 4 semaines (stETH), heures (USDC, dispersion), 0 (gel rsETH) | l'antériorité mesurée sur 2–3 épisodes n'est pas une espérance de gain |
| **Déterminisme / reproductibilité** | hash du dossier de décision sur k rejeux | **MESURABLE** immédiatement | le déterminisme n'est pas de la robustesse (`R3` §(d) n°4) |
| **Calibrage / couverture** | Brier, REL/RES/UNC, ECE, conformal split | **MESURABLE** mais non conclusionnel sous N ≈ 5–12 fenêtres | pas de garantie de couverture hors échangeabilité |
| **Impact de nos propres ordres** | — | **NON MESURABLE** sans exécution réelle | un backtest n'incorpore pas notre propre impact |
| **Latence et exécution réelles** | — | **NON MESURABLE** en rejeu | nos temps de réaction simulés ≠ temps réels |
| **Coût de capital / financement** | — | **NON MESURABLE** (hypothèses) | un P&L simulé sans financement est optimiste par construction |
| **Comportement d'un acteur répété** (herding, réaction des autres) | — | **NON MESURABLE** ; doit être déclaré (le régulateur l'a nommé, `R3` §(d) n°15) | pas de revendication « agent autonome » sans cette réserve |

**Le forward (paper trading) est la seule voie pour trois choses** : (1) l'exécution et la latence réelles ; (2) la surprise (des fenêtres que personne n'a choisies) ; (3) la crédibilité devant un jury industriel. Protocole de paper trading **CONCEPTION** :

1. **Fenêtre** : à partir du gel (G1–G6), 4 à 6 semaines, sans interruption (inclut obligatoirement des week-ends).
2. **Enregistrement avant observation** : chaque décision est écrite et **hachée** avant que l'issue ne soit connue ; le prix d'exécution réel (ou simulé à partir du carnet public) est enregistré à l'instant `t_action`.
3. **Métriques** : les mêmes (§B.1), plus le taux de déclenchement (`#{décisions ≠ NO-ACTION} / #fenêtres`), la latence, et le **coût de la politique** (nombre d'appels, temps, coût monétaire par décision utile).
4. **Règle d'honnêteté** : si **aucun** épisode de rupture ne survient dans la fenêtre (cas le plus probable), on publie : « 0 perte évitée observée — la démonstration porte sur la préparation, pas sur le gain ». Une affirmation de gain avec zéro événement est un mensonge statistique.
5. **Puissance** : avec 4–6 semaines de paper trading, le nombre d'événements exploitables est de l'ordre de 0–1 ; aucune supériorité ne peut être revendiquée, seulement une **faisabilité opérationnelle** (cadence, latence, journal, absence d'action hors enveloppe).

---

## (e) Exemple chiffré de bout en bout — USDC, mars 2023, lu deux fois

> Position illustrative (non sourcée) : **20 M$ d'exposition USDC** pour la DAO, **2 M$ d'inventaire USDC** pour le desk. Prix : valeurs **MESURÉES** (`W2A` §2.1, `W2B` §Famille 1) — voir E.1. Prix d'exécution hypothétique (`P_exec = 0,95`) : **hypothèse de travail**, clairement étiquetée, avec sensibilité.

### E.1 — Les faits mesurés (aucune invention)

| Instant (UTC) | Fait | Valeur | Source |
|---|---|---|---|
| 2023-03-10, journée | Retraits de **> 40 Md$** de SVB en une journée ; SVB en résolution | — | FAIT SOURCÉ (Fed FEDS 2025-12-17) |
| 2023-03-10 ~22:00 | Circle annonce ne pas pouvoir retirer **3,3 Md$** (≈ 8 % des réserves) ; marché primaire USDC fermé tout le week-end | — | FAIT SOURCÉ (Fed FEDS) |
| 2023-03-10 20:08 | Oracle Aave V3 USDC = **1,0002 $** ; 3pool : DAI 192,65 M / **USDC 197,79 M** / USDT 135,25 M | — | **MESURÉ** (`W2A`) |
| 2023-03-11 07:57 | Agrégat DeFiLlama USDC = **0,876675 $** | décote 1233 bp | **MESURÉ** (`W2B`) |
| 2023-03-11 12:59 | Oracle Aave V3 USDC = **0,9069 $** ; 3pool vidée de ses USDT : DAI 40,97 M / **USDC 333,64 M** / **USDT 10,06 M** | écart oracle/marché 296 bp | **MESURÉ** (`W2A`, `W2B`) |
| 2023-03-11 14:00 | **Binance USDC/USDT plus bas 1 min = 0,8820** ; OKX 14:01 = **0,9108** | — | **MESURÉ** (`W2A`, `W2B`) |
| 2023-03-11 07:00 | Bitstamp USDC = **0,80526** | décote **19,5 %** | **MESURÉ** (`W2B`) |
| 2023-03-11 (même épisode) | **Dispersion inter-venues mesurée : 767–870 bp** selon la paire de venues retenue | — | **MESURÉ** (`W2B`) |
| 2023-03-12 02:31 → 17:22 | Oracle Aave : 0,9754 → 0,9599 ; la 3pool se re-remplit (USDT 8,74 M) | — | **MESURÉ** (`W2A`) |
| 2023-03-13 08:51 | Oracle Aave : **0,9910** ; USDC est revenu à ≥ 0,99 $ | — | **MESURÉ** (`W2A`) + FAIT SOURCÉ (Eco : « recovered to $0.99+ within 48 hours ») |
| 2023-03-12 | FDIC/Trésor/Fed garantissent tous les déposants de SVB ; Circle confirme la levée du risque | — | FAIT SOURCÉ (Circle pressroom ; Fed FEDS) |

**Repères de la DAO** (ENS IPS 6.46, FAIT SOURCÉ) : charges 2025 = **16,4 M$/an** → **1 366 667 $/mois** → **44 932 $/jour** ; plancher de runway = **49 340 000 $**.

### E.2 — Lecture 1 : persona DAO (« perte évitée », en jours de runway)

**Hypothèse de travail** : une alerte déclenchée dans la nuit du 10 au 11 mars permet de pré-positionner une partie du stablecoin exposé à **`P_exec = 0,95`** (l'action est exécutée **avant** le creux ; 0,95 n'est **pas** une valeur mesurée, voir la sensibilité ci-dessous).

**(a) Si la DAO devait honorer des charges dans la fenêtre** (cas où la perte est *réelle*) :

| Scénario de conversion | Unités USDC nécessaires pour payer 1 366 667 $ | Coût en unités au-delà du pair | En jours de runway |
|---|---|---|---|
| Vendredi, avant stress (parité 1,00) | 1 366 667 | 0 | 0 |
| Vente au prix de stress mesuré **0,8820** (Binance, plus bas 1 min) | 1 549 509 | **+182 842** | **+4,07 j** |
| Vente au prix agrégé **0,876675** (DefiLlama, 07:57 UTC) | 1 558 921 | **+192 254** | **+4,28 j** |
| Vente au prix de stress mesuré **0,80526** (Bitstamp) | 1 697 174 | **+330 508** | **+7,36 j** |

**Perte évitée** par le pré-positionnement à 0,95 : **110 912 $ (2,47 j de runway)** si la conversion aurait eu lieu à 0,8820 ; **120 324 $ (2,68 j)** au prix agrégé 0,876675 ; **258 578 $ (5,75 j)** si elle aurait eu lieu sur la venue la plus décotée (0,80526). *Calculé* (`calculs_w2d.json`).

**(b) Si la DAO n'avait aucune obligation de vente dans la fenêtre** (cas le plus fréquent) : la position se valorise au plus bas (perte de mark-to-market), puis **revient à 0,9910 le 13 mars**. Le pré-positionnement à 0,95 et le **retour** à 0,99 coûte alors `20 M × (0,95 − 0,99)/1` = **−800 000 $ (−4,0 %)** avant frais. **La « perte évitée » est négative : c'est la prime d'assurance payée.** *Calculé*.
Conclusion méthodologique : pour une DAO, **la perte évitée n'est pas une grandeur du monde, c'est une grandeur conditionnelle**. La formule à figer est :

```
Perte évitée attendue (DAO) = P(obligation dans la fenêtre) × (Perte évitée | obligation)
                              − (1 − P(obligation)) × Coût de l'aller-retour
```

Avec les nombres ci-dessus : si `P(obligation) = 20 %` (hypothèse à figer, non sourcée), l'espérance sur 20 M$ exposés est `0,2 × 110 912 − 0,8 × 800 000 = −617 818 $` → **l'action n'est pas justifiée sur 20 M$ exposés avec cette hypothèse** ; elle le devient si l'exposition au stress est plus grande, si la venue est contrainte (0,80526 → 258 578 $ gagnés) ou si `P(obligation)` est plus élevé. **C'est le calcul que la DAO doit faire, et il doit figurer dans le dossier, pas dans une note de bas de page.** *Calculé*.

**(c) Ce que la DAO gagne même quand elle perd de l'argent** : le risque d'incapacité de liquidation. La bonne métrique n'est pas le P&L, c'est la **probabilité de tomber sous le plancher de runway** et le **délai de sortie** : au plus bas, la profondeur de sortie en stablecoin était suffisante (USDC/USDT restait échangeable), mais les PSM DAI se sont vidés « en heures » et Binance/Coinbase ont **suspendu les conversions USDC→USD** (FAIT SOURCÉ, BPI) — un chemin de sortie *contractuel* peut se fermer sans que le marché cesse de coter. Un agent qui n'anticipe que le **prix** manque la moitié du risque.

### E.3 — Lecture 2 : persona desk (P&L simulé, aller-retour, asymétrie)

Inventaire illustratif **2 M$ d'USDC** détenu comme collatéral d'un desk ; coût d'aller-retour hypothétique **20 bp** (`k = 4 000 $`), à mesurer réellement (frais + slippage via l'échelle de profondeur).

| Scénario | `P_exec` | `P_T` | `ΔP&L_net = q(P_exec − P_T) − k` | En % de l'inventaire |
|---|---|---|---|---|
| Coupe **tardive** (0,95) puis re-entrée après guérison (0,99) | 0,95 | 0,99 | **−84 000 $** | **−4,20 %** |
| Coupe **précoce** (0,98) puis re-entrée (0,99) | 0,98 | 0,99 | **−24 000 $** | **−1,20 %** |
| Coupe **précoce** (0,99), **pas de re-entrée**, scénario où la parité ne se rétablit pas (0,88 — **contrefactuel étiqueté**) | 0,99 | 0,88 | **+216 000 $** | **+10,80 %** |
| Idem, mais sortie contrainte à la venue la plus décotée (0,80526 — **contrefactuel**) | 0,99 | 0,80526 | **+365 480 $** | **+18,27 %** |

*Calculé* (`calculs_w2d.json`). **Lecture honnête** : sur le chemin **réellement réalisé** (guérison), l'agent de dérisquage **perd 4,2 %** ; sur le chemin contrefactuel (non-rétablissement), il « gagne » 10,8 à 18,3 %. C'est la signature d'un **put**, pas d'une alpha : la valeur est dans la queue, pas dans la moyenne, et elle ne peut être évaluée qu'en **espérance sur des scénarios pondérés** (§B.4, point 3).

Corollaire opérationnel pour le desk (et c'est une conclusion forte du dossier) : **la décision de dérisquage d'inventaire n'est pas une décision de marché, c'est une décision de tolérance au risque de valorisation de collatéral**, avec une règle de seuil du type `x·(P_T − P_exec) > k_aller-retour + financement` (§B.4, point 1). Avec `k = 20 bp`, il faut un écart de ≥ 20 bp pour que l'aller-retour soit neutre — soit un prix de sortie supérieur de 20 bp au prix de ré-entrée attendu.

### E.4 — Trois leçons de l'exemple, à inscrire dans la doc technique

1. **Le prix de référence « retenu » (oracle) n'est pas le prix auquel on sort.** Au pire de l'épisode, l'oracle Aave affichait 0,9069 pendant que les venues traitaient 0,805–0,882 : une fonction de perte construite sur l'oracle **sous-estime la perte de 296 bp au minimum, et jusqu'à 1 000 bp sur la venue la plus mauvaise** (MESURÉ). Toute perte évitée doit être calculée au prix **réalisable** de la venue où l'action a effectivement lieu.
2. **La dispersion entre venues (767–870 bp) est du même ordre que la décote elle-même.** Pour une exposition répartie, « vendre » n'a pas un prix, mais une **distribution** de prix ; la fonction d'objectif doit prendre `P_exec` comme une **variable**, pas comme une constante, et rapporter la sensibilité.
3. **Un dépeg qui guérit rend l'assurance coûteuse ; un dépeg qui ne guérit pas rend l'inaction fatale.** Sur les deux personas, le même épisode donne un « gain » et une « perte » ; c'est la **structure de l'obligation** (et non le prix) qui décide du signe. C'est l'argument central pour refuser un score unique et pour publier deux lectures.

---

## (f) Ce qui reste à trancher par l'équipe

1. **Objet de l'objectif : regret ou espérance ?** Proposition : les **deux**, mais publiés séparément — le regret par fenêtre comme métrique de **décision** (comparable entre systèmes, indépendante du scénario réalisé), l'espérance sur scénarios pondérés comme revendication **économique**. Décision attendue : qui signe les probabilités de scénarios (G6) ?
2. **Unité de compte de la DAO** : dollars, jours de runway, ou les deux ? Proposition : **les deux**, jours de runway en premier plan pour la DAO (c'est son unité native), dollars en annexe. Impact : la conversion dépend de l'opex de référence (16,4 M$/an pour ENS — quelle référence pour ORVYREN ?).
3. **Convention de valorisation** (§B.0) : terminale ou liquidation ? Proposition : **liquidation** pour la DAO (plus prudente, cohérente avec l'IPS « redeemable within 7 days »), **terminale + financement** pour le desk. Décision attendue avant G1.
4. **Faut-il modéliser la re-entrée ?** Proposition : **oui pour le desk** (dans la même fenêtre, coût d'aller-retour explicite), **non pour la DAO** dans l'épisode (la ré-entrée relève de la politique de réallocation, pas de l'agent). Décision attendue avant G1.
5. **Seuils chiffrés de §C.4** : 5 % de perte évitée, 10 % de friction, 6 h d'antériorité, 30 bp de slippage, 20 % de drawdown, Sharpe > 0 avec borne basse > 0. **Ce sont des propositions, pas des faits** ; ils doivent être validés ou remplacés **avant** l'ouverture du jeu d'évaluation.
6. **`P(obligation)` par fenêtre** (persona DAO) : hypothèse à figer, à justifier par un raisonnement explicite (calendrier de charges, appels de marge, redemptions) — aucune source publique n'existe (déclarer « hypothèse »).
7. **Jeu de scénarios du persona desk** : quels scénarios contrefactuels, avec quelles probabilités, et qui les gèle ? Proposition minimale : (i) réalisé, (ii) non-rétablissement à 48 h, (iii) guérison lente (5 jours), (iv) venue unique contrainte (0,80526).
8. **Épisodes de développement/évaluation** : confirmer l'arbitrage de §C.2 (USDC + stETH en développement ; rsETH + USD0++ en évaluation), et décider du sort de **xUSD** (aucune série de prix → cas qualitatif seulement).
9. **Niveau d'autonomie revendiqué** : l'agent **propose** ou **exécute** ? Cela change la fonction d'objectif (qualité de recommandation vs coût d'exécution) et la métrique de sûreté.
10. **Budget de risque explicite par épisode** : introduire une variable d'enveloppe `max_perte_par_episode` (aujourd'hui absente des sources : **NON TROUVÉ** côté DAO) et un plafond de taille d'action (`x_max`), pour que la politique soit bornée par construction.
11. **Coût de capital et financement** (persona desk) : quel taux retenir, et comment l'inclure sans transformer un P&L simulé en fiction ? Proposition : publier **deux** P&L (hors et avec financement) et laisser la différence visible.
12. **Qui gèle, qui rejoue** : nommer un responsable du gel (G1–G6), un exécutant aveugle (qui lance l'évaluation sans avoir écrit le code), et un relecteur externe (un tiers qui n'a pas écrit le code), même si le relecteur arrive après le concours (`R3` §B.6, item reporté).

---

## Sources

Statut de consultation : toutes les URL ci-dessous ont été **ouvertes ou extraites** le 15/10/2026 (sauf mention `[snippet]` = résumé de moteur de recherche, non ouvert).

**Persona DAO**
1. `[ouvert]` ENS DAO — *[6.46] [Social] 2026 Endowment Investment Policy Update*, post KPK du **8 mai 2026**, vote social passé, thread fermé le **11 août 2026** — <https://discuss.ens.domains/t/6-46-social-2026-endowment-investment-policy-update/22106> (copie complète : `raw_w2d/pages/…22106.md`)
2. `[snippet]` ENS Docs — *EP 6.46* — <https://docs.ens.domains/dao/proposals/6.46/>
3. `[ouvert]` KPK — *Monthly Treasury Report: June 2026*, **27 juillet 2026** — <https://kpk.io/blog/monthly-treasury-report-june-2026>
4. `[ouvert]` KPK — *Framework for Active DAO Treasury Execution*, **4 janvier 2023** — <https://kpk.io/blog/kpk-asset-management-framework>
5. `[ouvert]` Compound DAO — *Request for Proposals (RFP): Compound DAO Treasury Management Program* (page consultée le 15/10/2026 ; date de publication non affichée) — <https://www.comp.xyz/t/request-for-proposals-rfp-compound-dao-treasury-management-program/7867>
6. `[ouvert]` ENS DAO forum — *ENS Endowment: Independent Risk Teardown*, `riskypete` (Sentralis), **14 juillet 2026** — <https://discuss.ens.domains/t/ens-endowment-independent-risk-teardown/22282>
7. `[ouvert]` Eco — *Stablecoin Treasury Management: 2026 Best Practices* (mise à jour > 1 mois au 15/10/2026) — <https://eco.com/support/en/articles/14799675-stablecoin-treasury-management-2026-best-practices>
8. `[ouvert]` Eco — *Stablecoin Depeg: What Causes It and How to Spot Risk* — <https://eco.com/support/en/articles/15182160-stablecoin-depeg-what-causes-it-and-how-to-spot-risk>
9. `[snippet]` Eco — *DAO Treasury Management: Onchain Governance & Spend* — <https://eco.com/support/en/articles/14799687-dao-treasury-management-onchain-governance-spend>
10. `[snippet]` Steakhouse Financial — documentation (cadre de risque, curation de vaults) et *ENS Financial Reporting by Steakhouse* (forum ENS) — <https://www.steakhouse.financial/docs> ; <https://discuss.ens.domains/t/ens-financial-reporting-by-steakhouse/16601> ; dashboard <https://dune.com/steakhouse/ens-steakhouse>
11. `[snippet]` ChainScore Labs — *How to Design a Treasury Stress Testing and Simulation Process* (seuils de perte à trois niveaux ; « Llama Risk Framework » cité comme utilisé par Gitcoin et ENS) — <https://chainscorelabs.com/guides/governance-operations-architecture/treasury-management-systems/how-to-design-a-treasury-stress-testing-and-simulation-process>
12. `[snippet]` Rubric Financial — définition de « runway » (trésorerie ÷ burn mensuel net) — <https://www.rubricfinancial.com/glossary/runway>

**Épisode USDC / SVB (faits)**
13. `[ouvert]` Federal Reserve, *FEDS Notes* : Du, Sonawane, Watsky — *In the Shadow of Bank Runs: Lessons from the Silicon Valley Bank Failure and Its Impact on Stablecoins*, **17 décembre 2025** — <https://www.federalreserve.gov/econres/notes/feds-notes/in-the-shadow-of-bank-run-lessons-from-the-silicon-valley-bank-failure-and-its-impact-on-stablecoins-20251217.html>
14. `[snippet]` Bank Policy Institute — *Stablecoin Risks: Some Warning Bells* (USDC 0,87 $ ; run dès le 9 mars ; suspension des conversions par Binance et Coinbase ; USDe 0,65 $ le 10/10/2025) — <https://bpi.com/stablecoin-risks-some-warning-bells/>
15. `[ouvert]` Sankaewtong, Kitzler, Haslhofer, Ikeda — *Tracing Stablecoin Contagion during the USDC Depeg after the Silicon Valley Bank Collapse*, arXiv:2606.07442, **5 juin 2026** — <https://arxiv.org/html/2606.07442v1>
16. `[snippet]` *Stablecoin reserve risk under the GENIUS Act: Evidence from the Silicon Valley Bank shock*, ScienceDirect (accès ouvert) — déviation anormale de pic **≈ 1260 bp** pour USDC ; déviation médiane de pic **2,97 %** (régime GENIUS) vs **5,85 %** (statu quo) — <https://www.sciencedirect.com/science/article/pii/S1059056026007331>
17. `[ouvert]` Circle — *3.3 billion of USDC reserve risk removed; dollar de-peg closes* — <https://www.circle.com/pressroom/3-3-billion-of-usdc-reserve-risk-removed-dollar-de-peg-closes>
18. `[MESURÉ interne]` `W2A_donnees_episodes.md` §2.1 (oracle Aave, Curve 3pool, Binance/OKX/Kraken/Bitstamp) et `W2B_signaux_detection.md` §Famille 1 (dispersion 767–870 bp, Bitstamp 0,80526, oracle 0,9069)

**Persona desk**
19. `[ouvert]` Keyrock — *What is Crypto market making? A guide* (page consultée le 15/10/2026 ; pas de date affichée) — <https://keyrock.com/knowledge-hub/guide-crypto-market-making/>
20. `[ouvert]` DWF Labs — *How to Choose a Crypto Market Maker: 10 Key Criteria to Consider*, **13 septembre 2024** (mise à jour **5 septembre 2025**) — <https://www.dwf-labs.com/news/how-to-choose-a-crypto-market-maker-10-key-criteria-to-consider>
21. `[ouvert]` *Backtesting Market Making Strategies in Crypto Landscapes* (thèse, diva-portal) — <https://his.diva-portal.org/smash/get/diva2:1972292/FULLTEXT01.pdf>
22. `[snippet]` IBKR Quant Campus — *Equity Market-Neutral Trading with Dealer-Exposure Levels…* (formules MaxDD, Sortino, information ratio) — <https://www.interactivebrokers.com/campus/ibkr-quant-news/equity-market-neutral-trading-with-dealer-exposure-levels-and-options-flow-confirmation/>
23. `[snippet]` *Investment portfolio optimization with supervised learning and attention mechanism*, ScienceDirect (formules SoR, MDD, IR ; MDD 20–30 % en stress pour les méthodes classiques) — <https://www.sciencedirect.com/science/article/pii/S1110866525002324>
24. `[snippet]` JKP Factors — *Problem Set 3* (coûts : 10 bp par dollar échangé ; Sharpe 1,86) — <https://jkpfactors.com/ctf/download/doc/d1905a8e-bb64-4914-8979-26adfc49d3a0>
25. `[snippet]` NeH Capital — *Electronic Market Making: Spread Capture and Inventory Risk*, **2 octobre 2026** (diagnostics : realised spread, inventory duration, markout, pertes en volatilité) — <https://www.nehcap.com/2026/10/02/electronic-market-making-spread-inventory-risk/>
26. `[snippet]` XR Academy — *Economics of Market Making* (décomposition `Net P&L = V·S + V·R − V·AS − V·EC − I·HC·T − OC − K·CC`) — <https://xrpacademy.com/course/market-making-xrp/lesson/economics-of-market-making>
27. `[ouvert]` Bailey & López de Prado — *The Deflated Sharpe Ratio*, JPM 40(5), 2014 — PDF <https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf> ; SSRN <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551> ; *False Strategy Theorem* (AMM 2021) cité via <https://www.quantresearch.org/Publications.htm>

**Protocole interne**
28. `[MESURÉ interne]` `R3_evaluation_benchmark.md` (B.0–B.7, §(d) pièges, §Sources) — base du pré-enregistrement étendu ici
29. `[MESURÉ interne]` `raw_w2d/calculs_w2d.json` — tous les chiffres calculés de ce document (double comptage, runway, pertes évitées, P&L desk, dispersion)

---

## Non trouvé (à ne pas combler par des inventions)

1. **Objectifs chiffrés publiés par un desk crypto nommé** (Wintermute, GSR, Keyrock, Amber Group) : aucune interview publique trouvée le 15/10/2026 exposant un Sharpe cible, un budget de drawdown, une tolérance de slippage, un coût de capital interne ou un ratio capacité/ADV. Les objectifs du persona desk (§A.2.5) sont une **reconstruction par métriques de la profession**, pas une citation.
2. **Budget de risque chiffré par une DAO** : aucun document de politique trouvé qui énonce une perte maximale par épisode ou un drawdown budgété en valeur absolue pour une trésorerie de DAO. L'IPS ENS impose un **rapport** de drawdown mensuel, pas un **plafond**.
3. **Cibles chiffrées de Steakhouse / Block Analitica / Lido / Aave / Sky** sur l'appétit de risque : non trouvées (les recherches du 15/10/2026 sur « Block Analitica / Gauntlet / Sky » n'ont **rien** renvoyé d'exploitable). Le seul ancrage chiffré obtenu pour une DAO est l'IPS ENS 6.46 (runway, concentrations, plafonds d'actifs).
4. **Distribution de probabilité publique de scénarios de dépeg** (pour l'évaluation en espérance du persona desk, §B.4) : non trouvée. Les `p_s` seront **nos hypothèses**.
5. **Série de prix exploitable pour xUSD / Stream Finance (nov. 2025)** : non trouvée (`W2A`, `W2B`) → exclu de l'évaluation quantitative.
6. **Sensibilité de `P(obligation)`** pour une trésorerie de DAO (fréquence réelle des ventes forcées pendant une crise) : non trouvée. C'est le paramètre le plus déterminant de l'exemple §E.2 et il est aujourd'hui une hypothèse.
7. **Profondeur d'exécution des stablecoins au pire de la crise USDC** (échelle `get_dy` sur les pools actifs le 11 mars 2023) : non mesurée ; seules les séries de prix et les soldes de la 3pool le sont. Chantier ouvert (cf. `W2B` §(f) chantier 5).
