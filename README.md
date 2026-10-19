# ORVYREN — an on-chain wallet agent that decides, refuses and abstains — and proves it

**2026 Shenzhen International FinTech Competition — International Track, Theme F
“Agent Wallet / Autonomous On-chain Wallet”.**

ORVYREN turns public financial signals into **bounded, verifiable decisions**. It
crosses independent sources, formulates competing hypotheses, buys the one
observation that separates them, decides — or abstains and says exactly what is
missing — and never acts outside an authorised envelope: a deterministic policy
that lives outside the language model, plus on-chain permissions. Every step
leaves a trail a third party can recompute without our repository.

## The loop

```
observe ──▶ verify ──▶ graph ──▶ hypotheses ──▶ discriminating test
                                                        │
        prove ◀── execute (policy + envelope) ◀── decide ─┘
```

- **Deterministic by construction**: the policy, the decision calculus, the
  bounds, the audit chain. **LLM by design**: hypothesis generation, the choice
  of the next test, the adversarial critique. No number ever comes out of a
  model.
- Refusal is a first-class outcome: `DENY`, `REQUIRE_APPROVAL` and honest
  abstention (`ARRET-3`, with `what_would_change`) are recorded, not hidden.

## One real case

rsETH / KelpDAO, April 2026. The protocol's oracle still valued rsETH at
**2 526,76 USD** at the exploit instant while the market price dropped to
**1 686 USD** (documented divergence **-31 %**; the market series itself is not
archived — see the limits register). The reserve had saturated its supply cap
(**99,999 %**) and was frozen at block **24 908 723**, with utilisation at
**≈ 0,008 %** — the mechanism was a freeze, not the “100 % utilisation” of the
early briefs.

The live agents run of that case ends in **abstention**: `ARRET-3`, the critic
returns `INCOHERENTE`, escalation `REQUIRE_APPROVAL`, and **zero transactions
proposed**. The report lists the five observations that would change the
verdict. That run is the honest unit of work — it is shipped, byte-identical, in
`evidence/demo_runs/agents/rseth-2026-04/`.

## Try it

```bash
python -m unittest discover -s tests          # 1515 tests, OK (skipped=3) — measured 2026-10-18
python scripts/verify_frozen.py               # pre-registered evaluation protocol: COMPLIANT
PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay    # full decision, offline
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip
                                              # VERDICT: OFFLINE_PASS — 16 checks, 0 failed
```

Dashboard (offline, real state, no external resource):

```bash
cd frontend && npm ci && npm run build && cd ..
PYTHONPATH=src python -m orvyren.api           # http://127.0.0.1:8321
```

A single runbook, with the expected output of every step:
[`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Measured, not claimed

| What | Command | Result |
|---|---|---|
| Test suite | `python -m unittest discover -s tests` | 1515 tests, OK (3 skipped) |
| Third-party audit packet | `python run_verify.py <packet>.zip` | `OFFLINE_PASS`, 16 checks, 0 failed |
| Frozen evaluation protocol | `python scripts/verify_frozen.py` | `COMPLIANT` (byte-identical recalculation) |
| Policy | `policy_v1.yaml` + `src/orvyren/policy/` | 14 deterministic rules, production mode fail-closed |
| Execution preflight | `src/orvyren/execution/preflight.py` | 10 controls, stop at the first failure |
| Demonstration graph | `GET /api/graph/info` | 16 174 nodes · 12 937 relations · 15 000 Aave v3 Base events (database **not** shipped) |
| One agent run | shipped run summary | 0,0357 USD, 13 journal lines, abstention with 5 research leads |

## Architecture

| Module | Role |
|---|---|
| `data`, `quality` | connectors and quality gates; every figure carries its source and its unsured gaps |
| `graph` | relation catalogue (35 types), 17-field record, point-in-time queries Q1–Q8, append-only SQLite store, read-only API |
| `agents` | bounded MA-B loop: orchestrator + adversarial critic in separate processes, chained journals, native tool calling with strict JSON fallback, provenance gate, optional FTS memory |
| `decision` | deterministic RDOF search, three separate axes, abstention A1–A5, bridge that turns an agents run into the DecisionRecord |
| `policy` | the first lock: 14 rules, pure evaluation, no LLM, fail-closed |
| `execution` | intents, guard, 10-control preflight, bounded loop, receipt verification |
| `chain`, `audit`, `verify` | hash-chained run events, hashed artifacts per handoff, reproducible audit packet |
| `ui`, `api` | React/Vite SPA + FastAPI (`/ws/live`), plus a stdlib fallback UI |

Agent runs are two processes that never share memory: the orchestrator proposes,
the critic brakes. The critic never cancels a decision — it forces escalation.

## What this system does not do

Deliberately, and written down in
[`docs/SUBMISSION_SCOPE_AND_GAPS.md`](docs/SUBMISSION_SCOPE_AND_GAPS.md):

- **No measured decision gain.** The evaluation has not run (`N=0`); no
  superiority claim is made anywhere.
- **The autonomous signing path has never been exercised end to end.** It is
  implemented, preflighted and unit-tested; the 13 demonstration transactions
  were signed by a human-held testnet key (1 success, 12 forced reverts — the
  reverts *are* the demonstration).
- **No market series for rsETH.** The market price above is a documented point,
  not an archived series; the critic raises this as a blocking objection.
- The demonstration graph database is a local artifact with a reconstruction
  pipeline; the repository ships a smaller versioned snapshot, and the UI states
  which one it is reading.
- Q8 (permissions) is `NOT_INGESTED` on the Aave slice; Q2 returns `NO_PATH`
  because no dependency edges are populated there.

## Security

Safe 2/3 with a Zodiac Roles v2 module, an agent with no admin right and a kill
switch its owners can pull; a policy outside the model; a fail-closed preflight;
hash-chained evidence verified by a third-party tool. The full control-by-control
report — threats, exact tests, measured results, residual risks — is
[`docs/SECURITY.md`](docs/SECURITY.md).

## Repository

```
src/orvyren/     the system (data · quality · graph · branches · agents · decision ·
                 policy · execution · chain · audit · verify · replay · evaluation · ui · api)
scripts/         episode reconstructions, Aave ingestion, testnet demo kit
tests/           1515 offline tests
fixtures/        archived measurements used by tests and offline modes (+ their source notes)
evidence/        proofs: reconstructed episodes, audit packets, sealed agent runs, snapshots
corpus/          archived USDC/SVB March 2023 observations (offline replay)
frozen/          pre-registered evaluation protocol G1–G6 (sealed, byte-identical recalc)
docs/            technical note, security report, runbook, limits register, ADRs
```

Nothing in the repository is generated at import time, and the pipeline, the
episode reconstructions and the whole test suite run offline.

## Licence

MIT — see `LICENSE`. Third-party components and data sources: `LICENSES.md`.
