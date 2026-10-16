# G3 — Fenêtres DEV/EVAL, embargos (gel v1)

**Statut : GELÉ v1 (propositions ouvertes marquées NOT DONE)** — 2026-10-16T00:00:00Z.
Sources : B7 §d.1/§d.2, FREEZE_V2 §7, DOC2 §5.8.4. Code gelé :
`src/orvyren/evaluation/windows.py` — sha256 `25a3315434945d292a1365e40777085467c03f68a3d6db47d3bfdd26d72f0338`.

## 1. Registre — jeu DÉVELOPPEMENT

| Fenêtre | Type | Bornes UTC | Sources |
|---|---|---|---|
| `dev-usdc-2023-03` | stress | 2023-03-10T00:00:00Z → 2023-03-14T00:00:00Z | evidence/episode_usdc_2023-03.json, corpus/usdc_observations.csv |
| `dev-usdc-2023-02-temoin` | temoin | 2023-02-15T00:00:00Z → 2023-02-18T00:00:00Z | corpus/usdc_observations.csv, corpus/manifest.json |
| `dev-steth-2022-06` | stress | 2022-05-09T00:00:00Z → 2022-07-31T00:00:00Z | evidence/episode_steth_2022-06.json |
| `dev-steth-2022-05-calme` | calme | 2022-05-01T00:00:00Z → 2022-05-08T00:00:00Z | evidence/episode_steth_2022-06.json |

## 2. Registre — jeu ÉVALUATION

| Fenêtre | Type | Bornes UTC | Sources |
|---|---|---|---|
| `eval-rseth-2026-04` | stress | 2026-04-17T00:00:00Z → 2026-04-21T00:00:00Z | evidence/episode_rseth_2026-04.json, B7 §d.1 |
| `eval-usd0pp-2025-01` | stress | 2025-01-08T00:00:00Z → 2025-01-31T00:00:00Z | B7 §d.1 |

## 3. Critère CALME — application mécanique (le résultat s'écrit, il ne s'ajuste pas)

Critère gelé (B7 §d.1) : `max|P_t − 1| < 0,5 %` sur toute la fenêtre ; échec → reclassée STRESS.

* fenêtre témoin USDC 15–18/02/2023 : écart maximal mesuré **1.300000 %** ≥ 0,5 % → **reclassée STRESS** (mais 0 dépeg soutenu : la règle AX0 n'y produit aucun signal, cf. `evidence/baseline_report.json`) ;
* fenêtre calme stETH 01–08/05/2022 : écart maximal mesuré **0.222689 %** < 0,5 % → **CALME confirmée** (mesure sur la série de décote réalisable get_dy).

## 4. NOT DONE — fenêtres non dérivables (jamais inventées)

| Fenêtre | Statut | Motif |
|---|---|---|
| eval-calme-2025-2026 (≥ 6) | NOT DONE | Liste exacte et bornes des fenêtres CALME EVAL à figer (B7 Q6 / FREEZE_V2 §11.5) : exige le critère CALME appliqué à des séries 2025–2026 non encore archivées dans le dépôt. Aucune fenêtre n'est inventée. |
| dev-calme-2022-2023 (≥ 6) | PARTIEL | Une seule fenêtre calme DEV est dérivable aujourd'hui (dev-steth-2022-05-calme, critère satisfait). La fenêtre témoin USDC échoue au critère CALME gelé (reclassée STRESS). Les fenêtres calmes restantes dépendent d'un chantier de collecte (R3 §C.8). |

## 5. Les quatre embargos (vérificateurs dans `windows.py`)

1. **Paramètres** — aucune constante de G1–G6 modifiable après la première exécution EVAL ; toute
   modification invalide l'évaluation (nouvelle version datée + hash + journal des variantes).
2. **Données (24 h)** — la bande `[début EVAL − 24 h, début EVAL]` est retirée du DEV
   (`data_embargo_violations`).
3. **Inspection** — avant le gel, aucune inspection des fenêtres EVAL au-delà du publié ;
   après la première exécution, le jeu est brûlé.
4. **Calibration croisée** — les mois de calibration des seuils ne peuvent chevaucher une
   fenêtre CALME EVAL (`cross_calibration_violations`) ; sans cette règle, la calibration
   « voit » le jeu d'évaluation.

## 6. Porte de gel (vérification mécanique, B7 §d.2.5)

* `verify_frozen_package(frozen_dir)` : `G1..G6.sha256` présents, lisibles, concordants — sinon **refus** ;
* `eval_run_gate(frozen_dir, lock_path, force)` : refus de la 2ᵉ exécution EVAL sans `--force` ;
  avec `--force`, mention obligatoire : « évaluation ré-exécutée (invalide pour la revendication) » ;
* le script d'évaluation EVAL doit refuser d'écrire si une fenêtre CALME EVAL chevauche la
  période de calibration déclarée.

## 7. Ce qui reste ouvert (écrit, non bloquant)

Liste exacte des fenêtres CALME EVAL 2025–2026 (B7 Q6) et fenêtres calmes DEV restantes
(R3 §C.8) : dépendent d'un chantier de collecte — NOT DONE assumé.
