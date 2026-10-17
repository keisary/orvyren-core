# Réconciliation et état de la recherche — 17/10

**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Auteur** : Hermes.
**Date** : 2026-10-17.
**Objet** : répondre à « as-tu fini toute la recherche ? », intégrer les contradictions des autres IA, et fixer ce qui reste avant de construire.

---

## 0. Réponse directe

**Non. Toute la recherche décrite par le prompt n'est pas terminée.**

J'ai couvert le **cœur graphe** (audit, schéma, benchmark synthétique, synthèse draft) et j'ai commencé l'implémentation du schéma. Les autres chantiers du brief — données, agents, produit, concurrence, synthèse finale — ne sont pas terminés par moi. D'autres IA ont déposé des rapports graphe et deux contradictions qui corrigent mes conclusions ; elles ne sont pas encore intégrées dans une synthèse finale.

| Chantier | État | Fichiers / preuves | Ce qui manque |
|---|---|---|---|
| `10_graph` — audit 34 relations | **FAIT, portée contestée** | `10_graph__audit-34-relations__hermes…` | Codex conteste le quota 16–18 ; slice ramené à 8–10 |
| `10_graph` — schéma cible | **FAIT, révisé** | `10_graph__schema-cible__hermes…` | SQL/PGQ retiré ; index `(src,kind)` retiré ; benchmark v4 à intégrer |
| `10_graph` — entités/événements | **PARTIEL** | schéma `nodes`/`events` dans le rapport | résolution d'entités/événements non implémentée |
| `10_graph` — temporalité/PIT | **PARTIEL** | `valid_from/to`, `inserted_at/revision`, block | reorg, finalité, PIT sur données réelles non testés |
| `10_graph` — requêtes/propagation | **PARTIEL** | Q1–Q8 Python sur fixtures ; SQL décrit | Q1–Q8 SQL sur store live, Q9–Q14 |
| `10_graph` — benchmark | **FAIT, synthétique** | `_bench/bench_results_guarded.json` | benchmark Aave réel, p50/p95, parité |
| `30_data` — sources/ingestion | **NON FAIT** | plan dans le schéma | pipeline, RPC, manifest, watermark, reorg |
| `30_data` — résolution/extraction | **NON FAIT** | — | entités, événements, documents |
| `20_agents` — tool calling | **NON FAIT** (note conceptuelle seulement) | réponse chat + brief | adaptateur provider-agnostique, outils live |
| `20_agents` — runtime/mémoire | **NON FAIT** | — | boucle, mémoire, checkpoints, évaluation |
| `40_product` — persona/UI | **NON FAIT** | — | persona, JTBD, écran d'enquête |
| `50_competition` — positionnement | **NON FAIT** | — | barème, démo, risques |
| `60_synthesis` — synthèse | **DRAFT** | `60_synthesis__graph-first-architecture…` | attendre les autres rapports et trancher |

**Conclusion** : la recherche n'est pas « finie ». Le graphe est défriché et le schéma est implémenté, mais le système n'est pas encore alimenté, requêtable par SQL, ni produit.

---

## 1. Contradictions acceptées

### 1.1 SQL/PGQ n'existe pas dans PostgreSQL livrable — MiniMax a raison

Mon rapport citait `PostgreSQL + SQL/PGQ` comme cible et une URL `ddl-property-graphs.html` (404). Le patch SQL/PGQ a été commité puis **reverté** ; PG 19 RC1 ne le livre pas. La seule capacité temporelle native à retenir est **`WITHOUT OVERLAPS`** (PG 19), et les requêtes de chemin restent en **`WITH RECURSIVE`**.

**Correction appliquée** : rapport schéma, audit et synthèse réécrits ; sources remplacées par la doc PostgreSQL courante, `WITHOUT OVERLAPS`, et les commits de rollback. Plus aucune dépendance à SQL/PGQ.

### 1.2 L'index `(src, kind)` est nuisible — MiniMax a raison

Mesure MiniMax : sur 50 000 arêtes, Q1 passe de **0,0537 s sans index manuel** à **6,2687 s avec `(src, kind)`** (×117) ; ×139 à 100 000. Mécanisme : l'index manuel empêche SQLite de construire son index automatique `(lifecycle, src)`, et le plan retombe sur `(lifecycle)` seul.

**Correction appliquée** : index `(src, kind)` / `(dst, kind)` retirés du DDL du rapport et du code (`store.py`). La cible est une table **`edge_current`** matérialisée, indexée sur `(src, kind)` seulement après mesure.

### 1.3 Le benchmark v2 est dégénéré — MiniMax a raison

Mon générateur v2 avait `q2_paths = 1` et ~60 arêtes/nœud ; il n'exerçait pas la propagation. MiniMax v4 mesure **Q1 0,055 s à 50 000** et **0,220 s à 100 000** (×342 vs Python ; 31,7 Mo). La conclusion « SQL ≫ Python » tient, mais mes seuils étaient trop laxistes.

**Correction appliquée** : le rapport garde le tableau v2 comme **plancher conservateur**, ajoute les chiffres v4, et fixe les seuils à **< 0,25 s à 50k** et **< 0,5 s à 100k**. Le benchmark Aave réel reste à faire.

### 1.4 Le scope 16–18 relations / 10⁴–10⁵ événements en 72 h est trop ambitieux — Codex a raison

