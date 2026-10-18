#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench of the graph snapshot/provenance export (W1 lot L1.6).

Contract (DOC4 W1 [DONE]): ``graph_snapshot.json`` is hashed, point-in-time,
and a third party can re-verify both artefacts from the files alone
(``sha256sum -c MANIFEST.sha256`` + internal ``snapshot_hash``).

Execution: ``python -m pytest tests/test_graph_export.py -q``.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from orvyren.graph.export import (  # noqa: E402
    PROVENANCE_SCHEMA,
    SNAPSHOT_SCHEMA,
    build_provenance,
    build_snapshot,
    snapshot_sha256,
    write_snapshot_dir,
)
from orvyren.graph.queries import load_fixture_records  # noqa: E402

FIXTURES = os.path.join(HERE, "..", "fixtures", "graphs")
AS_OF = "2026-10-16T00:00:00Z"


def load_case(name):
    return load_fixture_records(os.path.join(FIXTURES, "%s.json" % name))


class TestSnapshot(unittest.TestCase):

    def test_snapshot_is_pit_frozen_and_hashed(self):
        snapshot = build_snapshot(load_case("usdc_2023-03"), "usdc-2023-03", AS_OF)
        self.assertEqual(snapshot["schema"], SNAPSHOT_SCHEMA)
        self.assertEqual(snapshot["counts"]["records"], 8)  # DEPOSITED_IN window closed
        self.assertEqual(snapshot["counts"]["by_kind"]["HOLDS"], 1)
        self.assertEqual(len(snapshot["snapshot_hash"]), 64)
        self.assertEqual(snapshot["snapshot_hash"], snapshot_sha256(snapshot))

    def test_fail_closed_before_knowledge_clock(self):
        snapshot = build_snapshot(load_case("usdc_2023-03"), "usdc-2023-03",
                                  "2023-03-11T12:00:00Z")
        self.assertEqual(snapshot["counts"]["records"], 0)
        self.assertEqual(snapshot["records"], [])

    def test_deterministic_and_sensitive(self):
        records = load_case("rseth_2026-04")
        first = build_snapshot(records, "rseth_2026-04", AS_OF)
        second = build_snapshot(load_case("rseth_2026-04"), "rseth_2026-04", AS_OF)
        self.assertEqual(first["snapshot_hash"], second["snapshot_hash"])
        # a single payload change flips the hash
        import copy
        tampered = copy.deepcopy(first)
        tampered["records"][0]["payload"]["cap_ratio_max"] = 0.999
        self.assertNotEqual(snapshot_sha256(tampered), first["snapshot_hash"])


class TestProvenance(unittest.TestCase):

    def test_chains_and_hashes(self):
        provenance = build_provenance(load_case("usdc_2023-03"), "usdc-2023-03", AS_OF)
        self.assertEqual(provenance["schema"], PROVENANCE_SCHEMA)
        origins = {chain["origin"] for chain in provenance["chains"]}
        self.assertIn("claim:oracle_min_chainlink", origins)
        self.assertIn("obs:bitstamp_low", origins)  # observation -> source hops
        self.assertTrue(provenance["hashes_complete"])
        for chain in provenance["chains"]:
            for hop in chain["chain"]:
                self.assertEqual(len(hop["fingerprint"]), 16)


class TestWriteDir(unittest.TestCase):

    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="orvyren_graph_export_")
        self.addCleanup(shutil.rmtree, self.out, ignore_errors=True)

    def test_files_and_manifest_verify(self):
        paths = write_snapshot_dir(load_case("steth_2022-06"), "steth-2022-06",
                                   "2022-06-16T00:00:00Z", self.out)
        for key in ("snapshot", "provenance", "manifest"):
            self.assertTrue(os.path.exists(paths[key]), key)
        # third-party verification: sha256sum -c MANIFEST.sha256 (recomputed here)
        with open(paths["manifest"], encoding="utf-8") as handle:
            for line in handle:
                digest, name = line.split()
                with open(os.path.join(self.out, name), "rb") as artefact:
                    self.assertEqual(hashlib.sha256(artefact.read()).hexdigest(), digest)
        with open(paths["snapshot"], encoding="utf-8") as handle:
            snapshot = json.load(handle)
        self.assertEqual(snapshot["snapshot_hash"], paths["snapshot_hash"])
        # byte-identical re-export (determinism)
        with open(paths["snapshot"], "rb") as handle:
            first = handle.read()
        write_snapshot_dir(load_case("steth_2022-06"), "steth-2022-06",
                           "2022-06-16T00:00:00Z", self.out)
        with open(paths["snapshot"], "rb") as handle:
            self.assertEqual(handle.read(), first)


if __name__ == "__main__":
    unittest.main()
