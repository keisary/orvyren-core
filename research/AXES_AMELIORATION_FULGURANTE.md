# AXES D'AMÉLIORATION FULGURANTE — ORVYREN
## Document d'analyse et de recherche — v3 (consolidée, avec socle MIMIR/DFKG et registre d'hypothèses)

**Date** : 14 octobre 2026 · **Destinataire** : équipe ORVYREN + analyse externe (GPT Astra)
**Pièces liées** : `R1_orchestration_VOI.md` (20 sources vérifiées) · `R2_permissions_onchain.md` (458 lignes, contrats vérifiés on-chain) · `R3_evaluation_benchmark.md` (58 URL) · `figures/orvyren_cycle_complet.png` · socle de référence : `D:\midas_v2\MIMIR\docs\MIMIR_Technical_Design.md` (V3 gelée) + `MIMIR_Critical_Review_v3.md`

**Comment utiliser ce document** : la §0 donne le constat, la §1 le socle MIMIR/DFKG à exploiter (définitions, types de relation), la §2 les acteurs et l'observation du monde, la §3 les axes d'amélioration sourcés, la §4 le fonctionnement cible, la **§5 le registre d'hypothèses (HYP-01…HYP-15) — c'est le cœur du document à analyser** — et la §6 les questions ouvertes posées à la recherche.

---

## 0. Constat, sans détour

Le prototype actuel est un **pipeline déterministe sur un seul cas** (décrochage USDC mars 2023) : collecte multi-sources, classification de 3 hypothèses pré-enregistrées, baseline A0, politique déterministe hors LLM, instruction on-chain non signée + vérification de reçu, dossier d'audit. **116 tests verts**, preuves réelles, corpus de 1 375 observations.

Ce qui **n'existe pas encore** — et se joue précisément là : pas d'agent (pas de boucle planifier → outil → évaluer), **pas de registre de branches**, pas de calcul de valeur de l'information, pas de calibration, exposition en valeurs de démonstration. Vue complète : `figures/orvyren_cycle_complet.png` (1 station verte = faite et testée · 5 orange = partielles · 3 rouges = à construire).

---

## 1. Le socle : MIMIR / DFKG — ce qu'on réutilise, ce qu'on adapte, ce qu'on étend

ORVYREN ne doit pas réinventer sa couche de connaissance : **MIMIR a déjà défini, gelé (V3) et spécifié un substrat complet — le Dynamic Financial Knowledge Graph (DFKG)**. La stratégie retenue : **le graphe d'abord** — ORVYREN instancie une tranche T0 du DFKG, puis l'étend. Voici exactement ce que MIMIR fournit.

### 1.1 Le modèle d'objets (MIMIR §10.1) — à reprendre tel quel

- **Couche monde** : `Entity` (**acteurs, institutions, actifs, marchés, variables économiques**), `Event`, `Relation`.
- **Couche connaissance** : `Observation`, `Claim`, `Evidence`, `Hypothesis`, `Prediction`, `Outcome`.

**Pourquoi c'est structurant pour ORVYREN** : nos objets actuels (observation, claim, hypothèse, décision) sont un sous-ensemble non nommé de ce modèle. En adoptant les définitions MIMIR, on hérite d'un vocabulaire vérifié, d'une discipline de preuve, et de la compatibilité avec le système macro-financier existant.

### 1.2 Les identifiants canoniques (MIMIR §10.2)

`VAR-` (variable économique) · `SER-` (série source) · `EVT-` (événement) · `OBS-` (observation) · `CLM-` (claim) · `REL-` (relation causale) · `SCN-` (scénario) · `FCT-` (prévision) · `THS-` (thèse de trade) · `OUT-` (résultat). Les identifiants externes (ids de séries, dates de vintage) sont des **champs de preuve, jamais des clés**.

### 1.3 Les six horloges (MIMIR §10.5) — le cœur de l'anti-fuite temporelle

Chaque objet porte **six temps** : `event`, `publication`, `observation`, `effective`, `validity`, `revision`. **C'est ce que notre corpus ne fait pas encore complètement** : nous avons `ts_event` et `retrieved_at`, il manque les temps de publication/effectivité/validité/révision — indispensables pour prouver qu'une décision n'utilise que ce qui était *public* à l'instant simulé.

### 1.4 La chaîne de provenance (MIMIR §10.5) — à adopter intégralement

`Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome`, **chaque flèche étant une ligne de lien explicite** — « pour qu'un verdict puisse être remonté du P&L jusqu'à la source ». Notre `verify_chain` (claims → observations → sources) est un début ; MIMIR ajoute les maillons `Extraction`, `Prediction`, `Outcome` — ce sont eux qui manquent pour relier une décision à son résultat.

### 1.5 Le *Relation record* — les types de relation (MIMIR §11.2)

**C'est le point que tu demandes d'exploiter en priorité.** Chaque relation causale est un enregistrement typé à 10 champs :

| Champ | Signification | Exemple |
|---|---|---|
| `relation_id` | identifiant | `REL-01` |
| `cause` / `effect` | références d'objets | `EVT:FOMC_DECISION.surprise → VAR:DGS2` |
| `mechanism` | mécanisme en une étiquette | `short-rate-expectations` |
| `conditions` | prédicats d'état/régime sous lesquels la relation est affirmée | « régime haute volatilité » |
| `regime_scope`, `horizon_scope` | portée déclarée | `h ≤ 5 j` |
| `epistemic_status` | **`CAUSAL-DOCUMENTED` / `CAUSAL-HYPOTHESIS` / `MODELLED`** | — |
| `sign_prior` | signe attendu (+/−/ambigu) | `+` si surprise hawkish |
| `provenance` | référence littérature ou mécanisme documenté | — |
| `lifecycle` | **`DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED`** (+ `REACTIVATION CANDIDATE`) | — |

**Exemples réels de la carte curatée MIMIR (T0, ensemble confirmatoire complet)** : `REL-01` surprise de politique → taux 2 ans (repricing des anticipations, documenté, h ≤ 5 j) · `REL-02` → taux 10 ans (chemin anticipé + prime de terme, h ≤ 20 j) · `REL-03` → change USD (différentiel de taux/carry, h ≤ 20 j) · `REL-04` → indices actions (canal du taux d'actualisation, h ≤ 20 j) · `REL-05` → pétrole (canal demande vs canal dollar, **hypothèse**, ambigu, h ≤ 60 j) · `REL-07` état de risque × surprise → actions (**amplification dépendante de l'état**, h ≤ 5 j) · `REL-08` état d'inflation × surprise → taux (asymétrie de la fonction de réaction) · `REL-09` pétrole → anticipations d'inflation → taux (transmission de second ordre, ambigu) · `REL-10` actions → sentiment de risque → FX.

**Règles MIMIR à reprendre telles quelles** : une relation `CAUSAL-DOCUMENTED` entre dans le chemin confirmatoire avec sa provenance stockée comme claim ; une relation `CAUSAL-HYPOTHESIS` est évaluée dans le même run mais **rapportée distinctement** ; une relation dont l'effet estimé contredit son signe documenté au-delà de la bande pré-enregistrée est **signalée, jamais silencieusement conservée**, et passe en `EVALUATING`.

**Ce que ça change concrètement pour ORVYREN** : nos trois hypothèses (H1 perturbation locale / H2 stress / H3 artefact) deviennent des **nœuds de la couche connaissance reliés par des `Relation` typées** — par exemple : `OBS:prix-bitstamp-07h → CLM:divergence-ville → HYP:perturbation-locale` (relation `SUPPORTS`), et `OBS:offre-24h → CLM:contraction → HYP:stress-reel` (relation `SUPPORTS`, avec `sign_prior` et portée temporelle).

### 1.6 Labels épistémiques et cycles de vie (MIMIR §0.3)

**Labels** : `FACT` · `REPORTED` · `STATISTICAL` · `CAUSAL-DOCUMENTED` · `CAUSAL-HYPOTHESIS` · `MODEL-INFERRED` · `REJECTED`. **Règle** : « une hypothèse ne devient jamais silencieusement une base de conception établie ; toute affirmation portant un label le conserve dans chaque document qui la cite ». **Statuts** : `DECIDED` · `DECIDED DIRECTION` · `CANDIDATE` · `OPEN` · `REJECTED` · `DEFERRED`.

**C'est l'équivalent mature de notre distinction FAIT SOURCÉ / MESURE / HYPOTHÈSE / INCONNU** — à adopter pour rendre ORVYREN lisible par quiconque connaît MIMIR.

### 1.7 Ce que MIMIR fait et qu'on doit rattraper (leçons structurelles)

