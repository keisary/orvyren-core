#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — journal replay determinism test (W7, B1 §6.2).

Frozen criterion: **k = 10 journal replays ⇒ identical transcript hash**
(offline, no key, no network). Each replay lives in its own session; any
divergence breaks the criterion and the test fails.

Run: python -m pytest tests/test_replay_determinism.py -q
"""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.replay import journal as journal_mod  # noqa: E402
from orvyren.replay import corpus as corpus_mod  # noqa: E402

CASE = "usdc-2023-03"
INPUTS_PRESENT = os.path.isfile(os.path.join(ROOT, "fixtures", "agents", CASE,
                                             "run_inputs.json"))
K_REPLAYS = 10


@unittest.skipUnless(INPUTS_PRESENT, "agent fixtures absent")
class ReplayDeterminismTest(unittest.TestCase):
    def test_k10_identical_transcript_hashes(self):
        work_root = tempfile.mkdtemp(prefix="orvyren_replay_k10_")
        self.addCleanup(shutil.rmtree, work_root, True)
        report = journal_mod.replay_k(CASE, work_root, k=K_REPLAYS, quiet=True)
        self.assertEqual(report["k"], K_REPLAYS)
        self.assertEqual(len(report["hashes"]), K_REPLAYS)
        self.assertTrue(report["identical"],
                        "divergent hashes over k=%d: %s" % (K_REPLAYS,
                                                            sorted(set(report["hashes"]))))
        self.assertEqual(len(set(report["hashes"])), 1)

    def test_replay_k_rejects_invalid_k(self):
        with self.assertRaises(journal_mod.ReplayJournalError):
            journal_mod.replay_k(CASE, tempfile.mkdtemp(prefix="orvyren_replay_bad_"), k=0)

    def test_episode_payload_must_be_an_object(self):
        handle, path = tempfile.mkstemp(prefix="orvyren_episode_", suffix=".json")
        os.close(handle)
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as output:
                output.write("[1, 2, 3]")
            with self.assertRaises(corpus_mod.CorpusError):
                corpus_mod.series_from_episode(path)
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
