#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — verifier for the ``frozen/`` freeze package (offline).

Three checks, in this order:

1. **fingerprints** — the ``G1..G6.sha256`` manifests exist and agree with the
   files they reference (``orvyren.evaluation.windows.verify_frozen_package``);
2. **chains** — ``forecasts_dev.jsonl`` (``prev_hash`` + self-carried digest)
   and ``outcomes_dev.jsonl`` (chaining + link by forecast <-> outcome
   fingerprint);
3. **full recalculation** — the package is rebuilt into a temporary directory
   by ``scripts/freeze_sprint0.py`` and compared **byte for byte**: this is the
   proof that ``frozen/`` is recomputable offline.

Output: one line per check, then the verdict. Exit code 0 if everything agrees,
1 otherwise (usable in CI). No network access.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import tempfile
import time
from typing import Optional, Sequence

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
sys.path.insert(0, os.path.join(DEFAULT_REPO_ROOT, "src"))

from orvyren.evaluation import forecasts as forecasts_mod  # noqa: E402
from orvyren.evaluation import outcomes as outcomes_mod  # noqa: E402
from orvyren.evaluation import windows as windows_mod  # noqa: E402


def _configure_stdio() -> None:
    """Force UTF-8 on stdout/stderr: a Windows cp1252 console must never make
    verification fail on an unrepresentable character."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # non-reconfigurable stream (test capture, pipe)
            pass


def _load_builder():
    spec = importlib.util.spec_from_file_location("freeze_sprint0", os.path.join(SCRIPTS_DIR, "freeze_sprint0.py"))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def verify(frozen_dir: str, repo_root: str, recalc: bool = True) -> bool:
    ok = True

    # 1. G1..G6 fingerprints
    try:
        hashes = windows_mod.verify_frozen_package(frozen_dir)
        for name in sorted(hashes):
            print(f"[OK]   {name}.sha256 verified ({hashes[name][:16]}…)")
    except Exception as exc:  # noqa: BLE001 — the report must show everything
        print(f"[KO]   frozen package: {exc}")
        ok = False

    # 2. forecast / outcome chains
    forecasts_path = os.path.join(frozen_dir, "forecasts_dev.jsonl")
    outcomes_path = os.path.join(frozen_dir, "outcomes_dev.jsonl")
    try:
        records = forecasts_mod.load_forecasts(forecasts_path)
        ids = forecasts_mod.verify_forecast_chain(records, path=forecasts_path)
        print(f"[OK]   forecasts_dev.jsonl: {len(ids)} forecasts, chain verified")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   forecasts_dev.jsonl: {exc}")
        ok = False
        records = []
    try:
        outcomes = outcomes_mod.load_outcomes(outcomes_path)
        ids_out = outcomes_mod.verify_outcome_chain(outcomes, path=outcomes_path)
        print(f"[OK]   outcomes_dev.jsonl: {len(ids_out)} outcomes, chain verified")
        by_id = {record["forecast_id"]: record for record in records}
        for outcome in outcomes:
            linked = by_id.get(outcome["forecast_id"])
            if linked is None:
                raise KeyError("outcome links to unknown forecast %r (forecasts loaded: %d)"
                               % (outcome["forecast_id"], len(records)))
            outcomes_mod.check_link(linked, outcome)
        print(f"[OK]   forecast <-> outcome link by fingerprint: {len(outcomes)}/{len(records)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   outcomes_dev.jsonl: {exc}")
        ok = False

    if not recalc:
        return ok

    # 3. full offline recalculation into a temporary directory
    started = time.perf_counter()
    builder = _load_builder()
    tmp = tempfile.mkdtemp(prefix="orvyren_frozen_recalc_")
    try:
        builder.build_all(tmp, repo_root=repo_root)
        elapsed = time.perf_counter() - started
        names = sorted(os.listdir(frozen_dir))
        mismatches = []
        for name in names:
            source = os.path.join(frozen_dir, name)
            rebuilt = os.path.join(tmp, name)
            if not os.path.isfile(rebuilt):
                mismatches.append(name)
                continue
            with open(source, "rb") as handle:
                left = handle.read().replace(b"\r\n", b"\n")
            with open(rebuilt, "rb") as handle:
                right = handle.read().replace(b"\r\n", b"\n")
            if left != right:
                mismatches.append(name)
        extra = sorted(set(os.listdir(tmp)) - set(names))
        if mismatches or extra:
            print(f"[KO]   recalc: mismatches {mismatches or ''} {('extra: ' + str(extra)) if extra else ''}")
            ok = False
        else:
            print(f"[OK]   offline recalc byte-identical ({len(names)} files, {elapsed:.2f} s)")
    except Exception as exc:  # noqa: BLE001
        print(f"[KO]   offline recalc: {exc}")
        ok = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


def main(argv: Optional[Sequence[str]] = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Verify frozen/: fingerprints, chains, offline recalculation.")
    parser.add_argument("--frozen", default=None, help="package directory (default: <repo>/frozen)")
    parser.add_argument("--repo-root", default=None, help="repository root (default: parent of scripts/)")
    parser.add_argument("--no-recalc", action="store_true", help="skip the full recalculation (fast)")
    args = parser.parse_args(argv)
    repo_root = args.repo_root or DEFAULT_REPO_ROOT
    frozen_dir = args.frozen or os.path.join(repo_root, "frozen")
    ok = verify(frozen_dir, repo_root, recalc=not args.no_recalc)
    print("VERDICT: " + ("frozen package COMPLIANT" if ok else "MISMATCHES DETECTED — do not claim"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
