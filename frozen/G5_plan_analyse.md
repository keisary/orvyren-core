# G5 — Analysis plan (freeze v1)

**Status: FROZEN v1** — 2026-10-16T00:00:00Z. Sources: B7 §b.1–b.4, §e.2–e.5, DOC2 §5.8.2.
Frozen code: `calibration.py` sha256
`51f42db1dcfff81dd5fe81e5115c7344f52c84f5c3880d5340a9a48d2a536722`,
`forecasts.py` sha256 `8a519087d7c29aa1289d80e59e3d0da886a403d7a581273624ab301f72d19d33`,
`outcomes.py` sha256 `4ad4db541badefdd6efba6749ad2b71ebf657a66bc35aadd9c0c19a2ac2cfb94`.

## 1. Published metrics (C1–C7) and formulas

| Code | Metric | Formula |
|---|---|---|
| C1 | Brier score | `BS = (1/N) Σ (p_t − y_t)²` |
| C2 | Murphy decomposition | `BS = REL − RES + UNC`, evaluated on the **same bins as the ECE** (exact identity, tested) |
| C3 | ECE | `Σ_b (n_b/N)·|acc_b − conf_b|`, **10 fixed bins** `[b/10, (b+1)/10)`, frozen in advance |
| C4 | Reliability curve | per bin: `n_b`, `conf_b`, `acc_b`, Wilson CI (empty bins displayed) |
| C5 | Wilson | `z = 1,959964` ; upper bound of 0/n = `z²/(n+z²)` |
| C6 | Block bootstrap | circular, 6–12 h blocks, 10 000 replications, **fixed seed** (20261016), percentile 2,5–97,5 |
| C7 | Skill | `BSS = 1 − BS / (ȳ(1−ȳ))` ; `None` if the climatology is degenerate |

KAT vector (reference unit test, tolerance 1e-12): `p = [0,2×5 ; 0,8×5]`,
`y = [0,0,0,0,0, 1,1,0,1,1]` → BS 0,100 ; REL 0,020 ; RES 0,160 ; UNC 0,240 ; ECE 0,100 ; ȳ 0,400.

## 2. Cascade "when may we say calibrated" (applied mechanically)

| N (resolved frozen forecasts) | What is published | Label |
|---|---|---|
| N < 5 | nothing | "NOT COMPUTED — insufficient N" (D11 threshold) |
| 5 ≤ N < 30 | BS, REL, RES, UNC, ȳ, list ; ECE **without** any claim | "non-conclusive" |
| 30 ≤ N < 100 | + bootstrap CI, reliability curve + Wilson per bin | "non-conclusive" |
| N ≥ 100 | everything + BSS with lower bound | claim possible **under the 5 conditions** |

**The 5 conditions to write "calibrated"**: N ≥ 100 out of sample ; ECE ≤ 0,05 with CI
upper bound ≤ 0,08 ; no systematic deviation (sign test, `max_b |acc_b − conf_b| ≤ 0,10`) ;
BSS CI lower bound > 0 ; ≥ 2 disjoint episode families + declaration of non-tuning.
With N = 5–12, the default state is "non-conclusive" — **published as is**.

## 3. Comparison statistics

* Wilson on **all** proportions ; mandatory sentence for a "0 failure":
  « 0/6 ne signifie pas taux nul, mais taux compatible avec jusqu'à ≈ 39 % (borne supérieure de Wilson) » ;
* McNemar **exact** on discordant pairs (`p = 2·Σ C(n,k)/2^n`, bounded at 1 ; KAT 6-0 → 0,03125) ;
* block bootstrap (C6) on every series statistic — never i.i.d. CIs ;
* B0 placebo: full distribution + A2 percentile.

## 4. Imposed report structure (B7 §b.4, 8 sections)

1. scope and hashes (set, episodes, N, period, code_hash, data_hash, list of forecast_id) ;
2. global table (N, ȳ, BS + CI, REL/RES/UNC, ECE, BSS, verdict) ;
3. reliability curve (one line per bin) ;
4. decomposition by family (persona, type, episode — **N displayed per cell**) ;
5. forecast appendix (`forecast_id | p | y | (p−y)² | horizon | resolver`) ;
6. anomalies and corrections (`supersedes`, unresolved, quarantines) ;
7. limitations spelled out (contamination, non-exchangeability, sample sizes) ;
8. verdict in controlled language (never "calibrated" without the 5 conditions).

## 5. Frozen language rules

Every table carries its `N` and its validity ; never merge DEV and EVAL ; never
average R⁻ and R⁺ ; no single aggregate score ; a report without a hash is not verifiable ;
"calibrated" is a controlled word (5 conditions), below that it is "not established".

## 6. Executable verifications

`tests/test_evaluation_calibration.py` — sha256
`2e1b00644b7e9a60485ad1564d5af52829b703c0ad96d50dc8b66a1262af940d` : exact KATs,
Wilson vs raw_b7 table (± 0,001), deterministic bootstrap (2 identical runs), cascade.
