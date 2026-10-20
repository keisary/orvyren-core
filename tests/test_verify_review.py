#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — revue ciblée verify/replay/branches : tests de régression.

Chaque test épingle un défaut réel trouvé à la revue du 2026-10-17 puis corrigé
(détails : D:/orvyren_10h_2026-10-17/review/verify_replay_branches.md) :

* A1 — tête de chaîne du manifest non assertée pour graph/agent, jonction
  LINK/SEAL sautée sans count pour exec ;
* A2 — zeroing du self-hash à la première occurrence au lieu du champ self ;
* A4 — `_REPO_ROOT` du module dossier non restauré ;
* A5 — coercions numériques de la politique non gardées (crash au lieu d'un
  échec nommé) ;
* A7 — fenêtre absente (TypeError) et supply à zéro (ZeroDivisionError) ;
* A8 — `data` de log illisible (ValueError) ;
* C2 — `refs: null` (AttributeError) ;
* replay/clock — `step_to_next` dragué jusqu'à la fin de fenêtre par un
  événement hors fenêtre ;
* replay/corpus — ancre de bloc `true` (bool) acceptée ; entrée de manifest
  sans `path` (TypeError) ;
* replay/dossier — ligne corrompue de runs.jsonl qui abort la vérification T10 ;
* replay/journal — run_outcome.json corrompu → JSONDecodeError au lieu de
  ReplayJournalError ;
* branches — champs `null` → AttributeError au lieu des codes E_HYP_* ;
  ids dupliqués au load_jsonl écrasés silencieusement.

Run: python -m pytest tests/test_verify_review.py -q
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.verify import engine as engine_mod  # noqa: E402
from orvyren.replay import clock as clock_mod  # noqa: E402
from orvyren.replay import corpus as corpus_mod  # noqa: E402
from orvyren.replay import dossier as dossier_mod  # noqa: E402
from orvyren.replay import journal as journal_mod  # noqa: E402
from orvyren.branches import hypotheses as hyp_mod  # noqa: E402


def _chain(stream, kinds_and_payloads):
    """Build a valid chained JSONL stream with the engine's own hash rule."""
    prev = engine_mod.GENESIS
    records = []
    for seq, (kind, payload) in enumerate(kinds_and_payloads, 1):
        record = {"v": 1, "stream": stream, "seq": seq, "kind": kind,
                  "payload": payload, "refs": {}, "prev_hash": prev}
        body = {key: value for key, value in record.items() if key != "record_hash"}
        prev = engine_mod.sha256_hex(engine_mod.canonical_json(body).encode("utf-8"))
        record["record_hash"] = prev
        records.append(record)
    return records


class _TempRootTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="orvyren_review_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path) or self.root, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path

    def write_jsonl(self, rel, records):
        return self.write(rel, "".join(engine_mod.canonical_json(r) + "\n" for r in records))


