"""Render clean main maps for the Dalton CHIRPS component.

Maps remain outside Stata because they require polygon geometries. All non-map
figures are rendered by the companion Stata publication-graphics do-file.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import make_valid


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
GUATEMALA = WORKSPACE / "02_projects" / "07_Playdata" / "02_Guatemala"
MUNIS = GUATEMALA / "sources" / "JSON_Departamenos_Municipios_LugaresPoblados" / "Mapas-TopoJSON-Guatemala-main" / "munis.json"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
APPENDIX = FIGURES / "Appendix"
TABLES = APPENDIX / "tables"
TEX_BODY = FIGURES / ".tex_body"
SITES = [("Olopa", "Chiquimula"), ("Chahal", "Alta Verapaz"), ("Patzité", "Quiché")]

GROUPS = ["0", "1-10", "11-25", "26-50", "51-75", "76-100"]
COLOURS = {
    "0": "#67000d",
    "1-10": "#cb181d",
    "11-25": "#fb6a4a",
    "26-50": "#fdd0a2",
    "51-75": "#9ecae1",
    "76-100": "#3182bd",
}
LABELS_AVAILABLE = {
    "0": "0: lower than every earlier total",
    "1-10": "1–10: exceptionally dry",
    "11-25": "11–25: dry",
    "26-50": "26–50: below median",
    "51-75": "51–75: above median",
    "76-100": "76–100: wet relative to history",
}
LABELS_LEAVE_ONE_OUT = {
    "0": "0: lower than every other total",
    "1-10": "1–10: exceptionally dry",
    "11-25": "11–25: dry",
    "26-50": "26–50: below median",
    "51-75": "51–75: above median",
    "76-100": "76–100: wet relative to history",
}
ZSCORE_GROUPS = ["z_ge_0", "z_m05_to_0", "z_m10_to_m05", "z_m15_to_m10", "z_m20_to_m15", "z_m25_to_m20", "z_lt_m25"]
ZSCORE_COLOURS = {
    "z_ge_0": "#2171b5",
    "z_m05_to_0": "#fff7d6",
    "z_m10_to_m05": "#fdd835",
    "z_m15_to_m10": "#fb8c00",
    "z_m20_to_m15": "#ef5350",
    "z_m25_to_m20": "#c62828",
    "z_lt_m25": "#67000d",
}
ZSCORE_LABELS = {
    "z_ge_0": "z ≥ 0",
    "z_m05_to_0": "−0.5 ≤ z < 0",
    "z_m10_to_m05": "−1.0 ≤ z < −0.5",
    "z_m15_to_m10": "−1.5 ≤ z < −1.0",
    "z_m20_to_m15": "−2.0 ≤ z < −1.5",
    "z_m25_to_m20": "−2.5 ≤ z < −2.0",
    "z_lt_m25": "z < −2.5",
}


def load_geometry() -> gpd.GeoDataFrame:
    geo = gpd.read_file(MUNIS)
    if geo.crs is None:
        geo = geo.set_crs("EPSG:4326")
    geo = geo.loc[~geo["id"].astype(str).eq("0") & ~geo["Departamento"].str.upper().eq("BELICE")].copy()
    geo.loc[~geo.geometry.is_valid, "geometry"] = geo.loc[~geo.geometry.is_valid, "geometry"].map(make_valid)
    geo["municipality_id"] = pd.to_numeric(geo["id"], errors="raise").astype(int)
    geo = geo.rename(columns={"Departamento": "department", "Municipio": "municipality"})
    if len(geo) != 340 or geo["municipality_id"].duplicated().any():
        raise ValueError("Expected exactly 340 unique Guatemala municipality polygons.")
    return geo[["municipality_id", "department", "municipality", "geometry"]]


def site_points(geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = geo.to_crs("EPSG:6933").copy()
    points["geometry"] = points.centroid
    points = points.to_crs(geo.crs)
    wanted = pd.DataFrame(SITES, columns=["municipality", "department"])
    return points.merge(wanted, on=["municipality", "department"], validate="one_to_one")


def draw_base(ax, values: gpd.GeoDataFrame) -> None:
    for group in GROUPS:
        subset = values.loc[values["percentile_group"].eq(group)]
        if not subset.empty:
            subset.plot(ax=ax, color=COLOURS[group], edgecolor="white", linewidth=0.10, zorder=1)
    ax.set_axis_off()
    ax.set_aspect("equal")


def draw_sites(ax, points: gpd.GeoDataFrame, labels: bool = False) -> None:
    points.plot(ax=ax, marker="o", color="#111111", edgecolor="white", linewidth=0.7, markersize=32, zorder=10)
    if labels:
        for item in points.itertuples():
            ax.annotate(
                item.municipality, (item.geometry.x, item.geometry.y), xytext=(3.5, 3.5),
                textcoords="offset points", fontsize=7.2, color="#111111", zorder=11,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 0.12},
            )


def rainfall_handles(labels: dict[str, str] = LABELS_AVAILABLE) -> list:
    return [Patch(facecolor=COLOURS[group], edgecolor="white", label=labels[group]) for group in GROUPS]


def corridor_handles(ax, geo: gpd.GeoDataFrame) -> list:
    legacy = geo.loc[geo["legacy_sesan_core_2016"].eq(1)].geometry.union_all()
    expanded_only = geo.loc[geo["sesan_expanded_only_2025"].eq(1)].geometry.union_all()
    gpd.GeoSeries([expanded_only], crs=geo.crs).boundary.plot(
        ax=ax, color="#3f3f3f", linewidth=1.10, linestyle=(0, (5.5, 3.5)), zorder=6
    )
    gpd.GeoSeries([legacy], crs=geo.crs).boundary.plot(ax=ax, color="#111111", linewidth=1.75, zorder=7)
    return [
        Line2D([0], [0], color="#111111", lw=1.75, label="Legacy/core SESAN annex list (solid; 67 matched)"),
        Line2D([0], [0], color="#3f3f3f", lw=1.10, linestyle=(0, (5.5, 3.5)), label="Current expanded-only list (dashed; 93)"),
    ]


def save(fig, stem: str, appendix: bool = False) -> None:
    """Save geometry and legend only; TeX supplies title, subtitle, and notes."""
    TEX_BODY.mkdir(parents=True, exist_ok=True)
    prefix = "appendix_" if appendix else ""
    fig.savefig(TEX_BODY / f"{prefix}{stem}_body.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def choropleth_2026(geo: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> None:
    values = geo.merge(
        pd.read_csv(DERIVED / "chirps_historical_comparison_2015_2019_2026_municipality.csv").query("year == 2026")[
            ["municipality_id", "percentile_group"]
        ], on="municipality_id", validate="one_to_one"
    )
    fig, ax = plt.subplots(figsize=(7.45, 7.95), facecolor="white")
    draw_base(ax, values)
    draw_sites(ax, points, labels=True)
    handles = rainfall_handles() + [Line2D([0], [0], marker="o", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=6, label="Field municipality")]
    ax.legend(handles=handles, loc="lower left", fontsize=6.9, frameon=False, labelspacing=0.45, handlelength=1.25)
    fig.tight_layout()
    save(fig, "fig01a_chirps_percentile_2026")


def historical_comparison(
    geo: gpd.GeoDataFrame,
    points: gpd.GeoDataFrame,
    years: list[int],
    stem: str,
    comparison_file: str,
    labels: dict[str, str],
) -> None:
    comparisons = pd.read_csv(TABLES / comparison_file)
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 5.1), facecolor="white")
    for axis, year, panel in zip(axes, years, ["(a)", "(b)", "(c)"], strict=True):
        values = geo.merge(
            comparisons.loc[comparisons["year"].eq(year), ["municipality_id", "percentile_group"]],
            on="municipality_id", validate="one_to_one"
        )
        draw_base(axis, values)
        draw_sites(axis, points, labels=year == 2026)
        axis.text(0.0, 1.015, f"({panel}) {year}", transform=axis.transAxes, fontsize=8.5, fontweight="bold")
    fig.legend(handles=rainfall_handles(labels), loc="lower center", ncol=3, fontsize=7.2, frameon=False, bbox_to_anchor=(0.5, 0.07), columnspacing=1.1, handlelength=1.25)
    fig.tight_layout()
    save(fig, stem)


def common_reference_zscore_map(geo: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> None:
    zscores = pd.read_csv(TABLES / "chirps_common_reference_zscore_2015_2019_2025_municipality.csv")
    def zscore_group(value: float) -> str:
        if value >= 0:
            return "z_ge_0"
        if value >= -0.5:
            return "z_m05_to_0"
        if value >= -1.0:
            return "z_m10_to_m05"
        if value >= -1.5:
            return "z_m15_to_m10"
        if value >= -2.0:
            return "z_m20_to_m15"
        if value >= -2.5:
            return "z_m25_to_m20"
        return "z_lt_m25"
    zscores["zscore_group"] = zscores["rainfall_z_score_common"].map(zscore_group)
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 5.1), facecolor="white")
    for axis, year, panel in zip(axes, [2015, 2019, 2025], ["(a)", "(b)", "(c)"], strict=True):
        values = geo.merge(
            zscores.loc[zscores.year.eq(year), ["municipality_id", "zscore_group"]],
            on="municipality_id", validate="one_to_one",
        )
        for group in ZSCORE_GROUPS:
            subset = values.loc[values.zscore_group.eq(group)]
            if not subset.empty:
                subset.plot(ax=axis, color=ZSCORE_COLOURS[group], edgecolor="white", linewidth=0.10, zorder=1)
        draw_sites(axis, points, labels=year == 2025)
        axis.text(0.0, 1.015, f"{panel} {year}", transform=axis.transAxes, fontsize=8.5, fontweight="bold")
        axis.set_axis_off()
        axis.set_aspect("equal")
    handles = [Patch(facecolor=ZSCORE_COLOURS[group], edgecolor="white", label=ZSCORE_LABELS[group]) for group in ZSCORE_GROUPS]
    handles += [Line2D([0], [0], marker="o", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=6, label="Field municipality")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=7.1, frameon=False, bbox_to_anchor=(0.5, 0.055), columnspacing=1.0, handlelength=1.25)
    fig.tight_layout(rect=(0, 0.12, 1, 1), w_pad=0.15)
    save(fig, "fig01g_chirps_common_reference_zscore_2015_2019_2025")


def corridor_map(geo: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.45, 7.95), facecolor="white")
    geo.plot(ax=ax, color="#f4f4f4", edgecolor="#d6d6d6", linewidth=0.16, zorder=1)
    handles = corridor_handles(ax, geo)
    draw_sites(ax, points, labels=True)
    ax.set_axis_off(); ax.set_aspect("equal")
    handles += [Line2D([0], [0], marker="o", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=6, label="Field municipality")]
    ax.legend(handles=handles, loc="lower left", fontsize=7.1, frameon=False, labelspacing=0.55)
    fig.tight_layout()
    save(fig, "fig01d_sesan_corridor_definitions")


def overlap_map(geo: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> None:
    comparisons = pd.read_csv(DERIVED / "chirps_historical_comparison_2015_2019_2026_municipality.csv")
    values = geo.merge(comparisons.loc[comparisons["year"].eq(2026), ["municipality_id", "percentile_group"]], on="municipality_id", validate="one_to_one")
    fig, ax = plt.subplots(figsize=(7.45, 7.95), facecolor="white")
    draw_base(ax, values)
    handles = rainfall_handles() + corridor_handles(ax, values)
    draw_sites(ax, points, labels=True)
    handles += [Line2D([0], [0], marker="o", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=6, label="Field municipality")]
    ax.legend(handles=handles, loc="lower left", fontsize=6.5, frameon=False, labelspacing=0.38, handlelength=1.25)
    fig.tight_layout()
    save(fig, "fig01e_chirps_sesan_overlap_2026")


def fao_appendix_map(geo: gpd.GeoDataFrame, points: gpd.GeoDataFrame) -> None:
    asis = pd.read_csv(DERIVED / "fao_asis_2026_municipality.csv")
    values = geo.merge(asis[["municipality_id", "asis_value"]], on="municipality_id", validate="one_to_one")
    values["asis_class"] = pd.cut(values["asis_value"], [-0.001, 1, 10, 30, 60, 100.001], labels=["0–1", ">1–10", ">10–30", ">30–60", ">60–100"])
    palette = {"0–1": "#f7fbff", ">1–10": "#c6dbef", ">10–30": "#6baed6", ">30–60": "#2171b5", ">60–100": "#08306b"}
    fig, ax = plt.subplots(figsize=(7.45, 7.95), facecolor="white")
    for category, colour in palette.items():
        values.loc[values["asis_class"].eq(category)].plot(ax=ax, color=colour, edgecolor="white", linewidth=0.10, zorder=1)
    values.loc[values["asis_value"].isna()].plot(ax=ax, facecolor="#e5e7eb", edgecolor="#737373", hatch="....", linewidth=0.25, zorder=2)
    draw_sites(ax, points, labels=True)
    ax.set_axis_off(); ax.set_aspect("equal")
    handles = [Patch(facecolor=colour, edgecolor="white", label=f"{category}%") for category, colour in palette.items()]
    handles += [Patch(facecolor="#e5e7eb", edgecolor="#737373", hatch="....", label="No valid in-season cells"), Line2D([0], [0], marker="o", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=6, label="Field municipality")]
    ax.legend(handles=handles, loc="lower left", fontsize=6.9, frameon=False, labelspacing=0.42)
    fig.tight_layout()
    APPENDIX.mkdir(parents=True, exist_ok=True)
    save(fig, "app01_fao_asis_municipality_map", appendix=True)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    APPENDIX.mkdir(parents=True, exist_ok=True)
    geo = load_geometry()
    corridor = pd.read_csv(TABLES / "table_corridor_definitions.csv")
    geo = geo.merge(corridor[["municipality_id", "legacy_sesan_core_2016", "sesan_expanded_only_2025"]], on="municipality_id", validate="one_to_one")
    points = site_points(geo)
    choropleth_2026(geo, points)
    historical_comparison(
        geo, points, [2015, 2019, 2026], "fig01b_chirps_driest_years_2015_2019_2026",
        "chirps_common_reference_leave_one_out_municipality.csv", LABELS_LEAVE_ONE_OUT,
    )
    historical_comparison(
        geo, points, [2024, 2025, 2026], "fig01c_chirps_recent_years_2024_2025_2026",
        "chirps_reference_available_each_year_municipality.csv", LABELS_AVAILABLE,
    )
    common_reference_zscore_map(geo, points)
    corridor_map(geo, points)
    overlap_map(geo, points)
    fao_appendix_map(geo, points)
    print("Built six main-map bodies and one Appendix FAO-map body for TeX framing.")


if __name__ == "__main__":
    main()
