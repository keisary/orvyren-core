#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — ADR registry (`docs/decisions/`): index + check (W8, L8.5).

Verifies that the registry is **numbered without gaps or duplicates** and that
the `README.md` table reflects the `ADR-*.md` files exactly (number, link,
status, date). `--write` regenerates the table; `--check` (default) fails on
any divergence — it is the CI-wired check.

Expected format in each `ADR-NNNN-*.md`:

    # ADR-0001 — Title ...
    **Date :** 2026-10-16 · **Statut : ACCEPTÉE · **Portée :** ...

Usage::

    python scripts/adr_index.py --check       # CI: 0 = compliant
    python scripts/adr_index.py --write       # regenerate the README table
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
_FILE_NUMBER_RE = re.compile(r"^ADR-(\d{4})")
_DATE_RE = re.compile(r"\*\*Date\s*:\*\*\s*(\d{4}-\d{2}-\d{2})")
_STATUS_RE = re.compile(r"\*\*Statut\s*:\s*(.+?)(?:·|\n|$)")
_README_ROW_RE = re.compile(
    r"^\|\s*(\d{4})\s*\|\s*\[(.*?)\]\((ADR-[^)]+\.md)\)\s*\|\s*([^|]+?)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*$",
    re.MULTILINE)

#: Section heading used as the insertion anchor in ``docs/decisions/README.md``.
REGISTRE_HEADER = "## Registre"
#: Placeholder status/date, matched by :func:`check` — not a document format.
STATUS_MISSING = "(status missing)"
DATE_MISSING = "(date missing)"


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
        file_number_match = _FILE_NUMBER_RE.match(name)
        if title_match is None and file_number_match is None:
            # Odd file (e.g. "ADR-INDEX.md"): cannot be numbered — scan() must
            # never raise on odd files, so it is left out of the registry.
            continue
        number = int(title_match.group(1)) if title_match else int(file_number_match.group(1))
        title = title_match.group(2) if title_match else name
        status_raw = status_match.group(1).strip() if status_match else STATUS_MISSING
        status_raw = re.sub(r"\*+", "", status_raw).strip()
        entries.append({
            "number": number,
            "file": name,
            "title": title,
            "status_core": status_raw.split("—")[0].strip(),
            "status_raw": status_raw,
            "date": date_match.group(1) if date_match else DATE_MISSING,
        })
    entries.sort(key=lambda entry: (entry["number"], entry["file"]))
    return entries


def check(entries, decisions_dir):
    """Return a list of human-readable problems ([] = compliant registry)."""
    problems = []
    numbers = [entry["number"] for entry in entries]
    for missing in range(1, (max(numbers) if numbers else 0) + 1):
        if missing not in numbers:
            problems.append("missing number: ADR-%04d" % missing)
    seen = set()
    for number in numbers:
        if number in seen:
            problems.append("duplicate number: ADR-%04d" % number)
        seen.add(number)
    for entry in entries:
        if entry["status_core"] == STATUS_MISSING:
            problems.append("missing status in %s" % entry["file"])
        if entry["date"] == DATE_MISSING:
            problems.append("missing date in %s" % entry["file"])

    readme_path = os.path.join(decisions_dir, "README.md")
    try:
        with open(readme_path, "r", encoding="utf-8") as handle:
            readme = handle.read()
    except OSError:
        return problems + ["unreadable README.md in %s" % decisions_dir]
    rows = {int(row[0]): row for row in _README_ROW_RE.findall(readme)}
    for entry in entries:
        row = rows.get(entry["number"])
        if row is None:
            problems.append("README.md: missing row for ADR-%04d" % entry["number"])
            continue
        _num, _label, link, status_cell, date_cell = row
        if link != entry["file"]:
            problems.append("README.md: wrong link for ADR-%04d (%s ≠ %s)"
                            % (entry["number"], link, entry["file"]))
        if status_cell.strip() != entry["status_core"]:
            problems.append("README.md: divergent status for ADR-%04d (%r ≠ %r)"
                            % (entry["number"], status_cell.strip(), entry["status_core"]))
        if date_cell != entry["date"]:
            problems.append("README.md: divergent date for ADR-%04d" % entry["number"])
    for number in rows:
        if number not in numbers:
            problems.append("README.md: orphan row for ADR-%04d" % number)
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
        raise SystemExit("E_ADR_README: section '%s' not found in %s" % (REGISTRE_HEADER, readme_path))
    start = text.index(REGISTRE_HEADER)
    after = text[start + len(REGISTRE_HEADER):]
    # Replace only the registry section; preserve any later sections verbatim
    # instead of truncating the README at the table.
    next_section = re.search(r"(?m)^##\s+", after)
    tail = after[next_section.start():] if next_section else ""
    head = text[:start] + REGISTRE_HEADER + "\n\n" + render_registry(entries)
    if tail:
        head = head.rstrip("\n") + "\n\n" + tail.lstrip("\n")
    else:
        head = head.rstrip("\n") + "\n"
    with open(readme_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(head)
    return readme_path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="adr_index.py",
                                     description="ADR registry: index check (default) or regeneration.")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="ADR directory (default: docs/decisions)")
    parser.add_argument("--check", action="store_true", help="check only (default)")
    parser.add_argument("--write", action="store_true", help="regenerate the README.md table")
    args = parser.parse_args(argv)

    decisions_dir = os.path.abspath(args.dir)
    if not os.path.isdir(decisions_dir):
        print("E_ADR_DIR: not found: %s" % decisions_dir, file=sys.stderr)
        return 1
    entries = scan(decisions_dir)
    if args.write:
        path = rewrite_readme(decisions_dir, entries)
        print("ADR registry written: %s (%d entries)" % (path, len(entries)))
        return 0
    problems = check(entries, decisions_dir)
    if problems:
        for problem in problems:
            print("ADR INDEX: %s" % problem, file=sys.stderr)
        return 1
    print("ADR INDEX OK — %d entries, contiguous numbering, README.md up to date." % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
