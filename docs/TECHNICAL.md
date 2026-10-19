# ORVYREN — Technical Description of the Delivered System

**2026 Shenzhen International FinTech Competition — International Track, Theme F
("Agent Wallet / Autonomous On-chain Wallet").**

What is actually built, component by component, with the command that proves each
statement. Every figure was re-measured on this tree before being written down.
Three rules: **no number from memory** (a figure comes from a command printed here,
or from a named artifact and field); **four levels are never mixed** —
*implemented*, *wired*, *modelled*, *absent* — because a tested module is not a
capability until a runner calls it; **what was not measured is declared not
measured**, which matters for the signing path, the evaluation and the 16k graph.

Scope authority: [`SUBMISSION_SCOPE_AND_GAPS.md`](SUBMISSION_SCOPE_AND_GAPS.md);
per-finding ledger: [`ECARTS_REGISTRE.md`](ECARTS_REGISTRE.md). Where this document
disagrees with them, the measurement printed here wins.

## 1. What ORVYREN is

An **on-chain wallet agent for DAO treasuries** that turns public financial signals
into **bounded, auditable decisions** — and refuses, or abstains, when the evidence
does not carry a decision.

One sentence: *it watches the collateral graph of a lending market, formulates
competing explanations for a risk break, buys only the observation that separates
them, decides with a deterministic calculus, and can move funds only inside an
envelope that lives outside the language model.*

**Persona and job.** The first user is a DAO treasury operator holding stablecoins
and liquid staking tokens against lending-market exposure. The job is not "trade":
it is **to be early and to be able to justify**, after the fact, why the treasury
moved or did not. The unit of output is therefore a **decision record with its
refusal path** — verdict, what would change it, which rules were evaluated, which
artifacts hash to what.

**One real case: rsETH / KelpDAO, April 2026.** The Aave v3 Ethereum Core rsETH
reserve saturated its supply cap and was administratively frozen while the oracle
still valued the asset above its market price; the market itself was frozen, so the
"price" was not a realisable exit.

| Fact | Value | Field (`evidence/episode_rseth_2026-04.json`) |
|---|---|---|
| freeze transition | `isFrozen` 0→1 at block 24 908 723 (2026-04-18 19:03:59 UTC) | `headline.rsETH_frozen_transition_block` |
| cap saturation | ratio 0.9999886466022144 at 18:00 UTC | `headline.cap_ratio_max` |
| utilisation at the freeze | 7.946826023583168e-05 | `series["2026-04-18T19:03:59Z"].rsETH.utilisation` |
| oracle at the freeze | 2513.66460329 USD | `headline.rsETH_oracle_at_2026-04-18T19:03:59Z` |
| oracle at the exploit instant | 2526.7563881 USD | `headline.rsETH_oracle_at_2026-04-18T17:35:00Z` |
| market price | 1686 USD — documented point, **series not archived** | `fixtures/sources/RSETH_MEASURE_2.md` |

The mechanism was **a freeze plus cap saturation**, not the "100 % utilisation"
squeeze of the early briefs — utilisation is 0,008 %. The counter-intuitive
hypothesis saying otherwise (HYP-004) is kept in the case on purpose and refuted by
that measured figure. What the shipped live run did with the case is the honest
unit of work: it **abstained** (§5.8).

**How to verify**

```bash
PYTHONPATH=src python -c "import json;d=json.load(open('evidence/episode_rseth_2026-04.json'));print(d['headline']['rsETH_frozen_transition_block'], d['headline']['rsETH_oracle_at_2026-04-18T19:03:59Z'])"
# -> 24908723 2513.66460329
```

## 2. The decision loop

Five stages — **1** observe (`data/`, `quality/`) · **2** structure at a point in time
(`graph/`) · **3** hypothesise and discriminate (**LLM**, `agents/`) · **4** decide
(`decision/`) · **5** authorise, act, prove (`policy` → `execution` →
`chain`/`audit`/`verify`). Stages 1, 2, 4 and 5 are deterministic by construction.

**Observe.** Connectors read reserves, oracle feeds, venue prices and archived
documents. The quality gate answers one question per hour: *may a decision rely on
this hour?* — `OK` only with a price from at least `MIN_INDEPENDENT_VENUES`
independent venues, otherwise `INSUFFICIENT` with the missing venues **named**.

**Structure.** Observations become typed, bitemporal, provenance-carrying relations
(§4.4), readable as *world at T*, *known at T*, or the **PIT decision set** — the
only one a decision may use.

**Hypothesise and discriminate — the only LLM stage.** Two processes run a bounded
loop: plan, call a tool, evaluate the observation, promote or reject claims, stop
(§5.2). The LLM proposes; it never executes, never produces a figure that enters a
decision, never touches policy or execution code.

**Decide.** The evidence state is replayed through RDOF — deterministic ordering by
falsification value, effects computed by counterfactual re-classification, stops on
invariance or budget — and yields three separate axes plus a mandatory
`what_would_change` when inconclusive (§6).

**Authorise, act, prove.** An action is an `Intent`; policy evaluates 14 rules
outside the model; a 10-control preflight runs only on the real path; a signature
produces a receipt verified against what policy allowed; every stage writes into one
hash-chained run a third party re-verifies offline (§7–§9).

**Deterministic vs not.** Deterministic: quality gate, graph writes and reads, PIT
selection, RDOF ordering and stops, abstention A1–A5, the 14 policy rules, the
preflight, the ledger, the chain, the verifier. LLM: which hypotheses are formed,
which test is proposed, the adversarial critique — their output enters the journal
as **claims with refs** and an LLM number never enters a decision figure. Not
measured: whether the LLM stage improves decision quality (`N=1`, §9.6).

**How to verify**

```bash
python -m unittest tests.test_quality_graph tests.test_graph_queries tests.test_decision -q
python -m unittest tests.test_agents_mab tests.test_policy tests.test_executor -q
```

## 3. Module map

"Proves" means something outside the module calls it, or a test pins its contract.

