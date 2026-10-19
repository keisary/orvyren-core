import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { GraphQueryResult } from "@/lib/types";
import { fmtCompact, fmtHash, fmtNumber, fmtTime, shortAddress, truncate } from "@/lib/format";
import { toneForClass } from "@/lib/graph-theme";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Select } from "@/components/ui/input";
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

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return fmtNumber(value, 4);
  if (typeof value === "object") return truncate(JSON.stringify(value), 90);
  return String(value);
}

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
              <TD
                key={column}
                className={`max-w-[260px] break-all ${
                  typeof row[column] === "number" ? "text-right" : ""
                }`}
              >
                {formatCell(row[column])}
              </TD>
            ))}
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

/** Written meaning for non-OK statuses (§4.8): a status word alone is not an
 *  explanation. */
function StatusExplanation({ status, query }: { status: string; query?: string }) {
  if (status === "NO_PATH") {
    return (
      <div className="space-y-0.5 text-meta text-muted">
        <div>NO_PATH — no dependency path was found in this dataset.</div>
        <div>Dependency edges are not populated in the demonstrated slice.</div>
      </div>
    );
  }
  if (status === "NOT_INGESTED") {
    // Q8 uses the same status when the permissions view has no rows: never
    // conclude "this id does not exist" from a permission-shaped answer.
    if ((query ?? "").startsWith("q8")) {
      return (
        <div className="text-meta text-muted">
          NOT_INGESTED — permission data is not available in this dataset.
        </div>
      );
    }
    return (
      <div className="text-meta text-muted">
        NOT_INGESTED — this id does not exist in the demonstrated dataset.
      </div>
    );
  }
  if (status === "OK") {
    return <div className="text-meta text-muted">No rows match these parameters.</div>;
  }
  return <div className="text-meta text-muted">{status} — see the runbook for this status.</div>;
}

