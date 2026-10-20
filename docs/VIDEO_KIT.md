# ORVYREN — video kit (≤ 5 minutes, English)

**Measured on this working tree, 2026-10-20, 09:05–09:15 UTC.** Every command in
this file was executed before it was written; the outputs below are the real ones.
Where reality differs from `docs/DEMO_SCRIPT_10MIN.md`, the difference is stated
in the block (§3.4) and collected in §7 — the video says what the machine said,
not what the ten-minute script hoped.

**Shape.** Five content blocks plus a 15-second closing line. Total **4:45**, with
15 s of margin against the 5:00 limit. Each block starts and ends on a known
screen, so a mistake costs 30–70 s, never the whole video.

| Block | In | Out | Dur | Screen (SPA route) | Command executed | Words | Pace |
|---|---|---|---|---|---|---|---|
| 1 — the thesis, abstention as a result | 0:00 | 0:30 | 30 s | `/live` | `curl /api/health` (optional) | 60 | 120 wpm |
| 2 — the rsETH case, measured | 0:30 | 1:30 | 60 s | `/markets` | `sed -n '10,22p' run_inputs.json` | 107 | 107 wpm |
| 3 — the agent run on screen | 1:30 | 2:40 | 70 s | `/live` | `grep` on `run_outcome.json` | 132 | 113 wpm |
| 4 — agents → decision → policy → execution | 2:40 | 3:40 | 60 s | terminal only | `run_executor.py --dry-run` | 104 | 104 wpm |
| 5 — third-party verifier + the honest limit | 3:40 | 4:30 | 50 s | `/audit` + terminal | `verify/orvyren_verify.py .` | 86 | 103 wpm |
| 6 — closing line | 4:30 | 4:45 | 15 s | `/live` | — | 28 | 112 wpm |

Average pace 109 wpm: slow enough to read numbers, fast enough to fit the limit.
The word counts are the subtitle text of §6 — they are the same words.

## 1. Rules of this kit

- **English voice-over, English subtitles.** The subtitles are mandatory and are
  in §6, already timed to the block boundaries.
