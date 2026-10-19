# G6 — Economic assumptions (freeze v1, status SIGNED)

**Status: SIGNED — electronic validation by the team lead on 2026-10-19.** 2026-10-16T00:00:00Z.
Signatory: **AKUE-BITCHI Adote Jovanny** — re-sealed after translation + sensitivity, no parameter changed, before first EVAL — electronic validation by the team lead, explicit authorisation in the Hermes session of 2026-10-19. The sheet
`G6_FEUILLE_DE_SIGNATURE.md` carries the validation ; the values below are
those on which the first EVAL runs.
Sources: W2-D §B.3/B.4, §E.2, §(f) 1–7 and 11–12 ; B7 §b.5, §e.3/e.4, Q1 ; FREEZE_V2 §C7.

## 1. Signed parameters and values

| Parameter | Signed value | Status | Source / justification |
|---|---|---|---|
| `opex_ref` (runway days) | **44 932 $/day** | VALIDATED (declared external reference) | ENS IPS 6.46: 16,4 M$/year of 2025 expenses ; computed conversion 16 400 000 ÷ 365 (W2-D §A.1.1, §E.1 ; B7 Q13) |
| `P(obligation)` — USDC DEV window (calculation example) | **0,20** | VALIDATED (unsourced assumption) | working value of W2-D §E.2(b) — « an assumption to be frozen, unsourced » ; no public frequency of forced sales exists |
| `P(obligation)` — EVAL windows | **0,20 per EVAL window** | SIGNED — unsourced working assumption | no public source (W2-D §Non trouvé 6) ; DEV value kept for all EVAL windows, with written justification and published `P*` sensitivity |
| desk scenarios `p_s` | **4 scenarios**: (i) realized, (ii) no re-establishment at 48 h, (iii) slow healing (5 d), (iv) single constrained venue (0,80526 — counterfactual) ; **p_s = 0,25 / 0,25 / 0,25 / 0,25** | SIGNED — list and uniform prior not calibrated | W2-D §(f) 7 ; no public distribution of depeg scenarios (W2-D §Non trouvé 4): the `p_s` are signed assumptions, published with the P&L and their sensitivity |
| `r_capital` (desk funding rate) | **0 %** (desk funded in cash) | SIGNED — working assumption | no source found (B7 Q16) ; "cash without funding" base, 5 % and 10 % sensitivities published with the P&L |
| desk round-trip cost (illustrative) | 20 bp (`k = 4 000 $` on 2 M$) | VALIDATED (illustration) | W2-D §E.3 — « hypothetical, to be measured for real » |

## 2. Attached rules (frozen)

* avoided loss is **never** published unconditionally:
  `E[perte évitée] = P(oblig) · (perte | oblig) − (1 − P(oblig)) · coût_AR`, both factors visible ;
* any modification of `P(obligation)`, of the `p_s` or of `r_capital` requires a **named re-signature**
  + justification + published sensitivity (B7 §f.2) ;
* a forecast `p` can **never** be produced by an LLM (forbidden by construction, B7 §a.5.5).

## 3. Required sensitivity

For every window where `P(obligation)` enters a verdict, publish the sensitivity of the
sign of `E[perte évitée]` to `P(obligation)`: the switch value is exactly computable
(`P* = coût_AR / (perte|oblig + coût_AR)`) — it must appear in the dossier.

## 4. Signature

Validated by **AKUE-BITCHI Adote Jovanny** on **2026-10-19** — re-sealed after translation + sensitivity, no parameter changed, before first EVAL — electronic validation by the team lead, explicit authorisation in the Hermes session of 2026-10-19.
A scanned handwritten copy may be attached to the submission ; the reference
electronic validation is this document and `G6_FEUILLE_DE_SIGNATURE.md`.
