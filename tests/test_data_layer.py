#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test bench: on-chain data layer + episode reconstruction evidence.

What is covered
---------------
* ``orvyren.data.rpc``   -- ABI codec, endpoint fallback, contract-error handling,
  block<->timestamp search, ``eth_getLogs`` pagination (through an injected fake
  transport: **this bench never touches the network**);
* ``orvyren.data.aave``  -- packed reserve configuration (LTV, liquidation
  threshold, **frozen bit**, caps), reserve state (utilisation, cap_ratio) and the
  binary search that dates a freeze to the second;
* ``orvyren.data.curve`` -- ``get_dy`` quote -> realisable price and discount;
* ``orvyren.data.chainlink`` -- round data, and the measured Aave-side quirk where
  ``latestRoundData()`` reverts on the capped rsETH feed;
* ``scripts/reconstruct_*_episode.py`` -- the offline (``--from-cache``) rebuild of
  both episodes against the archived W2-A/W2-B measurements;
* the evidence JSON in ``evidence/`` -- shape, completeness and internal
  consistency (cap_ratio = supply/cap, discount = 1 - price, ladder monotonicity).

Fixtures are the archived measurements in ``fixtures/raw_w2a`` and
``fixtures/raw_w2b`` plus the evidence files themselves; every expected number is
either read from those files or rebuilt here from an ABI payload.

Execution: ``python -m unittest discover -s tests -v``
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
SCRIPTS = os.path.join(ROOT, "scripts")
for path in (SRC, SCRIPTS):
    if path not in sys.path:
        sys.path.insert(0, path)

from orvyren.data import (ArchiveRpc, ChainlinkFeed, CurvePool, RpcError, RpcRangeError,  # noqa: E402
                          parse_utc, time_grid, utc_iso)
from orvyren.data import aave as aave_module  # noqa: E402
from orvyren.data.aave import AaveV3Pool, ReserveConfig, find_freeze_block  # noqa: E402
from orvyren.data.chainlink import FEED_RSETH_CAPPED_ETH_USD, FEED_STETH_ETH, FeedError  # noqa: E402
from orvyren.data.curve import STETH_POOL_ETH_INDEX, STETH_POOL_STETH_INDEX, steth_pool  # noqa: E402
from orvyren.data.rpc import (MAX_GET_LOGS_RANGE, decode_address, decode_int,  # noqa: E402
                              decode_string, decode_uint, decode_words, encode_address,
                              encode_int, encode_uint)

import recon_common  # noqa: E402
import reconstruct_rseth_episode as rseth_script  # noqa: E402
import reconstruct_steth_episode as steth_script  # noqa: E402

RAW_W2A = os.path.join(ROOT, "fixtures", "raw_w2a")
RAW_W2B = os.path.join(ROOT, "fixtures", "raw_w2b")
EVIDENCE = os.path.join(ROOT, "evidence")

RSETH = "0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
STETH_ETH_FEED = FEED_STETH_ETH
CAP_FEED = FEED_RSETH_CAPPED_ETH_USD
STETH_POOL_ADDRESS = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"
ETH_PLACEHOLDER = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
RSETH_ATOKEN = "0x2D62109243b87C4bA3EE7bA1D91B0dD0A074d7b1"
RSETH_VDEBT = "0x6de3E52a1b7294A34e271a508082B1Ff4a37E30e"

#: Block/timestamp pair verified on-chain (research/W2B, signal 2.2).
FREEZE_FIRST_BLOCK = 24908723
FREEZE_FIRST_UTC = "2026-04-18T19:03:59Z"
#: Values measured by W2-B at the supplyCap saturation (2026-04-18T18:00Z).
SATURATION_SUPPLY = 529_993.9826991734
SATURATION_CAP_RATIO = 0.999988646602214
#: Worst Curve discount of the stETH episode (block 14 970 000, 2022-06-15T22:43:58Z).
WORST_DISCOUNT_BPS_1_STETH = 618.5454112860477


def load_fixture(name, *directories):
    """Read a JSON fixture: search the given dirs, then research/, then the repo root."""
    for directory in list(directories) + [RAW_W2A, RAW_W2B, ROOT]:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise unittest.SkipTest(f"fixture {name} not found (looked in {directories}, raw_w2a, raw_w2b)")


def abi_uint(value):
    return f"{int(value):064x}"


def words_to_hex(words):
    return "0x" + "".join(abi_uint(word) for word in words)


def abi_string(text):
    payload = text.encode("utf-8").hex()
    padded = payload + "0" * ((64 - len(payload) % 64) % 64)
    return "0x" + abi_uint(32) + abi_uint(len(text)) + padded


def hex_address_to_word(address):
    return int(encode_address(address), 16)


class StubRpc:
    """Minimal client double: canned answers keyed by ``(address, selector)``."""

    def __init__(self, responses=None, timestamps=None):
        self.responses = responses or {}
        self.timestamps = timestamps or {}
        self.calls = []

    def eth_call(self, to, data, block="latest"):
        key = (to.lower(), data[:10].lower())
        self.calls.append(("eth_call", key, block))
        answer = self.responses.get(key)
        if answer is None:
            raise AssertionError(f"unexpected eth_call to {to} with selector {data[:10]}")
        if isinstance(answer, Exception):
            raise answer
        if callable(answer):
            return answer(to, data, block)
        return answer

    def block_timestamp(self, block, *args, **kwargs):
        self.calls.append(("block_timestamp", block))
        if block in self.timestamps:
            return self.timestamps[block]
        raise AssertionError(f"unexpected block_timestamp({block})")


