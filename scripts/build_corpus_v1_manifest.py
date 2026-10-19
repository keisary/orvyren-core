#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — L1.5: ``replay/corpus_v1.manifest.json`` manifest (contract B7 §d.3).

Lists **file by file** what the replay (W7) may consume: relative paths,
``sha256``, byte size — plus the declared windows (main, control, CALM,
series). The manifest is **rebuildable**: ``--check`` recomputes it and compares
byte for byte (CI/test).

What is NOT included is declared in so many words (``missing_declared``) —
never invented.

Usage::

    python scripts/build_corpus_v1_manifest.py           # (re)write the manifest
    python scripts/build_corpus_v1_manifest.py --check   # verify (rc 0/1)
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES_GLOBS = (
    "corpus/usdc_observations.csv",
    "corpus/raw/**/*.json",
    "corpus/raw/**/*.csv",
    "corpus/series/*.json",
)

# Content of the manifest (frozen artefact): keep the declared strings as they
# are published — they are data, not console text.
MISSING_DECLARED = (
    {"piece": "série xUSD (nov 2025)", "reason": "qualitatif seulement (B7 §8) — non intégré"},
    {"piece": "séries stETH/rsETH horaires", "reason": "vivent dans evidence/épisodes (W3) — à intégrer côté W7 si requis"},
)
MULTI_DECLARED = ("corpus/series/usd0pp_2025-01.json",
                  "série USD0++ (jan 2025), 635 points horaires — importée de la sonde W3-C (archive)")


def _sha256(path: str) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _windows_summary() -> dict:
    windows: dict = {}
    main_manifest = os.path.join(REPO_ROOT, "corpus", "manifest.json")
    if os.path.exists(main_manifest):
        with open(main_manifest, encoding="utf-8") as handle:
            windows["corpus"] = json.load(handle).get("windows", {})
    calm = os.path.join(REPO_ROOT, "corpus", "calm_manifest.json")
    if os.path.exists(calm):
        with open(calm, encoding="utf-8") as handle:
            windows["calm"] = json.load(handle).get("windows", {})
    usd0pp = os.path.join(REPO_ROOT, "corpus", "series", "usd0pp_2025-01.json")
    if os.path.exists(usd0pp):
        with open(usd0pp, encoding="utf-8") as handle:
            series = json.load(handle)
        windows["usd0pp_2025-01"] = series.get("window", [])
    return windows


def build_manifest() -> dict:
    files = []
    for pattern in FILES_GLOBS:
        for path in sorted(glob.glob(os.path.join(REPO_ROOT, pattern), recursive=True)):
            # Stay inside the repository (escape guard). The former "skip any
            # path containing /tmp" rule silently emptied the manifest when
            # the repo itself lived under /tmp — exactly CI's pristine
            # clean-clone job, which materialises HEAD in /tmp/clone.
            full = os.path.abspath(path)
            if os.path.commonpath([full, os.path.abspath(REPO_ROOT)]) != os.path.abspath(REPO_ROOT):
                continue
            rel = os.path.relpath(path, REPO_ROOT).replace("\\", "/")
            files.append({"path": rel, "sha256": _sha256(path),
                          "bytes": os.path.getsize(path)})
    manifest = {
        "schema": "orvyren/corpus-v1-manifest/v1",
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "contract": "B7 §d.3 — corpus figé du rejeu (W7)",
        "files": files,
        "totals": {"files": len(files), "bytes": sum(f["bytes"] for f in files)},
        "windows": _windows_summary(),
        "missing_declared": [dict(item) for item in MISSING_DECLARED],
        "multiple_series": {"path": MULTI_DECLARED[0], "note": MULTI_DECLARED[1]},
    }
    # built_at is a stamp, not content: exclude it so the digest (and --check)
    # are stable across rebuilds.
    frozen = {key: value for key, value in manifest.items()
              if key not in ("manifest_sha256", "built_at")}
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(frozen, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()
    return manifest


def _serialize(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="build_corpus_v1_manifest.py")
    parser.add_argument("--check", action="store_true",
                        help="verify the manifest on disk (rc 0 = identical)")
    args = parser.parse_args(argv)
    target = os.path.join(REPO_ROOT, "replay", "corpus_v1.manifest.json")
    manifest = build_manifest()
    text = _serialize(manifest)
    if args.check:
        if not os.path.exists(target):
            print("E_MANIFEST_ABSENT: %s" % target)
            return 1
        with open(target, "r", encoding="utf-8", newline="") as handle:
            on_disk = handle.read().replace("\r\n", "\n")
        # built_at varies: compare everything EXCEPT the build stamp
        def _strip(payload: str) -> str:
            data = json.loads(payload)
            data.pop("built_at", None)
            return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
        if _strip(on_disk) != _strip(text):
            print("E_MANIFEST_STALE: divergence (rerun without --check)")
            return 1
        print("PASS — manifest up to date (%d files)" % manifest["totals"]["files"])
        return 0
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("ORVYREN — corpus v1 manifest written: replay/corpus_v1.manifest.json")
    print("  files    : %d (%d bytes)" % (manifest["totals"]["files"],
                                         manifest["totals"]["bytes"]))
    print("  sha256   : %s" % manifest["manifest_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
