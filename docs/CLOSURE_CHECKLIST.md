# ORVYREN — closure checklist (10 items)

**Status snapshot: 2026-10-19T13:50Z.** Every “current evidence” line below was
measured on this working tree, at that date, with the command shown next to it.
“DONE” means the command was run and its output is quoted; “TODO” means the work
is not done; “BLOCKED” means the work cannot be completed from this tree alone
(no commit / no clean clone / an upstream artefact must be rebuilt first).

The tree is **not yet frozen**: files were still being edited at 13:47Z. Nothing
below may be re-dated without re-running the command.

| # | Closure item | Status | Current evidence (measured) | Proving command |
|---|---|---|---|---|
| 1 | Closing SHA fixed | **BLOCKED** | No commit exists for today's tree yet; the orchestrator owns commits. Docs, tests and `scripts/run_scenario_rseth.py` all changed on 2026-10-19 (mtimes 13:27–13:47Z), so no SHA can be quoted as the submission state. | `git status --porcelain` (must print nothing) · `git rev-parse HEAD` → record the 40 hex chars here |
| 2 | Suite + front build **on that SHA**, raw outputs kept | **BLOCKED** on item 1 (suite itself is green) | `Ran 1546 tests in 75.190s` / `OK (skipped=3)` at 2026-10-19T13:57Z on the working tree (three consecutive green runs: 13:40, 13:49, 13:57Z). `frontend/dist/` exists but was not rebuilt after the last source edits; no run on a frozen SHA. | `python -m unittest discover -s tests -q 2>&1 \| tee dist/closure/tests.txt` · `cd frontend && npm ci && npm run build 2>&1 \| tee ../dist/closure/frontend-build.txt` · after commit: `make test-clone` |
| 3 | Test counters synchronised | **DONE** | One counter only: **1546 tests, OK (skipped=3), measured 2026-10-19T13:49Z** in `README.md` (3 places), `docs/RUNBOOK.md`, `docs/SECURITY.md`, `docs/TECHNICAL.md`, `docs/SUBMISSION_SCOPE_AND_GAPS.md`, `docs/DEMO_SCRIPT_10MIN.md`, `DEMO_KIT.md`. A `grep` for the three retired counters returns **no match** (this table writes the pattern so it does not match itself). | `python -m unittest discover -s tests 2>&1 \| grep -E "^Ran"` · `grep -rnE '14(11\|18)\|15(15)' README.md docs/*.md DEMO_KIT.md` → empty |
| 4 | rsETH scenario regenerated from the delivered run | **TODO** | `evidence/scenario_rseth/scenario_report.md` line 3 still cites agents run `rseth-2026-04_live_20261018T110722Z`, while the delivered run is `…T200027592497Z` (`evidence/demo_runs/agents/rseth-2026-04/`). The report is therefore one run behind the shipped artefact (gap G-13). | `head -3 evidence/scenario_rseth/scenario_report.md` · `ls evidence/demo_runs/agents/rseth-2026-04/` · regenerate: `python scripts/run_scenario_rseth.py --help` (agents source), then re-check the header matches `run_outcome.json` |
| 5 | EVAL contradiction resolved | **DONE** | `evidence/evaluation/SUPERSEDED_NOTE.md` is now a dated historical note (17/10 artefacts, why replaced, operation order, what stays true); G-16 is closed; README no longer claims an unrun evaluation (it states N=1, 2026-10-19, no superiority claim). Current report: `generated: 2026-10-19T03:00:46Z`, `content hash c143c243…`, N=1, superiority `NOT COMPUTED`. | `head -40 evidence/evaluation/SUPERSEDED_NOTE.md` · `head -3 evidence/evaluation/evaluation_report.md` · `grep -n "G-16" docs/SUBMISSION_SCOPE_AND_GAPS.md` · `grep -rnE 'N ?= ?0' README.md docs/*.md` → empty |
| 6 | Freeze chronology documented | **DONE** | `frozen/G6_FEUILLE_DE_SIGNATURE.md`: **SIGNED — validated on 2026-10-19**, “re-sealed after translation + sensitivity, no parameter changed, **before first EVAL**”. Order (translation → sensitivity → re-seal → signature → EVAL 03:00:46Z) is written in `SUPERSEDED_NOTE.md` §c and `frozen/README.md`. | `python scripts/verify_frozen.py` → `VERDICT: frozen package COMPLIANT` (measured 2026-10-19T13:33Z) · `tail -1 evidence/evaluation/variants.log` |
| 7 | `.docx` regenerated from the final `.md` | **TODO** | `dist/docs/*.docx` are dated 13:27–13:31Z, **before** the Markdown edits of 13:45–13:50Z (counters, graph note, demo script). No in-repo generator target exists (`grep docx Makefile` → empty): regeneration is manual, and G-17 already declares that the `.docx` may lag. | `ls -la dist/docs/*.docx` vs `ls -la README.md docs/*.md` (docx must be newer) · re-export each `.md` (pandoc / LibreOffice) then `ls -la dist/docs/` |
| 8 | Package built in a clean environment + audit ZIP verified **separately** | **BLOCKED** | (a) `python run_verify.py evidence/audit_packets/audit_packet_rseth_20261016-2340_01M526YS.zip` → **`VERDICT: FAIL — 16 checks, 2 failed`** at 2026-10-19T13:42Z (`A4.dossier.rerender.md` and `.html` byte mismatch: `src/orvyren/audit/dossier.py` changed after the packet was built). (b) The newest review ZIP `dist/orvyren_core_review_2026-10-19.zip` is dated 12:15Z, before today's edits. The `OFFLINE_PASS`, 16/0 claim is **not reproducible from the shipped packet** until it is rebuilt. (c) Rebuild gate run on 2026-10-19T14:10Z: **Safe USDC balance = 0** on Base Sepolia (agent gas 0,001486 ETH, sufficient; D1–D10 pass, module enabled). Run A is frozen at 100 USDC, so a fresh 13-receipt session cannot be produced — `INSUFFICIENT_TOKEN_BALANCE` — until the Safe is funded (Circle faucet: 20 USDC per (asset, network) per 2 h ⇒ 5 requests ≈ 8 h). Alternative, if chosen: a declared deviation to 20 USDC, carried to the gaps register. | `python run_verify.py <packet>.zip` → must print `OFFLINE_PASS — 16 checks, 0 failed` · `run_verify.py <packet>.zip --mutate-test` → `mutations 6/6` · `make docker-test` (clean env) · `unzip -l dist/orvyren_core_review_*.zip \| head` |
| 9 | Demo run from a clean clone | **TODO** | Not performed. A clone does not contain the 16,174-node database (G-14): the demo must read `evidence/graph.sqlite` (520 observations, schema v2). `make test-clone` uses `git archive HEAD`, so it depends on item 1. | after commit: `make test-clone` · `git clone <repo> /tmp/orvyren_clean && cd /tmp/orvyren_clean && cd frontend && npm ci && npm run build` · then the `docs/DEMO_SCRIPT_10MIN.md` pre-flight (including its audit gate) |
| 10 | Closure time verified | **TODO** | No closure timestamp recorded yet. It must be taken **after** items 1–2 and 7–8 pass, not before. | `date -u +%Y-%m-%dT%H:%M:%SZ` → paste the value into this file and into the submission form; re-run items 2, 3, 6 and 8 in the same minute |

## Blocking summary (read this first)

1. **Item 8 is the hard blocker**: the shipped audit packet fails verification
   (2/16) because `src/orvyren/audit/dossier.py` postdates it. Rebuild the packet
   from the current code, then re-run `run_verify.py` **and** `--mutate-test`.
2. **Item 1 is the gate for 2 and 9**: no SHA means no frozen submission state,
   and `make test-clone` cannot run.
3. **Item 4** is a content staleness, not a failure: the report is valid but
   describes the 11:07Z run, not the delivered 20:00Z run.
4. Items 3, 5 and 6 are closed and dated; do not re-open them by editing prose
   without re-running their proving command.

## Definition of done

All ten rows read **DONE**, each with a timestamp **after** the closing SHA, and
the two raw outputs (`dist/closure/tests.txt`, `dist/closure/frontend-build.txt`)
are stored next to the submission bundle. Any row left TODO/BLOCKED must be
listed as an open gap in `docs/SUBMISSION_SCOPE_AND_GAPS.md`, not silently
dropped.
