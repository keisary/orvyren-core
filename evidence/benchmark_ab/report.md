# ORVYREN mini-benchmark — A0 (deterministic engine) vs A2 (full agents)

> **small-N diagnostic run — no superiority claim (G1 threshold N>=100 not reached)**

- run_id: `bench-20261018T133447594030Z-bf2c060b6a80`
- N scored runs: **12** (total runs: 12)
- modes: A0, A2 — same episodes, same declared budgets
- declared budget (identical for both modes): {"cost_usd": 0.1, "llm_calls": 30, "note": "Identical declared caps for both modes and every run. These are the caps the recorded A2 replay store was recorded under (fixtures/agents/usdc-2023-03 run budget, run_agents.py A5 frozen ceilings) \u2014 a replay under different caps fails cleanly (E_LLM_NOT_RECORDED -> ARRET-3 abstention) instead of improvising. A0 is deterministic and consumes none of them (0 by construction).", "tool_calls": 12, "wall_seconds": 600}

## Verdict mapping (read this before the table)

- **A0** — decision verdict of run_decision.py crossed with the authorization axis when evaluated (ACTION_RECOMMENDED -> ALLOW unless the axis says DENY/REQUIRE_APPROVAL; NO_ACTION -> NO_ACTION; INCONCLUSIVE -> abstention)
- **A2** — fragility gate of run_agents.py (run_outcome.json): inconclusive -> abstention; FRAGILE/INCOHERENTE escalation -> REQUIRE_APPROVAL; otherwise the agent layer did not brake -> ALLOW. ALLOW here is NOT a policy authorization and NOT an executed action.

## Comparative table

| case | synthetic | mode | N runs | verdicts (counts) | match | miss | other | abstentions | cost USD (total) | latency s (mean) | LLM calls | tool calls | claims rejected (provenance) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| usdc-2023-03 | no | A0 | 3 | ALLOW:3 | 3 | 0 | 0 | 0 | 0.0000 | 0.4687 | 0.0000 | 0.0000 | 0 |
| usdc-2023-03 | no | A2 | 3 | REQUIRE_APPROVAL:3 | 3 | 0 | 0 | 0 | 0.0055 | 1.0470 | 15.0000 | 6.0000 | 0 |
| placebo-calm-2023-03 | yes | A0 | 3 | NO_ACTION:3 | 3 | 0 | 0 | 0 | 0.0000 | 0.2760 | 0.0000 | 0.0000 | 0 |
| placebo-calm-2023-03 | yes | A2 | 3 | abstention:3 | 3 | 0 | 0 | 3 | 0.0055 | 1.0623 | 15.0000 | 6.0000 | 6 |

N per mode — A0: 6 scored / 6 runs · A2: 6 scored / 6 runs.

## Per-case reading (declared expectations, measured outcomes)

### usdc-2023-03

- declared: The 2023-03 USDC depeg is a documented, archived episode: venue minima 0.80526-0.882 USD on 2023-03-11 and an inter-venue dispersion of 870.07 bps (sources listed per row above). A mode that concludes a flat NO_ACTION (nothing happened) misses a documented event.
- acceptable calls: ALLOW, REQUIRE_APPROVAL, abstention · wrong calls: NO_ACTION
- declared agent expectation: The archived A2 replay critiques the evidence as FRAGILE (source-dependence of the aggregators) and escalates to REQUIRE_APPROVAL while listing what was NOT searched (executability depth). The expected agent-layer contribution is an auditable brake + provenance ledger, not a different decision. This expectation is declared from the archived recording (fixtures/agents/usdc-2023-03 + recorded store), not invented for the benchmark.
- measured delta: `agents_abstain_where_engine_acts` — the agent layer brakes/abstains while the engine recommends acting

### placebo-calm-2023-03 — SYNTHETIC PLACEBO (fabricated, not real data)

- declared: No signal exists in this series by construction. A mode that finds a decisive depeg, a source contradiction or an artifact here is hallucinating: the only right calls are NO_ACTION or a justified abstention. Any decisive call — or an escalation demanding human review of nothing — is a false positive and is scored as a miss.
- acceptable calls: NO_ACTION, abstention · wrong calls: ALLOW, DENY, REQUIRE_APPROVAL
- declared agent expectation: The agents must find nothing decisive on a calm case and abstain or conclude nothing (ARRET / no-action). MEASURED 2026-10-18 on the seeded store: 3/3 runs abstain (inconclusive, ARRET-1) — the provenance gate rejects the scripted claims citing unobserved references (E_REF_NOT_OBSERVED, visible journal lines) and no admissible evidence remains, so the forced-abstention rule fires. A decisive verdict here would be a negative result for the agents.
- measured delta: `different_calls` — the two modes disagree on this case — the declaration ranks neither (N too small)

