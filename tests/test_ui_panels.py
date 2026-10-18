#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: the 3-panel UI (M10, B4).

Situation / Graphe / Décision with a permanent banner (mode + block + hash +
age), Q1/Q4/Q6/Q7 visible, LIVE/REPLAY/FIXTURE source resolution and the
honest « SOURCE MANQUANTE » rule: a panel whose source is absent says so, and
a panel whose source exists but returned zero rows does NOT.

Execution: ``python -m pytest tests/test_ui_panels.py -q``
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from orvyren.ui import panels  # noqa: E402
from orvyren.ui import server as ui_server  # noqa: E402

SNAPSHOT = {
    "schema": "orvyren-ui-snapshot/v1",
    "generated_at": "2026-10-17T12:37:34+00:00",
    "mode": "LIVE",
    "as_of": "2026-10-17T11:12:57+00:00",
    "as_of_block": 52723115,
    "counts": {"relations": 12937, "nodes": 16174, "events": 15000,
               "relation_provenance": 12937},
    "graph_hash": "016d6af64fa15b0d58a48550404a455362be374cf0d8e36b52bf0f68ce428c3c",
    "q1": {"query": "Q1", "rows": [{"asset": "asset:x", "amount": 1}],
           "count": 1, "mode": "LIVE"},
    "q4": {"query": "Q4", "rows": [], "count": 0, "mode": "LIVE"},
    "q6": {"query": "Q6", "rows": [{"ref_id": "event:1"}], "count": 1,
           "mode": "LIVE"},
    "q7": {"query": "Q7", "rows": [{"src": "position:p", "amount": 2}],
           "count": 1, "mode": "LIVE"},
}


class FakeCtx:
    def __init__(self, evidence_dir):
        self.evidence_dir = evidence_dir

    def evidence_path(self, *parts):
        return os.path.join(self.evidence_dir, *parts)


class FakeApi:
    """Deterministic stand-in for orvyren.graph.api (LIVE path)."""

    def snapshot(self, db=None):
        return {"query": "snapshot", "counts": {"relations": 2},
                "graph_hash": "abc", "mode": "LIVE"}

    def pit(self, db=None, **kwargs):
        return {"query": "Q4", "rows": [{"relation_id": "rel:1"}],
                "count": 1, "as_of": None, "mode": "LIVE"}

    def exposure(self, db, holder, **kwargs):
        return {"query": "Q1", "holder": holder, "rows": [{"amount": 1}],
                "count": 1, "as_of": None, "mode": "LIVE"}

    def concentration(self, db, asset, **kwargs):
        return {"query": "Q7", "asset": asset, "rows": [], "count": 0,
                "counterparties": 0, "as_of": None, "mode": "LIVE"}

    def provenance(self, db, relation_id):
        return {"query": "Q6", "relation_id": relation_id,
                "rows": [{"ref_id": "event:9"}], "count": 1, "mode": "LIVE"}


class PanelsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="orvyren-ui-panels-")
        cls.evidence = os.path.join(cls.tmp, "evidence")
        os.makedirs(cls.evidence, exist_ok=True)
        cls.ctx = FakeCtx(cls.evidence)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestSourceResolution(PanelsFixture):
    def test_fixture_fallback_when_no_snapshot(self):
        payload = panels.panels_payload(self.ctx)
        self.assertEqual(payload["mode"], "FIXTURE")
        self.assertIn("maquette.json", payload["source"])
        self.assertEqual(sorted(payload["panels"]["graphe"]),
                         ["Q1", "Q4", "Q6", "Q7"])

    def test_replay_snapshot_wins_over_fixture(self):
        with open(os.path.join(self.evidence, "ui_snapshot.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(SNAPSHOT, handle)
        try:
            payload = panels.panels_payload(self.ctx)
            self.assertEqual(payload["mode"], "REPLAY")
            self.assertEqual(payload["source"], "evidence/ui_snapshot.json")
            self.assertEqual(payload["panels"]["situation"]["counts"]["events"],
                             15000)
            # Les clés minuscules du snapshot A sont bien lues.
            self.assertEqual(payload["panels"]["graphe"]["Q1"]["count"], 1)
            self.assertEqual(payload["panels"]["graphe"]["Q6"]["rows"][0]["ref_id"],
                             "event:1")
        finally:
            os.remove(os.path.join(self.evidence, "ui_snapshot.json"))

    def test_no_source_means_source_manquante_everywhere(self):
        payload = panels.panels_payload(self.ctx, maquette_path="n'existe/pas.json")
        self.assertIsNone(payload["mode"])
        for code in panels.QUERY_CODES:
            self.assertEqual(payload["panels"]["graphe"][code]["statut"],
                             panels.MISSING)
        self.assertEqual(payload["panels"]["decision"]["statut"], panels.MISSING)
        html_text = panels.build_html(payload)
        self.assertGreaterEqual(html_text.count("SOURCE MANQUANTE"), 6)

    def test_zero_rows_with_source_is_not_missing(self):
        block = {"query": "Q4", "rows": [], "count": 0,
                 "provenance": [{"ref": "x"}], "mode": "REPLAY"}
        html_text = panels.build_html({"banner": {}, "panels": {
            "situation": {"counts": {}, "statut": panels.MISSING},
            "graphe": {code: block for code in panels.QUERY_CODES},
            "decision": {"statut": panels.MISSING}}})
        self.assertIn("0 ligne (source présente", html_text)

    def test_live_mode_with_injected_api(self):
        saved = {key: os.environ.get(key) for key in
                 ("ORVYREN_UI_HOLDER", "ORVYREN_UI_ASSET", "ORVYREN_UI_RELATION")}
        os.environ["ORVYREN_UI_HOLDER"] = "addr:test:0xaaa"
        os.environ["ORVYREN_UI_ASSET"] = "debt:test:0xddd"
        os.environ["ORVYREN_UI_RELATION"] = "rel:1"
        try:
            payload = panels.panels_payload(self.ctx, live=True, api=FakeApi())
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(payload["mode"], "LIVE")
        self.assertEqual(payload["panels"]["situation"]["counts"]["relations"], 2)
        self.assertEqual(payload["panels"]["graphe"]["Q1"]["count"], 1)
        self.assertEqual(payload["panels"]["graphe"]["Q6"]["count"], 1)
        # Q7 existe mais renvoie zéro ligne : ce n'est PAS une source manquante.
        self.assertEqual(payload["panels"]["graphe"]["Q7"]["rows"], [])
        self.assertNotIn("statut", payload["panels"]["graphe"]["Q7"])


class TestHtmlContract(PanelsFixture):
    def test_banner_and_three_panels(self):
        payload = panels.panels_payload(self.ctx)
        html_text = panels.build_html(payload)
        for token in ("Situation", "Graphe", "Décision", "Q1", "Q4", "Q6", "Q7",
                      "mode=", "bloc=", "hash=", "âge="):
            self.assertIn(token, html_text)
        self.assertIn(payload["banner"]["mode"], ("FIXTURE", "REPLAY"))
        self.assertNotIn("RENDER ERROR", html_text)


class TestServerRoutes(PanelsFixture):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.httpd = ui_server.make_server(
            "127.0.0.1", 0, evidence_dir=cls.evidence, quiet=True)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=10)
        super().tearDownClass()

    def _get(self, path):
        with urllib.request.urlopen(
                "http://127.0.0.1:%d%s" % (self.port, path), timeout=15) as r:
            return r.status, r.read().decode("utf-8")

    def test_panels_route_renders(self):
        status, body = self._get("/panels")
        self.assertEqual(status, 200)
        self.assertIn("Situation", body)
        self.assertIn("Décision", body)

    def test_api_panels_route_returns_json(self):
        status, body = self._get("/api/panels")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["schema"], "orvyren/ui-panels/v1")
        self.assertEqual(sorted(payload["panels"]["graphe"]),
                         ["Q1", "Q4", "Q6", "Q7"])


if __name__ == "__main__":
    unittest.main()
