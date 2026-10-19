# G4 — Per-persona thresholds (freeze v1, status VALIDATED)

**Status: VALIDATED — electronic validation by the team lead on 2026-10-19.** 2026-10-16T00:00:00Z.
Signatory: **AKUE-BITCHI Adote Jovanny** — re-sealed after translation + sensitivity, no parameter changed, before first EVAL — electronic validation by the team lead, explicit authorisation in the Hermes session of 2026-10-19. Sources: W2-D §C.4.1 (DAO), §C.4.2 (desk),
B7 §e.3/e.4 (metrics). The values below are **taken as is**
from the source documents and **validated**; they are not measured facts.

## 1. DAO persona (treasury)

| Code | Criterion | Formulation | Validated value |
|---|---|---|---|
| SD1 | Material avoided loss | `(L(A0) − L(A2)) / q` in % of the exposure, conditional on the obligation ; second display in runway days | ≥ 5 % |
| SD2 | Controlled friction | cumulative cost of A2 over CALM windows | ≤ 10 % of the crisis avoided loss |
| SD3 | Anticipation | lead time vs the low point of the realizable price ; reaction delay | ≥ 6 h on ≥ 1 EVAL episode ; ≤ 60 min |
| SD4 | Superiority | `R̄(A2) < R̄(A1)` and `< R̄(B0)`, with intervals, R⁻/R⁺ separate | strictly lower |
| SD5 | Traceability | provenance + hash on 100 % of actions ; 0 action outside the envelope | 100 % / 0 |
| SD6 | Honesty | "non-conclusive" everywhere power is missing ; avoided loss published as `P × conditionnel` | present/absent |

## 2. desk persona (P&L)

| Code | Criterion | Formulation | Validated value |
|---|---|---|---|
| ST1 | Cumulative net P&L | all costs included (fees, measured slippage, funding) + block bootstrap interval | > 0 |
| ST2 | Execution quality | realized slippage vs the `get_dy` ladder ; size ≤ Depth_100bp | ≤ 30 bp in stress |
| ST3 | Bounded risk | MaxDD of the decision series over the allocated capital | ≤ 20 % per episode |
| ST4 | Risk-adjusted | Sharpe/Sortino + DSR corrected for the number of variants | CI lower bound > 0 otherwise "non-conclusive" |
| ST5 | Superiority | `ΔP&L(A2) > ΔP&L(A1)` and `> ΔP&L(B0)` with intervals | strictly greater |
| ST6 | Declared asymmetry | agent described as a put ; `p_s` scenarios published | present/absent |

## 3. Common anti-optimism (mandatory devices)

B0 (M ≥ 200, full distribution) · CALM windows mandatory in both sets ·
`ȳ` published everywhere · Wilson on every proportion · block bootstrap (6–12 h, 10 000
replications, fixed seed) · DSR/variants log · separate R⁻/R⁺ + contingency table ·
contamination mention · "what we do not claim" ·
**a single scalar is forbidden** (metric vector + declared unmeasured axes).

## 4. Executable verification to come

The SD/ST thresholds are **not yet read by code** (harness §e.6 items 6–7 are not
built): this document freezes them as a **validated** declaration, the executable
verification will come with `harness.py`. Any modification after the first EVAL run
invalidates the evaluation (parameter embargo).
