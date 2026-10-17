# 10_graph — Benchmark et évaluation du graphe

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `10_graph`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : protocole de benchmark, mesures disponibles, limites, benchmark Aave réel, critères d'acceptation. Les rapports `schema-cible` et les contradictions MiniMax/Codex sont lus.
**Fichiers lus** : `10_graph/_bench/bench_graph_scale.py`, `bench_results_guarded.json`, `bench_tuned_results.json`, `bench_index_results.json`, `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`, `10_graph__contradiction-72h-scope__codex__2026-10-17.md`.

---

## 0. Verdict

Le benchmark disponible est **synthétique**, pas Aave. Il prouve une chose : **matérialiser le graphe en SQL est indispensable** ; Q1 en Python scanne et s'effondre, Q1 en SQLite reste sous la seconde. Il ne prouve **pas** que 10⁴–10⁵ événements réels sont ingérables en 72 h, ni que la sémantique des arêtes est correcte.

**Décision** : utiliser le benchmark v4 MiniMax comme référence de performance, le benchmark v2 Hermes comme plancher conservateur, et exécuter un **benchmark Aave réel** avant toute revendication. Ne pas appeler « validation » un smoke test.

---

## 1. Ce qui a été mesuré

### 1.1 Générateur v2 Hermes (50k)

| Relations | Nœuds | Validation | Q1 Python | Q1 SQLite | Q2 SQLite | Fichier |
|---:|---:|---:|---:|---:|---:|---:|
| 1 000 | 179 | 4,96 ms | 4,51 ms | 17,69 ms | 0,31 ms | 356 Ko |
| 10 000 | 449 | 49,60 ms | 641,85 ms | 186,75 ms | 2,04 ms | 3,12 Mo |
| 50 000 | 1 649 | 277,16 ms | 20 703,95 ms | 979,04 ms | 31,21 ms | 15,66 Mo |

**Limite** : générateur dégénéré (`q2_paths=1`, ~60 arêtes/nœud) ; le Q2 Python n'est pas représentatif. C'est un **plancher**.

### 1.2 Générateur v4 MiniMax (référence)

| Arêtes | Nœuds | Q1 Python | Q1 SQLite réglé | Écart | Taille |
|---:|---:|---:|---:|---:|---:|
| 50 000 | — | 18,75 s | **0,055 s** | ×338 | — |
| 100 000 | 15 845 | 75,31 s | **0,220 s** | ×342 | 31,68 Mo |

**Index `(src,kind)`** : 6,2687 s à 50k (×117) ; 30,68 s à 100k (×139). **Ne pas le créer.**

### 1.3 Ce que cela prouve

- SQL ≫ Python pour les requêtes de traversée.
- SQLite suffit à 10⁵ arêtes avec ~32 Mo.
- Un index manuel sur `src` peut être **pire** que pas d'index ; la stratégie `edge_current` est la bonne.
- Le stockage n'est pas le goulet ; **le pont entre les deux représentations de relation** l'est.

### 1.4 Ce que cela ne prouve pas

- Débit d'ingestion RPC réel.
- Sémantique des arêtes, provenance, PIT, reorg.
- Q1–Q14 sur le store live.
- Gain de décision vs un agent sans graphe.
- 10⁴–10⁵ événements Aave en 72 h (Codex).

---

## 2. Protocole du benchmark Aave réel

### 2.1 Données

- Base mainnet, `chain_id = 8453`, Aave v3.
- 30 jours, un marché, un bloc finalisé.
- 10 000+ événements décodés (Pool, Oracle, tokens, proxy).
- Un portefeuille de démonstration avec positions Aave.

### 2.2 Mesures

| Mesure | Méthode | Cible |
|---|---|---|
| Ingestion | events/s, octets/s, erreurs | 10k en < 10 min |
| Q1 exposition | p50/p95, 5 répétitions | < 0,25 s à 50k |
| Q2 chemins | p50/p95, nombre de chemins | < 0,1 s |
| Q4 PIT | p50/p95, exactitude | < 0,1 s |
| Q6 provenance | couverture | 100 % |
| Q7 concentration | p50/p95, HHI | < 0,1 s |
| Q8 permissions | p50/p95, as-of | < 0,1 s |
| Taille DB | fichier, index | < 50 Mo à 10k |
| Parité | fixture ↔ SQL | 100 % |

### 2.3 Protocole

1. Figer le bloc, le hash, l'address book et l'ABI.
2. Ingérer dans une base vide ; mesurer le débit.
3. Rejouer le même batch : zéro doublon.
4. Exécuter Q1/Q4/Q6/Q7/Q8 5 fois ; p50/p95.
5. Comparer fixture ↔ SQL.
6. Tester un fait inséré après T (PIT).
7. Publier les limites et les chiffres bruts.

---

## 3. Critères d'acceptation

- **50 000 relations** : Q1 < 0,25 s ; Q2 < 0,1 s ; Q7/Q8 < 0,1 s.
- **100 000 relations** : Q1 < 0,5 s ; Q4/Q7/Q8 < 0,5 s.
- **Provenance** : 100 % des claims de la décision ont une chaîne complète.
- **PIT** : 0 fuite du futur dans le test.
- **Ingestion** : 10k événements en < 10 min ; rejeu idempotent.
- **Honnêteté** : si un chiffre n'est pas mesuré, il n'est pas dans le rapport.

---

## 4. Plan 72 h

- J1 : ingestion Aave 30 jours, 10k events ; compter.
- J2 : Q1/Q4/Q6/Q7/Q8 SQL ; 5 répétitions.
- J3 : benchmark final, p50/p95, limites, snapshot.
- **Pas** de PostgreSQL, pas de SQL/PGQ, pas de graph DB.
- **Pas** de GNN/GraphRAG.
- **Pas** de revendication de 10⁵ si 10k seulement.

---

## 5. Risques

| Risque | Mitigation |
|---|---|
| RPC rate-limited | provider archive free, cache, 30 jours |
| Générateur synthétique trompeur | benchmark Aave réel |
| Index nuisible | edge_current, pas `(src,kind)` |
| Mesure unique | 5 répétitions, p50/p95 |
| Parité non testée | fixture ↔ SQL |
| Scope 10⁵ | 10k d'abord, 50k si mesuré |
| Confusion « smoke test » / « validation » | libellés explicites |

---

## 6. Sources

- `_bench/bench_graph_scale.py` ; `bench_results_guarded.json`.
- `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md` (v4, index).
- `10_graph__contradiction-72h-scope__codex__2026-10-17.md` (scope).
- `10_graph__schema-cible__hermes__2026-10-17.md` §10.
- SQLite `EXPLAIN QUERY PLAN` — https://sqlite.org/eqp.html — consulté 2026-10-17.
- Aave `IPool.sol` — https://github.com/aave/aave-v3-core/blob/master/contracts/interfaces/IPool.sol — consulté 2026-10-17.
- Base docs — https://docs.base.org/ — consulté 2026-10-17.
