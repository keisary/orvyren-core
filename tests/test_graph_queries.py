#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench of the 8 core graph queries Q1-Q8 (W1 lot L1.4).

Contract (DOC4 W1 [DONE]): the queries are the store's **test contract** — on
the frozen episode fixtures (``fixtures/graphs/``: USDC 2023-03, stETH
2022-06, rsETH 2026-04) they must reproduce the published figures and uphold
the structural invariants:

- Q1: transitive HOLDS is **never** closed (détenir ≠ contrôler);
- Q2: only DEPENDS_ON / AFFECTS are traversed — SUPPORTS / REFUTES /
  CONTRADICTS / CORRELATES_WITH are structurally untraversable;
- Q4: point-in-time = world validity ∩ knowledge clock (the 18:30 rsETH state
  must NOT show the 19:03:59 freeze);
- Q6: every provenance hop carries its fingerprint.

Execution: ``python -m pytest tests/test_graph_queries.py -q``.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from orvyren.graph.queries import (  # noqa: E402
    DEPENDENCY_KINDS,
    FORBIDDEN_PROPAGATION_KINDS,
    load_fixture_records,
    q1_consolidated_exposure,
    q2_dependency_paths,
    q3_open_contradictions,
    q4_pit_state,
    q5_episode_timeline,
    q6_provenance_walk,
    q7_concentration,
    q8_permission_state,
)
from orvyren.graph.record import record_from_dict  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "graphs")


def load_case(name):
    return load_fixture_records(os.path.join(FIXTURES, "%s.json" % name))


def _rec(**kw):
    """Build one record dict with test defaults (all 17 fields available)."""
    base = {
        "relation_id": "t-1", "family": "STRUCTURE_EXPOSURE", "kind": "HOLDS",
        "src": "", "dst": "", "src_kind": "TRESORERIE", "dst_kind": "STABLECOIN",
        "mechanism": "CUSTODY", "sign_prior": "+", "conditions": "measured",
        "regime_scope": "global", "horizon_scope": "episode",
        "epistemic_status": "FACT", "lifecycle": "ACTIVE",
        "validation_status": "VALIDATED",
        "valid_from": "2023-01-01T00:00:00Z", "valid_to": None,
        "inserted_at": "2023-01-01T00:00:00Z",
        "source_family_id": "SF-TEST", "extract_method": "HUMAN",
        "payload": {},
    }
    base.update(kw)
    return record_from_dict(base)


class TestFixturesIntegrity(unittest.TestCase):

    def test_fixture_sizes(self):
        self.assertEqual(len(load_case("usdc_2023-03")), 9)
        self.assertEqual(len(load_case("steth_2022-06")), 4)
        self.assertEqual(len(load_case("rseth_2026-04")), 7)

    def test_queries_are_pure_and_deterministic(self):
        records = load_case("usdc_2023-03")
        first = q1_consolidated_exposure(records, "treasury:dao_usdc")
        second = q1_consolidated_exposure(records, "treasury:dao_usdc")
        self.assertEqual(first, second)
        records2 = load_case("usdc_2023-03")
        self.assertEqual(first, q1_consolidated_exposure(records2, "treasury:dao_usdc"))