class A1ChainHeadTest(_TempRootTest):
    """Le head_hash du manifest doit être asserté pour tout flux présent."""

    def _manifest(self, graph_head, records=2):
        return {"streams": {
            "exec": {"present": False, "reason": "n/a"},
            "agent": {"present": False, "reason": "n/a"},
            "graph": {"present": True, "path": "graph.jsonl",
                      "records": records, "head_hash": graph_head}}}

    def test_a1_graph_head_mismatch_detected(self):
        # A stream rewritten end-to-end (valid recomputed hashes, same length)
        # must fail on the manifest head — the gap found at review.
        recs = _chain("graph", [("INSERT", {"rel": "A"}), ("INSERT", {"rel": "B"})])
        self.write_jsonl("graph.jsonl", recs)
        good = engine_mod.check_a1_chains(self.root, self._manifest(recs[-1]["record_hash"]))
        self.assertTrue([c for c in good if c["id"] == "A1.graph.chain"][0]["ok"])
        forged = engine_mod.check_a1_chains(self.root, self._manifest("f" * 64))
        check = [c for c in forged if c["id"] == "A1.graph.chain"][0]
        self.assertFalse(check["ok"])
        self.assertIn("head_hash", str(check["detail"].get("reason")))

    def test_a1_agent_count_and_head(self):
        recs = _chain("agent", [("STEP", {"n": 1}), ("STEP", {"n": 2})])
        self.write_jsonl("agent.jsonl", recs)
        manifest = {"streams": {
            "exec": {"present": False, "reason": "n/a"},
            "graph": {"present": False, "reason": "n/a"},
            "agent": {"present": True, "path": "agent.jsonl",
                      "records": 3, "head_hash": recs[-1]["record_hash"]}}}
        checks = engine_mod.check_a1_chains(self.root, manifest)
        check = [c for c in checks if c["id"] == "A1.agent.chain"][0]
        self.assertFalse(check["ok"], "count mismatch must be detected")
        manifest["streams"]["agent"]["records"] = 2
        manifest["streams"]["agent"]["head_hash"] = "0" * 64
        checks = engine_mod.check_a1_chains(self.root, manifest)
        check = [c for c in checks if c["id"] == "A1.agent.chain"][0]
        self.assertFalse(check["ok"], "head mismatch must be detected")

    def test_a1_exec_without_count_fails(self):
        recs = _chain("exec", [("OBS", {"n": 1})])
        self.write_jsonl("audit.jsonl", recs)
        manifest = {"streams": {
            "graph": {"present": False, "reason": "n/a"},
            "agent": {"present": False, "reason": "n/a"},
            "exec": {"present": True, "path": "audit.jsonl",
                     "head_hash": recs[-1]["record_hash"]}}}  # no records count
        checks = engine_mod.check_a1_chains(self.root, manifest)
        check = [c for c in checks if c["id"] == "A1.exec.chain"][0]
        self.assertFalse(check["ok"], "junction unverifiable => never a silent pass")
        self.assertIn("junction", str(check["detail"].get("reason")))


