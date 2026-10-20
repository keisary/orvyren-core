# ORVYREN-Core — Security Report

**Submission artefact** — 2026 Shenzhen International FinTech Competition, Topic F (agent
wallet / bounded autonomous on-chain execution). Repository `orvyren-core`.

**Measured on** 2026-10-20, tree at commit `3cca017`
(`3cca0175778395ecf731396440cb998d12a66c76`, HEAD of `master`), Windows 11, CPython 3.11.15,
from the repository root. Every figure below was re-measured on this exact tree in this
pass; nothing under `src/`, `tests/` or `scripts/` was modified by this documentation pass.

**Measurement rule.** Every figure below comes from a command quoted beside it and run
during this pass; what could not be exercised is written **not measured** or **not
exercised**, never inferred from the design. Each capability sits at one of three
levels — *implemented* (module + tests), *wired* (called by the runner), *exercised*
(run, with an artefact): a tested module is not a capability until it is wired, and a
dry run proves nothing about a live chain.

---

## 1. Scope and method

**Audited surface.** `src/orvyren/policy/` (deterministic first lock),
`src/orvyren/execution/` (`preflight.py`, `guard.py`, `loop.py`), `src/orvyren/chain/`,
`src/orvyren/agents/` (tool bounds, provenance, budget), `src/orvyren/verify/`,
`src/orvyren/api/`, `scripts/demo/check_env_hygiene.py`, `scripts/inspect_env_masked.py`,
the Base Sepolia envelope (Safe + Zodiac Roles v2) and the audit packet in
`evidence/audit_packets/`.

**Out of scope, declared.** Mainnet and custody of real funds, the operator's key hygiene outside the repository, LLM
provider internals, the npm/Vite build, the honesty of public RPC endpoints. No external firm has audited this code (§7).

**Method, per control.** Read the enforcing code → name the test that holds the line → run
it or the artefact verifier → record the residual risk the control does *not* remove. §8
gives every command, so nothing here must be taken on trust.

---

## 2. Permission tiers

The agent is an EOA that is a **member of a narrowly scoped Zodiac Roles role**, with no
administrative right anywhere: it cannot widen its own envelope, install a module, or
change policy.

| Tier | Capability | Key material | Implemented | Exercised | Refused by construction |
|---|---|---|---|---|---|
| **T0 — Read-only analytics** | corpus/graph reads; `eth_chainId`, `eth_getBalance`, `eth_getCode`, `eth_call` | none | yes | yes (graph API, verify engine, preflight) | — |
| **T1 — Decision artefacts** | decision record, unsigned intent (token + calldata), audit dossier | none on the decision path | yes | yes (dry-run executor, 1 and 5 ticks) | non-`ALLOW` verdicts stop at `guard.assert_allowed()` |
| **T2 — Bounded testnet execution** | one allow-listed ERC-20 transfer: ≤ 100/tx, ≤ 300/24 h, 24 h intent TTL | a dedicated key held **outside** the agent process | yes | **partial**: 13 Base Sepolia transactions signed by a human-held demo key; the system's own `--execute` path has **never** run end to end (G-12) | policy P1–P14, preflight 10 controls, on-chain role |
| **T3 — Extended actions** (swap, approve, `change_policy`, revoke) | — | — | none by design | no | `ACTIONS_SOUS_APPROBATION` → `REQUIRE_APPROVAL`, never autonomous |
| **T4 — Policy or configuration change** | — | — | none by design | no | no code path mutates policy or the role; `assignRoles` is a Safe transaction needing 2 of 3 owners |

---

## 3. Threat model

Asset → threat → control → **exact test** → measured result → residual risk.