## When the agents help / add nothing / must abstain

### When the agents help

- measured: **none** in this sample (N=12). No case shows the agent layer matching the declared expectation where the engine missed it.
- measured: usdc-2023-03 — the agent layer brakes/abstains where the engine recommends acting. This is a difference in caution (audit trail, escalation, what was NOT searched); it is NOT ranked as better — the declared expectation accepts both calls.

### When the agents add nothing — or degrade

- add nothing: none measured in this sample.
- degrade: none measured in this sample.
- disagree without a declared winner: placebo-calm-2023-03 (the declaration ranks neither).

### When the agents must abstain

- declared rule (B1 §5.3): a FRAGILE/INCOHERENTE reading never cancels — it brakes towards REQUIRE_APPROVAL / abstention. On a no-signal (placebo) case the agents must find nothing decisive and abstain or conclude nothing.
- measured: abstained or not executed (declared as missing) on: placebo-calm-2023-03

## Raw runs

| run_id | case | mode | run | status | verdict | quality | abstained | cost USD | latency s | LLM | tools | claims rejected |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `bench-20261018T133439305294Z-a8c226a64e63` | usdc-2023-03 | A0 | 1 | ok | ALLOW | match | False | 0.0000 | 0.4690 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133440361432Z-c38efee98e73` | usdc-2023-03 | A2 | 1 | ok | REQUIRE_APPROVAL | match | False | 0.0018 | 1.0470 | 5.0000 | 2.0000 | 0 |
| `bench-20261018T133440808717Z-a6026f26d042` | usdc-2023-03 | A0 | 2 | ok | ALLOW | match | False | 0.0000 | 0.4370 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133441863404Z-87d042814096` | usdc-2023-03 | A2 | 2 | ok | REQUIRE_APPROVAL | match | False | 0.0018 | 1.0470 | 5.0000 | 2.0000 | 0 |
| `bench-20261018T133442373405Z-a8aa050e24fa` | usdc-2023-03 | A0 | 3 | ok | ALLOW | match | False | 0.0000 | 0.5000 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133443441203Z-88fbff0ec52e` | usdc-2023-03 | A2 | 3 | ok | REQUIRE_APPROVAL | match | False | 0.0018 | 1.0470 | 5.0000 | 2.0000 | 0 |
| `bench-20261018T133443743597Z-bca2d9584ccf` | placebo-calm-2023-03 | A0 | 1 | ok | NO_ACTION | match | False | 0.0000 | 0.2660 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133444879387Z-179e6d71048d` | placebo-calm-2023-03 | A2 | 1 | ok | abstention | match | True | 0.0018 | 1.1250 | 5.0000 | 2.0000 | 2 |
| `bench-20261018T133445189338Z-10af6af3341a` | placebo-calm-2023-03 | A0 | 2 | ok | NO_ACTION | match | False | 0.0000 | 0.2810 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133446257219Z-f0203c3f1ef5` | placebo-calm-2023-03 | A2 | 2 | ok | abstention | match | True | 0.0018 | 1.0470 | 5.0000 | 2.0000 | 2 |
| `bench-20261018T133446570024Z-ac622a4592ec` | placebo-calm-2023-03 | A0 | 3 | ok | NO_ACTION | match | False | 0.0000 | 0.2810 | 0.0000 | 0.0000 | 0 |
| `bench-20261018T133447594030Z-551d43971e73` | placebo-calm-2023-03 | A2 | 3 | ok | abstention | match | True | 0.0018 | 1.0150 | 5.0000 | 2.0000 | 2 |

## Superiority

- N=12 · G1 threshold N>=100 · claimable: no
- refused: N=12 < 100 (G1 threshold) — no superiority claim is made or implied anywhere in this report

## Limitations

- N=12 scored run(s) — far below the G1 superiority threshold (N>=100); no ranking of A0 vs A2 is claimed or implied.
- Journal-mode A2 runs are deterministic offline replays of recorded responses (pinned run_id): repeated runs demonstrate replay determinism, NOT independent samples. N counts runs and must not be read as independent evidence.
- A2 cost/latency figures are the recorded per-call spend of the replay (real recorded cost) plus harness-measured wall time; A0 is deterministic and spends nothing (0 by construction).
- The RDOF/axes enrichment of run_decision.py is scoped to case 'usdc-2023-03'; other case ids run the v0 deterministic engine (--no-rdof) — a declared substitution, recorded per run.

