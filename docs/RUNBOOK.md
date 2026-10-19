# ORVYREN — single-path runbook (demonstration)

One path, in order. Every command below was executed on **2026-10-18** from `D:/orvyren_core` (Windows 11,
Python 3.11.15, Node 22.23.2); the blocks show the output it produced, the times are wall-clock. If a step
does not print what is written here, stop and read §10 — the system is fail-closed, and a wrong "green" is
worse than a refusal.

- 10-minute narrative that drives these steps: `docs/DEMO_SCRIPT_10MIN.md`.
- What is deliberately **not** claimed: `docs/SUBMISSION_SCOPE_AND_GAPS.md`.
- Paths are relative to the repository root; runs write under `evidence/demo_runs/`; every
  `python -m orvyren.*` entry point needs `PYTHONPATH=src`.

## 1. Requirements — ≈ 1 min

```
$ python --version        # Python 3.11.15
$ node --version          # v22.23.2  (Node 20+ needed, frontend build only)
$ python -m pip install -r requirements.txt -r requirements-frontend.txt
Requirement already satisfied: …            (every line, exit 0, 3 s)
$ cd frontend && npm ci && cd ..
added 104 packages, and audited 105 packages in 51s
found 0 vulnerabilities                     (55 s)
```

`requirements.txt` is the isolated signer (`eth-account==0.14.0`); `requirements-frontend.txt` is the
dashboard backend (FastAPI/uvicorn); the core is stdlib-only and imports neither.

**If it fails.** `pip`: wrong interpreter (`python -c "import sys; print(sys.executable)"`). `npm`: Node
below 20 or no registry access; `frontend/node_modules/` is gitignored, so its absence before `npm ci` is normal.

## 2. Verify the suite — ≈ 2 min

```
$ python -m unittest discover -s tests -q
Ran 1546 tests in 73.427s

OK (skipped=3)                              (exit 0, wall 75 s)   [measured 2026-10-19T13:49Z]
```

The three skips are environment gates, each printing its reason under `-v`: `eth-account present: the
"library missing" path is not testable`, and twice `set ORVYREN_LIVE_RPC=1 to run the read-only Base
Sepolia RPC test`.

**If it fails.** Run from the repository root; a different `Ran N` means a different tree (`git status`),
not a different system. Never relax a test to make the step green — the suite is the rehearsal gate.

## 3. Verify the frozen evaluation protocol — ≈ 2 s

```
$ python scripts/verify_frozen.py
[OK]   G1.sha256 verified (a3bb291002037874…)
…
[OK]   offline recalc byte-identical (20 files, 1.05 s)
VERDICT: frozen package COMPLIANT
```

**If it fails** with `VERDICT: MISMATCHES DETECTED — do not claim`, a file under `frozen/` or a module
it covers changed without a visible re-seal: the tripwire working. Re-seal per `frozen/INDEX.md`; never
patch it silently.

## 4. Build and open the dashboard — ≈ 30 s (build 19 s, server 2–4 s), fully offline

```
$ cd frontend && npm run build && cd ..
vite v7.3.7 building client environment for production…
✓ 1693 modules transformed.
✓ built in 8.25s                            (19 s)

$ PYTHONPATH=src python -m orvyren.api
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8321 (Press CTRL+C to quit)
```

Then, in a second shell (the API is ready 2–4 s after start), before announcing anything:

```
$ curl -s http://127.0.0.1:8321/api/health
{"status":"ok","version":"orvyren/api/v1","graph_db":"../orvyren_10h_2026-10-17/graph_v3.sqlite","graph_db_absent":false,"frontend_dist":"frontend/dist","frontend_built":true,"mode":"offline-demo"}
```

Open **`http://127.0.0.1:8321`** — routes `/live`, `/graph`, `/markets`, `/decision`, `/audit` (`/`
redirects to `/live`). No network resource is fetched. Which graph is on screen is stated by the API, never
assumed: `graph_db_absent:false` plus 16 174 nodes / 12 937 relations / 15 000 Aave v3 Base events means the
50 MB database, a **local artifact outside the repository**; a clone without it falls back to
`evidence/graph.sqlite` (schema v2: 520 observations, 4 relations, no `nodes` table) and `/api/health` says so.

Fallback UI (stdlib, no Node, if the SPA cannot be built):

```
$ PYTHONPATH=src python run_audit.py --serve --port 8099 --out-dir "$LOCALAPPDATA/Temp/orvyren_audit_ui"
[orvyren-ui] 127.0.0.1 - "GET / HTTP/1.1" 200 -     → http://127.0.0.1:8099
```