- **The jury sees the system run.** Five of the six blocks contain a command the
  operator types on camera: `curl`, `sed`, `grep`, `python run_executor.py`,
  `python verify/orvyren_verify.py`. The only pre-recorded element is the agent
  run itself, and the screen says so ("Recorded agent run · single source: run
  outcome").
- **No number is read unless it is on screen or produced by the command in the
  same shot.** Each block below names the file or endpoint behind each figure.
- **One take per block, no cuts inside a block.** If a command prints something
  unexpected, stop, do not narrate around it — see §4.
- **Never speed up, loop or re-time footage of a run and present it as live.**

## 2. Pre-flight (T-15 minutes)

Run these in order. Each one is a gate: if it fails, fix it before recording.

**2.1 — API up.** In one terminal, from the repository root:

```bash
cd D:/orvyren_core
PYTHONPATH=src python -m orvyren.api
```

Server binds `127.0.0.1:8321`. In a second terminal:

```bash
curl -s http://127.0.0.1:8321/api/health
```

Measured today:

```text
{"status":"ok","version":"orvyren/api/v1","graph_db":"../orvyren_10h_2026-10-17/graph_v3.sqlite","graph_db_absent":false,"frontend_dist":"frontend/dist","frontend_built":true,"mode":"offline-demo"}
```

`"frontend_built":true` is gate 2. `"mode":"offline-demo"` is the claim the video
makes: no network. (`graph_db` points outside the repository — see §7, item 2.)

**2.2 — frontend build.** `frontend/dist/` is present and served (visible in the
payload above). **Do not rebuild 30 minutes before recording**: a rebuild changes
chunk hashes and can shift layout. If you do rebuild (`cd frontend && npm run
build`), re-walk all five routes before the first take.

**2.3 — which graph.** `curl -s http://127.0.0.1:8321/api/graph/info | head -c 300`.
This machine has the 16,174-node local database; a clone falls back to
`evidence/graph.sqlite` (520 observations). Both are legitimate; know which one
you are showing, because §7 forbids one specific sentence about it.

**2.4 — browser.** One window, 1920×1080, **zoom 100 %** (Ctrl+0), no other tabs,
no bookmarks bar, full screen (F11). Dark or light theme does not matter; the
first frame of every block must be the same theme.

**2.5 — the live stream chip.** On `/live`, the chip next to "Evidence" must read
`Connection LIVE · N ms`. If it reads `Connection DEGRADED — Stream interrupted`,
the WebSocket dropped: hard reload (Ctrl+Shift+R). If it persists, kill the API
and relaunch it, then reload. Do not record a `DEGRADED` chip: it looks like a
broken product, and it hides that the numbers are recomputed from files.

**2.6 — terminal.** Two panes side by side, font 16 pt minimum, prompt shortened
for the shoot:

```bash
export PS1='$ '
export PYTHONIOENCODING=utf-8
clear
```

The commands in §3 are copy-pasteable as written; nothing needs editing on camera.

**2.7 — audit packet extracted** (Block 5), once, off camera:

```bash
cd ~ && rm -rf orvyren_audit && mkdir orvyren_audit && cd orvyren_audit
unzip -q D:/orvyren_core/evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip
```

Result: `~/orvyren_audit/audit_packet_rseth_20261020-1012_01M5CCNN/`.

**2.8 — recording.** 60 fps, cursor visible, notifications off (Windows Focus
Assist → Alarms only), microphone armed, and a clock visible off-screen for the
block boundaries.

## 3. The blocks

### 3.1 — Block 1 · 0:00–0:30 · "the thesis, and abstention as a result"

**Screen.** Route `/live`, URL `http://127.0.0.1:8321/live`. Nothing is clicked.
The Run selector is already on `rseth-2026-04_live_20261018T200027592497Z`, and
the two panels in frame are **Run budget** (LLM 5/30, Tool 1/12, Elapsed 34.4/600 s,
Cost $0.0357/$0.10) and **Agent outcome** (ABORTED · Stop ARRET-3 · Critic verdict
INCOHERENTE · Escalation REQUIRE_APPROVAL).

**Command (optional, 3 s).** If you want one proof of life before the first
sentence:

```bash
curl -s http://127.0.0.1:8321/api/health
```

Output: the one-line JSON quoted in §2.1. Cut it if you prefer a clean screen
opening — it also displays the out-of-repo `graph_db` path, which invites a
question you do not want at second five.

**Voice-over (exact, 60 words).**

> One claim: an agent that knows when to stop. This is ORVYREN, a bounded on-chain
> agent for DAO treasuries. It reads, it reasons, it refuses. Today the interesting
> result is not a trade. It is an abstention: the reason written down, the budget
> spent written down, and a packet anyone can verify offline. Everything here runs
> on this machine, offline.

**Direction.** Hold on the two panels; no scroll until "It is an abstention", then
a single scroll to centre **Agent outcome** on "the reason written down". The
cursor stays still. Do not say "demo": say "this machine".

---

### 3.2 — Block 2 · 0:30–1:30 · "the rsETH case, measured"

**Screen.** Route `/markets`, URL `http://127.0.0.1:8321/markets`. Episode
selector on `rseth-2026-04 — rsETH / KelpDAO -- Aave V3 Ethereum Core` (default).
Three headline cards are in frame: **Oracle price at freeze $2,513.66**,
**Peak supply-cap usage 99.999 % (529,993.98 / 530,000 rsETH)**,
**First frozen block 24,908,723**. Keep the `cash` chart visible: the drop between
the 18:00 and 19:00 marks is the freeze.

**Command (typed at 0:55, 2 s).**

```bash
cd D:/orvyren_core
sed -n '10,22p' fixtures/agents/rseth-2026-04/run_inputs.json
```

**Measured output (today):**

```text
    "facts": {
      "freeze_first_frozen_block": 24908723,
      "freeze_first_frozen_utc": "2026-04-18T19:03:59Z",
      "supply_cap_saturation_ratio": 0.9999886466022144,
      "supply_cap_saturation_utc": "2026-04-18T18:00:00Z",
      "oracle_at_freeze_usd": 2513.66460329,
      "market_price_usd": 1686,
      "oracle_market_divergence_pct": -31,
      "rseth_utilisation_at_freeze": 7.946826023583168e-05,
      "collateral_rseth_at_exploit": 89567,
      "weth_borrowed_usd_at_exploit": 190000000,
      "stress_marker": "KelpDAO/LayerZero exploit; rsETH reserve administratively frozen; market frozen"
    }
```

This is the **frozen input the agents were given** — not a slide. If the first
line is not `"facts": {`, the file shifted: `grep -n '"facts"' fixtures/agents/rseth-2026-04/run_inputs.json`
and adjust the two line numbers before recording.

**Voice-over (exact, 107 words).**

> April 18th, 2026. rsETH, Aave v3 core market. The oracle marked 2,526.76 dollars
> at the exploit block, and 2,513.66 at the freeze. The documented market price was
> 1,686: the oracle overstated the collateral by about a third. Just over an hour
> earlier, the supply cap had saturated at 99.999 percent — 529,993.98 out of
> 530,000 rsETH. Six tokens of room left, not a closed door. Then the reserve was
> frozen at block 24,908,723. Utilisation at the freeze was 0.0079 percent, so the
> counter-intuitive story, a liquidity squeeze, is refuted by measurement. 89,567
> rsETH of collateral, 190 million borrowed. The question is not prediction. It is:
> what do you do when the proof is missing?

**Where each figure lives (do not improvise a source).**

| Figure | Value | File · key |
|---|---|---|
| oracle at exploit block 24,908,282 (17:34:59) | 2,526.7563881 | `evidence/episode_rseth_2026-04.json` · `feed_checks[0].aave_oracle_price` |
| oracle at freeze block 24,908,723 | 2,513.66460329 | same file · `feed_checks[3]`, `headline.rsETH_oracle_at_2026-04-18T19:03:59Z` |
| market price (documented) | 1,686 | `fixtures/agents/rseth-2026-04/run_inputs.json` · `market_price_usd` |
| cap ratio | 0.9999886466 → 99.999 % | same file · `supply_cap_saturation_ratio`; `a_token_supply_at_cap_max` 529,993.9827 |
| residual capacity | 6.0173 rsETH | computed: 530,000 − 529,993.9827 |
| first frozen block | 24,908,723 | `evidence/episode_rseth_2026-04.json` · `freeze_transition.first_frozen_block` (14-step binary search) |
| utilisation at freeze | 7.9468e-05 → 0.0079 % | `run_inputs.json` · `rseth_utilisation_at_freeze` |
| collateral / borrowed | 89,567 rsETH / 190 M USD | `run_inputs.json` · `collateral_rseth_at_exploit`, `weth_borrowed_usd_at_exploit` |

**Two arithmetic traps — say "about a third", never "−31 %".**
`1686 / 2526.7563881 − 1 = −33.27 %`; `1686 / 2513.66460329 − 1 = −32.93 %`. The
file stores `oracle_market_divergence_pct: -31`, a documented round figure, and
**the sealed run's own critic flags the mismatch** (finding `CONTRADICTION`,
severity MAJEUR). The video says "about a third", which is true for both readings.

