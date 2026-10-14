# ORVYREN-Core

**A finance decision engine with a verifiable audit trail and a policy-gated on-chain action.**
Pilot case: a treasury decision when a stablecoin (USDC) shows a price/liquidity anomaly — March 2023 (SVB) episode, reconstructed point-in-time.

Submission context: 2026 Shenzhen International FinTech Competition — International Track, **Topic F (Agent Wallet / Autonomous On-chain Wallet)**. Submission deadline: **20 October 2026, 15:59 UTC**.

---

## What is actually implemented today (no placeholders)

| Piece | State | Proof |
|---|---|---|
| **Policy service** — deterministic ALLOW / DENY / REQUIRE_APPROVAL, computed outside any LLM | **Implemented, tested** | `src/policy.py`, 12 tests green (`tests/test_policy.py`) |
| **Safety bench** — the seven pre-declared attacks (wrong recipient, amount above cap, unlisted asset, wrong chain ID, replayed intent, expired permission, prompt injection) + cumulative cap, approval-only actions, unknown action | **Implemented, tested** | `python -m unittest discover -s tests -v` → 12/12 OK |
| **Corpus collector** — real historical data with retrieval timestamps and a source manifest | **Implemented, ran** | `collect_corpus.py` → `corpus/` (`manifest.json`, `usdc_observations.csv`, raw payloads) |

Everything else (fact graph, branch registry, decision engine, audit page, wallet execution) is **planned and not yet written** — see `FREEZE_V1.md` §6 for the build order. Nothing in this repository claims to work if it does not.

## Layout

```
orvyren_core/
├── FREEZE_V1.md          décisions à geler avant de coder (D1–D12) + inconnues
├── collect_corpus.py     collecteur de corpus horodaté (stdlib uniquement)
├── corpus/               corpus archivé : raw/, manifest.json, usdc_observations.csv, README.md
├── src/policy.py         service de politique déterministe (hors LLM)
└── tests/test_policy.py  banc de sûreté (7 attaques + cas nominal + plafonds)
```

## Run

```bash
python collect_corpus.py            # collecte réseau (~4 min) ; réécrit corpus/
python collect_corpus.py --offline  # rejoue l'archive, sans réseau
python -m unittest discover -s tests -v
```

## Data rules (non-negotiable)

1. **Testnet prices are never used as market context.** All decision inputs come from real market data; the testnet is only where the bounded action is executed.
2. **Point-in-time only.** A historical analysis may use only what was available at the simulated instant; later sources are labelled as *ex post* context.
3. **One source is not independence.** An aggregator price and a single venue price can share the same underlying data; the corpus stores aggregator + two independent venues so *between-venue* gaps can be measured.
4. **The issuer statement is documentation, not truth.** It is stored as a dated reference to be read and quoted, never auto-summarised into a fact.

## Policy envelope (proposal D9 — to be frozen)

Chain Base Sepolia (84532) only · one allowlisted test asset (USDC) · one allowlisted recipient (reserve wallet) · 100 USDC per transaction · 300 USDC cumulative · 24 h permission expiry · idempotency by `intent_id` · everything outside this envelope is **DENY**; exposure or configuration changes are **REQUIRE_APPROVAL** — never autonomous.

## Deliberately not included in this slice

Multi-chain, graph database, parallel multi-agent cluster, on-chain attestation (EAS), ERC-7715 permissions, real mainnet funds, investment advice, performance promises. Each reopens only with a measured need.

## Required submission pieces (competition)

Technical documentation (EN) · presentation deck (≤ 10 min) · **demo video (≤ 5 min)** · source code with README, deployment instructions and tests · security self-assessment (permission tiers × known risks) · execution evidence (real on-chain transaction hash + receipt, plus a documented refusal).
