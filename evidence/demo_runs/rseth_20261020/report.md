# ORVYREN — demo session report

- session: `evidence/demo_runs/rseth_20261020`
- run_id: `01M5CCNNTXNSC3YEVEPAJFBWWH` · case: `rseth` · mode: **execute**
- chain: Base Sepolia (84532) — testnet only, no real money

## Journal (SHA-256 chained append-only)

- records: **64**
- recomputed chain: **OK (no write detected)**
- stream heads: `{"exec": "baef83d061f0c2872ce3f3391349155981a9ab01174f7b2ad839b5d7c632ecce"}`

## Counters

- authorized executions (POLICY ALLOW entries): 3
- off-chain refusals (POLICY DENY): 6
- approval requests (REQUIRE_APPROVAL): 1
- submitted transactions: 10 · receipts recorded: 10
- signatures issued by the service: 10

## Independent verification (re-reading the tx_hash values)

- 1 compliant executions, 6 off-chain refusals, 9 forced attempts refused by the chain

## What this report does not prove

- testnet prices are not market data (no performance is claimed);
- in dry-run, **no transaction was sent**: the hashes are placeholders tagged `simulated`;
- coverage is not exhaustiveness: what is not journaled does not exist for the reviewer.