1. **Pré-enregistrement gelé et haché** (MIMIR §5.5) : le paquet de pré-enregistrement est figé au jalon M0, haché, référencé par chaque run d'audit. Notre « règle de décision gelée » est l'embryon — MIMIR en fait un objet versionné.
2. **Matrice de falsification + ordre des tests (du moins cher au plus cher)** (§5.2-5.3) et **politique de multiplicité par familles de tests** (§5.4) — nous n'avons rien de tel.
3. **Portes d'échec canoniques et plan de puissance statistique** (§5.6-5.7) — le pendant exact de ce que R3 recommande (puissance ≈ 93 fenêtres → ne rien revendiquer).
4. **Propagation bornée** (§11.4) : « jamais comme un parcours de graphe non contraint » — structure + mécanismes actifs + conditions d'état + délais + probabilité + rétroaction, avec itération bornée et décroissance. À reprendre pour toute propagation d'effets dans ORVYREN.
5. **Journal d'audit natif + attribution d'erreur + révision** (§13.3-13.5) : chaque erreur est attribuée (donnée ? modèle ? décision ?) et chaque révision est un objet. Notre dossier doit s'aligner.
6. **États de sûreté et opération dégradée** (§13.7) : le système sait dire *dans quel état* il est. À reprendre.

### 1.8 Ce qu'on adapte (écarts assumés)

| Point MIMIR | Adaptation ORVYREN | Raison |
|---|---|---|
| T0 sans base graphe (tables relationnelles Parquet/DuckDB, ADR-002) | idem : SQLite/tables + liens explicites | cohérent avec la décision MIMIR, pas de dépendance |
| Carte causale macro (FOMC, taux) | **notre cas** : stress de stabilité (stablecoins/USDC), acteurs bancaires, trésorerie | le DFKG est instancié sur un autre sous-domaine, la structure est identique |
| Système de **trading** multi-actifs | ORVYREN = brique **décision + politique + exécution bornée** (et, en cible, recommandations de trading) | ORVYREN est un consommateur/procuration du DFKG, pas un concurrent |

### 1.9 Extension expérimentale : DFKG × Deep Learning / ML (à défricher)

**Étiquetage obligatoire : tout ce qui suit est `CAUSAL-HYPOTHESIS` / `MODEL-INFERRED` — très expérimental.**

MIMIR exclut volontairement la découverte automatique de relations du T0 (§11.2 : « automatic discovery is out of T0 »). C'est précisément l'espace où du ML peut se brancher sur le DFKG, à condition de ne jamais court-circuiter la discipline épistémique :

1. **Extraction et résolution** — NER/entity linking vers les `Entity` (banques, régulateurs, actifs), extraction d'événements depuis les communiqués (date de publication, pas de fuite temporelle), déduplication d'événements (MIMIR §10.4 laisse ce chemin au tier FULL).
2. **Découverte de relations assistée** — prédiction de liens sur le graphe (relations manquantes entre `Entity`/`Event`/`VAR`), plongements temporels de graphe de connaissance (TKG embeddings), extraction de relations par LLM sous contrainte de schéma strict (avec provenance littérature obligatoire avant tout passage en `CAUSAL-DOCUMENTED`).
3. **Estimation d'effets** — MIMIR utilise des projections locales (ADR-010) ; alternative expérimentale : attendre une qualité supérieure d'un modèle relationnel/apprenant la transmission. À comparer **à budget de données égal**, avec la même discipline de porte d'échec.
4. **Propagation apprise** — remplacer la propagation bornée manuelle par un réseau de passage de messages sur le graphe, en gardant la contrainte « pas de parcours non contraint » et la traçabilité des relations utilisées (§11.4).
5. **Régimes** — classification probabiliste de régime (MIMIR §11.7 admet `UNKNOWN`) par modèle séquentiel, avec calibration obligatoire.
6. **Détection de contradictions** — apparier des claims qui se contredisent (embeddings + NLI) pour alimenter le critique adversarial.
7. **Confiance d'extraction** — score de qualité de chaque extraction qui devient un attribut d'observation, jamais un fait.

**Règle d'or** (non négociable) : le ML **propose**, le pipeline déterministe **dispose** ; toute sortie de modèle est étiquetée et n'entre jamais dans un calcul financier comme un chiffre établi.

---

## 2. Acteurs et observation du monde

