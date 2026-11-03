#!/usr/bin/env python3
"""Build the compact publication figures used by the Overleaf drought brief.

The three first-page figures use the existing 234 x 145 point report-body
standard. Figure 4 is a full-width four-map assembly. Titles and source notes
remain in LaTeX; the PDFs contain only the plot body and internal legends.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"
PDF_OUT = ROOT / "out" / "figures" / "pdf"
PNG_OUT = ROOT / "out" / "figures" / "png"
MONTHLY = DATA / "monthly_rainfall_1981_2026.csv"


ORANGE = "#E35925"
BLUE = "#1976A3"
TEAL = "#319F90"
PURPLE = "#7566A8"
GRAY = "#747474"
LIGHT_GRAY = "#E9E9E4"
POSTRERA = "#F7D5C6"
GRID = "#DEDEDE"
INK = "#303030"
RED_SCALE = ["#FFF5F0", "#FCBBA1", "#FC9272", "#EF3B2C", "#99000D"]
GREEN_SCALE = ["#EDF8F5", "#B2E2E2", "#66C2A4", "#2CA25F", "#006D2C"]
BLUE_SCALE = ["#EFF3FF", "#BDD7E7", "#6BAED6", "#3182BD", "#08519C"]
ORANGE_SCALE = ["#FFF5EB", "#FDD0A2", "#FDAE6B", "#F16913", "#A63603"]


def style() -> None:
    mpl.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 6.4,
        "axes.labelsize": 6.4,
        "xtick.labelsize": 5.8,
        "ytick.labelsize": 5.8,
        "legend.fontsize": 6.2,
        "axes.edgecolor": "#666666",
        "axes.linewidth": .55,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save(fig: plt.Figure, stem: str) -> None:
    PDF_OUT.mkdir(parents=True, exist_ok=True)
    PNG_OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(PDF_OUT / f"{stem}.pdf", facecolor="white", metadata={"Creator": "Guatemala drought replication"})
    fig.savefig(PNG_OUT / f"{stem}.png", facecolor="white", dpi=220)
    plt.close(fig)


def clean_axis(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=GRID, linewidth=.45, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=2, width=.45, color="#777777", pad=1.5)


def figure1_monthly() -> None:
    data = pd.read_csv(MONTHLY)
    hist = data.loc[data.year.le(2025)]
    y15 = data.loc[data.year.eq(2015)].set_index("month")
    y26 = data.loc[data.year.eq(2026)].set_index("month")
    fig, ax = plt.subplots(figsize=(3.25, 2.02))
    ax.axvspan(.5, 4.5, color=LIGHT_GRAY, zorder=-2)
    # Split the September box exactly at its centre: its left half remains in
    # the Primera field and its right half begins the Postrera field.
    ax.axvspan(9.0, 12.5, color=POSTRERA, zorder=-2)
    for month in range(1, 13):
        values = hist.loc[hist.month.eq(month), "rain_mm"].to_numpy()
        p10, p25, p50, p75, p90 = np.quantile(values, [.1, .25, .5, .75, .9])
        ax.vlines(month, p10, p90, color=GRAY, linewidth=.65, zorder=2)
        ax.hlines([p10, p90], month-.12, month+.12, color=GRAY, linewidth=.65, zorder=2)
        ax.add_patch(plt.Rectangle((month-.25, p25), .5, p75-p25,
                                   facecolor="#D8D8D8", edgecolor=GRAY, linewidth=.55, zorder=2))
        ax.hlines(p50, month-.25, month+.25, color="#4F4F4F", linewidth=.75, zorder=3)
        if month in y15.index:
            ax.scatter(month-.09, y15.loc[month, "rain_mm"], marker="^", s=14,
                       color=BLUE, edgecolor="white", linewidth=.35, zorder=4)
        if month in y26.index:
            ax.scatter(month+.09, y26.loc[month, "rain_mm"], marker="o", s=14,
                       color=ORANGE, edgecolor="white", linewidth=.35, zorder=4)
    ax.set_xlim(.5, 12.5)
    ax.set_ylim(0, 620)
    ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_ylabel("Monthly rainfall (mm)", labelpad=2)
    clean_axis(ax)
    handles = [
        Patch(facecolor=LIGHT_GRAY, edgecolor="#BBBBB5", linewidth=.5, label="No season"),
        Patch(facecolor="white", edgecolor="#999999", linewidth=.5, label="Primera"),
        Patch(facecolor=POSTRERA, edgecolor=POSTRERA, label="Postrera"),
        Line2D([], [], marker="^", linestyle="none", markersize=4, color=BLUE, label="2015"),
        Line2D([], [], marker="o", linestyle="none", markersize=4, color=ORANGE, label="2026"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, 1.14), ncol=5,
              frameon=False, handlelength=1.1, columnspacing=.9, handletextpad=.35, borderaxespad=0)
    fig.subplots_adjust(left=.13, right=.995, bottom=.16, top=.86)
    save(fig, "figure-1-monthly-rainfall")


def figure2_pdf() -> None:
    curves = pd.read_csv(DATA / "chirps_distribution_curves.csv")
    fig, ax = plt.subplots(figsize=(3.25, 2.02))
    colors = {"Pooled": GRAY, "2015": BLUE, "2026": ORANGE}
    population_styles = {"Municipalities": (0, (4, 2)), "Agricultural workers": "solid"}
    for population in ("Municipalities", "Agricultural workers"):
        primary = population == "Agricultural workers"
        for series in ("Pooled", "2015", "2026"):
            row = curves.loc[curves.population.eq(population) & curves.series.eq(series)]
            ax.plot(row.z, row.pdf, color=colors[series], linestyle=population_styles[population],
                    linewidth=1.65 if primary else .9, alpha=1 if primary else .20, zorder=3 if primary else 2)
    ax.axvline(-2, color="#777777", linewidth=.65, linestyle=(0, (2, 2)), zorder=1)
    ax.text(-1.96, ax.get_ylim()[1]*.92, "Extreme threshold  z = −2", color="#666666", fontsize=5.7)
    ax.set_xlim(-4.5, 2.5)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("CHIRPS Primera anomaly (leave-one-out z)", labelpad=2)
    ax.set_ylabel("Density", labelpad=2)
    clean_axis(ax)
    year_handles = [Line2D([], [], color=colors[s], linewidth=2, linestyle="solid", label=s)
                    for s in ("Pooled", "2015", "2026")]
    year_legend = ax.legend(handles=year_handles, loc="upper center", bbox_to_anchor=(.5, 1.43), ncol=3,
                            frameon=False, handlelength=2.3, columnspacing=1.45, borderaxespad=0)
    ax.add_artist(year_legend)
    style_handles = [
        Line2D([], [], color=INK, linewidth=.9, linestyle=population_styles["Municipalities"],
               label="Dashed: municipalities (unweighted)"),
        Line2D([], [], color=INK, linewidth=1.65, linestyle=population_styles["Agricultural workers"],
               label="Solid: agricultural-worker weighted"),
    ]
    ax.legend(handles=style_handles, loc="upper center", bbox_to_anchor=(.5, 1.28), ncol=1,
              fontsize=5.25, frameon=False, handlelength=2.4, labelspacing=.25,
              handletextpad=.4, borderaxespad=0)
    fig.subplots_adjust(left=.13, right=.995, bottom=.19, top=.70)
    save(fig, "figure-2-rainfall-anomaly")


def figure3_exposure() -> None:
    climate = pd.read_csv(DATA / "climate_exposure_annual.csv")
    climate = climate.loc[climate.window.eq("Primera (May--Aug)")]
    era = climate.loc[climate["product"].eq("ERA5-Land")]
    chirps = climate.loc[climate["product"].eq("CHIRPS")]
    fig, ax = plt.subplots(figsize=(3.25, 2.02))
    specs = [
        (era, "department_share_pct", ORANGE, True, "ERA5 territory"),
        (era, "agricultural_worker_share_pct", ORANGE, False, "ERA5 workers"),
        (chirps, "department_share_pct", BLUE, True, "CHIRPS territory"),
        (chirps, "agricultural_worker_share_pct", BLUE, False, "CHIRPS workers"),
    ]
    # A single uniform time scale intentionally shows the clustering of large
    # drought-exposure events near the present. Wide grouped bars may overlap
    # adjacent zero-drought years slightly, while remaining centred on year.
    offsets = [-.72, -.24, .24, .72]
    for (frame, metric, color, outline, _), offset in zip(specs, offsets):
        ax.bar(frame.year + offset, frame[metric], width=.48,
               color="white" if outline else color, edgecolor=color,
               linewidth=.7, zorder=3)
    ax.set_xlim(1949, 2027.2)
    ax.set_ylim(0, 100)
    clean_axis(ax)
    ax.axvline(1981, color="#666666", linestyle=(0, (2, 2)), linewidth=.65, zorder=1)
    ax.text(1982, 94, "CHIRPS begins", fontsize=5.7, color="#666666")
    ax.set_xticks([1950, 1970, 1981, 1990, 2000, 2010, 2015, 2020, 2026])
    ax.tick_params(axis="x", labelrotation=42)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")
    ax.set_ylabel("Share below z = −2 (%)", labelpad=2)
    handles = [Patch(facecolor="white" if outline else color, edgecolor=color, linewidth=.7, label=label)
               for _, _, color, outline, label in specs]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, .985), ncol=2,
               frameon=False, fontsize=7.2, handlelength=1.55, columnspacing=1.4, handletextpad=.45)
    fig.subplots_adjust(left=.13, right=.995, bottom=.25, top=.79)
    save(fig, "figure-3-extreme-drought-exposure")


def geodata() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    municipal = gpd.read_file(DATA / "figure4_municipal.geojson")
    department = gpd.read_file(DATA / "figure4_department.geojson")
    department["label_point"] = list(zip(department.label_lon, department.label_lat))
    table = pd.read_csv(DATA / "appendix_A3_department.csv")
    table = table.loc[table.national_row.eq(0)].copy()
    department = department.merge(table, on="department", validate="one_to_one")
    return municipal, department


def classify(values: pd.Series, edges: list[float]) -> np.ndarray:
    return np.clip(np.digitize(values.to_numpy(), edges, right=False), 0, len(edges))


def map_panel(ax: plt.Axes, geo: gpd.GeoDataFrame, classes: np.ndarray, colors: list[str],
              title: str, stats: tuple[str, str], labels: list[str], bubbles: bool = False) -> None:
    ax.set_axis_off()
    for code, color in enumerate(colors):
        geo.loc[classes == code].plot(ax=ax, color=color, edgecolor="white", linewidth=.18, zorder=1)
    ax.text(0, 1.155, title, transform=ax.transAxes, ha="left", va="bottom",
            fontsize=7.0, weight="bold", linespacing=.9)
    ax.text(0, 1.095, stats[0], transform=ax.transAxes, ha="left", va="bottom", fontsize=5.7, weight="bold", color="#4A4A4A")
    ax.text(0, 1.035, stats[1], transform=ax.transAxes, ha="left", va="bottom", fontsize=5.7, weight="bold", color="#4A4A4A")
    handles = [Patch(facecolor=c, edgecolor="#777777", linewidth=.3, label=l) for c, l in zip(colors, labels)]
    if bubbles:
        counts = geo.agricultural_workers.to_numpy()
        lo, hi = np.sqrt(counts.min()), np.sqrt(counts.max())
        sizes = 9 + 120 * (np.sqrt(counts)-lo)/(hi-lo)
        points = geo.label_point.to_list()
        ax.scatter([p[0] for p in points], [p[1] for p in points], s=sizes,
                   facecolor="#FFFFFFAA", edgecolor="#005A2B", linewidth=.75, zorder=4)
        for value in (25_000, 75_000, 175_000):
            size = 9 + 120 * (np.sqrt(value)-lo)/(hi-lo)
            handles.append(Line2D([], [], marker="o", linestyle="none", markersize=np.sqrt(max(size, 1)),
                                  markerfacecolor="white", markeredgecolor="#005A2B",
                                  label=f"{value/1000:.0f}k workers"))
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, -.18), ncol=2 if bubbles else 3,
              frameon=False, fontsize=5.2, handlelength=1.1, columnspacing=.4,
              handletextpad=.22, borderaxespad=0, labelspacing=.2)


def figure4_maps() -> None:
    municipal, dept = geodata()
    fig, axes = plt.subplots(1, 4, figsize=(7.0, 2.35))
    z_edges = [-2.5, -2, -1.5, -1]
    z_classes = classify(municipal.z, z_edges)
    z_labels = ["< −2.5 SD", "−2.5–−2", "−2–−1.5", "−1.5–−1", "≥ −1 SD"]
    map_panel(axes[0], municipal, z_classes, RED_SCALE[::-1],
              "a. CHIRPS municipal\nanomaly, 2026",
              ("757 mm in 2026", "Historical mean 1,102 mm (SD 179)"),
              z_labels)

    share_edges = [20, 30, 40, 50]
    share_classes = classify(dept.agricultural_dependence_pct, share_edges)
    map_panel(axes[1], dept, share_classes, GREEN_SCALE,
              "b. Agricultural\nemployment, 2018",
              ("1,393,220 agricultural workers", "28.0% of occupied workers"),
              ["<20%", "20–30%", "30–40%", "40–50%", "≥50%"], bubbles=True)

    poverty_edges = [40, 55, 70, 85]
    poverty_classes = classify(dept.poverty_general_pct, poverty_edges)
    map_panel(axes[2], dept, poverty_classes, BLUE_SCALE,
              "c. Poverty,\nENCOVI 2023",
              ("56.0% in poverty", "16.2% in extreme poverty"),
              ["<40%", "40–55%", "55–70%", "70–85%", "≥85%"])

    priority_edges = [20, 35, 50, 65]
    priority_classes = classify(dept.r_bal, priority_edges)
    map_panel(axes[3], dept, priority_classes, ORANGE_SCALE,
              "d. Department\nprioritization",
              ("Balanced priority index", "R = 100(Z⁰·⁴⁰ N⁰·²⁰ S⁰·²⁰ P⁰·²⁰)"),
              ["<20", "20–35", "35–50", "50–65", "≥65"])
    for ax in axes.flat:
        dept.boundary.plot(ax=ax, color="#4D4D4D", linewidth=.35, zorder=3)
    # Lower the axes enough to keep both wrapped title lines inside the PDF box.
    fig.subplots_adjust(left=.008, right=.992, bottom=.16, top=.76, wspace=.08)
    save(fig, "figure-4-four-map-assemblage")


def main() -> None:
    style()
    figure1_monthly()
    figure2_pdf()
    figure3_exposure()
    figure4_maps()
    print(f"Wrote publication figures to {PDF_OUT} and {PNG_OUT}")


if __name__ == "__main__":
    main()
