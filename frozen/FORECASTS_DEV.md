# Frozen DEV forecasts — detailed reading

**8 forecasts frozen on 2026-10-16T00:00:00Z**, chained by `prev_hash` in `frozen/forecasts_dev.jsonl`, resolved by the deterministic resolver (`frozen/outcomes_dev.jsonl`). **DEV** set exclusively: these forecasts demonstrate the **method** (falsifiability + resolution + scores), they claim **no** predictive performance — the 2022–2023 episodes are inside the training data of the 2026 models (B7 §d.1, DECLARED).

## Summary (N = 8, cascade label: « non-conclusive »)

* `ȳ` (DEV climatology) = **0.500000** (4/8 forecasts resolved to 1) ;
* sustained-depeg proportion (`depeg` subset, 3 forecasts): 3/3 ;
* proportion over the whole set: 4/8, Wilson 95 % CI = [0.2152 ; 0.7848] ;
* `absence_attendue` subset (4 forecasts: control windows + pre/post-crisis): 0/4 observed depeg — Wilson upper bound = 0.4899 ;
* mandatory sentence (B7 §b.2): « 0/6 does not mean a zero rate, but a rate compatible with up to ≈ 39 % (Wilson upper bound) » ; transposed here: 0/4 does not mean a zero rate — a rate compatible with up to ≈ 49.0 %.

`BS/REL/RES/UNC/ECE`: **not published in this file** — the official calibration report (`evidence/calibration_report_skeleton.md`) remains the N = 0 skeleton, and the cascade imposes « non-conclusive » as long as N < 30 (computable as soon as the harness publishes its scores).

**Honesty observation on the `p` values**: the prior used is an LOO climatology count. Mechanically, excluding the target window removes crisis windows from the count of crisis forecasts: `p` can therefore be **lower in crisis than in calm** (e.g. h-crise 0,2437 against h-calme-1 0,2995). This is not a computation error, it is the limit of the prior — an estimator conditioned on the current state (rather than a global climatology) is an identified work item, outside v1.

## Forecast details

### `dev-usdc-2023-03.h-calme-1` — Fenêtre témoin USDC, 16/02/2023 00:00Z (calme dans le sens « aucun dépeg soutenu »)

* **Statement**: Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2023-02-16T00:00:00Z
* **p = 0.299492** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2023-02-16T06:00:00Z
* **Resolution (deterministic)**: y = **0** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.999701, "max_discount_pct": 0.0299, "first_violation_utc": "2023-02-16T03:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash**: sha256 `fe17c6055b7626e3bc4fd034253a3b93…` · prev_hash `0000000000000000…` · outcome `dev-usdc-2023-03.h-calme-1.h_class`

### `dev-usdc-2023-03.h-calme-2` — Fenêtre témoin USDC, 17/02/2023 00:00Z

* **Statement**: Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2023-02-17T00:00:00Z
* **p = 0.299492** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2023-02-17T06:00:00Z
* **Resolution (deterministic)**: y = **0** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.999157, "max_discount_pct": 0.0843, "first_violation_utc": "2023-02-17T05:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash**: sha256 `9e91d1a94fbd8a3a8bd2d7b21ebe505b…` · prev_hash `fe17c6055b7626e3…` · outcome `dev-usdc-2023-03.h-calme-2.h_class`

### `dev-usdc-2023-03.h-pre-crise` — USDC, veille du dépeg (10/03/2023 12:00Z)

* **Statement**: Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2023-03-10T12:00:00Z
* **p = 0.299492** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 59/197 = 0.299492 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2023-03-10T18:00:00Z
* **Resolution (deterministic)**: y = **0** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.99558, "max_discount_pct": 0.442, "first_violation_utc": "2023-03-10T14:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash**: sha256 `9223887fa5e88e70793b399477c22708…` · prev_hash `9e91d1a94fbd8a3a…` · outcome `dev-usdc-2023-03.h-pre-crise.h_class`

### `dev-usdc-2023-03.h-crise` — USDC, cœur de crise (11/03/2023 04:00Z)

* **Statement**: Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2023-03-11T04:00:00Z
* **p = 0.243655** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 48/197 = 0.243655 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2023-03-11T10:00:00Z
* **Resolution (deterministic)**: y = **1** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.876675, "max_discount_pct": 12.3325, "first_violation_utc": "2023-03-11T08:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2023-03-11T10:00:00Z"}
* **Provenance/hash**: sha256 `17b99a81cab01aecf126d1a51dcfd136…` · prev_hash `9223887fa5e88e70…` · outcome `dev-usdc-2023-03.h-crise.h_class`

### `dev-usdc-2023-03.h-post-crise` — USDC, retour vers la parité (13/03/2023 12:00Z)

