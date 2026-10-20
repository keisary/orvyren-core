import { useEffect, useMemo, useRef } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { colorsForClasses, cssVar, FALLBACK } from "@/lib/graph-theme";
import type { LabelMode, SubgraphEdge, SubgraphNode } from "./subgraph";

/**
 * Sigma.js v3 canvas — the drawing surface ONLY.
 *
 * Discipline fixed here (ART_DIRECTION §2):
 *  - no control is painted on the canvas: zoom / labels / depth live in the
 *    toolbars above and below it, so nothing covers a node;
 *  - ONE label kind at a time (`node` | `relation` | `none`), never both;
 *  - the graph is built from the bounded query subgraph, never from the full
 *    payload (the screen does not have the budget to pass it 16k nodes);
 *  - layout positions come from the subgraph module (deterministic rings):
 *    no ForceAtlas2 run, so a re-run paints the same picture and the camera
 *    never jumps;
 *  - selection never moves the camera; hover only dims non-neighbours.
 */

export interface GraphCameraApi {
  zoomIn: () => void;
  zoomOut: () => void;
  resetView: () => void;
}

interface Props {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
  classes: Record<string, number>;
  selected: string | null;
  onSelect: (id: string | null) => void;
  labelMode: LabelMode;
  hiddenClasses: Set<string>;
  onCamera?: (api: GraphCameraApi) => void;
}

function edgeLabel(edge: SubgraphEdge, mode: LabelMode): string {
  if (mode !== "relation") return "";
  const kind = edge.kind || "relation";
  return edge.count > 1 ? `${kind} ×${edge.count}` : kind;
}

