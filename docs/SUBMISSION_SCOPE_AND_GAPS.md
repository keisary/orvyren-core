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
| the v1 design notes | Archived out of the repository (2026-10-18); a figure that disagrees with a measurement is corrected in the measurement’s favour |

Not delivered, not claimed: anything listed in the gap register below.
Research reports are research, not capability.

## Delivered (each with its executable proof)

All figures measured at commit `b8f8bd3` (2026-10-18); the test counter and the
EVAL report were re-measured on 2026-10-19 (dates given on each line). Re-measure
with the commands below before quoting anywhere else.

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
   sealed store): agents abstain on ARRET-3, critic INCOHERENTE (10 findings)
   → REQUIRE_APPROVAL; the execution leg consumes **the DecisionRecord built
   from that very run** (`orvyren.decision.agents_source`), which carries no
   intent → `NO_ACTION`, no policy evaluation, zero signed. The
   counter-intuitive competitor is refuted in the A1-A5 complement by the
   measured utilisation; `what_would_change` is listed there (the run's own
   `non_recherche` is empty at ARRET-3, declared as a gap). Chain verified end
   to end (`chain_verification.json`, 9/9 checks, `PASS`), run_id
   `scenario-rseth-2026-04-20261019T134804Z`.
   Proof: `evidence/scenario_rseth/scenario_report.md` (raw step outputs included).
10. **Honest A0-vs-A2 benchmark.** Small-N banner mandatory, superiority
    wording refused below N≥100, failures as visible as successes, placebo
    labelled synthetic. Proof: `evidence/benchmark_ab/report.md`,
    `python -m unittest tests.test_benchmark_ab`.
11. **Real SPA dashboard + API.** Five screens on real system state (live runs
    over WebSocket, WebGL graph on 16,174 nodes with Q1–Q8 panel, stress-episode
    charts, decision/policy/execution views, audit chains recomputed), offline
    build served by FastAPI, zero external resources. (The 16,174-node base is the
    **local v3 artifact, not shipped** — G-14; the delivered scenario ran on the
    520-observation `evidence/graph.sqlite`, where Q2 is `NO_PATH`, Q7 `debt_backed`
    is unfiltered and Q8 is `NOT_INGESTED`.)
    Proof: `python -m unittest discover -s tests -p "test_api*.py"`;
    `cd frontend && npm run build`.
12. **Measured performance work.** PIT indexes (Q1 −91 %, Q5 −90 % on the real
    DB), gzip + ETag/304, WS compression pinned, Sigma tuning, lazy chunks.
    Proof: `tests/test_graph_pit_fixes.py::PitIndexContractTest`.
13. **Test suite.** `python -m unittest discover -s tests -q` → `Ran 1549
    tests ... OK (skipped=3)`, measured 2026-10-19T13:49Z on this tree; the 3
    skips are documented (testnet RPC gate ×2, eth-account absent path ×1).

## Gap register (open — not claimed, not hidden)

| # | Gap | Status | Where |
|---|---|---|---|
| G-1 | EVAL decision-gain sample N=1 (first EVAL, 2026-10-19): one scored window `eval-usd0pp-2025-01`, `eval-rseth-2026-04` skipped (no archived series); superiority tests `NOT COMPUTED — N < 100`, no superiority claim anywhere | Open, by design until N≥100 | `evidence/evaluation/`, benchmark banner |
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
| G-13 | ~~The scenario's execution leg replays the **pilot USDC decision** under the rsETH run_id (declared substitution).~~ **Closed (2026-10-19)**: `scripts/run_scenario_rseth.py` builds the case DecisionRecord with `build_decision_from_agents` (`decision/decision_agents_<case>.json`) and runs the executor with `--case rseth-2026-04 --decision-source agents --agents-run <sealed run>`; the agents record carries no intent, so the tick ends `NO_ACTION` / `NO_ACTIONABLE_INTENT` with **no policy evaluation, 0 signature, 0 transfer**. `chain_verification.json` compares the record's axes with the executor's per-tick `decision_summary` (9/9 checks, `PASS`). The packaged dossier was regenerated with a new run_id **`scenario-rseth-2026-04-20261019T134804Z`** (agents run `rseth-2026-04_live_20261018T200027592497Z`, 0 new LLM spend, 0.035731 USD realised in the sealed run); the previous dossier (`scenario-rseth-2026-04-20261018T110722Z`, which produced a USDC `intent-usdc-2023-03-…` under the rsETH run id) is archived in `D:/orvyren_internal_2026-10-18/scenario_rseth_superseded/` with a `SUPERSEDED_NOTE.md`. The legacy pilot leg remains selectable with an explicit `--decision-source corpus` and its report declares itself legacy | Closed | `scripts/run_scenario_rseth.py`, `run_executor.py`, `src/orvyren/decision/agents_source.py`, `evidence/scenario_rseth/chain_verification.json` |
| G-14 | The live scenario agents interrogated `evidence/graph.sqlite` (520 obs, schema v2); the 16,174-node v3 database is a local artifact with a reconstruction pipeline, not in the repository | Open, declared | `docs/RUNBOOK.md` §4 |
| G-15 | `queries.q7 debt_backed` sums all visible `OWES` rows without an asset filter (contract figure pinned by tests) — never present it as an exposure metric; the filtered measure is `graph/api.concentration` | Open | `review/graph_eval_bench.md` |
| G-16 | The 2026-10-17 DEV report pair (`mean_R_minus = 0.0000`, pre-fix formula) has been **replaced** by the first EVAL of 2026-10-19 (`generated: 2026-10-19T03:00:46Z`, content hash `c143c243…`, N=1) — executed after the G6 signature of the same day; the earlier artefacts and the operation order are documented in a dated historical note, and no byte-identical claim is made any more | Closed (history documented) | `evidence/evaluation/SUPERSEDED_NOTE.md` |
| G-18 | Live rsETH planners were stopped by **prompt conformance, not by evidence**: runs ended `ARRET-3` / `E_LOOP_OUTPUT_INVALID` (plan missing `$schema` after re-prompt; discriminant criterion containing a digit). **Fixed 2026-10-18**: every validation error now names the field and the rule (`tache.critere_discriminant: no digit allowed — state the criterion qualitatively, figures come from refs`), and an extra attempt (3 instead of 2) is granted only while the LLM budget allows it — otherwise `ARRET-2`, never an overspend. The success path is unchanged: a sealed journal replay still costs the same 5 LLM calls, and no prompt, scripted store or policy file was touched (`grep -c erreurs_validation fixtures/agents/store_usdc-2023-03/*.json` = 0) | Closed | `tests/test_agents_plan_recovery.py` |
| G-17 | `dist/docs/*.docx` are dated builds (2026-10-17) of the `.md` sources, shipped in the submission bundle (gitignored, not tracked): their test counters were refreshed surgically on 2026-10-18 (3 replacements, layout preserved); other text may lag its `.md` — the `.md` files and the README counter are the live source | Declared | this register |
