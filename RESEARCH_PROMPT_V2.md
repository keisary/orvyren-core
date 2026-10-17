# ORVYREN — Research Brief V2

**Statut : INTERNE — NE PAS SOUMETTRE AU CONCOURS.**
**Date : 2026-10-17.**
**Donneur d'ordre : Jovanny (Team Leader).**
**Objet : reconstruire ORVYREN comme un vrai système, avec le graphe comme cœur de l'innovation.**
**Dossier de campagne : `D:/orvyren_research_v2_2026-10-17/`.**
**Dépôt : `D:/orvyren_core` (privé).**

> **Lis ce document en entier avant de répondre.**
> Cette recherche est donnée **en parallèle à plusieurs IA**. Tu n'es pas seul. Tu verras des fichiers que tu n'as pas écrits. Lis `INDEX.md` avant d'écrire, ajoute ta ligne, ne modifie jamais le rapport d'une autre IA. Si tu es en désaccord, écris un rapport de contradiction ; ne supprime pas.
>
> **Prends le temps nécessaire.** Plusieurs heures de lecture et de recherche, pas une réponse de dix minutes. La qualité prima sur la vitesse. Mais la vitesse d'exécution du plan, ensuite, compte : le concours est dans **72 heures**.
>
> **Recherche seulement.** Ne modifie pas le code, ne fais pas de `git`, ne lance aucune transaction, ne touche à aucune clé, ne crée aucun fichier dans le dépôt en dehors du dossier de recherche.

---

## 0. Pourquoi cette campagne existe

ORVYREN-Core est candidat au **2026 Shenzhen International FinTech Competition — International Track — Thème F « Agent Wallet / Autonomous On-chain Wallet »**. La deadline de soumission est le **20/10/2026 à 15:59 UTC** (23:59 Pékin). Le barème est **40 % accomplissement, 30 % sécurité, 30 % innovation**, avec un bonus Challenge de 0 à 5. Le concours encourage les projets **ambitieux et importants** ; un prototype étroit, même propre, ne passera pas la sélection.

Le projet a construit quelque chose de réel : une politique de 14 règles hors LLM, une exécution signée sur testnet, des reçus, un dossier d'audit T10, un rejeu PIT, 844 tests. **Mais ce n'est pas le système décrit par l'idée d'origine.** C'est le **noyau de confiance** d'un système qui n'a pas été construit.

La phrase qui doit guider toute la campagne :

> **Nous avons assez construit la preuve du système. Il faut maintenant construire le système.**

Cela ne veut pas dire jeter le noyau de confiance. Cela veut dire arrêter de le présenter comme le produit, et construire autour de lui : les données, le graphe, les agents outillés, la mémoire, la recherche, le produit.

---

## 1. Le diagnostic, sans langue de bois

Les reproches du donneur d'ordre, reformulés comme des exigences de recherche :

1. **Le système est construit autour d'un cas, pas d'un persona ni d'un problème.** Le cas `usdc-2023-03` est devenu l'identifiant du système (`decide.py:51`, `:190`). Un produit traite une **classe de situations** pour un **utilisateur récurrent**, pas un épisode historique.
2. **La partie agent est mal maîtrisée.** Un agent, ce n'est pas un prompt qui répond : c'est **un LLM + des outils callables + une mémoire + une boucle de contrôle**. Aujourd'hui, les outils sont des lookups sur fixtures, sans réseau, et le journal est une trace, pas une mémoire interrogeable.
3. **Il n'y a pas de vraie pipeline de collecte en inférence.** `collect_corpus.py` est un collecteur one-shot pour un cas. Il n'y a ni scheduler, ni worker, ni watermark, ni source manifest, ni reprise. Les agents ne peuvent pas déclencher une recherche : la recherche est un **enum** déterministe (RDOF) sur des faits déjà enregistrés, pas un **outil**.
4. **Le « cas contrôlé » contamine tout** : les branches, le graphe, l'évaluation, l'UI. Un seul cas câblé, 2 fenêtres EVAL sautées (EVAL N=0), 12 écrans statiques d'audit. Chaque brique est optimisée pour un test de fixtures, pas pour un système ouvert.
5. **Le graphe est ridiculement petit.** 520 observations, **4 relations**, 4 claims, 0 table `entities`/`events`, 208 Ko. Or le catalogue ORVYREN définit **34 types de relations** (8 preuve/dérivation, 15 structure/exposition, 3 mécanisme économique, 8 contrainte/permission), un **record à 17 champs**, et **8 requêtes Q1–Q8**. Le graphe est un catalogue, pas un graphe.
6. **La construction multi-agent n'est pas maîtrisée.** Deux rôles effectifs (orchestrateur + critique), un seul outil par tâche, pas de mémoire, pas de reprise, pas d'évaluation d'agent. Il faut **copier les patterns éprouvés** avant d'ajouter une « sauce » originale.

**Ne défends pas le système actuel. Vérifie, mesure, confronte, propose.** Si une prémisse de ce brief est fausse, dis-le avec des preuves. Si tu trouves un fait qui contredit le diagnostic, écris-le : c'est utile.

---

## 2. La direction : le graphe est l'innovation, pas les agents

Les agents qui réfléchissent, appellent des outils, font des recherches et exécutent des ordres **existent déjà partout**. Ce n'est pas un différenciateur en 2026. La sécurité et la preuve sont nécessaires, mais elles ne suffisent pas : le projet a déjà beaucoup poussé la sécurité, et le jury peut le voir comme une couche d'audit, pas comme un agent wallet ambitieux.

