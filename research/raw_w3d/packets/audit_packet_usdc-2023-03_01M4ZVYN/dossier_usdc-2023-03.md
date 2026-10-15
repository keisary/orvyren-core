# ORVYREN-Core Decision Dossier — case usdc-2023-03

> produced by ORVYREN-Core v0.1 — deterministic engine, no human edit

| Field | Value |
| --- | --- |
| Case | usdc-2023-03 |
| Window | 2023-03-09T00:00:00+00:00 → 2023-03-15T00:00:00+00:00 |
| Generated (UTC) | 2026-10-14T15:47:12Z |
| Engine | ORVYREN-Core 0.1 |

## Decision

- **Verdict:** ACTION_RECOMMENDED
- **Amount:** 100.0 USDC (test)
- **Action:** transfer — from treasury to reserve

### Rationale

- Pre-registered decision rule (frozen before evaluation): H2 SUPPORTED and available_to_move > 0 -> ACTION_RECOMMENDED (bounded 100 USDC test transfer, D8); H1 SUPPORTED and H2 REFUTED -> NO_ACTION (local perturbation, no exposure reduction); missing required series -> INCONCLUSIVE with missing_inputs.
- Rule 1 fires: H2 is SUPPORTED and available_to_move = min(100.0, 500.0 - 350.0) = 100.0000 USDC > 0, so the bounded demonstration action of FREEZE_V1 D8 is recommended: transfer of 100.0000 USDC (test) from wallet 'treasury' to wallet 'reserve'.
- H1 local liquidity perturbation: REFUTED. The deviation did not stay local: > 1.0% persisted more than 12 h on 2 independent venues (persistent episodes: bitstamp 42.0 h, binance 45.0 h), while the aggregator fell to 0.876675 (12.3325%), beyond the 0.5% tolerance.
- H2 broad stress on asset or issuer: SUPPORTED. 34 simultaneous hourly observation(s) more than 1.0% below peg on 2 independent venues (binance, bitstamp) from 2023-03-11T14:00:00+00:00 to 2023-03-13T08:00:00+00:00; deepest: bitstamp 0.86267 at 2023-03-11T07:00:00+00:00 (13.7330%); binance 0.91280 at 2023-03-11T15:00:00+00:00 (8.7200%); circulating supply moved -7.1722% in 24 h (2023-03-11T00:00:00+00:00 -> 2023-03-12T00:00:00+00:00), threshold 1.0%.
- H3 data or market artifact: REFUTED. 2 independent sources (binance, bitstamp) were concordant over 34 simultaneous hour(s); no structural inconsistency and no unexplained divergence was found in the corpus.

### Conditions

- Any execution must first be authorized by the deterministic policy service (src/orvyren/policy, FREEZE_V1 D9): Base Sepolia chain 84532, allowlisted test-USDC asset, allowlisted reserve recipient, <= 100 USDC per transaction, <= 300 USDC cumulative, 24 h permission, idempotent intent_id.
- Test assets only; no mainnet funds (FREEZE_V1 D5/D8).
- The decision is scoped to the frozen corpus revision (sha256 recorded in inputs_summary) and to the recorded window; new observations outside it invalidate the case.
- Contract-level verification of the asset was not possible from this corpus (no contract field); it remains an open check before any mainnet-grade claim.

### Provenance

- {"timestamp_utc": "2023-03-11T07:00:00+00:00", "value": 0.86267, "venue": "bitstamp"}
- {"timestamp_utc": "2023-03-11T04:00:00+00:00", "value": 0.98622, "venue": "bitstamp"}
- {"timestamp_utc": "2023-03-13T14:00:00+00:00", "value": 0.99921, "venue": "bitstamp"}
- {"timestamp_utc": "2023-03-11T15:00:00+00:00", "value": 0.9128, "venue": "binance"}
- {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.9129, "venue": "binance"}
- {"timestamp_utc": "2023-03-11T08:00:00+00:00", "value": 0.876675, "venue": "defillama"}
- {"timestamp_utc": "2023-03-12T22:00:00+00:00", "value": 0.98945, "venue": "bitstamp"}
- {"timestamp_utc": "2023-03-13T11:00:00+00:00", "value": 0.987, "venue": "binance"}
- … +67 more entries (complete list in the source decision JSON, hashed in Evidence & integrity)

## Hypothesis verdicts