| # | Asset | Threat | Control | Exact test | Measured result | Residual risk |
|---|---|---|---|---|---|---|
| 1 | Treasury funds | over-cap transfer | policy P5/P6 + on-chain allowance 300 USDC/24 h | `tests.test_policy.TestPolicyBench.test_02_montant_au_dessus_du_plafond`, `test_08_plafond_cumule` | pass; on chain the same attempt (`forced-C1`) reverted `status 0x0` | a policy bug can still authorise a wrong-but-in-cap transfer |
| 2 | Treasury funds | unlisted recipient | policy P3 **and** role condition `Or(EqualTo(B), EqualTo(C))` | `tests.test_policy.TestPolicyBench.test_01_destinataire_hors_allowlist` | pass; `forced-C2` reverted `0xd0a9bf58` (condition, not `NoMembership` — the agent *is* a member) | recipient addresses live in `scripts/demo/.env`, unversioned |
| 3 | Key material | key reaching LLM, logs or git | no signing code on the decision path; sensitive names read by **name only** | `tests.test_execution.TestGuard.test_mask_secret_never_reveals_the_value`, `test_mask_rpc_url_hides_api_keys` | pass; `check_env_hygiene.py` → `VERDICT: OK` | operator machine compromise out of scope |
| 4 | Safe control | agent widens its allow-list / installs a module | role target has `Function` clearance on USDC only; one function `transfer(address,uint256)`; no admin permission | `tests.test_policy_zodiac_conformance.TestOfflineConformance.test_fixture_et_politique_conformes` | pass; `forced-C3a` (`allowTarget`) reverted by the module, `forced-C3b` (`Safe.enableModule`) by the Safe | mastercopy has had incidents — version pinned to v2.1.1 |
| 5 | Whole envelope | agent keeps acting after an incident | kill switch `assignRoles(agent,[AGENT],[false])`, one Safe transaction | run D: `evidence/demo_runs/rseth/runs/rseth_20261016T113026Z_463CFD/summary.json` | revocation tx `0x0fb96134…9a41` `0x1`; next agent attempt `0xe9be566f…272b` reverted `0xfd8e9f28` = expected selector | revocation costs one block (~2 s on Base); no automatic trigger |
| 6 | Decision integrity | prompt injection steers a tool call | closed schemas (`additionalProperties: false`), bounded `limit`/`max_depth`/`as_of_block`, `deadline_s ∈ (0, 600]` enforced | `tests.test_agents_provenance_bounds.GraphToolBoundsTest` (11 tests) | 11/11 pass, incl. `test_the_deadline_is_enforced_not_decorative` | injection can still waste budget — bounded, not impossible |
| 7 | Evidence | fabricated references in a claim | provenance P0-6: cite only what the run observed | `tests.test_agents_provenance_bounds.JournalWriteRefValidationTest.test_a_claim_citing_an_invented_ref_is_rejected_but_visible` | pass: `E_REF_NOT_OBSERVED`, line kept visible, excluded from the critic packet | sealed seed's critic still cites one unobserved ref (G-6) |
| 8 | Treasury funds | replay / double spend | 24 h intent TTL, processed-id set, P10 content fingerprint | `tests.test_execution_preflight.IntentStateTest.test_replayed_intent_is_refused`, `test_expired_intent` | pass | processed-id set is per-run ledger state, not a global nonce registry |
| 9 | Funds | signed on the wrong chain | preflight P2 `CHAIN_ID_MISMATCH` | `tests.test_execution_preflight.PolicyAndChainTest.test_chain_id_mismatch`, `test_chain_id_transport_error_is_fail_closed` | pass (RPC failure ⇒ FAIL, never PASS) | a lying RPC is trusted (§6) |
| 10 | Funds | wrong token / no code at target | preflight P7 + packet check A8 | `tests.test_execution_preflight.ChainFactsTest.test_missing_contract_code`; `tests.test_verify_engine.VerifyEngineEndToEndTest.test_offline_pass_with_b_skipped` | pass; A8 cross-checks every receipt's Transfer log against the authorised intent | — |
| 11 | Audit trail | silent edit of journal, dossier, receipt or verifier | `RunChain` (hashed events, sha256 manifest, handoff check) + frozen verifier | `tests.test_chain_run_id` (35); `python run_verify.py … --mutate-test` | `verify() → (True, '')`; mutations **6/6 detected** | detection, not prevention |
| 12 | Secrets | key committed to git | `.gitignore` + value scanner over tracked files | `tests.test_env_hygiene` (8); `scripts/demo/check_env_hygiene.py` | `H1/H2/H3/H5 PASS`; `H2` = no key value in **1214** tracked files; `H4` skipped (not POSIX) | a key pasted into an untracked file is invisible to this scan |
| 13 | Spend | runaway LLM/tool cost | ceilings `llm_calls 30 · tool_calls 12 · wall_seconds 600 · cost_usd 0.10`, `_refuse_widened_budget`, stop `ARRET-2` | `tests.test_agents_provenance_bounds`, `tests.test_agents_plan_recovery` (11) | pass; a run may tighten a ceiling, never widen it | provider-side billing errors are outside the loop |
| 14 | Local API | anyone on the machine drives the dashboard | binds `127.0.0.1:8321` by default (`api/config.py:43`) | **no test asserts the absence of authentication** | no `Authorization`/`Depends`/API-key handling exists in `src/orvyren/api/` | **declared gap**: no auth; loopback is the only boundary |
| 15 | Supply chain | malicious package in the runtime | standard library only in the core | `tests.test_execution_preflight.SourceHygieneTest.test_module_is_stdlib_only_and_lf`; import inventory (§6) | pass; `src/` imports only `fastapi`/`uvicorn` (lazy API boundary) outside the stdlib | the npm build is not audited |

