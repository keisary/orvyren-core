#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — testnet demo kit: **isolated signer service** (W3-D, B5 §a.1).

This is the ONLY kit module allowed to import an external library
(``eth-account``, MIT, isolated). No other kit module imports it.

Two modes:

* ``--dry-run`` (default): **simulated signature** — no key read, no network,
  no message signed; the "transaction hash" produced is explicitly a
  placeholder (derived with SHA-256 from the content, tagged ``simulated: true``);
* ``--execute``: real signature through ``eth-account`` **if installed**; otherwise
  a clear install message and exit code 3. The key is read **only** from
  ``ORVYREN_PRIVATE_KEY`` (process environment), never displayed, never
  journaled, never written to disk.

Invariants (B5 §a.1):

* S2 — the key lives only in the process environment variable;
* S3 — never in a log, a prompt, a file, an error message;
* S7 — the signer knows neither the LLM, nor the graph, nor the policy: it
  receives an **already authorized** transaction (traced ALLOW verdict);
* S10 — the journal records only the address and the hash, never the key.

CLI:

    python scripts/demo/signer.py --check
    python scripts/demo/signer.py --dry-run --tx-file tx.example.json
    python scripts/demo/signer.py --address   # derived address (real mode), to compare with ORVYREN_AGENT_ADDRESS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:  # package (``demo.signer``)
    from . import common
except ImportError:  # direct execution: python scripts/demo/signer.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

KEY_ENV_NAME = "ORVYREN_PRIVATE_KEY"
EXIT_USAGE = 2
EXIT_DEPENDENCY = 3
EXIT_KEY = 4


class SignerError(Exception):
    """Signer service error (never any key material in the message)."""


class SignerDependencyError(SignerError):
    """Signing library missing (``eth-account``)."""


def _import_account():
    """Deferred import of ``eth-account`` (dependency isolated to the signer alone)."""
    try:
        from eth_account import Account  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on the environment
        raise SignerDependencyError(
            "real signing requires the isolated eth-account library — "
            "install with: python -m pip install eth-account   (MIT; to be declared in LICENSES.md). "
            "The --dry-run mode works without it.") from exc
    return Account


def _is_hex_key(value: str) -> bool:
    text = value.strip()
    body = text[2:] if text.startswith("0x") else text
    return len(body) == 64 and all(c in "0123456789abcdefABCDEF" for c in body)


def fake_tx_hash(tx: Dict[str, Any]) -> str:
    """**Placeholder** deterministic hash of a simulated transaction (never a chain hash)."""
    return "0x" + common.sha256_hex(common.canonical_json(tx).encode("utf-8"))


class Signer:
    """Isolated signer: receives a ready transaction, returns a hash (or refuses).

    ``dry_run=True``: no key is read, no network is touched.
    ``dry_run=False``: the key is read from the process environment and
    passed to ``eth-account``; nothing but the address and the hash comes out.
    """

    def __init__(self, *, rpc_url: str = common.DEFAULT_RPC_URL, chain_id: int = common.CHAIN_ID_DEMO,
                 dry_run: bool = True, signature_log: Optional[common.SignatureLog] = None,
                 env: Optional[Dict[str, str]] = None):
        self.rpc_url = rpc_url
        self.chain_id = int(chain_id)
        self.dry_run = bool(dry_run)
        self.signature_log = signature_log
        self.env = os.environ if env is None else env
        self._address: Optional[str] = None

    # --- state (never a key value) --------------------------------------------

    def key_present(self) -> bool:
        """Is the key variable present and well formed? (name only, never the value)."""
        value = (self.env.get(KEY_ENV_NAME) or "").strip()
        return bool(value) and _is_hex_key(value)

    def library_available(self) -> bool:
        try:
            _import_account()
            return True
        except SignerDependencyError:
            return False

    def address(self) -> Optional[str]:
        """Public address derived from the key (real mode). The address is not a secret."""
        if self._address:
            return self._address
        if self.dry_run:
            return None
        key = (self.env.get(KEY_ENV_NAME) or "").strip()
        if not _is_hex_key(key):
            raise SignerError(
                "{} missing or malformed (32 hex bytes expected) — no signature issued".format(KEY_ENV_NAME))
        account = _import_account().from_key(key)
        self._address = str(account.address).lower()
        return self._address

    # --- signature ------------------------------------------------------------

    def sign_transaction(self, tx: Dict[str, Any], *, intent_id: str = "") -> Dict[str, Any]:
        """Signs an **already authorized** transaction.

        Returns ``{"mode", "tx_hash", "simulated", "signed_transaction"(hex, never journaled),
        "address"}``. In dry-run: placeholder hash, no network access, no key.
        """
        if not isinstance(tx, dict):
            raise SignerError("transaction expected as an object")
        for forbidden in ("privateKey", "private_key", "secret", "mnemonic"):
            if forbidden in tx:
                raise SignerError("forbidden field in a transaction: {!r}".format(forbidden))
        if int(tx.get("chainId", self.chain_id)) != self.chain_id:
            raise SignerError("transaction chainId ≠ pinned chain {}".format(self.chain_id))

        if self.dry_run:
            digest = fake_tx_hash({"tx": tx, "intent_id": intent_id})
            result = {
                "mode": "dry-run",
                "simulated": True,
                "tx_hash": digest,
                "signed_transaction": None,
                "address": None,
                "note": "simulated signature: no key read, no network, no message signed "
                        "(the hash is a placeholder and must never be mistaken for a chain hash)",
            }
            if self.signature_log is not None:
                self.signature_log.append(intent_id=intent_id or "-", mode="dry-run",
                                          tx_hash=digest, note="simulated")
            return result

        account = _import_account()
        key = (self.env.get(KEY_ENV_NAME) or "").strip()
        if not _is_hex_key(key):
            raise SignerError(
                "{} missing or malformed — real signing refused".format(KEY_ENV_NAME))
        local = account.from_key(key)
        if "from" in tx:
            # eth-account requires the exact EIP-55 address in 'from' (stdlib builders
            # normalize addresses to lowercase): check, then rewrite with the key's casing.
            if str(tx["from"]).strip().lower() != str(local.address).lower():
                raise SignerError(
                    "'from' field inconsistent with the key's address — signature refused")
            tx = {**tx, "from": local.address}
        if tx.get("to"):
            # eth-account also rejects a non-checksummed 'to': normalize to EIP-55
            # (casing does not change the signed bytes) — incident measured on 2026-10-16.
            try:
                from eth_utils import to_checksum_address  # eth-account dependency
                tx = {**tx, "to": to_checksum_address(str(tx["to"]).strip())}
            except Exception as exc:
                raise SignerError(
                    "'to' field not convertible to an EIP-55 address — signature refused") from exc
        signed = local.sign_transaction(tx)
        # ``signed.hash`` (eth-account) is the keccak of the signed transaction.
        tx_hash = str(getattr(signed, "hash", b"").hex()) if hasattr(signed, "hash") else ""
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash if tx_hash else ""
        raw_hex = signed.raw_transaction.hex()
        if not raw_hex.startswith("0x"):
            raw_hex = "0x" + raw_hex
        result = {
            "mode": "execute",
            "simulated": False,
            "tx_hash": tx_hash.lower(),
            "signed_transaction": raw_hex,   # in memory only — never journaled
            "address": str(local.address).lower(),
            "note": "signed transaction ready to broadcast (one in flight at a time)",
        }
        if self.signature_log is not None:
            self.signature_log.append(intent_id=intent_id or "-", mode="execute",
                                      tx_hash=result["tx_hash"], note="signed")
        return result

    def send_raw_transaction(self, raw_hex: str, *, timeout: int = common.RPC_TIMEOUT_SECONDS) -> str:
        """Broadcasts a signed transaction (real mode only). Idempotent re-broadcast tolerated."""
        if self.dry_run:
            raise SignerError("send_raw_transaction is forbidden in dry-run")
        result = common.rpc(self.rpc_url, "eth_sendRawTransaction", [raw_hex], timeout)
        if not isinstance(result, str) or not result.startswith("0x"):
            raise SignerError("unexpected response to eth_sendRawTransaction")
        return result.lower()

    def safe_dict(self) -> Dict[str, Any]:
        return {
            "signer": "scripts/demo/signer.py (isolated)",
            "mode": "dry-run" if self.dry_run else "execute",
            "library_available": self.library_available(),
            "key_env_name": KEY_ENV_NAME,
            "key_present": self.key_present(),
            "rpc_masked": common.mask_rpc_url(self.rpc_url),
            "chain_id": self.chain_id,
            "key_material": "never read in dry-run; never logged in any mode",
        }


