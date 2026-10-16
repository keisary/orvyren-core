# G2 — Comparateurs (gel v1)

**Statut : GELÉ v1** — 2026-10-16T00:00:00Z. Sources : B7 §e.1 (table + collision
d'étiquettes tranchée), W2-D §C.1. Code gelé : `src/orvyren/evaluation/comparators.py` —
sha256 `29d93707ad86058acc6c7994aad66b478743d1928d99a2ca60314d807a47aece`.

## 1. Étiquettes gelées (la collision R3/W2-D est tranchée)

| Code | Système | Définition opérationnelle | Coût |
|---|---|---|---|
| **A0** | NO-ACTION | ne rien faire sur toute la fenêtre | 0 |
| **A1** | Règle de seuil | décote D ≥ 50 bp pendant 15 min → réduction bornée x* = min(x_max, Depth_ε, x_seuil) | ~0 |
| **A2** | Agent ORVYREN | corpus → graphe → hypothèses → branche → critique → politique bornée (rejeu journal sinon archive k=3) | plafonné, mesuré |
| **B0** | Placebo apparié | mêmes nombre et tailles d'actions que A2, horodatages tirés uniformément sur la grille horaire, M ≥ 200, graine fixée | ~0 |
| **AX0** | Règle gelée du dépôt (ex-« A0 » de R3) | 0,99 × 2 obs consécutives → réduction de 100 USDC ; déléguée à `decision/baseline.py` | ~0 |
| **O** | Oracle ex post faisable | `min_{b ∈ F} L(b)` avec la fonction de perte gelée — borne inférieure du regret, pas une vérité terrain | hors ligne |

La règle gelée du dépôt s'écrit **AX0** dans tous les rapports du concours (l'étiquette
« A0-code » est interdite : sans cette résolution, « A0 a fait mieux que A0 » était écrit).

## 2. Paramètres gelés

* A1 : `min_discount_bp = 50`, `persistence_minutes = 15` (soit, sur grille horaire, **deux
  lectures consécutives**, gap ≤ 90 min ; un épisode = un seul déclenchement) ;
* B0 : `seed = 20261016`, `M ≥ 200`, grille horaire, tirages **reproductibles** (même graine → mêmes horodatages) ;
* plafond d'action démo `x_max = 100 USDC` (FREEZE_V2 §E2 ; repris de
  `evidence/decision_usdc-2023-03.json`).

## 3. Phrases pré-écrites (gelées AVANT exécution, B7 §e.1)

> Si A2 ne bat pas B0, la valeur du système n'est pas dans le **choix du moment** — écrit tel quel.
>
> Si A2 ne bat pas A1, la valeur du système n'est pas dans la **délibération** — écrit tel quel.

## 4. Vérifications exécutables

`tests/test_evaluation_comparators.py` — sha256
`0c4c9e3d4203b82d0950ca37f55b1bb8293466544be00e065a6d07e132653a05` :
A0 = 0 action ; A1 déclenche/un-seul-signal/trou casse la contiguïté ; **AX0 reproduit
`evidence/baseline_report.json`** (2 signaux fenêtre principale, 0 sur la fenêtre témoin) ;
B0 reproductible et M ≥ 200 exigé ; oracle = membre de F.

## 5. NOT DONE

* A2 : code produit par les blocs A–E (agents, graphe, politique) — hors Sprint 0 ; les clés API
  d'équipe restent un bloquant du mode `REPLAY-ARCHIVE` (B7 §0.11) ;
* `Depth_ε` et `x_seuil` d'A1 : non mesurés → plafond x_max, note de substitution sur chaque action.