**Direction.** Point at the three cards in order (price, cap, block). The command
cut happens on "Just over an hour earlier". Come back to the screen on "Utilisation
at the freeze". Do not open "Episode facts (all, raw keys)" — the terminal already
shows the same numbers, and the panel scrolls the cards out of frame.

---

### 3.3 — Block 3 · 1:30–2:40 · "the agent run on screen"

**Screen.** Route `/live` (same tab), URL `http://127.0.0.1:8321/live`. Confirm
**Run** = `rseth-2026-04_live_20261018T200027592497Z`. Two frames carry the block:
**Run budget** (5/30 · 1/12 · 34.4/600 s · $0.0357/$0.10) and **Agent outcome**
(ABORTED · Stop ARRET-3 · Reason `E_LOOP_OUTPUT_INVALID: orchestrator plan invalid after re-prompt` · Critic verdict
INCOHERENTE · Escalation REQUIRE_APPROVAL). Below it, the journal badges
`PLAN: 4 · REFLECTION: 6 · TOOL_CALL: 1 · TOOL_RESULT: 1 · STOP: 1`.

**Command (typed at 2:05, 3 s).**

```bash
grep -E '"(stop_condition|verdict_lecture)"' \
  evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/run_outcome.json
```

**Measured output (today):**

```text
  "verdict_lecture": "INCOHERENTE"
  "stop_condition": "ARRET-3"
```

Optional second proof, if you have 5 spare seconds (used only if you skip the
health check in Block 1):

```bash
grep -A5 '"budget_used"' evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z/run_outcome.json
```

```text
"budget_used": {
   "cost_usd": 0.035731098,
   "llm_calls": 5.0,
   "tool_calls": 1.0,
   "wall_seconds": 34.42200000000594
  },
```

**Voice-over (exact, 132 words).**

> This is the recorded run. Every number comes from one outcome file, not from a
> re-enactment. Five LLM calls out of thirty. One tool call out of twelve.
> Thirty-four seconds out of six hundred. Three and a half cents out of ten. The
> run stopped itself: ARRET-3, abstention. The critic runs in a separate process.
> It returned INCOHERENTE. It does not decide. It brakes. And it forces escalation
> to a human. Why it stopped: the plan was refused because the discriminating
> criterion contained a digit. That is a schema rule, not a judgement. The
> hypothesis that should have won, a liquidity squeeze, was refuted by the
> utilisation you just saw. The plan also lists what it did not search: oracle
> freshness, the per-account debt ledger, the realisable value of frozen collateral.

**Direction.** Say "Five LLM calls out of thirty" with the cursor on the card, one
click per figure (count, tool, time, cost). Cut to terminal for the two `grep`
lines on "The run stopped itself", back to screen on "The critic runs in a separate
process". Open one `PLAN` event (the "Expand" link) while saying "what it did not
search" — the five `non_recherche` bullets are in that payload, in French.

**Do not run a live LLM call in this block.** It costs money, it is
non-deterministic, and every number in the subtitles would become false. The point
of the block is that the run *replays*: the chip says "Recorded agent run".

**Precision note (worth one sentence if a jury member asks).** The five research
leads are in the **plan payload** of the run. The bridge field
`outcome.non_recherche` — the one the DecisionRecord copies into
`what_would_change` — is **empty**, because the run stopped at ARRET-3 before
enumerating it; `evidence/scenario_rseth/scenario_report.md` line 55 declares that
gap rather than filling it by hand. The five *sourced* leads live in the A1–A5
abstention complement (same report, §decision). Say "the plan lists what it did not
search", never "the run produced five follow-ups".

---

### 3.4 — Block 4 · 2:40–3:40 · "agents → decision → policy → execution"

**Screen.** Terminal, full frame. No SPA route carries this chain: `/decision`
shows the **USDC pilot** case only (`/api/decision/cases` → `["usdc-2023-03"]`),
so cutting to it during an rsETH block would show a different case. If you want a
3-second cut to `/audit` on "the journal chain verifies", do it — but the 84-record
chain displayed there is the 16/10 demonstration chain, **not** the dry-run you
just executed; say it, or do not cut.

**Command.**

```bash
cd D:/orvyren_core
python run_executor.py --case rseth-2026-04 --decision-source agents \
  --agents-run evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z \
  --dry-run
```

**Measured output (today, 0.42–0.67 s):**

```text
NOTE: ORVYREN_AGENT_MEMBER, ORVYREN_AVAILABLE_BALANCE unset — P11/P7 fail closed (DENY). Pass --demo-defaults for the offline demo.
ORVYREN — autonomous executor (dry-run)
  case       : rseth-2026-04  (1 tick(s) executed)
  policy     : v1.0  hash 6515358722284704  (D:\orvyren_core\policy_v1.yaml)
  envelope   : PASS (source: fixture)
  recipient  : 0x1111111111111111111111111111111111111111
  ledger     : D:\orvyren_core\evidence\demo_runs\executor\rseth-2026-04\ledger.json  (0.00 USDC spent / 24 h before the run)
  journal    : D:\orvyren_core\evidence\demo_runs\executor\rseth-2026-04\journal.jsonl
  tick  intent                                        amount   verdict   outcome
     1  -                                                 0.00  DENY      NO_ACTION
        denied: NO_ACTIONABLE_INTENT the DecisionRecord carries no executable intent
  journal chain    : VALID (1 record(s))
  summary    : 0 ALLOW · 1 DENY · 0 DRY-RUN · 0 signed · 0 error(s)
  spent 24 h after the run : 0.00 USDC
```