| Module | Role | What proves it |
|---|---|---|
| `data/` | read-only connectors: archive JSON-RPC, Aave v3 reserve struct incl. `isFrozen`, Chainlink, Curve | `scripts/reconstruct_*.py` → `evidence/episode_*.json` (§1) |
| `quality/` | coverage + independence gate per hour | `evidence/quality_report.json`; `tests/test_quality_graph.py` |
| `graph/` | catalogue, 17-group record, Q1–Q8, bitemporal clocks, append-only SQLite store, read-only API, PIT export | `tests/test_graph_*.py`; live HTTP §10 |
| `branches/` | hypothesis record (12 groups), 7-state lifecycle, 5 transition rules | `tests/test_branches_hypotheses.py` |
| `agents/` | bounded MA-B loop, two processes, 3-mode tool registry, tool calling, chained journal, provenance ledger, ACH reflexion, optional FTS memory | `run_agents.py`; `evidence/demo_runs/agents/rseth-2026-04/` |
| `decision/` | deterministic RDOF, 3 axes, abstention A1–A5, catalogs, agents→decision bridge | `run_decision.py`, `python -m orvyren.decide`; bridge read by `run_executor.py --decision-source agents` |
| `policy/` | 14 deterministic rules, fail-closed, production/simulation modes, bundle hash | `policy_v1.yaml` + `tests/test_policy.py`; measured verdicts §7 |
| `execution/` | intents, guard, 10-control preflight, bounded loop, ledger, receipt verification | `run_executor.py`, `run_execution_demo.py`; `tests/test_execution_preflight.py`, `test_executor.py` |
| `chain/` | `RunChain`: hash-chained events, sha256 artifact manifest, `run_id`/`parent_run_id`, fail-closed handoffs | `tests/test_chain_run_id.py`; `chain.verify_ok=true` in every executor run (§8.5) |
| `audit/` | one-page dossier (Markdown + self-contained HTML), every input hashed | `evidence/dossier_usdc-2023-03.md`; A2/A4 checks §9.4 |
| `verify/` | T10 third-party verifier + 6-mutation self-test | `run_verify.py` → `OFFLINE_PASS`, 16 checks, 6/6 (§9) |
| `replay/` | strict PIT clock, journal replay, archive replay (refuses without key), corpus manifest | `run_replay.py inspect|journal|archive|verify` |
| `evaluation/` | frozen protocol G1–G6, loss/comparators/calibration, harness with `eval_run.lock` + embargo | `verify_frozen.py` → `COMPLIANT`; `evidence/eval_run.lock` (§9.6) |
| `ui/` | stdlib fallback UI, 12 screens, banner per screen, no JS, no external asset | `run_audit.py --serve` → `/ui`; `tests/test_ui_routes.py` |
| `api/` | FastAPI REST + `/ws/live`, serves the SPA and real artifacts | `python -m orvyren.api` on 127.0.0.1:8321 (§10) |
| `frontend/` | React 19 + Vite SPA, 5 screens, Sigma.js graph, Lightweight Charts, offline build | `frontend/package.json`, `frontend/dist/`, `tests/test_api*.py` |

