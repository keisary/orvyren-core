#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Curve pool reader -- the **realisable** sale price (ORVYREN-Core data layer).

``get_dy(i, j, dx)`` (``0x5e0d443f``) is the only price in this project that can
be executed: it returns the *actual* output of a swap of ``dx`` against the pool
invariant **at a given archive block**, fees and slippage included.  It is what
separates "the price displayed" from "the price obtainable", which is the core
question of the ORVYREN dossier.

stETH/ETH pool ``0xDC24316b9AE028F1497c275EB9192a3Ea0f67022`` (measured
2026-10-15):

* ``coins(0)`` = ``0xEeee...EEeE`` (native ETH), ``coins(1)`` = Lido stETH
  (``0xae7ab9...7fE84``);
* **selling stETH** is therefore ``get_dy(1, 0, dx)``; the realisable price is
  ``dy / dx`` and the discount is ``1 - dy / dx`` -- e.g. 0.9993 on
  2022-05-05 (6.6 bps) and **0.9381 on 2022-06-15T22:43Z (618.5 bps)**, the
  June-2022 figure reproduced by ``scripts/reconstruct_steth_episode.py``.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from orvyren.data.rpc import (ArchiveRpc, decode_address, decode_uint,
                              encode_int, encode_uint)

__all__ = [
    "CURVE_STETH_POOL",
    "CURVE_3POOL",
    "STETH_POOL_ETH_INDEX",
    "STETH_POOL_STETH_INDEX",
    "SEL_GET_DY",
    "SEL_BALANCES",
    "SEL_COINS",
    "SEL_TOTAL_SUPPLY",
    "CurvePool",
    "steth_pool",
    "steth_sell_quote",
    "steth_discount_ladder",
]

#: Curve stETH/ETH (the "LST" pool of the June-2022 episode).
CURVE_STETH_POOL = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"
#: Curve 3pool (DAI/USDC/USDT), used as a stablecoin-depth reference.
CURVE_3POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"

#: Coin slots of the stETH pool, read with ``coins(i)`` on 2026-10-15.
STETH_POOL_ETH_INDEX = 0
STETH_POOL_STETH_INDEX = 1

SEL_GET_DY = "0x5e0d443f"
SEL_BALANCES = "0x4903b0d1"
SEL_COINS = "0xc6610657"
SEL_TOTAL_SUPPLY = "0x18160ddd"


@dataclass(frozen=True)
class SwapQuote:
    """Result of ``get_dy`` for one size, with the price and discount derived."""

    pool: str
    block: Any
    index_in: int
    index_out: int
    amount_in_raw: int
    amount_out_raw: int
    decimals_in: int
    decimals_out: int

    @property
    def amount_in(self) -> float:
        return self.amount_in_raw / 10 ** self.decimals_in

    @property
    def amount_out(self) -> float:
        return self.amount_out_raw / 10 ** self.decimals_out

    @property
    def price(self) -> Optional[float]:
        """Output units per input unit (``None`` when the input is zero)."""
        if self.amount_in_raw == 0:
            return None
        return (self.amount_out_raw / 10 ** self.decimals_out) / (
            self.amount_in_raw / 10 ** self.decimals_in
        )

    @property
    def discount_bps(self) -> Optional[float]:
        """``(1 - price) * 10 000``: positive means selling costs you money."""
        price = self.price
        return None if price is None else (1.0 - price) * 10_000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block": self.block,
            "pool": self.pool,
            "index_in": self.index_in,
            "index_out": self.index_out,
            "amount_in": self.amount_in,
            "amount_out": self.amount_out,
            "amount_in_raw": str(self.amount_in_raw),
            "amount_out_raw": str(self.amount_out_raw),
            "price": self.price,
            "discount_bps": self.discount_bps,
        }