class A2SelfHashPositionTest(unittest.TestCase):
    def test_a2_self_hash_zeroes_the_row_position(self):
        # The declared hash appears EARLIER in the file: zeroing must hit the
        # self row (positional), not the first textual occurrence.
        fake = "ab" * 32
        text = ("table | `%s` |\n" % fake
                + "dossier (self, md) | dossier_x.md | `%s` |\n" % fake)
        path = tempfile.mkdtemp(prefix="orvyren_selfhash_")
        self.addCleanup(shutil.rmtree, path, True)
        target = os.path.join(path, "dossier_x.md")
        with open(target, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        row = text.rindex(fake)
        positional = text[:row] + engine_mod.GENESIS + text[row + 64:]
        first = text.replace(fake, engine_mod.GENESIS, 1)
        expected = engine_mod.sha256_hex(positional.encode("utf-8"))
        wrong = engine_mod.sha256_hex(first.encode("utf-8"))
        self.assertNotEqual(expected, wrong, "the two rules must differ here")
        result = engine_mod.recompute_self_hash(target, engine_mod._MD_SELF_RE)
        self.assertEqual(result["computed"], expected)


class A4RepoRootRestoreTest(_TempRootTest):
    def test_a4_restores_repo_root(self):
        import orvyren.verify.engine as engine_module
        seen = {}

        class _Stub:
            _REPO_ROOT = "ORIGINAL_ROOT"

            @staticmethod
            def build(decision_path, out_dir, extra_paths=None, generated_at=None):
                seen["repo_root"] = _Stub._REPO_ROOT
                md = os.path.join(out_dir, "dossier_x.md")
                html = os.path.join(out_dir, "dossier_x.html")
                for path, body in ((md, "MD"), (html, "HTML")):
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(body)
                return {"md_path": md, "html_path": html}

        self.write("decision.json", "{}")
        self.write("dossier_x.md", "MD")
        self.write("dossier_x.html", "HTML")
        manifest = {"dossier": {"md": "dossier_x.md", "html": "dossier_x.html",
                                "generated_at": "2026-10-17T00:00:00Z",
                                "inputs": {"decision": "decision.json"}}}
        original = engine_module._dossier_mod
        engine_module._dossier_mod = _Stub
        try:
            checks = engine_mod.check_a4_rerender(self.root, manifest)
        finally:
            engine_module._dossier_mod = original
        self.assertTrue(all(c["ok"] for c in checks), checks)
        self.assertEqual(seen["repo_root"] != "ORIGINAL_ROOT", True,
                         "build must see the staging display root")
        self.assertEqual(_Stub._REPO_ROOT, "ORIGINAL_ROOT",
                         "_REPO_ROOT must be restored after the check")


class A5PolicyGuardTest(_TempRootTest):
    def test_a5_unreadable_policy_field_named_not_crash(self):
        self.write("policy.json", json.dumps({"ttl_intent_minutes": "abc"}))
        self.write_jsonl("audit.jsonl", [
            {"kind": "POLICY", "payload": {"intent_id": "i1", "verdict": "ALLOW"}}])
        manifest = {"policy": {"file": "policy.json"},
                    "streams": {"exec": {"path": "audit.jsonl"}}}
        checks = engine_mod.check_a5_policy(self.root, manifest)
        self.assertEqual(len(checks), 1)
        self.assertFalse(checks[0]["ok"])
        self.assertIn("unreadable numeric field", str(checks[0]["detail"]))

    def test_a5_unreadable_cumulative_named_not_crash(self):
        self.write("policy.json", json.dumps({"ttl_intent_minutes": 15}))
        self.write_jsonl("audit.jsonl", [
            {"kind": "INTENT", "payload": {"intent_id": "i1"}},
            {"kind": "POLICY", "payload": {"intent_id": "i1", "verdict": "ALLOW",
                                           "context_used": {"cumulative_spent": "abc"}}}])
        manifest = {"policy": {"file": "policy.json"},
                    "streams": {"exec": {"path": "audit.jsonl"}}}
        checks = engine_mod.check_a5_policy(self.root, manifest)
        self.assertFalse(checks[0]["ok"])
        failures = checks[0]["detail"]["failures"]
        self.assertTrue(any("cumulative_spent" in str(f) for f in failures), failures)


class A7SignalsGuardTest(_TempRootTest):
    def _run(self, decision, rows):
        self.write("decision.json", json.dumps(decision))
        self.write("corpus.csv", "timestamp_utc,venue,metric,value\n" + rows)
        manifest = {"decision": {"path": "decision.json"},
                    "fixtures": {"corpus": "corpus.csv"}}
        return engine_mod.check_a7_fixtures(self.root, manifest)

    def test_a7_missing_window_and_zero_supply_named_not_crash(self):
        checks = self._run({"window": {}}, "")
        self.assertFalse(checks[0]["ok"])
        self.assertIn("recompute failed", str(checks[0]["detail"]))
        zero = ("2023-03-10T00:00:00Z,defillama_supply_aggregate,circulating_usd,0.0\n"
                "2023-03-10T01:00:00Z,defillama_supply_aggregate,circulating_usd,1.0\n")
        checks = self._run({"window": {"start": "2023-03-10T00:00:00Z",
                                       "end": "2023-03-11T00:00:00Z"}}, zero)
        self.assertFalse(checks[0]["ok"])
        self.assertIn("recompute failed", str(checks[0]["detail"]))


class A8ReceiptsGuardTest(_TempRootTest):
    def test_a8_bad_log_data_named_not_crash(self):
        transfer = engine_mod.TRANSFER_TOPIC
        receipt = {"status": "0x1", "logs": [{
            "address": "0xtoken", "topics": [transfer, "0x" + "1" * 64, "0x" + "2" * 40],
            "data": "0xZZ"}]}
        self.write("receipts/r1.json", json.dumps(receipt))
        self.write_jsonl("audit.jsonl", [
            {"kind": "INTENT", "payload": {"intent_id": "i1", "recipient": "0x" + "2" * 40,
                                           "asset": "0xtoken", "amount_base_units": "5"}},
            {"kind": "RECEIPT", "refs": {"intent_id": "i1"},
             "payload": {"tx_hash": "0xtx", "raw_ref": "receipts/r1.json",
                         "status": "0x1"}}])
        manifest = {"streams": {"exec": {"path": "audit.jsonl"}}}
        checks = engine_mod.check_a8_receipts(self.root, manifest)
        self.assertFalse(checks[0]["ok"])
        problems = checks[0]["detail"]["problems"]
        self.assertTrue(any(p.get("reason") == "LOG_DATA_UNREADABLE" for p in problems),
                        problems)


class C2RefsGuardTest(_TempRootTest):
    def test_c2_null_refs_not_crash(self):
        self.write_jsonl("audit.jsonl", [
            {"kind": "SUBMIT", "refs": None, "payload": {}},
            {"kind": "POLICY", "refs": {"intent_id": "forced-1"}, "payload": {}}])
        manifest = {"streams": {"exec": {"path": "audit.jsonl"}}}
        checks = engine_mod.check_c_coverage(self.root, manifest)
        check = [c for c in checks if c["id"] == "C2.refs.resolve"][0]
        self.assertTrue(check["ok"], check["detail"])


class ClockStepToNextTest(unittest.TestCase):
    def _clock(self):
        return clock_mod.ReplayClock(t_sim_start_utc="2023-03-10T00:00:00Z",
                                     t_sim_end_utc="2023-03-12T00:00:00Z",
                                     run_id="review")

    def test_step_to_next_ignores_out_of_window_events(self):
        clock = self._clock()
        # Only out-of-window events: no admissible event exists — the clock must
        # NOT jump to the window end (old behaviour dragged t_sim to the end and
        # handed back an instant where the event is still inadmissible).
        self.assertIsNone(clock.step_to_next(["2023-03-20T00:00:00Z"]))
        self.assertEqual(clock.t_sim_iso(), "2023-03-10T00:00:00Z")
        self.assertEqual(clock.step_index, 0)
        # In-window events still work, in order; the end boundary is inclusive.
        self.assertEqual(clock.step_to_next(["2023-03-20T00:00:00Z",
                                             "2023-03-12T00:00:00Z"]),
                         "2023-03-12T00:00:00Z")
        self.assertIsNone(clock.step_to_next(["2023-03-20T00:00:00Z"]))


class CorpusAnchorsTest(_TempRootTest):
    def test_block_for_rejects_bool_anchors(self):
        anchors = {"2023-03-10": True, "2023-03-09": 42}
        self.assertEqual(corpus_mod.block_for(anchors, "2023-03-10T05:00:00Z"), 42,
                         "a JSON true is not a block number")
        self.assertIsNone(corpus_mod.block_for({"2023-03-10": True},
                                               "2023-03-10T05:00:00Z"))
        with self.assertRaises(corpus_mod.CorpusError):
            corpus_mod.require_pinned_block(True)

    def test_load_manifest_entry_without_path_is_corpus_error(self):
        path = self.write("manifest.json", json.dumps({"files": [{"sha256": "0" * 64}]}))
        with self.assertRaises(corpus_mod.CorpusError):
            corpus_mod.load_manifest(path)


class DossierRunsLogTest(_TempRootTest):
    def test_verify_dossier_skips_corrupt_runs_log_lines(self):
        content = {"schema": "orvyren.replay-dossier/v1", "banner": "REPLAY — x",
                   "provenance": {"mode": "REPLAY-JOURNAL", "replay_id": "r1"},
                   "run_id": "run-1", "clock_audit": {"valid": True}}
        stripped = {key: value for key, value in content.items()
                    if key not in ("content_sha256", "ts_wall_utc", "duration_s")}
        import hashlib
        content_sha = hashlib.sha256(
            dossier_mod.canonical_json(dossier_mod._strip_wall(stripped)).encode("utf-8")
        ).hexdigest()
        document = dict(content, content_sha256=content_sha,
                        ts_wall_utc="2026-10-17T00:00:00Z", duration_s=1.0)
        doc_path = self.write("dossier.json", json.dumps(document))
        log_path = self.write("runs.jsonl",
                              '{"replay_id": "r1", "content_sha256": TRUNCATED\n'
                              + "123\n"
                              + json.dumps({"replay_id": "r1",
                                            "content_sha256": content_sha}) + "\n")
        verdict = dossier_mod.verify_replay_dossier(doc_path, runs_log=log_path)
        self.assertEqual(verdict["verdict"], "OK", verdict)
        self.assertTrue(verdict["registered"])


class JournalOutcomeGuardTest(_TempRootTest):
    def test_load_transcript_corrupt_outcome_is_replay_error(self):
        run_dir = os.path.join(self.root, "run")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "run_outcome.json"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write("{truncated")
        with self.assertRaises(journal_mod.ReplayJournalError):
            journal_mod.load_transcript(run_dir)
        with open(os.path.join(run_dir, "run_outcome.json"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write("[1, 2]")
        with self.assertRaises(journal_mod.ReplayJournalError):
            journal_mod.load_transcript(run_dir)


class HypothesesNullToleranceTest(_TempRootTest):
    def test_validate_null_fields_produce_codes_not_crash(self):
        record = hyp_mod.HypothesisRecord(
            id=None, case_id=None, enonce=None, p="probable", p_gel_ref=None,
            criteres=(hyp_mod.Criterion(nom="soutien", predicat=None, seuil=None,
                                        sources=None, fenetre=None),),
            histoire=(hyp_mod.HistoryEntry(utc=None, transition=None, raison=None),),
            provenance=None)
        codes = hyp_mod.validate_hypothesis(record)
        for expected in ("E_HYP_ID_EMPTY", "E_HYP_CASE_EMPTY", "E_HYP_ENONCE_EMPTY",
                         "E_HYP_CRITERION_INCOMPLETE", "E_HYP_P_NO_GEL_REF",
                         "E_HYP_HISTORY_INCOMPLETE"):
            self.assertIn(expected, codes)

    def test_record_from_dict_null_lists_forgiving(self):
        record = hyp_mod.record_from_dict({
            "id": "H-1", "case_id": "c", "enonce": "e",
            "criteres": None, "preuves_pour": None, "preuves_contre": None,
            "inconnues": None, "histoire": None, "provenance": None,
            "relations": None})
        self.assertEqual(record.preuves_pour, ())
        self.assertEqual(record.relations, ())
        self.assertEqual(record.provenance, {})

    def test_load_jsonl_duplicate_id_rejected(self):
        data = hyp_mod.record_to_dict(_valid_record())
        path = self.write("h.jsonl", json.dumps(data) + "\n" + json.dumps(data) + "\n")
        with self.assertRaises(ValueError) as caught:
            hyp_mod.HypothesisRegistry.load_jsonl(path)
        self.assertIn("E_HYP_ID_TAKEN", str(caught.exception))


def _valid_record():
    return hyp_mod.HypothesisRecord(
        id="H-1", case_id="c", enonce="e",
        criteres=(hyp_mod.Criterion(nom="soutien", predicat="p", seuil="s",
                                    sources=("src",), fenetre="f"),
                  hyp_mod.Criterion(nom="refutation", predicat="p", seuil="s",
                                    sources=("src",), fenetre="f")),
        provenance={"auteur": "a", "modele": "m", "date": "d"})


class VerifierZipSafetyTest(_TempRootTest):
    def test_zip_slip_member_is_refused(self):
        archive_path = os.path.join(self.root, "evil.zip")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../escape.txt", "owned")
        root, cleanup, error = engine_mod.resolve_target(archive_path)
        self.assertIsNone(root)
        self.assertIsNone(cleanup)
        self.assertIn("unsafe archive member", error)

    def test_manifest_path_escape_is_not_read(self):
        outside = os.path.join(os.path.dirname(self.root), "outside_manifest_%d.md" % os.getpid())
        with open(outside, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("outside")
        try:
            checks = engine_mod.check_a2_dossier(
                self.root, {"dossier": {"md": "../outside_manifest_%d.md" % os.getpid()}})
            self.assertFalse(checks[0]["ok"])
            self.assertEqual(checks[0]["detail"].get("reason"), "unsafe dossier path")
        finally:
            os.remove(outside)

    def test_non_http_rpc_scheme_is_refused(self):
        with self.assertRaises(ValueError):
            engine_mod._rpc("file:///tmp/rpc.json", "eth_chainId", [])

    def test_valid_packet_zip_is_extracted(self):
        packet = os.path.join(self.root, "packet")
        os.makedirs(os.path.join(packet, "pkt"))
        with open(os.path.join(packet, "pkt", "manifest.json"), "w",
                  encoding="utf-8", newline="\n") as handle:
            handle.write("{}")
        archive_path = os.path.join(self.root, "packet.zip")
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(os.path.join(packet, "pkt", "manifest.json"), "pkt/manifest.json")
        root, cleanup, error = engine_mod.resolve_target(archive_path)
        try:
            self.assertIsNone(error)
            self.assertIsNotNone(root)
            self.assertTrue(os.path.isfile(os.path.join(root, "manifest.json")))
        finally:
            if cleanup:
                shutil.rmtree(cleanup, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
