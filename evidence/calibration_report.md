> **DEV** — rapport de calibration — N = 8 — non conclusionnel

# Calibration — jeu DEV (prévisions gelées `frozen/forecasts_dev.jsonl`)

## 1. Périmètre et hashes

- N = **8** prévision(s) résolue(s) · non résolues : 0
- forecasts `c9d4763720d91724` · outcomes `b1dd134c06f1afd4` · code `0a90281453610c1b`

## 2. Tableau global (N = 8)

- **bins** : 10
- **bs** : 0.23864066201860576
- **bss** : 0.04543735192557696
- **ece** : 0.1805886901606228
- **n** : 8
- **rel** : 0.12765848155989915
- **res** : 0.15
- **unc** : 0.25
- **verdict** : non conclusionnel
- **ybar** : 0.5
- **bootstrap** : {"block_size": 6, "n_reps": 10000, "seed": 20261016}

## 3. Courbe de fiabilité (bins, N affiché)

| bin | n_b | conf | acc | IC Wilson |
|---|---|---|---|---|
| 0 | 1 | 0.0081 | 1.0000 | 0.2065–1.0000 |
| 1 | 0 | — | — | — |
| 2 | 5 | 0.2863 | 0.2000 | 0.0362–0.6245 |
| 3 | 0 | — | — | — |
| 4 | 0 | — | — | — |
| 5 | 0 | — | — | — |
| 6 | 0 | — | — | — |
| 7 | 0 | — | — | — |
| 8 | 0 | — | — | — |
| 9 | 2 | 0.9893 | 1.0000 | 0.3424–1.0000 |

## 4. Par famille (N par cellule)

- **steth-2022-06** — N = 3 — Brier 0.3281
- **usdc-2023-03** — N = 5 — Brier 0.1850

## 5. Annexe des prévisions (N = 8)

| forecast_id | p | y | (p−y)² | horizon | règle |
|---|---|---|---|---|---|
| `dev-usdc-2023-03.h-calme-1` | 0.2995 | 0 | 0.0897 | H_class | sustained_depeg_v1 |
| `dev-usdc-2023-03.h-calme-2` | 0.2995 | 0 | 0.0897 | H_class | sustained_depeg_v1 |
| `dev-usdc-2023-03.h-pre-crise` | 0.2995 | 0 | 0.0897 | H_class | sustained_depeg_v1 |
| `dev-usdc-2023-03.h-crise` | 0.2437 | 1 | 0.5721 | H_class | sustained_depeg_v1 |
| `dev-usdc-2023-03.h-post-crise` | 0.2893 | 0 | 0.0837 | H_class | sustained_depeg_v1 |
| `dev-steth-2022-05.t-calme` | 0.0081 | 1 | 0.9838 | T | calm_window_v1 |
| `dev-steth-2022-05.t-rupture` | 0.9786 | 1 | 0.0005 | T | sustained_depeg_v1 |
| `dev-steth-2022-06.h-crise` | 1.0000 | 1 | 0.0000 | H_class | sustained_depeg_v1 |

> cascade §b.3 : N < 5 rien ; 5 ≤ N < 30 « non conclusionnel » ; ECE non revendicable avant N ≥ 100 et les 5 conditions