#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — **masked** inspector for local environment files.

**Never** prints a secret value: only names, presence and a length. Used to
check that a local ``.env`` file is properly git-ignored and that the expected
keys (on-chain demo, LLM) are present — without ever exposing them in a
terminal, a log or a conversation.

Usage::

    python scripts/inspect_env_masked.py                      # default files
    python scripts/inspect_env_masked.py --require-live-keys  # exit 1 if an LLM key is missing

Default files: ``scripts/demo/.env`` and ``scripts/demo/owners.env``
(both git-ignored — the command verifies it).
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

#: Keys expected for the agents' live mode (FREEZE_V2 A2).
LIVE_KEY_NAMES = ("ORVYREN_DEEPSEEK_API_KEY", "ORVYREN_MIMO_API_KEY")
#: Name fragments that must never be displayed (not even partially).
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
        description="ORVYREN — masked view of local env files (never values).")
    parser.add_argument("--env-file", action="append", default=None)
    parser.add_argument("--require-live-keys", action="store_true",
                        help="exit with code 1 if an expected LLM key is missing")
    args = parser.parse_args(argv)

    files = args.env_file or list(DEFAULT_FILES)
    seen: "dict[str, int]" = {}
    for path in files:
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        if not os.path.isfile(path):
            print("[missing] %s" % rel)
            continue
        ignored = _git_ignored(path)
        state = {True: "git-ignored ✓", False: "!! TRACKED BY GIT — DANGER", None: "git ?"}[ignored]
        print("[file]    %s  (%s)" % (rel, state))
        for key, length in _read_keys(path):
            seen.setdefault(key, length)
            secret = any(hint in key.upper() for hint in SECRET_HINTS)
            shown = "present (len %d)" % length if length else "empty"
            if secret and length:
                shown += " — never displayed"
            print("    %-34s %s" % (key, shown))
        print()

    print("live-mode keys (agents):")
    missing = []
    for name in LIVE_KEY_NAMES:
        length = seen.get(name)
        if length:
            print("    %-34s present (len %d)" % (name, length))
        else:
            missing.append(name)
            print("    %-34s MISSING" % name)
    if args.require_live_keys and missing:
        print("E_LIVE_KEYS_MISSING: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
