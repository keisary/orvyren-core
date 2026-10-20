import { useMemo, type ReactNode } from "react";
import type { GraphQueryResult } from "@/lib/types";
import { fmtNumber, shortAddress, truncate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { displayName, kindLabel, type SubgraphNode } from "./subgraph";

/**
 * The right rail — one question: *why is this node on the canvas?*
 *
 * Three answers, in the order the question is asked (ART_DIRECTION §2.5):
 *  1. the QUERY that produced the view (and its status, in words);
 *  2. the RELATION that pulled this node in (kind, direction, parent, hop);
 *  3. the PROVENANCE refs of that relation (Q6), or an honest "none recorded".
 *
 * Nothing here is a modal and nothing is duplicated from the header: the rail
 * is the only place that explains a selection.
 */

export function RailSection({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border-b border-line px-5 py-4">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h3 className="text-section-title font-semibold text-ink">{title}</h3>
        {meta ? <span className="text-meta text-muted">{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[86px_minmax(0,1fr)] items-baseline gap-2 py-1">
      <span className="text-meta text-muted">{label}</span>
      <span className="min-w-0 break-words text-table text-ink">{children}</span>
    </div>
  );
}

interface RelationRow {
  relation_id?: string;
  kind?: string;
  src?: string;
  dst?: string;
  family?: string;
  sign_prior?: string;
}

export function SelectionRail({
  node,
  detail,
  detailLoading,
  detailError,
  relationId,
  onPickRelation,
  provenance,
  provenanceLoading,
  provenanceError,
  onClear,
}: {
  node: SubgraphNode | null;
  detail?: Record<string, unknown> | null;
  detailLoading: boolean;
  detailError: boolean;
  relationId: string | null;
  onPickRelation: (id: string | null) => void;
  provenance?: GraphQueryResult | null;
  provenanceLoading: boolean;
  provenanceError: boolean;
  onClear: () => void;
}) {
  const relations = useMemo<RelationRow[]>(() => {
    const rows = (detail?.relations as RelationRow[] | undefined) ?? [];
    return rows.slice(0, 40);
  }, [detail]);
  const groups = useMemo(() => {
    const map = new Map<
      string,
      { kind: string; src: string; dst: string; count: number; relationId: string }
    >();
    for (const relation of relations) {
      const key = `${relation.kind}|${relation.src}|${relation.dst}`;
      const existing = map.get(key);
      if (existing) existing.count += 1;
      else
        map.set(key, {
          kind: String(relation.kind ?? "relation"),
          src: String(relation.src ?? ""),
          dst: String(relation.dst ?? ""),
          count: 1,
          relationId: String(relation.relation_id ?? ""),
        });
    }
    // One line per *kind of link*, not one line per relation record: 200
    // HOLDS rows saying the same thing are the repetition this page removes.
    return [...map.values()]
      .sort((a, b) => b.count - a.count || a.kind.localeCompare(b.kind))
      .slice(0, 8);
  }, [relations]);
  const relationTotal = Number(detail?.relation_count ?? relations.length);
  const truncated = detail?.relations_truncated === true || relationTotal > relations.length;

  const provenanceRows = useMemo(() => {
    const rows = (provenance?.rows as Record<string, unknown>[] | undefined) ?? [];
    return rows.slice(0, 8);
  }, [provenance]);

  if (!node) {
    return (
      <div className="px-5 py-6">
        <p className="text-body text-ink">Nothing selected.</p>
        <p className="mt-1 text-meta text-muted">
          Click a node on the canvas: this rail then writes down the query that brought it
          here, the relation that links it, and the provenance refs of that relation.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
        <div className="min-w-0">
          <div className="text-meta text-muted">{kindLabel(node.kind)}</div>
          <h2 className="mt-0.5 break-words text-[17px] font-semibold leading-[24px] text-ink">
            {node.label}
          </h2>
        </div>
        <Button variant="ghost" size="sm" onClick={onClear} aria-label="Clear selection">
          Clear
        </Button>
      </div>

      <RailSection
        title="Why it is here"
        meta={node.hop === 0 ? "root" : `${node.hop} hop${node.hop > 1 ? "s" : ""}`}
      >
        {node.hop === 0 ? (
          <p className="text-table text-ink">
            Root of the query: every other node on the canvas is drawn from it.
          </p>
        ) : node.via ? (
          <div className="space-y-1">
            <p className="text-table text-ink">
              Reached by <span className="font-mono text-code">{node.via.kind}</span> —{" "}
              {node.via.direction === "out" ? (
                <>
                  <span className="font-medium">{displayLabel(node.via.parent)}</span> → this
                  node.
                </>
              ) : (
                <>
                  this node → <span className="font-medium">{displayLabel(node.via.parent)}</span>.
                </>
              )}
            </p>
            <p className="text-meta text-muted">hop {node.hop} of the query.</p>
            <Button
              variant="secondary"
              size="sm"
              className="mt-1"
              onClick={() =>
                onPickRelation(relationId === node.via?.relationId ? null : node.via?.relationId ?? null)
              }
            >
              {relationId === node.via.relationId ? "Hide provenance" : "Show provenance"}
            </Button>
          </div>
        ) : (
          <p className="text-table text-muted">No relation recorded for this hop.</p>
        )}
        {node.aggregated ? (
          <p className="mt-2 border-l-2 border-line-strong pl-3 text-meta text-muted">
            Aggregated: this contract stands for{" "}
            <span className="tnum text-ink">{node.relationCount.toLocaleString("en-GB")}</span>{" "}
            relations, drawn as one node. Its neighbourhood is not expanded — that is the
            fan this page refuses to paint.
          </p>
        ) : null}
      </RailSection>

      <RailSection title="Identity">
        <Field label="Node id">
          <span className="font-mono text-code break-all">{node.id}</span>
        </Field>
        {node.kind !== node.cls ? (
          <Field label="Kind">
            <span className="font-mono text-code">{node.kind}</span>
          </Field>
        ) : null}
        <Field label="Class">{node.cls}</Field>
        <Field label="Relations">
          <span className="tnum">{node.relationCount.toLocaleString("en-GB")}</span>{" "}
          <span className="text-muted">in the dataset</span>
        </Field>
        {detail?.address ? (
          <Field label="Address">
            <span className="font-mono text-code break-all">{String(detail.address)}</span>
          </Field>
        ) : null}
      </RailSection>

      <RailSection
        title="Links"
        meta={detailLoading ? "loading…" : `${relationTotal.toLocaleString("en-GB")} relations`}
      >
        {detailError ? (
          <p className="text-meta text-muted">
            Node detail unavailable — the API did not answer for this id.
          </p>
        ) : groups.length === 0 ? (
          <p className="text-meta text-muted">
            {detailLoading ? "Reading relations…" : "No relation recorded for this node."}
          </p>
        ) : (
          <ul className="-mx-1 divide-y divide-line">
            {groups.map((group) => {
              const active = relationId === group.relationId;
              const direction = group.src === node.id ? "→" : "←";
              const counterpart = group.src === node.id ? group.dst : group.src;
              return (
                <li key={`${group.kind}|${group.src}|${group.dst}`}>
                  <button
                    type="button"
                    onClick={() => onPickRelation(active ? null : group.relationId)}
                    aria-pressed={active}
                    className={
                      "flex w-full items-baseline justify-between gap-2 px-1 py-1.5 text-left " +
                      "transition-colors duration-100 hover:bg-surface2 " +
                      (active ? "bg-accent-soft" : "")
                    }
                  >
                    <span className="min-w-0">
                      <span className="block font-mono text-code text-ink">
                        {group.kind}{" "}
                        <span className="text-muted">
                          {direction} {displayLabel(counterpart)}
                        </span>
                      </span>
                      <span className="block text-meta text-muted">
                        {group.count > 1
                          ? `${group.count.toLocaleString("en-GB")} relations of this link`
                          : "1 relation"}
                      </span>
                    </span>
                    <span className="shrink-0 text-meta text-muted">
                      {active ? "shown" : "refs"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {truncated ? (
          <p className="mt-2 text-meta text-muted">
            Grouped from the first {relations.length} of{" "}
            {relationTotal.toLocaleString("en-GB")} relations.
          </p>
        ) : null}
      </RailSection>

      <RailSection title="Provenance" meta={relationId ? "Q6" : undefined}>
        {!relationId ? (
          <p className="text-meta text-muted">
            Pick a relation above to read the refs recorded for it.
          </p>
        ) : provenanceError ? (
          <p className="text-meta text-muted">
            The provenance query did not answer. No refs are invented to fill the gap.
          </p>
        ) : provenanceLoading ? (
          <p className="text-meta text-muted">Reading provenance…</p>
        ) : provenanceRows.length === 0 ? (
          <p className="text-meta text-muted">
            No provenance ref recorded for this relation in this slice — the relation
            exists, its source refs were not ingested.
          </p>
        ) : (
          <ul className="space-y-2">
            {provenanceRows.map((row, index) => (
              <li key={index} className="border-l-2 border-line pl-3">
                <div className="font-mono text-code break-all text-ink">
                  {String(row.ref_kind ?? "ref")} · {truncate(row.ref_id ?? "—", 60)}
                </div>
                <div className="text-meta text-muted">
                  {String(row.source_family_id ?? "unknown family")}
                  {row.extract_method ? ` · ${String(row.extract_method)}` : ""}
                  {row.run_id ? ` · run ${shortAddress(row.run_id)}` : ""}
                </div>
              </li>
            ))}
          </ul>
        )}
      </RailSection>
    </div>
  );
}

function displayLabel(nodeId: string): string {
  return displayName({ id: nodeId, label: nodeId, kind: nodeId.split(":")[0] ?? "" });
}

/** What a status MEANS, not just its code — a code alone is not an answer. */
export function statusMeaning(status: string): string {
  switch (String(status ?? "").toUpperCase()) {
    case "OK":
      return "The query answered.";
    case "NO_PATH":
      return "No dependency path was found in this dataset: the signed-dependency family is not populated in the demonstrated slice.";
    case "NOT_INGESTED":
      return "This id is not in the demonstrated dataset — nothing was invented to fill it.";
    case "NO_OPEN_CONTRADICTIONS":
      return "No unresolved contradiction pair is recorded in this slice.";
    case "SCHEMA_UNSUPPORTED":
      return "This database version does not carry the tables this query needs.";
    case "BAD_ARGS":
      return "One argument is outside its bound; the query was refused, not trimmed.";
    case "DB_NOT_FOUND":
      return "The graph database was not found at the configured path.";
    case "UNKNOWN_QUERY":
      return "Unknown query name.";
    default:
      return "";
  }
}

/** Compact record-query result: the rail is the only place rows are shown. */
export function QueryResultBlock({
  result,
  isFetching,
  error,
}: {
  result: GraphQueryResult | null;
  isFetching: boolean;
  error: boolean;
}) {
  const rows = (result?.rows as Record<string, unknown>[] | undefined) ?? [];
  const columns = useMemo(() => {
    const keys: string[] = [];
    for (const row of rows.slice(0, 12)) {
      for (const key of Object.keys(row)) if (!keys.includes(key)) keys.push(key);
    }
    return keys.slice(0, 4);
  }, [rows]);

  if (error) {
    return <p className="text-meta text-muted">The query did not answer (API error).</p>;
  }
  if (isFetching) return <p className="text-meta text-muted">Running…</p>;
  if (!result) {
    return (
      <p className="text-meta text-muted">
        No query run yet. The canvas already shows the default neighbourhood; run a
        question to record its answer here.
      </p>
    );
  }
  const status = String(result.status ?? "OK");
  const count = Number(result.count ?? rows.length);
  const meaning = statusMeaning(status);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge variant={status === "OK" ? "ok" : "neutral"}>{status}</Badge>
        <Badge variant="neutral">
          {count.toLocaleString("en-GB")} row{count === 1 ? "" : "s"}
        </Badge>
        {typeof result.latency_ms === "number" ? (
          <Badge variant="neutral">{fmtNumber(result.latency_ms, 1)} ms</Badge>
        ) : null}
      </div>
      {meaning ? <p className="text-meta text-muted">{meaning}</p> : null}
      {rows.length > 0 ? (
        <div className="overflow-auto border border-line">
          <table className="w-full text-table">
            <thead className="border-b border-line-strong bg-surface2">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column}
                    className="whitespace-nowrap px-2 py-1.5 text-left text-meta font-semibold text-muted"
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.slice(0, 8).map((row, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td
                      key={column}
                      className="max-w-[160px] truncate whitespace-nowrap px-2 py-1.5 font-mono text-code text-ink"
                    >
                      {cell(row[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {rows.length > 8 ? (
        <p className="text-meta text-muted">
          Showing 8 of {count.toLocaleString("en-GB")} rows.
        </p>
      ) : null}
    </div>
  );
}

function cell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return fmtNumber(value, 2);
  if (typeof value === "object") return truncate(JSON.stringify(value), 40);
  return truncate(String(value), 40);
}
