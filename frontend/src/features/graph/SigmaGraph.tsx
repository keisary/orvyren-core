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
    for (const edge of payload.edges) {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        graph.addEdgeWithKey(edge.id, edge.source, edge.target, {
          size: 0.6,
          color: DIM_EDGE,
          hidden: false,
        });
      }
    }

    // Réglages perf Sigma vérifiés (doc « Improve rendering performances ») :
    // pas d'anti-aliasing sur les arêtes, pas d'événements d'arêtes, couleurs
    // pleines (jamais d'opacité < 1), primitives minimales.
    const settings = {
      renderEdgeLabels: false,
      enableEdgeEvents: false,
      antialiasEdges: false,
      labelFont: "ui-monospace, Consolas, monospace",
      labelSize: 10,
      labelColor: { color: "#8fa3bb" },
      labelDensity: 0.08,
      labelGridCellSize: 110,
      stagePadding: 40,
      minCameraRatio: 0.03,
      maxCameraRatio: 4,
      nodeReducer: (node: string, attrs: Record<string, unknown>) => {
        const focus = hovered ?? selected;
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
        const focus = hovered ?? selected;
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
