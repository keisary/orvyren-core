# G1 — Loss function (freeze v1)

**Status: FROZEN v1** — 2026-10-16T00:00:00Z. Normative source: W2-D §B.1 (corrected
formulation), §B.6 (six tests), B7 §e.1/e.3 (persona metrics). Frozen code:
`src/orvyren/evaluation/loss.py` — sha256 `98ee9bc0a3f9f3ab6023ff4bb75cb19c5131f27e7a76c07fa4548023f9ecda70`.

## 1. Frozen formulas

```
W_T(keep)        = C + q · P_T
W_T(sell x)      = C + x · P_exec(x, t_action) − k + (q − x) · P_T
L(a)             = W_t0 − W_T(a)                    [USD, or bp of W_t0]
R(a)             = L(a) − min_{b ∈ F} L(b) ≥ 0     [USD]
R⁻ / R⁺          = cost of the false positive / of the false negative vs A0 (published separately)
```

## 2. Valuation conventions (never mixed)

| Convention | Definition | Frozen usage |
|---|---|---|
| `terminale` | the remaining position is worth `P_T` (price realizable at T) | desk: terminal + funding |
| `liquidation` | the remaining position is worth the liquidation price measured at T (depth ladder) | DAO (more conservative, W2-D §(f) 3 recommendation) |

The code **refuses** (`ValuationError`) the `liquidation` convention without a
provided depth ladder: no unmeasured conversion is passed off as a measurement.

## 3. Feasible action family F and cost k

* `F` = fractions of q `{0 ; 0,25 ; 0,5 ; 0,75 ; 1}`, `x = 0` always included;
  policy cap `x_max` applied by `min(x, x_max)` (demo: 100 USDC, FREEZE_V2 §E2) ;
* `k` = explicit costs **not already included** in `P_exec` (fees, gas, bridging, funding) ;
* `P_exec(x)` = average price obtained for size x, taken from the measured depth ladder —
  never a screen price. `Depth_ε` remains **to be measured** (work item W2-B §(f) 5): NOT DONE.

## 4. Personas

* **DAO** — no re-entry during the episode; conditional avoided loss
  `E[perte] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR` (both factors published);
  second reading in **runway days**, `opex_ref = 44 932 $/day` (G6).
* **desk** — re-entry modelled in the same window: `ΔP&L = x·(P_exec − P_T) − k − financement` ;
  Sharpe/Sortino/MaxDD aggregates (R_f = 0 by crypto convention; `None` when not computable).

## 5. The six tests (W2-D §B.6) — must pass before the freeze

| # | Test | Expected |
|---|---|---|
| T1 | Neutrality (P_exec = P_T, k = 0 ⇒ R = 0) | 0 exact (detects the double counting of §B.2) |
| T2 | Translation invariance | R unchanged to 1e-12 |
| T3 | Monotonicity in cost | L and R increasing |
| T4 | Sign consistency (P_exec > P_T) | R(act) = 0, R(do nothing) > 0 |
| T5 | Inventory additivity | linear in q and in x |
| T6 | Degenerate reference (P_t = 1) | all regrets 0 ; useless action = k |

Executable proof: `tests/test_evaluation_loss.py` — sha256
`90b705d0b47551b8deea80c1ab58772746c1599f673d4631888a828fc9b7ba88` ; command
`python -m pytest tests/test_evaluation_loss.py -q` (12 tests).

## 6. What is NOT frozen here (NOT DONE, written as is)

* `Depth_ε` (execution depth in crisis): not measured → x_max cap used and **noted** on every A1 action;
* `r_capital` (desk funding rate): no source — see G6;
* the historical `q(1 − P_T)` bug of the earlier formula (W2-D §B.2) is reproduced in a test for non-regression (displayed gap 20 against real gap 10).

## 7. Revision

Any modification of this file or of `loss.py` after the first EVAL run
**invalidates** the evaluation (parameter embargo, B7 §d.2.1): new dated
version + hash + entry in the variants log.