Keep `--out-dir`: without it the tracked dossier `evidence/dossier_usdc-2023-03.*` is re-rendered with a new
`Generated (UTC)` line and goes dirty. Stop both servers with `Ctrl-C`; the API binds 127.0.0.1 only.

## 5. Replay a decision — < 1 s

```
$ PYTHONPATH=src python -m orvyren.decide --case usdc-2023-03 --replay
ORVYREN — decision (replay): usdc-2023-03
  epistemic_verdict    : CONCLUANT
  economic_action      : CONVERTIR/TRANSFÉRER
  authorization_verdict: None
  intent               : {"intent_id": "intent-usdc-2023-03-a-d1", "action": "transfer", "chain_id": 84532, …}
  rationale            : verdicts: H1 REFUTED, H2 SUPPORTED, H3 REFUTED ; RDOF: stop "stable decision (invariance c1)" after 1 search(es), cost 0.65 s / 1 call(s) ; action: CONVERTIR/TRANSFÉRER (catalog catalog/v1)
  written              : …\evidence\decision_record_usdc-2023-03.json
```

0.6 s, deterministic: it rewrites the tracked record byte-identically. The French value labels belong to the
sealed artifact contract (they are hashed), not to the competition language.

## 6. Replay a sealed agents run — ≈ 1 s

```
$ PYTHONPATH=src python run_agents.py --case usdc-2023-03 --replay journal
ORVYREN — run_agents · usdc-2023-03 · mode journal
  [orchestrator] done — 12 journal lines, state DONE/ARRET-1
    [critic] report written — verdict FRAGILE, 1 objection(s)
  ==== run summary usdc-2023-03 (journal) ====
    orchestrator   12 lines — agent_id:orchestrator — chain OK
    critic          1 lines — agent_id:critic — chain OK
    stop           : ARRET-1
    budget         : llm 5/30 · tools 2/12 · 0s/600s · $0.0018/$0.10
    escalation     : REQUIRE_APPROVAL (the critic never cancels — it brakes)
```

Exit 0, 1.1 s; a timestamped session appears under `evidence/demo_runs/agents/usdc-2023-03/`. `chain OK` on
both roles means the two JSONL journals were re-hashed and match the sealed heads. `--memory` is **off** by
default: enabling it changes the recorded prompt, so a memory run needs its own recording.

**If it fails** on another case (e.g. `--case rseth-2026-04`) with `E_LLM_NOT_RECORDED`, that case has no
recorded store (gap G-3) — use §7, never a simulated replay.

## 7. Agents → decision → policy → execution, dry-run — < 1 s

Feeds the DecisionRecord **from the sealed rsETH agents run** — no re-derivation, no key, no network:

```
$ PYTHONPATH=src python run_executor.py --case rseth-2026-04 --decision-source agents \
    --agents-run evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z
NOTE: ORVYREN_AGENT_MEMBER, ORVYREN_AVAILABLE_BALANCE unset — P11/P7 fail closed (DENY). Pass --demo-defaults for the offline demo.
ORVYREN — autonomous executor (dry-run)
  case       : rseth-2026-04  (1 tick(s) executed)
  policy     : v1.0  hash 6515358722284704  (…\policy_v1.yaml)
  tick  intent                                        amount   verdict   outcome
     1  -                                                 0.00  DENY      NO_ACTION
        denied: NO_ACTIONABLE_INTENT the DecisionRecord carries no executable intent
  journal chain    : VALID (1 record(s))
  summary    : 0 ALLOW · 1 DENY · 0 DRY-RUN · 0 signed · 0 error(s)
```

Exit 0, 0.55 s. This is the expected result, not a degraded one: in
`evidence/demo_runs/executor/rseth-2026-04/journal.jsonl` the record carries
`{"epistemic_verdict":"INCONCLUSIVE","economic_action":null,"authorization_verdict":"REQUIRE_APPROVAL"}`, `executed:false`,
`signed=0`. The agents abstained and the chain carried the abstention through policy to the executor — the
LLM's reasoning is the input of the decision, not decoration.

**If it fails** with `AgentsSourceError`, a journal head no longer matches the sealed `run_outcome.json` —
the run directory was edited. Re-clone; never patch a sealed run.

## 8. Verify a third-party audit packet — ≈ 1 s (self-test 3 s)

```
$ python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip
CHECK A1.exec.chain                RECOMPUTED  ok
…
CHECK B1.chain.rpc                 SKIPPED     ok
VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations n/a      (exit 0, 1.1 s)
```

