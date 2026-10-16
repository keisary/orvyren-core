# Prévisions DEV gelées — lecture détaillée (FR)

**8 prévisions gelées le 2026-10-16T00:00:00Z**, chaînées par `prev_hash` dans `frozen/forecasts_dev.jsonl`, résolues par le résolveur déterministe (`frozen/outcomes_dev.jsonl`). Jeu **DEV** exclusivement : ces prévisions démontrent la **méthode** (falsifiabilité + résolution + scores), elles ne revendiquent **aucune** performance prédictive — les épisodes 2022–2023 sont dans les données d'entraînement des modèles 2026 (B7 §d.1, DECLARÉ).

## Synthèse (N = 8, libellé de la cascade : « non conclusionnel »)

* `ȳ` (climatologie DEV) = **0.500000** (4/8 prévisions résolues à 1) ;
* proportion de dépeg soutenu (sous-ensemble `depeg`, 3 prévisions) : 3/3 ;
* proportion sur l'ensemble : 4/8, IC de Wilson 95 % = [0.2152 ; 0.7848] ;
* sous-ensemble `absence_attendue` (4 prévisions : fenêtres témoin + pré/post-crise) : 0/4 dépeg observé — borne supérieure de Wilson = 0.4899 ;
* phrase obligatoire (B7 §b.2) : « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » ; transposée ici : 0/4 ne signifie pas taux nul — taux compatible avec jusqu'à ≈ 49.0 %.

`BS/REL/RES/UNC/ECE` : **non publiés dans ce fichier** — le rapport de calibration officiel (`evidence/calibration_report_skeleton.md`) reste le squelette N = 0, et la cascade impose « non conclusionnel » tant que N < 30 (sera calculable dès que le harnais publiera ses scores).

**Constat d'honnêteté sur les `p`** : le prior employé est un comptage de climatologie LOO. Mécaniquement, exclure la fenêtre cible retire des fenêtres de crise du comptage des prévisions de crise : `p` peut donc être **plus bas en crise qu'en calme** (ex. h-crise 0,2437 contre h-calme-1 0,2995). Ce n'est pas une erreur de calcul, c'est la limite du prior — un estimateur conditionnel à l'état courant (et non une climatologie globale) est un chantier identifié, hors v1.

## Détail des prévisions

### `dev-usdc-2023-03.h-calme-1` — Fenêtre témoin USDC, 16/02/2023 00:00Z (calme dans le sens « aucun dépeg soutenu »)

* **Énoncé** : Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2023-02-16T00:00:00Z
* **p = 0.299492** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2023-02-16T06:00:00Z
* **Résolution (déterministe)** : y = **0** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.999701, "max_discount_pct": 0.0299, "first_violation_utc": "2023-02-16T03:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash** : sha256 `d80c4159c7c8ff3636bd84854669939f…` · prev_hash `0000000000000000…` · outcome `dev-usdc-2023-03.h-calme-1.h_class`

### `dev-usdc-2023-03.h-calme-2` — Fenêtre témoin USDC, 17/02/2023 00:00Z

* **Énoncé** : Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2023-02-17T00:00:00Z
* **p = 0.299492** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2023-02-17T06:00:00Z
* **Résolution (déterministe)** : y = **0** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.999157, "max_discount_pct": 0.0843, "first_violation_utc": "2023-02-17T05:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash** : sha256 `d7c2dcbeb30b980b07997e3e6a053020…` · prev_hash `d80c4159c7c8ff36…` · outcome `dev-usdc-2023-03.h-calme-2.h_class`

### `dev-usdc-2023-03.h-pre-crise` — USDC, veille du dépeg (10/03/2023 12:00Z)

* **Énoncé** : Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2023-03-10T12:00:00Z
* **p = 0.299492** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2023-03-10T18:00:00Z
* **Résolution (déterministe)** : y = **0** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.99558, "max_discount_pct": 0.442, "first_violation_utc": "2023-03-10T14:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash** : sha256 `b051327c08a3043dbe72e27799e57b13…` · prev_hash `d7c2dcbeb30b980b…` · outcome `dev-usdc-2023-03.h-pre-crise.h_class`

### `dev-usdc-2023-03.h-crise` — USDC, cœur de crise (11/03/2023 04:00Z)

* **Énoncé** : Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2023-03-11T04:00:00Z
* **p = 0.243655** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 48/197 = 0.243655 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2023-03-11T10:00:00Z
* **Résolution (déterministe)** : y = **1** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.876675, "max_discount_pct": 12.3325, "first_violation_utc": "2023-03-11T08:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2023-03-11T10:00:00Z"}
* **Provenance/hash** : sha256 `ed738a33bea74a09a18a1b578625d5d7…` · prev_hash `b051327c08a3043d…` · outcome `dev-usdc-2023-03.h-crise.h_class`