**Voice-over (exact, 104 words).**

> Now the chain, in one command. The agents run feeds a DecisionRecord. The record
> feeds a fourteen-rule policy, written in YAML, outside the model. The policy
> feeds the executor. Verdict: DENY. Not because the state was unreadable. Because
> the DecisionRecord carries no executable intent. An abstention produces no
> action, by construction. Zero signed. Zero spent. The journal chain verifies. The
> model proposes. The system decides. The key never enters the model's process.
> This path is dry-run only. The execute branch exists. It is preflighted on every
> run. This system has never exercised it. I will not show you a signature I did
> not make.

**Direction.** Type the command on "Now the chain", press Enter, and let the table
land before speaking the verdict. Point at `DENY` then `NO_ACTION`, then at
`0 signed`. Leave the `NOTE:` line in frame: two environment variables unset and
the policy fails closed — that is the safety story, not noise.

**Correction to the ten-minute script.** `DEMO_SCRIPT_10MIN.md` says this DENY
comes from unreadable state (`BALANCE_UNREADABLE`, `AGENT_NOT_MEMBER`). Measured
today the denial code is **`NO_ACTIONABLE_INTENT`** — the bridge refused because
the DecisionRecord carries no intent. Same conclusion (no action), different
reason. Say the reason you see on screen.

**Each take adds one directory** under
`evidence/demo_runs/executor/rseth-2026-04/chain/<run_id>/` — that is the audit
trail, not clutter. Do not delete them on camera.

---

### 3.5 — Block 5 · 3:40–4:30 · "third-party verification, and the honest limit"

**Screen.** Route `/audit`, URL `http://127.0.0.1:8321/audit`. Expand
**"Verify without the repository"** before recording: it prints the exact command
`python verify/orvyren_verify.py .`, which is what you then type. The panel
**Offline audit packet** shows 45 files · 224.4 kB and the published sha256
`63f4cefd905047eca2f71b4fa0c99fb05fb4cdb38bcc661919583f0c7592b83f`.

**Command (four lines, typed at 3:48).**

```bash
cd ~/orvyren_audit/audit_packet_rseth_20261020-1012_01M5CCNN
python verify/orvyren_verify.py .
```

**Measured output (today, 0.50 s):**

```text
CHECK A1.exec.chain                RECOMPUTED  ok
CHECK A1.agent.absent              COVERED     ok
CHECK A1.graph.chain               RECOMPUTED  ok
CHECK A2.dossier.md                RECOMPUTED  ok
CHECK A2.dossier.html              RECOMPUTED  ok
CHECK A3.packet.sha256             RECOMPUTED  ok
CHECK A3.dossier.inputs            RECOMPUTED  ok
CHECK A4.dossier.rerender.md       RECOMPUTED  ok
CHECK A4.dossier.rerender.html     RECOMPUTED  ok
CHECK A5.policy.verdicts           RECOMPUTED  ok
CHECK A6.graph.snapshot            RECOMPUTED  ok
CHECK A7.fixtures.signals          RECOMPUTED  ok
CHECK A8.receipts.cross            RECOMPUTED  ok
CHECK C1.agent.journal             COVERED     ok
CHECK C2.refs.resolve              COVERED     ok
CHECK B1.chain.rpc                 SKIPPED     ok
VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations n/a
```

**Then, second command (typed at 4:12, 2.6 s):**

```bash
python verify/orvyren_verify.py . --mutate-test
```

**Measured output (last 7 lines):**

```text
MUTATION M1 detected (A2.dossier.md, A3.packet.sha256, A4.dossier.rerender.md)
MUTATION M2 detected (A1.exec.chain, A3.packet.sha256)
MUTATION M3 detected (A3.dossier.inputs, A3.packet.sha256, A4.dossier.rerender.html, A4.dossier.rerender.md)
MUTATION M4 detected (A3.packet.sha256, A8.receipts.cross)
MUTATION M5 detected (A3.packet.sha256, A8.receipts.cross)
MUTATION M6 detected (A3.packet.sha256)
VERDICT: OFFLINE_PASS — 16 checks, 0 failed, mutations 6/6
```

**Voice-over (exact, 86 words).**

> Third-party verification, without our repository. I unzip a 209-kilobyte packet
> and run the verifier inside it. Sixteen checks, zero failed, offline. Then six
> deliberate mutations: six detected. You do not have to trust the machine that
> produced the evidence. You run the check yourself. What I will not claim: this
> is N equals one. No superiority over a baseline is computed. One episode cannot
> support it. And the execute path has never run. What you are watching is a brake
> that works, measured. Not a yield.

**Direction.** Start on `/audit` for the "without our repository" sentence, cut to
terminal on "I unzip", back to `/audit` on "You run the check yourself" (the packet
panel and the sha256 stay on screen). The `N = 1` sentence is spoken to the
`NOT RUN` badge of "Offline packet verification" — say nothing about it, or say
"not run in this view, and that is written on the badge".

