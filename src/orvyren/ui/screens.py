# -*- coding: utf-8 -*-
"""ORVYREN-Core — read-only builders for the twelve local UI screens (W8, L8.1-L8.3).

Twelve offline screens rendered as plain server-side HTML: **no JavaScript, no
external asset, no network**.  Every screen carries a mandatory banner with:

* its **mode** (``LIVE`` / ``REPLAY — journal scellé`` / ``DONNÉES FIGÉES`` …),
* the **wall clock** (UTC, read once per request),
* the **simulated clock** when the underlying artefact has one,
* the **sources** it renders, with a short SHA-256 per file.

A screen never invents data: a missing source renders as ``SOURCE ABSENTE``.

Screens (L8.1: 1-9, L8.3: 10-12):

======  ==============================  =========================================
1       Fenêtre & PIT                   épisodes archivés + horloge du rejeu
2       Graphe                          snapshots de graphe (contenu adressé)
3       Branches                        hypothèses + trace RDOF du dossier figé
4       Timeline des réflexions         appels LLM scellés (role, modèle, coût)
5       Recherche & coût                requêtes graphe + coût cumulé des appels
6       Dossier                         dossier de décision one-page (liens)
7       Refus politique                 verdicts P1-P14 + refus + garde-fous
8       Quarantaine                     heures écartées par les portes qualité
9       Coût par décision               coût vs plafonds gelés (A5)
10      Runs A/C/E                      événements chaîne + reçus + export
11      Journal (3 flux)                chaîne / agents / méta, volumétrie, têtes
12      Kill switch                     K0/K1 + séquence testée (refus, révocation)
======  ==============================  =========================================
"""

import datetime
import glob
import hashlib
import html
import json
import os
import re

_SCREENS_DIRNAME = "screens"  # kept for symmetry; builders live in this module


class Ctx:
    """Immutable context: where the repository and the evidence live."""

    __slots__ = ("repo_root", "evidence_dir")

    def __init__(self, repo_root, evidence_dir):
        self.repo_root = os.path.abspath(repo_root)
        self.evidence_dir = os.path.abspath(evidence_dir)

    def repo_path(self, *parts):
        return os.path.join(self.repo_root, *parts)

    def evidence_path(self, *parts):
        return os.path.join(self.evidence_dir, *parts)


# --------------------------------------------------------------------------
# generic helpers — every read is defensive; a screen never raises on a
# missing file, it renders SOURCE ABSENTE instead.
# --------------------------------------------------------------------------


def _esc(value):
    return html.escape(str(value), quote=True)


def _rel(ctx, path):
    try:
        return os.path.relpath(path, ctx.repo_root).replace(os.sep, "/")
    except ValueError:
        return path


def _sha256_short(path, length=16):
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()[:length]
    except OSError:
        return None


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _read_jsonl(path, limit=None):
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if limit and len(rows) >= limit:
                    break
    except OSError:
        return None
    return rows


def _exists_note(ctx, path):
    if os.path.exists(path):
        return ""
    return '<p class="warn">SOURCE ABSENTE : <code>%s</code></p>' % _esc(_rel(ctx, path))


def _clock_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _table(headers, rows, cap=None):
    if cap is not None and len(rows) > cap:
        rows = rows[:cap]
        truncated = True
    else:
        truncated = False
    parts = ['<table><thead><tr>']
    parts += ["<th>%s</th>" % _esc(h) for h in headers]
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>" + "".join("<td>%s</td>" % _esc(cell) for cell in row) + "</tr>")
    parts.append("</tbody></table>")
    if truncated:
        parts.append('<p class="note">(table tronquée pour l\'affichage)</p>')
    return "".join(parts)


def _source_banner_list(ctx, sources):
    items = []
    for path in sources:
        short = _sha256_short(path)
        name = _rel(ctx, path)
        if short:
            items.append("<li><code>%s</code> <span class=\"sha\">sha256:%s…</span></li>" % (_esc(name), short))
        else:
            items.append("<li><code>%s</code> <span class=\"warn\">absent</span></li>" % _esc(name))
    return "<ul class=\"sources\">%s</ul>" % "".join(items)


