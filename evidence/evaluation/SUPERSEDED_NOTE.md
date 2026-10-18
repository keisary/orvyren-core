# SUPERSEDED — evaluation report of 2026-10-17

`evaluation_report.md` and `evaluation_report.json` in this directory were
produced on **2026-10-17 09:12**, before the R−/R+ aggregation fix of
2026-10-18 (`src/orvyren/evaluation/harness.py`, now G1-correct:
R+ = max(0, L(A0)−L(a)), R− = max(0, L(a)−L(A0)) per window vs A0).

Consequences:

- every `mean_R_minus` value of `0.0000` in those files is an artifact of the
  old formula (max/min of the oracle regret), **not a measurement**;
- the files are left **byte-identical** on purpose: their `content_sha256` is
  referenced by `variants.log` and the G6 calibration embargo was signed on
  2026-10-17 — regenerating them would invalidate the signed evaluation;
- quote no figure from these two files without this note; the code is the
  current truth, these artifacts are historical.

Gap register: `docs/SUBMISSION_SCOPE_AND_GAPS.md` G-16.
