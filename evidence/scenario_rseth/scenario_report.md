# Scenario report — rsETH / KelpDAO, April 2026 (E2E demonstration)

Case `rseth-2026-04` · scenario run_id `scenario-rseth-2026-04-20261019T134804Z` · agents run_id `rseth-2026-04_live_20261018T200027592497Z` · executor run_id `scenario-rseth-2026-04-20261019T134804Z` (parent `rseth-2026-04_live_20261018T200027592497Z`).
Decision source of the execution leg: **`agents`** — the per-tick DecisionRecord is built from the sealed agents run by `src/orvyren/decision/agents_source.py` (no pilot replay).
Every figure below is read from the sourced fixture (`fixtures/agents/rseth-2026-04/run_inputs.json`) at report time; each fixture figure points to its source and `tests/test_fixtures_rseth_inputs.py` crosses fixture against source at runtime.

## 1. Risk observed

Observed risk (Aave v3 Ethereum Core, rsETH reserve, KelpDAO collateral): the reserve saturated its supply cap at 2026-04-18T18:00:00Z (cap ratio 0.9999886466022144, 529993.9826991736 rsETH against a 530000 rsETH cap) and was administratively frozen at 2026-04-18T19:03:59Z (isFrozen 0 -> 1, block 24908723; last unfrozen block 24908722). The oracle retained 2513.66460329 USD at the freeze (2526.7563881 USD at the exploit instant 2026-04-18T17:35:00Z, 2419.21294349 USD on 2026-04-20T00:00:00Z) while the market price is documented at 1686 USD — a documented divergence of -31 % — and the market itself was frozen (no realisable exit). The documented exploit posted 89567 rsETH as collateral against roughly 190000000 USD of WETH borrowed.

## 2. Hypotheses

Concurrent hypotheses (ACH-style, frozen before the run; one counter-intuitive competitor kept alive on purpose):
  - HYP-001 [UNDER_TEST] — The rsETH reserve of the Aave v3 core market was administratively frozen (isFrozen 0 -> 1 at block 24 908 723, 2026-04-18 19:03:59 UTC): withdrawals are blocked from that instant.
  - HYP-002 [UNDER_TEST] — The value retained by the oracle diverges from the market price (about -31 %): valuing the position on the oracle overstates the realisable value of the collateral.
  - HYP-003 [UNDER_TEST] — The supply cap saturation (99.999 % at 2026-04-18 18:00 UTC) preceded the freeze and constrained the market: no new supply could enter before the administrative freeze.
  - HYP-004 (counter-intuitive) [UNDER_TEST] — Counter-intuitive competitor: the reserve is blocked by a full utilisation of the market (a 100 % utilisation leaves no cash to withdraw) - the freeze is only a symptom of a liquidity squeeze.

## 3. Evidence

