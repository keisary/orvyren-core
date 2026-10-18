#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — execution-layer bench: calldata, receipt decoding/verification, guard.

Fully offline by default. The only network test is skipped unless
ORVYREN_LIVE_RPC=1 (and it is read-only: chain id and block number).
Run: python -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from orvyren.policy import (ALLOWED_ASSET, ALLOWED_CHAIN_ID,  # noqa: E402
                            EVAL_MODE_SIMULATION, default_config,
                            evaluate as _policy_evaluate)


def evaluate(*args, **kwargs):
    """Test bench = declared simulation (P1-3): production is the strict
    default of ``orvyren.policy.evaluate``; these benches exercise rule logic
    without a state snapshot, which is the declared simulation mode."""
    kwargs.setdefault("mode", EVAL_MODE_SIMULATION)
    return _policy_evaluate(*args, **kwargs)

from orvyren.execution.chain import (  # noqa: E402
    ChainError,
    erc20_balance_of_data,
    erc20_transfer_calldata,
    normalize_tx_hash,
)
from orvyren.execution.guard import (  # noqa: E402
    ConfigurationError,
    ExecutionConfig,
    PolicyViolationError,
    assert_allowed,
    execution_allowed,
    mask_rpc_url,
    mask_secret,
)
from orvyren.execution.intents import (  # noqa: E402
    EXPECTED_VERDICTS,
    RESERVE_ADDRESS,
    TREASURY_ADDRESS,
    build_demo_intents,
)
from orvyren.execution.verify import (  # noqa: E402
    TRANSFER_TOPIC,
    decode_transfer,
    is_transfer_log,
    value_to_base_units,
    verify_receipt,
)

import run_execution_demo as demo  # noqa: E402

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
CHAIN_ID_HEX = "0x14a34"  # 84532
TX_HASH = "0x" + "ab" * 32
OTHER_TOKEN = "0x0000000000000000000000000000000000000000"
OTHER_ADDRESS = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

# Exact expected values for I1: transfer(0x1111…1111, 100000000) on the USDC test token.
I1_CALLDATA = (
    "0xa9059cbb"
    "0000000000000000000000001111111111111111111111111111111111111111"
    "0000000000000000000000000000000000000000000000000000000005f5e100"
)
I1_BALANCE_OF_DATA = (
    "0x70a08231"
    "0000000000000000000000002222222222222222222222222222222222222222"
)

EXPECTED_TRANSFER = {
    "token": ALLOWED_ASSET,
    "from": TREASURY_ADDRESS,
    "to": RESERVE_ADDRESS,
    "amount_usdc": 100.0,
}


def make_transfer_log(token=ALLOWED_ASSET, sender=TREASURY_ADDRESS, recipient=RESERVE_ADDRESS,
                      value_base_units=100_000_000):
    """Synthetic, well-formed ERC-20 Transfer log."""
    return {
        "address": token,
        "topics": [
            TRANSFER_TOPIC,
            "0x" + sender[2:].lower().rjust(64, "0"),
            "0x" + recipient[2:].lower().rjust(64, "0"),
        ],
        "data": "0x" + format(value_base_units, "064x"),
        "logIndex": "0x0",
    }


def make_receipt(logs=None, status="0x1", chain_id=CHAIN_ID_HEX, include_chain=True):
    receipt = {
        "transactionHash": TX_HASH,
        "blockNumber": "0x1234",
        "status": status,
        "logs": [make_transfer_log()] if logs is None else logs,
    }
    if include_chain:
        receipt["chainId"] = chain_id
    return receipt


class TestValueConversions(unittest.TestCase):
    def test_value_to_base_units_100_usdc(self):
        self.assertEqual(value_to_base_units(100, 6), 100000000)

    def test_value_to_base_units_default_decimals(self):
        self.assertEqual(value_to_base_units(100), 100000000)

    def test_value_to_base_units_fractions(self):
        self.assertEqual(value_to_base_units(1.5, 6), 1500000)
        self.assertEqual(value_to_base_units(0.000001, 6), 1)

    def test_value_to_base_units_rejects_sub_unit_amount(self):
        with self.assertRaises(ValueError):
            value_to_base_units(0.0000001, 6)


