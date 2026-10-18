#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Step-0 guard tests for the Aave ingestion script's timestamp provenance."""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from scripts import ingest_aave_base  # noqa: E402


class FailingRpc:
    def block_timestamp(self, block):
        raise OSError("rpc down")


class IngestTimestampGuardTest(unittest.TestCase):
    def test_block_times_never_substitute_wall_clock(self):
        with self.assertRaises(RuntimeError) as caught:
            ingest_aave_base.block_times(FailingRpc(), [100], 100, 101)
        self.assertIn("block timestamp unavailable", str(caught.exception))

    def test_zero_timestamp_is_rejected(self):
        class ZeroRpc:
            def block_timestamp(self, block):
                return 0

        with self.assertRaises(RuntimeError):
            ingest_aave_base.block_times(ZeroRpc(), [100], 100, 101)

    def test_unknown_reserve_metadata_is_not_guessed(self):
        class EmptyRpc:
            def eth_call(self, address, data, block):
                return "0x"

        with self.assertRaises(RuntimeError):
            ingest_aave_base.reserve_meta(
                EmptyRpc(), "0x000000000000000000000000000000000000dead", 100)


if __name__ == "__main__":
    unittest.main()
