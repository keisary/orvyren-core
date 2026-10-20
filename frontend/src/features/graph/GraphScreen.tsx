import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { GraphPayload, GraphQueryResult } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, Label, Select } from "@/components/ui/input";
import { cn } from "@/lib/cn";
import { toneForClass } from "@/lib/graph-theme";
import SigmaGraph, { type GraphCameraApi } from "./SigmaGraph";
import {
  QueryResultBlock,
  RailSection,
  SelectionRail,
  statusMeaning,
  Field,
} from "./Rail";
import {
  buildSubgraph,
  classCounts,
  displayName,
  indexGraph,
  kindLabel,
  pickDefaultRoot,
  recount,
  resolveNodeId,
  topNodes,
  type LabelMode,
} from "./subgraph";

/**
 * Graph — the dedicated full-screen route (ART_DIRECTION §2.3).
 *
 * One question per screen: *what is this exposure, and what justifies it?*
 *  - the canvas is the page (≥ 70 vh), with no control painted over it;
 *  - the query bar asks the question, the view bar bounds the picture
 *    (depth, label kind, camera), the legend filters, the right rail explains;
 *  - the canvas only ever draws a bounded subgraph (`subgraph.ts`), never the
 *    16 174-node world.
 */

type FieldKey =
  | "node"
  | "holder"
  | "src"
  | "dst"
  | "subject"
  | "asset"
  | "relation_id"
  | "as_of"
  | "as_of_block"
  | "kinds";

interface FieldDef {
  label: string;
  kind: "node" | "text";
  width: string;
  placeholder?: string;
}

const FIELDS: Record<FieldKey, FieldDef> = {
  node: { label: "Start node", kind: "node", width: "w-[236px]" },
  holder: { label: "Holder", kind: "node", width: "w-[236px]" },
  src: { label: "Source", kind: "node", width: "w-[236px]" },
  dst: { label: "Target", kind: "node", width: "w-[236px]" },
  subject: { label: "Subject", kind: "node", width: "w-[236px]" },
  asset: { label: "Asset / market", kind: "node", width: "w-[236px]" },
  relation_id: {
    label: "Relation id",
    kind: "text",
    width: "w-[236px]",
    placeholder: "relation id",
  },
  as_of: { label: "As of (ISO)", kind: "text", width: "w-[170px]", placeholder: "2026-04-18T19:03:59Z" },
  as_of_block: { label: "Block", kind: "text", width: "w-[120px]", placeholder: "52723115" },
  kinds: { label: "Relation kinds", kind: "text", width: "w-[170px]", placeholder: "DEPOSITED_IN,…" },
};

type QuestionKey =
  | "neighbourhood"
  | "q1"
  | "q2"
  | "q8"
  | "q3"
  | "q4"
  | "q5"
  | "q6"
  | "q7"
  | "snapshot";

interface Question {
  label: string;
  api: string | null;
  group: "subgraph" | "records";
  fields: FieldKey[];
  rootField?: FieldKey;
  answers: string;
}

const QUESTIONS: Record<QuestionKey, Question> = {
  neighbourhood: {
    label: "Neighbourhood of a node",
    api: null,
    group: "subgraph",
    fields: ["node"],
    rootField: "node",
    answers: "Who is this node connected to, and through which relations?",
  },
  q1: {
    label: "Q1 — exposure of a holder",
    api: "q1",
    group: "subgraph",
    fields: ["holder", "as_of", "as_of_block"],
    rootField: "holder",
    answers: "What does this holder own, directly and through deposits?",
  },
  q2: {
    label: "Q2 — signed dependency path",
    api: "q2",
    group: "subgraph",
    fields: ["src", "dst", "kinds", "as_of"],
    rootField: "src",
    answers: "Which signed dependency path links two nodes?",
  },
  q8: {
    label: "Q8 — permissions of a subject",
    api: "q8",
    group: "subgraph",
    fields: ["subject", "as_of", "as_of_block"],
    rootField: "subject",
    answers: "What can this subject do — roles and allowances?",
  },
  q4: {
    label: "Q4 — state at a block",
    api: "q4",
    group: "records",
    fields: ["as_of", "as_of_block"],
    answers: "Which relations were valid at this point in time?",
  },
  q5: {
    label: "Q5 — event timeline",
    api: "q5",
    group: "records",
    fields: ["as_of", "as_of_block"],
    answers: "Which first-class events were observable up to this instant?",
  },
  q6: {
    label: "Q6 — provenance of a relation",
    api: "q6",
    group: "records",
    fields: ["relation_id"],
    answers: "Which source refs justify this relation?",
  },
  q7: {
    label: "Q7 — counterparty concentration",
    api: "q7",
    group: "records",
    fields: ["asset", "as_of"],
    answers: "How concentrated is this asset's counterparty set (HHI)?",
  },
  q3: {
    label: "Q3 — open contradictions",
    api: "q3",
    group: "records",
    fields: [],
    answers: "Which contradiction pairs are still unresolved?",
  },
  snapshot: {
    label: "Snapshot — deterministic hash",
    api: "snapshot",
    group: "records",
    fields: ["as_of", "as_of_block"],
    answers: "What is the content hash of the graph at this instant?",
  },
};

