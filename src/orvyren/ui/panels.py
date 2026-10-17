# -*- coding: utf-8 -*-
"""``panels`` — the 3-panel demo UI (M10, 10 h slice).

One page, three panels — **Situation / Graphe / Décision** — with a permanent
banner (mode, block, hash, age). The graph panel shows Q1/Q4/Q6/Q7. Nothing is
ever invented: when a source is absent the panel renders **« SOURCE
MANQUANTE »**.

Source resolution (first hit wins, and the banner names it):

1. ``LIVE``  — :mod:`orvyren.graph.api` (read-only SQL) when ``live=True``;
2. ``REPLAY``— ``evidence/ui_snapshot.json`` (published by A);
3. ``FIXTURE``— the B0 maquette ``src/orvyren/ui/maquette.json``;
4. nothing → every panel says « SOURCE MANQUANTE ».

The data's own ``mode`` stamp is displayed next to the display mode: a
snapshot measured LIVE is shown REPLAY **from** LIVE data — both are visible.

Standard library only (no JavaScript, no external asset — the W8 rule).
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Tuple

__all__ = ["panels_payload", "build_html", "QUERY_CODES", "PANEL_NAMES"]

#: The four queries the graph panel must show (CONTRACT.md « UI »).
QUERY_CODES: Tuple[str, ...] = ("Q1", "Q4", "Q6", "Q7")

#: The three panels.
PANEL_NAMES: Tuple[str, ...] = ("Situation", "Graphe", "Décision")

MISSING = "SOURCE MANQUANTE"
MODES = ("LIVE", "REPLAY", "FIXTURE", "SYNTHETIC")

_MAQUETTE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "maquette.json")


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _age_stamp(stamp: str) -> str:
    """Human age of an ISO-8501 stamp (or MISSING)."""
    if not stamp:
        return MISSING
    try:
        moment = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return str(stamp)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - moment
    seconds = int(delta.total_seconds())
    if seconds < 0:
        return "%s (horloge locale en avance)" % stamp
    if seconds < 3600:
        return "%d min" % (seconds // 60)
    if seconds < 86400:
        return "%d h" % (seconds // 3600)
    return "%d j" % (seconds // 86400)


def _missing_block(query: str) -> Dict[str, Any]:
    return {"query": query, "statut": MISSING, "as_of": None, "rows": [],
            "count": 0, "latency_ms": None, "provenance": [], "mode": None}


def _query_block(payload: Mapping[str, Any], query: str) -> Dict[str, Any]:
    """Normalise one query block of a snapshot/maquette payload."""
    candidates = (
        payload.get("panels", {}).get("graphe", {}) if isinstance(payload.get("panels"), Mapping) else {},
        payload,
    )
    for source in candidates:
        if not isinstance(source, Mapping):
            continue
        block = source.get(query) or source.get(query.lower())
        if isinstance(block, Mapping) and block.get("rows") is not None:
            normalised = _missing_block(query)
            normalised.update({key: value for key, value in block.items()})
            normalised.pop("statut", None)
            normalised.setdefault("provenance", [])
            return normalised
    return _missing_block(query)


def _snapshot_source(evidence_dir: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """The REPLAY source ``evidence/ui_snapshot.json`` (A publishes it)."""
    path = os.path.join(evidence_dir, "ui_snapshot.json")
    data = _read_json(path)
    return (data, "evidence/ui_snapshot.json") if data else (None, MISSING)


def _fixture_source(maquette_path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    data = _read_json(maquette_path)
    return (data, "src/orvyren/ui/maquette.json") if data else (None, MISSING)


def _live_payload(api: Any, db: Optional[str], defaults: Mapping[str, Any]
                  ) -> Dict[str, Any]:
    """Query the read-only graph API. Unqueryable panels stay honest."""
    import os as _os
    db = db or _os.environ.get("ORVYREN_GRAPH_DB")
    situation = api.snapshot(db)
    graphe: Dict[str, Any] = {}
    graphe["Q4"] = api.pit(db, limit=20)
    holder = _os.environ.get("ORVYREN_UI_HOLDER") or defaults.get("holder") or ""
    asset = _os.environ.get("ORVYREN_UI_ASSET") or defaults.get("asset") or ""
    relation_id = (_os.environ.get("ORVYREN_UI_RELATION")
                   or defaults.get("relation_id") or "")
    graphe["Q1"] = api.exposure(db, holder) if holder else _missing_block("Q1")
    graphe["Q7"] = api.concentration(db, asset) if asset else _missing_block("Q7")
    graphe["Q6"] = (api.provenance(db, relation_id) if relation_id
                    else _missing_block("Q6"))
    return {"situation": situation, "graphe": graphe}


def panels_payload(ctx: Any = None, *, live: bool = False,
                   api: Any = None, db: Optional[str] = None,
                   maquette_path: Optional[str] = None
                   ) -> Dict[str, Any]:
    """The 3-panel payload (JSON) — banner + Situation/Graphe/Décision."""
    evidence_dir = (ctx.evidence_path() if ctx is not None
                    else os.path.join(os.getcwd(), "evidence"))
    snapshot, snapshot_source = _snapshot_source(evidence_dir)
    fixture, fixture_source = _fixture_source(maquette_path or _MAQUETTE)
    chosen: Optional[Dict[str, Any]] = None
    mode, source = None, MISSING
    if live and api is not None:
        defaults = snapshot or fixture or {}
        chosen = _live_payload(api, db, defaults)
        mode, source = "LIVE", "graph/api.py (read-only SQL)"
    elif snapshot is not None:
        chosen = {"situation": snapshot, "graphe": snapshot}
        mode, source = "REPLAY", snapshot_source
    elif fixture is not None:
        fixture_panels = fixture.get("panels", {}) if isinstance(fixture.get("panels"), Mapping) else {}
        chosen = {"situation": fixture_panels.get("situation", fixture),
                  "graphe": fixture_panels.get("graphe", fixture)}
        mode, source = "FIXTURE", fixture_source
    if chosen is None:
        chosen = {"situation": {}, "graphe": {}}

    situation = chosen.get("situation") or {}
    if not isinstance(situation, Mapping):
        situation = {}
    banner_data = (fixture or snapshot or {}).get("banner", {}) \
        if isinstance((fixture or snapshot or {}).get("banner"), Mapping) else {}
    data_mode = (snapshot or fixture or {}).get("mode")
    graph_hash = situation.get("graph_hash") or banner_data.get("graph_hash") or MISSING
    as_of = (situation.get("as_of") or banner_data.get("as_of")
             or (snapshot or {}).get("as_of") or MISSING)
    as_of_block = (situation.get("as_of_block") or banner_data.get("as_of_block")
                   or (snapshot or {}).get("as_of_block") or MISSING)
    generated_at = (snapshot or fixture or {}).get("generated_at") \
        or banner_data.get("age") or ""

    decision = _decision_panel(evidence_dir, fixture)
    return {
        "schema": "orvyren/ui-panels/v1",
        "mode": mode,
        "data_mode": data_mode,
        "source": source,
        "banner": {
            "mode": mode or MISSING,
            "data_mode": data_mode or MISSING,
            "as_of": as_of,
            "as_of_block": as_of_block,
            "graph_hash": graph_hash,
            "age": _age_stamp(generated_at) if generated_at else MISSING,
            "source": source,
        },
        "panels": {
            "situation": {
                "counts": situation.get("counts") if isinstance(situation.get("counts"), Mapping) else {},
                "graph_hash": graph_hash,
                "statut": MISSING if not situation.get("counts") else "OK",
            },
            "graphe": {code: _query_block(chosen.get("graphe") or {}, code)
                       for code in QUERY_CODES},
            "decision": decision,
        },
    }


def _decision_panel(evidence_dir: str, fixture: Optional[Mapping[str, Any]]
                    ) -> Dict[str, Any]:
    """Decision panel — the agent loop's output, else SOURCE MANQUANTE."""
    import glob
    candidates = sorted(glob.glob(os.path.join(evidence_dir, "decision_*.json")))
    if candidates:
        data = _read_json(candidates[-1])
        if data:
            return {"statut": "OK", "source": os.path.basename(candidates[-1]),
                    "decision": data}
    fixture_decision = (fixture or {}).get("panels", {}).get("decision") \
        if isinstance((fixture or {}).get("panels"), Mapping) else None
    if isinstance(fixture_decision, Mapping):
        return {"statut": MISSING, "source": "src/orvyren/ui/maquette.json",
                "note": fixture_decision.get("note", "")}
    return {"statut": MISSING, "source": MISSING, "note": ""}