Two boundary rules are structural: **no agent process imports `orvyren.policy` or
`orvyren.execution`** (the model's process cannot reach the locks), and
**`execute_intent` is never registerable** in any tool registry — refused by name
and by tool name at registration, and again at execution.

**How to verify**

```bash
python -c "import ast,pathlib
print([ (str(p),n.module) for p in pathlib.Path('src/orvyren/agents').rglob('*.py')
  for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
  if isinstance(n,ast.ImportFrom) and (n.module or '').startswith(('orvyren.policy','orvyren.execution'))])"
# -> []
```

## 4. The graph

### 4.1 Catalogue — 35 kinds in 4 families

`graph/catalog.py` defines machine-checkable relation kinds with family, sign prior,
lifecycle and validation semantics: proof/derivation **8**, structure/exposure
**16**, economic mechanism **3**, constraint/permission **8** — **35 total**, pinned
by `tests/test_graph_catalog.py` (`assertEqual(len(RELATION_CATALOG), 35)`), not by
this paragraph. The count moved from 34 to 35 when the event/liquidation kinds
(`LIQUIDATED_IN`) entered the catalogue for the Aave slice.

**What "defined" does not mean.** 35 kinds are *defined*; **13** are used in the
versioned fixtures; **1** (`SUPPORTS`) exists in the graph the repository ships.
"The system has 35 relations" is false; the sentence above is the true one.

### 4.2 Record — 17 field groups

`record.RELATION_RECORD_FIELD_GROUPS`: 17 groups, 30 concrete fields,
`FIELD_GROUP_COUNT = 17` — (1) `relation_id` (2) `family` (3) `kind` (4) `src`,
`dst`, `src_kind`, `dst_kind` (5) `mechanism` (6) `sign_prior` (7) `conditions`,
`regime_scope`, `horizon_scope` (8) `epistemic_status` (9) `lifecycle` (10)
`validation_status` (11) `valid_from`, `valid_to`, `valid_from_block`,
`valid_to_block` (12) `revision`, `inserted_at`, `superseded_by` (13)
`provenance_refs`, `source_family_id` (14) `extract_method`, `model_version`,
`run_id` (15) `chain_ref` (16) `confidence` (17) `payload`.

Records are validated against the catalogue on write with stable `E_*` codes: a
kind outside the catalogue cannot be stored. The on-chain fields (`chain_ref`, block
range, finality) are what make a fact replayable exactly.

### 4.3 Queries Q1–Q8

`queries.py` is the store's test contract; `graph/api.py` implements the same eight
against SQLite.

| Query | Question | Status on the shipped data |
|---|---|---|
| Q1 | consolidated exposure of a holder, direct + indirect | answers; bounded expansion, never transitive `HOLDS` |
| Q2 | dependency paths between two nodes | `NO_PATH` on the Aave slice (no `DEPENDS_ON`/`AFFECTS` populated) |
| Q3 | unresolved contradictions | `NO_OPEN_CONTRADICTIONS` on the slice |
| Q4 | PIT state of the graph at T | answers |
| Q5 | episode timeline, admissible on **both** clocks | answers; empty on the slice window |
| Q6 | provenance walk relation → claims → observations → sources | answers by `relation_id` |
| Q7 | concentration: debt backed by an asset | **do not quote a figure** — the fixture implementation sums all visible `OWES` rows (G-15); filtered measure is `graph/api.concentration` |
| Q8 | permission state as-of a block | `NOT_INGESTED` — no Safe/Zodiac data in the slice |

### 4.4 Point-in-time correctness

Two clocks, formally distinct and tested: **event time** (when the fact was true) and
**observation time** (when we learned it). Q5 filters on both; instant comparisons go
through `julianday` on aware-UTC datetimes, never through lexicographic comparison of
timestamp strings. The invariant of `temporal.pit_at`: *a revision published after
`as_of` never changes a past decision.*

### 4.5 Store

**Append-only**: `store.py` installs `BEFORE UPDATE` / `BEFORE DELETE` triggers
raising `append-only table: <name>` on every table — the guarantee does not depend on
application discipline. **SQLite, not PostgreSQL** (stdlib `sqlite3`; no server, no
pgvector). **Additive migrations** (`ALTER TABLE ADD COLUMN`) with a `SCHEMA_VERSION`,
so an old file still opens. **The read API opens the file `mode=ro`** (URI
read-only): a write through the API is impossible by construction.

### 4.6 Populated vs not — two databases, never quoted as one

**(a) The repository snapshot — `evidence/graph.sqlite`:** 520 observations · 4
claims · 4 relations (all `supports`) · 4 sources · 1 hypothesis · 0 decision nodes;
schema version row `2`. **Zero structural edges** — no `HOLDS`, `DEPOSITED_IN`,
`COLLATERALIZES`, `DEPLOYED_ON`, `PRICED_BY`. It is an episode snapshot, not a
market graph.

**(b) The demonstration database — outside the repository:** 16 174 nodes · 12 937
relations · 15 000 events · 12 937 provenance rows. Relations by kind: `HOLDS` 4 873
· `DEPOSITED_IN` 4 873 · `OWES` 1 976 · `COLLATERALIZES` 1 171 · `PART_OF` 11 ·
`IS_A` 11 · `DEPLOYED_ON` 11 · `CONSTRAINS` 11 — **8 kinds**. Nodes: `EVENT` 15 000 ·
`ADRESSE` 753 · `POSITION` 377 · `MARCHE` 11 · `PARAMETRE` 11 · `ACTIF` 6 · `DETTE` 6
· `CLASSE` 3 · `STABLECOIN` 3 · `LST` 2 · `CHAINE` 1 · `POOL` 1. Ingested from Aave
v3 Pool logs on Base (`scripts/ingest_aave_base.py`) with a recorded watermark (pool
`0x1f0ba738…`, block 52 723 533, status `OK`). It is a **local artifact with a
reconstruction pipeline, not part of the repository** (≈50 MB); a clean clone shows
(a), never (b), and the UI states which one it reads.

**(c) The fixtures — `fixtures/graphs/*.json`:** 3 files, **20 records**, **13 kinds**
(`usdc_2023-03.json` 9/6, `steth_2022-06.json` 4/2, `rseth_2026-04.json` 7/6).

**How to verify**

```bash
PYTHONPATH=src python -c "from orvyren.graph.catalog import catalog_stats,RELATION_CATALOG;print(catalog_stats(),len(RELATION_CATALOG))"
# -> {'PROOF_DERIVATION': 8, 'STRUCTURE_EXPOSURE': 16, 'ECONOMIC_MECHANISM': 3, 'CONSTRAINT_PERMISSION': 8} 35
PYTHONPATH=src python -c "import sqlite3;c=sqlite3.connect('evidence/graph.sqlite');print([(t,c.execute('select count(*) from '+t).fetchone()[0]) for t in ('observations','claims','relations')])"
# -> [('observations', 520), ('claims', 4), ('relations', 4)]
```

## 5. The agents

### 5.1 Two processes, two roles, no shared memory

`run_agents.py` spawns **two separate OS processes** per run
(`agents/worker.py --role orchestrator|critic`). The **orchestrator** runs the bounded
loop, plans, calls tools, evaluates observations, writes `journal_orchestrator.jsonl`;
the **critic** receives the evidence packet and attacks the reading on a second model
family, writing `journal_critic.jsonl`. They communicate **only** through
serialisable JSON files — never shared memory. The critic never cancels a decision:
it **forces escalation** (`REQUIRE_APPROVAL`), a stronger and more auditable outcome
than a veto.

### 5.2 The bounded loop

`agents/loop.py` runs plan → act → observe → evaluate with four counters and five
stops. Ceilings are frozen in `contracts.DEFAULT_BUDGET_LIMITS`: `llm_calls` 30 ·
`tool_calls` 12 · `wall_seconds` 600 · `cost_usd` 0.10 — a caller may lower them,
never raise them (`E_BUDGET_WIDENED`). The budget is **part of the recorded prompt**,
so a replay at a different budget fails closed instead of improvising.

| Stop | Meaning | Failure? |
|---|---|---|
| `ARRET-1` | no task left with positive value | no — orderly |
| `ARRET-2` | a ceiling reached (checked before every call) | no — orderly |
| `ARRET-3` | validation impossible → quarantine, then abort | **yes** — fail-closed |
| `ARRET-4` | sufficient evidence (guard-rail hook) | no |
| `ARRET-5` | no research worth its cost (`NetVoI <= 0`) | no |

`ARRET-3` is the only failure state and it is deliberate: an invalid output is
**never coerced** into a valid one; the bounded repair (a re-prompt naming the field
and rule) consumes the same budget, so when the ceiling forbids the next call the run
stops in `ARRET-2` rather than overspend.

### 5.3 Tool calling

A model never executes a tool. `agents/llm.py` offers **native tool calling**
(OpenAI-style specs, `tool_choice: auto`, and **no** `response_format` — the two are
rejected together by most providers; returned `tool_calls` are normalised into a
canonical blob, so a tool-using turn replays bit-identically), and a **strict JSON
fallback** (`orvyren/toolcall/v1`) used only when the provider emits no native call.
The downgrade is **always journaled** (`fallback_motif` + a `TOOL_CALL` line): a
silent downgrade is a bug, a visible one is a fact.

Arguments are closed objects (`additionalProperties: false`): an unknown or missing
key refuses the call and the tool never runs. **Bounds are imposed by code**: `limit`,
`max_depth`, `as_of_block` are range-checked (`E_TOOL_ARGS_RANGE`; a negative `limit`
would become `LIMIT -1` in SQLite, i.e. unbounded, and `0` stays a legal value).
`deadline_s` is validated (finite, > 0, ≤ 600) and **enforced** against an injectable
clock: a late result is `E_TOOL_DEADLINE` and its data is dropped.

### 5.4 Registry — three modes, one code path

`tools.build_registry(mode=...)` has one implementation; only the data provider
changes (`tool_sources.py`). **`fixture`** serves archived fixtures (7 v1 tools;
`compute_signal` is fixture-only, because a pre-computed signal is a hard-coded
decision). **`live`** interrogates the graph API and the measured corpus with its
arguments (arguments change the result; `read_chain` returns `E_TOOL_NO_LIVE_SOURCE`
— no RPC wired, honest, not faked). **`replay`** serves recorded responses
bit-identically; a miss is `E_TOOL_NOT_RECORDED`, never a fallback.

v1 set: `read_prices`, `read_supply`, `read_chain`, `fetch_document`,
`compute_signal`, `graph_query`, `journal_write`. The live/replay set drops
`compute_signal` and adds `graph_path`, `graph_snapshot`. `journal_write` is the
run's **output basin** and is never wrapped by a replay source — wrapping it would
silently delete the replay's own claims. `execute_intent` is in no set and refuses
registration.

### 5.5 Provenance — P0-6, three gates

A claim may only cite references the run **really observed**. The run keeps an
`ObservedRefs` ledger seeded from fixture rows, snapshot refs and authorised refs. A
claim citing an unknown ref is **rejected visibly** (`E_REF_NOT_OBSERVED`) — never
repaired with a "similar" source — at three independent doors: `JournalWriteTool`,
the loop's `_record_evaluation`, and `worker.build_evidence_packet` (the second
barrier, so a rejected claim cannot reach the critic packet). Journals are
append-only JSONL **chained by hash** (`prev_hash`/`record_hash`); a modified line
breaks the chain.