const DEMO = "addr:eip155:8453:0xbe00a0de23a02a85d7fb7451ab9b69d84fd61fe3";

const DEFAULTS: Record<FieldKey, string> = {
  node: DEMO,
  holder: DEMO,
  src: "addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427",
  dst: "asset:eip155:8453:0x4200000000000000000000000000000000000006",
  subject: "addr:eip155:8453:0x2b8ce2c87c166d8e24e186e7e4253c11fc805427",
  asset: "asset:eip155:8453:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
  relation_id: "struct:constrains:0xecac9c5f704e954931349da37f60e39f515c11c1",
  as_of: "",
  as_of_block: "",
  kinds: "",
};

const LABEL_MODES: { key: LabelMode; label: string; hint: string }[] = [
  { key: "node", label: "Node", hint: "Node names only" },
  { key: "relation", label: "Relation", hint: "Relation kinds only" },
  { key: "none", label: "None", hint: "No labels — shape and tone only" },
];

function nf(value: number): string {
  return value.toLocaleString("en-GB");
}

export default function GraphScreen() {
  const graphQuery = useQuery({
    queryKey: ["graph-full"],
    queryFn: api.graphFull,
    staleTime: 300_000,
  });
  const payload: GraphPayload | undefined = graphQuery.data;
  const index = useMemo(() => (payload ? indexGraph(payload) : null), [payload]);

  const [question, setQuestion] = useState<QuestionKey>("neighbourhood");
  const [params, setParams] = useState<Record<FieldKey, string>>({ ...DEFAULTS });
  const [root, setRoot] = useState<string>("");
  const [rootError, setRootError] = useState<string | null>(null);
  const [depth, setDepth] = useState(2);
  const [labelMode, setLabelMode] = useState<LabelMode>("node");
  const [hiddenClasses, setHiddenClasses] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<string | null>(null);
  const [relationId, setRelationId] = useState<string | null>(null);
  const [result, setResult] = useState<GraphQueryResult | null>(null);
  const [resultSig, setResultSig] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(false);
  const cameraRef = useRef<GraphCameraApi | null>(null);

  const definition = QUESTIONS[question];

  // First payload sets the seed: the demo holder when it exists, else the
  // most connected node. Never a synthetic id.
  useEffect(() => {
    if (!index || root) return;
    const seed = pickDefaultRoot(index) ?? "";
    if (seed) {
      setRoot(seed);
      setParams((previous) => ({ ...previous, node: seed }));
    }
  }, [index, root, params.node]);

  const subgraph = useMemo(
    () => (index && root ? buildSubgraph(index, root, depth) : null),
    [index, root, depth],
  );
  const counts = useMemo(
    () => (subgraph ? recount(subgraph, hiddenClasses) : null),
    [subgraph, hiddenClasses],
  );
  const classes = useMemo(() => (subgraph ? classCounts(subgraph) : []), [subgraph]);

  const detailQuery = useQuery({
    queryKey: ["graph-node", selected],
    queryFn: () => api.graphNode(selected!),
    enabled: Boolean(selected),
    staleTime: 60_000,
  });
  const provenanceQuery = useQuery({
    queryKey: ["graph-q6", relationId],
    queryFn: () => api.graphQuery("q6", { relation_id: relationId ?? "" }),
    enabled: Boolean(relationId),
    staleTime: 60_000,
  });

  const selectedNode = useMemo(
    () => subgraph?.nodes.find((node) => node.id === selected) ?? null,
    [subgraph, selected],
  );

  const top = useMemo(() => (index ? topNodes(index, 40) : []), [index]);
  const nodeOptions = useMemo(() => {
    const options = top.map((node) => ({ id: node.id, label: displayName(node), kind: node.kind }));
    for (const field of definition.fields) {
      if (FIELDS[field].kind !== "node") continue;
      const value = params[field];
      if (!value || options.some((option) => option.id === value)) continue;
      const node = index?.nodeById.get(value);
      options.unshift({
        id: value,
        label: node ? displayName(node) : value,
        kind: node?.kind ?? "",
      });
    }
    return options;
  }, [top, definition.fields, params, index]);

  const sig = JSON.stringify(params);
  const isStaleResult = result !== null && resultSig !== sig;

  const selectNode = (id: string | null) => {
    setSelected(id);
    const node = id && subgraph ? subgraph.nodes.find((item) => item.id === id) : null;
    setRelationId(node?.via?.relationId ?? null);
  };

  const run = async () => {
    setRunError(false);
    if (!definition.api) {
      const resolved = index ? resolveNodeId(index, params.node) : null;
      if (!resolved) {
        setRootError(`No node in this dataset matches “${params.node}”.`);
        return;
      }
      setRootError(null);
      setRoot(resolved);
      setResult(null);
      setResultSig("");
      selectNode(null);
      return;
    }
    setRunning(true);
    try {
      const data = await api.graphQuery(definition.api, params);
      setResult(data);
      setResultSig(sig);
      if (definition.rootField && index) {
        const resolved = resolveNodeId(index, params[definition.rootField]);
        if (resolved) {
          setRoot(resolved);
          setRootError(null);
          selectNode(null);
        } else {
          setRootError(
            `“${params[definition.rootField]}” is not in this dataset — the canvas keeps its previous root.`,
          );
        }
      }
    } catch {
      setRunError(true);
      setResult(null);
    } finally {
      setRunning(false);
    }
  };

  const toggleClass = (cls: string) => {
    setHiddenClasses((previous) => {
      const next = new Set(previous);
      if (next.has(cls)) next.delete(cls);
      else next.add(cls);
      return next;
    });
  };

  const legacy = payload?.schema === "legacy";
  const dbShort = payload?.db ? (payload.db.split(/[\\/]/).pop() ?? payload.db) : "";

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background">
      {/* ---- one title zone: the only place the dataset totals are written --- */}
      <header className="flex shrink-0 flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b border-line bg-surface px-6 py-2">
        <div className="min-w-0">
          <h1 className="text-page-title font-semibold tracking-[-0.02em] text-ink">Graph</h1>
          <p className="mt-0.5 text-meta text-muted">
            The canvas draws the subgraph one question returns — never the whole graph.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-meta text-muted">
          <span>{legacy ? "Repository snapshot" : "Aave v3 · Base"}</span>
          <span className="font-mono text-code text-ink tnum">
            {payload ? `${nf(payload.counts.nodes)} nodes · ${nf(payload.counts.edges)} relations` : "—"}
          </span>
          <Badge variant="neutral">{payload ? `schema ${payload.schema}` : "loading"}</Badge>
          {dbShort ? (
            <span className="font-mono text-code" title={payload?.db}>
              {dbShort}
            </span>
          ) : null}
        </div>
      </header>

      {/* ---- query bar: the question lives here, never on the canvas -------- */}
      <div className="flex shrink-0 flex-wrap items-end gap-x-3 gap-y-2 border-b border-line bg-surface px-6 py-1.5">
        <div className="w-[268px]">
          <Label htmlFor="graph-question">Question</Label>
          <Select
            id="graph-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value as QuestionKey)}
          >
            <optgroup label="Subgraph">
              {Object.entries(QUESTIONS)
                .filter(([, item]) => item.group === "subgraph")
                .map(([key, item]) => (
                  <option key={key} value={key}>
                    {item.label}
                  </option>
                ))}
            </optgroup>
            <optgroup label="Records — answer in the rail, canvas unchanged">
              {Object.entries(QUESTIONS)
                .filter(([, item]) => item.group === "records")
                .map(([key, item]) => (
                  <option key={key} value={key}>
                    {item.label}
                  </option>
                ))}
            </optgroup>
          </Select>
        </div>

        {definition.fields.map((fieldKey) => {
          const field = FIELDS[fieldKey];
          return (
            <div key={fieldKey} className={cn(field.width, "shrink-0")}>
              <Label htmlFor={`graph-field-${fieldKey}`}>{field.label}</Label>
              {field.kind === "node" ? (
                <Select
                  id={`graph-field-${fieldKey}`}
                  value={params[fieldKey]}
                  onChange={(event) =>
                    setParams((previous) => ({ ...previous, [fieldKey]: event.target.value }))
                  }
                >
                  {nodeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  id={`graph-field-${fieldKey}`}
                  value={params[fieldKey]}
                  placeholder={field.placeholder}
                  onChange={(event) =>
                    setParams((previous) => ({ ...previous, [fieldKey]: event.target.value }))
                  }
                />
              )}
            </div>
          );
        })}

        <Button className="shrink-0" onClick={run} disabled={running || !payload}>
          {running ? "Running…" : "Run"}
        </Button>
      </div>

      {/* ---- view bar: depth / label kind / camera / subgraph-vs-total ------ */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-6 gap-y-2 border-b border-line bg-surface2 px-6 py-1">
        <div className="flex items-center gap-2">
          <span className="text-meta text-muted">Depth</span>
          <span className="font-mono text-code text-ink tnum">{depth}</span>
          <div className="flex items-center">
            <button
              type="button"
              className={STEP}
              onClick={() => setDepth((value) => Math.max(1, value - 1))}
              disabled={depth <= 1}
              aria-label="One hop less"
              title="One hop less"
            >
              −
            </button>
            <button
              type="button"
              className={cn(STEP, "w-auto px-2 text-meta")}
              onClick={() => setDepth((value) => Math.min(3, value + 1))}
              disabled={depth >= 3}
              title="Expand the query by one hop"
            >
              +1 hop
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-meta text-muted">Labels</span>
          <div className="flex border border-line-strong">
            {LABEL_MODES.map((mode) => (
              <button
                key={mode.key}
                type="button"
                title={mode.hint}
                aria-pressed={labelMode === mode.key}
                onClick={() => setLabelMode(mode.key)}
                className={cn(
                  "h-7 px-2.5 text-meta transition-colors duration-100",
                  labelMode === mode.key
                    ? "bg-ink text-on-accent"
                    : "bg-surface text-muted hover:bg-surface2 hover:text-ink",
                )}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-meta text-muted">View</span>
          <div className="flex">
            <button
              type="button"
              className={STEP}
              onClick={() => cameraRef.current?.zoomOut()}
              aria-label="Zoom out"
              title="Zoom out"
            >
              −
            </button>
            <button
              type="button"
              className={cn(STEP, "w-auto px-2 text-meta")}
              onClick={() => cameraRef.current?.resetView()}
            >
              Reset
            </button>
            <button
              type="button"
              className={STEP}
              onClick={() => cameraRef.current?.zoomIn()}
              aria-label="Zoom in"
              title="Zoom in"
            >
              +
            </button>
          </div>
        </div>

        {subgraph && counts ? (
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-code text-ink tnum">
              {nf(subgraph.nodes.length)} / {nf(subgraph.totals.nodes)} nodes
            </span>
            <span className="text-meta text-muted">·</span>
            <span className="font-mono text-code text-ink tnum">
              {nf(subgraph.edges.length)} edges
            </span>
            {subgraph.mergedRelations > 0 ? (
              <Badge variant="neutral" title="Parallel relations collapsed into one line per node pair">
                {nf(subgraph.mergedRelations)} merged
              </Badge>
            ) : null}
            {subgraph.aggregatedNodes > 0 ? (
              <Badge
                variant="neutral"
                title="High-degree contracts drawn once, carrying their relation count"
              >
                {subgraph.aggregatedNodes} aggregated
              </Badge>
            ) : null}
            {subgraph.hiddenNodes > 0 ? (
              <Badge
                variant="warn"
                title={`Budget: ${depth} hop${depth > 1 ? "s" : ""}, 40 nodes max. Raise the depth or pick a narrower root to see more.`}
              >
                +{nf(subgraph.hiddenNodes)} not shown
              </Badge>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* ---- canvas + provenance rail -------------------------------------- */}
      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="relative min-h-[70vh] flex-1 bg-surface">
            {graphQuery.isPending ? (
              <Quiet title="Loading the graph dataset…" />
            ) : graphQuery.isError || !payload || !index ? (
              <Quiet
                title="Graph database unavailable."
                detail="The API answered without a readable graph payload. Nothing is drawn rather than drawn wrong."
              />
            ) : rootError ? (
              <Quiet title="No subgraph to draw." detail={rootError} />
            ) : !subgraph || subgraph.status !== "OK" ? (
              <Quiet
                title="This dataset has no such node."
                detail="Pick another start node — the canvas never invents a node to fill the frame."
              />
            ) : subgraph.nodes.length === 0 ? (
              <Quiet title="Nothing to draw." detail="This node has no neighbour at this depth." />
            ) : subgraph ? (
              <SigmaGraph
                nodes={subgraph.nodes}
                edges={subgraph.edges}
                classes={payload.classes}
                selected={selected}
                onSelect={selectNode}
                labelMode={labelMode}
                hiddenClasses={hiddenClasses}
                onCamera={(camera) => {
                  cameraRef.current = camera;
                }}
              />
            ) : null}
          </div>

          {/* legend = filter: hidden classes go grey AND leave the counts */}
          <div className="flex shrink-0 flex-wrap items-center gap-x-2 gap-y-2 border-t border-line bg-surface px-6 py-1">
            <span className="text-meta text-muted">Classes</span>
            {classes.length === 0 ? (
              <span className="text-meta text-muted">—</span>
            ) : (
              classes.map(({ cls, count }) => {
                const hidden = hiddenClasses.has(cls);
                return (
                  <button
                    key={cls}
                    type="button"
                    onClick={() => toggleClass(cls)}
                    aria-pressed={!hidden}
                    title={hidden ? `Show ${cls} again` : `Grey out ${cls}`}
                    className={cn(
                      "inline-flex h-7 items-center gap-1.5 border px-2 text-meta transition-colors duration-100",
                      hidden
                        ? "border-line bg-surface text-muted"
                        : "border-line-strong bg-surface2 text-ink",
                    )}
                  >
                    <span
                      aria-hidden
                      className="inline-block h-2.5 w-2.5"
                      style={{ background: hidden ? "var(--color-graph-dim)" : toneForClass(cls) }}
                    />
                    <span className={hidden ? "line-through decoration-line-strong" : ""}>
                      {kindLabel(cls)}
                    </span>
                    <span className="tnum">{hidden ? "hidden" : nf(count)}</span>
                  </button>
                );
              })
            )}
            <span className="ml-auto text-meta text-muted">
              {counts && subgraph
                ? `Visible: ${nf(counts.nodes)} of ${nf(subgraph.nodes.length)} nodes · ${nf(
                    counts.relations,
                  )} relations${hiddenClasses.size > 0 ? ` · ${hiddenClasses.size} class${
                    hiddenClasses.size === 1 ? "" : "es"
                  } greyed` : ""}`
                : "Wheel to zoom · drag to pan · click a node for its provenance"}
            </span>
          </div>
        </div>

        <aside
          aria-label="Provenance"
          className="flex w-[372px] shrink-0 flex-col overflow-auto border-l border-line bg-surface"
        >
          {selectedNode ? (
            <SelectionRail
              node={selectedNode}
              detail={detailQuery.data ?? null}
              detailLoading={detailQuery.isFetching}
              detailError={detailQuery.isError}
              relationId={relationId}
              onPickRelation={setRelationId}
              provenance={provenanceQuery.data ?? null}
              provenanceLoading={provenanceQuery.isFetching}
              provenanceError={provenanceQuery.isError}
              onClear={() => selectNode(null)}
            />
          ) : (
            <>
              <div className="border-b border-line px-5 py-4">
                <h2 className="text-section-title font-semibold text-ink">Query</h2>
                <p className="mt-1 text-meta text-muted">{definition.answers}</p>
              </div>
              <RailSection
                title="Result"
                meta={isStaleResult ? "parameters changed — re-run" : undefined}
              >
                <QueryResultBlock
                  result={result}
                  isFetching={running}
                  error={runError}
                />
                {result && result.status && result.status !== "OK" && statusMeaning(result.status) === "" ? (
                  <p className="mt-2 text-meta text-muted">
                    {result.status} — see the runbook for this status.
                  </p>
                ) : null}
              </RailSection>
              <RailSection title="Selection">
                <p className="text-meta text-muted">
                  Click a node on the canvas to read why it is there: the query that
                  returned it, the relation that reached it, and the provenance refs of
                  that relation. Depth and labels are set in the bar above the canvas.
                </p>
              </RailSection>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

const STEP =
  "flex h-7 w-7 items-center justify-center border border-line-strong bg-surface " +
  "font-mono text-[13px] leading-none text-ink transition-colors duration-100 " +
  "hover:bg-surface2 disabled:pointer-events-none disabled:border-line disabled:text-muted " +
  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent";

function Quiet({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center p-8">
      <div className="max-w-[420px] text-center">
        <p className="text-body font-medium text-ink">{title}</p>
        {detail ? <p className="mt-1 text-meta text-muted">{detail}</p> : null}
      </div>
    </div>
  );
}
