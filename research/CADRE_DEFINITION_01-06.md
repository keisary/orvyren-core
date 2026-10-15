# ORVYREN — CADRE DE DÉFINITION 01–06

**Version 1 — 15 octobre 2026.** Ce document remplit le plan en six sections et **fusionne** tout le matériau accumulé (vision canonique du projet, document V0.2, sémantique MIMIR, recherches R1–R3, revues Astra, corrections de l'équipe). Chaque section : **PROPOSITION** (à corriger par l'équipe), **À TRANCHER** (le choix qui te revient), **RECHERCHES À LANCER**.
Statuts : `[PROPOSITION]` à valider · `[À TRANCHER]` décision d'équipe · `[ACQUIS]` déjà établi.

---

> **MISE À JOUR DU 15/10 (soir) — direction corrigée par l'équipe, sections 01 et 02 en révision.**
> **Cible** : ce ne sont pas les profils grand public proposés en v1, mais — par ordre d'étude — **(1) les banques et institutions financières, (2) les organisations et la gestion basée sur la DeFi** (trésoreries on-chain, DAOs, fonds), **(3) les équipes de trading crypto**. Le critère décisif n'est pas le profil mais **la donnée disponible** : chaque famille d'utilisateur expose des données différentes (publiques on-chain, APIs privées, flux de custody), et le produit doit être défini par ce qu'il peut réellement lire et faire.
> **Problème** : il ne se formule pas à partir du cas USDC, mais **comme celui de MIMIR — en version on-chain**. Transposition de travail (d'après MIMIR, design technique §2.1) :
> *« L'information on-chain et de marché est publique et abondante, mais ses effets voyagent à travers des chaînes d'acteurs, de variables, d'instruments et de régimes, sur plusieurs horizons. Trois familles d'approches dominent : les pipelines événement→transaction, la prévision isolée par actif, et les graphes de connaissance descriptifs. Le pari d'ORVYREN est qu'une modélisation intégrée et épistémiquement explicite — structure des événements, mécanismes causals, contexte temporel, transmission entre marchés et protocoles, régimes, scénarios — apporte une valeur prédictive et décisionnelle incrémentale par rapport à ces baselines fragmentées. »*
> **Recherche en cours** : `U1_banques_institutions.md`, `U2_defi_organisations.md`, `P1_probleme_financier.md` → les sections 01 et 02 ci-dessous seront réécrites à leur retour, avec sources et chiffres vérifiés.

---

## 01 — UTILISATEUR PRINCIPAL

### [PROPOSITION] Trois profils candidats, un principal recommandé

| | Profil | Douleur | Volume typique | Accès | Verdict |
|---|---|---|---|---|---|
| **P1** | **L'indépendant ou la petite structure rémunéré·e en stablecoins** (freelance, commerçant, diaspora, e-commerçant) qui thésaurise en USDC/USDT | Son capital dort sur une chaîne qu'il/elle ne peut pas surveiller en continu ; un dépeg ou une tension peut lui coûter des mois de revenus ; il/elle ne sait pas quoi faire quand ça bouge | 1 k – 100 k $ | On-chain natif, sans KYC lourd, accessible depuis n'importe où (Togo, Afrique de l'Ouest, marchés frontière) | **Recommandé** |
| **P2** | **La trésorerie crypto d'une organisation** (petite entreprise, ONG, collectif, DAO) | Besoin de contrôle, de rôles et de traçabilité en plus de la protection | 50 k – 5 M $ | On-chain natif | Fort, mais exige des fonctions organisationnelles (rôles, approbations) qui complexifient la première tranche |
| **P3** | **Le particulier crypto-natif averti** qui veut automatiser sa gestion | Veut du rendement et de l'automatisation, pas seulement de la protection | 5 k – 500 k $ | On-chain natif | Bon second profil, mais « veut du rendement » pousse vers la promesse la plus difficile à prouver |

**Qui possède les actifs** : **l'utilisateur** — ORVYREN agit **pour lui**, par **autorité déléguée et révocable** (permissions bornées). Le système ne collecte pas des fonds ; il gère une exposition qui reste la propriété de son détenteur.
**Qui bénéficie des décisions** : l'utilisateur (protection du capital, exécution, traçabilité). C'est aussi lui qui fixe les objectifs et les contraintes (plancher, horizon, tolérance).