def fake_transport(*, fail_urls=(), chain=None, logs=None, record=None, head=40_000_000, block_error=None):
    """Transport answering the four RPC methods the data layer uses.

    ``chain`` maps a block number to its timestamp (or is a callable, to model a
    synthetic linear chain).
    """
    chain_fn = chain if callable(chain) else (lambda block: (chain or {}).get(block))
    logs = logs if logs is not None else {}

    def transport(url, payload, timeout):
        request = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
        method = request["method"]
        params = request.get("params") or []
        if record is not None:
            record.append((url, method, params))
        if url in fail_urls:
            raise OSError("connection refused")
        if method == "eth_blockNumber":
            return json.dumps({"jsonrpc": "2.0", "id": 1, "result": hex(head)}).encode()
        if method == "eth_getBlockByNumber":
            if block_error is not None:
                return json.dumps({"jsonrpc": "2.0", "id": 1, "error": block_error}).encode()
            block = int(params[0], 16)
            return json.dumps(
                {"jsonrpc": "2.0", "id": 1, "result": {"number": hex(block), "timestamp": hex(chain_fn(block))}}
            ).encode()
        if method == "eth_call":
            return json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + "0" * 64}).encode()
        if method == "eth_getLogs":
            span = int(params[0]["toBlock"], 16) - int(params[0]["fromBlock"], 16) + 1
            if span > MAX_GET_LOGS_RANGE:
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "error": {"code": -32000, "message": "ranges over 10000 blocks are not supported on free plan"},
                    }
                ).encode()
            return json.dumps({"jsonrpc": "2.0", "id": 1, "result": logs.get(params[0]["fromBlock"], [])}).encode()
        raise AssertionError(f"unexpected method {method}")

    return transport


class CodecTests(unittest.TestCase):
    """ABI encoding/decoding primitives."""

    def test_uint_and_int_round_trip(self):
        self.assertEqual(encode_uint(0), "0" * 64)
        self.assertEqual(int(encode_uint(530000), 16), 530000)
        self.assertEqual(decode_uint("0x" + encode_uint(2 ** 200)), 2 ** 200)
        # int128 indices of Curve: a negative value must be sign-extended to the full word.
        self.assertEqual(encode_int(2), "0" * 63 + "2")
        self.assertEqual(int(encode_int(-1), 16), 2 ** 256 - 1)
        self.assertEqual(decode_int("0x" + encode_int(-1000)), -1000)

    def test_encoding_rejects_garbage(self):
        for value, call in ((-1, encode_uint), (2 ** 256, encode_uint), (-(2 ** 255) - 1, encode_int)):
            with self.assertRaises(ValueError):
                call(value)
        for address in ("0x1234", "not-an-address", "0x" + "z" * 40):
            with self.assertRaises(ValueError):
                encode_address(address)

    def test_address_codec_matches_the_measured_calldata(self):
        # getAssetPrice(rsETH): selector + the address left-padded to one word.
        self.assertEqual(encode_address(RSETH), "0" * 24 + RSETH[2:].lower())
        self.assertEqual(decode_address(hex_address_to_word(RSETH)), RSETH.lower())

    def test_words_splitting_and_length_guard(self):
        payload = words_to_hex([1, 2, 3, 4, 5])
        self.assertEqual(decode_words(payload), [1, 2, 3, 4, 5])
        self.assertEqual(decode_uint(payload, 2), 3)
        with self.assertRaises(ValueError):
            decode_words("0x123")

    def test_decode_string_on_the_capped_feed_payload(self):
        self.assertEqual(decode_string(abi_string("Capped rsETH / ETH / USD")), "Capped rsETH / ETH / USD")
        self.assertEqual(decode_string(abi_string("STETH / ETH")), "STETH / ETH")


