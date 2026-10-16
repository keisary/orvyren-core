#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — kit de démo testnet (W5, L5.2) : **hygiène des secrets** (offline).

Contrôles (aucun réseau) :

* **H1** — aucun ``.env`` / ``owners.env`` n'est **versionné** (exceptions
  ``*.example.*`` autorisées) ;
* **H2** — la **valeur** de chaque clé privée présente en local n'apparaît dans
  **aucun fichier suivi** du dépôt (recherche en mémoire, la clé n'est jamais
  passée en argument ni imprimée) ;
* **H3** — chaque fichier d'env local est bien couvert par ``.gitignore``
  (``git check-ignore``) ;
* **H4** — permissions POSIX : lecture/écriture propriétaire seulement
  (``chmod 600`` ; SKIPPED sous Windows) ;
* **H5** — noms des secrets présents dans l'environnement du processus
  (information : l'attendu est « aucun » hors processus de signature).

CLI :

    python scripts/demo/check_env_hygiene.py [--out report.json]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

try:  # paquet (``demo.check_env_hygiene``)
    from . import common
except ImportError:  # exécution directe : python scripts/demo/check_env_hygiene.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import common  # type: ignore  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ENV_FILES = (os.path.join(HERE, ".env"), os.path.join(HERE, "owners.env"))

SECRET_KEYS = ("ORVYREN_PRIVATE_KEY", "ORVYREN_OWNER1_PRIVATE_KEY",
               "ORVYREN_OWNER2_PRIVATE_KEY", "ORVYREN_OWNER3_PRIVATE_KEY",
               "ORVYREN_SIGNER_KEY", "ORVYREN_MNEMONIC", "ORVYREN_SEED")
MAX_SCAN_BYTES = 8 * 1024 * 1024

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_NO_GIT = 3


def _git(root: str, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(["git", "-C", root, *args], capture_output=True,
                                text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode not in (0, 1, 128):
        return None
    return result.stdout


def run(*, env_files: List[str], repo_root: str) -> Dict[str, Any]:
    report: Dict[str, Any] = {"repo_root": repo_root, "env_files": [], "checks": [],
                              "verdict": "OK"}
    tracked_raw = _git(repo_root, "ls-files")
    git_available = tracked_raw is not None
    if not git_available:
        tracked: List[str] = []
    else:
        tracked = [line.strip() for line in tracked_raw.splitlines() if line.strip()]

    # H1 — aucun .env versionné (exceptions *example*)
    if not git_available:
        report["checks"].append({"id": "H1.tracked_env", "status": "SKIPPED",
                                 "detail": "git indisponible — contrôles H1/H2/H3 sautés"})
    else:
        tracked_env = [rel for rel in tracked
                       if (os.path.basename(rel) == ".env" or os.path.basename(rel) == "owners.env")
                       and ".example" not in os.path.basename(rel)]
        report["checks"].append({
            "id": "H1.tracked_env", "status": "PASS" if not tracked_env else "FAIL",
            "detail": "aucun .env versionné" if not tracked_env
                      else "FICHIERS SENSIBLES VERSIONNÉS : %s" % ", ".join(tracked_env)})

    # H2 — valeurs des clés locales absentes des fichiers suivis
    secrets: List[bytes] = []
    for path in env_files:
        values = common.read_env_file(path)
        report["env_files"].append({"path": common.display_path(path) if os.path.isfile(path)
                                    else path, "present": os.path.isfile(path)})
        for key in SECRET_KEYS:
            value = values.get(key, "").strip()
            if len(value) >= 16:  # jetons courts ignorés (placeholders)
                body = value[2:] if value.startswith("0x") else value
                secrets.append(value.encode("ascii", "ignore"))
                if body != value:
                    secrets.append(body.encode("ascii", "ignore"))
    if not git_available:
        pass
    elif not secrets:
        report["checks"].append({"id": "H2.secret_values", "status": "PASS",
                                 "detail": "aucune clé locale présente — rien à confronter"})
    else:
        hits: List[str] = []
        for rel in tracked:
            full = os.path.join(repo_root, rel)
            try:
                if os.path.getsize(full) > MAX_SCAN_BYTES:
                    continue
                with open(full, "rb") as handle:
                    blob = handle.read()
            except OSError:
                continue
            if b"\x00" in blob:
                continue
            if any(needle in blob for needle in secrets):
                hits.append(rel)
        report["checks"].append({
            "id": "H2.secret_values", "status": "PASS" if not hits else "FAIL",
            "detail": "aucune valeur de clé dans %d fichiers suivis" % len(tracked)
                      if not hits else "VALEUR DE CLÉ TROUVÉE DANS : %s" % ", ".join(hits)})

    # H3 — fichiers d'env locaux couverts par .gitignore
    present_envs = [path for path in env_files if os.path.isfile(path)]
    if not git_available:
        pass
    elif not present_envs:
        report["checks"].append({"id": "H3.gitignore", "status": "PASS",
                                 "detail": "aucun fichier d'env local présent"})
    else:
        not_ignored: List[str] = []
        for path in present_envs:
            result = subprocess.run(["git", "-C", repo_root, "check-ignore", "-q", path],
                                    capture_output=True, text=True)
            if result.returncode != 0:
                not_ignored.append(common.display_path(path))
        report["checks"].append({
            "id": "H3.gitignore", "status": "PASS" if not not_ignored else "FAIL",
            "detail": "tous les fichiers d'env locaux sont ignorés" if not not_ignored
                      else "NON IGNORÉS : %s" % ", ".join(not_ignored)})

    # H4 — permissions (POSIX uniquement)
    if os.name == "posix":
        bad_perms: List[str] = []
        for path in present_envs:
            mode = os.stat(path).st_mode & 0o777
            if mode & 0o077:
                bad_perms.append("%s (%o)" % (common.display_path(path), mode))
        report["checks"].append({
            "id": "H4.perms", "status": "PASS" if not bad_perms else "FAIL",
            "detail": "600 partout" if not bad_perms else "PERMISSIONS LARGES : %s"
                      % ", ".join(bad_perms)})
    else:
        report["checks"].append({"id": "H4.perms", "status": "SKIPPED",
                                 "detail": "Windows — permissions POSIX sans objet"})

    # H5 — noms des secrets présents dans l'environnement (information)
    env = common.load_session_env()
    try:
        present = sorted(common.present_secret_env_names(env))
    except Exception:
        present = [key for key in SECRET_KEYS if env.get(key)]
    report["checks"].append({"id": "H5.process_env", "status": "PASS",
                             "detail": {"secret_env_names_present": present,
                                        "expectation": "aucun hors processus de signature"}})

    report["verdict"] = "FAIL" if any(check["status"] == "FAIL" for check in report["checks"]) \
        else ("NO_GIT" if not git_available else "OK")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_env_hygiene.py",
        description="ORVYREN (W5/L5.2) — hygiène des secrets : rien de versionné, "
                    "aucune valeur de clé dans les fichiers suivis, .gitignore et "
                    "permissions. Offline.")
    parser.add_argument("--env-file", action="append", default=None)
    parser.add_argument("--repo-root", default=REPO_ROOT)
    parser.add_argument("--out", default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    report = run(env_files=args.env_file or list(DEFAULT_ENV_FILES), repo_root=args.repo_root)
    if args.out:
        common.write_json(args.out, report)
    if not args.quiet:
        for check in report["checks"]:
            print("  [%s] %s — %s" % (check["status"], check["id"], str(check["detail"])[:200]))
        print("VERDICT: %s" % report["verdict"])
    if report["verdict"] == "NO_GIT":
        return EXIT_NO_GIT
    return EXIT_OK if report["verdict"] == "OK" else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
