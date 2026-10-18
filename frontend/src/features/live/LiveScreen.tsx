import { useEffect, useMemo, useState } from "react";
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
  fmtTime,
  truncate,
  verdictVariant,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea, Select } from "@/components/ui/input";
import { ScreenShell } from "@/components/ScreenShell";
import { SubstitutionBanner } from "@/components/SubstitutionBanner";

const TYPE_COLOR: Record<string, "info" | "violet" | "warn" | "ok" | "deny" | "neutral"> = {
  "agent.thought": "info",
  "agent.evidence": "violet",
  "agent.decision": "ok",
  "agent.critique": "warn",
  "agent.error": "deny",
  "run.status": "neutral",
  "market.tick": "ok",
};

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card className="min-w-[130px] flex-1">
      <CardContent className="px-3.5 py-2.5">
        <div className="text-[9.5px] font-semibold uppercase tracking-[0.16em] text-muted">
          {label}
        </div>
        <div className="mono mt-1 text-[17px] font-semibold tnum text-ink">{value}</div>
        {hint ? <div className="mono text-[9.5px] text-muted/80">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}

function EventRow({ event }: { event: RunEvent }) {
  const [open, setOpen] = useState(false);
  const payload = event.payload ?? {};
  const kind = String(payload.kind ?? "");
  const agent = String(payload.agent ?? payload.exchange ?? "system");
  const status = String(payload.status ?? "");
  const content = String(payload.content ?? "");
  const refs = (payload.refs as string[] | undefined) ?? [];
  const llm = (payload.llm ?? {}) as Record<string, unknown>;
  const validation = (payload.validation ?? {}) as Record<string, unknown>;
  const tokens = `${fmtCompact(payload.tokens_in ?? 0)}↑ ${fmtCompact(payload.tokens_out ?? 0)}↓`;
  return (
    <div className="border-b border-line/70 px-3 py-2 transition-colors hover:bg-surface2/50">
      <div className="flex flex-wrap items-center gap-2">
        <span className="mono w-16 shrink-0 text-[10px] tnum text-muted">
          #{String(payload.run_seq ?? event.seq)}
        </span>
        <Badge variant={TYPE_COLOR[event.type] ?? "neutral"}>{event.type}</Badge>
        {kind ? <Badge variant="neutral">{kind}</Badge> : null}
        {status ? (
          <Badge variant={verdictVariant(status)}>{status}</Badge>
        ) : null}
        <span className="mono text-[10.5px] text-muted">{agent}</span>
        <span className="mono text-[10px] tnum text-muted/80">{fmtTime(event.ts)}</span>
        <span className="flex-1" />
        {typeof payload.cost_usd === "number" && payload.cost_usd > 0 ? (
          <span className="mono text-[10px] tnum text-muted">
            ${fmtNumber(payload.cost_usd as number, 4)} · {tokens} · {String(payload.latency_ms ?? 0)}ms
          </span>
        ) : null}
      </div>
      {content ? (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="mono mt-1 w-full whitespace-pre-wrap break-words rounded bg-surface2/40 px-2 py-1.5 text-left text-[11px] leading-relaxed text-ink/90"
        >
          {open ? content : truncate(content, 260)}
        </button>
      ) : null}
      {refs.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {refs.map((ref) => (
            <Badge key={ref} variant="violet" title={ref}>
              {truncate(ref, 42)}
            </Badge>
          ))}
        </div>
      ) : null}
      {(payload.exchange as string | undefined) ? (
        <div className="mono mt-1 text-[10px] text-accent2">
          exchange: {String(payload.exchange)}
        </div>
      ) : null}
      {Object.keys(llm).length > 0 || validation.motif ? (
        <div className="mono mt-1 text-[9.5px] text-muted/80">
          {llm.provider ? (
            <span>
              LLM {String(llm.provider)}/{String(llm.model)} ({String(llm.model_version_pinned)})
              temp {String(llm.temperature)} ·{" "}
            </span>
          ) : null}
          {validation.provenance_ok === false ? (
            <span className="text-down">incomplete provenance · </span>
          ) : null}
          {validation.motif ? <span>{String(validation.motif)}</span> : null}
          {payload.prev_hash ? (
            <span> · prev {fmtHash(payload.prev_hash, 8)}</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default function LiveScreen() {
  const runsQuery = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const runs = useMemo(() => runsQuery.data?.runs ?? [], [runsQuery.data]);
  const [runId, setRunId] = useState<string>("");
  const liveStatus = useLiveStore((s) => s.status);
  const liveEvents = useLiveStore((s) => s.events);

  useEffect(() => {
    if (!runId && runs.length > 0) {
      const preferred = runs.find((r) => r.journals.orchestrator.present) ?? runs[0];
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
  const timeline: RunEvent[] =
    liveStatus === "live" && wsEvents.length > 0 ? wsEvents : (eventsQuery.data?.events ?? []);

  // Live budget = deduplicated WS stream of THIS run (a genuinely live run has
  // no outcome yet). See also ``budget`` below: never outcome + WS stream
  // summed — the stream replays the same journal.
  const liveBudget = useMemo(() => {
    const acc = { cost_usd: 0, tokens_in: 0, tokens_out: 0, llm_calls: 0, tool_calls: 0, wall_seconds: 0 };
    let firstMs = Number.POSITIVE_INFINITY;
    let lastMs = Number.NEGATIVE_INFINITY;
    for (const event of wsEvents) {
      const payload = event.payload ?? {};
      if (typeof payload.cost_usd === "number") acc.cost_usd += payload.cost_usd;
      if (typeof payload.tokens_in === "number") acc.tokens_in += payload.tokens_in;
      if (typeof payload.tokens_out === "number") acc.tokens_out += payload.tokens_out;
      if (payload.llm && typeof payload.llm === "object") acc.llm_calls += 1;
      if (event.type === "agent.evidence" && payload.kind === "TOOL_CALL") acc.tool_calls += 1;
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

  const bundle = bundleQuery.data;
  const spec = bundle?.spec ?? null;
  const outcome = (bundle?.outcome ?? {}) as Record<string, unknown>;
  const budgetUsed = (outcome.budget_used ?? {}) as Record<string, number>;
  const run = runs.find((r) => r.run_id === runId) ?? ({} as RunSummary);
  // Displayed budget = ONE source: the recorded outcome of the run when it
  // exists, otherwise the live WS stream. Never the sum of both: the stream
  // replays the same journal and would double the count on every loop.
  const budget = Object.keys(budgetUsed).length > 0 ? budgetUsed : liveBudget;
  // Budget ceilings = the run spec (real artefact: run.json "budget").
  const budgetLimits = (
    run.budget && Object.keys(run.budget).length > 0 ? run.budget : (spec?.budget ?? {})
  ) as Record<string, number>;
  const evidence = bundle?.exchanges?.find((x) => x.name.includes("evidence"));
  const critique = bundle?.exchanges?.find((x) => x.name.includes("critique"));
  const claims = (evidence?.data?.claims as Record<string, unknown>[] | undefined) ?? [];
  const criticReport = (critique?.data ?? {}) as Record<string, unknown>;
  const verify = verifyQuery.data?.agents?.orchestrator;
  const kinds = run.journals?.orchestrator?.kinds ?? {};

  return (
    <ScreenShell
      title="Live — agents running"
      subtitle={
        <span className="mono">
          hash-chained journal · hypotheses · referenced claims · critic verdicts
        </span>
      }
      actions={
        <>
          <Select
            className="w-72"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          >
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} ({r.mode || "?"} · {r.state || "?"})
              </option>
            ))}
          </Select>
          <Badge variant={liveStatus === "live" ? "live" : "warn"}>
            {liveStatus === "live" ? "WS stream live" : "REST polling fallback"}
          </Badge>
        </>
      }
    >
      <div className="mb-3">
        <SubstitutionBanner substitution={bundle?.substitution ?? run.substitution ?? null} />
      </div>

      <div className="mb-3 rounded-md border border-accent/25 bg-accent/[0.04] p-2.5">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-[9.5px] font-semibold uppercase tracking-[0.16em] text-muted">
            run budget — used / budget
          </span>
          <Badge variant="ok">≈ $0.04 per full run</Badge>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <Kpi
            label="llm calls"
            value={`${fmtNumber(budget.llm_calls ?? 0, 0)} / ${fmtNumber(budgetLimits.llm_calls ?? 0, 0)}`}
          />
          <Kpi
            label="tool calls"
            value={`${fmtNumber(budget.tool_calls ?? 0, 0)} / ${fmtNumber(budgetLimits.tool_calls ?? 0, 0)}`}
          />
          <Kpi
            label="wall time"
            value={`${fmtSeconds(budget.wall_seconds ?? 0)} / ${fmtSeconds(budgetLimits.wall_seconds ?? 0)}`}
            hint="run latency vs time budget"
          />
          <Kpi
            label="cost"
            value={`$${fmtNumber(budget.cost_usd ?? 0, 4)} / $${fmtNumber(budgetLimits.cost_usd ?? 0, 2)}`}
            hint="≈ $0.04 per full run (measured)"
          />
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2.5">
        <Kpi
          label="tokens in / out"
          value={`${fmtCompact(budget.tokens_in ?? 0)} / ${fmtCompact(budget.tokens_out ?? 0)}`}
          hint={`llm calls ${fmtCompact(budget.llm_calls ?? 0)}`}
        />
        <Kpi
          label="hypotheses"
          value={String(spec?.hypotheses?.length ?? run.hypotheses ?? 0)}
          hint={`gaps ${spec?.lacunes?.length ?? run.lacunes ?? 0}`}
        />
        <Kpi
          label="events"
          value={`${timeline.length}${eventsQuery.data?.total ? ` / ${eventsQuery.data.total}` : ""}`}
          hint={
            verify?.verified
              ? "chain verified ✓"
              : verify
                ? "chain NOT verified"
                : "verifying…"
          }
        />
        <Kpi
          label="run state"
          value={String(outcome.state ?? run.state ?? "—")}
          hint={String(outcome.stop_condition ?? run.stop_condition ?? "")}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>execution timeline</CardTitle>
            <div className="mono flex flex-wrap gap-1.5 text-[10px] text-muted">
              {Object.entries(kinds).map(([kind, count]) => (
                <Badge key={kind} variant="neutral">
                  {kind}: {count}
                </Badge>
              ))}
            </div>
          </CardHeader>
          <ScrollArea className="max-h-[560px] rounded-none border-0">
            {timeline.length === 0 ? (
              <div className="p-6 text-center text-muted">loading journal…</div>
            ) : (
              timeline.map((event) => (
                <EventRow
                  key={`${event.seq}-${String((event.payload ?? {}).journal_id ?? "")}`}
                  event={event}
                />
              ))
            )}
          </ScrollArea>
        </Card>

        <div className="flex flex-col gap-3">
          <Card>
            <CardHeader>
              <CardTitle>hypotheses & gaps</CardTitle>
              <Badge variant="info">{spec?.case_id ?? run.case_id ?? ""}</Badge>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {(spec?.hypotheses ?? []).map((hypothesis) => (
                <div key={hypothesis.id} className="rounded-md border border-line bg-surface2/40 p-2.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="info">{hypothesis.id}</Badge>
                    <Badge variant={verdictVariant(hypothesis.etat)}>{hypothesisLabel(hypothesis.etat)}</Badge>
                  </div>
                  <div className="mt-1.5 text-[11.5px] leading-relaxed text-ink/90">
                    {hypothesis.enonce}
                  </div>
                  <div className="mono mt-1 space-y-0.5 text-[10px] text-muted">
                    {Object.entries(hypothesis.criteres ?? {}).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-accent2">{key}</span>: {value}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {(spec?.lacunes ?? []).map((gap) => (
                <div key={gap.lacune_id} className="rounded-md border border-warn/25 bg-warn/5 p-2.5">
                  <Badge variant="warn">{gap.lacune_id}</Badge>
                  <div className="mt-1 text-[11px] text-ink/85">{gap.question}</div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>evidence packet</CardTitle>
              <Badge variant="violet">{evidence ? claims.length : 0} claims</Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              {evidence ? (
                <>
                  <div className="mono text-[10px] text-muted">
                    {String(evidence.data.packet_id ?? "")} · snapshot{" "}
                    {String(evidence.data.snapshot_ref ?? "")}
                  </div>
                  {claims.map((claim, index) => (
                    <div key={index} className="rounded border border-line bg-surface2/40 p-2">
                      <div className="text-[11px] text-ink/90">{String(claim.text)}</div>
                      <div className="mono mt-1 text-[9.5px] text-muted">
                        {String(claim.journal_id)}
                        {((claim.refs as string[]) ?? []).length > 0
                          ? ` · refs: ${((claim.refs as string[]).join(", "))}`
                          : " · no refs (unusable)"}
                      </div>
                    </div>
                  ))}
                  {evidence.data.summary ? (
                    <div className="mono text-[10px] text-muted">
                      {String(evidence.data.summary)}
                    </div>
                  ) : null}
                </>
              ) : (
                <div className="text-[11px] text-muted">no exchange packet for this run</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>critic & outcome</CardTitle>
              <Badge variant={verdictVariant(outcome.state ?? run.state)}>
                {String(outcome.state ?? run.state ?? "—")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="mono text-[10.5px] leading-relaxed text-ink/85">
                <div>
                  <span className="text-muted">stop: </span>
                  {String(outcome.stop_condition ?? "—")}
                </div>
                <div>
                  <span className="text-muted">reason: </span>
                  {String(outcome.motif ?? run.motif ?? "—")}
                </div>
                <div>
                  <span className="text-muted">critic verdict: </span>
                  {String(outcome.critique_verdict || criticReport.$status || "—")}
                </div>
              </div>
              {(outcome.non_recherche as string[] | undefined)?.length ? (
                <div>
                  <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">
                    not searched
                  </div>
                  {(outcome.non_recherche as string[]).map((line, index) => (
                    <div key={index} className="mt-1 text-[10.5px] leading-relaxed text-warn/90">
                      • {line}
                    </div>
                  ))}
                </div>
              ) : null}
              {(criticReport.errors as string[] | undefined)?.length ? (
                <div>
                  <div className="text-[9.5px] uppercase tracking-[0.14em] text-down">critic errors</div>
                  {(criticReport.errors as string[]).map((line, index) => (
                    <div key={index} className="mono mt-1 text-[10px] text-down/90">
                      {truncate(line, 180)}
                    </div>
                  ))}
                </div>
              ) : null}
              {verify ? (
                <div className="mono rounded border border-line bg-surface2/40 p-2 text-[10px]">
                  <div className={verify.verified ? "text-up" : "text-down"}>
                    journal chain: {verify.verified ? "VERIFIED" : "DRIFT"}
                  </div>
                  <div className="mt-1 text-muted">
                    recomputed head {fmtHash(verify.recomputed_head, 12)}
                  </div>
                  <div className="text-muted">
                    recorded head {fmtHash(verify.recorded_head, 12)}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {(bundle?.tool_calls ?? []).length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>tool calls (store)</CardTitle>
                <Badge variant="neutral">{bundle!.tool_calls.length}</Badge>
              </CardHeader>
              <ScrollArea className="max-h-52 rounded-none border-0">
                {bundle!.tool_calls.map((call, index) => (
                  <div key={index} className="mono border-b border-line/60 px-3 py-1.5 text-[10px]">
                    <div className="text-accent">{String(call.tool ?? call.name ?? "call")}</div>
                    <div className="text-muted">{truncate(JSON.stringify(call.args ?? call), 140)}</div>
                  </div>
                ))}
              </ScrollArea>
            </Card>
          ) : null}
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
