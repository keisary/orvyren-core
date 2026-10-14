#!/usr/bin/env python
"""ORVYREN-Core v0.1 - build the one-page decision dossier, optionally serve it.

Usage (from anywhere; relative paths resolve against the repository root)::

    python run_audit.py
    python run_audit.py --serve
    python run_audit.py --serve --host 127.0.0.1 --port 8000

Reads ``evidence/decision_usdc-2023-03.json`` plus any optional extra report
that exists (``baseline_report.json``, ``policy_execution_demo.json``,
``quality_report.json``) and writes ``evidence/dossier_usdc-2023-03.md`` and
``evidence/dossier_usdc-2023-03.html``. Missing inputs are reported inside the
dossier (``Missing input: <path>``) and are never invented.

``--extra LABEL=PATH`` adds (or overrides) an input file, e.g. to build a
demonstration dossier from a fixture stored outside the repository.
"""

import argparse
import datetime
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from orvyren.audit import dossier  # noqa: E402

DEFAULT_DECISION = os.path.join("evidence", "decision_usdc-2023-03.json")
DEFAULT_OUT_DIR = "evidence"
EXTRA_INPUTS = (
    ("baseline_report", os.path.join("evidence", "baseline_report.json")),
    ("policy_execution_demo", os.path.join("evidence", "policy_execution_demo.json")),
    ("quality_report", os.path.join("evidence", "quality_report.json")),
)


def _resolve(path):
    return path if os.path.isabs(path) else os.path.join(_REPO_ROOT, path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="run_audit.py",
        description="Build the ORVYREN-Core v0.1 decision dossier (and optionally serve it).",
    )
    parser.add_argument(
        "--decision",
        default=DEFAULT_DECISION,
        metavar="PATH",
        help="decision JSON to render (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        metavar="DIR",
        help="dossier output directory (default: %(default)s)",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="additional input to hash and render, repeatable "
        "(e.g. --extra baseline_report=fixtures/baseline.json)",
    )
    parser.add_argument("--serve", action="store_true", help="start the dossier HTTP server after building")
    parser.add_argument("--host", default="127.0.0.1", help="server bind host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=8000, help="server bind port (default: %(default)s)")
    parser.add_argument(
        "--generated-at",
        default=None,
        metavar="ISO8601",
        help="freeze the dossier's 'Generated (UTC)' field (e.g. 2026-10-14T14:42:45Z) "
        "to rebuild a byte-identical dossier from identical inputs",
    )
    args = parser.parse_args(argv)

    generated_at = None
    if args.generated_at:
        try:
            frozen = datetime.datetime.fromisoformat(
                args.generated_at.strip().replace("Z", "+00:00"))
        except ValueError:
            parser.error("--generated-at expects an ISO-8601 timestamp, got: %s" % args.generated_at)
        if frozen.tzinfo is None:
            frozen = frozen.replace(tzinfo=datetime.timezone.utc)
        generated_at = frozen.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    decision_path = _resolve(args.decision)
    out_dir = _resolve(args.out_dir)

    extras = {}
    for label, relative in EXTRA_INPUTS:
        candidate = _resolve(relative)
        if os.path.exists(candidate):
            extras[label] = candidate
    for item in args.extra:
        if "=" not in item:
            parser.error(f"--extra expects LABEL=PATH, got: {item}")
        label, raw = item.split("=", 1)
        extras[label.strip()] = _resolve(raw.strip())

    result = dossier.build(decision_path, out_dir, extra_paths=extras, generated_at=generated_at)

    print(f"ORVYREN-Core v{dossier.ENGINE_VERSION} - audit dossier built")
    print(f"  case          : {result['case']}")
    if generated_at:
        print(f"  generated_at  : {generated_at} (frozen - reproducible rebuild)")
    if os.path.exists(decision_path):
        print(f"  decision input: {decision_path}")
    else:
        print(f"  decision input: {decision_path}  [MISSING - marked as 'Missing input' in the dossier]")
    print(f"  markdown      : {result['md_path']}")
    print(f"  html          : {result['html_path']}")
    print(f"  sha256 (md)   : {result['sha256']}")
    print(f"  sha256 (html) : {result['sha256_html']}")
    print(f"  inputs hashed : {sum(1 for r in result['inputs'] if r['sha256'])} of {len(result['inputs'])} declared")
    for record in result["inputs"]:
        line = f"    - {record['label']}: {record['path']} [{record['status']}]"
        if record["sha256"]:
            line += f" sha256={record['sha256']}"
        print(line)
    print("  note          : sha256 (md/html) is the reproducible self-hash, computed over the")
    print("                  rendered file with its own self-hash field zeroed to 64 '0's.")

    if args.serve:
        from orvyren.ui import server as ui_server

        ui_server.serve(args.host, args.port, evidence_dir=out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
