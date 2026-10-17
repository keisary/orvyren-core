#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure: USDC venue divergence and supply contraction, March 2023.

Reads the archived corpus (corpus/usdc_observations.csv) and produces
figures/usdc_divergence.png — two panels:
  top    : hourly price per venue over the crisis window, with the 0.99
           baseline trigger line and the 1.00 peg;
  bottom : daily circulating supply (aggregate vs Ethereum) around the crisis.

All values are computed from the corpus; nothing is hardcoded.
"""

import csv
import datetime as dt
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "corpus", "usdc_observations.csv")
OUT = os.path.join(HERE, "figures", "usdc_divergence.png")

MAIN_START = dt.datetime(2023, 3, 9, tzinfo=dt.timezone.utc)
MAIN_END = dt.datetime(2023, 3, 15, tzinfo=dt.timezone.utc)


def parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load():
    prices, supply = {}, {"defillama_supply_aggregate": [], "defillama_supply_ethereum": []}
    with open(CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            venue = row["venue"]
            if row["metric"] in ("price_usd", "close_usd", "close_usdcusdt"):
                if MAIN_START <= parse(row["timestamp_utc"]) <= MAIN_END:
                    label = "defillama (aggregate)" if venue == "defillama" else venue
                    prices.setdefault(label, []).append((parse(row["timestamp_utc"]), float(row["value"])))
            elif venue in supply:
                supply[venue].append((parse(row["timestamp_utc"]), float(row["value"]) / 1e9))
    for series in list(prices.values()) + list(supply.values()):
        series.sort()
    return prices, supply


def main():
    prices, supply = load()
    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(11.5, 7.6), height_ratios=[2.15, 1], sharex=False,
        gridspec_kw={"hspace": 0.42},
    )

    colors = {"defillama (aggregate)": "#1f77b4", "binance": "#ff7f0e", "bitstamp": "#d62728"}
    troughs = []
    for label, series in sorted(prices.items()):
        xs = [t for t, _ in series]
        ys = [v for _, v in series]
        ax.plot(xs, ys, label=label, color=colors.get(label, "#555555"), linewidth=1.7)
        lo_t, lo_v = min(series, key=lambda p: p[1])
        ax.plot([lo_t], [lo_v], "o", color=colors.get(label, "#555555"), markersize=4.5)
        troughs.append((label, lo_t, lo_v))

    # Trough values in one box (bottom-left area is free) instead of colliding callouts.
    troughs.sort(key=lambda item: item[2])
    box = "\n".join(f"{lab}: {val:.4f}  ({ts:%d/%m %H:%M}Z)" for lab, ts, val in troughs)
    ax.text(
        0.015, 0.035, "Lowest hourly print per source\n" + box,
        transform=ax.transAxes, fontsize=9, va="bottom", ha="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#999999", alpha=0.95),
    )

    ax.axhline(1.00, color="#2ca02c", linewidth=1.0, linestyle=":", label="peg 1.00")
    ax.axhline(0.99, color="#7f7f7f", linewidth=1.0, linestyle="--", label="baseline A0 trigger 0.99")
    ax.set_ylabel("USDC price (USD)")
    ax.set_ylim(0.855, 1.012)
    ax.set_title(
        "USDC venue divergence during the SVB weekend — the same asset, three different prices",
        fontsize=12, fontweight="bold", loc="left",
    )
    ax.legend(loc="lower right", fontsize=9, framealpha=0.92)
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.tick_params(axis="x", labelsize=9)

    for label, colour, ls in (
        ("defillama_supply_aggregate", "#1f77b4", "-"),
        ("defillama_supply_ethereum", "#9467bd", "--"),
    ):
        series = supply[label]
        if not series:
            continue
        xs = [t for t, _ in series]
        ys = [v for _, v in series]
        pretty = "aggregate (all chains)" if "aggregate" in label else "Ethereum only"
        ax2.plot(xs, ys, color=colour, linestyle=ls, linewidth=1.7, label=pretty)
    # Supply deltas: only annotate series that actually have points (the plot
    # loop above already skips empty ones -- indexing blindly here would crash).
    if supply["defillama_supply_aggregate"] and supply["defillama_supply_ethereum"]:
        first_a, last_a = supply["defillama_supply_aggregate"][0], supply["defillama_supply_aggregate"][-1]
        first_e, last_e = supply["defillama_supply_ethereum"][0], supply["defillama_supply_ethereum"][-1]
        ax2.text(
            0.015, 0.05,
            f"aggregate: {first_a[1]:.1f} → {last_a[1]:.1f} bn USD "
            f"({last_a[1] - first_a[1]:+.1f}, {100 * (last_a[1] / first_a[1] - 1):+.0f}%)\n"
            f"Ethereum:  {first_e[1]:.1f} → {last_e[1]:.1f} bn USD "
            f"({last_e[1] - first_e[1]:+.1f}, {100 * (last_e[1] / first_e[1] - 1):+.0f}%)",
            transform=ax2.transAxes, fontsize=9, va="bottom", ha="left",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#999999", alpha=0.95),
        )
    ax2.set_ylabel("Circulating supply (bn USD)")
    ax2.set_title("Supply contraction around the crisis (daily)", fontsize=10.5, loc="left")
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(alpha=0.25)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))

    fig.text(
        0.01, 0.005,
        "Source: ORVYREN-Core corpus (corpus/usdc_observations.csv), collected 2026-10-14 — "
        "DeFiLlama aggregate, Bitstamp, Binance. Values are stored observations; no smoothing.",
        fontsize=7.2, color="#555555",
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight")
    print("figure:", OUT)
    for label, series in sorted(prices.items()):
        lo_t, lo_v = min(series, key=lambda p: p[1])
        print(f"  {label:24s} min {lo_v:.5f} @ {lo_t:%Y-%m-%dT%H:%MZ}  ({len(series)} pts)")
    for label, series in supply.items():
        if series:
            print(f"  {label:24s} {series[0][1]:.2f} → {series[-1][1]:.2f} bn USD ({len(series)} pts)")


if __name__ == "__main__":
    main()
