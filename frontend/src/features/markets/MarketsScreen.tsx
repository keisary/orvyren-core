import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SeriesLine } from "@/lib/types";
import { fmtBps, fmtCompact, fmtNumber, fmtUnix, truncate } from "@/lib/format";
import { seriesStyle } from "@/lib/graph-theme";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { ScreenShell } from "@/components/ScreenShell";
import PriceChart, { type SeriesChartStyle } from "./PriceChart";

/** Toggles carry the stable per-line style (assigned before any filtering):
 *  switching series can never reassign colors or line styles (§4.8). */
function SeriesToggles({
  lines,
  visible,
  onToggle,
  styleMap,
}: {
  lines: SeriesLine[];
  visible: Record<string, boolean>;
  onToggle: (id: string) => void;
  styleMap: Record<string, SeriesChartStyle>;
}) {
  const visibleCount = lines.filter((line) => visible[line.id] !== false).length;
  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {lines.map((line) => {
          const on = visible[line.id] !== false;
          const style = styleMap[line.id] ?? seriesStyle(0);
          return (
            <label
              key={line.id}
              className="flex cursor-pointer items-center gap-1.5 text-meta text-muted hover:text-ink"
            >
              <input
                type="checkbox"
                checked={on}
                onChange={() => {
                  // Maximum three visible series per chart (§4.6): selection,
                  // not a multicolor palette.
                  if (!on && visibleCount >= 3) return;
                  onToggle(line.id);
                }}
                className="h-3.5 w-3.5 accent-[#24543d]"
              />
              <span
                aria-hidden
                className="inline-block h-0.5 w-4"
                style={{ background: on ? style.color : "var(--color-line-strong)" }}
              />
              {line.label}
            </label>
          );
        })}
      </div>
      {lines.length > 3 ? (
        <div className="mt-1 text-meta text-muted">
          Maximum three series visible — uncheck one to switch.
        </div>
      ) : null}
    </div>
  );
}

/** Explicit fact mapping (§4.6): named facts from the artefact's own keys,
 *  never a blind Object.entries().slice(). The rest stays reachable through
 *  the "Episode facts (all)" details. */
function headlineFacts(headline: Record<string, unknown>) {
  const facts: { label: string; value: string; sub?: string }[] = [];
  const freezeTs = String(headline.rsETH_frozen_transition_utc ?? "");
  const oracleKey = freezeTs ? `rsETH_oracle_at_${freezeTs}` : "";
  if (oracleKey && headline[oracleKey] !== undefined) {
    facts.push({
      label: "Oracle price at freeze",
      value: `$${fmtNumber(headline[oracleKey], 2)}`,
      sub: freezeTs,
    });
  }
  if (headline.cap_ratio_max !== undefined) {
    facts.push({
      label: "Peak supply-cap usage",
      value: `${fmtNumber(Number(headline.cap_ratio_max) * 100, 3)}%`,
      sub: `${fmtNumber(headline.a_token_supply_at_cap_max, 2)} / ${fmtNumber(
        headline.supply_cap_rsETH ?? headline.supply_cap,
        0,
      )} rsETH · ${String(headline.cap_ratio_max_utc ?? "")}`,
    });
  }
  if (headline.rsETH_frozen_transition_block !== undefined) {
    facts.push({
      label: "First frozen block",
      value: Number(headline.rsETH_frozen_transition_block).toLocaleString("en-GB"),
      sub: freezeTs,
    });
  }
  return facts;
}

function summarizeValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return fmtNumber(value, 4);
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    // "decote_bps" is an artefact key (kept as-is), never renamed.
    const interesting = ["utc", "ts", "discount_bps", "block", "low", "decote_bps"].filter(
      (key) => record[key] !== undefined,
    );
    if (interesting.length > 0) {
      return interesting
        .map((key) => {
          const raw = record[key];
          return `${key}=${key === "ts" || key === "block" ? String(raw) : fmtNumber(raw, 2)}`;
        })
        .join(" · ");
    }
    return truncate(JSON.stringify(value), 80);
  }
  return String(value);
}

