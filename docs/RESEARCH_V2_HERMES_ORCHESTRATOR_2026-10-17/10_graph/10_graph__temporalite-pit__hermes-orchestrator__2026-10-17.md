# 10_graph — Temporalité, PIT, provenance et révision

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `10_graph`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : les six horloges, le bitemporel, l'état PIT, les blocs/finalité/reorg, la provenance, les contradictions et la révision. Le DDL est dans `10_graph__schema-cible__hermes__2026-10-17.md` ; ici, les règles et les tests.
**Fichiers lus** : `src/orvyren/graph/temporal.py`, `record.py`, `store.py`, `queries.py`, `evidence/graph.sqlite`, `B2_GRAPHE_ETUDE.md` §1, §4.3–4.5, `MIMIR_Technical_Design.md` §10.5, §8.3, §11.2–11.4, `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`.

---

## 0. Verdict

Le dépôt a un **bon socle** (`valid_from/valid_to`, `inserted_at`, `revision`, `pit_at`), et le schéma v3 ajoute les champs on-chain et la provenance. Mais :

- aucune **finalité/reorg** n'est traitée dans le store ;
- le graphe live n'a que 520 observations et 4 supports, sans entités/événements ;
- les Q1–Q8 ne tournent pas sur le store ;
- **PostgreSQL ne fournit pas le system time** : `WITHOUT OVERLAPS` (PG 19) garantit l'intervalle de validité, pas l'historique de connaissance ; le bitemporel reste applicatif.
- **SQL/PGQ n'existe pas** dans une version livrable (patch reverté) : le PIT doit être en SQL standard + `WITH RECURSIVE`.

**Décision** : PIT **bitemporel applicatif** sur SQLite pour la démo, avec un bloc finalisé et un snapshot ; PostgreSQL plus tard pour `WITHOUT OVERLAPS`, pas pour SQL/PGQ. Ne jamais revendiquer un live reorg-safe avant un test de reorg.

---

## 1. Les six horloges

| Horloge | Champ | Question |
|---|---|---|
| event time | `event_time` / `valid_from` | Quand le fait s'est produit |
| publication time | `publication_time` | Quand il est devenu public |
| observation time | `observation_time` / `retrieved_at` | Quand le système l'a vu |
| effective time | `effective_time` | Quand l'effet s'applique |
| validity | `valid_from` / `valid_to` | Quand le fait est vrai |
| revision | `inserted_at` / `revision` | Quand la connaissance a changé |

**Règle** : une décision utilise l'intersection **monde à T** ∩ **connu à T**. Un fait peut exister dans le monde avant d'être connaissable ; il ne doit pas entrer dans une décision antérieure.

---

## 2. Bitemporel : deux axes, pas un

| Axe | Question | Filtre |
|---|---|---|
| **Valid time** (monde) | Le fait est-il vrai à T ? | `valid_from <= T < valid_to` (ou `valid_to IS NULL`) |
| **Transaction time** (connaissance) | Le système connaissait-il ce fait à T ? | `inserted_at <= T`, révision maximale par `relation_id` |

```sql
WITH known AS (
    SELECT relation_id, MAX(revision) AS rev
    FROM relations
    WHERE inserted_at <= :as_of
    GROUP BY relation_id
)
SELECT r.*
FROM relations r
JOIN known k ON k.relation_id = r.relation_id AND k.rev = r.revision
WHERE r.valid_from <= :as_of
  AND (r.valid_to IS NULL OR :as_of < r.valid_to);
```

**On-chain** : le bloc est le temps primaire. `block_number <= B` et `valid_from_block <= B < valid_to_block` ; le timestamp n'est qu'un affichage. Le bloc doit être **finalisé** ou explicitement marqué `PENDING`.

---

## 3. Finalité et reorg

### 3.1 Règles

- Utiliser le tag `finalized` quand le RPC le fournit ; sinon une profondeur de confirmation configurable (ex. 64 blocs) et `finality=PENDING`.
- Un fait orphelin n'est **jamais supprimé** : il est marqué `REORGED`/`ORPHANED` et `superseded_by` pointe vers la réobservation.
- Le watermark d'ingestion est lié à `(source_id, last_block, last_block_hash)` ; un reorg réinitialise le curseur au dernier bloc commun.
- Une décision passée n'est jamais réécrite : elle référence un snapshot et le bloc utilisés.

### 3.2 Ce qu'on peut revendiquer en 72 h

- **Snapshot à un bloc finalisé** : oui.
- **Live reorg-safe** : non, sauf test de reorg et politique de confirmation.
- **Replay offline** : oui, avec le snapshot et les manifests.

**Libellés obligatoires** : `LIVE`, `REPLAY`, `SYNTHETIC`, `SANDBOX` ; afficher le bloc/hash et l'heure de lecture.