**Les acteurs à modéliser explicitement** (couche `Entity` du DFKG) — pas seulement « le marché » :

| Catégorie | Acteurs | Ce qu'Orvyren observe d'eux |
|---|---|---|
| **Bancaires** | banques commerciales, banques centrales (régulateur monétaire), trésoriers de banque | décisions de politique, communiqués, flux de dépôts/réserves, expositions interbancaires |
| **Marchés** | teneurs de marché, exchanges, fonds, market makers de stablecoins | profondeur, écarts de prix par venue, stress de liquidité, flux de redemption |
| **Émetteurs / infrastructures** | émetteurs de stablecoins, custodians, réseaux (chaînes), oracles | déclarations datées, preuves de réserves, incidents on-chain |
| **Réglementaires / surveillance** | FSB, BCE, Fed, régulateurs nationaux | textes, alertes, changements de règles (contrainte réelle du système) |
| **Entreprises (client final)** | trésoriers d'entreprises, PME, importateurs/exportateurs | expositions réelles, contraintes de trésorerie (notre utilisateur actuel) |

**Observation globale du monde** — le DFKG ne doit pas être un graphe de prix : il doit porter l'**état du monde** (MIMIR §11.6, *world state record*) : régime monétaire, conditions de liquidité, tensions d'acteurs, événements en cours, incertitude déclarée (avec `UNKNOWN` autorisé). Pour ORVYREN, cela veut dire observer : le prix **et** la capacité de sortie, les acteurs **et** leurs contraintes, les événements **et** leur fenêtre de validité.

**Dimension trading** — ORVYREN n'est pas un robot de trading, mais ses décisions doivent s'intégrer au monde du trading : impact du portefeuille, coûts, horizon d'exécution, et — en cible — produire des **thèses de trade** (`THS-`) avec thèse, invalidation, taille, et P&L suivi en **paper trading** (MIMIR §12.7-12.8 : exécution papier, coûts, P&L — jamais de fonds réels dans le prototype).

---

## 3. Les axes d'amélioration (consolidés, sourcés)

