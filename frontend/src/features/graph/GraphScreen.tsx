import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { GraphQueryResult } from "@/lib/types";
import { fmtCompact, fmtHash, fmtNumber, shortAddress, truncate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, ScrollArea, Select } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScreenShell } from "@/components/ScreenShell";
import SigmaGraph from "./SigmaGraph";

/** Demonstration values = `evidence/ui_snapshot.json` (real graph run). */
const DEFAULTS: Record<string, string> = {
  holder: "addr:eip155:8453:0xbe00a0de23a02a85d7fb7451ab9b69d84fd61fe3",
  src: "addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427",
  dst: "asset:eip155:8453:0x4200000000000000000000000000000000000006",
  asset: "debt:eip155:8453:0xa238dd80c259a72e81d7e4664a9801593f98d1c5:0x4200000000000000000000000000000000000006",
  subject: "addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427",
  relation_id: "struct:constrains:0xecac9c5f704e954931349da37f60e39f515c11c1",
  as_of_block: "52723115",
  max_depth: "3",
  limit: "25",
  kinds: "",
  as_of: "",
};

interface QueryDef {
  label: string;
  fields: (keyof typeof DEFAULTS)[];
}

const QUERIES: Record<string, QueryDef> = {
  q1: { label: "Q1 — consolidated exposure (direct + indirect)", fields: ["holder", "as_of", "as_of_block", "max_depth"] },
  q2: { label: "Q2 — signed dependency paths", fields: ["src", "dst", "kinds", "max_depth", "as_of", "as_of_block"] },
  q3: { label: "Q3 — open contradictions", fields: [] },
  q4: { label: "Q4 — point-in-time state", fields: ["as_of", "as_of_block", "limit"] },
  q5: { label: "Q5 — event timeline", fields: ["as_of", "as_of_block", "limit"] },
  q6: { label: "Q6 — relation provenance", fields: ["relation_id"] },
  q7: { label: "Q7 — counterparty concentration (HHI)", fields: ["asset", "as_of", "as_of_block"] },
  q8: { label: "Q8 — permissions (roles, allowances)", fields: ["subject", "as_of", "as_of_block"] },
  snapshot: { label: "Snapshot — deterministic graph hash", fields: ["as_of", "as_of_block"] },
};