**Gate — read this before shooting.** From the repository,
`python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip`
prints **`VERDICT: OFFLINE_PASS — 16 checks, 0 failed`** (measured 2026-10-20T10:12Z),
and `--mutate-test` prints `mutations 6/6`. The packet was rebuilt on 2026-10-20 from a
fresh testnet session (`evidence/demo_runs/rseth_20261020/`, runs A→E, 10 receipts: 1
success + 9 chain refusals), so it is re-rendered by the current
`src/orvyren/audit/dossier.py` and both verifiers agree. The earlier 16/10 packet failed
`A4.dossier.rerender` for a renderer change and is archived out of the repository
(`SUPERSEDED_NOTE.md`). Two honest ways to shoot the block:

*Option A — rebuild the packet (4 s, recommended).* It produces a new zip with a new
sha256, so it is the owner's call:

```bash
cd D:/orvyren_core
python scripts/build_audit_packet.py --session evidence/demo_chain/rseth --case rseth --out-dir evidence/audit_packets
```

```text
ORVYREN — audit packet v2 assembled
  packet        : D:\orvyren_core\dist\audit_packets\audit_packet_rseth_20261020-1012_01M5CCNN (45 files)
  zip           : D:\orvyren_core\dist\audit_packets\audit_packet_rseth_20261020-1012_01M5CCNN.zip
  zip sha256    : 63f4cefd905047eca2f71b4fa0c99fb05fb4cdb38bcc661919583f0c7592b83f
  bundle_digest : dd8511cdb521c77447427008a2c6449e5c62fd1f42e5c12d7208b327be942748
  verification  : OFFLINE_PASS (16 checks), mutations 6/6
```

Measured into a scratch directory; the packet name embeds the assembly timestamp
(`…-0910…`), so **the file name, the sha256 and the bundle digest are per-build** —
read them from your own output, never copy them into a slide. With `--out-dir
evidence/audit_packets`, the two paths become `evidence/audit_packets/…`.

The repo verifier then passes on the new zip (measured: `VERDICT: OFFLINE_PASS —
16 checks, 0 failed`). Re-run it on camera if you choose this path.

*Option B — keep the shipped packet and verify it with its own frozen verifier*
(what §3.5 shows). It passes 16/0 because the verifier travels inside the packet,
built at the same instant as the evidence — which is precisely the third-party
property the block is about. Do not claim "our repository verifies our packet";
claim "the packet verifies itself, without our repository".

---

### 3.6 — Block 6 · 4:30–4:45 · closing line

**Screen.** Back to `/live`, URL `http://127.0.0.1:8321/live`, framing the two
panels (budget + ARRET-3). No command, no cursor movement.

**Voice-over (exact, 28 words).**

> Four cents for an agent run that abstains honestly, and one command to verify it
> offline. The rest is in the gaps register, including what we have not done.

**Direction.** Cut on the last word. No music sting, no logo animation — the video
ends on a number and a caveat, which is the project's voice.

---

## 4. Plan B — when something is down

**4.1 — The LLM provider is down (or has no key).** Trigger: you are about to run
the agents live and the provider errors. Do not improvise. Run the deterministic
replay instead:

```bash
cd D:/orvyren_core
python run_agents.py --case usdc-2023-03 --replay journal --session "$HOME/orvyren_video/replay"
```

**Measured output (today, 1.07 s):**

```text
ORVYREN — run_agents · usdc-2023-03 · mode journal
  run       : /c/Users/User/orvyren_video/replay\usdc-2023-03_journal_20261020T091417059882Z
  [orchestrator] process started…
    [orchestrator] done — 12 journal lines, state DONE/ARRET-1
  [critic] process started…
    [critic] report written — verdict FRAGILE, 1 objection(s)

  ==== run summary usdc-2023-03 (journal) ====
    orchestrator   12 lines — agent_id:orchestrator — chain OK
    critic          1 lines — agent_id:critic — chain OK
    stop           : ARRET-1 
    budget         : llm 5/30 · tools 2/12 · 0s/600s · $0.0018/$0.10
    critique       : FRAGILE
    escalation     : REQUIRE_APPROVAL (the critic never cancels — it brakes)
    not searched   : profondeur d'exécution réalisable non mesurée
    cumulative LLM cost: $0.0018
    artifacts      : /c/Users/User/orvyren_video/replay\usdc-2023-03_journal_20261020T091417059882Z
```

**The sentence that keeps it honest** (say it while it runs, word for word):

> "The provider is down, so I am running the deterministic replay of the USDC
> pilot: a different case, the same code path, one second, no network. The rsETH
> numbers on this screen come from the sealed run recorded on 18 October — I am not
> reading them onto this replay."

Note what this replay is **not**: it stops at `ARRET-1` with a `FRAGILE` critique,
2 tool calls and $0.0018 — not `ARRET-3`/`INCOHERENTE`/1 tool call/$0.035731. Never
say "same result". If the block is short on time, drop the replay and keep Block 3
on the recorded screen; the recorded screen needs no provider at all.

**4.2 — The API will not start.** Do not fake the dashboard. Fall back to the
stdlib dossier server, which reads the same evidence without FastAPI/uvicorn:

```bash
cd D:/orvyren_core
PYTHONPATH=src python run_audit.py --serve --port 8399
```

Measured: HTTP 200 on `http://127.0.0.1:8399/`, page title
`ORVYREN-Core Decision Dossier — case usdc-2023-03`. Say what changed: "the SPA is
not up; this is the static dossier, same evidence files".

