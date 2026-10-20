# ORVYREN — Jury demo script (10 minutes)

Target: `http://127.0.0.1:8321`, pre-warmed at H-10 (API up, build served,
Live screen fed, graph laid out once, `run_verify.py` dry-run once, scenario
replayed once). **No rebuild after pre-warming.**

| Time | Screen | Content |
|---|---|---|
| 0:00–0:40 | Live | Hook: "Reflexive agents that decide, refuse and abstain — and leave an offline-verifiable proof. 16,174 nodes, 15,000 real on-chain events, 1,549 green tests (measured 2026-10-19), a full agent run for 4 cents." Dashboard already alive (WS, run_id on screen); one line: the hub replays the recording for the booth. |
| 0:40–1:40 | Markets | "The oracle said 2,526.76 USD per rsETH while the market said 1,686: about a third below (the documented figure is −31 %; these two prints imply −33 %). The reserve saturated its cap at 99.999 % (529,993.98 / 530,000 rsETH), then was frozen at block 24,908,723. Documented result: 89,567 rsETH of collateral against ~190M USD borrowed." Say upfront: the market price is a documented figure, not yet an archived series (the system says so itself). Transition: "The question is not prediction — it is what to do when the proof is missing. An agent run, now." |
| 1:40–3:20 | Live + terminal | Run the scenario live. During the ~35 s: narrate the budget — "5 of 30 LLM calls, 1 of 12 tool calls, 34 of 600 wall-seconds, 0.035731 of 0.10 USD — the budget is not decorative, the run stops at its bound." (measured in `evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/run_outcome.json`, `outcome.budget_used`: `llm_calls 5.0`, `tool_calls 1.0`, `wall_seconds 34.422`, `cost_usd 0.035731098`). **Plan B** if a provider error shows: "The LLM provider is down — planned case: deterministic replay, that is a feature" → `python run_agents.py --case usdc-2023-03 --replay journal --session evidence/demo_replay` (~1 s, same hashes). Give the ~60 recovered seconds to the graph and the audit. |
| 3:20–4:20 | Decision | "Result: abstention. ARRET-3, INCONCLUSIVE, escalation REQUIRE_APPROVAL. The critic says INCOHERENTE — it does not decide, it brakes." Show the abstention complement (`evidence/scenario_rseth/decision/abstention_rseth-2026-04.json` → `what_would_change_the_verdict`): 5 research leads (archived rsETH market series; oracle freshness — latestRoundData() reverts on the capped feed; dense cap_ratio window; per-account debt ledger; the missing discriminating rsETH observation). Note for the record: the agents record's own `what_would_change` is **empty** at `ARRET-3` — the leads live in the A1–A5 complement. "HYP-001/002/003 stay INCONCLUSIVE, and the counter-intuitive hypothesis — a liquidity squeeze — is REFUTED by measurement: utilisation 0.008 % at freeze. The hypothesis that should have won lost, against the data." |
| 4:20–5:20 | Graph | "16,174 nodes, 12,937 relations, 15,000 Aave v3 Base events over 30,000 blocks, in WebGL — every query is point-in-time SQL with provenance." Pan/zoom, then Q1 exposure 81.6 ms p50, Q4 PIT 25.3 ms, Q7 concentration 10.6 ms; "the PIT indexes divided Q1 by 11 (−91 %), Q5 by 10 (−90 %)". Honest note immediately: "The 50 MB database is a local artifact with its reconstruction pipeline; a clone holds the versioned 520-observation snapshot. The dashboard states which database it is on." |
| 5:20–6:20 | Decision & Policy | "The policy is outside the LLM, written in YAML, fail-closed. The model proposes, the system decides, the agent never holds the key." Show P1–P14 and the scenario's measured DENY (`NO_ACTIONABLE_INTENT`: the sealed agents record carries no intent, so no policy evaluation happens at all): "this DENY comes from the absence of a decided intent — that is the proof, not a failure. No decided intent, no action." (The `BALANCE_UNREADABLE` / `AGENT_NOT_MEMBER` refusals belong to the separate `run_executor.py` corpus demo, with the policy evaluated and the state unreadable.) And: "the --execute path is preflighted but never exercised by the system; we never show a dry-run as an on-chain proof." |
| 6:20–7:20 | Execution (chained journal) | Show the 7 kinds (INTENT, POLICY, SIMULATION, SUBMIT, RECEIPT, VERIFY, OUTCOME), the shared run_id parented to the agents run, the policy_hash. "13 demo transactions: 1 success, 12 refusals — 12/13 are deliberate reverts (C1/C2/C3a/C3b/C4): we forced the locks and the chain said no, every refusal journalled first-class." **MANDATORY BANNER before any execution journal**: "this tick runs the case's **own** sealed agents decision (`scenario-rseth-2026-04-20261019T134804Z`, built by `decision/agents_source.py`): it carries no intent, so the tick is `NO_ACTION` — 0 policy evaluation, 0 signature, 0 transfer. No pilot substitution. The 13 transactions shown next are the **separate** 16/10 testnet session (1 success, 12 forced reverts)." |
| 7:20–8:40 | Audit | Live: `python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip` → **if, and only if, the rebuilt packet prints `OFFLINE_PASS`**: "OFFLINE_PASS. Third-party verification, without our repository, without our API: hash chains recomputed, 6 of 6 mutations detected. You take the zip, not our word." (**gate: the packet must be rebuilt and re-verified first — the shipped 16/10 packet currently fails A4 with `VERDICT: FAIL — 16 checks, 2 failed`, see the pre-flight below.**) Fallback line: "and the same run replayed bit for bit: 1.09 s, same chain heads." |
| 8:40–9:40 | Honesty | "Three things we will not claim today: (1) the execution tick consumes the agents' **own** decision and that decision carries no intent — so the chain ends `NO_ACTION`, 0 signature, 0 transfer: we show a brake, not an automated action, and we never present the 16/10 testnet transactions as an autonomous one; (2) the agents' financial added value is not measured — benchmark N=12, six runs per mode (3 A0 + 3 A2 on the real episode, 3 A0 + 3 A2 on the **synthetic placebo, which was executed**: the agents abstain 3/3 there), far below the N≥100 threshold: we show an auditable brake, not a yield gain (source: `evidence/benchmark_ab/report.md`); (3) the real --execute path has never been exercised by the system. Everything is in the one-page gaps register." |
| 9:40–10:00 | Close | "ORVYREN in one number: 4 cents for an agent run that abstains honestly — and an offline-verifiable audit packet in one command. The next hours close the gaps register, not the paint." |