class ArchiveRpcTests(unittest.TestCase):
    """Client behaviour: fallback, error typing, block search, log pagination."""

    def test_fallback_to_the_second_endpoint(self):
        urls = ("https://first.invalid", "https://second.invalid")
        rpc = ArchiveRpc(urls, retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(fail_urls={"https://first.invalid"}))
        self.assertEqual(rpc.eth_block_number(), 40_000_000)
        self.assertEqual(rpc.last_url, "https://second.invalid")
        self.assertEqual(list(rpc.url_hits), ["https://second.invalid"])
        self.assertEqual(rpc.errors, 1)
        self.assertEqual(rpc.provenance()["calls"], 2)

    def test_unreachable_endpoints_raise_a_named_error(self):
        rpc = ArchiveRpc(("https://a.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(fail_urls={"https://a.invalid"}))
        with self.assertRaises(RpcError) as ctx:
            rpc.eth_block_number()
        self.assertIn("eth_blockNumber", str(ctx.exception))
        self.assertIn("https://a.invalid", str(ctx.exception))

    def test_contract_revert_stops_after_the_first_endpoint(self):
        # A revert is the contract's answer, identical everywhere: no point trying the
        # second endpoint (measured case: latestRoundData() on the capped rsETH feed).
        seen = []
        rpc = ArchiveRpc(("https://a.invalid", "https://b.invalid"), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(record=seen, block_error={"code": 3, "message": "execution reverted"}))
        with self.assertRaises(RpcError) as ctx:
            rpc.get_block(1)
        self.assertIn("execution reverted", str(ctx.exception))
        self.assertEqual(len(seen), 1, "a contract-level error must not be replayed on the next endpoint")

    def test_node_error_moves_on_to_the_next_endpoint(self):
        seen = []

        def transport(url, payload, timeout):
            request = json.loads(payload.decode())
            seen.append(url)
            if url == "https://a.invalid":
                return json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"message": "archive pruned"}}).encode()
            return json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x1"}).encode()

        rpc = ArchiveRpc(("https://a.invalid", "https://b.invalid"), retries=0, backoff=0.0, timeout=1,
                         transport=transport)
        self.assertEqual(rpc.eth_block_number(), 1)
        self.assertEqual(seen, ["https://a.invalid", "https://b.invalid"])

    def test_block_at_timestamp_finds_the_last_block_at_or_before(self):
        genesis = 1438269988
        chain = lambda block: genesis + 12 * block  # synthetic 12 s chain
        rpc = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(chain=chain))
        for offset in (0, 1, 11, 12, 5000, 123456):
            target = genesis + 12 * 1_000_000 + offset
            block = rpc.block_at_timestamp(target)
            self.assertLessEqual(chain(block), target, f"block {block} starts after the target {target}")
            self.assertGreater(chain(block + 1), target, f"block {block} is not the last one before {target}")

    def test_block_at_timestamp_reuses_cached_timestamps(self):
        genesis = 1438269988
        calls = []
        rpc = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(chain=lambda block: genesis + 12 * block, record=calls))
        first = rpc.block_at_timestamp(genesis + 12 * 500_000)
        before = len(calls)
        second = rpc.block_at_timestamp(genesis + 12 * 500_000)
        self.assertEqual(first, second)
        self.assertLess(len(calls) - before, 6, "a repeated search must cost almost nothing (timestamps cached)")
        self.assertLess(len(calls), 80, "a single search must stay around 20 calls, not hundreds")

    def test_get_logs_paginates_at_the_free_tier_limit(self):
        calls = []
        rpc = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(chain=lambda block: block, record=calls, logs={"0x0": [{"a": 1}]}))
        logs = rpc.get_logs(from_block=0, to_block=24_999, address=RSETH)
        self.assertEqual(logs, [{"a": 1}])
        ranges = [(int(p[0]["fromBlock"], 16), int(p[0]["toBlock"], 16))
                  for _, method, p in calls if method == "eth_getLogs"]
        self.assertEqual(ranges, [(0, 9999), (10000, 19999), (20000, 24999)])
        for start, stop in ranges:
            self.assertLessEqual(stop - start + 1, MAX_GET_LOGS_RANGE)

    def test_get_logs_refuses_an_oversized_chunk_and_types_node_refusals(self):
        rpc = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(chain=lambda block: block))
        with self.assertRaises(ValueError):
            rpc.get_logs(from_block=0, to_block=10, chunk_size=MAX_GET_LOGS_RANGE + 1)
        refusing = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                              transport=lambda url, payload, timeout: json.dumps(
                                  {"jsonrpc": "2.0", "id": 1, "error": {"message": "range too large"}}).encode())
        with self.assertRaises(RpcRangeError) as ctx:
            refusing.get_logs(from_block=0, to_block=5_000, chunk_size=5_000)
        self.assertIn("free public endpoints cap", str(ctx.exception))

    def test_invalid_arguments_are_rejected_early(self):
        rpc = ArchiveRpc(("https://chain.invalid",), retries=0, backoff=0.0, timeout=1,
                         transport=fake_transport(chain=lambda block: block))
        with self.assertRaises(ValueError):
            rpc.eth_call("not-an-address", "0x18160ddd", 1)
        with self.assertRaises(ValueError):
            rpc.eth_call(RSETH, "18160ddd", 1)          # missing 0x
        with self.assertRaises(ValueError):
            rpc.block_at_timestamp(1, low=10, high=10)