**La vraie originalité d'ORVYREN doit être le graphe** : une représentation **dynamique, temporelle, provenance-aware, épistémiquement explicite et orientée décision** du monde on-chain et financier. Un agent générique ne peut pas décider avec la même qualité s'il n'a pas cette représentation. Le graphe doit devenir :

- le **cœur du produit** (pas un décor pour une démo) ;
- le **principal outil des agents** (requêtes, snapshots, chemins, contradictions) ;
- le **support de la décision** (exposition, propagation, concentration, permissions, scénarios) ;
- la **preuve de l'innovation** (ce que le jury voit et comprend en premier).

La question centrale de la campagne :

> **Quel graphe faut-il construire pour qu'ORVYREN prenne de meilleures décisions qu'un agent outillé sans graphe, et pour que ce graphe soit visible, requêtable et crédible en 72 heures ?**

---

## 3. Ce que MIMIR a réellement cherché à faire pour le graphe

**Important : ne copie pas le T0 de MIMIR. Copie sa vision du graphe.** Le T0 est un slice volontairement minimal (79 événements, 10 relations, Parquet/DuckDB, pas de résolution d'entités/événements, pas de base graphe). La vision, elle, est un **Dynamic Financial Knowledge Graph (DFKG)** :

- **Dynamic** : le graphe évolue ; les relations sont créées, renforcées, affaiblies, suspendues, rejetées, réactivées ; l'histoire est conservée, jamais réécrite.
- **Time-aware** : six horloges (événement, publication, observation, effet, validité, révision) ; PIT strict ; on ne confond jamais « le monde à T » et « ce que le système savait à T ».
- **Provenance-aware** : chaîne `Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome`, chaque flèche étant une ligne explicite, pas du texte libre.
- **Epistemically explicit** : `FACT`, `REPORTED`, `STATISTICAL`, `CAUSAL-DOCUMENTED`, `CAUSAL-HYPOTHESIS`, `MODEL-INFERRED`, `REJECTED` ; une prédiction ne devient jamais un fait ; les contradictions sont conservées.
- **Relation-first** : une relation est un objet de première classe avec cause/effet, mécanisme, conditions, régime, horizon, statut épistémique, signe, provenance, cycle de vie, confiance.
- **Causal/propagation** : le graphe ne sert pas qu'à décrire ; il propage des effets (structure + mécanismes + conditions + délais + probabilité + feedback), avec itération bornée, jamais une traversée non contrainte.
- **Portfolio-aware** : le portefeuille est un état du système, pas une sortie ; les expositions directes et indirectes sont dans le graphe.
- **Multi-horizon** : les effets n'ont pas tous le même horizon ; les scénarios et prévisions sont liés.
- **Révisable** : `DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED`, avec archivage des rejets et conditions de réactivation.
- **Auditable** : une décision se reconstruit de l'outcome jusqu'à la source, via les relations et les preuves.

**Ce que MIMIR n'a pas résolu et qu'ORVYREN doit résoudre pour le on-chain :**

- la résolution d'entités et d'événements à l'échelle (le T0 ne l'exerce pas) ;
- le stockage graphe à l'échelle (le T0 reste sur Parquet/DuckDB) ;
- l'extraction documentaire fiable avec ancrage et validation ;
- le lien entre graphe, agents outillés et décision en temps réel ;
- la propagation sur des mécanismes DeFi (collatéral, oracles, ponts, gouvernance, rôles) ;
- la preuve que le graphe apporte un **gain de décision** mesurable, pas seulement une belle visualisation.

**Documents à lire (chemins exacts) :**

| Document | Pourquoi | Sections critiques |
|---|---|---|
| `D:/midas_v2/MIMIR/docs/MIMIR_Technical_Design.md` | Spécification technique du DFKG | §0.3 (statuts), §5.4 (temps/provenance), §6.3 (propagation), §8.3 (révision), §10.1–10.6 (objet, event, temps, store), §11.2–11.4 (relation, causalité, propagation) |
| `D:/midas_v2/MIMIR/docs/MIMIR_Project_Description_V3.docx` | Vision et principes | §1.2 (principes), §5 (Wave 1 — Knowledge Foundation), §6 (Wave 2 — World Intelligence), §8 (Wave 4 — revision/audit) |
| `C:/Users/User/Downloads/Project_2_DFKG_Research_State_0_a11y.docx` | **La vision réelle du graphe** (pas le T0) | §3.1, §5, §7, §8, §9, §10, §11, §12, §13, §14, §16, §17–18, §20–21 |
| `D:/midas_v2/MIMIR/docs/MIMIR_Critical_Review_v3.md` | Ce que le T0 ne couvre pas | §4 (points à trancher), §5 (verdict) |
| `D:/orvyren_archive_2026-10-15/research/B2_GRAPHE_ETUDE.md` | **Le pont MIMIR → ORVYREN** : 34 relations, record 17 champs, PIT, stockage, pipeline, Q1–Q14, ML | §0 (résumé), §1 (temporel/PIT), §2 (stockage), §3 (catalogue), §4 (pipeline), §5 (ML), §6 (requêtes), §7 (recommandations) |

**Question de recherche :** quelles parties de cette vision sont (a) indispensables au MVP 72 h, (b) utiles mais reportables, (c) du pur sur-design ? Justifie chaque choix par un cas d'usage et un coût, pas par une préférence technologique.