class TestCalldata(unittest.TestCase):
    def test_i1_calldata_is_exact(self):
        intent = build_demo_intents()[0]
        calldata = erc20_transfer_calldata(intent.recipient, value_to_base_units(intent.amount))
        self.assertEqual(calldata, I1_CALLDATA)
        self.assertEqual(len(calldata), 138)  # 4-byte selector + 2 x 32 bytes

    def test_i1_calldata_components(self):
        calldata = erc20_transfer_calldata(RESERVE_ADDRESS, 100_000_000)
        self.assertTrue(calldata.startswith("0xa9059cbb"))
        self.assertEqual(calldata[10:74], "0" * 24 + RESERVE_ADDRESS[2:].lower())
        self.assertEqual(calldata[74:], format(100_000_000, "064x"))

    def test_balance_of_data_is_exact(self):
        self.assertEqual(erc20_balance_of_data(TREASURY_ADDRESS), I1_BALANCE_OF_DATA)
        self.assertEqual(len(I1_BALANCE_OF_DATA), 74)

    def test_invalid_recipient_is_rejected_not_repaired(self):
        with self.assertRaises(ChainError):
            erc20_transfer_calldata("0x1234", 1)

    def test_invalid_amount_is_rejected(self):
        with self.assertRaises(ChainError):
            erc20_transfer_calldata(RESERVE_ADDRESS, -1)
        with self.assertRaises(ChainError):
            erc20_transfer_calldata(RESERVE_ADDRESS, 1.5)

    def test_tx_hash_validation_preserves_case(self):
        self.assertEqual(normalize_tx_hash("0x" + "AB" * 32), "0x" + "AB" * 32)
        with self.assertRaises(ChainError):
            normalize_tx_hash("0x123")


class TestTransferDecoding(unittest.TestCase):
    def test_decode_transfer_fields(self):
        decoded = decode_transfer(make_transfer_log())
        self.assertEqual(decoded["from"], TREASURY_ADDRESS.lower())
        self.assertEqual(decoded["to"], RESERVE_ADDRESS.lower())
        self.assertEqual(decoded["value_base_units"], 100_000_000)
        self.assertEqual(decoded["value"], 100.0)
        self.assertEqual(decoded["token"], ALLOWED_ASSET.lower())

    def test_is_transfer_log_matches_token_case_insensitively(self):
        log = make_transfer_log(token=ALLOWED_ASSET)
        self.assertTrue(is_transfer_log(log))
        self.assertTrue(is_transfer_log(log, ALLOWED_ASSET))
        self.assertTrue(is_transfer_log(log, ALLOWED_ASSET.lower()))

    def test_is_transfer_log_rejects_other_token(self):
        log = make_transfer_log(token=OTHER_TOKEN)
        self.assertFalse(is_transfer_log(log, ALLOWED_ASSET))

    def test_is_transfer_log_rejects_other_event(self):
        log = make_transfer_log()
        log["topics"][0] = "0x" + "00" * 32
        self.assertFalse(is_transfer_log(log))

    def test_decode_transfer_rejects_non_transfer_logs(self):
        with self.assertRaises(ValueError):
            decode_transfer({"topics": ["0x" + "00" * 32], "data": "0x"})
        with self.assertRaises(ValueError):
            decode_transfer({"topics": [TRANSFER_TOPIC] * 4, "data": "0x"})  # ERC-721 shape