class AaveTests(unittest.TestCase):
    """Aave V3 reserve decoding, against the raw configuration words archived by W2-B."""

    def setUp(self):
        self.configs = load_fixture("aave_rseth_reserveconfig.json", RAW_W2B)
        self.by_label = {row["utc"]: row for row in self.configs}
        self.by_block = {row["block"]: row for row in self.configs}

    def test_reserve_config_parses_the_archived_words(self):
        unfrozen = ReserveConfig.from_word(int(self.by_block[24900327]["config"]["raw"], 16))
        frozen = ReserveConfig.from_word(int(self.by_block[24911049]["config"]["raw"], 16))
        self.assertEqual(
            (unfrozen.ltv_bps, unfrozen.liquidation_threshold_bps, unfrozen.liquidation_bonus_bps),
            (0, 7500, 10750),
        )
        self.assertEqual(unfrozen.decimals, 18)
        self.assertEqual(unfrozen.supply_cap, 530_000)
        self.assertEqual(unfrozen.borrow_cap, 1)
        self.assertEqual(unfrozen.e_mode_category, 0)
        self.assertTrue(unfrozen.is_active)
        self.assertFalse(unfrozen.borrowing_enabled)
        self.assertFalse(unfrozen.is_frozen, "rsETH was not frozen before the exploit window")
        self.assertTrue(frozen.is_frozen, "the rsETH reserve is frozen once the episode is over")
        self.assertTrue(ReserveConfig.from_word(int(self.by_block[24957514]["config"]["raw"], 16)).is_paused)
        self.assertEqual(ReserveConfig.from_word(0).supply_cap, 0)

    def test_reserve_config_agrees_with_the_archive_decoding(self):
        row = self.by_label["2026-04-18T12:00:00"]
        config = ReserveConfig.from_word(int(row["config"]["raw"], 16))
        self.assertAlmostEqual(config.liquidation_threshold_bps / 10_000, row["config"]["lt_thr"], places=6)
        self.assertAlmostEqual(config.liquidation_bonus_bps / 10_000, row["config"]["liq_bonus"], places=6)
        self.assertEqual(config.supply_cap, row["config"]["supplyCap"])
        self.assertEqual(config.decimals, row["config"]["decimals"])
        self.assertEqual(config.is_frozen, row["config"]["isFrozen"])

    def test_reserve_state_matches_the_archived_saturation_point(self):
        rows = load_fixture("aave_rseth_apr2026_v2.json", RAW_W2B)
        row = [entry for entry in rows if entry["utc"] == "2026-04-18T18:00:00"][0]
        supply = int(round(row["rsETH_supply"] * 10 ** 18))
        cash = int(round(row["rsETH_cash"] * 10 ** 18))
        debt = 42_077_077_642_537_130          # rsETH variable debt measured by W2-B (18 decimals)
        # The reserve configuration of 17 April (not yet frozen) drives the flags here.
        config_word = int(self.by_block[24900327]["config"]["raw"], 16)
        stub = StubRpc(
            responses={
                (aave_module.AAVE_V3_ETHEREUM_POOL.lower(), aave_module.SEL_GET_RESERVE_DATA): lambda to, data, block: words_to_hex(
                    [config_word, 10 ** 27, 0, 10 ** 27, 0, 0, 0, 0,
                     hex_address_to_word(RSETH_ATOKEN), 0, hex_address_to_word(RSETH_VDEBT), 0, 0]
                ),
                (RSETH_ATOKEN.lower(), aave_module.SEL_TOTAL_SUPPLY): "0x" + abi_uint(supply),
                (RSETH_VDEBT.lower(), aave_module.SEL_TOTAL_SUPPLY): "0x" + abi_uint(debt),
                (RSETH.lower(), aave_module.SEL_BALANCE_OF): "0x" + abi_uint(cash),
                (aave_module.AAVE_V3_ETHEREUM_ORACLE.lower(), aave_module.SEL_GET_ASSET_PRICE): "0x" + abi_uint(
                    int(round(row["oracle_px_usd"] * 10 ** 8))
                ),
            }
        )
        state = AaveV3Pool(stub).reserve_state(RSETH, row["block"])
        self.assertAlmostEqual(state["a_token_supply"], row["rsETH_supply"], places=6)
        # Two utilisations are recorded, and both are checked against the archive:
        # ``utilisation`` (variable debt / aToken supply) and ``utilisation_cash_gap``
        # (1 - cash / aToken supply), which is the U of the archived snapshot.
        self.assertAlmostEqual(state["utilisation"], debt / supply, places=15)
        self.assertAlmostEqual(state["utilisation_cash_gap"], row["U"], places=12)
        self.assertAlmostEqual(state["oracle_price"], row["oracle_px_usd"], places=6)
        self.assertAlmostEqual(state["cap_ratio"], SATURATION_CAP_RATIO, places=12)
        self.assertGreater(state["cap_ratio"], 0.9999, "the 18:00 UTC point saturates the 530 000 rsETH cap")
        self.assertFalse(state["is_frozen"])
        self.assertEqual(state["decimals"], 18)
        self.assertEqual(state["a_token"].lower(), RSETH_ATOKEN.lower())

    def test_reserve_state_without_oracle_skips_the_oracle_call(self):
        config_word = int(self.by_block[24900327]["config"]["raw"], 16)
        stub = StubRpc(
            responses={
                (aave_module.AAVE_V3_ETHEREUM_POOL.lower(), aave_module.SEL_GET_RESERVE_DATA): words_to_hex(
                    [config_word, 0, 0, 0, 0, 0, 0, 0, hex_address_to_word(RSETH_ATOKEN), 0,
                     hex_address_to_word(RSETH_VDEBT), 0, 0]
                ),
                (RSETH_ATOKEN.lower(), aave_module.SEL_TOTAL_SUPPLY): "0x" + abi_uint(1000 * 10 ** 18),
                (RSETH_VDEBT.lower(), aave_module.SEL_TOTAL_SUPPLY): "0x" + abi_uint(500 * 10 ** 18),
                (RSETH.lower(), aave_module.SEL_BALANCE_OF): "0x" + abi_uint(500 * 10 ** 18),
            }
        )
        state = AaveV3Pool(stub).reserve_state(RSETH, 1, with_oracle=False)
        self.assertNotIn("oracle_price", state)
        self.assertAlmostEqual(state["utilisation"], 0.5, places=12)
        self.assertAlmostEqual(state["utilisation_cash_gap"], 0.5, places=12)
        self.assertEqual(len(stub.calls), 4, "reserve_state must not read the oracle when asked to skip it")

    def test_find_freeze_block_bisects_and_dates_both_sides(self):
        flip = FREEZE_FIRST_BLOCK
        frozen_word = int(self.by_label["2026-04-18T12:00:00"]["config"]["raw"], 16)     # frozen (block 24 911 049)
        unfrozen_word = int(self.by_label["2026-04-17T00:00:00"]["config"]["raw"], 16)   # not frozen

        def reserve_data(to, data, block):
            number = int(block, 16) if isinstance(block, str) else int(block)
            word = frozen_word if number >= flip else unfrozen_word
            return words_to_hex([word] + [0] * 12)

        stub = StubRpc(
            responses={(aave_module.AAVE_V3_ETHEREUM_POOL.lower(), aave_module.SEL_GET_RESERVE_DATA): reserve_data},
            timestamps={flip - 1: parse_utc(FREEZE_FIRST_UTC) - 12, flip: parse_utc(FREEZE_FIRST_UTC)},
        )
        result = find_freeze_block(AaveV3Pool(stub), RSETH, low=24_900_327, high=24_911_049)
        self.assertEqual(result["first_frozen_block"], flip)
        self.assertEqual(result["last_unfrozen_block"], flip - 1)
        self.assertEqual(utc_iso(result["first_frozen_ts"]), FREEZE_FIRST_UTC)
        self.assertLess(result["steps"], 20, "the search must stay logarithmic, not scan the range")

    def test_measured_constants(self):
        self.assertEqual(aave_module.AAVE_V3_ETHEREUM_POOL, "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2")
        self.assertEqual(aave_module.AAVE_V3_ETHEREUM_ORACLE, "0x54586bE62E3c3580375aE3723C145253060Ca0C2")
        self.assertEqual(aave_module.ORACLE_UNIT, 10 ** 8)