---

## 4. Ce qu'ORVYREN a déjà, et ce qui manque

### 4.1 Actifs à réutiliser

- **34 types de relations** : `src/orvyren/graph/catalog.py:272–408` ; répartition 8 / 15 / 3 / 8 ; `catalog_stats()` le vérifie (`:414–419`). Le catalogue a été construit à partir de MIMIR/RC (14 types), du domaine DeFi/on-chain (13 types) et de besoins explicites (7 types).
- **Record de relation à 17 champs** : `src/orvyren/graph/record.py:86–135`, groupes `:138–156` ; il distingue `epistemic_status`, `lifecycle`, `validation_status` et porte `valid_from/valid_to`, `revision`, `provenance_refs`, `source_family_id`, `extract_method`, `chain_ref`, `confidence`, `payload`.
- **8 requêtes Q1–Q8** : `src/orvyren/graph/queries.py:10–27` — exposition consolidée, chemins de dépendance, contradictions, état PIT, chronologie, provenance, concentration, permissions. Elles sont écrites comme **contrats de test** sur des `RelationRecord`.
- **3 fixtures d'épisodes** : `fixtures/graphs/usdc_2023-03.json` (9 records, 6 kinds), `steth_2022-06.json` (4 records, 2 kinds), `rseth_2026-04.json` (7 records, 6 kinds) — 20 records au total, 13 kinds distincts.
- **Snapshots + provenance** : `evidence/graph_snapshots/...` ; store append-only avec triggers `UPDATE`/`DELETE` interdits (`src/orvyren/graph/store.py:1–16,136–141`).
- **Noyau de confiance** : `policy/`, `execution/`, `replay/`, `verify/`, `audit/`, 844 tests, T10 16/16, preuves on-chain.
- **Une base de décision** : `decide.py`, `decision/rdof.py`, 3 axes, hypothèses, `NO-ACTION`, `INCONCLUSIVE`.

### 4.2 Le trou central, mesuré

| Indicateur | Valeur réelle | Preuve |
|---|---:|---|
| Observations dans le graphe live | **520** | `evidence/graph.sqlite` |
| Claims | **4** | `evidence/graph.sqlite` |
| Relations | **4** | `evidence/graph.sqlite` |
| Types de relations instanciés dans le graphe live | **1** : `SUPPORTS` | 4 lignes `supports` |
| Arêtes structurelles/économiques dans le graphe live | **0** | aucune `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `DEPLOYED_ON`, `PRICED_BY`, etc. |
| Tables `entities` / `events` | **0 / 0** | schéma SQLite |
| Taille du graphe | **208 Ko** | fichier SQLite |
| Types de relations définis | **34** | `catalog.py` |
| Types réellement utilisés dans les 3 fixtures | **13** | 20 records |
| Requêtes Q1–Q8 | **8 définies**, exécutées sur des fixtures Python, pas sur le graphe SQL | `queries.py` |
| Store SQLite | table `relations` à 7 colonnes (`src`, `dst`, `kind`, `source_family_id`, `extract_method`, `revision`, `inserted_at`) | `store.py:94–104` |
| Record 17 champs | défini, mais **non utilisé par le store SQLite** | `record.py` vs `store.py` |
| Collecte | one-shot `collect_corpus.py` ; pas de scheduler/worker | `collect_corpus.py` |
| Outils agents | 7, tous fixtures, zéro réseau | `agents/tools.py:10–17,75–84` |
| Mémoire agent | journal append-only, pas de retrieval | `agents/journal.py` |
| UI | 12 écrans statiques d'audit | `ui/screens.py:617` |
| EVAL | **N = 0**, 2 fenêtres sautées | `evidence/evaluation_eval/` |

**Conclusion du trou :** le graphe n'est pas « petit » ; il est **structurellement absent**. Les 34 relations sont un catalogue, les 17 champs sont une spécification, les Q1–Q8 sont des tests sur fixtures. Le graphe live ne contient que des liens de support entre 4 claims et une hypothèse. Il n'y a pas de monde on-chain modélisé.

### 4.3 Le problème agent, mesuré

- `agents/contracts.py:202–212` : `LLMBackend.complete()` ne prend que `system_prompt` + `payload` ; **pas de paramètre `tools`**, pas de `tool_calls`, pas de messages d'outil.
- `agents/llm.py` : transport **OpenAI-compatible JSON mode** (`json_object`), pas le mode natif de tool calling.
- `agents/loop.py:8` : **une seule tâche en vol, un seul outil par tâche**, un appel de planification et une évaluation.
- `agents/tools.py` : 7 outils déterministes sur fixtures ; `read_prices` ignore `from`/`to` (test `tests/test_agents_tools.py:155`).
- `agents/journal.py` : trace d'audit, pas de store long terme, pas de retrieval.
- `config/models.json` : rôles déclarés (orchestrateur, explorateur, critique, canoniseur), mais l'exécution réelle est orchestrateur + critique ; pas de spécialistes outillés.

**Le tool calling des LLM :** les modèles utilisés (DeepSeek, MiMo, GLM, Kimi) sont des LLM avec, pour certains, une API de **function/tool calling**. Le modèle ne exécute pas l'outil : il émet un appel structuré (`tool_calls`) ; c'est le runtime qui valide, exécute et renvoie le résultat. DeepSeek documente ce mécanisme (`https://api-docs.deepseek.com/guides/tool_calls`) ; le code actuel ne l'utilise pas. Pour MiMo/GLM/Kimi, **vérifier chaque endpoint** : compatible OpenAI ne signifie pas nécessairement tool calling natif, et les formats peuvent différer. Une des questions de recherche est de concevoir un **adaptateur provider-agnostique** avec fallback JSON strict.