Codex conteste le quota et l'absence de preuve de débit RPC. Le slice réaliste est **un réseau, un protocole/marché, un bloc, un portefeuille**, **8–10 relations**, **10 000+ événements** (50 000 seulement si le débit est mesuré), avec preuves/PIT/inconnues.

**Correction appliquée** : audit, schéma et synthèse ramenés à **8–10 relations core** et **10 000+ événements** ; 16 reste un maximum conditionnel, pas un quota.

### 1.5 Deux représentations de relation sans pont — MiniMax a raison, partiellement corrigé

Le dépôt a `models.Relation` (6 champs, kinds minuscules) et `record.RelationRecord` (17 champs, kinds majuscules). Q1–Q8 lisent le second ; le store live écrit le premier. J'ai ajouté `insert_relation_record` (pont pour les nouvelles écritures), mais **`insert_relation` legacy, `relation_by_id` et Q1–Q8 ne sont pas encore unifiés**. C1/C2 ne sont pas complètement fermés.

**Correction partielle** : `insert_relation_record` valide le catalogue, crée les nœuds et écrit la provenance. **Reste** : supprimer/déprécier le chemin legacy, unifier le vocabulaire `kind`, faire lire Q1–Q8 sur le store, et générer les snapshots depuis le store (pas depuis les fixtures).

---

## 2. Ce que j'ai changé dans le code

- Schéma v3 dans `src/orvyren/graph/store.py` : `nodes`, `node_aliases`, `events`, `event_observations`, `relation_provenance`, `source_families`, `ingestion_watermarks`, `graph_snapshots`.
- `relations` : 17 champs + `chain_id`, bloc, tx, log, finalité, confiance, payload ; migration additive.
- `insert_relation_record` : validation catalogue, nœuds manquants, provenance.
- `snapshot_v2`, `graph_counts`, `set_watermark`, `record_graph_snapshot`.
- Index `(src, kind)` / `(dst, kind)` retirés ; commentaire de mise en garde.
- Tests : `tests/test_graph_store_v2.py` (12 cas) ; suite complète **856 passed, 3 skipped, 261 subtests** (pytest) et **859 OK (skipped=3)** (unittest) avant la dernière correction d'index ; `verify_frozen.py` COMPLIANT.

**Ce que le code ne fait pas encore** : ingestion Aave, Q1–Q8 SQL, outils agent, UI, EVAL.

---

## 3. Ce qui reste, par ordre

### P0 — débloquer le graphe (avant toute UI/démo)

1. **C1 — un seul vocabulaire `kind`** : uppercase, validé contre `RELATION_CATALOG` à l'écriture ; déprécier `models.Relation` ou le convertir explicitement.
2. **C2 — pont complet** : `GraphStore.insert_relation` accepte un `RelationRecord` (ou est remplacé) ; `relation_by_id` retourne le record 17 champs ; Q1–Q8 lisent le store live ; snapshots générés depuis le store, pas des fixtures.
3. **Ingestion Aave v3 Base** : un marché, 30 jours, bloc finalisé, 10 000+ événements, manifest, watermark, preuve PIT.
4. **Benchmark réel** : Q1/Q2/Q7/Q8 sur le graphe Aave, p50/p95, parité fixture ↔ SQL.

### P1 — produit et agents

5. `graph_query` / `graph_path` / `graph_snapshot` comme outils typés.
6. Mémoire working/episodic/semantic et boucle agent.
7. Écran d'enquête unique ; démo 5 min ; policy/execution existantes.
8. Évaluation honnête : N petit, pas de revendication EVAL.

### P2 — recherche restante

9. `30_data` : sources, résolution, extraction documentaire.
10. `20_agents` : tool calling provider-agnostique, runtime, mémoire.
11. `40_product` : persona, JTBD, UI.
12. `50_competition` : barème, démo, risques.
13. `60_synthesis` : synthèse finale après tous les rapports.

**Chemin critique** : C1/C2 (≈12 h) → ingestion (12–24 h) → Q1/Q4/Q6/Q7/Q8 SQL (8–12 h) → UI/démo (8–12 h). Le reste est parallèle ou post-20/10.

---

## 4. Recommandation

- **Ne pas dire que la recherche est finie.**
- **Ne pas commencer la vidéo, le deck ou les 12 écrans** avant C1/C2 + ingestion ; sinon on refait un prototype.
- **Un seul slice** : Aave v3 Base, un marché, un portefeuille, un bloc, 8–10 relations, 10 000+ événements. Le graphe doit être **visible et requêtable**, pas seulement stocké.
- **Corriger d'abord le pont** : tant que Q1–Q8 ne lisent pas ce que le store écrit, le schéma le mieux conçu restera vide.

---

## 5. Sources

- Contradiction Codex : `10_graph/10_graph__contradiction-72h-scope__codex__2026-10-17.md`.
- Contradiction MiniMax : `10_graph/10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`.
- Schéma MiniMax : `10_graph__schema-cible__minimax-code__2026-10-17.md`.
- Rapports Hermes : `10_graph__audit-34-relations__hermes…`, `10_graph__schema-cible__hermes…`, `60_synthesis__graph-first-architecture__hermes…`.
- Code : `src/orvyren/graph/store.py`, `tests/test_graph_store_v2.py`.
- PostgreSQL : doc courante, `WITHOUT OVERLAPS` PG 19, commits SQL/PGQ rollback (voir rapport schéma §14).
