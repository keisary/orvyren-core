#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — L1.5 : manifeste ``replay/corpus_v1.manifest.json`` (contrat B7 §d.3).

Liste **fichier par fichier** ce que le rejeu (W7) peut consommer : chemins
relatifs, ``sha256``, taille — plus les fenêtres déclarées (principales,
contrôle, CALME, séries). Le manifeste est **reconstructible** : ``--check``
recalcule et compare à l'octet (CI/test).

Ce qui n'est PAS inclus est déclaré en toutes lettres (``missing_declared``) —
jamais inventé.

Usage ::

    python scripts/build_corpus_v1_manifest.py           # (ré)écrit le manifeste
    python scripts/build_corpus_v1_manifest.py --check   # vérifie (rc 0/1)
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
            if os.path.sep + "tmp" + os.path.sep in path:
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
                        help="vérifie le manifeste sur disque (rc 0 = identique)")
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
            print("E_MANIFEST_STALE: divergence (relancer sans --check)")
            return 1
        print("PASS — manifeste à jour (%d fichiers)" % manifest["totals"]["files"])
        return 0
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("ORVYREN — corpus v1 manifest écrit : replay/corpus_v1.manifest.json")
    print("  fichiers : %d (%d octets)" % (manifest["totals"]["files"],
                                            manifest["totals"]["bytes"]))
    print("  sha256   : %s" % manifest["manifest_sha256"][:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
