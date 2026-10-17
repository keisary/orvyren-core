"""ORVYREN-Core audit dossier builder (Python standard library only).

Builds the one-page decision dossier from the engine's machine-readable
artefacts:

* ``decision_<case>.json`` -- primary input: case/window, inputs summary,
  hypothesis verdicts (H1/H2/H3), decision block (verdict, action, rationale,
  conditions, limits, provenance) and calibration;
* optional extras: ``baseline_report.json`` (A0 baseline comparison),
  ``policy_execution_demo.json``, ``quality_report.json``.

Guarantees
----------
* Deterministic: identical inputs and an identical ``generated_at`` value
  produce byte-identical Markdown and HTML output.
* Verifiable: every input file actually read is listed with its SHA-256, and
  the dossier itself carries a reproducible self-hash (SHA-256 over the file
  with the 64-character self-hash field zeroed to 64 ``0`` characters).
* Honest: absent, unreadable or invalid inputs are reported verbatim
  (``Missing input: <path>``) and never invented on their behalf.

The HTML rendering is fully self-contained: inline CSS, no scripts, no
external resources of any kind.
"""

import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone

ENGINE_NAME = "ORVYREN-Core"
ENGINE_VERSION = "0.1"
PRODUCED_CLAUSE = "produced by ORVYREN-Core v0.1 — deterministic engine, no human edit"
MISSING = "(not provided in source JSON)"
SELF_HASH_ZERO = "0" * 64

# Bounded previews keep the dossier readable ("one page"); the exact counts are
# always reported and the complete lists stay in the hashed source JSON.
REFS_PREVIEW = 4
PROVENANCE_PREVIEW = 8
BASELINE_SIGNALS_PREVIEW = 6

# Accepted aliases for the optional inputs, normalised to canonical labels.
_EXTRA_ALIASES = {
    "baseline": "baseline_report",
    "policy": "policy_execution_demo",
    "policy_execution": "policy_execution_demo",
    "quality": "quality_report",
}

# Regexes used to read back the metadata the server exposes over HTTP.
_META_PATTERNS = {
    "case": re.compile(r"^\| Case \| (.*?) \|$", re.MULTILINE),
    "generated_at": re.compile(r"^\| Generated \(UTC\) \| (.*?) \|$", re.MULTILINE),
    "verdict": re.compile(r"^- \*\*Verdict:\*\* (.*)$", re.MULTILINE),
}

# Inline stylesheet for the standalone HTML rendering (no external assets).
_CSS = """
:root{--ink:#16181d;--muted:#5b6470;--line:#d8dde3;--soft:#f5f7f9;--ok:#0a7d3a;--warn:#9a6b00;--neutral:#5b6470;--alert:#b3261e}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 40px;background:#fff;color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,-apple-system,Arial,sans-serif}
main{max-width:960px;margin:0 auto}
h1{font-size:21px;margin:0 0 4px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:24px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:14px;margin:14px 0 4px}
p{margin:4px 0}
.produced{color:var(--muted);font-size:12.5px;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:14px;margin:6px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:600}
code,.mono{font-family:Consolas,Menlo,monospace;font-size:12.5px;word-break:break-all}
.badge{display:inline-block;padding:3px 10px;border-radius:3px;font-weight:600;font-size:14px}
.badge.ok{background:#e6f4ea;color:var(--ok);border:1px solid #bfe3c9}
.badge.warn{background:#fdf3dd;color:var(--warn);border:1px solid #f0dcae}
.badge.neutral{background:#eef1f4;color:var(--neutral);border:1px solid var(--line)}
.missing{border-left:4px solid var(--alert);background:#fdf0ef;padding:8px 12px;margin:10px 0}
.note{color:var(--muted);font-size:12.5px}
ul{margin:4px 0 4px 20px;padding:0}
pre{background:var(--soft);border:1px solid var(--line);padding:8px;overflow:auto;font-size:12.5px;margin:6px 0}
.foot{margin-top:28px;padding-top:10px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
"""