class TestQ1ConsolidatedExposure(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = load_case("usdc_2023-03")

    def test_direct_and_indirect(self):
        result = q1_consolidated_exposure(self.records, "treasury:dao_usdc")
        self.assertEqual(result["holder"], "treasury:dao_usdc")
        self.assertEqual([item["asset"] for item in result["direct"]], ["asset:usdc"])
        self.assertEqual(result["direct"][0]["relation_id"], "usdc-holds-treasury")
        self.assertEqual(len(result["indirect"]), 1)
        indirect = result["indirect"][0]
        self.assertEqual(indirect["asset"], "asset:usdc")
        self.assertEqual(indirect["protocol"], "marche:aave_v3_usdc_reserve")
        self.assertEqual(indirect["kind"], "DEPOSITED_IN")
        self.assertEqual(indirect["depth"], 1)
        self.assertEqual(result["protocols"], ["marche:aave_v3_usdc_reserve"])

    def test_as_of_window_excludes_closed_relations(self):
        inside = q1_consolidated_exposure(self.records, "treasury:dao_usdc",
                                          as_of="2023-03-13T00:00:00Z")
        self.assertEqual(len(inside["indirect"]), 1)
        # DEPOSITED_IN ends 2023-03-14 (valid_to exclusive) -> closed afterwards
        after = q1_consolidated_exposure(self.records, "treasury:dao_usdc",
                                         as_of="2023-03-14T00:00:00Z")
        self.assertEqual(after["indirect"], [])
        self.assertEqual(len(after["direct"]), 1)  # HOLDS stays open

    def test_transitive_holds_is_never_closed(self):
        records = (
            _rec(relation_id="a-hold", kind="HOLDS", src="treasury:t", dst="asset:wrapper"),
            _rec(relation_id="b-hold", kind="HOLDS", src="asset:wrapper", dst="asset:deep"),
            _rec(relation_id="c-dep", kind="DEPOSITED_IN", src="asset:wrapper",
                 dst="protocol:p1"),
        )
        result = q1_consolidated_exposure(records, "treasury:t")
        self.assertEqual([i["asset"] for i in result["direct"]], ["asset:wrapper"])
        self.assertEqual([i["protocol"] for i in result["indirect"]], ["protocol:p1"])
        # the HOLDS edge wrapper -> deep must NOT appear anywhere (détenir ≠ contrôler)
        flat = [i["asset"] for i in result["direct"]] \
            + [i["asset"] for i in result["indirect"]] \
            + [i["protocol"] for i in result["indirect"]]
        self.assertNotIn("asset:deep", flat)


class TestQ2DependencyPaths(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rseth = load_case("rseth_2026-04")

    def test_incoming_depends_on(self):
        paths = q2_dependency_paths(self.rseth, "asset:rseth")
        self.assertEqual(len(paths), 1)
        path = paths[0]
        self.assertEqual(path["dependent"], "marche:aave_v3_weth_market")
        self.assertEqual(path["path"], ["asset:rseth", "marche:aave_v3_weth_market"])
        self.assertEqual(path["kinds"], ["DEPENDS_ON"])
        self.assertEqual(path["sign"], "+")
        self.assertAlmostEqual(path["weight"], 0.5)

    def test_outgoing_affects_with_channel(self):
        paths = q2_dependency_paths(self.rseth, "variable:rseth_supply_saturation")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]["dependent"], "variable:rseth_is_frozen")
        self.assertEqual(paths[0]["channels"], ["GOVERNANCE"])

    def test_forbidden_kinds_are_never_traversed(self):
        for case in ("usdc_2023-03", "steth_2022-06", "rseth_2026-04"):
            for path in q2_dependency_paths(load_case(case), "asset:rseth"):
                self.assertTrue(set(path["kinds"]) <= DEPENDENCY_KINDS)
        # in-test decoy: a SUPPORTS edge into the node must not create a path
        records = (
            _rec(relation_id="decoy", kind="SUPPORTS", family="PROOF_DERIVATION",
                 src="claim:x", dst="node:A", src_kind="CLAIM", dst_kind="HYPOTHESE"),
            _rec(relation_id="real", kind="DEPENDS_ON", src="node:B", dst="node:A",
                 src_kind="MARCHE", dst_kind="MARCHE"),
        )
        paths = q2_dependency_paths(records, "node:A")
        self.assertEqual([p["dependent"] for p in paths], ["node:B"])
        self.assertNotIn("claim:x", {p["dependent"] for p in paths})
        self.assertTrue(FORBIDDEN_PROPAGATION_KINDS
                        .isdisjoint({k for p in paths for k in p["kinds"]}))

    def test_sign_product_and_hop_decay(self):
        records = (
            _rec(relation_id="r1", kind="DEPENDS_ON", src="node:B", dst="node:A",
                 sign_prior="-"),
            _rec(relation_id="r2", kind="DEPENDS_ON", src="node:C", dst="node:B",
                 sign_prior="-"),
        )
        paths = {p["dependent"]: p for p in q2_dependency_paths(records, "node:A")}
        self.assertEqual(paths["node:B"]["weight"], 0.5)
        self.assertAlmostEqual(paths["node:C"]["weight"], 0.25)
        self.assertEqual(paths["node:C"]["sign"], "+")  # sign product (-- -> +)
        self.assertEqual(paths["node:C"]["path"], ["node:A", "node:B", "node:C"])

    def test_cycles_are_cut(self):
        records = (
            _rec(relation_id="r1", kind="DEPENDS_ON", src="node:B", dst="node:A"),
            _rec(relation_id="r2", kind="DEPENDS_ON", src="node:A", dst="node:B"),
        )
        paths = q2_dependency_paths(records, "node:A")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]["dependent"], "node:B")
        # a cycle closure path (dependent == origin) is never emitted
        self.assertNotIn("node:A", {p["dependent"] for p in paths})


