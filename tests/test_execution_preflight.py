#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — fail-closed preflight bench (transport injected, offline).

Every control of ``orvyren.execution.preflight`` is exercised through a fake
transport: no socket, no node, no key. The fake answers from a ``method -> value
| exception | callable`` table, so a failure can be planted exactly where the
control looks.

Run: python -m unittest tests.test_execution_preflight -v
"""

import ast
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from orvyren.policy import Intent  # noqa: E402

from orvyren.execution import preflight as preflight_module  # noqa: E402
from orvyren.execution.preflight import (  # noqa: E402
    CHECK_CODES,
    INTENT_TTL_SECONDS,
    MAX_GAS_LIMIT,
    PreflightRpcError,
    abi_encode_balance_of,
    abi_encode_transfer,
    amount_to_base_units,
    decode_uint256,
    hex_data,
    run_preflight,
)

MODULE_PATH = os.path.join(ROOT, "src", "orvyren", "execution", "preflight.py")

TOKEN = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
AGENT = "0x" + "a1" * 20
TREASURY = "0x" + "b2" * 20
RECIPIENT = "0x" + "c3" * 20
CHAIN_ID = 84532
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def make_intent(amount="100", created_at=None, intent_id="I1", recipient=RECIPIENT):
    """Build a bounded intent; ``amount`` stays a string on purpose (no float)."""
    return Intent(
        intent_id=intent_id,
        action="transfer",
        chain_id=CHAIN_ID,
        asset=TOKEN,
        amount=amount,
        recipient=recipient,
        created_at=NOW - timedelta(minutes=30) if created_at is None else created_at,
        justification="preflight bench",
    )


class FakeRpc:
    """Transport stub: one canned answer (value, exception or callable) per method."""

    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, [dict(p) if isinstance(p, dict) else p for p in params]))
        handler = self.responses.get(method)
        if handler is None:
            raise PreflightRpcError("no canned response for {}".format(method))
        if isinstance(handler, BaseException):
            raise handler
        if callable(handler):
            return handler(method, params)
        return handler

    def methods(self):
        return [method for method, _ in self.calls]


def happy_responses(gas_estimate=21000, agent_balance=10 ** 18,
                    token_balance=1000 * 10 ** 6, code="0x6080604052"):
    """Answers that let every control pass."""

    def eth_call(method, params):
        data = str(params[0].get("data", ""))
        if data.startswith("0x70a08231"):
            return hex(token_balance)
        if data.startswith("0xa9059cbb"):
            return "0x" + "0" * 63 + "1"
        raise AssertionError("unexpected eth_call data: {}".format(data))

    return {
        "eth_chainId": hex(CHAIN_ID),
        "eth_getCode": code,
        "eth_estimateGas": hex(gas_estimate),
        "eth_getBalance": hex(agent_balance),
        "eth_call": eth_call,
    }


def run(rpc, **overrides):
    """Call run_preflight with passing defaults, overriding one knob at a time."""
    kwargs = dict(
        policy_verdict="ALLOW",
        processed_intent_ids=(),
        now=NOW,
        rpc=rpc,
        expected_chain_id=CHAIN_ID,
        agent_address=AGENT,
        treasury_address=TREASURY,
        token_address=TOKEN,
        token_decimals=6,
        env={},
    )
    kwargs.update(overrides)
    intent = kwargs.pop("intent", None)
    return run_preflight(make_intent() if intent is None else intent, **kwargs)


def statuses(result):
    return {check.name: check.status for check in result.checks}


def detail_of(result, name):
    for check in result.checks:
        if check.name == name:
            return check.detail
    raise AssertionError("no check named {}".format(name))


class HappyPathTest(unittest.TestCase):
    def test_all_ten_checks_pass(self):
        result = run(FakeRpc(happy_responses()))

        self.assertTrue(result.ok)
        self.assertEqual("", result.failed_code)
        self.assertEqual(10, len(result.checks))
        self.assertEqual(
            ["P1", "P2", "P3", "P4", "P5", "P7", "P12", "P9a", "P9b", "P11"],
            [check.name for check in result.checks])
        for check in result.checks:
            self.assertEqual("PASS", check.status)
            self.assertEqual("", check.code)
            self.assertTrue(check.detail)

    def test_gas_limit_is_ceil_of_1_25_estimate(self):
        result = run(FakeRpc(happy_responses(gas_estimate=21000)))

        self.assertEqual(21000, result.gas_estimate)
        self.assertEqual(26250, result.gas_limit)  # ceil(1.25 * 21000)

    def test_gas_limit_is_capped(self):
        result = run(FakeRpc(happy_responses(gas_estimate=600000)))

        self.assertTrue(result.ok)
        self.assertEqual(600000, result.gas_estimate)
        self.assertEqual(MAX_GAS_LIMIT, result.gas_limit)

    def test_rpc_methods_and_calldata(self):
        rpc = FakeRpc(happy_responses())
        result = run(rpc)

        self.assertTrue(result.ok)
        self.assertEqual(
            ["eth_chainId", "eth_getCode", "eth_estimateGas", "eth_getBalance",
             "eth_call", "eth_call"],
            rpc.methods())
        estimate_call = rpc.calls[2][1][0]
        self.assertEqual(TREASURY, estimate_call["from"])
        self.assertEqual(TOKEN, estimate_call["to"])
        self.assertEqual(hex_data(abi_encode_transfer(RECIPIENT, 100 * 10 ** 6)),
                         estimate_call["data"])
        balance_call = rpc.calls[4][1][0]
        self.assertEqual(hex_data(abi_encode_balance_of(TREASURY)), balance_call["data"])
        simulation_call = rpc.calls[5][1][0]
        self.assertEqual(TREASURY, simulation_call["from"])
        self.assertEqual(hex_data(abi_encode_transfer(RECIPIENT, 100 * 10 ** 6)),
                         simulation_call["data"])


class PolicyAndChainTest(unittest.TestCase):
    def test_deny_blocks_at_p1(self):
        rpc = FakeRpc(happy_responses())
        result = run(rpc, policy_verdict="DENY")

        self.assertFalse(result.ok)
        self.assertEqual("POLICY_NOT_ALLOW", result.failed_code)
        self.assertEqual("FAIL", statuses(result)["P1"])
        self.assertEqual([], rpc.calls)  # nothing is queried once P1 fails
        self.assertEqual(0, result.gas_estimate)
        self.assertEqual(0, result.gas_limit)

    def test_require_approval_blocks_at_p1(self):
        result = run(FakeRpc(happy_responses()), policy_verdict="REQUIRE_APPROVAL")

        self.assertFalse(result.ok)
        self.assertEqual("POLICY_NOT_ALLOW", result.failed_code)
        self.assertIn("REQUIRE_APPROVAL", detail_of(result, "P1"))

    def test_chain_id_mismatch(self):
        result = run(FakeRpc(happy_responses()), expected_chain_id=8453)

        self.assertFalse(result.ok)
        self.assertEqual("CHAIN_ID_MISMATCH", result.failed_code)
        self.assertEqual("FAIL", statuses(result)["P2"])
        self.assertIn("84532", detail_of(result, "P2"))
        self.assertIn("8453", detail_of(result, "P2"))

    def test_chain_id_transport_error_is_fail_closed(self):
        rpc = FakeRpc(happy_responses())
        rpc.responses["eth_chainId"] = PreflightRpcError("rpc transport error calling eth_chainId")
        result = run(rpc)

        self.assertFalse(result.ok)
        self.assertEqual("CHAIN_ID_MISMATCH", result.failed_code)
        self.assertEqual(["eth_chainId"], rpc.methods())

    def test_malformed_chain_id_is_fail_closed(self):
        rpc = FakeRpc(happy_responses())
        rpc.responses["eth_chainId"] = "not-hex"
        result = run(rpc)

        self.assertEqual("CHAIN_ID_MISMATCH", result.failed_code)


class IntentStateTest(unittest.TestCase):
    def test_expired_intent(self):
        intent = make_intent(created_at=NOW - timedelta(seconds=INTENT_TTL_SECONDS + 1))
        result = run(FakeRpc(happy_responses()), intent=intent)

        self.assertFalse(result.ok)
        self.assertEqual("INTENT_EXPIRED", result.failed_code)
        self.assertIn("expired", detail_of(result, "P3"))

    def test_intent_at_the_ttl_boundary_expires(self):
        # expires == now is not ">", so the boundary itself is refused.
        intent = make_intent(created_at=NOW - timedelta(seconds=INTENT_TTL_SECONDS))
        result = run(FakeRpc(happy_responses()), intent=intent)

        self.assertEqual("INTENT_EXPIRED", result.failed_code)

    def test_naive_created_at_is_refused(self):
        intent = make_intent(created_at=datetime(2026, 10, 18, 11, 30))
        result = run(FakeRpc(happy_responses()), intent=intent)

        self.assertFalse(result.ok)
        self.assertEqual("INTENT_EXPIRED", result.failed_code)
        self.assertIn("timezone-naive", detail_of(result, "P3"))

    def test_replayed_intent_is_refused(self):
        result = run(FakeRpc(happy_responses()), processed_intent_ids={"other", "I1"})

        self.assertFalse(result.ok)
        self.assertEqual("INTENT_ALREADY_PROCESSED", result.failed_code)
        self.assertIn("I1", detail_of(result, "P4"))

    def test_processed_ids_accept_none(self):
        result = run(FakeRpc(happy_responses()), processed_intent_ids=None)

        self.assertTrue(result.ok)


class KillSwitchTest(unittest.TestCase):
    def test_pause_flag_blocks(self):
        result = run(FakeRpc(happy_responses()), env={"ORVYREN_K0_PAUSED": "TrUe"})

        self.assertFalse(result.ok)
        self.assertEqual("AGENT_PAUSED", result.failed_code)
        self.assertIn("ORVYREN_K0_PAUSED", detail_of(result, "P5"))

    def test_falsey_pause_values_do_not_block(self):
        for raw in ("0", "false", "no", "off", "", "  "):
            with self.subTest(raw=raw):
                result = run(FakeRpc(happy_responses()), env={"ORVYREN_K0_PAUSED": raw})
                self.assertTrue(result.ok)


class ChainFactsTest(unittest.TestCase):
    def test_missing_contract_code(self):
        for code in ("0x", "0x0", ""):
            with self.subTest(code=code):
                result = run(FakeRpc(happy_responses(code=code)))
                self.assertFalse(result.ok)
                self.assertEqual("TARGET_CODE_MISSING", result.failed_code)
                self.assertEqual("FAIL", statuses(result)["P7"])

    def test_get_code_error_is_fail_closed(self):
        rpc = FakeRpc(happy_responses())
        rpc.responses["eth_getCode"] = PreflightRpcError("boom")
        result = run(rpc)

        self.assertEqual("TARGET_CODE_MISSING", result.failed_code)

    def test_insufficient_gas_balance(self):
        # estimate 21000 -> 42000 wei required, the agent holds less.
        result = run(FakeRpc(happy_responses(agent_balance=41999)))

        self.assertFalse(result.ok)
        self.assertEqual("INSUFFICIENT_GAS_BALANCE", result.failed_code)
        self.assertIn("41999", detail_of(result, "P9a"))
        self.assertIn("42000", detail_of(result, "P9a"))
        self.assertEqual(21000, result.gas_estimate)
        self.assertEqual(26250, result.gas_limit)  # the estimate is still reported

    def test_insufficient_token_balance(self):
        result = run(FakeRpc(happy_responses(token_balance=100 * 10 ** 6 - 1)))

        self.assertFalse(result.ok)
        self.assertEqual("INSUFFICIENT_TOKEN_BALANCE", result.failed_code)
        self.assertEqual("FAIL", statuses(result)["P9b"])
        self.assertIn("100000000", detail_of(result, "P9b"))

    def test_token_balance_uses_balance_of_treasury(self):
        rpc = FakeRpc(happy_responses())
        result = run(rpc)

        self.assertTrue(result.ok)
        self.assertEqual(hex_data(abi_encode_balance_of(TREASURY)), rpc.calls[4][1][0]["data"])


class GasAndSimulationTest(unittest.TestCase):
    def test_gas_estimate_error(self):
        rpc = FakeRpc(happy_responses())
        rpc.responses["eth_estimateGas"] = PreflightRpcError("execution reverted")
        result = run(rpc)

        self.assertFalse(result.ok)
        self.assertEqual("GAS_ESTIMATE_FAILED", result.failed_code)
        self.assertEqual(0, result.gas_estimate)
        self.assertEqual(0, result.gas_limit)
        self.assertEqual("SKIP", statuses(result)["P9a"])

    def test_zero_gas_estimate_is_refused(self):
        result = run(FakeRpc(happy_responses(gas_estimate=0)))

        self.assertEqual("GAS_ESTIMATE_FAILED", result.failed_code)
        self.assertEqual(0, result.gas_limit)

    def test_simulation_revert(self):
        rpc = FakeRpc(happy_responses())

        def eth_call(method, params):
            data = str(params[0].get("data", ""))
            if data.startswith("0xa9059cbb"):
                raise PreflightRpcError("execution reverted: ERC20: transfer amount exceeds balance")
            return hex(1000 * 10 ** 6)

        rpc.responses["eth_call"] = eth_call
        result = run(rpc)

        self.assertFalse(result.ok)
        self.assertEqual("SIMULATION_REVERT", result.failed_code)
        self.assertEqual("FAIL", statuses(result)["P11"])

    def test_simulation_returning_false_is_refused(self):
        rpc = FakeRpc(happy_responses())
        rpc.responses["eth_call"] = lambda method, params: (
            "0x" + "0" * 64 if str(params[0].get("data", "")).startswith("0xa9059cbb")
            else hex(1000 * 10 ** 6))
        result = run(rpc)

        self.assertEqual("SIMULATION_REVERT", result.failed_code)
        self.assertIn("false", detail_of(result, "P11"))


class StopAtFirstFailureTest(unittest.TestCase):
    def test_remaining_checks_are_skipped_with_the_blocking_code(self):
        result = run(FakeRpc(happy_responses()), processed_intent_ids=["I1"])

        self.assertEqual("INTENT_ALREADY_PROCESSED", result.failed_code)
        self.assertEqual(
            ["PASS", "PASS", "PASS", "FAIL", "SKIP", "SKIP", "SKIP", "SKIP", "SKIP", "SKIP"],
            [check.status for check in result.checks])
        for check in result.checks[4:]:
            self.assertEqual("SKIP", check.status)
            self.assertEqual("not evaluated: INTENT_ALREADY_PROCESSED", check.detail)
            self.assertIn(check.code, CHECK_CODES)  # a skip still names its own code

    def test_every_failure_code_is_a_catalogue_code(self):
        scenarios = [
            (dict(policy_verdict="DENY"), "POLICY_NOT_ALLOW"),
            (dict(expected_chain_id=1), "CHAIN_ID_MISMATCH"),
            (dict(intent=make_intent(created_at=NOW - timedelta(days=2))), "INTENT_EXPIRED"),
            (dict(processed_intent_ids=["I1"]), "INTENT_ALREADY_PROCESSED"),
            (dict(env={"ORVYREN_K0_PAUSED": "1"}), "AGENT_PAUSED"),
        ]
        for overrides, expected in scenarios:
            with self.subTest(code=expected):
                result = run(FakeRpc(happy_responses()), **overrides)
                self.assertEqual(expected, result.failed_code)
                self.assertIn(result.failed_code, CHECK_CODES)


class AmountConversionTest(unittest.TestCase):
    def test_accepts_exact_decimal_strings(self):
        cases = [
            ("1.0", 6, 1000000),
            ("0.000001", 6, 1),
            ("100", 6, 100 * 10 ** 6),
            ("123.456789", 6, 123456789),
            ("0", 6, 0),
            ("1", 18, 10 ** 18),
        ]
        for value, decimals, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(expected, amount_to_base_units(value, decimals))

    def test_accepts_float_and_int_inputs_without_rounding(self):
        self.assertEqual(1000000, amount_to_base_units(1.0, 6))
        self.assertEqual(1, amount_to_base_units(0.000001, 6))
        self.assertEqual(100 * 10 ** 6, amount_to_base_units(100, 6))
        self.assertEqual(1500000, amount_to_base_units(1.5, 6))

    def test_rejects_scientific_notation(self):
        for value in ("1e-6", "1E6", " 2e3 "):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    amount_to_base_units(value, 6)

    def test_rejects_signs_negatives_and_extra_decimals(self):
        for value in ("-1", "+1", -1, -0.5, "1.0000001", 1.0e-7):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    amount_to_base_units(value, 6)

    def test_rejects_non_decimal_inputs(self):
        for value in ("", "abc", "1,5", None, True):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    amount_to_base_units(value, 6)


class AbiEncodingTest(unittest.TestCase):
    def test_transfer_calldata_vector(self):
        encoded = hex_data(abi_encode_transfer(TOKEN, 1000000))

        self.assertEqual(138, len(encoded))  # 0x + 4-byte selector + 2 words
        self.assertTrue(encoded.startswith("0xa9059cbb"))
        self.assertEqual("0" * 24 + TOKEN[2:].lower(), encoded[10:74])
        self.assertEqual(int("f4240", 16), decode_uint256("0x" + encoded[74:]))

    def test_balance_of_calldata_vector(self):
        encoded = hex_data(abi_encode_balance_of(TREASURY))

        self.assertEqual(74, len(encoded))
        self.assertTrue(encoded.startswith("0x70a08231"))
        self.assertTrue(encoded.endswith(TREASURY[2:].lower()))

    def test_rejects_bad_addresses_and_amounts(self):
        for address in ("0x1234", "not-an-address", "0x" + "zz" * 20, None):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    abi_encode_transfer(address, 1)
        with self.assertRaises(ValueError):
            abi_encode_transfer(RECIPIENT, -1)
        with self.assertRaises(ValueError):
            abi_encode_transfer(RECIPIENT, "12")

    def test_hex_data_and_decode_uint256_helpers(self):
        self.assertEqual("0x00ff", hex_data(b"\x00\xff"))
        self.assertEqual("0xabcd", hex_data("0xABCD"))
        self.assertEqual(0, decode_uint256("0x"))
        self.assertEqual(84532, decode_uint256("0x14a34"))
        self.assertEqual(7, decode_uint256(7))
        with self.assertRaises(ValueError):
            decode_uint256("nope")
        with self.assertRaises(TypeError):
            hex_data(42)


class SerialisationTest(unittest.TestCase):
    def test_to_dict_is_stable_and_json_serialisable(self):
        first = run(FakeRpc(happy_responses())).to_dict()
        second = run(FakeRpc(happy_responses())).to_dict()

        self.assertEqual(json.dumps(first, sort_keys=False), json.dumps(second, sort_keys=False))
        self.assertEqual(list(first.keys()), list(second.keys()))
        self.assertEqual(list(first.keys()), ["ok", "failed_code", "gas_estimate", "gas_limit", "checks"])
        self.assertEqual(set(first["checks"][0].keys()), {"name", "status", "code", "detail"})
        self.assertTrue(json.loads(json.dumps(first))["ok"])

    def test_failed_result_serialises_the_blocking_code(self):
        payload = run(FakeRpc(happy_responses()), policy_verdict="DENY").to_dict()

        self.assertFalse(payload["ok"])
        self.assertEqual("POLICY_NOT_ALLOW", payload["failed_code"])
        self.assertEqual("FAIL", payload["checks"][0]["status"])
        self.assertEqual("POLICY_NOT_ALLOW", payload["checks"][0]["code"])


class JsonRpcTransportTest(unittest.TestCase):
    class _Response:
        def __init__(self, body):
            self.body = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    def test_call_posts_json_rpc_and_returns_result(self):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return self._Response({"jsonrpc": "2.0", "id": 1, "result": "0x14a34"})

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            result = preflight_module.JsonRpc("https://rpc.example.invalid", timeout=3.0).call(
                "eth_chainId", [])

        self.assertEqual("0x14a34", result)
        self.assertEqual(3.0, captured["timeout"])
        body = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual("2.0", body["jsonrpc"])
        self.assertEqual("eth_chainId", body["method"])
        self.assertEqual([], body["params"])
        self.assertEqual("POST", captured["request"].get_method())

    def test_error_envelope_raises_without_leaking_the_endpoint(self):
        def fake_urlopen(request, timeout=None):
            return self._Response({"jsonrpc": "2.0", "id": 1,
                                   "error": {"code": -32000, "message": "boom"}})

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            with self.assertRaises(PreflightRpcError) as raised:
                preflight_module.JsonRpc("https://rpc.example/SECRETKEY").call("eth_call", [])

        self.assertEqual(-32000, raised.exception.code)
        self.assertNotIn("SECRETKEY", str(raised.exception))

    def test_transport_and_decoding_errors_raise(self):
        def failing(request, timeout=None):
            raise OSError("connection refused")

        with mock.patch("urllib.request.urlopen", failing):
            with self.assertRaises(PreflightRpcError):
                preflight_module.JsonRpc("https://rpc.example.invalid").call("eth_chainId", [])

        with mock.patch("urllib.request.urlopen", lambda request, timeout=None: self._Response(b"<html>")):
            with self.assertRaises(PreflightRpcError):
                preflight_module.JsonRpc("https://rpc.example.invalid").call("eth_chainId", [])

        with mock.patch("urllib.request.urlopen", lambda request, timeout=None: self._Response({"id": 1})):
            with self.assertRaises(PreflightRpcError):
                preflight_module.JsonRpc("https://rpc.example.invalid").call("eth_chainId", [])


class SourceHygieneTest(unittest.TestCase):
    def test_module_is_stdlib_only_and_lf(self):
        with open(MODULE_PATH, "rb") as handle:
            raw = handle.read()
        self.assertNotIn(b"\r\n", raw, "preflight.py must be written in LF")

        tree = ast.parse(raw.decode("utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
        self.assertTrue(roots)
        self.assertEqual(set(), roots & {"web3", "eth_account", "requests", "httpx", "aiohttp"})

    def test_rpc_without_call_is_a_type_error(self):
        with self.assertRaises(TypeError):
            run(object())


if __name__ == "__main__":
    unittest.main(verbosity=2)
