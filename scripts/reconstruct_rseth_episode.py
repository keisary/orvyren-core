#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rebuild the **rsETH / KelpDAO (18-21 April 2026)** episode into evidence JSON.

What it produces
----------------
``evidence/episode_rseth_2026-04.json``: an hourly series (2026-04-17T00:00Z ->
2026-04-21T00:00Z, plus the four key blocks of the episode) of, for the three
reserves involved (rsETH collateral, WETH, USDC) on **Aave V3 Ethereum Core**:

* the price the protocol **retains** for rsETH (``AaveOracle.getAssetPrice``,
  which is exactly the ``latestAnswer`` of the ``Capped rsETH / ETH / USD``
  Chainlink feed -- verified at every key block);
* the ``isFrozen`` bit of the reserve, with the **dated** 0 -> 1 transition;
* ``cap_ratio`` = aToken supply / supplyCap (the measured 99.999 % saturation of
  2026-04-18T18:00Z);
* utilisation ``U`` (variable debt / aToken supply) and the aToken supply;
* the exploit block (~17:35Z), the Guardian market freeze (~18:52Z) and the
  on-chain freeze of the rsETH reserve (block 24 908 723 = 2026-04-18T19:03:59Z).

Modes
-----
* default: read the chain through the archive RPCs (``--workers`` parallel);
* ``--from-cache``: rebuild from the JSON already archived in
  ``fixtures/raw_w2a`` and ``fixtures/raw_w2b`` -- no network at all.  The run
  falls back to that mode automatically when the very first call fails.

The output file is written *progressively* (atomic replace after every point),
so an interrupted run can simply be started again: ``--resume`` (default) keeps
the points already measured.

Usage
-----
    python scripts/reconstruct_rseth_episode.py                 # network, full run
    python scripts/reconstruct_rseth_episode.py --from-cache     # offline rebuild
    python scripts/reconstruct_rseth_episode.py --workers 8 --quiet
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recon_common import (EVIDENCE_DIR, dump_json_atomic, load_partial, load_raw,  # noqa: E402
                          merge_provenance, new_client, parallel_measure,
                          resolve_blocks, resolve_blocks_parallel, utc_now)

from orvyren.data import AaveV3Pool, ChainlinkFeed, parse_utc, time_grid, utc_iso  # noqa: E402
from orvyren.data.aave import find_freeze_block  # noqa: E402
from orvyren.data.chainlink import FEED_RSETH_CAPPED_ETH_USD  # noqa: E402

# --------------------------------------------------------------------------- #
# Episode constants (addresses and blocks measured 2026-10-15, see research/W2*)
# --------------------------------------------------------------------------- #
RSETH = "0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
RESERVES = (("rsETH", RSETH), ("WETH", WETH), ("USDC", USDC))

GRID_START = "2026-04-17T00:00:00Z"
GRID_END = "2026-04-21T00:00:00Z"
GRID_STEP = 3600

#: Timestamps of the episode that must appear in the series whatever the step.
KEY_TIMESTAMPS = (
    "2026-04-18T17:35:00Z",   # exploit executed (Messari timeline)
    "2026-04-18T18:00:00Z",   # supplyCap saturation measured (W2-B)
    "2026-04-18T18:52:00Z",   # Guardian market freeze announced (Galaxy)
    "2026-04-18T19:03:59Z",   # rsETH reserve frozen on-chain (block 24 908 723)
    "2026-04-20T00:00:00Z",   # WETH LTV -> 0 and WETH reserve frozen
)

#: Reference blocks already dated by W2-A/W2-B (used for the cache rebuild and
#: as a cross-check of the block search).
REFERENCE_BLOCKS = {
    "24908200": "2026-04-18T17:21:00Z (W2-A: rsETH LTV 0, WETH U 88.60 %)",
    "24908282": "2026-04-18T17:34:59Z (exploit, W2-A block finder)",
    "24908405": "2026-04-18T18:00:00Z (supplyCap saturated, 529 993.98 / 530 000)",
    "24908664": "2026-04-18T18:51:59Z (Guardian freeze, W2-A/W2-B)",
    "24908722": "2026-04-18T19:03:47Z (last block with isFrozen = 0)",
    "24908723": "2026-04-18T19:03:59Z (first block with isFrozen = 1)",
    "24909500": "2026-04-18T19:07:00Z (W2-A: WETH U 100.01 %)",
    "24917377": "2026-04-20T00:00:11Z (W2-A: WETH LTV 0 and frozen)",
}