function ResultTable({ result }: { result: GraphQueryResult }) {
  const rows = result.rows ?? [];
  const columns = useMemo(() => {
    const keys: string[] = [];
    for (const row of rows.slice(0, 25)) {
      for (const key of Object.keys(row)) {
        if (!keys.includes(key)) keys.push(key);
      }
    }
    return keys;
  }, [rows]);
  return (
    <Table>
      <THead>
        <TR>
          {columns.map((column) => (
            <TH key={column}>{column}</TH>
          ))}
        </TR>
      </THead>
      <TBody>
        {rows.slice(0, 25).map((row, index) => (
          <TR key={index}>
            {columns.map((column) => (
              <TD key={column} className="mono max-w-[260px] break-all text-[10.5px]">
                {formatCell(row[column])}
              </TD>
            ))}
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return fmtNumber(value, 4);
  if (typeof value === "object") return truncate(JSON.stringify(value), 90);
  return String(value);
}

export default function GraphScreen() {
  const graphQuery = useQuery({ queryKey: ["graph-full"], queryFn: api.graphFull, staleTime: 300_000 });
  const [selected, setSelected] = useState<string | null>(null);
  const [queryName, setQueryName] = useState("q1");
  const [params, setParams] = useState<Record<string, string>>({ ...DEFAULTS });
  const [layoutState, setLayoutState] = useState<"cached" | "computing" | "done" | "">("");
  const [ran, setRan] = useState<GraphQueryResult | null>(null);

  const runQuery = useQuery({
    queryKey: ["graph-query", queryName, params],
    queryFn: () => api.graphQuery(queryName, params),
    enabled: false,
  });

  const detailQuery = useQuery({
    queryKey: ["graph-node", selected],
    queryFn: () => api.graphNode(selected!),
    enabled: Boolean(selected),
  });

  const payload = graphQuery.data;
  const def = QUERIES[queryName];

  return (
    <ScreenShell
      title="On-chain risk graph"
      subtitle={
        <span className="mono">
          sigma.js v3 (WebGL) · {payload ? `${fmtCompact(payload.counts.nodes)} nodes / ${fmtCompact(payload.counts.edges)} edges · ${payload.db}` : "loading…"}
          {layoutState === "computing" ? " · FA2 layout running…" : ""}
          {layoutState === "done" ? " · FA2 layout computed and persisted ✓" : ""}
          {layoutState === "cached" ? " · layout pre-computed ✓" : ""}
        </span>
      }
      actions={
        <>
          <Badge variant="info">Q1–Q8 · read contract</Badge>
          {payload ? <Badge variant="neutral">version {fmtHash(payload.graph_version, 8)}</Badge> : null}
        </>
      }
    >
      <div className="grid h-full min-h-0 grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_460px]">
        <Card className="flex min-h-[600px] flex-col overflow-hidden">
          <CardHeader>
            <CardTitle>visualisation</CardTitle>
            <div className="flex flex-wrap items-center gap-1.5">
              {payload
                ? Object.entries(payload.classes)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 10)
                    .map(([cls, count]) => (
                      <Badge key={cls} variant="neutral">
                        {cls}: {fmtCompact(count)}
                      </Badge>
                    ))
                : null}
            </div>
          </CardHeader>
          <div className="relative min-h-0 flex-1 bg-background">
            {payload ? (
              <SigmaGraph
                payload={payload}
                selected={selected}
                onSelect={setSelected}
                onLayout={setLayoutState}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-muted">
                {graphQuery.isError ? "graph database unavailable" : "loading graph…"}
              </div>
            )}
            <div className="pointer-events-none absolute bottom-2 left-2 rounded border border-line bg-surface/90 px-2 py-1 mono text-[9.5px] text-muted">
              click node = details · wheel = zoom · click empty = deselect
            </div>
          </div>
        </Card>
        <div className="flex min-h-0 flex-col gap-3">
          <Card>
            <CardHeader>
              <CardTitle>queries Q1–Q8</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <Select value={queryName} onChange={(e) => setQueryName(e.target.value)}>
                {Object.entries(QUERIES).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value.label}
                  </option>
                ))}
              </Select>
              <div className="grid grid-cols-2 gap-2">
                {def.fields.map((field) => (
                  <div key={field} className={field === "as_of" || field === "kinds" ? "col-span-2" : ""}>
                    <Label>{field}</Label>
                    <Input
                      value={params[field] ?? ""}
                      onChange={(e) =>
                        setParams((prev) => ({ ...prev, [field]: e.target.value }))
                      }
                      placeholder="(empty)"
                    />
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    runQuery.refetch().then(({ data }) => setRan(data ?? null));
                  }}
                >
                  run query
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setParams({ ...DEFAULTS })}
                >
                  snapshot values
                </Button>
              </div>
              {runQuery.isFetching ? <div className="text-muted">running…</div> : null}
              {ran ? (
                <div className="mono flex flex-wrap gap-1.5 text-[10px]">
                  <Badge variant={ran.status && ran.status !== "OK" ? "warn" : "ok"}>
                    {ran.status ?? "OK"}
                  </Badge>
                  {ran.count !== undefined ? <Badge variant="neutral">count {ran.count}</Badge> : null}
                  {ran.latency_ms !== undefined ? (
                    <Badge variant="neutral">{fmtNumber(ran.latency_ms, 1)} ms</Badge>
                  ) : null}
                  {typeof ran.hhi === "number" ? (
                    <Badge variant="info">HHI {fmtNumber(ran.hhi, 4)}</Badge>
                  ) : null}
                  {typeof ran.counterparties === "number" ? (
                    <Badge variant="neutral">{ran.counterparties} counterparties</Badge>
                  ) : null}
                  {ran.graph_hash ? (
                    <Badge variant="violet">hash {fmtHash(String(ran.graph_hash), 10)}</Badge>
                  ) : null}
                </div>
              ) : null}
              {ran ? (
                <ScrollArea className="max-h-64">
                  <ResultTable result={ran} />
                </ScrollArea>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>node details</CardTitle>
              {selected ? <Badge variant="info">{shortAddress(selected)}</Badge> : null}
            </CardHeader>
            <CardContent>
              {!selected ? (
                <div className="text-[11px] text-muted">
                  select a node in the graph to see its identity, relations and
                  degree.
                </div>
              ) : detailQuery.data ? (
                <div className="space-y-2">
                  <div className="mono text-[10.5px] break-all text-ink/90">{selected}</div>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="neutral">{String(detailQuery.data.kind ?? "?")}</Badge>
                    <Badge variant="neutral">{String(detailQuery.data.node_class ?? detailQuery.data.kind ?? "?")}</Badge>
                    <Badge variant="info">{String(detailQuery.data.relation_count ?? 0)} relations</Badge>
                  </div>
                  {detailQuery.data.address ? (
                    <div className="mono text-[10px] text-muted">
                      address {String(detailQuery.data.address)}
                    </div>
                  ) : null}
                  <ScrollArea className="max-h-52">
                    <Table>
                      <THead>
                        <TR>
                          <TH>relation</TH>
                          <TH>kind</TH>
                          <TH>src → dst</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {((detailQuery.data.relations as Record<string, unknown>[]) ?? [])
                          .slice(0, 25)
                          .map((relation, index) => (
                            <TR key={index}>
                              <TD className="mono text-[10px]">{fmtHash(String(relation.relation_id), 10)}</TD>
                              <TD>
                                <Badge variant="neutral">{String(relation.kind)}</Badge>
                              </TD>
                              <TD className="mono max-w-[220px] break-all text-[9.5px] text-muted">
                                {shortAddress(relation.src)} → {shortAddress(relation.dst)}
                              </TD>
                            </TR>
                          ))}
                      </TBody>
                    </Table>
                  </ScrollArea>
                </div>
              ) : (
                <div className="text-muted">loading…</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ScreenShell>
  );
}
