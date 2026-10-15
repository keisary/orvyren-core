# ORVYREN — B3 · ÉTUDE DU BLOC DÉCISION

**Des hypothèses à l'action bornée : format et cycle de vie des hypothèses (ACH), mécanisme de recherche v1, abstention/escalade, catalogues d'actions par persona, règle de décision généralisée, scénarios et épisodes.**

**Version 1 — 15 octobre 2026.** Sous-agent B3. Dépôt : `D:\orvyren_core`. Matière brute et sources : `research/raw_b3/` (`notes_b3_sources.md` + fichiers web extraits). Ce document répond aux questions 3.1–3.7 de `research/SYSTEME_ZONES_OMBRE.md` §3 (« LA DÉCISION ») et prépare la note de décision du bloc C. Il ne committe rien et ne modifie aucun code.

**Règle de lecture (mêmes étiquettes que W2-D, plus une)** :

| Étiquette | Signification |
|---|---|
| **FAIT SOURCÉ** | affirmé par une source publique citée (URL + date), non re-vérifié par nous numériquement |
| **MESURÉ (interne)** | valeur produite par une mesure ORVYREN antérieure, traçable dans `evidence/` ou les rapports W2/W3 |
| **CONCEPTION** | proposition de conception ORVYREN, non sourcée, à geler par l'équipe |
| **PROPOSITION** | recommandation explicite de ce document à l'équipe (statut : à trancher) |
| **NON TROUVÉ** | absence de source publique, écrite telle quelle plutôt que comblée par une invention |

---

## 0. Résumé exécutif (ce que ce document tranche ou propose)

1. **ACH : ce qu'on garde, ce qu'on ne copie pas.** La littérature empirique ne soutient PAS l'efficacité de la matrice ACH seule : Mandel, Karvetski & Dhami (JDM 13(6), nov. 2018) trouvent que le groupe ACH a été *moins* exact et cohérent que le contrôle (la recalibration + agrégation, elles, réduisent l'erreur de 61 %) ; une étude de 2024 (Cogn. Res. 9:37) montre que la présentation « matrice ACH » n'a pas réduit le biais de confirmation (la disposition transposée, si). Ce qu'on garde : **falsifiabilité obligatoire, réfutation d'abord, sensibilité aux items critiques, jalons d'observation future** — ce que ACH a de solide conceptuellement, sans revendiquer son format. **PROPOSITION.**
2. **Format d'hypothèse = record contrôlé** (12 champs, critère de réfutation obligatoire, preuves référencées, historique append-only) et **cycle de vie à 7 états** avec transitions journalisées ; une branche proposée par le LLM démarre **sans poids** (règle R1 : `p = 0` jusqu'à validation). **CONCEPTION.**
3. **Mécanisme de recherche v1 = ordre déterministe par falsification** (5 règles, zéro probabilité) : « quel fait départage ? » devient « quel prédicat observable, déjà instrumenté en W2-B, peut changer le verdict d'une hypothèse pour le coût le plus faible ». La VoI (EVPI/EVSI, `NetVoI = VoI − c`) reste **derrière une interface**, activable seulement sous conditions. **CONCEPTION/PROPOSITION.**
4. **Abstention généralisée** : 5 conditions (A1–A5) au-delà du cas USDC, format de sortie `INCONCLUSIVE` enrichi (« ce qui manque » + « ce qui changerait le verdict »), et table déterministe **ESCALATE vs NO-ACTION**. L'avertissement conformal sur les événements rares (coverage minoritaire < 1 %) interdit de s'appuyer sur une couverture globale. **CONCEPTION.**
5. **Catalogues d'actions bornées v1** : 8 actions DAO (pré-positionner/convertir, sortir d'un LST, rembourser une dette, retirer la liquidité, rapatrier des fonds, geler des dépenses, ne rien faire, escalader) et 4 actions desk (réduire/sortir borné, hedger, dimensionner, ne rien faire), chacune avec déclencheur, bornes, coût, effet attendu et applicabilité on-chain (Zodiac Roles v2, W2-C). **CONCEPTION.**
6. **Règle de décision généralisée** : pseudo-spécification complète (§e) qui matérialise les **3 axes** (épistémique / économique / autorisation), place les seuils (liés à W2-B et W2-D) et garantit le **déterminisme sur les chiffres** (« aucun nombre produit par le LLM »). **CONCEPTION.**
7. **Scénarios v1 : qualitatif d'abord.** Probabilités seulement si gelées (`frozen_at`, hash, critère de résolution) ; scoring futur Brier/ECE ; sous N insuffisant → « non établi ». **CONCEPTION.**
8. **Les deux épisodes retenus sont traversés de bout en bout** (§g) avec les nombres réels déjà mesurés : USDC 2023 (développement) et rsETH 2026 (évaluation) — signaux → hypothèses → fait discriminant → candidat d'action bornée ou abstention.
9. **Une réconciliation à faire avant toute évaluation** : le corpus v0 (clôtures horaires, `corpus/usdc_observations.csv`) et la reconstruction W3 (plus bas horaires, `evidence/episode_*.json`) n'emploient pas la même convention de prix — 0,86267 (close) contre 0,80526 (low) pour Bitstamp. Il faut **geler une convention** avant le gel G1. **MESURÉ (interne) ; PROPOSITION.**
10. **Ce qui reste ouvert** : conditions d'activation de la VoI, garde-fous exacts de la génération d'hypothèses par le LLM, calibration par quantiles des seuils (chantier W2-B n°5), et signature des probabilités gelées (§h).

---

## (a) Hypothèses concurrentes : ACH, format de record, cycle de vie

### a.1 Ce que dit la littérature établie (établissement des faits)

1. **ACH est née dans l'analyse du renseignement.** Richards J. Heuer Jr., *Psychology of Intelligence Analysis* (CIA, 1999), formalise l'*Analysis of Competing Hypotheses* : identifier toutes les hypothèses plausibles, lister les preuves, construire une **matrice hypothèses × preuves**, et **chercher à réfuter** chaque hypothèse plutôt qu'à la confirmer — l'hypothèse qui survit à la réfutation est retenue, aucune conclusion par vote de confirmations. **FAIT SOURCÉ** (CIA 1999, PDF officiel). Le *Tradecraft Primer* de la CIA (mars 2009) intègre ACH aux techniques analytiques structurées : il constate que « les analystes génèrent rarement l'ensemble complet des hypothèses dès le début d'un projet » et montre une **matrice avec scores d'incohérence** par hypothèse — un exemple décisif : des informations « incohérentes » avec toutes les hypothèses sauf une doivent faire examiner ce que l'on aurait omis. **FAIT SOURCÉ** (CIA, mars 2009, extrait).
2. **L'efficacité empirique d'ACH est, au mieux, non démontrée — et deux résultats récents sont négatifs.**
   - Mandel, Karvetski & Dhami, *Boosting intelligence analysts' judgment accuracy: What works, what fails?*, **Judgment and Decision Making 13(6):607–621, novembre 2018** : des analystes formés à ACH sont comparés à un groupe du même corps non formé ; le groupe ACH juge mieux **l'utilité de l'information**, mais le groupe contrôle est **un peu plus exact (et cohérent)** ; « ACH failed to improve accuracy ». En revanche, **coherentization + agrégation** réduisent l'erreur absolue moyenne des jugements probabilistes de **61 %**. **FAIT SOURCÉ.**
   - *Effects of task structure and confirmation bias in alternative hypotheses evaluation*, **Cognitive Research: Principles and Implications 9:37, 13 juin 2024** (doi 10.1186/s41235-024-00560-y) : N=161, la présentation en **matrice type ACH n'a pas réduit le biais de confirmation** ; la disposition *transposée* (hypothèses en lignes, preuves en colonnes) l'a réduit ; la matrice ACH n'a conféré aucun bénéfice de sensibilité à la crédibilité des preuves ; 62 analystes militaires néerlandais ne montraient majoritairement pas de biais de confirmation. **FAIT SOURCÉ** (abstract vérifié via Europe PMC).
3. **Ce que la recherche en agents 2025-2026 ajoute** : la réfutation peut être **opérationnalisée par un agent** — *Popper* (arXiv:2502.09858, 14 février 2025) fait concevoir et exécuter par des agents LLM des **expériences de réfutation** ciblant les implications mesurables d'une hypothèse, avec contrôle strict de l'erreur de type I par test séquentiel. Un protocole plus récent (arXiv:2610.18298, octobre 2026) propose une chaîne guidée par la falsification avec un format « candidate-bounded » auditable. **FAIT SOURCÉ** (abstracts) / **PRÉPRINT** (extrait partiel).
4. **La détection de contradictions est distincte de la justesse** : *Accurate but Not Humble* (arXiv:2610.12360, 8 octobre 2026) mesure l'**humilité épistémique** d'agents sous conflit de connaissances selon trois dimensions de trajectoire — **Identify, Solve, Escalate (ISE)** — et constate que « plus de précision ne correspond pas nécessairement à plus d'humilité » : des agents détectent le conflit mais **ne communiquent pas l'incertitude résiduelle** dans leur réponse finale. **FAIT SOURCÉ.**

**Lecture ORVYREN (conséquence directe)** : ne pas traiter ACH comme un algorithme à câbler tel quel, mais comme une **discipline** : (i) l'ensemble d'hypothèses doit être explicite et enregistré (y compris les hypothèses minoritaires) ; (ii) chaque hypothèse porte ses **preuves pour ET contre** ; (iii) la progression se fait par **réfutation** ; (iv) l'évaluation finale ne doit pas reposer sur une « matrice » mais sur des **critères pré-enregistrés et évalués par un composant déterministe** (les chiffres ne sortent jamais du LLM — invariant R1) ; (v) le **niveau d'escalade** (ISE) doit être une dimension explicite de la sortie. **CONCEPTION.**