### 5.6 Memory — present, optional, off by default

`agents/memory.py` is a minimal SQLite **FTS5** memory: one entry = text + refs, and
an entry without refs is refused (`E_MEMORY_NO_REFS`). Search is lexical,
deterministic (`rank, memory_id`), the query re-quoted so an FTS operator cannot
alter the syntax. It is **not part of a default run**: `worker.py` constructs it only
with `run_agents.py --memory`, which also adds the `memory_recall` tool. The reason
is replay integrity — the allow-list is part of the recorded planning prompt, so a
memory-enabled run needs its own recording. There is **no embedding, no vector
search, no semantic retrieval** in v1; that decision is recorded in
[`ADR-0003`](decisions/ADR-0003-recherche-semantique-ml1-v2.md) and reclassified to
V2.

### 5.7 Reflexive reasoning (ACH)

`agents/reflexion.py` builds a hypotheses × evidence matrix **in code** from the
agents' own claims: `COHERENT`/`INCOHERENT`/`NEUTRE` cells, diagnosticity weight per
evidence item, refutation-first ranking, and an explicit gap (the next discriminating
test). A change in the dominant hypothesis is an **escalation**, never a silent flip.
No prompt or payload is touched, so replay is preserved.

### 5.8 A measured run — the shipped rsETH live session

`evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/`
(real LLM calls, sealed store):

| Field | Value |
|---|---|
| `outcome.stop_condition` / `motif` | `ARRET-3` — `E_LOOP_OUTPUT_INVALID: orchestrator plan invalid after re-prompt (critere_discriminant contains a digit)` |
| `outcome.budget_used` · `critique` | 5 LLM calls, 1 tool, 34.42 s, **$0.035731098** · `INCOHERENTE`, 10 findings, 7 missing proofs |
| `escalation` · journals | `REQUIRE_APPROVAL` · orchestrator 13 lines (`9d1372f5…`), critic 1 (`924d84dd…`) |

The system spent 3.6 cents, produced a critique, and **proposed no transaction**. A
run that stops on the *form* of a plan rather than on the evidence is a real
limitation (G-18); the recovery path — a re-prompt naming the field and the rule —
exists and is unit-tested.

**How to verify**

```bash
python run_agents.py --case usdc-2023-03 --replay journal --session "$TEMP/sess"
# -> stop ARRET-1 · llm 5/30 · tools 2/12 · $0.0018 · critique FRAGILE · REQUIRE_APPROVAL · chain OK
python -c "import json;o=json.load(open('evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/run_outcome.json'));print(o['outcome']['stop_condition'],o['outcome']['budget_used']['cost_usd'],len(o['critique']['findings']))"
# -> ARRET-3 0.035731098 10
```

## 6. The decision engine

`decision/` is deterministic end to end: no probability, no model call, no wall-clock
in a figure.

### 6.1 RDOF — five rules, frozen order

1. **Evaluability** — mark every hypothesis criterion evaluable / not; collect the unknowns.
2. **Effects** — for each candidate predicate and outcome class, compute *"if the outcome
   were this class, what happens to each verdict?"* by counterfactual re-classification:
   **computed, never hard-coded**.
3. **Ordering** — frozen lexicographic order: (i) can refute the dominant hypothesis;
   (ii) makes evaluable a criterion carrying the opposite decision; (iii) resolves a
   registered contradiction; (iv) lowest measured cost.
4. **Execution** — collect the predicate, add it to the evidence state, restart.
5. **Stop** — first true: **c1 INVARIANCE** (every remaining outcome leads to the same
   action → "stable decision", even with budget left) or **c2 BUDGET** (with *what was
   not searched* and its possible effect).

The **dominant** hypothesis is the first, in the frozen order H1/H2/H3, that is not
`REFUTED` — the standing narrative the evidence has not eliminated. Value of
information stays behind one interface and returns `VOI_NOT_ESTIMABLE` in v1 (no
calibrated frozen probabilities): the mechanism takes over without changing the
decision and never becomes a failure point. `compare_rdof_vs_fixed_order` exists
because the order itself is a claim: RDOF is evaluated against the documented fixed
order before being relied on.

### 6.2 Three axes, never fused

| Axis | Values | Note |
|---|---|---|
| `epistemic_verdict` | `CONCLUANT` / `INCONCLUSIVE` + what is missing | axis 1 |
| `economic_action` | bounded-action enum or `null` | axis 2 |
| `authorization_verdict` | `ALLOW` / `DENY` / `REQUIRE_APPROVAL` | axis 3 — independent: "policy DENY" ≠ "epistemic failure" |

The double price convention is frozen (`FREEZE_V2` C5) and exposed as **one**
parameter, `PRICE_CONVENTION`: *alert on the low, decide on close + low*. The gap
between readings is reported wherever a threshold decides, instead of being hidden by
a convention.

### 6.3 Abstention A1–A5

Abstention is a first-class result with an enriched format: condition code, evidence,
and a mandatory `what_would_change` list.

| Code | Condition | Axis |
|---|---|---|
| A1 | a required input is missing | epistemic |
| A2 | an unresolved contradiction | epistemic |
| A3 | not identifiable within budget (RDOF c2 with ≥ 2 surviving hypotheses) | epistemic |
| A4 | the preferred action is outside the envelope/policy | **authorisation** — never confused with A1–A3 |
| A5 | two admissible measurement conventions give different verdicts | epistemic |

The output distinguishes `ESCALATE` from `NO-ACTION`: "I cannot decide" and "I decided
not to act" are different products.

### 6.4 The bridge — agents run → DecisionRecord

`decision/agents_source.py` reads one sealed agents run directory and returns a
payload of the **engine's own schema** (`orvyren-decision-record/v1`, pinned by an
equality test against `orvyren.decide.SCHEMA`), not an invented format. Six hard
rules: (1) **no invented figure** — a value the artifacts do not carry is
`"unavailable"` / `None`, never `0`; (2) **determinism** — no wall-clock, no `listdir`
order, two calls serialise identically; (3) **honest abstention** — `inconclusive`
**or** `escalation == REQUIRE_APPROVAL` ⇒ no action, no intent, `REQUIRE_APPROVAL`,
and `what_would_change` copied **verbatim** from `outcome.non_recherche`; (4) **a
bounded intent needs a declared bounded action** — a missing action, chain, asset or
amount yields no intent at all; (5) **provenance from the journals** — chain heads are
**recomputed** with the writer's hash function and compared to the sealed
`run_outcome.json`, a mismatch being `AgentsSourceError`; (6) **live runs are declared
non-replayable** (`source.replayable=false` with a reason) — not refused, because a
sealed live run is still usable evidence.

