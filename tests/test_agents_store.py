#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: ``agents.store`` — immutable content-addressed store (L2.6).

Covers the REPLAY-JOURNAL ground (DOC4 L2.6 / DOC2 §5.2.2): the store is
immutable (``E_STORE_IMMUTABLE`` on a conflicting rewrite), the prompt hash
is stable (k=10 identical recomputations), call lines are append-only JSONL,
``verify()`` recomputes every blob (a tampered response, a rewritten prompt or
an orphaned blob is caught) and recorded answers are replayed identically.

Execution: ``python -m pytest tests/test_agents_store.py -q``
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.agents import contracts  # noqa: E402
from orvyren.agents.store import ResponseStore, response_hash  # noqa: E402

ROLE = "orchestrator"
ROLE_VERSION = "orch-p1.0.0"
SCHEMA_ID = "orvyren/orch/v1"
SYSTEM_PROMPT = "SYSTÈME — orchestrateur (test)"
PAYLOAD = {"snapshot_at": "2023-03-12T00:00:00Z", "lacunes": [{"id": "L1"}]}
RAW = contracts.canonical_json(
    {"$schema": "orvyren/orch/v1", "stop": True, "motif_stop": "rien à chercher",
     "lacune_id": "L1", "tache": None, "non_recherche": []})


def call_line(prompt_hash, resp_hash, **overrides):
    entry = {
        "record_id": "rec-" + prompt_hash[:12],
        "prompt_hash": prompt_hash,
        "response_hash": resp_hash,
        "role": ROLE,
        "role_version": ROLE_VERSION,
        "schema_id": SCHEMA_ID,
        "ts_utc": "2026-10-16T00:00:00Z",
    }
    entry.update(overrides)
    return entry


