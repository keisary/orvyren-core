#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — regression tests for the execution/data deep review (2026-10-17).

Each test pins one bug found while reading every file of
``src/orvyren/execution/`` and ``src/orvyren/data/`` end to end:

* ``ReserveConfig.from_word`` bit widths (36-bit caps, 8-bit e-mode) — the
  on-chain ``ReserveConfiguration.sol`` layout;
* ``ChainlinkFeed.decimals`` cache poisoning across blocks;
* ``ChainlinkFeed.price`` fallback losing the price when ``description()``
  fails;
* ``CurvePool.get_dy_raw`` silently sending malformed calldata for a negative
  or fractional amount;
* ``encode_uint``/``encode_int`` silent truncation (float/bool/str);
* ``decode_string`` bare ``int()`` error on a bogus offset;
* raw endpoint URLs (possible API keys) leaking through error messages and
  ``provenance()`` in the data layer;
* ``execution.chain.rpc`` raising ``AttributeError`` on a non-object JSON-RPC
  error;
* ``PeriodLedger`` trusting its own ``window_hours`` field on load.

Standard library only (unittest).
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from orvyren.data.aave import ReserveConfig  # noqa: E402
from orvyren.data.chainlink import (  # noqa: E402
    SEL_DECIMALS,
    SEL_DESCRIPTION,
    SEL_LATEST_ANSWER,
    SEL_LATEST_ROUND_DATA,
    ChainlinkFeed,
)
from orvyren.data.curve import CurvePool  # noqa: E402
from orvyren.data.rpc import (  # noqa: E402
    ArchiveRpc,
    RpcError,
    _mask_endpoint,
    decode_string,
    encode_int,
    encode_uint,
)
from orvyren.execution import chain as chain_client  # noqa: E402
from orvyren.execution import loop as executor  # noqa: E402
from orvyren.execution.guard import mask_rpc_url  # noqa: E402

CAP_FEED = "0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3"


def abi_uint(value):
    return f"{int(value):064x}"


def abi_string(text):
    payload = text.encode("utf-8").hex()
    padded = payload + "0" * ((64 - len(payload) % 64) % 64)
    return "0x" + abi_uint(32) + abi_uint(len(text)) + padded


def config_word(*, ltv=0, liq_threshold=0, liq_bonus=0, decimals=18,
                is_frozen=0, borrow_cap=0, supply_cap=0, emode=0,
                unbacked_mint_cap=0, liq_protocol_fee=0):
    """Assemble one Aave V3 ``ReserveConfiguration`` word from the real bit layout."""
    value = 0
    value |= (ltv & 0xFFFF)
    value |= (liq_threshold & 0xFFFF) << 16
    value |= (liq_bonus & 0xFFFF) << 32
    value |= (decimals & 0xFF) << 48
    value |= (is_frozen & 1) << 57
    value |= (borrow_cap & 0xFFFFFFFFF) << 80
    value |= (supply_cap & 0xFFFFFFFFF) << 116
    value |= (liq_protocol_fee & 0xFFFF) << 152
    value |= (emode & 0xFF) << 168
    value |= (unbacked_mint_cap & 0xFFFFFFFFF) << 176
    return value


