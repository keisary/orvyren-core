# 60_synthesis — Architecture v2 et conclusion de la campagne

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `60_synthesis`.
**Statut** : INTERNE — synthèse de campagne, ne pas soumettre.
**Périmètre** : conclusion des recherches, architecture cible, plan 72 h, claims autorisés, reste à faire.
**Rapports intégrés** : tous les rapports `10_graph`, `30_data`, `20_agents`, `40_product`, `50_competition` du dossier de campagne, ainsi que Codex (scope), MiniMax (SQL/PGQ, index, deux représentations), Mimo (audit 34 relations), et les snapshots `docs/RESEARCH_V2_*`.

---

## 0. Conclusion

**ORVYREN v2 est un système graph-first de gestion du risque de trésorerie on-chain, pas un prototype mono-cas.**

- Le **graphe** est l'innovation : temporel, provenance-aware, épistémiquement explicite, orienté décision.
- Les **agents** sont nécessaires mais génériques : un orchestrateur, un chercheur, un critique ; des outils callables ; une mémoire.
- La **sécurité** est la couche de confiance : policy hors LLM, signature isolée, reçu, audit.
- Le **produit** est un espace d'enquête unique, pas 12 écrans d'audit.

**Slice 72 h** : Aave v3 Base, un marché, 30 jours, bloc finalisé, **10 000+ événements**, **8–10 relations**, SQLite. **Pas** de 16–18 relations, **pas** de 10⁵ promis, **pas** de SQL/PGQ, **pas** de base graphe, **pas** de swarm.

**Chemin critique** : C1/C2 (pont relation + Q1–Q8 sur le store) → ingestion Aave → Q1/Q4/Q6/Q7/Q8 SQL → écran d'enquête → démo/preuve. Le reste est parallèle ou post-20/10.

---

## 1. Couverture de la recherche

| Chantier | Rapport | Statut |
|---|---|---|
| Audit 34 relations | `10_graph__audit-34-relations__hermes` + Mimo + Codex | Fait, portée 8–10 |
| Schéma cible | `10_graph__schema-cible__hermes` + MiniMax | Fait, révisé |
| Entités/événements | `10_graph__entites-evenements__hermes-orchestrator` | Fait |
| Temporalité/PIT | `10_graph__temporalite-pit__hermes-orchestrator` | Fait |
| Requêtes/propagation | `10_graph__requetes-propagation__hermes-orchestrator` | Fait |
| Benchmark | `10_graph__benchmark__hermes-orchestrator` | Fait, synthétique |
| Sources/ingestion | `30_data__sources-ingestion__hermes-orchestrator` | Fait |
| Résolution/extraction | `30_data__resolution-extraction__hermes-orchestrator` | Fait |
| Tool calling | `20_agents__tool-calling__hermes-orchestrator` | Fait |
| Runtime/mémoire | `20_agents__runtime-memoire__hermes-orchestrator` | Fait |
| Évaluation agent | `20_agents__evaluation__hermes-orchestrator` | Fait |
| Persona/UI | `40_product__persona-ui__hermes-orchestrator` | Fait |
| Concurrence | `50_competition__positionnement__hermes-orchestrator` | Fait |
| Synthèse | ce rapport | Fait |

**Ce que la campagne ne fournit pas** : ingestion exécutée, Q1–Q8 SQL sur Aave, UI, démo, EVAL. Ce sont des **travaux d'implémentation**, pas des rapports.

---

## 2. Décisions d'architecture

### 2.1 Stockage

- **SQLite** pour la démo et le replay offline.
- **PostgreSQL** cible 2–4 semaines pour les contraintes temporelles (`WITHOUT OVERLAPS`, PG 19) et la concurrence.
- **Pas de SQL/PGQ** : patch reverté, aucune version livrable.
- **Pas de Neo4j/Kuzu/DuckPGQ** au concours : 10⁵ tient en ~32 Mo et 0,22 s sur SQLite.
- **DuckDB/Parquet** : analytique, pas journal transactionnel.

### 2.2 Graphe

