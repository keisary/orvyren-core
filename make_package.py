#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the shareable review package (ZIP + sha256 manifests).

Creates dist/orvyren_core_review_<YYYY-MM-DD>.zip containing the whole working
tree (including .git, so reviewers keep history), plus inside the archive:
  - MANIFEST.sha256        : sha256 of every working file (verifiable with
                             `sha256sum -c MANIFEST.sha256`)
  - PACKAGE_INFO.txt       : what this snapshot is, when it was built,
                             what it excludes, and the archive's own hash.

Excluded from the archive: __pycache__, *.pyc, dist/, .venv, OS noise.
The archive itself is written to dist/ and its sha256 is printed.
"""

import datetime as dt
import hashlib
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
SKIP_DIRS = {"__pycache__", "dist", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".zip", ".log")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def working_files():
    """Every file to include, relative to the repo root (sorted)."""
    out = []
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(SKIP_SUFFIXES):
                continue
            full = os.path.join(root, name)
            out.append(os.path.relpath(full, HERE).replace("\\", "/"))
    return sorted(out)


def manifest_entries(files):
    """Manifest covers working files only (.git internals excluded on purpose)."""
    lines = []
    for rel in files:
        if rel.startswith(".git/") or rel == "MANIFEST.sha256":
            continue
        lines.append(f"{sha256_file(os.path.join(HERE, rel))}  {rel}")
    return lines


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(DIST, exist_ok=True)
    zip_path = os.path.join(DIST, f"orvyren_core_review_{stamp}.zip")

    files = working_files()
    manifest = manifest_entries(files)
    info = [
        "ORVYREN-Core — review package",
        f"built_at_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        "competition: 2026 Shenzhen International FinTech Competition, International Track, Topic F",
        "deadline_utc: 2026-10-20T15:59:00Z",
        "start_here: docs/REVIEW_KIT.md",
        "run_tests: python -m unittest discover -s tests",
        "run_pipeline: python run_pipeline.py",
        f"files: {len(files)} working files (+ .git history)",
        "verify: sha256sum -c MANIFEST.sha256",
        "excludes: __pycache__, *.pyc, dist/, caches. Corpus AND evidence are included on purpose (they are proofs).",
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(os.path.join(HERE, rel), rel)
        zf.writestr("MANIFEST.sha256", "\n".join(manifest) + "\n")
        zf.writestr("PACKAGE_INFO.txt", "\n".join(info) + "\n")

    print(f"package : {zip_path}")
    print(f"size    : {os.path.getsize(zip_path) / 1e6:.2f} MB")
    print(f"files   : {len(files)} (+ MANIFEST.sha256, + PACKAGE_INFO.txt)")
    print(f"sha256  : {sha256_file(zip_path)}")


if __name__ == "__main__":
    main()
