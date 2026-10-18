# rsETH / KelpDAO 2026-04 — provenance of the case inputs (`measure-2`)

Source note for `fixtures/agents/rseth-2026-04/run_inputs.json`. It records **what
is measured, what is documented, and what is not archived** — the fixture may
only cite what this note actually establishes.

## Documented point values (not a series)

- Oracle valuation retained by the protocol at the exploit instant (2026-04-18
  17:35 UTC): **2 526,76 USD per rsETH**; still **2 513,66 USD** at the freeze
  (19:03:59 UTC, block 24 908 723) and **2 419,21 USD** on 2026-04-20.
- Market price on the window 18–20/04: while the market price dropped to **1 686 USD**, the divergence reached **-31 %** on the window (-32,9 % at the freeze, -30,3 % on 20/04, convention Δ = (market − oracle)/oracle).
- Supply cap saturation at the freeze: **99,999 %** (529 993,98 / 530 000 rsETH).
- Utilisation of the rsETH reserve at the freeze: **≈ 0,008 %** — the
  "100 % utilisation" figure of the earlier briefs is **refuted by measurement**;
  the mechanism was a freeze plus cap saturation, not utilisation.

## Status of each value

| Value | Status | Evidence |
|---|---|---|
| Oracle prices, freeze block, cap saturation | **measured** | `evidence/episode_rseth_2026-04.json` |
| Market price 1 686 USD | **documented, series NOT archived** | this note + gap register G-2 / G-7 |

The market price is a documented point quoted during the episode reconstruction
(2026-10-15 research campaign); **no hourly market series for rsETH was
archived**, so this figure cannot be re-derived from the repository. The run of
2026-04-18 therefore reports it as a *documented* input, never as a measured
series, and the LIVE tools have no rsETH price series to serve — the critic
raises this as a blocking objection, which is the honest behaviour and not a
regression.

## What must not be claimed from this note

- That a realised exit price was observed (the market was frozen: realisable
  value of the affected collateral is **unreadable**, cf. G-7).
- That the −31 % divergence is reproducible offline from a price series (only the
  oracle leg is).