class CurvePool:
    """Minimal reader for a Curve stableswap pool (``get_dy`` / ``balances``)."""

    def __init__(
        self,
        rpc: ArchiveRpc,
        address: str = CURVE_STETH_POOL,
        *,
        decimals: Sequence[int] = (18, 18),
        name: str = "stETH/ETH",
    ) -> None:
        self.rpc = rpc
        self.address = address
        self.decimals: Tuple[int, ...] = tuple(int(d) for d in decimals)
        self.name = name

    # -- pool metadata ------------------------------------------------------ #
    def coins(self, index: int, block: Any = "latest") -> str:
        """Address of coin ``index`` (``0xEeee..EEeE`` for native ETH)."""
        raw = self.rpc.eth_call(self.address, SEL_COINS + encode_int(index), block)
        return decode_address(decode_uint(raw))

    def balances(self, index: int, block: Any = "latest") -> int:
        """Raw coin balance of the pool (``balances(i)``)."""
        raw = self.rpc.eth_call(self.address, SEL_BALANCES + encode_int(index), block)
        return decode_uint(raw)

    def balances_whole(self, index: int, block: Any = "latest") -> float:
        return self.balances(index, block) / 10 ** self.decimals[index]

    def total_supply(self, block: Any = "latest") -> int:
        """LP token total supply (raw)."""
        return decode_uint(self.rpc.eth_call(self.address, SEL_TOTAL_SUPPLY, block))

    # -- pricing ------------------------------------------------------------ #
    def get_dy_raw(self, index_in: int, index_out: int, amount_in_raw: int, block: Any = "latest") -> int:
        """``get_dy(i, j, dx)`` as a raw integer (reverts if the pool cannot fill it)."""
        # encode_uint() rejects negatives and out-of-range values: a negative
        # amount formatted with ``f"{n:064x}"`` produces a signed 65-character
        # "hex" word (malformed calldata sent silently instead of an error).
        data = SEL_GET_DY + encode_int(index_in) + encode_int(index_out) + encode_uint(amount_in_raw)
        return decode_uint(self.rpc.eth_call(self.address, data, block))

    def get_dy(self, index_in: int, index_out: int, amount_in: float, block: Any = "latest") -> float:
        """``get_dy`` in whole output units for ``amount_in`` in whole input units."""
        raw_in = int(round(amount_in * 10 ** self.decimals[index_in]))
        raw_out = self.get_dy_raw(index_in, index_out, raw_in, block)
        return raw_out / 10 ** self.decimals[index_out]

    def quote(self, index_in: int, index_out: int, amount_in_raw: int, block: Any = "latest") -> SwapQuote:
        """Full quote (price + discount) for a raw input amount."""
        return SwapQuote(
            pool=self.address,
            block=block,
            index_in=index_in,
            index_out=index_out,
            amount_in_raw=int(amount_in_raw),
            amount_out_raw=self.get_dy_raw(index_in, index_out, amount_in_raw, block),
            decimals_in=self.decimals[index_in],
            decimals_out=self.decimals[index_out],
        )

    def ladder(
        self,
        index_in: int,
        index_out: int,
        sizes: Iterable[float],
        block: Any = "latest",
    ) -> List[SwapQuote]:
        """One quote per size, in the given order (``depth`` / slippage ladder)."""
        return [
            self.quote(index_in, index_out, int(round(size * 10 ** self.decimals[index_in])), block)
            for size in sizes
        ]


def steth_pool(rpc: ArchiveRpc, address: str = CURVE_STETH_POOL) -> CurvePool:
    """The stETH/ETH pool, with its measured coin order (ETH = 0, stETH = 1)."""
    return CurvePool(rpc, address, decimals=(18, 18), name="stETH/ETH")


def steth_sell_quote(rpc: ArchiveRpc, amount_steth: float, block: Any = "latest") -> Dict[str, Any]:
    """Realisable sale of ``amount_steth`` stETH into ETH at ``block``.

    Returns the ``SwapQuote`` payload (price in ETH per stETH, discount in bps).
    """
    pool = steth_pool(rpc)
    quote = pool.quote(
        STETH_POOL_STETH_INDEX,
        STETH_POOL_ETH_INDEX,
        int(round(amount_steth * 10 ** 18)),
        block,
    )
    payload = quote.to_dict()
    payload["size_steth"] = amount_steth
    return payload


def steth_discount_ladder(
    rpc: ArchiveRpc,
    block: Any,
    sizes: Sequence[float] = (1.0, 100.0, 1_000.0, 10_000.0),
) -> Dict[float, Dict[str, Any]]:
    """Discount ladder for the standard sizes of the dossier."""
    sizes = tuple(sizes)
    pool = steth_pool(rpc)
    out: Dict[float, Dict[str, Any]] = {}
    for size, quote in zip(sizes, pool.ladder(STETH_POOL_STETH_INDEX, STETH_POOL_ETH_INDEX, sizes, block)):
        payload = quote.to_dict()
        payload["size_steth"] = size
        out[float(size)] = payload
    return out
