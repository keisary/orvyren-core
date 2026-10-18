import { useEffect, useRef } from "react";
import {
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { SeriesLine } from "@/lib/types";

/**
 * Wrapper maison (~80 lignes) autour de TradingView Lightweight Charts v5 :
 * `createChart` + `addSeries(LineSeries|HistogramSeries)` + `setData`.
 * Le canvas est détruit au démontage (`chart.remove()`).
 */
export default function PriceChart({
  series,
  variant = "line",
  height = 320,
  valueFormat,
}: {
  series: SeriesLine[];
  variant?: "line" | "histogram";
  height?: number;
  valueFormat?: (value: number) => string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "#0d1420" },
        textColor: "#7c92ad",
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: 10,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#16223a" },
        horzLines: { color: "#16223a" },
      },
      rightPriceScale: { borderColor: "#1e2c41" },
      timeScale: {
        borderColor: "#1e2c41",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: "#22d3ee", style: 3, labelBackgroundColor: "#22d3ee" },
        horzLine: { color: "#22d3ee", style: 3, labelBackgroundColor: "#22d3ee" },
      },
      localization: valueFormat
        ? { priceFormatter: (price: number) => valueFormat(price) }
        : undefined,
    });
    chartRef.current = chart;

    const palette = ["#22d3ee", "#818cf8", "#34d399", "#fbbf24", "#f472b6", "#60a5fa"];
    series.forEach((line, index) => {
      const data = line.points
        .filter(([time, value]) => Number.isFinite(time) && Number.isFinite(value))
        .map(([time, value]) => ({ time: time as UTCTimestamp, value }))
        .sort((a, b) => a.time - b.time);
      if (data.length === 0) return;
      const color = palette[index % palette.length];
      if (variant === "histogram") {
        const target = chart.addSeries(HistogramSeries, {
          color,
          priceLineVisible: false,
          priceFormat: { type: "price", precision: 1, minMove: 0.1 },
        });
        target.setData(data);
      } else {
        const target = chart.addSeries(LineSeries, {
          color,
          lineWidth: 2,
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          title: line.label,
        });
        target.setData(data);
      }
    });
    chart.timeScale().fitContent();

    return () => {
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series, variant, height]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