# --------------------------------------------------------------------------- #
# Input handling
# --------------------------------------------------------------------------- #

# dossier.py -> audit -> orvyren -> src -> <repository root>
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _display_path(path):
    """Repo-relative POSIX path when the file lives inside the repository.

    Keeps dossiers portable: an absolute path (e.g. ``D:\\orvyren_core\\...``
    or a reviewer's home directory) must never leak into a hashed artefact,
    because it changes with the machine that built it. Paths outside the
    repository are reported unchanged so external fixtures stay identifiable.
    """
    text = str(path)
    try:
        relative = os.path.relpath(text, _REPO_ROOT).replace(os.sep, "/")
        if relative != ".." and not relative.startswith("../"):
            return relative
    except (OSError, ValueError):
        pass
    return text.replace(os.sep, "/")


def _normalized_bytes(path):
    """File bytes with CRLF collapsed to LF.

    Text digests must not depend on the platform's line endings: the recorded
    SHA-256 has to match the repository copy whether it was read on Windows
    (CRLF on disk) or on Linux/macOS (LF). ``.gitattributes`` enforces LF
    checkouts for text files; this function is the belt to that bra.
    """
    with open(path, "rb") as handle:
        raw = handle.read()
    return raw.replace(b"\r\n", b"\n")


def sha256_file(path):
    """Return the hex SHA-256 of a file, or None if unreadable.

    Text inputs are hashed over LF-normalised bytes (see ``_normalized_bytes``)
    so digests are platform-stable.
    """
    try:
        raw = _normalized_bytes(path)
    except OSError:
        return None
    return hashlib.sha256(raw).hexdigest()


def _canon_label(label):
    key = str(label).strip().lower()
    return _EXTRA_ALIASES.get(key, key)


def _read_input(label, path):
    """Read one input file. Never raises: problems are reported in the record."""
    record = {
        "label": label,
        "path": _display_path(path),
        "sha256": None,
        "status": "missing",
        "error": None,
        "data": None,
    }
    try:
        raw = _normalized_bytes(path)
    except FileNotFoundError:
        return record
    except OSError as exc:
        record["status"] = "unreadable"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        record["data"] = json.loads(raw.decode("utf-8"))
        record["status"] = "ok"
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        record["status"] = "invalid-json"
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def _iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(value):
    cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in str(value))
    cleaned = cleaned.strip("-.")
    return cleaned or "unknown"


def _case_id(decision_record, decision_path):
    data = decision_record.get("data")
    if isinstance(data, dict):
        case = data.get("case")
        if isinstance(case, str) and case.strip():
            return _safe_name(case.strip())
    stem = os.path.splitext(os.path.basename(str(decision_path)))[0]
    if stem.startswith("decision_"):
        stem = stem[len("decision_"):]
    return _safe_name(stem)


# --------------------------------------------------------------------------- #
# Value formatting shared by both renderers
# --------------------------------------------------------------------------- #

def _fmt_value(value):
    """Render any JSON-ish value as a compact, deterministic one-line string."""
    if value is None:
        return MISSING
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value if value.strip() else MISSING
    if isinstance(value, (list, tuple)):
        if not value:
            return "(empty list)"
        return "; ".join(_fmt_value(item) for item in value)
    if isinstance(value, set):
        if not value:
            return "(empty list)"
        return "; ".join(_fmt_value(item) for item in sorted(value, key=str))
    if isinstance(value, dict):
        if not value:
            return "(empty)"
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(", ", ": "))
    return str(value)


def _fmt_window(window):
    if isinstance(window, dict):
        start = window.get("start")
        end = window.get("end")
        if start or end:
            return f"{start if start is not None else MISSING} → {end if end is not None else MISSING}"
    return _fmt_value(window)


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, set):
        return sorted(value, key=str)
    return [value]


def _md_cell(value):
    """One-line, pipe-escaped cell for Markdown tables and bullets."""
    return _fmt_value(value).replace("|", "\\|").replace("\n", " ").strip()


