# Graph A — résultats d'ingestion et d'API (17/10/2026)

**Statut** : interne, exécuté sur `D:/orvyren_core_hermes` (`feat/10h-graph`, commits `1d73183`, `9580bf1`). Après fusion B, `master` compte **1072 tests** (1069 verts, 3 sautés) ; ce document conserve les mesures de la piste A.
**But** : prouver que le graphe v3 peut être peuplé et interrogé, sans revendiquer plus que mesuré.

## Résultat mesuré

| Élément | Valeur |
|---|---:|
| Chaîne / protocole | Base mainnet / Aave v3 Pool |
| Fenêtre | 30 000 blocs, `52695534` → `52725533` |
| Événements | **15 000** |
| Relations | **12 937** |
| Nœuds | **16 174** |
| Provenance | **12 937** lignes |
| Types de relations | **8** |
| Taille DB | 50 Mo (fichier local) |
| Tests | **868 passed, 3 skipped, 269 subtests** |

Types : `HOLDS`, `DEPOSITED_IN`, `OWES`, `COLLATERALIZES`, `PART_OF`, `DEPLOYED_ON`, `IS_A`, `CONSTRAINS`.

## Latences (API SQL read-only, 12,9k relations)

| Requête | p50 | p95 |
|---|---:|---:|
| Q1 exposition | 81,6 ms | 87,7 ms |
| Q4 PIT | 25,3 ms | 26,1 ms |
| Q7 concentration | 10,6 ms | 11,0 ms |
| snapshot | 125,3 ms | 135,5 ms |

## Commandes

```bash
cd D:/orvyren_core_hermes
PYTHONPATH=src python scripts/ingest_aave_base.py \
  --db D:/orvyren_10h_2026-10-17/graph_v3.sqlite \
  --blocks 30000 --max-events 15000 --chunk-size 1000

python scripts/backfill_structural_relations.py \
  --db D:/orvyren_10h_2026-10-17/graph_v3.sqlite

PYTHONPATH=src python scripts/export_ui_snapshot.py \
  --db D:/orvyren_10h_2026-10-17/graph_v3.sqlite \
  --out D:/orvyren_10h_2026-10-17/ui_snapshot.json
```

## Limites honnêtes

- **Pas de liquidation** dans la fenêtre : `LIQUIDATED_IN` est au catalogue mais 0 ligne ; aucun événement inventé.
- **Q8 = NOT_INGESTED** : pas de Safe/Zodiac dans ce slice.
- Les timestamps d'événements sont **interpolés entre deux blocs exacts** ; le bloc reste autoritaire pour le PIT.
- Le raw store et le manifeste sont dans `D:/orvyren_10h_2026-10-17/raw/`.
- Aucun fournisseur payant, aucune clé privée, aucun fonds réel.
- La base `graph_v3.sqlite` est externe au dépôt ; le snapshot UI (`evidence/ui_snapshot.json`) est la pièce versionnée.

## Ce qui reste

- Q8 : ingérer Safe/Zodiac si le scénario l'exige.
- `edge_current` matérialisée si Q1 doit passer sous 50 ms à 100k.
- Benchmark Aave à 100k+ si la fenêtre est élargie.
- EVAL agent : N=0, non revendiquée.