---

## 4. Controls by component

### 4.1 Policy — the deterministic first lock (`src/orvyren/policy/`)

- **14 rules, off-LLM**: `RULES_V1` = `P1-chain · P2-asset · P3-recipient · P4-function
  · P5-amount · P6-cumulative · P7-exposure · P8-permission · P9-freshness ·
  P10-idempotency · P11-pause · P12-envelope · P13-action · P14-budget`. Input is a typed
  `Intent`; no model text is ever parsed as an instruction. Verdict order is
  `DENY > REQUIRE_APPROVAL > ALLOW`, with denial codes from a frozen registry
  (`DENY_CODES_V1`), never free text.
- **Fail-closed by default.** `evaluate()` runs in `EVAL_MODE_PRODUCTION`: without a
  `PolicyState` the verdict is `DENY`, reason `STATE_REQUIRED`, and the state rules are
  recorded `FAIL`, never `SKIPPED` (`TestEvaluationModes.test_production_default_without_state_refuses`).
  Omitting `mode` is production (refusal); simulation must be declared
  (`test_simulation_must_be_declared_never_implicit`).
- **`policy_hash` on every decision** = `sha256(yaml_sha256 + ":" + code_sha256)`.
  Measured here: `651535872228470403f5603982eaadd9c4143c700f0ce159813f9edc7164ad5d`
  (yaml `b99ad99b…0c03`, code `82c52d87…ca80`); tests
  `TestPolicyV1Bundle.test_empreintes_coherentes`, `test_verdict_porte_version_et_empreinte`,
  `test_yaml_modifie_change_empreinte`.
- 52 policy tests + 17 parameter tests + 8 Zodiac-conformance tests, all green.

### 4.2 Preflight — the second lock before any signature

Ten real controls, in a declared order, stopping at the first failure. `P6`, `P8` and `P10`
of the wider design **do not exist** in this slice: absent from `CHECK_ORDER` rather than
silently passing. The order is:

> P1 `POLICY_NOT_ALLOW` → P2 `CHAIN_ID_MISMATCH` (unreadable chain id included) → P3
> `INTENT_EXPIRED` (24 h TTL, naive datetime refused) → P4 `INTENT_ALREADY_PROCESSED` → P5
> `AGENT_PAUSED` → P7 `TARGET_CODE_MISSING` → P12 `GAS_ESTIMATE_FAILED` (estimate
> failure/zero **or** an amount/recipient that cannot be ABI-encoded) → P9a
> `INSUFFICIENT_GAS_BALANCE` (balance < 2 × estimate) → P9b `INSUFFICIENT_TOKEN_BALANCE` →
> P11 `SIMULATION_REVERT` (`eth_call` revert, or a `false` return).

