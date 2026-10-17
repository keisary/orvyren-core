# 10_graph — Requêtes de décision et propagation

**Auteur / agent** : Hermes-orchestrateur (deepseek-flash, session recherche V2).
**Date** : 2026-10-17.
**Chantier** : `10_graph`.
**Statut** : INTERNE — recherche V2, ne pas soumettre.
**Périmètre** : Q1–Q14, SQL, chemins autorisés/interdits, propagation, index, tests de parité. Le DDL est dans `10_graph__schema-cible__hermes__2026-10-17.md`.
**Fichiers lus** : `src/orvyren/graph/queries.py`, `catalog.py`, `record.py`, `store.py`, `B2_GRAPHE_ETUDE.md` §6–7, `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md`, `10_graph__contradiction-72h-scope__codex__2026-10-17.md`.

---

## 0. Verdict

Les Q1–Q8 existent, mais **sur des `RelationRecord` Python en mémoire**, pas sur le graphe SQL. Q9–Q14 sont spécifiées dans B2 mais non exposées. Aucune des 14 requêtes n'est exécutable sur `evidence/graph.sqlite` dans son état actuel.

**Décision** : pour le slice 72 h, écrire **Q1, Q4, Q6, Q7, Q8** en SQL sur le store v3, avec test de parité fixture ↔ SQL ; Q2/Q3/Q10 si le temps ; Q9/Q11–Q14 en roadmap. **Pas de SQL/PGQ** ; `WITH RECURSIVE`, profondeur bornée, pas d'index manuel `(src, kind)`.

---

## 1. Les requêtes qui justifient le graphe

| # | Question | Relations | Priorité |
|---|---|---|---|
| Q1 | Exposition consolidée de la trésorerie (directe + indirecte) | `HOLDS`, `DEPOSITED_IN`, `COLLATERALIZES`, `OWES` | **P0** |
| Q2 | Chemins de dépendance d'un actif (canal, signe, profondeur) | `DEPENDS_ON`, `AFFECTS` | P1 |
| Q3 | Contradictions ouvertes | `CONTRADICTS` | P1 |
| Q4 | État PIT (monde ∩ connaissance) | toutes + `valid_from/to`, `inserted_at/revision`, block | **P0** |
| Q5 | Chronologie d'un épisode | `events`, `event_observations` | P1 (après events) |
| Q6 | Provenance décision → source | `OBSERVED_FROM`, `EXTRACTED_FROM`, `DERIVED_FROM` | **P0** |
| Q7 | Concentration (dette/collatéral, HHI) | `OWES`, `COLLATERALIZES`, `CONSTRAINS` | **P0** |
| Q8 | Permissions as-of bloc | `MEMBER_OF`, `ALLOWS`, `REVOKES`, `ADMINISTERED_BY` | **P0** (si Safe) |
| Q9 | Fraîcheur oracle/observations | `PRICED_BY`, observations | P1 |
| Q10 | Faits manquants discriminants | anti-join par type | P1 |
| Q11 | Invariants inter-chaînes | `DEPLOYED_ON`, `BRIDGED_VIA` | P2 |
| Q12 | Chaîne de contrôle | `ADMINISTERED_BY`, `GOVERNED_BY`, `IMPLEMENTED_BY` | P2 |
| Q13 | Révision/invalidation | `SUPERSEDES`, `valid_to` | P1 |
| Q14 | Recherche sémantique | pgvector (option) | P2 |

---

## 2. SQL Q1 — exposition

```sql
WITH RECURSIVE direct(asset) AS (
    SELECT DISTINCT dst
    FROM relations
    WHERE src = :holder AND kind = 'HOLDS'
      AND lifecycle = 'ACTIVE' AND validation_status = 'VALIDATED'
      AND valid_from <= :as_of AND (valid_to IS NULL OR :as_of < valid_to)
),
walk(asset, protocol, kind, depth, trail) AS (
    SELECT asset, NULL, NULL, 0, '/' || asset || '/'
    FROM direct
    UNION
    SELECT w.asset, r.dst, r.kind, w.depth + 1, w.trail || r.dst || '/'
    FROM walk w
    JOIN relations r ON r.src = w.asset
    WHERE w.depth < 3
      AND r.kind IN ('DEPOSITED_IN','COLLATERALIZES','REHYPOTHECATED_TO')
      AND r.lifecycle = 'ACTIVE' AND r.validation_status = 'VALIDATED'
      AND r.valid_from <= :as_of AND (r.valid_to IS NULL OR :as_of < r.valid_to)
      AND instr(w.trail, '/' || r.dst || '/') = 0
)
SELECT * FROM walk;
```

**Invariants** : `HOLDS` n'est jamais transitif ; profondeur ≤ 3 ; cycles via `trail`. PostgreSQL : `strpos` au lieu de `instr`.

---

## 3. SQL Q2 — dépendances