`B1` is `SKIPPED` by design (no network offline). Prove the verifier still sees tampering: add `--mutate-test`
→ `MUTATION M1 … M6 detected (…)` for all six, then `VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations 6/6` (3.3 s).

**If it fails** with `OFFLINE_FAIL`, do not present the packet. The verifier is the frozen copy shipped
inside the packet: no repository, no API, no trust in us.

## 9. The `--execute` path — what is real, what is not

Prerequisites, read by name (values never printed): an explicit `--run-id`, `ORVYREN_PRIVATE_KEY`
(+ `eth-account`), `ORVYREN_AGENT_ADDRESS`, `ORVYREN_SAFE_ADDRESS`, `ORVYREN_RPC_URL_BASE_SEPOLIA`. With
`--execute` the gate is a **10-control fail-closed preflight** per intent, stopping at the first `FAIL`:
`POLICY_NOT_ALLOW`, `CHAIN_ID_MISMATCH`, `INTENT_EXPIRED`, `INTENT_ALREADY_PROCESSED`, `AGENT_PAUSED`,
`TARGET_CODE_MISSING`, `GAS_ESTIMATE_FAILED`, `INSUFFICIENT_GAS_BALANCE`, `INSUFFICIENT_TOKEN_BALANCE`,
`SIMULATION_REVERT`. A dry-run never touches it.

The three refusals, exercised here — each exits **4**, before any tick, so no journal is written:

```
$ PYTHONPATH=src python run_executor.py --case usdc-2023-03 --execute
ERROR --execute: E_CHAIN_RUN_ID_REQUIRED — a real run requires an explicit --run-id (fail-closed, never auto-generated); a re-run also passes --parent-run-id.

$ PYTHONPATH=src python run_executor.py --case usdc-2023-03 --execute --run-id demo-001
ERROR --execute: ORVYREN_PRIVATE_KEY missing or malformed — --execute refused (fail-closed)

$ ORVYREN_PRIVATE_KEY=0x1111…1111 PYTHONPATH=src python run_executor.py --case usdc-2023-03 --execute --run-id demo-001   # 64-hex dummy, never a real key
ERROR preflight: preflight configuration missing: ORVYREN_RPC_URL_BASE_SEPOLIA, ORVYREN_AGENT_ADDRESS, ORVYREN_SAFE_ADDRESS
```

**Not exercised: a signed, broadcast transaction.** Everything up to and including the preflight is
implemented and tested, but no run in this repository was signed end to end by the agent itself (gap G-12).
The 13 on-chain testnet transactions of the kit were signed by a human-held disposable key — 1 success, 12
forced reverts, and the reverts *are* the demonstration. Never show a dry-run as on-chain proof. Wallet,
faucets, Safe + Roles, runs A→E: `DEMO_KIT.md`.

## 10. Troubleshooting — the five failures that actually happen

| # | Symptom (exact message) | Cause / fix |
|---|---|---|
| 1 | `ModuleNotFoundError: No module named 'orvyren'` | `python -m orvyren.*` without `PYTHONPATH=src`, or wrong cwd. Prefix it and run from the repository root. |
| 2 | `ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8321)` | A previous API is still up. `Ctrl-C` it, or `ORVYREN_API_PORT=8322 PYTHONPATH=src python -m orvyren.api`. The trailing OS text is localised; the code is `10048`. |
| 3 | `GET /` → **503**, body `{"error":"frontend build not found","expected":"frontend/dist","hint":"run `npm ci && npm run build` in frontend/"}`; `/api/health` has `"frontend_built":false` | `frontend/dist` absent (gitignored). Build it (§4). Every `/api/*` route still works; only the SPA shell is missing. |
| 4 | `[critic] non-conforming output — quarantined (E_LLM_CALL_FAILED: E_LLM_NOT_RECORDED:<sha256>)` | `--replay journal` on a case with no recorded store (rsETH: gap G-3). Not a bug, never simulated — use §7, or record live with `--replay live --record-live`. |
| 5 | `usage error: target must be an audit packet zip or directory: README.md` (exit 2) | `run_verify.py` got something that is not a packet. Pass the `audit_packet_*.zip` from `evidence/audit_packets/`. |

Exit codes: `run_executor.py` 0 = ok, 3 = kill switch engaged (`ORVYREN_K0_PAUSED=1` → `PAUSE / kill switch
ENGAGED`, every tick `DENY`), 4 = `--execute` prerequisite refused; `run_verify.py` 0 = `PASS`/`OFFLINE_PASS`,
1 = `FAIL`, 2 = usage.

If none of these match, stop and read out what the terminal said — the gap register lists everything that may legitimately refuse.