**4.3 — A command fails on camera.** Stop the take. Do not narrate a failure into
a success. Reload, re-run, or move to the next block; a 40-second block is cheaper
than a false claim. The only failure the video is allowed to show is one you
explain, and the explanation is already written down (checklist item 8, gap G-12).

**4.4 — A block overruns.** Cut in this order: the optional health check (Block 1),
the mutation test (Block 5, saves 3 s), the `grep` insert (Block 3, saves 4 s).
Never cut the closing line, and never cut the `N = 1` sentence.

## 5. Assets to prepare before recording

| # | Asset | How | Used in |
|---|---|---|---|
| 1 | `01_live_budget.png` | `/live`, frame on Run budget, 1920×1080 | 1, 3, 6 |
| 2 | `02_live_outcome.png` | `/live`, frame on Agent outcome (ARRET-3, INCOHERENTE) | 1, 3 |
| 3 | `03_markets_headline.png` | `/markets`, the three cards + cash chart | 2 |
| 4 | `04_audit_packet.png` | `/audit`, "Verify without the repository" expanded | 5 |
| 5 | `05_executor_dryrun.txt` | stdout of §3.4, pasted verbatim | 4 |
| 6 | `06_verifier_pass.txt` | stdout of §3.5 (17 lines) | 5 |
| 7 | `07_mutation_6of6.txt` | 6 `MUTATION` lines + verdict | 5 |
| 8 | `08_subtitles.srt` | §6, imported and re-timed after the edit | all |
| 9 | `09_shotlist.csv` | this table | edit |

These are for the editor, not for the screen: the video shows the live app, never
a screenshot of the app.

## 6. Subtitles (SRT, English)

One line = one idea, 93 cues, timed to the block boundaries (last cue ends at
`00:04:45,000`). Import as SRT, then nudge to the recorded voice — the text must
not change, only the timings.

