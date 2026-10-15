# ORVYREN — REVUE CROISÉE ET CADRE CONCRET

**Version 1 — 15 octobre 2026.** Synthèse de la revue Astra-2 (« architecture cible et ordre de construction »), de nos propositions (AXES v3, R1 orchestration/VOI, R2 permissions on-chain, R3 évaluation) et des corrections vérifiées. **Ce document fixe la direction, le cadre et le premier lot de travail.**

---

## 0. Ce que ce document tranche

1. **Ce qu'on construit** : un **monolithe modulaire** autour d'un **registre de preuves temporelles**, puis une **petite boucle de recherche bornée**. Un **DFKG partiel et adapté** — pas l'ontologie MIMIR entière.
2. **Ce qu'on ne fait pas avant le concours** : migration de stockage, modèle probabiliste improvisé, délégation on-chain ajoutée à la dernière minute.
3. **Le chemin utile d'ici le 20/10** : règles explicites → données admissibles → calculs traçables → branches révisables → décision → autorisation persistante → instruction humaine → reçu. Une petite boucle discriminante peut le compléter.
4. **La valeur revendiquée** : une décision **reconstructible** et une **autorité limitée**. La valeur prédictive du graphe, du ML et de la VoI **reste à établir** — nous ne la revendiquons pas.
5. **Le registre d'hypothèses passe de 15 à 13** : 3 sortent (1 convertie en exigence, 1 éliminée, 1 fusionnée, 1 reformulée), 2 entrent (dépendance de sources, utilisateur trésorier).
6. **Premier lot d'essais** : T10 → T12 → T03 → T02 (13–19 h), avec repli documenté si la capacité manque.

---

## 1. Verdict sur la revue Astra-2 : ce qu'on vérifie, ce qu'on adopte

Nous avons testé ses critiques les plus dures. **Toutes celles qui étaient vérifiables sont exactes.**

### 1.1 Adopté — corrections à porter dans nos documents

