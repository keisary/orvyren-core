# ORVYREN — COMPRENDRE TOUT, SIMPLEMENT
## Guide complet du système, des décisions et de ce qui reste à trancher

**15 octobre 2026.** Ce document explique l'ensemble : ce qu'est ORVYREN, comment il fonctionne, ce qui existe vraiment, **toutes les décisions prises** (par qui, pourquoi, statut), et **les points sur lesquels on peut légitimement être en désaccord**. Il est écrit pour être lu sans jargon.

---

# PARTIE 1 — LE SYSTÈME, EN CLAIR

## 1.1 Le problème

Quand un actif financier vacille (un stablecoin qui perd son ancrage de 1,00 $, une banque qui fait faillite), trois choses arrivent en même temps :
1. **Les chiffres se contredisent** — le même USDC valait 0,805 sur Bitstamp, 0,863 sur l'agrégat, 0,913 sur Binance, à quelques heures d'écart, en mars 2023 ;
2. **Personne ne sait pourquoi** — simple trou de liquidité local ? vraie crise de l'émetteur ? erreur de données ?
3. **Il faut décider vite, avec de l'argent réel** — et après coup, personne ne peut expliquer *pourquoi* la décision a été prise.

Les entreprises et les banques ont des tableurs et des logiciels de trésorerie. Ce qu'elles n'ont pas : un système qui **cherche activement la vérité**, dit **« je ne sais pas »** quand il ne peut pas conclure, et **laisse une trace qu'un tiers peut recalculer**.

## 1.2 Ce qu'ORVYREN est (et n'est pas)

**C'est** : un agent qui transforme un signal de risque en **décision financière bornée et vérifiable** — il croise les sources, formule les explications possibles, cherche le fait qui les départage, calcule la décision, la fait passer par des verrous, et archive tout.

**Ce n'est pas** : un chatbot qui commente des graphiques · un robot de trading qui promet des gains · un système qui a accès à votre argent (il n'a **jamais** de clé).

## 1.3 Comment il fonctionne — le cycle, étape par étape

**Exemple réel qui traverse tout le document : le week-end SVB, mars 2023.**

