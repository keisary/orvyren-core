/**
 * Query subgraph: the ONLY thing the graph canvas is allowed to draw.
 *
 * ART_DIRECTION.md §2 — "the graph never shows the world, it shows an answer
 * to a question". This module turns the full payload (16k nodes / 13k
 * relations) into a bounded, legible subgraph:
 *
 *  - BFS from one root, `depth` hops (1..3), never more than NODE_BUDGET nodes;
 *  - high-degree protocol contracts are AGGREGATED: drawn once, carrying the
 *    count of relations they stand for, and never expanded (`DEPOSITED_IN`
 *    ×4 873 must not become 4 873 lines);
 *  - parallel relations between two drawn nodes collapse into ONE edge that
 *    keeps its relation count and the dominant relation id (so provenance can
 *    still be asked: Q6 on that id);
 *  - the count of reachable-but-not-drawn neighbours is returned, never
 *    silently dropped;
 *  - layout is deterministic (concentric rings by hop + hash jitter), so the
 *    same query always paints the same picture — no force atlas, no camera
 *    jumps, no random seed to re-learn.
 *
 * Pure functions only (no React, no DOM): the legibility rules are testable
 * without a browser.
 */

import type { GraphEdge, GraphNode, GraphPayload } from "@/lib/types";

/** Hard budget: a page never renders more than ~40 nodes (ART_DIRECTION §2.2). */
export const NODE_BUDGET = 40;
/** Drawn edges are capped too: 40 nodes still allow 780 pairs. */
export const EDGE_BUDGET = 90;
/** A node at/above this degree is a protocol hub, collapsed into one badge. */
export const HUB_DEGREE = 250;

export type LabelMode = "node" | "relation" | "none";

export interface AdjacencyEntry {
  edgeId: string;
  kind: string;
  other: string;
  direction: "out" | "in";
}

export interface GraphIndex {
  nodeById: Map<string, GraphNode>;
  adjacency: Map<string, AdjacencyEntry[]>;
  degree: Map<string, number>;
  edges: GraphEdge[];
  totals: { nodes: number; relations: number };
}

export interface ViaRelation {
  edgeId: string;
  relationId: string;
  kind: string;
  direction: "out" | "in";
  parent: string;
}

export interface SubgraphNode {
  id: string;
  label: string;
  kind: string;
  cls: string;
  degree: number;
  size: number;
  x: number;
  y: number;
  /** 0 = root, 1..depth = BFS hop. */
  hop: number;
  /** True when the node stands for all its relations (protocol hub). */
  aggregated: boolean;
  /** Relations this node stands for (full degree for an aggregated hub). */
  relationCount: number;
  via: ViaRelation | null;
}

export interface SubgraphEdge {
  id: string;
  source: string;
  target: string;
  /** Dominant relation kind of the collapsed pair. */
  kind: string;
  /** How many relations this one line stands for. */
  count: number;
  /** Representative relation id — the handle for Q6 provenance. */
  relationId: string;
}

export type SubgraphStatus = "OK" | "NO_ROOT" | "ROOT_NOT_FOUND";

export interface Subgraph {
  root: string;
  depth: number;
  status: SubgraphStatus;
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
  /** Reachable at this depth but excluded by the node budget. */
  hiddenNodes: number;
  /** Every relation between drawn nodes (collapsed or not). */
  relationsInView: number;
  /** Relations collapsed into a drawn edge (relationsInView - edges.length). */
  mergedRelations: number;
  /** Aggregated hub nodes among the drawn ones. */
  aggregatedNodes: number;
  totals: { nodes: number; relations: number };
}

/** One pass over the payload; memoise it, it is O(nodes + edges). */
export function indexGraph(payload: GraphPayload): GraphIndex {
  const nodeById = new Map<string, GraphNode>();
  for (const node of payload.nodes) nodeById.set(node.id, node);

  const adjacency = new Map<string, AdjacencyEntry[]>();
  const degree = new Map<string, number>();
  const push = (from: string, entry: AdjacencyEntry) => {
    const list = adjacency.get(from);
    if (list) list.push(entry);
    else adjacency.set(from, [entry]);
    degree.set(from, (degree.get(from) ?? 0) + 1);
  };
  for (const edge of payload.edges) {
    push(edge.source, {
      edgeId: edge.id,
      kind: edge.kind,
      other: edge.target,
      direction: "out",
    });
    push(edge.target, {
      edgeId: edge.id,
      kind: edge.kind,
      other: edge.source,
      direction: "in",
    });
  }
  return {
    nodeById,
    adjacency,
    degree,
    edges: payload.edges,
    totals: { nodes: payload.nodes.length, relations: payload.edges.length },
  };
}