- **Record 17 champs** persisté + champs on-chain.
- **`nodes`, `events`, `event_observations`, `relation_provenance`, `source_families`, `ingestion_watermarks`, `graph_snapshots`**.
- **EVENT** de première classe ; `IMPLEMENTED_BY` et `WRAPS` à ajouter (P1) ; `ROLE_OF`/`LIQUIDATED_IN` en veille.
- **8–10 relations** pour le slice : `DEPLOYED_ON`, `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `PRICED_BY`, `CONSTRAINS`, `OBSERVED_FROM`, `DERIVED_FROM`, `SUPPORTS`, `CONTRADICTS`.
- **Q1/Q4/Q6/Q7/Q8** en SQL ; Q2/Q3/Q10 si le temps ; Q9/Q11–Q14 roadmap.

### 2.3 Données

- Aave v3 Base, un marché, 30 jours, bloc finalisé, 10k+ événements.
- Source manifest, raw store hashé, watermark, reorg `REORGED`, idempotence.
- Résolution déterministe `chain:address` ; alias = preuve ; événements `(chain, tx, log)`.
- 2–3 documents max ; extraction LLM hors chemin décisionnel.

### 2.4 Agents

- Orchestrateur + chercheur + critique ; pas de swarm.
- Outils : `graph_query`, `chain_logs`, `price_history`, `fetch_document` ; action séparée.
- Tool calling natif quand disponible ; fallback JSON strict.
- Mémoire working + episodic + semantic ; PIT-safe ; pas de chat log.
- Budget 8 itérations / 12 appels ; trace ; checkpoint.

### 2.5 Produit

- Persona : opérateur de trésorerie on-chain.
- Un espace d'enquête : exposition, hypothèses, graphe, preuves, recherche, décision, policy, reçu.
- Démo 5 min ; graphe visible dans les 30 premières secondes.
- Pas de 12 écrans.

### 2.6 Concurrence

- Barème 40/30/30 + bonus.
- Graph-first, security as trust layer, honest claims.
- Claims autorisés : 34 types définis ; policy hors LLM ; preuve on-chain.
- Claims interdits : 16–18 relations live, 10⁵ événements, SQL/PGQ, multi-agent complet, EVAL concluante, zéro clé.

---

## 3. Contradictions intégrées

| Contradiction | Décision |
|---|---|
| SQL/PGQ (MiniMax) | Retiré ; `WITHOUT OVERLAPS` + `WITH RECURSIVE` |
| Index `(src,kind)` (MiniMax) | Retiré ; `edge_current` après mesure |
| Benchmark v2 dégénéré (MiniMax) | v4 : 0,055 s/50k, 0,220 s/100k ; seuils resserrés |
| Scope 16–18 / 10⁵ (Codex) | 8–10 relations, 10k+ événements, bloc fixe |
| Deux représentations (MiniMax) | C1/C2 en chemin critique, pas encore fermés |
| Mimo : 34 types garder + `IMPLEMENTED_BY`/`WRAPS` | Oui, catalogue gardé ; 8–10 peuplés |
| Mimo : deux writers | C1 : un seul writer validant ; legacy déprécié |

---

## 4. Plan 72 h

### 4.1 J1 — C1/C2 + ingestion

- **C1** : vocabulaire `kind` unique (majuscules), validation catalogue à l'écriture.
- **C2** : `GraphStore.insert_relation` accepte/valide `RelationRecord` ; `relation_by_id` retourne le record ; Q1–Q8 lisent le store ; snapshots depuis le store.
- Ingestion Aave v3 Base, 30 jours, bloc finalisé, 10k+ événements.
- Raw store + manifest + watermark.

### 4.2 J2 — relations + SQL + agent

- 8–10 relations, `chain_ref` partout, provenance.
- Q1/Q4/Q6/Q7/Q8 en SQL ; parité fixture ↔ SQL.
- Outils `graph_query`, `graph_path`, `graph_snapshot`.
- Écran d'enquête (un seul).

### 4.3 J3 — preuve + démo

- Benchmark Aave réel : p50/p95, counts, limites.
- Démo 5 min ; policy/execution ; reçu ; snapshot.
- Doc technique EN + rapport sécurité + README ; vidéo seulement si stable.

### 4.4 Critères d'acceptation

- 10k+ événements, 2k+ nœuds, 8k+ relations, 8–10 kinds.
- Q1 50k < 0,25 s ; 100k < 0,5 s (v4).
- 100 % provenance sur la décision.
- PIT : 0 fuite du futur.
- 0 action hors policy.
- Mode LIVE/REPLAY/SYNTHETIC explicite.

---

## 5. Ce qui est déjà fait

- Schéma v3 mergé sur `master` (`bc8dc73`) : tables monde, 17 champs, provenance, watermark, snapshots.
- 856 tests pytest / 859 unittest, 3 sautés ; `verify_frozen` COMPLIANT.
- Rapports de recherche complets (ce dossier) + contradictions + réconciliation.
- Benchmark synthétique et seuils v4.

## 6. Ce qui reste

1. C1/C2 (12 h).
2. Ingestion Aave (12–24 h).
3. Q1–Q8 SQL + parité (8–12 h).
4. Outils agent + mémoire (8–12 h).
5. Écran d'enquête (8–12 h).
6. Démo + doc + sécurité (8–12 h).
7. EVAL : N=0, à ne pas revendiquer.

---

## 7. Risques

| Risque | Mitigation |
|---|---|
| Refaire un prototype | C1/C2 + ingestion avant UI |
| Graphe vide | counts avant démo |
| Données fixtures présentées live | mode explicite |
| SQL/PGQ | retiré |
| Index nuisible | edge_current |
| Scope | 8–10 relations, 10k events |
| Sécurité déclarative | corriger `SECURITY_SELF_ASSESSMENT.md:11` |
| EVAL N=0 | pas de claim |

---

## 8. Recommandation finale

**Construire le slice, pas le catalogue.** Le graphe doit être **peuplé, requêtable et visible**. Les agents doivent **chercher** avec des outils réels. La policy doit rester **hors LLM**. Le produit doit être **un écran d'enquête**. Et les claims doivent être **plus petits que ce qui est mesuré**.

Si l'équipe ne peut pas faire C1/C2 + ingestion avant la deadline, la soumission doit être **honnête** : « couche de confiance et de preuve pour agent wallet », pas « système multi-agent complet ». Mais l'objectif reste le slice graph-first.

---

## 9. Sources

- Tous les rapports du dossier `D:/orvyren_research_v2_2026-10-17/` (INDEX).
- `docs/RESEARCH_V2_*` sur `master`.
- Code `src/orvyren/graph/store.py`, `tests/test_graph_store_v2.py`.
- `B2_GRAPHE_ETUDE.md`, MIMIR §10–11, DFKG Research State §3–18.
- Contradictions Codex/MiniMax, audit Mimo.
