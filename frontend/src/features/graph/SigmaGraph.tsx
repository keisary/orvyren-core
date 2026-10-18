import { useEffect, useMemo, useRef, useState } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import type { GraphPayload } from "@/lib/types";

/** Canvas Sigma.js v3 (WebGL) — un seul contexte WebGL à l'écran. */

const PALETTE = [
  "#22d3ee", "#818cf8", "#34d399", "#fbbf24", "#f472b6",
  "#60a5fa", "#a3e635", "#fb923c", "#c084fc", "#2dd4bf",
  "#f87171", "#94a3b8",
];

const BG = "#070b11";
const DIM = "#22344a";
const DIM_EDGE = "#16233a";

function layoutKey(version: string) {
  return `orvyren:layout:${version}`;
}

interface Props {
  payload: GraphPayload;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onLayout?: (state: "cached" | "computing" | "done") => void;
}

export default function SigmaGraph({ payload, selected, onSelect, onLayout }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  // Reducers are built ONCE per payload: they must read the focus through a
  // ref, otherwise they keep the ``selected``/``hovered`` of the build render
  // and the dim/highlight never reacts to clicks and hovers.
  const focusRef = useRef<string | null>(null);

  const colors = useMemo(() => {
    const mapping: Record<string, string> = {};
    Object.keys(payload.classes)
      .sort()
      .forEach((cls, index) => {
        mapping[cls] = PALETTE[index % PALETTE.length];
      });
    return mapping;
  }, [payload]);

  const adjacency = useMemo(() => {
    const map: Record<string, Set<string>> = {};
    for (const edge of payload.edges) {
      (map[edge.source] ??= new Set()).add(edge.target);
      (map[edge.target] ??= new Set()).add(edge.source);
    }
    return map;
  }, [payload]);

  // Build + render
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const cached = window.localStorage.getItem(layoutKey(payload.graph_version));
    let positions: Record<string, [number, number]> | null = null;
    if (cached) {
      try {
        positions = JSON.parse(cached) as Record<string, [number, number]>;
        onLayout?.("cached");
      } catch {
        positions = null;
      }
    }
    if (!positions) onLayout?.("computing");

    const graph = new Graph({ multi: true, type: "directed" });
    for (const node of payload.nodes) {
      const position = positions?.[node.id];
      graph.addNode(node.id, {
        x: position ? position[0] : node.x,
        y: position ? position[1] : node.y,
        size: node.size,
        color: colors[node.cls] ?? "#22d3ee",
        label: node.label,
      });
    }
    for (const [index, edge] of payload.edges.entries()) {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        // graphology keys must be unique: a repeated relation id (revisions)
        // gets a suffixed key instead of throwing and killing the canvas.
        const key = graph.hasEdge(edge.id) ? `${edge.id}#${index}` : edge.id;
        graph.addEdgeWithKey(key, edge.source, edge.target, {
          size: 0.6,
          color: DIM_EDGE,
          hidden: false,
        });
      }
    }

    // Sigma perf settings ("Improve rendering performances", 16k nodes):
    // minimal primitives (edge "line" = 4 vertices, never arrow/triangle), no
    // edge events (avoids a second picking render pass), full colours (never
    // opacity < 1), reduced anti-aliasing via antiAliasingFeather (the
    // `antialiasEdges` option only exists in sigma v4: kept for the upgrade,
    // ignored by 3.0.3), labels culled by density AND by rendered size.
    const settings = {
      renderEdgeLabels: false,
      enableEdgeEvents: false,
      antialiasEdges: false,
      defaultEdgeType: "line",
      antiAliasingFeather: 0.5,
      labelFont: "ui-monospace, Consolas, monospace",
      labelSize: 10,
      labelColor: { color: "#8fa3bb" },
      labelDensity: 0.08,
      labelGridCellSize: 110,
      labelRenderedSizeThreshold: 8,
      stagePadding: 40,
      minCameraRatio: 0.03,
      maxCameraRatio: 4,
      nodeReducer: (node: string, attrs: Record<string, unknown>) => {
        const focus = focusRef.current;
        if (!focus) return attrs;
        const visible = node === focus || (adjacency[focus]?.has(node) ?? false);
        return {
          ...attrs,
          color: visible ? attrs.color : DIM,
          label: visible ? attrs.label : "",
          zIndex: visible ? 1 : 0,
        };
      },
      edgeReducer: (edge: string, attrs: Record<string, unknown>) => {
        const focus = focusRef.current;
        if (!focus) return { ...attrs, color: DIM_EDGE };
        const source = graph.source(edge);
        const target = graph.target(edge);
        const visible = source === focus || target === focus;
        return {
          ...attrs,
          color: visible ? "#22d3ee" : DIM_EDGE,
          size: visible ? 1.4 : 0.4,
          zIndex: visible ? 2 : 0,
        };
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;

    const sigma = new Sigma(graph, container, settings);
    sigmaRef.current = sigma;

    sigma.on("clickNode", ({ node }) => onSelect(node));
    sigma.on("clickStage", () => onSelect(null));
    sigma.on("enterNode", ({ node }) => setHovered(node));
    sigma.on("leaveNode", () => setHovered(null));

    // Layout FA2 en worker (une fois), positions persistées par graph_version.
    if (!positions) {
      const worker = new Worker(new URL("./fa2.worker.ts", import.meta.url), {
        type: "module",
      });
      workerRef.current = worker;
      worker.onmessage = (event: MessageEvent<{ positions: Record<string, [number, number]> }>) => {
        const computed = event.data.positions;
        for (const node of payload.nodes) {
          const position = computed[node.id];
          if (position) {
            graph.setNodeAttribute(node.id, "x", position[0]);
            graph.setNodeAttribute(node.id, "y", position[1]);
        }
        }
        try {
          window.localStorage.setItem(
            layoutKey(payload.graph_version),
            JSON.stringify(computed),
          );
        } catch {
          // quota dépassé : le layout restera non persisté, pas bloquant
        }
        onLayout?.("done");
        worker.terminate();
        workerRef.current = null;
      };
      worker.postMessage({
        nodes: payload.nodes.map((n) => ({ id: n.id, x: n.x, y: n.y })),
        edges: payload.edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
        iterations: 120,
      });
    }

    return () => {
      workerRef.current?.terminate();
      workerRef.current = null;
      sigma.kill();
      sigmaRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payload, colors, adjacency, onSelect]);

  // Focus changes must repaint through the reducers (they read ``focusRef``).
  useEffect(() => {
    focusRef.current = hovered ?? selected;
    sigmaRef.current?.refresh();
  }, [hovered, selected]);

  // Recentre la caméra sur le nœud sélectionné.
  useEffect(() => {
    const sigma = sigmaRef.current;
    if (!sigma || !selected) return;
    const graph = sigma.getGraph();
    if (!graph.hasNode(selected)) return;
    const camera = sigma.getCamera();
    camera.animate(
      { x: graph.getNodeAttribute(selected, "x"), y: graph.getNodeAttribute(selected, "y"), ratio: 0.12 },
      { duration: 350 },
    );
  }, [selected]);

  return <div ref={containerRef} className="h-full w-full" />;
}