# ---------------------------------------------------------------------------
# HTML rendering (no JavaScript, no external asset).
# ---------------------------------------------------------------------------
def _table(headers, rows, cap=25) -> str:
    head = "".join("<th>%s</th>" % _esc(h) for h in headers)
    body = "".join(
        "<tr>%s</tr>" % "".join("<td>%s</td>" % _esc(cell) for cell in row)
        for row in rows[:cap])
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, body)


def _block_html(block: Mapping[str, Any]) -> str:
    rows = block.get("rows") or []
    if block.get("statut") == MISSING:
        return "<p class=\"missing\">%s</p>" % _esc(MISSING)
    if not rows:
        # Source présente, zéro ligne : ce n'est pas une source manquante.
        return "<p>0 ligne (source présente, count=%s)</p>" % _esc(block.get("count"))
    headers = sorted({key for row in rows if isinstance(row, Mapping)
                      for key in row})
    body = [[row.get(header) for header in headers]
            for row in rows if isinstance(row, Mapping)]
    note = ("<p>count=%s · latency_ms=%s · mode=%s</p>"
            % (_esc(block.get("count")), _esc(block.get("latency_ms")),
               _esc(block.get("mode"))))
    return note + _table(headers, body)


def build_html(payload: Mapping[str, Any]) -> str:
    """Server-rendered 3-panel page (the M10 contract, in one screen)."""
    banner = payload.get("banner", {})
    parts = [
        "<!DOCTYPE html><html lang=\"fr\"><head><meta charset=\"utf-8\">",
        "<title>ORVYREN — 3 panneaux</title>",
        "<style>body{font-family:sans-serif;margin:1em}table{border-collapse:collapse}"
        "td,th{border:1px solid #999;padding:2px 6px;font-size:12px}"
        ".banner{background:#eee;padding:6px;margin-bottom:1em}"
        ".missing{color:#a00;font-weight:bold}section{margin-bottom:2em}</style>",
        "</head><body>",
        "<div class=\"banner\"><strong>mode=%s</strong> · data_mode=%s · bloc=%s · "
        "hash=%s · âge=%s · source=%s</div>"
        % (_esc(banner.get("mode")), _esc(banner.get("data_mode")),
           _esc(banner.get("as_of_block")), _esc(banner.get("graph_hash")),
           _esc(banner.get("age")), _esc(banner.get("source"))),
    ]
    panels = payload.get("panels", {})

    situation = panels.get("situation", {})
    parts.append("<section id=\"situation\"><h2>1 · Situation</h2>")
    if situation.get("statut") == MISSING or not situation.get("counts"):
        parts.append("<p class=\"missing\">%s</p>" % _esc(MISSING))
    else:
        parts.append(_table(["clé", "valeur"],
                            sorted(situation.get("counts", {}).items())))
    parts.append("</section>")

    parts.append("<section id=\"graphe\"><h2>2 · Graphe</h2>")
    for code in QUERY_CODES:
        block = panels.get("graphe", {}).get(code, _missing_block(code))
        parts.append("<h3>%s</h3>" % _esc(code))
        parts.append(_block_html(block))
    parts.append("</section>")

    decision = panels.get("decision", {})
    parts.append("<section id=\"decision\"><h2>3 · Décision</h2>")
    if decision.get("statut") == MISSING:
        parts.append("<p class=\"missing\">%s</p>" % _esc(MISSING))
        if decision.get("note"):
            parts.append("<p>%s</p>" % _esc(decision.get("note")))
    else:
        parts.append("<pre>%s</pre>"
                     % _esc(json.dumps(decision.get("decision", {}),
                                       indent=2, ensure_ascii=False)))
    parts.append("</section></body></html>")
    return "".join(parts)
