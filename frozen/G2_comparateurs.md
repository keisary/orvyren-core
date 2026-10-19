# G2 — Comparators (freeze v1)

**Status: FROZEN v1** — 2026-10-16T00:00:00Z. Sources: B7 §e.1 (table + resolved
label collision), W2-D §C.1. Frozen code: `src/orvyren/evaluation/comparators.py` —
sha256 `23ac4438bdbeacfefe689a2bbdf144d4cf4b06ad2b778e59d8d212a8d5d345b3`.

## 1. Frozen labels (the R3/W2-D collision is resolved)

| Code | System | Operational definition | Cost |
|---|---|---|---|
| **A0** | NO-ACTION | do nothing over the whole window | 0 |
| **A1** | Threshold rule | discount D ≥ 50 bp for 15 min → bounded reduction x* = min(x_max, Depth_ε, x_seuil) | ~0 |
| **A2** | ORVYREN agent | corpus → graph → hypotheses → branch → critique → bounded policy (journal replay otherwise archive k=3) | capped, measured |
| **B0** | Matched placebo | same number and sizes of actions as A2, timestamps drawn uniformly over the hourly grid, M ≥ 200, fixed seed | ~0 |
| **AX0** | Frozen repository rule (ex-R3 "A0") | 0,99 × 2 consecutive obs → 100 USDC reduction ; delegated to `decision/baseline.py` | ~0 |
| **O** | Ex post feasible oracle | `min_{b ∈ F} L(b)` with the frozen loss function — lower bound of the regret, not ground truth | offline |

The frozen repository rule is written **AX0** in every competition report (the label
"A0-code" is forbidden: without that resolution, "A0 did better than A0" was written).

## 2. Frozen parameters

* A1: `min_discount_bp = 50`, `persistence_minutes = 15` (i.e. on the hourly grid, **two
  consecutive readings**, gap ≤ 90 min ; one episode = a single trigger) ;
* B0: `seed = 20261016`, `M ≥ 200`, hourly grid, draws **reproducible** (same seed → same timestamps) ;
* demo action cap `x_max = 100 USDC` (FREEZE_V2 §E2 ; taken from
  `evidence/decision_usdc-2023-03.json`).

## 3. Pre-written sentences (frozen BEFORE execution, B7 §e.1)

> If A2 does not beat B0, the value of the system is not in the **choice of timing** — written as is.
>
> If A2 does not beat A1, the value of the system is not in the **deliberation** — written as is.

## 4. Executable verifications

`tests/test_evaluation_comparators.py` — sha256
`0c4c9e3d4203b82d0950ca37f55b1bb8293466544be00e065a6d07e132653a05` :
A0 = 0 action ; A1 triggers/single-signal/gap breaks contiguity ; **AX0 reproduces
`evidence/baseline_report.json`** (2 signals main window, 0 on the control window) ;
B0 reproducible and M ≥ 200 required ; oracle = member of F.

## 5. NOT DONE

* A2: code produced by blocks A–E (agents, graph, policy) — outside Sprint 0 ; team API
  keys remain a blocker for `REPLAY-ARCHIVE` mode (B7 §0.11) ;
* `Depth_ε` and `x_seuil` of A1: not measured → x_max cap, substitution note on every action.
