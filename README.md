# ORVYREN-Core

**A finance decision engine with a verifiable audit trail and a policy-gated on-chain action.**
Pilot case: a treasury decision when a stablecoin (USDC) showed a price/liquidity anomaly — March 2023 (SVB) episode, reconstructed point-in-time.

Submission context: 2026 Shenzhen International FinTech Competition — International Track, **Topic F (Agent Wallet / Autonomous On-chain Wallet)**. Submission deadline: **20 October 2026, 15:59 UTC**.

The design question this repository answers: *when three sources disagree about the same asset, what can an autonomous agent be allowed to do — and what must it prove afterwards?*

---

## Quick start (no dependencies, no network, no secrets)

Python 3.11, standard library only. From the repository root:

```bash
python -m unittest discover -s tests      # 116 tests (2 skipped: live-RPC, opt-in)
python run_pipeline.py                    # full pipeline end-to-end + evidence summary
python run_audit.py --serve               # one-page decision dossier on http://127.0.0.1:8000
```

Replay is offline by design: the corpus is archived under `corpus/`, and every stage reads the archive. Network is needed only to re-collect the corpus (`python collect_corpus.py --force`) or to verify a real on-chain receipt.

## What is implemented today (executed, not described)

| Piece | State | Proof |
|---|---|---|
| **Corpus collector** — multi-source, timestamped, with a declared-limits manifest | Implemented, ran | `collect_corpus.py` → `corpus/` (1 375 observations, 5 series, raw payloads + `manifest.json`) |
| **Data quality + provenance graph** — normalization, coverage, `data_gate`, append-only SQLite store with 12 triggers refusing UPDATE/DELETE | Implemented, tested | `run_quality.py` → `evidence/quality_report.json`, `evidence/graph.sqlite` (provenance: 4/4 claims OK) |
| **Decision engine** — pre-registered hypotheses H1/H2/H3 with falsification criteria, a frozen decision rule, and an INCONCLUSIVE path | Implemented, tested | `run_decision.py` → `evidence/decision_usdc-2023-03.json` (H1 REFUTED, H2 SUPPORTED, H3 REFUTED → ACTION_RECOMMENDED) |
| **Baseline A0** — the simple rule the project must beat, measured on crisis **and** control windows | Implemented, tested | `evidence/baseline_report.json` (2 signals in crisis, 0 in control → 0 false signals) |
| **Policy service** — deterministic ALLOW / DENY / REQUIRE_APPROVAL, computed outside any LLM | Implemented, tested | `src/orvyren/policy/`, `tests/test_policy.py` (7 pre-declared attacks, 12 tests) |
| **Execution layer** — policy-gated **unsigned** instruction (the agent never holds a key), human executes, agent verifies the ERC-20 receipt on-chain | Implemented, tested | `run_execution_demo.py` → `evidence/policy_execution_demo.json` (1 ALLOW, 1 DENY, 1 REQUIRE_APPROVAL) |
| **Audit dossier + viewer** — one self-contained page with sha256 of every input and a reproducible self-hash | Implemented, ran | `run_audit.py` → `evidence/dossier_usdc-2023-03.md` / `.html`; `python run_audit.py --serve` |
| **Pipeline orchestrator** — runs the four stages in order, records stage results and artifact hashes, fails loudly | Implemented, ran | `run_pipeline.py` → `evidence/pipeline_summary.json` |

Nothing in this repository claims to work if it does not: every row above was produced by running the command shown.

### Pilot case results (real numbers, reproducible from `corpus/`)

- Lowest hourly prints on 11 March 2023: **bitstamp 0.86267 (07:00Z) · DeFiLlama aggregate 0.87667 (08:00Z) · binance 0.91280 (15:00Z)** — the same asset, three different prices.
- Circulating supply: **41.63 → 32.89 bn USD** around the crisis (≈ −21%).
- Verdicts: **H1 (local perturbation) REFUTED · H2 (broad stress) SUPPORTED · H3 (data artifact) REFUTED** — H2 supported by 34 hours of simultaneous >1% deviation across two independent venues plus a −7.2% supply drop in 24 h.
- Decision: **ACTION_RECOMMENDED** — bounded transfer of **100 USDC (test)** from the treasury wallet to the reserve wallet, with 75 provenance references and the frozen rule stated in the rationale.
- Policy on the same intent: ALLOW for 100 USDC · **DENY** above the per-transaction or cumulative cap · **REQUIRE_APPROVAL** for any configuration change.
- Honest caveats, written into the outputs: exposure parameters are demonstration values (500 USDC envelope, 350 floor); corpus coverage is uneven (binance 83/145 h); the control window has no exchange observations.

## Layout

```
orvyren_core/
├── docs/REVIEW_KIT.md        start here for a review (onboarding, checklists, report format)
├── docs/                     technical + security documentation (EN)
├── FREEZE_V1.md              the 12 frozen decisions (D1–D12) + external unknowns
├── ARCHITECTURE_V1.md        execution model, module map, dependency rule, interfaces
├── collect_corpus.py         timestamped multi-source collector (stdlib only)
├── run_pipeline.py           end-to-end orchestrator + evidence summary
├── run_quality.py            data quality + provenance graph builder
├── run_decision.py           hypothesis classification + decision engine
├── run_execution_demo.py     policy verdicts + unsigned on-chain instruction
├── run_audit.py              dossier builder (+ --serve)
├── figure_divergence.py      the case figure (figures/usdc_divergence.png)
├── make_package.py           build dist/ review package (zip + sha256 manifest)
├── corpus/                   archived corpus: raw/, manifest.json, usdc_observations.csv
├── evidence/                 every produced artifact (json, sqlite, md, html) + hashes
├── src/orvyren/              policy · decision · quality · graph · execution · audit · ui
└── tests/                    policy safety bench + decision + quality/graph + execution + audit
```

## Data rules (non-negotiable)

1. **Testnet prices are never used as market context.** All decision inputs come from real market data; the testnet is only where the bounded action is executed.
2. **Point-in-time only.** A historical analysis may use only what was available at the simulated instant; later sources are labelled as *ex post* context.
3. **One source is not independence.** An aggregator price and a single venue price can share the same underlying data; the corpus stores the aggregator plus two independent venues so *between-venue* gaps can be measured.
4. **The issuer statement is documentation, not truth.** It is stored as a dated reference to be read and quoted, never auto-summarised into a fact.

## Policy envelope (frozen — FREEZE_V1 D9)

Chain Base Sepolia (84532) only · one allowlisted test asset (USDC) · one allowlisted recipient (reserve wallet) · 100 USDC per transaction · 300 USDC cumulative · 24 h permission expiry · idempotency by `intent_id` · everything outside this envelope is **DENY**; exposure or configuration changes are **REQUIRE_APPROVAL** — never autonomous. The agent holds **no key**: it emits an unsigned instruction, a human executes it, and the agent verifies the receipt against the authorized intent.

## Deliberately not included in this slice

Multi-chain, dedicated graph database, parallel multi-agent cluster, on-chain attestation (EAS), ERC-7715 permissions, real mainnet funds, investment advice, performance promises. Each reopens only with a measured need.

## Required submission pieces (competition)

Technical documentation (EN) · presentation deck (≤ 10 min) · **demo video (≤ 5 min)** · source code with README, deployment instructions and tests · security self-assessment (permission tiers × known risks) · execution evidence (real on-chain transaction hash + receipt, plus a documented refusal).
