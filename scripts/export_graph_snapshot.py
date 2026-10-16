#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — export d'un instantané de graphe point-in-time (W1/L1.6).

Écrit ``graph_snapshot.json`` + ``provenance.json`` + ``MANIFEST.sha256`` pour
un cas et un instant simulé — l'artefact consommé par le paquet d'audit (W6)
et re-vérifiable par un tiers (``sha256sum -c MANIFEST.sha256``).

Usage ::

    python scripts/export_graph_snapshot.py --case usdc-2023-03 --as-of 2026-10-16T00:00:00Z
    python scripts/export_graph_snapshot.py --case rseth-2026-04 --as-of 2026-04-18T18:30:00Z

Sortie par défaut : ``evidence/graph_snapshots/<case>@<as_of compact>/``.
Stdlib uniquement ; aucun accès réseau.
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
                        help="cas des fixtures (ex. usdc-2023-03)")
    parser.add_argument("--as-of", required=True,
                        help="instant simulé ISO-8601 (ex. 2026-10-16T00:00:00Z)")
    parser.add_argument("--out", default=None,
                        help="répertoire de sortie (défaut evidence/graph_snapshots/<case>@<as_of>)")
    args = parser.parse_args(argv)

    fixture = os.path.join(REPO_ROOT, "fixtures", "graphs", "%s.json" % args.case)
    if not os.path.exists(fixture):
        raise SystemExit("E_CASE_UNKNOWN: %s absent" % fixture)
    records = load_fixture_records(fixture)

    compact = args.as_of.replace(":", "").replace("-", "")
    out_dir = args.out or os.path.join(REPO_ROOT, "evidence", "graph_snapshots",
                                       "%s@%s" % (args.case, compact))
    paths = write_snapshot_dir(records, args.case, args.as_of, out_dir)
    print("ORVYREN — instantané de graphe exporté (L1.6)")
    print("  cas      : %s @ %s" % (args.case, args.as_of))
    print("  sortie   : %s" % out_dir)
    print("  snapshot : sha256=%s" % paths["snapshot_hash"][:16])
    print("  provenance: sha256=%s" % paths["provenance_hash"][:16])
    print("  vérif    : (cd %s && sha256sum -c MANIFEST.sha256)" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