| Hypothesis | Verdict | Evidence refs |
| --- | --- | --- |
| H1 | REFUTED | 8 — {"timestamp_utc": "2023-03-11T04:00:00+00:00", "value": 0.98622, "venue": "bitstamp"}; {"timestamp_utc": "2023-03-11T07:00:00+00:00", "value": 0.86267, "venue": "bitstamp"}; {"timestamp_utc": "2023-03-11T08:00:00+00:00", "value": 0.876675, "venue": "defillama"}; {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.9129, "venue": "binance"}; … +4 more (full list in the hashed decision JSON) |
| H2 | SUPPORTED | 72 — {"timestamp_utc": "2023-03-11T00:00:00+00:00", "value": 42097257578.0, "venue": "defillama_supply_aggregate"}; {"timestamp_utc": "2023-03-11T07:00:00+00:00", "value": 0.86267, "venue": "bitstamp"}; {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.9129, "venue": "binance"}; {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.915, "venue": "bitstamp"}; … +68 more (full list in the hashed decision JSON) |
| H3 | REFUTED | 4 — {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.9129, "venue": "binance"}; {"timestamp_utc": "2023-03-11T14:00:00+00:00", "value": 0.915, "venue": "bitstamp"}; {"timestamp_utc": "2023-03-13T08:00:00+00:00", "value": 0.9879, "venue": "binance"}; {"timestamp_utc": "2023-03-13T08:00:00+00:00", "value": 0.98843, "venue": "bitstamp"} |

## Baseline A0 — main window vs control

- **Rule:** If the aggregator price (venue=defillama) is below 0.99 for 2 consecutive hourly observations, reduce the exposure by 100 USDC; otherwise NO-ACTION (FREEZE_V1.md D6). One signal per episode of consecutive observations below 0.99, fired on the second observation; episodes are broken by 1 h gaps.

| Metric | Main window | Control |
| --- | --- | --- |
| Signals | 2 | 0 |
| False signals | — | 0 |

Main window signals (2):
- {"action": {"amount_usdc": 100.0, "type": "reduce_exposure"}, "consecutive_observations": 2, "episode": {"end_utc": "2023-03-12T23:00:00+00:00", "min_value": 0.876675, "min_value_utc": "2023-03-11T08:00:00+00:00", "observations": 46, "start_utc": "2023-03-11T02:00:00+00:00"}, "evidence_refs": [{"timestamp_utc": "2023-03-11T02:00:00+00:00", "value": 0.9840669405733308, "venue": "defillama"}, {"timestamp_utc": "2023-03-11T03:00:00+00:00", "value": 0.9798257461693491, "venue": "defillama"}], "trigger_deviation_pct": 2.017425, "trigger_value": 0.9798257461693491, "triggered_at_utc": "2023-03-11T03:00:00+00:00", "venue": "defillama"}
- {"action": {"amount_usdc": 100.0, "type": "reduce_exposure"}, "consecutive_observations": 2, "episode": {"end_utc": "2023-03-13T09:00:00+00:00", "min_value": 0.980323694466695, "min_value_utc": "2023-03-13T08:00:00+00:00", "observations": 5, "start_utc": "2023-03-13T05:00:00+00:00"}, "evidence_refs": [{"timestamp_utc": "2023-03-13T05:00:00+00:00", "value": 0.9860398348829958, "venue": "defillama"}, {"timestamp_utc": "2023-03-13T06:00:00+00:00", "value": 0.983199, "venue": "defillama"}], "trigger_deviation_pct": 1.6801, "trigger_value": 0.983199, "triggered_at_utc": "2023-03-13T06:00:00+00:00", "venue": "defillama"}

Control signals (0):
- none listed


## Inputs summary

