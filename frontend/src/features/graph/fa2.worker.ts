/// <reference lib="webworker" />
// ForceAtlas2 en Web Worker : calculé une fois, positions persistées côté
// client (le layout est le calcul le plus coûteux de la feature graphe).
import Graph from "graphology";
import fa2Layout, { inferSettings } from "graphology-layout-forceatlas2";

export interface WorkerNode {
  id: string;
  x: number;
  y: number;
}
export interface WorkerEdge {
  id: string;
  source: string;
  target: string;
}

interface Request {
  nodes: WorkerNode[];
  edges: WorkerEdge[];
  iterations: number;
}

self.onmessage = (event: MessageEvent<Request>) => {
  const { nodes, edges, iterations } = event.data;
  const graph = new Graph({ multi: true, type: "directed" });
  for (const node of nodes) {
    if (!graph.hasNode(node.id)) {
      graph.addNode(node.id, { x: node.x, y: node.y, size: 1 });
    }
  }
  for (const edge of edges) {
    if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
      graph.addEdgeWithKey(edge.id, edge.source, edge.target, {});
    }
  }
  const settings = inferSettings(graph);
  const positions = fa2Layout(graph, { settings, iterations });
  const payload: Record<string, [number, number]> = {};
  for (const [id, position] of Object.entries(positions) as [
    string,
    { x: number; y: number },
  ][]) {
    payload[id] = [position.x, position.y];
  }
  (self as unknown as Worker).postMessage({ positions: payload });
};