class TestQ3OpenContradictions(unittest.TestCase):

    def test_open_pair_from_fixture(self):
        pairs = q3_open_contradictions(load_case("usdc_2023-03"))
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["claim_a"], "claim:market_min_bitstamp")
        self.assertEqual(pairs[0]["claim_b"], "claim:oracle_min_chainlink")
        self.assertEqual(pairs[0]["relation_id"], "usdc-contradiction-oracle-market")

    def test_resolved_or_superseded_pairs_are_hidden(self):
        records = (
            _rec(relation_id="c1", kind="CONTRADICTS", family="PROOF_DERIVATION",
                 src="claim:a", dst="claim:b", validation_status="REJECTED"),
            _rec(relation_id="c2", kind="CONTRADICTS", family="PROOF_DERIVATION",
                 src="claim:c", dst="claim:d", superseded_by="c3"),
        )
        self.assertEqual(q3_open_contradictions(records), [])


class TestQ4PitState(unittest.TestCase):

    def test_usdc_reconstruction_is_fail_closed_in_2023(self):
        # inserted_at = 2026-10-15: at a 2023 moment the reconstruction knows
        # nothing (knowledge clock) — the PIT invariant is fail-closed.
        self.assertEqual(q4_pit_state(load_case("usdc_2023-03"),
                                      "2023-03-11T12:00:00Z"), ())
        # at a 2026 moment: the 9 reconstructions are known; the DEPOSITED_IN
        # window closed on 2023-03-14 (valid_to exclusive) -> 8 records stay
        self.assertEqual(len(q4_pit_state(load_case("usdc_2023-03"),
                                          "2026-10-16T00:00:00Z")), 8)

    def test_steth_knowledge_clock(self):
        records = load_case("steth_2022-06")
        early = q4_pit_state(records, "2022-05-10T00:00:00Z")
        self.assertEqual([r.relation_id for r in early], ["steth-event-1"])
        at_worst = q4_pit_state(records, "2022-06-15T01:00:00Z")
        self.assertEqual(len(at_worst), 4)

    def test_rseth_freeze_is_not_known_at_1830(self):
        records = load_case("rseth_2026-04")
        before = q4_pit_state(records, "2026-04-18T18:30:00Z")
        self.assertEqual(len(before), 5)
        ids = {r.relation_id for r in before}
        self.assertNotIn("rseth-freeze-constrains-market", ids,
                         "le gel (19:03:59) ne doit PAS être visible à 18:30")
        self.assertNotIn("rseth-saturation-affects-freeze", ids)
        after = q4_pit_state(records, "2026-04-18T19:04:30Z")
        self.assertEqual(len(after), 6)
        self.assertIn("rseth-freeze-constrains-market",
                      {r.relation_id for r in after})


class TestQ5EpisodeTimeline(unittest.TestCase):

    def test_window_and_clocks(self):
        entries = q5_episode_timeline(load_case("usdc_2023-03"),
                                      "2023-03-11T00:00:00Z", "2023-03-12T00:00:00Z")
        self.assertEqual(len(entries), 7)
        event_times = [entry["event_time"] for entry in entries]
        self.assertEqual(event_times, sorted(event_times))
        self.assertEqual(entries[0]["relation_id"], "usdc-derived-dispersion")
        # clocks are kept separate: event_time is historical, tx_time is the
        # reconstruction clock (2026) — never conflated into one field
        for entry in entries:
            self.assertIsNotNone(entry["event_time"])
            self.assertNotEqual(entry["event_time"], entry["tx_time"])