| Axe | Contenu | Fondement sourcé | Priorité |
|---|---|---|---|
| **A — Orchestration bayésienne (valeur de l'information)** | ne chercher que ce qui peut changer la décision ; arrêt calculé `VoI(q) − c` | arXiv:2605.00742 (§4.1) ; ACL 2026 pp. 42879–42896 (meilleur que seuils manuels dans 18/20 conditions, +1,36 pt) ; arXiv:2601.01522 (postérieure mono-LLM inadéquate) | **P0** |
| **B — Registre de branches** | hypothèses vivantes (preuves pour/contre, critères de réfutation, probabilité, historique) ; ablation A1/A2 | conception V0.2 §7 ; MIMIR `Hypothesis` + catégories de cycle de vie | **P0** |
| **C — Permission on-chain réelle** | double verrou : politique hors chaîne + **mandat borné appliqué par la chaîne** (ERC-7715 `erc20-token-periodic`, 300 USDC/période de 24 h, octroi humain unique) | EIP-7715 ; MetaMask Delegation Toolkit ; **contrats vérifiés par nos soins sur Base Sepolia le 14/10/2026** (DelegationManager déployé, Enforcer déployé ; Safe Allowance **absent** → écarté) ; repli Coinbase Spend Permissions | **P1** |
| **D — Audit reconstructible + abstention de plein droit** | journal d'étapes chaîné par hash ; le LLM canonise, le pipeline calcule ; abstention = sortie de première classe | arXiv:2606.00671 (« confiant et faux indiscernable de confiant et juste ») ; arXiv:2603.20449 (solveur en pré-condition) ; OTel : `gen_ai.*` déprécié le 12/06/2026, dépôt dédié **sans release** au 12/10/2026 → héberger son propre journal (17a-4) | **P0** |
| **E — Évaluation qui rend crédible** | regret (faux positif/négatif séparés) + Brier/décomposition + ECE + conformal + **placebo B0** (200 tirages) + ablations ; puissances : ≈ 93 fenêtres/groupe → **ne rien revendiquer** | R3 (protocole complet) ; UK Treasury Committee HC 684 (20/01/2026) ; BoE/FCA (avril 2026) ; FSB (10/06/2026) | **P0/P1** |
| **F — Moteur de risque réel** | fin des valeurs 500/350 : portefeuille modélisé, décotes, horizons, fonction d'utilité explicite | MIMIR §12.5 (impact portefeuille) ; §4.1 (fonction d'objectif) | **P0** |
| **G — Calibration gouvernée** | prévisions gelées, Brier/ECE, ajustement des seuils par procédure | arXiv:2602.06948 (22 % réel vs 77 % déclaré) ; MIMIR §13.3 (attribution d'erreur) | **P1** |
| **H — Acteurs séparés** | analyste / critique / risque / conformité / signataire — chacun justifié par ablation | conception §8 ; MIMIR §13.5 (audit natif) | P2 |
| **I — Système qui tourne** | surveillance continue, multi-actifs, reprise, journal d'épisodes | MIMIR §13.6 (drift) ; urgence : endpoints DeFiLlama `/pools` `/chart` ferment le **13/11/2026** | P2 |
| **J — Preuve élargie** | liquidité on-chain profonde, redemption, preuves de réserves | MIMIR §7.3 (familles de données) ; §7.8 (règles d'évaluation) | P2 |
| **K — Banc d'attaques 7 → 12** | + frontière de période (effet 2×), révocation en cours d'exécution, oracle, accumulation, calldata mal décimé ; borne de Wilson publiée | R2 (limite on-chain) ; R3 (recommandation) | **P1** |

---

## 4. Le fonctionnement optimal et complet (cible)

**DFKG d'abord** : une couche de connaissance (objets MIMIR, six horloges, chaîne de provenance, relations typées) alimentée par des connecteurs multi-acteurs, avec un état du monde explicite et une incertitude déclarée. **Puis la boucle** : surveillance → épisode → branches concurrentes probabilisées → calculateur de valeur de l'information → agent de recherche à outils bornés (lecture seule) + critique adversarial → verdicts mis à jour → décision sous contrainte d'utilité (impact portefeuille, coûts, horizon) → **double verrou** (politique déterministe, puis mandat on-chain) → exécution humaine/signataire → vérification du reçu → **journal reconstructible** → calibration périodique gouvernée. L'abstention (`INCONCLUSIVE`) est une sortie normale, chiffrée (ce qui manquait, à quel coût).

**Invariants** : (1) aucun chiffre déterminant ne vient d'un LLM ; (2) aucune action sans les deux verrous ; (3) aucune conclusion sans provenance ; (4) rien n'est supprimé (branches mortes, refus) ; (5) tout label épistémique se conserve dans chaque document qui cite l'affirmation ; (6) l'arrêt et l'abstention sont des décisions.

---

## 5. REGISTRE D'HYPOTHÈSES (le cœur du document)

Format : énoncé · statut · label · critère de soutien · critère de réfutation · données requises · coût. Chaque hypothèse est écrite pour être **attaquable** — c'est le but.

| ID | Énoncé (en une phrase) | Statut | Label |
|---|---|---|---|
| HYP-01 | Un graphe de connaissance typé (DFKG : objets MIMIR, six horloges, chaîne de provenance, relations typées) réduit les conclusions prématurées par rapport à un pipeline plat, à budget égal | OPEN | CAUSAL-HYPOTHESIS |
| HYP-02 | Une politique d'arrêt par valeur de l'information (`VoI(q) − c ≥ 0`) égale ou dépasse les seuils réglés à la main sur nos propres fenêtres | OPEN | STATISTICAL |
| HYP-03 | Le registre de branches (3-5 hypothèses explicites, avec réfutation enregistrée) améliore la qualité de décision mesurée par le regret, et bat un placebo apparié | OPEN | CAUSAL-HYPOTHESIS |
| HYP-04 | Le label épistémique change la décision : une conclusion reposant uniquement sur des relations `CAUSAL-HYPOTHESIS` est significativement plus souvent classée INCONCLUSIVE/REPORTED | OPEN | MODEL-INFERRED |
| HYP-05 | Le double verrou (politique + mandat on-chain) empêche 100 % des actions hors enveloppe sur un banc de 12 attaques, mais introduit un effet de frontière de période mesurable (dépense 2× possible en limite de période) | OPEN | STATISTICAL |
| HYP-06 | La calibration des probabilités est meilleure quand elles sont élicitées avant exécution en cadrage « recherche de bug » que par confiance déclarée | OPEN | STATISTICAL |
| HYP-07 | Une extension ML du DFKG (plongements de graphe / prédiction de liens) retrouve des relations manquantes de la carte curatée, mesurée en précision@k sur des relations tenues à l'écart | OPEN | MODEL-INFERRED |
| HYP-08 | L'observation multi-acteurs (banques, infrastructures, régulateurs) améliore la précision du diagnostic d'épisode par rapport aux seules données de marché (détection plus précoce ou moins de faux signaux) | OPEN | CAUSAL-HYPOTHESIS |
| HYP-09 | La décision bornée (réduire l'exposition de 100) a un regret inférieur à la baseline A0 sur les épisodes historiques, **nette des coûts**, sans supériorité statistique revendiquée | OPEN | STATISTICAL |
| HYP-10 | Un tiers indépendant peut recalculer la décision à partir des seules sources archivées (reproductibilité), y compris la remontée `Outcome → Source` | OPEN | FACT (testable) |
| HYP-11 | La séparation des rôles (propose / réfute / valide / exécute) réduit le taux de décisions fausses sur le banc adversarial par rapport à un agent unique | OPEN | CAUSAL-HYPOTHESIS |
| HYP-12 | L'abstention (INCONCLUSIVE) produit un regret inférieur à une action forcée quand la preuve manque (fenêtres à données trouées) | OPEN | STATISTICAL |
| HYP-13 | Les acteurs bancaires/financiers produisent des comportements corrélés détectables (herding) qui constituent un signal exploitable avant le mouvement de prix | OPEN | CAUSAL-HYPOTHESIS |
| HYP-14 | Une carte de relations apprise par ML (au lieu de curatée) améliore le pouvoir prédictif mais **dégrade la traçabilité** — mesurer le compromis | OPEN | MODEL-INFERRED |
| HYP-15 | La propagation bornée (délais, décroissance, itération limitée) surpasse une propagation libre du graphe, y compris avec un graphe enrichi par ML | OPEN | MODEL-INFERRED |

### Détail des hypothèses clés

**HYP-01 — La valeur du graphe.**
*Soutien* : meilleure traçabilité et moins de conclusions prématurées sur fenêtres pré-enregistrées (mesure : taux de décisions infirmées après coup, à budget égal).
*Réfutation* : performances identiques au pipeline plat sur ≥ 3 fenêtres, ou coût de structure non justifié.
*Données* : notre corpus (USDC mars 2023 + fenêtre témoin) + 2 épisodes supplémentaires (UST mai 2022, stETH juin 2022 — datasets publics à vérifier).
*Coût* : élevé (structure de graphe + requêtes as-of). *C'est l'hypothèse la plus stratégique : elle décide si ORVYREN adopte le DFKG ou une version « plate ».*

**HYP-02 — L'arrêt par valeur de l'information.**
*Soutien* : `VoI(q) − c ≥ 0` avant chaque recherche ; sur nos fenêtres, égaler ou battre un seuil manuel réglé — condition de réplication du résultat ACL (18/20).
*Réfutation* : la politique VOI consomme plus de budget pour une qualité égale, ou l'incertitude des probabilités subjectives rend le calcul inexploitable.
*Données* : les nôtres + protocole R3. *Coût* : moyen (peut être une bibliothèque standard).

**HYP-05 — Le double verrou et sa limite.**
*Soutien* : 12/12 attaques refusées, dont ≥ 1 refus par la chaîne elle-même (transaction revertée visible sur BaseScan) ; borne de Wilson publiée.
*Réfutation* : une attaque passe, **ou** l'effet de frontière de période (dépense 2× en limite) est exploitable en pratique.
*Données* : Base Sepolia + ERC-7715 (contrats déjà vérifiés déployés). *Coût* : moyen ; dépend d'un octroi humain (extension MetaMask ≥ 13.23.0) ou du repli Coinbase.

**HYP-08 — L'observation du monde comme avantage.**
*Soutien* : sur les épisodes, des variables d'acteurs (flux, communiqués datés, liquidité on-chain) améliorent la précision ou l'avance du diagnostic vs prix seuls.
*Réfutation* : aucune amélioration hors échantillon, ou l'amélioration disparaît quand on tient compte du coût des données.
*Données* : communiqués datés (Circle, Fed, FSB), données on-chain (profondeur des pools), séries de flux. *Coût* : élevé.

**HYP-13 — Herding bancaire.**
*Soutien* : détection d'une corrélation de comportement (horodatages, tailles, séquences) précédant un mouvement — à définir avec précision, car c'est un sujet réglementaire actif (BoE/FCA, avril 2026).
*Réfutation* : le signal n'est qu'un artefact d'agrégation ou disparaît sous contrôle de volatilité.
*Coût* : élevé, très expérimental — à traiter comme recherche exploratoire, pas comme argument de vente.

---

## 6. Questions ouvertes posées à la recherche (pour GPT Astra)

1. **DFKG × ML** : quelles méthodes 2025-2026 sont réellement déployables sur un graphe financier temporel *sans* dégrader la traçabilité (TKG embeddings, R-GCN, TGN, GNN explicables) ? Quelles garanties de provenance existe-t-il pour des relations apprises ?
2. **Types de relation** : la liste MIMIR (`CAUSAL-DOCUMENTED` / `CAUSAL-HYPOTHESIS` / `MODELLED` + lifecycle + portée) est-elle suffisante pour le domaine bancaire/stabilité, ou faut-il d'autres catégories (par ex. `REGULATORY-CONSTRAINT`, `LIQUIDITY-MECHANISM`) ?
3. **Acteurs bancaires** : quelles données publiques et datées permettent d'observer des acteurs bancaires (dépôts, réserves, expositions) sans accès privilégié ?
4. **Trading** : comment mesurer proprement le regret d'une décision de réduction d'exposition quand la vérité terrain est « ce qui aurait été le mieux ex post » — et quelles précautions anti-optimisme du benchmark ?
5. **VOI** : comment estimer une valeur d'information robuste quand les probabilités sont subjectives et les coûts hétérogènes (latence, argent, réputation) ?
6. **Multi-acteurs** : comment tester HYP-13 (herding) sans se raconter d'histoires (contrôles, placebo, pré-enregistrement) ?
7. **Abstention** : quelle est la littérature 2025-2026 sur l'abstention comme décision de premier ordre dans les systèmes financiers ?

---

## 7. Priorisation avant le 20 octobre 2026 (15 h 59 UTC)

**P0** — branches + VOI minimal (HYP-02, HYP-03) · moteur de risque réel + fonction de perte gelée et hachée (HYP-09) · journal reconstructible + abstention (HYP-10) · placebo B0 et regret (R3).
**P1** — mandat on-chain + démonstration « DENY par la chaîne » (HYP-05) · banc d'attaques étendu (12) · registre de prévisions gelées (HYP-06).
**P2** — extension ML du DFKG (HYP-07, HYP-14, HYP-15) · acteurs bancaires et herding (HYP-08, HYP-13) · rôles séparés (HYP-11) · système continu.

**Ce qu'on affirme au jury (sans mentir)** : nos recherches sont conduites comme une réplication ouverte (sources publiées, critères de réfutation pré-enregistrés, placebo obligatoire) ; nous ne revendiquons aucune supériorité statistique — nous démontrons la **faisabilité de la mesure** et la **traçabilité de bout en bout**.

---

## Annexe — Sources clés

arXiv:2605.00742 (orchestration bayésienne, 01/05/2026) · hal-05480691 (27/01/2026) · ACL 2026 pp. 42879–42896 (arrêt par valeur de l'information) · arXiv:2601.01522 (04/01/2026) · arXiv:2606.00671 (LLM canoniseur, abstention) · arXiv:2603.20449 (solveur en pré-condition) · arXiv:2607.04096 (contrats typés) · arXiv:2602.06948 (sur-confiance, 06/02/2026) · EIP-7715 + MetaMask Advanced Permissions + Relay (04/2026) + contrats vérifiés Base Sepolia (nous, 14/10/2026) · OpenTelemetry v1.42.0 (12/06/2026) + ibl.ai (17a-4, 12/10/2026) · UK Treasury Committee HC 684 (20/01/2026) + BoE/FCA (avril 2026) + FSB (10/06/2026) · Vals AI Finance Agent v1.1 · arXiv:2607.19238 (FinanceComplexQA) · MIMIR : `MIMIR_Technical_Design.md` §0.3, §5, §10, §11.2, §11.4, §11.6, §12.5, §12.7, §13 (V3 gelée).

*139 sources uniques au total dans les trois rapports de recherche `research/R1_*.md`, `R2_*.md`, `R3_*.md`.*