### 6.5 A measured decision

`PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay` prints
(measured): `epistemic_verdict: CONCLUANT`, `economic_action: CONVERTIR/TRANSFÉRER`,
an intent of 100.0 USDC, and the rationale *"verdicts: H1 REFUTED, H2 SUPPORTED, H3
REFUTED ; RDOF: stop "stable decision (invariance c1)" after 1 search(es), cost 0.65 s
/ 1 call(s)"*. The search stopped on **invariance after one observation** — the
second was not worth buying because every outcome of the remaining predicate led to
the same action. That is the mechanism working, not a shortcut.

**How to verify**

```bash
python -m unittest tests.test_decision tests.test_decision_rdof tests.test_decision_axes -q
PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay | head -8
```

## 7. Policy

`policy/` is the first lock and it lives **outside** the model: pure, synchronous,
stdlib-only, unimportable from an agent process. Parameters come from
`policy_v1.yaml` (not code constants); the bundle hash is
`sha256(yaml_sha256 + ":" + code_sha256)`, so a change of *code* also changes the
published policy fingerprint.

| Rule | What it checks | Denial code(s) |
|---|---|---|
| P1 | chain id allowed | `CHAIN_NOT_ALLOWED` |
| P2 | asset allowed | `ASSET_NOT_ALLOWED` |
| P3 | recipient in the resolved allowlist | `RECIPIENT_NOT_ALLOWED` |
| P4 | operation and (target, selector) registered | `OPERATION_NOT_ALLOWED`, `TARGET_NOT_ALLOWED`, `FUNCTION_NOT_ALLOWED` |
| P5 | per-tx cap, finite, exact base units | `AMOUNT_NOT_FINITE`, `AMOUNT_INVALID`, `AMOUNT_ABOVE_TX_CAP` |
| P6 | rolling 24 h cumulative | `CUMULATIVE_INVALID`, `AMOUNT_ABOVE_PERIOD_CAP` |
| P7 | balance / floor / exposure cap | `BALANCE_UNREADABLE`, `BALANCE_INSUFFICIENT`, `FLOOR_BREACH`, `EXPOSURE_ABOVE_CAP` |
| P8 | permission present and unexpired | `PERMISSION_MISSING`, `PERMISSION_EXPIRED` |
| P9 | intent freshness (TTL, clock skew) | `INTENT_STALE`, `INTENT_NOT_YET_VALID` |
| P10 | idempotency (by id and by content hash) | `INTENT_ALREADY_PROCESSED` |
| P11 | pause + agent membership | `PAUSED`, `AGENT_NOT_MEMBER` |
| P12 | envelope status (Roles v2 permissions) | `ENVELOPE_DRIFT`, `ENVELOPE_UNVERIFIED` |
| P13 | action scope | `ACTION_UNKNOWN` |
| P14 | budget | `BUDGET_EXCEEDED`, `BUDGET_UNREADABLE` |

**28 denial codes** in `DENY_CODES_V1` (29 reason codes counting
`ACTION_NEEDS_HUMAN_APPROVAL`, a verdict, not a denial). Codes are never renamed and
never reused.

**Fail-closed, concretely.** Production is the default mode: `evaluate(...,
mode=production)` with no `PolicyState` returns **DENY `STATE_REQUIRED`**, and
P7/P11/P12/P14 are recorded `FAIL`, never `SKIPPED`. Simulation must be **declared**
(`EVAL_MODE_SIMULATION`) — used by test benches, the replay verifier, the
authorisation axis and the demo helper, each declaring it; an unknown mode is a hard
`ValueError`. Unreadable is denied: `agent_member=None`, `available_balance=None`,
`envelope_status=None` deny — a default of `True` or `1000` would turn the kill
switch into decoration. `max_per_tx` / `max_cumulative` non-finite or ≤ 0 is refused
at load time, because `NaN > cap` is always false and would silently disable the
comparison. `DRIFT` and `UNVERIFIED` are denial codes **and** set `safe_mode=true`,
so a caller reading only `verdict` cannot mistake a safe-mode decision for a normal
one.

**Measured verdicts** (`run_execution_demo.py`, real `policy_v1.yaml`, full state, no
signature):

```
policy: policy_v1.yaml v1.0 (hash 6515358722284704)
I1  ALLOW            transfer       100.0 USDC   deny_codes: -
I2  DENY             transfer       500.0 USDC   deny_codes: AMOUNT_ABOVE_TX_CAP, AMOUNT_ABOVE_PERIOD_CAP
I3  REQUIRE_APPROVAL change_policy  100.0 USDC   deny_codes: ACTION_NEEDS_HUMAN_APPROVAL
    SKIPPED rules: P4-function — approval-only action — no direct call in v1
24 h period (4 x 100.0 USDC, cap 300.0): 1 ALLOW · 2 ALLOW · 3 ALLOW · 4 DENY AMOUNT_ABOVE_PERIOD_CAP
cumulative re-read after restart: 300.0 USDC (3 entries) · guard blocks: 2 (I2, I3)
state rules evaluated (state supplied): P7/P11/P12/P14 — none SKIPPED
```

**How to verify**

```bash
python -m unittest tests.test_policy -q
PYTHONPATH=src python run_execution_demo.py --out "$TEMP/demo.json" | tail -20
```

## 8. Execution

### 8.1 Intent and guard

An `Intent` is a structured, **unauthorised by nature** request: `intent_id`,
`action`, `chain_id`, `asset`, `amount`, `recipient`, `created_at`, `justification`.
It is the only structure crossing decision → policy; the decision record never
reaches the signer, and an inconclusive decision yields no intent.
`execution/guard.py` (`assert_allowed`) is the coarser second barrier used by the
demo kit: it refuses a policy-denied instruction and counts what it blocked.

### 8.2 Preflight — ten controls, documented order

`execution/preflight.py`, `run_preflight(...)`: ten controls, **stop at the first
FAIL**; the rest stay `SKIP` with `detail="not evaluated: <code>"` — never `PASS`.

| # | Control | Code | # | Control | Code |
|---|---|---|---|---|---|
| 1 | policy verdict is ALLOW | `POLICY_NOT_ALLOW` | 6 | target has code | `TARGET_CODE_MISSING` |
| 2 | chain id matches | `CHAIN_ID_MISMATCH` | 7 | gas estimate succeeds | `GAS_ESTIMATE_FAILED` |
| 3 | intent not expired | `INTENT_EXPIRED` | 8 | gas balance ≥ 2 × estimate | `INSUFFICIENT_GAS_BALANCE` |
| 4 | not already processed | `INTENT_ALREADY_PROCESSED` | 9 | token balance sufficient | `INSUFFICIENT_TOKEN_BALANCE` |
| 5 | agent not paused | `AGENT_PAUSED` | 10 | simulation does not revert | `SIMULATION_REVERT` |