| # | Critique d'Astra | Vérification | Correction à porter |
|---|---|---|---|
| C1 | AXES §1.3 : « chaque objet porte six temps » est faux — MIMIR §10.5 porte les six horloges **sur les objets qui les définissent** | Lecture du doc technique MIMIR : confirmation | Reformuler AXES §1.3 ; ne jamais remplir six colonnes avec des dates inventées |
| C2 | AXES §1.5 confond **relation de preuve** (`SUPPORTS` observation→hypothèse) et **relation causale** (mécanisme économique) — « un graphe de preuves n'établit pas un mécanisme économique » | Lecture MIMIR §11.2 vs notre §1.5 : confirmation | Séparer les familles de relations (§2.3 ci-dessous) |
| C3 | R1 : ALLOW/DENY/REQUIRE_APPROVAL sont des **verdicts d'autorisation**, pas les actions économiques dont on optimise l'utilité | Exact — notre pseudo-code mélangeait les deux boucles | Séparer boucle économique et boucle d'autorisation (§2.4) |
| C4 | R1 : H1/H2/H3 **ne forment pas une partition** (stress réel et artefact peuvent coexister) — normaliser à somme = 1 impose une exclusivité fausse | Exact | Branches **qualitatives d'abord** ; toute probabilité est gelée, mise à jour par observation, jamais un catset forcé |
| C5 | R1 : `c_s + lat_s` additionne des unités incompatibles ; `argmax VoI` sous contrainte `VoI > c` ≠ `argmax (VoI − c)` ; la log-loss d'une issue inconnue n'est pas observable au prochain appel | Exact | Coûts séparés (argent / secondes) ; critère `Net = EVSI − coût_total` ; fiabilité mise à jour **seulement** quand l'issue prévue devient disponible |
| C6 | R2 : un bytecode non vide n'établit ni hash attendu, ni paramètres, ni sûreté d'intégration ; deux adresses Safe vides ne prouvent pas l'absence de tout déploiement Safe | Exact (nos propres réserves R2 §0/§8 le disaient déjà) | Retirer les raccourcis de garantie ; dire « contrat présent avec code à un bloc donné », rien de plus |
| C7 | R2 : utiliser **l'intersection** des contraintes locales et accordées ; une permission plus large ne doit **jamais** élargir la politique ; une clé déléguée a une autorité même sans solde | Exact | Politique = `policy_local ∧ policy_granted` ; supprimer l'argument « clé sans valeur intrinsèque » |
| C8 | R3 M1 : la formule de regret **double-compte** le drawdown évité — exemple E=100, action à 1, minimum 0,9 : écart affiché 20, richesse réelle 10 | **Recalculé à la main : exact.** `L(NO-ACTION)=10`, `L(RÉDUIRE)=−10`, écart 20 — alors que vendre à 1 vs garder jusqu'à 0,9 change la richesse de 10 | Remplacer M1 par la **formulation richesse + actions faisables** (§2.5) |
| C9 | R3 M2 : REL parfait pour une prévision constante à 0,5 est faux sauf si la fréquence observée vaut 0,5 ; 5 prévisions permettent 5 carrés, pas une conclusion de calibration | Exact | Garder le seuil, ajouter « NON CALCULÉ — N insuffisant », publier effectifs et taux de base |
| C10 | R3 : Wilson sur 12 attaques choisies n'est pas une garantie opérationnelle ; « 93 fenêtres » dimensionne deux proportions indépendantes, pas un test apparié | **Recalculé** : Wilson 0/6 = 39,0 % ; 0/12 = 24,3 % ; McNemar exact 6–0 = 0,03125 | Publier la **matrice de couverture** des attaques ; dire « borne indicative », pas garantie ; McNemar exact sur discordances |
| C11 | R3 B0 : 200 tirages dans la même fenêtre = réalisations d'un placebo conditionnel, pas 200 crises | Exact | Apparier taille, durée, budget, liquidité, dates admissibles |
| C12 | La fermeture d'endpoints DeFiLlama `/pools` et `/chart/{pool}` **n'établit pas** la fermeture des endpoints prix/offre du collecteur ; OTel ≠ conformité d'archivage réglementaire (journal métier ≠ traces d'observabilité) | Exact — nous avions glissé des conclusions en avant | Retirer l'« alerte migration » ; requalifier l'axe D (audit) : conformité **non revendiquée** |

### 1.2 Adopté avec nuance

- **« 50/100 en l'état, 70–75 atteignable »** : nous le prenons comme **objectif de travail**, pas comme mesure. Seule une évaluation avec le protocole de R3 corrigé pourra le dire.
- **HYP-05 hors du premier lot** : d'accord — sans chemin de permission déjà intégré, sa faisabilité est inférieure à sa valeur démonstrative. On garde pour le concours la **démonstration minimale** (un refus par la politique, un refus par la chaîne si l'octroi est prêt).
- **Branches qualitatives avant probabilités validées** : adopté. Une probabilité inventée dégraderait la preuve plus qu'elle n'aiderait.

### 1.3 Rien de contesté sur le fond

Aucune critique vérifiable d'Astra-2 ne s'est révélée fausse. Nous gardons uniquement deux positions propres : (i) la règle de dépendance d'ARCHITECTURE_V1 reste un garde-fou de conception, **assouplie** pour laisser la boucle recherche→preuves remonter via l'orchestrateur ; (ii) nous continuons d'exiger la **réciprocité** : toute affirmation de nos documents porte son label épistémique.

---

## 2. Le cadre concret retenu

### 2.1 Choix structurants (architecture)

