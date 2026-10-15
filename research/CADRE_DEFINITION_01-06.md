# ORVYREN — CADRE DE DÉFINITION 01–06

**Version 2 — 15 octobre 2026.** Trois recherches dédiées (U1 banques, U2 DeFi/trading, P1 problème) sont intégrées : les sections **01 et 02 sont réécrites** avec sources et chiffres vérifiés ; les sections 03–06 restent en proposition. Chaque section : **PROPOSITION**, **À TRANCHER** (le choix qui revient à l'équipe), **RECHERCHES**.
Statuts : `[PROPOSITION]` à valider · `[À TRANCHER]` décision d'équipe · `[ACQUIS]` établi par recherche (sourcé).

---

## 01 — UTILISATEUR PRINCIPAL *(réécrit — v2)*

### [ACQUIS] Les trois familles, départagées par la recherche

| Famille | Verdict de recherche | Preuves clés |
|---|---|---|
| **Banques & institutions financières** | **Marché réel, mais pas un premier client en 2026** → cible **phase 2 (2027-2028)** | Industrialisation réelle (DTC en production 15/07/2026 ; Agorá CHF 800 k ; JPMD sur Base ; Kinexys > 7 Md$/jour ; 300+ banques chez Fireblocks) **mais** : positions sur registres **permissionnés** (Kinexys, Besu privé, Canton) → un agent qui ne lit que le public est **aveugle** ; tout agent externe = **tiers TIC DORA** ; **AI Act art. 14** impose la supervision humaine ; cycles d'achat incompatibles avec une démo |
| **Organisations & gestion DeFi** (trésoreries de protocoles, DAOs, fonds) | **Crédible — et le meilleur axe pour le thème F** : primitives d'autorisation déjà acceptées, données publiques | Trésoreries en baisse : Lido 157,5 → 121,0 → 88,3 M$ ; ENS 101,6 → 67,7 M$ · budgets risque contestés : **Chaos Labs quitte Aave le 06/04/2026** (refuse 5 M$/an, minimum estimé 8 M$) · incidents venant de l'infra/contrepartie, pas de la stratégie : **rsETH/KelpDAO 18/04/2026 ≈ 292 M$**, bad debt Aave 123,7–230,1 M$ · **espace vide réel** : exécution décisionnelle bornée 24/7 + urgence + opérations mécaniques, vendue sous le coût humain (kpk 0,50 %/an, DeFi Saver 0,25–0,30 %) · précédent d'enveloppe native : **Zodiac Roles v2** avec caps, déjà adopté en gouvernance (ENS EP 6.39, mises à jour de permissions #8/#9) |
| **Équipes de trading crypto** (desks, market makers, fonds) | **Adjacent crédible** — cible secondaire de la phase 1 | Automatisation existante mais opaque (algo, risk engines internes type Keyrock) ; besoin identifié : **jambe DeFi de l'exécution** (liquidité DEX, vaults, hedge perps on-chain, settlement) sous limites d'exposition codées, 24/7 ; budgets outillage non publics (« non trouvé ») |

### [PROPOSITION] L'utilisateur principal recommandé

> **La trésorerie on-chain d'une organisation (protocole, DAO, fonds) qui doit protéger et opérer son capital en continu, 24/7, sans pouvoir payer une équipe de risque à plein temps.**

Trois raisons décisives, dans cet ordre :
1. **La donnée** (le critère que tu as posé, confirmé par les deux recherches) : tout son périmètre est **public on-chain** (positions, protocoles, historiques) — un agent peut réellement lire, vérifier et agir. À l'inverse, une banque vit sur des registres privés : un agent externe y est structurellement aveugle en 2026.
2. **La douleur est chiffrée et récente** : incidents 2026 (rsETH, bad debt), budgets de risque en contraction, trésoreries qui fondent → la valeur (protection, urgence, exécution) est un besoin **déjà payé**, pas un pari marketing.
3. **L'enveloppe existe déjà** : les primitives d'autorisation bornée (Zodiac Roles, Safe, caps) sont **acceptées par ces organisations** — le produit s'insère dans un standard, il ne demande pas un acte de foi.

**Qui possède les actifs** : l'organisation (sa DAO, son protocole, son fonds). ORVYREN agit par **autorité déléguée, bornée et révocable**. **Qui bénéficie** : l'organisation — capital protégé, exécution disponible 24/7, décisions traçables ; à terme, ses utilisateurs finaux.

### [TRANCHÉ par l'équipe — 14–15/10]
1. **Trésoreries de DAOs/protocoles D'ABORD** ; les **desks de trading ensuite** si le temps le permet. Les deux personas sont développés avec des **objectifs et critères distincts** : **DAO = prévision du risque et anticipation** (protéger, prévenir, rendre des comptes) · **desks = rentabilité** (performance, P&L net). → objet du chantier de recherche **W2-D** (`W2D_objectifs_mesure.md`).
2. **La phase 2 « banques »** reste conservée comme cible de déploiement (argument de vision devant le jury).

---

## 02 — PROBLÈME FINANCIER PRÉCIS *(réécrit — v2)*

### [ACQUIS] La formulation recommandée par la recherche

> **« Les marchés on-chain sont transparents, mais leurs risques ne sont pas lisibles : la solvabilité d'une position dépend d'une chaîne de collatéraux (stablecoins, tokens de staking liquide, actifs ré-hypothéqués) dont la valorisation retenue s'écarte silencieusement du prix réellement réalisable — et dont la dégradation est annoncée des jours à des semaines à l'avance par des signaux publics dispersés entre plusieurs chaînes, plusieurs protocoles, des places centralisées et des annonces datées. »**

ORVYREN intègre ces signaux dans un graphe explicite — **acteurs** (émetteurs, protocoles de prêt/perp, ponts et vérificateurs, vaults, market makers, gouvernance) · **variables** (décote de peg, composition et profondeur réelle du collatéral, ré-hypothécation, distance à la liquidation, concentration, paramètres de protocole, annonces datées) · **marchés** (DeFi + venues centralisées, où la divergence prix de place / état on-chain est elle-même une variable) · **horizons** (minutes · heures-jours · jours-semaines) · **régimes** (normal, stress de liquidité, stress de crédit, crise de confiance) — afin de **détecter ces ruptures et d'agir dans une autorité bornée : détecter, informer, réduire ou refuser l'exposition.**

### [ACQUIS] Les preuves qui portent cette formulation

| Cas | Ce que les signaux publics disaient | Antériorité |
|---|---|---|
| **USD0++ (Usual)** | Annonce publique du **plancher** le 09/01/2025 → dépeg | **2 jours** |
| **xUSD (Stream Finance)** | Position **invisibilisée** car valorisée à 1 $ fixe dans les marchés de prêt | détectable **avant** (03–04/11/2025) par la valorisation |
| **KelpDAO / rsETH** | **292 M$** (18/04/2026) — détectable seulement par *cross-chain invariant monitoring* (Chainalysis) ; fenêtre de réaction de **46–77 min** (gel à 100 % d'utilisation) | minutes (invariant), jours (paramètres) |
| **Alameda / FTX** | Collatéral **~40 % en FTT**, révélé le 02/11/2022 | **9 jours** avant la faillite |
| **Canal PSM** | La Fed documente le feedback TradFi↔DeFi et le canal des contrats autonomes qui « canalise et amplifie la contagion » (FEDS Notes, 17/12/2025) | documenté |

### [ACQUIS] Les régulateurs nomment le problème — ils disent manquer d'outils

IOSCO (« données on-chain et off-chain », lacunes de surveillance DeFi) · BCE (stablecoins « central[s] dans l'univers crypto », « surveillance supplémentaire justifiée ») · ESRB · OCDE · Réserve fédérale (FEDS Notes). **Ce qu'ils déclarent manquer : des métriques et des sources de données pour suivre ces risques en temps réel** — ORVYREN se place donc sur une **demande institutionnelle documentée**.

### [PROPOSITION] Trois formulations candidates, une recommandée

- **Candidat A — Intégrité des invariants inter-chaînes** (noyau dur vérifiable : un invariant qui casse est un fait, pas une opinion) → **gardé comme primitive de vérification**.
- **Candidat B — Rupture de solvabilité et de liquidité via le graphe de collatéral** → **RECOMMANDÉ** (c'est la formulation ci-dessus : elle couvre les cas documentés et justifie le graphe).
- **Candidat C — Intégration multi-canaux avec mémoire de graphe** (isomorphisme MIMIR complet) → **reporté** (le plus ambitieux, le moins prouvable à court terme).

### [À TRANCHER]
- **Valider le candidat B** comme problème officiel du projet (avec A en invariant) ?
- **La promesse d'action** : « réduire ou refuser l'exposition » (défensif, mesurable) ou viser aussi la **capture d'opportunité** (plus ambitieux, plus difficile à prouver) ? *Recommandation : défensif d'abord.*

### [RECHERCHES — les manques déclarés par P1]
- **PN1** — Vérité terrain horodatée à la granularité nécessaire pour **évaluer** (qui n'existe pas aujourd'hui en accès libre) : à construire ou simuler.
- **PN2** — Licences et coûts des **valorisations on-chain historiques multi-chaînes** (à vérifier avant d'en dépendre).
- **PN3** — Aucun chiffre agrégé public trouvé pour stETH/Celsius (« non trouvé ») et aucune quantification de « ce qu'un agent aurait économisé » : à assumer ou à construire par simulation avec bornes.

---

## 03 — DÉCISION À AMÉLIORER

### [PROPOSITION] Une décision, trois familles *(recadrées sur l'utilisateur v2)*

| Famille | Exemple concret (trésorerie on-chain) | Aujourd'hui | Avec ORVYREN |
|---|---|---|---|
| **Protection** (stress) | « Un collatéral décroche à 100 % d'utilisation du marché, il est 3 h du matin » | Réaction humaine en heures ; l'incident de référence a laissé **46–77 minutes** de fenêtre | Détecter, qualifier (invariants + graphe), appliquer le **playbook défensif préapprouvé** ou refuser de conclure |
| **Opérations** (mécanique 24/7) | « Rééquilibrer entre deux bandes, honorer un calendrier, maintenir un runway » | Équipe réduite, tâches répétitives, coût humain | Exécution bornée dans une enveloppe vérifiable (caps, allowlists) |
| **Placement** | « Où garder 2 000 ETH : quels supports, quel risque, quelle liquidité ? » | Décisions annuelles, peu instrumentées | Évaluation qualité/risque des supports, décision tracée — **après** protection et opérations |

**Ce que la décision doit devenir** : évaluée (pas réflexe), bornée (pas illimitée), traçable (recalculable).
**Ordre de valeur recommandé** (validé par U2) : **urgence > opérations > rendement**. Jamais « gérant discrétionnaire ».

### [À TRANCHER]
- **La première démo démontre quelle famille ?** *Recommandation : protection (cas USDC/collatéral déjà outillé) + une opération mécanique (pour montrer le 24/7).*

---

## 04 — PÉRIMÈTRE FINANCIER

### [PROPOSITION] Public on-chain d'abord, « collatéral & stablecoins » au centre

| Dimension | Phase 1 | Extension | Exclu volontairement |
|---|---|---|---|
| **Actifs** | Stablecoins (USDC, USDT, DAI), **LST majeurs** (stETH/rsETH et équivalents), ETH — c'est le **graphe de collatéral** le cœur du problème | wBTC, autres LST/LRT, actifs tokenisés | Levier discrétionnaire, alts illiquides, tokens exotiques |
| **Chaînes** | **Ethereum + Base** (Ethereum = profondeur réelle du collatéral ; Base = exécution économique et choix concours) | Arbitrum, Polygon | Chaînes inconnues / non vérifiables |
| **Protocoles** | Lending majeurs (Aave), DEX majeurs (Uniswap), staking liquide, ponts officiels — **allowlistés, contrats vérifiés** | Autres protocoles après filtre | Protocoles non vérifiés, fermes de rendement |
| **Horizons** | Minutes (invariants, urgence) · heures-jours (stress) · jours-semaines (position) · mois (allocation) | — | HFT |
| **Données** | Prix multi-venues, **états on-chain** (positions, utilisation, profondeur), offres, **annonces datées** — et, si intégration : APIs de custody | Preuves de réserves, données de venues centralisées | Jeux sans horodatage admissible |
| **Cadre** | **Données publiques** + testnet pour l'exécution démontrée | APIs privées **seulement** si un utilisateur l'exige | Fonds réels, émission de jetons, promesse de rendement |

**Principe confirmé par le critère « donnée »** : ORVYREN est un agent du **monde public on-chain** ; l'intégration à des registres privés (custody bancaire) est une **phase 2**, conditionnée à un partenaire.

### [À TRANCHER]
- Retenir **Ethereum + Base** ? (Ethereum est nécessaire pour le graphe de collatéral réel ; Base pour l'exécution démonstrative.)
- Le périmètre phase 1 inclut-il **les LST** en plus des stablecoins ? *Recommandation : oui — c'est là que vit le problème documenté (rsETH).*

---

## 05 — RÉSULTAT MESURABLE

### [PROPOSITION] Quatre axes de preuve, du plus fort au plus faible

| Axe | Mesure | Comparateur | Honnêteté |
|---|---|---|---|
| **1. Économique — protéger** | **Perte évitée** / richesse nette, nette des coûts, en regret vs l'ensemble des actions **faisables** | Ne rien faire (A0) · règle de seuil (A1) · agent (A2) · **placebo apparié** (B0) | Sur peu d'épisodes : **mesure**, pas preuve statistique — écrit noir sur blanc |
| **2. Qualité de décision** | Calibration (Brier/ECE quand N suffit), INCONCLUSIVE corrects, contradictions détectées avant décision | Absence de ces mécanismes | Jamais de conclusion sur N insuffisant |
| **3. Opérationnel** | **0 opération hors politique** (matrice d'attaques nommée), **temps détection→action** (la valeur de l'urgence : 46–77 min), 100 % provenance recalculable, coût par décision | Alertes seules / bot opaque | Bornes de Wilson publiées comme indicatives |
| **4. Utilisateur** | Un tiers retrouve motif, limites et donnée manquante plus vite dans le dossier que dans les logs | CSV + logs bruts | Tâches définies |

**La preuve la plus forte : le paper trading en avant** (décisions publiées avant le résultat). Pour une trésorerie DAO, le **premier cas réel** peut venir d'une proposition de gouvernance (précédent EP 6.39) — une démonstration que le jury peut vérifier.

### [À TRANCHER]
- **Critère principal** : je recommande **« perte évitée nette + temps de réaction »** (le temps est la valeur la plus incontestable pour cette cible).

---

## 06 — MODÈLE D'AUTONOMIE

### [CONCEPTION PROPOSÉE] Cinq niveaux, une enveloppe, des verrous

| Niveau | Capacité | Qui signe |
|---|---|---|
| **T0 — Observer** | Lecture continue, analyse, alertes, dossier de situation | — |
| **T1 — Proposer** | Intentions structurées, simulations, scénarios | — |
| **T2 — Exécuter borné** | **L'agent exécute seul dans son enveloppe** (plafonds par transaction et période, allowlists d'actifs/contrats/fonctions/destinataires, expiration, idempotence, pause d'urgence) | **le système** (signer limité) |
| **T3 — Étendre** | Hors enveloppe : préparé, jamais exécuté seul | humain (approbation) |
| **T4 — Gouverner** | Politique, plafonds, clés, allowlists | humain uniquement — **l'agent ne peut jamais élargir ses droits** |

**Les verrous** : politique déterministe **hors LLM** · le LLM ne détient jamais de clé · l'exécution n'accepte qu'une intention **déjà autorisée** · reçu vérifié contre l'intention · **double verrou on-chain** possible : l'enveloppe native existe déjà dans l'écosystème cible (**Zodiac Roles v2** avec caps sur Safe — adopté en gouvernance, ex. ENS EP 6.39) · kill switch et journal opposable à tous les niveaux.
**Précédents à citer** : Chaos Labs quittant Aave (la responsabilité du risk management est « indéfinie ») → l'enveloppe bornée + journal sont aussi une réponse **juridique**, pas seulement technique.

### [À TRANCHER]
- **L'enveloppe T2 de la première démo** : montants, actifs, destinataires, durée (le 100/300/24 h actuel est un exemple).
- **Le verrou on-chain (Zodiac Roles) fait-il partie de la phase 1 ?** *Recommandation : oui — c'est le standard déjà accepté par la cible.*

---

## FUSION — ce que ce cadre absorbe, et ce qu'il abandonne

**Absorbé** : la vision canonique (comprendre → anticiper → décider → exécuter → apprendre) · la boucle du V0.2 §4.1 · les rôles du V0.2 §8 (agents) et le graphe factuel (mémoire partagée, sémantique MIMIR — projets distincts) · la politique + signer limité (§10) · les recherches R1–R3 (mesure, autonomie) · **les recherches U1/U2/P1 (utilisateur et problème — v2 de ce document)** · les corrections Astra · les invariants (PIT, autorisation, intégrité, comptabilité, dépendance des sources).

**Abandonné** : les profils grand public de la v1 (remplacés par les trois familles institutionnelles) · l'exécution par un humain (contraire au topic) · la deadline appliquée au code · la réduction du projet au prototype (il devient la brique politique+provenance) · « ORVYREN brique de MIMIR ».

---

## PROCHAINES RECHERCHES (ordre)

1. **PN1–PN3** (vérité terrain, licences, quantification des pertes évitables) — conditionne la section 05.
2. **R6a/R6b/R6c** (permissions on-chain, signer limité, responsabilité) — conditionne la démo et les 30 % sécurité.
3. **R3a/R5a/R5b** (règle de décision de référence, benchmark honnête, fonction de perte gelée) — dès que PN1 est cadré.
4. **R4a/R4b** (faisabilité technique Ethereum+Base : liquidité, données historiques, coûts).
5. **Étude d'intégration Zodiac Roles v2** (l'enveloppe native de la cible) — nouveau, issu de U2.
