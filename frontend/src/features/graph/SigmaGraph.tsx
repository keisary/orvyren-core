import { useEffect, useMemo, useRef, useState } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import type { GraphPayload } from "@/lib/types";
import { colorsForClasses, cssVar, FALLBACK } from "@/lib/graph-theme";

/** Sigma.js v3 canvas (WebGL) — a single WebGL context on screen.
 *
 *  Fixes vs the previous version (§4.8):
 *  - tones come from the class NAME (stable across payloads), never from a
 *    sort index that silently reassigns colors;
 *  - node events enabled — hover focus actually works now;
 *  - no camera animation on selection (the view never jumps by itself);
 *  - zoom controls are explicit buttons, labels at 12px ink on ivory.
 */

function layoutKey(version: string) {
  return `orvyren:layout:${version}`;
}

interface Props {
  payload: GraphPayload;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onLayout?: (state: "cached" | "computing" | "done" | "served" | "failed") => void;
}

export default function SigmaGraph({ payload, selected, onSelect, onLayout }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  // Reducers are built ONCE per payload: they must read the focus through a
  // ref, otherwise they keep the ``selected``/``hovered`` of the build render
  // and the dim/highlight never reacts to clicks and hovers.
  const focusRef = useRef<string | null>(null);

  const colors = useMemo(() => colorsForClasses(payload.classes), [payload]);

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

    const surface = cssVar("--color-surface", FALLBACK.surface);
    const ink = cssVar("--color-ink", FALLBACK.ink);
    const dim = cssVar("--color-graph-dim", FALLBACK.graphDim);
    const edgeDim = cssVar("--color-graph-edge", FALLBACK.graphEdge);
    const accent = cssVar("--color-accent", FALLBACK.accent);
    const fallbackNode = cssVar("--color-graph-node", FALLBACK.graphNode);

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
        color: colors[node.cls] ?? fallbackNode,
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
          color: edgeDim,
          hidden: false,
        });
      }
    }

    // Sigma perf settings (16k nodes): minimal primitives (edge "line"),
    // no edge events (avoids a second picking render pass), full colours
    // (never opacity < 1), reduced anti-aliasing. Node events ARE enabled —
    // without them enterNode/leaveNode never fire and hover focus is dead.
    const settings = {
      backgroundColor: surface,
      renderEdgeLabels: false,
      enableEdgeEvents: false,
      enableNodeEvents: true,
      antialiasEdges: false,
      defaultEdgeType: "line",
      antiAliasingFeather: 0.5,
      labelFont: 'Consolas, "Cascadia Mono", monospace',
      labelSize: 12,
      labelColor: { color: ink },
      labelDensity: 0.1,
      labelGridCellSize: 120,
      labelRenderedSizeThreshold: 7,
      stagePadding: 40,
      minCameraRatio: 0.03,
      maxCameraRatio: 4,
      nodeReducer: (node: string, attrs: Record<string, unknown>) => {
        const focus = focusRef.current;
        if (!focus) return attrs;
        const visible = node === focus || (adjacency[focus]?.has(node) ?? false);
        return {
          ...attrs,
          color: visible ? attrs.color : dim,
          label: visible ? attrs.label : "",
          zIndex: visible ? 1 : 0,
        };
      },
      edgeReducer: (edge: string, attrs: Record<string, unknown>) => {
        const focus = focusRef.current;
        if (!focus) return { ...attrs, color: edgeDim };
        const source = graph.source(edge);
        const target = graph.target(edge);
        const visible = source === focus || target === focus;
        return {
          ...attrs,
          color: visible ? accent : edgeDim,
          size: visible ? 1.4 : 0.4,
          zIndex: visible ? 2 : 0,
        };
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;

    let sigma: Sigma;
    try {
      sigma = new Sigma(graph, container, settings);
    } catch {
      // WebGL unavailable: say so honestly, the REST queries stay usable.
      setFailed(true);
      onLayout?.("failed");
      return;
    }
    sigmaRef.current = sigma;

    sigma.on("clickNode", ({ node }) => onSelect(node));
    sigma.on("clickStage", () => onSelect(null));
    sigma.on("enterNode", ({ node }) => setHovered(node));
    sigma.on("leaveNode", () => setHovered(null));

    // FA2 layout in a worker (once), positions persisted per graph_version.
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
          // quota exceeded: the layout stays unpersisted, not blocking
        }
        onLayout?.("done");
        worker.terminate();
        workerRef.current = null;
      };
      // If the worker fails, fall back to the served coordinates — never get
      // stuck on "computing" (the hint must keep telling the truth).
      worker.onerror = () => {
        onLayout?.("served");
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
  // Selection never moves the camera by itself (§4.8) — only the buttons do.
  useEffect(() => {
    focusRef.current = hovered ?? selected;
    sigmaRef.current?.refresh();
  }, [hovered, selected]);

  const reducedMotion = () =>
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const zoom = (factor: number) => {
    const sigma = sigmaRef.current;
    if (!sigma) return;
    const camera = sigma.getCamera();
    const current = camera.getState();
    const ratio = Math.min(4, Math.max(0.03, current.ratio * factor));
    if (reducedMotion()) camera.setState({ ...current, ratio });
    else camera.animate({ ...current, ratio }, { duration: 200 });
  };

  const resetView = () => {
    const sigma = sigmaRef.current;
    if (!sigma) return;
    const target = { x: 0.5, y: 0.5, ratio: 1 };
    if (reducedMotion()) sigma.getCamera().setState(target);
    else sigma.getCamera().animate(target, { duration: 250 });
  };

  const controlClass =
    "flex h-8 w-8 items-center justify-center border border-line bg-surface " +
    "font-mono text-[14px] leading-none text-ink transition-colors duration-100 " +
    "hover:border-line-strong hover:bg-surface2 " +
    "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent";

  return (
    <div className="relative h-full w-full">
      {failed ? (
        <div className="flex h-full items-center justify-center px-6 text-center text-meta text-muted">
          Canvas unavailable (WebGL failed) — the queries and tables remain
          available.
        </div>
      ) : (
        <div ref={containerRef} className="h-full w-full" />
      )}
      {failed ? null : (
        <div className="absolute right-2 top-2 flex flex-col gap-1">
          <button type="button" className={controlClass} onClick={() => zoom(0.8)} aria-label="Zoom in" title="Zoom in">
            +
          </button>
          <button type="button" className={controlClass} onClick={() => zoom(1.25)} aria-label="Zoom out" title="Zoom out">
            −
          </button>
          <button
            type="button"
            className={controlClass}
            onClick={resetView}
            aria-label="Reset view"
            title="Reset view"
          >
            ⤾
          </button>
        </div>
      )}
    </div>
  );
}