* **Statement**: Un dépeg soutenu de l'USDC (écart > 1 % du pair sur ≥ 2 observations horaires consécutives de la série agrégée DeFiLlama) est observé dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2023-03-13T12:00:00Z
* **p = 0.289340** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 57/197 = 0.289340 ; corpus figé (corpus/usdc_observations.csv, sha256 c31088b3de428a35…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2023-03-13T18:00:00Z
* **Resolution (deterministic)**: y = **0** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.99102079028018, "max_discount_pct": 0.897921, "first_violation_utc": "2023-03-13T12:00:00Z", "sustained_runs": 0, "longest_run_obs": 0, "first_sustained_utc": null}
* **Provenance/hash**: sha256 `5c937a3a8e6d6b7bd618cfdbc611387b…` · prev_hash `17b99a81cab01aec…` · outcome `dev-usdc-2023-03.h-post-crise.h_class`

### `dev-steth-2022-05.t-calme` — stETH, fenêtre calme (critère CALME gelé)

* **Statement**: La fenêtre 05/05 → 08/05/2022 tient le critère CALME gelé (max |1 − prix réalisable stETH| < 0,5 %) sur la série get_dy 1 stETH.
* **Set**: dev · **persona**: dao · **horizon**: T (72.0 h) · frozen: 2022-05-05T00:00:00Z
* **p = 0.008130** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 2/246 = 0.008130 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Resolution rule**: `calm_window_v1` · `resolve_not_before` = 2022-05-08T00:00:00Z
* **Resolution (deterministic)**: y = **1** — observed: {"rule": "calm_window_v1", "tolerance_pct": 0.5, "n_observations": 4, "max_abs_deviation_pct": 0.222689, "worst_observation_utc": "2022-05-08T00:00:00Z", "worst_price": 0.9977731075831178}
* **Provenance/hash**: sha256 `01d34e99f137328d1465cf5cfeff6e6c…` · prev_hash `5c937a3a8e6d6b7b…` · outcome `dev-steth-2022-05.t-calme.t`

### `dev-steth-2022-05.t-rupture` — stETH, ouverture de la décote (13–21/05/2022)

* **Statement**: La décote réalisable stETH (get_dy pour 1 stETH) dépasse 1 % sur ≥ 2 observations consécutives de la grille pendant les 7 jours suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: T (168.0 h) · frozen: 2022-05-12T00:00:00Z
* **p = 0.978632** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 229/234 = 0.978632 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2022-05-19T00:00:00Z
* **Resolution (deterministic)**: y = **1** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 1500, "n_observations": 8, "min_price": 0.9759097579306899, "max_discount_pct": 2.409024, "first_violation_utc": "2022-05-14T00:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2022-05-19T00:00:00Z"}
* **Provenance/hash**: sha256 `792ff1c6433248361d109fc09e4313de…` · prev_hash `01d34e99f137328d…` · outcome `dev-steth-2022-05.t-rupture.t`

### `dev-steth-2022-06.h-crise` — stETH, fenêtre horaire 10→17/06/2022 (gel des retraits Celsius)

* **Statement**: La décote réalisable stETH reste au-dessus de 1 % sur ≥ 2 observations horaires consécutives dans les 6 h suivant t_frozen.
* **Set**: dev · **persona**: dao · **horizon**: H_class (6.0 h) · frozen: 2022-06-13T00:00:00Z
* **p = 1.000000** — origin: estimateur explicite — comptage empirique des fenêtres de calibration DEV de même durée/grille, fenêtre cible exclue (LOO) — B7 §a.4 : p = 153/153 = 1.000000 ; corpus figé (evidence/episode_steth_2022-06.json, sha256 22fb64ee37081175…)
* **Resolution rule**: `sustained_depeg_v1` · `resolve_not_before` = 2022-06-13T06:00:00Z
* **Resolution (deterministic)**: y = **1** — observed: {"rule": "sustained_depeg_v1", "ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "n_observations": 7, "min_price": 0.9471168317600716, "max_discount_pct": 5.288317, "first_violation_utc": "2022-06-13T03:00:00Z", "sustained_runs": 1, "longest_run_obs": 7, "first_sustained_utc": "2022-06-13T06:00:00Z"}
* **Provenance/hash**: sha256 `78c6a7e49ddde3eef4cb280a33d471ff…` · prev_hash `792ff1c643324836…` · outcome `dev-steth-2022-06.h-crise.h_class`

## What is NOT claimed

* no superiority of agent A2 (the A0/A1/B0 harness is not built) ;
* no calibration ('non-conclusive' at N < 30, 5-condition requirement at N ≥ 100) ;
* the origin of each `p` is published with its counts (function `base_rate_loo`): the target window is excluded from the count, but the count remains a climatology prior — on crisis windows, a climatology prior mechanically underestimates risk (observation, not excuse).
