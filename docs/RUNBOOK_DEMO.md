# ORVYREN — Demo Runbook (single path)

One path, in order. Every command runs from the repository root on a clean
clone. No oral explanation is required: each step prints its own evidence.

## 0. Requirements

- Python 3.11 (`python -m unittest ...` must work; the core is stdlib-only)
- Node 20+ (frontend build only)
- Optional for the LIVE agent leg: LLM keys in `scripts/demo/.env`
  (`ORVYREN_DEEPSEEK_API_KEY`, `ORVYREN_MIMO_API_KEY`) — never committed,
  checked by `python scripts/demo/check_env_hygiene.py` (VERDICT: OK)

## 1. Verify the suite (≈ 80 s)

```
python -m unittest discover -s tests -q
```

Expected: `Ran 1411 tests ... OK (skipped=3)` (the 3 skips are documented:
2 testnet RPC gates, 1 eth-account absent path).

## 2. Verify the frozen evaluation protocol

```
python scripts/verify_frozen.py
```

Expected: `VERDICT: frozen package COMPLIANT` (byte-identical recalculation).

## 3. Build and open the dashboard (offline demo)

```
pip install -r requirements-frontend.txt
cd frontend && npm ci && npm run build && cd ..
PYTHONPATH=src python -m orvyren.api
```

Open `http://127.0.0.1:8321` — five screens on real artifacts: Live (agent
runs, WebSocket), Graph (16,174 nodes, Q1–Q8 panel), Markets (3 stress
episodes), Decision & Policy (RDOF + P1–P14 verdicts + receipts), Audit
(journal chains recomputed, sealed packets). No network resource is fetched.

## 4. Replay the demonstration scenario (offline, no key)

```
python scripts/run_scenario_rseth.py --collect-only
```

Collects the versioned artifacts of the executed live run into
`evidence/scenario_rseth/` and prints the step summary. The full narrative
(risk → hypotheses → evidence → decision → policy → execution) is
`evidence/scenario_rseth/scenario_report.md`.

**Honest reading of the execution leg (declared substitution).** The rsETH
conclusion is the agents' abstention (ARRET-3, critic INCOHERENTE →
REQUIRE_APPROVAL). The execution tick in the artifacts replays the **pilot
USDC decision** to demonstrate the mechanism (policy → chained journal →
run_id): the rsETH case decision follows the documented abstention path
(`E_WHAT_WOULD_CHANGE_REQUIRED` on the probe is the recorded refusal, kept as
evidence). Do not project the execution journal without this reading — the
dashboard shows the same banner.

**Graph data used by the demo.** The redistributable demo graph is
`evidence/graph.sqlite` (520 observations, schema v2) + `evidence/ui_snapshot.json`;
the 16,174-node / 12,937-edge Aave v3 database (~50 MB) is a **local artifact**
(`D:/orvyren_10h_2026-10-17/graph_v3.sqlite`) with its reconstruction pipeline,
not in the repository. The dashboard and the scenario state which database
they are on; nothing claims the 16k graph comes from a clone.

## 5. Run the scenario LIVE (optional — needs the keys of step 0)

```
(set -a; source scripts/demo/.env; set +a; python scripts/run_scenario_rseth.py)
```

Expected: a sealed live session (real DeepSeek/MiMo calls, cost printed),
critic verdict, honest abstention with `what_would_change`, dry-run execution
chained to the agents run_id, policy DENY fail-closed. The script stops
honestly on any failure (rc 2 = missing keys, rc 5 = failed step) and never
fabricates an artifact.

## 6. Run the A0-vs-A2 benchmark (offline)

```
python run_benchmark_ab.py --cases usdc-2023-03 placebo-calm-2023-03 --runs 3 --out-dir evidence/benchmark_ab
```

Expected: `report.json` + `report.md` with the mandatory small-N banner
("no superiority claim"), the placebo labelled synthetic, and the honesty
sections (when agents help / add nothing / must abstain) always rendered.
Read the report WITH its three caveats in the same view: the A2 leg is one
recorded run replayed (not independent samples), the placebo A2 leg may be
`not_executed`, and A0 runs without the pilot RDOF outside `usdc-2023-03`.
The benchmark shows an auditable brake; agent usefulness is **not** measured.

## 6b. Fallback plan if a live LLM provider is down

The demo never depends on a provider being up:

```
python run_agents.py --case usdc-2023-03 --replay journal --session evidence/demo_replay
```

Deterministic recorded replay (~1 s), same journals, same hash chains.
A live run that meets a dead provider stops honestly (bounded retries, stable
error codes, never a fake OK) — switch to the replay and continue.

## 7. Verify an audit packet (third-party check, no repo needed)

```
python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip
```

Expected: `OFFLINE_PASS` (class-A checks recomputed, mutations detected).

## Known gaps

See `docs/SUBMISSION_SCOPE_AND_GAPS.md` (gap register G-1..G-11) — nothing
outside that register is claimed.