function nodeSize(degree: number): number {
  const size = 3.6 + 2.4 * Math.log10(1 + Math.max(0, degree));
  return Math.round(Math.min(11, Math.max(3.6, size)) * 10) / 10;
}

function hash01(text: string): number {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

interface Visited {
  id: string;
  hop: number;
  via: ViaRelation | null;
}

/** Wide canvases are the norm: rings become ellipses so the frame is used. */
const ASPECT = 1.7;
/** Nodes per turn before a crowded ring opens a wider sub-ring. */
const PER_RING = 14;

/**
 * Concentric layout: hop 0 at the centre, each hop in its own radius band, so
 * "distance from the answer" is literally the distance on screen. A crowded
 * band splits into sub-rings instead of piling labels on top of each other.
 * Deterministic per node id (jitter), so a re-run is comparable.
 */
function layout(visited: Visited[]): Map<string, { x: number; y: number }> {
  const rings = new Map<number, Visited[]>();
  for (const item of visited) {
    const ring = rings.get(item.hop);
    if (ring) ring.push(item);
    else rings.set(item.hop, [item]);
  }
  const positions = new Map<string, { x: number; y: number }>();
  const hops = [...rings.keys()].sort((a, b) => a - b);
  let bandStart = 0;
  for (const hop of hops) {
    const items = rings.get(hop)!;
    if (hop === 0) {
      for (const item of items) positions.set(item.id, { x: 0, y: 0 });
      bandStart += 1.45;
      continue;
    }
    const turns = Math.max(1, Math.ceil(items.length / PER_RING));
    items.forEach((item, index) => {
      const turn = Math.floor(index / PER_RING);
      const slot = index % PER_RING;
      const inTurn = Math.min(PER_RING, items.length - turn * PER_RING);
      const radius = bandStart + 0.62 * turn;
      const jitter = (hash01(item.id) - 0.5) * 0.05;
      const angle = -Math.PI / 2 + (2 * Math.PI * slot) / inTurn + turn * 0.42 + jitter;
      positions.set(item.id, {
        x: Math.round(Math.cos(angle) * radius * ASPECT * 1000) / 1000,
        y: Math.round(Math.sin(angle) * radius * 1000) / 1000,
      });
    });
    bandStart += 0.62 * turns + 0.35;
  }
  return positions;
}

/**
 * Build the bounded subgraph of one query.
 *
 * `depth` is the number of hops from the root (2 by default). Nodes are taken
 * in BFS order — nearest hop first, highest degree first — so the budget always
 * keeps the most connected neighbours of the answer.
 */
export function buildSubgraph(
  index: GraphIndex,
  root: string | null,
  depth: number,
  nodeBudget = NODE_BUDGET,
  edgeBudget = EDGE_BUDGET,
): Subgraph {
  const totals = index.totals;
  const empty: Subgraph = {
    root: root ?? "",
    depth,
    status: root ? "ROOT_NOT_FOUND" : "NO_ROOT",
    nodes: [],
    edges: [],
    hiddenNodes: 0,
    relationsInView: 0,
    mergedRelations: 0,
    aggregatedNodes: 0,
    totals,
  };
  if (!root) return empty;
  if (!index.nodeById.has(root)) return empty;

  const visited: Visited[] = [{ id: root, hop: 0, via: null }];
  const seen = new Set([root]);
  const queue: Visited[] = [{ id: root, hop: 0, via: null }];
  let head = 0;
  while (head < queue.length) {
    const item = queue[head];
    head += 1;
    if (item.hop >= depth) continue;
    // Beyond the first ring a high-degree contract is a LEAF: walking its
    // neighbourhood is exactly the 4 873-line fan this page refuses to draw.
    // At hop 1 it is still expanded — "exposure of a holder" means holder →
    // assets → counterparties, and the node budget (not the hub rule) keeps
    // that legible.
    const isHub = item.id !== root && (index.degree.get(item.id) ?? 0) >= HUB_DEGREE;
    if (isHub && item.hop >= 2) continue;
    const neighbours = [...(index.adjacency.get(item.id) ?? [])];
    neighbours.sort((a, b) => {
      const byDegree =
        (index.degree.get(b.other) ?? 0) - (index.degree.get(a.other) ?? 0);
      return byDegree !== 0 ? byDegree : a.other.localeCompare(b.other);
    });
    for (const neighbour of neighbours) {
      if (seen.has(neighbour.other)) continue;
      if (!index.nodeById.has(neighbour.other)) continue;
      seen.add(neighbour.other);
      const next: Visited = {
        id: neighbour.other,
        hop: item.hop + 1,
        via: {
          edgeId: neighbour.edgeId,
          relationId: neighbour.edgeId,
          kind: neighbour.kind,
          direction: neighbour.direction,
          parent: item.id,
        },
      };
      visited.push(next);
      queue.push(next);
    }
  }

  const drawn = visited.slice(0, Math.max(1, nodeBudget));
  const positions = layout(drawn);
  const drawnIds = new Set(drawn.map((item) => item.id));

  const nodes: SubgraphNode[] = drawn.map((item) => {
    const node = index.nodeById.get(item.id)!;
    const degree = index.degree.get(item.id) ?? 0;
    const aggregated = item.hop >= 2 && degree >= HUB_DEGREE;
    const raw = positions.get(item.id) ?? { x: 0, y: 0 };
    // A collapsed hub sits just outside its ring: it carries a long badge and
    // would otherwise be drawn flush against its highest-degree sibling
    // (neighbours are ordered by degree, so the two biggest are adjacent).
    const position = aggregated ? { x: raw.x * 1.3, y: raw.y * 1.3 } : raw;
    const size = nodeSize(degree) * (item.hop === 0 ? 1.35 : aggregated ? 1.2 : 1);
    // An aggregated contract carries its badge in the label: "… · 1,672
    // relations" is the whole point of not drawing the 1,672 lines.
    const name = canvasLabel(node);
    return {
      id: node.id,
      label: aggregated ? `${name} · ${degree.toLocaleString("en-GB")} relations` : name,
      kind: node.kind || "UNKNOWN",
      cls: node.cls || node.kind || "UNKNOWN",
      degree,
      size: Math.round(size * 10) / 10,
      x: position.x,
      y: position.y,
      hop: item.hop,
      aggregated,
      relationCount: degree,
      via: item.via,
    };
  });

  // Collapse parallel relations into one line per node pair.
  interface Pair {
    source: string;
    target: string;
    kinds: Map<string, number>;
    relationId: string;
    count: number;
  }
  const pairs = new Map<string, Pair>();
  for (const edge of index.edges) {
    if (!drawnIds.has(edge.source) || !drawnIds.has(edge.target)) continue;
    if (edge.source === edge.target) continue;
    const key =
      edge.source < edge.target
        ? `${edge.source}\u0000${edge.target}`
        : `${edge.target}\u0000${edge.source}`;
    const pair = pairs.get(key);
    if (pair) {
      pair.count += 1;
      pair.kinds.set(edge.kind, (pair.kinds.get(edge.kind) ?? 0) + 1);
    } else {
      pairs.set(key, {
        source: edge.source,
        target: edge.target,
        kinds: new Map([[edge.kind, 1]]),
        relationId: edge.id,
        count: 1,
      });
    }
  }
  const relationsInView = [...pairs.values()].reduce((sum, pair) => sum + pair.count, 0);
  const ordered = [...pairs.values()].sort((a, b) => b.count - a.count);
  const edges: SubgraphEdge[] = ordered.slice(0, edgeBudget).map((pair) => {
    const dominant = [...pair.kinds.entries()].sort((a, b) => b[1] - a[1])[0];
    return {
      id: `${pair.source}->${pair.target}`,
      source: pair.source,
      target: pair.target,
      kind: dominant ? dominant[0] : "",
      count: pair.count,
      relationId: pair.relationId,
    };
  });

  return {
    root,
    depth,
    status: "OK",
    nodes,
    edges,
    hiddenNodes: Math.max(0, visited.length - drawn.length),
    relationsInView,
    mergedRelations: Math.max(0, relationsInView - edges.reduce((sum, edge) => sum + edge.count, 0)),
    aggregatedNodes: nodes.filter((node) => node.aggregated).length,
    totals,
  };
}

/** Counts after the legend filter: hidden classes are greyed AND not counted. */
export function recount(subgraph: Subgraph, hidden: Set<string>) {
  const visible = subgraph.nodes.filter((node) => !hidden.has(node.cls));
  const ids = new Set(visible.map((node) => node.id));
  const edges = subgraph.edges.filter(
    (edge) => ids.has(edge.source) && ids.has(edge.target),
  );
  return {
    nodes: visible.length,
    edges: edges.length,
    relations: edges.reduce((sum, edge) => sum + edge.count, 0),
  };
}

/** Node classes present in the subgraph, with their drawn-node counts. */
export function classCounts(subgraph: Subgraph): { cls: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const node of subgraph.nodes) counts.set(node.cls, (counts.get(node.cls) ?? 0) + 1);
  return [...counts.entries()]
    .map(([cls, count]) => ({ cls, count }))
    .sort((a, b) => b.count - a.count || a.cls.localeCompare(b.cls));
}