### `dev-usdc-2023-03.h-post-crise` — USDC, retour vers la parité (13/03/2023 12:00Z)

* **Énoncé** : Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2023-03-13T12:00:00Z
* **p = 0.289340** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 57/197 = 0.289340 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2023-03-13T18:00:00Z
* **Résolution (déterministe)** : y = **0** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.99102079028018, "max_discount_pct": 0.897921, "first_violation_utc": "2023-03-13T12:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash** : sha256 `c6099b02a50f21c33788ed2db56b9589…` · prev_hash `ed738a33bea74a09…` · outcome `dev-usdc-2023-03.h-post-crise.h_class`

### `dev-steth-2022-05.t-calme` — stETH, fenêtre calme (critère CALME gelé)

* **Énoncé** : La fenêtre 05/05 → 08/05/2022 tient le critère CALME gelé (max |1 − prix réalisable stETH| < 0,5 %) sur la série get_dy 1 stETH.
* **Jeu** : dev · **persona** : dao · **horizon** : T (72.0 h) · gelée : 2022-05-05T00:00:00Z
* **p = 0.008130** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 2/246 = 0.008130 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Règle de résolution** : `calm_window_v1` · `resolve_not_before` = 2022-05-08T00:00:00Z
* **Résolution (déterministe)** : y = **1** — observé : {"rule": "calm_window_v1", "tolerance_pct": 0.5, "n_observations": 4, "max_abs_deviation_pct": 0.222689, "worst_observation_utc": "2022-05-08T00:00:00Z", "worst_price": 0.9977731075831178}
* **Provenance/hash** : sha256 `1b337e40dc4e5b442c061658f1653b45…` · prev_hash `c6099b02a50f21c3…` · outcome `dev-steth-2022-05.t-calme.t`

### `dev-steth-2022-05.t-rupture` — stETH, ouverture de la décote (13–21/05/2022)

* **Énoncé** : La décote réalisable stETH (get_dy pour 1 stETH) dépasse 1 % sur ≥ 2 observations consécutives de la grille pendant les 7 jours suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : T (168.0 h) · gelée : 2022-05-12T00:00:00Z
* **p = 0.978632** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 229/234 = 0.978632 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2022-05-19T00:00:00Z
* **Résolution (déterministe)** : y = **1** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 1500, "n_observations": 8, "min_price": 0.9759097579306899, "max_discount_pct": 2.409024, "first_violation_utc": "2022-05-14T00:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2022-05-19T00:00:00Z"}
* **Provenance/hash** : sha256 `ba17cd7389b70327fc5dd350844393dd…` · prev_hash `1b337e40dc4e5b44…` · outcome `dev-steth-2022-05.t-rupture.t`

### `dev-steth-2022-06.h-crise` — stETH, fenêtre horaire 10→17/06/2022 (gel des retraits Celsius)

* **Énoncé** : La décote réalisable stETH reste au-dessus de 1 % sur ≥ 2 observations horaires consécutives dans les 6 h suivant t_frozen.
* **Jeu** : dev · **persona** : dao · **horizon** : H_class (6.0 h) · gelée : 2022-06-13T00:00:00Z
* **p = 1.000000** — origine : estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 153/153 = 1.000000 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Règle de résolution** : `sustained_depeg_v1` · `resolve_not_before` = 2022-06-13T06:00:00Z
* **Résolution (déterministe)** : y = **1** — observé : {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.9471168317600716, "max_discount_pct": 5.288317, "first_violation_utc": "2022-06-13T03:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2022-06-13T06:00:00Z"}
* **Provenance/hash** : sha256 `a6d3491fb42554965600a296cbcb99bc…` · prev_hash `ba17cd7389b70327…` · outcome `dev-steth-2022-06.h-crise.h_class`

## Ce qui n'est PAS revendiqué

* aucune supériorité de l'agent A2 (le harnais A0/A1/B0 n'est pas construit) ;
* aucune calibration (« non conclusionnel » à N < 30, exigence des 5 conditions à N ≥ 100) ;
* l'origine de chaque `p` est publiée avec ses effectifs (fonction `base_rate_loo`) : la fenêtre cible est exclue du comptage, mais le comptage reste un prior de climatologie — sur des fenêtres de crise, un prior de climatologie sous-estime mécaniquement le risque (constat, pas excuse).