### a.2 Comment l'agent formule, soutient, réfute, fusionne — avec garde-fous

Le principe acté par l'équipe (« ça se fait par l'agent avec son raisonnement ») se traduit par une **division stricte des rôles** (déjà posée dans R1 « LLM propose, solveur dispose ») :

| Étape | Qui agit | Sortie | Garde-fous (obligatoires) |
|---|---|---|---|
| **Formuler** | Agent LLM (explorateur) | 1–n propositions d'hypothèses : énoncé d'une phrase, mécanisme supposé, portée (actif, venue, horizon) | (G1) **Falsifiabilité** : refus si l'agent ne peut pas fournir un **critère de réfutation** formulé comme un test sur au moins un prédicat instrumenté (signal W2-B ou fait documentaire daté) ; (G2) toute proposition nouvelle entre à **poids nul** (`p=0`) — elle ne rentre dans le calcul d'utilité qu'après validation et affectation d'un prior explicite (règle R1 Algorithme 2) ; (G3) chaque élément invoqué est une **référence** (timestamp, source, valeur) — pas de prose libre. |
| **Soutenir / réfuter** | Composant **déterministe** (critères enregistrés) + LLM rédacteur du motif | Statut de l'hypothèse (SUPPORTED / REFUTED / INCONCLUSIVE) + `evidence_refs` + critères évalués | (G4) un critère dont les entrées manquent n'est **jamais** « supposé satisfait » : il devient non évaluable et l'hypothèse reste INCONCLUSIVE (c'est la règle 4 du moteur v0, déjà prouvée sur USDC) ; (G5) aucun nombre produit par l'agent ne peut déclencher un critère — les seuils sont comparés par le composant déterministe sur les observations ; |
| **Fusionner / scinder** | Agent propose ; validation = dédup exacte + revue | `MERGED_INTO` / `SPLIT_FROM` / `SUPERSEDES` | (G6) une fusion ne réécrit pas l'historique : deux records fusionnés gardent leur trace et pointent l'un vers l'autre ; (G7) une fusion doit préserver la **lisibilité de la contradiction** : si H_a et H_b se contredisent, elles ne peuvent pas être « fusionnées » pour lisser le désaccord — il faut soit une hypothèse de résolution, soit l'enregistrement d'une relation `CONTRADICTS`. |
| **Contradiction** | Détection déterministe (intégrité + divergence) ; l'agent l'explique | Relation `CONTRADICTS` (famille « preuve et dérivation », RC §2.3) + mise en file d'une recherche discriminante | (G8) une contradiction non résolue **bloque** la conclusion (pas de verdict CONCLUANT tant qu'elle est active) — cf. INV-INTEGRITY ; (G9) les sources corrélées (même famille d'archive) ne comptent **pas** comme deux confirmations (INV-DEPENDENCE). |

**Pourquoi ces garde-fous et pas d'autres ?** Les résultats négatifs de a.1 disent deux choses : le format ne protège pas (2024), et l'agrégation statistique aide (2018). Donc : le LLM apporte la **couverture des hypothèses** et l'**explication**, pas la garantie ; la garantie vient des **critères pré-enregistrés et des invariants**. **CONCEPTION**, appuyée sur FAIT SOURCÉ.

### a.3 Format du record d'hypothèse (à geler)

**CONCEPTION** — 12 champs (proches de V0.2 §7.1, étendus de ce que W2-D/A2 exigent) :

| # | Champ | Type | Contenu / règle |
|---|---|---|---|
| 1 | `id` | ULID | identifiant stable, jamais réutilisé |
| 2 | `case_id` | string | épisode / fenêtre (`usdc-2023-03`, `rseth-2026-04`, …) |
| 3 | `enonce` | string | une phrase, falsifiable, avec mécanisme et portée (actif, venue, horizon) |
| 4 | `criteres` | liste | ≥ 1 critère `soutien` (S) et **≥ 1 critère `refutation` (R) obligatoire** ; chaque critère = prédicat sur observations + seuil + sources admissibles + fenêtre |
| 5 | `preuves_pour` | refs[] | observations `(timestamp_utc, venue/valeur, source)` |
| 6 | `preuves_contre` | refs[] | idem — obligatoire de tenir les deux listes (le champ ne peut pas rester vide *par omission*) |
| 7 | `inconnues` | refs[] | séries/faits requis absents → alimente `missing_inputs` |
| 8 | `etat` | enum | {CREATED, UNDER_TEST, SUPPORTED, REFUTED, INCONCLUSIVE, MERGED_INTO, ARCHIVED} (cf. a.4) |
| 9 | `p` | ∅ ou enum | **jamais un nombre** : ∅ tant que non gelé, puis étiquette gelée {improbable, possible, probable} + réf. de gel ; le nombre n'arrive qu'en annexe de calibration (f) |
| 10 | `histoire` | journal | append-only : (horodatage, transition, raison, refs, hash du dossier) — aucune réécriture |
| 11 | `provenance` | objet | auteur logique (nom de rôle, pas de personne), version du logiciel/modèle, date, sources du texte générateur |
| 12 | `relations` | refs[] | `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`, `SUPERSEDES`, `MERGED_INTO`/`SPLIT_FROM` (familles RC §2.3) |

Squelette JSON (illustratif, **CONCEPTION**) :

```json
{
  "id": "H-01J9V8...",
  "case_id": "rseth-2026-04",
  "enonce": "Le décrochage est un stress d'émetteur/actif (rsETH non adossé), pas une perturbation de venue.",
  "criteres": [
    {"nom": "soutien", "predicat": "invariant_inter_chaines_viole == true", "seuil": "ecart > tolerance 0",
     "sources": ["eth_getLogs OFT adapter", "totalSupply() par chaine"], "fenetre": "t-48h..t+24h"},
    {"nom": "refutation", "predicat": "divergence oracle/marche < 100 bps pendant >= 2 h ET isFrozen == 0",
     "seuil": "voir W2-B 1.3 / 2.2", "sources": ["Chainlink latestAnswer", "Pool.getReserveData"], "fenetre": "t0..t0+6h"}
  ],
  "preuves_pour": [],
  "preuves_contre": [],
  "inconnues": [],
  "etat": "CREATED",
  "p": null,
  "histoire": [{"utc": "2026-04-18T18:05:00Z", "transition": "CREATED", "raison": "proposée par l'explorateur (faits: cap_ratio, oracle)", "refs": ["evt:cap_ratio@18:00Z"]}],
  "provenance": {"auteur": "agent:explorateur v0", "modele": "à figer", "date": "2026-04-18T18:05:00Z"},
  "relations": []
}
```

### a.4 Cycle de vie (états et transitions)

```text
CREATED ─────── première évaluation par un critère ───────► UNDER_TEST
   │                                                          │
   │ fusion validée                                           ├── critère S satisfait ──► SUPPORTED
   ▼                                                          ├── critère R satisfait ──► REFUTED
MERGED_INTO (pointeur vers le record retenu; trace conservée) ├── critères non évaluables / non franchis ──► INCONCLUSIVE
                                                              │
 tout état ──── inutile / morte (masse, dédup, épisode clos) ──► ARCHIVED   (état, jamais suppression)
                                                              │
                                     nouvelle preuve / nouveau cas ──► retour UNDER_TEST (même record, journal append-only)
```

Règles de transition (**CONCEPTION**) :
1. **SUPPORTED exige un critère S explicitement satisfait** ; **REFUTED exige un critère R explicitement satisfait** ; sinon INCONCLUSIVE — jamais un état « par défaut ».
2. **Une seule transition par observation**, journalisée avec les refs ; pas de mise à jour silencieuse.
3. **ARCHIVED n'est pas une suppression** (append-only) : c'est la distillation bornée exigée par la mémoire bornée des agents ; un réveil réutilise le même `id` et le même historique.
4. **MERGED_INTO / SPLIT_FROM** : la fusion n'est permise que si les énoncés sont **équivalents après dédup sémantique validée** ; les contradictions restent visibles (G7).
5. **Un enregistrement ARCHIVED ne peut jamais satisfaire une preuve obligatoire** (REQ-LABEL de la revue croisée) : c'est l'état, pas l'historique, qui compte.

### a.5 Garde-fous de falsifiabilité — checklist opposable (à porter dans le gel)

- [ ] Chaque hypothèse a un **critère de réfutation** formulé comme un test exécutable par nos instruments (sinon : refus à la création).
- [ ] Chaque critère référence des **sources admissibles** nommées, avec leur pas temporel et leur convention (close vs low, cf. §g.4).
- [ ] Aucun chiffre de décision ne provient du LLM (invariant R1 Algorithme 3).
- [ ] Un LLM ne peut pas **retirer** une hypothèse — seul son état change (ARCHIVED) ; la liste des hypothèses d'un cas est gelée à l'ouverture et versionnée.
- [ ] La sensibilité est calculée : montrer que le verdict **ne tient pas** à un seul item de preuve sans le dire (sensibilité aux items critiques = étape ACH « analyze sensitivity »).
- [ ] Les jalons d'observation future (étape ACH 8) sont matérialisés par le **mécanisme de recherche v1** (§b) : chaque inconnue a au moins un prédicat candidat.

---

## (b) Mécanisme de recherche v1 (déterministe) + VoI future (interface)

### b.1 Ce que dit l'état de l'art (rappel sourcé, R1 + compléments)

- **Formules canoniques** : `EVPPI` (information parfaitement parfaite sur un sous-ensemble de paramètres) et `EVSI` (information imparfaite), avec la propriété **EVSI ≤ EVPPI** — le plafond budgétaire naturel d'une recherche (**FAIT SOURCÉ**, Heath et al., *Medical Decision Making* 40(3):314–326, epub 16 avril 2020).
- **Règle d'arrêt de l'état de l'art** : « un appel d'agent supplémentaire n'est justifié que si sa valeur d'information attendue dépasse son coût » (**FAIT SOURCÉ**, Papamarkou et al., arXiv:2605.00742 v1 1er mai 2026 ; version ESSEC HAL du 27 janvier 2026) ; `NetVoI(q) = VoI(q) − c`, arrêt si `max_q NetVoI ≤ 0`, sans réglage de seuil (**FAIT SOURCÉ**, Dong et al., ACL 2026 Long Papers, juillet 2026 — 18/20 conditions, jusqu'à +1,36 point, coût de calcul ≈ 10× les baselines).
- **Le VOI exact multi-étapes est intractable** et les approximations one-step sont l'implémentation prévue (**FAIT SOURCÉ/R1 §3(b)**) ; une variante par gradient apporte des bornes de regret (**FAIT SOURCÉ**, Li et al., WWW '25, 22 avril 2025).
- **Pièges mesurés** (R1 §4) : confiance verbale du LLM mal calibrée ; seuils fragiles ; évidence corrélée ; token ≠ task-level ; les critères KL/EIG instables pour les événements rares (arXiv:2604.21849, 23 avril 2026).
- **Nouveau complément (15/10/2026)** : les jugements sur la **valeur de l'information varient selon les 11 LLM testés** et modifient le comportement de recherche (breadth vs depth) — *On Open-Ended Information Seeking for Information Elicitation Agents*, arXiv:2610.07509, 5 octobre 2026. **FAIT SOURCÉ** (abstract). → Renforce l'exigence : la valeur d'une recherche ne doit **pas** être jugée « au ressenti » du modèle.

### b.2 LE mécanisme v1 : « recherche discriminante ordonnée par falsification » (RDOF)

**CONCEPTION** — v1 n'implemente **aucun calcul probabiliste**. Il choisit la prochaine recherche par une **comparaison déterministe de branches** sur des prédicats instrumentés (les signaux W2-B et les faits documentaires), selon 5 règles :

**Entrées**
- `H` : hypothèses enregistrées avec leurs critères S/R (a) ;
- `P` : catalogue de **prédicats observables** — chaque prédicat `p` = (source, endpoint, grandeur, **seuils enregistrés** qui partitionnent ses valeurs possibles en classes, pas temporel, coût mesuré (requêtes, secondes), historique disponible oui/non, périmètre actif/venue/chaine) ;
- `É` : état de preuve admissible (observations référencées, PIT) ;
- `B_max` : budget de la décision (nb de recherches, appels, secondes, coût monétaire — plafonds **gelés**).

**Procédure (une itération)**

```text
1. ÉVALUABILITÉ : pour chaque h ∈ H, marquer chaque critère (S/R) évaluable / non évaluable
   sous É ; collecter les inconnues (missing_inputs).
2. EFFET DES PRÉDICATS (déterministe, sans probabilité) : pour chaque prédicat p non collecté,
   pour chacune de ses issues possibles (classes définies par ses seuils enregistrés),
   calculer le verdict de chaque h « si l'issue était celle-là » :
       effet(p) ⊆ { peut_supporter(h), peut_réfuter(h), rend_évaluable(h), inchangé }
   (le calcul est exact pour les prédicats à issue binaire ou à seuils ; sinon il reste
    borné par les classes de seuils, jamais extrapolé).
3. ORDONNANCEMENT (comparaison lexicographique, ordre GELÉ, égalités tranchées par id) :
      (i)  peut réfuter l'hypothèse actuellement dominante            ← réfutation d'abord
      (ii) rend évaluable un critère portant une décision opposée      ← inconnue la plus décisive
      (iii) résout une contradiction enregistrée non résolue
      (iv) coût le plus faible (secondes + appels, MESURÉS)
4. EXÉCUTION : collecter le prédicat choisi, l'ajouter à É avec ses refs, retourner en 1.
5. ARRÊT (dans l'ordre, première condition vraie) :
      c1. INVARIANCE : pour tous les prédicats restants, toutes les issues possibles donnent la
          même action candidate sous la règle de décision gelée → arrêt « décision stable » ;
      c2. BUDGET : B_max atteint → arrêt « budget épuisé » ; le dossier LISTE ce qui n'a pas été
          recherché et l'effet possible (delta) que cela pourrait avoir ;
      c3. GARDE-FOU DE CONFIANCE (optionnel, désactivé par défaut) : masse/étiquette stable au
          seuil — jamais le critère principal (RC/A2).
```

**Ce que « quel fait départage H1/H2 ? » veut dire exactement ici** : un fait `f` (prédicat collecté) départage si, en le comparant aux seuils enregistrés, **le verdict d'au moins une hypothèse change** — et le mécanisme privilégie les faits dont l'une des issues **réfute** l'hypothèse tenue pour dominante, c'est-à-dire les **tests les plus falsifiants accessibles au coût le plus bas**. C'est la transposition opérationnelle de l'étape ACH « sensibilité aux items critiques » et de la réfutation poppérienne (arXiv:2502.09858), en restant dans un cadre **déterministe, auditable, sans probabilités inventées**.

**Micro-exemple (USDC, 11 mars 2023, après les signaux de 07:00–08:00).** État de preuve : décote > 1 % simultanée sur Binance et Bitstamp (issue de la série déjà collectée, coût nul) ; H1 reste possible tant que la persistance n'est pas tranchée et H2 tant que la baisse d'offre n'est pas observée. Prédicats candidats : (i) *persistance > 12 h sur ≥ 2 venues* — issue directement lisible dans les séries déjà en main (coût 0, mais verdict seulement disponible en fin de fenêtre) ; (ii) *baisse d'offre 24 h > 1 %* — 1 requête (coût marginal, verdict immédiat) ; (iii) *dispersion inter-venues ≥ 300 bps* — déjà mesurée (870 bps ; coût 0). Ordre appliqué : (iii) et les faits déjà collectés passent en premier (coût 0, règle (iv) appliquée après les règles (i)–(iii)) ; parmi les prédicats restants, (ii) **peut réfuter H1** (une baisse d'offre est incompatible avec une perturbation locale) et coûte moins cher qu'attendre (i) — c'est donc (ii) qui part en tête dès que la règle (i) s'applique. Résultat mesuré : −7,1722 % sur 24 h → H1 réfutée, H2 soutenue. C'est exactement la trace que le dossier v1 doit porter (question → prédicat → coût réel → effet sur les verdicts).

**Exemples de prédicats v1** (issus de W2-B §(c), « 5 signaux à implémenter en premier », tous déjà exécutés le 15/10/2026) :

| Prédicat | Issue | Coût mesuré | Effet type |
|---|---|---|---|
| `isFrozen` d'une réserve (bit 57, `Pool.getReserveData`) | 0/1 | 1 `eth_call`/marché/bloc (~0,4–0,7 s, W3-A) | passage 0→1 = « la sortie est fermée » → peut réfuter H1 (perturbation locale réversible) |
| `supplyCap` ratio (`S/supplyCap`) | classes {<95 %, ≥95 %, ≥99 % saturé} | idem | saturation → peut soutenir un stress d'émetteur (H2) |
| divergence oracle/marché `Δ` (W2-B 1.3) | classes {<100 bps, ≥100 bps} | 2 lectures | survalorisation retenue → réfute « artefact » ou « local » selon le signe |
| dispersion inter-venues `σ_disp` (W2-B 1.2) | classes {<100, ≥100, ≥300 bps} | 1 req/venue | ≥300 bps → la référence unique n'est plus fiable |
| baisse d'offre 24 h (W2-B 6.3) | classes {<1 %, ≥1 %} | 1 req | peut soutenir/réfuter le stress large (H2) |
| `get_dy` ladder (W2-B 1.4/1.5) | décote par taille | n appels | décote **réalisable** → dimensionne l'action (borne) |

**Coûts** : les budgets s'appuient sur des coûts **mesurés** (W3-A : ~0,65 s/appel séquentiel sur `eth.drpc.org`, ~0,36 s sur blastapi, 12,4 appels/s sur 8 fils ; W3-B : reconstruction USDC complète ~2 min ; lecture horaire oracle+Aave ~15 s). Le budget par décision doit être exprimé en **requêtes+secondes**, pas en tokens (le raisonnement LLM est compté séparément, cf. W2-D piège n°7).

**Ce qui distingue v1 d'un ordre fixe** (c'est ce qui sera évalué, essai T02/HYP-02R) : l'ordre **s'adapte à l'état de preuve** — un prédicat dont l'issue ne peut plus changer la décision n'est jamais acheté (règle c1), et la réfutation du leader passe avant la confirmation. **Un ordre fixe borné reste le repli documenté** si le mécanisme n'est pas livré (RC §2.1).

### b.3 VoI derrière l'interface (v2, non livrée en v1)

**CONCEPTION** — le branchement VoI se fait derrière une interface unique `value_of_search(predicat) -> {voi, statut}` :
- quand des probabilités **gelées et calibrées** existent (f), `VoI(q)` approx one-step (équations ACL) ; arrêt si `max NetVoI ≤ 0` ; `B_max ≤ EVPI estimé` ;
- sinon le service renvoie **`VOI_NOT_ESTIMABLE`** et le mécanisme v1 prend la main sans changer le résultat de la décision (la VoI n'est jamais un point de défaillance) ;
- conditions d'activation à trancher : calibration démontrée sur ≥ N cas (à définir), journalisation complète, et test T02 concluant (valeurs = énumération ; aucun outil inutile acheté ; budget respecté).

---

## (c) Abstention & déferral : conditions générales, format, ESCALATE vs NO-ACTION

### c.1 Littérature (ce qui est établi)

- **Rejet (reject option)** : la règle de Chow (1970) rejette quand l'utilité espérée de décider est inférieure au coût de rejet — la décision d'abstention est **coût-optimale** et non un aveu d'échec (**FAIT SOURCÉ**, Chow, IEEE Trans. Inf. Theory, 1970). La revue *Machine learning with a reject option* (Springer, 29 mars 2024) distingue rejet **d'ambiguïté** et rejet de **nouveauté** (hors-distribution) et rappelle que la règle de Chow suppose les distributions connues (**FAIT SOURCÉ**, doi 10.1007/s10994-024-06534-x).
- **Déférence à l'humain** : *Learning to Defer* (survey, preprint Zenodo déc. 2025) et Madras et al. (arXiv:1711.06664, 2018) formalisent la décision jointe machine→humain (**FAIT SOURCÉ** métadonnées / SNIPPET).
- **Danger des garanties globales sur les événements rares** : *Cost-Sensitive Conformal Prediction and Human-in-the-Loop Abstention* (arXiv:2607.27143, 29 juillet 2026) montre que le **CP marginal sous-couvre les classes minoritaires jusqu'à 0,5 %** et que **CP conditionnel (Mondrian) + abstention contrôlée par coût sous budget de revue humaine** réduit le coût de décision attendu (benchmark 15 jeux, 7 modèles, 3 150 runs). **FAIT SOURCÉ** (abstract). → Pour ORVYREN, l'événement d'intérêt (rupture de peg) **est** la classe minoritaire : toute couverture « globale » est trompeuse.
- **Humilité épistémique opérationnelle** : dimensions **Identify / Solve / Escalate** (arXiv:2610.12360) — l'escalade est une **dimension mesurable** de la trajectoire, et l'échec typique est de détecter sans communiquer l'incertitude résiduelle. **FAIT SOURCÉ.**

### c.2 Les 5 conditions générales d'abstention (au-delà d'USDC)

**CONCEPTION** — l'agent doit **s'abstenir** (et le dire) dès que l'une de ces conditions est vraie ; chacune est vérifiable sans probabilités :

| # | Condition | Test opérationnel | Exemple déjà rencontré |
|---|---|---|---|
| **A1** | **Entrée requise absente** | une série/un fait nécessaire à un critère S ou R manque → `missing_inputs` non vide | règle 4 du moteur v0 (série Bitstamp absente d'une fenêtre) |
| **A2** | **Contradiction non résolue** | ≥ 2 sources de nature distincte se contredisent au-delà des tolérances **et** aucune relation `CONTRADICTS` résolue ; ou drapeau d'intégrité (doublon conflictuel, timestamp non-UTC, valeur non-positive) | divergence oracle/marché non expliquée ; cas Drift « prix ~1 $ fabriqué » (W2-B 4.3) |
| **A3** | **Décision non identifiable sous budget** | après épuisement de `B_max`, deux hypothèses survivantes prescrivent des **actions opposées** et le fait discriminant n'est pas obtenable (coût > budget ou source inexistante) | USDC 2023 si l'offre en circulation n'avait pas été disponible ; rsETH après fermeture de la sortie (g) |
| **A4** | **Hors enveloppe / politique** | l'intention dérivée de l'action économiquement préférée viole `x ≤ x_max`, la venue n'est pas au allowlist, l'expiration est passée | tout refus de politique (W2-C runs B/C) |
| **A5** | **Convention de mesure ambiguë** | deux lectures admissibles du même fait donnent deux verdicts (close vs low ; deux pas d'échantillonnage) sans convention gelée | Bitstamp 0,86267 (close) vs 0,80526 (low), §g.4 |

Note : A4 est une abstention **d'autorisation** (axe 3), jamais confondue avec A1–A3, **épistémiques** (axe 1) — c'est la correction C3 de la revue croisée.

### c.3 Format de sortie « INCONCLUSIVE + ce qui manque »

**CONCEPTION** — étend le dossier v0 (`verdict/action/rationale/conditions/limits/provenance/missing_inputs`) :

```json
{
  "epistemic_verdict": "INCONCLUSIVE",
  "conditions_declenchees": ["A1"],
  "missing_inputs": ["offre en circulation 24 h (defillama_supply_aggregate)"],
  "what_would_change_the_verdict": [
    {"fait": "baisse d'offre >= 1 % sur 24 h", "hypotheses_affectees": ["H2"],
     "predicat": "P-6.3", "cible": "defillama stablecoins", "cout_estime": "1 requete, <5 s"}
  ],
  "decision_delta": {"si_H2_soutenue": "candidat A-D1 (convertir borne x*)", "si_H2_refutee": "NO_ACTION documente"},
  "budget": {"consomme": {"recherches": 2, "appels": 14, "s": 9.6}, "reste": null, "raison_arret": "budget épuisé (c2)"},
  "escalade": null,
  "action": null
}
```

Règles : `missing_inputs` **énumère** chaque fait manquant avec sa source possible et son coût estimé (pas « données insuffisantes » en prose) ; `what_would_change_the_verdict` = les faits discriminants (le lien direct avec §b) ; `decision_delta` montre les deux décisions selon l'issue — c'est ce qui rend l'abstention **utile** et non un refus muet.

### c.4 Quand ESCALATE (humain requis) vs NO-ACTION

**CONCEPTION** — table de décision déterministe (différences **explicites**) :

| Situation | Sortie | Motif |
|---|---|---|
| Verdict conclusif ; aucune action faisable ne passe le seuil économique (coût ≥ gain conditionnel) ; l'attente ne crée pas d'obligation nouvelle | **NO-ACTION** (avec motif chiffré) | « ne rien faire est la décision optimale sous les hypothèses gelées » (W2-D §B.4.1) |
| Verdict conclusif ; action décidée **hors enveloppe** (x > x_max, venue exclue) ou politique = REQUIRE_APPROVAL | **ESCALATE** (dossier prêt à signer) | A4 ; c'est le flux REQUIRE_APPROVAL de W2-C (Delay module, T3) |
| Verdict conclusif ; le fait décisif obtenable seulement par un canal non outillé (contact humain, information privée, document payant) | **ESCALATE** | l'agent ne peut pas acheter l'information |
| INCONCLUSIVE (A1/A2) mais **perte potentielle bornée** et budget épuisé : le pire cas sous actions faisables reste sous le seuil de danger | **NO-ACTION** + journal d'abstention | asymétrie des coûts favorable (Chow) |
| INCONCLUSIVE (A1/A2/A3) et les deux hypothèses survivantes prescrivent des actions opposées dont la mauvaise est coûteuse au-delà du seuil | **ESCALATE** | A3 ; « postérieure fragile → abstention ou escalade » (R1/ arXiv:2605.00742) |
| Intégrité en échec (preuve déterminante invalide, provenance orpheline) | **ESCALATE** (et blocage) | INV-INTEGRITY : « une preuve déterminante invalide ne produit jamais d'action » |
| **Rappel** : « attendre » n'est pas « ne pas agir » — NO-ACTION doit être justifié comme la meilleure action faisable, pas comme l'absence de décision | — | RC §2.2 ; W2-D (le put payé) |

L'humilité épistémique (ISE) se matérialise ainsi : `Identify` = conditions A1–A3 détectées ; `Solve` = recherche discriminante (§b) ; `Escalate` = table ci-dessus. **CONCEPTION** adossée à FAIT SOURCÉ (arXiv:2610.12360).

---

## (d) Catalogues d'actions bornées par persona (v1)

### d.1 Principes communs

- Une action n'est **jamais** un ordre libre : c'est une **intention bornée** (actif, montant, dest, fonction, expiration) que la politique peut refuser (W2-C), et dont l'exécutable est vérifié avant/après (receipt).
- **Bornes par construction** : `x* = min(x_max_rôle, Depth_ε(venue), x_seuil)` — où `Depth_ε` est la profondeur de sortie mesurée (`get_dy`/QuoterV2, W2-B 1.5) et `x_seuil` la taille qui passe le seuil économique (W2-D).
- **Le coût est dans la décision** : frais + gas + slippage mesuré + (desk) financement. Sans coût, une « perte évitée » peut être inventée (W2-D pièges n°4).
- Chaque action est étiquetée **applicable on-chain** (v1 : transfert ERC-20 réel + autres actions en **simulation** tant que l'enveloppe Zodiac ne les couvre pas) — honnêteté de démo (V0.2 §10/§13).

### d.2 Catalogue DAO (trésorerie / protocole) — 8 actions bornées

| # | Action | Déclencheur (épistémique) | Déclencheur (économique) | Bornes v1 | Coût | Effet attendu | Applicabilité on-chain | Ancrage réel |
|---|---|---|---|---|---|---|---|---|
| **A-D1** | **Pré-positionner / convertir** une part du stablecoin exposé vers un support non exposé (autre émetteur, ou cash au timelock) | H2 SUPPORTED (stress large) **ou** H1 SUPPORTED sans certitude de confinement, avec A1–A3 levées | `E[perte évitée] = P(obligation)·(L(A0)−L(a)) > coût` ; sinon NO-ACTION | x ≤ x_max ; venue au allowlist ; ≤ profondeur `Depth_ε` | frais + slippage mesurés (`get_dy`) + gas | réduit l'exposition conditionnelle à l'obligation de vendre ; **paye une prime sinon** (aller-retour ≈ −4,0 % mesuré sur l'exemple USDC/W2-D §E.2b) | Oui (swap via CoW/Curve, cap Zodiac) — v1 démo : transfert de test | Maker 11-13/03/2023 (PSM : gap 950→250 M$, `tin` 1 %) ; Eco (diversifier ≥ 2 émetteurs) ; ENS IPS (priorité runway « Unconditional ») |
| **A-D2** | **Sortir d'un LST** (stETH/rsETH → ETH) via veto/retrait/swap | décote **réalisable** > seuil (W2-B 1.4 : ≥ 100/300/600 bps) **et** tendance non transitoire (persistance > 12 h) | idem A-D1 ; l'action est justifiée si la décote peut encore se creuser ou si la redemption on-chain risque d'être suspendue | ≤ profondeur ; dead-line avant files de redemption | slippage ladder mesuré (ex. 10 000 stETH → 7,13 bp en calme ; 755 bp le 14/06/2022) | évite la matérialisation d'une décote croissante ; anti-précédent 3AC/Celsius (liquidité qui ne revient pas) | Oui (Curve, avec slippage réel mesuré) | stETH mai-juin 2022 (antériorité 30 j mesurée, W3-A §3) ; « exit liquidity in two regimes » (Sentralis 14/07/2026) |
| **A-D3** | **Rembourser une dette / dé-leverer** une position collatéralisée | hausse de la probabilité de gel/liquidation de la **venue de dette** (isFrozen, LTV→0, utilisation ≈100 % sur WETH/USDC) | coût du remboursement < perte attendue sous gel (blocked exit) | x ≤ disponible+dette ; ordre : désendetter d'abord si collatéral verrouillé | frais + gas | réduit la surface de liquidation ; libère du collatéral si LTV imposé | Oui (repay/withdraw dans le allowlist de rôles) | rsETH 18-20/04/2026 : WETH gelé et LTV WETH → 0 ; USDC Aave → cash 6 403 $ (MESURÉ) |
| **A-D4** | **Retirer la liquidité / ne pas en ajouter** (retirer des prêts/vaults/pools) | signal de gel ou de saturation (`cap_ratio ≥ 95 %`, `isFrozen`, utilisation-cash ≥ 99 %, files de redemption) | coût du retrait (gas) < valeur d'option de la sortie ; si la sortie est déjà fermée → ESCALATE | ≤ cash disponible ; priorité aux positions à panier de sortie le plus fermé | gas + éventuels coûts de sortie (pénalités) | convertit « valeur retenue » en « valeur disponible » (redeemability, IPS ENS : ≥90 % < 7 j) | Oui (withdraw) | KPK/ENS sort de ses positions Aave le 18/04/2026, reconstruit en mai **sans perte** (KPK H1, 14/08/2026) |
| **A-D5** | **Rapatrier vers le timelock / le module runway** (réapprovisionner le floor) | le buffer opérationnel descend sous cible (6 mois pour ENS) ou le runway projeté s'approche du plancher | arbitrage liquidité vs coût d'opportunité déclaré | ≤ cible du module ; montants standardisés (ex. tranches 1 500/3 000 ETH chez Lido) | gas + coût d'opportunité | maintient la contrainte dure (runway) ; sert la reddition de comptes | Oui (déjà automatisé chez ENS) | ENS Registrar Manager + module Zodiac (~6 mois USDC) ; Lido TMC (tranches standard/urgence) |
| **A-D6** | **Geler / réduire des dépenses** | stress prolongé, perte de valeur USD de la trésorerie, décision de gouvernance | n/a (décision politique) | relève de la gouvernance — **pas une action de l'agent** | — | protège la trésorerie ; cadence longue | **Non** (proposition de gouvernance) → ESCALATE | Lido : utilisation EGG 22 % en 4 mois, coupes après repli de février (Q1'2026) ; Aave : buyback 50→30 M$ |
| **A-D7** | **Ne rien faire** (documenté) | verdict conclusif sans action passant le seuil ; ou H1 SUPPORTED + H2 REFUTED (perturbation locale) | coût d'une action ≥ gain conditionnel | x = 0 | 0 (mais coût d'opportunité si l'alerte se répète — friction SD2 ≤ 10 %) | évite la prime systématique ; conserve le risque (à écrire) | Oui (état par défaut) | W2-D §B.4.1 (desk) ; moteur v0 règle 2 |
| **A-D8** | **Escalader** (comité/treasury manager/gouvernance) | A3/A4/A5 ou intégrité en échec (c.4) | — | — | latence humaine | décision tracée et responsable ; pas de blocage silencieux | via file d'approbation (T3, Delay) | W2-C (flux REQUIRE_APPROVAL à implémenter) ; Chaos Labs : responsabilité « fondamentalement indéfinie » |

### d.3 Catalogue desk (rentabilité) — 4 actions bornées

| # | Action | Déclencheur | Bornes v1 | Coût | Effet attendu | Applicabilité | Ancrage |
|---|---|---|---|---|---|---|---|
| **K-D1** | **Réduire / sortir** une position d'inventaire (stablecoin ou collatéral) | signal de rupture (D ≥ 200 bps, dispersion ≥ 300 bps) **et** `x·(P_T − P_exec) > k_aller-retour + financement` (W2-D) | x ≤ min(x_max, `Depth_ε`) ; pas de re-entrée implicite — la décision inclut le plan de retour ou le dit | frais+slippage+fin. | réduit la perte de queue ; **coûte** si le peg se rétablit (put payé : −4,2 % sur l'exemple USDC) | Oui | W2-D §E.3 ; DeFi Saver (stop-loss automation 0,25–0,30 %) |
| **K-D2** | **Hedger** (short perp / option de depeg) | exposition résiduelle à un actif dont la décote est possible ; coût du hedge < perte conditionnelle | notionnel ≤ exposition ; marge pré-financée ; venue au allowlist (v2, démo seulement) | funding + prime d'option | neutralise la queue sans vendre le spot | **Simulation** en v1 (pas dans l'enveloppe Zodiac v1) | depegwatch 19/09/2025 (swaps/options de depeg) ; Ethena (delta-neutral) — SNIPPETS |
| **K-D3** | **Dimensionner** (sizing) | toujours, avant toute action | `x = min(x_max, Depth_ε, x*)` ; publier `Slip(x)` réalisé vs budget (ST2 ≤ 30 bp) | — | évite d'exécuter une « perte évitée » plus petite que le coût d'exécution | Oui | W2-D §A.2.5/T4 |
| **K-D4** | **Ne rien faire / attendre** | le seuil n'est pas franchi ; ou incertitude symétrique et coût d'aller-retour prohibitif | x = 0 | 0 | évite le churn (le coût décide du signe du Sharpe — JKP snippet) | Oui | W2-D §B.4 ; Miller/DSR (Bailey & López de Prado 2014) |

### d.4 Règles transverses (à geler avec les catalogues)

1. **Aucune action n'ouvre une exposition nouvelle** en épisode de stress (uniquement réduire/convertir/rembourser/retirer) — c'est la borne que W2-C sait vérifier on-chain. **CONCEPTION**.
2. `x_max` par action et par persona, compteur glissant 24 h (plafond d'accumulation, attention W2-C : pas de plafond « glissant » natif).
3. Toute action porte son **effet attendu en perte évitée conditionnelle** (DAO) ou **ΔP&L net** (desk), recalculé à la taille réelle.
4. Le catalogue est **versionné** ; l'exécution cite la version (INV-AUTH).

---

## (e) Règle de décision généralisée : pseudo-spécification

### e.1 Structure (3 axes matérialisés)

```text
ENTRÉES
  É      état de preuve admissible (observations PIT référencées)          ← B1/B2
  H      hypothèses + critères (format a.3), version gelée                 ← bloc C
  pers   persona ∈ {DAO, desk} ; mandat (contraintes, floor, caps)
  F      exposition consolidée (positions, unités, venues, valorisation
         oracle ET valorisation réalisable)                               ← W2-B double prix
  E      enveloppe : x_max par type d'action, venues/actifs au allowlist,
         expiration, plafonds 24 h                                         ← W2-C
  k      coûts mesurés (frais, gas, slippage, financement)
  P      catalogue de prédicats observables (coût, seuils)                 ← §b
  B_max  budget de recherche gelé

SORTIES (3 axes séparés, jamais fusionnés — RC §2.2)
  epistemic_verdict   ∈ {CONCLUANT, INCONCLUSIVE}              + missing_inputs + what_would_change
  economic_action     ∈ {CONSERVER, CONVERTIR/TRANSFÉRER, CÉDER(x*), RÉDUIRE(x*), HEDGER(x*),
                         RAPATRIER, ESCALADER}                 (ou null si INCONCLUSIVE)
  authorization_verdict ∈ {ALLOW, DENY, REQUIRE_APPROVAL}      (indépendant des deux autres)
  dossier             verdicts H, faits discriminants, calculs, prévision gelée, budget, hash
```

### e.2 Pseudocode (déterministe ; les nombres ne sortent jamais du LLM)

```text
 1  verdicts ← classer(H, É)                     # critères pré-enregistrés (v0 généralisé)
 2  si verdicts contiennent une inconnue critique :
        prochaine ← RDOF.choisir(É, H, P, B_max)        # §b.2
        si prochaine ≠ ∅ et budget disponible : collecter ; retour en 1
 3  epi ← CONCLUANT si (∃h SUPPORTED) ou (∀h REFUTED, critères évaluables)
        sinon INCONCLUSIVE (conditions A1–A3 ; format c.3)
 4  si epi = INCONCLUSIVE :
        economic ← table c.4 (NO-ACTION documenté ou ESCALATE) ; action ← ∅ ; aller en 8
 5  A_cand ← {a ∈ catalogue(pers) : déclencheurs(a) satisfaits sous verdicts}
        # ex. DAO : H2 → {A-D1, A-D2?, A-D3?, A-D4, A-D5} ; H1 seul → {A-D7}
 6  pour chaque a ∈ A_cand :
        x*(a) ← min(x_max(a), Depth_ε, x_seuil(a))                # bornes (d)
        si x*(a) = 0 : écarter(a, motif="borne nulle")
        gain(a) ← DAO : P(obligation)·(L(A0) − L(a)) ; desk : ΔP&L_net(a)
        coût(a) ← k(a) + coût_recherche_mesuré
        # Loss model W2-D : W_T, L(a) = W_t0 − W_T(a), regret ; jamais deux fois la même perte
        si gain(a) − coût(a) ≤ 0 : écarter(a, motif="seuil économique non franchi")
 7  economic ← argmax_a (gain(a) − coût(a)) ; si A_cand est vide : CONSERVER/ATTENDRE (motif)
        → x* ; P_exec(x*) ; ΔL publié ; sensibilités (P_exec ∈ {min, méd, pire venue})
 8  si economic ∈ {CONVERTIR, CÉDER, RÉDUIRE, HEDGER, RAPATRIER} :
        intention ← intent borné (actif, montant x*, dest, fonction, expiration)
        authorization ← politique(intention)      # ALLOW / DENY / REQUIRE_APPROVAL
        # DENY ⇒ dossier conservé ; REQUIRE_APPROVAL ⇒ ESCALATE
 9  si une prévision est émise : la GELER (f)
 10 dossier ← {verdicts, faits discriminants (refs), calculs, budget, hash} ; journaliser
```

### e.3 Où se placent les seuils (et d'où ils viennent)

| Seuil | Valeur | Source | Statut |
|---|---|---|---|
| décote alerte / rupture / sortie obligatoire | ≥ 50 bps (15 min) / ≥ 200 bps / ≥ 500 bps | W2-B §Famille 1 (justifiés par l'épisode USDC : dispersion 870 bps) | seuils candidats — calibration par quantiles ouverte (W2-B chantier 5) |
| dispersion inter-venues | > 100 bps (référence à abandonner) / > 300 bps (venue exclue) | W2-B 1.2 | idem |
| divergence oracle/marché | \|Δ\| > 100 bps pendant > 1 h → ne plus valoriser sur l'oracle | W2-B 1.3 (296 bps mesurés en 2023 ; 31 % en 2026) | idem |
| saturation cap / gel | cap_ratio ≥ 95 % / `isFrozen` 0→1 | W2-B 2.2, 2.5 (99,9989 % mesuré) | MESURÉ (rsETH) |
| baisse d'offre 24 h | > 1 % | W2-B 6.3 / moteur v0 (frozen) | gelé dans v0 |
| persistance / récupération (H1) | > 12 h de persistance sur ≥ 2 venues ; récupération < 12 h à 0,1 % | moteur v0 (`scenarios.py`, gelé) | gelé dans v0 ; à généraliser |
| seuil desk | `x·(P_T − P_exec) > k_aller-retour + financement` | W2-D §B.4 | CONCEPTION (à figer) |
| seuil DAO (perte évitée / friction) | ≥ 5 % de l'exposition (conditionnel) ; friction ≤ 10 % de la perte évitée | W2-D §C.4.1 (SD1/SD2) | CONCEPTION (à figer avant EVAL) |
| vol de recherche / budget | B_max en requêtes+secondes ; cap dur d'itérations ; allowlist de sources | R1 Alg. 1 + Stack Overflow determinism layer (2026-10-07) | CONCEPTION |
| plausibilité P(obligation) | hypothèse explicite gelée, sensibilité publiée | W2-D §E.2 / G6 | NON TROUVÉ (aucune source publique) |

### e.4 Ce qui reste déterministe et ce que fait le LLM

- **Déterministe** : classement des hypothèses, évaluation des critères, seuils, taille x*, pertes/regrets, politique d'autorisation, choix du prédicat (RDOF), arrêts, hash du dossier.
- **LLM (jamais un chiffre)** : rédiger les énoncés d'hypothèses, canonicaliser des documents vers le schéma, expliquer le motif et les contradictions, proposer des jalons — tout est **validé par schéma** et rejeté/en quarantaine si un champ est inconnu (V0.2 §5.3 ; R1 Alg. 3).
- **Invariants applicables** (portes obligatoires) : INV-PIT, INV-AUTH, INV-INTEGRITY, INV-ACCOUNTING, INV-DEPENDENCE + « aucun chiffre LLM ». Une sortie `INCONCLUSIVE` est une sortie **de première classe**, pas un échec.

---

## (f) Scénarios & probabilités v1 : qualitatif d'abord, gel et scoring

**CONCEPTION** — s'appuie sur les corrections C4/C9 de la revue croisée et le protocole W2-D §C :

1. **Représentation qualitative d'abord.** Les hypothèses ne forment **pas une partition** (stress réel et artefact peuvent coexister) : aucune normalisation à somme 1. Le champ `p` d'un record reste ∅ jusqu'à gel ; quand il est gelé, c'est une **étiquette ordinale** {improbable, possible, probable} accompagnée d'une **définition calibrée** écrite au moment du gel (à quelle fréquence historique l'étiquette correspond).
2. **Qui produit quoi.** L'agent **propose** les énoncés et l'élicitation (cadrée en « recherche de bugs », le cadrage mesuré comme le mieux calibré — Kaddour et al., arXiv:2602.06948, 6 février 2026) ; le composant déterministe **écrit** la prévision gelée et son hash ; un humain **signe** le gel (G6 de W2-D).
3. **Quand on gèle.** Avant que l'issue ne soit connue : prévision = {énoncé, critère de résolution, horizon `T`, date de gel, empreinte SHA-256, état de l'observation au gel}. Une prévision non gelée n'entre dans aucun calcul (interdit : confiance verbale du modèle — ACL 2026 §6.1).
4. **Scoring futur.** Brier score (Brier 1950) et décomposition REL/RES/UNC ; règles strictement propres (Gneiting & Raftery 2007) ; ECE et couverture conformale quand N le permettra ; **effectifs publiés** (pas « 5 carrés = calibré », C9) ; sous N insuffisant → « **non établi** » (V0.2 §9.3).
5. **v1 : aucune probabilité dans la décision.** En v1, la décision ne dépend d'aucune probabilité (le mécanisme §b n'en utilise pas) ; les seules valeurs « probabilistes » sont des **hypothèses explicites gelées** (ex. `P(obligation)`) avec **sensibilité publiée** — interdiction de publier une espérance sans les deux facteurs visibles (W2-D §B.3).
6. **Lien protocole** : G1–G7 de W2-D (fonction de perte, comparateurs, fenêtres+embargo, seuils, plan d'analyse, hypothèses économiques, journal des variantes) restent la référence ; ce document n'y ajoute que le **format des prévisions** et la règle « qualitatif d'abord ».

---

## (g) Les deux épisodes retenus, traversés de bout en bout

> Tous les chiffres proviennent de `evidence/episode_usdc_2023-03.json`, `evidence/episode_rseth_2026-04.json`, `evidence/decision_usdc-2023-03.json`, `evidence/baseline_report.json` et des rapports W2/W3 (**MESURÉ (interne)**), ou des sources citées (**FAIT SOURCÉ**). Les sorties « v1 » sont **CONCEPTION**.

### g.1 Épisode USDC / SVB, 10–13 mars 2023 (jeu DÉVELOPPEMENT)

**Chaîne de décision (faits mesurés)**

| Instant (UTC) | Fait mesuré | Valeur |
|---|---|---|
| 10/03 ~22:00 | Circle annonce l'exposition SVB (3,3 Md$, ~8 % des réserves) ; marché primaire fermé tout le week-end | FAIT SOURCÉ (Fed FEDS, 17/12/2025) |
| 11/03 03:00 | **divergence oracle/marché extrême : −558,9 bps** (l'oracle affiche encore 0,99065 quand la médiane des venues est ~0,935 : survalorisation retenue ≈ +5,6 %) | MESURÉ (W3-B) |
| 11/03 07:00 | plus bas horaires : Bitstamp **0,80526** (décote 1 947 bps), OKX 0,8698 ; clôture Bitstamp 0,86267 | MESURÉ (W3-B/W2-B) |
| 11/03 07:53 | **minimum dense de l'oracle Chainlink : 0,8833** (correction de W2-B : sa grille donnait 0,90687) | MESURÉ (W3-B) |
| 11/03 07:57 | agrégat DeFiLlama **0,876675** (décote 1 233 bps) | MESURÉ (reproduit) |
| 11/03 08:00 | dispersion horaire maximale inter-venues : **1 047,7 bps** | MESURÉ (W3-B) |
| 11/03 (fenêtre) | dispersion fenêtre : **870,07 bps** ; supply en circulation **−7,17 % sur 24 h** | MESURÉ (W2-B/v0) |
| 10→14/03 | Aave V3 USDC : U 0,6443 → pic **0,8727** (11/03 03:00) → **0,2754** (12/03 23:00) | MESURÉ (W3-B) |
| 13/03 08:51 | oracle Aave **0,9910** ; guérison | MESURÉ |

**Hypothèses (moteur v0, pré-enregistrées)** → H1 « perturbation locale » : **REFUTED** (décote > 1 % persistante > 12 h sur 2 venues indépendantes : Bitstamp 42 h, Binance 45 h ; agrégat tombé à 0,876675, au-delà de la tolérance 0,5 %). H2 « stress large actif/émetteur » : **SUPPORTED** (34 heures simultanées > 1 % sur Binance+Bitstamp ; baisse d'offre −7,17 % sur 24 h). H3 « artefact » : **REFUTED** (2 sources concordantes, pas d'incohérence structurelle).

**Fait discriminant (v0/v1)** : la **conjonction** (i) simultanéité sur ≥ 2 venues indépendantes et (ii) **baisse d'offre en circulation > 1 %/24 h** — c'est ce couple qui fait basculer H1→H2 ; la divergence oracle/marché (−559 bps) et la dispersion (870–1 048 bps) sont les faits qui **écartent la confiance dans une source unique** (et donc une erreur de mesure, H3).

**Candidat d'action bornée (v1, DAO)** : H2 SUPPORTED → **A-D1** (convertir/pré-positionner une part bornée de l'exposition USDC vers un support non exposé), conditionné à `P(obligation)` et au coût : avec l'exemple W2-D (20 M$ exposés, sortie exécutable ~0,95, obligation de payer 1,37 M$), perte évitée **110 912 $ (2,47 j de runway)** si conversion à 0,8820 ; mais **−800 000 $ (−4,0 %)** si aucune obligation (prime payée). NB : la sortie **à 0,95 est une hypothèse de travail**, non mesurée ; la sensibilité doit être publiée (pire venue 0,80526 → perte évitée 258 578 $). **MESURÉ/CONCEPTION (W2-D §E.2).**
**Ce que le moteur v0 renvoie aujourd'hui** : `ACTION_RECOMMENDED` = **transfert de démonstration de 100 USDC test** (D8, borne `min(100, 500−350)`) — la revue croisée impose de le présenter comme un test de la **chaîne de contrôle**, pas comme une réduction d'exposition.
**Abstention** : chemin `INCONCLUSIVE` déjà prouvé (règle 4 prioritaire si une série manque) ; baseline A0 comparée : 2 signaux sur la fenêtre principale, **0 faux signal** sur la fenêtre contrôle 15–18/02/2023.

### g.2 Épisode rsETH / KelpDAO, 17–21 avril 2026 (jeu ÉVALUATION)

**Chaîne de décision (faits mesurés)**

| Instant (UTC) | Fait | Valeur | Statut |
|---|---|---|---|
| 18/04 17:35 | exploit exécuté (paquet LayerZero forgé, DVN 1-of-1 ; 116 500 rsETH libérés, nonce 308 vs 307 côté source) | ~292 M$ | FAIT SOURCÉ (LlamaRisk 20/04 ; Galaxy 22/04) |
| 18/04 18:00 | **plafond d'émission rsETH saturé : 99,9989 % (529 993,98/530 000)**, après +48 725 rsETH déposés en ~6 h | MESURÉ (on-chain, bloc 24 908 406) |
| 18/04 18:52 | gel des marchés annoncé par le Guardian (77 min après le drain) | FAIT SOURCÉ (Galaxy) |
| 18/04 19:03:59 | **`isFrozen` 0→1 (bloc 24 908 723) : la sortie est fermée** | MESURÉ (dichotomie, 14 itérations) |
| 19/04 08:00 | **WETH gelé, LTV 0 ; utilisation WETH 100,0079 %** ; **cash USDC d'Aave = 6 403 $ pour 2,47 Md$ de supply** (utilisation-cash ≈ 99,9997 %) | MESURÉ |
| 18–20/04 | oracle retenu rsETH : **2 526,76 $** à l'exploit → **2 513,66 $** au gel → **2 419,21 $** le 20/04, pendant que le marché décroche à **1 686 $** (divergence **−31 %**) | MESURÉ (oracle) / MESURÉ (marché, W2-B 1.3) |
| 20/04 | rapport d'incident : bad debt estimé **123,7 M$/230,1 M$** ; TVL DeFi −13 Md$ en 48 h | FAIT SOURCÉ (LlamaRisk/Aave ; Galaxy) |

**Hypothèses (à généraliser telles quelles dans v1)** : H1 « perturbation locale de venue » → **REFUTED** (invariant inter-chaînes violé + gel + divergence oracle/marché durable) ; H2 « stress d'actif/émetteur (rsETH non adossé) » → **SUPPORTED** (documents datés + saturation du plafond + gel) ; H3 « artefact » → **REFUTED** (faits concordants on-chain + documents ; 5/5 vérifications d'oracle identiques).
**Fait discriminant** : l'**invariant inter-chaînes** (« locké sur Ethereum ≥ minté sur les chaînes distantes », W2-B I1/I2/5.1-5.2 — le fait nommé par Chainalysis comme la seule détection possible) ; avant le gel, l'observation locale disponible était la **saturation du plafond** (18:00) ; après le gel, le fait discriminant devient l'**état de fermeture de la sortie** lui-même (isFrozen, utilisation-cash) — l'ordre de recherche v1 (rédaction (i) « réfuter le leader ») place précisément ces deux prédicats en tête.

**Candidat d'action bornée (v1, DAO)** : H2 SUPPORTED dès 18:00 avec A1–A3 levées → **A-D4/A-D2** (retirer les positions adossées à rsETH / sortir du LST) et **A-D3/A-D4** (désendetter, retirer des marchés Aave) bornés par la profondeur et le cash disponibles ; fenêtre d'exécution mesurée ≈ 1 h 29 (17:35 → 19:03:59) avant fermeture — cohérente avec le précédent réel : **KPK/ENS sort de ses positions Aave le 18/04, reconstruit en mai, sans perte** (FAIT SOURCÉ, KPK H1 14/08/2026). Après 19:03:59, la sortie rsETH est **fermée** (isFrozen) et celle des pools USDC/WETH quasi fermée (cash 6 403 $) : la sortie v1 honnête est **INCONCLUSIVE/ESCALATE (A3/A4)** avec `what_would_change` = un canal de sortie exécutable (redeemability), pas une instruction d'achat/vente. **MESURÉ + CONCEPTION.**
**Abstention** : c'est l'épisode d'évaluation où l'abstention **est** la bonne réponse après le gel — et où l'échec typique (détecter sans communiquer l'incertitude, arXiv:2610.12360) est directement référencé par la sortie `INCONCLUSIVE` enrichie (§c.3).

### g.3 Ce que les deux épisodes démontrent ensemble (et ce qu'ils ne démontrent pas)

- **Démontrent** : la chaîne « signal → hypothèses → fait discriminant → action bornée **ou** abstention » est exécutable sur données réelles, sans clé API, avec des nombres reproductibles (rejeu isolé : W3-B relance identique au bit près pour rsETH).
- **Ne démontrent pas** : une performance financière ou une supériorité prédictive (USDC 2023 est dans les données d'entraînement des modèles de 2026 ; rsETH reste un cas unique). Aucune revendication de gain sans évaluation gelée (V0.2 §9.4).
- **W2-D C.2 est respecté** : USDC + stETH en développement ; rsETH en évaluation ; xUSD exclu (pas de série de prix).

### g.4 Réconciliation à trancher avant le gel (MESURÉ (interne))

Deux conventions coexistent pour la même heure (11/03 07:00) : le corpus v0 utilise la **clôture** horaire Bitstamp (**0,86267**, `corpus/usdc_observations.csv`) et DeFiLlama horaire ; la reconstruction W3 utilise les **plus bas** horaires (**0,80526**) et la série chart DeFiLlama (0,876675 à 07:57:53Z). Les deux sont correctes, mais **un seuil comparé à des conventions différentes n'a pas le même sens** (le « worst case » change de 740 bps). **PROPOSITION** : geler, par source, une convention (ex. « stress = low ; référence = close ») et reporter les deux lectures partout où un seuil décide ; à faire avant G1 (gel de la fonction de perte).

---

## (h) Recommandations & questions ouvertes

### h.1 Recommandations (à transformer en décisions d'équipe)

1. **R1 — Adopter le format de record d'hypothèse de §a.3** (12 champs, critère de réfutation obligatoire, `p` = ∅/étiquettes, historique append-only). C'est le livrable 3.1 de la carte des zones d'ombre ; il conditionne tout le reste.
2. **R2 — Adopter le cycle de vie à 7 états (§a.4)** avec les 5 règles de transition, et l'exigence « un LLM ne retire jamais une hypothèse » (ARCHIVED, jamais supprimé).
3. **R3 — Livrer le mécanisme v1 RDOF (§b.2) et le tester contre l'ordre fixe** (essai T02/HYP-02R) : sans ce test, la VoI n'est pas activable. La VoI reste **hors du chemin critique** (`VOI_NOT_ESTIMABLE` autorisé).
4. **R4 — Adopter les 5 conditions d'abstention et le format `INCONCLUSIVE` enrichi (§c.3)** ; en particulier rendre `what_would_change_the_verdict` obligatoire (c'est ce qui transforme l'abstention en plan de recherche).
5. **R5 — Adopter les catalogues d'actions bornées (§d)** : DAO 8 actions, desk 4 ; toute action nouvelle passe par le même gabarit (déclencheur épistémique, seuil économique, bornes, coût, effet, applicabilité). Les actions on-chain non démontrables restent en **simulation** (honnêteté V0.2 §13.3).
6. **R6 — Matérialiser les 3 axes dans le dossier** (`epistemic_verdict` / `economic_action` / `authorization_verdict`) et écrire une fois pour toutes : « INCONCLUSIVE ≠ NO-ACTION » ; « DENY de politique ≠ échec épistémique ».
7. **R7 — Scénarios : qualitatif d'abord, prévision gelée avant observation, scoring a posteriori** (Brier/ECE, « non établi » sous N) ; ne jamais laisser une probabilité LLM entrer dans la décision.
8. **R8 — Trancher la réconciliation des conventions de prix (§g.4) avant G1** et l'inscrire dans le gel (SHA-256).
9. **R9 — `P(obligation)` : hypothèse explicite, gelée, avec sensibilité publiée** (les deux facteurs visibles) ; la revue d'équipe doit nommer qui la signe (G6).
10. **R10 — Conserver la séparation DEV/EVAL (USDC+stETH / rsETH+USD0++)** et l'embargo ; l'épisode rsETH ne doit pas servir à régler un seuil.

### h.2 Questions ouvertes

1. **Garde-fous exacts de la génération d'hypothèses par le LLM** : quel schéma de validation, qui valide la déduplication sémantique (fusion), et comment mesurer le coût de cette étape (budget par décision) ? (Lien bloc A — agents.)
2. **Conditions d'activation de la VoI** : quel N de cas gelés/calibrés, quel test d'acceptation, et qui re-calibre ?
3. **Calibration des seuils par quantiles** (W2-B chantier 5) : sur combien de fenêtres, et à quelle cadence ?
4. **Représentation de la « fermeture de sortie »** (redeemability) : faut-il un état explicite `exit_closed` distinct de `price` dans l'axe épistémique (rsETH l'impose) ?
5. **Cas xUSD / perte invisible à prix fixe** : le catalogue et les critères couvrent-ils l'« invisibilisation » (W2-B 4.1) sans série de prix exploitable ?
6. **Escalade : canal et SLA** — qui est escaladé, en combien de temps, et comment la latence humaine entre dans la fonction de perte ?
7. **Multi-épisodes simultanés** : le registre d'hypothèses est-il par cas ou global (le budget de recherche est-il partagé) ?
8. **Test de falsifiabilité des catalogues eux-mêmes** : quelle expérience montre qu'une action bornée fait mieux que NO-ACTION à coût égal (HYP-12R/T12) ?

### h.3 Non trouvé (à ne pas combler par des inventions)

- **Aucune évaluation publiée d'ACH intégrée à un agent LLM financier** (les travaux agents 2025-2026 sont en science/santé/TCM — arXiv:2502.09858, 2610.18298).
- **Aucune distribution publique de scénarios de dépeg** ni de fréquence P(obligation) pour une trésorerie de DAO (W2-D §(f) point 6 ; non trouvé confirmé le 15/10/2026).
- **Aucun budget de risque chiffré publié par une DAO** (plafond de perte par épisode) — l'IPS ENS impose un *rapport* de drawdown, pas un plafond.
- **Prix publics des fournisseurs de risque** (Chaos Labs, Gauntlet, Hypernative, LlamaRisk…) : non publics (U2).
- **Objectifs chiffrés de desks** (Sharpe cible, budget de drawdown) : non trouvés (W2-D).
- **Coût exact d'un swap « de crise » sur CoW/Curve pour une trésorerie DAO pendant un week-end de fermeture du primaire** : non mesuré (seule la profondeur en calme et la décote LST sont mesurées).

---

## Sources (URL + dates)

**Externes (consultées le 15 octobre 2026, sauf mention)** :

1. Heuer, R. J. — *Psychology of Intelligence Analysis* — CIA, 1999 — https://cia.gov/resources/csi/static/Pyschology-of-Intelligence-Analysis.pdf *(texte intégral non extrait ; page/index consultés)*.
2. CIA — *A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis* — mars 2009 — https://cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf *(extrait)*.
3. Mandel, D. R., Karvetski, C. W., Dhami, M. K. — *Boosting intelligence analysts' judgment accuracy: What works, what fails?* — Judgment and Decision Making 13(6):607–621, novembre 2018 — DOI 10.1017/S1930297500006628 — https://www.cambridge.org/core/journals/judgment-and-decision-making/article/.../1530E9DAE8F42B2E8FC2B5FE374DB50F *(PDF extrait)*.
4. *Effects of task structure and confirmation bias in alternative hypotheses evaluation* — Cognitive Research: Principles and Implications 9:37, 13 juin 2024 — DOI 10.1186/s41235-024-00560-y — https://ncbi.nlm.nih.gov/pmc/articles/PMC11169332 *(abstract vérifié via Europe PMC)*.
5. Popper (framework) — *Automated Hypothesis Validation with Agentic Sequential Falsifications* — arXiv:2502.09858, 14 février 2025 — https://arxiv.org/abs/2502.09858.
6. *Output Discipline Sets the Floor: A Falsification-Guided, Model-Agnostic Agent Protocol…* — arXiv:2610.18298 — https://arxiv.org/html/2610.18298v1 *(extrait)*.
7. *Accurate but Not Humble: Evaluating Epistemic Humility in LLM Agents under Knowledge Conflict* — arXiv:2610.12360, 8 octobre 2026 — https://arxiv.org/abs/2610.12360.
8. *On Open-Ended Information Seeking for Information Elicitation Agents* — arXiv:2610.07509, 5 octobre 2026 — https://arxiv.org/abs/2610.07509.
9. Chow, C. K. — *On Optimum Recognition Error and Reject Tradeoff* — IEEE Trans. Inf. Theory, 1970 — DOI 10.1109/tit.1970.1054406.
10. *Machine learning with a reject option: a survey* — Machine Learning 113:3073–3110, publié 29 mars 2024 — DOI 10.1007/s10994-024-06534-x — https://link.springer.com/doi/10.1007/s10994-024-06534-x *(extrait)*.
11. Strong, J., Sun, E., Rogers, H., Higham, H., Noble, A. — *Learning to Defer: A Survey* — preprint Zenodo v1.0, décembre 2025 — DOI 10.5281/zenodo.17843044.
12. Madras, D. et al. — *Predict Responsibly…* — arXiv:1711.06664 — https://arxiv.org/html/1711.06664v3 *(snippet)*.
13. *Cost-Sensitive Conformal Prediction and Human-in-the-Loop Abstention…* — arXiv:2607.27143, 29 juillet 2026 — https://arxiv.org/abs/2607.27143.
14. Brier, G. W. — *Verification of forecasts expressed in terms of probability* — Monthly Weather Review 78(1):1–3, 1950 — https://journals.ametsoc.org/view/journals/mwre/78/1/1520-0493_1950_078_0001_vofeit_2_0_co_2.pdf.
15. Gneiting, T., Raftery, A. E. — *Strictly Proper Scoring Rules, Prediction, and Estimation* — JASA 102(477):359–378, 2007 — https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf.
16. Avellaneda, M., Stoikov, S. — *High-frequency trading in a limit order book* — Quantitative Finance 8(3):217–224, avril 2008 — https://math.nyu.edu/inmemoriam/avellaneda//HighFrequencyTrading.pdf.
17. MakerDAO (NewsBTC via cryptonews.net) — *How MakerDAO Intervened, Saving DAI From Depegging* — 13 mars 2023, 15:30 UTC — https://cryptonews.net/news/altcoins/20663169/ *(extrait)* ; *MakerDAO Weighs Using Emergency Switch…* — https://cryptonews.net/news/altcoins/20662841.
18. LlamaRisk (Aave) — *rsETH Incident Report (April 20, 2026)* — 20 avril 2026, 20:12 UTC — https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580 *(extrait)*.
19. Galaxy Research — *KelpDAO/LayerZero Exploit Drains $290m, Freezes DeFi Markets* — 22 avril 2026 — https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi *(via U2)*.
20. Depegwatch — *How to Hedge Against Stablecoin Depegs Using On-Chain Derivatives* — 19 septembre 2025 — https://depegwatch.com/2025/09/19/how-to-hedge-against-stablecoin-depegs-using-on-chain-derivatives *(snippet)*.
21. Sources déjà citées dans les rapports internes (FAIT SOURCÉ au sens des rapports) : Fed FEDS Notes 17/12/2025 (SVB/USDC/PSM) ; ENS IPS 6.46 (8 mai 2026) ; KPK H1 2026 (14 août 2026) ; Lido Q1 2026 (4 juin 2026) ; Eco (depeg / best practices) ; Chaos Labs (6 avril 2026) ; Dong et al. ACL 2026 ; Papamarkou et al. arXiv:2605.00742 (1er mai 2026) et HAL 27 janvier 2026 ; Heath et al. Med Decis Making (16 avril 2020) ; Kaddour et al. arXiv:2602.06948 (6 février 2026) ; Bailey & López de Prado JPM 40(5), 2014 — voir `research/R1_orchestration_VOI.md`, `research/W2D_objectifs_mesure.md`, `research/U2_defi_organisations.md`.

**Interne (MESURÉ)** :

- `evidence/episode_usdc_2023-03.json`, `evidence/decision_usdc-2023-03.json`, `evidence/baseline_report.json`, `evidence/episode_rseth_2026-04.json`, `evidence/episode_steth_2022-06.json` ; `corpus/usdc_observations.csv`.
- `research/W2B_signaux_detection.md` ; `research/W2D_objectifs_mesure.md` ; `research/W3_reconstruction_usdc2023.md` ; `research/W3_reconstruction_rseth_steth.md` ; `research/R1_orchestration_VOI.md` ; `research/REVUE_CROISEE_ET_CADRE_CONCRET.md` ; `research/SYSTEME_ZONES_OMBRE.md` ; `research/U2_defi_organisations.md` ; `src/orvyren/decision/{scenarios,engine,baseline,exposure}.py` ; `research/W2C_enveloppe_execution.md`.
- Matière brute de ce chantier : `research/raw_b3/` (voir `notes_b3_sources.md`).

*Fin du document. Aucun fichier du dépôt n'a été modifié en dehors de `research/` ; aucun commit effectué.*