class TestQ6ProvenanceWalk(unittest.TestCase):

    def test_chain_with_hashes(self):
        result = q6_provenance_walk(load_case("usdc_2023-03"),
                                    "claim:oracle_min_chainlink")
        self.assertEqual(result["origin"], "claim:oracle_min_chainlink")
        hops = [(hop["from"], hop["to"], hop["kind"]) for hop in result["chain"]]
        self.assertEqual(hops, [
            ("claim:oracle_min_chainlink", "obs:chainlink_low", "EXTRACTED_FROM"),
            ("obs:chainlink_low", "source:chainlink", "OBSERVED_FROM"),
        ])
        self.assertTrue(result["hashes_complete"])
        for hop in result["chain"]:
            self.assertEqual(len(hop["fingerprint"]), 16)

    def test_two_sources_sorted(self):
        result = q6_provenance_walk(load_case("usdc_2023-03"),
                                    "claim:dispersion_window")
        self.assertEqual([hop["to"] for hop in result["chain"]],
                         ["obs:binance_low", "obs:bitstamp_low",
                          "source:binance", "source:bitstamp"])
        self.assertTrue(result["hashes_complete"])

    def test_deterministic(self):
        records = load_case("steth_2022-06")
        first = q6_provenance_walk(records, "claim:event_terra")
        second = q6_provenance_walk(records, "claim:event_terra")
        self.assertEqual(first, second)
        self.assertEqual(first["chain"][0]["to"], "doc:nansen_report")


class TestQ7Concentration(unittest.TestCase):

    def test_rseth_supply_cap_saturation_reproduced(self):
        # Published figure: supplyCap saturation 99,999 % (rsETH 2026-04)
        result = q7_concentration(load_case("rseth_2026-04"),
                                  "parametre:supply_cap_rseth")
        self.assertIsNotNone(result["supply_cap_ratio"])
        self.assertAlmostEqual(result["supply_cap_ratio"],
                               529993.9826991736 / 530000, places=12)

    def test_rseth_collateral_weight_and_debt(self):
        result = q7_concentration(load_case("rseth_2026-04"), "asset:rseth")
        self.assertEqual(result["collateral_by_market"],
                         {"marche:aave_v3_weth_market": 89567})
        self.assertAlmostEqual(result["w_a"], 1.0)
        self.assertAlmostEqual(result["hhi"], 1.0)
        self.assertAlmostEqual(result["debt_backed"], 190000000.0)

    def test_hhi_two_markets(self):
        records = (
            _rec(relation_id="m1", kind="COLLATERALIZES", src="asset:a", dst="market:big",
                 payload={"amount": 75}),
            _rec(relation_id="m2", kind="COLLATERALIZES", src="asset:a", dst="market:small",
                 payload={"amount": 25}),
        )
        result = q7_concentration(records, "asset:a")
        self.assertAlmostEqual(result["hhi"], 0.625)
        self.assertAlmostEqual(result["w_a"], 0.75)


class TestQ8PermissionState(unittest.TestCase):

    def setUp(self):
        self.records = (
            _rec(relation_id="member", kind="MEMBER_OF", family="CONSTRAINT_PERMISSION",
                 src="agent:0xe1", dst="role:AGENT", src_kind="ADRESSE", dst_kind="ROLE",
                 valid_from="2026-10-16T00:00:00Z",
                 chain_ref={"chain_id": 84532, "block": 48191000, "tx_hash": "0x" + "ab" * 32}),
            _rec(relation_id="allow", kind="ALLOWS", family="CONSTRAINT_PERMISSION",
                 src="role:AGENT", dst="cible:usdc", src_kind="ROLE", dst_kind="CIBLE",
                 payload={"allowance": "usdc_daily", "refill": 300000000}),
            _rec(relation_id="revoke", kind="REVOKES", family="CONSTRAINT_PERMISSION",
                 src="role:DAO", dst="agent:0xe1", src_kind="ROLE", dst_kind="ADRESSE",
                 valid_from="2026-10-16T12:00:00Z",
                 payload={"subject": "agent:0xe1"}),
        )

    def test_membership_allowances_and_revocations(self):
        result = q8_permission_state(self.records, "agent:0xe1")
        self.assertEqual([r["role"] for r in result["roles"]], ["role:AGENT"])
        self.assertEqual(result["roles"][0]["block"], 48191000)
        self.assertEqual([(a["role"], a["target"]) for a in result["allowances"]],
                         [("role:AGENT", "cible:usdc")])
        self.assertEqual([r["right"] for r in result["revoked"]], ["agent:0xe1"])

    def test_block_anchor_filter(self):
        # as-of block 48_000_000 predates the membership (48_191_000): nothing visible
        result = q8_permission_state(self.records, "agent:0xe1", as_of_block=48000000)
        self.assertEqual(result["roles"], [])
        self.assertEqual(result["allowances"], [])

    def test_subject_without_records(self):
        result = q8_permission_state(self.records, "agent:0xnone")
        self.assertEqual(result["roles"], [])
        self.assertEqual(result["allowances"], [])
        self.assertEqual(result["revoked"], [])


if __name__ == "__main__":
    unittest.main()