export default function MarketsScreen() {
  const episodesQuery = useQuery({ queryKey: ["episodes"], queryFn: api.episodes });
  const episodes = episodesQuery.data?.episodes ?? [];
  const [episodeId, setEpisodeId] = useState<string>("");
  const activeId = episodeId || episodes[0]?.id || "";
  const seriesQuery = useQuery({
    queryKey: ["episode-series", activeId],
    queryFn: () => api.episodeSeries(activeId),
    enabled: Boolean(activeId),
  });
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [showAllEvents, setShowAllEvents] = useState(false);

  const series = seriesQuery.data;

  // Stable style per line.id — computed from the FULL lists, before filtering.
  const styleMap = useMemo(() => {
    const map: Record<string, SeriesChartStyle> = {};
    let index = 0;
    for (const line of [...(series?.lines ?? []), ...(series?.bars ?? [])]) {
      map[line.id] = seriesStyle(index);
      index += 1;
    }
    return map;
  }, [series]);

  // One chart per unit — price (USD) and discount (bps) never share an axis.
  const unitGroups = useMemo(() => {
    const map = new Map<string, SeriesLine[]>();
    for (const line of series?.lines ?? []) {
      const key = line.unit || line.kind;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(line);
    }
    return [...map.entries()];
  }, [series]);
  const bars = series?.bars ?? [];

  const toggle = (id: string) =>
    setVisible((prev) => ({ ...prev, [id]: prev[id] === false }));

  const facts = useMemo(() => headlineFacts(series?.headline ?? {}), [series]);
  const episodeIndex = episodes.find((episode) => episode.id === activeId);
  const events = series?.events ?? [];
  const shownEvents = showAllEvents ? events : events.slice(0, 3);

  return (
    <ScreenShell
      title="Market evidence"
      subtitle="Measured series (RPC + venues) · one chart per unit · milestones with their sources"
      context={[
        { label: "Episode", value: activeId || "—" },
        { label: "Evidence", value: "Historical evidence · archived series" },
      ]}
      actions={
        <>
          <div className="flex flex-col gap-1">
            <Label htmlFor="episode-select">Episode</Label>
            <Select
              id="episode-select"
              className="w-72"
              value={activeId}
              onChange={(event) => {
                setEpisodeId(event.target.value);
                setVisible({});
                setShowAllEvents(false);
              }}
            >
              {episodes.map((episode) => (
                <option key={episode.id} value={episode.id}>
                  {episode.id} — {truncate(episode.title, 42)}
                </option>
              ))}
            </Select>
          </div>
          {episodeIndex ? <Badge variant="neutral">{episodeIndex.points} points</Badge> : null}
        </>
      }
    >
      {!series ? (
        <div className="p-8 text-center text-meta text-muted">Loading series…</div>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{series.title}</CardTitle>
              {series.window && Object.keys(series.window).length > 0 ? (
                <span className="font-mono text-code text-muted">
                  window {JSON.stringify(series.window).slice(0, 90)}
                </span>
              ) : (
                <span className="text-meta text-muted">
                  Hourly grid · {series.lines?.[0]?.points?.length ?? "—"} points
                </span>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {facts.length > 0 ? (
                <div className="grid grid-cols-1 gap-px border border-line bg-line md:grid-cols-3">
                  {facts.map((fact) => (
                    <div key={fact.label} className="min-h-[88px] bg-surface px-4 py-3">
                      <div className="text-meta text-muted">{fact.label}</div>
                      <div className="mt-0.5 text-kpi font-semibold leading-[30px] tnum text-ink">
                        {fact.value}
                      </div>
                      {fact.sub ? (
                        <div className="mt-1 font-mono text-code text-muted">{fact.sub}</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-body text-muted">
                  No named episode fact is mapped for this artefact — the raw
                  headline stays available below.
                </div>
              )}
              <details>
                <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                  Episode facts (all, raw keys)
                </summary>
                <div className="mt-2 space-y-0.5">
                  {Object.entries(series.headline).map(([key, value]) => (
                    <div key={key} className="font-mono text-code">
                      <span className="text-muted">{key}</span>: {summarizeValue(value)}
                    </div>
                  ))}
                </div>
              </details>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="space-y-4">
              {unitGroups.map(([unit, lines], groupIndex) => {
                const shown = lines.filter((line) => visible[line.id] !== false);
                if (shown.length === 0) return null;
                return (
                  <Card key={unit}>
                    <CardHeader>
                      <CardTitle>
                        {groupIndex === 0 ? "Primary series" : "Comparison"} · {unit}
                      </CardTitle>
                      <Badge variant="neutral">
                        {shown.length} / {lines.length} series · {unit}
                      </Badge>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <SeriesToggles
                        lines={lines}
                        visible={visible}
                        onToggle={toggle}
                        styleMap={styleMap}
                      />
                      <PriceChart
                        series={shown}
                        height={groupIndex === 0 ? 280 : 160}
                        styles={styleMap}
                      />
                      <div className="text-meta text-muted">Time (UTC)</div>
                    </CardContent>
                  </Card>
                );
              })}

              {bars.filter((line) => visible[line.id] !== false).length > 0 ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Signal histogram · {bars[0]?.unit ?? "—"}</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <SeriesToggles
                      lines={bars}
                      visible={visible}
                      onToggle={toggle}
                      styleMap={styleMap}
                    />
                    <PriceChart
                      series={bars.filter((line) => visible[line.id] !== false)}
                      variant="histogram"
                      height={150}
                      styles={styleMap}
                      valueFormat={(value) => fmtBps(value)}
                    />
                  </CardContent>
                </Card>
              ) : null}
            </div>

            <div className="space-y-4">
              {/* Limitations that can change the verdict stay visible (§4.6). */}
              <Card>
                <CardHeader>
                  <CardTitle>Evidence limits</CardTitle>
                  <Badge variant="warn">declared honestly</Badge>
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {series.limitations.map((limitation, index) => (
                    <div key={index} className="text-body leading-5 text-ink">
                      • {limitation}
                    </div>
                  ))}
                  {series.limitations.length === 0 ? (
                    <div className="text-meta text-muted">No limitation declared.</div>
                  ) : null}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Episode events</CardTitle>
                  {events.length > 3 ? (
                    <button
                      type="button"
                      onClick={() => setShowAllEvents((value) => !value)}
                      className="text-meta font-medium text-muted hover:text-ink"
                    >
                      {showAllEvents ? "Show first three" : `Show all events (${events.length})`}
                    </button>
                  ) : null}
                </CardHeader>
                <CardContent className="space-y-2">
                  {shownEvents.map((event, index) => (
                    <div key={index} className="border border-line px-3 py-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="neutral">
                          {fmtUnix(Number(event.ts) || 0)}
                        </Badge>
                        <span className="text-body leading-5 text-ink">{event.label}</span>
                      </div>
                      <div className="mt-0.5 font-mono text-code text-muted">
                        {event.source}
                      </div>
                    </div>
                  ))}
                  {events.length === 0 ? (
                    <div className="text-meta text-muted">No milestone recorded.</div>
                  ) : null}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {series.notes.map((note, index) => (
                    <div key={index} className="text-body leading-5 text-ink">
                      • {note}
                    </div>
                  ))}
                  {series.notes.length === 0 ? (
                    <div className="text-meta text-muted">No note recorded.</div>
                  ) : null}
                </CardContent>
              </Card>

              <details className="border border-line bg-surface">
                <summary className="cursor-pointer px-4 py-2.5 text-meta font-medium text-muted hover:text-ink">
                  Source details (RPC provenance)
                </summary>
                <div className="space-y-1 border-t border-line px-4 py-3 font-mono text-code text-muted">
                  {Object.entries(series.rpc_provenance).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-ink">{key}</span>: {truncate(String(value), 110)}
                    </div>
                  ))}
                  {Object.keys(series.rpc_provenance).length === 0 ? (
                    <div>RPC metadata absent from this artefact.</div>
                  ) : null}
                </div>
              </details>
            </div>
          </div>
        </div>
      )}
    </ScreenShell>
  );
}