### [À TRANCHER]
1. **Lequel des trois est LE principal ?** (le projet ne peut en porter qu'un à fond pour la première tranche ; les autres restent secondaires).
2. **L'utilisateur est-il supposé peu technique** (le système doit tout expliquer) ou averti (il peut lire un dossier de décision) ?

### RECHERCHES À LANCER
- **R1a** — 5 à 8 entretiens piliers avec le profil P1 : fréquence réelle des épisodes subis, montants, ce qu'ils ont fait (ou pas fait), quels outils ils utilisent aujourd'hui, ce qu'ils accepteraient de déléguer. *Livrable : grille d'entretien + synthèse ; critère : ≥ 3 incidents vécus documentés.*
- **R1b** — Comment les détenteurs de stablecoins en marchés frontière se protègent-ils aujourd'hui (p2p, échange manuel, multi-wallets) ? Sources publiques + rapports.

---

### [RÉSULTAT RECHERCHE U1 — Banques & institutions financières (15/10, 32 Ko, 43 sources)]

**Ce qui est vrai** : l'industrialisation est réelle et budgétée — garde institutionnelle (300+ banques chez Fireblocks), collatéral tokenisé (pilote DTCC/Digital Asset sur les *margin calls* ; DTC en production juillet 2026), jetons de dépôt (JPMD sur Base ; Kinexys > 7 Md$/jour), repo intraday (JPM/HQLAᵡ), pilote Agorá (BIS, CHF 800 k, mai 2026), 9 banques européennes + BNP sur un euro-stablecoin MiCA.

**Douleurs documentées** (nommées par les infrastructures elles-mêmes) : réconciliation et interventions manuelles · mobilité du collatéral et appels de marge · liquidité intraday · trésorerie « 24/7 » sans fenêtre d'arrêt · fragmentation multi-chaînes · risque stablecoin (échec des tests BIS *singleness/elasticity/integrity*) · surveillance continue de positions tokenisées.

**Le fait décisif — la donnée** : **les positions bancaires ne sont pas publiques** (Kinexys = registre privé permissionné ; conversions DTC sur Besu privé ; Canton = confidentialité sélective). Un agent qui ne lit que le public on-chain **est aveugle sur une grande partie du périmètre bancaire** : il doit s'intégrer aux **APIs de custody/ledger** (Fireblocks, Taurus, Canton, plateformes internes).

**Contraintes structurantes** : **DORA** — l'agent devient un **tiers TIC** à contractualiser, auditer et pouvoir couper (depuis 17/01/2025) · **EU AI Act art. 14** — supervision humaine effective, double vérification dans certaines catégories (obligations principales : 02/08/2026) · **Bâle/SCO60** (depuis 01/01/2026) · **MiCA** · **GENIUS Act** (blocage/sanctions de stablecoins).

**Jamais délégué** : la décision d'exposition et l'appétit au risque · la finalité juridique du règlement · les clés et la garde · la conformité AML/sanctions · l'élargissement du mandat.

**3 cas d'usage documentés** : **UC1** collatéral & appels de marge (dans des paniers préapprouvés) · **UC2** trésorerie stablecoin/jetons de dépôt multi-chaînes (fenêtres de règlement) · **UC3** veille on-chain & réaction de contrepartie (dépeg, gel, suspension → playbook défensif préapprouvé, sinon escalade).

**Verdict** : marché **crédible**, mais **pas un premier client pour un MVP 2026** → cible **phase 2 (2027-2028)**. Les workflows UC1-UC3 constituent le **meilleur gabarit de « bounded autonomy »** à montrer dans la soumission, en lisant les données publiques (explorers, Canton, dépôts tokenisés) — les banques restant la cible de déploiement ultérieure.

**Condition de crédibilité si/vu** : intégration aux APIs de custody · enveloppe bornée vérifiable (allowlists, plafonds, fenêtres, double validation au-delà d'un seuil, kill switch, journal exportable) · positionnement **opérations** (jamais « décision d'investissement ») · mode *shadow/propose* d'abord · entrée via un fournisseur d'infrastructure ou un sandbox régulateur.

---

## 02 — PROBLÈME FINANCIER PRÉCIS

### [PROPOSITION] La formulation

> **« Mon capital on-chain subit des événements de risque que je ne peux pas traiter en continu : mes outils savent m'alerter, aucun ne sait m'expliquer ni agir — et mes décisions ne laissent aucune trace défendable. »**

Décomposition :

| Élément | Contenu |
|---|---|
| **Déclencheur** | Un dépeg de stablecoin, une tension de liquidité, une panne de protocole ou de chaîne, une fenêtre d'opportunité brève, un changement de règle (frais, pause, réglementation) |
| **Coût du problème** | **Pertes évitables** (cas USDC mars 2023 : ne rien faire coûte jusqu'à −10 % au pire du décrochage ; agir dans la bonne fenêtre est quasi neutre en coût) · **décisions tardives** (on agit après la panique) · **temps** (surveiller 24/7 est impossible) · **absence de trace** (aucune décision n'est défendable après coup) |
| **Pourquoi les outils actuels ne suffisent pas** | Les **alertes** font du bruit sans explication (« le prix bouge » — mais pourquoi ? est-ce réel ?) · les **dashboards** montrent des données, pas des décisions · l'**humain** n'est pas 24/7 et panique · les **tableurs** ne croisent pas des sources contradictoires · les **bots de trading** sont opaques, non bornés, et ne produisent aucune preuve |
| **Pourquoi maintenant** | Les rails on-chain permettent une **exécution programmée bornée** (permissions, plafonds) : on peut enfin laisser un agent agir sans lui donner un pouvoir illimité. C'est exactement l'objet du topic F |

### [À TRANCHER]
- Le problème principal : **la protection** (éviter la perte) ou **la gestion** (faire travailler le capital) ? *Recommandation : la protection d'abord — c'est mesurable, honnête et le cas pilote existe déjà.*

### RECHERCHES À LANCER
- **R2a** — Documenter l'ampleur des épisodes : quels cas historiques exploitables avec données publiques réelles (USDC mars 2023 ; stETH juin 2022 ; autres à vérifier — attention : USDT 2018 et LUNA ont déjà été écartés faute de données), et quelles pertes documentées pour un détenteur passif.
- **R2b** — État de l'art des **alertes vs décisions** : pourquoi les outils existants s'arrêtent à l'alerte (étude de produits : Zapper, DeBank, Hypernative, Ranger…).

---

## 03 — DÉCISION À AMÉLIORER

### [PROPOSITION] Une décision, trois familles

**La décision principale** : *« Que faire de mon exposition, maintenant — ne rien changer, réduire, réallouer, ou exécuter — et avec quelle preuve ? »*

| Famille | Exemple concret | Aujourd'hui | Avec ORVYREN |
|---|---|---|---|
| **Protection** (événement de risque) | « USDC décroche, il est 7 h du matin, je dors » | On découvre trop tard ; on ne sait pas si c'est local ou réel | L'agent croise les sources, cherche le fait qui départage, borne la réponse et **exécute** dans son enveloppe ou refuse de conclure |
| **Placement** (allocation) | « Où garder 40 k$ : quel stablecoin, quelle chaîne, quel protocole, à quel risque ? » | Choix par habitude ou par rendement affiché | Évaluation qualité/risque des supports, décision tracée |
| **Exécution** | « Comment sortir 20 k$ sans slippage ni frais inutiles ? » | Manuel, au moment de la panique | Exécution bornée (taille, venue, découpage) et vérification du reçu |

**Ce que la décision doit devenir** : évaluée (pas réflexe), bornée (pas illimitée), traçable (recalculable). Ni « ne rien faire par défaut », ni « agir pour agir ».

### [À TRANCHER]
- **La première démo démontre quelle famille ?** *Recommandation : protection (elle contient déjà le cas USDC, la politique, le refus).*

### RECHERCHES À LANCER
- **R3a** — Que fait un bon trésorier/gestionnaire dans ces situations (littérature professionnelle, pratiques documentées) ? En tirer la **règle de décision de référence** (baseline) à battre.
- **R3b** — Définir la décision comme un objet mesurable : quelles entrées, quelles options admissibles, quel critère — pour que l'on puisse la **juger** (voir 05).

---

## 04 — PÉRIMÈTRE FINANCIER

### [PROPOSITION] On-chain d'abord, « protection-stablecoins » au centre

| Dimension | Phase 1 (le produit) | Extension (après) | Exclu volontairement |
|---|---|---|---|
| **Actifs** | Stablecoins (USDC, USDT, DAI) — cœur ; plus ETH et wBTC comme valeurs de sortie | Autres majors, LST | Levier/perps, alts illiquides, tokens exotiques |
| **Chaînes** | Base (choix concours) + Ethereum | Arbitrum, Polygon | Chaînes inconnues/non allowlistées |
| **Protocoles** | DEX majeurs (Uniswap), lending majeurs (Aave), ponts officiels — tous **allowlistés**, contrats vérifiés | Autres protocoles à mesure qu'ils passent le filtre | Tout protocole non vérifié, toute ferme de rendement |
| **Horizons** | Événement : minutes → heures · Position : jours → semaines · Allocation : mois | Multi-horizons plus fin | Trading haute fréquence |
| **Données** | Prix multi-venues (agrégateur + exchanges), offre en circulation, liquidité on-chain, communiqués datés, données de chaîne (soldes, reçus) | Preuves de réserves, données d'acteurs | Tout jeu sans horodatage admissible |
| **Cadre** | Testnet pour l'exécution démontrée ; **aucun fonds réel requis** par la conception | Comptes réels **seulement** si un utilisateur l'exige | Émission de jetons, promesse de rendement |

**Principe** : ORVYREN est un système **on-chain** (le topic l'exige). Les signaux macro (le monde de MIMIR) peuvent un jour l'informer, mais ne font pas partie de son périmètre d'action.

### [À TRANCHER]
- **Base seule ou Base + Ethereum dès la phase 1 ?** (Base simplifie ; Ethereum ouvre la profondeur de liquidité réelle).
- **Stablecoins seuls ou avec ETH/wBTC dès la phase 1 ?** (l'actif de sortie change la nature de la démo).

### RECHERCHES À LANCER
- **R4a** — État des lieux technique : liquidité réelle et coûts par chaîne/protocole, disponibilité des données on-chain, contraintes d'accès depuis la zone de l'utilisateur.
- **R4b** — Faisabilité des cas pilotes sur ces chaînes (les données historiques existent-elles, et à quelle granularité ?).

---

## 05 — RÉSULTAT MESURABLE

### [PROPOSITION] Quatre axes de preuve, du plus fort au plus faible

| Axe | Mesure | Comparateur | Statut d'honnêteté |
|---|---|---|---|
| **1. Économique — protéger** | **Perte évitée** / richesse nette sur épisodes gelés, nette des coûts, en regret vs l'ensemble des actions **faisables** | Ne rien faire (A0) · règle de seuil (A1) · agent (A2) · **placebo apparié** (B0) | Sur 1–2 épisodes : c'est une **mesure**, pas une preuve statistique — à écrire noir sur blanc |
| **2. Qualité de décision** | Calibration des prévisions (Brier/ECE quand l'échantillon suffit), taux d'INCONCLUSIVE corrects, contradictions détectées avant décision | Absence de ces mécanismes | Publier les effectifs, jamais une conclusion sur N insuffisant |
| **3. Opérationnel** | 0 opération hors politique (matrice d'attaques **nommée**), 100 % des décisions avec provenance recalculable, temps détection→décision, coût par décision | Politique absente / bot opaque | Bornes de Wilson publiées comme indicatives |
| **4. Utilisateur** | Un tiers retrouve plus vite motif, limites et donnée manquante dans le dossier que dans les logs bruts (temps, erreurs) | CSV + logs bruts | Tâches définies, pas d'enquête de satisfaction |

**La preuve la plus forte** : **paper trading en avant** (décisions publiées avant le résultat, puis vérifiées) — dès que le système tourne. C'est ce qui distingue une démo d'un produit.

### [À TRANCHER]
- **Le critère principal** : je recommande **« perte évitée nette, mesurée sur épisodes + forward »**. Alternative : « richesse nette » (plus ambitieux, plus fragile sur un seul épisode).

### RECHERCHES À LANCER
- **R5a** — Concevoir le **benchmark honnête** : fixtures gelées, comparateurs, placebo, règles anti-optimisme (développement/évaluation séparés), et le dispositif de paper trading forward.
- **R5b** — Définir la **fonction de perte** du propriétaire (protéger un plancher ? éviter un drawdown ? gagner sur 12 mois ?) — décision de valeur, à écrire et geler.

---

## 06 — MODÈLE D'AUTONOMIE

### [CONCEPTION PROPOSÉE] Cinq niveaux, une enveloppe, des verrous

| Niveau | Capacité | Qui signe | Statut |
|---|---|---|---|
| **T0 — Observer** | Lecture continue, analyse, alertes, dossier de situation | personne | **Toujours actif** |
| **T1 — Proposer** | Intentions structurées, simulations, scénarios — rien n'est exécuté | personne | Toujours actif |
| **T2 — Exécuter borné** | **L'agent exécute seul dans son enveloppe** : plafonds par transaction et par période, allowlist d'actifs/contrats/fonctions/destinataires, expiration, identifiant d'idempotence, pause d'urgence | **le système** (signer limité) | **C'est le niveau que le topic exige** — cœur de la démo |
| **T3 — Étendre** | Toute action hors enveloppe : préparée, jamais exécutée seule | humain (approbation) | Par construction |
| **T4 — Gouverner** | Politique, plafonds, clés, allowlists : **l'agent ne peut jamais élargir ses propres droits** ni choisir librement un contrat ou un réseau | humain uniquement | Interdit à l'agent pour toujours |

**Les verrous (indépendants du modèle)** : la politique est déterministe et **hors LLM** ; le LLM ne détient jamais de clé ; l'exécution n'accepte qu'une intention **déjà autorisée** ; le reçu est vérifié et comparé à l'intention (contrat, émetteur, destinataire, montant exact) ; un **double verrou on-chain** (permissions bornées type ERC-7715 quand disponibles) peut s'ajouter au verrou logiciel ; journal opposable et arrêt d'urgence (kill switch) à tous les niveaux.

### [À TRANCHER]
- **L'enveloppe T2 de la première démo** : montants, actifs, destinataires, durée — l'exemple actuel (100 par transfert, 300 par période, 24 h) est une proposition, pas un acquis.
- **Le double verrou on-chain fait-il partie de la phase 1** ou vient-il après le premier parcours complet ?

### RECHERCHES À LANCER
- **R6a** — État réel des permissions on-chain (ERC-7715/7710, session keys, spend permissions) : ce qui est déployé, audité, utilisable en testnet, et ses limites exactes (plafond par transaction, frontières de période, révocation).
- **R6b** — Concevoir le **signer limité** : architecture (clé isolée, quotas, politique embarquée, procédure d'arrêt) et la matrice d'attaques associée (12 attaques nommées, résultat en couverture).
- **R6c** — Cadre de responsabilité de l'exécution autonome (limites légales, journal opposable, ce qu'on peut écrire dans le dossier du concours sans surpromettre).

---

## FUSION — ce que ce cadre absorbe, et ce qu'il abandonne

**Absorbé** :
- La **vision canonique** (comprendre → anticiper → décider → exécuter → apprendre) devient la colonne vertébrale.
- La **boucle du V0.2 §4.1** (observer → … → exécuter ou refuser → vérifier → réviser) est le fonctionnement de référence.
- Les **rôles du V0.2 §8** (orchestrateur, explorateur, critique, décideur) = les agents ; le **graphe factuel** = leur mémoire partagée (sémantique MIMIR, projet distinct).
- La **politique + exécuteur à signer limité (§10)** corrige mon erreur : l'autonomie d'exécution est **dans** le projet.
- Les **recherches R1–R3** alimentent 05 et 06 (mesure, autonomie) ; les **revues Astra** ont corrigé les formulations ; les **invariants** (PIT, autorisation, intégrité, comptabilité, dépendance des sources) restent des portes obligatoires.

**Abandonné** :
- L'exécution par un humain (contraire au topic) → remplacée par T2 + signer limité.
- La contrainte de deadline appliquée au code (le prototype a pris 30 minutes ; la deadline ne garde que les dépendances externes : KYC, comptes, réponses des organisateurs).
- La réduction du projet à mon prototype : il devient la **tranche politique+provenance**, une brique.
- La prémisse « ORVYREN brique de MIMIR » (elles sont séparées).

---

## LANCEMENT DES RECHERCHES — ordre recommandé

1. **R1a/R1b** (utilisateur) — conditionne tout le reste. *Sans utilisateur confirmé, 02–03 restent des hypothèses.*
2. **R2a** (épisodes et données) — vérifie que la douleur est documentable et mesurable.
3. **R5b** (fonction de perte) — décision de valeur à geler avant toute mesure.
4. **R6a/R6b** (autonomie et sécurité) — conditionne la démo et les 30 % du concours.
5. **R4a/R4b** (périmètre technique) — pendant que 1–4 avancent.
6. **R3a/R5a** (décision de référence et benchmark) — dès que la fonction de perte est gelée.

**Les questions restées ouvertes de mon message précédent** (§3 : wallet de qui, rentabilité, multi-agents, temps réel, ponts MIMIR) n'ont pas besoin d'être tranchées pour lancer R1–R2 — elles le seront par les sections 01–06 elles-mêmes.
