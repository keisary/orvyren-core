# G5 — Plan d'analyse (gel v1)

**Statut : GELÉ v1** — 2026-10-16T00:00:00Z. Sources : B7 §b.1–b.4, §e.2–e.5, DOC2 §5.8.2.
Code gelé : `calibration.py` sha256
`0a90281453610c1b6258a99540d0d060132c56264aab2039921f81ce845fad13`,
`forecasts.py` sha256 `b5857165694ae06f736018531c4d295031f30060af563a2f2f7b162047452d8d`,
`outcomes.py` sha256 `c2a725912a5239b62755aa48d57a5898dfc2e5b54efd0bf0b008f52dbe0c9c0d`.

## 1. Métriques publiées (C1–C7) et formules

| Code | Métrique | Formule |
|---|---|---|
| C1 | Score de Brier | `BS = (1/N) Σ (p_t − y_t)²` |
| C2 | Décomposition de Murphy | `BS = REL − RES + UNC`, évaluée sur les **mêmes intervalles que l'ECE** (identité exacte, testée) |
| C3 | ECE | `Σ_b (n_b/N)·|acc_b − conf_b|`, **10 intervalles fixes** `[b/10, (b+1)/10)`, gelés d'avance |
| C4 | Courbe de fiabilité | par intervalle : `n_b`, `conf_b`, `acc_b`, IC de Wilson (intervalles vides affichés) |
| C5 | Wilson | `z = 1,959964` ; borne sup. de 0/n = `z²/(n+z²)` |
| C6 | Bootstrap par blocs | circulaire, blocs 6–12 h, 10 000 réplications, **graine fixée** (20261016), percentile 2,5–97,5 |
| C7 | Compétence | `BSS = 1 − BS / (ȳ(1−ȳ))` ; `None` si climatologie dégénérée |

Vecteur KAT (test unitaire de référence, tolérance 1e-12) : `p = [0,2×5 ; 0,8×5]`,
`y = [0,0,0,0,0, 1,1,0,1,1]` → BS 0,100 ; REL 0,020 ; RES 0,160 ; UNC 0,240 ; ECE 0,100 ; ȳ 0,400.

## 2. Cascade « quand peut-on dire calibré » (applicée mécaniquement)

| N (prévisions gelées résolues) | Ce qui est publié | Libellé |
|---|---|---|
| N < 5 | rien | « NON CALCULÉ — N insuffisant » (seuil D11) |
| 5 ≤ N < 30 | BS, REL, RES, UNC, ȳ, liste ; ECE **sans** revendication | « non conclusionnel » |
| 30 ≤ N < 100 | + IC bootstrap, courbe de fiabilité + Wilson par intervalle | « non conclusionnel » |
| N ≥ 100 | tout + BSS avec borne basse | revendication possible **sous les 5 conditions** |

**Les 5 conditions pour écrire « calibré »** : N ≥ 100 hors échantillon ; ECE ≤ 0,05 avec borne
haute d'IC ≤ 0,08 ; pas de déviation systématique (test du signe, `max_b |acc_b − conf_b| ≤ 0,10`) ;
borne basse de l'IC de BSS > 0 ; ≥ 2 familles d'épisodes disjointes + déclaration de non-réglage.
Avec N = 5–12, l'état par défaut est « non conclusionnel » — **publié tel quel**.

## 3. Statistiques de comparaison

* Wilson sur **toutes** les proportions ; phrase obligatoire pour un « 0 échec » :
  « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » ;
* McNemar **exact** sur les paires discordantes (`p = 2·Σ C(n,k)/2^n`, borné à 1 ; KAT 6-0 → 0,03125) ;
* bootstrap par blocs (C6) sur toute statistique de série — jamais d'IC i.i.d. ;
* placebo B0 : distribution complète + percentile de A2.

## 4. Structure imposée du rapport (B7 §b.4, 8 sections)

1. périmètre et hashes (jeu, épisodes, N, période, code_hash, data_hash, liste des forecast_id) ;
2. tableau global (N, ȳ, BS + IC, REL/RES/UNC, ECE, BSS, verdict) ;
3. courbe de fiabilité (une ligne par intervalle) ;
4. décomposition par famille (persona, type, épisode — **N affiché par cellule**) ;
5. annexe des prévisions (`forecast_id | p | y | (p−y)² | horizon | résolveur`) ;
6. anomalies et corrections (`supersedes`, non résolues, quarantaines) ;
7. limites en toutes lettres (contamination, non-échangeabilité, tailles) ;
8. verdict en langage contrôlé (jamais « calibré » sans les 5 conditions).

## 5. Règles de langage gelées

Tout tableau porte son `N` et sa validité ; ne jamais fusionner DEV et EVAL ; ne jamais
moyenner R⁻ et R⁺ ; aucun score agrégé unique ; un rapport sans hash n'est pas vérifiable ;
« calibré » est un mot contrôlé (5 conditions), en dessous c'est « non établi ».

## 6. Vérifications exécutables

`tests/test_evaluation_calibration.py` — sha256
`221e895f3ec3664d7e30af48aaae8722415f5d90b4dea335c8ba790ed5ef7033` : KAT exacts,
Wilson vs table raw_b7 (± 0,001), bootstrap déterministe (2 exécutions identiques), cascade.