The agents of the run observed the tools of the case (real LLM calls at run time). The sourced figures of the fixture and their sources:
  - [prices|chainlink|rsETH-USD] 2026-04-18T17:35:00Z = 2526.7563881 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-18T17:35:00Z)
  - [prices|chainlink|rsETH-USD] 2026-04-18T19:03:59Z = 2513.66460329 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-18T19:03:59Z)
  - [prices|chainlink|rsETH-USD] 2026-04-20T00:00:00Z = 2419.21294349 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-20T00:00:00Z)
  - [prices|chainlink|rsETH-USD] 2026-04-17T17:00:00Z = 2631.56608381 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_peak.price)
  - [prices|market|rsETH-USD] 18–20/04 = 1686 (doc:fixtures/sources/RSETH_MEASURE_2.md#measure-2)
  - [supply|rseth] 2026-04-18T18:00:00Z = 529993.9826991736 (evidence:episode_rseth_2026-04.json#headline.a_token_supply_at_cap_max)
  - [supply|rseth] 2026-04-18T19:03:59Z = 529482.808951789 (evidence:episode_rseth_2026-04.json#series["2026-04-18T19:03:59Z"].rsETH.a_token_supply)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] isFrozen_first_frozen_block = 24908723 (evidence:episode_rseth_2026-04.json#headline.rsETH_frozen_transition_block)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] isFrozen_last_unfrozen_block = 24908722 (evidence:episode_rseth_2026-04.json#freeze_transition.last_unfrozen_block)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] supply_cap = 530000 (evidence:episode_rseth_2026-04.json#headline.supply_cap_rsETH)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] cap_ratio_max = 0.9999886466022144 (evidence:episode_rseth_2026-04.json#headline.cap_ratio_max)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] cap_ratio_max_block = 24908406 (evidence:episode_rseth_2026-04.json#headline.cap_ratio_max_block)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] a_token_supply_at_cap_max = 529993.9826991736 (evidence:episode_rseth_2026-04.json#headline.a_token_supply_at_cap_max)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] rseth_utilisation_at_freeze = 7.946826023583168e-05 (evidence:episode_rseth_2026-04.json#series["2026-04-18T19:03:59Z"].rsETH.utilisation)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] weth_utilisation_peak = 1.0000792945348582 (evidence:episode_rseth_2026-04.json#headline.weth_utilisation_peak)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] collateral_rseth_at_exploit = 89567 (fixture:fixtures/graphs/rseth_2026-04.json#records[relation_id=rseth-collateralizes-weth-market].payload.amount)
  - [chain|ethereum|0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7] weth_borrowed_usd_at_exploit = 190000000 (fixture:fixtures/graphs/rseth_2026-04.json#records[relation_id=rseth-owes-weth-borrowed].payload.amount)
  - [signals|oracle_market_divergence_pct] compute_signal:oracle_market_divergence_pct/v1 = -31 (doc:fixtures/sources/RSETH_MEASURE_2.md#measure-2)
  - [signals|rseth_utilisation_at_freeze] compute_signal:rseth_utilisation_at_freeze/v1 = 7.946826023583168e-05 (evidence:episode_rseth_2026-04.json#series["2026-04-18T19:03:59Z"].rsETH.utilisation)
  - [signals|supply_cap_saturation_ratio] compute_signal:supply_cap_saturation_ratio/v1 = 0.9999886466022144 (evidence:episode_rseth_2026-04.json#headline.cap_ratio_max)

Agent outcome (`run_outcome.json`): stop `ARRET-3`, inconclusive=True, critique verdict `INCOHERENTE`, escalation `REQUIRE_APPROVAL`.

## 4. Decision

Case decision = the **DecisionRecord built from the sealed agents run** by `src/orvyren/decision/agents_source.py` (`build_decision_from_agents`), written unchanged to `decision/decision_agents_rseth-2026-04.json` (schema `orvyren-decision-record/v1`). This is the exact record the executor consumes — nothing is re-derived from the pilot corpus.

  - source run: `rseth-2026-04_live_20261018T200027592497Z` (mode `live`, 14 journal line(s); chain heads recomputed from the journals: critic `924d84dde64c86ecb3c24bc0a758d9d152a36428658b759b5905fc4123a2112a`, orchestrator `9d1372f5457434c7bf4faccaae6eb545a48f60e2a8982e6918de23a36220a2df`)
  - epistemic verdict `INCONCLUSIVE` · economic action `null` · intent `null` · authorization `REQUIRE_APPROVAL`
  - escalation `REQUIRE_APPROVAL`, outcome state `ABORTED`, stop condition `ARRET-3` — motif: E_LOOP_OUTPUT_INVALID: orchestrator plan invalid after re-prompt (critere_discriminant contains a digit)
  - critic: `INCOHERENTE`, 10 finding(s), types ALTERNATIVE, CONTRADICTION, DEPENDANCE, MANQUE, OBSOLESCENCE, PIT, gravities BLOQUANT, MAJEUR, MINEUR
  - hypotheses: HYP-001 (UNDER_TEST), HYP-002 (UNDER_TEST), HYP-003 (UNDER_TEST), HYP-004 (UNDER_TEST) — every agents state is `UNDER_TEST` and the record's decision slot stays `unavailable`: the bridge never upgrades an agents state into a REFUTED/SUPPORTED verdict.
  - realised research cost: 0.035731 USD · 5 LLM call(s) · 1 tool call(s) · 34.42 s (declared caps: 0.1 USD / 30 calls / 600 s), read from `run_outcome.json`
  - what_would_change: 0 entr(ies) — the bridge copies `outcome.non_recherche` verbatim; the sealed run stopped at `ARRET-3` before enumerating one, so the list is empty. Declared gap, never filled by hand.

Case decision — A1-A5 abstention, **complement** (the research plan `decision/abstention_rseth-2026-04.json`, built from the case fixture and the critic findings through `orvyren.decision.abstention`, never a forced decision). It produces no intent and no economic action, and it is not the DecisionRecord:
  - epistemic verdict: INCONCLUSIVE (conditions: A1)
  - action: None — no autonomous transfer while the market is frozen and the evidence is inconclusive
  - escalation: ESCALATE — surviving hypotheses prescribe opposite actions and the wrong one is costly — fragile posterior
  - decision_delta: si_H1_soutenue -> no autonomous transfer is even possible: the reserve is frozen — document and escalate; si_H2_soutenue -> reduce the rsETH exposure off the oracle valuation (bounded x*) once an archived market series confirms the decoupling; si_H3_soutenue -> the supply-cap constraint is the binding mechanism: no new rsETH deposits, monitor the cap and the freeze bit; si_H4_soutenue -> a liquidity squeeze would call for a cash buffer on the WETH side instead of an rsETH action (refuted by the measured utilisation)
  - what_would_change (5 research entries):
    - [RSETH-P-MARKET-SERIES] an archived rsETH market/exit series over 2026-04-18..20 (L-1) — cible: market archives (DeFiLlama/Binance) — absent from the measured corpus (2 request(s), < 0.7 s; affects HYP-001, HYP-002, HYP-003)
    - [RSETH-P-ORACLE-FRESHNESS] the oracle updatedAt at the freeze — latestRoundData() reverts on the capped feed (L-2) — cible: eth_call on the capped rsETH/ETH/USD feed (1 request(s), < 0.7 s; affects HYP-001, HYP-002, HYP-003)
    - [RSETH-P-CAP-RATIO-WINDOW] a dense cap_ratio series between 2026-04-18T18:00:00Z and 2026-04-18T19:03:59Z — cible: evidence/episode_rseth_2026-04.json key points + RPC archive (critic PIT finding) (1 request(s), < 0.7 s; affects HYP-001, HYP-002, HYP-003)
    - [RSETH-P-BAD-DEBT-LEDGER] the per-account debt ledger behind the 123.7 / 230.1 M USD bad debt (L-3) — cible: Aave per-account data (3 request(s), < 0.7 s; affects HYP-001, HYP-002, HYP-003)
    - [RSETH-P-RSETH-TOOL-OBS] a discriminating rsETH tool observation in the run refs (critic BLOQUANT: the packet carried USDC series) — cible: an rsETH series in the measured corpus (corpus/ not populated for rsETH) (1 request(s), < 0.7 s; affects HYP-001, HYP-002, HYP-003)
  - verdicts: HYP-001 INCONCLUSIVE; HYP-002 INCONCLUSIVE; HYP-003 INCONCLUSIVE; HYP-004 REFUTED

Cross-check only — deterministic decision engine (`run_decision.py --no-rdof`). The v1 engine is wired to the frozen USDC pilot windows (FREEZE_V1 D1/D2) and peg hypotheses; its record `decision/decision_rseth-2026-04.json` is kept as a pilot-scoped cross-check, **not** as the case conclusion:
  - H1 INCONCLUSIVE (local liquidity perturbation)
  - H2 INCONCLUSIVE (broad stress on asset or issuer)
  - H3 INCONCLUSIVE (data or market artifact)

## 5. Policy verdict

**No policy verdict was produced, and none is invented.** The DecisionRecord carries `economic_action: null` and `intent: null` with `authorization_verdict: REQUIRE_APPROVAL`, so the executor records `NO_ACTIONABLE_INTENT` and stops before `policy.evaluate`: the policy axis is *not evaluated* — not ALLOW, not DENY.

`policy_v1.yaml` was loaded (version `v1.0`, hash `651535872228470403f5603982eaadd9c4143c700f0ce159813f9edc7164ad5d`) and no rule was applied, because there is nothing to authorise:
  - tick 1: outcome `NO_ACTION`, verdict `DENY`, policy `not evaluated`, reasons: NO_ACTIONABLE_INTENT — chain run_id scenario-rseth-2026-04-20261019T134804Z verify_ok=True

`REQUIRE_APPROVAL` is the record's own brake: an agents run never evaluates the policy, and with no intent there is no transition decision -> policy in the chain.

## 6. Execution

Dry-run only (no signature, no key read), on the case's **own** decision: `--case rseth-2026-04 --decision-source agents --agents-run <sealed run>`. The historical pilot replay (`--case usdc-2023-03`) is gone from this leg: it produced a USDC intent under the rsETH run id, which is exactly the substitution this dossier removes.

  - `decision` -> rc 0
  - `decision_agents_source` -> rc 0 (REQUIRE_APPROVAL)
  - `decision_abstention` -> rc 0 (ESCALATE)
  - `execution` -> rc 0

  - chain events head: `39a7b7f94618ec902522259375149e14ce35aa9f858acff873f1769cf7794b3f`
  - chain root `execution/chain/scenario-rseth-2026-04-20261019T134804Z/`; tick journal `execution/journal.jsonl` (append-only, chained; `policy_verdicts.json` extracts this run's ticks)
  - outcome of the leg: 1 tick(s), 0 intent(s), 0 signature(s), 0 transfer — an abstention that stops before the policy is the expected result, not a failed execution.

## 7. Chain verification

`chain_verification.json` (status `PASS`) compares the DecisionRecord with what the executor actually recorded:

  - decision record `decision/decision_agents_rseth-2026-04.json` sha256 `fdbe92f2e8cc8ee818484cb2ca5056e11a4aabadd41375a3dcf574e09fd6ecf7`
  - agents run `rseth-2026-04_live_20261018T200027592497Z` (mode `live`), chain heads critic `924d84dde64c86ecb3c24bc0a758d9d152a36428658b759b5905fc4123a2112a`, orchestrator `9d1372f5457434c7bf4faccaae6eb545a48f60e2a8982e6918de23a36220a2df` — recomputed from the journals, declared replayable=False
  - tick 1: outcome `NO_ACTION`, verdict `DENY`, policy `not evaluated`, reasons NO_ACTIONABLE_INTENT — 9/9 checks passed, chain run `scenario-rseth-2026-04-20261019T134804Z` parent `rseth-2026-04_live_20261018T200027592497Z`
  - chain events (in order): `DECISION_REPLAYED` -> `NO_ACTIONABLE_INTENT`
  - no `POLICY_DECIDED` and no execution event exists: with no intent the chain stops after `NO_ACTIONABLE_INTENT`

Status `PASS`: the record the executor consumed is the record in the dossier — same epistemic verdict, same authorization verdict, same (null) economic action, same intent absence, chain ids chained to the agents run, chain verified, 0 executed.

Chain of identifiers, each read from its artifact:
  1. risk observed — `evidence/episode_rseth_2026-04.json` (§1; fixture `fixtures/agents/rseth-2026-04/run_inputs.json`)
  2. hypotheses — `run.json` (HYP-001..HYP-004, state `UNDER_TEST`) (§2)
  3. evidence — `evidence_packet.json` packet `rseth-2026-04_live_20261018T200027592497Z-packet`, snapshot `graph_snapshot:rseth-2026-04@2026-04-18T19:03:59Z`, 1924 ref(s) (§3)
  4. critique — `critique_report.json` `INCOHERENTE`, 10 finding(s) (§3/§4)
  5. decision — `decision/decision_agents_rseth-2026-04.json` (sha256 `fdbe92f2e8cc8ee8`), from run `rseth-2026-04_live_20261018T200027592497Z` (§4)
  6. policy — not evaluated (no intent), tick outcome `NO_ACTION` (§5)
  7. execution — `execution/journal.jsonl`, chain `scenario-rseth-2026-04-20261019T134804Z`, events head `39a7b7f94618ec90` (§6)
  8. dossier — `scenario_run.json` + this report, run_id `scenario-rseth-2026-04-20261019T134804Z`

## 8. Gaps and explicit lacunae

Explicit lacunae of the case fixture:
  - L-1 — Can the documented market price (1 686 USD) be confirmed from an archived market series? The RPC data layer documents the retained price, not the exit price.
  - L-2 — What was the oracle freshness at the freeze? latestRoundData() reverts on the capped rsETH/ETH/USD feed, so no updatedAt is readable.
  - L-3 — What is the exact bad debt per account? The incident report gives 123.7 / 230.1 M USD, but the per-account debt ledger is out of this data layer.
  - L-4 — Was any realisable value left for the frozen collateral? No liquid venue is readable for a stolen/unbacked rsETH.

Declared gaps of this dossier (none of them is a conclusion):
  - `what_would_change` is empty in the DecisionRecord: the bridge copies `outcome.non_recherche` verbatim and the sealed run stopped at `ARRET-3` before enumerating a research plan. The A1-A5 complement (`decision/abstention_rseth-2026-04.json`, 5 entr(ies)) lists the sourced next observations; it is a complement, not a second decision.
  - the deterministic engine record `decision/decision_rseth-2026-04.json` is pilot-scoped (frozen USDC windows + peg hypotheses): it is a cross-check of the decision stage, never an rsETH conclusion.
  - the live run is not bit-replayable (wall-time and realised cost enter its payloads): `source.replayable=false`, declared by the bridge. An offline replay needs a recorded response store, absent for this case — never simulated.
  - the agents' hypotheses stayed `UNDER_TEST`: the record declares no hypothesis REFUTED or SUPPORTED. The critic's BLOQUANT finding (the packet carried no rsETH observation) is why the run stopped instead of concluding.
  - the market price and the ~-31 % divergence remain documentation figures (ORVYREN_DOC2_TECHNIQUE_COMPLET.md, measurement 2), not an archived market series.

## 9. Provenance and reproduction

Reproduce, sealed run (no LLM call, no new spend — the packaged mode):
```
python scripts/run_scenario_rseth.py --agents-run evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z \
    --run-id scenario-rseth-2026-04-20261019T134804Z --out-dir evidence/scenario_rseth
```
Reproduce, live agents (real LLM calls, keys from `scripts/demo/.env`; a new agents run and a new scenario run id):
```
(set -a; source scripts/demo/.env; set +a)
python scripts/run_scenario_rseth.py --out-dir evidence/scenario_rseth
```
Legacy leg (reproduce the superseded dossier only): add `--decision-source corpus`.

The bridge record `decision/decision_agents_rseth-2026-04.json` is the artifact to cite; `chain_verification.json` states whether the executor consumed it (and with which chain ids). Fixture: `fixtures/agents/rseth-2026-04/run_inputs.json`. Derived corpus: `fixtures/agents/rseth-2026-04/corpus_rseth.csv` (re-derived and compared by `tests/test_fixtures_rseth_inputs.py`). Targeted tests: `python -m unittest tests.test_fixtures_rseth_inputs tests.test_scenario_rseth`. No key or secret is stored in any artifact of this directory.

## 10. Raw step outputs

### step `decision` (rc 0)
stdout:
```
ORVYREN-Core decision run - case rseth-2026-04
Window (main):    2023-03-09T00:00:00+00:00 -> 2023-03-15T00:00:00+00:00
Corpus:           fixtures/agents/rseth-2026-04/corpus_rseth.csv (0 observations in window, sha256 7e313c7bb24e...)
Hypothesis verdicts:
  H1 local liquidity perturbation: INCONCLUSIVE
  H2 broad stress on asset or issuer: INCONCLUSIVE
  H3 data or market artifact: INCONCLUSIVE
Decision:         INCONCLUSIVE - action: null
Exposure envelope: exposure 500.0 USDC, floor 350.0 USDC, available_to_move 100.0 USDC
Missing inputs:   bitstamp hourly price series (independent venue); binance hourly price series (independent venue); defillama hourly price series (aggregator) required for the H1 aggregate-tolerance criterion; defillama_supply_aggregate daily circulating supply series (metric=circulating_usd) required for the 24 h supply-change criterion; defillama hourly price series (aggregator) required for the H3 divergence check
Baseline A0:      signals_main=0, signals_control=0, false_signals_control=0
Evidence:         evidence/scenario_rseth/decision/decision_rseth-2026-04.json
Evidence:         evidence/scenario_rseth/decision/baseline_report.json
```
stderr:
```
(empty)
```

### step `decision_agents_source` (rc 0)
stdout:
```
DecisionRecord orvyren-decision-record/v1 · epistemic INCONCLUSIVE · economic_action None · intent None · authorization REQUIRE_APPROVAL · escalation REQUIRE_APPROVAL · evidence_refs agents_journal:critic=924d84dde64c, agents_journal:orchestrator=9d1372f54574
```
stderr:
```
(empty)
```

### step `decision_abstention` (rc 0)
stdout:
```
abstention ESCALATE — action null; 5 what_would_change entr(ies); conditions A1
```
stderr:
```
(empty)
```

### step `execution` (rc 0)
stdout:
```
{
  "schema": "orvyren-executor-run/v1",
  "case": "rseth-2026-04",
  "mode": "dry-run",
  "ticks": 1,
  "ticks_run": 1,
  "recipient": "0x37877f6ffb6656e752bf4807b9c3c7b761a953a3",
  "run_id": "scenario-rseth-2026-04-20261019T134804Z",
  "parent_run_id": "rseth-2026-04_live_20261018T200027592497Z",
  "chain": {
    "run_id": "scenario-rseth-2026-04-20261019T134804Z",
    "parent_run_id": "rseth-2026-04_live_20261018T200027592497Z",
    "case_id": "rseth-2026-04",
    "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\chain\\scenario-rseth-2026-04-20261019T134804Z",
    "verify_ok": true,
    "verify_error": "",
    "events_head": "39a7b7f94618ec902522259375149e14ce35aa9f858acff873f1769cf7794b3f",
    "artifacts": 0
  },
  "policy": {
    "path": "D:\\orvyren_core\\policy_v1.yaml",
    "version": "v1.0",
    "policy_hash": "651535872228470403f5603982eaadd9c4143c700f0ce159813f9edc7164ad5d",
    "yaml_sha256": "b99ad99bc2d32184fd4e1b45fb136f0424e972f40d71cafeab622ae11acc0c03"
  },
  "envelope": {
    "status": "PASS",
    "source": "fixture",
    "fixture_path": "D:\\orvyren_core\\fixtures\\roles_agent_config.json",
    "note": "",
    "checks": [
      {
        "id": "D1",
        "name": "chain",
        "status": "PASS",
        "detail": {
          "chain_id": 84532
        }
      },
      {
        "id": "D3",
        "name": "role key",
        "status": "PASS",
        "detail": {}
      },
      {
        "id": "D4",
        "name": "role targets",
        "status": "PASS",
        "detail": {
          "targets": [
            "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
          ]
        }
      },
      {
        "id": "D5",
        "name": "role functions",
        "status": "PASS",
        "detail": {
          "functions": [
            [
              "0x036cbd53842c5426634e7929541ec2318f3dcf7e",
              "0xa9059cbb"
            ]
          ]
        }
      },
      {
        "id": "D7",
        "name": "allowance",
        "status": "PASS",
        "detail": {
          "mismatches": [],
          "fixture": 300000000,
          "policy": 300000000
        }
      },
      {
        "id": "D8",
        "name": "call quota",
        "status": "PASS",
        "detail": {
          "fixture": 10,
          "policy": 10
        }
      },
      {
        "id": "D9",
        "name": "scheduled revocation",
        "status": "PASS",
        "detail": {}
      },
      {
        "id": "D10",
        "name": "asset",
        "status": "PASS",
        "detail": {}
      }
    ]
  },
  "paused": false,
  "stopped": "",
  "journal": {
    "path": "evidence/scenario_rseth\\execution\\journal.jsonl",
    "records": 1,
    "ok": true,
    "error": ""
  },
  "ledger": {
    "path": "evidence/scenario_rseth\\execution\\ledger.json",
    "entries": 0,
    "spent_24h_before": 0.0,
    "spent_24h_after": 0.0
  },
  "counts": {
    "allow": 0,
    "deny": 1,
    "require_approval": 0,
    "dry_run": 0,
    "signed": 0,
    "no_action": 1,
    "errors": 0
  },
  "records": [
    {
      "case": "rseth-2026-04",
      "run_id": "scenario-rseth-2026-04-20261019T134804Z",
      "tick": 1,
      "ts_utc": "2026-10-19T13:48:05.784177+00:00",
      "mode": "dry-run",
      "dry_run": true,
      "verdict": "DENY",
      "policy_verdict": null,
      "outcome": "NO_ACTION",
      "executed": false,
      "intent": null,
      "decision_summary": {
        "epistemic_verdict": "INCONCLUSIVE",
        "economic_action": null,
        "authorization_verdict": "REQUIRE_APPROVAL"
      },
      "reasons": [
        "NO_ACTIONABLE_INTENT"
      ],
      "rules_evaluated": [],
      "skipped_rules": [],
      "policy_version": "v1.0",
      "policy_hash": "651535872228470403f5603982eaadd9c4143c700f0ce159813f9edc7164ad5d",
      "safe_mode": false,
      "state": {
        "paused": false,
        "agent_member": null,
        "envelope_status": "PASS",
        "available_balance": null,
        "cumulative_spent": 0.0,
        "budget_spent": 0.0,
        "budget_cap": 0.1
      },
      "tx_hash": null,
      "receipt_verification": null,
      "error": "the DecisionRecord carries no executable intent",
      "ledger_spent_after": null,
      "chain": {
        "run_id": "scenario-rseth-2026-04-20261019T134804Z",
        "parent_run_id": "rseth-2026-04_live_20261018T200027592497Z",
        "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\chain\\scenario-rseth-2026-04-20261019T134804Z",
        "verify_ok": true,
        "verify_error": "",
        "events_head": "39a7b7f94618ec902522259375149e14ce35aa9f858acff873f1769cf7794b3f"
      }
    }
  ],
  "demo_defaults": false
}
```
stderr:
```
NOTE: ORVYREN_AGENT_MEMBER, ORVYREN_AVAILABLE_BALANCE unset — P11/P7 fail closed (DENY). Pass --demo-defaults for the offline demo.
```