class TestReceiptVerification(unittest.TestCase):
    def test_correct_receipt_is_ok(self):
        result = verify_receipt(make_receipt(), EXPECTED_TRANSFER)
        self.assertTrue(result["ok"])
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["transfer"]["value_base_units"], 100_000_000)

    def test_wrong_recipient_is_detected(self):
        receipt = make_receipt(logs=[make_transfer_log(recipient=OTHER_ADDRESS)])
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("RECIPIENT_MISMATCH", result["mismatches"])

    def test_wrong_sender_is_detected(self):
        receipt = make_receipt(logs=[make_transfer_log(sender=OTHER_ADDRESS)])
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("SENDER_MISMATCH", result["mismatches"])

    def test_wrong_amount_is_detected(self):
        receipt = make_receipt(logs=[make_transfer_log(value_base_units=200_000_000)])
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("AMOUNT_MISMATCH", result["mismatches"])

    def test_failed_status_is_refused(self):
        result = verify_receipt(make_receipt(status="0x0"), EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("TRANSACTION_FAILED", result["mismatches"])

    def test_missing_status_is_refused(self):
        receipt = make_receipt()
        del receipt["status"]
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("RECEIPT_STATUS_MISSING", result["mismatches"])

    def test_wrong_token_contract_is_refused(self):
        receipt = make_receipt(logs=[make_transfer_log(token=OTHER_TOKEN)])
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("TOKEN_CONTRACT_MISMATCH", result["mismatches"])

    def test_no_transfer_log_is_refused(self):
        result = verify_receipt(make_receipt(logs=[]), EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("NO_TRANSFER_LOG", result["mismatches"])

    def test_wrong_chain_is_refused(self):
        receipt = make_receipt(chain_id="0x1")  # Ethereum mainnet
        result = verify_receipt(receipt, EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("CHAIN_ID_MISMATCH", result["mismatches"])

    def test_missing_chain_is_refused(self):
        result = verify_receipt(make_receipt(include_chain=False), EXPECTED_TRANSFER)
        self.assertFalse(result["ok"])
        self.assertIn("CHAIN_ID_MISSING", result["mismatches"])

    def test_expected_block_requires_the_five_fields(self):
        with self.assertRaises(ValueError):
            verify_receipt(make_receipt(), {"token": ALLOWED_ASSET})


class TestGuard(unittest.TestCase):
    def setUp(self):
        self.policy = default_config(RESERVE_ADDRESS, now=NOW)
        self.intents = {intent.intent_id: intent for intent in build_demo_intents()}

    def test_assert_allowed_passes_for_allow(self):
        decision = evaluate(self.intents["I1"], self.policy, now=NOW)
        self.assertTrue(execution_allowed(decision))
        self.assertIs(assert_allowed(decision), decision)

    def test_assert_allowed_raises_for_deny(self):
        decision = evaluate(self.intents["I2"], self.policy, now=NOW)
        with self.assertRaises(PolicyViolationError) as ctx:
            assert_allowed(decision)
        self.assertEqual(ctx.exception.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_TX_CAP", ctx.exception.reasons)

    def test_assert_allowed_raises_for_require_approval(self):
        decision = evaluate(self.intents["I3"], self.policy, now=NOW)
        with self.assertRaises(PolicyViolationError) as ctx:
            assert_allowed(decision)
        self.assertEqual(ctx.exception.verdict, "REQUIRE_APPROVAL")

    def test_defaults_from_empty_environment(self):
        config = ExecutionConfig.from_env({})
        self.assertEqual(config.rpc_url, "https://sepolia.base.org")
        self.assertEqual(config.treasury_address, TREASURY_ADDRESS)
        self.assertEqual(config.reserve_address, RESERVE_ADDRESS)
        self.assertEqual(config.max_per_tx, 100.0)
        self.assertEqual(config.max_cumulative, 300.0)
        self.assertEqual(config.permission_ttl_hours, 24)
        self.assertTrue(config.dry_run)
        self.assertEqual(config.secret_env_names_present, ())

    def test_environment_overrides_are_parsed(self):
        config = ExecutionConfig.from_env({
            "ORVYREN_MAX_PER_TX": "50",
            "ORVYREN_MAX_CUMULATIVE": "150",
            "ORVYREN_PERMISSION_TTL_HOURS": "6",
            "ORVYREN_DRY_RUN": "0",
        })
        self.assertEqual(config.max_per_tx, 50.0)
        self.assertEqual(config.max_cumulative, 150.0)
        self.assertEqual(config.permission_ttl_hours, 6)
        self.assertFalse(config.dry_run)

    def test_invalid_number_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            ExecutionConfig.from_env({"ORVYREN_MAX_PER_TX": "abc"})

    def test_invalid_address_raises_configuration_error(self):
        with self.assertRaises(ConfigurationError):
            ExecutionConfig.from_env({"ORVYREN_TREASURY_ADDRESS": "0x123"})

    def test_mask_secret_never_reveals_the_value(self):
        masked = mask_secret("s3cret-value")
        self.assertEqual(masked, "***")
        self.assertNotIn("s3cret", masked)

    def test_mask_rpc_url_hides_api_keys(self):
        with_key = "https://base-sepolia.g.alchemy.com/v2/SUPERSECRETKEY"
        masked = mask_rpc_url(with_key)
        self.assertNotIn("SUPERSECRETKEY", masked)
        self.assertIn("base-sepolia.g.alchemy.com", masked)
        self.assertEqual(mask_rpc_url("https://sepolia.base.org"), "https://sepolia.base.org")
        single_segment = mask_rpc_url("https://rpc.example.com/SECRETTOKEN")
        self.assertNotIn("SECRETTOKEN", single_segment)

    def test_config_repr_never_leaks_secrets(self):
        config = ExecutionConfig.from_env({
            "ORVYREN_RPC_URL_BASE_SEPOLIA": "https://base-sepolia.g.alchemy.com/v2/SUPERSECRETKEY",
            "ORVYREN_PRIVATE_KEY": "0xdeadbeefdeadbeef",
        })
        text = repr(config) + json.dumps(config.safe_dict())
        self.assertNotIn("SUPERSECRETKEY", text)
        self.assertNotIn("deadbeef", text)
        self.assertIn("ORVYREN_PRIVATE_KEY", text)  # the NAME is reported, never the value


class TestPolicyExecutionLink(unittest.TestCase):
    """Policy verdict -> execution: the guard is the bridge, and it blocks hard."""

    def setUp(self):
        self.policy = default_config(RESERVE_ADDRESS, now=NOW)
        self.intents = build_demo_intents()

    def test_demo_verdicts_are_as_specified(self):
        verdicts = {intent.intent_id: evaluate(intent, self.policy, now=NOW).verdict
                    for intent in self.intents}
        self.assertEqual(verdicts, EXPECTED_VERDICTS)

    def test_i2_deny_codes(self):
        decision = evaluate(self.intents[1], self.policy, now=NOW)
        self.assertEqual(decision.verdict, "DENY")
        self.assertIn("AMOUNT_ABOVE_TX_CAP", decision.reasons)

    def test_i3_requires_human_approval(self):
        decision = evaluate(self.intents[2], self.policy, now=NOW)
        self.assertEqual(decision.verdict, "REQUIRE_APPROVAL")
        self.assertIn("ACTION_NEEDS_HUMAN_APPROVAL", decision.reasons)

    def test_guard_blocks_denied_and_approval_intents(self):
        for intent in self.intents[1:]:
            decision = evaluate(intent, self.policy, now=NOW)
            with self.assertRaises(PolicyViolationError):
                assert_allowed(decision)


class TestDemoIntegration(unittest.TestCase):
    """Offline end-to-end check of what run_execution_demo.py actually produces."""

    def test_build_instruction_is_exact_and_unsigned(self):
        intent = build_demo_intents()[0]
        instruction = demo.build_instruction(intent)
        self.assertEqual(instruction, {
            "to": ALLOWED_ASSET,
            "calldata": I1_CALLDATA,
            "note": "human executes this transfer; the agent never holds the key",
        })

    def test_report_shape_and_verdicts(self):
        report = demo.build_report(ExecutionConfig.from_env({}), NOW)
        self.assertEqual(report["chain"], "Base Sepolia (84532)")
        self.assertFalse(report["agent_holds_key"])
        self.assertEqual([case["intent_id"] for case in report["cases"]], ["I1", "I2", "I3"])
        by_id = {case["intent_id"]: case for case in report["cases"]}
        self.assertEqual({case["intent_id"]: case["verdict"] for case in report["cases"]},
                         EXPECTED_VERDICTS)
        for key in ("intent_id", "action_type", "amount_usdc", "recipient",
                    "verdict", "deny_codes", "rules_evaluated", "instruction"):
            self.assertIn(key, by_id["I1"])
        self.assertEqual(by_id["I1"]["instruction"]["calldata"], I1_CALLDATA)
        self.assertIsNone(by_id["I2"]["instruction"])
        self.assertIsNone(by_id["I3"]["instruction"])
        self.assertIn("AMOUNT_ABOVE_TX_CAP", by_id["I2"]["deny_codes"])
        self.assertEqual(by_id["I3"]["deny_codes"], ["ACTION_NEEDS_HUMAN_APPROVAL"])
        self.assertEqual(report["receipt_verification"]["status"],
                         "no transaction hash provided yet (pending human execution)")
        self.assertEqual(report["verdict_check"]["unexpected"], [])
        self.assertEqual(len(report["guard_blocks"]), 2)
        json.dumps(report)  # the report must be JSON-serialisable as-is


class TestLiveRpc(unittest.TestCase):
    """Read-only network smoke test — skipped unless ORVYREN_LIVE_RPC=1."""

    @unittest.skipUnless(os.environ.get("ORVYREN_LIVE_RPC") == "1",
                         "set ORVYREN_LIVE_RPC=1 to run the read-only Base Sepolia RPC test")
    def test_chain_id_is_base_sepolia(self):
        from orvyren.execution.chain import chain_id
        self.assertEqual(chain_id(timeout=30), ALLOWED_CHAIN_ID)

    @unittest.skipUnless(os.environ.get("ORVYREN_LIVE_RPC") == "1",
                         "set ORVYREN_LIVE_RPC=1 to run the read-only Base Sepolia RPC test")
    def test_block_number_is_positive(self):
        from orvyren.execution.chain import block_number
        self.assertGreater(block_number(timeout=30), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