```sql
WITH RECURSIVE walk(node, path, depth) AS (
    SELECT src, '|' || src || '|' || dst || '|', 1
    FROM relations
    WHERE kind IN ('DEPENDS_ON','AFFECTS') AND dst = :asset
      AND lifecycle = 'ACTIVE' AND validation_status = 'VALIDATED'
    UNION ALL
    SELECT r.src, w.path || r.src || '|', w.depth + 1
    FROM walk w
    JOIN relations r ON r.dst = w.node
    WHERE r.kind IN ('DEPENDS_ON','AFFECTS')
      AND w.depth < 3
      AND instr(w.path, '|' || r.src || '|') = 0
)
SELECT * FROM walk;
```

**Interdits** : `SUPPORTS`, `REFUTES`, `CONTRADICTS`, `CORRELATES_WITH` ne se propagent jamais ; `CORRELATES_WITH` n'est pas causal ; `AFFECTS` ne se propage que via le moteur de propagation déclaré.

---

## 4. SQL Q8 — permissions

```sql
SELECT r.*
FROM relations r
WHERE r.kind IN ('MEMBER_OF','ALLOWS','REVOKES')
  AND r.chain_id = :chain
  AND r.block_number <= :block
  AND (r.valid_to_block IS NULL OR :block < r.valid_to_block)
  AND r.lifecycle = 'ACTIVE'
  AND r.validation_status = 'VALIDATED';
```

Une révocation ferme `valid_to_block` du droit ; elle ne supprime pas la ligne.

---

## 5. Propagation

**Autorisé** : clôture `PART_OF`/`IS_A` ; `DEPENDS_ON` borné avec décroissance ; `AFFECTS` via mécanismes nommés, conditions, horizons, feedback temporel.

**Interdit** : propager `SUPPORTS`/`CONTRADICTS` ; chaîner `CORRELATES_WITH` ; inverser `AFFECTS` sans déclaration ; fermer `HOLDS`.

**Règle** : une propagation doit citer les `relation_id` utilisés, leur statut épistémique, le signe, l'horizon et la provenance. Sans cela, c'est une opinion, pas une preuve.

---

## 6. Index et performance

- **Ne pas créer** `(src, kind)` / `(dst, kind)` sur l'append-only : MiniMax mesure ×117–139 de ralentissement (l'index manuel défait l'index automatique `(lifecycle, src)`).
- Cible : table **`edge_current`** matérialisée (dernières révisions non superseded), indexée sur `(src, kind)` seulement après mesure.
- Index utiles : `(relation_id, inserted_at)` pour le PIT, `(valid_from, valid_to)`, `(kind, lifecycle, validation_status)`, `(chain_id, block_number)`.
- Requêtes : profondeur ≤ 3, `LIMIT`, `EXPLAIN ANALYZE` ; pas de scan complet.

---

## 7. Tests de parité

1. Mêmes fixtures, `queries.py` vs SQL → même ensemble de relations.
2. Q1 : direct/indirect identiques ; pas de HOLDS transitif.
3. Q2 : chemins identiques ; pas de kind interdit.
4. Q4 : fait après T absent ; fait `valid_to < T` absent.
5. Q6 : chaque claim a une source ; aucun orphelin.
6. Q7 : HHI identique.
7. Q8 : révocation as-of bloc correcte.
8. Q1 50k < 0,25 s ; 100k < 0,5 s (générateur v4 MiniMax) — pas 1–2 s.

---

## 8. Plan 72 h

- Q1/Q4/Q6/Q7/Q8 en SQL sur store v3.
- Q3/Q10 si les données le permettent ; Q2 en lecture simple.
- Q5 après events ; Q9 après oracle ingest.
- Q11–Q14 : roadmap, pas de promesse.
- **Pas de SQL/PGQ**, **pas d'index `(src,kind)`**, **pas de base graphe**.

---

## 9. Risques

| Risque | Mitigation |
|---|---|
| Requête Q1 sur un graphe vide | vérifier les counts avant de conclure |
| Q2 propage une corrélation | invariant interdit + test |
| Index manuel | edge_current, pas d'index sur l'append-only |
| Q8 faux as-of | bloc + valid_to_block + test |
| Parité non testée | fixture ↔ SQL obligatoire |
| Scope 14 requêtes | Q1/Q4/Q6/Q7/Q8 seulement |

---

## 10. Sources

- `src/orvyren/graph/queries.py:10–27` (Q1–Q8), `:89–351`.
- `src/orvyren/graph/catalog.py` (34 kinds, familles).
- `src/orvyren/graph/store.py` (relations v3, indexes).
- `B2_GRAPHE_ETUDE.md` §6.1–6.3, §7.
- `10_graph__schema-cible__hermes__2026-10-17.md` (DDL).
- `10_graph__contradiction-sqlpgq-et-index__minimax-code__2026-10-17.md` (index, SQL/PGQ).
- `10_graph__contradiction-72h-scope__codex__2026-10-17.md` (scope).
- SQLite `WITH RECURSIVE` — https://sqlite.org/lang_with.html — consulté 2026-10-17.
- PostgreSQL recursive queries — https://www.postgresql.org/docs/18/queries-with.html — consulté 2026-10-17.
