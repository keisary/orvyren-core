#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aave V3 reserve reader (ORVYREN-Core data layer).

Reads, at any archive block, the state of an Aave V3 Ethereum Core reserve:

* ``getReserveData(address)`` (``0x35ea6a75``) -- the 13-word reserve struct;
* the packed configuration word (LTV, liquidation threshold, liquidation bonus,
  decimals, ``isActive`` bit 56, **``isFrozen`` bit 57**, ``borrowingEnabled``
  bit 58, ``isPaused`` bit 60, borrow cap, supply cap, e-mode category);
* ``aToken.totalSupply()`` / ``variableDebtToken.totalSupply()`` /
  ``underlying.balanceOf(aToken)`` -> utilisation U and cap utilisation;
* ``AaveOracle.getAssetPrice(asset)`` (``0xb3596f07``, 8 decimals) -- the price
  the protocol *retains* for the collateral.

Addresses and selectors below were verified on-chain on 2026-10-15 against
``https://eth.drpc.org`` and ``https://eth-mainnet.public.blastapi.io``
(research/W2B_signaux_detection.md, fixtures/raw_w2b/).  Measured examples:
rsETH reserve frozen between block 24 908 722 and 24 908 723
(2026-04-18T19:03:59Z), rsETH ``supplyCap`` = 530 000 with an aToken supply of
529 993.98 at 2026-04-18T18:00Z (99.999 % of cap).

Standard library only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from orvyren.data.rpc import ArchiveRpc, decode_address, decode_uint, encode_address

__all__ = [
    "AAVE_V3_ETHEREUM_POOL",
    "AAVE_V3_ETHEREUM_ORACLE",
    "SEL_GET_RESERVE_DATA",
    "SEL_GET_ASSET_PRICE",
    "SEL_TOTAL_SUPPLY",
    "SEL_BALANCE_OF",
    "ORACLE_UNIT",
    "ReserveConfig",
    "AaveV3Pool",
]

#: Aave V3 Ethereum Core (bgd-labs/aave-address-book, ``AaveV3Ethereum.sol``).
AAVE_V3_ETHEREUM_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
AAVE_V3_ETHEREUM_ORACLE = "0x54586bE62E3c3580375aE3723C145253060Ca0C2"

SEL_GET_RESERVE_DATA = "0x35ea6a75"
SEL_GET_ASSET_PRICE = "0xb3596f07"
SEL_TOTAL_SUPPLY = "0x18160ddd"
SEL_BALANCE_OF = "0x70a08231"

#: ``AaveOracle`` returns prices scaled by this unit (BASE_CURRENCY_UNIT = 1e8).
ORACLE_UNIT = 10 ** 8

#: ``getReserveData`` word index -> field name (Aave V3 ``DataTypes.ReserveData``).
RESERVE_DATA_FIELDS = (
    "configuration",
    "liquidity_index",
    "current_liquidity_rate",
    "variable_borrow_index",
    "current_variable_borrow_rate",
    "current_stable_borrow_rate",
    "last_update_timestamp",
    "id",
    "a_token",
    "stable_debt_token",
    "variable_debt_token",
    "interest_rate_strategy",
    "accrued_to_treasury",
)

#: Indices of the address-valued words of the reserve struct.
_ADDRESS_WORDS = (8, 9, 10, 11)