---

## 5. Questions de recherche, par chantier

Chaque rapport doit répondre à **un** chantier principal (ou explicitement couvrir plusieurs si le donneur d'ordre l'a demandé). Numérote ton fichier avec le préfixe du chantier.

### A. Graphe — ontologie, sémantique, modèle (`10_graph/`)

**Priorité 0. C'est le chantier central.**

1. **Audit des 34 relations.** Pour chaque type : définition, famille, sujet→objet, direction, transitivité, statut d'instanciation actuel (live/fixture/jamais), source de données réaliste, requête qui l'utilise, priorité MVP (`P0/P1/P2`), recommandation (`garder / fusionner / supprimer / ajouter`). Produis un tableau complet, pas une liste partielle.
2. **Quelles relations manquent pour le on-chain ?** Le catalogue a 34 types, mais le monde DeFi a des objets spécifiques : marchés, réserves, positions, dettes, LTV, seuils de liquidation, oracles, heartbeats, caps, pauses, rôles, allowances, ponts, DVN, timelocks, upgrades, gouvernance, PSM, wrappers, LST, vaults, DEX pools. Lesquels sont des nœuds, des événements, des relations, des paramètres ? Ajoute ce qui manque, avec une définition et un cas d'usage.
3. **Node/event model.** Le graphe actuel n'a ni `entities` ni `events`. Propose un modèle de nœuds et d'événements : identité canonique, adresses (`chain:address`), alias, cycle de vie d'un événement (rumor → announcement → confirmation → implementation → consequence), Actual/Expected/Surprise, event sourcing. Comment les événements deviennent-ils des nœuds de première classe sans exploser le nombre de nœuds ?
4. **Relation record.** Le record à 17 champs est-il suffisant ? Ajoute les champs DeFi nécessaires (block, tx, log_index, chain_id, finality, oracle heartbeat, role key, allowance, cap, LTV, LT, pause state…). Lesquels vont dans `payload` vs colonnes de première classe ? Comment garantir la validation ?
5. **Statuts épistémiques et cycle de vie.** Le catalogue distingue `FACT/REPORTED/STATISTICAL/CAUSAL-DOCUMENTED/CAUSAL-HYPOTHESIS/MODEL-INFERRED/REJECTED` et un lifecycle. Ces statuts sont-ils utilisés dans le code ? Comment empêcher une prédiction de devenir un fait ? Comment conserver une contradiction sans la fusionner ?
6. **Temporalité / PIT.** Six horloges, bitemporel, block time, `valid_from/valid_to`, `inserted_at`, `revision`, reorg, finality. Quel modèle exact pour ORVYREN ? Comment répondre à « le monde à T » vs « ce que le système savait à T » ? Quel est le coût en SQLite/Postgres ?
7. **Provenance et indépendance des sources.** Chaîne `Source → Observation → Extraction → Claim → Relation → Hypothesis → Prediction → Outcome` ; `source_family_id` ; éviter de compter deux fois la même source ; confiance. Comment l'implémenter sans noyer l'agent ?
8. **Ontologie standard vs maison.** FIBO est-il utile pour le on-chain ? Faut-il un noyau FIBO + extension DeFi, ou une ontologie DeFi native ? Compare 3 options (FIBO, schéma maison, hybride) sur précision, coût, interopérabilité, délai 72 h.
9. **Schéma cible.** Propose un schéma concret : tables/nœuds/arêtes, clés, index, contraintes, vues matérialisées, requêtes récursives. Compare **PostgreSQL** (tables + SQL/PGQ), **SQLite** (démo), **DuckDB/Parquet** (analytique), **Neo4j AuraDB Free** (graphe), **Kuzu** (écarté ? vérifier). Recommande une trajectoire 72 h → 2–4 semaines.
10. **Benchmark du graphe.** Définis un jeu de données et des métriques : nombre d'événements, types de relations, couverture de provenance, latence Q1–Q8, requêtes de propagation, taux de contradictions, PIT correct. Compare au moins 3 architectures sur le même benchmark.

### B. Graphe — données, ingestion, échelle (`30_data/`)

**Priorité 0.**