```text
1
00:00:00,000 --> 00:00:03,723
One claim: an agent that knows when to stop.

2
00:00:03,723 --> 00:00:07,232
This is ORVYREN, a bounded on-chain agent

3
00:00:07,232 --> 00:00:09,165
for DAO treasuries.

4
00:00:09,165 --> 00:00:12,100
It reads, it reasons, it refuses.

5
00:00:12,100 --> 00:00:15,823
Today the interesting result is not a trade.

6
00:00:15,823 --> 00:00:17,828
It is an abstention.

7
00:00:17,828 --> 00:00:20,334
The reason is written down.

8
00:00:20,334 --> 00:00:23,270
The budget spent is written down.

9
00:00:23,270 --> 00:00:26,134
And the packet verifies offline.

10
00:00:26,134 --> 00:00:30,000
Everything here runs on this machine, offline.

11
00:00:30,000 --> 00:00:34,041
April 18th, 2026. rsETH, Aave v3 core market.

12
00:00:34,041 --> 00:00:37,243
The oracle marked 2,526.76 dollars

13
00:00:37,243 --> 00:00:39,454
at the exploit block.

14
00:00:39,454 --> 00:00:41,817
2,513.66 at the freeze.

15
00:00:41,817 --> 00:00:45,324
The documented market price was 1,686.

16
00:00:45,324 --> 00:00:48,679
The oracle overstated the collateral

17
00:00:48,679 --> 00:00:50,584
by about a third.

18
00:00:50,584 --> 00:00:53,177
Just over an hour earlier,

19
00:00:53,177 --> 00:00:56,760
the supply cap had saturated: 99.999 %.

20
00:00:56,760 --> 00:00:59,809
529,993.98 out of 530,000 rsETH.

21
00:00:59,809 --> 00:01:03,698
Six tokens of room left. Not a closed door.

22
00:01:03,698 --> 00:01:06,366
Then the reserve was frozen

23
00:01:06,366 --> 00:01:08,501
at block 24,908,723.

24
00:01:08,501 --> 00:01:11,855
Utilisation at the freeze: 0.0079 %.

25
00:01:11,855 --> 00:01:14,752
So the liquidity-squeeze story

26
00:01:14,752 --> 00:01:17,344
is refuted by measurement.

27
00:01:17,344 --> 00:01:20,013
89,567 rsETH of collateral,

28
00:01:20,013 --> 00:01:22,224
190 million borrowed.

29
00:01:22,224 --> 00:01:25,197
The question is not prediction.

30
00:01:25,197 --> 00:01:27,408
It is: what do you do

31
00:01:27,408 --> 00:01:30,000
when the proof is missing?

32
00:01:30,000 --> 00:01:32,479
This is the recorded run.

33
00:01:32,479 --> 00:01:36,159
Every number comes from one outcome file,

34
00:01:36,159 --> 00:01:38,562
not from a re-enactment.

35
00:01:38,562 --> 00:01:41,341
Five LLM calls out of thirty.

36
00:01:41,341 --> 00:01:44,045
One tool call out of twelve.

37
00:01:44,045 --> 00:01:47,575
Thirty-four seconds out of six hundred.

38
00:01:47,575 --> 00:01:50,730
Three and a half cents out of ten.

39
00:01:50,730 --> 00:01:54,635
The run stopped itself: ARRET-3, abstention.

40
00:01:54,635 --> 00:01:58,090
The critic runs in a separate process.

41
00:01:58,090 --> 00:02:00,494
It returned INCOHERENTE.

42
00:02:00,494 --> 00:02:03,348
It does not decide. It brakes.

43
00:02:03,348 --> 00:02:06,652
And it forces escalation to a human.

44
00:02:06,652 --> 00:02:09,957
Why it stopped: the plan was refused

45
00:02:09,957 --> 00:02:13,262
because the discriminating criterion

46
00:02:13,262 --> 00:02:15,215
contained a digit.

47
00:02:15,215 --> 00:02:18,745
That is a schema rule, not a judgement.

48
00:02:18,745 --> 00:02:22,049
The hypothesis that should have won,

49
00:02:22,049 --> 00:02:25,054
a liquidity squeeze, was refuted

50
00:02:25,054 --> 00:02:28,058
by the utilisation you just saw.

51
00:02:28,058 --> 00:02:31,888
The plan also lists what it did not search:

52
00:02:31,888 --> 00:02:35,944
oracle freshness, the per-account debt ledger,

53
00:02:35,944 --> 00:02:39,1000
and the realisable value of frozen collateral.

54
00:02:40,000 --> 00:02:42,908
Now the chain, in one command.

55
00:02:42,908 --> 00:02:46,429
The agents run feeds a DecisionRecord.

56
00:02:46,429 --> 00:02:50,102
The record feeds a fourteen-rule policy,

57
00:02:50,102 --> 00:02:53,393
written in YAML, outside the model.

58
00:02:53,393 --> 00:02:56,301
The policy feeds the executor.

59
00:02:56,301 --> 00:02:57,985
Verdict: DENY.

60
00:02:57,985 --> 00:03:01,429
Not because the state was unreadable.

61
00:03:01,429 --> 00:03:04,031
Because the DecisionRecord

62
00:03:04,031 --> 00:03:06,862
carries no executable intent.

63
00:03:06,862 --> 00:03:09,1000
An abstention produces no action,

64
00:03:09,1000 --> 00:03:11,837
by construction.

65
00:03:11,837 --> 00:03:14,286
Zero signed. Zero spent.

66
00:03:14,286 --> 00:03:16,964
The journal chain verifies.

67
00:03:16,964 --> 00:03:20,561
The model proposes. The system decides.

68
00:03:20,561 --> 00:03:24,311
The key never enters the model's process.

69
00:03:24,311 --> 00:03:26,913
This path is dry-run only.

70
00:03:26,913 --> 00:03:29,515
The execute branch exists.

71
00:03:29,515 --> 00:03:32,500
It is preflighted on every run.

72
00:03:32,500 --> 00:03:35,791
This system has never exercised it.

73
00:03:35,791 --> 00:03:40,000
I will not show you a signature I did not make.

74
00:03:40,000 --> 00:03:44,619
Third-party verification, without our repository.

75
00:03:44,619 --> 00:03:47,618
I unzip a 209-kilobyte packet

76
00:03:47,618 --> 00:03:50,778
and run the verifier inside it.

77
00:03:50,778 --> 00:03:54,425
Sixteen checks, zero failed, offline.

78
00:03:54,425 --> 00:03:58,639
Then six deliberate mutations: six detected.

79
00:03:58,639 --> 00:04:02,204
You do not have to trust the machine

80
00:04:02,204 --> 00:04:05,041
that produced the evidence.

81
00:04:05,041 --> 00:04:07,877
You run the check yourself.

82
00:04:07,877 --> 00:04:10,308
What I will not claim:

83
00:04:10,308 --> 00:04:12,658
this is N equals one.

84
00:04:12,658 --> 00:04:16,791
No superiority over a baseline is computed.

85
00:04:16,791 --> 00:04:19,870
One episode cannot support it.

86
00:04:19,870 --> 00:04:23,355
And the execute path has never run.

87
00:04:23,355 --> 00:04:27,569
What you are watching is a brake that works,

88
00:04:27,569 --> 00:04:30,000
measured. Not a yield.

89
00:04:30,000 --> 00:04:32,793
Four cents for an agent run

90
00:04:32,793 --> 00:04:35,266
that abstains honestly.

91
00:04:35,266 --> 00:04:38,537
One command to verify it offline.

92
00:04:38,537 --> 00:04:41,809
The rest is in the gaps register,

93
00:04:41,809 --> 00:04:45,000
including what we have not done.

```

## 7. What it is forbidden to show

1. **`--execute` presented as exercised.** The real signing path is preflighted and
   **never run by this system** (gap G-12; the 16/10 T2 transactions were signed by
   a human key). Saying "and now it executes" over a dry-run is a lie the packet
   would contradict.
2. **The 16,174-node graph presented as what the agents reasoned on.** The agents
   scenario reasoned on `evidence/graph.sqlite` — 520 observations, schema v2
   (gap G-14). The 16k base is a local artifact outside the repository. You may
   show `/graph` as an asset; you may not say "the agents used this".
3. **Any number not measured in the shot.** No "−31 %" as arithmetic (measured:
   −33.27 % / −32.93 %), no "97 % accuracy", no "N > 1", no "superiority", no
   "production-ready". The only performance claim permitted is the one measured:
   a brake that works, on one episode.
4. **Presenting the wrong packet as passing.** The reference packet
   (`audit_packet_rseth_20261020-1012_01M5CCNN.zip`) prints `OFFLINE_PASS — 16 checks,
   0 failed` from the repository (measured 2026-10-20T10:12Z) **and** from its own
   embedded verifier. If you show any other zip, say which verifier you ran.
5. **A recorded run passed off as live.** The `/live` chip must stay visible:
   "Recorded agent run · single source: run outcome".
6. **The 13 demo transactions presented as this run's.** They belong to the 16/10
   pilot chain in `evidence/demo_chain/rseth/`; the rsETH agents run produced an
   abstention, not a transaction.
