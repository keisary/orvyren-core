# VAGUE 2 — SYNTHÈSE (W2-A → W2-E)

**15 octobre 2026** (rédigée de nuit, pendant que l'équipe dort). Cinq chantiers livrés :
`W2A_donnees_episodes.md` (39 Ko) · `W2B_signaux_detection.md` (30 Ko) · `W2C_enveloppe_execution.md` (76 Ko) · `W2D_objectifs_mesure.md` (77 Ko) · `W2E_concurrence_agents.md` (51 Ko).
Chaque fichier porte ses sources (URL + dates) et ses « non trouvé ». La construction correspondante est **en cours** (W3-A/B/C : couche données + épisodes probants + compléments).

---

## 1. En bref — ce que la vague 2 a établi

1. **La faisabilité technique ne dépend d'aucun budget** : l'état on-chain historique est accessible **gratuitement et sans clé** via `eth.drpc.org` / `blastapi` (testé de 2021 à 2026) ; les prix minute multi-venues sont gratuits (Binance dumps, OKX, Kraken, Bitstamp, DeFiLlama). Les payants (CoinGecko, Kaiko, Dune exécutable) sont évitables.
2. **Le cœur du problème est mesurable et déjà mesuré** : l'écart « valorisation retenue vs prix réalisable » — oracle Aave à 0,96 $ quand le marché USDC traitait 0,87–0,91 $ (mars 2023) ; oracle rsETH à ~2 500 $ quand sa valeur de sortie réalisable s'effondrait (avril 2026, −31 %).
3. **Trois épisodes retenus pour la démo et l'évaluation** : **rsETH/KelpDAO (avril 2026)**, **USD0++ (janvier 2025)**, **xUSD/Stream (novembre 2025)** ; **USDC mars 2023** et **stETH juin 2022** servent de backtests « prix » riches et faciles à citer. Le bad debt Aave 2026 n'est pas un épisode à part : c'est la conséquence mesurable du rsETH.
4. **L'enveloppe d'exécution est déjà le standard** : Zodiac Roles v2 (Safe) — **bytecode identique vérifié** sur Ethereum, Base et Base Sepolia ; précédent ENS×karpatkey en production depuis 2023, tenu face à un incident en 2026.
5. **Les objectifs et la mesure sont définis par persona** : DAO = contrainte de préservation (runway, obligations) mesurée en perte évitée conditionnelle + temps ; desk = P&L net + risque, avec un seuil d'action chiffré. La fonction de perte corrigée (sans double comptage) a passé 6 tests de cohérence.
6. **La différenciation tient, mais le créneau est étroit** : l'enveloppe bornée est devenue une commodité 2026 ; ce qui reste rare, c'est **la décision vérifiable** (provenance recalculable, abstention documentée) croisée avec **le signal de graphe de collatéral multi-protocole**.

---

## 2. Chantier par chantier

### W2-A — Données & vérité terrain
- Archive gratuite testée : `eth_call` sur blocs 2021→2026 (Aave V2/V3, Lido, Curve, Chainlink) ; seule limite : `eth_getLogs` ≤ 10 000 blocs/requête (pagination gratuite).
- Prix minute gratuits vérifiés : Binance (dumps `data.binance.vision` y compris aggTrades), OKX, Kraken, Bitstamp, DeFiLlama (avec scores de confiance). Coinbase Exchange : endpoint public USDC en 404 (à contourner) ; CoinGecko/CryptoCompare : 401 sans clé ; Dune gratuit = lecture seule (inutilisable en pipeline).
- « Valeur retenue vs valeur réalisable », le cœur du problème officiel : **mesurée** sur 2 épisodes (USDC : oracle 0,9599 vs marché 0,87–0,91 ; rsETH : oracle 2 513 $ vs réalisable ~0).
- Ce qui manque et devra être **reconstruit par nos soins** : séries de prix des tokens « invisibilisés » (xUSD, USD0++) depuis les pools DEX ; et la vérité terrain « actions faisables » (n'existe nulle part publiquement → simulation avec nos relevés).

### W2-B — Table des signaux
- **USDC mars 2023** : oracle Chainlink au plus bas **0,90687** vs agrégat DeFiLlama **0,876675**, Bitstamp **0,80526**, OKX 0,8698, Binance 0,8820 → **dispersion inter-venues 870 bps** ; l'oracle **sous-estime la décote de ~3 cents**. Seuils candidats posés (≥ 50 bps/15 min = alerte ; ≥ 200 bps = rupture ; ≥ 500 bps = sortie).
- **stETH juin 2022** : décote **réalisable** mesurée par `get_dy` Curve — **6,185 %** le 15 juin ; **> 2 % dès le 15–21 mai** → **≈ 4 semaines d'antériorité** avant le gel Celsius. Le seul signal à longue antériorité mesurée.
- **rsETH avril 2026 — correctif majeur** : le marché n'était **pas** à 100 % d'utilisation (U ≈ 0,008 %) ; le mécanisme réel = **gel administratif** (`isFrozen` bascule à 19:03:59 UTC, 1 h 29 après l'exploit) + **saturation du plafond d'émission à 99,999 %** (529 993,98/530 000) dès 18:00 UTC — mesure inédite. Les autres signaux (gel, saturation, divergence) sont de **confirmation**, pas d'anticipation : à dire honnêtement.
- Familles documentées : décote de peg · dispersion inter-venues · divergence oracle/marché · décote LST réalisable · profondeur/slippage · vitesse de drain · utilisation/gel/plafond · composition du collatéral · ré-hypothécation · invariants inter-chaînes · concentration.

### W2-C — Enveloppe d'exécution
- **Zodiac Roles v2 confirmé** : contrat `0xF2964CE6…83D5`, 24 409 octets, bytecode **identique** Ethereum/Base/Base Sepolia (vérifié `eth_getCode`) ; libs présentes sur le testnet.
- Modèle : **T2 dans une enveloppe votée** — rôle `bytes32` avec périmètre cible/fonction/paramètre + allowances (refill/maxRefill/period). Précédents : ENS×karpatkey (EP 5.12/5.14, mises à jour #8/#9/#10), Balancer, GnosisDAO, Scroll.
- Alternatives écartées : Coinbase Spend Permissions (trop étroit), Safe Allowance Module (absent de Base Sepolia), session keys (changement de socle).
- Limites à assumer dans le dossier : pas d'expiration native ; rafale de frontière de période → **compteur glissant hors chaîne en premier verrou** ; incidents amont 2026 (contournement ERC-1271 en v2.1.0, frontière MultiSend) → suivre les versions/commits.
- Signer : **EOA dédiée** du rôle, sans droits d'administration (reverts testés). Kill switch : 1 transaction (`assignRoles(false)`/`disableModule`), bloc Base ≈ 1,64 s ; le délai humain n'est pas compressible ; une tx incluse n'est pas annulable.
- Démo planifiée (5 runs sur Base Sepolia) : ALLOW · DENY hors chaîne · DENY par la chaîne · kill switch chronométré · journal revérifié contre la chaîne.
- Responsabilité : la seule phrase sourçable = Chaos Labs (avril 2026), « la responsabilité du risk management DeFi reste fondamentalement indéfinie ». On vend un **mandat délimité + journal opposable**, pas une immunité.

### W2-D — Objectifs & mesure par persona
- **Fonction de perte corrigée** (le bug de la « formule M1 » est éliminé et démontré) : `L(a) = W_t − W_T(a)` puis `R_w(a) = L(a) − min_b L(b)` (b parmi les actions **faisables**) ; identité du bug : écart_bugué − écart_vrai = q·(1−P_T) ; 6 tests de cohérence (neutralité, translation, monotonie, signe, additivité, référence dégénérée).
- **DAO** : objectif **contraint** (pas un scalaire) — préserver + servir les charges ; politique ENS 6.46 : plancher de runway **49,34 M$ = 3 ans**, « inconditionnel » ; mesuré en **perte évitée conditionnelle** + **jours de runway** (44 932 $/jour) + antériorité ≥ 6 h + latence + taux de fausses alertes.
- **Desk** : **ΔP&L net** (frais, slippage réalisable, financement) + Sharpe/Sortino/MaxDD ; seuil d'action `x·(P_T−P_exec) > coût d'aller-retour + financement` ; l'agent est un « PUT » — sur USDC : −4,2 % sur le chemin réalisé, **+10,8 % dans le contrefactuel**.
- **Protocole de pré-enregistrement prêt à geler** : comparateurs A0/A1/A2 + **B0 placebo apparié**, séparation DEV/EVAL, embargo, journal des variantes, seuils par persona. **12 points à trancher en §(f)** (convention de valorisation, P(obligation), scénarios desk, jeux DEV/EVAL, etc.).
- Non trouvé (assumé) : objectifs chiffrés publics de desks ; budgets de risque chiffrés des DAOs ; P(obligation) publique ; série xUSD → **exclu du quantitatif**.

### W2-E — Concurrence
- **L'enveloppe bornée est une commodité** (≥ 9 plateformes d'agent wallets ; Almanak affiche déjà Safe+Zodiac) ; **Brahma/ConsoleKit est mort** (racheté par Polymarket, produits éteints le 17/04/2026).
- **Concurrents les plus dangereux** : **LlamaRisk/LlamaGuard** (workflows rejouables, rôle borné, en production sur Aave) et **Chaos Labs Risk Oracles** (~10 Md$ sécurisés) — mais **mono-protocole et gouvernés**.
- **Aucun concurrent ne couvre les 5 axes.** Croisement unique d'ORVYREN : agent autonome multi-protocole × signal de graphe de collatéral × provenance recalculable × abstention/refus documentés × double enveloppe.
- Le créneau « **Policy Decision Record** » est désigné comme chantier ouvert par la littérature (arXiv:2601.04583).
- Leçon de pitch : **« vendre la décision, offrir l'exécution »** ; liste de veille concurrentielle en §d.

---

## 3. Corrections assumées (à porter au dossier)

1. « 100 % d'utilisation » sur rsETH → **faux tel que dit** ; le mécanisme réel : gel administratif + saturation du plafond d'émission de collatéral. (W2-B, confirmé W3-A)
2. « Bitstamp 0,8627 » → **résolu (W3-B)** : c'est la clôture horaire de la bougie 07:00Z (bas 0,80526 de la même bougie) ; le 0,8767 agrégat, lui, est reproduit à l'identique.
3. **Minimum dense de l'oracle USDC : 0,8833** (11/03 07:53:23Z, bloc 16 803 515, vérifié sur 2 RPC) — la valeur 0,90687 de W2-B était un point de grille exact mais **pas** le minimum (correction W3-B).
4. « 1 375 observations » et d'autres compteurs d'étapes antérieures sont périmés face aux mesures des vagues 2-3. (W2-A/B, W3)
5. **Décote stETH — chiffres finaux (W3-A, série 253 points)** : premier franchissement des 200 bps le **13/05/2022** (213,7 bps ; 66,9 bps la veille) ; pire point **6,93 % (1 stETH) / 6,98 % (1 000 stETH) le 14/06/2022 10:00Z**. (La fourchette « 15-21/05 » de W2-B, mesurée sur un échantillonnage plus clairsemé, est remplacée.)

## 4. Ce que ça change pour le projet

- **Épisodes** : la démo se fera sur **rsETH** (données on-chain les plus riches, gel daté à la seconde) ; l'évaluation quantitative couvre rsETH + USD0++ + USDC (stETH en backtest long). xUSD reste qualitatif tant que sa série n'existe pas.
- **Enveloppe** : la partie « agent wallet » du thème F est **tranchée** — Zodiac Roles v2 sur Base, signer EOA, kill switch, journal opposable. Reste à exécuter la démo testnet (kit W3-D).
- **Mesure** : on a désormais un protocole gelable et une fonction de perte qui résiste à la revue. Le « 10,8 % contrefactuel vs −4,2 % réalisé » illustre pourquoi la **comparaison au faisable** (et non au fantasme ex-post) est la règle.
- **Positionnement** : le pitch se recentre sur « décision vérifiable + graphe de collatéral », pas sur « agent autonome » (commoditisé).

## 5. Prochaines étapes

- **Fait (15/10)** : W3-A/B/C clos — couche données `src/orvyren/data/` (RPC archive avec repli drpc→blastapi, Aave, Curve, Chainlink) + **3 épisodes reconstruits et probants** (`evidence/episode_rseth_2026-04.json`, `episode_steth_2022-06.json`, `episode_usdc_2023-03.json`) ; compléments comblés : **séries xUSD (457 h) et USD0++ (635 h) trouvées**, concentration via Blockscout validée, Compound/Morpho testés, plan de calibration livré. Suite de tests : **221 verts, 2 sautés**. Commits `153b93b`, `3ac6ed3`.
- **Pause volontaire** : W3-D (kit de démo testnet) **non lancé** — la construction du produit est la prochaine phase, à déclencher par l'équipe.
- **Décisions à trancher (avec l'équipe)** : les 12 points de W2-D §(f), le choix définitif des jeux DEV/EVAL, le point de départ de la courbe de calibration, et les édits du cadre (§04/05/06) ci-dessous.
- **Restes assumés** : profondeur d'exécution des stablecoins au pire de mars 2023 (non mesurée) ; archive Comet/Morpho à confirmer ; calibration à exécuter (10-20 h de collecte estimées).

## 6. Édits proposés au cadre (à appliquer à son retour)

- **§04 Périmètre** : remplacer « LST Ethereum+Base » par les épisodes retenus (rsETH/USD0++/xUSD + backtests USDC/stETH) + chaînes Ethereum (lecture) / Base (exécution).
- **§05 Résultat mesurable** : pointer sur la fonction de perte corrigée + protocole A0/A1/A2/B0 par persona (W2-D).
- **§06 Autonomie** : préciser Zodiac Roles v2 (T2), kill switch 1 tx, limites assumées (pas d'expiration native, frontière de période) et signer EOA.
- **Annexes** : lier les cinq rapports W2 + la présente synthèse.
