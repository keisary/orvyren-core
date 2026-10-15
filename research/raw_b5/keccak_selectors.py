#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""B5 — Keccak-256 en Python pur (stdlib) pour vérifier les sélecteurs de fonction.

Vecteurs de contrôle (connus) :
  keccak256(b"")    = c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
  keccak256(b"abc") = 4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45
Sélecteur = 4 premiers octets du keccak256 de la signature canonique ASCII.
"""
import json

RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
ROT = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]
MASK = (1 << 64) - 1


def _rol(x, n):
    n %= 64
    return ((x << n) | (x >> (64 - n))) & MASK if n else x


def keccak_f(a):
    for rnd in range(24):
        # theta
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        # rho + pi
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], ROT[x][y])
        # chi
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
        # iota
        a[0][0] ^= RC[rnd]
    return a


def keccak256(data: bytes) -> bytes:
    rate = 136  # 1088 bits
    # padding Keccak original : 0x01 ... 0x80
    padlen = rate - (len(data) % rate)
    if padlen == 1:
        padded = data + b"\x81"
    else:
        padded = data + b"\x01" + b"\x00" * (padlen - 2) + b"\x80"
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8:(i + 1) * 8], "little")
            x, y = i % 5, i // 5
            a[x][y] ^= lane
        keccak_f(a)
    out = b""
    for i in range(4):  # 4 lanes = 32 bytes
        x, y = i % 5, i // 5
        out += a[x][y].to_bytes(8, "little")
    return out


def selector(sig: str) -> str:
    return "0x" + keccak256(sig.encode("ascii"))[:4].hex()


def main():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470", "vecteur vide KO"
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45", "vecteur abc KO"
    print("vecteurs keccak OK")

    sigs = {
        "transfer(address,uint256)": "0xa9059cbb",
        "approve(address,uint256)": "0x095ea7b3",
        "allowance(address,address)": "0xdd62ed3e",
        "balanceOf(address)": "0x70a08231",
        "repay(address,uint256,address)": "?",
        "repay(address,uint256,uint256,address)": "?",
        "supply(address,uint256,address,uint16)": "?",
        "withdraw(address,uint256,address)": "?",
        "exactInputSingle((address,address,uint24,address,uint256,uint256,uint160))": "?",
        "exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))": "?",
        "quoteExactInputSingle((address,address,uint256,uint24,uint160))": "?",
        "getUserAccountData(address)": "?",
        "getReservesList()": "?",
        "getReserveData(address)": "0x35ea6a75",
        "getPool(address,address,uint24)": "0x1698ee82",
        "execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)": "?",
        "execTransactionWithRoleReturnData(address,uint256,bytes,uint8,bytes32,bool)": "?",
        "assignRoles(address,bytes32[],bool[])": "?",
        "Transfer(address,address,uint256)": "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
    }
    out = {}
    for sig, expected in sigs.items():
        sel = selector(sig)
        ok = "" if expected in ("?",) else ("  OK" if sel == expected else "  <<< ÉCART vs " + expected)
        print(f"{sel}  {sig}{ok}")
        out[sig] = sel
    with open("D:/orvyren_core/research/raw_b5/selectors_keccak.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    main()
