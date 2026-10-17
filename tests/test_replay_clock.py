#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests de l'horloge de rejeu (W7, B7 §c.3).

Monotonie stricte, pas borné par la fin de fenêtre, avance par événements,
et surtout la **garde PIT** : admettre un objet futur abandonne le run
(``PITViolation``) et l'incident est écrit dans l'audit — test obligatoire.

Run: python -m pytest tests/test_replay_clock.py -q
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.replay import clock as clock_mod  # noqa: E402


class ReplayClockTest(unittest.TestCase):
    def _clock(self, **kwargs):
        return clock_mod.ReplayClock(t_sim_start_utc="2023-03-10T00:00:00Z",
                                     t_sim_end_utc="2023-03-12T00:00:00Z",
                                     run_id="test", **kwargs)

    def test_monotone_advance_and_end_cap(self):
        clock = self._clock(step_hours=1)
        t0 = clock.t_sim_iso()
        self.assertEqual(t0, "2023-03-10T00:00:00Z")
        self.assertEqual(clock.advance(), "2023-03-10T01:00:00Z")
        self.assertEqual(clock.advance(hours=47), "2023-03-12T00:00:00Z")
        with self.assertRaises(ValueError):  # déjà à la fin
            clock.advance()

    def test_step_to_next_event(self):
        clock = self._clock(step_hours=1)
        events = ["2023-03-09T22:00:00Z", "2023-03-10T03:00:00Z", "2023-03-10T01:30:00Z"]
        self.assertEqual(clock.step_to_next(events), "2023-03-10T01:30:00Z")
        self.assertEqual(clock.step_to_next(events), "2023-03-10T03:00:00Z")
        self.assertIsNone(clock.step_to_next(events))
        self.assertEqual(clock.step_index, 2)

    def test_pit_violation_aborts_and_is_audited(self):
        clock = self._clock()
        clock.advance()  # t_sim = 01:00
        clock.admit("2023-03-10T00:30:00Z", what="observation passée")  # admis
        with self.assertRaises(clock_mod.PITViolation):
            clock.admit("2023-03-10T02:00:00Z", what="observation future")
        audit = clock.audit()
        self.assertFalse(audit["valid"])
        self.assertEqual(len(audit["violations"]), 1)
        self.assertEqual(audit["violations"][0]["kind"], "PIT_VIOLATION")
        self.assertEqual(audit["violations"][0]["event_time_utc"], "2023-03-10T02:00:00Z")

    def test_admissible_flag(self):
        clock = self._clock()
        self.assertTrue(clock.admissible("2023-03-09T23:59:00Z"))
        self.assertTrue(clock.admissible("2023-03-10T00:00:00Z"))
        self.assertFalse(clock.admissible("2023-03-10T00:00:01Z"))

    def test_from_window_applies_init_band(self):
        from orvyren.evaluation import windows as windows_mod

        window = windows_mod.DEV_WINDOWS[0]
        clock = clock_mod.ReplayClock.from_window(window, run_id="t", init_band_hours=24)
        self.assertEqual(clock.t_sim_iso(), "2023-03-09T00:00:00Z")  # ouverture − 24 h
        self.assertEqual(clock.window()["t_sim_end_utc"], window.end_utc)
        clock_zero = clock_mod.ReplayClock.from_window(window, run_id="t", init_band_hours=0)
        self.assertEqual(clock_zero.t_sim_iso(), window.start_utc)


if __name__ == "__main__":
    unittest.main()