export default function GraphScreen() {
  const graphQuery = useQuery({ queryKey: ["graph-full"], queryFn: api.graphFull, staleTime: 300_000 });
  const [selected, setSelected] = useState<string | null>(null);
  const [queryName, setQueryName] = useState("q1");
  const [params, setParams] = useState<Record<string, string>>({ ...DEFAULTS });
  const [layoutState, setLayoutState] = useState<
    "cached" | "computing" | "done" | "served" | "failed" | ""
  >("");
  const [ran, setRan] = useState<{
    name: string;
    sig: string;
    at: string;
    data: GraphQueryResult;
  } | null>(null);

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
  // A result remembers WHICH query produced it (Astra-4 P1-3): switching Q
  // without touching fields must still flag the old result as previous.
  const isPreviousResult =
    ran !== null && (ran.sig !== JSON.stringify(params) || ran.name !== queryName);
  const legacy = payload?.schema === "legacy";
  const dbShort = payload?.db ? (payload.db.split(/[\\/]/).pop() ?? payload.db) : "—";
  const relations = ((detailQuery.data?.relations as Record<string, unknown>[]) ?? []).slice(0, 25);
  const relationsTruncated =
    detailQuery.data?.relations_truncated === true || relations.length >= 25;

  return (
    <ScreenShell
      title="Risk graph"
      subtitle={
        payload
          ? `${payload.counts.nodes.toLocaleString("en-GB")} nodes · ${payload.counts.edges.toLocaleString("en-GB")} relations · read-only queries Q1–Q8`
          : "Loading the graph dataset…"
      }
      context={[
        {
          label: "Dataset",
          value: payload ? (legacy ? "Repository snapshot" : "Aave v3 / Base") : "—",
        },
        {
          label: "Nodes",
          value: payload ? payload.counts.nodes.toLocaleString("en-GB") : "—",
        },
        {
          label: "Edges",
          value: payload ? payload.counts.edges.toLocaleString("en-GB") : "—",
        },
        { label: "Database", value: dbShort },
        { label: "Schema", value: payload ? String(payload.schema) : "—" },
        { label: "Version", value: payload ? String(payload.graph_version) : "—" },
      ]}
      actions={<Badge variant="info">Q1–Q8 · read contract</Badge>}
    >
      <div className="grid h-full min-h-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_440px]">
        <Card className="flex min-h-[600px] flex-col overflow-hidden">
          <CardHeader>
            <CardTitle>Visualization</CardTitle>
            <div className="flex flex-wrap items-center gap-1.5">
              {payload
                ? Object.entries(payload.classes)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 8)
                    .map(([cls, count]) => (
                      <span key={cls} className="inline-flex items-center gap-1.5 border border-line bg-surface px-1.5 py-0.5 text-meta text-muted"
                        title={legacy ? "Repository snapshot · legacy schema" : undefined}
                      >
                        <span
                          aria-hidden
                          className="inline-block h-2.5 w-2.5"
                          style={{ background: toneForClass(cls) }}
                        />
                        <span className="text-ink">{cls}</span>
                        <span className="tnum">{count.toLocaleString("en-GB")}</span>
                      </span>
                    ))
                : null}
            </div>
          </CardHeader>
          <div className="relative min-h-0 flex-1 bg-surface">
            {payload ? (
              <SigmaGraph
                payload={payload}
                selected={selected}
                onSelect={setSelected}
                onLayout={setLayoutState}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-meta text-muted">
                {graphQuery.isError ? "Graph database unavailable." : "Loading graph…"}
              </div>
            )}
            <div className="pointer-events-none absolute bottom-2 left-2 max-w-[440px] border border-line bg-surface px-2.5 py-1.5 text-meta text-muted">
              <div>Click a node for details · wheel to zoom · click empty space to deselect.</div>
              <div>
                Dataset overview
                {layoutState === "computing" ? " · layout computing…" : ""}
                {layoutState === "done" ? " · layout computed and cached" : ""}
                {layoutState === "cached" ? " · layout pre-computed" : ""}
                {layoutState === "served" ? " · using served coordinates" : ""}
                {layoutState === "failed" ? " · canvas unavailable" : ""}
                . Point-in-time filters apply to query results.
              </div>
            </div>
          </div>
        </Card>

        <div className="flex min-h-0 flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Queries Q1–Q8</CardTitle>
              {isPreviousResult ? (
                <Badge variant="neutral">Previous query result</Badge>
              ) : null}
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
                    <Label htmlFor={`q-${field}`}>{field}</Label>
                    <Input
                      id={`q-${field}`}
                      value={params[field] ?? ""}
                      onChange={(e) => setParams((prev) => ({ ...prev, [field]: e.target.value }))}
                      placeholder="(empty)"
                    />
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  onClick={() => {
                    const sig = JSON.stringify(params);
                    const name = queryName;
                    runQuery.refetch().then(({ data }) => {
                      if (data) {
                        setRan({ name, sig, at: new Date().toISOString(), data });
                      }
                    });
                  }}
                >
                  Run query
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setParams({ ...DEFAULTS })}
                >
                  Load example parameters
                </Button>
              </div>
              <div className="text-meta text-muted">
                Example parameters from the archived Aave Base snapshot.
              </div>
              {runQuery.isFetching ? <div className="text-meta text-muted">Running…</div> : null}
              {runQuery.isError ? (
                <div className="space-y-1.5">
                  <div className="text-meta text-ink">
                    Query failed — the API did not answer.
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => runQuery.refetch()}>
                    Retry
                  </Button>
                </div>
              ) : null}
              {ran ? (
                <div className="space-y-2">
                  <div className="text-meta text-muted">
                    Result of {QUERIES[ran.name]?.label ?? ran.name} · run{" "}
                    {fmtTime(ran.at)}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant={ran.data.status && ran.data.status !== "OK" ? "warn" : "ok"}>
                      {ran.data.status ?? "OK"}
                    </Badge>
                    {isPreviousResult ? (
                      <Badge variant="neutral">
                        Previous query result ({ran.name.toUpperCase()})
                      </Badge>
                    ) : null}
                    {ran.data.count !== undefined ? (
                      <Badge variant="neutral">count {ran.data.count}</Badge>
                    ) : null}
                    {ran.data.latency_ms !== undefined ? (
                      <Badge variant="neutral">
                        {fmtNumber(ran.data.latency_ms, 1)} ms (this response)
                      </Badge>
                    ) : null}
                    {typeof ran.data.hhi === "number" ? (
                      <Badge variant="info">HHI {fmtNumber(ran.data.hhi, 4)}</Badge>
                    ) : null}
                    {typeof ran.data.counterparties === "number" ? (
                      <Badge variant="neutral">{ran.data.counterparties} counterparties</Badge>
                    ) : null}
                    {ran.data.graph_hash ? (
                      <Badge variant="neutral">
                        hash {fmtHash(String(ran.data.graph_hash), 10)}
                      </Badge>
                    ) : null}
                  </div>
                  {String(ran.data.status ?? "OK") !== "OK" ||
                  (ran.data.rows ?? []).length === 0 ? (
                    <StatusExplanation
                      status={String(ran.data.status ?? "OK")}
                      query={ran.name}
                    />
                  ) : null}
                  {(ran.data.rows ?? []).length > 0 ? (
                    <div className="text-meta text-muted">
                      Showing {Math.min(25, (ran.data.rows ?? []).length)} of{" "}
                      {ran.data.count ?? (ran.data.rows ?? []).length} rows
                    </div>
                  ) : null}
                  <div className="max-h-64 overflow-auto border border-line">
                    <ResultTable result={ran.data} />
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Selected node</CardTitle>
              {selected ? <Badge variant="info">{shortAddress(selected)}</Badge> : null}
            </CardHeader>
            <CardContent>
              {!selected ? (
                <div className="text-body text-muted">
                  Select a node to inspect its identity and relations.
                </div>
              ) : detailQuery.data ? (
                <div className="space-y-2">
                  <div className="break-all font-mono text-code text-ink">{selected}</div>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge variant="neutral">kind {String(detailQuery.data.kind ?? "?")}</Badge>
                    <Badge variant="neutral">
                      class {String(detailQuery.data.node_class ?? detailQuery.data.kind ?? "?")}
                    </Badge>
                    <Badge variant="info">{String(detailQuery.data.relation_count ?? 0)} relations</Badge>
                  </div>
                  {detailQuery.data.address ? (
                    <div className="font-mono text-code text-muted">
                      address {String(detailQuery.data.address)}
                    </div>
                  ) : null}
                  <div className="max-h-52 overflow-auto border border-line">
                    <Table>
                      <THead>
                        <TR>
                          <TH>Relation</TH>
                          <TH>Kind</TH>
                          <TH>Src → dst</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {relations.map((relation, index) => (
                          <TR key={index}>
                            <TD>{fmtHash(String(relation.relation_id), 10)}</TD>
                            <TD>
                              <Badge variant="neutral">{String(relation.kind)}</Badge>
                            </TD>
                            <TD className="max-w-[220px] text-muted">
                              {shortAddress(relation.src)} → {shortAddress(relation.dst)}
                            </TD>
                          </TR>
                        ))}
                      </TBody>
                    </Table>
                  </div>
                  {relationsTruncated ? (
                    <div className="text-meta text-muted">
                      Showing the first {relations.length} of{" "}
                      {String(detailQuery.data.relation_count ?? relations.length)} relations.
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-meta text-muted">Loading…</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ScreenShell>
  );
}
