#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — décodage des sorties RPC brutes (Base Sepolia, 2026-10-15). Stdlib only."""
import json
import re

RAW = "D:/orvyren_core/research/raw_b5"


def words(hexstr):
    body = hexstr[2:]
    assert len(body) % 64 == 0, "not word aligned: %d" % len(body)
    return [body[i:i + 64] for i in range(0, len(body), 64)]


def addr_of(word):
    return "0x" + word[-40:]


RESULT_RE = re.compile(r'"result":"(0x[0-9a-fA-F]*)"')


def collect_results(path):
    """[(line_index, prev_header, hex_result)]"""
    lines = open(path, encoding="utf-8").read().splitlines()
    rows = []
    prev_header = ""
    for i, ln in enumerate(lines):
        if ln.startswith("==="):
            prev_header = ln.strip("= ").strip()
            continue
        if ln.startswith("getCode"):
            continue
        m = RESULT_RE.search(ln)
        if m:
            rows.append((i, prev_header, m.group(1)))
    return rows


def main():
    out = {}
    rows1 = collect_results(f"{RAW}/rpc_b5_probe_output.txt")
    rows2 = collect_results(f"{RAW}/rpc_b5_probe2_output.txt")
    rows3 = collect_results(f"{RAW}/rpc_b5_probe3_output.txt")

    def one(rows, header_sub, last=False):
        hits = [r for r in rows if header_sub.lower() in r[1].lower()]
        if not hits:
            return None, None
        _, hdr, val = hits[-1] if last else hits[0]
        return hdr, val

    # ---- probe1 ----
    hdr, val = one(rows1, "liquidity() + slot0()")
    # ce header contient les 4 lignes; on filtre sur le résultat de slot0 via longueur 7 mots
    w7 = [r for r in rows1 if len(r[2]) == 2 + 64 * 7]
    hdr0, slot0 = w7[0][1], w7[0][2]
    w = words(slot0)
    sqrt_price = int(w[0], 16)
    tick = int(w[1], 16)
    if tick >= 2 ** 23:
        tick -= 2 ** 24
    price_usdc_per_weth = 1e12 / ((sqrt_price / 2 ** 96) ** 2)
    out["pool_usdc_circle_weth_3000"] = {
        "sqrtPriceX96": w[0], "tick": tick,
        "price_usdc_per_weth": round(price_usdc_per_weth, 2),
    }

    liq_rows = [r for r in rows1 if len(r[2]) == 2 + 64 and int(r[2], 16) < 2 ** 200
                and int(r[2], 16) > 0]
    out["liquidity_small_words_probe1"] = [(r[1], r[2]) for r in liq_rows]

    # quoter probe1: la ligne apres le header QuoterV2
    for i, ln in enumerate(open(f"{RAW}/rpc_b5_probe_output.txt", encoding="utf-8")):
        pass
    lines1 = open(f"{RAW}/rpc_b5_probe_output.txt", encoding="utf-8").read().splitlines()
    for idx, ln in enumerate(lines1):
        if ln.startswith("=== QuoterV2"):
            m = RESULT_RE.search(lines1[idx + 1])
            qw = words(m.group(1))
            out["quoter_circle_usdc_50_fee3000"] = {
                "amountOut_wei": int(qw[0], 16),
                "amountOut_eth": int(qw[0], 16) / 1e18,
                "initializedTicksCrossed": int(qw[2], 16),
                "gasEstimate": int(qw[3], 16),
            }

    # getReserveData(Circle USDC) probe1 — attendu vide si non listé
    for idx, ln in enumerate(lines1):
        if ln.startswith("=== Aave v3 Pool getReserveData(USDC)"):
            m = RESULT_RE.search(lines1[idx + 1])
            rw = words(m.group(1))
            out["getReserveData_circle_usdc"] = {
                "words": len(rw),
                "nonzero_words": [(j, rw[j]) for j in range(len(rw)) if int(rw[j], 16) != 0],
            }

    # ---- probe2 : réserves Aave ----
    def reserve_decode(marker):
        lines2 = open(f"{RAW}/rpc_b5_probe2_output.txt", encoding="utf-8").read().splitlines()
        for idx, ln in enumerate(lines2):
            if ln.startswith(marker):
                m = RESULT_RE.search(lines2[idx + 1])
                rw = words(m.group(1))
                cfg = int(rw[0], 16)
                return {
                    "words": len(rw),
                    "LTV_bps": cfg & 0xFFFF,
                    "liqThreshold_bps": (cfg >> 16) & 0xFFFF,
                    "liqBonus_bps": (cfg >> 32) & 0xFFFF,
                    "decimals": (cfg >> 48) & 0xFF,
                    "isActive": (cfg >> 56) & 1,
                    "isFrozen": (cfg >> 57) & 1,
                    "borrowingEnabled": (cfg >> 58) & 1,
                    "paused": (cfg >> 60) & 1,
                    "reserveFactor_bps": (cfg >> 64) & 0xFFFF,
                    "borrowCap_whole": (cfg >> 80) & 0xFFFFFFFF,
                    "supplyCap_whole": (cfg >> 116) & 0xFFFFFFFF,
                    "liquidityIndex_ray": int(rw[1], 16) / 1e27,
                    "currentLiquidityRate_pct": int(rw[2], 16) / 1e27 * 100,
                    "currentVariableBorrowRate_pct": int(rw[4], 16) / 1e27 * 100,
                    "lastUpdateTimestamp": int(rw[6], 16),
                    "id": int(rw[7], 16),
                    "aTokenAddress": addr_of(rw[8]),
                    "variableDebtTokenAddress": addr_of(rw[10]),
                    "interestRateStrategy": addr_of(rw[11]),
                }
        return None

    out["aave_usdc_reserve"] = reserve_decode("=== Aave getReserveData(AaveUSDC)")
    out["aave_weth_reserve"] = reserve_decode("=== Aave getReserveData(WETH)")

    # ---- probe3 ----
    lines3 = open(f"{RAW}/rpc_b5_probe3_output.txt", encoding="utf-8").read().splitlines()
    for idx, ln in enumerate(lines3):
        if ln.startswith("=== slot0 du pool AaveUSDC"):
            m = RESULT_RE.search(lines3[idx + 1])
            w = words(m.group(1))
            sp = int(w[0], 16)
            tk = int(w[1], 16)
            if tk >= 2 ** 23:
                tk -= 2 ** 24
            out["pool_aaveusdc_weth_3000"] = {
                "sqrtPriceX96": w[0], "tick": tk,
                "price_usdc_per_weth": round(1e12 / ((sp / 2 ** 96) ** 2), 4),
            }
        if ln.startswith("=== liquidity() pool AaveUSDC"):
            m = RESULT_RE.search(lines3[idx + 1])
            out["liquidity_aaveusdc_weth_3000"] = int(m.group(1), 16)
        if ln.startswith("=== QuoterV2 AaveUSDC"):
            m = RESULT_RE.search(lines3[idx + 1])
            qw = words(m.group(1))
            out["quoter_aaveusdc_50_fee3000"] = {
                "amountOut_wei": int(qw[0], 16),
                "initializedTicksCrossed": int(qw[2], 16),
                "gasEstimate": int(qw[3], 16),
            }
        if ln.startswith("=== QuoterV2 CircleUSDC(50e6)->WETH fee 500"):
            m = RESULT_RE.search(lines3[idx + 1])
            qw = words(m.group(1))
            out["quoter_circle_usdc_50_fee500"] = {
                "amountOut_wei": int(qw[0], 16),
                "initializedTicksCrossed": int(qw[2], 16),
                "gasEstimate": int(qw[3], 16),
            }

    # gaz/blocs
    out["gas"] = {"eth_gasPrice_wei": 0x5b8d80, "eth_maxPriorityFeePerGas_wei": 0xf4240,
                  "baseFeePerGas_latest_wei": 0x4c4b40}
    out["block_latest_number_hex"] = "0x2deb6b9"
    out["block_latest_number_dec"] = 0x2deb6b9
    out["block_timestamp_latest"] = 0x6ad0cc52

    import datetime
    out["block_timestamp_latest_iso"] = datetime.datetime.fromtimestamp(
        0x6ad0cc52, datetime.timezone.utc).isoformat()

    print(json.dumps(out, indent=2))
    with open(f"{RAW}/b5_decoded_rpc.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