EVENTS: Sequence[Dict[str, str]] = (
    {
        "utc": "2026-04-18T17:35:00Z",
        "ts": str(parse_utc("2026-04-18T17:35:00Z")),
        "label": "exploit executed (89 567 rsETH collateral, ~190 M$ WETH borrowed)",
        "source": "https://messari.io/report/aave-cracks-in-the-monolithic-thesis",
    },
    {
        "utc": "2026-04-18T18:00:00Z",
        "ts": str(parse_utc("2026-04-18T18:00:00Z")),
        "label": "rsETH supplyCap saturated (measured: 529 993.98 / 530 000 = 99.999 %)",
        "source": "research/W2B_signaux_detection.md (signal 2.5, measured on-chain)",
    },
    {
        "utc": "2026-04-18T18:52:00Z",
        "ts": str(parse_utc("2026-04-18T18:52:00Z")),
        "label": "Guardian freeze of the rsETH markets announced (77 min after the drain)",
        "source": "https://www.galaxy.com/insights/research/kelpdao-layerzero-exploit-defi",
    },
    {
        "utc": "2026-04-18T19:03:59Z",
        "ts": str(parse_utc("2026-04-18T19:03:59Z")),
        "label": "rsETH reserve isFrozen 0 -> 1 (block 24 908 723): nobody can withdraw",
        "source": "research/W2B_signaux_detection.md (signal 2.2, binary search)",
    },
    {
        "utc": "2026-04-20T00:00:00Z",
        "ts": str(parse_utc("2026-04-20T00:00:00Z")),
        "label": "WETH reserve frozen and WETH LTV set to 0; bad debt reported (123.7 / 230.1 M$)",
        "source": "https://governance.aave.com/t/rseth-incident-report-april-20-2026/24580",
    },
)

#: Files archived by W2-A / W2-B, used by ``--from-cache``.
CACHE_FILES = (
    "aave_rseth_apr2026_v2.json",     # raw_w2b: 12 h series (supply, cash, U, oracle)
    "aave_rseth_apr2026.json",        # raw_w2b: same shape, 12 h grid
    "aave_rseth_reserveconfig.json",  # raw_w2b: configuration word per block (frozen bit)
    "aave_v3_rseth_2026.json",        # raw_w2a: key blocks, rsETH + WETH + USDC
    "aave_rseth_freeze_block.json",   # raw_w2b: dated freeze transition
    "rseth_supply_eth_2026.json",     # raw_w2b: rsETH ERC20 total supply on Ethereum
)

#: Block-time anchor measured on-chain (W2-B): block 24 908 723 = 2026-04-18T19:03:59Z.
#: Used only in ``--from-cache`` mode, to flag archived UTC labels that disagree with
#: the block they were stored with (the W2-B 12 h grid was built with an estimator,
#: and its labels drift by up to ~12 h around 2026-04-19).
BLOCK_TIME_ANCHOR = (24908723, parse_utc("2026-04-18T19:03:59Z"))
SECONDS_PER_BLOCK = 12.09

DEFAULT_OUTPUT = os.path.join(EVIDENCE_DIR, "episode_rseth_2026-04.json")

#: Reserve-state fields kept in the evidence series (raw integers dropped).
COMPACT_FIELDS = (
    "a_token_supply",
    "cash",
    "variable_debt_supply",
    "utilisation",
    "utilisation_cash_gap",
    "cap_ratio",
    "supply_cap",
    "is_frozen",
    "ltv_bps",
    "liquidation_threshold_bps",
    "decimals",
    "a_token",
    "oracle_price",
)


# --------------------------------------------------------------------------- #
# Network collection
# --------------------------------------------------------------------------- #
def compact_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Keep the citable fields of a reserve state (drop raw integers)."""
    return {key: state.get(key) for key in COMPACT_FIELDS if key in state}


def measure_point(client: Any, block: int) -> Dict[str, Any]:
    """One reserve snapshot per involved asset, plus the retained oracle prices."""
    pool = AaveV3Pool(client)
    point: Dict[str, Any] = {"block": block, "block_ts": client.block_timestamp(block)}
    for label, asset in RESERVES:
        state = pool.reserve_state(asset, block, with_oracle=(label != "USDC"))
        point[label] = compact_state(state)
    return point


def feed_check(client: Any, block: int) -> Dict[str, Any]:
    """Cross-check: AaveOracle price vs the capped Chainlink feed's latestAnswer."""
    pool = AaveV3Pool(client)
    feed = ChainlinkFeed(client, FEED_RSETH_CAPPED_ETH_USD, name="rseth_capped")
    oracle = pool.oracle_price(RSETH, block)
    answer = feed.latest_answer(block) / 10 ** feed.decimals(block)
    return {
        "block": block,
        "description": feed.description(block),
        "aave_oracle_price": oracle,
        "feed_latest_answer": answer,
        "equal": abs(oracle - answer) < 1e-9,
        "note": "latestRoundData() reverts on this capped feed; latestAnswer() is the only answer",
    }


