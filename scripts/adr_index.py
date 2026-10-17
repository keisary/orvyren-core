#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — registre ADR (`docs/decisions/`) : index + contrôle (W8, L8.5).

Vérifie que le registre est **numéroté sans trou ni doublon** et que le tableau
du `README.md` reflète exactement les fichiers `ADR-*.md` (numéro, lien, statut,
date). `--write` régénère le tableau ; `--check` (défaut) échoue en cas d'écart —
c'est le contrôle branché en CI.

Format attendu dans chaque `ADR-NNNN-*.md` :

    # ADR-0001 — Titre ...
    **Date :** 2026-10-16 · **Statut : ACCEPTÉE · **Portée :** ...

Usage ::

    python scripts/adr_index.py --check       # CI : 0 = conforme
    python scripts/adr_index.py --write       # régénère le tableau du README
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DEFAULT_DIR = os.path.join(REPO_ROOT, "docs", "decisions")

_TITLE_RE = re.compile(r"^#\s+ADR-(\d{4})\s+—\s+(.+?)\s*$", re.MULTILINE)
_DATE_RE = re.compile(r"\*\*Date\s*:\*\*\s*(\d{4}-\d{2}-\d{2})")
_STATUS_RE = re.compile(r"\*\*Statut\s*:\s*(.+?)(?:·|\n|$)")
_README_ROW_RE = re.compile(
    r"^\|\s*(\d{4})\s*\|\s*\[(.*?)\]\((ADR-[^)]+\.md)\)\s*\|\s*([^|]+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$",
    re.MULTILINE)

REGISTRE_HEADER = "## Registre"


def scan(decisions_dir):
    """Return the ADR entries, sorted by number. Never raises on odd files."""
    entries = []
    for name in sorted(os.listdir(decisions_dir)):
        if not (name.startswith("ADR-") and name.endswith(".md")):
            continue
        path = os.path.join(decisions_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                head = handle.read(4000)
        except OSError:
            continue
        title_match = _TITLE_RE.search(head)
        date_match = _DATE_RE.search(head)
        status_match = _STATUS_RE.search(head)
        number = int(title_match.group(1)) if title_match else int(name[4:8])
        title = title_match.group(2) if title_match else name
        status_raw = status_match.group(1).strip() if status_match else "(statut manquant)"
        status_raw = re.sub(r"\*+", "", status_raw).strip()
        entries.append({
            "number": number,
            "file": name,
            "title": title,
            "status_core": status_raw.split("—")[0].strip(),
            "status_raw": status_raw,
            "date": date_match.group(1) if date_match else "(date manquante)",
        })
    entries.sort(key=lambda entry: (entry["number"], entry["file"]))
    return entries


def check(entries, decisions_dir):
    """Return a list of human-readable problems ([] = registre conforme)."""
    problems = []
    numbers = [entry["number"] for entry in entries]
    for missing in range(1, (max(numbers) if numbers else 0) + 1):
        if missing not in numbers:
            problems.append("numéro manquant : ADR-%04d" % missing)
    seen = set()
    for number in numbers:
        if number in seen:
            problems.append("numéro dupliqué : ADR-%04d" % number)
        seen.add(number)
    for entry in entries:
        if "statut manquant" in entry["status_core"]:
            problems.append("statut manquant dans %s" % entry["file"])
        if "date manquante" in entry["date"]:
            problems.append("date manquante dans %s" % entry["file"])

    readme_path = os.path.join(decisions_dir, "README.md")
    try:
        with open(readme_path, "r", encoding="utf-8") as handle:
            readme = handle.read()
    except OSError:
        return problems + ["README.md illisible dans %s" % decisions_dir]
    rows = {int(row[0]): row for row in _README_ROW_RE.findall(readme)}
    for entry in entries:
        row = rows.get(entry["number"])
        if row is None:
            problems.append("README.md : ligne absente pour ADR-%04d" % entry["number"])
            continue
        _num, _label, link, status_cell, date_cell = row
        if link != entry["file"]:
            problems.append("README.md : lien erroné pour ADR-%04d (%s ≠ %s)"
                            % (entry["number"], link, entry["file"]))
        if status_cell.strip() != entry["status_core"]:
            problems.append("README.md : statut divergent pour ADR-%04d (%r ≠ %r)"
                            % (entry["number"], status_cell.strip(), entry["status_core"]))
        if date_cell != entry["date"]:
            problems.append("README.md : date divergente pour ADR-%04d" % entry["number"])
    for number in rows:
        if number not in numbers:
            problems.append("README.md : ligne orpheline pour ADR-%04d" % number)
    return problems


def render_registry(entries):
    """The markdown table for the registry section of ``README.md``."""
    lines = ["| # | ADR | Statut | Date |", "|---|---|---|---|"]
    for entry in entries:
        label = entry["title"]
        for prefix in ("ADR-%04d — " % entry["number"],):
            if label.startswith(prefix):
                label = label[len(prefix):]
        lines.append("| %04d | [%s](%s) | %s | %s |" % (
            entry["number"], label, entry["file"], entry["status_core"], entry["date"]))
    return "\n".join(lines) + "\n"


def rewrite_readme(decisions_dir, entries):
    readme_path = os.path.join(decisions_dir, "README.md")
    with open(readme_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if REGISTRE_HEADER not in text:
        raise SystemExit("E_ADR_README: section '%s' introuvable dans %s" % (REGISTRE_HEADER, readme_path))
    head = text.split(REGISTRE_HEADER)[0] + REGISTRE_HEADER + "\n\n"
    with open(readme_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(head + render_registry(entries))
    return readme_path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adr_index.py",
                                     description="Registre ADR : contrôle d'index (défaut) ou régénération.")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="répertoire des ADR (défaut : docs/decisions)")
    parser.add_argument("--check", action="store_true", help="contrôle seulement (défaut)")
    parser.add_argument("--write", action="store_true", help="régénère le tableau du README.md")
    args = parser.parse_args(argv)

    decisions_dir = os.path.abspath(args.dir)
    if not os.path.isdir(decisions_dir):
        print("E_ADR_DIR: introuvable : %s" % decisions_dir, file=sys.stderr)
        return 1
    entries = scan(decisions_dir)
    if args.write:
        path = rewrite_readme(decisions_dir, entries)
        print("ADR registry written: %s (%d entrées)" % (path, len(entries)))
        return 0
    problems = check(entries, decisions_dir)
    if problems:
        for problem in problems:
            print("ADR INDEX: %s" % problem, file=sys.stderr)
        return 1
    print("ADR INDEX OK — %d entrées, numérotation continue, README.md à jour." % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