_STYLE = """
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:1.5rem;max-width:1150px;color:#1a1a1a}
h1{font-size:1.35rem;margin:0 0 .4rem 0}
h2{font-size:1.05rem;margin:1.1rem 0 .4rem 0}
.banner{position:sticky;top:0;background:#101820;color:#f5f7fa;padding:.55rem .9rem;border-radius:6px;font-size:.85rem;display:flex;flex-wrap:wrap;gap:1.2rem}
.banner b{color:#ffd166}
.banner .mode{color:#7ae582}
nav{margin:.6rem 0;font-size:.9rem}
nav a{margin-right:1rem}
table{border-collapse:collapse;margin:.5rem 0;font-size:.85rem}
th,td{border:1px solid #ccc;padding:.25rem .5rem;text-align:left;vertical-align:top}
th{background:#f0f2f5}
code{background:#f4f4f4;padding:.05rem .25rem;border-radius:3px;font-size:.85em}
.warn{color:#b00020}
.note{color:#555;font-size:.85rem}
.sha{color:#777;font-size:.8rem}
.sources{font-size:.8rem;color:#555;margin:.2rem 0;padding-left:1.2rem}
footer{margin-top:1.4rem;color:#666;font-size:.8rem;border-top:1px solid #ddd;padding-top:.5rem}
.kv{margin:.3rem 0}
"""


def _page(ctx, screen_id, title, mode, clock_sim, body, sources):
    total = len(SCREEN_DEFS)
    prev_link = ('<a href="/screen/%d">← écran %d</a>' % (screen_id - 1, screen_id - 1)) if screen_id > 1 else ""
    next_link = ('<a href="/screen/%d">écran %d →</a>' % (screen_id + 1, screen_id + 1)) if 1 <= screen_id < total else ""
    doc = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><title>ORVYREN — écran %(id)d — %(title)s</title>
<style>%(style)s</style></head><body>
<div class="banner">
  <span>ÉCRAN %(id)d/%(total)d</span>
  <span class="mode">MODE : %(mode)s</span>
  <span>Horloge (UTC) : %(clock)s</span>
  <span>Horloge simulée : %(sim)s</span>
