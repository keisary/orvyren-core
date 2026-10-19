#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — DEV/EVAL window registry and embargoes (G3).

Normative sources: B7 §d.1 (final table of the datasets), §d.2 (the four
embargoes + mechanical verification), FREEZE_V2 §7 (G1–G4), DOC2 §5.8.4.

Four embargoes, four verifiers:

1. **parameters** — no G1–G6 constant can be modified after the first EVAL
   run (enforced by :func:`verify_frozen_package` + :func:`eval_run_gate`);
2. **data (24 h)** — the 24 h band preceding each EVAL window is removed from
   DEV (:func:`data_embargo_violations`);
3. **inspection** — the EVAL windows are neither inspected nor used to tune
   anything (outside the scope of the code: written commitment in G3);
4. **cross-calibration** — the months used to calibrate thresholds (quantiles)
   cannot overlap an evaluation CALM window
   (:func:`cross_calibration_violations`).

A window is registered here **only if its source is traceable** (repository
file or cited frozen decision). What is not derivable is listed
``TO FREEZE — NOT DONE`` with the reason, never invented.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

SET_DEV = "dev"
SET_EVAL = "eval"
SETS = (SET_DEV, SET_EVAL)

KIND_STRESS = "stress"
KIND_CALME = "calme"
KIND_TEMOIN = "temoin"

#: Data embargo band before each EVAL window (B7 §d.2.2).
DATA_EMBARGO_HOURS = 24

#: Canonical names of the freeze package (frozen/Gx.sha256, sha256sum format).
FROZEN_FILES = ("G1", "G2", "G3", "G4", "G5", "G6")

#: Mandatory mention of a forced EVAL re-run (B7 §d.2.5).
FORCED_RERUN_MENTION = "evaluation re-executed (invalid for the claim)"


class WindowError(ValueError):
    """Malformed window or forbidden overlap."""


class FreezeGateError(RuntimeError):
    """Freeze package absent, incomplete or mismatched — write refused."""


def parse_utc(stamp: str) -> _dt.datetime:
    """ISO-8601 timestamp (``Z`` or offset) → aware UTC ``datetime``."""
    text = stamp.replace("Z", "+00:00")
    parsed = _dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def format_utc(moment: _dt.datetime) -> str:
    """UTC ``datetime`` → canonical timestamp ``YYYY-MM-DDTHH:MM:SSZ``."""
    return moment.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_parse = parse_utc  # historical internal alias


@dataclass(frozen=True)
class Window:
    """Evaluation window: UTC bounds, dataset, role, provenance."""

    window_id: str
    episode_id: str
    set_label: str
    kind: str
    start_utc: str
    end_utc: str
    sources: Tuple[str, ...]
    role: str
    note: str = ""

    def __post_init__(self):
        if self.set_label not in SETS:
            raise WindowError(f"unknown dataset: {self.set_label!r}")
        if _parse(self.end_utc) <= _parse(self.start_utc):
            raise WindowError(f"empty or inverted window: {self.window_id}")

    @property
    def start(self) -> _dt.datetime:
        return _parse(self.start_utc)

    @property
    def end(self) -> _dt.datetime:
        return _parse(self.end_utc)

    def overlaps(self, other: "Window") -> bool:
        """Overlap of **closed** intervals (bounds included)."""
        return self.start < other.end and other.start < self.end

    def intersects(self, start_utc: str, end_utc: str) -> bool:
        start, end = _parse(start_utc), _parse(end_utc)
        return self.start < end and start < self.end

    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


# --- registry ----------------------------------------------------------------
# Every row cites its source: B7 §d.1 (dataset table) or a repository file.
# No EVAL "calm 2025–2026" window is registered: its exact list is an open
# point of the freeze (B7 Q6) — see PENDING_WINDOWS below.