class CurveTests(unittest.TestCase):
    """``get_dy`` -> realisable price and discount, against the W2-B measurements."""

    def setUp(self):
        self.rows = load_fixture("steth_juin2022.json", RAW_W2B)
        self.by_block = {row["block"]: row for row in self.rows}

    def stub_for(self, row):
        def coins(to, data, block):
            index = int(data[10:], 16)
            address = ETH_PLACEHOLDER if index == 0 else STETH_TOKEN
            return "0x" + abi_uint(hex_address_to_word(address))

        return StubRpc(
            responses={
                (STETH_POOL_ADDRESS.lower(), "0x5e0d443f"): lambda to, data, block: "0x" + abi_uint(
                    int(round(row["prix_vente_1stETH"] * 10 ** 18))
                ),
                (STETH_POOL_ADDRESS.lower(), "0xc6610657"): coins,
            }
        )

    def test_quote_reproduces_the_archived_sale_prices(self):
        for block, row in sorted(self.by_block.items()):
            quote = CurvePool(self.stub_for(row)).quote(STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, 10 ** 18, block)
            self.assertAlmostEqual(quote.amount_out, row["prix_vente_1stETH"], places=12, msg=f"block {block}")
            self.assertAlmostEqual(quote.discount_bps / 10_000, 1 - row["prix_vente_1stETH"], places=12, msg=f"block {block}")
            self.assertAlmostEqual(quote.discount_bps / 100, row["decote_vente_1_pct"], places=3, msg=f"block {block}")

    def test_june_2022_and_the_calm_baseline(self):
        worst = self.by_block[14_970_000]           # 2022-06-15T22:43:58Z
        quote = CurvePool(self.stub_for(worst)).quote(STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, 10 ** 18, 14_970_000)
        self.assertAlmostEqual(quote.discount_bps, WORST_DISCOUNT_BPS_1_STETH, places=6)
        self.assertGreater(quote.discount_bps, 600, "15 June 2022: selling 1 stETH cost ~6.2 %")
        calm = self.by_block[14_720_000]            # 2022-05-05T23:00:02Z
        calm_quote = CurvePool(self.stub_for(calm)).quote(STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, 10 ** 18, 14_720_000)
        self.assertLess(calm_quote.discount_bps, 10, "calm baseline: ~0.07 % before the episode")
        may = self.by_block[14_820_000]             # 2022-05-21T23:06:06Z
        self.assertGreater(1 - may["prix_vente_1stETH"], 0.02, "first measured point above 2 %")

    def test_discount_grows_with_the_size_sold(self):
        for block, row in sorted(self.by_block.items()):
            small = 1 - row["prix_vente_1stETH"]
            large = 1 - row["prix_vente_1000stETH"]
            self.assertGreaterEqual(large + 1e-12, small, f"block {block}: 1 000 stETH must not be cheaper than 1 stETH")

    def test_coin_order_of_the_steth_pool(self):
        pool = steth_pool(self.stub_for(self.rows[0]))
        self.assertEqual(pool.coins(0, 14_720_000).lower(), ETH_PLACEHOLDER.lower())
        self.assertEqual(pool.coins(1, 14_720_000).lower(), STETH_TOKEN.lower())
        self.assertEqual((STETH_POOL_ETH_INDEX, STETH_POOL_STETH_INDEX), (0, 1))

    def test_ladder_sends_one_call_per_size_with_the_right_decimals(self):
        row = self.by_block[14_970_000]
        calls = []

        def dy(to, data, block):
            calls.append(data)
            size = int(data[138:202], 16)          # selector(8) + i(64) + j(64) then dx(64)
            price = row["prix_vente_1stETH"] if size <= 10 ** 18 else row["prix_vente_1000stETH"]
            return "0x" + abi_uint(int(round(price * size)))

        quotes = steth_pool(StubRpc(responses={(STETH_POOL_ADDRESS.lower(), "0x5e0d443f"): dy})).ladder(
            STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, (1.0, 1000.0), 14_970_000
        )
        self.assertEqual(len(quotes), 2)
        self.assertEqual(len(calls), 2)
        self.assertAlmostEqual(quotes[0].amount_in, 1.0)
        self.assertAlmostEqual(quotes[1].amount_in, 1000.0)
        self.assertEqual(calls[0][10:74], "0" * 63 + "1")     # index_in = 1 (stETH)
        self.assertEqual(calls[0][74:138], "0" * 64)          # index_out = 0 (ETH)


class ChainlinkTests(unittest.TestCase):
    """Round data, and the capped rsETH feed that only answers ``latestAnswer()``."""

    #: Exact words of latestRoundData() on the STETH / ETH feed at block 14 970 000.
    STETH_ROUND_WORDS = [18446744073709551917, 944028156034378400, 1655284037, 1655284037, 18446744073709551917]

    def test_round_data_is_decoded_with_the_feed_decimals(self):
        stub = StubRpc(
            responses={
                (STETH_ETH_FEED.lower(), "0xfeaf968c"): words_to_hex(self.STETH_ROUND_WORDS),
                (STETH_ETH_FEED.lower(), "0x313ce567"): "0x" + abi_uint(18),
                (STETH_ETH_FEED.lower(), "0x7284e416"): abi_string("STETH / ETH"),
            }
        )
        feed = ChainlinkFeed(stub, STETH_ETH_FEED, name="steth_eth")
        round_data = feed.latest_round_data(14_970_000)
        self.assertEqual(round_data.updated_at, 1655284037)
        self.assertEqual(round_data.decimals, 18)
        self.assertEqual(round_data.description, "STETH / ETH")
        self.assertAlmostEqual(round_data.answer, 0.9440281560343784, places=15)
        self.assertEqual(round_data.age_seconds(1655284037 + 49_000), 49_000)
        payload = feed.price(14_970_000, block_timestamp=1655284037 + 49_000)
        self.assertEqual(payload["method"], "latestRoundData")
        self.assertAlmostEqual(payload["price"], 0.9440281560343784, places=15)

    def test_capped_rseth_feed_falls_back_to_latest_answer(self):
        answer_raw = int("3a869bcba9", 16)
        stub = StubRpc(
            responses={
                (CAP_FEED.lower(), "0xfeaf968c"): RpcError(
                    "eth_call refused by the contract: execution reverted"
                ),
                (CAP_FEED.lower(), "0x313ce567"): "0x" + abi_uint(8),
                (CAP_FEED.lower(), "0x7284e416"): abi_string("Capped rsETH / ETH / USD"),
                (CAP_FEED.lower(), "0x50d25bcd"): "0x" + abi_uint(answer_raw),
            }
        )
        feed = ChainlinkFeed(stub, CAP_FEED, name="rseth_capped")
        with self.assertRaises(FeedError):
            feed.latest_round_data(FREEZE_FIRST_BLOCK)
        payload = feed.price(FREEZE_FIRST_BLOCK)
        self.assertEqual(payload["method"], "latestAnswer")
        self.assertEqual(payload["description"], "Capped rsETH / ETH / USD")
        self.assertAlmostEqual(payload["price"], 2513.66460329, places=8)
        self.assertIsNone(payload["updated_at"], "the capped feed exposes no freshness")

    def test_feed_addresses_are_the_measured_ones(self):
        self.assertEqual(FEED_STETH_ETH, "0x86392dC19c0b719886221c78AB11eb8Cf5c52812")
        self.assertEqual(FEED_RSETH_CAPPED_ETH_USD, "0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3")


