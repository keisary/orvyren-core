# -*- coding: utf-8 -*-
"""Review deep — src/orvyren/ui/ + src/orvyren/audit/ (2026-10-17).

Locks the fixes from the deep review:

* readers accept a missing source path (``None``) without raising — screen 1
  used to render ``RENDER ERROR`` when the replay journal was absent;
* no literal ``None`` leaks into rendered screens (JSON nulls render ``—``);
* screen 3 renders the RDOF trace fields the dossier actually carries
  (``iteration``/``question``/``chosen_name``/``verdicts_after``), not the
  wrong ``step``/``kind``/``verdict``/``note`` keys that produced blank cells;
* the panels banner never displays another source's values (REPLAY page must
  not fall back to the maquette's banner);
* the ``/api/dossier`` case token can not path-traverse out of the evidence
  directory;
* the dossier self-hash field is the last 64-zero run, so 64 zeros inside
  hashed input data can not hijack the substitution.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "src"))

from orvyren.audit import dossier as dossier_mod  # noqa: E402
from orvyren.ui import panels  # noqa: E402
from orvyren.ui import screens  # noqa: E402
from orvyren.ui import server as ui_server  # noqa: E402


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


class _Ctx:
    def __init__(self, evidence_dir):
        self.evidence_dir = evidence_dir

    def evidence_path(self, *parts):
        return os.path.join(self.evidence_dir, *parts)


class TestReadersNeverRaise(unittest.TestCase):
    def test_missing_source_path_returns_none(self):
        self.assertIsNone(screens._read_json(None))
        self.assertIsNone(screens._read_jsonl(None))
        self.assertIsNone(screens._read_json("n'existe/pas.json"))

    def test_screen_1_without_replay_journal_renders_honestly(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ctx = screens.Ctx(_ROOT, tmp)
        body = screens.build_screen(1, ctx).decode("utf-8")
        self.assertNotIn("RENDER ERROR", body)
        self.assertIn("SOURCE MISSING", body)
        self.assertIn("MODE:", body)


class TestNoNoneLeaks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ctx = screens.Ctx(_ROOT, self.tmp)
        _write_json(os.path.join(self.tmp, "decision_record_usdc-2023-03.json"), {
            "case": None,
            "hypotheses_registry": {"ids": ["H1"], "etats": [None]},
            "rdof": {
                "stop": None,
                "stop_rule": None,
                "dominant_final": None,
                "trace": [{"iteration": 1, "question": None,
                           "verdicts_after": {"H1": None}}],
            },
        })

    def test_esc_renders_none_as_dash(self):
        self.assertEqual(screens._esc(None), "—")

    def test_screen_3_shows_no_literal_none(self):
        body = screens.build_screen(3, self.ctx).decode("utf-8")
        self.assertNotIn("RENDER ERROR", body)
        self.assertNotIn("None", body)
        self.assertIn("—", body)


class TestRdofTraceFields(unittest.TestCase):
    def test_trace_uses_the_record_keys(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ctx = screens.Ctx(_ROOT, tmp)
        _write_json(os.path.join(tmp, "decision_record_usdc-2023-03.json"), {
            "case": "trace-case",
            "rdof": {"dominant_final": "H2", "stop": "STOPVAL", "stop_rule": "RULEVAL",
                     "trace": [{"iteration": 7, "question": "QUESTIONVAL",
                                "chosen_name": "CHOSENNAMEVAL",
                                "verdicts_after": {"H2": "SUPPORTED"}}]},
        })
        body = screens.build_screen(3, ctx).decode("utf-8")
        for token in ("QUESTIONVAL", "CHOSENNAMEVAL", "SUPPORTED", "STOPVAL",
                      "RULEVAL", "H2"):
            self.assertIn(token, body, token)
        # No blank trace row: every slot of the single step is filled.
        self.assertNotIn("<td></td><td></td><td></td><td></td>", body)

    def test_unknown_trace_shape_falls_back_to_raw_step(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        ctx = screens.Ctx(_ROOT, tmp)
        _write_json(os.path.join(tmp, "decision_record_usdc-2023-03.json"), {
            "case": "trace-case",
            "rdof": {"trace": [{"autre_champ": "RAWSTEPVAL"}]},
        })
        body = screens.build_screen(3, ctx).decode("utf-8")
        self.assertIn("RAWSTEPVAL", body)


class TestPanelsBannerStaysOnSource(unittest.TestCase):
    def test_replay_banner_never_borrows_fixture_values(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        evidence = os.path.join(tmp, "evidence")
        os.makedirs(evidence, exist_ok=True)
        _write_json(os.path.join(evidence, "ui_snapshot.json"),
                    {"schema": "orvyren-ui-snapshot/v1", "counts": {"nodes": 1},
                     "q1": {"query": "Q1", "rows": [], "count": 0, "mode": "REPLAY"}})
        fixture_path = os.path.join(tmp, "maquette.json")
        _write_json(fixture_path, {
            "banner": {"mode": "REPLAY", "as_of": "FIXTURE-AS-OF",
                       "as_of_block": "FIXTURE-BLOCK",
                       "graph_hash": "FIXTURE-HASH", "age": "FIXTURE-AGE"},
            "panels": {"situation": {}, "graphe": {}, "decision": {"statut": "SOURCE MANQUANTE"}},
        })
        payload = panels.panels_payload(_Ctx(evidence), maquette_path=fixture_path)
        self.assertEqual(payload["mode"], "REPLAY")
        self.assertEqual(payload["banner"]["graph_hash"], panels.MISSING)
        self.assertEqual(payload["banner"]["as_of"], panels.MISSING)
        self.assertEqual(payload["banner"]["as_of_block"], panels.MISSING)
        self.assertEqual(payload["banner"]["data_mode"], panels.MISSING)
        html_text = panels.build_html(payload)
        for leaked in ("FIXTURE-HASH", "FIXTURE-AS-OF", "FIXTURE-BLOCK", "FIXTURE-AGE"):
            self.assertNotIn(leaked, html_text, leaked)

    def test_data_mode_prefers_the_data_stamp(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        evidence = os.path.join(tmp, "evidence")
        os.makedirs(evidence, exist_ok=True)
        _write_json(os.path.join(evidence, "ui_snapshot.json"),
                    {"schema": "orvyren-ui-snapshot/v1", "mode": "LIVE",
                     "counts": {"nodes": 1}})
        payload = panels.panels_payload(_Ctx(evidence), maquette_path="n'existe/pas.json")
        self.assertEqual(payload["banner"]["data_mode"], "LIVE")


class TestCaseTokenSanitised(unittest.TestCase):
    def test_traversal_tokens_stay_inside_the_evidence_dir(self):
        token = ui_server._safe_case_token("../../../Windows/win.ini")
        self.assertNotIn("/", token)
        self.assertNotIn("\\", token)
        self.assertNotIn("..", token)
        self.assertEqual(token, "win.ini")
        self.assertEqual(ui_server._safe_case_token("..\\..\\secret"), "secret")
        self.assertEqual(ui_server._safe_case_token("usdc-2023-03"), "usdc-2023-03")
        self.assertEqual(ui_server._safe_case_token(""), "unknown")


class TestSelfHashField(unittest.TestCase):
    def test_zero_run_in_input_data_cannot_hijack_the_self_hash(self):
        tmp = tempfile.mkdtemp(prefix="orvyren-review-")
        self.addCleanup(shutil.rmtree, tmp, True)
        zero_run = "0" * 64
        decision_path = os.path.join(tmp, "decision_hashcase.json")
        _write_json(decision_path, {
            "case": "hashcase",
            "window": {"start": "2023-03-01", "end": "2023-03-31"},
            "decision": {"verdict": "INCONCLUSIVE",
                         "rationale": ["embedded zero run: %s" % zero_run],
                         "provenance": ["prov-1"], "limits": ["lim-1"]},
            "hypothesis_verdicts": {"H1": {"verdict": "REFUTED", "evidence_refs": ["r1"]}},
        })
        out_dir = os.path.join(tmp, "out")
        result = dossier_mod.build(decision_path, out_dir,
                                   generated_at="2026-10-17T00:00:00Z")
        for key, path in (("sha256", result["md_path"]),
                          ("sha256_html", result["html_path"])):
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            # The input data's zero run is preserved verbatim.
            self.assertIn("embedded zero run: %s" % zero_run, text)
            # The self-hash field carries the hash, and zeroing exactly that
            # field reproduces the recorded self-hash.
            self.assertIn(result[key], text)
            zeroed = text.replace(result[key], zero_run, 1)
            recomputed = hashlib.sha256(zeroed.encode("utf-8")).hexdigest()
            self.assertEqual(recomputed, result[key], path)


if __name__ == "__main__":
    unittest.main()