| Choix | Justification | Alternative rejetée |
|---|---|---|
| **Monolithe Python modulaire**, CLI canonique, **worker unique**, UI en lecture seule | Rejeu et inspection faciles | Microservices/broker : aucun besoin mesuré |
| **Signataire = frontière externe** au monolithe | Sécurité par construction | Clé confiée au moteur |
| **DFKG partiel adapté** : schémas temporels, liens de preuve, relations curatées | Fidèle au T0 étroit de MIMIR et au SQLite existant | Importer l'ontologie complète (FOMC, macro) sur un pilote USDC |
| **SQLite transactionnel + archives de contenu immuables ; JSON pour les échanges** | Atomicité locale (jobs, branches, budgets) sans base graphe | Postgres maintenant (plus tard si multi-utilisateur) ; JSON seul pour les réservations |
| **Fonctions pures dans le domaine + orchestrateur explicite** | Permet le retour des recherches vers la connaissance sans cycle d'imports | Chaîne d'imports linéaire rigide |
| **Branches qualitatives d'abord**, probabilités seulement gelées et calibrées | Évite les distributions inventées | Convertir H1/H2/H3 ou une confiance LLM en distribution |
| **VoI derrière une interface**, repli déterministe (ordre fixe borné), `VOI_NOT_ESTIMABLE` autorisé | La VoI est un ajout, pas une dépendance vitale | Dépendre d'un estimateur de VoI non calibré |
| **Calculs financiers versionnés**, positions consolidées, simulateur séparé | Sépare l'économie des preuves techniques testnet | Donner un « P&L de protection » à un transfert interne |
| **Politique persistante** puis adaptateur de mandat, **signature humaine conservée** dans la première cible | Double verrou, responsabilités explicites | Déléguer une clé au moteur avant maturité |

### 2.2 Les trois axes de sortie (jamais interchangeables)

| Axe | Valeurs | Signification |
|---|---|---|
| `epistemic_verdict` | CONCLUANT / INCONCLUSIVE | Ce que les preuves permettent de dire — l'ignorance est un résultat |
| `economic_action` | CONSERVER / TRANSFÉRER / CÉDER *(simulation)* / ATTENDRE-ESCALADER | Ce qu'il est économiquement raisonnable de faire |
| `authorization_verdict` | ALLOW / DENY / REQUIRE_APPROVAL | Ce que la politique permet — indépendant des deux autres |

`INCONCLUSIVE` n'est pas `NO_ACTION` : attendre conserve souvent un risque existant. « Aucune nouvelle transaction » ≠ « aucun risque ».

### 2.3 Quatre familles de relations (séparation sens / preuve / autorité)

| Famille | Prédicats | Champs propres | Interdit |
|---|---|---|---|
| **Preuve et dérivation** | DERIVED_FROM, EXTRACTED_FROM, SUPPORTS, CONTRADICTS, SUPERSEDES | révision source, passage, recette, portée exacte | **SUPPORTS n'autorise aucune propagation causale** |
| **Structure et exposition** | ISSUED_BY, CUSTODIED_AT, HOLDS, OWES, REDEEMABLE_VIA | entités, unité, montant, date d'effet, date de connaissance | « absence de publication » ≠ « exposition nulle » |
| **Mécanisme économique** | AFFECTS (mécanisme : LIQUIDITY, REDEMPTION, FUNDING…) | cause, effet, conditions, signe, horizon, statut épistémique, provenance | une corrélation porte un statut **statistique**, pas causal |
| **Contrainte / permission** | CONSTRAINS, AUTHORIZES, REVOKES | autorité émettrice, sujet, périmètre, instrument, dates, version, preuve d'octroi | texte réglementaire informatif ≠ règle exécutable validée |

`epistemic_status`, `lifecycle` et `validation_status` restent **trois attributs séparés** (une relation ACTIVE peut rester hypothétique). Appui sémantique : W3C PROV-O (recommandation 2013), sans obligation d'importer RDF.

### 2.4 Les invariants (portes obligatoires, indépendantes des expériences)

