#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet : **service signataire isolé** (W3-D, B5 §a.1).

C'est le SEUL module du kit autorisé à importer une bibliothèque externe
(``eth-account``, MIT, isolé). Aucun autre module du kit ne l'importe.

Deux modes :

* ``--dry-run`` (défaut) : **signature simulée** — aucune clé lue, aucun réseau,
  aucun message signé ; le « hash de transaction » produit est explicitement
  factice (dérivé en SHA-256 du contenu, marqué ``simulated: true``) ;
* ``--execute`` : signature réelle par ``eth-account`` **si installé** ; sinon
  message d'installation clair et sortie 3. La clé est lue **uniquement** dans
  ``ORVYREN_PRIVATE_KEY`` (environnement du processus), jamais affichée, jamais
  journalisée, jamais écrite sur disque.

Invariants (B5 §a.1) :

* S2 — la clé ne vit que dans la variable d'environnement du processus ;
* S3 — jamais dans un log, un prompt, un fichier, un message d'erreur ;
* S7 — le signataire ne connaît ni le LLM, ni le graphe, ni la politique : il
  reçoit une transaction **déjà autorisée** (verdict ALLOW tracé) ;
* S10 — le journal n'enregistre que l'adresse et le hash, jamais la clé.

CLI :

    python scripts/demo/signer.py --check
    python scripts/demo/signer.py --dry-run --tx-file tx.example.json
    python scripts/demo/signer.py --address   # adresse dérivée (mode réel), à comparer à ORVYREN_AGENT_ADDRESS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

try:  # paquet (``demo.signer``)
    from . import common
except ImportError:  # exécution directe : python scripts/demo/signer.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

KEY_ENV_NAME = "ORVYREN_PRIVATE_KEY"
EXIT_USAGE = 2
EXIT_DEPENDENCY = 3
EXIT_KEY = 4


class SignerError(Exception):
    """Erreur du service signataire (jamais de matériel de clé dans le message)."""


class SignerDependencyError(SignerError):
    """Bibliothèque de signature absente (``eth-account``)."""


def _import_account():
    """Import retardé d'``eth-account`` (dépendance isolée au seul signataire)."""
    try:
        from eth_account import Account  # type: ignore
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        raise SignerDependencyError(
            "la signature réelle exige la bibliothèque isolée eth-account — "
            "installer avec : python -m pip install eth-account   (MIT ; à déclarer dans LICENSES.md). "
            "Le mode --dry-run fonctionne sans elle.") from exc
    return Account


def _is_hex_key(value: str) -> bool:
    text = value.strip()
    body = text[2:] if text.startswith("0x") else text
    return len(body) == 64 and all(c in "0123456789abcdefABCDEF" for c in body)


def fake_tx_hash(tx: Dict[str, Any]) -> str:
    """Hash **factice** et déterministe d'une transaction simulée (jamais un hash de chaîne)."""
    return "0x" + common.sha256_hex(common.canonical_json(tx).encode("utf-8"))