7. **A cut that removes the DENY.** If the executor says `DENY / NO_ACTION`, that
   is the result. Do not re-run with `--demo-defaults` to obtain an `ALLOW` and cut
   it in: it is a different scenario, and the journal would not match the voice.
8. **A failure narrated into a success.** If the verifier fails, the packet fails,
   or the API is down, say it (§4).
9. **The French internal journals "translated" on screen.** They are French by
   design; subtitles translate the voice, not the product's evidence.
10. **"The system is complete."** It is an operational DAO-treasury prototype with
    a declared gaps register; the video's last sentence points at it.

## 8. Verification log (measured 2026-10-20, 09:05–09:15 UTC)

`$RUN` below is `evidence/demo_runs/agents/rseth-2026-04/rseth-2026-04_live_20261018T200027592497Z`.

| # | Command | Result | Where |
|---|---|---|---|
| 1 | `curl -s 127.0.0.1:8321/api/health` | `status ok`, `mode offline-demo`, `frontend_built true` | §2.1 |
| 2 | `sed -n '10,22p' fixtures/agents/rseth-2026-04/run_inputs.json` | 13 lines, cap 0.9999886, block 24 908 723, market 1 686 | §3.2 |
| 3 | `grep -E '"(stop_condition\|verdict_lecture)"' $RUN/run_outcome.json` | `ARRET-3`, `INCOHERENTE` | §3.3 |
| 4 | `grep -A5 '"budget_used"' $RUN/run_outcome.json` | 5.0 calls, 1.0 tool, 34.422 s, 0.035731098 USD | §3.3 |
| 5 | `python run_executor.py --case rseth-2026-04 --decision-source agents --agents-run $RUN --dry-run` | `DENY / NO_ACTION`, `0 signed`, chain VALID, 0.42–0.67 s | §3.4 |
| 6 | `python verify/orvyren_verify.py .` (in the extracted packet) | `OFFLINE_PASS — 16 checks, 0 failed`, 0.50 s | §3.5 |
| 7 | `python verify/orvyren_verify.py . --mutate-test` | `6/6` detected, `OFFLINE_PASS`, 2.6 s | §3.5 |
| 8 | `python run_agents.py --case usdc-2023-03 --replay journal` | `ARRET-1`, `FRAGILE`, 5/30, 2/12, $0.0018, 1.07 s | §4.1 |
| 9 | `python scripts/build_audit_packet.py --session evidence/demo_chain/rseth --case rseth --out-dir <scratch>` | 45 files, `OFFLINE_PASS (16 checks), mutations 6/6`, 3.9 s | §3.5 |
| 10 | `python run_verify.py <rebuilt zip>` | `OFFLINE_PASS — 16 checks, 0 failed` | §3.5 |
| 11 | `python run_verify.py evidence/audit_packets/audit_packet_rseth_20261020-1012_01M5CCNN.zip` | `OFFLINE_PASS — 16 checks, 0 failed` (2026-10-20T10:12Z; same as the in-packet verifier) | §3.5 |
| 12 | `python run_agents.py --case rseth-2026-04 --replay journal` | **not replayable**: `E_LLM_NOT_RECORDED` on the critic call (no recorded store for this case) — see `run_inputs.json` note | §4.1 |
| 13 | `PYTHONPATH=src python run_audit.py --serve --port 8399` | HTTP 200, dossier page | §4.2 |
| 14 | `python scripts/run_scenario_rseth.py --agents-run $RUN` (one-command chain) | `DecisionRecord … INCONCLUSIVE · REQUIRE_APPROVAL (intent null)` / `abstention ESCALATE — action null (5 what_would_change entries)` / `verification PASS`, 1.6 s | §3.4 (alternative) |

**Corrections to `docs/DEMO_SCRIPT_10MIN.md` that this kit applies:**

1. The policy DENY is `NO_ACTIONABLE_INTENT`, not `BALANCE_UNREADABLE` /
   `AGENT_NOT_MEMBER` (§3.4).
2. The run's `what_would_change` is **empty**; the five leads come from the A1–A5
   abstention complement (§3.3).
3. `−31 %` is a documented figure that does not match the arithmetic the run
   itself cites; the video says "about a third" (§3.2).
4. The audit gate is not green on the shipped packet; the video uses the in-packet
   verifier or a rebuilt packet, never `run_verify.py` on the 16/10 zip (§3.5).
5. The rsETH agents case has **no** offline replay (`E_LLM_NOT_RECORDED`); Plan B
   is the USDC pilot replay, and it is labelled as such (§4.1).

## 9. What remains to the owner

- **Voice.** Record from §3 (the exact text) — 517 words, ~4:00 of speech in 4:45.
- **Capture.** Six takes (§3.1–§3.6), 1920×1080, 60 fps, per §2.
- **Edit.** Cut on the block boundaries; keep the `grep`/`sed` cuts short (2–4 s);
  do not add zooms on numbers that are already legible at 100 %.
- **Subtitles.** Import §6, re-time to the voice, keep the text verbatim.
- **Decision required:** rebuild the audit packet (Option A, §3.5) or shoot with
  the in-packet verifier (Option B). Option A changes a published sha256 and adds
  a file to `evidence/audit_packets/` — it is a repository change, not a video
  change.
- **Upload check:** the file must read **≤ 5:00**; this cut is 4:45, so the margin
  absorbs a title card if the platform adds one.

*Everything measured above is reproducible from this working tree with the commands
shown. Where a command does not reproduce, this file says why instead of proposing
a workaround.*
