#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet (W5, L5.2) : **génération de la clé jetable**.

Génère un EOA jetable **localement** (``eth-account``, même exception isolée
que ``signer.py`` — B5 §a.1) et l'écrit dans le fichier d'env de session :

* ``ORVYREN_PRIVATE_KEY`` — la clé (jamais affichée, jamais transmise) ;
* ``ORVYREN_AGENT_ADDRESS`` — l'adresse dérivée (publique), à financer via les
  robinets gratuits.

Garde-fous : refuse d'écraser une clé existante sans ``--force`` ; fichier
sortant en ``chmod 600`` quand la plateforme le permet ; la clé n'apparaît
**jamais** dans stdout/stderr ni dans un message d'erreur.

CLI :

    python scripts/demo/generate_signer_key.py            # écrit dans scripts/demo/.env
    python scripts/demo/generate_signer_key.py --check    # vérifie/rappelle l'adresse dérivée
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

try:  # paquet (``demo.generate_signer_key``)
    from . import common
except ImportError:  # exécution directe : python scripts/demo/generate_signer_key.py
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
        print("generate_signer_key: eth-account requis — installer « pip install "
              "eth-account==0.14.0 » (seule dépendance externe du kit, isolée au "
              "signataire).", file=sys.stderr)
        raise SystemExit(EXIT_DEPENDENCY)
    return Account


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().split("\n")


def _write_lines(path: str, lines: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    try:  # chmod 600 quand la plateforme le permet (POSIX)
        os.chmod(path, 0o600)
    except OSError:
        pass


def _assign(lines: List[str], pattern: "re.Pattern[str]", value: str) -> List[str]:
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
        result.append("%s%s" % (pattern.pattern.split("\\")[0].rstrip("= "), value))
    return result


def check_existing(env_path: str) -> Dict[str, Any]:
    """Vérifie localement : adresse dérivée ↔ ligne AGENT_ADDRESS du fichier."""
    Account = _require_eth_account()
    values = common.read_env_file(env_path)
    out: Dict[str, Any] = {"env_file": common.display_path(env_path),
                           "file_exists": os.path.isfile(env_path)}
    key = values.get("ORVYREN_PRIVATE_KEY", "").strip()
    if not key:
        out["key_present"] = False
        out["detail"] = "aucune clé dans le fichier — rien à vérifier"
        return out
    out["key_present"] = True
    try:
        address = Account.from_key(key).address
    except Exception:
        out["derived_address_ok"] = False
        out["detail"] = "clé présente mais illisible (valeur jamais affichée)"
        return out
    declared = values.get("ORVYREN_AGENT_ADDRESS", "").strip()
    out["derived_address"] = address
    out["declared_address"] = declared
    out["match"] = bool(declared) and declared.lower() == address.lower()
    out["detail"] = ("adresse dérivée == ORVYREN_AGENT_ADDRESS" if out["match"]
                     else "écart : mettre à jour ORVYREN_AGENT_ADDRESS avec l'adresse dérivée")
    return out


def generate(env_path: str, *, force: bool) -> Dict[str, Any]:
    Account = _require_eth_account()
    if os.path.isfile(env_path):
        existing = common.read_env_file(env_path).get("ORVYREN_PRIVATE_KEY", "").strip()
        if existing and not force:
            print("generate_signer_key: une clé est déjà présente dans %s — refus "
                  "d'écraser sans --force (une clé écrasée = une adresse abandonnée)."
                  % common.display_path(env_path), file=sys.stderr)
            raise SystemExit(EXIT_REFUSED)
        lines = _read_lines(env_path)
    else:
        if os.path.isfile(TEMPLATE_ENV):
            lines = _read_lines(TEMPLATE_ENV)
        else:
            lines = ["# ORVYREN — env de session (généré)"]
    account = Account.create()
    private_key = account.key.hex()
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key
    address = account.address
    lines = _assign(lines, KEY_LINE, private_key)
    lines = _assign(lines, ADDRESS_LINE, address)
    _write_lines(env_path, lines)
    return {"env_file": common.display_path(env_path), "agent_address": address,
            "wrote_key": True, "note": "clé jetable — la détruire après la démo "
                                       "(effacer la ligne du fichier)"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_signer_key.py",
        description="ORVYREN (W5/L5.2) — génère la clé jetable de l'agent EOA et "
                    "l'écrit dans l'env de session (jamais affichée). Testnet "
                    "uniquement.")
    parser.add_argument("--env-file", default=DEFAULT_ENV)
    parser.add_argument("--force", action="store_true",
                        help="écraser une clé existante (déconseillé)")
    parser.add_argument("--check", action="store_true",
                        help="vérifier l'adresse dérivée sans rien écrire")
    args = parser.parse_args(argv)

    if args.check:
        report = check_existing(args.env_file)
        for key, value in report.items():
            print("  %-18s %s" % (key, value))
        return EXIT_OK if report.get("match") or not report.get("key_present") else 1
    report = generate(args.env_file, force=args.force)
    print("generate_signer_key: clé jetable écrite dans %s (jamais affichée)" % report["env_file"])
    print("  agent_address  : %s" % report["agent_address"])
    print("  prochaines étapes : financer l'adresse via les robinets gratuits, puis")
    print("  relancer « python scripts/demo/faucet_check.py --rpc ».")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
