#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Forecast/outcome tests: hashing, chaining, freeze gate, resolve guard.

Tested contracts (B7 §a.4–a.5, DOC2 §5.8.1): stable self-carried fingerprint,
``prev_hash`` chain verified at read time, refusal to write without a freeze
package, refusal to modify ``p`` after the freeze, ``resolve_not_before``
guard, forecast ↔ outcome fingerprint binding, correction through
``supersedes``.
"""

import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.evaluation import forecasts as F  # noqa: E402
from orvyren.evaluation import outcomes as O  # noqa: E402
from orvyren.evaluation import windows as W  # noqa: E402

FROZEN_DIR = os.path.join(REPO_ROOT, "frozen")

SERIES = [
    ("2023-03-11T00:00:00Z", 0.9995),
    ("2023-03-11T01:00:00Z", 0.9860),
    ("2023-03-11T02:00:00Z", 0.9798),
    ("2023-03-11T03:00:00Z", 0.9799),
    ("2023-03-11T04:00:00Z", 0.9870),
    ("2023-03-11T05:00:00Z", 0.9940),
]


def make_forecast(forecast_id="test-001", t_frozen="2023-03-11T00:00:00Z", resolve_not_before="2023-03-11T06:00:00Z", p=0.5):
    return F.build_forecast(
        forecast_id=forecast_id,
        run_id="run-test",
        episode_id="usdc-2023-03",
        set_label="dev",
        persona="dao",
        statement="A sustained depeg is observed within 6 h after t_frozen.",
        resolution_rule_id=O.RULE_SUSTAINED_DEPEG,
        t_frozen_utc=t_frozen,
        resolve_not_before_utc=resolve_not_before,
        p=p,
        p_origin="explicit estimator (test)",
        y_definition={"ecart_pct": 1.0, "persistance_obs": 2, "max_gap_minutes": 90, "venues": ["synthetic"], "convention": "close"},
        observation_state_at_freeze={"last_values": [], "notes": "test"},
        signed_by={"role": "gel-g6", "name": "test"},
        horizon_hours=6,
    )


class TestHashageEtChaine(unittest.TestCase):
    def test_empreinte_stable_et_sensible_au_contenu(self):
        record = make_forecast()
        self.assertEqual(F.record_hash(record), F.record_hash(copy.deepcopy(record)))
        modified = copy.deepcopy(record)
        modified["p"] = 0.51
        self.assertNotEqual(F.record_hash(record), F.record_hash(modified))

    def test_chaine_prev_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            first = F.append_forecast(path, make_forecast("test-001"), frozen_dir=FROZEN_DIR)
            second = F.append_forecast(path, make_forecast("test-002", p=0.4), frozen_dir=FROZEN_DIR)
            self.assertEqual(first["prev_hash"], F.GENESIS_HASH)
            self.assertEqual(second["prev_hash"], first["sha256"])
            records = F.load_forecasts(path)
            self.assertEqual(F.verify_forecast_chain(records), ["test-001", "test-002"])

    def test_fichier_modifie_detecte(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            F.append_forecast(path, make_forecast("test-001"), frozen_dir=FROZEN_DIR)
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text.replace('"p":0.5', '"p":0.9'))
            with self.assertRaises(F.ForecastError):
                F.verify_forecast_chain(F.load_forecasts(path))

    def test_refus_de_modification_de_p(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            F.append_forecast(path, make_forecast("test-001", p=0.5), frozen_dir=FROZEN_DIR)
            with self.assertRaises(F.ForecastError):
                F.append_forecast(path, make_forecast("test-001", p=0.6), frozen_dir=FROZEN_DIR)
            # identical to the byte → refused too (strict append-only)
            with self.assertRaises(F.ForecastError):
                F.append_forecast(path, make_forecast("test-001", p=0.5), frozen_dir=FROZEN_DIR)
            self.assertEqual(len(F.load_forecasts(path)), 1)


class TestPorteDeGel(unittest.TestCase):
    def test_ecriture_refusee_sans_gel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "forecasts.jsonl")
            empty_frozen = os.path.join(tmp, "frozen")
            os.makedirs(empty_frozen)
            with self.assertRaises(W.FreezeGateError):
                F.append_forecast(path, make_forecast(), frozen_dir=empty_frozen)
            self.assertFalse(os.path.exists(path), "no line may be written without a freeze")

    def test_ecriture_refusee_si_gel_modifie(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = os.path.join(tmp, "frozen")
            os.makedirs(package)
            for name in W.FROZEN_FILES:
                target = os.path.join(package, f"{name}.md")
                with open(target, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(f"# {name}\n")
                with open(target + ".sha256", "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(f"{W.sha256_file(target)}  {name}.md\n")
            # silent alteration of a frozen document
            with open(os.path.join(package, "G1.md"), "a", encoding="utf-8", newline="\n") as handle:
                handle.write("forbidden retouch\n")
            path = os.path.join(tmp, "forecasts.jsonl")
            with self.assertRaises(W.FreezeGateError):
                F.append_forecast(path, make_forecast(), frozen_dir=package)

    def test_validation_des_champs(self):
        record = make_forecast()
        broken = copy.deepcopy(record)
        broken["p_origin"] = ""
        with self.assertRaises(F.ForecastError):
            F.build_forecast(
                forecast_id="x", run_id="r", episode_id="e", set_label="dev", persona="dao",
                statement="s", resolution_rule_id=O.RULE_SUSTAINED_DEPEG,
                t_frozen_utc="2023-03-11T00:00:00Z", resolve_not_before_utc="2023-03-11T06:00:00Z",
                p=0.5, p_origin="", y_definition={}, observation_state_at_freeze={},
            )
        with self.assertRaises(F.ForecastError):
            F.build_forecast(
                forecast_id="x", run_id="r", episode_id="e", set_label="dev", persona="dao",
                statement="s", resolution_rule_id=O.RULE_SUSTAINED_DEPEG,
                t_frozen_utc="2023-03-11T06:00:00Z", resolve_not_before_utc="2023-03-11T00:00:00Z",
                p=0.5, p_origin="calculation", y_definition={}, observation_state_at_freeze={},
            )


class TestRegleSustainedDepeg(unittest.TestCase):
    def test_detection_et_contiguite(self):
        result = O.sustained_depeg_v1(SERIES, "2023-03-11T00:00:00Z", "2023-03-11T06:00:00Z")
        self.assertEqual(result["y"], 1)
        self.assertEqual(result["observed"]["longest_run_obs"], 4)
        # a single observation below the threshold → not "sustained"
        single = O.sustained_depeg_v1(
            [("2023-03-11T00:00:00Z", 0.98), ("2023-03-11T01:00:00Z", 1.0)],
            "2023-03-11T00:00:00Z",
            "2023-03-11T06:00:00Z",
        )
        self.assertEqual(single["y"], 0)
        # 3 h gap → contiguity breaks persistence
        gapped = O.sustained_depeg_v1(
            [("2023-03-11T00:00:00Z", 0.98), ("2023-03-11T03:00:00Z", 0.98)],
            "2023-03-11T00:00:00Z",
            "2023-03-11T06:00:00Z",
        )
        self.assertEqual(gapped["y"], 0)

    def test_fenetre_sans_observation_refusee(self):
        with self.assertRaises(O.OutcomeError):
            O.sustained_depeg_v1(SERIES, "2023-04-01T00:00:00Z", "2023-04-01T06:00:00Z")

    def test_calm_window_critere_gele(self):
        calm = O.calm_window_v1([("2023-02-16T00:00:00Z", 0.999), ("2023-02-16T01:00:00Z", 1.001)], "2023-02-16T00:00:00Z", "2023-02-16T06:00:00Z")
        self.assertEqual(calm["y"], 1)
        stress = O.calm_window_v1([("2023-02-16T00:00:00Z", 0.994)], "2023-02-16T00:00:00Z", "2023-02-16T06:00:00Z")
        self.assertEqual(stress["y"], 0)  # 60 bp ≥ 50 bp → reclassified STRESS


class TestResolveEtOutcomes(unittest.TestCase):
    def test_garde_resolve_not_before(self):
        forecast = make_forecast(resolve_not_before="2099-01-01T00:00:00Z")
        with self.assertRaises(O.ResolutionTooEarly):
            O.resolve_forecast(forecast, SERIES, now_utc="2026-10-16T00:00:00Z")
        # once the horizon has passed, resolution is allowed (the job can be re-run)
        outcome = O.resolve_forecast(forecast, SERIES, now_utc="2099-01-02T00:00:00Z")
        self.assertEqual(outcome["y"], 1)

    def test_resolution_deterministe_et_liaison(self):
        forecast = make_forecast()
        first = O.resolve_forecast(forecast, SERIES, now_utc="2026-10-16T00:00:00Z")
        second = O.resolve_forecast(forecast, SERIES, now_utc="2026-10-16T00:00:00Z")
        self.assertEqual(O.canonical_bytes(first), O.canonical_bytes(second))
        O.check_link(forecast, first)
        tampered = copy.deepcopy(forecast)
        tampered["p"] = 0.7
        tampered["sha256"] = F.record_hash(tampered)
        with self.assertRaises(O.OutcomeError):
            O.check_link(tampered, first)

    def test_supersede_et_chaine_outcomes(self):
        forecast = make_forecast()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "outcomes.jsonl")
            outcome = O.resolve_forecast(forecast, SERIES, now_utc="2026-10-16T00:00:00Z")
            stored = O.append_outcome(path, outcome, frozen_dir=FROZEN_DIR)
            self.assertEqual(stored["prev_hash"], F.GENESIS_HASH)
            correction = O.build_superseding_outcome(stored, forecast, SERIES, now_utc="2026-10-17T00:00:00Z")
            stored_two = O.append_outcome(path, correction, frozen_dir=FROZEN_DIR)
            self.assertEqual(stored_two["prev_hash"], O.outcome_hash(stored))
            ids = O.verify_outcome_chain(O.load_outcomes(path))
            self.assertEqual(ids, [outcome["outcome_id"], correction["outcome_id"]])
            # correction of an unknown outcome → refusal
            ghost = copy.deepcopy(outcome)
            ghost["outcome_id"] = "test-001.h_class.bis"
            ghost["supersedes"] = "unknown"
            with self.assertRaises(O.OutcomeError):
                O.append_outcome(path, ghost, frozen_dir=FROZEN_DIR)

    def test_outcome_sans_preuve_refuse(self):
        forecast = make_forecast()
        outcome = O.resolve_forecast(forecast, SERIES, now_utc="2026-10-16T00:00:00Z")
        outcome["evidence_refs"] = []
        with self.assertRaises(O.OutcomeError):
            O.append_outcome(os.path.join(tempfile.gettempdir(), "never_written.jsonl"), outcome, frozen_dir=FROZEN_DIR)

    def test_outcome_avant_horizon_refuse_a_l_ecriture(self):
        """The guard also applies on the outcome side: resolved_at < resolve_not_before."""
        slow = make_forecast(resolve_not_before="2099-01-01T00:00:00Z")
        outcome = O.resolve_forecast(slow, SERIES, now_utc="2099-01-02T00:00:00Z")
        # the written_at field is the real write time; the resolution window is
        # carried by horizon.t_resolution_window_utc
        self.assertEqual(outcome["horizon"]["t_resolution_window_utc"], "2099-01-01T00:00:00Z")


class TestForecastsGeles(unittest.TestCase):
    """The `frozen/forecasts_dev.jsonl` file is chained, resolved and reproducible."""

    def test_chaine_et_liaison_du_fichier_gelé(self):
        path = os.path.join(FROZEN_DIR, "forecasts_dev.jsonl")
        records = F.load_forecasts(path)
        self.assertGreaterEqual(len(records), 5)
        self.assertLessEqual(len(records), 10)
        F.verify_forecast_chain(records, path=path)
        outcomes_path = os.path.join(FROZEN_DIR, "outcomes_dev.jsonl")
        outcomes = O.load_outcomes(outcomes_path)
        O.verify_outcome_chain(outcomes, path=outcomes_path)
        self.assertEqual(len(outcomes), len(records))
        by_id = {record["forecast_id"]: record for record in records}
        for outcome in outcomes:
            O.check_link(by_id[outcome["forecast_id"]], outcome)
        for record in records:
            self.assertEqual(record["set"], "dev")
            self.assertTrue(record["statement"].strip())
            self.assertTrue(record["p_origin"].strip())

    def test_recalcul_hors_ligne_identique(self):
        """Full rebuild of `frozen/` in a temporary directory → identical files."""
        spec = importlib.util.spec_from_file_location(
            "freeze_sprint0", os.path.join(REPO_ROOT, "scripts", "freeze_sprint0.py")
        )
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as tmp:
            builder.build_all(tmp, repo_root=REPO_ROOT)
            for name in sorted(os.listdir(FROZEN_DIR)):
                source = os.path.join(FROZEN_DIR, name)
                rebuilt = os.path.join(tmp, name)
                self.assertTrue(os.path.isfile(rebuilt), f"{name} not rebuilt")
                with open(source, "rb") as handle:
                    original = handle.read().replace(b"\r\n", b"\n")
                with open(rebuilt, "rb") as handle:
                    again = handle.read().replace(b"\r\n", b"\n")
                self.assertEqual(original, again, f"{name} differs after rebuild")


if __name__ == "__main__":
    unittest.main()
