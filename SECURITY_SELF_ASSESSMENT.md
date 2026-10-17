# ORVYREN-Core — Security self-assessment (permission tiers × risks × tests)

**Version**: ORVYREN-Core v0.1 · **Date**: 2026-10-14 · **Scope**: everything under `src/orvyren/`, the top-level runner scripts and the evidence chain, as built for the 2026 Shenzhen International FinTech Competition (Topic F).

This document maps the **permission tiers** the system is allowed to reach, the **risks** attached to each tier, and the **tests** that hold the line. Everything claimed here was executed; nothing is a roadmap item unless explicitly marked *(not implemented)*.

---

## 1. Design invariants (the rules the rest of this document refers to)

1. **The agent never holds a key.** No module of the decision / policy / research path signs or broadcasts, and no key material is ever recorded (all 13 `SUBMIT` lines of the `rseth` demo carry `key_material: "never recorded"`). **Correction (2026-10-17, M11)** — the blanket claim must not be read as « nothing was ever signed »: the T2 testnet demonstration broadcast 13 transactions signed by a dedicated human-held demo key, outside the agent and outside this repository (see §3bis for the receipts). The agent produced only unsigned bounded instructions, and the system verified the results afterwards (read-only JSON-RPC).
2. **The policy service is deterministic and outside any LLM.** `src/orvyren/policy` computes ALLOW / DENY / REQUIRE_APPROVAL from structured `Intent` fields only. No model output, text, or justification string is ever parsed as an instruction.
3. **Nothing executes without an explicit ALLOW.** `orvyren.execution.guard.assert_allowed()` raises for every other verdict; the demo asserts 0 out-of-policy actions.
4. **No number without provenance.** Every figure in the decision output references corpus observations; a claim without a resolvable reference is refused by the graph store.
5. **The archive is a proof.** The corpus is window-bounded, hashed (LF-normalised), the graph store is append-only (SQLite triggers), and the dossier carries a recomputable self-hash.

## 2. Permission tiers as implemented

| Tier | Capability | Key material | Status |
|---|---|---|---|
| **T0 — Read-only analytics** | read the archived corpus, compute quality/coverage, read chain data (chain id, receipt, balanceOf) | none | implemented |
| **T1 — Decision artefacts** | produce a decision candidate, an audit dossier and at most one **unsigned** transfer instruction (token contract + calldata) | none | implemented (demo executed) |
| **T2 — Bounded test execution** | the *human* sends the allowed transaction on Base Sepolia (test USDC, ≤ 100 per tx, ≤ 300 cumulative, 24 h permission, allowlisted recipient); the agent verifies the ERC-20 receipt against the authorized intent | human wallet only | ready; receipt verification runs when `ORVYREN_TX_HASH` is provided |
| **T3 — Extended actions** (swap / approve / anything else) | — | — | **REQUIRE_APPROVAL by construction — never autonomous** |
| **T4 — Policy or configuration change** | — | — | **REQUIRE_APPROVAL by construction — never autonomous**; the engine cannot widen its own envelope |

## 3bis. The 13 receipts of the `rseth` demo — 12/13 distinguished

The manifest counts `submits: 13, receipts: 13, signatures: 13` without
distinguishing their outcomes. The honest breakdown (measured, Base Sepolia,
2026-10-16, run `01M526YS3FMDNS6Z9EJYJPPG1E`) is:

| # | nonce | intent | scenario | receipt status | outcome |
|---|---|---|---|---|---|
| 1 | 1 | run A | the single in-policy bounded transfer | `0x1` | **success (the only one)** |
| 2 | 2 | `forced-C1` | 500 USDC over the `maxRefill` allowance | `0x0` | REVERTED by the module |
| 3 | 3 | `forced-C2` | 1 USDC to an unlisted recipient | `0x0` | REVERTED by the module |
| 4 | 4 | `forced-C1` | second attempt, same over-cap transfer | `0x0` | REVERTED by the module |
| 5 | 5 | `forced-C2` | second attempt, unlisted recipient | `0x0` | REVERTED by the module |
| 6 | 6 | `forced-C3a` | `allowTarget` (agent widens its own allowlist) | `0x0` | REVERTED by the module |
| 7 | 7 | `forced-C3b` | `Safe.enableModule` (agent takes over the Safe) | `0x0` | REVERTED by the Safe |
| 8–13 | 8–13 | `forced-C4` | cumulative-cap loop (repeated bounded transfers) | `0x0` ×6 | REVERTED by the module |

**The 12 reverts are the security demonstration, not failures**: every forced
attack was deliberately broadcast against the real module, and the chain
refused it (`status 0x0`, empty logs). One caveat is journaled honestly: for
several reverts the RPC could not return the revert reason
(`"block not found"` in the `VERIFY` lines), so the authority is the receipt
`status` — not a decoded revert selector. The single success (nonce 1) is the
only transfer that matched the authorized intent on chain id, token, sender,
recipient and exact base units (R7 matrix).

## 3. Risk register

Format: risk → control → evidence (test names live in `tests/`) → residual risk.

