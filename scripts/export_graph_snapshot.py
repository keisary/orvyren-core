#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — export of a point-in-time graph snapshot (W1/L1.6).

Writes ``graph_snapshot.json`` + ``provenance.json`` + ``MANIFEST.sha256`` for
one case and one simulated instant — the artefact consumed by the audit packet
(W6) and re-verifiable by a third party (``sha256sum -c MANIFEST.sha256``).

Usage::

    python scripts/export_graph_snapshot.py --case usdc-2023-03 --as-of 2026-10-16T00:00:00Z
    python scripts/export_graph_snapshot.py --case rseth-2026-04 --as-of 2026-04-18T18:30:00Z

Default output: ``evidence/graph_snapshots/<case>@<as_of compact>/``.
Standard library only; no network access.
"""

from __future__ import annotations

import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(REPO_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from orvyren.graph.export import write_snapshot_dir  # noqa: E402
from orvyren.graph.queries import load_fixture_records  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="export_graph_snapshot.py")
    parser.add_argument("--case", required=True,
                        help="fixture case (e.g. usdc-2023-03)")
    parser.add_argument("--as-of", required=True,
                        help="simulated ISO-8601 instant (e.g. 2026-10-16T00:00:00Z)")
    parser.add_argument("--out", default=None,
                        help="output directory (default evidence/graph_snapshots/<case>@<as_of>)")
    args = parser.parse_args(argv)

    fixture = os.path.join(REPO_ROOT, "fixtures", "graphs", "%s.json" % args.case)
    if not os.path.exists(fixture):
        raise SystemExit("E_CASE_UNKNOWN: %s missing" % fixture)
    records = load_fixture_records(fixture)

    compact = args.as_of.replace(":", "").replace("-", "")
    out_dir = args.out or os.path.join(REPO_ROOT, "evidence", "graph_snapshots",
                                       "%s@%s" % (args.case, compact))
    paths = write_snapshot_dir(records, args.case, args.as_of, out_dir)
    print("ORVYREN — graph snapshot exported (L1.6)")
    print("  case      : %s @ %s" % (args.case, args.as_of))
    print("  output    : %s" % out_dir)
    print("  snapshot  : sha256=%s" % paths["snapshot_hash"][:16])
    print("  provenance: sha256=%s" % paths["provenance_hash"][:16])
    print("  verify    : (cd %s && sha256sum -c MANIFEST.sha256)" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
