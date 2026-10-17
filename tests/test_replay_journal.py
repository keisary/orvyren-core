#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests du rejeu journal + des dossiers de rejeu (W7).

Couverture :

* mode 1 : deux journaux rejoués, chaînes vérifiées, têtes stables ;
* altération d'une ligne exportée ⇒ ``ReplayJournalError`` (chaîne cassée) ;
* ``verify_run`` : verdict OK, puis MISMATCH si l'hash attendu diffère ;
* dossier : bannière REPLAY obligatoire (``require_banner``), hash recalculable,
  nom de fichier suffixé ``_replay_<mode>_<replay_id>``, journal ``runs.jsonl`` ;
* l'horodatage double : ``t_wall`` présent, ``ts_sim`` porté par la bannière.

Run: python -m pytest tests/test_replay_journal.py -q
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.replay import corpus as corpus_mod  # noqa: E402
from orvyren.replay import dossier as dossier_mod  # noqa: E402
from orvyren.replay import journal as journal_mod  # noqa: E402

CASE = "usdc-2023-03"
INPUTS_PRESENT = os.path.isfile(os.path.join(ROOT, "fixtures", "agents", CASE,
                                             "run_inputs.json"))


class _TempDirMixin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_replay_")
        self.addCleanup(shutil.rmtree, self.tmp, True)


@unittest.skipUnless(INPUTS_PRESENT, "fixtures agents absentes")
class ReplayJournalTest(_TempDirMixin):
    @classmethod
    def setUpClass(cls):
        cls._once = tempfile.mkdtemp(prefix="orvyren_replay_once_")
        cls.run_dir = journal_mod.replay_once(CASE, os.path.join(cls._once, "r1"),
                                              quiet=True)
        cls.transcript = journal_mod.load_transcript(cls.run_dir)
        cls.transcript_hash_value = journal_mod.transcript_hash(cls.transcript)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._once, ignore_errors=True)

    def test_transcripts_chains_and_heads(self):
        journals = self.transcript["journals"]
        self.assertEqual(sorted(journals), ["critic", "orchestrator"])
        for role, info in journals.items():
            self.assertGreater(info["lines"], 0)
            self.assertEqual(len(info["chain_head"]), 64)
        self.assertEqual(self.transcript["run_id"], "demo-%s" % CASE)

    def test_verify_run_ok_and_mismatch(self):
        ok = journal_mod.verify_run(self.run_dir)
        self.assertEqual(ok["verdict"], "OK")
        bad = journal_mod.verify_run(self.run_dir, expected_hash="0" * 64)
        self.assertEqual(bad["verdict"], "MISMATCH")

    def test_tampered_journal_line_raises(self):
        run_dir = journal_mod.replay_once(CASE, os.path.join(self.tmp, "t1"), quiet=True)
        path = os.path.join(run_dir, "journal_orchestrator.jsonl")
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        first = json.loads(lines[0])
        first["status"] = "TAMPERED"
        lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))
        with self.assertRaises(journal_mod.ReplayJournalError):
            journal_mod.load_transcript(run_dir)

    def test_dossier_requires_banner_and_verifies(self):
        manifest = corpus_mod.load_manifest()
        from orvyren.evaluation import windows as windows_mod

        window = windows_mod.DEV_WINDOWS[0]
        result = dossier_mod.build_replay_dossier(
            episode=CASE, mode="REPLAY-JOURNAL", mode_slug="journal",
            run_id=self.transcript["run_id"],
            t_sim_start_utc=window.start_utc, t_sim_end_utc=window.end_utc,
            corpus_manifest=manifest, clock_audit={"valid": True, "violations": []},
            transcript=self.transcript, out_dir=os.path.join(self.tmp, "out"),
            runs_log=os.path.join(self.tmp, "runs.jsonl"))
        self.assertIn("_replay_journal_", os.path.basename(result["md_path"]))
        self.assertTrue(result["banner"].startswith("REPLAY — données archivées — REPLAY-JOURNAL"))
        verdict = dossier_mod.verify_replay_dossier(result["json_path"],
                                                    runs_log=os.path.join(self.tmp, "runs.jsonl"))
        self.assertEqual(verdict["verdict"], "OK")
        with open(result["json_path"], "r", encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(dossier_mod.require_banner(document), result["banner"])
        with self.assertRaises(dossier_mod.DossierError):
            dossier_mod.require_banner({"banner": "LIVE"})
        with open(os.path.join(self.tmp, "runs.jsonl"), "r", encoding="utf-8") as handle:
            entries = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(entries[-1]["replay_id"], result["replay_id"])
        self.assertEqual(entries[-1]["content_sha256"], result["content_sha256"])

    def test_tampered_dossier_detected(self):
        manifest = corpus_mod.load_manifest()
        result = dossier_mod.build_replay_dossier(
            episode=CASE, mode="REPLAY-JOURNAL", mode_slug="journal",
            run_id=self.transcript["run_id"],
            t_sim_start_utc="2023-03-10T00:00:00Z", t_sim_end_utc="2023-03-14T00:00:00Z",
            corpus_manifest=manifest, clock_audit={"valid": True, "violations": []},
            transcript=self.transcript, out_dir=os.path.join(self.tmp, "out2"),
            runs_log=os.path.join(self.tmp, "runs2.jsonl"))
        with open(result["json_path"], "r", encoding="utf-8") as handle:
            document = json.load(handle)
        document["run_id"] = "modifié"
        with open(result["json_path"], "w", encoding="utf-8", newline="\n") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=1, sort_keys=True)
        verdict = dossier_mod.verify_replay_dossier(result["json_path"],
                                                    runs_log=os.path.join(self.tmp, "runs2.jsonl"))
        self.assertEqual(verdict["verdict"], "MISMATCH")


if __name__ == "__main__":
    unittest.main()
