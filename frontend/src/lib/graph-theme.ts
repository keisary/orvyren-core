/**
 * Shared canvas theme (§4.8): ONE source for graph/plot colors.
 *
 * - `toneForClass` maps a node class NAME to a tone — stable across payloads
 *   (the old palette reindexed per payload, silently reassigning colors).
 * - Four restrained tones: ink for entities, the accent for instrumented
 *   positions, plot-secondary for records/relations, graph-node as fallback.
 *   The class NAME stays visible in the legend and the inspector — twelve
 *   hues were never the point.
 * - Tokens come from CSS (getComputedStyle), fallback = the literal value in
 *   styles/index.css, so canvas matches the document theme.
 */

export const FALLBACK = {
  surface: "#fcfcf9",
  ink: "#202823",
  muted: "#59635c",
  line: "#cdd3cb",
  lineStrong: "#788379",
  accent: "#24543d",
  accentSoft: "#e2ebe3",
  graphNode: "#7b867e",
  graphDim: "#cdd3cb",
  graphEdge: "#d8ddd6",
  plotSecondary: "#667269",
} as const;

export function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

/** Node class → tone, by name (never by sort index). */
export function toneForClass(cls: string): string {
  const c = cls.toLowerCase();
  if (/(addr|address|account|holder|wallet|eoa|user)/.test(c))
    return cssVar("--color-ink", FALLBACK.ink);
  if (/(asset|debt|position|reserve|pool|market|supply|collateral|claim)/.test(c))
    return cssVar("--color-accent", FALLBACK.accent);
  if (/(event|proof|provenance|source|relation|struct|constraint|block)/.test(c))
    return cssVar("--color-plot-secondary", FALLBACK.plotSecondary);
  return cssVar("--color-graph-node", FALLBACK.graphNode);
}

export function colorsForClasses(
  classes: Record<string, number>,
): Record<string, string> {
  const mapping: Record<string, string> = {};
  for (const cls of Object.keys(classes)) mapping[cls] = toneForClass(cls);
  return mapping;
}

/**
 * Series styles: assigned from the FULL line list (before any filtering, by
 * line.id) so toggling series can never reassign colors. Three styles max —
 * selection carries the rest, no multicolor palette.
 * 0 = main (accent solid), 1 = comparator (ink dashed), 2 = third (dotted).
 */
export function seriesStyle(index: number): { color: string; style: 0 | 1 | 2 } {
  const styles = [
    { color: cssVar("--color-accent", FALLBACK.accent), style: 0 as const },
    { color: cssVar("--color-ink", FALLBACK.ink), style: 1 as const },
    { color: cssVar("--color-plot-secondary", FALLBACK.plotSecondary), style: 2 as const },
  ];
  return styles[index % styles.length];
}
