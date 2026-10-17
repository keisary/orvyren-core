#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SQL API tests for the graph (Q1/Q4/Q6/Q7/Q8/snapshot), no network."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph import api  # noqa: E402
from orvyren.graph.record import ChainRef, RelationRecord  # noqa: E402
from orvyren.graph.store import GraphStore  # noqa: E402

USER = "addr:eip155:8453:0x00000000000000000000000000000000000000aa"
ASSET = "asset:eip155:8453:0x00000000000000000000000000000000000000bb"
MARKET = "market:eip155:8453:0x00000000000000000000000000000000000000cc:0x00000000000000000000000000000000000000bb"
POSITION = "position:eip155:8453:0x00000000000000000000000000000000000000aa:0x00000000000000000000000000000000000000bb"
DEBT = "debt:eip155:8453:0x00000000000000000000000000000000000000cc:0x00000000000000000000000000000000000000bb"
AS_OF = "2026-02-01T00:00:00+00:00"
BLOCK = 200


def rec(relation_id: str, kind: str, src: str, src_kind: str, dst: str,
        dst_kind: str, *, amount: float = 10.0, sign: str = "+") -> RelationRecord:
    return RelationRecord(
        relation_id=relation_id, family="STRUCTURE_EXPOSURE", kind=kind,
        src=src, dst=dst, src_kind=src_kind, dst_kind=dst_kind,
        mechanism="LIQUIDITY", sign_prior=sign,
        conditions="", regime_scope="test", horizon_scope="block",
        epistemic_status="FACT", lifecycle="ACTIVE", validation_status="VALIDATED",
        valid_from="2026-01-01T00:00:00+00:00", valid_to=None,
        valid_from_block=100, valid_to_block=None,
        revision=1, inserted_at="2026-01-01T00:00:01+00:00",
        provenance_refs=("event:eip155:8453:0xdead:1",),
        source_family_id="SF-TEST", extract_method="ONCHAIN_READ",
        chain_ref=ChainRef(chain_id=8453, block=100, tx_hash="0xdead"),
        confidence=1.0,
        payload={"amount": amount, "unit": "USDC", "as_of": AS_OF},
    )


class GraphApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "graph.sqlite")
        with GraphStore(self.db) as store:
            store.insert_relation_record(rec("rel-holds", "HOLDS", USER, "ADRESSE", ASSET, "STABLECOIN"))
            store.insert_relation_record(rec("rel-deposit", "DEPOSITED_IN", ASSET, "STABLECOIN", MARKET, "MARCHE"))
            store.insert_relation_record(rec("rel-owes", "OWES", POSITION, "POSITION", DEBT, "DETTE", amount=7.0))
            store.insert_relation_record(rec("rel-coll", "COLLATERALIZES", ASSET, "STABLECOIN", MARKET, "MARCHE", amount=3.0))

    def tearDown(self):
        self.tmp.cleanup()

    def test_q1_direct_and_indirect(self):
        result = api.exposure(self.db, USER, as_of=AS_OF, as_of_block=BLOCK)
        self.assertEqual(result["count"], 2)
        by_asset = {row["asset"]: row for row in result["rows"]}
        self.assertEqual(by_asset[ASSET]["depth"], 0)
        self.assertEqual(by_asset[MARKET]["depth"], 1)

    def test_q1_rejects_future(self):
        result = api.exposure(self.db, USER, as_of="2025-01-01T00:00:00+00:00",
                              as_of_block=50)
        self.assertEqual(result["count"], 0)

    def test_q4_pit(self):
        result = api.pit(self.db, as_of=AS_OF, as_of_block=BLOCK)
        self.assertEqual(result["count"], 4)
        future = api.pit(self.db, as_of="2025-01-01T00:00:00+00:00", as_of_block=50)
        self.assertEqual(future["count"], 0)

    def test_q6_provenance(self):
        result = api.provenance(self.db, "rel-holds")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["rows"][0]["ref_kind"], "EVENT")

    def test_q7_concentration(self):
        result = api.concentration(self.db, DEBT, as_of=AS_OF, as_of_block=BLOCK)
        self.assertEqual(result["counterparties"], 1)
        self.assertAlmostEqual(result["hhi"], 1.0)

    def test_q8_permissions_not_ingested(self):
        result = api.permissions(self.db, USER, as_of=AS_OF, as_of_block=BLOCK)
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["status"], "NOT_INGESTED")

    def test_snapshot_is_deterministic(self):
        first = api.snapshot(self.db, as_of=AS_OF, as_of_block=BLOCK)
        second = api.snapshot(self.db, as_of=AS_OF, as_of_block=BLOCK)
        self.assertEqual(first["graph_hash"], second["graph_hash"])
        self.assertEqual(first["counts"]["relations"], 4)


if __name__ == "__main__":
    unittest.main()