def collect_network(output_path: str, *, workers: int, resume: bool, log) -> Dict[str, Any]:
    """Full network run; returns the evidence payload."""
    grid = sorted(set(time_grid(GRID_START, GRID_END, GRID_STEP)) | {parse_utc(t) for t in KEY_TIMESTAMPS})
    grid_key = f"{GRID_START}..{GRID_END}/{GRID_STEP}s+key"
    payload: Dict[str, Any] = load_partial(output_path, mode="rpc", grid_key=grid_key) if resume else {}
    series: Dict[str, Any] = payload.get("series") or {}
    done = {point_ts for point_ts, point in series.items() if not point.get("error")}
    done_ts = {parse_utc(utc) for utc in done}
    todo = [ts for ts in grid if ts not in done_ts]
    worker_clients: List[Any] = []

    log(f"grid: {len(grid)} points ({len(done_ts)} already measured, {len(todo)} to go)")
    client = new_client(0)
    blocks: Dict[int, Dict[str, Any]] = {}
    known_blocks: Dict[int, Dict[str, Any]] = {}
    for utc, saved in (payload.get("blocks") or {}).items():
        if saved.get("block"):
            known_blocks[parse_utc(utc)] = {"block": saved["block"], "block_ts": saved.get("block_ts")}
    for utc, point in series.items():
        if point.get("block"):
            known_blocks.setdefault(parse_utc(utc), {"block": point["block"], "block_ts": point.get("block_ts")})
    pending = [ts for ts in todo if ts not in known_blocks]
    if pending:
        log(f"resolving {len(pending)} blocks (sliding window, checked floor)...")
        blocks = resolve_blocks_parallel(pending, workers=workers, log=log,
                                      client_factory=new_client)
        # Persist the block grid straight away: it is the slowest phase of a run, and an
        # interrupted run must not have to search it again.
        merged = dict(known_blocks)
        merged.update(blocks)
        payload["blocks"] = {utc_iso(ts): merged[ts] for ts in grid if ts in merged}
        payload["meta"] = dict(payload.get("meta") or {}, mode="rpc", grid_key=grid_key,
                               generated_utc=utc_now(), complete=False,
                               points_done=len(series), points_expected=len(grid))
        dump_json_atomic(output_path, payload)
    blocks.update(known_blocks)

    freeze = None
    try:
        freeze = find_freeze_block(AaveV3Pool(client), RSETH, low=24900327, high=24911049)
        freeze = {
            "last_unfrozen_block": freeze["last_unfrozen_block"],
            "last_unfrozen_ts": freeze["last_unfrozen_ts"],
            "last_unfrozen_utc": utc_iso(freeze["last_unfrozen_ts"]),
            "first_frozen_block": freeze["first_frozen_block"],
            "first_frozen_ts": freeze["first_frozen_ts"],
            "first_frozen_utc": utc_iso(freeze["first_frozen_ts"]),
            "steps": freeze["steps"],
            "method": "binary search on the isFrozen bit (block 24 900 327 not frozen, 24 911 049 frozen)",
        }
        log(f"freeze transition: {freeze['last_unfrozen_utc']} -> {freeze['first_frozen_utc']} (block {freeze['first_frozen_block']})")
    except Exception as exc:
        log(f"WARNING freeze search failed ({exc}); falling back to the archived value")
        try:
            cached = load_raw("aave_rseth_freeze_block.json", os.path.join(os.path.dirname(__file__), "..", "fixtures", "raw_w2b"))
            freeze = dict(cached, method="cache:aave_rseth_freeze_block.json")
        except FileNotFoundError:
            freeze = {"error": str(exc)}

    def worker(worker_client: Any, block: int) -> Dict[str, Any]:
        return measure_point(worker_client, block)

    block_to_ts = {blocks[ts]["block"]: ts for ts in grid}

    def on_result(block: int, point: Dict[str, Any]) -> None:
        series[utc_iso(block_to_ts[block])] = dict(point, ts=block_to_ts[block])
        payload["series"] = dict(sorted(series.items()))
        payload["meta"] = {
            "episode": "rsETH / KelpDAO -- Aave V3 Ethereum Core",
            "mode": "rpc",
            "grid_key": grid_key,
            "generated_utc": utc_now(),
            "complete": False,
            "points_done": len(payload["series"]),
            "points_expected": len(grid),
        }
        dump_json_atomic(output_path, payload)

    if todo:
        log(f"measuring {len(todo)} points with {workers} workers (3 reserves + oracle per point)...")
        started = time.time()
        parallel_measure([blocks[ts]["block"] for ts in todo], worker, workers=workers, log=log,
                         on_result=on_result, clients_out=worker_clients)
        log(f"measured in {time.time() - started:.0f}s")

    for ts in grid:  # make sure every grid point exists, even a failed one
        utc = utc_iso(ts)
        if utc not in series:
            series[utc] = {"ts": ts, "block": blocks[ts]["block"], "block_ts": blocks[ts]["block_ts"], "error": "not measured"}

    checks = []
    for label in KEY_TIMESTAMPS:
        block = blocks[parse_utc(label)]["block"]
        try:
            checks.append(feed_check(client, block))
        except Exception as exc:
            checks.append({"block": block, "error": str(exc)})

    payload.update(
        {
            "series": dict(sorted(series.items(), key=lambda item: item[1].get("ts", 0))),
            "freeze_transition": freeze,
            "feed_checks": checks,
            "reference_blocks": REFERENCE_BLOCKS,
            "events": [dict(event) for event in EVENTS],
            "rpc_provenance": merge_provenance(client, worker_clients),
            "meta": dict(
                payload.get("meta") or {},
                mode="rpc",
                grid_key=grid_key,
                generated_utc=utc_now(),
                complete=True,
                reserves=dict(RESERVES),
                reads_per_point="15 eth_call per point (4 per reserve + oracle, 3 reserves), "
                                "plus 2-3 eth_getBlockByNumber for the block floor",
                scope="Aave V3 Ethereum Core, reserves rsETH (collateral), WETH and USDC; "
                      "hourly step 3600 s plus the five key timestamps of the episode",
            ),
        }
    )
    return payload