| Invariant | Règle |
|---|---|
| **INV-PIT** | Modifier le futur, ou une révision publiée après `as_of`, ne change pas une décision passée ; une donnée sans horodatage admissible est inutilisable dans un test PIT |
| **INV-AUTH** | Redémarrage, concurrence, expiration et rejeu ne recréent pas de budget ; politique et intention exactes sont liées au reçu |
| **INV-INTEGRITY** | Une preuve déterminante invalide ne produit jamais d'action ; une provenance orpheline bloque |
| **INV-ACCOUNTING** | Un transfert interne conserve l'exposition consolidée hors frais ; le simulateur conserve la richesse selon les flux |
| **INV-DEPENDENCE** | Deux canaux issus de la même archive partagent un `source_family_id` : reformater n'est pas une nouvelle observation indépendante |

### 2.5 La mesure financière (remplace M1)

Pour une date de décision commune `t`, un horizon gelé `T = t+H`, une quantité `q`, une trésorerie `C`, une quantité cédée `x`, un coût total `k` :

```
W_T(conserver) = C + q × P_T
W_T(céder x)   = C + x × P_exec(t+latence) − k(x,t) + (q−x) × P_T
L(a) = W_t − W_T(a)          R_t(a) = L(a) − min_{b ∈ A_faisable(t)} L(b)
```

`P_exec` est un prix **réalisable** pour cette taille (délai, spread, profondeur) — le prix d'agrégateur n'en est pas la preuve. Sans données suffisantes : bornes de coûts et mention « simulation sous hypothèses », ou `NON_EVALUABLE`. L'oracle choisit ex post **parmi les mêmes actions faisables**. On publie aussi `ΔL = L(A2) − L(A1)`. Anti-optimisme : développement/calibration/audit séparés chronologiquement, embargo selon les horizons, univers et fenêtres fixés sans sélection des crises réussies, mêmes information/capital/plancher/coûts pour A0/A1/A2/B0, journal de toutes les variantes essayées. **USDC 2023, déjà inspecté, reste du développement.**

---

## 3. Registre d'hypothèses révisé (v4)

### 3.1 Sortent du registre

