# B7 — ÉTUDE DU BLOC APPRENTISSAGE & ÉVALUATION
### Pipeline outcomes · calibration (Brier/ECE/Wilson) · moteur de rejeu (2 modes) · jeux DEV/EVAL · harnais A0/A1/A2/B0 · apprentissage v1 vs V2

**Version 1 — 15 octobre 2026** (rédaction ~12 h 50 UTC). Auteur : sous-agent B7.
**Livrable** : `D:\orvyren_core\research\B7_EVALUATION_ETUDE.md`. **Matière brute** : `D:\orvyren_core\research\raw_b7\` (`exemples_calibration.json`, `exemples_calibration_sortie.txt`, `NOTES_b7_matiere_brute.md`). Aucun fichier existant modifié ; **aucun commit git** (règle projet).

**Chantier** : `SYSTEME_ZONES_OMBRE.md` §7 « APPRENTISSAGE & ÉVALUATION » — questions 7.1 (outcomes & calibration), 7.2 (replay engine PIT), 7.3 (jeux DEV/EVAL). Ce document **spécifie l'évaluation exécutable** : il étend le protocole W2-D §C (« prêt à geler ») et `R3_evaluation_benchmark.md` §B avec ce qui manque pour *implémenter* — objets, formats, formules, fichiers, tests — et pose les propositions d'apprentissage v1/V2.

**Périmètre** : la boucle mesure→apprentissage du système ORVYREN (outcomes, calibration, rejeu, jeux de données, harnais). **Hors périmètre** : le graphe (bloc B), la décision généralisée (bloc C), la politique/exécution (blocs 4–5), l'interface (bloc 8), les agents (bloc A — traité en B1, référencé ici pour le journal et le replay).

**Convention de preuve** — étiquettes identiques aux rapports du projet :
**[FAIT SOURCÉ]** affirmé par une source publique citée (URL + date) · **[MESURÉ] (interne)** valeur produite par une mesure ORVYREN traçable à un fichier · **[PROPOSITION]** choix de conception à trancher en revue · **[HYPOTHÈSE]** · **[NON TROUVÉ]** cherché, pas trouvé.

**Statut de ce document** : document d'ÉTUDE (il prépare la décision d'équipe, il ne la remplace pas). Les blocs marqués **[PROPOSITION]** sont à valider avant le gel G1–G7 de W2-D §C.5. Les rares points déjà tranchés par l'équipe sont marqués comme tels.

---

## 0. Résumé exécutif (onze points, à lire seul si pressé)

1. **Pipeline outcomes — trois producteurs distincts, jamais confondus** : (i) le **résolveur déterministe** (`evaluation/outcomes.py`) écrit l'outcome d'une **prévision gelée** (le seul qui entre dans le Brier/ECE) ; (ii) le **vérificateur de reçu** (`execution/verify.py`, existant) écrit l'**outcome d'exécution** (la chaîne a-t-elle fait ce que la politique a autorisé — codes de mismatch déjà implémentés) ; (iii) un **opérateur** écrit, avec attestation datée et références, l'outcome des cas **hors chaîne** (obligations DAO, épisode sans série de prix). Chaque outcome référence `forecast_id` + `forecast_hash` ; l'écriture est append-only et chaînée par hash. **[PROPOSITION]**.
2. **Deux horizons de résolution, gelés avant observation** : `H_class` = 6 h (événement « dépeg soutenu », définition R3 M2 : écart > 1 % persistant ≥ 2 observations) et `T` = fin de fenêtre d'épisode (métriques de perte/richesse W2-D §B.1). Un même forecast peut avoir deux outcomes (un par horizon). **[PROPOSITION]**.
3. **Calibration spécifiée pour implémentation stdlib** (contrainte projet : code neuf stdlib uniquement) : Brier + décomposition de Murphy **sur bins identiques à l'ECE** (l'identité `BS = REL − RES + UNC` devient exacte, donc testable — exemple chiffré vérifié en §(b).2 : `BS = 0,10`), ECE à 10 bins **fixes** gelés d'avance, bornes de Wilson, bootstrap par blocs maison (seed fixé). `arch` (recommandé par R3) n'est **pas à embarquer** dans `src/` — uniquement en outil d'analyse. **[MESURÉ] (interne, raw_b7)**.
4. **« Calibré » est un mot contrôlé** : interdit avant `N ≥ 100` prévisions gelées **hors échantillon**, ECE ≤ 0,05 avec IC bootstrap, absence de déviation systématique de la courbe de fiabilité, compétence > climatologie (borne basse de l'IC > 0), sur **≥ 2 familles d'épisodes disjointes**. En dessous : « **non établi** » (formulation V0.2 §9.3). Avec notre N réaliste (5–12), on publie `BS/REL/RES/UNC` + `ȳ`, jamais « calibré ». **[PROPOSITION]**.
5. **Replay engine — deux modes officiels, nommés** : `REPLAY-JOURNAL` (rejeu **bit-à-bit** du journal d'agents + magasin de réponses ; aucun réseau ; **seul mode dont le déterminisme est garanti par construction**) et `REPLAY-ARCHIVE` (recalcul sur **corpus figé + blocs fixes**, temperature 0, versions épinglées ; « même décision, texte différent » assumé). Ce second mode **remplace le nom `LIVE-REPLAY` de B1 §6.3** — « LIVE » contredisait le marquage obligatoire « REPLAY ». **[PROPOSITION]** (renommage) sur une architecture déjà proposée (B1 R-6).
6. **Marquage « REPLAY » obligatoire et vérifiable** : chaque artefact du rejeu porte `provenance.mode ∈ {LIVE, REPLAY-JOURNAL, REPLAY-ARCHIVE}`, `replay_id`, `t_sim_start/end`, `corpus_hash`, `code_hash` ; bannière à l'écran ; un rejeu **ne signe jamais** de transaction (les intents produits sont marqués `SIMULATED`). L'horloge simulée `t_sim` est la seule autorité PIT : tout objet d'`event_time > t_sim` est inadmissible (INV-PIT, REVUE_CROISEE §2.4) ; une violation **invalide** le run. **[PROPOSITION]**.
7. **`agent_journal` (B1 §3.4) est la timeline de démo** : le rejeu l'affiche par rôle (`agent_id`), par type (`kind ∈ {BRANCH_UPDATE, REFLECTION, CRITIQUE, …}`) et par statut (y compris `REJECTED`/`QUARANTINED`). Conséquence opérationnelle dure : **le journal doit être écrit dès la première exécution** — sans journal, il n'y a rien à rejouer en mode 1 (blocage actuel : le module agents n'existe pas dans le code). **[PROPOSITION]**.
8. **Jeux DEV/EVAL tranchés au niveau proposition** : **DEV** = USDC mars 2023 + stETH juin 2022 (« backtest long ») + fenêtres CALME 2022–2023 ; **EVAL** = rsETH avril 2026 (**principal**) + **USD0++ janvier 2025 (secondaire — retenu)** + fenêtres CALME 2025–2026 ; **xUSD novembre 2025 = qualitatif seulement** (série de prix trouvée par W3-C mais mécanique non comparable : wrapper staké, sorties suspendues, pas d'oracle ni de profondeur mesurée → ne peut pas alimenter une perte évitée). Embargo à trois volets (paramètres / données 24 h / inspection) ; **la première exécution EVAL invalide toute constante modifiée ensuite**. **[PROPOSITION]** — répond au point 8 des 12 points W2-D §(f).
9. **Collision d'étiquettes A0/A1 tranchée** : `R3` §B.2 appelait « A0 » la règle gelée 0,99 × 2 obs (celle du code, FREEZE_V1 D6) ; `W2-D` §C.1 appelle « A0 » l'action RIEN FAIRE. Pour le harnais : **A0 = NO-ACTION, A1 = règle de seuil W2-B, A2 = agent, B0 = placebo apparié (M ≥ 200)** ; la règle gelée du dépôt devient **`AX0`** (étiquette legacy « A0-code » interdite dans les rapports). Sans cette clarification, deux rapports se contrediraient. **[PROPOSITION]**.
10. **Apprentissage v1 = rien d'automatique — confirmé** : en v1, le système **calcule** (scores dès qu'un outcome arrive), **valide** (journal → graphe par validateurs déterministes uniquement) et **journalise** ; il ne **révise** ni seuils, ni politique, ni probabilités, ni prompts. Toute révision est humaine, versionnée, hashée, journalisée (`variants.log`). Les boucles V2 (calibration continue, seuils par quantiles, méta-apprentissage) sont **proposées et étiquetées** en §(f). **[PROPOSITION]**.
11. *(bonus)* **Blocages à lever** : (a) **aucune clé API d'équipe budgétée** (B1 R-7) → le mode `REPLAY-ARCHIVE` n'est pas exécutable aujourd'hui ; (b) **zéro prévision gelée à ce jour** → aucun score de Brier calculable (seuil D11 : ≥ 5) ; (c) le **gel G1–G6 n'est pas signé** ; (d) le module agents/journal **n'existe pas** dans `src/` (vérifié : `src/orvyren/` = audit, data, decision, execution, graph, policy, quality, ui) → le harnais doit démarrer sur les sorties déterministes existantes (dossier USDC v0) et le stub de journal.

---

## (a) Pipeline des outcomes — qui écrit quoi, quand, dans quel format

### a.1 Le vocabulaire (frontières à figer)

| Objet | Définition | Producteur | Entrée dans la calibration ? |
|---|---|---|---|
| **Prévision (forecast)** | énoncé gelé d'un événement futur, avec critère de résolution et horizon ; hashé ; **jamais modifié** | composant déterministe ; **signé par un humain** (G6, W2-D §C.5) | oui — c'est la brique `p` du Brier |
| **Outcome (résolution)** | résultat observé de la prévision à l'horizon, écrit **après** la fenêtre | résolveur déterministe (archives) ; ou opérateur attesté (hors chaîne) | oui — c'est la brique `y` |
| **Reçu (receipt)** | la chaîne a-t-elle exécuté l'action autorisée (token, destinataire, montant, statut) | `execution/verify.py` (existant, codes de mismatch stabilisés) | **non** — preuve d'exécution, pas de prévision |
| **Score** | `(p−y)²` par prévision, puis agrégats (BS/REL/RES/UNC/ECE) | recalculable à tout moment depuis (forecast, outcome) | c'est l'agrégat |
| **Attestation** | jugement humain documenté (obligation DAO honorée, sortie fermée sans prix…) | opérateur nommé, références + motif | oui, **étiquetée** `resolver=operator` |

**Règle** : le moteur de décision ne lit **jamais** un outcome (il est passé) ; les outcomes n'influencent la décision que via des révisions humaines gelées (§f). Cela évite toute fuite du futur dans le rejeu — c'est la contrepartie PIT du pipeline.

### a.2 Qui écrit un outcome — trois cas, jamais mélangés

1. **Cas « données publiques disponibles » (USDC, stETH, rsETH, USD0++, fenêtres CALME)** — le **résolveur déterministe** `evaluation/outcomes.py` lit le **corpus figé** (séries archivées avec `retrieved_at`), applique la **règle de résolution gelée** (même définition que la prévision, R3 M2 : « dépeg soutenu = écart > 1 % persistant ≥ 2 observations » ; convention de prix close/low **gelée par source**, cf. réconciliation `B3_DECISION_ETUDE.md` §g.4 à trancher avant G1), et écrit l'outcome. Aucun humain dans la boucle ; une divergence entre deux exécutions du résolveur est un **bug bloquant** (test de reproductibilité).
2. **Cas « action exécutée »** — le **vérificateur de reçu** atteste l'exécution (hash de tx, bloc, statut, log Transfer décodé, comparaison à l'allowlist de politique ; **10 codes de mismatch** déjà implémentés dans `verify.py`). Cet outcome sert la **sûreté** et l'inventaire « 0 action hors enveloppe » (SD5), **pas** le score de Brier.
3. **Cas « hors chaîne / hors données » (obligation DAO honorée pendant une fenêtre, épisode xUSD, source primaire fermée)** — un **opérateur nommé** écrit un outcome **attesté** : `resolver=mode:"operator"`, identité du signataire, sources (documents datés, captures), motif, et **question de résolution copiée du forecast**. Ces outcomes sont publiés **séparément** (table dédiée) et ne sont **jamais** agrégés avec les outcomes déterministes sans le drapeau.

**Question du brief — « le vérificateur de reçu ? »** : partiellement. Le vérificateur de reçu traite **l'exécution** (cas 2) ; la **résolution d'une prévision** (cas 1) est un autre objet, car une prévision peut être résolue sans qu'aucune transaction n'ait eu lieu (et une transaction peut exister sans prévision). Les confondre serait l'erreur « le reçu prouve la décision » — le reçu prouve l'action.

### a.3 Quand — fenêtres d'évaluation et états

- `t_frozen` : instant de gel de la prévision (UTC, à la minute) ; **les données postérieures à `t_frozen` ne sont pas admissibles à la prévision** (INV-PIT).
- `H_class` : horizon court de classification (défaut proposé : **6 h**, hérité de R3 §B.1 M2 — à figer). Résolution dès `t_frozen + H_class`, quand la donnée est archivée.
- `T` : horizon long = **fin de la fenêtre d'évaluation** de l'épisode (ex. rsETH : 17/04 → 21/04) — porte les métriques de richesse/perte (§e).
- `resolution_time` : **horodatage de la fenêtre de résolution**, pas de l'exécution du job. Un job relancé plus tard ne change pas `resolution_time` ; s'il change `y`, ce n'est pas une mise à jour, c'est une **correction** (nouvel outcome, `supersedes` — §a.5).
- États d'une prévision : `FROZEN` → `RESOLVED` (outcome écrit) ou `UNRESOLVED` (donnée manquante à H+Δ ; listée telle quelle dans le rapport — pas de suppression). Défaut proposé Δ = 7 jours avant classement `ABANDONED` (jamais résolue, jamais scorée, publiée).

### a.4 Format exact (schémas JSON à geler)

**Prévision gelée** (`calibration/forecasts.jsonl`, une ligne = un objet) :

```json
{
  "schema": "orvyren.forecast.v1",
  "forecast_id": "01JAVF3K8Q2M",
  "run_id": "01JAVF3J00A",
  "episode_id": "rseth-2026-04",
  "set": "eval",
  "persona": "dao",
  "statement": "Un dépeg soutenu de l'actif X est observé dans les 6 h suivant t_frozen.",
  "resolution_rule_id": "sustained_depeg_v1",
  "horizon": {"kind": "H_class", "hours": 6, "t_frozen_utc": "2026-04-18T17:35:00Z", "resolve_not_before_utc": "2026-04-18T23:35:00Z"},
  "p": 0.35,
  "p_origin": "estimateur explicite (comptage empirique fenêtres de calibration)", 
  "y_definition": {"ecart_pct": 1.0, "persistance_obs": 2, "venues": ["binance","bitstamp"], "convention": "low"},
  "observation_state_at_freeze": {"last_values": [], "notes": "…"},
  "refs": {"hypothesis_ids": ["H2"], "branch_ids": [], "observation_ids": []},
  "signed_by": {"role": "gel-g6", "name": "<à nommer>"},
  "sha256": "…",
  "prev_hash": "…"
}
```

**Outcome** (`calibration/outcomes.jsonl`) :

```json
{
  "schema": "orvyren.outcome.v1",
  "outcome_id": "01JAVG1R7T8N",
  "forecast_id": "01JAVF3K8Q2M",
  "forecast_hash": "…",
  "horizon": {"kind": "H_class", "t_resolution_utc": "2026-04-18T23:35:00Z"},
  "y": 1,
  "observed": {"value": 0.9867, "metric": "min_price_realizable", "venues": ["binance","bitstamp"], "persistance_obs": 3},
  "resolution_rule_id": "sustained_depeg_v1",
  "resolver": {"mode": "deterministic", "version": "outcomes-v1", "code_hash": "…"},
  "evidence_refs": ["observation:binance-2026-04-18T20", "…"],
  "written_at_utc": "2026-04-18T23:41:02Z",
  "prev_hash": "…",
  "supersedes": null
}
```

Champs obligatoires : `outcome_id`, `forecast_id`, `forecast_hash`, `y`, `resolver.mode`, `evidence_refs` (non vide), `written_at_utc`, `prev_hash`. Un outcome d'**exécution** suit la même enveloppe avec `schema: "orvyren.outcome.execution.v1"` et `receipt: {...}` (tx hash, bloc, token, from, to, amount, status, mismatch_code=null) — produit par `verify.py`.

### a.5 Liaison prévision gelée ↔ outcome (règles opposables)

1. **Clé de liaison** : `forecast_id` + `forecast_hash` (le hash du record gelé). Un outcome dont le `forecast_hash` ne correspond plus à la prévision sur disque est **rejeté** à l'ingestion (test automatique).
2. **Append-only** : ni forecast ni outcome ne sont jamais réécrits ; le fichier est chaîné par `prev_hash` (même mécanique que `audit.jsonl` de W2-C et le journal B1 §3.4).
3. **Corrections** : un nouvel outcome avec `supersedes: <outcome_id>` + motif ; l'ancien reste ; **les deux** apparaissent dans le rapport ; une correction **compte** dans `variants.log` (multiplicité, DSR/Jeffreys).
4. **Un forecast sans outcome** après `resolve_not_before + Δ` est `UNRESOLVED` et publié — pas caché.
5. **Interdits** : modifier `p` après gel ; écrire un outcome avant `resolve_not_before_utc` (le résolveur refuse : garde-fou de code, testé) ; faire produire `p` par un LLM (confiance verbale — R3 §A.19, B3 §f.4).

### a.6 Stockage (table de calibration et journal de fichiers)

**v1 (concours) — fichiers d'abord, base en miroir :**

| Artefact | Emplacement | Nature |
|---|---|---|
| Prévisions gelées | `calibration/forecasts.jsonl` | append-only, chaîné, source de vérité |
| Outcomes | `calibration/outcomes.jsonl` (+ `outcomes_execution.jsonl`) | append-only, chaîné |
| Scores par prévision | recalculables — jamais stockés comme vérité | `(p−y)²`, bin, contributions |
| Rapports de calibration | `calibration/rapports/<date>.md` + `.json` | instantanés hashés (N, BS, REL, RES, UNC, ȳ, ECE, IC, code_hash, data_hash) |
| Journal des variantes | `variants.log` (W2-D §C.3) | append-only |
| Miroir base | tables `forecasts`, `outcomes`, `calibration_runs` dans le store SQLite (→ Postgres v1) | requêtable, jamais autoritaire |

**Décision de conception** : les **scores** et agrégats sont **recalculables** (code + données hashés) et donc **non autoritaires** ; seuls `forecasts`/`outcomes` (et le journal) sont des enregistrements à conserver. C'est ce qui permet la reconstruction par un tiers (T10) sans faire confiance à un tableau de bord.

**DDL proposé (miroir SQLite, aligné ULID/append-only du store existant)** :

```sql
CREATE TABLE forecasts (
  forecast_id TEXT PRIMARY KEY, run_id TEXT, episode_id TEXT, set_ TEXT,
  persona TEXT, statement TEXT, horizon_kind TEXT, horizon_hours REAL,
  t_frozen_utc TEXT, p REAL, resolution_rule_id TEXT, sha256 TEXT, prev_hash TEXT,
  signed_by TEXT, created_at TEXT);
