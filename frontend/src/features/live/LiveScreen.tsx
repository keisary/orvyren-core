import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLiveStore } from "@/lib/store";
import { subscribeRun } from "@/lib/live-bridge";
import { api } from "@/lib/api";
import type { JournalEntry, RunEvent, RunSummary } from "@/lib/types";
import {
  fmtCompact,
  fmtHash,
  fmtNumber,
  fmtTime,
  truncate,
  verdictVariant,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea, Select } from "@/components/ui/input";
import { ScreenShell } from "@/components/ScreenShell";

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
  const agent = String(payload.agent ?? payload.exchange ?? "système");
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
          échange : {String(payload.exchange)}
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
            <span className="text-down">provenance incomplète · </span>
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
  const liveBudget = useLiveStore((s) => s.budget);

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

  // Flux WS pour ce run (fallback REST quand le socket est coupé).
  const wsEvents = useMemo(
    () =>
      liveEvents
        .filter((e) => e.run_id === runId)
        .map((e) => ({
          seq: Number(e.payload?.run_seq ?? e.seq),
          type: e.type,
          run_id: e.run_id,
          ts: e.ts,
          payload: e.payload,
        })) as RunEvent[],
    [liveEvents, runId],
  );
  const timeline: RunEvent[] =
    liveStatus === "live" && wsEvents.length > 0 ? wsEvents : (eventsQuery.data?.events ?? []);

  const bundle = bundleQuery.data;
  const spec = bundle?.spec ?? null;
  const outcome = (bundle?.outcome ?? {}) as Record<string, unknown>;
  const budgetUsed = (outcome.budget_used ?? {}) as Record<string, number>;
  const run = runs.find((r) => r.run_id === runId) ?? ({} as RunSummary);
  const evidence = bundle?.exchanges?.find((x) => x.name.includes("evidence"));
  const critique = bundle?.exchanges?.find((x) => x.name.includes("critique"));
  const claims = (evidence?.data?.claims as Record<string, unknown>[] | undefined) ?? [];
  const criticReport = (critique?.data ?? {}) as Record<string, unknown>;
  const verify = verifyQuery.data?.agents?.orchestrator;
  const kinds = run.journals?.orchestrator?.kinds ?? {};

  return (
    <ScreenShell
      title="Live — agents en cours"
      subtitle={
        <span className="mono">
          journal chaîné par hash · hypothèses · claims référencés · verdicts du critique
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
            {liveStatus === "live" ? "flux WS actif" : "repli polling REST"}
          </Badge>
        </>
      }
    >
      <div className="mb-3 flex flex-wrap gap-2.5">
        <Kpi
          label="coût cumulé"
          value={`$${fmtNumber((budgetUsed.cost_usd ?? 0) + liveBudget.cost_usd, 4)}`}
          hint={`budget ${fmtNumber(run.budget?.cost_usd ?? spec?.budget?.cost_usd ?? 0, 2)} $`}
        />
        <Kpi
          label="tokens in / out"
          value={`${fmtCompact((budgetUsed.tokens_in ?? 0) + liveBudget.tokens_in)} / ${fmtCompact(
            (budgetUsed.tokens_out ?? 0) + liveBudget.tokens_out,
          )}`}
          hint={`appels LLM ${fmtCompact((budgetUsed.llm_calls ?? 0) + liveBudget.llm_calls)}`}
        />
        <Kpi
          label="appels d'outils"
          value={fmtCompact((budgetUsed.tool_calls ?? 0) + liveBudget.tool_calls)}
          hint={`journal ${run.journals?.orchestrator?.lines ?? 0} lignes`}
        />
        <Kpi
          label="hypothèses"
          value={String(spec?.hypotheses?.length ?? run.hypotheses ?? 0)}
          hint={`lacunes ${spec?.lacunes?.length ?? run.lacunes ?? 0}`}
        />
        <Kpi
          label="événements"
          value={`${timeline.length}${eventsQuery.data?.total ? ` / ${eventsQuery.data.total}` : ""}`}
          hint={
            verify?.verified
              ? "chaîne vérifiée ✓"
              : verify
                ? "chaîne NON vérifiée"
                : "vérification…"
          }
        />
        <Kpi
          label="état run"
          value={String(outcome.state ?? run.state ?? "—")}
          hint={String(outcome.stop_condition ?? run.stop_condition ?? "")}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>timeline d'exécution</CardTitle>
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
              <div className="p-6 text-center text-muted">chargement du journal…</div>
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
              <CardTitle>hypothèses & lacunes</CardTitle>
              <Badge variant="info">{spec?.case_id ?? run.case_id ?? ""}</Badge>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {(spec?.hypotheses ?? []).map((hypothesis) => (
                <div key={hypothesis.id} className="rounded-md border border-line bg-surface2/40 p-2.5">
                  <div className="flex items-center gap-2">
                    <Badge variant="info">{hypothesis.id}</Badge>
                    <Badge variant={verdictVariant(hypothesis.etat)}>{hypotheseLabel(hypothesis.etat)}</Badge>
                  </div>
                  <div className="mt-1.5 text-[11.5px] leading-relaxed text-ink/90">
                    {hypothesis.enonce}
                  </div>
                  <div className="mono mt-1 space-y-0.5 text-[10px] text-muted">
                    {Object.entries(hypothesis.criteres ?? {}).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-accent2">{key}</span> : {value}
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
              <CardTitle>paquet de preuves</CardTitle>
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
                          : " · sans refs (non utilisable)"}
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
                <div className="text-[11px] text-muted">aucun paquet d'échanges pour ce run</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>critique & outcome</CardTitle>
              <Badge variant={verdictVariant(outcome.state ?? run.state)}>
                {String(outcome.state ?? run.state ?? "—")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="mono text-[10.5px] leading-relaxed text-ink/85">
                <div>
                  <span className="text-muted">arrêt : </span>
                  {String(outcome.stop_condition ?? "—")}
                </div>
                <div>
                  <span className="text-muted">motif : </span>
                  {String(outcome.motif ?? run.motif ?? "—")}
                </div>
                <div>
                  <span className="text-muted">verdict critique : </span>
                  {String(outcome.critique_verdict || criticReport.$status || "—")}
                </div>
              </div>
              {(outcome.non_recherche as string[] | undefined)?.length ? (
                <div>
                  <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">
                    non recherché
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
                  <div className="text-[9.5px] uppercase tracking-[0.14em] text-down">erreurs critique</div>
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
                    chaîne journal : {verify.verified ? "VÉRIFIÉE" : "ÉCART"}
                  </div>
                  <div className="mt-1 text-muted">
                    head recalculé {fmtHash(verify.recomputed_head, 12)}
                  </div>
                  <div className="text-muted">
                    head enregistré {fmtHash(verify.recorded_head, 12)}
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {(bundle?.tool_calls ?? []).length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>appels d'outils (store)</CardTitle>
                <Badge variant="neutral">{bundle!.tool_calls.length}</Badge>
              </CardHeader>
              <ScrollArea className="max-h-52 rounded-none border-0">
                {bundle!.tool_calls.map((call, index) => (
                  <div key={index} className="mono border-b border-line/60 px-3 py-1.5 text-[10px]">
                    <div className="text-accent">{String(call.tool ?? call.name ?? "appel")}</div>
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

function hypotheseLabel(etat: string): string {
  const map: Record<string, string> = {
    UNDER_TEST: "en test",
    SUPPORTED: "soutenue",
    REFUTED: "réfutée",
    INCONCLUSIVE: "non concluant",
  };
  return map[etat] ?? etat;
}

export type { JournalEntry };