| Key | Value |
| --- | --- |
| corpus | {"observations_in_file": 520, "observations_in_window": 387, "path": "corpus/usdc_observations.csv", "sha256": "c31088b3de428a35cad0833e323352d3fedecb251e4ccd07f168d884b4c8ea7e"} |
| exposure_parameters | {"action_usdc": 100.0, "available_to_move_usdc": 100.0, "exposure_usdc": 500.0, "floor_usdc": 350.0, "note": "demonstration parameters only: no real wallet, no real balance, no market impact modelled"} |
| peg_reference_usd | 1.0 |
| pre_registered_thresholds | {"aggregate_tolerance_pct": 0.5, "deviation_alert_pct": 1.0, "persistence_hours_limit": 12.0, "recovery_hours_limit": 12.0, "recovery_tolerance_pct": 0.1, "supply_drop_pct": 1.0, "supply_window_hours": 24.0} |
| sources | {"first_timestamp_utc": "2023-03-11T14:00:00+00:00", "last_timestamp_utc": "2023-03-15T00:00:00+00:00", "max_value": 0.9961, "metric": "close_usdcusdt", "min_value": 0.9128, "observations": 83, "venue": "binance"}; {"first_timestamp_utc": "2023-03-09T00:00:00+00:00", "last_timestamp_utc": "2023-03-15T00:00:00+00:00", "max_value": 1.00002, "metric": "close_usd", "min_value": 0.86267, "observations": 145, "venue": "bitstamp"}; {"first_timestamp_utc": "2023-03-09T00:00:00+00:00", "last_timestamp_utc": "2023-03-15T00:00:00+00:00", "max_value": 1.0031789557372346, "metric": "price_usd", "min_value": 0.876675, "observations": 145, "venue": "defillama"}; {"first_timestamp_utc": "2023-03-09T00:00:00+00:00", "last_timestamp_utc": "2023-03-15T00:00:00+00:00", "max_value": 43195640252.0, "metric": "circulating_usd", "min_value": 38001901940.0, "observations": 7, "venue": "defillama_supply_aggregate"}; {"first_timestamp_utc": "2023-03-09T00:00:00+00:00", "last_timestamp_utc": "2023-03-15T00:00:00+00:00", "max_value": 37059405596.0, "metric": "circulating_usd", "min_value": 32477824617.0, "observations": 7, "venue": "defillama_supply_ethereum"} |

## Policy execution demo

```json
{
  "agent_holds_key": false,
  "cases": [
    {
      "action_type": "transfer",
      "amount_usdc": 100.0,
      "deny_codes": [],
      "instruction": {
        "calldata": "0xa9059cbb00000000000000000000000011111111111111111111111111111111111111110000000000000000000000000000000000000000000000000000000005f5e100",
        "note": "human executes this transfer; the agent never holds the key",
        "to": "0x036cbd53842c5426634e7929541eC2318f3dCF7e"
      },
      "intent_id": "I1",
      "recipient": "0x1111111111111111111111111111111111111111",
      "rules_evaluated": [
        {
          "note": "84532",
          "result": "OK",
          "rule": "R1-chain"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R2-asset"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R3-recipient"
        },
        {
          "note": "100.0 <= 100.0",
          "result": "OK",
          "rule": "R4-amount"
        },
        {
          "note": "100.0 <= 300.0",
          "result": "OK",
          "rule": "R5-cumulative"
        },
        {
          "note": "2026-10-15T12:00:00+00:00",
          "result": "OK",
          "rule": "R6-permission"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R7-idempotency"
        },
        {
          "note": "transfer",
          "result": "OK",
          "rule": "R8-action"
        }
      ],
      "verdict": "ALLOW"
    },
    {
      "action_type": "transfer",
      "amount_usdc": 500.0,
      "deny_codes": [
        "AMOUNT_ABOVE_TX_CAP",
        "AMOUNT_ABOVE_PERIOD_CAP"
      ],
      "instruction": null,
      "intent_id": "I2",
      "recipient": "0x1111111111111111111111111111111111111111",
      "rules_evaluated": [
        {
          "note": "84532",
          "result": "OK",
          "rule": "R1-chain"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R2-asset"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R3-recipient"
        },
        {
          "code": "AMOUNT_ABOVE_TX_CAP",
          "result": "FAIL",
          "rule": "R4-amount"
        },
        {
          "code": "AMOUNT_ABOVE_PERIOD_CAP",
          "result": "FAIL",
          "rule": "R5-cumulative"
        },
        {
          "note": "2026-10-15T12:00:00+00:00",
          "result": "OK",
          "rule": "R6-permission"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R7-idempotency"
        }
      ],
      "verdict": "DENY"
    },
    {
      "action_type": "change_policy",
      "amount_usdc": 100.0,
      "deny_codes": [
        "ACTION_NEEDS_HUMAN_APPROVAL"
      ],
      "instruction": null,
      "intent_id": "I3",
      "recipient": "0x1111111111111111111111111111111111111111",
      "rules_evaluated": [
        {
          "note": "84532",
          "result": "OK",
          "rule": "R1-chain"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R2-asset"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R3-recipient"
        },
        {
          "note": "100.0 <= 100.0",
          "result": "OK",
          "rule": "R4-amount"
        },
        {
          "note": "100.0 <= 300.0",
          "result": "OK",
          "rule": "R5-cumulative"
        },
        {
          "note": "2026-10-15T12:00:00+00:00",
          "result": "OK",
          "rule": "R6-permission"
        },
        {
          "note": "",
          "result": "OK",
          "rule": "R7-idempotency"
        },
        {
          "code": "ACTION_NEEDS_HUMAN_APPROVAL",
          "result": "REQUIRE_APPROVAL",
          "rule": "R8-action"
        }
      ],
      "verdict": "REQUIRE_APPROVAL"
    }
  ],
  "chain": "Base Sepolia (84532)",
  "execution_config": {
    "agent_holds_key": false,
    "dry_run": true,
    "max_cumulative": 300.0,
    "max_per_tx": 100.0,
    "permission_ttl_hours": 24,
    "reserve_address": "0x1111111111111111111111111111111111111111",
    "rpc_url_masked": "https://sepolia.base.org",
    "secret_env_vars_present": [],
    "timeout_seconds": 30,
    "treasury_address": "0x2222222222222222222222222222222222222222"
  },
  "generated_at": "2026-10-14T15:47:12+00:00",
  "guard_blocks": [
    "I2: execution blocked: policy verdict 'DENY' — the instruction is refused (reason codes: AMOUNT_ABOVE_TX_CAP, AMOUNT_ABOVE_PERIOD_CAP)",
    "I3: execution blocked: policy verdict 'REQUIRE_APPROVAL' — a human approval is required before this instruction may be prepared (reason codes: ACTION_NEEDS_HUMAN_APPROVAL)"
  ],
  "mode": "unsigned instruction + human execution + on-chain receipt verification",
  "receipt_verification": {
    "status": "no transaction hash provided yet (pending human execution)"
  },
  "verdict_check": {
    "expected": {
      "I1": "ALLOW",
      "I2": "DENY",
      "I3": "REQUIRE_APPROVAL"
    },
    "unexpected": []
  }
}
```