1. **Sources pour le on-chain.** RPC archive, `eth_getLogs`, The Graph, Ponder, DeFiLlama, docs de protocoles, gouvernance, bridges, oracles, prix CEX/DEX, Safe/Zodiac. Pour chaque source : ce qu'elle fournit, PIT, licence, quota, coût, latence, limites, fiabilité.
2. **Choix du premier périmètre.** Un protocole (Aave v3 Base ?), une chaîne (Base ?), une fenêtre (30–90 jours), 3–5 marchés, 10⁴–10⁵ événements. Justifie par la valeur de démonstration, pas par la facilité.
3. **Pipeline.** Scheduler/worker, raw store immuable, hash, `retrieved_at`, normalisation, entity/event resolution, graph writer, watermark, reprise, idempotence, reorg/finality. Propose une architecture 72 h et une architecture 2–4 semaines.
4. **Résolution d'entités/événements.** Déterministe d'abord (`chain:address`, checksum), registre d'entités, alias comme preuves, résolution d'événements (un doc → plusieurs événements ; plusieurs docs → un événement), score de confiance, quarantaine. Où le LLM est-il utile, et où est-il interdit ?
5. **Extraction documentaire.** `GLiNER`, `REBEL`, `LangExtract`, LLM structuré avec ancrage. Comment garantir les offsets, la provenance, la validation, l'absence d'hallucination ? Quelles portes de validation ?
6. **Stockage et échelle.** 10⁴ → 10⁵ → 10⁶ événements. Mesure les coûts, la latence, les index, les requêtes récursives, les vues PIT. Faut-il un graph DB ou Postgres suffit-il ? Ne propose pas une base graphe sans benchmark.
7. **Qualité.** Fraîcheur, complétude, cohérence, duplication, intégrité temporelle, indépendance, schéma. Comment calculer un `quality_score` par source et par relation ? Comment bloquer une décision si la donnée est stale ?
8. **Coût et vitesse.** Le concours impose des sources gratuites et une démo hors-ligne. Propose un plan qui tient en 72 h avec des ressources gratuites, et un plan payant seulement si un gain est démontré.

### C. Graphe — raisonnement, requêtes, produit (`10_graph/` ou `40_product/`)

**Priorité 0.**

1. **Les 10–15 requêtes qui justifient le graphe.** Q1–Q8 existent ; Q9–Q14 sont proposées dans B2 (fraîcheur, faits manquants, invariants inter-chaînes, etc.). Lesquelles sont indispensables à la démo ? Lesquelles sont du confort ? Ajoute les requêtes propres au on-chain : chaîne de collatéral, exposition indirecte, concentration, chemin de dépendance, permission as-of, oracle stale, bridge invariant, contradiction, scénario.
2. **Propagation / contagion.** Comment propager un choc (depeg, freeze, oracle failure, bridge exploit) à travers le graphe ? Règles, décroissance, conditions, horizons, feedback. Quelles relations sont traversables, lesquelles sont interdites (`SUPPORTS` ne propage pas ; `CORRELATES_WITH` ne chaîne pas) ? Comment éviter les conclusions causales abusives ?
3. **Décision basée sur le graphe.** Comment le graphe alimente-t-il les hypothèses, les preuves, la décision, le `NO-ACTION` ? Donne un exemple de bout en bout : signal → requête → preuve → hypothèse → décision → policy → action/refus.
4. **Visualisation.** Quel écran montrer au jury ? Graphe interactif, timeline, chemins, contradictions, preuves, décision. Comment rendre le graphe **lisible en 30 secondes** sans être une décoration ?
5. **Scénario de démo.** Écris un script de 5 minutes : question, données live, 5 requêtes, 3 hypothèses, 2 recherches outillées, décision, policy, tx/reçu. Où le graphe est-il le héros ? Où l'agent est-il visible ?
6. **Évaluation du graphe.** Complétude, provenance, PIT, contradictions, latence, couverture des requêtes, gain de décision vs baseline sans graphe. Propose un protocole N≥30 (ou explique pourquoi N plus petit est non conclusionnel).

### D. Agents — runtime, outils, mémoire (`20_agents/`)

**Priorité 1.**

1. **Tool calling natif vs JSON.** DeepSeek documente les tool calls ; le code actuel utilise JSON mode. Conçois un adaptateur provider-agnostique : schémas JSON, `tools`, `tool_choice`, `tool_calls`, messages `tool`, erreurs, retries, fallback JSON strict. Vérifie MiMo, GLM, Kimi ; ne suppose pas.
2. **Catalogue d'outils ORVYREN.** Propose 8–15 outils : `graph_query`, `graph_snapshot`, `graph_path`, `chain_logs`, `chain_state`, `price_history`, `web_search`, `fetch_document`, `extract_event`, `hypothesis_update`, `evidence_attach`, `portfolio_exposure`, `policy_propose`, `execute_intent` (séparé). Pour chacun : schéma, entrées/sorties, idempotence, timeout, budget, erreurs, droits, traçabilité.
3. **Boucle d'agent.** ReAct ou plan-execute ? Une seule boucle ou orchestrateur + spécialistes ? Comment passer d'un plan à une observation, puis à une mise à jour d'hypothèse, puis à une décision ? Combien d'itérations maximum ? Comment éviter les boucles infinies et les appels coûteux ?
4. **Mémoire.** Working / episodic / semantic / procedural. Que stocker, où, comment retrieval, comment résumer, comment garantir PIT, comment éviter la mémoire inventée ? Compare MemGPT, Zep/Graphiti, LangGraph checkpoints/store, et une solution maison Postgres + FTS/pgvector.
5. **Orchestration multi-agent.** Manager pattern vs handoffs vs swarm. Combien d'agents pour le MVP ? Quels rôles sont réellement utiles (chercheur, extracteur, critique, évaluateur) ? Comment évaluer qu'un agent supplémentaire apporte un gain ? Ne propose pas un swarm sans mesure.
6. **Évaluation agent.** Succès de tâche, outils corrects, preuves nouvelles, couverture, coût, latence, reprises, sécurité. Comment construire un petit benchmark (20–50 tâches) en 72 h ? Quelles baselines A0/A1/A2 ?
7. **Migration du code actuel.** `LLMBackend.complete` → interface avec tools ; `ToolRegistry` → outils réels ; `loop.py` → boucle multi-étapes ; `journal.py` → trace + mémoire. Propose un plan de migration minimal, sans casser les tests.