| ID v3 | Sort | Devient |
|---|---|---|
| HYP-04 | **Exigence**, pas hypothèse empirique (observer plus d'abstentions serait tautologique) | `REQ-LABEL` : une proposition non validée ne peut satisfaire seule une preuve obligatoire ; tester des **mutations de statut** |
| HYP-09 | **Éliminée** sous sa forme actuelle (le transfert D8 ne réduit pas l'exposition émetteur ; une perte mal définie peut faire gagner n'importe quelle règle) | `HYP-09R` : en **paper trading**, une politique de cession simulée améliore la richesse nette ou une perte de trésorerie fixée, face à A0/A1 |
| HYP-14 | **Fusionnée** avec HYP-07 (un seul programme de recherche) | — |

### 3.2 Registre révisé

| ID | Formulation retenue (une ligne) | Coût | Priorité |
|---|---|---|---|
| **HYP-01R** | À données et actions égales, une **projection relationnelle** (tables plates + relations) puis un **raisonnement par relations** améliorent temps de diagnostic et défauts détectés — chaque étage mesuré séparément | 2–4 j | P1 |
| **HYP-02R** | Une VoI à un pas (`Net = EVSI − coût_total`, marge explicite) fait au moins aussi bien qu'un ordre fixe à catalogue, budget et appels égaux, et mieux sur ≥ 1 cas déclaré | 3–4 h (mécanique) + 3–5 j (pilote) | P2 |
| **HYP-03R** | Un registre de branches (avec/sans, même calcul, mêmes observations) évite contradictions oubliées et changements injustifiés ; effet regret mesuré séparément du placebo | 4–6 h + 2–4 j | P1 |
| **HYP-05A** | Zéro violation des contraintes déclarées **par couche** sur une matrice d'attaques **nommée** | 1–2 j | P1 (réduit) |
| **HYP-05B** | Caractériser les périodes de la permission périodique (frontière 2×) ; échec si l'on promet un plafond glissant que le contrat n'applique pas | 3–5 j | P2 |
| **HYP-06R** | Plan 2×2 : élicitation avant/après × cadrage neutre/critique — impact sur la calibration (Brier, discrimination) et le coût ; cible = réussite de tâche d'agent, pas le depeg | 2–3 j | Reporté |
| **HYP-07R** | Extension ML du graphe : masquage par périodes/familles sans fuite, précision@k **et** fraction d'inférences avec provenance complète ; budget égal à une règle simple | 2–4 sem. | Reporté (exploration) |
| **HYP-08R** | Primaire : **taux de fausses alertes à couverture donnée** ; secondaire : délai ; chaque famille d'acteurs ajoutée par ablation, dans l'ordre de sa date de publication | 1–2 sem. | Reporté |
| **HYP-10R** | Un tiers recalcule sans réseau chaque **calcul déterminant** (recette, entrées, version, sortie) ; toute mutation d'entrée détectée ; zéro référence pendante | 4–6 h | **P0 (T10)** |
| **HYP-11R** | La séparation analyste/politique/signataire est un **invariant** ; on teste seulement le bénéfice d'un second critique à budget de calcul égal (vs seconde passe du même modèle) | 2–4 j | P2 |
| **HYP-12R** | Sur 6 fixtures gelées (nominal stress, calme valide, source absente, preuve invalide, contradiction non résolue, donnée périmée) : zéro instruction dans les 4 cas non admissibles, conduite conforme dans les 2 valides ; mesurer coût d'attente | 2–3 h | **P0 (T12)** |
| **HYP-13R** | Porte de faisabilité d'abord : si l'horodatage public ne précède pas la cible, **arrêt précoce**. Ensuite : synchronisation résiduelle → apport hors temps → valeur nette, en trois étapes distinctes | 1–2 sem. puis plusieurs | Reporté |
| **HYP-15R** | La borne de propagation est un invariant ; mesurer ensuite borné vs aucune propagation vs un saut simple, mêmes entrées | 3–5 j | P2 |
| **HYP-DEPENDENCE** | Dédupliquer par `source_family_id` améliore la robustesse à budget égal (ne pas compter deux fois la même archive) | 2–4 h | P1 |
| **HYP-USER** | Un trésorier indépendant retrouve plus vite motif, limite d'autorité et donnée manquante dans le dossier que dans le CSV + logs ; temps et erreurs mesurés sur tâches définies | 1–2 j | P1 |

**Dépendances** : HYP-01R englobe une partie de 03/10/15 ; 04 est devenu une exigence qui recoupe 12 ; 07R/14 fusionnés ; 08R précède 13R (données) ; 09R est un résultat de bout en bout — **ne jamais additionner les gains** de ces expériences.

---

## 4. Premier lot d'essais (le cadre d'exécution)

Ordre : **T10 → T12 → T03 → T02**. Les invariants (§2.4) sont des **portes obligatoires** quoi qu'il arrive.

| Essai | Protocole minimal | Succès fixé d'avance | Ce qu'un échec démontre | Coût |
|---|---|---|---|---|
| **T10** (HYP-10R) | Cas nominal archivé + donnée absente + donnée invalide ; exporter chaque calcul déterminant avec recette et entrées ; recalculer sans base préfabriquée ni réseau ; perturber une entrée | 100 % des calculs déterminants recomputés ; mêmes verdicts ; chaque mutation détectée ; zéro référence pendante | Un calcul dépend d'un état caché ou d'une archive manquante | 4–6 h |
| **T12** (HYP-12R) | 6 fixtures gelées ; politique prudente vs action forcée ; coût d'attente inclus | 0 instruction dans les 4 cas non admissibles ; conforme dans les 2 valides ; couverture publiée | Une instruction illégitime, ou un système qui ne traite plus le nominal | 2–3 h |
| **T03** (HYP-03R) | 2 mini-épisodes synthétiques, 3 révélations chacun (confirmation puis contradiction ; manque puis résolution) ; avec/sans registre ; reprise après interruption | 6 transitions expliquées ; aucune preuve contraire perdue ; état final identique après reprise | Historique réécrit, ordre injustifié, contradiction oubliée. **Si le classifieur sans registre fait aussi bien, publier l'équivalence** (gain d'audit seulement) | 4–6 h |
| **T02** (HYP-02R) | Petit monde synthétique à 2 états et 3 outils (un inutile, un redondant, un discriminant) ; coût nul, coût > EVPI, prior perturbé ; vs ordre fixe | Valeurs = énumération à 1e−9 ; aucun outil inutile acheté ; budget respecté ; perte totale ≤ ordre fixe | Erreur d'unité, double comptage, budget dépassé → **VoI non robuste = abstention documentée** | 3–4 h |

