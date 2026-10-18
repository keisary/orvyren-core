# ORVYREN — Submission Scope and Gaps Register

**Authority.** For the 2026-10-20 submission, THIS document defines what is
actually delivered. Other documents rank as follows:

| Document | Role |
|---|---|
| `docs/SUBMISSION_SCOPE_AND_GAPS.md` (this file) | Delivered scope + open gaps — the single scope authority |
| `FREEZE_V2.md` | Frozen v1 contract decisions (46 decisions) |
| `frozen/G1..G6` + `scripts/verify_frozen.py` | Frozen evaluation protocol (byte-identical recalculation, `COMPLIANT`) |
| `docs/CODE_REVIEW_2026-10-17.md`, `docs/CODE_REVIEW_SUBAGENTS_2026-10-18.md` | Review records (findings + fixes) |
| `docs/AUDIT_CONSOLIDE_2026-10-18.md` | External audit + correction plan (source material — not a claim) |
| `ORVYREN_DOC1..DOC4` | Product/technical narrative (French); where a figure and a measurement disagree, the measurement wins and the docs are reconciled |

Not delivered, not claimed: anything listed in the gap register below.
Research reports are research, not capability.

## Delivered (each with its executable proof)

All figures measured at commit `b8f8bd3` (2026-10-18); re-measure with the
commands below before quoting anywhere else.

1. **Provenance-gated agent reasoning (P0-6).** A claim may only cite
   references the run really observed; invented references are rejected
   (visible journal line) and never reach the critic packet.
   Proof: `python -m unittest tests.test_agents_provenance_bounds tests.test_agents_review_fixes`.
2. **Unified LIVE/REPLAY/FIXTURE tool registry on the real graph (P0-1).**
   LIVE interrogates the graph API with its arguments (Q1–Q8), reads measured
   corpus series and archived documents; REPLAY serves recorded responses
   bit-identical (miss = `E_TOOL_NOT_RECORDED`); FIXTURE is the labelled
   simulation. Proof: `python -m unittest tests.test_agents_tool_modes`.
3. **Reflexive ACH reasoning.** Competing hypotheses (incl. one
   counter-intuitive), COHERENT/INCOHERENT/NEUTRE evidence matrix, diagnosticity
   weighting, refutation-first ranking, next discriminating test, change
   reactions (retest/revise/escalate — a dominant flip is never silent).
   Built in code from the agents' own claims; no LLM payload or prompt changed,
   replay preserved. Proof: `python -m unittest tests.test_agents_reflexion`.
4. **Shared run_id chain (P0-2).** Hash-chained events + per-artifact sha256
   manifest verified at every decision→policy→execution handoff; `parent_run_id`
   for re-runs; real execution refused without an explicit run_id.
   Proof: `python -m unittest tests.test_chain_run_id`.
5. **Fail-closed policy with explicit modes (P1-3).** Production default:
   no state → `STATE_REQUIRED` DENY (state rules never `SKIPPED`);
   simulation must be declared. Proof: `python -m unittest tests.test_policy`.
6. **Point-in-time correctness (P1-2).** Q5 admissibility on both clocks
   (`event_time` AND `observation_time`); aware-UTC instant comparisons
   (julianday) instead of lexicographic text. Proof:
   `python -m unittest tests.test_graph_pit_fixes`.
7. **Tool execution bounds (P1-1).** `deadline_s` enforced (monotone), negative
   `limit`/`max_depth` refused (`LIMIT -1` = unbounded in SQLite), ceilings
   imposed by code. Proof: `python -m unittest tests.test_agents_provenance_bounds`.
8. **Evaluation protocol hardening (P1-5).** G5 cascade gates published
   content (label/content divergence refused); the freeze gate really verifies
   the code hashes announced in the Gx documents; calibration embargo is
   mandatory. Proof: `python -m unittest tests.test_evaluation_protocol`;
   `python scripts/verify_frozen.py` → `COMPLIANT`.
9. **Live E2E scenario, rsETH/KelpDAO 2026-04.** Executed live (real LLM,
   sealed store): agents abstain on ARRET-3, critic INCOHERENTE (12 objections)
   → REQUIRE_APPROVAL, counter-intuitive hypothesis refuted by measured data,
   honest abstention with `what_would_change`, dry-run execution chained to the
   agents run_id, policy DENY fail-closed, zero signed.
   Proof: `evidence/scenario_rseth/scenario_report.md` (raw step outputs included).
10. **Honest A0-vs-A2 benchmark.** Small-N banner mandatory, superiority
    wording refused below N≥100, failures as visible as successes, placebo
    labelled synthetic. Proof: `evidence/benchmark_ab/report.md`,
    `python -m unittest tests.test_benchmark_ab`.
11. **Real SPA dashboard + API.** Five screens on real system state (live runs
    over WebSocket, WebGL graph on 16,174 nodes with Q1–Q8 panel, stress-episode
    charts, decision/policy/execution views, audit chains recomputed), offline
    build served by FastAPI, zero external resources.
    Proof: `python -m unittest discover -s tests -p "test_api*.py"`;
    `cd frontend && npm run build`.