class TimelineTests(unittest.TestCase):
    """Grid helpers used by both reconstruction scripts."""

    def test_utc_helpers_round_trip(self):
        self.assertEqual(utc_iso(0), "1970-01-01T00:00:00Z")
        self.assertEqual(parse_utc("2026-04-18T19:03:59Z"), 1_776_539_039)
        self.assertEqual(utc_iso(parse_utc("2022-06-15T22:43:58Z")), "2022-06-15T22:43:58Z")
        self.assertEqual(parse_utc("2026-04-18T19:03:59"), parse_utc("2026-04-18T19:03:59Z"))

    def test_time_grid_is_inclusive_and_rejects_bad_input(self):
        hourly = time_grid("2026-04-17T00:00:00Z", "2026-04-18T00:00:00Z", 3600)
        self.assertEqual(len(hourly), 25)
        self.assertEqual(utc_iso(hourly[0]), "2026-04-17T00:00:00Z")
        self.assertEqual(utc_iso(hourly[-1]), "2026-04-18T00:00:00Z")
        with self.assertRaises(ValueError):
            time_grid("2026-04-18T00:00:00Z", "2026-04-17T00:00:00Z", 3600)
        with self.assertRaises(ValueError):
            time_grid("2026-04-18T00:00:00Z", "2026-04-19T00:00:00Z", 0)

    def test_resolve_blocks_checks_the_floor_and_stays_consistent(self):
        genesis = 1438269988

        class Client:
            def block_at_timestamp(self, ts, low=0, high=None, max_attempts=64):
                return (ts - genesis) // 12

            def block_timestamp(self, block):
                return genesis + 12 * block

        targets = [genesis + 12 * 1_000 + 5, genesis + 12 * 1_000 + 900, genesis + 12 * 1_500 + 5]
        resolved = recon_common.resolve_blocks(targets, Client())
        self.assertEqual(sorted(resolved), sorted(targets))
        for ts, payload in resolved.items():
            self.assertLessEqual(payload["block_ts"], ts)
            self.assertGreater(payload["block_ts"] + 12, ts)

    def test_resolve_blocks_uses_the_estimate_then_verifies_every_point(self):
        genesis = 1438269988

        class Client:
            def __init__(self):
                self.searches = 0
                self.stamp_reads = 0

            def block_at_timestamp(self, ts, low=0, high=None, max_attempts=64):
                self.searches += 1
                return (ts - genesis) // 12      # the synthetic chain is exact

            def block_timestamp(self, block):
                self.stamp_reads += 1
                return genesis + 12 * block

        client = Client()
        base = genesis + 12 * 100_000
        targets = [base, base + 3600, base + 3600 * 2, base + 3600 * 3]
        resolved = recon_common.resolve_blocks(targets, client)
        self.assertEqual([payload["block"] for _, payload in sorted(resolved.items())],
                         [100_000, 100_300, 100_600, 100_900])
        self.assertLessEqual(client.searches, len(targets),
                             "the secant search must not run twice for the same point")
        self.assertLessEqual(client.stamp_reads, 8 * len(targets),
                             "a verified point costs a handful of timestamp reads, not a scan")

    def test_seconds_per_block_switches_at_the_merge(self):
        self.assertEqual(recon_common.seconds_per_block(parse_utc("2022-05-01T00:00:00Z")), 13.35)
        self.assertEqual(
            recon_common.seconds_per_block(parse_utc("2022-09-15T06:42:59Z")), 12.09
        )
        self.assertEqual(recon_common.MERGE_TIMESTAMP, 1663224179)

    def test_resolve_blocks_parallel_covers_every_target(self):
        genesis = 1438269988

        class Client:
            def block_at_timestamp(self, ts, low=0, high=None, max_attempts=64):
                return (ts - genesis) // 12

            def block_timestamp(self, block):
                return genesis + 12 * block

        targets = [genesis + 12 * (1_000 + index) for index in range(25)]
        resolved = recon_common.resolve_blocks_parallel(targets, workers=4, client_factory=Client)
        self.assertEqual(sorted(resolved), sorted(targets))


