> **EVAL** — evaluation report — set `eval` — N = 1 — non-conclusive: N < 100 (B7 §b.3 cascade)

# ORVYREN evaluation report — EVAL

*content hash*: `c143c24316ea990e79484ce24e918f07db1351e4ce0e6b24e13f1928226e4fb8` · *generated*: 2026-10-19T03:00:46Z · *skipped windows*: 1

**Parameters**: q = 100.0 · p_ref = 1.0 · k = 0.0 · B0 draws = 200

> DEV demonstration parameters: q = 100 USDC (mobilisable amount of the dossier), p_ref = 1.0, k = 0 (costs not measured in DEV) — to be frozen for EVAL

## Windows (N = 1)

| Window | Status | L(A0) | L(A1) | L(AX0) | L(A2) | R(A2) |
|---|---|---|---|---|---|---|
| `eval-rseth-2026-04` | SKIPPED | — | — | — | — | — |
| `eval-usd0pp-2025-01` | OK | 6.4420 | 2.1115 | — | — | — |

## Aggregates per config (N displayed per row; R⁻ ≠ R⁺, never averaged together)

| Config | N | mean L | mean R⁺ | mean R⁻ |
|---|---|---|---|---|
| A0 | 1 | 6.4420 | 0.0000 | 0.0000 |
| A1 | 1 | 2.1115 | 4.3305 | 0.0000 |

## Superiority & placebo

- Superiority tests status: **NOT COMPUTED — N < 100 (B7 §b.3 cascade)** — superiority tests (Wilson, exact McNemar, block bootstrap) run only when N ≥ 100 — the status follows the content actually computed; the harness refuses to publish a single aggregate score (B7 §e.5)

## Limits (written before reading)

- No single aggregate score; R⁻/R⁺ regrets published separately (W2-D pitfall #8).
- O = lower bound of the regret (execution at the best observed instant) — not a ground truth.
- DEV substitutions (P_exec = observed price, k = 0, A2 = deterministic dossier) declared in every window.

*Reproducible report: content hash `c143c24316ea990e79484ce24e918f07db1351e4ce0e6b24e13f1928226e4fb8` (real execution fields excluded).*