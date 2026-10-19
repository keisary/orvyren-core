# Historical note — the 2026-10-17 evaluation artefacts, and their replacement on 2026-10-19

**Status: historical, dated 2026-10-19.** This note describes files that are no
longer in this directory. It is not a description of the current report. The
current artefacts are the first **EVAL** execution of 2026-10-19.

## (a) What existed on 2026-10-17, and what it contained

On **2026-10-17 09:12 UTC** this directory held an `evaluation_report.md` /
`evaluation_report.json` pair produced by the DEV harness of that day. The
matching DEV run entry in `variants.log` is `2026-10-17T09:09:25Z`, set `dev`,
4 windows, `content_sha256` `9d5335946fbbadbf0016d603de44af4c393a89d6e690e4224199b22819894a86`
(the two earlier DEV entries of the same day, `2026-10-17T00:14:08Z` and
`2026-10-17T01:24:24Z`, carry `b3ef5eab4d26b540ed5046938c420ba580d3181396b58f6b985b095a7e7d5fbf`).

Those reports predate the **R−/R+ aggregation fix of 2026-10-18**
(`src/orvyren/evaluation/harness.py`, now computing R+ = max(0, L(A0)−L(a)) and
R− = max(0, L(a)−L(A0)) per window against A0). Consequently:

- every `mean_R_minus` value of `0.0000` in those files was an artifact of the
  old formula (max/min of the oracle regret), **not a measurement**;
- the figures were DEV-set figures (4 windows), not EVAL figures.

## (b) Why they were replaced

They were **replaced by the first EVAL execution**, run on **2026-10-19 after
the G6 signature of the same day** — not edited in place, and not regenerated
under the old formula. The report now in this directory is:

- `generated: 2026-10-19T03:00:46Z`
- `content hash c143c24316ea990e79484ce24e918f07db1351e4ce0e6b24e13f1928226e4fb8`
  (same hash as the `set: eval` line of `variants.log`, `n_windows: 1`)
- `N = 1` — `eval-usd0pp-2025-01` OK, `eval-rseth-2026-04` SKIPPED (no archived
  series); `A2` absent on the scored window (declared substitution)
- superiority tests `NOT COMPUTED — N < 100 (B7 §b.3 cascade)`

The DEV pair of 17/10 is no longer shipped; the 17/10 entries remain in
`variants.log` as the historical record of that set. They must not be quoted.

## (c) The order of operations that makes the sequence honest

1. translation of the freeze package;
2. published sensitivity of `P(obligation)`, `p_s` and `r_capital`;
3. visible re-seal of `frozen/` (`scripts/freeze_sprint0.py`; `verify_frozen.py`
   COMPLIANT on the re-sealed manifests);
4. **G6 signature on 2026-10-19** — “re-sealed after translation + sensitivity,
   no parameter changed, **before first EVAL**”
   (`frozen/G6_FEUILLE_DE_SIGNATURE.md`);
5. **first EVAL execution at 2026-10-19T03:00:46Z**.

The signature therefore precedes the measurement, the measured code postdates
the aggregation fix, and no assumption was changed after seeing the result. The
G6 sheet states the rule explicitly: any modification after the first EVAL
requires a named re-signature and re-labelling.

## (d) What remains true

- **No superiority claim.** N = 1 is far below the G1 threshold N ≥ 100; the
  harness refuses to publish a single aggregate score, and
  `superiority_tests.json` records `NOT COMPUTED`.
- The scored window is a **DEV-parameter** run (`q = 100`, `p_ref = 1.0`,
  `k = 0`), declared in the report header itself.
- `eval-rseth-2026-04` is **SKIPPED**: the case has no archived market series,
  so it contributes no measurement.
- No figure of the 17/10 DEV files is valid today; nothing in them is quoted
  outside this historical note.

Gap register: `docs/SUBMISSION_SCOPE_AND_GAPS.md` G-16 (closed — superseded by
the 19/10 EVAL, see this note).
