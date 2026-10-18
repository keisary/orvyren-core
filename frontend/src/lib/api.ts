import type {
  AuditStream,
  AuditSummary,
  EpisodeIndexItem,
  EpisodeSeries,
  GraphPayload,
  GraphQueryResult,
  JournalEntry,
  PolicyDemo,
  ReceiptsPayload,
  RunBundle,
  RunEvent,
  RunSummary,
  RunVerification,
} from "./types";

/** Client REST minimaliste — mêmes origines, 100 % offline. */

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} — ${path}`);
  }
  return (await response.json()) as T;
}

export const api = {
  health: () =>
    get<{
      status: string;
      version: string;
      graph_db: string;
      graph_db_absent: boolean;
      frontend_built: boolean;
    }>("/api/health"),

  runs: () => get<{ runs: RunSummary[]; count: number }>("/api/runs"),
  run: (id: string) => get<RunBundle>(`/api/runs/${encodeURIComponent(id)}`),
  runJournal: (id: string, agent: string, afterSeq = 0, limit = 300) =>
    get<{ run_id: string; agent: string; total: number; returned: number; entries: JournalEntry[] }>(
      `/api/runs/${encodeURIComponent(id)}/journal?agent=${agent}&after_seq=${afterSeq}&limit=${limit}`,
    ),
  runEvents: (id: string, afterSeq = 0, limit = 300) =>
    get<{ run_id: string; total: number; returned: number; events: RunEvent[] }>(
      `/api/runs/${encodeURIComponent(id)}/events?after_seq=${afterSeq}&limit=${limit}`,
    ),
  runVerify: (id: string) =>
    get<RunVerification>(`/api/runs/${encodeURIComponent(id)}/verify`),

  graphFull: () => get<GraphPayload>("/api/graph/full"),
  graphInfo: () => get<Record<string, unknown>>("/api/graph/info"),
  graphNode: (id: string) =>
    get<Record<string, unknown>>(`/api/graph/node/${encodeURIComponent(id)}`),
  graphNeighbors: (id: string, depth = 1) =>
    get<{ root: string; depth: number; nodes: string[]; edges: Record<string, unknown>[] }>(
      `/api/graph/neighbors/${encodeURIComponent(id)}?depth=${depth}`,
    ),
  graphQuery: (name: string, params: Record<string, string | number | undefined>) => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") search.set(key, String(value));
    }
    const qs = search.toString();
    return get<GraphQueryResult>(`/api/graph/query/${name}${qs ? `?${qs}` : ""}`);
  },

  episodes: () =>
    get<{ episodes: EpisodeIndexItem[]; count: number }>("/api/market/episodes"),
  episode: (id: string) =>
    get<Record<string, unknown>>(`/api/market/episodes/${encodeURIComponent(id)}`),
  episodeSeries: (id: string) =>
    get<EpisodeSeries>(`/api/market/series?episode=${encodeURIComponent(id)}`),
  corpus: () => get<Record<string, unknown>>("/api/market/corpus"),

  decisionCases: () => get<{ cases: string[] }>("/api/decision/cases"),
  decision: (caseId: string) =>
    get<Record<string, unknown>>(`/api/decision/${encodeURIComponent(caseId)}`),
  decisionRecord: (caseId: string) =>
    get<Record<string, unknown>>(`/api/decision/${encodeURIComponent(caseId)}/record`),

  policyVerdicts: () => get<PolicyDemo>("/api/policy/verdicts"),
  policyEffective: () => get<Record<string, unknown>>("/api/policy/effective"),
  executionIntents: () =>
    get<{
      cases: PolicyDemo["cases"];
      guard_blocks: string[];
      execution_config: Record<string, unknown>;
      expected_verdicts: Record<string, string>;
    }>("/api/execution/intents"),
  executionReceipts: () => get<ReceiptsPayload>("/api/execution/receipts"),

  auditSummary: () => get<AuditSummary>("/api/audit/summary"),
  auditStream: (afterSeq = 0, limit = 100) =>
    get<AuditStream>(`/api/audit/stream?after_seq=${afterSeq}&limit=${limit}`),
};