| # | Risk | Control | Evidence | Residual |
|---|---|---|---|---|
| R1 | Key custody / signing | no signing or broadcast code path exists; sensitive env vars (names list in `execution/guard.py`) are detected by name only, values never read; RPC URLs masked before any message | `guard` masking tests; demo prints `secret env vars detected (names only): none`; `execution/chain.py` exposes read-only methods only | human wallet hygiene outside scope |
| R2 | Policy bypass (action without verdict) | single deterministic gate `policy.evaluate()`; `guard.assert_allowed()` refuses anything but ALLOW before an instruction is prepared; architecture dependency rule (`execution` accepts only a `PolicyDecision.verdict == ALLOW`) | `test_policy.py` (12, incl. the 7 pre-declared attacks); `test_execution.py` guard tests; demo `guard_blocks` shows I2/I3 refused | future code paths must keep the gate — enforced by review + tests |
| R3 | Replay / double-send | idempotency by `intent_id` (R7), 24 h permission expiry (R6) | `test_05_intent_rejoue`, `test_06_permission_expiree`, `test_11_permission_absente` | none observed |
| R4 | Cap evasion (per tx / cumulative) | 100 per tx · 300 cumulative enforced in policy; env overrides validated (`> 0`) | `test_02`, `test_08`; `ORVYREN_MAX_*` parsing tests | none observed |
| R5 | Allowlist abuse (agent adds a recipient) | recipient allowlist (R3-recipient); any policy/config change is REQUIRE_APPROVAL; no autonomous path mutates configuration | `test_01`, `test_09`; `change_policy` intent → REQUIRE_APPROVAL in the demo | none observed |
| R6 | Data / oracle manipulation | three independent price producers with declared limits; corroboration criteria (H3) reject unexplained single-source divergence; hourly data gate; every claim carries observation refs in an append-only store | `test_quality_graph.py` (26); provenance 4/4 claims verified; `data_gate` tests; H3 divergence detection in `scenarios.py` | aggregator lag/coverage documented; not a market-data oracle |
| R7 | Receipt forgery / wrong transaction accepted | verification compares the decoded ERC-20 Transfer log against the authorized intent on **chain id, token contract, sender, recipient and exact base units**; missing status / missing transfer log / failed statuses are refused (fail closed) | `test_execution.py` mismatch matrix (wrong recipient, sender, amount, token, chain, failed/missing status, no log) | receipt + chain id are read from a read-only RPC: an honest node is assumed (documented) |
| R8 | Prompt / data injection | `Intent` is a typed dataclass; policy reads structured fields only; justification text is recorded, never executed; no LLM anywhere in the decision/policy path | `test_07_injection_de_donnee_externe`; architecture rule: an LLM (if ever used) is confined to the research layer and never produces a number | future LLM research layer must keep this boundary |
| R9 | Secret leakage into logs / git | masking helpers; values never read for sensitive names; `.env` git-ignored; `.env.example` carries placeholders only; evidence artifacts contain no secrets | `guard` tests; demo output; `.gitignore` secrets section | operator-supplied env hygiene |
| R10 | Supply-chain risk | Python standard library only (no runtime dependencies); `LICENSES.md` tracks every component and data source; CI runs offline | imports audit; CI (tests + full pipeline + offline replay) | stdlib updates are the runtime's responsibility |
| R11 | Evidence tampering | append-only SQLite (UPDATE/DELETE refused by triggers); content-addressed observations; canonical snapshot hash; dossier self-hash; LF-normalised digests + `.gitattributes`; pinned rebuild (`--generated-at`) | store trigger tests; snapshot stability tests; `tests/test_integrity_reproducibility.py` (16) | nothing can prevent someone editing a checkout — the hashes make it detectable |
| R12 | Scope creep / real funds | chain fixed to Base Sepolia (84532) only; test-USDC asset allowlist; demonstration exposure envelope (500 / 350 / 100 USDC); D4 exclusions list; no token issued, no performance promise | `test_policy.py` R1/R2 tests; `FREEZE_V1.md` D4/D5/D8; config defaults | none — deliberately bounded |

## 4. What is deliberately NOT in scope (v0.1)

- Mainnet, real funds, multi-chain, EAS attestation, ERC-7715 sessions, parallel multi-agent execution (see `FREEZE_V1.md` D4).
- Autonomous T3/T4 actions — they can only ever be *prepared for a human*.
- A key-management story for the agent: by design there is no key to manage.

## 5. Open items (tracked, with owners)

1. **Testnet evidence acceptance** — pending a written answer from the organizers (is a Base Sepolia transaction hash acceptable as execution evidence?). Until answered, evidence is labelled accordingly.
2. **Receipt verification against a real transaction** — ready (`verify_receipt` + read-only client); runs as soon as a human executes the demo transfer and exposes `ORVYREN_TX_HASH`.
3. **Receipt/chain-id trust in RPC** — documented assumption (read-only node); a future hardening step could query two independent RPC endpoints.

## 6. How to re-run the claims

```bash
python -m unittest discover -s tests          # 132 tests, all green (2 skipped: opt-in live-RPC)
python run_pipeline.py                        # rebuild every evidence artefact from the archive
python run_execution_demo.py                  # policy verdicts + unsigned instruction + guard blocks
sha256sum corpus/usdc_observations.csv        # equals the digest recorded in evidence/decision_usdc-2023-03.json
python -m unittest tests.test_integrity_reproducibility -v   # platform-stable digests, pinned rebuilds, window contract
```
