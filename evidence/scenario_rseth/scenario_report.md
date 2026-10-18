# Scenario report — rsETH / KelpDAO, April 2026 (E2E demonstration)

Case `rseth-2026-04` · scenario run_id `scenario-rseth-2026-04-20261018T110722Z` · agents run_id `rseth-2026-04_live_20261018T110722Z` · executor run_id `scenario-rseth-2026-04-20261018T110722Z` (parent `rseth-2026-04_live_20261018T110722Z`).
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

The LIVE agents observed the tools of the run (real LLM calls). The sourced figures of the fixture and their sources:
  - [prices|chainlink|rsETH-USD] 2026-04-18T17:35:00Z = 2526.7563881 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-18T17:35:00Z)
  - [prices|chainlink|rsETH-USD] 2026-04-18T19:03:59Z = 2513.66460329 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-18T19:03:59Z)
  - [prices|chainlink|rsETH-USD] 2026-04-20T00:00:00Z = 2419.21294349 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_at_2026-04-20T00:00:00Z)
  - [prices|chainlink|rsETH-USD] 2026-04-17T17:00:00Z = 2631.56608381 (evidence:episode_rseth_2026-04.json#headline.rsETH_oracle_peak.price)
  - [prices|market|rsETH-USD] 18–20/04 = 1686 (doc:ORVYREN_DOC2_TECHNIQUE_COMPLET.md#measure-2)
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
  - [signals|oracle_market_divergence_pct] compute_signal:oracle_market_divergence_pct/v1 = -31 (doc:ORVYREN_DOC2_TECHNIQUE_COMPLET.md#measure-2)
  - [signals|rseth_utilisation_at_freeze] compute_signal:rseth_utilisation_at_freeze/v1 = 7.946826023583168e-05 (evidence:episode_rseth_2026-04.json#series["2026-04-18T19:03:59Z"].rsETH.utilisation)
  - [signals|supply_cap_saturation_ratio] compute_signal:supply_cap_saturation_ratio/v1 = 0.9999886466022144 (evidence:episode_rseth_2026-04.json#headline.cap_ratio_max)

Agent outcome (`run_outcome.json`): stop `ARRET-3`, inconclusive=True, critique verdict `INCOHERENTE`, escalation `REQUIRE_APPROVAL`.

## 4. Decision

Case decision (LIVE agent chain): the run above — its outcome, evidence packet and critic verdict are the case-specific decision artifacts (`run_outcome.json`, `evidence_packet.json`, `critique_report.json`).

Case decision — abstention built through the documented A1-A5 path (`orvyren.decision.abstention`: detect_conditions -> what_would_change_entries -> escalate_vs_no_action -> build_inconclusive), never a forced decision:
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

Deterministic decision engine (`run_decision.py`, declared substitution): the v1 engine is wired to the frozen USDC pilot windows (FREEZE_V1 D1/D2) and peg hypotheses; on this case it records its own verdicts and missing inputs in `decision/decision_rseth-2026-04.json`:
  - H1 INCONCLUSIVE (local liquidity perturbation)
  - H2 INCONCLUSIVE (broad stress on asset or issuer)
  - H3 INCONCLUSIVE (data or market artifact)

## 5. Policy verdict

Policy evaluated on the execution leg (real `policy_v1.yaml`, real state, fail-closed resolvers):
  - tick 1: verdict `DENY` (policy `DENY`, reasons: BALANCE_UNREADABLE, AGENT_NOT_MEMBER) — chain run_id scenario-rseth-2026-04-20261018T110722Z verify_ok=True

## 6. Execution

Execution is always dry-run (no signature, no key read), chained under one run identity (`orvyren.chain`). The execution case probe (`rseth-2026-04` case, measured live in this run) ended `REFUSED_E_WHAT_WOULD_CHANGE_REQUIRED`: the v1 decision dossier is only constructible for the pilot case id and the executor CLI has no decision-provider override, so the policy/execution leg runs the pilot decision replay as a declared substitution (`--case usdc-2023-03`), chained under this scenario run id and parented to the agents run id:
  - `keys` -> rc 0
  - `agents` -> rc 0
  - `decision` -> rc 0
  - `decision_abstention` -> rc 0 (ESCALATE)
  - `execution_case_probe` -> rc 5 (REFUSED_E_WHAT_WOULD_CHANGE_REQUIRED)
  - `execution` -> rc 0
  - chain events head: ffb4a2c8fbe239092be53122a60792857d3a08a5793af9bd2d52d6cffb48cbda
  - tick journal: `execution/journal.jsonl` (chained JSONL, append-only; `policy_verdicts.json` extracts this run's ticks), chain root `execution/chain/scenario-rseth-2026-04-20261018T110722Z/`; the probe journal and chain are kept under `execution/case_attempt/`

## 7. Gaps and explicit lacunae

Explicit lacunae of the case fixture:
  - L-1 — Can the documented market price (1 686 USD) be confirmed from an archived market series? The RPC data layer documents the retained price, not the exit price.
  - L-2 — What was the oracle freshness at the freeze? latestRoundData() reverts on the capped rsETH/ETH/USD feed, so no updatedAt is readable.
  - L-3 — What is the exact bad debt per account? The incident report gives 123.7 / 230.1 M USD, but the per-account debt ledger is out of this data layer.
  - L-4 — Was any realisable value left for the frozen collateral? No liquid venue is readable for a stolen/unbacked rsETH.

Declared substitutions and limitations:
  - the deterministic decision engine of v1 is wired to the USDC pilot (frozen windows + peg hypotheses, `python -m orvyren.decide` refuses other case ids): its record is chained evidence of the decision stage mechanics, not an rsETH conclusion;
  - the v1 decision dossier (RDOF + A1-A5 abstention) is only constructible for the pilot case id: the execution case probe (`--case rseth-2026-04`) is kept under `execution/case_attempt/` with the measured refusal (`E_WHAT_WOULD_CHANGE_REQUIRED`); the executor tick decision therefore replays the pilot decision and the rsETH-specific conclusion is the agent chain's — with a frozen market the coherent action is no autonomous transfer;
  - no recorded response store exists for this case yet: only the LIVE run is executed; an offline `--replay journal` replay needs a recorded store first (never simulated);
  - the market price and the ~-31 % divergence are documentation figures (ORVYREN_DOC2_TECHNIQUE_COMPLET.md measurement 2), not archived market series (episode limitations).

## 8. Provenance and reproduction

Reproduce: `(set -a; source scripts/demo/.env; set +a; python scripts/run_scenario_rseth.py)` then inspect `evidence/scenario_rseth/`. Fixture: `fixtures/agents/rseth-2026-04/run_inputs.json`. Derived corpus: `fixtures/agents/rseth-2026-04/corpus_rseth.csv` (re-derived and compared by `tests/test_fixtures_rseth_inputs.py`). Targeted tests: `python -m unittest tests.test_fixtures_rseth_inputs tests.test_scenario_rseth`. No key or secret is stored in any artifact of this directory.

## 9. Raw step outputs

### step `keys` (rc 0)
stdout:
```
[file]    scripts/demo/.env  (git-ignored ✓)
    ORVYREN_RPC_URL_BASE_SEPOLIA       present (len 24)
    ORVYREN_CHAIN_ID                   present (len 5)
    ORVYREN_RPC_TIMEOUT_SECONDS        present (len 2)
    ORVYREN_SAFE_ADDRESS               present (len 42)
    ORVYREN_AGENT_ADDRESS              present (len 42)
    ORVYREN_MODULE_ADDRESS             present (len 42)
    ORVYREN_USDC_ADDRESS               present (len 42)
    ORVYREN_RECIPIENT_B                present (len 42)
    ORVYREN_RECIPIENT_C                present (len 42)
    ORVYREN_RECIPIENT_UNLISTED         present (len 42)
    ORVYREN_PRIVATE_KEY                present (len 66) — never displayed
    ORVYREN_K0_PAUSED                  empty
    ORVYREN_DEEPSEEK_API_KEY           present (len 35) — never displayed
    ORVYREN_MIMO_API_KEY               present (len 51) — never displayed

[file]    scripts/demo/owners.env  (git-ignored ✓)
    ORVYREN_OWNER1_ADDRESS             present (len 42)
    ORVYREN_OWNER1_PRIVATE_KEY         present (len 66) — never displayed
    ORVYREN_OWNER2_ADDRESS             present (len 42)
    ORVYREN_OWNER2_PRIVATE_KEY         present (len 66) — never displayed
    ORVYREN_OWNER3_ADDRESS             present (len 42)
    ORVYREN_OWNER3_PRIVATE_KEY         present (len 66) — never displayed

live-mode keys (agents):
    ORVYREN_DEEPSEEK_API_KEY           present (len 35)
    ORVYREN_MIMO_API_KEY               present (len 51)
```
stderr:
```
(empty)
```

### step `agents` (rc 0)
stdout:
```
ORVYREN — run_agents · rseth-2026-04 · mode live
  run       : evidence\scenario_rseth\agents_session\rseth-2026-04_live_20261018T110722Z
  store live: evidence\scenario_rseth\agents_session\rseth-2026-04_live_20261018T110722Z\store_live
  [orchestrator] process started…
    [orchestrator] done — 31 journal lines, state ABORTED/ARRET-3
  [critic] process started…
    [critic] report written — verdict INCOHERENTE, 12 objection(s)

  ==== run summary rseth-2026-04 (live) ====
    orchestrator   31 lines — agent_id:orchestrator — chain OK
    critic          1 lines — agent_id:critic — chain OK
    stop           : ARRET-3 (abstention)
    budget         : llm 9/30 · tools 7/12 · 60s/600s · $0.0397/$0.10
    critique       : INCOHERENTE
    escalation     : REQUIRE_APPROVAL (the critic never cancels — it brakes)
    not searched   : Une série de marché archivée pour le rsETH, sur une place liquide, confirme-t-elle un cours de sortie nettement inférieur aux lectures du feed oracle retenues sur la même fenêtre ? · Does an archived secondary-market price series for the collateral asset print a last trade before the freeze instant matching the documented market price rather than the retained oracle reading over the same window?
    cumulative LLM cost: $0.0397
    artifacts      : evidence\scenario_rseth\agents_session\rseth-2026-04_live_20261018T110722Z
```
stderr:
```
(empty)
```

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

### step `decision_abstention` (rc 0)
stdout:
```
abstention ESCALATE — action null; 5 what_would_change entr(ies); conditions A1
```
stderr:
```
(empty)
```

### step `execution_case_probe` (rc 5)
stdout:
```
{
  "schema": "orvyren-executor-run/v1",
  "case": "rseth-2026-04",
  "mode": "dry-run",
  "ticks": 1,
  "ticks_run": 1,
  "recipient": "0x37877f6ffb6656e752bf4807b9c3c7b761a953a3",
  "run_id": "scenario-rseth-2026-04-20261018T110722Z-case-probe",
  "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
  "chain": {
    "run_id": "scenario-rseth-2026-04-20261018T110722Z-case-probe",
    "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
    "case_id": "rseth-2026-04",
    "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\case_attempt\\chain\\scenario-rseth-2026-04-20261018T110722Z-case-probe",
    "verify_ok": true,
    "verify_error": "",
    "events_head": "427451a2bd3711050ca64061fb482a717089a0608422e72f650783adea953b1c",
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
  "stopped": "decision",
  "journal": {
    "path": "evidence\\scenario_rseth\\execution\\case_attempt\\journal.jsonl",
    "records": 2,
    "ok": true,
    "error": ""
  },
  "ledger": {
    "path": "evidence\\scenario_rseth\\execution\\case_attempt\\ledger.json",
    "entries": 0,
    "spent_24h_before": 0.0,
    "spent_24h_after": 0.0
  },
  "counts": {
    "allow": 0,
    "deny": 0,
    "require_approval": 0,
    "dry_run": 0,
    "signed": 0,
    "no_action": 0,
    "errors": 1
  },
  "records": [
    {
      "case": "rseth-2026-04",
      "run_id": "scenario-rseth-2026-04-20261018T110722Z-case-probe",
      "tick": 1,
      "ts_utc": "2026-10-18T11:11:30.938975+00:00",
      "mode": "dry-run",
      "dry_run": true,
      "verdict": "ERROR",
      "policy_verdict": null,
      "outcome": "ERROR",
      "executed": false,
      "intent": null,
      "decision_summary": {},
      "reasons": [],
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
      "error": "decision unavailable: E_WHAT_WOULD_CHANGE_REQUIRED: INCONCLUSIVE must enumerate what would change the verdict (B3 §c.3)",
      "ledger_spent_after": null,
      "chain": {
        "run_id": "scenario-rseth-2026-04-20261018T110722Z-case-probe",
        "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
        "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\case_attempt\\chain\\scenario-rseth-2026-04-20261018T110722Z-case-probe",
        "verify_ok": true,
        "verify_error": "",
        "events_head": "427451a2bd3711050ca64061fb482a717089a0608422e72f650783adea953b1c"
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

### step `execution` (rc 0)
stdout:
```
{
  "schema": "orvyren-executor-run/v1",
  "case": "usdc-2023-03",
  "mode": "dry-run",
  "ticks": 1,
  "ticks_run": 1,
  "recipient": "0x37877f6ffb6656e752bf4807b9c3c7b761a953a3",
  "run_id": "scenario-rseth-2026-04-20261018T110722Z",
  "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
  "chain": {
    "run_id": "scenario-rseth-2026-04-20261018T110722Z",
    "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
    "case_id": "usdc-2023-03",
    "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\chain\\scenario-rseth-2026-04-20261018T110722Z",
    "verify_ok": true,
    "verify_error": "",
    "events_head": "ffb4a2c8fbe239092be53122a60792857d3a08a5793af9bd2d52d6cffb48cbda",
    "artifacts": 2
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
    "path": "evidence\\scenario_rseth\\execution\\journal.jsonl",
    "records": 3,
    "ok": true,
    "error": ""
  },
  "ledger": {
    "path": "evidence\\scenario_rseth\\execution\\ledger.json",
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
    "no_action": 0,
    "errors": 0
  },
  "records": [
    {
      "case": "usdc-2023-03",
      "run_id": "scenario-rseth-2026-04-20261018T110722Z",
      "tick": 1,
      "ts_utc": "2026-10-18T11:11:31.368970+00:00",
      "mode": "dry-run",
      "dry_run": true,
      "verdict": "DENY",
      "policy_verdict": "DENY",
      "outcome": "DENIED_POLICY",
      "executed": false,
      "intent": {
        "intent_id": "intent-usdc-2023-03-a-d1-t001-scenario-rseth-2026-04-20261018T110722Z",
        "action": "transfer",
        "chain_id": 84532,
        "asset": "0x036cbd53842c5426634e7929541eC2318f3dCF7e",
        "amount": 100.0,
        "recipient": "0x37877f6ffb6656e752bf4807b9c3c7b761a953a3",
        "created_at": "2026-10-18T11:11:31.368970+00:00"
      },
      "decision_summary": {
        "epistemic_verdict": "CONCLUANT",
        "economic_action": "CONVERTIR/TRANSFÉRER",
        "authorization_verdict": "ALLOW"
      },
      "reasons": [
        "BALANCE_UNREADABLE",
        "AGENT_NOT_MEMBER"
      ],
      "rules_evaluated": [
        {
          "rule": "P1-chain",
          "result": "OK",
          "note": "84532"
        },
        {
          "rule": "P2-asset",
          "result": "OK",
          "note": ""
        },
        {
          "rule": "P3-recipient",
          "result": "OK",
          "note": ""
        },
        {
          "rule": "P4-function",
          "result": "OK",
          "note": "transfer -> (0x036cbd53842c5426634e7929541ec2318f3dcf7e, 0xa9059cbb)"
        },
        {
          "rule": "P5-amount",
          "result": "OK",
          "note": "100.0 <= 100.0"
        },
        {
          "rule": "P6-cumulative",
          "result": "OK",
          "note": "100.0 <= 300.0"
        },
        {
          "rule": "P7-exposure",
          "result": "FAIL",
          "code": "BALANCE_UNREADABLE"
        },
        {
          "rule": "P8-permission",
          "result": "OK",
          "note": "2026-10-19T11:11:31.367974+00:00"
        },
        {
          "rule": "P9-freshness",
          "result": "OK",
          "note": "age 0:00:00"
        },
        {
          "rule": "P10-idempotency",
          "result": "OK",
          "note": ""
        },
        {
          "rule": "P11-pause",
          "result": "FAIL",
          "code": "AGENT_NOT_MEMBER",
          "note": "role membership unreadable — fail closed"
        },
        {
          "rule": "P12-envelope",
          "result": "OK",
          "note": ""
        },
        {
          "rule": "P14-budget",
          "result": "OK",
          "note": "0.0 < 0.1"
        }
      ],
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
      "error": null,
      "ledger_spent_after": null,
      "chain": {
        "run_id": "scenario-rseth-2026-04-20261018T110722Z",
        "parent_run_id": "rseth-2026-04_live_20261018T110722Z",
        "root_dir": "D:\\orvyren_core\\evidence\\scenario_rseth\\execution\\chain\\scenario-rseth-2026-04-20261018T110722Z",
        "verify_ok": true,
        "verify_error": "",
        "events_head": "ffb4a2c8fbe239092be53122a60792857d3a08a5793af9bd2d52d6cffb48cbda"
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
