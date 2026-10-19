# G3 — DEV/EVAL windows, embargoes (freeze v1)

**Status: FROZEN v1 (open proposals marked NOT DONE)** — 2026-10-16T00:00:00Z.
Sources: B7 §d.1/§d.2, FREEZE_V2 §7, DOC2 §5.8.4. Frozen code:
`src/orvyren/evaluation/windows.py` — sha256 `c1cef663068761febabc8f0325759b948c0e885e4f44fc2974042c5e679eb4d0`.

## 1. Registry — DEVELOPMENT set

| Window | Type | UTC bounds | Sources |
|---|---|---|---|
| `dev-usdc-2023-03` | stress | 2023-03-10T00:00:00Z → 2023-03-14T00:00:00Z | evidence/episode_usdc_2023-03.json, corpus/usdc_observations.csv |
| `dev-usdc-2023-02-temoin` | temoin | 2023-02-15T00:00:00Z → 2023-02-18T00:00:00Z | corpus/usdc_observations.csv, corpus/manifest.json |
| `dev-steth-2022-06` | stress | 2022-05-09T00:00:00Z → 2022-07-31T00:00:00Z | evidence/episode_steth_2022-06.json |
| `dev-steth-2022-05-calme` | calme | 2022-05-01T00:00:00Z → 2022-05-08T00:00:00Z | evidence/episode_steth_2022-06.json |

## 2. Registry — EVALUATION set

| Window | Type | UTC bounds | Sources |
|---|---|---|---|
| `eval-rseth-2026-04` | stress | 2026-04-17T00:00:00Z → 2026-04-21T00:00:00Z | evidence/episode_rseth_2026-04.json, B7 §d.1 |
| `eval-usd0pp-2025-01` | stress | 2025-01-08T00:00:00Z → 2025-01-31T00:00:00Z | corpus/series/usd0pp_2025-01.json, B7 §d.1 |

## 3. CALM criterion — mechanical application (the result is written, not adjusted)

Frozen criterion (B7 §d.1): `max|P_t − 1| < 0,5 %` over the whole window ; failure → reclassified STRESS.

* USDC control window 15–18/02/2023: measured maximum deviation **1.300000 %** ≥ 0,5 % → **reclassified STRESS** (but 0 sustained depeg: rule AX0 produces no signal there, cf. `evidence/baseline_report.json`) ;
* stETH calm window 01–08/05/2022: measured maximum deviation **0.222689 %** < 0,5 % → **CALM confirmed** (measurement on the realizable get_dy discount series).

## 4. NOT DONE — windows that cannot be derived (never invented)

| Window | Status | Reason |
|---|---|---|
| eval-calme-2025-2026 (≥ 6) | NOT DONE | Exact list and bounds of the CALM EVAL windows to freeze (B7 Q6 / FREEZE_V2 §11.5): requires the CALM criterion applied to 2025–2026 series not yet archived in the repository. No window is invented. |
| dev-calme-2022-2023 (≥ 6) | PARTIEL | Only one DEV calm window is derivable today (dev-steth-2022-05-calme, criterion satisfied). The USDC control window fails the frozen CALM criterion (reclassified STRESS). The remaining calm windows depend on a collection work item (R3 §C.8). |

## 5. The four embargoes (verifiers in `windows.py`)

1. **Parameters** — no constant of G1–G6 may be modified after the first EVAL run ; any
   modification invalidates the evaluation (new dated version + hash + variants log).
2. **Data (24 h)** — the band `[début EVAL − 24 h, début EVAL]` is removed from DEV
   (`data_embargo_violations`).
3. **Inspection** — before the freeze, no inspection of the EVAL windows beyond what is published ;
   after the first run, the set is burned.
4. **Cross-calibration** — the calibration months of the thresholds cannot overlap an
   EVAL CALM window (`cross_calibration_violations`) ; without this rule, calibration
   "sees" the evaluation set.

## 6. Freeze gate (mechanical verification, B7 §d.2.5)

* `verify_frozen_package(frozen_dir)`: `G1..G6.sha256` present, readable, matching — otherwise **refusal** ;
* `eval_run_gate(frozen_dir, lock_path, force)`: refusal of the 2nd EVAL run without `--force` ;
  with `--force`, mandatory mention: "evaluation re-executed (invalid for the claim)" ;
* the EVAL evaluation script must refuse to write if an EVAL CALM window overlaps the
  declared calibration period.

## 7. What remains open (written, non-blocking)

Exact list of the 2025–2026 CALM EVAL windows (B7 Q6) and remaining DEV calm windows
(R3 §C.8): they depend on a collection work item — assumed NOT DONE.