# --------------------------------------------------------------------------- #
# Cache rebuild (no network)
# --------------------------------------------------------------------------- #
def _rows(payload: Any) -> List[Dict[str, Any]]:
    """Normalise an archived JSON file to a list of row dicts (``{"rows": [...]}`` too)."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("rows", "points", "series", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        return [payload]
    return []


def collect_from_cache(log) -> Dict[str, Any]:
    """Rebuild the series from the JSON archived by W2-A / W2-B (offline)."""
    series: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}
    repairs: List[Dict[str, Any]] = []

    def place(utc_label: str, block: Optional[int], source: str) -> Dict[str, Any]:
        """Return the point for an archived row, re-placing it when the label lies.

        The archival JSONs pair a UTC label with a block number, and in two of them the
        label is estimated rather than measured: the config file labels block 24 911 049
        (2026-04-19T02:49:47Z on-chain) as 2026-04-18T12:00:00Z, and the 12 h grid drifts by
        ~14.8 h.  A row is therefore placed at ``utc_label`` only when that label agrees with
        its own block within 2 h and no other row already claims that label; otherwise it is
        re-placed at the estimated time and the original label is recorded on the point.
        """
        estimate = estimate_utc(block) if block else None
        drifted = estimate is not None and abs(estimate - parse_utc(utc_label)) > 7200
        existing = series.get(utc_label)
        collision = existing is not None and block is not None and existing.get("block") not in (None, block)
        if (drifted or collision) and estimate is not None:
            key = utc_iso(estimate)
            entry = series.setdefault(key, {"ts": estimate, "block": block})
            entry.setdefault("archived_label", utc_label)
            entry.setdefault("source", source)
            repairs.append(
                {
                    "archived_label": utc_label,
                    "block": block,
                    "placed_at": key,
                    "reason": "label drifted from its block" if drifted else "two rows claim the same label",
                    "drift_hours": round(abs(estimate - parse_utc(utc_label)) / 3600.0, 1),
                }
            )
            return entry
        entry = series.setdefault(utc_label, {"ts": parse_utc(utc_label), "block": block})
        entry.setdefault("source", source)
        if block is not None:
            entry.setdefault("block", block)
        return entry

    for name in ("aave_rseth_apr2026_v2.json", "aave_rseth_apr2026.json"):
        try:
            rows = _rows(load_raw(name))
        except FileNotFoundError as exc:
            provenance[name] = f"missing: {exc}"
            continue
        provenance[name] = f"{len(rows)} points"
        for row in rows:
            utc = row["utc"] + "Z" if not str(row["utc"]).endswith("Z") else row["utc"]
            entry = place(utc, row.get("block"), f"cache:{name}")
            state = entry.setdefault("rsETH", {})
            state.setdefault("a_token_supply", row.get("rsETH_supply"))
            state.setdefault("cash", row.get("rsETH_cash"))
            state.setdefault("utilisation", row.get("U"))
            state.setdefault("utilisation_cash_gap", row.get("U"))
            state.setdefault("oracle_price", row.get("oracle_px_usd") or row.get("oracle_px"))
            state.setdefault("cap_ratio", (row["rsETH_supply"] / 530000) if row.get("rsETH_supply") else None)
            state.setdefault("supply_cap", 530000)

    try:
        configs = _rows(load_raw("aave_rseth_reserveconfig.json"))
        provenance["aave_rseth_reserveconfig.json"] = f"{len(configs)} points"
        for row in configs:
            utc = row["utc"] + "Z" if not str(row["utc"]).endswith("Z") else row["utc"]
            entry = place(utc, row.get("block"), "cache:aave_rseth_reserveconfig.json")
            config = row.get("config") or {}
            entry.setdefault("rsETH", {}).update(
                {
                    "is_frozen": config.get("isFrozen"),
                    "ltv_bps": int(round((config.get("ltv") or 0) * 10_000)),
                    "liquidation_threshold_bps": int(round((config.get("lt_thr") or 0) * 10_000)),
                    "supply_cap": config.get("supplyCap"),
                }
            )
    except FileNotFoundError as exc:
        provenance["aave_rseth_reserveconfig.json"] = f"missing: {exc}"

    try:
        key_rows = load_raw("aave_v3_rseth_2026.json")
        provenance["aave_v3_rseth_2026.json"] = f"{len(key_rows)} key blocks"
        for label, block_payload in key_rows.items():
            block = block_payload.get("block")
            entry = None
            for existing in series.values():
                if existing.get("block") == block:
                    entry = existing
                    break
            if entry is None:
                entry = place(utc_iso_from_label(label), block, "cache:aave_v3_rseth_2026.json")
            entry["source"] = "cache:aave_v3_rseth_2026.json"
            for asset in ("rsETH", "WETH", "USDC"):
                raw_state = block_payload.get(asset)
                if not raw_state:
                    continue
                state = entry.setdefault(asset, {})
                config = raw_state.get("config") or {}
                state.update(
                    {
                        "a_token_supply": raw_state.get("aToken_supply"),
                        "utilisation": raw_state.get("utilisation"),
                        "utilisation_cash_gap": raw_state.get("utilisation"),
                        "oracle_price": raw_state.get("prix_oracle_aave"),
                        "is_frozen": bool(config.get("frozen_bit")),
                        "ltv_bps": config.get("LTV_bps"),
                        "liquidation_threshold_bps": config.get("seuil_liq_bps"),
                    }
                )
                if asset == "rsETH" and raw_state.get("aToken_supply"):
                    state["cap_ratio"] = raw_state["aToken_supply"] / 530000
                    state["supply_cap"] = 530000
    except FileNotFoundError as exc:
        provenance["aave_v3_rseth_2026.json"] = f"missing: {exc}"

    try:
        freeze = load_raw("aave_rseth_freeze_block.json")
        provenance["aave_rseth_freeze_block.json"] = "1 transition"
        freeze = dict(freeze, method="cache:aave_rseth_freeze_block.json")
    except FileNotFoundError as exc:
        provenance["aave_rseth_freeze_block.json"] = f"missing: {exc}"
        freeze = {"error": str(exc)}

    for utc, entry in series.items():
        entry.setdefault("block_ts", None)

    annotations = annotate_block_estimates(series)
    repair_rows = repairs + [row for row in annotations["repairs"] if row not in repairs]
    mismatches = annotations["mismatches"]
    if repair_rows:
        log(f"cache rebuild: {len(repair_rows)} archived row(s) re-placed (label/block mismatch)")
    if mismatches:
        log(f"cache rebuild: {len(mismatches)} point(s) still carry a drifting label (flagged in place)")
    log(f"cache rebuild: {len(series)} points from {len(provenance)} candidate files")
    return {
        "series": dict(sorted(series.items(), key=lambda item: item[1].get("ts") or 0)),
        "freeze_transition": freeze,
        "events": [dict(event) for event in EVENTS],
        "reference_blocks": REFERENCE_BLOCKS,
        "label_repairs": repair_rows,
        "label_mismatches": mismatches,
        "cache_provenance": provenance,
        "meta": {
            "episode": "rsETH / KelpDAO -- Aave V3 Ethereum Core",
            "mode": "cache",
            "grid_key": "cache:w2a+w2b",
            "generated_utc": utc_now(),
            "complete": True,
            "reserves": dict(RESERVES),
            "scope": "Aave V3 Ethereum Core, reserves rsETH (collateral), WETH and USDC; "
                     "points are those archived by W2-A/W2-B (12 h grid + key blocks)",
            "note": "offline rebuild from fixtures/raw_w2a + fixtures/raw_w2b (no network call)",
            "cache_files": list(CACHE_FILES),
            "label_caveat": "the archived UTC labels are estimated for part of the grid; every row "
                            "whose label disagrees with its own block by more than 2 h is re-placed "
                            "at the estimated time (original label kept as archived_label, list in "
                            "label_repairs)",
        },
    }


def utc_iso_from_label(label: str) -> str:
    """W2-A key labels (``AVANT 18/04 ~17:21 UTC|rsETH``) -> ISO UTC."""
    known = {
        "AVANT 18/04 ~17:21 UTC": "2026-04-18T17:21:00Z",
        "AU GEL 18:52 UTC": "2026-04-18T18:52:00Z",
        "APRES gel ~18:57": "2026-04-18T18:57:00Z",
        "APRES gel ~19:07": "2026-04-18T19:07:00Z",
        "20/04 00:00 UTC": "2026-04-20T00:00:00Z",
    }
    for prefix, iso in known.items():
        if label.startswith(prefix):
            return iso
    raise KeyError(f"unknown W2-A label: {label!r}")


def estimate_utc(block: Optional[int]) -> Optional[int]:
    """Linear block -> timestamp estimate, anchored on the measured freeze block.

    Only used to expose, in ``--from-cache`` mode, the archived labels that do not
    match the block they carry (the estimate is good to a few minutes here).
    """
    if not block:
        return None
    anchor_block, anchor_ts = BLOCK_TIME_ANCHOR
    return int(anchor_ts + (int(block) - anchor_block) * SECONDS_PER_BLOCK)


def annotate_block_estimates(series: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Add ``block_utc_estimate`` to cache points; split the labels in two lists.

    Returns ``{"repairs": [...], "mismatches": [...]}``:

    * ``repairs``  -- archived labels that disagreed with their own block by more than
      2 h and were therefore **re-placed** at the estimated time (their ``archived_label``
      is kept on the point);
    * ``mismatches`` -- points still keyed by a drifting label (a point whose block is
      unknown cannot be re-placed, so it is flagged instead of being trusted).
    """
    repairs: List[Dict[str, Any]] = []
    mismatches: List[Dict[str, Any]] = []
    for utc, point in series.items():
        estimate = estimate_utc(point.get("block"))
        if estimate is None:
            continue
        point["block_utc_estimate"] = utc_iso(estimate)
        drifted = abs(estimate - parse_utc(utc))
        if drifted <= 7200:
            continue
        row = {
            "key": utc,
            "block": point["block"],
            "block_utc_estimate": point["block_utc_estimate"],
            "mismatch_hours": round(drifted / 3600.0, 1),
        }
        archived_label = point.get("archived_label")
        if archived_label:
            row["archived_label"] = archived_label
            repairs.append(row)
        else:
            point["label_mismatch_hours"] = row["mismatch_hours"]
            mismatches.append(row)
    return {"repairs": repairs, "mismatches": mismatches}


