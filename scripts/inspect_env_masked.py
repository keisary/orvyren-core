#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — inspecteur **masqué** des fichiers d'environnement locaux.

N'affiche **jamais** une valeur secrète : uniquement des noms, une présence et
une longueur. Sert à vérifier qu'un fichier ``.env`` local est bien ignoré par
git et que les clés attendues (démo on-chain, LLM) sont présentes — sans jamais
les exposer dans un terminal, un log ou une conversation.

Usage ::

    python scripts/inspect_env_masked.py                      # fichiers par défaut
    python scripts/inspect_env_masked.py --require-live-keys  # exit 1 si clé LLM absente

Fichiers par défaut : ``scripts/demo/.env`` et ``scripts/demo/owners.env``
(tous deux git-ignorés — la commande le vérifie).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DEFAULT_FILES = (os.path.join(REPO_ROOT, "scripts", "demo", ".env"),
                 os.path.join(REPO_ROOT, "scripts", "demo", "owners.env"))

#: Clés attendues pour le mode live des agents (FREEZE_V2 A2).
LIVE_KEY_NAMES = ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
#: Fragments de noms jamais affichables (même partiellement).
SECRET_HINTS = ("PRIVATE_KEY", "_API_KEY", "MNEMONIC", "SEED", "SIGNER")


def _read_keys(path: str) -> "list[tuple[str, int]]":
    entries: "list[tuple[str, int]]" = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            entries.append((key.strip(), len(value)))
    return entries


def _git_ignored(path: str) -> "bool | None":
    try:
        result = subprocess.run(["git", "-C", REPO_ROOT, "check-ignore", "-q", path],
                                capture_output=True)
    except OSError:
        return None
    return result.returncode == 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="inspect_env_masked.py",
        description="ORVYREN — vue masquée des fichiers d'env locaux (jamais de valeurs).")
    parser.add_argument("--env-file", action="append", default=None)
    parser.add_argument("--require-live-keys", action="store_true",
                        help="sortir en code 1 si une clé LLM attendue est absente")
    args = parser.parse_args(argv)

    files = args.env_file or list(DEFAULT_FILES)
    seen: "dict[str, int]" = {}
    for path in files:
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        if not os.path.isfile(path):
            print("[absent]  %s" % rel)
            continue
        ignored = _git_ignored(path)
        state = {True: "git-ignoré ✓", False: "!! SUIVI PAR GIT — DANGER", None: "git ?"}[ignored]
        print("[fichier] %s  (%s)" % (rel, state))
        for key, length in _read_keys(path):
            seen.setdefault(key, length)
            secret = any(hint in key.upper() for hint in SECRET_HINTS)
            shown = "présente (len %d)" % length if length else "vide"
            if secret and length:
                shown += " — jamais affichée"
            print("    %-34s %s" % (key, shown))
        print()

    print("clés du mode live (agents) :")
    missing = []
    for name in LIVE_KEY_NAMES:
        length = seen.get(name)
        if length:
            print("    %-34s présente (len %d)" % (name, length))
        else:
            missing.append(name)
            print("    %-34s ABSENTE" % name)
    if args.require_live_keys and missing:
        print("E_LIVE_KEYS_MISSING: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
