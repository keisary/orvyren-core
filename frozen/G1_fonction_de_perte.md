# G1 — Fonction de perte (gel v1)

**Statut : GELÉ v1** — 2026-10-16T00:00:00Z. Source normative : W2-D §B.1 (formulation
corrigée), §B.6 (six tests), B7 §e.1/e.3 (métriques persona). Code gelé :
`src/orvyren/evaluation/loss.py` — sha256 `2742dbc10c3ed0b67b4625edcf75625e12a5917c0bc4e68d7e37abab5f5247a8`.

## 1. Formules gelées

```
W_T(conserver)   = C + q · P_T
W_T(céder x)     = C + x · P_exec(x, t_action) − k + (q − x) · P_T
L(a)             = W_t0 − W_T(a)                    [USD, ou bp de W_t0]
R(a)             = L(a) − min_{b ∈ F} L(b) ≥ 0     [USD]
R⁻ / R⁺          = coûts du faux positif / du faux négatif vs A0 (publiés séparément)
```

## 2. Conventions de valorisation (jamais mélangées)

| Convention | Définition | Usage gelé |
|---|---|---|
| `terminale` | la position restante vaut `P_T` (prix réalisable en T) | desk : terminale + financement |
| `liquidation` | la position restante vaut le prix de liquidation mesuré à T (échelle de profondeur) | DAO (plus prudente, recommandation W2-D §(f) 3) |

Le code **refuse** (`ValuationError`) la convention `liquidation` sans échelle de
profondeur fournie : aucune conversion non mesurée ne se fait passer pour une mesure.

## 3. Famille d'actions faisables F et coût k

* `F` = fractions de q `{0 ; 0,25 ; 0,5 ; 0,75 ; 1}`, `x = 0` toujours inclus ;
  plafond de politique `x_max` appliqué par `min(x, x_max)` (démo : 100 USDC, FREEZE_V2 §E2) ;
* `k` = coûts explicites **non déjà inclus** dans `P_exec` (frais, gas, pontage, financement) ;
* `P_exec(x)` = prix moyen obtenu pour la taille x, issu de l'échelle de profondeur mesurée —
  jamais un prix d'écran. `Depth_ε` reste **à mesurer** (chantier W2-B §(f) 5) : NOT DONE.

## 4. Personas

* **DAO** — pas de re-entrée dans l'épisode ; perte évitée conditionnelle
  `E[perte] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR` (les deux facteurs publiés) ;
  seconde lecture en **jours de runway**, `opex_ref = 44 932 $/j` (G6).
* **desk** — re-entrée modélisée dans la même fenêtre : `ΔP&L = x·(P_exec − P_T) − k − financement` ;
  agrégats Sharpe/Sortino/MaxDD (R_f = 0 par convention crypto ; `None` quand non calculable).

## 5. Les six tests (W2-D §B.6) — doivent passer avant le gel

| # | Test | Attendu |
|---|---|---|
| T1 | Neutralité (P_exec = P_T, k = 0 ⇒ R = 0) | 0 exact (détecte le double comptage §B.2) |
| T2 | Invariance par translation | R inchangé à 1e-12 |
| T3 | Monotonie en coût | L et R croissants |
| T4 | Cohérence de signe (P_exec > P_T) | R(agir) = 0, R(ne rien faire) > 0 |
| T5 | Additivité de l'inventaire | linéaire en q et en x |
| T6 | Référence dégénérée (P_t = 1) | tous les regrets 0 ; action inutile = k |

Preuve exécutable : `tests/test_evaluation_loss.py` — sha256
`8f87f3f06718beb4032ffd0efe61a145764986571718a9696460d085efa541c4` ; commande
`python -m pytest tests/test_evaluation_loss.py -q` (12 tests).

## 6. Ce qui n'est PAS gelé ici (NOT DONE, écrit tel quel)

* `Depth_ε` (profondeur d'exécution en crise) : non mesurée → plafond x_max utilisé et **noté** sur chaque action A1 ;
* `r_capital` (taux de financement desk) : aucune source — voir G6 ;
* le bug historique `q(1 − P_T)` de la formule antérieure (W2-D §B.2) est reproduit en test pour non-régression (écart affiché 20 contre écart réel 10).

## 7. Révision

Toute modification de ce fichier ou de `loss.py` après la première exécution
EVAL **invalide** l'évaluation (embargo de paramètres, B7 §d.2.1) : nouvelle
version datée + hash + entrée au journal des variantes.