# --------------------------------------------------------------------------- #
# Headline metrics (computed from whichever series was produced)
# --------------------------------------------------------------------------- #
def _nearest_point(
    points: List[Any], iso: str, tolerance_s: int = 6 * 3600
) -> Optional[Any]:
    """Closest series point to ``iso`` within ``tolerance_s`` (grids differ between modes)."""
    target = parse_utc(iso)
    best = None
    for utc, point in points:
        delta = abs(parse_utc(utc) - target)
        if delta <= tolerance_s and (best is None or delta < best[0]):
            best = (delta, utc, point)
    return (best[1], best[2]) if best else None


def compute_headline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The citable figures of the episode, measured on the produced series."""
    points = [
        (utc, point)
        for utc, point in (payload.get("series") or {}).items()
        if isinstance(point, dict) and isinstance(point.get("rsETH"), dict)
    ]
    headline: Dict[str, Any] = {}

    capped = [(utc, p) for utc, p in points if p["rsETH"].get("cap_ratio") is not None]
    if capped:
        utc, point = max(capped, key=lambda item: item[1]["rsETH"]["cap_ratio"])
        headline["cap_ratio_max"] = point["rsETH"]["cap_ratio"]
        headline["cap_ratio_max_utc"] = utc
        headline["cap_ratio_max_block"] = point.get("block")
        headline["supply_cap_rsETH"] = point["rsETH"].get("supply_cap")
        headline["a_token_supply_at_cap_max"] = point["rsETH"].get("a_token_supply")

    frozen = [(utc, p) for utc, p in points if p["rsETH"].get("is_frozen") is not None]
    transitions = [
        (utc, p) for index, (utc, p) in enumerate(frozen)
        if index and frozen[index - 1][1]["rsETH"]["is_frozen"] != p["rsETH"]["is_frozen"]
    ]
    notes: List[str] = []
    freeze_transition = payload.get("freeze_transition") or {}
    authoritative_ts = freeze_transition.get("first_frozen_ts")
    if authoritative_ts is None and freeze_transition.get("first_frozen_utc"):
        authoritative_ts = parse_utc(freeze_transition["first_frozen_utc"])
    if transitions:
        utc, point = transitions[0]
        headline["rsETH_frozen_transition_utc_series"] = utc
        headline["rsETH_frozen_transition_block_series"] = point.get("block")
        if not freeze_transition.get("first_frozen_utc"):
            headline["rsETH_frozen_transition_utc"] = utc
            headline["rsETH_frozen_transition_block"] = point.get("block")
            headline["rsETH_frozen_transition_source"] = "series (first point with isFrozen = true)"
    if freeze_transition.get("first_frozen_utc"):
        headline["rsETH_frozen_transition_utc"] = freeze_transition["first_frozen_utc"]
        headline["rsETH_frozen_transition_block"] = freeze_transition["first_frozen_block"]
        headline["rsETH_frozen_transition_source"] = freeze_transition.get(
            "method", "binary search on the isFrozen bit"
        )
        headline["freeze_transition"] = freeze_transition
        series_ts = transitions[0][1].get("ts") if transitions else None
        if series_ts is not None and authoritative_ts is not None and abs(int(series_ts) - int(authoritative_ts)) > 2 * GRID_STEP:
            notes.append(
                f"the archived series flips isFrozen at {transitions[0][0]} (block "
                f"{transitions[0][1].get('block')}) while the binary search dates the freeze at "
                f"{freeze_transition.get('first_frozen_utc')} (block {freeze_transition.get('first_frozen_block')}): "
                f"the archived grid labels are the unreliable side (cache mode)"
            )

    oracle_points = [(utc, p) for utc, p in points if p["rsETH"].get("oracle_price") is not None]
    if oracle_points:
        headline["rsETH_oracle_first"] = {
            "utc": oracle_points[0][0],
            "price": oracle_points[0][1]["rsETH"]["oracle_price"],
        }
        peak = max(oracle_points, key=lambda item: item[1]["rsETH"]["oracle_price"])
        worst = min(oracle_points, key=lambda item: item[1]["rsETH"]["oracle_price"])
        headline["rsETH_oracle_peak"] = {"utc": peak[0], "price": peak[1]["rsETH"]["oracle_price"]}
        headline["rsETH_oracle_session_low"] = {"utc": worst[0], "price": worst[1]["rsETH"]["oracle_price"]}
        # The three readings the dossier cites, taken at the closest point of whichever
        # grid was produced (the RPC grid carries the exact timestamps as keys).
        for label in ("2026-04-18T17:35:00Z", "2026-04-18T19:03:59Z", "2026-04-20T00:00:00Z"):
            match = _nearest_point(oracle_points, label)
            if match is None:
                continue
            headline[f"rsETH_oracle_at_{label}"] = match[1]["rsETH"]["oracle_price"]
            headline[f"rsETH_oracle_at_{label}_utc"] = match[0]

    weth = [(utc, p) for utc, p in points if isinstance(p.get("WETH"), dict) and p["WETH"].get("utilisation") is not None]
    if weth:
        utc, point = max(weth, key=lambda item: item[1]["WETH"]["utilisation"])
        headline["weth_utilisation_peak"] = point["WETH"]["utilisation"]
        headline["weth_utilisation_peak_utc"] = utc
        headline["weth_utilisation_peak_block"] = point.get("block")
        headline["weth_a_token_supply_at_peak"] = point["WETH"].get("a_token_supply")

    if payload.get("feed_checks"):
        headline["capped_feed_checks"] = [
            {"block": check.get("block"), "description": check.get("description"), "equal": check.get("equal")}
            for check in payload["feed_checks"]
        ]
    if notes:
        headline["notes"] = notes
    return headline


def summarise(payload: Dict[str, Any], output_path: str) -> str:
    """Readable run summary (what was measured, where it landed)."""
    series = payload.get("series") or {}
    headline = payload.get("headline") or {}
    errors = [utc for utc, point in series.items() if point.get("error")]
    oracle_first = headline.get("rsETH_oracle_first") or {}
    oracle_20 = headline.get("rsETH_oracle_at_2026-04-20T00:00:00Z")
    weth_peak = headline.get("weth_utilisation_peak")
    lines = [
        f"episode rsETH 2026-04 -- mode {payload['meta']['mode']} -- {len(series)} points -> {output_path}",
        f"  supplyCap rsETH sature : {headline.get('cap_ratio_max')} le {headline.get('cap_ratio_max_utc')} "
        f"(aToken {headline.get('a_token_supply_at_cap_max')} / cap {headline.get('supply_cap_rsETH')})",
        f"  gel on-chain (isFrozen): {headline.get('rsETH_frozen_transition_utc')} "
        f"(bloc {headline.get('rsETH_frozen_transition_block')})",
        f"  oracle rsETH retenu    : {oracle_first.get('price')} $ le {oracle_first.get('utc')}"
        + (f", {oracle_20} $ le 2026-04-20" if oracle_20 is not None else ""),
        f"  utilisation WETH pic   : {weth_peak} le {headline.get('weth_utilisation_peak_utc')}"
        if weth_peak is not None else "  utilisation WETH pic   : n/a (mode cache: pas de point WETH)",
    ]
    if errors:
        lines.append(f"  points en erreur       : {len(errors)} ({errors[:3]}...)")
    if payload.get("label_repairs"):
        lines.append(f"  labels re-places       : {len(payload['label_repairs'])} (voir label_repairs)")
    if payload.get("label_mismatches"):
        lines.append(f"  labels incoherents     : {len(payload['label_mismatches'])} (voir label_mismatches)")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the rsETH / KelpDAO April-2026 episode into evidence JSON.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="output evidence file")
    parser.add_argument("--from-cache", action="store_true", help="rebuild from fixtures/raw_w2* without any network call")
    parser.add_argument("--workers", type=int, default=6, help="parallel workers for the RPC phase (default 6)")
    parser.add_argument("--no-resume", action="store_true", help="ignore points already present in the output file")
    parser.add_argument("--quiet", action="store_true", help="only print the final summary")
    args = parser.parse_args(argv)

    def log(message: str) -> None:
        if not args.quiet:
            print(message, flush=True)

    if args.from_cache:
        payload = collect_from_cache(log)
    else:
        try:
            payload = collect_network(args.out, workers=args.workers, resume=not args.no_resume, log=log)
        except Exception as exc:
            print(f"[rseth] network run failed ({type(exc).__name__}: {exc}) -- falling back to --from-cache",
                  file=sys.stderr, flush=True)
            payload = collect_from_cache(log)

    payload["headline"] = compute_headline(payload)
    payload["limitations"] = [
        "rsETH is priced in USD by the Capped rsETH / ETH / USD feed, whose latestRoundData() reverts: "
        "no oracle freshness (updatedAt) is available for that reserve.",
        "The realisable value of the rsETH collateral is not readable from this data layer (no liquid "
        "venue for a stolen/unbacked rsETH): the series documents the retained price, not the exit price.",
        "Bad debt (123.7 / 230.1 M$ per the Aave incident report) is out of scope here: it needs the "
        "per-account debt ledger, not reserve aggregates.",
    ]
    dump_json_atomic(args.out, payload)
    print(summarise(payload, args.out), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