DEV_WINDOWS: Tuple[Window, ...] = (
    Window(
        window_id="dev-usdc-2023-03",
        episode_id="usdc-2023-03",
        set_label=SET_DEV,
        kind=KIND_STRESS,
        start_utc="2023-03-10T00:00:00Z",
        end_utc="2023-03-14T00:00:00Z",
        sources=("evidence/episode_usdc_2023-03.json", "corpus/usdc_observations.csv"),
        role="Development episode #1 (B7 §d.1): tune the thresholds, debug, measure the costs; contamination accepted.",
    ),
    Window(
        window_id="dev-usdc-2023-02-temoin",
        episode_id="usdc-2023-02",
        set_label=SET_DEV,
        kind=KIND_TEMOIN,
        start_utc="2023-02-15T00:00:00Z",
        end_utc="2023-02-18T00:00:00Z",
        sources=("corpus/usdc_observations.csv", "corpus/manifest.json"),
        role="Control window of the frozen AX0 rule (FREEZE_V1 D7; baseline_report.json: 0 signal).",
        note=(
            "Frozen CALM criterion (max|P−1| < 0.5 %) NOT satisfied on this window: "
            "reclassified STRESS by mechanical application of the criterion (B7 §d.1) — measurement in frozen/G3."
        ),
    ),
    Window(
        window_id="dev-steth-2022-06",
        episode_id="steth-2022-06",
        set_label=SET_DEV,
        kind=KIND_STRESS,
        start_utc="2022-05-09T00:00:00Z",
        end_utc="2022-07-31T00:00:00Z",
        sources=("evidence/episode_steth_2022-06.json",),
        role="Long DEV backtest (B7 §d.1): long-series control, threshold non-regression.",
    ),
    Window(
        window_id="dev-steth-2022-05-calme",
        episode_id="steth-2022-06",
        set_label=SET_DEV,
        kind=KIND_CALME,
        start_utc="2022-05-01T00:00:00Z",
        end_utc="2022-05-08T00:00:00Z",
        sources=("evidence/episode_steth_2022-06.json",),
        role="DEV calm window on the stETH achievable-discount series (frozen CALM criterion satisfied — measurement in frozen/G3).",
    ),
)

EVAL_WINDOWS: Tuple[Window, ...] = (
    Window(
        window_id="eval-rseth-2026-04",
        episode_id="rseth-2026-04",
        set_label=SET_EVAL,
        kind=KIND_STRESS,
        start_utc="2026-04-17T00:00:00Z",
        end_utc="2026-04-21T00:00:00Z",
        sources=("evidence/episode_rseth_2026-04.json", "B7 §d.1"),
        role="EVALUATION #1 (main) — single execution after the freeze; post-freeze abstention = expected answer.",
    ),
    Window(
        window_id="eval-usd0pp-2025-01",
        episode_id="usd0pp-2025-01",
        set_label=SET_EVAL,
        kind=KIND_STRESS,
        start_utc="2025-01-08T00:00:00Z",
        end_utc="2025-01-31T00:00:00Z",
        sources=("corpus/series/usd0pp_2025-01.json", "B7 §d.1"),
        role="EVALUATION #2 (secondary) — different mechanism (contractual de-basing); likely contamination accepted.",
        note=(
            "Series archived in the repository (W3-C probe, corpus/series/usd0pp_2025-01.json, "
            "pinned by replay/corpus_v1.manifest.json) — the window is instrumented; "
            "the earlier 'series to be assembled outside the repository' caveat is closed."
        ),
    ),
)

#: Windows not registered for lack of a derivable source — NOT DONE, reason written.
PENDING_WINDOWS: Tuple[dict, ...] = (
    {
        "window_id": "eval-calme-2025-2026 (≥ 6)",
        "status": "NOT DONE",
        "reason": (
            "Exact list and bounds of the CALM EVAL windows to freeze (B7 Q6 / FREEZE_V2 §11.5): "
            "requires the CALM criterion applied to 2025–2026 series not yet archived in the repository. "
            "No window is invented."
        ),
    },
    {
        "window_id": "dev-calme-2022-2023 (≥ 6)",
        "status": "PARTIEL",
        "reason": (
            "Only one DEV calm window is derivable today (dev-steth-2022-05-calme, criterion satisfied). "
            "The USDC control window fails the frozen CALM criterion (reclassified STRESS). "
            "The remaining calm windows depend on a collection work item (R3 §C.8)."
        ),
    },
)


# --- embargoes ---------------------------------------------------------------


def overlap_violations(windows: Sequence[Window]) -> List[Tuple[str, str]]:
    """Forbidden overlaps inside one dataset (R3 §B.3: paired windows are disjoint)."""
    pairs: List[Tuple[str, str]] = []
    for i, left in enumerate(windows):
        for right in windows[i + 1 :]:
            if left.overlaps(right):
                pairs.append((left.window_id, right.window_id))
    return pairs


def check_no_overlap(windows: Sequence[Window]) -> None:
    """Raise :class:`WindowError` if two windows of the dataset overlap."""
    pairs = overlap_violations(windows)
    if pairs:
        raise WindowError(f"window overlap forbidden: {pairs}")


