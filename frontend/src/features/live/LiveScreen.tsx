import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useLiveStore } from "@/lib/store";
import { subscribeRun } from "@/lib/live-bridge";
import { api } from "@/lib/api";
import type { RunEvent, RunSummary } from "@/lib/types";
import {
  fmtCompact,
  fmtHash,
  fmtNumber,
  fmtSeconds,
  fmtStamp,
  fmtTime,
  hypothesisVariant,
  truncate,
  verdictVariant,
} from "@/lib/format";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { Flash } from "@/components/ui/bits";
import { ScreenShell } from "@/components/ScreenShell";
import { SubstitutionBanner } from "@/components/SubstitutionBanner";


function Row({ label, value }: { label: string; value: string }) {
  if (!value || value === "—") return null;
  return (
    <div className="flex gap-2">
      <dt className="w-28 shrink-0 text-code text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-code text-ink">{value}</dd>
    </div>
  );
}

function BudgetCell({
  label,
  value,
  ceiling,
  flashValue,
}: {
  label: string;
  value: string;
  ceiling?: string;
  flashValue: unknown;
}) {
  return (
    <div className="bg-surface px-4 py-3">
      <div className="text-meta text-muted">{label}</div>
      <div className="mt-0.5 flex items-baseline gap-1.5">
        <Flash
          value={flashValue}
          className="text-kpi font-semibold tnum leading-[30px] text-ink"
        >
          {value}
        </Flash>
        {ceiling ? <span className="text-meta tnum text-muted">{ceiling}</span> : null}
      </div>
    </div>
  );
}

function EventRow({ event, fresh }: { event: RunEvent; fresh: boolean }) {
  const [open, setOpen] = useState(false);
  const payload = event.payload ?? {};
  const kind = String(payload.kind ?? "");
  const agent = String(payload.agent ?? payload.exchange ?? "system");
  const status = String(payload.status ?? "");
  const content = String(payload.content ?? "");
  const refs = (payload.refs as string[] | undefined) ?? [];
  const llm = (payload.llm ?? {}) as Record<string, unknown>;
  const validation = (payload.validation ?? {}) as Record<string, unknown>;
  return (
    <div
      className={cn(
        "border-b border-line px-4 py-2.5 transition-colors duration-100 hover:bg-surface2/60",
        fresh && "row-in",
      )}
    >
      {/* Time UTC (92px) · Agent (96px) · Event (140px) — a recurring pattern */}
      <div className="flex items-center gap-2">
        <span className="w-[92px] shrink-0 font-mono text-code tnum text-muted">
          {fmtTime(event.ts)}
        </span>
        <span className="w-[96px] shrink-0 truncate font-mono text-code text-ink">
          {agent}
        </span>
        <span className="w-[140px] shrink-0 truncate font-mono text-code font-medium text-ink">
          {event.type}
        </span>
        {kind ? <Badge variant="neutral">{kind}</Badge> : null}
        {status ? <Badge variant={verdictVariant(status)}>{status}</Badge> : null}
        <span className="ml-auto shrink-0 font-mono text-code tnum text-muted">
          {typeof payload.cost_usd === "number" && payload.cost_usd > 0
            ? `$${fmtNumber(payload.cost_usd as number, 4)} · ${String(payload.latency_ms ?? 0)} ms`
            : ""}
        </span>
      </div>
      {content ? (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="mt-1.5 block w-full whitespace-pre-wrap break-words text-left text-body leading-5 text-ink"
          aria-expanded={open}
        >
          <span className={open ? "" : "line-clamp-2"}>{content}</span>
          <span className="mt-0.5 block text-meta font-medium text-muted">
            {open ? "Collapse" : "Expand"}
          </span>
        </button>
      ) : null}
      {refs.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-code text-muted select-text">
          {refs.map((ref) => (
            <span key={ref}>{ref}</span>
          ))}
        </div>
      ) : null}
      {open ? (
        <div className="mt-1 space-y-0.5 border-t border-line pt-1 font-mono text-code text-muted">
          <div>
            seq {String(payload.run_seq ?? event.seq)}
            {payload.prev_hash ? ` · prev ${fmtHash(payload.prev_hash, 8)}` : ""}
          </div>
          {llm.provider ? (
            <div>
              LLM {String(llm.provider)}/{String(llm.model)} (
              {String(llm.model_version_pinned)}) temp {String(llm.temperature)}
            </div>
          ) : null}
          {validation.provenance_ok === false ? (
            <div className="text-ink">incomplete provenance</div>
          ) : null}
          {validation.motif ? <div>{String(validation.motif)}</div> : null}
        </div>
      ) : null}
    </div>
  );
}

