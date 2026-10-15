#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN on-chain data layer -- archive reads used to rebuild past episodes.

Modules
-------
``rpc``        archive JSON-RPC client: endpoint fallback (``eth.drpc.org`` then
               ``eth-mainnet.public.blastapi.io``), timeouts, block<->timestamp
               search, ``eth_getLogs`` paginated to 10 000 blocks, ABI codec;
``aave``       Aave V3 reserve reader: ``getReserveData`` (LTV, threshold,
               **frozen bit**, caps), aToken/variable-debt supplies, cash,
               utilisation ``U``, ``cap_ratio``, oracle price;
``curve``      Curve pool reader: ``get_dy`` -> the *realisable* sale price and
               discount of stETH/ETH at an archive block;
``chainlink``  Chainlink aggregator reader: ``latestRoundData`` / ``latestAnswer``
               / ``description`` at an archive block.

Every address, selector and limit in these modules was verified on-chain on
2026-10-15 against the two free archives above; the raw measurements are in
``research/raw_w2a/`` and ``research/raw_w2b/`` and the reasoning in
``research/W2A_donnees_episodes.md``, ``research/W2B_signaux_detection.md`` and
``research/W3_reconstruction_rseth_steth.md``.

Standard library only (``urllib``, ``json``, ``datetime``).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from orvyren.data import aave, chainlink, curve, rpc
from orvyren.data.aave import (AAVE_V3_ETHEREUM_ORACLE, AAVE_V3_ETHEREUM_POOL,
                               AaveV3Pool, ReserveConfig)
from orvyren.data.chainlink import (FEED_RSETH_CAPPED_ETH_USD, FEED_STETH_ETH,
                                    ChainlinkFeed, RoundData)
from orvyren.data.curve import CURVE_STETH_POOL, CurvePool
from orvyren.data.rpc import (DEFAULT_RPC_URLS, MAX_GET_LOGS_RANGE,
                              ArchiveRpc, RpcError, RpcRangeError)

__all__ = [
    "aave",
    "chainlink",
    "curve",
    "rpc",
    "ArchiveRpc",
    "RpcError",
    "RpcRangeError",
    "DEFAULT_RPC_URLS",
    "MAX_GET_LOGS_RANGE",
    "AaveV3Pool",
    "ReserveConfig",
    "AAVE_V3_ETHEREUM_POOL",
    "AAVE_V3_ETHEREUM_ORACLE",
    "CurvePool",
    "CURVE_STETH_POOL",
    "ChainlinkFeed",
    "RoundData",
    "FEED_STETH_ETH",
    "FEED_RSETH_CAPPED_ETH_USD",
    "utc_iso",
    "parse_utc",
    "time_grid",
]

#: Default step of the reconstructed series (one point per hour).
HOUR_SECONDS = 3600
DAY_SECONDS = 86_400


def utc_iso(timestamp: int) -> str:
    """Unix timestamp -> ``2026-04-18T19:03:59Z`` (the key format of the evidence files)."""
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> int:
    """``2026-04-18T19:03:59Z`` (or ``...T19:03:59``) -> unix timestamp."""
    cleaned = str(text).strip().replace("Z", "+00:00")
    stamp = datetime.fromisoformat(cleaned)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return int(stamp.timestamp())


def time_grid(start: str, end: str, step_seconds: int = HOUR_SECONDS) -> List[int]:
    """Ascending unix timestamps from ``start`` to ``end`` inclusive.

    ``time_grid("2026-04-17T00:00:00Z", "2026-04-18T00:00:00Z", 3600)`` gives 25
    points; a step that does not divide the span simply stops before ``end``.
    """
    if step_seconds <= 0:
        raise ValueError(f"step_seconds must be positive, got {step_seconds}")
    first, last = parse_utc(start), parse_utc(end)
    if last < first:
        raise ValueError(f"empty grid: start {start} is after end {end}")
    grid: List[int] = []
    current = first
    while current <= last:
        grid.append(current)
        current = int((datetime.fromtimestamp(current, tz=timezone.utc) + timedelta(seconds=step_seconds)).timestamp())
    return grid