## Quality report

```json
{
  "claims": [
    {
      "created_at": "2026-10-14T15:47:10+00:00",
      "fingerprint": "d6cb095fc695a249",
      "id": "claim-defillama-low-main",
      "refs": [
        "547c6426c72953ad"
      ],
      "text": "DeFiLlama aggregated USDC price reached its lowest hourly value of the main window on 2023-03-11T08:00:00+00:00: 0.87667 (price_usd)."
    },
    {
      "created_at": "2026-10-14T15:47:10+00:00",
      "fingerprint": "1f7d1ecbf0a555f1",
      "id": "claim-bitstamp-low-main",
      "refs": [
        "e9d188069b6b8f1a"
      ],
      "text": "Bitstamp USDC/USD close reached its lowest hourly value of the main window on 2023-03-11T07:00:00+00:00: 0.86267 (close_usd)."
    },
    {
      "created_at": "2026-10-14T15:47:10+00:00",
      "fingerprint": "e4b34b4b2db224e7",
      "id": "claim-binance-low-main",
      "refs": [
        "09db96e264842925"
      ],
      "text": "Binance USDC/USDT close reached its lowest hourly value of the main window on 2023-03-11T15:00:00+00:00: 0.91280 (close_usdcusdt)."
    },
    {
      "created_at": "2026-10-14T15:47:10+00:00",
      "fingerprint": "3333b33545a9da63",
      "id": "claim-supply-contraction",
      "refs": [
        "c11e9e87d05d0f49",
        "27e8d337fdfe28ad"
      ],
      "text": "USDC circulating supply (DeFiLlama aggregate) fell from 43176044700 USD on 2023-03-10 to 42097257578 USD on 2023-03-11 (-1078787122 USD, -2.50%), a supply contraction."
    }
  ],
  "corpus": {
    "csv": "corpus/usdc_observations.csv",
    "flagged": 0,
    "kept": 520,
    "rejected": 0,
    "rows": 520
  },
  "coverage": {
    "first_two_venue_hour": "2023-03-09T00:00:00+00:00",
    "hours_by_independent_venue_count": {
      "2": 62,
      "3": 83
    },
    "hours_with_three_independent_venues": 83,
    "hours_with_two_plus_independent_venues": 145,
    "independent_price_venues": [
      "defillama",
      "binance",
      "bitstamp"
    ],
    "last_two_venue_hour": "2023-03-15T00:00:00+00:00",
    "per_venue": {
      "binance": {
        "coverage_ratio": 0.5724,
        "first_hour": "2023-03-11T14:00:00+00:00",
        "hours_covered": 83,
        "hours_in_window": 145,
        "last_hour": "2023-03-15T00:00:00+00:00",
        "metrics": [
          "close_usdcusdt"
        ],
        "observations": 83
      },
      "bitstamp": {
        "coverage_ratio": 1.0,
        "first_hour": "2023-03-09T00:00:00+00:00",
        "hours_covered": 145,
        "hours_in_window": 145,
        "last_hour": "2023-03-15T00:00:00+00:00",
        "metrics": [
          "close_usd"
        ],
        "observations": 145
      },
      "defillama": {
        "coverage_ratio": 1.0,
        "first_hour": "2023-03-09T00:00:00+00:00",
        "hours_covered": 145,
        "hours_in_window": 145,
        "last_hour": "2023-03-15T00:00:00+00:00",
        "metrics": [
          "price_usd"
        ],
        "observations": 145
      },
      "defillama_supply_aggregate": {
        "coverage_ratio": 0.0483,
        "first_hour": "2023-03-09T00:00:00+00:00",
        "hours_covered": 7,
        "hours_in_window": 145,
        "last_hour": "2023-03-15T00:00:00+00:00",
        "metrics": [
          "circulating_usd"
        ],
        "observations": 7
      },
      "defillama_supply_ethereum": {
        "coverage_ratio": 0.0483,
        "first_hour": "2023-03-09T00:00:00+00:00",
        "hours_covered": 7,
        "hours_in_window": 145,
        "last_hour": "2023-03-15T00:00:00+00:00",
        "metrics": [
          "circulating_usd"
        ],
        "observations": 7
      }
    },
    "window": {
      "end": "2023-03-15T00:00:00+00:00",
      "hours": 145,
      "start": "2023-03-09T00:00:00+00:00"
    }
  },
  "data_gate_examples": [
    {
      "hour": "2023-03-09T00:00:00+00:00",
      "missing": [
        "binance"
      ],
      "status": "OK",
      "venues_present": [
        "bitstamp",
        "defillama"
      ]
    },
    {
      "hour": "2023-03-11T07:00:00+00:00",
      "missing": [
        "binance"
      ],
      "status": "OK",
      "venues_present": [
        "bitstamp",
        "defillama"
      ]
    },
    {
      "hour": "2023-03-11T08:00:00+00:00",
      "missing": [
        "binance"
      ],
      "status": "OK",
      "venues_present": [
        "bitstamp",
        "defillama"
      ]
    },
    {
      "hour": "2023-03-11T15:00:00+00:00",
      "missing": [],
      "status": "OK",
      "venues_present": [
        "binance",
        "bitstamp",
        "defillama"
      ]
    },
    {
      "hour": "2023-03-15T00:00:00+00:00",
      "missing": [],
      "status": "OK",
      "venues_present": [
        "binance",
        "bitstamp",
        "defillama"
      ]
    },
    {
      "hour": "2023-03-16T00:00:00+00:00",
      "missing": [
        "defillama",
        "binance",
        "bitstamp"
      ],
      "status": "INSUFFICIENT",
      "venues_present": []
    }
  ],
  "generated_at": "2026-10-14T15:47:11.620648+00:00",
  "graph": {
    "claims_inserted": 4,
    "counts": {
      "claims": 4,
      "decision_nodes": 0,
      "hypotheses": 1,
      "observations": 520,
      "relations": 4,
      "sources": 4
    },
    "database": "evidence/graph.sqlite",
    "observations_inserted": 520,
    "relations_inserted": 4,
    "snapshot": {
      "counts": {
        "claims": 4,
        "decision_nodes": 0,
        "hypotheses": 1,
        "observations": 520,
        "relations": 4,
        "sources": 4
      },
      "graph_version": "orvyren-graph-v1",
      "hash": "6c02b63403aad46942c46060b9fa643f9e7683a7138164eeac7c712ab50f7294",
      "rows_total": {
        "claims": 4,
        "decision_nodes": 0,
        "hypotheses": 1,
        "observations": 520,
        "relations": 4,
        "sources": 4
      },
      "schema_version": 1
    },
    "sources": [
      "binance",
      "bitstamp",
      "defillama",
      "defillama_supply"
    ]
  },
  "hypotheses": [
    {
      "claims": [
        "claim-binance-low-main",
        "claim-bitstamp-low-main",
        "claim-defillama-low-main",
        "claim-supply-contraction"
      ],
      "criteria_refute": [
        "no independent venue prints a price below the 0.995 USD band",
        "the supply level is flat or rising across 2023-03-10 and 2023-03-11"
      ],
      "criteria_support": [
        "at least two independent venues print a price below 0.95 USD within the main window",
        "the aggregate circulating supply contracts day over day"
      ],
      "id": "H1-usdc-disclosure-disorder",
      "state": "UNDER_TEST",
      "statement": "USDC experienced a genuine market dislocation in March 2023, visible in independent venue prices and in a contraction of circulating supply."
    }
  ],
  "normalization": {
    "counts_by_metric": {
      "circulating_usd": 74,
      "close_usd": 145,
      "close_usdcusdt": 83,
      "price_usd": 218
    },
    "counts_by_venue": {
      "binance": 83,
      "bitstamp": 145,
      "defillama": 218,
      "defillama_supply_aggregate": 37,
      "defillama_supply_ethereum": 37
    },
    "flagged": [],
    "kept": 520,
    "rejected": [],
    "total": 520
  },
  "provenance": {
    "claims_checked": 4,
    "claims_failed": 0,
    "ok": true,
    "results": [
      {
        "checked": 1,
        "claim_id": "claim-binance-low-main",
        "error": null,
        "missing": [],
        "ok": true
      },
      {
        "checked": 1,
        "claim_id": "claim-bitstamp-low-main",
        "error": null,
        "missing": [],
        "ok": true
      },
      {
        "checked": 1,
        "claim_id": "claim-defillama-low-main",
        "error": null,
        "missing": [],
        "ok": true
      },
      {
        "checked": 2,
        "claim_id": "claim-supply-contraction",
        "error": null,
        "missing": [],
        "ok": true
      }
    ]
  }
}
```