CREATE TABLE outcomes (
  outcome_id TEXT PRIMARY KEY, forecast_id TEXT NOT NULL, forecast_hash TEXT NOT NULL,
  horizon_kind TEXT, t_resolution_utc TEXT, y INTEGER, resolver_mode TEXT,
  resolver_version TEXT, evidence_refs TEXT, written_at TEXT, prev_hash TEXT,
  supersedes TEXT, superseded_by TEXT);
CREATE TABLE calibration_runs (
  run_id TEXT PRIMARY KEY, generated_at TEXT, set_ TEXT, n INTEGER,
  bs REAL, rel REAL, res REAL, unc REAL, ybar REAL, ece REAL,
  code_hash TEXT, data_hash TEXT, verdict TEXT);
```

### a.7 Ce qui n'est **pas** un outcome (pour éviter les abus)

- la **valeur de marché** à un instant pour une position qu'on n'a pas vendue (mark-to-market ≠ réalisation ; W2-D piège n°9) ;
- une **opinion** de modèle (« je suis sûr à 85 % ») ;
- un **prix d'agrégateur** présenté comme prix réalisable ;
- un résultat **partiel** présenté comme final (une prévision sur l'événement `H_class` ne se résout pas sur `T`) ;
- un outcome d'exécution présenté comme preuve d'une **décision correcte**.

---

## (b) Calibration — métriques implémentables, seuils, rapport, non-établi

### b.1 Les métriques spécifiées (formules exactes, sources)

Notations : `N` prévisions gelées résolues ; `p_t` probabilité gelée ; `y_t ∈ {0,1}` outcome ; `ȳ = (1/N)Σy_t` climatologie ; `B` bins.

| Code | Métrique | Formule | Source |
|---|---|---|---|
| C1 | **Score de Brier** | `BS = (1/N) Σ (p_t − y_t)²` | Brier 1950 ; repris de R3 §A.4-17 |
| C2 | **Décomposition de Murphy** | `BS = REL − RES + UNC`, `REL = Σ_b (n_b/N)(conf_b − acc_b)²`, `RES = Σ_b (n_b/N)(acc_b − ȳ)²`, `UNC = ȳ(1−ȳ)` — **évaluée sur les mêmes bins gelés que l'ECE** (estimations binnées), ce qui rend l'identité **exacte** et donc testable | Murphy 1973, *A New Vector Partition of the Probability Score*, J. Appl. Meteor. 12(4):595–600, <https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2> |
| C3 | **ECE** | `ECE = Σ_b (n_b/N)·|acc_b − conf_b|`, **10 bins fixes** sur [0,1] gelés avant toute mesure (jamais de bins adaptatifs après voir les résultats — comparabilité) ; rapporter `n_b` par bin (aucun bin vide silencieux) | Naeini, Cooper & Hauskrecht, AAAI 2015, <https://ojs.aaai.org/index.php/AAAI/article/view/9602> (via R3 §A.4-18) |
| C4 | **Courbe de fiabilité** | table par bin : `n_b`, `conf_b` (moyenne des p), `acc_b` (fréquence observée), IC de Wilson par bin | R3 §B.1 M3 |
| C5 | **Bornes de Wilson** | IC 95 % d'une proportion : `(p̂ + z²/2n ± z·√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)`, `z = 1,959964` | Wilson, *Probable Inference…*, JASA 22(158):209–212, 1927, <https://doi.org/10.1080/01621459.1927.10502953> |
| C6 | **Bootstrap par blocs** (statistiques de série) | rééchantillonnage circulaire par blocs de 6–12 h, 10 000 réplications, **seed fixé** ; percentile 2,5–97,5 | R3 §B.5-3 (paquet `arch` recommandé — **réimplanté en stdlib** pour respecter la contrainte projet) |
| C7 | **Skill vs climatologie** | `BSS = 1 − BS/BS_clim`, `BS_clim = ȳ(1−ȳ)` ; IC bootstrap | convention Brier skill score ; R3 §B.1 M2 (taux de base obligatoire) |

**Contrainte d'implémentation (projet)** : code neuf **stdlib uniquement** → C1–C7 sont implantés en Python pur (`evaluation/calibration.py`), `z` fourni en constante, bootstrap via `random.Random(seed)` (déterministe). `arch`/`numpy`/`scipy` restent acceptables dans des **scripts d'analyse hors `src/`** (le dossier concours ne doit pas exiger d'installation exotique).

### b.2 Exemple chiffré vérifié (jeu de test « known answer ») — [MESURÉ] (interne)

`p = [0,2 ×5 ; 0,8 ×5]`, `y = [0,0,0,0,0, 1,1,0,1,1]` (10 prévisions) :

| Grandeur | Valeur calculée |
|---|---|
| `BS` | **0,100000** |
| `REL` | **0,020000** |
| `RES` | **0,160000** |
| `UNC` | **0,240000** |
| identité `REL − RES + UNC` | **0,100000 = BS** ✔ (exactitude binnée) |
| `ECE` (10 bins fixes) | **0,100000** (bin 2 : n=5, conf 0,2, acc 0,0 ; bin 8 : n=5, conf 0,8, acc 0,8) |
| `ȳ` | **0,400000** |

Fichier : `research/raw_b7/exemples_calibration.json`. **Ce vecteur est le test unitaire de référence** de `calibration.py` (tolérance 1e-12) : il détecte une erreur de binning, de formule ou d'identité en une exécution.

**Bornes de Wilson utiles (calculées, raw_b7)** — le tableau à recopier dans les rapports pour les proportions :

| n | 0 réussite/n → borne sup. 95 % | 1/n → IC | 2/n → IC |
|---|---|---|---|
| 6 | **39,0 %** | [3,0 % ; 56,4 %] | [9,7 % ; 70,0 %] |
| 12 | **24,2 %** | [1,5 % ; 35,4 %] | [4,7 % ; 44,8 %] |
| 36 | **9,6 %** | [0,5 % ; 14,2 %] | [1,5 % ; 18,1 %] |
| 100 | **3,7 %** | [0,2 % ; 5,5 %] | [0,6 % ; 7,0 %] |

Phrase obligatoire partout où un « 0 échec » apparaît : « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » (R3 §B.5-1).

### b.3 Quand peut-on dire « calibré » — cascade et garde-fous

**Cascade de calcul** (garde-fou petit échantillon) :

| N (prévisions gelées résolues) | Ce qui est publié | Libellé |
|---|---|---|
| `N < 5` | **rien** — « NON CALCULÉ — N insuffisant » | seuil D11 de FREEZE_V1 (déjà acté) |
| `5 ≤ N < 30` | `BS`, `REL`, `RES`, `UNC`, `ȳ`, liste des prévisions ; ECE **sans** revendication | **« non conclusionnel »** |
| `30 ≤ N < 100` | idem + IC bootstrap sur BS, courbe de fiabilité + IC Wilson par bin | **« non conclusionnel »** (ECE toujours non revendicable, R3 §B.1 M3) |
| `N ≥ 100` | tout + `BSS` avec borne basse d'IC | revendication possible, sous les 5 conditions ci-dessous |

**« Calibré (jeu X, méthode Brier/ECE, N = …) » exige les CINQ conditions** [PROPOSITION] :

1. `N ≥ 100` prévisions gelées **hors échantillon** (résolues par outcome déterministe ; les outcomes `operator` comptés à part) ;
2. `ECE ≤ 0,05` avec IC bootstrap à 95 % dont la borne supérieure ≤ 0,08 ;
3. courbe de fiabilité **sans déviation systématique** : test du signe sur les écarts `acc_b − conf_b` (bins à `n_b ≥ 10`), `p > 0,05` ; et `max_b |acc_b − conf_b| ≤ 0,10` ;
4. **compétence** : borne inférieure de l'IC à 95 % de `BSS > 0` (mieux que la climatologie) ;
5. **≥ 2 familles d'épisodes disjointes** (jamais un seul épisode ; « calibré sur un cas » est une contradiction) — et le jeu n'a servi à **aucun** réglage de seuil ou de prompt (déclaration + `variants.log`).

**Garde-fous permanents (anti-optimisme)** : publier `N` et `ȳ` partout ; ne jamais fusionner DEV et EVAL ; ne jamais moyenner `R⁻` et `R⁺` (W2-D piège n°8) ; pas de binification a posteriori ; inclure les prévisions non résolues en annexe ; hasher le code de scoring et les prévisions (un rapport sans hash est un rapport non vérifiable) ; refuser toute comparaison de deux ECE à N < 100 (bruit du à la binification, R3 §A.4-18).

### b.4 À quoi ressemble le rapport de calibration (structure du livrable)

`calibration/rapports/YYYY-MM-DD_<set>.md` + `.json` — sections imposées :

1. **Périmètre et hashes** : jeu (dev/eval), épisodes, `N`, période, `code_hash`, `data_hash`, liste des `forecast_id` (lien fichier).
2. **Tableau global** : `N`, `ȳ`, `BS`, `REL`, `RES`, `UNC` (+ IC bootstrap de BS), `ECE` (+ IC), `BSS` (+ IC), verdict (« non établi » / « non conclusionnel » / « calibré » — §b.3).
3. **Courbe de fiabilité** : une ligne par bin (`bin`, `n_b`, `conf_b`, `acc_b`, IC Wilson), + figure.
4. **Décomposition par famille** : par persona, par type d'événement (A/D/T), par épisode — **avec N affiché par cellule**.
5. **Annexe des prévisions** : table `forecast_id | p | y | (p−y)² | horizon | résolveur`.
6. **Anomalies et corrections** : outcomes `supersedes`, non résolues, quarantaines.
7. **Limites en toutes lettres** : contamination (épisodes 2022–2025 dans les données d'entraînement des modèles 2026), non-échangeabilité, tailles.
8. **Verdict en langage contrôlé** — une phrase, du vocabulaire imposé (jamais « calibré » sans les 5 conditions).

Le rapport est un **artefact hashé** listé dans l'evidence pack ; il ne modifie rien (aucune écriture de seuil).

### b.5 Ce qui reste « non établi » (liste à recopier dans le dossier)

- **Calibration de la prévision** tant que `N < 100` → « non établi » (V0.2 §9.3) ; avec nos 5–12 fenêtres réalistes, c'est l'état **par défaut** jusqu'après le concours.
- **Transférabilité DEV → EVAL** : la calibration mesurée sur un régime ne se transporte pas à un autre (non-stationnarité) ; on peut la **mesurer**, pas la **garantir**.
- **Couverture conformale en crise** : la garantie est conditionnelle à l'échangeabilité, violée par construction en crise (R3 §B.5-4) → publier couverture prédite vs empirique, jamais une garantie nue.
- **Confiance verbalisée du LLM** : jamais une probabilité (R3 §A.4-19 ; B3 §f.4) — non établie par construction dans notre pipeline (interdite).
- **`P(obligation)` et `p_s` (scénarios)** : hypothèses signées, pas des estimations calibrées ; aucune source publique (W2-D §(f) 6–7 ; B3 h.3).
- **Qualité de la décision ≠ calibration de la prévision** : le Brier mesure les prévisions ; la perte évitée/le P&L mesurent les décisions (§e). Aucun des deux ne remplace l'autre ; aucun score unique (R3 B.0 règle 4).

---

## (c) Moteur de rejeu (« replay engine ») — spécification complète

### c.1 Objectifs et réponse à la carte (§7.2)

Le replay sert **trois usages** distincts, avec **trois niveaux de garantie** différents :

| Usage | Exigence | Mode |
|---|---|---|
| **Démo** — « voir l'évolution des réflexions » | rejouer une histoire passée, salle sans réseau | `REPLAY-JOURNAL` |
| **Évaluation** — exécuter A0/A1/A2/B0 sur les jeux DEV/EVAL, PIT strict | recalculer des décisions sur données archivées | les deux (voir §e) |
| **T10 (reconstructibilité par un tiers)** | un tiers recalcule sans réseau chaque calcul déterminant | `REPLAY-JOURNAL` + corpus + code figés |

La carte demandait de trancher « agents en direct sur données archivées » vs « sorties rejouées » : **les deux, en modes séparés et étiquetés** (recommandation B1 R-6 conservée) ; le mode « live » (données courantes) est hors démo.

### c.2 Les deux modes officiels (noms à figer)

| Mode | Ce qui est rejoué | Déterminisme | Réseau | Étiquette affichée |
|---|---|---|---|---|
| **`REPLAY-JOURNAL`** | le **journal d'agents** (`agent_journal`, B1 §3.4) + le **magasin de réponses** (prompts/réponses bruts, adressés par hash) : on relit la séquence étape par étape, rien n'est recalculé | **bit-à-bit garanti par construction** (vérification du chaînage `prev_hash` à la lecture) | aucun | `REPLAY (journal, rseth-2026-04, t_sim=…)` |
| **`REPLAY-ARCHIVE`** | les **appels LLM sont recalculés** sur les données archivées (corpus figé + blocs fixes), versions de modèle épinglées, temperature 0 | **non garanti** — « même décision, texte différent » ; c'est un résultat à publier, pas un échec | fournisseur LLM (aucun RPC « live » : toutes les lectures chaîne passent par blocs fixes) | `REPLAY (archive, données archivées)` |
| *(hors rejeu)* `LIVE` | données courantes | non déterministe par nature | oui | `LIVE` |

**Renommage proposé** : B1 §6.3 nommait le second mode `LIVE-REPLAY` ; le mot « LIVE » y contredisait le marquage obligatoire « REPLAY » et prêtait à confusion avec le mode données courantes. **`REPLAY-ARCHIVE`** est retenu ici ; dans la traçabilité, consigner `alias: LIVE-REPLAY (B1 §6.3)` pour que les rapports antérieurs restent lisibles. [PROPOSITION]

**Ce qu'on attend de chaque mode** : le mode 1 est la **preuve de reconstructibilité** et le support de la démo ; le mode 2 est la **preuve que le système tourne** (raisonnement non pré-écrit) et le seul mode possible pour une évaluation A2 « vivante » — avec l'honnêteté qui va avec (k rejeux, distribution des sorties, R3 §B.1 M5-D3).

### c.3 Horloge simulée

**Composant** `replay/clock.py` — `ReplayClock` :

- Champs : `t_sim` (ISO-8601 UTC, temps simulé), `t_wall` (horloge réelle, pour la journalisation), `run_id`, `step`.
- `t_sim` est **strictement monotone** (jamais en arrière) et **piloté par les événements du corpus** : au pas `k`, `t_sim` = horodatage de l'événement admissible suivant (granularité minimale : l'heure du corpus ; les événements on-chain : le bloc).
- **Autorité PIT** : tout objet portant `event_time > t_sim` est **inadmissible** (INV-PIT — REVUE_CROISEE §2.4) ; la tentative d'admission d'un objet futur **abandonne le run** (`PIT_VIOLATION`) et l'incident est écrit (un audit PIT par run — B2 §7.5). Le test de violation (injecter une observation future → le run doit refuser) est un test unitaire obligatoire.
- **Configuration du run** : `t_sim_start` (ouverture de fenêtre, moins la bande d'initialisation de 24 h, cf. embargo §d.3), `t_sim_end` (fin de fenêtre), `pas` (1 h par défaut), liste des sources actives.
- **Double horodatage obligatoire** dans chaque artefact produit : `ts_sim` (temps simulé — sert à PIT) et `ts_wall` (temps d'exécution réel — sert à l'audit d'exécution). Confondre les deux est la faille classique (« le rejeu a l'air d'avoir prédit parce que ses timestamps sont ceux du rejeu »).

### c.4 Sources admissibles (corpus figé + blocs fixes)

| Source | Contenu | Gel |
|---|---|---|
| **Corpus figé** | `corpus/` (USDC : 520 obs, manifest du 2026-10-14) + séries W3 (stETH 253 pts, rsETH, USD0++ 635 h, xUSD 457 h) + fenêtres CALME | `replay/corpus_v1.manifest.json` : liste de fichiers + `sha256` + `retrieved_at` + bornes temporelles |
| **Blocs fixes** | toutes les lectures chaîne (oracle, Aave, Curve, `getLogs`) **ancrées à un bloc explicite** — table `replay/blocks_v1.json` (1 ancre/jour reconstruite par dichotomie, résolue et cachée) | version dans le manifest ; **aucun `latest`** dans un run de rejeu (garde-fou de code) |
| **Config gelée** | G1–G6 (fonction de perte, comparateurs, fenêtres, seuils, plan d'analyse, hypothèses économiques) + `config/models.yaml` (IDs épinglés + date de vérification, test de fumée si l'ID disparaît — B1 §2.7) | `frozen/Gx.sha256` |
| **Journal + magasin de réponses** | `agent_journal` (B1 §3.4) + `journal/<run_id>/<journal_id>.json` (prompts/réponses bruts) | hash par ligne + chaînage |

Vérification au démarrage : le moteur refuse de démarrer si un hash de manifest ne correspond pas au disque ; en mode 1 il vérifie **tout** le chaînage avant de rejouer la première étape.

### c.5 Marquage obligatoire « REPLAY »

1. **Champ de provenance** dans tout artefact produit (dossier de décision, report, JSONL, figure) : `provenance: {mode, replay_id, t_sim_start, t_sim_end, corpus_hash, code_hash, alias?}`.
2. **Bannière** : toute sortie écran/HTML/PDF issue d'un rejeu porte en tête la phrase `REPLAY — données archivées —<mode>— <épisode> — t_sim=<début>→<fin>` ; en mode `LIVE` la bannière doit dire `LIVE`.
3. **Nommage des fichiers** : suffixe `_replay_<mode>_<replay_id>` pour distinguer un dossier de démonstration d'un dossier live.
4. **Interdiction d'effets** : un run de rejeu **ne signe jamais** et **n'émet jamais** de transaction ; les intentions produites sont marquées `SIMULATED` et le vérificateur de politique s'exécute en mode sec. (Exception tracée : les 5 runs de démo Base Sepolia de W2-C sont de l'évidence `LIVE` sur testnet, pas du rejeu.)
5. **Journal des rejeux** : `replay/runs.jsonl` (append-only) : `replay_id`, mode, épisode, t_sim, hashes, résultat (hash du dossier recalculé), durée, coût.

### c.6 Intégration de `agent_journal` (montrer l'évolution des réflexions)

Le rejeu est le **véhicule d'affichage** du journal B1 ; la table `agent_journal` **est** la timeline :

- Filtres d'affichage : par `agent_id` (colonnes explorateur/critique), par `kind` (`PLAN`, `TOOL_CALL`, `REFLECTION`, `HYPOTHESIS_PROPOSED`, `BRANCH_UPDATE`, `CRITIQUE`, `DECISION_DRAFT`, `STOP`, `REJECTED`…), par branche (`refs`), par pas (`step_index`).
- Écrans (script B1 §6.4 conservé) : fenêtre & PIT → graphe → **branches avec timeline d'états** (`CREATED → EXPLORING → WEAKENED → REFUTED/SUPPORTED`, transitions datées et référencées) → **réflexions par agent** → recherche & coût (`cout_reel`, `non_recherche[]`) → décision → verrous → refus/quarantaine → coût par décision.
- En mode 1, la séquence est **la séquence enregistrée** ; en mode 2, la nouvelle exécution écrit un **nouveau journal** (même schéma, `mode=REPLAY-ARCHIVE`) que l'on peut afficher **côte à côte** avec l'original (démonstration du non-déterminisme : même décision, texte différent — décision de scénario à trancher, question B1 Q6).
- **Exigence opérationnelle** : journaliser **dès la première exécution** (B1 §6.5) — sinon le mode 1 n'a rien à rejouer. Aujourd'hui, le module agents n'existe pas : le mode 1 est **spécifié mais non alimentable** ; le jalon minimal est le premier run USDC instrumenté.

### c.7 Déterminisme : limites établies et mitigations

**Ce qui est établi** [FAIT SOURCÉ] (repris de B1 §6.2) :

- « même prompt, temperature 0 → deux sorties différentes » est le comportement par défaut des piles hébergées (non-associativité des flottants + batching dynamique) — Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference*, 2025-09-10, <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference>.
- La variabilité a plusieurs couches (échantillonnage, environnement, données, infrastructure, lots, détails numériques) — arXiv:2606.08998, 8 juin 2026.
- **Aucun paramètre `seed`** de reproductibilité trouvé dans la documentation consultée (DeepSeek, MiMo) — [NON TROUVÉ], pages officielles consultées le 15/10/2026 (B1 §2.5).
- Les **identifiants de modèles bougent** (redirection DeepSeek V4→V4.1 ; dépréciation MiMo `mimo-v2.5` fixée au 21/10/2026) — B1 R-3.

**Mitigations (les sept, opposables)** :

1. **Le seul déterminisme promis est celui du mode journal** — phrase à écrire dans la doc technique : « la reproductibilité bit-à-bit est une propriété du **rejeu de journal** ; le recalcul est une démonstration de fonctionnement. »
2. **Chaînage par hash** du journal et des payloads (une ligne modifiée casse la chaîne → détection mécanique).
3. **Mode 2 : k ≥ 3 rejeux**, on publie la distribution des sorties et des décisions (M5-D3 de R3), pas seulement la modale.
4. **Versions épinglées** (`config/models.yaml` + date + test de fumée qui échoue si l'ID n'existe plus) et **repli multi-fournisseur** documenté (le mode journal rend le repli non critique pour la démo).
5. **Archivage systématique** prompt complet + réponse brute (magasin de contenu adressé par hash) : tout recalcul peut être **diffé** ligne à ligne contre l'original.
6. **Double horodatage** (t_sim / t_wall) et audit PIT par run (violation = run invalide).
7. **Vocabulaire contrôlé devant le jury** : ne jamais dire « la température 0 garantit » ; dire « le mode journal est bit-à-bit ; le recalcul reproduit la décision, le texte diffère — et nous le montrons ».

**Coût** (pour dimensionner) [MESURÉ] : 12 appels/décision, 3 épisodes ≈ **0,04 $** (DeepSeek flash hors pointe ; MiMo 0,03 $ ; Kimi 0,34 $) — `raw_b1/couts_b1.json` ; latence 30–90 s par passe ; les quotas (MiMo 100 RPM) suffisent. Le facteur limitant est la **journalisation**, pas le prix (B1 §6.5).

### c.8 Interfaces et plan d'implémentation minimal

**CLI proposés** :

```
python run_replay.py inspect --manifest replay/corpus_v1.manifest.json --episode rseth-2026-04 --t-sim 2026-04-18T18:00Z
python run_replay.py journal  --run-id <run_id>                    # mode 1, offline, bit-à-bit
python run_replay.py archive  --episode rseth-2026-04 --k 3        # mode 2, recalcul (LLM requis)
python run_replay.py verify   --run-id <run_id> --mode journal     # T10 : recalcule et compare les hashes
```

**Fichiers** (stdlib, relançables, tests pytest ajoutés — les 221 actuels restent verts) :

| Fichier | Contenu | Effort |
|---|---|---|
| `src/orvyren/replay/clock.py` | `ReplayClock`, `as_of`, garde-fous PIT | 0,5 j |
| `src/orvyren/replay/corpus.py` | lecture manifest + séries + ancres de blocs, refus des trous silencieux | 0,5 j |
| `src/orvyren/replay/journal.py` | lecture/vérification du chaînage, itérateur d'étapes (mode 1) | 0,5 j |
| `src/orvyren/replay/archive.py` | boucle de recalcul (mode 2), collecte des journaux produits | 0,5 j |
| `src/orvyren/replay/dossier.py` | reconstruction/assemblage du dossier + comparaison de hashes | 0,5 j |
| `run_replay.py` (racine) | CLI `inspect/journal/archive/verify` | 0,5 j |
| `tests/test_replay_clock.py` | monotonie, as_of, **violation PIT → abandon** | 0,5 j |
| `tests/test_replay_journal.py` | chaînage, étape par étape, hash du dossier identique | 0,5 j |
| `tests/test_replay_determinism.py` | k=10 rejeux journal → hash identique (offline) | 0,25 j |

**Total ≈ 4,25 j** dont ~1,5 j criticables avant la soumission (le reste post-soumission). **Prérequis bloquant** : un premier run d'agents instrumenté (module `research/` absent du code — B1 R-7c) ; en attendant, le mode 1 peut être démontré sur le **dossier déterministe USDC existant** (`evidence/decision_usdc-2023-03.json`, auto-hashé) qui donne déjà une reconstructibilité partielle.

### c.9 Ce que le rejeu ne prouvera jamais (à ne pas revendiquer)

- une performance financière ou prédictive (§e) ;
- l'impact de nos ordres sur le marché, la latence réelle, la surprise — exige le **forward/paper trading** (W2-D §(d)) ;
- que le raisonnement serait identique en conditions live ;
- que « rejouable » = « robuste » (R3 §(d) n°4).

---

## (d) Jeux DEV / EVAL — affectation, séparation, embargo, publication

### d.1 Tableau définitif (proposition, remplace les affectations partielles antérieures)

| Épisode | Fenêtre (UTC) | **Jeu** | Rôle | Justification |
|---|---|---|---|---|
| **USDC / SVB** | 2023-03-10 → 14 | **DÉVELOPPEMENT** | régler seuils, calibrer, déboguer, mesurer les coûts ; démonstration du bug de perte | épisode le plus documenté ; dans les données d'entraînement de tout modèle 2026 (contamination assumée, W2-D piège n°13) ; corpus 520 obs déjà archivé |
| **stETH / Celsius** | 2022-05 → 2022-06 (série 253 pts) | **DEV — « backtest long »** | contrôle de longue série ; antériorité (213,7 bp le 13/05, pire 6,93 %/6,98 % le 14/06 10:00Z) ; validation de seuils hors crise | seule série à 4 semaines d'antériorité (W2-B/W3-A) ; sert de test de non-régression, pas de réglage fin |
| **rsETH / KelpDAO** | 2026-04-17 → 21 | **ÉVALUATION #1 (principal)** | exécution **une fois**, après gel ; abstention post-gel = réponse attendue | le mieux instrumenté (gel daté à la seconde : bloc 24 908 723 = 19:03:59Z ; cap 99,9989 % à 18:00 ; divergence oracle −31 %), le plus tardif → contamination la plus faible ; jeu « brûlé » après ouverture |
| **USD0++ / Usual** | 2025-01-08 → 31 | **ÉVALUATION #2 (secondaire) — RETENU** | second cas d'évaluation : mécanisme différent (changement du plancher de rachat : 0,995 → 0,87), série horaire (635 pts) + reconstruction on-chain (610 swaps, écart moyen 0,31 %) | évite le N=1 rsETH ; série solide ; maillon « débasement contractuel » (pas un run classique) ; probablement contaminé (2025 < cutoff) → **démonstration de méthode**, à écrire tel quel |
| **Fenêtres CALME 2022–2023** | ≥ 6 fenêtres (R3 §C.8) | **DEV** | taux de faux signaux, couverture conformal, friction | critère `CALME` gelé : `max|P_t − 1| < 0,5 %` sur toute la fenêtre, appliqué mécaniquement ; échec → reclassé `STRESS` |
| **Fenêtres CALME 2025–2026** | ≥ 6 fenêtres | **EVAL** | friction, faux signaux, placebo B0 | doit être ≥ 1 an après les épisodes DEV ; à figer (liste + bornes) |
| **xUSD / Stream** | 2025-11-02 → 12 | **HORS JEU (qualitatif seul)** | cas d'« invisibilisation » documenté en annexe | décision : la série existe désormais (CoinGecko horaire 457 pts + Uniswap v4 411 swaps, W3-C) **mais** la mécanique diffère (wrapper staké — pas d'ancrage à 1 $, sorties suspendues, pas d'oracle ni de profondeur mesurée) → aucune perte évitée quantifiable honnêtement ; candidat v2 si une vérité terrain de sortie est reconstruite |

**Décision USD0++ (la question du brief)** : **OUI, en EVAL** — c'est l'épisode le plus proche d'un « stress d'émetteur institutionnel » après rsETH, sa série est le résultat d'une double mesure indépendante (DefiLlama + reconstruction on-chain), et l'exclure condamnerait l'évaluation à N = 1 crise. Contre-argument assumé : sa datation est partiellement corrigée par nos mesures (premier affaiblissement 08/01 18:57 ; décrochage 10/01 15:58 ; le brief disait 11/01) — c'est justement ce que l'évaluation doit être capable d'exécuter proprement.

**Décision xUSD** : **qualitatif** (annexe du dossier) ; la réponse au registre (« réintégrer au quantitatif ? ») est **non, pour le concours** ; avec la série W3-C, il pourra devenir un cas DEV de « détection » (pas de perte évitée) [PROPOSITION].

### d.2 Règles de séparation (les trois embargos, étendus)

1. **Embargo de paramètres** : aucune constante de G1–G6 (fonction de perte, seuils `D`/`H`/`x_max`, `P(obligation)`, coûts `k`, scénarios `p_s`, bins de calibration) n'est modifiable après la **première exécution sur EVAL**. Toute modification **invalide** l'évaluation (re-étiquetage obligatoire en tête du rapport) — pas « affaiblit » (W2-D §C.2).
2. **Embargo de données (24 h)** : la bande de 24 h précédant chaque fenêtre EVAL est retirée du DEV (initialisation uniquement).
3. **Embargo d'inspection** : avant le gel, personne n'inspecte les fenêtres EVAL au-delà de ce que W2-A/W2-B/W3 ont déjà publié ; après la première exécution, le jeu EVAL est **brûlé** (plus jamais « nouveauté »).
4. **Embargo de calibration croisée (nouveau — le piège du plan W3-C §5)** : le plan « seuils par quantiles P99/P99,9 sur 12 mois de calme » **ne doit pas** être calibré sur des mois chevauchant les fenêtres CALME 2025–2026 du jeu EVAL. Règle proposée : les quantiles utilisés pour **toute revendication d'évaluation** sont calculés **hors** de ces mois (ou la contamination est déclarée en tête de rapport). Sans cette règle, la calibration des seuils « voit » le jeu d'évaluation — c'est la fuite la plus sournoise de ce chantier.
5. **Vérification mécanique** : `run_evaluation.py --set eval` refuse d'écrire si (a) `frozen/G1..G6.sha256` absents ou non concordants, (b) `eval_run.lock` existe (deuxième exécution = `--force` + mention « évaluation ré-exécutée (invalide pour la revendication) »), (c) une fenêtre CALME EVAL chevauche la période de calibration déclarée.

### d.3 Ce qu'on peut publier AVANT la soumission (20/10) sans contaminer l'évaluation

| Publiable avant (et recommandé) | Aussi publiable | **Interdit avant la 1ʳᵉ exécution EVAL** |
|---|---|---|
| `G1–G7` gelés + `sha256` (pré-enregistrement complet : perte, comparateurs, fenêtres, seuils, plan d'analyse, hypothèses, journal) | Démonstration du bug de la fonction de perte (identité `q(1−P_T)`) | résultats EVAL à quelque titre que ce soit |
| Spécification harnais + calibration (ce document) + tests unitaires | Résultats **DEV** (USDC : A0/A1 sur DEV par exemple) avec l'étiquette DEV visible | seuils « ajustés après un coup d'œil » sur EVAL (embargo d'inspection) |
| Rapport de calibration **squelette** avec `N=0` (« non calculé ») | Statistiques publiques des épisodes (re-mesures W3) | toute moyenne EVAL/DEV agrégée ; toute revendication de supériorité |
| Politique de marquage REPLAY + mode journal (spec) | Coûts de rejeu mesurés (0,04 $/3 épisodes) | listes de fenêtres EVAL modifiées après ouverture |

**Position recommandée sur la soumission** : publier **le gel + la démonstration DEV + l'évaluation en une passe si la capacité existe** (une exécution EVAL, résultat publié tel quel, même décevant) ; sinon publier **le pré-enregistrement sans chiffres EVAL** et l'écrire explicitement (« évaluation EVAL gelée, non encore exécutée à la date de soumission ») — c'est plus fort qu'un chiffre contaminé.

---

## (e) Harnais d'évaluation — A0/A1/A2/B0, métriques par persona, sorties, implémentation

### e.1 Les comparateurs (résolution de la collision d'étiquettes)

| Code | Système | Définition opérationnelle | Coût |
|---|---|---|---|
| **A0** | **NO-ACTION** | ne rien faire sur toute la fenêtre ; l'adversaire décisif du regret (W2-D §C.1) | 0 |
| **A1** | **Règle de seuil** | décote `D ≥ 50 bp` pendant 15 min → réduction bornée `x* = min(x_max, Depth_ε, x_seuil)` ; seuils issus de W2-B §1.1, à geler | ~0 |
| **A2** | **Agent ORVYREN** | corpus → graphe → hypothèses → branche → critique → politique bornée ; sortie du mode `REPLAY-JOURNAL` en priorité, sinon `REPLAY-ARCHIVE` (k=3) | budget plafonné, mesuré |
| **B0** | **Placebo apparié** | **même nombre et mêmes tailles d'actions** que A2, horodatages tirés uniformément sur la grille horaire de la fenêtre, **M ≥ 200 tirages, graine fixée** ; publier la **distribution** (moyenne, quantiles, percentile de A2 dans la distribution) | ~0 |
| **AX0** | **Règle gelée du dépôt (ex-« A0 » de R3)** | 0,99 × 2 obs consécutives → réduction 100 $ (FREEZE_V1 D6 ; `decision/baseline.py`, 2 signaux sur la fenêtre principale, 0 faux signal sur la fenêtre contrôle 15–18/02/2023) — conservée comme comparateur **supplémentaire** | ~0 |
| **O** | **Oracle ex post faisable** | `min_{b ∈ F} L(b)` sur la famille d'actions **faisables**, même fonction de perte gelée ; borne inférieure du regret, pas une vérité terrain | hors ligne |

**Collision réglée** : R3 §B.2 appelait « A0 » la règle gelée et « A1 » sa version 2-venues ; W2-D §C.1 appelle « A0 » NO-ACTION. Les rapports du concours utiliseront **W2-D** : `A0 = NO-ACTION`, `A1 = seuil`, la règle du code devient **`AX0`**. (La référence au code dira « baseline gelée (AX0, ex-A0) ».) Sans cette résolution, « A0 a fait mieux que A0 » était écrit noir sur blanc dans deux rapports.

**Règle pré-écrite** (W2-D §C.1, conservée) : si A2 ne bat pas B0, la valeur n'est pas dans le **choix du moment** — l'écrire. Si A2 ne bat pas A1, la valeur n'est pas dans la **délibération** — l'écrire. Ces deux phrases sont gelées **avant** l'exécution.

### e.2 Boucle d'exécution du harnais

```
pour chaque set ∈ {dev, eval} :            # garde de gel (§d.2.5)
  pour chaque fenêtre w du set :
    pour chaque config ∈ {A0, A1, A2, B0, AX0(, O)} :
      actions(w, config)  ->  [a_t]        # A2 : rejeu (journal puis archive) ; A0/A1/B0 : générées
      W_T, L(a), R(a)     ->  calculés par loss.py (G1 gelé)
    agrégats par fenêtre, par persona (DAO / desk), par config
  agrégats par set + intervalles (Wilson, bootstrap par blocs, McNemar)
  rapport + JSON + variants.log