**Capacité requise : 13–19 h** en plus de l'autorisation persistante, des règles et des livrables. **Si la capacité n'existe pas avant le gel : exécuter T10, T12 et la trace de T03 ; reporter T02.** Aucun de ces essais ne suffira à soutenir une supériorité financière — ils évaluent des **faisabilités et des contrats**.

---

## 5. Conséquences pour la soumission du 20 octobre

**Le chemin livré** : règles explicites → données admissibles → calculs traçables → branches révisables → décision → autorisation persistante → instruction humaine → reçu.

**La démo D8 est reformulée honnêtement** : le transfert interne teste la **chaîne de contrôle** (politique, instruction, reçu, vérification), **pas** une réduction d'exposition à l'émetteur — celle-ci ne s'évalue qu'en simulation de cession séparée (HYP-09R). À écrire dans le dossier et à dire à la vidéo.

**Ce qu'on ne fait pas** : migration de stockage, modèle probabiliste improvisé, délégation on-chain de dernière minute. Le mandat reste un **objectif documenté** (avec sa mesure : contrats présents à un bloc donné, sans revendication d'audit).

**Corrections à porter dans les documents existants** : C1 (six horloges), C2 (familles de relations), C3–C5 (R1 : boucles séparées, pas de partition, unités, Net), C6–C7 (R2 : intersection, fin des raccourcis), C8–C11 (R3 : M1 richesse, M2 effectifs, Wilson indicatif + matrice, placebo apparié), C12 (retirer l'alerte migration DeFiLlama ; requalifier l'axe D).

**Livrables restants** : doc technique EN · vidéo ≤ 5 min (tournage J5) · deck ≤ 10 min · wallet de test financé (instruction + reçu réels) · vérification de conformité finale.

---

## 6. Décisions à prendre (proposées à l'équipe)

1. **Adopter ce cadre** : monolithe + DFKG partiel + 4 familles de relations + 3 axes de sortie + 5 invariants.
2. **Adopter le premier lot** T10 → T12 → T03 → T02 avec ses critères de succès gelés (et le repli si capacité insuffisante).
3. **Entériner le registre v4** : 13 hypothèses révisées + 2 nouvelles ; `REQ-LABEL` en exigence ; HYP-09R en paper trading ; HYP-14 fusionnée.
4. **Reformuler la démo D8** et l'écrire dans les documents publics (honnêteté).
5. **Porter les 12 corrections** dans AXES/R1/R2/R3 (une révision datée, pas une réécriture silencieuse).

---

## Annexe — Où sont les pièces

| Document | Emplacement |
|---|---|
| Revue Astra-1 (18 findings) | `docs/sujet-F/astra-1-amelioration-globale.md` — **hors dépôt, à récupérer** |
| Revue Astra-2 (ce document en synthétise la partie reçue) | texte fourni par l'équipe, à archiver |
| AXES v3, R1, R2, R3 | `research/` |
| Auto-évaluation sécurité | `docs/SECURITY_SELF_ASSESSMENT.md` |
| Kit de revue (mis à jour) | `docs/REVIEW_KIT.md` |
| Freeze et architecture | `FREEZE_V1.md`, `ARCHITECTURE_V1.md` |