class StoreTest(unittest.TestCase):
    """Immutability, addressing, call log and verification."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = ResponseStore(self._tmp.name)

    def seed(self):
        """A consistent store: prompt blob + response blob + call line."""
        p_hash = self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                        SYSTEM_PROMPT, PAYLOAD)
        r_hash = response_hash(RAW)
        self.store.save_prompt(p_hash, SYSTEM_PROMPT, PAYLOAD)
        self.store.save_response(r_hash, RAW)
        self.store.record_call(call_line(p_hash, r_hash))
        return p_hash, r_hash

    # -- addressing ---------------------------------------------------------
    def test_prompt_hash_is_stable_and_input_sensitive(self):
        hashes = {self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                         SYSTEM_PROMPT, PAYLOAD)
                  for _ in range(10)}
        self.assertEqual(len(hashes), 1, msg=f"k=10 replay hashes: {hashes}")
        digest = next(iter(hashes))
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, digest.lower())
        for changed in (
                self.store.hash_prompt(ROLE, "orch-p1.0.1", SCHEMA_ID, SYSTEM_PROMPT, PAYLOAD),
                self.store.hash_prompt("critic", ROLE_VERSION, SCHEMA_ID, SYSTEM_PROMPT, PAYLOAD),
                self.store.hash_prompt(ROLE, ROLE_VERSION, "orvyren/crit/v1", SYSTEM_PROMPT, PAYLOAD),
                self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID, SYSTEM_PROMPT + " !", PAYLOAD),
                self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID, SYSTEM_PROMPT,
                                       {"snapshot_at": "autre"})):
            self.assertNotEqual(digest, changed, msg="hash must pin every input")

    def test_recorded_prompt_hash_is_reproducible_on_a_cold_store(self):
        _, r_hash = self.seed()
        other = ResponseStore(self._tmp.name)
        recomputed = other.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                       SYSTEM_PROMPT, PAYLOAD)
        self.assertEqual(self.store.find_call(recomputed)["response_hash"], r_hash)

    # -- immutability -------------------------------------------------------
    def test_conflicting_prompt_rewrite_raises_E_STORE_IMMUTABLE(self):
        p_hash = self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                        SYSTEM_PROMPT, PAYLOAD)
        self.store.save_prompt(p_hash, SYSTEM_PROMPT, PAYLOAD)
        self.store.save_prompt(p_hash, SYSTEM_PROMPT, PAYLOAD)  # identical: no-op
        with self.assertRaises(ValueError) as caught:
            self.store.save_prompt(p_hash, SYSTEM_PROMPT, {"autre": "payload"})
        self.assertIn("E_STORE_IMMUTABLE", str(caught.exception))

    def test_conflicting_response_rewrite_raises_E_STORE_IMMUTABLE(self):
        r_hash = response_hash(RAW)
        self.store.save_response(r_hash, RAW)
        self.store.save_response(r_hash, RAW)
        with self.assertRaises(ValueError) as caught:
            self.store.save_response(r_hash, "réponse réécrite en secret")
        self.assertIn("E_STORE_IMMUTABLE", str(caught.exception))

    def test_no_update_and_no_delete_api(self):
        for forbidden in ("update", "delete", "remove", "pop", "clear"):
            self.assertFalse(hasattr(self.store, forbidden), forbidden)

    # -- call log -----------------------------------------------------------
    def test_record_call_appends_one_jsonl_line_per_call(self):
        p_hash, r_hash = self.seed()
        self.store.record_call(call_line(p_hash, r_hash, record_id="rec-2"))
        lines = [l for l in self.store.calls_path.read_bytes().decode("utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            entry = json.loads(line)
            for field in ("record_id", "prompt_hash", "response_hash", "role",
                          "role_version", "schema_id", "ts_utc"):
                self.assertIn(field, entry)

    def test_find_call_returns_none_then_the_last_entry(self):
        p_hash, r_hash = self.seed()
        self.assertIsNone(self.store.find_call("0" * 64))
        self.store.record_call(call_line(p_hash, r_hash, record_id="rec-2"))
        self.assertEqual(self.store.find_call(p_hash)["record_id"], "rec-2")

    def test_record_call_rejects_incomplete_entries(self):
        with self.assertRaises(ValueError) as caught:
            self.store.record_call({"record_id": "rec-x", "prompt_hash": "a" * 64})
        self.assertIn("E_STORE_CALL_INCOMPLETE", str(caught.exception))

    def test_get_response_round_trips_and_reports_missing_blobs(self):
        _, r_hash = self.seed()
        self.assertEqual(self.store.get_response(r_hash), RAW)
        with self.assertRaises(FileNotFoundError) as caught:
            self.store.get_response("f" * 64)
        self.assertIn("E_STORE_MISSING_BLOB", str(caught.exception))

    # -- verification -------------------------------------------------------
    def test_verify_accepts_a_consistent_store(self):
        self.seed()
        ok, problems = self.store.verify()
        self.assertTrue(ok, msg=f"problems: {problems}")
        self.assertEqual(problems, [])

    def test_verify_detects_a_tampered_response_blob(self):
        _, r_hash = self.seed()
        self.store.blob_path(r_hash).write_bytes(b"{\"stop\": true}")
        ok, problems = self.store.verify()
        self.assertFalse(ok)
        self.assertEqual(len(problems), 1, msg=f"problems: {problems}")
        self.assertIn(r_hash, problems[0])

    def test_verify_detects_a_rewritten_prompt_blob(self):
        p_hash, _ = self.seed()
        rewritten = contracts.canonical_json(
            {"payload": {"autre": True}, "system_prompt": SYSTEM_PROMPT})
        self.store.blob_path(p_hash).write_bytes(rewritten.encode("utf-8"))
        ok, problems = self.store.verify()
        self.assertFalse(ok)
        self.assertTrue(any(p_hash in p for p in problems), msg=f"problems: {problems}")

    def test_verify_detects_an_orphan_prompt_blob(self):
        orphan = self.store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                        SYSTEM_PROMPT, {"sans": "appel"})
        self.store.save_prompt(orphan, SYSTEM_PROMPT, {"sans": "appel"})
        ok, problems = self.store.verify()
        self.assertFalse(ok)
        self.assertTrue(any(orphan in p for p in problems), msg=f"problems: {problems}")

    def test_verify_detects_a_bad_blob_name(self):
        (self.store.blobs_dir / "pas-un-hash.txt").write_bytes(b"x")
        ok, problems = self.store.verify()
        self.assertFalse(ok)
        self.assertTrue(any("bad blob name" in p for p in problems), msg=f"{problems}")

    def test_calls_view_is_pure(self):
        self.seed()
        before = self.store.calls_path.read_bytes()
        self.store.calls()
        self.store.find_call("0" * 64)
        self.store.verify()
        self.assertEqual(self.store.calls_path.read_bytes(), before)


class ReplayInvariantTest(unittest.TestCase):
    """The recorded answer is the ground truth: k=10 identical replays."""

    def test_recorded_payload_replays_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ResponseStore(tmp)
            p_hash = store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                       SYSTEM_PROMPT, PAYLOAD)
            r_hash = response_hash(RAW)
            store.save_prompt(p_hash, SYSTEM_PROMPT, PAYLOAD)
            store.save_response(r_hash, RAW)
            store.record_call(call_line(p_hash, r_hash))
            raws = {store.get_response(store.find_call(
                store.hash_prompt(ROLE, ROLE_VERSION, SCHEMA_ID,
                                  SYSTEM_PROMPT, PAYLOAD))["response_hash"])
                for _ in range(10)}
            self.assertEqual(raws, {RAW})
            self.assertEqual(hashlib.sha256(RAW.encode("utf-8")).hexdigest(), r_hash)


if __name__ == "__main__":
    unittest.main()
