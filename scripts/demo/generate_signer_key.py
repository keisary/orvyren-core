#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit (W5, L5.2): **throwaway key generation**.

Generates a throwaway EOA **locally** (``eth-account``, the same isolated
exception as ``signer.py`` — B5 §a.1) and writes it into the session env file:

* ``ORVYREN_PRIVATE_KEY`` — the key (never displayed, never transmitted);
* ``ORVYREN_AGENT_ADDRESS`` — the derived (public) address, to be funded via the
  free faucets.

Safeguards: refuses to overwrite an existing key without ``--force``; output
file in ``chmod 600`` when the platform allows it; the key **never** appears
in stdout/stderr nor in an error message.

CLI:

    python scripts/demo/generate_signer_key.py            # writes to scripts/demo/.env
    python scripts/demo/generate_signer_key.py --check    # checks/recalls the derived address
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:  # package (``demo.generate_signer_key``)
    from . import common
except ImportError:  # direct execution: python scripts/demo/generate_signer_key.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV = os.path.join(HERE, ".env")
TEMPLATE_ENV = os.path.join(HERE, "config.example.env")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_DEPENDENCY = 3
EXIT_REFUSED = 4

KEY_LINE = re.compile(r"^(ORVYREN_PRIVATE_KEY\s*=).*$")
ADDRESS_LINE = re.compile(r"^(ORVYREN_AGENT_ADDRESS\s*=).*$")


def _require_eth_account() -> Any:
    try:
        from eth_account import Account  # type: ignore
    except ImportError:
        print("generate_signer_key: eth-account required — install \"pip install "
              "eth-account==0.14.0\" (the kit's only external dependency, isolated to the "
              "signer).", file=sys.stderr)
        raise SystemExit(EXIT_DEPENDENCY)
    return Account


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().split("\n")


def _write_lines(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    try:  # chmod 600 when the platform allows it (POSIX)
        os.chmod(path, 0o600)
    except OSError:
        pass


def _assign(lines: List[str], pattern: "re.Pattern[str]", value: str,
            key_name: str) -> List[str]:
    replaced = False
    result: List[str] = []
    for line in lines:
        match = pattern.match(line)
        if match and not replaced:
            result.append("%s%s" % (match.group(1), value))
            replaced = True
        else:
            result.append(line)
    if not replaced:
        result.append("%s=%s" % (key_name, value))
    return result


def check_existing(env_path: str) -> Dict[str, Any]:
    """Checks locally: derived address ↔ AGENT_ADDRESS line of the file."""
    Account = _require_eth_account()
    values = common.read_env_file(env_path)
    out: Dict[str, Any] = {"env_file": common.display_path(env_path),
                           "file_exists": os.path.isfile(env_path)}
    key = values.get("ORVYREN_PRIVATE_KEY", "").strip()
    if not key:
        out["key_present"] = False
        out["detail"] = "no key in the file — nothing to check"
        return out
    out["key_present"] = True
    try:
        address = Account.from_key(key).address
    except Exception:
        out["derived_address_ok"] = False
        out["detail"] = "key present but unreadable (value never displayed)"
        return out
    declared = values.get("ORVYREN_AGENT_ADDRESS", "").strip()
    out["derived_address"] = address
    out["declared_address"] = declared
    out["match"] = bool(declared) and declared.lower() == address.lower()
    out["detail"] = ("derived address == ORVYREN_AGENT_ADDRESS" if out["match"]
                     else "mismatch: update ORVYREN_AGENT_ADDRESS with the derived address")
    return out


def generate(env_path: str, *, force: bool) -> Dict[str, Any]:
    Account = _require_eth_account()
    if os.path.isfile(env_path):
        existing = common.read_env_file(env_path).get("ORVYREN_PRIVATE_KEY", "").strip()
        if existing and not force:
            print("generate_signer_key: a key is already present in %s — refusing "
                  "to overwrite without --force (an overwritten key = an abandoned address)."
                  % common.display_path(env_path), file=sys.stderr)
            raise SystemExit(EXIT_REFUSED)
        lines = _read_lines(env_path)
    else:
        if os.path.isfile(TEMPLATE_ENV):
            lines = _read_lines(TEMPLATE_ENV)
        else:
            lines = ["# ORVYREN — session env (generated)"]
    account = Account.create()
    private_key = account.key.hex()
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    address = account.address
    lines = _assign(lines, KEY_LINE, private_key, "ORVYREN_PRIVATE_KEY")
    lines = _assign(lines, ADDRESS_LINE, address, "ORVYREN_AGENT_ADDRESS")
    _write_lines(env_path, lines)
    return {"env_file": common.display_path(env_path), "agent_address": address,
            "wrote_key": True, "note": "throwaway key — destroy it after the demo "
                                       "(erase the line from the file)"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_signer_key.py",
        description="ORVYREN (W5/L5.2) — generates the EOA agent throwaway key and "
                    "writes it into the session env (never displayed). Testnet "
                    "only.")
    parser.add_argument("--env-file", default=DEFAULT_ENV)
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing key (discouraged)")
    parser.add_argument("--check", action="store_true",
                        help="check the derived address without writing anything")
    args = parser.parse_args(argv)

    if args.check:
        report = check_existing(args.env_file)
        for key, value in report.items():
            print("  %-18s %s" % (key, value))
        return EXIT_OK if report.get("match") or not report.get("key_present") else 1
    report = generate(args.env_file, force=args.force)
    print("generate_signer_key: throwaway key written to %s (never displayed)" % report["env_file"])
    print("  agent_address  : %s" % report["agent_address"])
    print("  next steps: fund the address via the free faucets, then")
    print("  rerun \"python scripts/demo/faucet_check.py --rpc\".")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