Properties held by 43 green tests (`tests.test_execution_preflight`): stop-at-first, with
later checks `SKIP … "not evaluated: <code>"`; every code in the catalogue
(`test_every_failure_code_is_a_catalogue_code`); transport errors are failures
(`test_chain_id_transport_error_is_fail_closed`, `test_get_code_error_is_fail_closed`);
amounts are integer base units, refusing scientific notation, signs and excess decimals
(`AmountConversionTest`); error text never leaks the endpoint, which may embed an API key
(`test_error_envelope_raises_without_leaking_the_endpoint`); nothing outside the standard
library is imported (`SourceHygieneTest.test_module_is_stdlib_only_and_lf`).

**Wiring, measured.** The gate runs only on the real path, before the signer: `run_loop`
records `PREFLIGHT_REFUSED`, sets `executed=False`, stops with `stopped="preflight"` and
leaves `counts["signed"] == 0`; a non-mapping answer is a refusal (`PREFLIGHT_UNAVAILABLE`);
configuration is checked **by variable name**, and a missing name refuses at start-up. A
dry run never calls the preflight. Tests: `tests.test_execution_wiring` (12 green), incl.
`PreflightGateTests.test_refusal_blocks_the_signature`, `test_dry_run_never_calls_the_preflight`
and `PreflightConfigTests.test_missing_configuration_is_refused_by_name`.

### 4.3 On-chain envelope — the second lock on chain (Base Sepolia)

| Component | Measured value |
|---|---|
| Safe | `0x000e11a54daadf202542a0136f974f24d7c38be0`, 2-of-3 (two signers recorded in `evidence/demo_runs/setup/dao_assign_roles_last.json`) |
| Roles module | `0x7e2b7798ab4b4db837b30107f0d2a3ffb24e95e8` (45-byte proxy), mastercopy `0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5` |
| Mastercopy version | **v2.1.1**, 24 409 bytes, sha256 `89c5dc33…cd05`, source match 26/26 files (`evidence/demo_runs/setup/d10_resolution.json`) |
| Agent EOA | `0xe1039e345fa2ad9ecceab7bb160fd5e53f58f01c` — role member, no admin permission |

Role content (`fixtures/roles_agent_config.json`, captured read-only at block 48 192 974):
one target with `Function` clearance on USDC `0x036cbd53…cf7e` — **not** a broad `Target`
clearance; one allowed function `transfer(address,uint256)` `CALL`; condition
`param0 ∈ {B, C}`; condition `param1` `within_allowance usdc_daily` = 300 USDC refilled
every 86 400 s; call quota 10 per 86 400 s. No permission exists for `allowTarget`,
`scopeTarget`, `enableModule` or any Safe administration, so no policy or prompt can
produce one. `tests.test_policy_zodiac_conformance` (8 tests) checks that
`policy_v1.yaml` and the captured envelope agree, and that a simulated drift raises SAFE
MODE (`ENVELOPE_DRIFT` / `ENVELOPE_UNVERIFIED` → DENY).

### 4.4 Agents and LLM — bounded, provenance-gated, budgeted

- **Tool calling bounded by code**: closed argument objects, numeric ceilings
  (`E_TOOL_ARGS_RANGE`; a negative `limit` is refused because SQLite reads `LIMIT -1` as
  unbounded, while `0` stays a legal bounded value), `deadline_s` validated then
  **enforced** (`MAX_DEADLINE_S = 600`, `E_TOOL_DEADLINE` drops late data).
- **Provenance P0-6**: `ObservedRefs` is the run's ledger of references really returned
  by tools; a claim citing anything else is rejected with `E_REF_NOT_OBSERVED` at three
  gates (journal write, evaluation record, critic packet), stays visible, and is never
  swapped for a look-alike source.
- **Hard budgets, tighter-only**: `llm_calls 30`, `tool_calls 12`, `wall_seconds 600`,
  `cost_usd 0.10`. **Five fail-closed stops** `ARRET-1..5`; `ARRET-3` is the validation
  failure and the only non-orderly one. 25 green tests in
  `tests.test_agents_provenance_bounds`, 11 in `tests.test_agents_plan_recovery`.

### 4.5 Audit chain (`src/orvyren/chain/`)