### E. Produit, persona, concours (`40_product/`, `50_competition/`)

**Priorité 1.**

1. **Persona.** Opérateur de trésorerie on-chain (DAO/protocole) : quel rôle exact, quelles décisions, quelles contraintes, quels outils actuels, quelle douleur, quel budget. Évite le persona vague « DeFi user ».
2. **Job-to-be-done.** « Chaque jour / à chaque alerte, je dois savoir si mon exposition est menacée, pourquoi, avec quelles preuves, et quelle action bornée est admissible. » Traduis en parcours, écrans, données, décisions.
3. **UI.** Un espace d'enquête, pas 12 écrans d'audit : alerte, hypothèses, graphe, preuves, recherche en cours, décision, policy, receipt. Propose une maquette textuelle/wireframe et les 5 interactions clés.
4. **Concours.** Barème 40/30/30 + bonus. Que regarde un jury ? Comment les meilleurs projets se différencient-ils ? Comment le graphe peut-il porter l'innovation sans sacrifier la sécurité ? Quel est le risque de paraître « trop recherche » ou « trop audit » ?
5. **MVP 72 h.** Scope exact, livrables, ordre, effort (h-agent), critères d'acceptation, risques, ce qu'on coupe. Le plan doit être réalisable par 2–3 agents en parallèle, avec un chemin critique clair.
6. **Ce qu'il ne faut pas construire.** Liste explicite : multi-chaîne exhaustif, GNN, GraphRAG produit, base graphe dédiée, 5 agents, UI complète, EVAL N≥100, KMS, etc. Justifie chaque exclusion par le temps et la valeur.

### F. Synthèse (`60_synthesis/`)

**Priorité 0, après les autres rapports.**

1. Lire tous les rapports du dossier (INDEX).
2. Produire une synthèse qui **tranche** : schéma de graphe cible, pipeline de données, runtime agent, UI, plan 72 h, plan 2–4 semaines, risques, questions ouvertes.
3. Ne pas faire un catalogue d'options : choisir une architecture, avec les preuves et les compromis.
4. Estimer l'effort en h-agent et identifier le chemin critique.
5. Lister les 10 décisions que le Team Leader doit prendre, avec une recommandation par défaut.

---

## 6. Format obligatoire de chaque rapport

Chaque rapport est un fichier Markdown autonome. Il doit contenir :

1. **En-tête** : titre, auteur/modèle, date, chantier, statut (`DRAFT`, `REVIEW`, `FINAL`), fichiers lus (chemins exacts), temps passé.
2. **Résumé exécutif** : 10 lignes maximum, avec la recommandation principale.
3. **Contexte et question** : ce que tu cherches à résoudre, ce que tu exclus.
4. **Preuves** : chaque affirmation interne avec `fichier:ligne` ; chaque affirmation externe avec URL + date de consultation. Utilise les labels `[FAIT]`, `[MESURÉ]`, `[HYPOTHÈSE]`, `[PROPOSITION]`, `[INCONNU]`.
5. **Analyse** : options, tradeoffs, ce qui existe déjà, ce qui manque.
6. **Recommandation** : une option principale, pourquoi, ce qu'elle coûte, ce qu'elle risque.
7. **Tableau d'audit des 34 relations** (obligatoire pour les rapports graphe) : type, définition, instanciation actuelle, source, requête, priorité, décision.
8. **Schéma / architecture proposée** : tables, colonnes, index, contraintes, flux. Pour le graphe, un diagramme Mermaid ou ASCII.
9. **Plan 72 h** : ce que tu construirais, dans quel ordre, avec quel effort ; ce que tu coupes.
10. **Plan 2–4 semaines** : ce qui vient après, et pourquoi.
11. **Risques et modes d'échec** : techniques, données, produit, concurrence.
12. **Questions ouvertes** : ce que tu n'as pas pu vérifier ; ce que le Team Leader doit trancher.
13. **Sources** : internes (chemins + lignes), externes (URL + date).
14. **« Ce que je construirais d'abord » / « Ce que je ne construirais pas »** : deux listes courtes.

**Interdits :** conseils génériques (« utilisez un vector DB »), chiffres inventés, benchmarks non exécutés, affirmations non sourcées, propositions de frameworks sans cas d'usage, modifications du code, `git`, transactions, clés.

---

## 7. Dossier, nommage, travail en parallèle

**Dossier de campagne :** `D:/orvyren_research_v2_2026-10-17/`

```
00_brief/          brief, index, conventions
10_graph/          ontologie, schéma, requêtes, raisonnement, benchmark
20_agents/         runtime, outils, mémoire, orchestration, évaluation
30_data/           sources, ingestion, résolution, stockage, qualité
40_product/        persona, JTBD, UI, parcours, métriques
50_competition/    barème, positionnement, démo, risques
60_synthesis/      synthèse, décisions, plan intégré
```

**Nommage :**

```
<chantier>__<sujet>__<auteur-ou-modele>__<YYYY-MM-DD>.md
```

Exemples :

- `10_graph__audit-34-relations__claude__2026-10-17.md`
- `10_graph__schema-cible-postgres__gpt__2026-10-17.md`
- `30_data__ingestion-aave-base__gemini__2026-10-17.md`
- `20_agents__tool-calling-provider-agnostic__deepseek__2026-10-17.md`
- `60_synthesis__architecture-v2__hermes__2026-10-18.md`