```

**Budgets égaux** (R3 B.0 règle 2) : A2 et ses variantes partagent le même plafond d'appels/tokens/temps par décision ; les économies d'un composant retiré ne sont pas réinvesties sans déclaration. **Unité d'analyse = la fenêtre** (jamais l'heure — R3 B.0 règle 3). **Vecteur, pas scalaire** (règle 4).

### e.3 Métriques persona DAO (trésorerie / protocole)

Formules (fonction de perte gelée G1, W2-D §B.1 — richesse + actions faisables) :

```
W_T(conserver) = C + q·P_T
W_T(céder x)   = C + x·P_exec(x,t) − k + (q−x)·P_T
L(a)           = W_t0 − W_T(a)                     [USD]
R_w(a)         = L(a) − min_{b∈F} L(b)  ≥ 0       [USD ou bp de W_t0]
```

| Code | Mesure | Formule exacte | Seuil proposé (W2-D §C.4.1) |
|---|---|---|---|
| **SD1** | Perte évitée matérielle | `(L_w(A0) − L_w(A2)) / q` en % de l'exposition, **conditionnellement à l'obligation** (`E[perte évitée] = P(oblig)·(perte|oblig) − (1−P)·coût aller-retour`, les deux facteurs publiés) ; **second affichage en jours de runway** : `(L(A0) − L(A2)) / opex_jour`, `opex_jour = 44 932 $/j` (réf. ENS IPS : 16,4 M$/an ; conversion calculée raw_b7), paramètre `opex_ref` à figer | ≥ 5 % (à valider) ; jours publiés tels quels |
| **SD2** | Friction maîtrisée | coût cumulé de A2 sur les fenêtres CALME | ≤ 10 % de la perte évitée de crise |
| **SD3** | Anticipation | antériorité (h avant le point bas du prix **réalisable**) ≥ 6 h sur ≥ 1 épisode EVAL ; délai de réaction ≤ 60 min | oui/non |
| **SD4** | Supériorité comparateurs | `R̄(A2) < R̄(A1)` et `< R̄(B0)`, **avec intervalles**, regrets `R⁻`/`R⁺` séparés + table de contingence | strictement inférieur |
| **SD5** | Traçabilité | 100 % des actions avec provenance + hash ; 0 action hors enveloppe | 100 % / 0 |
| **SD6** | Honnêteté | mentions « non conclusionnel » là où la puissance manque ; perte évitée publiée comme `P × conditionnel` | présent / absent |

### e.4 Métriques persona desk (P&L)

```
ΔP&L_net(a) = [x·P_exec(x,t) + (q−x)·P_T − q·P_ref] − frais − gas − financement (I_moy·r_capital·Δt)
ΔP&L en bp  = ΔP&L_net / (q·P_ref) · 10 000
Sharpe      = (moyenne(r_net) − R_f)/σ(r_net),  R_f = 0 (convention crypto)
Sortino     = (moyenne − R_f)/σ_d,  σ_d = écart-type des seuls rendements négatifs
MaxDD       = min_t ( Equity_t / max_{u≤t} Equity_u − 1 )
```

| Code | Mesure | Seuil proposé (W2-D §C.4.2) |
|---|---|---|
| **ST1** | ΔP&L net cumulé sur les fenêtres EVAL, tous coûts inclus (frais, slippage mesuré, financement) | > 0, avec intervalle bootstrap par blocs |
| **ST2** | Qualité d'exécution : slippage réalisé vs échelle `get_dy` ; taille ≤ `Depth_100bp` | ≤ 30 bp sur une sortie de stablecoin en stress |
| **ST3** | Risque borné : `MaxDD` de la série de décisions | ≤ 20 % du capital alloué par épisode |
| **ST4** | Risque ajusté : Sharpe/Sortino **+ DSR** (Bailey & López de Prado 2014) corrigé du nombre de variantes du journal | Sharpe > 0 avec borne basse d'IC > 0, sinon « non conclusionnel » |
| **ST5** | Supériorité : `ΔP&L(A2) > ΔP&L(A1)` et `> ΔP&L(B0)` | strictement supérieur, avec intervalles |
| **ST6** | Asymétrie déclarée : l'agent est un **put** (coût certain, gain conditionnel) ; scénarios `p_s` publiés | présent/absent |

**Deux P&L publiés** (hors et avec financement — W2-D §(f) 11) ; la re-entrée est modélisée pour le desk (coût d'aller-retour explicite, même fenêtre) et **pas** pour la DAO (la ré-entrée relève de la politique de réallocation — décision à confirmer, G1).

### e.5 Sorties du harnais (rapport + JSON)

| Fichier | Contenu | Convention |
|---|---|---|
| `evaluation/report.md` | rapport lisible : périmètre, gel référencé, tableaux par persona, regrets séparés, table de contingence, placebo B0, limites | bannière `DEV`/`EVAL`/`REPLAY-<mode>` en tête ; français interne, anglais pour la soumission |
| `evaluation/report.json` | même contenu machine, avec bloc `headline` (convention projet `evidence/*.json`) : `{n_windows, pertes_evitees, regrets, ratios, verdicts, hashes}` | chaque chiffre traçable vers `windows/*.json` |
| `evaluation/windows/<window_id>.json` | détail par fenêtre : actions par config, `R_t` heure par heure, coûts, refs | recalculable |
| `evaluation/placebo_B0.json` | distribution complète des M tirages (200 ≥) + percentile de A2 | graine, M, méthode écrits |
| `evaluation/superiority_tests.json` | Wilson, McNemar exact (tables `[[n11,n10],[n01,n00]]`), bootstrap par blocs | 10 000 réplications, seed fixé |
| `variants.log` | journal des variantes (une ligne par exécution, **échecs inclus**) | append-only (W2-D §C.3) |
| `figures/` | courbe de fiabilité, `R_t` par fenêtre, distribution B0 | matplotlib (outil d'analyse, hors `src/`) |

**Règle de langage** : tout tableau porte `N` et la mention de validité (« non conclusionnel si N < 100 ») ; aucun score agrégé unique ; regrets `R⁻`/`R⁺` jamais moyennés ensemble.

### e.6 Plan d'implémentation minimal (fichiers, tests, effort)

| # | Fichier | Contenu | Tests | Effort |
|---|---|---|---|---|
| 1 | `src/orvyren/evaluation/loss.py` | `W_T`, `L`, `R`, `R⁻`/`R⁺`, conventions de valorisation (paramètre `convention ∈ {terminale, liquidation}`) | `tests/test_evaluation_loss.py` : **six tests W2-D §B.6** (neutralité, translation, monotonie, signe, additivité, référence dégénérée) | 0,5 j |
| 2 | `src/orvyren/evaluation/comparators.py` | A0, A1 (seuils paramétrés), B0 (graine, M), AX0 (délègue à `decision/baseline.py`), O (oracle faisable) | `tests/test_evaluation_comparators.py` : A0 = 0 action ; B0 reproductible ; AX0 reproduit `baseline_report.json` (2 signaux main, 0 contrôle) | 0,5 j |
| 3 | `src/orvyren/evaluation/windows.py` | registre fenêtres DEV/EVAL (bornes, épisode, set, sources), vérificateur d'embargo (24 h ; chevauchement calibration croisée) | `tests/test_evaluation_windows.py` : chevauchements détectés, set eval refusé sans gel | 0,25 j |
| 4 | `src/orvyren/evaluation/forecasts.py` + `outcomes.py` | formats §a.4, hachage, chaînage, règle `sustained_depeg_v1`, garde `resolve_not_before`, states | `tests/test_evaluation_forecast_outcome.py` : liaison par hash, correction `supersedes`, refus d'écriture avant horizon, reproductibilité du résolveur | 0,5 j |
| 5 | `src/orvyren/evaluation/calibration.py` | C1–C7 (stdlib) | `tests/test_evaluation_calibration.py` : KAT §b.2 (BS/REL/RES/UNC/ECE exacts), bornes de Wilson vs table raw_b7 (±0,001), bootstrap déterministe (seed) | 0,5 j |
| 6 | `src/orvyren/evaluation/harness.py` | boucle §e.2, agrégats, tests de supériorité | `tests/test_evaluation_harness.py` : run DEV USDC de bout en bout hors-ligne ; JSON conforme au schéma ; déterminisme (2 exécutions → même hash) | 0,75 j |
| 7 | `src/orvyren/evaluation/report.py` + `run_evaluation.py` (racine) + `run_calibration.py` | rendu MD/JSON, bannières, `variants.log`, gate de gel | `tests/test_evaluation_report.py` : bannière obligatoire, `N` affiché, refus si gel absent | 0,5 j |

**Total ≈ 3,5 j** cumulés, **≈ 1,5 j de chemin critique** si items 1–2 (perte + comparateurs) et 5 (calibration) avancent en parallèle — cohérent avec l'estimation R3 §B.6. Tous les modules : **stdlib**, relançables, hors-ligne (sauf mode archive). **Contrainte** : la suite existante (**221 verts, 2 sautés**) reste verte ; les nouveaux tests s'ajoutent.

### e.7 Faisabilité avant le 20/10 (honnête)

- **Livrable réaliste avant soumission** : items 1, 2, 5 + la spec (ce document) + le gel G1–G2 hashés + un run **DEV** (A0/A1/AX0/B0 sur USDC, A2 sur dossier déterministe). Le Brier n'est calculable que si ≥ 5 prévisions gelées existent (D11) — **aucune n'existe aujourd'hui** ; en produire 5–10 sur DEV est faisable (elles seront « non conclusionnelles » mais réelles, avec `ȳ` et Wilson).
- **Non réaliste avant soumission** : EVAL complet avec A2 recalculé (dépend des clés API et du module agents), calibration continue, quantiles W3-C (10–20 h de collecte), T10 par un tiers.
- **Ce qui doit être fait même sans capacité** : le **gel G1–G6** (hash + date) et la **liste des fenêtres EVAL** — sans eux, rien de ce qui précède n'est opposable.

---

## (f) Apprentissage v1 vs V2

### f.1 Ce qui est révisé automatiquement en v1 — **rien** (confirmé)

Constat à écrire noir sur blanc (réponse à la question « probablement rien — à confirmer ») : en v1, **aucune** boucle d'apprentissage n'écrit dans la décision. Ce qui est automatique en v1 est un **calcul**, pas une révision :

| Automatique en v1 (calcul / contrôle) | Révision ? |
|---|---|
| Résolution des prévisions → écriture des outcomes (résolveur déterministe, à H+Δ) | non — enregistrement |
| Calcul des scores (BS/REL/RES/UNC/ECE/Wilson) à chaque outcome | non — recalculable, non autoritaire |
| Vérification du chaînage (journal, audit, outcomes) | non — intégrité |
| Promotion journal → graphe (schéma, provenance, « pas de chiffre du LLM », quarantaine) | non — **validation déterministe** (B1 §3.5) ; une branche nouvelle naît à `p = 0` |
| Data gate (couverture de fenêtre, ≥ 2 sources indépendantes) | non — porte d'admission |
| Journalisation des coûts, latences, variantes | non — comptabilité |

Aucun seuil, aucun prior, aucun prompt, aucune politique ne se modifie sans une **intervention humaine** sous forme de gel versionné. Interdiction explicite : un LLM ne produit ni promesse de probabilité (B3 §f.4), ni chiffre (invariant projet), ni modification de politique (D2 : « le LLM ne détient rien »).

### f.2 Ce qui est révisé — par les humains, sous quelles formes

| Objet révisé | Règle | Forme du changement |
|---|---|---|
| Seuils des signaux (`D`, `H`, `x_max`, classes de prédicats) | uniquement par le **plan de calibration quantiles** (W3-C §5) ou une décision d'équipe motivée | nouveau fichier de seuils + `sha256` + date + motif + entrée `variants.log` ; **jamais** pendant/après une fenêtre EVAL ouverte sans invalidation |
| Fonction de perte, convention de valorisation, `F` (famille d'actions) | G1 — gel avant exécution | nouvelle version G1-v2 ; invalide l'évaluation EVAL si postérieure |
| `P(obligation)`, scénarios `p_s`, taux de financement | G6 — hypothèses signées | re-signature nommée + justification + sensibilité publiée |
| Fenêtres DEV/EVAL, embargo | G3 — déclaration | nouvelle version ; une fenêtre EVAL ouverte reste « brûlée » |
| Versions de modèles | épinglage (`config/models.yaml` + date) ; événements de dérive documentés (DeepSeek redirection, MiMo 21/10/2026) | mise à jour datée + test de fumée + journal |
| Politique (règles de refus/limites) | revue d'équipe | nouvelle version de politique, attaques re-testées |

**Cadence de revue proposée** : trimestrielle (alignée sur la cadence des rapports DAO de KPK) + à chaque déclencheur (dérive détectée, nouvel épisode, changement de version de modèle). **Règle d'or** : toute révision = **nouveau gel hashé**, jamais un « patch » silencieux ; le `variants.log` inclut les révisions ratées.

### f.3 Propositions V2 (étiquetées [PROPOSITION V2] — rien de tout ceci n'est dans le périmètre concours)

1. **V2-A — Calibration continue** : job périodique qui, à chaque nouvel outcome, met à jour `calibration_runs` et les courbes ; **alertes de dérive** (ECE glissant > seuil annoncé, test du signe qui bascule, `BSS` qui passe ≤ 0) → *proposition* de re-gel soumise à un humain (jamais automatique). Tableau de bord « prévisions en attente / résolues / non résolues ». Prérequis : volume (N ≥ 100) et rétention des séries.
2. **V2-B — Révision des seuils par quantiles** : exécuter mois par mois le plan W3-C §5 (P99 = alerte, P99,9 = rupture, niveau épisode = sortie ; contre-validation sur les 6 épisodes ; période de contrôle < 1 % / < 0,1 % d'heures) ; garde-fous : jamais pendant une fenêtre EVAL ouverte ; jamais calibrer sur les mois des fenêtres CALME EVAL (embargo §d.2.4) ; chaque révision re-joue le DEV (non-régression) puis re-gèle. Prérequis : 10–20 h de collecte (W3-C), `calibration/thresholds_v1.json`.
3. **V2-C — Méta-apprentissage** (trois sous-propositions, par ordre de sagesse) :
   - **C1 — sélection de composants à budget égal** : HYP-11R (second critique vs seconde passe du même modèle, REVUE_CROISEE §3.2) ; c'est de l'apprentissage **organisationnel** (expérience), pas du fine-tuning. Candidat v2 le plus défendable.
   - **C2 — ordre de recherche appris (RDOF → ordre appris)** : apprendre *quels prédicats réfutent réellement* à partir de l'historique du journal (compteurs de réfutations par type de prédicat), en gardant l'ordre déterministe gelé comme repli ; testé par T02 (RDOF vs ordre fixe, B3 §b.2). Interdit tant que le journal n'existe pas.
   - **C3 — conformal adaptatif + calibration ≥ 100 obs** : CPTC (change points, NeurIPS 2025) exploré en v2, avec la limite d'échangeabilité documentée (R3 §B.5-4).
4. **V2-D — Interdits d'apprentissage (garde-fous à écrire au gel)** : pas de bandit/RL sur la politique avant paper trading prolongé (le nombre d'épisodes requis est hors d'échelle, W2-D §(d) : 0–1 événement en 4–6 semaines) ; pas d'auto-modification de prompt ou de seuil par un LLM ; pas d'usage d'un outcome EVAL pour régler quoi que ce soit (le jeu reste brûlé) ; pas de fine-tuning sur les épisodes d'évaluation ; toute boucle d'apprentissage doit passer par un gel humain et le `variants.log`.

---

## (g) Questions ouvertes (à trancher en revue B7)

| # | Question | Ce qui la ferme | Coût |
|---|---|---|---|
| Q1 | **Qui signe G6** (`P(obligation)`, scénarios `p_s`) et avec quelles valeurs ? (12 points W2-D §(f) 6–7 et 12) | nommer le responsable + valeurs de départ + sensibilité | 0,5 j |
| Q2 | **Convention de valorisation** (terminale vs liquidation) avant G1 — recommandation W2-D : liquidation pour la DAO, terminale + financement pour le desk | décision écrite dans G1 | 0,25 j |
| Q3 | **Re-entrée** : modélisée pour le desk (oui/non, fenêtre), exclue DAO — confirmer | G1 | 0,25 j |
| Q4 | **Reconciliation close/low** (`B3_DECISION_ETUDE.md` §g.4) : gel par source avant G1 (sinon les seuils changent de sens) | table de conventions | 0,25 j |
| Q5 | **H_class = 6 h** et définition exacte de « dépeg soutenu » (2 observations ? 2 venues ? convention) | G1/G5 (règle de résolution `sustained_depeg_v1`) | 0,25 j |
| Q6 | **Fenêtre CALME 2025–2026** : liste exacte (≥ 6) + bornes + exclusion de la calibration quantiles | G3 | 0,5 j |
| Q7 | **Prévisions gelées avant soumission** : en produire 5–10 sur DEV (faisable) ou assumer `N=0` (« non calculé — N insuffisant ») ? | décision d'équipe | 0,5 j |
| Q8 | **EVAL avant le 20/10 ou après** ? (recommandation : une passe si capacité, sinon pré-enregistrement seul) | décision d'équipe | — |
| Q9 | **Clés API** (budget, une clé par rôle) — bloquant du mode `REPLAY-ARCHIVE` (B1 R-7) | provisioning | 0,5 j |
| Q10 | **xUSD** : critères de réintégration quantitative (série + profondeur + vérité terrain de sortie) | définition de critères | 0,25 j |
| Q11 | **A0/A1 → AX0** : acceptation du renommage pour tous les rapports (dont ceux déjà écrits) | note d'équipe | 0,1 j |
| Q12 | **B0** : nombre de tirages (200 ? 1000 ?), grille des horodatages (horaire), et taille des actions (mêmes tailles que A2, ligne à ligne) | G2 | 0,25 j |
| Q13 | **Opex de référence** pour la conversion runway (ENS 16,4 M$/an utilisé comme référence externe — quel paramètre pour ORVYREN ?) | G4/G6 | 0,25 j |
| Q14 | **Retention/export du journal** (B1 Q3/Q7) : export dans le dossier public en extraits `ACCEPTED` seulement ? | décision d'équipe | 0,25 j |
| Q15 | **Rejeu public avant concours** : montrer le mode journal (dossier USDC v0) suffit-il, ou faut-il le mode archive (et donc les clés) ? | décision d'équipe | — |
| Q16 | **Taux de financement desk** (`r_capital`) : valeur + publication des deux P&L | G6 | 0,25 j |

---

## (h) Réponse aux 12 points de W2-D §(f) (traçabilité)

| Point W2-D §(f) | Réponse B7 | Section |
|---|---|---|
| 1. Regret ou espérance ? | Les deux, publiés séparément ; signature de `p_s` = G6 (Q1) | §e.3, §e.4 |
| 2. Unité DAO (USD / jours de runway) | Les deux, jours en premier ; `opex_ref` paramétré (Q13) | §e.3 |
| 3. Convention de valorisation | Paramètre G1 `{terminale, liquidation}` ; recommandation en §e.1 et Q2 | §e.1, Q2 |
| 4. Re-entrée | Desk : oui (même fenêtre) ; DAO : non (politique de réallocation) — à confirmer G1 | Q3 |
| 5. Seuils chiffrés | Conservés provisoires (§e.3/e.4) ; gel G4 avant EVAL | §e.3, §e.4 |
| 6. `P(obligation)` | Hypothèse signée (G6) ; format d'outcome attesté prévu | §a.2, Q1 |
| 7. Scénarios desk | `p_s` gelés (G6) ; publiés avec le P&L | §e.4 |
| 8. Jeux DEV/EVAL | **Tranché ici** : §d.1 (USD0++ → EVAL ; xUSD → qualitatif) | §d.1 |
| 9. Autonomie revendiquée | Hors B7 (bloc C/politique) — le harnais mesure l'action, pas le niveau | — |
| 10. Budget de risque par épisode | `x_max`/`max_perte_par_episode` : paramètres de politique (bloc C) ; le harnais les consomme | §e.1 |
| 11. Coût du capital / financement | Deux P&L publiés ; `r_capital` en G6 (Q16) | §e.4 |
| 12. Qui gèle, qui rejoue | Responsable du gel G1–G6 + exécutant + relecteur externe (T10) — à nommer (Q1) | §c.8, Q1 |

---

## Sources

**Documents internes ORVYREN (référence principale de ce document — tous lus le 15/10/2026)**
1. `research/SYSTEME_ZONES_OMBRE.md` §7 (carte des décisions, 15/10/2026) — chantier de ce document.
2. `research/W2D_objectifs_mesure.md` (15/10/2026) — fonction de perte corrigée (§B), six tests (§B.6), protocole prêt à geler (§C), 12 points (§f), mesurable vs forward (§d), exemple USDC (§e). Chiffres cités : 44 932 $/j, 49,34 M$ ; identité du bug `q(1−P_T)` ; pertes évitées 110 912 $ / 258 578 $ ; −4,2 % / +10,8 %.
3. `research/R3_evaluation_benchmark.md` (14–15/10/2026) — métriques M1–M6 (§B.1), comparateurs (§B.2), design (§B.3), petit échantillon (§B.5 : puissance ≈ 93 fenêtres, Wilson, McNemar, bootstrap), pièges (§(d)), non-revendiqué (§B.7), fenêtres témoins (§C.8).
4. `research/B1_AGENTS_ETUDE.md` §6 (15/10/2026) — modes de rejeu, déterminisme (R-6/R-7), coût des rejeux (0,0396 $/3 épisodes), `agent_journal` (§3.4), questions Q1–Q8.
5. `research/B3_DECISION_ETUDE.md` (15/10/2026) — RDOF (§b.2), abstention (§c), catalogues (§d), scénarios qualitatifs d'abord (§f), épisodes traversés (§g), réconciliation close/low (§g.4).
6. `research/W3C_complements_signaux.md` (15/10/2026) — plan de calibration 12 mois (§5), séries xUSD/USD0++, scénarios de coûts de collecte (10–20 h).
7. `research/DECISIONS_ET_PROCHAINES_ETAPES.md` (15/10/2026) — « à trancher » (12 points, xUSD, etc.), état des pièces de soumission.
8. `research/VAGUE2_SYNTHESE.md` (15/10/2026) — synthèse des corrections (oracle 0,8833 ; stETH 13/05 ; = 221 tests verts).
9. `FREEZE_V1.md` — D6 (règle gelée 0,99 × 2 obs), D11 (Brier si ≥ 5 prévisions gelées).
10. `evidence/episode_usdc_2023-03.json`, `episode_steth_2022-06.json`, `episode_rseth_2026-04.json`, `baseline_report.json`, `corpus/manifest.json` — mesures citées (minima, dispersions, transitions).
11. `src/orvyren/quality/checks.py`, `normalize.py` (data gate, rejets explicites) ; `src/orvyren/decision/baseline.py` (AX0) ; `src/orvyren/execution/verify.py` (10 codes de mismatch).
12. `research/raw_b7/exemples_calibration.json` — calculs de ce document (Wilson, KAT, conversions).

**Sources externes (citées, avec URL et date)**
13. Brier, G. W., *Verification of forecasts expressed in terms of probability*, Monthly Weather Review 78(1):1–3, **1950** (repris de R3 §A.4-17, consulté le 15/10/2026).
14. Murphy, A. H., *A New Vector Partition of the Probability Score*, J. Appl. Meteor. 12(4):595–600, **1973** — <https://doi.org/10.1175/1520-0450(1973)012%3C0595:ANVPOT%3E2.0.CO;2>.
15. Naeini, Cooper & Hauskrecht, *Obtaining Well Calibrated Probabilities Using Bayesian Binning*, AAAI **2015** — <https://ojs.aaai.org/index.php/AAAI/article/view/9602> (URL par R3, consultée le 15/10/2026).
16. Wilson, E. B., *Probable Inference, the Law of Succession, and Statistical Inference*, JASA 22(158):209–212, **1927** — <https://doi.org/10.1080/01621459.1927.10502953> (vérifiée le 15/10/2026).
17. Bailey & López de Prado, *The Deflated Sharpe Ratio*, JPM 40(5), **2014** — <https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf> (via W2-D §A.2.3).
18. Thinking Machines Lab, *Defeating Nondeterminism in LLM Inference*, **10 septembre 2025** — <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference> (via B1 §6.2).
19. Sheppard, K., documentation `arch` — bootstraps de séries (`CircularBlockBootstrap`, `StationaryBootstrap`), consultée le 15/10/2026 via R3 §A.4-21 — <https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html>.
20. ENS DAO IPS 6.46 (KPK, 8 mai 2026 ; thread clos 11 août 2026) — runway 49,34 M$ = 3 ans, opex 16,4 M$/an — <https://discuss.ens.domains/t/6-46-social-2026-endowment-investment-policy-update/22106> (via W2-D §A.1.1).
21. Références épisodes (déjà sourcées dans les rapports, rappel) : Fed FEDS Notes (17/12/2025) ; Aave governance rsETH incident report (20/04/2026) ; LlamaRisk (20/04/2026) ; cointelegraph USD0++ ; incrypted/onchainatlas xUSD — voir les sources complètes dans W2-A/W2-B/W2-D/W3-C.

## Non trouvé (à ne pas combler par des inventions)

1. **Aucun format standard public d'« outcome » pour agents financiers** (le format §a.4 est une conception ORVYREN, alignée sur la chaîne de provenance B2) — non trouvé lors des lectures du 15/10/2026 (les formats voisins — PROV-O, bitemporal — ne spécifient pas les outcomes de prévision).
2. **Aucune distribution publique de scénarios de dépeg** ni **fréquence publique de `P(obligation)`** — non trouvé (confirmé w2-D §Non trouvé 4–6, 15/10/2026).
3. **Aucun seuil de calibration « industriel »** (quel ECE/N minimal admet un régulateur pour ce type de système) : non trouvé ; nos seuils (§b.3) sont des **[PROPOSITION]**, pas des normes.
4. **Aucun paramètre `seed` documenté** chez DeepSeek/MiMo (B1 §2.5, pages officielles du 15/10/2026) — la reproductibilité passe par le journal, pas par la graine.
5. **Aucune cible chiffrée publique** de desk (Sharpe, budget de drawdown) — W2-D §Non trouvé 1 (réaffirmé).
6. **Aucun standard** pour la classification DEV/EVAL d'un agent d'évaluation financière (les pratiques de pré-enregistrement viennent des sciences ; R3 §A.4-23) — les règles §d.2 sont des [PROPOSITION].

---

*Tout est reproductible depuis `D:\orvyren_core`. Ce document ne remplace pas les rapports cités : il les rend exécutables. Aucun commit git n'a été effectué (règle projet : l'orchestrateur seul commite).*