Three facts worth stating. The order **P12 before P9a** is deliberate and in the
docstring: the gas-balance check needs `2 × estimate`, so the estimate must exist
first — the numbering is the policy's, the execution order is the preflight's. **P6,
P8 and P10 do not exist as preflight controls** and are never reported as "passed":
ten controls, ten codes, **not twelve** — older documents claiming twelve described a
design, not this code. The module is pure stdlib with an injectable transport
(`JsonRpc` over `urllib`), so no test touches the network; selectors are hard-coded
(`0x70a08231` balanceOf, `0xa9059cbb` transfer) and amounts are integer base units
(`amount_to_base_units` refuses scientific notation, signs and excess decimals).

### 8.3 The gate is in the loop

`execution/loop.run_loop(preflight_runner=...)` runs the preflight **only on the real
path**, before any signature. A refusal yields `outcome=PREFLIGHT_REFUSED`,
`executed=False`, a `PREFLIGHT_REFUSED` chain event, `stopped="preflight"`,
`counts["signed"] == 0`; a non-mapping response is a refusal (`PREFLIGHT_UNAVAILABLE`).
A **dry run never touches the preflight** — there is nothing to protect.
Configuration is checked **by variable name** at start-up
(`ORVYREN_RPC_URL_BASE_SEPOLIA`, `ORVYREN_AGENT_ADDRESS`, `ORVYREN_SAFE_ADDRESS`):
absent means refusal at start-up, never a silent skip.

### 8.4 Dry-run vs `--execute`

| | dry-run (default) | `--execute` |
|---|---|---|
| reads a key | no | yes, lazily, only for the signing step |
| preflight | not run | mandatory, before signature |
| run id | auto-generated | **explicit** (`E_CHAIN_RUN_ID_REQUIRED`) |
| signature / broadcast | no | yes |
| receipt verification | no | yes (`execution/verify.verify_receipt`) |

### 8.5 Measured behaviour of both paths

```bash
PYTHONPATH=src python run_executor.py --ticks 5 --json          # fail-closed default
# -> "counts": {"allow": 0, "deny": 5, "require_approval": 0, "dry_run": 0, "signed": 0, ...}
PYTHONPATH=src python run_executor.py --ticks 5 --demo-defaults --json   # declared demo defaults
# -> "counts": {"allow": 3, "deny": 2, ..., "dry_run": 3, "signed": 0}  (ticks 4-5: AMOUNT_ABOVE_PERIOD_CAP)
PYTHONPATH=src python run_executor.py --execute --run-id r1 ; echo $?    # real path, no key
# -> ERROR --execute: ORVYREN_PRIVATE_KEY missing or malformed — --execute refused (fail-closed) / 4
```

Both readings belong side by side: the first is the **safety** proof (an unreadable
state cannot spend), the second the **mechanism** proof (the rules fire in order and
the 24 h cap bites at the fourth transfer). Every run also writes a `RunChain` and
reports it: `"chain": {"run_id": "run-…", "verify_ok": true, "events_head": "…",
"artifacts": 10}`.

### 8.6 What has never been exercised

**The `--execute` path has never run end to end.** Preflight, signing, broadcast and
receipt verification are implemented and unit-tested with injected transports, but no
run of this system has ever signed and broadcast a transaction by itself.

The 13 demonstration transactions on Base Sepolia were signed by a **human-held
testnet key** outside the agent: 1 succeeded (`status 0x1` — the single transfer
inside the policy envelope) and 12 reverted (`status 0x0` — forced attacks
C1/C2/C3a/C3b/C4, **refused by the on-chain envelope**). The reverts **are** the
demonstration: the Zodiac Roles v2 permission layer refused a 500 USDC transfer above
the allowance, a transfer to a non-allowlisted recipient, and the rest — on-chain, not
in a log. The one success proves the permitted path works. This is gap **G-12**, and
this document makes no autonomous-execution claim.

**How to verify**

```bash
python -m unittest tests.test_execution_preflight tests.test_executor -q
PYTHONPATH=src python run_executor.py --ticks 5 --demo-defaults --json | grep -o '"counts": {[^}]*}'
python -c "import json,glob,collections;print(collections.Counter(json.load(open(p))['status'] for p in glob.glob('evidence/demo_chain/rseth/receipts/*.json')))"
# -> Counter({'0x0': 12, '0x1': 1})
```

## 9. Audit and verification

The claim this section supports is narrow and checkable: **a third party can
recompute what happened without trusting us and without our repository.**

**9.1 RunChain.** Events are JSONL carrying `run_id` / `parent_run_id` / `case_id` /
`stage` / `ts_utc` / `prev_hash`; artifacts are written to `root_dir/<stage>/<name>`
atomically and registered in `manifest.json` as `{stage, sha256, bytes}`; the manifest
is **verified at every handoff** (present + sha256 valid) and a failure is
`ChainContractError`, fail-closed — the next stage never runs on unverified inputs.
Ids are never reused, a re-run carries `parent_run_id`, and `--execute` without an
explicit `--run-id` is refused (`E_CHAIN_RUN_ID_REQUIRED`). Stage and artifact names
are validated as flat tokens, so a drive-colon cannot escape `root_dir/<stage>/`.

**9.2 The dossier.** `audit/dossier.py` renders a one-page dossier (Markdown + a fully
self-contained HTML: inline CSS, **no scripts, no external resource**). Every input
actually read is listed with its SHA-256, the dossier carries a reproducible
self-hash (the 64-char field zeroed before hashing), and a missing or invalid input
is printed verbatim (`Missing input: <path>`) — never substituted.

**9.3 The T10 verifier.** `verify/engine.py` recomputes, offline by default: **A** —
`A1` execution chain + graph chain + agent absence · `A2` dossier md/html · `A3`
packet sha256 + dossier inputs · `A4` dossier re-render byte-identical · `A5` policy
verdicts · `A6` graph snapshot · `A7` fixtures/signals · `A8` receipts cross-check;
**B** — on-chain re-verification via `--rpc` (skipped offline, reported `SKIPPED`,
never ok-by-default); **C** — `C1` agent journal · `C2` refs resolve. A4 is the
strict one: the packet's own dossier must re-render byte-identical from its inputs,
which is why re-staging uses the same display root as the build.

**9.4 Measured: the reference packet.** 47 files; zip sha256
`a0c4562050a6c468ab8a2adea4a858acdd8e76154640b5f42b1be94ecc0a669e`, matching its
published sidecar (`sha256sum -c` → `OK`). The run prints every check
(`CHECK A1.exec.chain RECOMPUTED ok` … `CHECK C2.refs.resolve COVERED ok`), with
`B1.chain.rpc` reported `SKIPPED` offline, and ends
`VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations n/a`.

