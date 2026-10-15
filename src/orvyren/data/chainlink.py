#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Chainlink feed reader at a given archive block (ORVYREN-Core data layer).

A lending protocol does not price its collateral at the market price: it prices
it at the oracle answer *it retains*.  Reading that answer at an archive block is
what makes the "retained value vs realisable value" gap measurable.

Feeds used by the dossier (addresses confirmed on-chain on 2026-10-15, see
research/W2B_signaux_detection.md):

===================== ============================================ ========= ========
name                  address                                      decimals  ABI
===================== ============================================ ========= ========
``steth_eth``         ``0x86392dC19c0b719886221c78AB11eb8Cf5c52812`` 18       full
``rseth_capped``      ``0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3``  8       capped
``usdc_usd``          ``0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6``  8       full
``eth_usd``           ``0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419``  8       full
===================== ============================================ ========= ========

**Measured ABI quirk (2026-04, verified):** the Aave-side capped feed
``Capped rsETH / ETH / USD`` exposes ``description()``, ``decimals()`` and
``latestAnswer()`` but **reverts on ``latestRoundData()``** -- so freshness
(``updatedAt``) is unavailable for that feed and :meth:`ChainlinkFeed.price`
falls back to ``latestAnswer()``.  ``description()`` is itself a detection
signal: the label *Capped* announces a price that can be wrong on purpose.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from orvyren.data.rpc import ArchiveRpc, RpcError, decode_string, decode_uint

__all__ = [
    "SEL_LATEST_ROUND_DATA",
    "SEL_LATEST_ANSWER",
    "SEL_DESCRIPTION",
    "SEL_DECIMALS",
    "FEED_STETH_ETH",
    "FEED_RSETH_CAPPED_ETH_USD",
    "FEED_USDC_USD",
    "FEED_ETH_USD",
    "KNOWN_FEEDS",
    "FeedError",
    "RoundData",
    "ChainlinkFeed",
]

SEL_LATEST_ROUND_DATA = "0xfeaf968c"
SEL_LATEST_ANSWER = "0x50d25bcd"
SEL_DESCRIPTION = "0x7284e416"
SEL_DECIMALS = "0x313ce567"

FEED_STETH_ETH = "0x86392dC19c0b719886221c78AB11eb8Cf5c52812"
FEED_RSETH_CAPPED_ETH_USD = "0x7292C95A5f6A501a9c4B34f6393e221F2A0139c3"
FEED_USDC_USD = "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6"
FEED_ETH_USD = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"

#: Label -> address, for callers that read a feed by name.
KNOWN_FEEDS: Dict[str, str] = {
    "steth_eth": FEED_STETH_ETH,
    "rseth_capped_eth_usd": FEED_RSETH_CAPPED_ETH_USD,
    "usdc_usd": FEED_USDC_USD,
    "eth_usd": FEED_ETH_USD,
}


class FeedError(RpcError):
    """The feed does not answer the requested method (revert / missing method)."""


@dataclass(frozen=True)
class RoundData:
    """``latestRoundData()`` unpacked (Aave's capped feed does not provide it)."""

    round_id: int
    answer_raw: int
    started_at: int
    updated_at: int
    answered_in_round: int
    decimals: int
    description: Optional[str] = None

    @property
    def answer(self) -> float:
        return self.answer_raw / 10 ** self.decimals

    def age_seconds(self, block_timestamp: int) -> int:
        """Seconds between the last feed update and ``block_timestamp``."""
        return int(block_timestamp) - int(self.updated_at)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_id": self.round_id,
            "answer": self.answer,
            "answer_raw": str(self.answer_raw),
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "answered_in_round": self.answered_in_round,
            "decimals": self.decimals,
            "description": self.description,
        }


class ChainlinkFeed:
    """One aggregator, read at any archive block."""

    def __init__(
        self,
        rpc: ArchiveRpc,
        address: str,
        *,
        name: Optional[str] = None,
        decimals: Optional[int] = None,
    ) -> None:
        self.rpc = rpc
        self.address = address
        self.name = name or address
        self._decimals = decimals
        self._description: Optional[str] = None

    # -- metadata ----------------------------------------------------------- #
    def description(self, block: Any = "latest") -> str:
        """Feed label (e.g. ``STETH / ETH``, ``Capped rsETH / ETH / USD``)."""
        if block == "latest" and self._description is not None:
            return self._description
        value = decode_string(self.rpc.eth_call(self.address, SEL_DESCRIPTION, block))
        if block == "latest":
            self._description = value
        return value

    def decimals(self, block: Any = "latest") -> int:
        """Feed decimals (8 for USD feeds, 18 for the stETH/ETH ratio feed)."""
        if self._decimals is not None:
            return self._decimals
        value = decode_uint(self.rpc.eth_call(self.address, SEL_DECIMALS, block))
        self._decimals = value
        return value

    # -- answers ------------------------------------------------------------ #
    def latest_round_data(self, block: Any = "latest") -> RoundData:
        """``latestRoundData()`` -- raises :class:`FeedError` when unsupported."""
        try:
            raw = self.rpc.eth_call(self.address, SEL_LATEST_ROUND_DATA, block)
        except RpcError as exc:
            raise FeedError(
                f"{self.name}: latestRoundData() unavailable at block {block} "
                f"(Aave's capped feeds expose latestAnswer() only): {exc}"
            ) from exc
        words = [decode_uint(raw, i) for i in range(5)]
        try:
            label: Optional[str] = self.description(block)
        except RpcError:
            label = None
        return RoundData(
            round_id=words[0],
            answer_raw=words[1],
            started_at=words[2],
            updated_at=words[3],
            answered_in_round=words[4],
            decimals=self.decimals(block),
            description=label,
        )

    def latest_answer(self, block: Any = "latest") -> int:
        """``latestAnswer()`` (raw integer) -- the capped feed's only readable answer."""
        return decode_uint(self.rpc.eth_call(self.address, SEL_LATEST_ANSWER, block))

    def price(self, block: Any = "latest", *, block_timestamp: Optional[int] = None) -> Dict[str, Any]:
        """Best available answer for ``block``, with its provenance.

        Returns ``{"price", "method", "decimals", "description"}`` plus
        ``updated_at`` / ``age_seconds`` when the feed supports
        ``latestRoundData``.
        """
        payload: Dict[str, Any] = {
            "feed": self.address,
            "name": self.name,
            "block": block,
        }
        try:
            round_data = self.latest_round_data(block)
        except FeedError:
            decimals = self.decimals(block)
            payload.update(
                {
                    "price": self.latest_answer(block) / 10 ** decimals,
                    "method": "latestAnswer",
                    "decimals": decimals,
                    "description": self.description(block),
                    "updated_at": None,
                    "age_seconds": None,
                }
            )
            return payload
        payload.update(
            {
                "price": round_data.answer,
                "method": "latestRoundData",
                "decimals": round_data.decimals,
                "description": round_data.description,
                "round_id": round_data.round_id,
                "updated_at": round_data.updated_at,
                "age_seconds": (
                    round_data.age_seconds(block_timestamp) if block_timestamp is not None else None
                ),
            }
        )
        return payload