## Limits & uncertainties

- Exposure parameters are demonstration values, not a real portfolio: 500.0 USDC exposure, 350.0 USDC floor, 100.0 USDC action.
- Corpus coverage is uneven: binance 83 observation(s); bitstamp 145 observation(s); defillama 145 observation(s); defillama_supply_aggregate 7 observation(s); defillama_supply_ethereum 7 observation(s); the control window has no exchange observations.
- The aggregator is a multi-venue median with possible lag; the supply series is daily and covers observable on-chain supply only.
- H2 identifies stress consistent with an asset/issuer event; price and supply data alone do not attribute it between the asset and its issuer.
- This engine produces a decision candidate only and never executes; the baseline A0 comparison lives in evidence/baseline_report.json.

## Evidence & integrity

| Input | Path | SHA-256 |
| --- | --- | --- |
| decision | evidence/decision_usdc-2023-03.json | `b65c0634be924b18954258dedb93e7f8965ae2728fb129f1dd56c39c01b76bbd` |
| baseline_report | evidence/baseline_report.json | `fa68d11f36232719f5400b5aab1d1cfab19b7808aaeb3e01297bd7bf4f868ae8` |
| policy_execution_demo | evidence/policy_execution_demo.json | `3712a68321bb7017d786eb94cd94630afde9f77eb93293037ae3adae4a953fe1` |
| quality_report | evidence/quality_report.json | `5478728ceb60ca0b066d65c674c398f848abce01cb57ed7630c1db842a30bed4` |
| dossier (self, md) | evidence/dossier_usdc-2023-03.md | `73399190489fac60b061a3441be1f62a5685f867788f4dfa3e92fd1f239e8ac7` |

Self-hash rule: the `dossier (self, md)` row is the SHA-256 of this Markdown file computed with its own 64-hex-character self-hash field zeroed (64 `0` characters). It is reproducible with any SHA-256 tool: replace that field with zeros and hash the file. With identical inputs and build time this dossier is byte-identical.

---

produced by ORVYREN-Core v0.1 — deterministic engine, no human edit · ORVYREN-Core v0.1 · generated 2026-10-14T15:47:12Z (UTC)
