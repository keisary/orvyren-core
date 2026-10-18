/** Types of the real artefacts served by the API (aligned on src/orvyren/api). */

/** Declared substitution of the rsETH scenario (honest replay disclosure). */
export interface ScenarioSubstitution {
  declared: boolean;
  banner: string;
  case_id: string;
  agents_run_id?: string;
  executor_run_id?: string;
  execution_leg?: string;
  execution_probe_refusal?: string;
  agents_abstention?: string;
  epistemic_verdict?: string;
  state?: string;
  stop_condition?: string;
  budget?: Record<string, number>;
  budget_used?: Record<string, number>;
  sources?: string[];
}

export interface JournalSummary {
  present: boolean;
  lines: number;
  kinds: Record<string, number>;
  agent_ids?: string[];
}

export interface RunSummary {
  run_id: string;
  path: string;
  case_id: string;
  mode: string;
  created_at: string;
  schema: string;
  state: string;
  stop_condition: string;
  inconclusive: boolean | null;
  motif: string;
  budget: Record<string, number>;
  budget_used: Record<string, number>;
  hypotheses: number;
  lacunes: number;
  journals: { orchestrator: JournalSummary; critic: JournalSummary };
  exchanges: string[];
  has_store: boolean;
  chain_heads: Record<string, string>;
  substitution?: ScenarioSubstitution | null;
}

export interface Hypothesis {
  id: string;
  enonce: string;
  etat: string;
  p: string;
  criteres: Record<string, string>;
}

export interface RunSpec {
  schema: string;
  run_id: string;
  case_id: string;
  mode: string;
  created_at: string;
  budget: Record<string, number>;
  hypotheses: Hypothesis[];
  lacunes: { lacune_id: string; question: string }[];
  snapshot: Record<string, unknown>;
  tool_fixtures?: Record<string, unknown>;
  store_dir?: string;
}

export interface JournalEntry {
  seq: number;
  journal_id: string;
  run_id: string;
  episode_id: string;
  agent_id: string;
  role_version: string;
  step_index: number;
  ts_utc: string;
  kind: string;
  content: string;
  refs: string[];
  status: string;
  validation: Record<string, unknown>;
  llm: Record<string, unknown>;
  prompt_hash: string;
  response_hash: string;
  tokens_in: number;
  tokens_out: number;
  cached_in: number;
  cost_usd: number;
  latency_ms: number;
  prev_hash: string;
}

export interface RunEvent {
  seq: number;
  type: string;
  run_id: string;
  ts: string;
  payload: Record<string, unknown>;
}

export interface RunBundle {
  run_id: string;
  path: string;
  spec: RunSpec | null;
  outcome: Record<string, unknown> | null;
  run_outcome: Record<string, unknown> | null;
  worker_done_orchestrator: Record<string, unknown> | null;
  worker_done_critic: Record<string, unknown> | null;
  exchanges: { name: string; data: Record<string, unknown> }[];
  tool_calls: Record<string, unknown>[];
  substitution?: ScenarioSubstitution | null;
}

export interface ChainReport {
  present: boolean;
  lines?: number;
  links_ok?: boolean;
  recomputed_head?: string;
  recorded_head?: string;
  verified?: boolean;
  error?: string;
}

export interface RunVerification {
  run_id: string;
  agents: Record<string, ChainReport>;
}

export interface GraphNode {
  id: string;
  label: string;
  kind: string;
  cls: string;
  address: string;
  degree: number;
  size: number;
  x: number;
  y: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: string;
  family: string;
  sign: string;
  amount: number | null;
}

export interface GraphPayload {
  graph_version: string;
  db: string;
  schema: string;
  counts: { nodes: number; edges: number };
  classes: Record<string, number>;
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout: Record<string, unknown>;
  latency_ms: number;
}

export interface GraphQueryResult {
  query: string;
  status?: string;
  rows?: Record<string, unknown>[];
  count?: number;
  latency_ms?: number;
  [key: string]: unknown;
}

export interface EpisodeIndexItem {
  id: string;
  file: string;
  title: string;
  window: Record<string, unknown>;
  points: number;
  headline: Record<string, unknown>;
  events: { utc: string; ts: string; label: string; source: string }[];
  limitations: string[];
}

export interface SeriesLine {
  id: string;
  label: string;
  unit: string;
  kind: string;
  points: [number, number][];
}

export interface EpisodeSeries {
  id: string;
  title: string;
  window: Record<string, unknown>;
  lines: SeriesLine[];
  bars: SeriesLine[];
  events: EpisodeIndexItem["events"];
  headline: Record<string, unknown>;
  notes: string[];
  limitations: string[];
  rpc_provenance: Record<string, unknown>;
}

export interface PolicyRule {
  rule: string;
  result: string;
  note?: string;
  code?: string;
}

export interface PolicyCase {
  intent_id: string;
  action_type: string;
  amount_usdc: number;
  recipient: string;
  verdict: "ALLOW" | "DENY" | "REQUIRE_APPROVAL";
  deny_codes: string[];
  rules_evaluated: PolicyRule[];
  skipped_rules: { rule?: string; reason?: string }[];
  policy_version: string;
  policy_hash: string;
  instruction?: { to: string; calldata: string; note: string };
}

export interface PolicyDemo {
  generated_at: string;
  chain: string;
  mode: string;
  agent_holds_key: boolean;
  policy: Record<string, unknown>;
  policy_state: Record<string, unknown>;
  demo_defaults: Record<string, unknown>;
  execution_config: Record<string, unknown>;
  cases: PolicyCase[];
  guard_blocks: string[];
  period_cap_check: Record<string, unknown>;
  receipt_verification: Record<string, unknown>;
  verdict_check: Record<string, unknown>;
}

export interface Receipt {
  name: string;
  tx_hash: string;
  status: string;
  block_number: string;
  from: string;
  to: string;
  contract_address: string;
  gas_used: string;
  effective_gas_price: string;
  logs: number;
  source: string;
  raw: Record<string, unknown>;
}

export interface ReceiptsPayload {
  setup_receipts: Receipt[];
  chain_receipts: Receipt[];
  tx_hashes?: Record<string, unknown>;
  setup_chain?: Record<string, unknown>;
  simulations?: Record<string, unknown>;
  encodages?: Record<string, unknown>;
}

export interface AuditSnapshot {
  id: string;
  path: string;
  manifest?: string;
  snapshot?: {
    schema: string;
    case_id: string;
    as_of: string;
    counts: { records: number; by_kind: Record<string, number>; by_family: Record<string, number> };
    snapshot_hash: string;
    records: Record<string, unknown>[];
  };
  provenance?: {
    schema: string;
    case_id: string;
    as_of: string;
    chains: unknown[];
    origins: number;
    hashes_complete: boolean;
    provenance_hash: string;
  };
}

export interface AuditChain {
  name: string;
  path: string;
  run_id: string;
  first_kind: string;
  last_kind: string;
  records: number;
  links_ok: boolean;
  head: string;
  genesis_ok: boolean;
  hash_form: string;
  verified: boolean;
}

export interface AuditSummary {
  snapshots: AuditSnapshot[];
  packets: {
    name: string;
    path: string;
    size: number;
    sha256_file?: string;
    files: { name: string; size: number }[];
  }[];
  chains: AuditChain[];
  manifest?: string;
  runs: { run_id: string; verify: RunVerification }[];
  scenario_substitution?: ScenarioSubstitution;
}

export interface AuditStream {
  stream: string;
  total: number;
  returned: number;
  after_seq: number;
  records: Record<string, unknown>[];
  has_more: boolean;
}