**Règles de collaboration :**

- Lis `INDEX.md` avant d'écrire.
- Ajoute une ligne à `INDEX.md` : fichier, auteur/modèle, chantier, date, statut, conclusion en une phrase.
- **N'écrase jamais** un fichier existant. Si tu dois corriger, crée `...__v2.md` et explique le delta.
- Si tu es en désaccord avec un autre rapport, crée `...__contradiction.md` et cite le fichier/ligne contesté.
- Si tu n'as pas accès au système de fichiers, rends le rapport complet dans ta réponse, avec le **nom de fichier exact** en première ligne ; l'humain le sauvegardera.
- Cette campagne est parallèle : d'autres IA peuvent écrire en même temps. Ce n'est pas une erreur si tu vois des fichiers que tu n'as pas créés.

---

## 8. Les documents et le code à lire (liste minimale)

### 8.1 Idée d'origine (à lire avant de proposer)

| Fichier | Ce qu'il faut y chercher |
|---|---|
| `C:/Users/User/fintechathon_recherche/concours/orvyren_v0_1_texte.txt` | §1.1 (cinq capacités), §3 (persona/problème/JTBD), §6–7 (architecture, données, graphe), §8 (branches/recherche), §9 (agents/outils), §13 (expérimentation), §14 (MVP) |
| `C:/Users/User/fintechathon_recherche/orvyren_v02/ORVYREN_Selection_Cas_Usage_V0_1.txt` | §4 (problème/utilisateur/question), §5 (différenciation), §6 (mesures), §7 (validation) |
| `C:/Users/User/fintechathon_recherche/orvyren_v02/ORVYREN_Document_de_reference_V0_2.txt` | §1 (définition), §3 (cas/utilisateur), §5–8 (architecture, données, branches, agents), §12–13 (expérimentation, MVP) |
| `D:/orvyren_core/ORVYREN_DOC1_EXPLICATION_SIMPLE.md` | §2 (pour qui), §3 (boucle), §6 (ce que la v1 devait construire) |
| `D:/orvyren_core/ORVYREN_DOC2_TECHNIQUE_COMPLET.md` | architecture, agents, données, décision |
| `D:/orvyren_core/ORVYREN_DOC3_PROPOSITIONS_ET_ECARTES.md` | options écartées, pourquoi |
| `D:/orvyren_core/ORVYREN_DOC4_PLAN_IMPLEMENTATION.md` | plan initial, lots, W1–W8 |
| `D:/orvyren_core/FREEZE_V2.md` | règles de gel, ce qui est figé |
| `D:/orvyren_core/DEMO_KIT.md` | preuves on-chain, démo |
| `D:/orvyren_core/SECURITY_SELF_ASSESSMENT.md` | sécurité revendiquée (ligne 11 à corriger) |
| `D:/orvyren_core/AUDIT_PROMPT.md` | audit externe, questions |

### 8.2 État actuel et analyse

| Fichier | Ce qu'il faut y chercher |
|---|---|
| `D:/orvyren_core/docs/REANALYSE_ORVYREN_2026-10-17.md` | la réanalyse complète, les six écarts, l'architecture cible |
| `D:/orvyren_core/docs/RECHERCHE_AMELIORATION_ET_SCALING_2026-10-17.md` | mesures, top 10, scalabilité |
| `D:/orvyren_archive_2026-10-15/research/B2_GRAPHE_ETUDE.md` | **le document graphe central** : 34 relations, 17 champs, PIT, stockage, pipeline, Q1–Q14, ML |
| `D:/orvyren_core/src/orvyren/graph/catalog.py` | 34 types, familles, stats |
| `D:/orvyren_core/src/orvyren/graph/record.py` | record 17 champs, validation |
| `D:/orvyren_core/src/orvyren/graph/queries.py` | Q1–Q8 |
| `D:/orvyren_core/src/orvyren/graph/store.py` | store SQLite append-only, schéma mince |
| `D:/orvyren_core/src/orvyren/graph/models.py` | modèles Observation/Claim/Relation/Hypothesis/DecisionNode |
| `D:/orvyren_core/fixtures/graphs/*.json` | 3 épisodes, 20 records, 13 kinds |
| `D:/orvyren_core/evidence/graph.sqlite` | 520 observations, 4 claims, 4 SUPPORTS |
| `D:/orvyren_core/evidence/quality_report.json` | compteurs, qualité |
| `D:/orvyren_core/evidence/graph_snapshots/` | snapshots + provenance |
| `D:/orvyren_core/src/orvyren/agents/tools.py` | 7 outils fixtures |
| `D:/orvyren_core/src/orvyren/agents/loop.py` | boucle bornée, 1 tâche/1 outil |
| `D:/orvyren_core/src/orvyren/agents/journal.py` | journal append-only |
| `D:/orvyren_core/src/orvyren/agents/llm.py` | JSON mode, pas de tool calling natif |
| `D:/orvyren_core/src/orvyren/agents/contracts.py` | `LLMBackend`, `ToolResult`, `Tool` |
| `D:/orvyren_core/src/orvyren/decide.py` | cas unique, décision |
| `D:/orvyren_core/src/orvyren/decision/` | RDOF, axes, hypothèses |
| `D:/orvyren_core/src/orvyren/policy/` | 14 règles, PolicyState |
| `D:/orvyren_core/src/orvyren/execution/` | intent, ledger, signer, receipt |
| `D:/orvyren_core/collect_corpus.py` | collecte one-shot |
| `D:/orvyren_core/src/orvyren/data/` | adaptateurs Aave/Chainlink/Curve/RPC |
| `D:/orvyren_core/config/models.json` | modèles, rôles, prix, fallbacks |
| `D:/orvyren_core/src/orvyren/ui/screens.py` | 12 écrans statiques |
| `D:/orvyren_core/tests/` | tests agents, graphe, décision, policy, exécution |