</div>
<nav><a href="/ui">index des écrans</a><a href="/">dossier one-page</a>%(prev)s%(next)s</nav>
<h1>%(title)s</h1>
%(body)s
<h2>Sources rendues</h2>
%(sources)s
<footer>ORVYREN-Core — page statique servie localement (hors-ligne) : aucun JavaScript,
aucun asset externe, aucune donnée inventée. Un champ absent s'affiche
« SOURCE ABSENTE » ou « — ».</footer>
</body></html>
""" % {
        "id": screen_id, "total": total, "title": _esc(title), "mode": _esc(mode),
        "clock": _clock_now(), "sim": _esc(clock_sim if clock_sim else "—"),
        "style": _STYLE, "body": body, "sources": _source_banner_list(ctx, sources),
        "prev": prev_link, "next": next_link,
    }
    return doc.encode("utf-8")


# --------------------------------------------------------------------------
# builders — one per screen
# --------------------------------------------------------------------------


def _s1_fenetre_pit(ctx):
    episodes = sorted(glob.glob(ctx.evidence_path("episode_*.json")))
    rows = []
    clock_sim = None
    for path in episodes:
        data = _read_json(path) or {}
        window = data.get("window") or {}
        end = window.get("end_utc")
        if end and (clock_sim is None or end > clock_sim):
            clock_sim = end
        rows.append((
            data.get("case", os.path.basename(path)),
            data.get("mode", "—"),
            "%s → %s" % (window.get("start_utc", "—"), end or "—"),
            window.get("n_points", "—"),
            window.get("step_s", "—"),
            len(data.get("sources") or []),
        ))
    body = _exists_note(ctx, ctx.evidence_path("episode_usdc_2023-03.json"))
    body += "<p>Fenêtres d'épisode utilisées par le harnais : <b>PIT strict</b> — " \
            "tout fait postérieur à la fenêtre est rejeté (run abandonné + audit).</p>"
    body += _table(["cas", "mode", "fenêtre (UTC)", "points", "pas (s)", "sources"], rows)
    journal = _read_json(_first_glob(ctx.evidence_path("replay", "*_replay_journal_*.json")))
    if journal:
        body += "<h2>Horloge du rejeu (journal)</h2>"
        body += _table(["run_id", "ts_wall_utc", "transcript_hash", "note horloge"], [(
            journal.get("run_id", "—"), journal.get("ts_wall_utc", "—"),
            (journal.get("transcript_hash") or "—")[:20] + "…",
            (journal.get("clock_audit") or {}).get("note", "—"),
        )])
    return {"title": "1 · Fenêtre & PIT", "mode": "DONNÉES FIGÉES — épisodes archivés",
            "clock_sim": clock_sim, "body": body,
            "sources": episodes + [p for p in [_first_glob(ctx.evidence_path("replay", "*_replay_journal_*.json"))] if p]}


def _first_glob(pattern):
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def _s2_graphe(ctx):
    snapshots = sorted(glob.glob(ctx.evidence_path("graph_snapshots", "*")))
    rows = []
    sources = []
    for snap_dir in snapshots:
        snap_file = os.path.join(snap_dir, "graph_snapshot.json")
        data = _read_json(snap_file) or {}
        counts = data.get("counts") or {}
        counts_txt = ", ".join("%s=%s" % (k, v) for k, v in sorted(counts.items())) or "—"
        rows.append((
            data.get("case_id", os.path.basename(snap_dir)),
            data.get("as_of", "—"),
            counts_txt,
            len(data.get("records") or []),
            (data.get("snapshot_hash") or "—")[:20] + "…",
        ))
        if os.path.exists(snap_file):
            sources.append(snap_file)
    body = "<p>Snapshots exportés du graphe (34 relations / 4 familles, record 17 champs). " \
           "Contenu <b>adressé par hash</b> : le snapshot cité dans une preuve est re-vérifiable hors-ligne.</p>"
    body += _table(["cas", "as_of", "compteurs", "records", "snapshot_hash"], rows)
    return {"title": "2 · Graphe", "mode": "SNAPSHOTS FIGÉS (contenu adressé)",
            "clock_sim": None, "body": body, "sources": sources}


def _s3_branches(ctx):
    record_path = ctx.evidence_path("decision_record_usdc-2023-03.json")
    record = _read_json(record_path) or {}
    rows = []
    registry = record.get("hypotheses_registry") or {}
    for hyp in registry.get("ids") or []:
        rows.append((hyp, ", ".join(registry.get("etats") or ["—"])))
    body = _exists_note(ctx, record_path)
    body += "<p>Branches (hypothèses) du dossier <code>%s</code> et trace du processus de décision RDOF :</p>" % _esc(record.get("case", "—"))
    body += _table(["hypothèse", "état"], rows)
    rdof = record.get("rdof") or {}
    trace = rdof.get("trace") or []
    if isinstance(trace, list) and trace:
        trace_rows = []
        for step in trace:
            if isinstance(step, dict):
                trace_rows.append(tuple(str(step.get(k, ""))[:90] for k in ("step", "kind", "verdict", "note")))
            else:
                trace_rows.append((str(step)[:160], "", "", ""))
        body += "<h2>Trace RDOF</h2>"
        body += _table(["étape", "kind", "verdict", "note"], trace_rows, cap=16)
    body += "<h2>Arrêt & budget de recherche</h2>"
    body += _table(["arrêt", "règle", "dominant final"], [(
        rdof.get("stop", "—"), rdof.get("stop_rule", "—"),
        json.dumps(rdof.get("dominant_final"), ensure_ascii=False)[:120])])
    abstention = record.get("abstention")
    if abstention is not None:
        body += "<p>Abstention (A1-A5) : <code>%s</code></p>" % _esc(json.dumps(abstention, ensure_ascii=False)[:200])
    return {"title": "3 · Branches", "mode": "REPLAY — dossier de décision figé",
            "clock_sim": None, "body": body, "sources": [record_path]}


def _s4_timeline(ctx):
    calls_path = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "calls.jsonl")
    calls = _read_jsonl(calls_path) or []
    seed_path = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "SEED.json")
    blobs_dir = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "blobs")
    blobs = sorted(os.listdir(blobs_dir)) if os.path.isdir(blobs_dir) else []
    rows = []
    last_ts = None
    for index, call in enumerate(calls, start=1):
        last_ts = call.get("ts_utc") or last_ts
        rows.append((
            index, call.get("ts_utc", "—"), call.get("role", "—"),
            "%s %s" % (call.get("model", "—"), call.get("model_version_pinned", "")),
            "%s/%s" % (call.get("tokens_in", "—"), call.get("tokens_out", "—")),
            call.get("latency_ms", "—"), call.get("cost_usd", "—"),
            "%s → %s" % ((call.get("prompt_hash") or "—")[:10], (call.get("response_hash") or "—")[:10]),
        ))
    body = _exists_note(ctx, calls_path)
    body += '<p class="note">Sorties <b>figées de démonstration</b> (SEED.json) : le rejeu est bit-à-bit et ' \
            're-vérifiable ; une session <b>live</b> exige la clé fournisseur (jamais dans le dépôt).</p>'
    body += _table(["n°", "ts_utc", "rôle", "modèle", "tokens in/out", "latence (ms)", "coût ($)", "prompt → réponse"], rows)
    body += "<p>Blobs scellés : <b>%d</b> fichiers (prompts + réponses adressés par hash) dans <code>fixtures/agents/store_usdc-2023-03/blobs/</code>.</p>" % len(blobs)
    if os.path.exists(seed_path):
        body += "<p>SEED.json — provenance : <code>%s</code></p>" % _esc((_sha256_short(seed_path, 24) or "?") + "…")
    return {"title": "4 · Timeline des réflexions", "mode": "REPLAY — journal scellé",
            "clock_sim": last_ts, "body": body, "sources": [p for p in (calls_path, seed_path) if os.path.exists(p)]}


def _s5_recherche_cout(ctx):
    queries_path = ctx.repo_path("src", "orvyren", "graph", "queries.py")
    names = []
    try:
        with open(queries_path, "r", encoding="utf-8") as handle:
            names = re.findall(r"^def ([a-zA-Z0-9_]+)\(", handle.read(), re.MULTILINE)
    except OSError:
        names = []
    calls_path = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "calls.jsonl")
    calls = _read_jsonl(calls_path) or []
    total = sum(float(c.get("cost_usd") or 0) for c in calls)
    per_model = {}
    for call in calls:
        per_model.setdefault(call.get("model", "—"), [0, 0.0])
        per_model[call.get("model", "—")][0] += 1
        per_model[call.get("model", "—")][1] += float(call.get("cost_usd") or 0)
    model_rows = [(m, "%d appels" % n, "%.6f $" % c) for m, (n, c) in sorted(per_model.items())]
    body = "<h2>Recherche</h2>"
    if names:
        body += "<p>Requêtes graphe disponibles (module <code>src/orvyren/graph/queries.py</code>) :</p>"
        body += "<ul>" + "".join("<li><code>%s</code></li>" % _esc(n) for n in names) + "</ul>"
    else:
        body += _exists_note(ctx, queries_path)
    body += "<p class='note'>Recherche <b>sémantique / embeddings</b> : reclassée en V2 — absente de la v1 " \
            "(voir <code>docs/decisions/ADR-0003</code>).</p>"
    body += "<h2>Coût cumulé des appels LLM (session scellée)</h2>"
    body += _table(["modèle", "volume", "coût"], model_rows + [("TOTAL", "%d appels" % len(calls), "%.6f $" % total)])
    return {"title": "5 · Recherche & coût", "mode": "REPLAY — journal scellé",
            "clock_sim": None, "body": body,
            "sources": [p for p in (queries_path, calls_path) if os.path.exists(p)]}


def _s6_dossier(ctx):
    from orvyren.audit import dossier as dossier_mod

    latest = dossier_mod.find_latest_dossier(ctx.evidence_dir)
    body = ""
    sources = []
    if latest:
        md_path = latest[: -len(".html")] + ".md"
        meta = dossier_mod.parse_dossier_metadata(md_path) if os.path.isfile(md_path) else {}
        body += _table(["champ", "valeur"], [
            ("cas", meta.get("case", "—")),
            ("verdict", meta.get("verdict", "—")),
            ("généré (UTC)", meta.get("generated_at", "—")),
            ("sha256 (md)", dossier_mod.sha256_file(md_path) if os.path.isfile(md_path) else "—"),
            ("sha256 (html)", dossier_mod.sha256_file(latest)),
            ("fichier html", _rel(ctx, latest)),
        ])
        body += '<p><a href="/">▸ ouvrir le dossier one-page (HTML servi)</a> · ' \
                '<a href="/api/dossier">aperçu JSON (/api/dossier)</a></p>'
        sources = [latest] + ([md_path] if os.path.isfile(md_path) else [])
    else:
        body += '<p class="warn">Aucun dossier construit. Lancer <code>python run_audit.py</code>.</p>'
    return {"title": "6 · Dossier", "mode": "REPLAY — dossier figé", "clock_sim": None,
            "body": body, "sources": sources}


def _s7_refus_politique(ctx):
    path = ctx.evidence_path("policy_execution_demo.json")
    data = _read_json(path) or {}
    cases = data.get("cases") or []
    rows = []
    for case in cases:
        rows.append((
            case.get("intent_id", "—"), case.get("action_type", "—"),
            case.get("amount_usdc", "—"), case.get("verdict", "—"),
            ", ".join(case.get("deny_codes") or []) or "—",
            len(case.get("rules_evaluated") or []),
        ))
    body = _exists_note(ctx, path)
    body += "<p>Démonstration politique (P1-P14) — cas I1/I2/I3 et verdicts attendus :</p>"
    body += _table(["intent", "action", "montant USDC", "verdict", "codes de refus", "règles évaluées"], rows)
    verdict_check = data.get("verdict_check") or {}
    unexpected = verdict_check.get("unexpected") or []
    body += "<h2>Contrôle des verdicts</h2>"
    body += '<p>Attendus : <code>%s</code> — inattendus : <b>%s</b></p>' % (
        _esc(json.dumps(verdict_check.get("expected", {}), ensure_ascii=False)),
        _esc(len(unexpected)))
    guard_blocks = data.get("guard_blocks") or []
    if guard_blocks:
        body += "<h2>Garde-fous (blocages d'exécution)</h2><ul>"
        body += "".join("<li>%s</li>" % _esc(str(block)) for block in guard_blocks)
        body += "</ul>"
    receipt = data.get("receipt_verification") or {}
    if receipt:
        body += "<p class='note'>Vérification des reçus : %s</p>" % _esc(json.dumps(receipt, ensure_ascii=False)[:240])
    return {"title": "7 · Refus politique", "mode": "%s (Base Sepolia) — preuves capturées" % (data.get("mode", "LIVE")),
            "clock_sim": None, "body": body, "sources": [path]}


def _s8_quarantaine(ctx):
    path = ctx.evidence_path("quality_report.json")
    data = _read_json(path) or {}
    examples = data.get("data_gate_examples") or []
    rows = []
    for example in examples:
        rows.append((
            example.get("hour", "—"), example.get("status", "—"),
            ", ".join(example.get("venues_present") or []) or "—",
            ", ".join(example.get("missing") or []) or "—",
        ))
    body = _exists_note(ctx, path)
    body += "<p>Heures examinées par les <b>portes qualité</b> : une source manquante est " \
            "<b>déclarée</b> (jamais comblée silencieusement) — ce qui n'atteint pas la couverture " \
            "requise n'entre pas dans une décision.</p>"
    body += _table(["heure", "statut", "sources présentes", "manquantes"], rows, cap=30)
    coverage = data.get("coverage") or {}
    if coverage:
        body += "<h2>Couverture</h2>"
        body += _table(["champ", "valeur"], [
            ("venues de prix indépendantes", ", ".join(coverage.get("independent_price_venues") or []) or "—"),
            ("heures avec ≥2 sources indépendantes", coverage.get("hours_with_two_plus_independent_venues", "—")),
            ("première heure à 2 sources", coverage.get("first_two_venue_hour", "—")),
            ("dernière heure à 2 sources", coverage.get("last_two_venue_hour", "—")),
        ])
    return {"title": "8 · Quarantaine", "mode": "DONNÉES FIGÉES — portes qualité",
            "clock_sim": None, "body": body, "sources": [path]}


def _s9_cout_decision(ctx):
    calls_path = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "calls.jsonl")
    calls = _read_jsonl(calls_path) or []
    total = sum(float(c.get("cost_usd") or 0) for c in calls)
    rows = [(c.get("ts_utc", "—"), c.get("role", "—"), c.get("model", "—"),
             "%s+%s" % (c.get("tokens_in", "—"), c.get("tokens_out", "—")), c.get("cost_usd", "—")) for c in calls]
    body = "<p>Plafonds gelés (A5, fail-closed) : <b>≤ 30 appels</b>, ≤ 12 outils, ≤ 10 min, " \
           "<b>≤ 0,10 $</b> par décision. Dépassement ⇒ arrêt immédiat, jamais de dégradation silencieuse.</p>"
    body += _table(["ts_utc", "rôle", "modèle", "tokens", "coût ($)"], rows)
    body += _table(["consommation", "valeur"], [
        ("appels LLM", "%d / 30" % len(calls)),
        ("coût total", "%.6f $ / 0,10 $" % total),
        ("part du plafond", "%.2f %%" % (100.0 * total / 0.10)),
    ])
    record = _read_json(ctx.evidence_path("decision_record_usdc-2023-03.json")) or {}
    research = record.get("research_cost") or {}
    limites = research.get("limites") or {}
    consomme = research.get("consomme") or {}
    if limites or consomme:
        body += "<h2>Budget de recherche du dossier (RDOF)</h2>"
        body += _table(["ressource", "consommé", "plafond"], [
            ("recherches", consomme.get("recherches", "—"), limites.get("recherches", "—")),
            ("appels", consomme.get("appels", "—"), limites.get("appels", "—")),
            ("secondes", consomme.get("secondes", "—"), limites.get("secondes", "—")),
        ])
    return {"title": "9 · Coût par décision", "mode": "REPLAY — journal scellé",
            "clock_sim": None, "body": body,
            "sources": [calls_path] + [p for p in [ctx.evidence_path("decision_record_usdc-2023-03.json")] if os.path.exists(p)]}


def _s10_runs(ctx):
    audit_path = ctx.evidence_path("demo_runs", "rseth", "audit.jsonl")
    records = _read_jsonl(audit_path) or []
    kinds = {}
    run_starts = []
    for record in records:
        kind = record.get("kind", "?")
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == "RUN_START":
            payload = record.get("payload") or {}
            run_starts.append((
                payload.get("run", "—"), record.get("mode", "—"),
                payload.get("case", "—"), payload.get("journal_records_at_start", "—"),
            ))
    body = _exists_note(ctx, audit_path)
    body += "<p>Chaîne d'exécution réelle (testnet) : chaque événement est enchaîné par hash " \
            "(<code>prev_hash</code> → <code>record_hash</code>).</p>"
    body += _table(["run", "mode", "cas", "enregistrements au départ"], run_starts)
    body += "<h2>Événements par type</h2>"
    body += _table(["type", "nombre"], sorted(kinds.items()))
    receipts_dir = ctx.evidence_path("demo_runs", "rseth", "receipts")
    receipts = sorted(os.listdir(receipts_dir)) if os.path.isdir(receipts_dir) else []
    body += "<h2>Reçus on-chain</h2><p>%d reçus scellés. Exemples :</p>" % len(receipts)
    body += "<ul>" + "".join("<li><code>%s</code></li>" % _esc(name[:26] + "…") for name in receipts[:8]) + "</ul>"
    a_tx = [name for name in receipts if name.startswith("0x82827c")]
    if a_tx:
        body += "<p>RUN A (transfert 100 USDC) : <code>%s</code></p>" % _esc(a_tx[0][:26] + "…")
    manifest_path = ctx.evidence_path("demo_runs", "rseth", "export", "manifest.json")
    manifest = _read_json(manifest_path) or {}
    if manifest:
        counters = manifest.get("counters") or {}
        body += "<h2>Export (RUN E)</h2>"
        body += _table(["champ", "valeur"], [
            ("run_id", manifest.get("run_id", "—")),
            ("exporté (UTC)", manifest.get("exported_at", "—")),
            ("compteurs", ", ".join("%s=%s" % (k, v) for k, v in sorted(counters.items()))[:200]),
        ])
    return {"title": "10 · Runs A/C/E", "mode": "LIVE (Base Sepolia testnet) — preuves de chaîne",
            "clock_sim": None, "body": body,
            "sources": [p for p in (audit_path, manifest_path) if os.path.exists(p)]}


def _s11_journal(ctx):
    audit_path = ctx.evidence_path("demo_runs", "rseth", "audit.jsonl")
    calls_path = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "calls.jsonl")
    replay_path = _first_glob(ctx.evidence_path("replay", "*_replay_journal_*.json"))
    audit_rows = _read_jsonl(audit_path) or []
    calls = _read_jsonl(calls_path) or []
    journal = _read_json(replay_path) if replay_path else None
    last_hash = (audit_rows[-1].get("record_hash") if audit_rows else None) or "—"
    blobs_dir = ctx.repo_path("fixtures", "agents", "store_usdc-2023-03", "blobs")
    blobs = len(os.listdir(blobs_dir)) if os.path.isdir(blobs_dir) else 0
    rows = [
        ("flux chaîne (LIVE)", _rel(ctx, audit_path) if os.path.exists(audit_path) else "absent",
         "%d enregistrements" % len(audit_rows), "tête : %s…" % last_hash[:16]),
        ("flux agents (REPLAY)", _rel(ctx, calls_path) if os.path.exists(calls_path) else "absent",
         "%d appels scellés · %d blobs" % (len(calls), blobs),
         "transcript : %s…" % ((journal or {}).get("transcript_hash") or "—")[:16]),
        ("flux méta (rejeu)", _rel(ctx, replay_path) if replay_path else "absent",
         "run_id : %s" % ((journal or {}).get("run_id") or "—"),
         "content : %s…" % ((journal or {}).get("content_sha256") or "—")[:16]),
    ]
    body = "<p>Journal d'audit à <b>trois flux</b> (W6) : chaque flux est append-only, " \
           "enchaîné par hash et re-vérifiable hors-ligne par <code>python run_verify.py &lt;cible&gt;</code>.</p>"
    body += _table(["flux", "fichier", "volumétrie", "tête / empreinte"], rows)
    return {"title": "11 · Journal (3 flux)", "mode": "MIXTE — chaque flux est étiqueté",
            "clock_sim": None, "body": body,
            "sources": [p for p in (audit_path, calls_path, replay_path) if p and os.path.exists(p)]}


def _s12_kill_switch(ctx):
    audit_path = ctx.evidence_path("demo_runs", "rseth", "audit.jsonl")
    records = _read_jsonl(audit_path) or []
    sequence = []
    revoke_tx = None
    for record in records:
        payload_text = json.dumps(record.get("payload"), ensure_ascii=False)
        low = payload_text.lower()
        if any(word in low for word in ("revoke", "pause", "reset", "refus", "0xfd8e9f28")):
            sequence.append((record.get("kind", "?"), record.get("mode", "—"), payload_text[:170]))
        if revoke_tx is None:
            match = re.search(r"0x0fb9[0-9a-f]{8}", payload_text)
            if match:
                revoke_tx = match.group(0)
    body = "<p>Procédure de coupe-circuit (gel v2) : <b>K0</b> = pause immédiate (drapeau, ≤ 5 min) ; " \
           "<b>K1</b> = révocation du rôle AGENT (Safe/Zodiac, ≤ 60 min). Fail-closed : tout refus " \
           "on-chain est un événement de journal, jamais un silence.</p>"
    body += _table(["niveau", "mécanisme", "délai", "testé"], [
        ("K0", "drapeau de pause (ORVYREN_K0_PAUSED)", "≤ 5 min", "RUN D — refus contrôlé"),
        ("K1", "revoke role AGENT (Roles v2)", "≤ 60 min", "RUN D — révocation on-chain"),
        ("reset", "restauration du rôle (reprise)", "—", "RUN D — reset confirmé"),
    ])
    receipts_dir = ctx.evidence_path("demo_runs", "rseth", "receipts")
    receipts = sorted(os.listdir(receipts_dir)) if os.path.isdir(receipts_dir) else []
    revoked = [name for name in receipts if "0fb9" in name]
    if revoked:
        revoke_tx = revoked[0][:26] + "…"
    if revoke_tx:
        body += "<p>Révocation : <code>%s</code> — refus refusé par la chaîne avec le sélecteur " \
                "<code>0xfd8e9f28</code> après révocation (preuve d'application effective).</p>" % _esc(revoke_tx)
    if sequence:
        body += "<h2>Séquence observée (journal chaîne)</h2>"
        body += _table(["type", "mode", "extrait"], sequence, cap=10)
    return {"title": "12 · Kill switch", "mode": "LIVE (Base Sepolia testnet) — preuves capturées",
            "clock_sim": None, "body": body, "sources": [p for p in (audit_path,) if os.path.exists(p)]}


SCREEN_DEFS = (
    (1, "fenetre-pit", "Fenêtre & PIT", _s1_fenetre_pit),
    (2, "graphe", "Graphe", _s2_graphe),
    (3, "branches", "Branches", _s3_branches),
    (4, "timeline", "Timeline des réflexions", _s4_timeline),
    (5, "recherche-cout", "Recherche & coût", _s5_recherche_cout),
    (6, "dossier", "Dossier", _s6_dossier),
    (7, "refus-politique", "Refus politique", _s7_refus_politique),
    (8, "quarantaine", "Quarantaine", _s8_quarantaine),
    (9, "cout-decision", "Coût par décision", _s9_cout_decision),
    (10, "runs", "Runs A/C/E", _s10_runs),
    (11, "journal", "Journal (3 flux)", _s11_journal),
    (12, "kill-switch", "Kill switch", _s12_kill_switch),
)


def screen_ids():
    return [screen_id for screen_id, _slug, _title, _builder in SCREEN_DEFS]


def build_screen(screen_id, ctx):
    """Render screen ``screen_id`` (1..12) as UTF-8 HTML bytes. Unknown id: KeyError."""
    for sid, slug, title, builder in SCREEN_DEFS:
        if sid == screen_id:
            try:
                result = builder(ctx)
            except Exception as exc:  # a screen must never take the server down
                result = {
                    "title": title,
                    "mode": "ERREUR DE RENDU",
                    "clock_sim": None,
                    "body": '<p class="warn">ERREUR DE RENDU : %s: %s</p>' % (_esc(type(exc).__name__), _esc(exc)),
                    "sources": [],
                }
            return _page(ctx, sid, result["title"], result["mode"], result.get("clock_sim"),
                         result["body"], result.get("sources") or [])
    raise KeyError(screen_id)


def build_index(ctx):
    """Render ``/ui`` — the offline index of the twelve screens."""
    parts = ['<table><thead><tr><th>écran</th><th>titre</th><th>mode</th><th>état</th></tr></thead><tbody>']
    for sid, slug, title, builder in SCREEN_DEFS:
        try:
            probe = builder(ctx) or {}
            status = "OK" if probe.get("sources") else "sources manquantes"
            mode = probe.get("mode", "—")
        except Exception as exc:
            status = "erreur : %s" % type(exc).__name__
            mode = "—"
        parts.append(
            '<tr><td><a href="/screen/%d">%d</a></td><td>%s</td><td>%s</td><td>%s</td></tr>'
            % (sid, sid, _esc(title), _esc(mode), _esc(status)))
    parts.append("</tbody></table>")
    body = "<p>Visionneuse locale <b>hors-ligne</b> : douze écrans de démonstration et d'audit. " \
           "Chaque écran affiche son <b>mode</b> et son <b>horloge</b> ; un champ absent est déclaré, jamais inventé.</p>"
    body += "".join(parts)
    return _page(ctx, 0, "Index des écrans", "INDEX — hors-ligne", None, body, [])