> **Re-measured 2026-10-19T13:42Z on the same packet: `VERDICT: FAIL — 16 checks,
> 2 failed`** (`A4.dossier.rerender.md`, `A4.dossier.rerender.html`).
> `src/orvyren/audit/dossier.py` changed after the packet was built, so its A4
> re-render no longer matches. The packet must be rebuilt and §9.4/§9.5
> re-measured before this transcript is quoted — `docs/CLOSURE_CHECKLIST.md` item 8.

**9.5 Measured: the mutation self-test.** A verifier that always says "ok" is
worthless, so the tool attacks its own packet — M1 one byte of the dossier body · M2
one character in an `audit.jsonl` line · M3 one digit of an amount in
`decision_*.json` · M4 one amount in a raw receipt · M5 removal of a receipt file · M6
one modified line of the frozen verifier. All six are detected:

```
MUTATION M1 detected (A2.dossier.md, A3.packet.sha256, A4.dossier.rerender.md)
MUTATION M2 detected (A1.exec.chain, A3.packet.sha256)
MUTATION M3 detected (A3.dossier.inputs, A3.packet.sha256, A4.dossier.rerender.html, A4.dossier.rerender.md)
MUTATION M4 detected (A3.packet.sha256, A8.receipts.cross) · M5 detected (same two)
MUTATION M6 detected (A3.packet.sha256)
VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations 6/6
```

**9.6 Evaluation — `N=1`, non-conclusive.** The protocol is frozen (`frozen/G1..G6`,
byte-identical recalculation, `verify_frozen.py` → `COMPLIANT`, 20 files, 1.10 s)
and the harness enforces the gates that make a later number trustworthy: the
freeze gate really checks the code hashes announced in the Gx documents, the
calibration embargo is mandatory, and `eval_run.lock` is burned — an EVAL pass
requires `--force` and an explicit mention. **N = 1**: the first EVAL ran on
**2026-10-19**, after the G6 signature of the same day — one window scored
(`eval-usd0pp-2025-01`), one skipped (`eval-rseth-2026-04`, no archived series),
`A2` absent on the scored window (declared substitution). That is far below
`N ≥ 100`, so **no superiority claim** is made anywhere and the harness refuses
the wording below the threshold. The mini-benchmark that exists is diagnostic
only: 12 runs, A0 (deterministic engine) vs A2 (full agents), one real episode +
one labelled synthetic placebo that **was executed** — `evidence/benchmark_ab/report.md`
carries the banner *"no superiority claim (G1 threshold N>=100 not reached)"*. The
current report is `generated: 2026-10-19T03:00:46Z`, content hash `c143c243…`,
superiority tests `NOT COMPUTED`; the 2026-10-17 DEV pair is history, documented
in `SUPERSEDED_NOTE.md` — no figure may be quoted from it.

**How to verify**

```bash
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip --mutate-test | tail -7
(cd evidence/audit_packets && sha256sum -c audit_packet_rseth_20261016-2340_01M526YS.zip.sha256)
(cd evidence/demo_chain/rseth && sha256sum -c MANIFEST.sha256 | tail -1)
python scripts/verify_frozen.py | tail -1
test -f evidence/eval_run.lock && echo "EVAL lock present (burned)"
```

## 10. Interfaces

**The SPA** (`frontend/`) is a real React 19 + Vite + Tailwind application — not a
static page without JavaScript — with five screens: Live (agent runs, sealed
sessions, WebSocket stream), Graph (Sigma.js/graphology rendering + Q1–Q8 panel),
Markets (stress-episode series, Lightweight Charts), Decision & policy (RDOF output,
P1–P14 verdicts, intents and receipts), Audit (journal chains recomputed, sealed
packets). The build is offline: `npm ci && npm run build`, no external resource at
runtime, `frontend/dist/` served by the API.

**The API** (`api/`) is FastAPI: **25 REST endpoints** in `routes.py` plus `/ws/live`,
default bind `127.0.0.1:8321` (`ORVYREN_API_HOST` / `ORVYREN_API_PORT`). Imports are
lazy, so the unittest suite stays green without FastAPI installed and the API tests
skip visibly. An unmatched path returns `404` JSON — never a `503` blaming a missing
build — and `/api/` and `/ws/` are never swallowed by the SPA fallback.

Measured on a live instance:

```bash
ORVYREN_API_PORT=8399 PYTHONPATH=src python -m orvyren.api &
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8399/     # -> 200
curl -s http://127.0.0.1:8399/api/health
# -> {"status":"ok",…,"graph_db":"../orvyren_10h_2026-10-17/graph_v3.sqlite",
#     "graph_db_absent":false,"frontend_built":true,"mode":"offline-demo"}
curl -s http://127.0.0.1:8399/api/graph/info | head -c 120   # -> {… "nodes":{"count":16174 …
```

Query latency over 5 calls each (warm cache): `q1` 16–19 ms, `q4` 34–39 ms, `q7`
15–17 ms; `q8` answers `NOT_INGESTED`, `count: 0` — an honest status, a different
fact from "no permissions exist".

**Database selection.** `api/config.py` prefers the 50 MB demonstration database at
`ORVYREN_DEFAULT_GRAPH_DB` and falls back to the in-repo `evidence/graph.sqlite` when
absent. `/api/health` reports which one is open (`graph_db`, `graph_db_absent`) and
the UI shows it: on a clean clone a reader sees the 520-observation snapshot with a
visible label, not a silent 16k graph.

**The stdlib fallback UI.** `run_audit.py --serve` exposes `/ui` with **12 screens**
(`ui/screens.py`) — HTML, no JavaScript, no external asset, deliberately, as the
offline safety net when Node is unavailable. Each screen carries a mandatory banner
(mode + clock) and a source table with short sha256s; a missing source prints `SOURCE
MISSING`, a present-but-empty source prints `0 rows (source present)` — never
conflated.

**How to verify**

```bash
python -m unittest discover -s tests -p "test_api*.py" -q
grep -c "@router\." src/orvyren/api/routes.py                       # -> 25
python -c "from orvyren.ui.screens import screen_ids;print(len(screen_ids()))"   # -> 12
python -m unittest tests.test_ui_routes tests.test_ui_panels -q
```

## 11. Measured numbers

Each row is a command someone else can run on this tree. Values were produced on
2026-10-18, except the test-suite row, measured 2026-10-19, on this machine;
different hardware may change timings, never counts.