12. **Measured performance work.** PIT indexes (Q1 −91 %, Q5 −90 % on the real
    DB), gzip + ETag/304, WS compression pinned, Sigma tuning, lazy chunks.
    Proof: `tests/test_graph_pit_fixes.py::PitIndexContractTest`.
13. **Test suite.** `python -m unittest discover -s tests -q` → `Ran 1411
    tests ... OK (skipped=3)` at `b8f8bd3`; the 3 skips are documented (testnet
    RPC gate ×2, eth-account absent path ×1).

## Gap register (open — not claimed, not hidden)

| # | Gap | Status | Where |
|---|---|---|---|
| G-1 | EVAL decision-gain sample N=0 (no superiority claim anywhere) | Open, by design until N≥100 | `evidence/evaluation/`, benchmark banner |
| G-2 | Live corpus has no rsETH price series — live tools served other assets' rows on the scenario (critic BLOQUANT) | Open | `evidence/scenario_rseth/scenario_report.md` |
| G-3 | No recorded response store for `rseth-2026-04` — offline journal replay of that case unavailable until one is recorded (never simulated) | Open | scenario report |
| G-4 | Q2 dependency paths return `NO_PATH` on the Aave slice (no `DEPENDS_ON`/`AFFECTS` edges populated); Q8 permissions `NOT_INGESTED` (no Safe/Zodiac data in slice) | Open, honest outputs | `evidence/` run reports |
| G-5 | Two tautological assertions in hash-frozen test files (`test_evaluation_loss.py:106`, `test_evaluation_calibration.py:97`) — **FIXED + RE-SEALED 2026-10-18** with a visible G1/G5 re-seal (measured identities replace the tautologies; hashes recalculated via `freeze_sprint0.py`; `verify_frozen.py` COMPLIANT; suite green; dedicated commit) | Closed | `docs/ECARTS_REGISTRE.md` TH-1/TH-2 |
| G-6 | The sealed seed's recorded critic cites a reference absent from its packet — a strict critic-side ref gate would need a visible store re-seed | Open | `review/agents_chain.md` §non corrigé |
| G-7 | Scenario lacunae L-1..L-4 (market/exit series unarchived, oracle freshness unverifiable on the capped feed, per-account bad-debt ledger out of the data layer, realisable value of frozen collateral unreadable) | Open | scenario report |
| G-8 | Contract questions for owners: `queries.q7 debt_backed` asset filter inconsistency (pinned figure), `comparators.a1_signal_times` trigger granularity (G2-hash frozen) | Open | `review/graph_eval_bench.md` |
| G-9 | Benchmark N small (1 real episode + 1 synthetic placebo) — diagnostic only | Open, banner enforced | `evidence/benchmark_ab/report.md` |
| G-10 | Deferred optimizations (prompt prefix ordering, parallel tool-calls, journal block hashing, WS backpressure, LLM streaming) | Deliberately deferred | `research/optimization_scalability.md` |
| G-11 | mypy backlog (inherited `Optional` annotations) and non-fatal Bandit findings | Accepted debt | review record |
| G-12 | The `--execute` real path is preflighted but never exercised end to end by the system itself (dry-run everywhere; the T2 transactions were signed by a human key). Two readings are shown side by side: no env → DENY fail-closed (the safety proof) and `--demo-defaults` → policy mechanism, never safety | Open | `run_executor.py`, `docs/DEMO_KIT.md` |
| G-13 | The scenario's execution leg replays the **pilot USDC decision** under the rsETH run_id (declared substitution — the rsETH conclusion is the agents' abstention); the rsETH case probe is refused `E_WHAT_WOULD_CHANGE_REQUIRED` and kept as evidence | Open, banner enforced in UI and runbook | `evidence/scenario_rseth/` |
| G-14 | The live scenario agents interrogated `evidence/graph.sqlite` (520 obs, schema v2); the 16,174-node v3 database is a local artifact with a reconstruction pipeline, not in the repository | Open, declared | `docs/RUNBOOK_DEMO.md` §4 |
| G-15 | `queries.q7 debt_backed` sums all visible `OWES` rows without an asset filter (contract figure pinned by tests) — never present it as an exposure metric; the filtered measure is `graph/api.concentration` | Open | `review/graph_eval_bench.md` |
| G-16 | Published `evidence/evaluation/` report predates the R−/R+ aggregation fix (it shows R− = 0.0000 from the old formula) — **annotated** in `evidence/evaluation/SUPERSEDED_NOTE.md`, artifacts left byte-identical (G6 signed embargo + `variants.log` hash) | Annotated, regeneration deferred | `evidence/evaluation/SUPERSEDED_NOTE.md` |
| G-17 | `dist/docs/*.docx` are dated builds (2026-10-17) of the `.md` sources, shipped in the submission bundle (gitignored, not tracked): their test counters were refreshed surgically on 2026-10-18 (3 replacements, layout preserved); other text may lag its `.md` — the `.md` files and the README counter are the live source | Declared | this register |