| # | Étape | Ce qui se passe | Avec l'exemple USDC |
|---|---|---|---|
| 1 | **Observer** | On lit plusieurs sources indépendantes : agrégateur de prix, deux exchanges, offre en circulation, chaîne, communiqués | 520 observations archivées, horodatées, avec leur source |
| 2 | **Vérifier les données** | Units, doublons, trous de couverture. Une donnée manquante est **déclarée manquante**, jamais inventée | Couverture mesurée par heure et par source (Binance 83 h, Bitstamp 145 h sur 145) |
| 3 | **Détecter un épisode** | Un écart dépasse un seuil → le système ouvre un raisonnement | Bitstamp décroche à 0,8627 le 11/03 à 07 h |
| 4 | **Poser les hypothèses concurrentes** | Plusieurs explications possibles, chacune avec un critère de réfutation **écrit d'avance** | H1 = trou de liquidité local · H2 = vraie crise · H3 = erreur de données |
| 5 | **Chercher le fait qui tranche** | Quel fait départagerait H1 de H2 ? Le système va le chercher (dans ce cas : l'offre en circulation) | L'offre chute de 7,17 % en 24 h → **H2 soutenue**, H1 réfutée, H3 réfutée |
| 6 | **Décider** | Si la preuve suffit : quelle action, quel montant ? Sinon : **INCONCLUSIVE avec la liste de ce qui manque** | ACTION_RECOMMENDED : transférer 100 USDC de test (montant calculé : `min(100, exposition − plancher)`) |
| 7 | **Passer les verrous** | Une politique **déterministe, hors IA**, vérifie la demande : bonne chaîne ? actif autorisé ? destinataire connu ? ≤ 100 par transaction ? ≤ 300 cumulés ? permission valide ? pas déjà exécutée ? | ALLOW pour 100 USDC · DENY si 500 · REQUIRE_APPROVAL si changement de règle |
| 8 | **Exécuter** | L'agent prépare l'**instruction non signée** (le calldata exact). **Un humain l'exécute** dans son wallet — l'agent n'a pas de clé | Calldata prêt : `0xa9059cbb…` + destinataire + 100 000 000 (100 USDC en unités de base) |
| 9 | **Vérifier** | L'agent lit le reçu sur la chaîne et vérifie que **ce qui s'est passé = ce qui était autorisé** (contrat, émetteur, destinataire, montant exact) | Vérificateur prêt ; en attente du premier vrai transfert humain |
| 10 | **Archiver et apprendre** | Dossier d'une page avec les empreintes (sha256) de chaque pièce ; quand les prévisions deviennent vérifiables, on les score | Dossier + journal d'intégrité ; calibration encore à faire |

**La règle d'or** : aucun calcul financier ne vient d'un modèle de langage. L'IA propose des structures ; des fonctions déterministes calculent, vérifient et refusent.

---

# PARTIE 2 — CE QUI EXISTE VRAIMENT (ET CE QUI N'EXISTE PAS)

## 2.1 Existe, testé, exécuté (147 tests verts)

- **Corpus** : 520 observations, 5 séries, fenêtre de crise (9–15 mars) + fenêtre témoin (15–18 février), manifeste de provenance, mode hors-ligne.
- **Politique** : verdict ALLOW / DENY / REQUIRE_APPROVAL, 8 règles, **7 attaques pré-déclarées** testées (+ plus tard : NaN, valeurs infinies, cumul invalide).
- **Moteur de décision** : H1/H2/H3 pré-enregistrées, règle de décision gelée, baseline A0 (la règle simple qu'il faut battre), chemin INCONCLUSIVE prouvé.
- **Données + graphe de preuve** : normalisation, couverture, base SQLite **en ajout seul** (12 déclencheurs refusent modification/suppression), vérification de la chaîne de provenance.
- **Exécution** : instruction non signée (calldata ERC-20 exact), vérification de reçu (contrat, émetteur, destinataire, montant, statut), garde qui bloque tout sauf ALLOW.
- **Audit** : dossier d'une page (Markdown + HTML autonome) avec sha256 de chaque entrée et un auto-hash recalculable.
- **Orchestrateur** : `run_pipeline.py` enchaîne tout et **échoue bruyamment** ; la démo a été vérifiée depuis une extraction à froid du paquet.

## 2.2 N'existe pas encore (le travail réel)

- **Aucun agent** : pas de boucle « planifier → appeler un outil → évaluer → s'arrêter ». Aujourd'hui c'est un pipeline qui s'exécute, pas un agent qui cherche.
- **Aucun registre de branches** : les hypothèses sont trois blocs figés, pas des objets vivants qu'on explore, qu'on fusionne, qu'on abandonne.
- **Aucun calcul de valeur de l'information** : on cherche « un fait discriminant », sans calculer si ça valait son coût.
- **Aucune calibration** : on ne mesure pas encore si nos probabilités sont justes.
- **Portefeuille en valeurs de démonstration** : exposition 500 / plancher 350 / action 100 — des chiffres d'exemple.
- **Pas de permission on-chain réelle** : l'humain exécute, la chaîne ne borne rien.

---

# PARTIE 3 — LA CARTE DES DÉCISIONS

Trois statuts : **[FIGÉ]** décidé, on n'y revient qu'avec une raison forte · **[À DÉBATTRE]** contestable, c'est ici que ton désaccord compte · **[REPORTÉ]** prévu, pas maintenant.

| # | Décision | Qui / statut | Pourquoi (une ligne) |
|---|---|---|---|
| 1 | Candidater au **thème F** (Agent Wallet), abandonner le thème E | Équipe — **[FIGÉ]** | Thème signature du concours, bonus 0–5 ; un seul thème par équipe |
| 2 | **Cas pilote : décrochage USDC / SVB mars 2023** | Équipe — **[FIGÉ]** | Données publiques réelles, trois sources divergentes mesurables |
| 3 | **Positionnement** : « producteur de décisions vérifiables », pas « portier de l'exécution » | Équipe — **[FIGÉ]** | L'exécution est commoditisée (ERC-8273, x402…) ; la décision tracée, non |
| 4 | **L'agent ne détient aucune clé** ; l'humain exécute, l'agent vérifie le reçu | Équipe — **[FIGÉ]** | Zéro risque de manipulation de fonds ; l'autorité limitée est le produit |
| 5 | **Réseau** : Base Sepolia (testnet), USDC de test, 100 par transaction | Équipe — **[FIGÉ]** | Aucun fonds réel ; conformité (sensibilité crypto en Chine) |
| 6 | **Politique déterministe hors LLM** (8 règles) | Équipe — **[FIGÉ]** | Un modèle ne doit jamais pouvoir contourner un verrou |
| 7 | **Pré-enregistrement** : hypothèses et seuils gelés avant de regarder les résultats | Équipe — **[FIGÉ]** | Sinon l'évaluation ne vaut rien |
| 8 | **Bibliothèque standard uniquement, rejeu hors-ligne obligatoire** | Équipe — **[FIGÉ]** | Démo impossible à casser par une panne réseau |
| 9 | **DFKG partiel adapté** (pas l'ontologie MIMIR complète) | Astra-2 — **[À DÉBATTRE]** | Seul le sous-ensemble utile au cas est instancié ; MIMIR reste la référence |
| 10 | **Branches qualitatives d'abord**, probabilités seulement gelées et calibrées | Astra-2 — **[À DÉBATTRE]** | Une probabilité inventée dégrade la preuve |
| 11 | **VoI derrière une interface**, avec repli déterministe | Astra-2 — **[À DÉBATTRE]** | La valeur de l'information reste à établir ; elle ne doit pas être un point de rupture |
| 12 | **Quatre familles de relations** séparées (preuve / structure / mécanisme / contrainte) | Astra-2 — **[À DÉBATTRE]** | `SUPPORTS` (preuve) ≠ relation causale (mécanisme) |
| 13 | **Trois sorties séparées** : épistémique / économique / autorisation | Astra-2 — **[À DÉBATTRE]** | « Je ne sais pas » ≠ « ne rien faire » ≠ « interdit » |
| 14 | **Cinq invariants** : PIT, autorisation, intégrité, comptabilité, dépendance des sources | Astra-2 — **[À DÉBATTRE]** | Ce sont les règles qui tiennent même quand tout le reste change |
| 15 | **La démo D8 teste la chaîne de contrôle, pas une couverture** | Astra-2 — **[À DÉBATTRE]** (honnêteté imposée) | Transférer l'USDC entre deux wallets de la même entité ne réduit pas le risque émetteur |
| 16 | **Hypothèses** : 3 sortent du registre (1 convertie en exigence, 1 éliminée, 1 fusionnée) | Astra-2 — **[À DÉBATTRE]** | Voir partie 4 : c'est le débat le plus concret |
| 17 | **Premier lot d'essais** T10 → T12 → T03 → T02 (13–19 h) | Astra-2 — **[À DÉBATTRE]** | Commencer par la reconstructibilité et l'abstention, pas par la VoI |
| 18 | **Pas de migration de stockage / modèle probabiliste / délégation on-chain avant le concours** | Astra-2 — **[FIGÉ sauf objection]**, tendance | Trois façons classiques de casser une démo à 5 jours de la fin |
| 19 | **Aucune supériorité statistique revendiquée** (petit échantillon assumé) | Astra-2 + R3 — **[À DÉBATTRE]** | 1 crise ne prouve rien ; on démontre la faisabilité de la mesure |
| 20 | **Livrables** : doc technique EN, vidéo ≤ 5 min, deck ≤ 10 min, wallet financé, rapport sécurité | Équipe — **[FIGÉ]** | Exigences du concours |

---

# PARTIE 4 — LES POINTS RÉELLEMENT CONTESTABLES

C'est ici que ton désaccord est utile. Pour chaque point : le débat, les deux camps, et **ce qui le trancherait**.

### D9 — Faut-il adopter un DFKG partiel, ou aller plus loin avec MIMIR ?
- **Camp « partiel »** (Astra) : seuls les schémas temporels, les liens de preuve et les relations curatées servent le cas USDC. Importer l'ontologie complète (FOMC, macro) serait de la décoration.
- **Camp « plus MIMIR »** (toi) : c'est le socle du projet, ses définitions et types de relation sont ce qui donne sa profondeur au graphe.
- **Ce qui trancherait** : HYP-01R. Si la projection relationnelle + le raisonnement par relations apportent un gain mesurable (temps de diagnostic, défauts détectés) à données égales, on élargit. Sinon, on reste au socle minimal. **Coût de l'essai : 2–4 jours.**

### D10 — Branches qualitatives ou probabilisées ?
- **Camp « qualitatif »** (Astra) : sans calibration, une probabilité est une invention.
- **Camp « probabilisé »** (la VoI en a besoin pour calculer une valeur).
- **Ce qui trancherait** : on peut faire les deux **en séquence** — qualitatif maintenant, probabilités quand les prévisions seront gelées et scorées (HYP-06R). Ce n'est pas un vrai dilemme.

### D11 — La valeur de l'information : investir ou pas ?
- **Camp « après »** (Astra) : la VoI est le dernier ajout ; elle n'est pas prouvée ; T02 est reportable.
- **Camp « c'est notre différenciation »** (position initiale de notre recherche) : la littérature 2026 en fait la règle des agents bays-consistants.
- **Ce qui trancherait** : T02, le petit monde synthétique à 3 outils — c'est un test de mécanique, pas d'utilité financière. S'il passe, on garde ; sinon, on documente l'abandon (c'est aussi un résultat).

### D15/D8 — La démo on-chain : que démontre-t-elle vraiment ?
- **Le vrai débat** : transférer de l'USDC d'un wallet à un autre de la même entité **ne réduit pas** l'exposition au risque émetteur. Astra a raison, et l'écrire honnêtement est plus fort que de le masquer.
- **Options** : (a) assurer que trésorerie et réserve ont des **propriétaires/contreparties distincts** dans la fiction de la démo ; (b) présenter la démo comme un **test de la chaîne de contrôle** (politique → instruction → reçu) ; (c) simuler en plus une **cession** (vente) en paper trading (HYP-09R).
- **Ce qui trancherait** : laquelle des trois raconte la meilleure histoire **vraie**. Mon avis : (b) + (c).

### D16 — Le registre d'hypothèses : ces suppressions sont-elles justes ?
- **HYP-04 → exigence** : la tester serait tautologique (si la règle interdit d'agir, observer plus d'abstentions ne prouve rien). Si tu veux la garder comme hypothèse empirique, il faut un design humain distinct → coûteux, hors délai.
- **HYP-09 éliminée** : conséquence directe de D8/D15. Si tu choisis une cession simulée, une **nouvelle** hypothèse la remplace.
- **HYP-14 fusionnée** avec HYP-07, **HYP-15 reformulée** (comparer à « rien » et « un saut », pas à une propagation libre qui est un mauvais témoin).
- **Ce qui trancherait** : ton avis sur chaque hypothèse — garder/éliminer est une décision de valeur, pas de fait.

### D19 — « Aucune supériorité statistique revendiquée » : assez ambitieux pour un jury ?
- **Camp « honnête »** (Astra + R3) : avec 1 crise, toute revendication de performance serait fragile.
- **Risque** : un jury peut préférer une ambition forte. Contre-argument : nous revendiquons la **reconstructibilité**, la **sécurité** et la **faisabilité de la mesure** — c'est vérifiable, donc plus fort.
- **Ce qui trancherait** : ajouter **un 2e cas** (UST mai 2022 ou stETH juin 2022 — à vérifier : les données manquent peut-être) donnerait 2 points, pas une statistique. Décision produit.

### D17 — Le premier lot d'essais : est-ce le bon ordre ?
- **Ordre retenu** : T10 (reconstructibilité) → T12 (abstention) → T03 (branches) → T02 (VoI).
- **Alternative** : commencer par les branches + VoI (le « cœur »), parce que c'est ce qui impressionne.
- **Ce qui trancherait** : la règle « la sûreté avant la recherche supplémentaire ». Si le temps manque, **T10 et T12 sont non négociables** — ce sont eux qui protègent les 30 % de la note « sécurité ».

### D9bis — Et la question la plus stratégique : ORVYREN vs MIMIR
- Aujourd'hui, ORVYREN **réutilise** le socle conceptuel de MIMIR (graphe, provenance, relations, labels). La question ouverte : ORVYREN devient-il **une brique de MIMIR** (le module « décision de risque » du système macro-financier), ou reste-t-il autonome ?
- **Conséquence pratique** : si ORVYREN devient une brique de MIMIR, l'architecture cible, le vocabulaire et les identifiants doivent s'aligner complètement (et le pitching change : « le premier module de décision vérifiable pour le DFKG »).

---

# PARTIE 5 — COMMENT ON RÉVISE (la méthode)

Pour chaque décision contestée, on applique la même procédure — courte et honnête :

1. **Tu énonces ton désaccord** (et si possible l'alternative que tu préfères).
2. Je réponds par écrit à quatre questions : **qu'est-ce qui dépend de cette décision ?** · **qu'est-ce que ça coûte de changer ?** · **qu'est-ce qui est vérifiable ?** · **quelle preuve nous ferait changer d'avis ?**
3. Si c'est vérifiable : on écrit un essai (critère de succès fixé **avant**), on l'exécute, on publie le résultat — y compris s'il nous contredit.
4. Si c'est une décision de valeur (pas un fait) : tu tranches, et on l'écrit dans le gel avec sa date et sa raison.
5. Toute révision est **datée et versionnée** — jamais une réécriture silencieuse.

**Les questions de recherche à pousser si on rouvre un débat** : DFKG × ML sans perte de traçabilité ; données publiques sur les acteurs bancaires ; mesure honnête du regret de cession ; robustesse de la VoI sous incertitude du modèle ; littérature sur l'abstention en finance ; quels 2e/3e cas historiques sont réellement exploitables.

---

# ANNEXE — MINI-GLOSSAIRE

| Terme | En clair |
|---|---|
| **DFKG** | « Graphe de connaissance financier dynamique » : une base qui stocke des faits, événements et relations **avec leur source et leur date** |
| **Pré-enregistrement** | Écrire les critères de réussite/échec **avant** de faire l'expérience, pour ne pas tricher après coup |
| **VoI / EVPI / EVSI** | « Valeur de l'information » : combien vaut le fait d'aller chercher une donnée, comparé à son coût |
| **Baseline A0** | La règle simple (seuil fixe) que le système doit battre — l'adversaire du projet |
| **INCONCLUSIVE** | Verdict honnête : « les données ne permettent pas de conclure, voici ce qui manque » |
| **INV-PIT** | « Point-in-time » : à l'instant simulé, n'utiliser que ce qui était **public** à cet instant |
| **Brier / ECE** | Scores qui mesurent si des probabilités annoncées sont justes |
| **Regret** | Écart entre la décision prise et la meilleure décision possible **parmi celles qui étaient faisables** |
| **Wilson (borne)** | Intervalle de confiance sur un taux observé — « 0 échec sur 12 » est compatible avec un vrai taux de 24 % |
| **Politique (service)** | Le verrou déterministe qui rend ALLOW / DENY / REQUIRE_APPROVAL |
| **Mandat (ERC-7715)** | Permission bornée qu'un wallet donne à un agent (montant, période, destinataire) — appliquée **par la chaîne** |