| # | What | Command | Result |
|---|---|---|---|
| 1 | Test suite | `python -m unittest discover -s tests -q` | `Ran 1546 tests in 73.427s` — `OK (skipped=3)` — measured 2026-10-19T13:49Z |
| 2 | Frozen protocol | `python scripts/verify_frozen.py` | `COMPLIANT` (20 files, 1.10 s) |
| 3 | Audit packet + tamper test | `run_verify.py …01M526YS.zip [--mutate-test]`; `sha256sum -c` on its sidecar | **2026-10-18**: `OFFLINE_PASS — 16 checks, 0 failed` · `mutations 6/6` · zip `a0c4562050a6c4…` `OK`. **Re-measured 2026-10-19T13:42Z: `FAIL — 16 checks, 2 failed`** (`A4.dossier.rerender.md/.html` — `audit/dossier.py` changed after the packet was built); packet rebuild required |
| 4 | Testnet receipts | count over `evidence/demo_chain/rseth/receipts/*.json`; `sha256sum -c MANIFEST.sha256` | 13 files (`0x1` ×1, `0x0` ×12); manifest 16 files `OK` |
| 5 | Relation catalogue | `catalog.catalog_stats()` | 35 kinds — 8 / 16 / 3 / 8 |
| 6 | Relation record | `len(RELATION_RECORD_FIELD_GROUPS)` | 17 groups / 30 fields |
| 7 | Graph fixtures | `fixtures/graphs/*.json` | 3 files, 20 records, 13 kinds |
| 8 | Repo graph | `count(*)` on `evidence/graph.sqlite` | 520 observations · 4 claims · 4 relations (all `supports`) |
| 9 | Demo graph (outside repo) | `count(*)` on `graph_v3.sqlite` | 16 174 nodes · 12 937 relations · 15 000 events |
| 10 | Policy | `len(RULES_V1)` | 14 rules, 28 denial codes |
| 11 | Preflight | `len(preflight.CHECK_ORDER)` | 10 controls |
| 12 | Executor | `run_executor.py --ticks 5 --json` / `--demo-defaults` | `allow 0 · deny 5 · signed 0` / `allow 3 · deny 2 · dry_run 3 · signed 0` |
| 13 | Executor, real path, no key | `run_executor.py --execute --run-id r1` | rc **4**, refused before the first tick |
| 14 | Agent replay (scripted) | `run_agents.py --case usdc-2023-03 --replay journal` | `ARRET-1` · 5/30 LLM · 2/12 tools · **$0.0018** · FRAGILE → REQUIRE_APPROVAL |
| 15 | Shipped live run | `run_outcome.json` | `ARRET-3` · 5 LLM · **$0.035731098** · 10 findings · REQUIRE_APPROVAL |
| 16 | Decision engine | `python -m orvyren.decide --case usdc-2023-03 --replay` | `CONCLUANT` · RDOF c1 after 1 search · 0.65 s |
| 17 | Execution demo | `run_execution_demo.py` | I1 ALLOW · I2 DENY (2 codes) · I3 REQUIRE_APPROVAL · 4th transfer DENY |
| 18 | API / graph over HTTP | `curl /api/health`, `/api/graph/info` | `200` · `nodes.count 16174` · `relations.count 12937` |
| 19 | Q1/Q4/Q7 latency | 5 calls each | 16–19 ms / 34–39 ms / 15–17 ms |
| 20 | SPA screens / routes / fallback UI | `frontend/src/features`, `routes.py`, `screen_ids()` | 5 screens · 25 endpoints + `/ws/live` · 12 HTML screens |
| 21 | Evaluation | `evidence/eval_run.lock` | present (burned) — **N = 0** |
| 22 | ADR index | `python scripts/adr_index.py --check` | `ADR INDEX OK — 4 entries` |

**How to verify** — every command in the *Command* column above is runnable from the
repository root and prints the result in the *Result* column; no row depends on our
hardware except the timings in rows 1 and 19.

## 12. Known limits

The authoritative list is the gap register
[`SUBMISSION_SCOPE_AND_GAPS.md`](SUBMISSION_SCOPE_AND_GAPS.md) §*Gap register* (G-1 …
G-18), with the per-finding ledger in [`ECARTS_REGISTRE.md`](ECARTS_REGISTRE.md).

| Id | Limit | Consequence |
|---|---|---|
| **G-12** | `--execute` never exercised end to end; the 13 testnet transactions were signed by a human key | no claim of autonomous signing |
| **G-1** | evaluation `N=1` (first EVAL, 2026-10-19; one window, far below N≥100) | no measured decision gain, no superiority claim |
| **G-14** | the 16 174-node graph is a local artifact with a reconstruction pipeline | a clean clone shows the 520-observation snapshot; the UI says which |
| **G-4** | Q2 `NO_PATH` on the Aave slice; Q8 `NOT_INGESTED` | dependency and permission questions answered "unknown", not fabricated |
| **G-2 / G-7** | no archived rsETH market series; realisable value of frozen collateral unreadable | the −31 % divergence is a documented point, not a measured series — the critic raises it as blocking |
| **G-3 / G-6** | no recorded response store for `rseth-2026-04`; the sealed seed's critic cites one unobserved ref | offline replay of that case unavailable; the strict critic-side ref gate is deferred (re-seeding is the fix) |
| **G-13** | the packaged scenario report still drives the corpus leg for execution | code-level closure exists (`--decision-source agents`); the report is to be regenerated |

Contract and data limits: **Q7 `debt_backed`** (fixture implementation) sums all
visible `OWES` rows without an asset filter — pinned by a frozen test, never an
exposure metric; the filtered measure is `graph/api.concentration` (G-8, G-15).
**`hashes_complete`** in Q6 is structurally `True` (fingerprint recomputed on the
fly): "every hop carries a fingerprint" is true, "the flag proves it was compared" is
not. **`node_detail`** transports at most 200 relations with no REST pagination (the
count is honest: `relation_count`, `relations_truncated`). **No JS test runner** and
**a French SPA** next to an English fallback UI — both left as-is for this submission.

Explicit non-claims, because these are the sentences that would inflate the system:
**not** "12 preflight controls" (there are 10); **not** "autonomous signing service in
production" (the path exists, is tested, never signed by itself); **not** "embeddings
/ semantic search in v1" (V2 by ADR-0003; the only retrieval is FTS5 behind
`--memory`); **not** "working/episodic/semantic memory" (one lexical FTS memory,
optional, off by default); **not** "static HTML UI without JavaScript" (the product UI
is a React SPA; the 12-screen HTML UI is the fallback); **not** "PostgreSQL" (SQLite);
**not** "35 relations" (35 kinds defined, 13 in fixtures, 1 in the shipped graph);
**not** "decision gain proven" (`N=1`, against an `N≥100` threshold).

**How to verify** — `python run_verify.py <packet>.zip --mutate-test` (the audit claim)
and `test -f evidence/eval_run.lock` (the evaluation claim) close everything above.

A system that abstains, refuses and writes down what it could not measure **is** the
product. This document is written so a reader can check that claim rather than
believe it.
