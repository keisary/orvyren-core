#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the shareable review package (ZIP + sha256 manifests).

Creates dist/orvyren_core_review_<YYYY-MM-DD>.zip containing the whole working
tree (including .git, so reviewers keep history), plus inside the archive:
  - MANIFEST.sha256        : sha256 of every working file (verifiable with
                             `sha256sum -c MANIFEST.sha256`)
  - PACKAGE_INFO.txt       : what this snapshot is, when it was built,
                             what it excludes, and the archive's own hash.

Excluded from the archive: __pycache__, *.pyc, *.pyo, dist/, .venv, OS noise,
*.zip and *.log (so the nested audit-packet archives under evidence/ do not
travel inside this one), and a deny-list of secret-bearing names (.env,
*.env except *.example.env, config.env, owners.env, id_*, *.pem, *.key,
secrets/) -- a `.gitignore` does not constrain a zip built by walking a working
tree (Astra review F08). The finished zip is re-scanned and a forbidden name
inside aborts the build. The archive itself is written to dist/ and its sha256
is printed.
"""

import datetime as dt
import hashlib
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, "dist")
SKIP_DIRS = {"__pycache__", "dist", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
SKIP_SUFFIXES = (".pyc", ".pyo", ".zip", ".log")

#: Deny-list for shared packages: this artefact gets zipped and passed around,
#: and .gitignore does not constrain a zip built from the working tree (F08).
FORBIDDEN_BASENAMES = {
    ".env",
    # secret-bearing names created by scripts/demo/ (signer + RPC credentials):
    "config.env", "owners.env",
    "id_ed25519", "id_ed25519.pub", "id_rsa", "id_rsa.pub", "id_ecdsa",
    "google_client_secret.json", "google_token.json",
}
FORBIDDEN_PREFIXES = (".env.",)              # .env.local, .env.bak... (.env.example stays allowed)
FORBIDDEN_SUFFIXES = (".pem", ".key", ".keystore")
FORBIDDEN_DIRS = {"secrets", ".secrets"}


def is_forbidden(rel):
    """True when the relative path names a file that must not be packaged."""
    parts = rel.replace("\\", "/").split("/")
    if any(part in FORBIDDEN_DIRS for part in parts[:-1]):
        return True
    name = parts[-1]
    if name in FORBIDDEN_BASENAMES:
        return True
    if name.startswith(FORBIDDEN_PREFIXES) and name != ".env.example":
        return True
    # Any *.env is secret-bearing unless it is an explicit example file
    # (.env.example, config.example.env...).
    if name.endswith(".env") and "example" not in name:
        return True
    return name.endswith(FORBIDDEN_SUFFIXES)


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
            rel = os.path.relpath(full, HERE).replace("\\", "/")
            if is_forbidden(rel):
                continue
            out.append(rel)
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
    working = [f for f in files if not f.startswith(".git/")]
    info = [
        "ORVYREN-Core — review package",
        f"built_at_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
        "competition: 2026 Shenzhen International FinTech Competition, International Track, Topic F",
        "deadline_utc: 2026-10-20T15:59:00Z",
        "start_here: docs/REVIEW_KIT.md",
        "run_tests: python -m unittest discover -s tests",
        "run_pipeline: python run_pipeline.py",
        f"files: {len(working)} working files, hashed in MANIFEST.sha256 "
        f"(+ .git history: {len(files) - len(working)} git files)",
        "verify: sha256sum -c MANIFEST.sha256",
        "excludes: __pycache__, *.pyc, *.pyo, *.zip, *.log, dist/, caches, and a secret deny-list "
        "(.env, *.env except *.example.env, id_*, *.pem, *.key, secrets/). Corpus and evidence text "
        "artefacts are included on purpose (they are proofs); the audit-packet .zip archives stay out "
        "(delivered separately, see evidence/audit_packets/README.md).",
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            zf.write(os.path.join(HERE, rel), rel)
        zf.writestr("MANIFEST.sha256", "\n".join(manifest) + "\n")
        zf.writestr("PACKAGE_INFO.txt", "\n".join(info) + "\n")

    # Defense in depth: re-scan the finished archive; a forbidden name inside
    # it means the exclusion logic above missed a path -- abort, do not ship.
    with zipfile.ZipFile(zip_path) as zf:
        forbidden = [name for name in zf.namelist() if is_forbidden(name)]
    if forbidden:
        os.remove(zip_path)
        raise SystemExit(
            "refusing to ship: forbidden file(s) inside the package: "
            + ", ".join(sorted(forbidden)))

    print(f"package : {zip_path}")
    print(f"size    : {os.path.getsize(zip_path) / 1e6:.2f} MB")
    print(f"files   : {len(working)} working (+ .git history, + MANIFEST.sha256, + PACKAGE_INFO.txt)")
    print(f"sha256  : {sha256_file(zip_path)}")


if __name__ == "__main__":
    main()