### 8.3 Sources externes utiles (à vérifier et dater)

- **MIMIR / DFKG** : voir §3.
- **Ontologies** : FIBO (`https://spec.edmcouncil.org/fibo/`), PROV-O (`https://www.w3.org/TR/prov-o/`).
- **Temporalité** : SQL:2011 temporal features (Snodgrass/Kulkarni), Martin Fowler bitemporal (`https://martinfowler.com/articles/bitemporal-history.html`), PostgreSQL 18/19 SQL/PGQ, DuckDB DuckPGQ.
- **Mémoire d'agents** : MemGPT (arXiv:2310.08560), Zep/Graphiti (arXiv:2501.13956), LangGraph persistence (`https://docs.langchain.com/oss/python/langgraph/persistence`).
- **Agents** : Anthropic *Building effective agents* (`https://www.anthropic.com/engineering/building-effective-agents`), OpenAI *A practical guide to building agents* (`https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents`), ReAct (arXiv:2210.03629), 12-Factor Agents (`https://github.com/humanlayer/12-factor-agents`), AutoGen (arXiv:2308.08155), Voyager (arXiv:2305.16291).
- **Tool calling** : DeepSeek (`https://api-docs.deepseek.com/guides/tool_calls`) ; vérifier MiMo/GLM/Kimi dans leurs docs.
- **Données on-chain** : The Graph (`https://thegraph.com/docs/en/subgraphs/querying/introduction/`), Ponder (`https://ponder.sh/docs/get-started`), DeFiLlama (`https://api-docs.defillama.com/`), Aave docs, Safe/Zodiac docs, Base RPC (`https://sepolia.base.org` pour le testnet ; mainnet Base pour les données).
- **Stockage** : PostgreSQL SQL/PGQ, Neo4j AuraDB Free, DuckDB/DuckPGQ, SQLite recursive CTE, `pgvector`.

---

## 9. Les questions auxquelles la campagne doit répondre

À la fin, le Team Leader doit pouvoir répondre **oui** ou **non** à ces questions, avec des preuves :

1. **Graphe** : a-t-on un schéma de graphe qui modélise réellement le monde on-chain (entités, événements, relations, paramètres, permissions) et qui tient 10⁴–10⁵ événements en 72 h ?
2. **Données** : a-t-on une pipeline qui ingère des données live, avec source manifest, PIT, provenance, reprise, et qui alimente le graphe sans intervention manuelle ?
3. **Agents** : a-t-on un agent qui appelle réellement des outils (pas des fixtures), qui consulte le graphe, qui déclenche une recherche, qui met à jour ses hypothèses et qui garde une mémoire ?
4. **Produit** : a-t-on un parcours utilisateur et un écran qui montrent le graphe, les preuves, la recherche, la décision, la policy et l'action ?
5. **Innovation** : le graphe est-il le **héros** de la démo, et pas un décor ? Un jury peut-il dire « je n'ai jamais vu ce graphe-là » ?
6. **Sécurité** : le noyau de confiance existant est-il conservé et branché sur le nouveau système, sans régression ?
7. **72 h** : le plan est-il réalisable par 2–3 agents, avec un chemin critique et des critères d'acceptation ?
8. **Honnêteté** : sait-on ce qui est live, ce qui est replay, ce qui est fixture, ce qui n'est pas revendiqué ?

---

## 10. Ton et posture

- **Ne flatte pas.** Si le projet est faible sur un point, dis-le.
- **Ne récite pas** les documents : apporte une analyse, des chiffres, des schémas, des décisions.
- **Ne propose pas** un framework ou une base de données sans avoir mesuré le besoin.
- **Ne copie pas** le T0 de MIMIR : copie la vision, adapte au on-chain, et dis ce qui ne marche pas.
- **Ne construis pas** un énième agent générique : le graphe est la différence.
- **Pense produit** : un utilisateur, un job, une preuve, une action, un résultat.
- **Pense concours** : 72 h, 40/30/30, top 10, un jury qui voit beaucoup de démos.
- **Pense vitesse** : P0 d'abord, chemins critiques, technologies boring, gratuit, réutilisable.

---

## 11. Instruction finale

**Lis les documents. Mesure le code. Cherche l'état de l'art. Prends le temps.**
Puis écris un rapport qui **tranche** : ce qu'il faut construire pour que le graphe devienne le cœur d'ORVYREN, ce qu'il faut couper, et comment le faire en 72 heures sans refaire un prototype.

**La question n'est pas « comment améliorer le prototype ? ». La question est « quel système faut-il construire, et pourquoi le graphe en est-il le cœur ? ».**

---

*Brief interne — ne pas inclure dans les livrables de soumission. Toute mention de MIMIR doit être retirée des documents publics ; les rapports de recherche restent internes.*