export default function SigmaGraph({
  nodes,
  edges,
  classes,
  selected,
  onSelect,
  labelMode,
  hiddenClasses,
  onCamera,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const modeRef = useRef<LabelMode>(labelMode);
  const hiddenRef = useRef<Set<string>>(hiddenClasses);
  const focusRef = useRef<string | null>(null);
  const selectionRef = useRef<string | null>(selected);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  const colors = useMemo(() => colorsForClasses(classes), [classes]);

  const adjacency = useMemo(() => {
    const map: Record<string, Set<string>> = {};
    for (const edge of edges) {
      (map[edge.source] ??= new Set()).add(edge.target);
      (map[edge.target] ??= new Set()).add(edge.source);
    }
    return map;
  }, [edges]);

  // Build + mount: one Sigma instance per subgraph (the subgraph is tiny, and
  // a rebuild is what guarantees the reducers see the new node set).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const ink = cssVar("--color-ink", FALLBACK.ink);
    const muted = cssVar("--color-muted", FALLBACK.muted);
    const dim = cssVar("--color-graph-dim", FALLBACK.graphDim);
    const edgeDim = cssVar("--color-graph-edge", FALLBACK.graphEdge);
    const accent = cssVar("--color-accent", FALLBACK.accent);
    const fallbackNode = cssVar("--color-graph-node", FALLBACK.graphNode);

    const graph = new Graph({ multi: true, type: "directed" });
    for (const node of nodes) {
      graph.addNode(node.id, {
        x: node.x,
        y: node.y,
        size: node.size,
        color: colors[node.cls] ?? fallbackNode,
        label: node.label,
      });
    }
    for (const [index, edge] of edges.entries()) {
      if (!graph.hasNode(edge.source) || !graph.hasNode(edge.target)) continue;
      graph.addEdgeWithKey(`e${index}:${edge.id}`, edge.source, edge.target, {
        size: edge.count > 1 ? 1.2 : 0.8,
        color: edgeDim,
        label: edge.count > 1 ? `${edge.kind} ×${edge.count}` : edge.kind,
      });
    }

    const settings = {
      renderEdgeLabels: modeRef.current === "relation",
      enableEdgeEvents: false,
      enableNodeEvents: true,
      antialiasEdges: false,
      defaultEdgeType: "line",
      antiAliasingFeather: 0.5,
      labelFont: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
      labelSize: 11,
      labelWeight: "500",
      labelColor: { color: ink },
      edgeLabelFont: '"Cascadia Mono", Consolas, monospace',
      edgeLabelSize: 10,
      edgeLabelColor: { color: muted },
      labelDensity: 1,
      labelGridCellSize: 132,
      labelRenderedSizeThreshold: 0,
      stagePadding: 56,
      minCameraRatio: 0.05,
      maxCameraRatio: 4,
      nodeReducer: (node: string, attrs: Record<string, unknown>) => {
        const mode = modeRef.current;
        const hidden = hiddenRef.current;
        const focus = focusRef.current;
        const data = nodes.find((item) => item.id === node);
        const cls = data?.cls ?? "";
        const isSelected = selectionRef.current === node;

        // Legend = filter: a hidden class stays drawn (the picture keeps its
        // shape) but goes grey, loses its label and its size.
        if (hidden.has(cls)) {
          return {
            ...attrs,
            color: dim,
            label: "",
            size: Math.max(2.5, Number(attrs.size ?? 4) * 0.55),
            zIndex: 0,
          };
        }
        const visible = !focus || node === focus || (adjacency[focus]?.has(node) ?? false);
        const label =
          mode === "node" && (visible || isSelected) ? String(attrs.label ?? "") : "";
        return {
          ...attrs,
          color: isSelected ? accent : visible ? attrs.color : dim,
          label,
          // An aggregated contract must never lose its badge to the label
          // grid: its count is the reason it is drawn instead of 1 672 lines.
          forceLabel: label !== "" && Boolean(data?.aggregated),
          size: isSelected ? Number(attrs.size ?? 4) * 1.25 : attrs.size,
          zIndex: isSelected ? 3 : data?.aggregated ? 2 : visible ? 1 : 0,
        };
      },
      edgeReducer: (edge: string, attrs: Record<string, unknown>) => {
        const mode = modeRef.current;
        const focus = focusRef.current;
        const source = graph.source(edge);
        const target = graph.target(edge);
        const sourceNode = nodes.find((item) => item.id === source);
        const targetNode = nodes.find((item) => item.id === target);
        const hidden =
          hiddenRef.current.has(sourceNode?.cls ?? "") ||
          hiddenRef.current.has(targetNode?.cls ?? "");
        const label = mode === "relation" ? String(attrs.label ?? "") : "";
        if (hidden) {
          return { ...attrs, color: dim, label: "", size: 0.5, zIndex: 0 };
        }
        if (!focus) return { ...attrs, label, color: edgeDim };
        const inFocus = source === focus || target === focus;
        return {
          ...attrs,
          label: inFocus ? label : "",
          color: inFocus ? accent : edgeDim,
          size: inFocus ? 1.5 : 0.5,
          zIndex: inFocus ? 2 : 0,
        };
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any;

    const sigma = new Sigma(graph, container, settings);
    sigmaRef.current = sigma;

    // One repaint once the browser has laid the flexbox out: Sigma measures
    // its container at construction, and a first frame at 0×0 would leave the
    // subgraph unpainted. `refresh()` only redraws — `resize()` rebuilds the
    // label layer and silently loses the labels, so it is never called here.
    const frame = window.requestAnimationFrame(() => sigma.refresh());

    sigma.on("clickNode", ({ node }) => selectRef.current(node));
    sigma.on("clickStage", () => selectRef.current(null));

    onCamera?.({
      zoomIn: () => {
        const camera = sigma.getCamera();
        const state = camera.getState();
        const ratio = Math.max(0.05, state.ratio * 0.8);
        if (prefersReducedMotion()) camera.setState({ ...state, ratio });
        else camera.animate({ ...state, ratio }, { duration: 180 });
      },
      zoomOut: () => {
        const camera = sigma.getCamera();
        const state = camera.getState();
        const ratio = Math.min(4, state.ratio * 1.25);
        if (prefersReducedMotion()) camera.setState({ ...state, ratio });
        else camera.animate({ ...state, ratio }, { duration: 180 });
      },
      resetView: () => {
        const target = { x: 0.5, y: 0.5, ratio: 1 };
        if (prefersReducedMotion()) sigma.getCamera().setState(target);
        else sigma.getCamera().animate(target, { duration: 220 });
      },
    });

    return () => {
      window.cancelAnimationFrame(frame);
      sigma.kill();
      sigmaRef.current = null;
    };
    // Rebuild only when the node/edge sets change; label/filter changes are
    // repainted through the reducers below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, colors, adjacency]);

  // Repaint on any presentation change (labels, filter, selection) without
  // touching the camera or the layout.
  useEffect(() => {
    modeRef.current = labelMode;
    hiddenRef.current = hiddenClasses;
    selectionRef.current = selected;
    const sigma = sigmaRef.current;
    if (!sigma) return;
    sigma.setSetting("renderEdgeLabels", labelMode === "relation");
    sigma.refresh();
  }, [labelMode, hiddenClasses, selected]);

  return <div ref={containerRef} className="h-full w-full" />;
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}