class ReconstructionScriptTests(unittest.TestCase):
    """The scripts, exercised in their offline (``--from-cache``) mode."""

    @staticmethod
    def quiet(_message):
        pass

    def test_cli_from_cache_writes_a_readable_evidence_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as workdir:
            for module, name, token in (
                (rseth_script, "rseth.json", "rsETH"),
                (steth_script, "steth.json", "stETH"),
            ):
                out = os.path.join(workdir, name)
                code = module.main(["--from-cache", "--out", out, "--quiet"])
                self.assertEqual(code, 0)
                with open(out, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                self.assertTrue(payload["meta"]["complete"])
                self.assertEqual(payload["meta"]["mode"], "cache")
                self.assertIn(token, payload["meta"]["episode"])
                self.assertTrue(payload["series"])
                self.assertIn("limitations", payload)
                self.assertIn("headline", payload)
                self.assertTrue(payload["meta"]["cache_files"])

    def test_rseth_cache_rebuild_matches_the_archived_measurements(self):
        payload = rseth_script.collect_from_cache(self.quiet)
        payload["headline"] = rseth_script.compute_headline(payload)
        series = payload["series"]
        self.assertTrue(payload["meta"]["complete"])
        self.assertEqual(payload["meta"]["mode"], "cache")

        # The supplyCap saturation measured by W2-B on 2026-04-18T18:00Z.
        point = series["2026-04-18T18:00:00Z"]
        self.assertAlmostEqual(point["rsETH"]["a_token_supply"], SATURATION_SUPPLY, places=6)
        self.assertAlmostEqual(point["rsETH"]["cap_ratio"], SATURATION_CAP_RATIO, places=12)
        self.assertEqual(point["rsETH"]["supply_cap"], 530_000)
        self.assertGreater(point["rsETH"]["cap_ratio"], 0.9999)
        self.assertEqual(payload["headline"]["cap_ratio_max_utc"], "2026-04-18T18:00:00Z")

        # The freeze is dated by the binary search archived by W2-B, not by the grid labels.
        self.assertEqual(payload["headline"]["rsETH_frozen_transition_utc"], FREEZE_FIRST_UTC)
        self.assertEqual(payload["headline"]["rsETH_frozen_transition_block"], FREEZE_FIRST_BLOCK)
        self.assertEqual(payload["freeze_transition"]["last_unfrozen_block"], FREEZE_FIRST_BLOCK - 1)

        # Archived labels that disagree with their own block are re-placed, never silently trusted.
        repairs = {(row["archived_label"], row["block"]) for row in payload["label_repairs"]}
        self.assertIn(("2026-04-18T12:00:00Z", 24_911_049), repairs,
                      "the config row labelled 12:00 actually holds block 24 911 049 (19 April)")
        for row in payload["label_repairs"]:
            self.assertEqual(utc_iso(parse_utc(row["placed_at"])), row["placed_at"])
            self.assertGreaterEqual(row["drift_hours"], 2.0)
        # ... and no point is left keyed by a label that contradicts its own block.
        for utc, entry in series.items():
            estimate = entry.get("block_utc_estimate")
            if estimate and not entry.get("archived_label"):
                self.assertLessEqual(abs(parse_utc(estimate) - parse_utc(utc)), 7200, utc)
        self.assertEqual(payload["label_mismatches"], [])

        checked = 0
        for utc, entry in series.items():
            state = entry.get("rsETH") or {}
            if state.get("a_token_supply") and state.get("supply_cap"):
                self.assertAlmostEqual(
                    state["cap_ratio"], state["a_token_supply"] / state["supply_cap"], places=12, msg=utc
                )
                checked += 1
        self.assertGreater(checked, 10, "the archived series must carry enough points to be worth rebuilding")

    def test_rseth_summary_reports_the_episode(self):
        payload = rseth_script.collect_from_cache(self.quiet)
        payload["headline"] = rseth_script.compute_headline(payload)
        text = rseth_script.summarise(payload, "<memory>")
        self.assertIn("rsETH", text)
        self.assertIn(FREEZE_FIRST_UTC, text)
        oracle = payload["headline"].get("rsETH_oracle_at_2026-04-20T00:00:00Z")
        self.assertIsNotNone(oracle, "the 20 April oracle reading is archived and must be reported")
        self.assertGreater(oracle, 2000)
        self.assertLess(oracle, 3000)

    def test_steth_cache_rebuild_reproduces_the_2022_measurements(self):
        payload = steth_script.collect_from_cache(self.quiet)
        payload["headline"] = steth_script.compute_headline(payload)
        series = payload["series"]
        self.assertTrue(payload["meta"]["complete"])
        self.assertEqual(steth_script.GRID_START, "2022-05-01T00:00:00Z")
        self.assertEqual(steth_script.DETAIL_START, "2022-06-10T00:00:00Z")

        baseline = payload["headline"]["baseline"]
        self.assertLess(baseline["discount_bps_1stETH"], 10, "2022-05-05 baseline is ~6.6 bps")

        first_200 = payload["headline"]["first_above_200bps_1stETH"]
        self.assertEqual(first_200["utc"], "2022-05-21T23:06:06Z")
        self.assertGreater(first_200["discount_bps"], 200)
        self.assertLess(first_200["previous_point_discount_bps"], 200)
        self.assertEqual(utc_iso(first_200["ts"]), first_200["utc"])

        worst = payload["headline"]["worst_1stETH"]
        self.assertAlmostEqual(worst["discount_bps"], WORST_DISCOUNT_BPS_1_STETH, places=6)
        self.assertEqual(worst["block"], 14_970_000)
        self.assertEqual(utc_iso(parse_utc(worst["utc"])), "2022-06-15T22:43:58Z")

        for utc, entry in series.items():
            for _size, quote in (entry.get("discount") or {}).items():
                self.assertAlmostEqual(quote["discount_bps"], (1 - quote["price_eth_per_steth"]) * 10_000.0, places=6, msg=utc)
                self.assertAlmostEqual(quote["discount_pct"], quote["discount_bps"] / 100.0, places=9, msg=utc)
        self.assertIn("stETH", steth_script.summarise(payload, "<memory>"))

    def test_scripts_expose_the_measured_reference_blocks(self):
        self.assertIn("24908723", rseth_script.REFERENCE_BLOCKS)
        self.assertIn("24908722", rseth_script.REFERENCE_BLOCKS)
        self.assertEqual(rseth_script.GRID_STEP, 3600)
        self.assertEqual(rseth_script.RESERVES[0][1], RSETH)
        self.assertIn(14_970_000, [row[0] for row in steth_script.REFERENCE_POINTS])
        self.assertEqual(steth_script.SIZES, (1.0, 100.0, 1_000.0, 10_000.0))

    def test_rseth_block_estimate_flags_only_real_drift(self):
        # The anchor itself must not drift; a block a day later must.
        self.assertEqual(rseth_script.estimate_utc(FREEZE_FIRST_BLOCK), parse_utc(FREEZE_FIRST_UTC))
        day_later = rseth_script.estimate_utc(FREEZE_FIRST_BLOCK + 7200)
        self.assertGreater(day_later - parse_utc(FREEZE_FIRST_UTC), 20 * 3600)
        self.assertLess(day_later - parse_utc(FREEZE_FIRST_UTC), 26 * 3600)


class EvidenceFileTests(unittest.TestCase):
    """The committed evidence JSON must be parseable, complete and self-consistent."""

    def evidence(self, name):
        path = os.path.join(EVIDENCE, name)
        if not os.path.isfile(path):
            self.skipTest(f"{name} not generated yet (run scripts/reconstruct_*.py)")
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_rseth_evidence_shape_and_values(self):
        payload = self.evidence("episode_rseth_2026-04.json")
        self.assertTrue(payload["meta"]["complete"])
        self.assertIn(payload["meta"]["mode"], ("rpc", "cache"))
        series = payload["series"]
        self.assertGreater(len(series), 20)
        keys = list(series)
        self.assertEqual(keys, sorted(keys), "series keys must be sorted ISO timestamps, one per step")
        for utc in keys:
            self.assertRegex(utc, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

        freeze = payload["freeze_transition"]
        self.assertEqual(freeze["first_frozen_block"], FREEZE_FIRST_BLOCK)
        self.assertEqual(freeze["first_frozen_utc"], FREEZE_FIRST_UTC)
        self.assertEqual(freeze["last_unfrozen_block"], FREEZE_FIRST_BLOCK - 1)
        headline = payload["headline"]
        self.assertEqual(headline["rsETH_frozen_transition_block"], FREEZE_FIRST_BLOCK)
        self.assertGreater(headline["cap_ratio_max"], 0.9999)
        self.assertEqual(headline["supply_cap_rsETH"], 530_000)

        flags = [(utc, entry["rsETH"].get("is_frozen"))
                 for utc, entry in series.items() if isinstance(entry.get("rsETH"), dict)]
        flags = [(utc, flag) for utc, flag in flags if flag is not None]
        self.assertTrue(flags, "the series must carry the rsETH frozen flag")
        transitions = [index for index in range(1, len(flags)) if flags[index][1] != flags[index - 1][1]]
        self.assertEqual(len(transitions), 1,
                         "the frozen flag must flip exactly once (the freeze is the episode)")
        flip_utc, flip_flag = flags[transitions[0]]
        self.assertTrue(flip_flag)
        self.assertEqual(flip_utc, FREEZE_FIRST_UTC,
                         "the flip must land on the measured freeze second")
        self.assertEqual(utc_iso(parse_utc(flip_utc)), flip_utc)

        for utc, entry in series.items():
            state = entry.get("rsETH") or {}
            if state.get("cap_ratio") is not None and state.get("supply_cap"):
                self.assertAlmostEqual(state["cap_ratio"], state["a_token_supply"] / state["supply_cap"], places=9, msg=utc)
            if state.get("oracle_price") is not None:
                self.assertGreater(state["oracle_price"], 1000, msg=utc)
                self.assertLess(state["oracle_price"], 5000, msg=utc)

    def test_rseth_evidence_keeps_the_retained_price_high_on_18_april(self):
        payload = self.evidence("episode_rseth_2026-04.json")
        window = [
            entry["rsETH"]["oracle_price"]
            for utc, entry in payload["series"].items()
            if isinstance(entry.get("rsETH"), dict) and entry["rsETH"].get("oracle_price") and utc.startswith("2026-04-18")
        ]
        self.assertTrue(window, "18 April must carry oracle readings")
        self.assertGreater(min(window), 2300, "the capped feed stayed in the 2 300-2 600 $ band that day")
        self.assertLess(max(window), 2700)

    def test_steth_evidence_shape_and_values(self):
        payload = self.evidence("episode_steth_2022-06.json")
        self.assertTrue(payload["meta"]["complete"])
        series = payload["series"]
        self.assertGreater(len(series), 20)
        keys = list(series)
        self.assertEqual(keys, sorted(keys))
        expected_sizes = {"1", "100", "1000", "10000"} if payload["meta"]["mode"] == "rpc" else None

        worst = None
        for utc, entry in series.items():
            discount = entry.get("discount") or {}
            if expected_sizes is not None and discount:
                missing = expected_sizes - set(discount)
                self.assertFalse(missing, f"{utc}: missing sizes {missing}")
            for size, quote in discount.items():
                self.assertAlmostEqual(quote["discount_bps"], (1 - quote["price_eth_per_steth"]) * 10_000.0, places=6, msg=utc)
                if worst is None or quote["discount_bps"] > worst[1]:
                    worst = (utc, quote["discount_bps"], size)
        self.assertIsNotNone(worst)
        self.assertGreater(worst[1], 550, f"the episode must contain a >5.5 % discount, got {worst}")

        june15 = [entry for utc, entry in series.items() if utc.startswith("2022-06-15")]
        self.assertTrue(june15, "15 June 2022 (the worst day) must be in the series")
        best_15 = max(
            (quote["discount_bps"] for entry in june15 for quote in (entry.get("discount") or {}).values()),
            default=0,
        )
        self.assertGreater(best_15, 500, "15 June 2022 must show the ~6 % discount measured by W2-B")

        for utc, entry in series.items():
            ordered = sorted(((float(size), quote["discount_bps"]) for size, quote in (entry.get("discount") or {}).items()))
            for (small_size, small), (large_size, large) in zip(ordered, ordered[1:]):
                self.assertLessEqual(small, large + 5.0,
                                     f"{utc}: selling {large_size} stETH must cost at least as much as {small_size}")

    def test_both_evidence_files_are_present_and_readable(self):
        for name, token in (("episode_rseth_2026-04.json", "rsETH"), ("episode_steth_2022-06.json", "stETH")):
            payload = self.evidence(name)
            self.assertIn("generated_utc", payload["meta"])
            self.assertIn(token, payload["meta"]["episode"])
            self.assertGreater(len(payload["series"]), 0)
            self.assertIn("limitations", payload, "an evidence file states what it does not cover")


if __name__ == "__main__":
    unittest.main(verbosity=2)