class StubRpc:
    """Minimal eth_call double keyed by (address, selector)."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def eth_call(self, to, data, block="latest"):
        key = (to.lower(), data[:10].lower())
        self.calls.append((key, block))
        answer = self.responses.get(key)
        if answer is None:
            raise AssertionError(f"unexpected eth_call to {to} selector {data[:10]}")
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            return answer(to, data, block)
        return answer


class ReserveConfigBitLayoutTests(unittest.TestCase):
    """Field widths must match ReserveConfiguration.sol (36-bit caps, 8-bit e-mode)."""

    def test_supply_cap_keeps_its_36_bits(self):
        word = config_word(supply_cap=(1 << 32) + 7)
        self.assertEqual(ReserveConfig.from_word(word).supply_cap, (1 << 32) + 7)

    def test_borrow_cap_keeps_its_36_bits(self):
        word = config_word(borrow_cap=(1 << 32) + 1)
        self.assertEqual(ReserveConfig.from_word(word).borrow_cap, (1 << 32) + 1)

    def test_emode_is_not_polluted_by_the_unbacked_mint_cap(self):
        # unbacked mint cap = 1 sets bit 176: a 16-bit e-mode mask would read
        # category 1 as 0x0101 = 257.
        word = config_word(emode=1, unbacked_mint_cap=1)
        self.assertEqual(ReserveConfig.from_word(word).e_mode_category, 1)

    def test_measured_rseth_fixture_words_still_decode(self):
        path = os.path.join(ROOT, "fixtures", "raw_w2b", "aave_rseth_reserveconfig.json")
        if not os.path.exists(path):
            self.skipTest("fixture aave_rseth_reserveconfig.json not found")
        with open(path, "r", encoding="utf-8") as handle:
            rows = json.load(handle)
        self.assertGreater(len(rows), 0)
        for row in rows:
            config = ReserveConfig.from_word(int(row["config"]["raw"], 16))
            self.assertEqual(config.supply_cap, row["config"]["supplyCap"], row["block"])
            self.assertEqual(config.borrow_cap, row["config"]["borrowCap"], row["block"])
            self.assertEqual(config.decimals, row["config"]["decimals"], row["block"])
            self.assertEqual(config.e_mode_category, row["config"]["eMode"], row["block"])


class ChainlinkFeedTests(unittest.TestCase):

    def test_decimals_are_not_pinned_by_a_historical_read(self):
        stub = StubRpc(responses={
            (CAP_FEED.lower(), SEL_DECIMALS): lambda to, data, block: "0x" + abi_uint(
                8 if block == 100 else 18),
        })
        feed = ChainlinkFeed(stub, CAP_FEED, name="capped")
        self.assertEqual(feed.decimals(100), 8)
        # The historical read must not become the answer for every later call.
        self.assertEqual(feed.decimals("latest"), 18)

    def test_price_fallback_survives_a_failing_description(self):
        stub = StubRpc(responses={
            (CAP_FEED.lower(), SEL_LATEST_ROUND_DATA): RpcError("execution reverted"),
            (CAP_FEED.lower(), SEL_LATEST_ANSWER): "0x" + abi_uint(250_000_000),
            (CAP_FEED.lower(), SEL_DECIMALS): "0x" + abi_uint(8),
            (CAP_FEED.lower(), SEL_DESCRIPTION): RpcError("execution reverted"),
        })
        feed = ChainlinkFeed(stub, CAP_FEED, name="capped")
        payload = feed.price(100)
        self.assertEqual(payload["method"], "latestAnswer")
        self.assertEqual(payload["price"], 2.5)
        self.assertIsNone(payload["description"], "a missing label must not lose the price")


class CurveCalldataTests(unittest.TestCase):

    def _pool(self):
        return CurvePool(StubRpc(), decimals=(18, 18), name="stETH/ETH")

    def test_negative_amount_is_refused_not_encoded(self):
        with self.assertRaises(ValueError):
            self._pool().get_dy_raw(1, 0, -1)

    def test_fractional_amount_is_refused_not_truncated(self):
        with self.assertRaises(ValueError):
            self._pool().get_dy_raw(1, 0, 1.5)

    def test_oversized_amount_is_refused(self):
        with self.assertRaises(ValueError):
            self._pool().get_dy_raw(1, 0, 1 << 256)


class AbiCodecStrictnessTests(unittest.TestCase):

    def test_encode_uint_refuses_float_bool_and_str(self):
        for bad in (1.5, True, "10", None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                encode_uint(bad)

    def test_encode_int_refuses_float_and_bool(self):
        for bad in (1.5, False):
            with self.assertRaises(ValueError, msg=repr(bad)):
                encode_int(bad)

    def test_encode_int_still_handles_negative_indexes(self):
        self.assertEqual(int(encode_int(-1), 16), (1 << 256) - 1)

    def test_decode_string_bogus_offset_raises_a_named_error(self):
        payload = "0x" + abi_uint(128) + abi_uint(4) + abi_uint(0)  # offset 128 bytes past the end
        with self.assertRaises(ValueError) as ctx:
            decode_string(payload)
        self.assertIn("offset out of range", str(ctx.exception))

    def test_decode_string_round_trip(self):
        self.assertEqual(decode_string(abi_string("Capped rsETH / ETH / USD")),
                         "Capped rsETH / ETH / USD")


class EndpointMaskingTests(unittest.TestCase):

    KEYED = "https://base-sepolia.g.alchemy.com/v2/CANARY_SECRET"
    FRONT = "https://rpc.example.com/CANARY_SECRET/v1"

    def test_key_in_the_path_is_masked(self):
        masked = _mask_endpoint(self.KEYED)
        self.assertNotIn("CANARY_SECRET", masked)
        self.assertIn("base-sepolia.g.alchemy.com", masked)
        self.assertIn("/v2/***", masked)

    def test_key_at_the_front_of_the_path_is_masked(self):
        masked = _mask_endpoint(self.FRONT)
        self.assertNotIn("CANARY_SECRET", masked)

    def test_mask_never_raises_and_matches_the_guard_helper(self):
        for url in (self.KEYED, self.FRONT, "https://sepolia.base.org",
                    "https://host:notaport/x", "::::", ""):
            self.assertEqual(_mask_endpoint(url), mask_rpc_url(url), url)

    def test_rpc_errors_carry_no_key_and_provenance_is_masked(self):
        def failing(url, payload, timeout):
            raise OSError("connection refused")

        rpc = ArchiveRpc((self.KEYED,), retries=0, backoff=0.0, transport=failing)
        with self.assertRaises(RpcError) as ctx:
            rpc.call("eth_blockNumber", [])
        message = str(ctx.exception)
        self.assertNotIn("CANARY_SECRET", message)
        self.assertIn("base-sepolia.g.alchemy.com", message)
        provenance = rpc.provenance()
        self.assertNotIn("CANARY_SECRET", json.dumps(provenance))
        self.assertIn("base-sepolia.g.alchemy.com", provenance["endpoints"][0])


class ChainRpcErrorShapeTests(unittest.TestCase):
    """execution.chain.rpc must raise RpcError whatever shape the error field has."""

    class _Response:
        def __init__(self, body):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    def _call_with_body(self, body):
        import urllib.request
        original = urllib.request.urlopen
        urllib.request.urlopen = lambda request, timeout=None: self._Response(body)
        try:
            return chain_client.rpc("https://node.invalid", "eth_chainId", [])
        finally:
            urllib.request.urlopen = original

    def test_non_object_error_becomes_a_typed_rpc_error(self):
        with self.assertRaises(chain_client.RpcError) as ctx:
            self._call_with_body(json.dumps(
                {"jsonrpc": "2.0", "id": 1, "error": "boom"}).encode("utf-8"))
        self.assertIn("boom", str(ctx.exception))

    def test_object_error_still_carries_its_code(self):
        with self.assertRaises(chain_client.RpcError) as ctx:
            self._call_with_body(json.dumps(
                {"jsonrpc": "2.0", "id": 1,
                 "error": {"code": -32000, "message": "nope"}}).encode("utf-8"))
        self.assertEqual(ctx.exception.code, -32000)


class LedgerWindowTests(unittest.TestCase):
    """The persisted window is part of the spending contract — refuse drift."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_review_")
        self.path = os.path.join(self.tmp, "ledger.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, window_hours=24.0):
        ledger = executor.PeriodLedger(self.path, window=timedelta(hours=window_hours))
        ledger.record(executor.parse_iso("2026-10-17T12:00:00Z"), "intent-1", 100.0)

    def test_mismatched_window_is_refused(self):
        self._write(window_hours=24.0)
        with self.assertRaises(executor.LedgerError):
            executor.PeriodLedger(self.path, window=timedelta(hours=1.0))

    def test_matching_window_loads(self):
        self._write(window_hours=24.0)
        reopened = executor.PeriodLedger(self.path)
        self.assertEqual(reopened.spent(executor.parse_iso("2026-10-17T13:00:00Z")), 100.0)

    def test_legacy_ledger_without_window_field_loads(self):
        with open(self.path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump({"schema": "orvyren-executor-ledger/v1",
                       "entries": [{"ts_utc": "2026-10-17T12:00:00Z",
                                    "intent_id": "intent-1", "amount": 5.0}]}, handle)
        reopened = executor.PeriodLedger(self.path)
        self.assertEqual(len(reopened.entries()), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