/* ------------------------------------------------------------------ naming
   Node labels in the dataset are raw ids (`asset:eip155:8453:0x4200…`).
   Printing them verbatim was half of the "undecipherable" complaint: the
   display name keeps the kind and ONE short hex, and the rail always shows
   the untouched id. The four well-known Base contracts below are named so a
   demo reads as an exposure, not as a wall of hex; an unknown address keeps
   its short hex (no invented name).
   ------------------------------------------------------------------------ */

const KNOWN_ACTORS: Record<string, string> = {
  "0x4200000000000000000000000000000000000006": "WETH",
  "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": "USDC",
  "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf": "cbBTC",
  "0xa238dd80c259a72e81d7e4664a9801593f98d1c5": "Aave v3",
};

/** Kinds whose id is `protocol:asset` — painted as `Kind ASSET` on canvas. */
const INSTRUMENT_KINDS = new Set(["MARCHE", "DETTE", "POSITION", "CONTRAT"]);

const KIND_LABEL: Record<string, string> = {
  ADRESSE: "Account",
  ACTIF: "Asset",
  STABLECOIN: "Stablecoin",
  MARCHE: "Market",
  POSITION: "Position",
  DETTE: "Debt",
  CONTRAT: "Contract",
  EVENT: "Event",
  PROOF: "Proof",
  ORACLE: "Oracle",
};

