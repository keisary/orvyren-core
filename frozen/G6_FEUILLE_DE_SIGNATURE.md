# G6 — Signature sheet for the economic assumptions

**Overall status: SIGNED — validated on 2026-10-19.** 2026-10-16T00:00:00Z.
Protocol: FREEZE_V2 §C7 (« G6 signed by the team lead (default) + published sensitivity »).
Signatory: **AKUE-BITCHI Adote Jovanny** — re-sealed after translation + sensitivity, no parameter changed, before first EVAL — electronic validation by the team lead, explicit authorisation in the Hermes session of 2026-10-19.

Instructions: the signatory ticks each validated parameter, fills in the values
marked `NOT DONE`, dates and signs. The values below are those of the
first EVAL ; any modification after that run requires a named re-signature
and re-labelling.

## Economic assumption parameters

| # | Parameter | Signed value | Source of the proposal | TICK |
|---|---|---|---|---|
| 1 | `opex_ref` (runway days) | 44 932 $/day | ENS IPS 6.46: 16,4 M$/year ÷ 365 (W2-D §A.1.1/E.1) | ☑ validated ☐ modified → …………… |
| 2 | `P(obligation)` — USDC DEV example | 0,20 | working value of W2-D §E.2(b), explicitly unsourced | ☑ validated ☐ modified → …………… |
| 3 | `P(obligation)` — per EVAL window | **0,20 per EVAL window** | no public source (W2-D §Non trouvé 6) ; signed working assumption | ☑ provided below |
| 4 | Desk scenarios (list) | realized · no re-establishment 48 h · slow healing 5 d · single constrained venue 0,80526 | W2-D §(f) 7 | ☑ validated ☐ modified → …………… |
| 5 | `p_s` (scenario probabilities) | **0,25 / 0,25 / 0,25 / 0,25** | no public distribution (W2-D §Non trouvé 4) ; signed uniform prior | ☑ provided below |
| 6 | `r_capital` (desk funding) | **0 %** (cash) | B7 Q16 — no source ; cash base without funding | ☑ provided below |
| 7 | Round-trip cost (desk illustration) | 20 bp | W2-D §E.3 (« hypothetical, to be measured ») | ☑ validated ☐ modified → …………… |

## Values to provide (where applicable)

* `P(obligation)` per EVAL window (written justification per window): **0,20 for each
  EVAL window** — unsourced working assumption, identical to the DEV value ; no
  public frequency of forced sales exists. The `P*` sensitivity is published with the P&L.
* `p_s` of the desk scenarios (with sensitivity): **0,25 / 0,25 / 0,25 / 0,25** — explicitly
  uncalibrated uniform prior ; sensitivity published with the P&L and the report.
* `r_capital` (source or written assumption): **0 %** — desk funded in cash, without funding ;
  the 5 % and 10 % sensitivity variants are published with the P&L.

## Signatures

| Role | Name | Date (UTC) | Signature / hash of the signing commit |
|---|---|---|---|
| Team lead (default, FREEZE_V2 §C7) | AKUE-BITCHI Adote Jovanny | 2026-10-19 | re-sealed after translation + sensitivity, no parameter changed, before first EVAL — electronic validation by the team lead, explicit authorisation in the Hermes session of 2026-10-19 |
| Witness (optional) | | | |

**Embargo reminder**: after the first EVAL run, any modification of these
parameters **invalidates** the evaluation (re-labelling mandatory) — it does not "weaken" it (B7 §d.2.1).