def data_embargo_violations(
    dev_windows: Sequence[Window],
    eval_windows: Sequence[Window],
    band_hours: int = DATA_EMBARGO_HOURS,
) -> List[dict]:
    """Data embargo: the ``[start − 24 h, start]`` band of every EVAL window
    must not cross **any** DEV window (B7 §d.2.2)."""
    violations: List[dict] = []
    for eval_window in eval_windows:
        band_start = eval_window.start - _dt.timedelta(hours=band_hours)
        for dev_window in dev_windows:
            if dev_window.start < eval_window.start and dev_window.end > band_start:
                violations.append(
                    {
                        "eval_window": eval_window.window_id,
                        "dev_window": dev_window.window_id,
                        "band": [band_start.strftime("%Y-%m-%dT%H:%M:%SZ"), eval_window.start_utc],
                        "rule": f"{band_hours} h band removed from DEV",
                    }
                )
    return violations


def cross_calibration_violations(
    calibration_periods: Sequence[str],
    eval_calm_windows: Sequence[Window],
) -> List[dict]:
    """Cross-calibration embargo (B7 §d.2.4).

    ``calibration_periods``: months declared for threshold calibration, in
    ``"YYYY-MM"`` format (whole month). A CALM EVAL window (all or part of its
    interval) falling inside a calibration month = violation: the calibration
    would "see" the evaluation dataset.
    """
    violations: List[dict] = []
    for period in calibration_periods:
        if not re.fullmatch(r"\d{4}-\d{2}", period):
            raise WindowError(f"calibration period expected in YYYY-MM format: {period!r}")
        year, month = int(period[:4]), int(period[5:7])
        period_start = _dt.datetime(year, month, 1, tzinfo=_dt.timezone.utc)
        period_end = _dt.datetime(year + (month // 12), (month % 12) + 1, 1, tzinfo=_dt.timezone.utc)
        for window in eval_calm_windows:
            if window.start < period_end and period_start < window.end:
                violations.append(
                    {
                        "calibration_period": period,
                        "eval_window": window.window_id,
                        "rule": "claim quantiles are computed outside the CALM EVAL windows",
                    }
                )
    return violations


# --- freeze gate -------------------------------------------------------------


def _normalized_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        raw = handle.read()
    return raw.replace(b"\r\n", b"\n")


def sha256_file(path: str) -> str:
    """SHA-256 of the file bytes, CRLF normalised to LF (portability)."""
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def _read_sha256sum(manifest_path: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    with open(manifest_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise FreezeGateError(f"unreadable sha256sum line in {manifest_path}: {line!r}")
            digest, name = parts[0].lower(), parts[1].strip().lstrip("*")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise FreezeGateError(f"invalid digest in {manifest_path}: {digest!r}")
            entries.append((digest, name))
    return entries


def verify_frozen_package(frozen_dir: str, required: Sequence[str] = FROZEN_FILES) -> dict:
    """Verify ``frozen/Gx.sha256``: presence, readability, match.

    Returns ``{name: sha256}`` when everything matches; raises
    :class:`FreezeGateError` with the detail of the first mismatch (freeze
    absent, incomplete or modified → every evaluation write is refused).
    """
    if not os.path.isdir(frozen_dir):
        raise FreezeGateError(f"freeze package absent: {frozen_dir} (G1–G6 required before any write)")
    hashes: dict = {}
    for name in required:
        manifest = os.path.join(frozen_dir, f"{name}.sha256")
        if not os.path.isfile(manifest):
            raise FreezeGateError(f"freeze manifest missing: {manifest}")
        entries = _read_sha256sum(manifest)
        if not entries:
            raise FreezeGateError(f"freeze manifest empty: {manifest}")
        for digest, referenced in entries:
            target = referenced if os.path.isabs(referenced) else os.path.join(frozen_dir, referenced)
            if not os.path.isfile(target):
                raise FreezeGateError(f"{manifest} references a missing file: {referenced}")
            actual = sha256_file(target)
            if actual != digest:
                raise FreezeGateError(
                    f"mismatched digest for {referenced}: {actual} ≠ {digest} (freeze modified?)"
                )
            hashes[name] = actual
    return hashes


def eval_run_gate(frozen_dir: str, lock_path: Optional[str] = None, force: bool = False) -> Optional[str]:
    """EVAL run gate (B7 §d.2.5): refusal without a freeze; refusal of the
    second execution without ``force``; mandatory mention when ``force`` is used.

    Returns ``None`` when a first execution is possible, or the **mandatory
    mention** to write at the top of the report when ``force`` is used.
    """
    verify_frozen_package(frozen_dir)
    if lock_path and os.path.exists(lock_path):
        if not force:
            raise FreezeGateError(
                f"evaluation lock present ({lock_path}): second execution forbidden without --force "
                "(the EVAL dataset is burned after the first execution)"
            )
        return FORCED_RERUN_MENTION
    return None
