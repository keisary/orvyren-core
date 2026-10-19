import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SeriesLine } from "@/lib/types";
import { fmtBps, fmtNumber, fmtTime, fmtUnix, truncate } from "@/lib/format";
import { seriesStyle } from "@/lib/graph-theme";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { ScreenShell } from "@/components/ScreenShell";
import { DisclosureBlock } from "@/components/SubstitutionBanner";
import PriceChart, { type SeriesChartStyle } from "./PriceChart";

/* ------------------------------------------------------------------ groups
 * One chart per PHYSICAL semantic (Astra-4 P0-1): market prices in USD,
 * each % ratio alone, quantities per reserve asset — rsETH, WETH and USDC
 * quantities never share an axis, and no axis is named after a metric. */

const METRIC_EN: Record<string, string> = {
  cash: "balance",
  variable_debt_supply: "variable debt",
  a_token_supply: "aToken supply",
  utilisation: "utilisation",
  cap_ratio: "supply-cap usage",
  oracle_price: "oracle price",
};
const METRIC_RANK: Record<string, number> = {
  oracle_price: 0,
  cap_ratio: 1,
  utilisation: 2,
  cash: 3,
  variable_debt_supply: 4,
  a_token_supply: 5,
};
const KIND_EN: Record<string, string> = {
  price: "Price",
  discount: "Discount",
  exposure: "Exposure",
  signal: "Signal",
};
const ASSET_RANK: Record<string, number> = { rsETH: 0, WETH: 1, USDC: 2 };

interface ChartGroup {
  key: string;
  title: string;
  unit: string;
  rank: number;
  lines: SeriesLine[];
}

function groupKeyOf(line: SeriesLine): string {
  if (line.unit === "%" && line.metric) return `%|${line.metric}`;
  if (line.kind === "price" && line.unit === "USD") return "price|USD";
  if (line.asset && line.unit === line.asset) return `qty|${line.asset}`;
  return `${line.kind}|${line.unit}`;
}

function buildGroups(lines: SeriesLine[]): ChartGroup[] {
  const map = new Map<string, SeriesLine[]>();
  for (const line of lines) {
    const key = groupKeyOf(line);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(line);
  }
  const groups: ChartGroup[] = [];
  for (const [key, groupLines] of map.entries()) {
    const first = groupLines[0];
    const metric = first.metric ?? "";
    const asset = first.asset ?? "";
    let title: string;
    let rank: number;
    if (key === "price|USD") {
      title = groupLines.some((line) => line.asset === "rsETH")
        ? "rsETH oracle price · USD"
        : "Price · USD";
      rank = 0;
    } else if (key.startsWith("%|")) {
      const en = METRIC_EN[metric] ?? metric;
      title = `${en.charAt(0).toUpperCase()}${en.slice(1)} · %`;
      rank = 10 + (METRIC_RANK[metric] ?? 9);
    } else if (key.startsWith("qty|")) {
      title = `${asset} reserve balances (${first.unit})`;
      rank = 20 + (ASSET_RANK[asset] ?? 3);
    } else if (first.kind === "price") {
      title = `${KIND_EN.price} · ${first.unit}`;
      rank = 1;
    } else if (first.kind === "discount") {
      title = `${KIND_EN.discount} · ${first.unit}`;
      rank = 30;
    } else {
      title = `${KIND_EN[first.kind] ?? "Series"} · ${first.unit}`;
      rank = 31 + (METRIC_RANK[metric] ?? 0);
    }
    groupLines.sort(
      (a, b) => (METRIC_RANK[a.metric ?? ""] ?? 9) - (METRIC_RANK[b.metric ?? ""] ?? 9),
    );
    groups.push({ key, title, unit: first.unit, rank, lines: groupLines });
  }
  groups.sort((a, b) => a.rank - b.rank);
  return groups;
}

/** Explicit default selection, at most three per chart: the documented
 *  median/min pair for USDC, rsETH alone when several reserves share USD,
 *  otherwise the first three (§4.6). */