---

## 4. Provenance et contradictions

### 4.1 Chaîne

`Source → Observation → Event → Claim/Relation → Hypothesis → Decision → Execution → Outcome`

Chaque flèche est une ligne (`relation_provenance`, `event_observations`, `OBSERVED_FROM`, `EXTRACTED_FROM`, `DERIVED_FROM`), pas du texte libre.

### 4.2 Indépendance

`source_family_id` est la clé : deux sources du même famille ne comptent pas comme deux preuves. Une observation reçue deux fois est une **révision**, pas un doublon.

### 4.3 Contradictions

- `CONTRADICTS` conserve les deux claims, avec sources et intervalles.
- Une contradiction non résolue est un **signal de recherche**, pas une erreur à masquer.
- `SUPPORTS`/`REFUTES` ne se propagent jamais comme causalité ; `CORRELATES_WITH` est statistique et non chaînable.
- Une relation `REJECTED` reste dans l'historique ; sa réactivation est une décision datée.

---

## 5. Révision

`DISCOVERED → EVALUATING → ACTIVE → WEAKENING → SUSPENDED → REJECTED`, avec `REACTIVATION CANDIDATE`.

- Une révision insère une nouvelle ligne (`revision+1`), ne met jamais à jour l'ancienne.
- `superseded_by` pointe vers la nouvelle révision.
- Niveau L1–L2 (confiance/paramètre) peuvent être automatiques ; L3+ (création/suppression de relation) exigent une décision tracée.
- Un snapshot de décision référence une version de graphe ; il ne la copie pas.

---

## 6. Tests PIT

1. Un fait inséré après T n'apparaît pas dans `pit_at(T)`.
2. Un fait valide dans le monde mais non connu à T n'apparaît pas.
3. Un fait `valid_to < T` n'apparaît pas.
4. Une révision 2 remplace la 1 dans la vue courante, mais la 1 reste dans l'historique.
5. Un fait `REORGED` n'est plus retourné par `world_at`.
6. Deux rebuilds du même snapshot donnent le même hash.
7. Q1/Q4/Q6/Q7/Q8 sur fixtures = Q1/Q4/Q6/Q7/Q8 sur SQL.
8. Un claim sans observation est refusé ; une relation sans source est refusée.

---

## 7. Plan 72 h

- **Un bloc finalisé** Aave v3 Base + un snapshot ; pas de live reorg-safe revendiqué.
- Ajouter `valid_from_block`, `valid_to_block`, `finality`, `block_hash` (déjà dans le schéma v3).
- Ingestion : `finalized` ou profondeur 64 ; watermark ; `REORGED` append-only.
- Q4 PIT sur le snapshot ; Q6 provenance ; tests 1–6.
- **Pas** de PostgreSQL/SQL/PGQ pour la démo ; SQLite `WITH RECURSIVE`.
- **Pas** de prétention « live » si le test de reorg n'est pas fait.

---

## 8. Risques

| Risque | Mitigation |
|---|---|
| Confondre `inserted_at` et `event_time` | Tests PIT ; deux filtres |
| Bloc non finalisé | tag `finalized` ou `PENDING` explicite |
| Reorg silencieux | `REORGED` + watermark + replay |
| PostgreSQL system time inexistant | bitemporel applicatif ; `WITHOUT OVERLAPS` seulement pour la validité |
| SQL/PGQ absent | `WITH RECURSIVE` |
| Snapshot non hashé | `graph_snapshots` + hash |
| Contradiction masquée | `CONTRADICTS` conservé |

---

## 9. Sources

- `src/orvyren/graph/temporal.py` (as-of, PIT).
- `src/orvyren/graph/record.py:86–135` (validité, révision).
- `src/orvyren/graph/store.py:58–258` (colonnes, tables), `:333–386` (migration).
- `src/orvyren/graph/queries.py` Q4/Q6.
- `B2_GRAPHE_ETUDE.md` §1, §4.3–4.5, §6.1.
- `MIMIR_Technical_Design.md` §10.5, §8.3, §11.2–11.4.
- `Project_2_DFKG_Research_State_0_a11y.docx` §10–11, §16.
- PostgreSQL 19 temporal tables — https://www.postgresql.org/docs/19/ddl-temporal-tables.html — consulté 2026-10-17.
- PostgreSQL commit SQL/PGQ rollback — https://git.postgresql.org/pg/commitdiff/2b9e1aff4d3d933ae8ee377fef22c2af9c7797e8 — consulté 2026-10-17.
- SQLite `WITH RECURSIVE` — https://sqlite.org/lang_with.html — consulté 2026-10-17.
- Contradiction MiniMax : `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`.