export default function LiveScreen() {
  const runsQuery = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const runs = useMemo(() => runsQuery.data?.runs ?? [], [runsQuery.data]);
  // Selection lives in the URL (?run=) via router primitives, independent of
  // the WS transport: reloads, shared links AND cross-route navigation keep
  // the same run (Astra-4 P0-3 / Astra-5 continuité).
  const [searchParams, setSearchParams] = useSearchParams();
  const [runId, setRunIdState] = useState<string>(
    () => searchParams.get("run") ?? "",
  );
  const setRunId = (next: string) => {
    setRunIdState(next);
    const params = new URLSearchParams(window.location.search);
    if (next) params.set("run", next);
    else params.delete("run");
    setSearchParams(params, { replace: true });
  };
  const liveStatus = useLiveStore((s) => s.status);
  const liveEvents = useLiveStore((s) => s.events);
  const journalRef = useRef<HTMLDivElement | null>(null);
  // Rows painted after this count are "new" (they get the one-shot row-in).
  const initialCountRef = useRef<number | null>(null);

  useEffect(() => {
    if (!runId && runs.length > 0) {
      // The scenario-linked run first (its disclosure is the declared one),
      // then any run with an orchestrator journal.
      const preferred =
        runs.find((r) => r.substitution?.declared) ??
        runs.find((r) => r.journals.orchestrator.present) ??
        runs[0];
      setRunId(preferred.run_id);
    }
  }, [runs, runId]);

  useEffect(() => {
    if (runId) subscribeRun(runId);
  }, [runId]);

  const bundleQuery = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId),
    enabled: Boolean(runId),
  });
  const verifyQuery = useQuery({
    queryKey: ["run-verify", runId],
    queryFn: () => api.runVerify(runId),
    enabled: Boolean(runId),
  });
  const eventsQuery = useQuery({
    queryKey: ["run-events", runId],
    queryFn: () => api.runEvents(runId, 0, 500),
    enabled: Boolean(runId),
    refetchInterval: liveStatus === "live" ? false : 10_000,
  });

  // WS stream for this run (REST fallback when the socket is down). The hub
  // loops the recorded run for the demo: only one occurrence per event
  // (run_seq/journal_id) is kept, otherwise the timeline and the counters
  // would repeat on every loop.
  const wsEvents = useMemo(() => {
    const seen = new Set<string>();
    const out: RunEvent[] = [];
    for (const e of liveEvents) {
      if (e.run_id !== runId) continue;
      const payload = e.payload ?? {};
      const key = String(payload.journal_id ?? payload.run_seq ?? e.seq);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        seq: Number(payload.run_seq ?? e.seq),
        type: e.type,
        run_id: e.run_id,
        ts: e.ts,
        payload,
      });
    }
    return out;
  }, [liveEvents, runId]);
  // REST journal ∪ deduplicated WS stream: the recorded run is complete from
  // the first paint (no "1 of N" while the hub streams), live events append.
  const timeline: RunEvent[] = useMemo(() => {
    const base = eventsQuery.data?.events ?? [];
    if (wsEvents.length === 0) return base;
    const key = (event: RunEvent) =>
      String((event.payload ?? {}).journal_id ?? (event.payload ?? {}).run_seq ?? event.seq);
    const seen = new Set(base.map(key));
    const merged = [...base];
    for (const event of wsEvents) {
      const k = key(event);
      if (seen.has(k)) continue;
      seen.add(k);
      merged.push(event);
    }
    return merged.sort((a, b) => a.seq - b.seq);
  }, [eventsQuery.data, wsEvents]);

  // Live budget = deduplicated WS stream of THIS run (a genuinely live run has
  // no outcome yet). Never outcome + WS stream summed — the stream replays the
  // same journal and would double the count on every loop.
  const liveBudget = useMemo(() => {
    const acc = {
      cost_usd: 0,
      tokens_in: 0,
      tokens_out: 0,
      llm_calls: 0,
      tool_calls: 0,
      wall_seconds: 0,
    };
    let firstMs = Number.POSITIVE_INFINITY;
    let lastMs = Number.NEGATIVE_INFINITY;
    for (const event of wsEvents) {
      const payload = event.payload ?? {};
      if (typeof payload.cost_usd === "number") acc.cost_usd += payload.cost_usd;
      if (typeof payload.tokens_in === "number") acc.tokens_in += payload.tokens_in;
      if (typeof payload.tokens_out === "number") acc.tokens_out += payload.tokens_out;
      if (payload.llm && typeof payload.llm === "object") acc.llm_calls += 1;
      if (event.type === "agent.evidence" && payload.kind === "TOOL_CALL")
        acc.tool_calls += 1;
      const tsMs = Date.parse(String(event.ts ?? ""));
      if (Number.isFinite(tsMs)) {
        firstMs = Math.min(firstMs, tsMs);
        lastMs = Math.max(lastMs, tsMs);
      }
    }
    if (Number.isFinite(firstMs) && Number.isFinite(lastMs) && lastMs > firstMs) {
      acc.wall_seconds = (lastMs - firstMs) / 1000;
    }
    return acc;
  }, [wsEvents]);

  useEffect(() => {
    if (timeline.length > 0 && initialCountRef.current === null) {
      initialCountRef.current = timeline.length;
    }
  }, [timeline.length]);

  const bundle = bundleQuery.data;
  const spec = bundle?.spec ?? null;
  const outcome = (bundle?.outcome ?? {}) as Record<string, unknown>;
  const runOutcome = (bundle?.run_outcome ?? {}) as Record<string, unknown>;
  const budgetUsed = (outcome.budget_used ?? {}) as Record<string, number>;
  const run = runs.find((r) => r.run_id === runId) ?? ({} as RunSummary);
  // Displayed budget = ONE source: the recorded outcome of the run when it
  // exists, otherwise the live WS stream. Never the sum of both.
  const hasOutcome = Object.keys(budgetUsed).length > 0;
  const budget = hasOutcome ? budgetUsed : liveBudget;
  // Budget ceilings = the run spec (real artefact: run.json "budget").
  const budgetLimits = (
    run.budget && Object.keys(run.budget).length > 0 ? run.budget : (spec?.budget ?? {})
  ) as Record<string, number>;
  // Before any source has spoken, show "—" — a fabricated 0/0 is a lie
  // about the run (Astra-4 P1-1).
  const budgetKnown = hasOutcome || wsEvents.length > 0;
  const evidence = bundle?.exchanges?.find((x) => x.name.includes("evidence"));
  const critique = bundle?.exchanges?.find((x) => x.name.includes("critique"));
  const claims = (evidence?.data?.claims as Record<string, unknown>[] | undefined) ?? [];
  const criticReport = (critique?.data ?? {}) as Record<string, unknown>;
  const critiqueBlock = (runOutcome.critique ?? {}) as Record<string, unknown>;
  // Findings are OBJECTS ({enonce, gravite, refs, test_discriminant, type}):
  // never cast to string[] — that rendered "[object Object]" (Astra P0-2).
  // Read path: run_outcome.critique.findings first, then exchange fallbacks.
  const rawFindings: unknown[] =
    (critiqueBlock.findings as unknown[] | undefined) ??
    (runOutcome.findings as unknown[] | undefined) ??
    (criticReport.findings as unknown[] | undefined) ??
    (criticReport.errors as unknown[] | undefined) ??
    [];
  const escalation = String(runOutcome.escalation ?? outcome.escalation ?? "");
  type FindingShape = {
    enonce?: string;
    gravite?: string;
    refs?: string[];
    test_discriminant?: string;
    type?: string;
  };
  const blockingFindings = rawFindings
    .map((item) => (typeof item === "object" && item !== null ? (item as FindingShape) : {}))
    .filter((item) => item.gravite === "BLOQUANT" && item.enonce);
  const criticVerdict = String(
    critiqueBlock.verdict_lecture ??
      outcome.critique_verdict ??
      criticReport.$status ??
      "—",
  );
  const verify = verifyQuery.data?.agents?.orchestrator;
  const kinds = run.journals?.orchestrator?.kinds ?? {};
  const state = String(outcome.state ?? run.state ?? "—");
  const stopCondition = String(outcome.stop_condition ?? run.stop_condition ?? "");

  const scrollLatest = () => {
    const el = journalRef.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollTo({ top: el.scrollHeight, behavior: reduced ? "auto" : "smooth" });
  };

  return (
    <ScreenShell
      title="Agent activity"
      subtitle="Recorded agent run · hash-chained journal · referenced claims · critic verdicts"
      context={[
        { label: "Case", value: run.case_id ?? "—" },
        { label: "Run", value: runId || "—" },
        { label: "Evidence", value: "Recorded run" },
      ]}
      actions={
        <>
          <div className="flex flex-col gap-1">
            <Label htmlFor="run-select">Run</Label>
            <Select
              id="run-select"
              className="w-80"
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
            >
              {runs.map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id} ({r.mode || "?"} · {r.state || "?"})
                </option>
              ))}
            </Select>
          </div>
          <Badge variant="neutral">Mode: {String(run.mode || "replay")}</Badge>
        </>
      }
    >
      <div className="space-y-4">
        {runsQuery.isError ? (
          <div className="border border-line bg-surface px-4 py-4 text-center">
            <div className="text-body text-ink">
              {runs.length === 0
                ? "Runs unavailable — the API did not answer."
                : `Refresh failed — showing runs loaded at ${fmtStamp(runsQuery.dataUpdatedAt)}.`}
            </div>
            <Button
              variant="secondary"
              className="mt-2"
              onClick={() => runsQuery.refetch()}
            >
              Retry
            </Button>
          </div>
        ) : runsQuery.isFetching && runs.length === 0 ? (
          <div className="border border-line bg-surface px-4 py-3 text-center text-meta text-muted">
            Loading runs…
          </div>
        ) : runsQuery.data && runs.length === 0 ? (
          <div className="border border-line bg-surface px-4 py-4 text-center">
            <div className="text-body text-ink">No run is available in this view.</div>
            <Button
              variant="secondary"
              className="mt-2"
              onClick={() => runsQuery.refetch()}
            >
              Refresh runs
            </Button>
          </div>
        ) : null}
        <SubstitutionBanner substitution={bundle?.substitution ?? run.substitution ?? null} />

        {/* Run budget: ONE band, four cells, used / ceiling (§4.5). */}
        <div className="border border-line bg-surface">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-2">
            <span className="text-section-title font-semibold">Run budget</span>
            <span className="text-meta text-muted">
              {hasOutcome ? "Recorded run totals" : "Live stream totals"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-px bg-line min-[1100px]:grid-cols-4">
            <BudgetCell
              label="LLM calls"
              flashValue={budget.llm_calls}
              value={
                budgetKnown && budget.llm_calls !== undefined
                  ? fmtNumber(budget.llm_calls, 0)
                  : "—"
              }
              ceiling={
                budgetLimits.llm_calls !== undefined
                  ? `/ ${fmtNumber(budgetLimits.llm_calls, 0)}`
                  : undefined
              }
            />
            <BudgetCell
              label="Tool calls"
              flashValue={budget.tool_calls}
              value={
                budgetKnown && budget.tool_calls !== undefined
                  ? fmtNumber(budget.tool_calls, 0)
                  : "—"
              }
              ceiling={
                budgetLimits.tool_calls !== undefined
                  ? `/ ${fmtNumber(budgetLimits.tool_calls, 0)}`
                  : undefined
              }
            />
            <BudgetCell
              label="Elapsed time"
              flashValue={budget.wall_seconds}
              value={
                budgetKnown && budget.wall_seconds !== undefined
                  ? fmtNumber(budget.wall_seconds, 1)
                  : "—"
              }
              ceiling={
                budgetLimits.wall_seconds !== undefined
                  ? `/ ${fmtNumber(budgetLimits.wall_seconds, 0)} s`
                  : undefined
              }
            />
            <BudgetCell
              label="Recorded cost"
              flashValue={budget.cost_usd}
              value={
                budgetKnown && budget.cost_usd !== undefined
                  ? `$${fmtNumber(budget.cost_usd, 4)}`
                  : "—"
              }
              ceiling={
                budgetLimits.cost_usd !== undefined
                  ? `/ $${fmtNumber(budgetLimits.cost_usd, 2)}`
                  : undefined
              }
            />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 min-[1100px]:grid-cols-[minmax(0,1fr)_320px]">
          <Card>
            <CardHeader>
              <CardTitle>Agent journal</CardTitle>
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant="neutral">
                  Showing {timeline.length}
                  {typeof eventsQuery.data?.total === "number" &&
                  timeline.length <= eventsQuery.data.total
                    ? ` of ${eventsQuery.data.total}`
                    : ""}{" "}
                  events
                </Badge>
                <Button variant="secondary" size="sm" onClick={scrollLatest}>
                  Latest event
                </Button>
              </div>
            </CardHeader>
            {eventsQuery.isError && eventsQuery.data ? (
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-surface2 px-4 py-2">
                <span className="text-meta text-ink">
                  Refresh failed — journal loaded at {fmtStamp(eventsQuery.dataUpdatedAt)}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => eventsQuery.refetch()}
                >
                  Retry
                </Button>
              </div>
            ) : null}
            {!eventsQuery.data &&
            (eventsQuery.isFetching || eventsQuery.isError) &&
            timeline.length > 0 ? (
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-surface2 px-4 py-2">
                <span
                  className={
                    eventsQuery.isError ? "text-meta text-ink" : "text-meta text-muted"
                  }
                >
                  {eventsQuery.isError
                    ? "Journal unavailable — showing partial live events."
                    : "Partial live events shown — the archived journal is still loading…"}
                </span>
                {eventsQuery.isError ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => eventsQuery.refetch()}
                  >
                    Retry
                  </Button>
                ) : null}
              </div>
            ) : null}
            <div ref={journalRef} className="max-h-[560px] overflow-auto">
              {timeline.length === 0 ? (
                !runId ? (
                  <div className="px-4 py-6 text-center text-meta text-muted">
                    No run selected — its journal cannot be loaded.
                  </div>
                ) : eventsQuery.isError ? (
                  <div className="px-4 py-6 text-center">
                    <div className="text-body text-ink">
                      Journal unavailable — the API did not answer.
                    </div>
                    <Button
                      variant="secondary"
                      className="mt-2"
                      onClick={() => eventsQuery.refetch()}
                    >
                      Retry
                    </Button>
                  </div>
                ) : !eventsQuery.data && eventsQuery.isFetching ? (
                  <div className="px-4 py-6 text-center text-meta text-muted">
                    Loading journal…
                  </div>
                ) : (
                  <div className="px-4 py-6 text-center text-meta text-muted">
                    No journal event for this run yet.
                  </div>
                )
              ) : (
                timeline.map((event, index) => (
                  <EventRow
                    key={`${event.seq}-${String((event.payload ?? {}).journal_id ?? "")}`}
                    event={event}
                    fresh={initialCountRef.current !== null && index >= initialCountRef.current}
                  />
                ))
              )}
            </div>
          </Card>

          <div className="flex flex-col gap-4">
            {/* Result first: state the outcome before details (§4.5). */}
            <Card>
              <CardHeader>
                <CardTitle>Agent outcome</CardTitle>
                <Badge variant={verdictVariant(state)}>{state}</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {bundleQuery.isError ? (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-meta text-ink">
                      {bundleQuery.data
                        ? `Refresh failed — run dossier loaded at ${fmtStamp(bundleQuery.dataUpdatedAt)}`
                        : "Run dossier unavailable — the API did not answer."}
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => bundleQuery.refetch()}
                    >
                      Retry
                    </Button>
                  </div>
                ) : !bundleQuery.data && bundleQuery.isFetching ? (
                  <div className="text-meta text-muted">Loading run dossier…</div>
                ) : null}
                {state === "ABORTED" && stopCondition ? (
                  <div className="text-[13px] font-semibold leading-[18px] text-ink">
                    Run stopped — {stopCondition}
                  </div>
                ) : null}
                <dl className="space-y-1">
                  <Row label="Run state" value={state} />
                  <Row label="Stop" value={stopCondition} />
                  <Row label="Reason" value={String(outcome.motif ?? run.motif ?? "")} />
                  <Row label="Critic verdict" value={criticVerdict} />
                  <Row label="Escalation" value={escalation} />
                </dl>
                {blockingFindings.length > 0 ? (
                  <div>
                    <div className="text-meta text-muted">Blocking objections</div>
                    {blockingFindings.map((finding, index) => (
                      <div key={index} className="mt-1 break-words text-body leading-5 text-ink">
                        {finding.enonce}
                      </div>
                    ))}
                    <div className="mt-1 text-meta text-muted">
                      Full findings in Critique report · original record in French (FR).
                    </div>
                  </div>
                ) : null}
                {(outcome.non_recherche as string[] | undefined)?.length ? (
                  <div>
                    <div className="text-meta text-muted">Not searched</div>
                    {(outcome.non_recherche as string[]).map((line, index) => (
                      <div key={index} className="mt-1 text-meta leading-4 text-ink">
                        • {line}
                      </div>
                    ))}
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Initial hypotheses</CardTitle>
                <Badge variant="info">{spec?.case_id ?? run.case_id ?? ""}</Badge>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {(spec?.hypotheses ?? []).map((hypothesis) => (
                  <div key={hypothesis.id} className="border border-line px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="info">{hypothesis.id}</Badge>
                      <Badge variant={hypothesisVariant(hypothesis.etat)}>
                        {hypothesisLabel(hypothesis.etat)}
                      </Badge>
                    </div>
                    <div className="mt-1.5 text-body leading-5 text-ink">
                      {hypothesis.enonce}
                    </div>
                    <div className="mt-1 space-y-0.5 font-mono text-code text-muted">
                      {Object.entries(hypothesis.criteres ?? {}).map(([key, value]) => (
                        <div key={key}>
                          <span className="font-medium text-ink">{key}</span>: {value}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {(spec?.hypotheses ?? []).length === 0 ? (
                  <div className="text-meta text-muted">No hypothesis in this spec.</div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Missing evidence</CardTitle>
                <Badge variant="warn">{spec?.lacunes?.length ?? run.lacunes ?? 0}</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {(spec?.lacunes ?? []).map((gap) => (
                  <div key={gap.lacune_id} className="border border-line px-3 py-2">
                    <Badge variant="warn">{gap.lacune_id}</Badge>
                    <div className="mt-1 text-body leading-5 text-ink">{gap.question}</div>
                  </div>
                ))}
                {(spec?.lacunes ?? []).length === 0 ? (
                  <div className="text-meta text-muted">No missing evidence declared.</div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Evidence packet</CardTitle>
                <Badge variant="neutral">{evidence ? claims.length : 0} claims</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {evidence ? (
                  <>
                    <div className="font-mono text-code text-muted">
                      {String(evidence.data.packet_id ?? "")} · snapshot{" "}
                      {String(evidence.data.snapshot_ref ?? "")}
                    </div>
                    <details>
                      <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                        Show claims ({claims.length})
                      </summary>
                      <div className="mt-2 space-y-2">
                        {claims.map((claim, index) => (
                          <div key={index} className="border border-line px-3 py-2">
                            <div className="text-body leading-5 text-ink">
                              {String(claim.text)}
                            </div>
                            <div className="mt-1 font-mono text-code text-muted">
                              {String(claim.journal_id)}
                              {((claim.refs as string[]) ?? []).length > 0
                                ? ` · refs: ${((claim.refs as string[]).join(", "))}`
                                : " · no refs (unusable)"}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                    {evidence.data.summary ? (
                      <div className="font-mono text-code text-muted">
                        {String(evidence.data.summary)}
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="text-meta text-muted">
                    No exchange packet for this run.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Critique report</CardTitle>
                <Badge variant={criticVerdict ? verdictVariant(criticVerdict) : "neutral"}>
                  {criticVerdict}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {rawFindings.length > 0 ? (
                  <div>
                    <div className="text-meta text-muted">Findings</div>
                    {rawFindings.map((item, index) => {
                      const object =
                        typeof item === "object" && item !== null
                          ? (item as {
                              enonce?: string;
                              gravite?: string;
                              refs?: string[];
                              test_discriminant?: string;
                              type?: string;
                            })
                          : {};
                      const text =
                        typeof item === "string" ? item : String(object.enonce ?? "");
                      return (
                        <div key={index} className="mt-1.5 border border-line px-3 py-2">
                          <div className="flex flex-wrap items-center gap-1.5">
                            {object.type ? <Badge variant="neutral">{object.type}</Badge> : null}
                            {object.gravite ? (
                              <Badge variant={object.gravite === "BLOQUANT" ? "deny" : "warn"}>
                                {object.gravite}
                              </Badge>
                            ) : null}
                          </div>
                          <div className="mt-1 break-words text-body leading-5 text-ink">
                            {text}
                          </div>
                          {(object.refs ?? []).length > 0 ? (
                            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-code text-muted select-text">
                              {(object.refs ?? []).map((ref) => (
                                <span key={ref}>{ref}</span>
                              ))}
                            </div>
                          ) : null}
                          {object.test_discriminant ? (
                            <details className="mt-1">
                              <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                                Discriminating test
                              </summary>
                              <div className="mt-0.5 break-words text-body leading-5 text-ink">
                                {object.test_discriminant}
                              </div>
                            </details>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-meta text-muted">No finding recorded.</div>
                )}
                {verify ? (
                  <div className="border border-line bg-surface2 px-3 py-2 font-mono text-code">
                    <div className="text-ink">
                      Journal chain: {verify.verified ? "VERIFIED" : "DRIFT"}
                    </div>
                    <div className="mt-0.5 text-muted">
                      recomputed head {fmtHash(verify.recomputed_head, 12)}
                    </div>
                    <div className="text-muted">
                      recorded head {fmtHash(verify.recorded_head, 12)}
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Run details</CardTitle>
                <Badge variant="neutral">{String(run.mode || "replay")}</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                {Object.keys(kinds).length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(kinds).map(([kind, count]) => (
                      <Badge key={kind} variant="neutral">
                        {kind}: {count}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                <dl className="space-y-1">
                  <Row
                    label="Source"
                    value={hasOutcome ? "run outcome (recorded)" : "live event stream"}
                  />
                  <Row
                    label="Tokens"
                    value={
                      budgetKnown
                        ? `${budget.tokens_in !== undefined ? fmtCompact(budget.tokens_in) : "—"} in · ${budget.tokens_out !== undefined ? fmtCompact(budget.tokens_out) : "—"} out`
                        : ""
                    }
                  />
                  <Row label="Events" value={`${eventsQuery.data?.total ?? timeline.length}`} />
                  <Row label="Hypotheses" value={`${spec?.hypotheses?.length ?? run.hypotheses ?? 0}`} />
                  <Row label="Missing ev." value={`${spec?.lacunes?.length ?? run.lacunes ?? 0}`} />
                  <Row label="Created" value={String(run.created_at ?? "")} />
                  <Row label="Schema" value={String(run.schema ?? "")} />
                </dl>
              </CardContent>
            </Card>

            {(bundle?.tool_calls ?? []).length > 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>Tool records</CardTitle>
                  <Badge variant="neutral">{bundle!.tool_calls.length}</Badge>
                </CardHeader>
                <CardContent>
                  <details>
                    <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                      Show recorded tool calls
                    </summary>
                    <div className="mt-2 max-h-52 overflow-auto border border-line">
                      {bundle!.tool_calls.map((call, index) => (
                        <div
                          key={index}
                          className="border-b border-line px-3 py-1.5 font-mono text-code last:border-b-0"
                        >
                          <div className="text-ink">
                            {String(call.tool ?? call.name ?? "call")}
                          </div>
                          <div className="text-muted">
                            {truncate(JSON.stringify(call.args ?? call), 140)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                </CardContent>
              </Card>
            ) : null}
          </div>
        </div>
      </div>
    </ScreenShell>
  );
}

function hypothesisLabel(etat: string): string {
  const map: Record<string, string> = {
    UNDER_TEST: "under test",
    SUPPORTED: "supported",
    REFUTED: "refuted",
    INCONCLUSIVE: "inconclusive",
  };
  return map[etat] ?? etat;
}