def _h(value):
    """HTML-escaped rendering of any JSON-ish value."""
    return html.escape(_fmt_value(value), quote=True)


def _json_block(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _refs_summary(refs):
    """Return (count, display_text) for one hypothesis' evidence_refs.

    At most ``REFS_PREVIEW`` refs are displayed; the exact count is always
    reported and the complete list stays in the hashed decision JSON.
    """
    if refs is None:
        return 0, MISSING
    if isinstance(refs, (list, tuple, set)):
        items = [_fmt_value(item) for item in sorted(refs, key=str)]
        if not items:
            return 0, "(none listed)"
        if len(items) > REFS_PREVIEW:
            shown = "; ".join(items[:REFS_PREVIEW])
            return len(items), f"{shown}; … +{len(items) - REFS_PREVIEW} more (full list in the hashed decision JSON)"
        return len(items), "; ".join(items)
    return 1, _fmt_value(refs)


def _decision_fields(decision):
    """(label, raw_value) pairs describing the decision block."""
    data = decision if isinstance(decision, dict) else {}
    rows = [("Verdict", data.get("verdict"))]
    action = data.get("action")
    if isinstance(action, dict):
        amount = action.get("amount_usdc")
        asset = action.get("asset") or "USDC"
        rows.append(("Amount", f"{amount if amount is not None else MISSING} {asset}"))
        atype = action.get("type") or "action"
        source = action.get("from_wallet") or MISSING
        target = action.get("to_wallet") or MISSING
        rows.append(("Action", f"{atype} — from {source} to {target}"))
    elif action is None:
        rows.append(("Amount", "n/a — no action proposed"))
        rows.append(("Action", "none (no transfer proposed)"))
    else:
        rows.append(("Amount", "n/a"))
        rows.append(("Action", action))
    return rows


def _hypothesis_rows(hypotheses):
    """(key, verdict, ref_count, refs_text) rows, sorted for determinism."""
    if not isinstance(hypotheses, dict) or not hypotheses:
        return [("—", None, 0, MISSING)]
    rows = []
    for key in sorted(hypotheses.keys(), key=str):
        entry = hypotheses[key] if isinstance(hypotheses[key], dict) else {}
        count, shown = _refs_summary(entry.get("evidence_refs"))
        rows.append((str(key), entry.get("verdict"), count, shown))
    return rows


def _baseline_view(record):
    """Normalise the baseline report into display fields."""
    if record is None:
        return {"available": False, "note": "baseline report was not supplied to the builder."}
    if record["status"] != "ok":
        return {"available": False, "note": f"{record['path']} — {record['status']}"}
    data = record["data"] if isinstance(record["data"], dict) else {}
    return {
        "available": True,
        "rule": data.get("rule"),
        "main": [_fmt_value(item) for item in _as_list(data.get("signals_main"))],
        "control": [_fmt_value(item) for item in _as_list(data.get("signals_control"))],
        "false_signals": data.get("false_signals_control"),
    }


def _problem_inputs(ctx):
    return [r for r in ([ctx["decision_rec"]] + ctx["extras"]) if r["status"] != "ok"]


def _input_rows(ctx):
    """Evidence-table rows for every declared input file."""
    rows = []
    for record in [ctx["decision_rec"]] + ctx["extras"]:
        if record["sha256"]:
            status_text = record["status"]
        elif record["error"]:
            status_text = f"{record['status']}: {record['error']}"
        else:
            status_text = "missing (file not read)"
        rows.append({
            "kind": record["label"],
            "path": record["path"],
            "sha": record["sha256"],
            "status_text": status_text,
        })
    return rows


def _other_extras(ctx):
    """Extras rendered as generic JSON sections (everything except baseline)."""
    return [r for r in ctx["extras"] if r["label"] != "baseline_report"]


def _extra_title(label):
    return str(label).replace("_", " ").replace("-", " ").capitalize()


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #

def render_markdown(ctx):
    """Render the dossier as Markdown; the self-hash field still holds the
    zeroed token, substituted by :func:`build` before the file is written."""
    case = ctx["case"]
    lines = []
    add = lines.append

    add(f"# {ENGINE_NAME} Decision Dossier — case {case}")
    add("")
    add(f"> {PRODUCED_CLAUSE}")
    add("")

    add("| Field | Value |")
    add("| --- | --- |")
    add(f"| Case | {_md_cell(case)} |")
    add(f"| Window | {_md_cell(_fmt_window(ctx['window']))} |")
    add(f"| Generated (UTC) | {_md_cell(ctx['generated_at'])} |")
    add(f"| Engine | {ENGINE_NAME} {ENGINE_VERSION} |")
    add("")

    problems = _problem_inputs(ctx)
    if problems:
        add("## Missing inputs")
        add("")
        for record in problems:
            if record["status"] == "missing":
                add(f"- Missing input: {record['path']}")
            else:
                add(f"- {record['status']} input: {record['path']} ({record['error']})")
        add("")

    add("## Decision")
    add("")
    if isinstance(ctx["decision"], dict) and ctx["decision"]:
        for label, value in _decision_fields(ctx["decision"]):
            add(f"- **{label}:** {_md_cell(value)}")
    else:
        add(f"- **Verdict:** {MISSING}")
        add("- Decision data unavailable or empty in the source input; nothing is inferred.")
    add("")

    decision = ctx["decision"] if isinstance(ctx["decision"], dict) else {}
    for section, key in (("Rationale", "rationale"), ("Conditions", "conditions"), ("Provenance", "provenance")):
        add(f"### {section}")
        add("")
        items = _as_list(decision.get(key))
        preview = PROVENANCE_PREVIEW if key == "provenance" else None
        shown = items[:preview] if (preview and len(items) > preview) else items
        if shown:
            for item in shown:
                add(f"- {_md_cell(item)}")
        else:
            add(f"- {MISSING}")
        if preview and len(items) > len(shown):
            add(f"- … +{len(items) - len(shown)} more entries (complete list in the source decision JSON, hashed in Evidence & integrity)")
        add("")

    add("## Hypothesis verdicts")
    add("")
    add("| Hypothesis | Verdict | Evidence refs |")
    add("| --- | --- | --- |")
    for key, verdict, count, refs_text in _hypothesis_rows(ctx["hypotheses"]):
        add(f"| {_md_cell(key)} | {_md_cell(verdict)} | {count} — {_md_cell(refs_text)} |")
    add("")

    add("## Baseline A0 — main window vs control")
    add("")
    view = _baseline_view(ctx["baseline"])
    if not view["available"]:
        add(f"- Baseline comparison unavailable: {_md_cell(view['note'])}")
    else:
        add(f"- **Rule:** {_md_cell(view['rule'])}")
        add("")
        add("| Metric | Main window | Control |")
        add("| --- | --- | --- |")
        add(f"| Signals | {len(view['main'])} | {len(view['control'])} |")
        add(f"| False signals | — | {_md_cell(view['false_signals'])} |")
        add("")
        for title, signals in (("Main window signals", view["main"]), ("Control signals", view["control"])):
            add(f"{title} ({len(signals)}):")
            if signals:
                shown = signals[:BASELINE_SIGNALS_PREVIEW] if len(signals) > BASELINE_SIGNALS_PREVIEW else signals
                for signal in shown:
                    add(f"- {_md_cell(signal)}")
                if len(signals) > len(shown):
                    add(f"- … +{len(signals) - len(shown)} more (full list in the hashed baseline report)")
            else:
                add("- none listed")
            add("")
    add("")

    if ctx["inputs_summary"] is not None:
        add("## Inputs summary")
        add("")
        summary = ctx["inputs_summary"]
        if isinstance(summary, dict) and summary:
            add("| Key | Value |")
            add("| --- | --- |")
            for key in sorted(summary.keys(), key=str):
                add(f"| {_md_cell(key)} | {_md_cell(summary[key])} |")
        else:
            add(f"- {_md_cell(summary)}")
        add("")

    if ctx["calibration"] is not None:
        add("## Calibration")
        add("")
        add(f"- {_md_cell(ctx['calibration'])}")
        add("")

    for record in _other_extras(ctx):
        add(f"## {_extra_title(record['label'])}")
        add("")
        if record["status"] == "ok":
            add("```json")
            add(_json_block(record["data"]))
            add("```")
        else:
            add(f"- Input not available (status: {record['status']}).")
        add("")

    add("## Limits & uncertainties")
    add("")
    limits = _as_list(decision.get("limits"))
    if limits:
        for item in limits:
            add(f"- {_md_cell(item)}")
    else:
        add(f"- {MISSING}")
    add("")

    add("## Evidence & integrity")
    add("")
    add("| Input | Path | SHA-256 |")
    add("| --- | --- | --- |")
    for row in _input_rows(ctx):
        sha = f"`{row['sha']}`" if row["sha"] else row["status_text"]
        add(f"| {_md_cell(row['kind'])} | {_md_cell(row['path'])} | {sha} |")
    add(f"| dossier (self, md) | {_md_cell(ctx['md_path_display'])} | `{SELF_HASH_ZERO}` |")
    add("")
    add(
        "Self-hash rule: the `dossier (self, md)` row is the SHA-256 of this Markdown file "
        "computed with its own 64-hex-character self-hash field zeroed (64 `0` characters). "
        "It is reproducible with any SHA-256 tool: replace that field with zeros and hash the file. "
        "With identical inputs and build time this dossier is byte-identical."
    )
    add("")
    add("---")
    add("")
    add(f"{PRODUCED_CLAUSE} · {ENGINE_NAME} v{ENGINE_VERSION} · generated {ctx['generated_at']} (UTC)")
    add("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# HTML rendering (self-contained)
# --------------------------------------------------------------------------- #

def _verdict_class(verdict):
    value = (_fmt_value(verdict) or "").upper()
    if value == "ACTION_RECOMMENDED":
        return "ok"
    if value == "INCONCLUSIVE":
        return "warn"
    return "neutral"


def render_html(ctx):
    """Render the dossier as standalone HTML; the self-hash field still holds
    the zeroed token, substituted by :func:`build` before the file is written."""
    case = ctx["case"]
    parts = []
    add = parts.append

    add("<!DOCTYPE html>")
    add('<html lang="en">')
    add("<head>")
    add('<meta charset="utf-8">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add(f"<title>{_h(ENGINE_NAME)} Decision Dossier — case {_h(case)}</title>")
    add("<style>")
    add(_CSS.strip())
    add("</style>")
    add("</head>")
    add("<body>")
    add("<main>")

    add("<header>")
    add(f"<h1>{_h(ENGINE_NAME)} Decision Dossier</h1>")
    add(f'<p class="produced">{_h(PRODUCED_CLAUSE)}</p>')
    add("</header>")

    add('<table class="kv">')
    add("<thead><tr><th>Field</th><th>Value</th></tr></thead>")
    add("<tbody>")
    add(f"<tr><td>Case</td><td>{_h(case)}</td></tr>")
    add(f"<tr><td>Window</td><td>{_h(_fmt_window(ctx['window']))}</td></tr>")
    add(f"<tr><td>Generated (UTC)</td><td>{_h(ctx['generated_at'])}</td></tr>")
    add(f"<tr><td>Engine</td><td>{_h(ENGINE_NAME)} {_h(ENGINE_VERSION)}</td></tr>")
    add("</tbody>")
    add("</table>")

    problems = _problem_inputs(ctx)
    if problems:
        add('<section class="missing">')
        add("<h2>Missing inputs</h2>")
        add("<ul>")
        for record in problems:
            if record["status"] == "missing":
                add(f"<li>Missing input: <code>{html.escape(record['path'])}</code></li>")
            else:
                add(
                    f"<li>{html.escape(record['status'])} input: "
                    f"<code>{html.escape(record['path'])}</code> ({html.escape(str(record['error']))})</li>"
                )
        add("</ul>")
        add("</section>")

    add("<section>")
    add("<h2>Decision</h2>")
    if isinstance(ctx["decision"], dict) and ctx["decision"]:
        add("<ul>")
        for label, value in _decision_fields(ctx["decision"]):
            if label == "Verdict":
                add(f'<li><strong>{_h(label)}:</strong> <span class="badge {_verdict_class(value)}">{_h(value)}</span></li>')
            else:
                add(f"<li><strong>{_h(label)}:</strong> {_h(value)}</li>")
        add("</ul>")
    else:
        add(f"<p><strong>Verdict:</strong> {_h(None)}</p>")
        add("<p>Decision data unavailable or empty in the source input; nothing is inferred.</p>")

    decision = ctx["decision"] if isinstance(ctx["decision"], dict) else {}
    for section, key in (("Rationale", "rationale"), ("Conditions", "conditions"), ("Provenance", "provenance")):
        add(f"<h3>{section}</h3>")
        items = _as_list(decision.get(key))
        preview = PROVENANCE_PREVIEW if key == "provenance" else None
        shown = items[:preview] if (preview and len(items) > preview) else items
        if shown:
            add("<ul>")
            for item in shown:
                add(f"<li>{_h(item)}</li>")
            if preview and len(items) > len(shown):
                add(
                    f'<li class="note">… +{len(items) - len(shown)} more entries '
                    "(complete list in the source decision JSON, hashed in Evidence &amp; integrity)</li>"
                )
            add("</ul>")
        else:
            add(f"<p>{_h(None)}</p>")
    add("</section>")

    add("<section>")
    add("<h2>Hypothesis verdicts</h2>")
    add("<table>")
    add("<thead><tr><th>Hypothesis</th><th>Verdict</th><th>Evidence refs</th></tr></thead>")
    add("<tbody>")
    for key, verdict, count, refs_text in _hypothesis_rows(ctx["hypotheses"]):
        add(f"<tr><td>{_h(key)}</td><td>{_h(verdict)}</td><td>{count} — {_h(refs_text)}</td></tr>")
    add("</tbody>")
    add("</table>")
    add("</section>")

    add("<section>")
    add("<h2>Baseline A0 — main window vs control</h2>")
    view = _baseline_view(ctx["baseline"])
    if not view["available"]:
        add(f"<p>Baseline comparison unavailable: {_h(view['note'])}</p>")
    else:
        add(f"<p><strong>Rule:</strong> {_h(view['rule'])}</p>")
        add("<table>")
        add("<thead><tr><th>Metric</th><th>Main window</th><th>Control</th></tr></thead>")
        add("<tbody>")
        add(f"<tr><td>Signals</td><td>{len(view['main'])}</td><td>{len(view['control'])}</td></tr>")
        add(f"<tr><td>False signals</td><td>—</td><td>{_h(view['false_signals'])}</td></tr>")
        add("</tbody>")
        add("</table>")
        for title, signals in (("Main window signals", view["main"]), ("Control signals", view["control"])):
            add(f"<h3>{title} ({len(signals)})</h3>")
            if signals:
                shown = signals[:BASELINE_SIGNALS_PREVIEW] if len(signals) > BASELINE_SIGNALS_PREVIEW else signals
                add("<ul>")
                for signal in shown:
                    add(f"<li>{html.escape(signal)}</li>")
                if len(signals) > len(shown):
                    add(
                        f'<li class="note">… +{len(signals) - len(shown)} more '
                        "(full list in the hashed baseline report)</li>"
                    )
                add("</ul>")
            else:
                add('<p class="note">none listed</p>')
    add("</section>")

    if ctx["inputs_summary"] is not None:
        add("<section>")
        add("<h2>Inputs summary</h2>")
        summary = ctx["inputs_summary"]
        if isinstance(summary, dict) and summary:
            add("<table>")
            add("<thead><tr><th>Key</th><th>Value</th></tr></thead>")
            add("<tbody>")
            for key in sorted(summary.keys(), key=str):
                add(f"<tr><td>{html.escape(str(key))}</td><td>{_h(summary[key])}</td></tr>")
            add("</tbody>")
            add("</table>")
        else:
            add(f"<p>{_h(summary)}</p>")
        add("</section>")

    if ctx["calibration"] is not None:
        add("<section>")
        add("<h2>Calibration</h2>")
        add(f"<p>{_h(ctx['calibration'])}</p>")
        add("</section>")

    for record in _other_extras(ctx):
        add("<section>")
        add(f"<h2>{_h(_extra_title(record['label']))}</h2>")
        if record["status"] == "ok":
            add(f"<pre>{html.escape(_json_block(record['data']))}</pre>")
        else:
            add(f"<p>Input not available (status: {html.escape(str(record['status']))}).</p>")
        add("</section>")

    add("<section>")
    add("<h2>Limits &amp; uncertainties</h2>")
    limits = _as_list(decision.get("limits"))
    if limits:
        add("<ul>")
        for item in limits:
            add(f"<li>{_h(item)}</li>")
        add("</ul>")
    else:
        add(f"<p>{_h(None)}</p>")
    add("</section>")

    add("<section>")
    add("<h2>Evidence &amp; integrity</h2>")
    add("<table>")
    add("<thead><tr><th>Input</th><th>Path</th><th>SHA-256</th></tr></thead>")
    add("<tbody>")
    for row in _input_rows(ctx):
        sha = f"<code>{html.escape(row['sha'])}</code>" if row["sha"] else html.escape(row["status_text"])
        add(f"<tr><td>{_h(row['kind'])}</td><td><code>{html.escape(row['path'])}</code></td><td>{sha}</td></tr>")
    add(
        f"<tr><td>dossier (self, html)</td>"
        f"<td><code>{html.escape(ctx['html_path_display'])}</code></td>"
        f"<td><code>{SELF_HASH_ZERO}</code></td></tr>"
    )
    add("</tbody>")
    add("</table>")
    add(
        '<p class="note">Self-hash rule: the <code>dossier (self, html)</code> row is the SHA-256 of this '
        "HTML file computed with its own 64-hex-character self-hash field zeroed (64 <code>0</code> characters). "
        "It is reproducible with any SHA-256 tool: replace that field with zeros and hash the file. "
        "With identical inputs and build time this dossier is byte-identical.</p>"
    )
    add("</section>")

    add(
        f'<footer class="foot">{_h(PRODUCED_CLAUSE)} · {_h(ENGINE_NAME)} v{_h(ENGINE_VERSION)} · '
        f"generated {_h(ctx['generated_at'])} (UTC)</footer>"
    )
    add("</main>")
    add("</body>")
    add("</html>")
    add("")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def _stamp_self_hash(template, self_hash):
    """Insert ``self_hash`` into the rendered template's self-hash field.

    The field is the **last** 64-zero run of the template: hashed input data
    rendered above the Evidence & integrity section can legitimately contain
    64 zeros, and a first-match substitution would then stamp the hash inside
    the data instead of the self-hash field (silently breaking the
    reproducible self-hash rule).
    """
    idx = template.rfind(SELF_HASH_ZERO)
    if idx < 0:
        return template
    return template[:idx] + self_hash + template[idx + len(SELF_HASH_ZERO):]


def build(decision_path, out_dir, extra_paths=None, generated_at=None):
    """Build the one-page decision dossier.

    Parameters
    ----------
    decision_path : str
        Path of ``decision_<case>.json``. A missing or unreadable path does
        not raise: the dossier reports it as ``Missing input: <path>``.
    out_dir : str
        Directory receiving ``dossier_<case>.md`` and ``dossier_<case>.html``
        (created if needed).
    extra_paths : dict[str, str] | None
        Optional extra inputs, e.g. ``{"baseline_report": "...json"}``. Missing
        extras are reported, never invented.
    generated_at : str | None
        ISO-8601 UTC build timestamp. Defaults to the current time; pass a
        fixed value for byte-identical reproducible builds.

    Returns
    -------
    dict
        ``{"md_path", "html_path", "sha256", ...}`` — ``sha256`` (and
        ``sha256_html``) are the reproducible self-hashes: SHA-256 over the
        rendered file with the file's own 64-hex self-hash field zeroed.
        ``sha256_md_file`` / ``sha256_html_file`` are the digests of the bytes
        as written. ``inputs`` lists every declared input with its status.
    """
    generated = generated_at or _iso_now()

    decision_record = _read_input("decision", decision_path)
    seen = set()
    try:
        seen.add(os.path.normcase(os.path.abspath(str(decision_path))))
    except (OSError, ValueError):
        pass

    extras = []
    for label in sorted((extra_paths or {}).keys(), key=str):
        path = (extra_paths or {})[label]
        try:
            key = os.path.normcase(os.path.abspath(str(path)))
        except (OSError, ValueError):
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        extras.append(_read_input(_canon_label(label), path))
    extras.sort(key=lambda r: (r["label"], r["path"]))

    data = decision_record["data"] if isinstance(decision_record.get("data"), dict) else {}
    decision = data.get("decision")
    decision = decision if isinstance(decision, dict) else {}
    case = _case_id(decision_record, decision_path)

    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.abspath(os.path.join(out_dir, f"dossier_{case}.md"))
    html_path = os.path.abspath(os.path.join(out_dir, f"dossier_{case}.html"))

    ctx = {
        "case": case,
        "generated_at": generated,
        "window": data.get("window"),
        "inputs_summary": data.get("inputs_summary"),
        "hypotheses": data.get("hypothesis_verdicts"),
        "decision": decision,
        "calibration": data.get("calibration"),
        "decision_rec": decision_record,
        "extras": extras,
        "baseline": next((r for r in extras if r["label"] == "baseline_report"), None),
        "md_path_display": _display_path(md_path),
        "html_path_display": _display_path(html_path),
    }

    md_template = render_markdown(ctx)
    md_self_hash = hashlib.sha256(md_template.encode("utf-8")).hexdigest()
    md_final = _stamp_self_hash(md_template, md_self_hash)

    html_template = render_html(ctx)
    html_self_hash = hashlib.sha256(html_template.encode("utf-8")).hexdigest()
    html_final = _stamp_self_hash(html_template, html_self_hash)

    with open(md_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(md_final)
    with open(html_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(html_final)

    return {
        "case": case,
        "generated_at": generated,
        "md_path": md_path,
        "html_path": html_path,
        "sha256": md_self_hash,
        "sha256_html": html_self_hash,
        "sha256_md_file": hashlib.sha256(md_final.encode("utf-8")).hexdigest(),
        "sha256_html_file": hashlib.sha256(html_final.encode("utf-8")).hexdigest(),
        "inputs": [
            {
                "label": record["label"],
                "path": record["path"],
                "sha256": record["sha256"],
                "status": record["status"],
            }
            for record in [decision_record] + extras
        ],
    }


def find_latest_dossier(evidence_dir):
    """Return the most recently modified ``dossier_*.html`` in a directory."""
    try:
        names = sorted(os.listdir(evidence_dir))
    except OSError:
        return None
    candidates = []
    for name in names:
        if name.startswith("dossier_") and name.endswith(".html"):
            path = os.path.join(evidence_dir, name)
            if os.path.isfile(path):
                candidates.append(path)
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda p: (os.path.getmtime(p), os.path.basename(p)))
    except OSError:
        return max(candidates, key=os.path.basename)


def parse_dossier_metadata(md_path):
    """Read case/verdict/generated_at back from a rendered dossier Markdown."""
    meta = {"case": None, "verdict": None, "generated_at": None}
    try:
        with open(md_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return meta
    for key, pattern in _META_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = match.group(1).strip().replace("\\|", "|")
            meta[key] = None if value == MISSING else value
    return meta
