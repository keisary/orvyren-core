import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { SeriesLine } from "@/lib/types";
import { cssVar, seriesStyle, FALLBACK } from "@/lib/graph-theme";

export interface SeriesChartStyle {
  color: string;
  style: 0 | 1 | 2; // 0 solid, 1 dotted, 2 dashed (see graph-theme.seriesStyle)
}

const LINE_STYLES: Record<0 | 1 | 2, LineStyle> = {
  0: LineStyle.Solid,
  1: LineStyle.Dotted,
  2: LineStyle.Dashed,
};

/**
 * Hand-rolled wrapper around TradingView Lightweight Charts v5.
 * Light document theme: ivory ground, hairline grid (horizontal only), ink
 * dashed crosshair, 12px labels (§4.8). Colors/units are assigned by line.id
 * BEFORE any filtering (styles prop), so toggles can never reassign them.
 */
export default function PriceChart({
  series,
  variant = "line",
  height = 320,
  valueFormat,
  styles,
}: {
  series: SeriesLine[];
  variant?: "line" | "histogram";
  height?: number;
  valueFormat?: (value: number) => string;
  styles?: Record<string, SeriesChartStyle>;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

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
      },
      crosshair: {
        // Line flips with the theme (ink); the label chip stays near-black
        // because the library draws WHITE text on it — a light chip would
        // make that text invisible in the dark theme.
        vertLine: { color: ink, style: LineStyle.Dashed, labelBackgroundColor: "#131722" },
        horzLine: { color: ink, style: LineStyle.Dashed, labelBackgroundColor: "#131722" },
      },
      localization: valueFormat
        ? { priceFormatter: (price: number) => valueFormat(price) }
        : undefined,
    });

    series.forEach((lineEntry, index) => {
      const data = lineEntry.points
        .filter(([time, value]) => Number.isFinite(time) && Number.isFinite(value))
        .map(([time, value]) => ({ time: time as UTCTimestamp, value }))
        .sort((a, b) => a.time - b.time);
      if (data.length === 0) return;
      const chartStyle = styles?.[lineEntry.id] ?? seriesStyle(index);
      if (variant === "histogram") {
        const target = chart.addSeries(HistogramSeries, {
          color: chartStyle.color,
          priceLineVisible: false,
          priceFormat: { type: "price", precision: 1, minMove: 0.1 },
        });
        target.setData(data);
      } else {
        const target = chart.addSeries(LineSeries, {
          color: chartStyle.color,
          lineWidth: 2,
          lineStyle: LINE_STYLES[chartStyle.style],
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          title: lineEntry.label,
          // Grouped thousands on the value axis (§4.6: legible figures).
          priceFormat: {
            type: "custom",
            formatter: (price: number) =>
              Math.abs(price) >= 1000
                ? price.toLocaleString("en-GB", { maximumFractionDigits: 0 })
                : price.toLocaleString("en-GB", { maximumFractionDigits: 2 }),
          },
        });
        target.setData(data);
      }
    });
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series, variant, height, styles, valueFormat]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