export function kindLabel(kind: string): string {
  const key = (kind || "").toUpperCase();
  if (KIND_LABEL[key]) return KIND_LABEL[key];
  const text = key.toLowerCase().replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function shortHex(value: string, head = 6, tail = 4): string {
  const text = String(value ?? "");
  if (text.length <= head + tail + 1) return text;
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}

/** Human phrase for a relation enum: `DEPOSITED_IN` → `deposited in`. */
export function relationPhrase(kind: string): string {
  return String(kind ?? "").toLowerCase().replace(/_/g, " ");
}

/**
 * Short form painted ON the canvas: a kind prefix on every one of 40 nodes
 * doubles the label length and half of them collide. Known contracts keep
 * their name, everything else is one short hex — the kind is a tone and a
 * rail field, not a repeated word.
 */
export function canvasLabel(node: Pick<GraphNode, "id" | "label" | "kind">): string {
  const kind = (node.kind || "").toUpperCase();
  const label = String(node.label ?? "");
  const parts = String(node.id ?? "").split(":");
  const addresses = parts.filter((part) => /^0x[0-9a-fA-F]{40}$/.test(part));
  const named = addresses
    .map((address) => KNOWN_ACTORS[address.toLowerCase()])
    .filter((name): name is string => Boolean(name));
  if (named.length > 0) {
    // Instrument nodes (market / debt / position) are addressed by a
    // protocol + asset pair; on canvas the protocol is the page context and
    // the pair is what collides with its sibling, so only the kind word and
    // the asset are painted. The rail still spells the pair out.
    if (INSTRUMENT_KINDS.has(kind) && named.length > 1) {
      return `${kindLabel(kind)} ${named[named.length - 1]}`;
    }
    const name = named.join(" / ");
    return kind === "ACTIF" || kind === "STABLECOIN" ? name : `${kindLabel(kind)} ${name}`;
  }
  if (kind === "EVENT" && label && !label.includes(":eip155:")) {
    const words = label.toLowerCase().replace(/_/g, " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
  }
  if (addresses.length > 0) return shortHex(addresses[addresses.length - 1], 6, 4);
  if (label && !label.includes(":eip155:")) return label;
  return shortHex(parts[parts.length - 1] ?? node.id, 8, 4);
}

export function displayName(node: Pick<GraphNode, "id" | "label" | "kind">): string {
  const kind = (node.kind || "").toUpperCase();
  const label = String(node.label ?? "");
  const parts = String(node.id ?? "").split(":");
  const addresses = parts.filter((part) => /^0x[0-9a-fA-F]{40}$/.test(part));

  if (kind === "EVENT" && label && !label.includes(":eip155:")) {
    const words = label.toLowerCase().replace(/_/g, " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
  }
  const named = addresses
    .map((address) => KNOWN_ACTORS[address.toLowerCase()])
    .filter((name): name is string => Boolean(name));
  if (named.length > 0) return `${kindLabel(kind)} ${named.join(" / ")}`;
  if (addresses.length > 0) {
    return `${kindLabel(kind)} ${shortHex(addresses[addresses.length - 1])}`;
  }
  if (label && !label.includes(":eip155:")) return label;
  return shortHex(parts[parts.length - 1] ?? node.id, 10, 4);
}

/** Ordered node ids for the pickers: most connected first. */
export function topNodes(index: GraphIndex, limit = 40): GraphNode[] {
  return [...index.nodeById.values()]
    .sort(
      (a, b) =>
        (index.degree.get(b.id) ?? 0) - (index.degree.get(a.id) ?? 0) ||
        a.id.localeCompare(b.id),
    )
    .slice(0, limit);
}

/**
 * Seed of the page. A demo root must produce a *readable* picture: some
 * addresses have 600 relations but only two distinct neighbours (a long
 * history of HOLDS), which paints three dots. Candidates are tried in order
 * and the first one with a real neighbourhood wins; otherwise the most
 * connected node. Nothing is invented when the dataset has neither.
 */
const SEED_CANDIDATES = [
  // WETH on Base — ~106 neighbours at 2 hops: assets, markets, holders.
  "asset:eip155:8453:0x4200000000000000000000000000000000000006",
  // Aave v3 USDC market — 5 neighbours, 15 at 2 hops: the cleanest exposure.
  "market:eip155:8453:0xa238dd80c259a72e81d7e4664a9801593f98d1c5:0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
];

export function pickDefaultRoot(index: GraphIndex): string | null {
  for (const candidate of SEED_CANDIDATES) {
    if (!index.nodeById.has(candidate)) continue;
    const probe = buildSubgraph(index, candidate, 2);
    if (probe.nodes.length >= 8) return candidate;
  }
  return topNodes(index, 1)[0]?.id ?? null;
}

/**
 * Accept an address or a bare node id and return the id that exists in the
 * payload — no silent guess: `null` means "this dataset has no such node".
 */
export function resolveNodeId(index: GraphIndex, raw: string | null | undefined): string | null {
  const value = String(raw ?? "").trim();
  if (!value) return null;
  if (index.nodeById.has(value)) return value;
  if (/^0x[0-9a-fA-F]{40}$/.test(value)) {
    const lower = value.toLowerCase();
    for (const kind of ["addr", "asset", "market", "position", "debt"]) {
      const candidate = `${kind}:eip155:8453:${lower}`;
      if (index.nodeById.has(candidate)) return candidate;
    }
    for (const node of index.nodeById.values()) {
      if (String(node.address ?? "").toLowerCase() === lower) return node.id;
    }
  }
  return null;
}