class Signer:
    """Signataire isolé : reçoit une transaction prête, rend un hash (ou refuse).

    ``dry_run=True`` : aucune clé n'est lue, aucun réseau n'est touché.
    ``dry_run=False`` : la clé est lue dans l'environnement du processus et
    passée à ``eth-account`` ; rien d'autre que l'adresse et le hash ne sort.
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

    # --- état (jamais de valeur de clé) --------------------------------------

    def key_present(self) -> bool:
        """La variable de clé est-elle présente et bien formée ? (nom seul, jamais la valeur)."""
        value = (self.env.get(KEY_ENV_NAME) or "").strip()
        return bool(value) and _is_hex_key(value)

    def library_available(self) -> bool:
        try:
            _import_account()
            return True
        except SignerDependencyError:
            return False

    def address(self) -> Optional[str]:
        """Adresse publique dérivée de la clé (mode réel). L'adresse n'est pas un secret."""
        if self._address:
            return self._address
        if self.dry_run:
            return None
        key = (self.env.get(KEY_ENV_NAME) or "").strip()
        if not _is_hex_key(key):
            raise SignerError(
                "{} absente ou mal formée (32 octets hex attendus) — aucune signature émise".format(KEY_ENV_NAME))
        account = _import_account().from_key(key)
        self._address = str(account.address).lower()
        return self._address

    # --- signature ------------------------------------------------------------

    def sign_transaction(self, tx: Dict[str, Any], *, intent_id: str = "") -> Dict[str, Any]:
        """Signe une transaction **déjà autorisée**.

        Retourne ``{"mode", "tx_hash", "simulated", "signed_transaction"(hex, jamais journalisé),
        "address"}``. En dry-run : hash factice, aucun accès réseau, aucune clé.
        """
        if not isinstance(tx, dict):
            raise SignerError("transaction attendue sous forme d'objet")
        for forbidden in ("privateKey", "private_key", "secret", "mnemonic"):
            if forbidden in tx:
                raise SignerError("champ interdit dans une transaction: {!r}".format(forbidden))
        if int(tx.get("chainId", self.chain_id)) != self.chain_id:
            raise SignerError("chainId de la transaction ≠ chaîne épinglée {}".format(self.chain_id))

        if self.dry_run:
            digest = fake_tx_hash({"tx": tx, "intent_id": intent_id})
            result = {
                "mode": "dry-run",
                "simulated": True,
                "tx_hash": digest,
                "signed_transaction": None,
                "address": None,
                "note": "signature simulée : aucune clé lue, aucun réseau, aucun message signé "
                        "(le hash est factice et ne doit jamais être assimilé à un hash de chaîne)",
            }
            if self.signature_log is not None:
                self.signature_log.append(intent_id=intent_id or "-", mode="dry-run",
                                          tx_hash=digest, note="simulated")
            return result

        account = _import_account()
        key = (self.env.get(KEY_ENV_NAME) or "").strip()
        if not _is_hex_key(key):
            raise SignerError(
                "{} absente ou mal formée — la signature réelle est refusée".format(KEY_ENV_NAME))
        local = account.from_key(key)
        if "from" in tx:
            # eth-account exige l'adresse EIP-55 exacte dans 'from' (les builders stdlib
            # normalisent les adresses en minuscules) : vérifier puis réécrire avec la casse de la clé.
            if str(tx["from"]).strip().lower() != str(local.address).lower():
                raise SignerError(
                    "champ 'from' incohérent avec l'adresse de la clé — signature refusée")
            tx = {**tx, "from": local.address}
        if tx.get("to"):
            # eth-account refuse aussi un 'to' non-checksummé : normaliser en EIP-55
            # (la casse ne change pas les octets signés) — incident mesuré le 2026-10-16.
            try:
                from eth_utils import to_checksum_address  # dépendance d'eth-account
                tx = {**tx, "to": to_checksum_address(str(tx["to"]).strip())}
            except Exception as exc:
                raise SignerError(
                    "champ 'to' non convertible en adresse EIP-55 — signature refusée") from exc
        signed = local.sign_transaction(tx)
        # ``signed.hash`` (eth-account) est le keccak de la transaction signée.
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
            "signed_transaction": raw_hex,   # en mémoire uniquement — jamais journalisé
            "address": str(local.address).lower(),
            "note": "transaction signée prête à être diffusée (une seule en vol à la fois)",
        }
        if self.signature_log is not None:
            self.signature_log.append(intent_id=intent_id or "-", mode="execute",
                                      tx_hash=result["tx_hash"], note="signed")
        return result

    def send_raw_transaction(self, raw_hex: str, *, timeout: int = common.RPC_TIMEOUT_SECONDS) -> str:
        """Diffuse une transaction signée (mode réel uniquement). Re-broadcast idempotent toléré."""
        if self.dry_run:
            raise SignerError("send_raw_transaction est interdit en dry-run")
        result = common.rpc(self.rpc_url, "eth_sendRawTransaction", [raw_hex], timeout)
        if not isinstance(result, str) or not result.startswith("0x"):
            raise SignerError("réponse inattendue à eth_sendRawTransaction")
        return result.lower()

    def safe_dict(self) -> Dict[str, Any]:
        return {
            "signer": "scripts/demo/signer.py (isolé)",
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
    print("ORVYREN — contrôle du service signataire (aucune clé affichée)")
    print("  bibliothèque eth-account : {}".format("présente" if info["library_available"] else "ABSENTE"))
    print("  variable {} : {}".format(KEY_ENV_NAME, "présente" if info["key_present"] else "absente/vide"))
    print("  RPC : {}".format(info["rpc_masked"]))
    print("  mode : {}".format(info["mode"]))
    if not info["library_available"]:
        print("  → signature réelle indisponible : python -m pip install eth-account")
    if not info["key_present"]:
        print("  → clé absente : renseigner {} dans .env (jamais versionné) ou l'environnement".format(KEY_ENV_NAME))
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="signer.py",
        description="ORVYREN — service signataire isolé (dry-run simulé / execute avec eth-account). "
                    "Jamais de clé journalisée.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=None,
                      help="signature simulée : aucune clé lue, aucun réseau (défaut)")
    mode.add_argument("--execute", action="store_true", help="signature réelle (exige eth-account + ORVYREN_PRIVATE_KEY)")
    parser.add_argument("--check", action="store_true", help="état du service : bibliothèque, présence de la clé (par nom)")
    parser.add_argument("--address", action="store_true", help="adresse publique dérivée de la clé (mode réel)")
    parser.add_argument("--tx-file", help="fichier JSON d'une transaction à signer (exemple : tx.example.json)")
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
            print("mode dry-run : aucune adresse dérivée (aucune clé lue)")
            return 0
        try:
            print(signer.address())
            return 0
        except SignerError as exc:
            print("ERREUR: {}".format(exc), file=sys.stderr)
            return EXIT_KEY

    if not args.tx_file:
        parser.print_help()
        return EXIT_USAGE

    try:
        with open(args.tx_file, "r", encoding="utf-8") as handle:
            tx = json.load(handle)
    except (OSError, ValueError) as exc:
        print("ERREUR: transaction illisible: {}".format(exc), file=sys.stderr)
        return EXIT_USAGE

    try:
        result = signer.sign_transaction(tx, intent_id=str(tx.get("intent_id") or ""))
    except SignerDependencyError as exc:
        print("ERREUR: {}".format(exc), file=sys.stderr)
        return EXIT_DEPENDENCY
    except SignerError as exc:
        print("ERREUR: {}".format(exc), file=sys.stderr)
        return EXIT_KEY

    print("mode : {}".format(result["mode"]))
    print("hash : {}".format(result["tx_hash"]))
    if result.get("simulated"):
        print("(hash FACTICE — signature simulée, aucune transaction n'existe sur une chaîne)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
