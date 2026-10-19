import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { SeriesLine } from "@/lib/types";
import { cssVar, seriesStyle, FALLBACK } from "@/lib/graph-theme";

export interface SeriesChartStyle {
  color: string;
  style: 0 | 1 | 2; // 0 solid, 1 dotted, 2 dashed (graph-theme.seriesStyle)
}

const LINE_STYLES: Record<0 | 1 | 2, LineStyle> = {
  0: LineStyle.Solid,
  1: LineStyle.Dotted,
  2: LineStyle.Dashed,
};

/** Display formatter per PHYSICAL unit (Astra-4 P0-1): % keeps enough
 *  decimals that 0.008 % never becomes 0.0, USD groups thousands. */
export function formatterFor(unit: string): (price: number) => string {
  if (unit === "%") {
    return (price) => {
      const pct = price * 100;
      const decimals = Math.abs(pct) >= 1 ? 3 : 5;
      return `${pct.toLocaleString("en-GB", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      })}%`;
    };
  }
  if (unit === "bps") {
    return (price) =>
      `${price.toLocaleString("en-GB", { maximumFractionDigits: 1 })} bps`;
  }
  if (unit === "ETH" || unit === "ratio") {
    return (price) => price.toLocaleString("en-GB", { maximumFractionDigits: 4 });
  }
  return (price) =>
    Math.abs(price) >= 1000
      ? price.toLocaleString("en-GB", { maximumFractionDigits: 0 })
      : price.toLocaleString("en-GB", { maximumFractionDigits: 2 });
}

function toData(line: SeriesLine) {
  return line.points
    .filter(([time, value]) => Number.isFinite(time) && Number.isFinite(value))
    .map(([time, value]) => ({ time: time as UTCTimestamp, value }))
    .sort((a, b) => a.time - b.time);
}

/**
 * Lightweight Charts v5 wrapper (spec §4.6 + Astra-4 P1-2).
 *
 * - The chart instance is created ONCE per mount; series are synced in place
 *   afterwards, and fitContent runs only on the first fit — toggling a
 *   series no longer resets the reader's time window.
 * - The price formatter follows the group's physical unit (% / USD / bps);
 *   parent keys this component by group id so `unit` stays fixed per mount.
 * - Styles arrive per line.id assigned before filtering: toggles can never
 *   reassign colors or line styles.
 */
export default function PriceChart({
  series,
  variant = "line",
  height = 320,
  unit = "",
  valueFormat,
  styles,
}: {
  series: SeriesLine[];
  variant?: "line" | "histogram";
  height?: number;
  unit?: string;
  valueFormat?: (value: number) => string;
  styles?: Record<string, SeriesChartStyle>;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesMap = useRef(
    new Map<string, ISeriesApi<"Line"> | ISeriesApi<"Histogram">>(),
  );
  const fittedRef = useRef(false);
  const unitRef = useRef(unit);
  const vfRef = useRef(valueFormat);
  unitRef.current = unit;
  vfRef.current = valueFormat;

  // Create once: document theme, horizontal hairlines only, ink dashed
  // crosshair on a near-black chip (the library draws white label text).
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const surface = cssVar("--color-surface", FALLBACK.surface);
    const muted = cssVar("--color-muted", FALLBACK.muted);
    const line = cssVar("--color-line", FALLBACK.line);
    const lineStrong = cssVar("--color-line-strong", FALLBACK.lineStrong);
    const ink = cssVar("--color-ink", FALLBACK.ink);

    const chart = createChart(container, {
      autoSize: true,
      height,
      layout: {
        background: { type: ColorType.Solid, color: surface },
        textColor: muted,
        fontFamily: 'Arial, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 12,
        attributionLogo: false,
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: line },
      },
      rightPriceScale: { borderColor: lineStrong },
      timeScale: {
        borderColor: lineStrong,
        timeVisible: true,
        secondsVisible: false,
        // Consistent UTC ticks: MM-DD at day boundaries, HH:MM inside.
        tickMarkFormatter: (time: number) => {
          const iso = new Date(time * 1000).toISOString();
          return iso.slice(11, 16) === "00:00" ? iso.slice(5, 10) : iso.slice(11, 16);
        },
      },
      crosshair: {
        // Line flips with the theme (ink); the label chip stays near-black
        // because the library draws WHITE text on it.
        vertLine: { color: ink, style: LineStyle.Dashed, labelBackgroundColor: "#131722" },
        horzLine: { color: ink, style: LineStyle.Dashed, labelBackgroundColor: "#131722" },
      },
      localization: {
        priceFormatter: (price: number) => {
          if (vfRef.current) return vfRef.current(price);
          return formatterFor(unitRef.current)(price);
        },
      },
    });
    chartRef.current = chart;
    fittedRef.current = false;

    return () => {
      seriesMap.current.clear();
      chartRef.current = null;
      chart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height, variant]);

  // Sync series in place: add / update / remove without recreating the
  // chart; fitContent only the first time (window preserved on toggles).
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    const keep = new Set(series.map((entry) => entry.id));

    for (const [id, existing] of Array.from(seriesMap.current.entries())) {
      if (keep.has(id)) continue;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      chart.removeSeries(existing as any);
      seriesMap.current.delete(id);
    }

    let hasData = false;
    series.forEach((entry, index) => {
      const data = toData(entry);
      if (data.length === 0) return;
      hasData = true;
      const chartStyle = styles?.[entry.id] ?? seriesStyle(index);
      const existing = seriesMap.current.get(entry.id);
      if (existing) {
        existing.applyOptions({
          color: chartStyle.color,
          ...(variant === "line" ? { lineStyle: LINE_STYLES[chartStyle.style] } : {}),
        });
        existing.setData(data);
        return;
      }
      if (variant === "histogram") {
        const target = chart.addSeries(HistogramSeries, {
          color: chartStyle.color,
          priceLineVisible: false,
          priceFormat: { type: "price", precision: 2, minMove: 0.01 },
        });
        target.setData(data);
        seriesMap.current.set(entry.id, target);
      } else {
        const target = chart.addSeries(LineSeries, {
          color: chartStyle.color,
          lineWidth: 2,
          lineStyle: LINE_STYLES[chartStyle.style],
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          title: entry.label,
        });
        target.setData(data);
        seriesMap.current.set(entry.id, target);
      }
    });

    if (hasData && !fittedRef.current) {
      chart.timeScale().fitContent();
      fittedRef.current = true;
    }
  }, [series, styles, variant]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