# --- CLI ---------------------------------------------------------------------


def _print_check(signer: Signer) -> int:
    info = signer.safe_dict()
    print("ORVYREN — signer service check (no key displayed)")
    print("  eth-account library: {}".format("present" if info["library_available"] else "MISSING"))
    print("  variable {}: {}".format(KEY_ENV_NAME, "present" if info["key_present"] else "missing/empty"))
    print("  RPC: {}".format(info["rpc_masked"]))
    print("  mode: {}".format(info["mode"]))
    if not info["library_available"]:
        print("  → real signing unavailable: python -m pip install eth-account")
    if not info["key_present"]:
        print("  → key missing: set {} in .env (never versioned) or in the environment".format(KEY_ENV_NAME))
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="signer.py",
        description="ORVYREN — isolated signer service (simulated dry-run / execute with eth-account). "
                    "Never a journaled key.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="simulated signature: no key read, no network (default)")
    mode.add_argument("--execute", action="store_true", help="real signature (requires eth-account + ORVYREN_PRIVATE_KEY)")
    parser.add_argument("--check", action="store_true", help="service state: library, key presence (by name)")
    parser.add_argument("--address", action="store_true", help="public address derived from the key (real mode)")
    parser.add_argument("--tx-file", help="JSON file of a transaction to sign (example: tx.example.json)")
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or common.DEFAULT_RPC_URL)
    args = parser.parse_args(argv)

    dry_run = not args.execute
    if args.dry_run:
        dry_run = True
    signer = Signer(rpc_url=args.rpc_url, dry_run=dry_run)

    if args.check:
        return _print_check(signer)

    if args.address:
        if dry_run:
            print("dry-run mode: no derived address (no key read)")
            return 0
        try:
            print(signer.address())
            return 0
        except SignerError as exc:
            print("ERROR: {}".format(exc), file=sys.stderr)
            return EXIT_KEY

    if not args.tx_file:
        parser.print_help()
        return EXIT_USAGE

    try:
        with open(args.tx_file, "r", encoding="utf-8") as handle:
            tx = json.load(handle)
    except (OSError, ValueError) as exc:
        print("ERROR: unreadable transaction: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    try:
        result = signer.sign_transaction(tx, intent_id=str(tx.get("intent_id") or ""))
    except SignerDependencyError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_DEPENDENCY
    except SignerError as exc:
        print("ERROR: {}".format(exc), file=sys.stderr)
        return EXIT_KEY

    print("mode: {}".format(result["mode"]))
    print("hash: {}".format(result["tx_hash"]))
    if result.get("simulated"):
        print("(PLACEHOLDER hash — simulated signature, no transaction exists on any chain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
