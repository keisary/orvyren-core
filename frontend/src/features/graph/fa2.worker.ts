/// <reference lib="webworker" />
// ForceAtlas2 in a Web Worker: computed once, positions persisted client-side
// (the layout is the most expensive computation of the graph feature).
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
  for (const [index, edge] of edges.entries()) {
    if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
      // Unique keys only: a repeated relation id (revisions) would throw.
      const key = graph.hasEdge(edge.id) ? `${edge.id}#${index}` : edge.id;
      graph.addEdgeWithKey(key, edge.source, edge.target, {});
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