@dataclass(frozen=True)
class ReserveConfig:
    """The packed ``configuration`` word of an Aave V3 reserve, decoded."""

    raw: int
    ltv_bps: int
    liquidation_threshold_bps: int
    liquidation_bonus_bps: int
    decimals: int
    is_active: bool
    is_frozen: bool
    borrowing_enabled: bool
    stable_borrow_enabled: bool
    is_paused: bool
    borrow_cap: int
    supply_cap: int
    e_mode_category: int
    liquidation_protocol_fee_bps: int

    @classmethod
    def from_word(cls, word: int) -> "ReserveConfig":
        """Decode the configuration word (bit layout of ``ReserveConfiguration``).

        Field widths follow the on-chain library exactly
        (``ReserveConfiguration.sol``: ``MAX_VALID_BORROW_CAP``/
        ``MAX_VALID_SUPPLY_CAP`` = 2**36-1, ``MAX_VALID_EMODE_CATEGORY`` = 255):
        the caps are **36-bit** fields and the e-mode category is **8-bit**.  A
        32-bit cap mask truncates any cap >= 2**32, and a 16-bit e-mode mask
        bleeds the low bits of the unbacked mint cap (bits 176-183) into the
        category.
        """
        value = int(word)
        return cls(
            raw=value,
            ltv_bps=value & 0xFFFF,
            liquidation_threshold_bps=(value >> 16) & 0xFFFF,
            liquidation_bonus_bps=(value >> 32) & 0xFFFF,
            decimals=(value >> 48) & 0xFF,
            is_active=bool((value >> 56) & 1),
            is_frozen=bool((value >> 57) & 1),
            borrowing_enabled=bool((value >> 58) & 1),
            stable_borrow_enabled=bool((value >> 59) & 1),
            is_paused=bool((value >> 60) & 1),
            borrow_cap=(value >> 80) & 0xFFFFFFFFF,
            supply_cap=(value >> 116) & 0xFFFFFFFFF,
            e_mode_category=(value >> 168) & 0xFF,
            liquidation_protocol_fee_bps=(value >> 152) & 0xFFFF,
        )

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly view (``raw`` kept as a hex string, as read)."""
        payload = asdict(self)
        payload["raw"] = hex(self.raw)
        return payload


class AaveV3Pool:
    """Reserve-level reader for an Aave V3 pool (Ethereum Core by default)."""

    def __init__(
        self,
        rpc: ArchiveRpc,
        pool_address: str = AAVE_V3_ETHEREUM_POOL,
        oracle_address: str = AAVE_V3_ETHEREUM_ORACLE,
    ) -> None:
        self.rpc = rpc
        self.pool_address = pool_address
        self.oracle_address = oracle_address

    # -- reserve struct ----------------------------------------------------- #
    def get_reserve_data(self, asset: str, block: Any) -> Dict[str, Any]:
        """Raw ``getReserveData(asset)`` decoded into a named dict."""
        raw = self.rpc.eth_call(self.pool_address, SEL_GET_RESERVE_DATA + encode_address(asset), block)
        words = [decode_uint(raw, i) for i in range(len(raw[2:]) // 64)]
        if len(words) < len(RESERVE_DATA_FIELDS):
            raise ValueError(
                f"getReserveData({asset}) returned {len(words)} words, expected >= "
                f"{len(RESERVE_DATA_FIELDS)}"
            )
        out: Dict[str, Any] = {}
        for index, name in enumerate(RESERVE_DATA_FIELDS):
            word = words[index]
            out[name] = decode_address(word) if index in _ADDRESS_WORDS else word
        return out

    def reserve_config(self, asset: str, block: Any) -> ReserveConfig:
        """Decoded reserve configuration (LTV, frozen bit, supply cap, decimals)."""
        data = self.get_reserve_data(asset, block)
        return ReserveConfig.from_word(data["configuration"])

    def a_token(self, asset: str, block: Any) -> str:
        return self.get_reserve_data(asset, block)["a_token"]

    def variable_debt_token(self, asset: str, block: Any) -> str:
        return self.get_reserve_data(asset, block)["variable_debt_token"]

    # -- token-level reads -------------------------------------------------- #
    def total_supply(self, token: str, block: Any) -> int:
        """``ERC20.totalSupply()`` in token units (raw integer)."""
        return decode_uint(self.rpc.eth_call(token, SEL_TOTAL_SUPPLY, block))

    def balance_of(self, token: str, holder: str, block: Any) -> int:
        """``ERC20.balanceOf(holder)`` in token units (raw integer)."""
        return decode_uint(
            self.rpc.eth_call(token, SEL_BALANCE_OF + encode_address(holder), block)
        )

    def oracle_price(self, asset: str, block: Any, *, unit: int = ORACLE_UNIT) -> float:
        """Price the protocol *retains* for ``asset`` (oracle, 8 decimals)."""
        raw = decode_uint(self.rpc.eth_call(self.oracle_address, SEL_GET_ASSET_PRICE + encode_address(asset), block))
        return raw / unit

    # -- composed state ----------------------------------------------------- #
    def reserve_state(self, asset: str, block: Any, *, with_oracle: bool = True) -> Dict[str, Any]:
        """One-call-per-field snapshot of a reserve at ``block``.

        Keys: ``a_token_supply`` and ``cash`` (underlying held by the aToken),
        both in whole tokens; ``variable_debt_supply``; ``utilisation``
        (``variable debt / aToken supply`` -- the definition used for the rsETH
        episode, measured 88.60 % -> 100.01 % on WETH), ``utilisation_cash_gap``
        (``1 - cash / aToken supply``, the ``U_r`` of W2-B signal 2.1, equal to
        the former when no interest is pending), ``cap_ratio``
        (``aToken supply / supplyCap``) and the oracle price.
        """
        data = self.get_reserve_data(asset, block)
        config = ReserveConfig.from_word(data["configuration"])
        scale = 10 ** config.decimals
        a_token = data["a_token"]
        a_token_supply = self.total_supply(a_token, block)
        variable_debt_supply = self.total_supply(data["variable_debt_token"], block)
        cash = self.balance_of(asset, a_token, block)
        state: Dict[str, Any] = {
            "block": block,
            "asset": asset,
            "decimals": config.decimals,
            "a_token": a_token,
            "variable_debt_token": data["variable_debt_token"],
            "a_token_supply": a_token_supply / scale,
            "a_token_supply_raw": a_token_supply,
            "cash": cash / scale,
            "cash_raw": cash,
            "variable_debt_supply": variable_debt_supply / scale,
            "variable_debt_supply_raw": variable_debt_supply,
            "utilisation": (variable_debt_supply / a_token_supply) if a_token_supply else None,
            "utilisation_cash_gap": (1.0 - cash / a_token_supply) if a_token_supply else None,
            "supply_cap": config.supply_cap,
            "cap_ratio": (a_token_supply / scale / config.supply_cap) if config.supply_cap else None,
            "is_frozen": config.is_frozen,
            "is_active": config.is_active,
            "is_paused": config.is_paused,
            "ltv_bps": config.ltv_bps,
            "liquidation_threshold_bps": config.liquidation_threshold_bps,
            "borrowing_enabled": config.borrowing_enabled,
        }
        if with_oracle:
            state["oracle_price"] = self.oracle_price(asset, block)
        return state


def find_freeze_block(
    pool: AaveV3Pool,
    asset: str,
    *,
    low: int,
    high: int,
    max_steps: int = 64,
) -> Dict[str, Any]:
    """Binary-search the exact block where ``isFrozen`` turns true.

    ``low`` must be a block where the reserve is *not* frozen and ``high`` a
    block where it is; the return value dates both sides to the second.
    """
    def frozen(block: int) -> Optional[bool]:
        try:
            return pool.reserve_config(asset, block).is_frozen
        except Exception:
            return None

    flips = 0
    for _ in range(max_steps):
        if high - low <= 1:
            break
        middle = (low + high) // 2
        state = frozen(middle)
        if state is None:
            break
        flips += 1
        if state:
            high = middle
        else:
            low = middle
    if frozen(low) is not False or frozen(high) is not True:
        raise ValueError(
            f"freeze search failed: block {low} is not unfrozen / block {high} is not frozen"
        )
    return {
        "last_unfrozen_block": low,
        "last_unfrozen_ts": pool.rpc.block_timestamp(low),
        "first_frozen_block": high,
        "first_frozen_ts": pool.rpc.block_timestamp(high),
        "steps": flips,
    }