**Timing rules.** Total 600 s = 40+60+100+60+60+60+60+80+60+20. If the live run
fails or drags, block 1:40–3:20 goes to replay and the ~60 recovered seconds go
to the graph (4:20) and the audit (7:20) — never improvisation. If a timed
rehearsal exceeds 11 minutes, cut the execution block (6:20–7:20) first.

**Every figure above has a file behind it.** Agent budget:
`evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/run_outcome.json`
(`outcome.budget_used`, `outcome.motif`, `outcome.stop_condition`). Abstention
and its 5 research leads: `evidence/scenario_rseth/scenario_report.md` §decision.
Benchmark: `evidence/benchmark_ab/report.md` (N=12, placebo synthetic and
executed). Graph: the 16,174-node base is a **local artifact outside the
repository**; the shipped scenario queried `evidence/graph.sqlite` (520
observations, schema v2). Test count: `python -m unittest discover -s tests`.

**Pre-flight gate (do not skip).** `python run_verify.py
evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip` must print
`OFFLINE_PASS — 16 checks, 0 failed` before the doors open. Measured
**2026-10-19T13:37Z**: `VERDICT: FAIL — 16 checks, 2 failed`
(`A4.dossier.rerender.md` / `.html` byte mismatch). The packet must be rebuilt
from the current `src/orvyren/audit/dossier.py` before this block is shown; see
`docs/CLOSURE_CHECKLIST.md` item 8.
