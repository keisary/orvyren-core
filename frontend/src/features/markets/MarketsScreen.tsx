import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SeriesLine } from "@/lib/types";
import { fmtBps, fmtCompact, fmtNumber, fmtUnix, truncate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, ScrollArea, Select } from "@/components/ui/input";
import { ScreenShell } from "@/components/ScreenShell";
import PriceChart from "./PriceChart";

function SeriesToggles({
  lines,
  visible,
  onToggle,
}: {
  lines: SeriesLine[];
  visible: Record<string, boolean>;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1">
      {lines.map((line, index) => {
        const palette = ["#22d3ee", "#818cf8", "#34d399", "#fbbf24", "#f472b6", "#60a5fa"];
        const on = visible[line.id] !== false;
        return (
          <label
            key={line.id}
            className="mono flex cursor-pointer items-center gap-1.5 text-[10px] text-muted hover:text-ink"
          >
            <input
              type="checkbox"
              checked={on}
              onChange={() => onToggle(line.id)}
              className="accent-[#22d3ee]"
            />
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ background: on ? palette[index % palette.length] : "#33465f" }}
            />
            {line.label}
          </label>
        );
      })}
    </div>
  );
}

function HeadlineGrid({ headline }: { headline: Record<string, unknown> }) {
  const entries = Object.entries(headline).slice(0, 12);
  return (
    <div className="grid grid-cols-2 gap-1.5 lg:grid-cols-3">
      {entries.map(([key, value]) => (
        <div key={key} className="rounded border border-line bg-surface2/40 px-2 py-1.5">
          <div className="mono text-[9px] uppercase tracking-wider text-muted">{key}</div>
          <div className="mono text-[10.5px] leading-snug text-ink/90">
            {summarizeValue(value)}
          </div>
        </div>
      ))}
    </div>
  );
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

  const series = seriesQuery.data;
  const priceLines = useMemo(
    () => (series?.lines ?? []).filter((line) => line.kind === "price" || line.kind === "discount"),
    [series],
  );
  const exposureLines = useMemo(
    () => (series?.lines ?? []).filter((line) => line.kind === "exposure" || line.kind === "signal"),
    [series],
  );
  const bars = series?.bars ?? [];

  const toggle = (id: string) =>
    setVisible((prev) => ({ ...prev, [id]: prev[id] === false }));

  const episodeIndex = episodes.find((episode) => episode.id === activeId);

  return (
    <ScreenShell
      title="Markets — stress episodes"
      subtitle={
        <span className="mono">
          measured series (RPC + venues) · prices & exposures · TradingView Lightweight Charts v5
        </span>
      }
      actions={
        <>
          <Select
            className="w-64"
            value={activeId}
            onChange={(event) => {
              setEpisodeId(event.target.value);
              setVisible({});
            }}
          >
            {episodes.map((episode) => (
              <option key={episode.id} value={episode.id}>
                {episode.id} — {truncate(episode.title, 42)}
              </option>
            ))}
          </Select>
          {episodeIndex ? <Badge variant="info">{episodeIndex.points} points</Badge> : null}
        </>
      }
    >
      {!series ? (
        <div className="p-8 text-center text-muted">loading series…</div>
      ) : (
        <div className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle>{series.title}</CardTitle>
              <div className="mono text-[10px] text-muted">
                window {JSON.stringify(series.window).slice(0, 90)}
              </div>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <HeadlineGrid headline={series.headline} />
              {series.events.length > 0 ? (
                <div>
                  <Label>documented episode milestones</Label>
                  <ScrollArea className="mt-1 max-h-40">
                    {series.events.map((event, index) => (
                      <div key={index} className="border-b border-line/60 px-2.5 py-1.5">
                        <div className="flex items-center gap-2">
                          <Badge variant="warn">{fmtUnix(Number(event.ts) || 0)}</Badge>
                          <span className="text-[11px] text-ink/90">{event.label}</span>
                        </div>
                        <div className="mono mt-0.5 text-[9.5px] text-muted">{event.source}</div>
                      </div>
                    ))}
                  </ScrollArea>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>price / discount</CardTitle>
                <Badge variant="neutral">{priceLines.length} series</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                <SeriesToggles lines={priceLines} visible={visible} onToggle={toggle} />
                <PriceChart
                  series={priceLines.filter((line) => visible[line.id] !== false)}
                  height={340}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>exposure & signals</CardTitle>
                <Badge variant="neutral">
                  {exposureLines.length + bars.length} series
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                <SeriesToggles
                  lines={[...bars, ...exposureLines]}
                  visible={visible}
                  onToggle={toggle}
                />
                {bars.filter((line) => visible[line.id] !== false).length > 0 ? (
                  <>
                    <Label>signal histogram ({bars[0].unit})</Label>
                    <PriceChart
                      series={bars.filter((line) => visible[line.id] !== false)}
                      variant="histogram"
                      height={150}
                      valueFormat={(value) => fmtBps(value)}
                    />
                  </>
                ) : null}
                <Label>measured exposures</Label>
                <PriceChart
                  series={exposureLines.filter((line) => visible[line.id] !== false)}
                  height={190}
                  valueFormat={(value) => fmtCompact(value)}
                />
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>RPC provenance</CardTitle>
              </CardHeader>
              <CardContent className="mono space-y-1 text-[10px] text-muted">
                {Object.entries(series.rpc_provenance).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-accent2">{key}</span>: {truncate(String(value), 110)}
                  </div>
                ))}
                {Object.keys(series.rpc_provenance).length === 0 ? (
                  <div>RPC metadata absent from this artefact</div>
                ) : null}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {series.notes.map((note, index) => (
                  <div key={index} className="text-[10.5px] leading-relaxed text-ink/85">
                    • {note}
                  </div>
                ))}
                {series.notes.length === 0 ? <div className="text-muted">—</div> : null}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>declared limitations</CardTitle>
                <Badge variant="warn">declared honestly</Badge>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {series.limitations.map((limitation, index) => (
                  <div key={index} className="text-[10.5px] leading-relaxed text-warn/90">
                    • {limitation}
                  </div>
                ))}
                {series.limitations.length === 0 ? <div className="text-muted">—</div> : null}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </ScreenShell>
  );
}