`RunChain` writes hash-chained events (`run_id`, `case_id`, `stage`, `ts_utc`, `prev_hash`)
plus a `sha256` manifest per artifact, verified at every decision→policy→execution handoff;
a mismatch raises `ChainContractError` and stops the run. Real execution without an explicit
`--run-id` is refused with `E_CHAIN_RUN_ID_REQUIRED` (process code 4) before any tick.
Measured: `RunChain(...).verify() → (True, '')` on
`evidence/scenario_rseth/execution/chain/scenario-rseth-2026-04-20261019T134804Z` (2
artifacts, `parent_run_id` = the agents run). Tests: `tests.test_chain_run_id` (35), incl.
`test_real_mode_without_run_id_is_refused_fail_closed` and
`test_artifact_carries_its_provenance_envelope`.

### 4.6 Secrets hygiene

`scripts/demo/check_env_hygiene.py` — H1 no versioned `.env`, H2 no key value in tracked
files, H3 every local env file is git-ignored, H4 POSIX permissions (skipped on Windows),
H5 no secret name in the process environment — and `scripts/inspect_env_masked.py`,
which prints **names and lengths only**: measured output ends with
`ORVYREN_PRIVATE_KEY present (len 66) — never displayed`. `.gitignore` covers `.env` at
any depth, `scripts/demo/config.env`, `scripts/demo/owners.env`, `*.key`, `secrets/`.

---

## 5. Evidence of execution — the 13 Base Sepolia transactions

Session `01M526YS3FMDNS6Z9EJYJPPG1E`, 2026-10-16. Counted from the receipt files, not from a
summary: `evidence/demo_chain/rseth/receipts/*.json` → **13 files, 12 with `status 0x0`, 1
with `status 0x1`**. The tree re-verifies: `sha256sum -c MANIFEST.sha256` → **16/16 OK**.

| Intent | Count | Status | Refused by |
|---|---|---|---|
| run A — the single in-policy bounded transfer | 1 | `0x1` | — (the only success) |
| `forced-C1` — 500 USDC above the role's `maxRefill` | 2 | `0x0` | the Roles module |
| `forced-C2` — 1 USDC to an unlisted recipient | 2 | `0x0` | the Roles module (condition, `0xd0a9bf58`) |
| `forced-C3a` — `allowTarget` (agent widens its own target) | 1 | `0x0` | the Roles module |
| `forced-C3b` — `Safe.enableModule` (agent takes over the Safe) | 1 | `0x0` | the Safe |
| `forced-C4` — cumulative-cap loop | 6 | `0x0` | the Roles module |

Independent re-verification against the live chain:
`python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip --rpc https://sepolia.base.org`
→ `VERDICT: PASS — 26 checks, 0 failed` (10 receipts `REVERIFIED`).

