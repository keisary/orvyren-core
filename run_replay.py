#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — replay engine CLI (W7, B7 §c.8).

Four sub-commands:

    python run_replay.py inspect --episode usdc-2023-03 [--t-sim ISO]
        frozen corpus verified (hash), window, block anchors, series gaps.
    python run_replay.py journal --case usdc-2023-03 [--k 10] [--session DIR]
        mode 1 — bit-for-bit; produces a replay dossier marked REPLAY.
    python run_replay.py archive --case usdc-2023-03 [--k 3]
        mode 2 — LLM recomputation (requires a key; without a key: explicit refusal, code 3).
    python run_replay.py verify --run-dir DIR [--dossier FILE]
        T10 — recomputes the transcript and compares it with the dossier hash.

A replay run **never signs** and emits no transaction (B7 §c.5-4).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from orvyren.evaluation import windows as windows_mod  # noqa: E402
from orvyren.replay import archive as archive_mod  # noqa: E402
from orvyren.replay import clock as clock_mod  # noqa: E402
from orvyren.replay import corpus as corpus_mod  # noqa: E402
from orvyren.replay import dossier as dossier_mod  # noqa: E402
from orvyren.replay import journal as journal_mod  # noqa: E402

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_UNAVAILABLE = 3


def _configure_stdio() -> None:
    """Force UTF-8 on stdout/stderr: a Windows cp1252 console must never
    make the CLI fail on a non-representable character."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # stream cannot be reconfigured (test capture, pipe)
            pass


def _find_window_for_episode(episode: str):
    for window in tuple(windows_mod.DEV_WINDOWS) + tuple(windows_mod.EVAL_WINDOWS):
        if window.episode_id == episode or window.window_id == episode:
            return window
    return None


def _clock_for(case_id: str, run_id: str):
    window = _find_window_for_episode(case_id)
    if window is None:
        raise SystemExit("E_WINDOW_UNKNOWN: no window registered for %s "
                         "(windows: %s)" % (case_id, [w.window_id for w in windows_mod.DEV_WINDOWS]))
    return clock_mod.ReplayClock.from_window(window, run_id=run_id), window


def cmd_inspect(args) -> int:
    manifest = corpus_mod.load_manifest(args.manifest)
    print("frozen corpus — %d files, manifest hash %s"
          % (len(manifest["files"]), manifest["manifest_sha256"]))
    window = _find_window_for_episode(args.episode)
    if window is not None:
        print("  window     : %s (%s → %s, %s)" % (window.window_id, window.start_utc,
                                                   window.end_utc, window.kind))
        try:
            label, points = corpus_mod.window_series(window)
            gaps = corpus_mod.find_gaps(points)
            print("  series     : %s — %d points, %d gap(s)" % (label, len(points), len(gaps)))
            for gap in gaps[:3]:
                print("    gap: %s -> %s (%.1f min)" % (gap["after_utc"], gap["before_utc"],
                                                       gap["gap_minutes"]))
        except corpus_mod.CorpusError as exc:
            print("  series     : UNRESOLVED — %s" % exc)
    else:
        print("  window     : none (unregistered episode) — declared, never invented")
    anchors = corpus_mod.load_block_anchors()
    if anchors is None:
        print("  anchors    : replay/blocks_v1.json MISSING — table declared missing "
              "(never invented); any chain access requires a pinned block")
    else:
        print("  anchors    : %d day(s) resolved" % len(anchors))
    if args.t_sim:
        print("  t_sim      : %s (requested — inspection clock; the replay sub-commands "
              "build their clock from the window)" % args.t_sim)
    return EXIT_OK


def cmd_journal(args) -> int:
    manifest = corpus_mod.load_manifest(args.manifest)
    clock, window = _clock_for(args.case, "replay-journal")
    started = time.time()
    if args.k <= 1:
        session = args.session or tempfile.mkdtemp(prefix="orvyren_replay_journal_")
        run_dir = journal_mod.replay_once(args.case, session, quiet=args.quiet)
        transcript = journal_mod.load_transcript(run_dir)
        k_report = None
        print("journal replay — run %s" % run_dir)
    else:
        work_root = args.session or tempfile.mkdtemp(prefix="orvyren_replay_k_")
        k_report = journal_mod.replay_k(args.case, work_root, k=args.k, quiet=True)
        run_dir = k_report["run_dirs"][-1]
        transcript = journal_mod.load_transcript(run_dir)
        print("journal replay × %d — hash %s: %s"
              % (args.k, "IDENTICAL" if k_report["identical"] else "DIVERGENT", k_report["hash"]))
        if not k_report["identical"]:
            return EXIT_FAIL
    audit = clock.audit(extra={"note": "journal mode — recorded sequences, clock not "
                                      "consumed (no future event admitted)"})
    result = dossier_mod.build_replay_dossier(
        episode=args.case, mode="REPLAY-JOURNAL", mode_slug="journal",
        run_id=transcript.get("run_id") or "demo-%s" % args.case,
        t_sim_start_utc=window.start_utc, t_sim_end_utc=window.end_utc,
        corpus_manifest=manifest, clock_audit=audit, transcript=transcript,
        k_report=k_report, out_dir=args.out_dir,
        duration_s=round(time.time() - started, 3))
    print("  dossier    : %s" % result["md_path"])
    print("  banner     : %s" % result["banner"])
    print("  hash       : %s" % result["content_sha256"])
    return EXIT_OK


def cmd_archive(args) -> int:
    manifest = corpus_mod.load_manifest(args.manifest)
    try:
        report = archive_mod.replay_archive(args.case, args.session or
                                            tempfile.mkdtemp(prefix="orvyren_replay_archive_"),
                                            k=args.k, quiet=args.quiet)
    except archive_mod.ArchiveUnavailable as exc:
        print("archive: EXPLICIT REFUSAL — %s" % exc, file=sys.stderr)
        return EXIT_UNAVAILABLE
    clock, window = _clock_for(args.case, "replay-archive")
    result = dossier_mod.build_replay_dossier(
        episode=args.case, mode="REPLAY-ARCHIVE", mode_slug="archive",
        run_id="%s-archive" % args.case,
        t_sim_start_utc=window.start_utc, t_sim_end_utc=window.end_utc,
        corpus_manifest=manifest, clock_audit=clock.audit(), archive_report=report,
        out_dir=args.out_dir)
    print("archive dossier : %s" % result["md_path"])
    print("banner          : %s" % result["banner"])
    return EXIT_OK


def cmd_verify(args) -> int:
    if args.dossier:
        verdict = dossier_mod.verify_replay_dossier(args.dossier)
        print("dossier %s — hash %s (%s)" % (args.dossier, verdict["computed"],
                                            verdict["verdict"]))
        if verdict.get("error"):
            print("  %s" % verdict["error"], file=sys.stderr)
        if verdict["verdict"] != "OK":
            return EXIT_FAIL
    if args.run_dir:
        expected = None
        if args.dossier:
            with open(args.dossier, "r", encoding="utf-8") as handle:
                expected = json.load(handle).get("transcript_hash")
        result = journal_mod.verify_run(args.run_dir, expected_hash=expected)
        print("run %s — transcript %s%s" % (args.run_dir, result["transcript_hash"],
                                            "" if expected is None else
                                            " (%s)" % result["verdict"]))
        if result["verdict"] != "OK":
            return EXIT_FAIL
    return EXIT_OK


def main(argv=None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        prog="run_replay.py",
        description="ORVYREN — replay engine: REPLAY-JOURNAL (bit-for-bit) and "
                    "REPLAY-ARCHIVE (recomputation); REPLAY marking mandatory.")
    parser.add_argument("--manifest", default=corpus_mod.DEFAULT_MANIFEST)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("inspect", help="frozen corpus + window + anchors (read-only)")
    p.add_argument("--episode", required=True)
    p.add_argument("--t-sim", default=None)
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("journal", help="mode 1 — bit-for-bit, offline")
    p.add_argument("--case", required=True)
    p.add_argument("--k", type=int, default=1)
    p.add_argument("--session", default=None)
    p.add_argument("--out-dir", default=dossier_mod.DEFAULT_OUT_DIR)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_journal)

    p = sub.add_parser("archive", help="mode 2 — recomputation (LLM key required)")
    p.add_argument("--case", required=True)
    p.add_argument("--k", type=int, default=archive_mod.MIN_REPLAYS)
    p.add_argument("--session", default=None)
    p.add_argument("--out-dir", default=dossier_mod.DEFAULT_OUT_DIR)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_archive)

    p = sub.add_parser("verify", help="T10 — recomputes and compares hashes")
    p.add_argument("--run-dir", default=None)
    p.add_argument("--dossier", default=None)
    p.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    if args.command == "verify" and not (args.dossier or args.run_dir):
        parser.error("\"verify\" requires --run-dir DIR and/or --dossier FILE "
                     "(without a target, no check would be performed: explicit refusal)")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