function defaultVisibleFor(groups: ChartGroup[]): Record<string, boolean> {
  const visible: Record<string, boolean> = {};
  for (const group of groups) {
    const ids = group.lines.map((line) => line.id);
    const preferred = ["price:median", "price:min"].filter((id) => ids.includes(id));
    let on: string[];
    if (preferred.length > 0) {
      on = preferred;
    } else {
      const rseth = group.lines.filter((line) => line.asset === "rsETH").map((l) => l.id);
      on = rseth.length > 0 ? rseth : ids.slice(0, 3);
    }
    for (const id of ids) visible[id] = on.includes(id);
  }
  return visible;
}

/** Toggles: stable per-line style (assigned before filtering) + the real
 *  line pattern (solid / dotted / dashed) so legend and plot agree. */
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
  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {lines.map((line) => {
          const on = visible[line.id] !== false;
          const style = styleMap[line.id] ?? seriesStyle(0);
          const borderStyle = style.style === 0 ? "solid" : style.style === 1 ? "dotted" : "dashed";
          return (
            <label
              key={line.id}
              className="flex cursor-pointer items-center gap-1.5 text-meta text-muted hover:text-ink"
            >
              <input
                type="checkbox"
                checked={on}
                onChange={() => onToggle(line.id)}
                className="h-3.5 w-3.5 accent-[#24543d]"
              />
              <span
                aria-hidden
                className="inline-block w-4 border-t-2"
                style={{
                  borderTopStyle: borderStyle,
                  borderTopColor: on ? style.color : "var(--color-line-strong)",
                }}
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
  // The jury episode is rsETH when it exists (§4.6), else the first one.
  const activeId =
    episodeId || episodes.find((episode) => episode.id.includes("rseth"))?.id ||
    episodes[0]?.id || "";
  const seriesQuery = useQuery({
    queryKey: ["episode-series", activeId],
    queryFn: () => api.episodeSeries(activeId),
    enabled: Boolean(activeId),
  });
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [showAllEvents, setShowAllEvents] = useState(false);

  const series = seriesQuery.data;

  const groups = useMemo(
    () => buildGroups(series?.lines ?? []),
    [series],
  );

  // Styles assigned per line.id INSIDE each group (before any filtering):
  // three visible series always get three distinct style/color pairs.
  const styleMap = useMemo(() => {
    const map: Record<string, SeriesChartStyle> = {};
    for (const group of groups) {
      group.lines.forEach((line, index) => {
        map[line.id] = seriesStyle(index);
      });
    }
    (series?.bars ?? []).forEach((line, index) => {
      map[line.id] = seriesStyle(index);
    });
    return map;
  }, [groups, series]);

  // New episode → explicit default selection (≤3 per chart), reset events.
  useEffect(() => {
    if (!series) return;
    const initial = defaultVisibleFor(groups);
    for (const bar of series.bars ?? []) initial[bar.id] = true;
    setVisible(initial);
    setShowAllEvents(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series]);

  const toggle = (id: string) =>
    setVisible((prev) => {
      const turningOn = prev[id] === false;
      if (turningOn) {
        const group = groups.find((entry) => entry.lines.some((line) => line.id === id));
        const count = group
          ? group.lines.filter((line) => prev[line.id] !== false).length
          : 0;
        if (count >= 3) return prev; // maximum three visible series per chart
      }
      return { ...prev, [id]: turningOn };
    });

  const bars = series?.bars ?? [];
  const facts = useMemo(() => headlineFacts(series?.headline ?? {}), [series]);
  const episodeIndex = episodes.find((episode) => episode.id === activeId);
  const events = series?.events ?? [];
  const shownEvents = showAllEvents ? events : events.slice(0, 3);
  const isEth = activeId.includes("rseth") || activeId.includes("steth");
  const evidenceValue = `Historical evidence · ${isEth ? "Ethereum" : "archived venues"}`;
  const subtitle = `${activeId.startsWith("rseth") ? "rsETH / April 2026 · " : ""}${evidenceValue} · measured series (RPC + venues)`;

  const limitations = [...(series?.limitations ?? [])];
  if (activeId.includes("rseth")) {
    // Authorized copy (Astra-3 §2.3D): the freeze bit does not prove that
    // withdrawals were blocked — say exactly that, visibly.
    limitations.push(
      "Reserve freeze observed. Withdrawal availability was not established.",
    );
  }

  return (
    <ScreenShell
      title="Market evidence"
      subtitle={subtitle}
      context={[
        { label: "Episode", value: activeId || "—" },
        { label: "Evidence", value: evidenceValue },
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
          {episodesQuery.isError && episodesQuery.data ? (
            <>
              <span className="text-meta text-ink">
                Refresh failed — list loaded at {fmtTime(episodesQuery.dataUpdatedAt)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => episodesQuery.refetch()}
              >
                Retry
              </Button>
            </>
          ) : null}
        </>
      }
    >
      {seriesQuery.isError && !series ? (
        <div className="border border-line bg-surface px-4 py-8 text-center">
          <div className="text-body text-ink">
            Series unavailable — the API did not answer.
          </div>
          <Button
            variant="secondary"
            className="mt-3"
            onClick={() => seriesQuery.refetch()}
          >
            Retry
          </Button>
        </div>
      ) : !series ? (
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
            {groups.length === 0 && bars.length === 0 ? (
              <div className="border border-line bg-surface px-4 py-6 text-center text-body text-muted lg:col-span-2">
                This episode has no measurable series.
              </div>
            ) : null}
            <div className="space-y-4">
              {groups.map((group, groupIndex) => {
                const shown = group.lines.filter((line) => visible[line.id] !== false);
                return (
                  <Card key={group.key}>
                    <CardHeader>
                      <CardTitle>{group.title}</CardTitle>
                      <Badge variant="neutral">
                        {shown.length} / {group.lines.length} series · {group.unit}
                      </Badge>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <SeriesToggles
                        lines={group.lines}
                        visible={visible}
                        onToggle={toggle}
                        styleMap={styleMap}
                      />
                      {shown.length === 0 ? (
                        <div className="flex h-24 items-center justify-center border border-line text-meta text-muted">
                          No series selected — check one above.
                        </div>
                      ) : (
                        <PriceChart
                          key={group.key}
                          series={shown}
                          unit={group.unit}
                          height={groupIndex === 0 ? 280 : 160}
                          styles={styleMap}
                        />
                      )}
                      <div className="text-meta text-muted">
                        Time (UTC) · Sampled observations; lines connect available points.
                      </div>
                    </CardContent>
                  </Card>
                );
              })}

              {bars.length > 0 ? (
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
                    {bars.filter((line) => visible[line.id] !== false).length === 0 ? (
                      <div className="flex h-24 items-center justify-center border border-line text-meta text-muted">
                        No series selected — check one above.
                      </div>
                    ) : (
                      <PriceChart
                        key="histogram"
                        series={bars.filter((line) => visible[line.id] !== false)}
                        variant="histogram"
                        unit="bps"
                        height={150}
                        styles={styleMap}
                        valueFormat={(value) => fmtBps(value)}
                      />
                    )}
                  </CardContent>
                </Card>
              ) : null}
            </div>

            <div className="space-y-4">
              {activeId.includes("rseth") ? (
                <DisclosureBlock
                  title="Documented market quote: $1,686"
                  body="Not an archived market series. Not time-aligned with the oracle reading."
                  sources={["fixtures/raw_w2b/defillama_rseth_apr2026.json"]}
                />
              ) : null}

              {/* Limitations that can change the verdict stay visible (§4.6). */}
              <Card>
                <CardHeader>
                  <CardTitle>Evidence limits</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5">
                  {limitations.map((limitation, index) => (
                    <div key={index} className="text-body leading-5 text-ink">
                      • {limitation}
                    </div>
                  ))}
                  {limitations.length === 0 ? (
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