**Re-measured 2026-10-20 — refreshed reference packet.** A second session
(`01M5CCNNTXNSC3YEVEPAJFBWWH`, 2026-10-20, Safe funded at 100 USDC) replayed the same five
runs end to end on Base Sepolia: **10 receipts — 1 `0x1` (run A's 100 USDC transfer) and
9 `0x0` chain refusals** — and 64 run journal entries. Its packet is
`evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip`, sha256
`63f4cefd905047eca2f71b4fa0c99fb05fb4cdb38bcc661919583f0c7592b83f`, `bundle_digest`
`dd8511cd…`: `OFFLINE_PASS — 16 checks, 0 failed`, `--mutate-test` **6/6**, and `--rpc`
`PASS — 26 checks, 0 failed`. The 16/10 packet was moved out of the repository
(`D:/orvyren_internal_2026-10-18/audit_packets_superseded/` + `SUPERSEDED_NOTE.md`) because
`A4.dossier.rerender` re-renders the dossier with the **current** code and
`src/orvyren/audit/dossier.py` changed after it was sealed — not because its evidence was
wrong: its own embedded verifier still prints `OFFLINE_PASS`.

**What this proves.** The envelope is real: a forced instruction set was broadcast against
the deployed module and the chain rejected 12 of 13 attempts while the one legitimate
transfer landed. The refusal is a receipt, not a policy log line.

**What it does not prove.** (a) The 13 transactions were signed by a **human-held demo key
outside the agent**; the system's own `--execute` path has never run end to end (G-12).
(b) For several reverts the RPC returned no decoded reason, so the authority is the receipt
`status`, not a selector. (c) Nothing here bounds judgement: a correct-but-harmful transfer
inside the caps is still allowed.

---

## 6. Scans and static analysis (run during this pass)

| Scan | Command | Measured result |
|---|---|---|
| Unit suite | `python -m unittest discover -s tests` | `Ran 1549 tests in 139.6 s — FAILED (failures=2, skipped=3)` — measured 2026-10-20 on `3cca017`; both failures are named just below |
| Skipped tests | `… -v` | 2 × `set ORVYREN_LIVE_RPC=1 …` (`TestLiveRpc`), 1 × "eth-account present: the library-missing path is not testable" |
| Bandit 1.9.4 | `python -m bandit -r src -f txt` | **40 findings, 0 High** (28 Medium, 12 Low) over 26 786 LOC, 0 `#nosec`: 22 × B608, 5 × B310, 5 × B110, 4 × B105, 2 × B311, 1 × B104, 1 × B101 — same rule mix as the previous pass, re-measured on `3cca017` |
| Ruff 0.16.5 | `python -m ruff check src scripts run_*.py` | `All checks passed!` — exit 0 over `src`, `scripts` and every `run_*.py` |
| Mypy 2.4.0 | `python -m mypy src --ignore-missing-imports` | `Found 101 errors in 24 files (checked 91 source files)` — untriaged, this is G-11 |
| Third-party verifier | `python run_verify.py <packet.zip> --mutate-test` | **re-measured 2026-10-20T10:12Z on `audit_packet_rseth_20261020-1012_01M5CCNN.zip`: `OFFLINE_PASS — 16 checks, 0 failed, mutations 6/6`** (packet rebuilt from the fresh 2026-10-20 session, so it re-renders with the current `audit/dossier.py`); the verifier shipped inside the zip prints the same. `--rpc` → `PASS — 26 checks, 0 failed` (10 receipts `REVERIFIED`) |
| Chain re-check | `… --rpc https://sepolia.base.org` | `PASS — 26 checks, 0 failed` (2026-10-20 packet, 10 receipts) |
| Secret hygiene | `python scripts/demo/check_env_hygiene.py` | `VERDICT: OK` (H4 skipped: Windows) |
| Dependency inventory | AST walk over `src/**/*.py` | 31 stdlib modules; outside the stdlib only `fastapi` + `uvicorn` (lazy API boundary) and two in-repo scripts imported on the execution/replay paths |

**Two tests fail on this tree — declared, not waived.** On `3cca017`, the suite ends
`FAILED (failures=2)`: `tests.test_agents_review_fixes.RunAgentsPathsAndTimeoutTest.test_run_stamps_never_collide_within_one_second`
(`AssertionError: 2 != 3` — two of three run stamps generated inside one second collided;
intermittent, it passes 3/3 when run alone) and
`tests.test_api_artifacts.TestArtifacts.test_audit_summary_chains_and_packets`
(`AssertionError: 1 not greater than or equal to 2` — the test requires two packets under
`evidence/audit_packets/`, and the superseded 2026-10-16 packet was moved out of the
repository on 2026-10-20, leaving exactly one). Neither failure touches a control of §3–§5:
one is a timestamp-collision flake in run-path naming, the other an artefact-count
assertion in the read-only API. Both are open defects at HEAD.

**Bandit triage, honestly.** B608 (22) marks SQL assembled by `%` formatting: the
interpolated fragments are table/column names taken from fixed tuples or from schema
introspection (`_columns`), never request text, and values are bound with `?`; the
connection is opened `mode=ro`. B310 (5) marks `urlopen` on operator-supplied endpoints.
B105 (4) marks constants whose *names* contain `TOKEN`/`PASS` (status and enum strings, not
credentials). B104 (1) is a `"0.0.0.0"` display fallback in the dossier server banner. None
is High, and none has been individually fixed: the backlog is declared (G-11), not closed.

**Not run, declared.** No external audit, no SCA/CVE scan (`pip-audit` absent), no fuzzing, no DAST, no formal verification; mypy is not a CI gate.

**Trust assumptions.** Chain reads assume one honest RPC; there is no cross-provider
agreement and no finality check beyond `latest`. The verifier assumes the packet it opens is
the packet delivered — its sha256 travels beside it (`audit_packet_…zip.sha256`, re-checked:
equal).

---

## 7. Known gaps and residual risks

The authoritative register is `docs/SUBMISSION_SCOPE_AND_GAPS.md`. Security-relevant
entries:

| Ref | Residual risk |
|---|---|
| G-12 | The system's own `--execute` path is preflighted but **never exercised end to end**; the 13 testnet transactions were signed by a human. |
| G-11 | Mypy backlog (101 errors measured on 2026-10-20 at `3cca017`) and 40 Bandit findings are accepted debt, not fixed. |
| §3 #14 | The local API has **no authentication**; the only boundary is the `127.0.0.1` binding, which `ORVYREN_API_HOST` can override. |
| G-6 | The sealed seed's recorded critic cites one reference absent from its packet; a strict critic-side gate needs a visible re-seed. |
| G-14 | The live scenario ran on the 520-observation `evidence/graph.sqlite`, not the 16 174-node local database. |
| — | No external audit or bug bounty; no key-management story beyond "the agent holds no signing key on the decision path"; no finality check, no cross-RPC corroboration, no on-chain nonce registry. Detection, not prevention: `RunChain` and the T10 verifier make tampering *visible*; they do not stop someone with write access. |

No stronger claim is made elsewhere in the submission: the other documents cite this report for their limits.

---

## 8. How to re-run every claim

```bash
python -V                                   # 3.11.15 used for this report

# 1. suite (1549 tests, 3 skips) and the per-control modules
python -m unittest discover -s tests -q
python -m unittest tests.test_execution_preflight tests.test_execution_wiring -q     # 43 + 12
python -m unittest tests.test_policy tests.test_policy_yaml tests.test_policy_zodiac_conformance -q  # 52 + 17 + 8
python -m unittest tests.test_chain_run_id -q                                        # 35
python -m unittest tests.test_agents_provenance_bounds tests.test_agents_plan_recovery -q  # 25 + 11
python -m unittest tests.test_env_hygiene tests.test_verify_engine -q                # 8 + 7 (mutations 6/6)
# 2. the policy hash actually carried by decisions
PYTHONPATH=src python -c "from orvyren.policy import load_policy; b=load_policy('policy_v1.yaml', recipients={'B':'0x37877f6ffb6656e752bf4807b9c3c7b761a953a3','C':'0x9f59adcdea0341e258e3ac98e7f9c57a2277760e'}); print(b.config.policy_hash)"
# 3. audit packet: offline, mutations, live receipts
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip --mutate-test
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip --rpc https://sepolia.base.org
# 4. demo receipts and their manifest
python -c "import json,glob,collections; g=glob.glob('evidence/demo_chain/rseth/receipts/*.json'); c=collections.Counter(json.load(open(f))['status'] for f in g); print(len(g),dict(c))"
(cd evidence/demo_chain/rseth && sha256sum -c MANIFEST.sha256)
# 5. run-chain integrity of the packaged scenario
PYTHONPATH=src python -c "from orvyren.chain import RunChain; c=RunChain('scenario-rseth-2026-04-20261019T134804Z','rseth-2026-04',parent_run_id='rseth-2026-04_live_20261018T200027592497Z',root_dir='evidence/scenario_rseth/execution/chain/scenario-rseth-2026-04-20261019T134804Z'); print(c.verify())"
# 6. secret hygiene and static analysis
python scripts/demo/check_env_hygiene.py
python scripts/inspect_env_masked.py        # names and lengths only
python -m bandit -r src -f txt
python -m ruff check src
python -m mypy src --ignore-missing-imports
```

**On-chain claims** (kill switch, role content) are re-read, not re-executed: they need a
funded Base Sepolia environment and human Safe signatures
(`scripts/demo/dao_assign_roles.py --enable false|true`, `scripts/demo/verify_addresses.py`).
This pass did not re-run them; the artefacts cited in §4.3 and §5 *are* the measurements,
and they stay byte-identical under the manifest check above.
