# ORVYREN — Frontend art direction (2026-10-19)

Scope: replace the current single dense dashboard with a **set of pages** that
share a common shell. Two design languages are combined on purpose:
**skeuomorphism for meaning**, **minimalism for reading**.

---

## 1. What the research actually says

| Source | Point retained |
|---|---|
| NN/g, *Characteristics of Minimalism in Web Design* (112 sites analysed) | Minimalism = flat surfaces, limited palette, **few elements**, negative space, dramatic typography. Not emptiness: hierarchy carried by type and space. |
| designmd.app, *Skeuomorphism* | "Texture must carry meaning… **remove the texture and see if the interface loses meaning**. If nothing changes, you are decorating." Also: one light source, depth serves hierarchy, **restraint — one or two skeuomorphic elements surrounded by clean space**. |
| IxDF, *Top 10 UI Trends* | Neumorphism = the flat/skeuomorphic hybrid; its weakness is contrast — extruded controls must stay unmistakably interactive. |
| daisyUI, *UI trends 2026* | Skeuomorphism returns as **material languages** (paper/ink/seal, chrome, wood) used to explain hierarchy or give a product a setting. |
| Medium, *From Realism to Minimalism* | Skeuomorphism helps **unfamiliar, high-stakes** interfaces (recognition over recall); flat/minimal wins for **speed and expert scanning**. A risk console needs both, on different surfaces. |

**Conclusion for ORVYREN.** The product's whole claim is *provable, sealed, recomputable*. That is a physical idea: a **ledger**, a **seal**, an **instrument**. So skeuomorphism earns its place only where it says something true:

| Skeuomorphic device | What it means here | Where it may appear |
|---|---|---|
| Embossed **seal / stamp** | a hash-signed, immutable artefact | G6 sheet, audit packet, frozen package |
| **Ledger paper** with ruled lines | append-only journal, one line = one fact | run journal, receipts, decision record |
| **Gauge with a needle** | a bounded budget consumed (LLM calls, tools, seconds, USD) | agent run header |
| **Inset plate / bezel** | a lock: policy envelope, preflight gate, kill switch | policy & execution pages |
| **Sealed envelope** | the audit packet the jury can open without us | audit page |

Everything else is minimal: no texture on tables, charts, forms, navigation.

**Hard limits (both languages).**
- One light source, top-left; shadows are short and directional, never glows.
- No gradient on text, no glassmorphism, no emoji, no icon soup.
- Off-black `#14161a` on paper `#f7f5f1`; a single accent **copper** `#b4622d` for "action/attention", a single semantic red `#a8322a` for DENY only.
- Typography does the hierarchy: one serif for the "record" voice (headings, sealed artefacts), one grotesque for data and UI. Numerals always tabular.
- Contrast: every extruded control keeps ≥ 4.5:1; neumorphic softness never at the cost of a visible boundary.

---

## 2. The complaint being fixed

> "The page is too vibecoded, everything is crammed — and the graph is
> unreadable, it shows too much irrelevant information."

Two causes, two rules:

1. **One page carried five jobs** (live runs, graph, markets, decision, audit).
   → **Split into routes**, each with one question to answer, one primary action.
2. **The graph rendered everything at once** (16 174 nodes).
   → **Progressive disclosure**: the graph never shows the world, it shows an
   *answer to a question*, with the path that justifies it.

### Graph legibility rules (non-negotiable)

1. **Never render the full graph.** Entry states are queries: "exposure of
   holder X", "path A → B", "state at block N", "permissions of Y". The canvas
   draws the returned subgraph only.
2. **Depth 2 by default**, with an explicit `+1 hop` control; the count of hidden
   neighbours is always displayed (`+ 1 214 not shown`).
3. **One label kind at a time**: node label, relation label, or value — chosen by
   toggle, never all three.
4. **Aggregation first**: 2 000 `DEPOSITED_IN` edges from one protocol collapse
   into one node with a badge (`2 000 relations`), expandable on click.
5. **Selection is a conversation**: clicking a node opens a side rail with *why
   it is here* (the query, the relation, the provenance refs) — not a modal.
6. **Stable layout**: same query = same layout (seeded), so a re-run is
   comparable; layout animation only on expand/collapse.
7. **Legend is a filter**: hidden families go grey and are removed from the
   counts, never silently.

---

## 3. The pages (shared shell, one accent)

| Route | One question | Primary action | Density |
|---|---|---|---|
| **Overview** | *What is the state of the system right now?* | open the latest run | low — 4 KPI + 1 list |
| **Live runs** | *What are the agents doing, within which bounds?* | replay / open journal | medium |
| **Graph** | *What is this exposure, and what justifies it?* | change the question (query bar) | high, but only the subgraph |
| **Decision** | *Why this action — or this abstention?* | read `what_would_change` | medium |
| **Execution & policy** | *What was authorised, and what was refused?* | inspect a refusal | high (tables) |
| **Audit** | *Can I verify it without you?* | run the verifier | low |
| **Markets & episodes** | *What happened, measured?* | open an episode | medium |
| **Limits** | *What does this system not do?* | read the register | low |

Shell: fixed left rail (icons + labels, 64→220 px on hover), top bar carrying
**mode** (`LIVE` / `REPLAY` / `FIXTURE`) and the **clock**, which are mandatory
banners today and must stay permanent, non-dismissible.

---

## 4. Component grammar

- **Record card** (skeuomorphic restraint): paper surface, ruled header line,
  serif title, monospace digest at the bottom — used *only* for sealed
  artefacts (decision record, packet, frozen doc). Max one per screen.
- **Gauge**: budget consumed, drawn as an arc with a needle; the numeric value
  is always printed next to it (never gauge-only).
- **Table**: hairline rules, no zebra, tabular numerals, right-aligned figures;
  refusals carry a small red left border, not a red fill.
- **Chip**: only for states (`ALLOW` `DENY` `REQUIRE_APPROVAL` `NO_ACTION`),
  never for decoration.
- **Empty / absent source**: a deliberate, quiet panel — the product must never
  look broken when a source is missing; it must look *honest*.

---

## 5. Three directions to sketch (dispatched in parallel)

| Variant | Stance | Skeuomorphic device | Risk |
|---|---|---|---|
| **A. Instrument panel** | minimal base, mechanical gauges, engraved labels | gauge + inset plate | can look like a cockpit if overdone |
| **B. Sealed ledger** | editorial, paper, typographic, dense tables | stamp/seal + ruled paper | can read as a report, less "live" |
| **C. Quiet console** | dark, near-neumorphic, very low chrome | soft emboss on controls only | contrast trap (the classic neumorphism failure) |

Each variant is a standalone HTML file covering **two screens**: *Overview* and
*Graph* (same data, different disclosure), verified in a real browser before
being shown.

The winner is then rebuilt as the real SPA (`frontend/`, React + Vite + Tailwind),
page by page, without changing a single API contract.
