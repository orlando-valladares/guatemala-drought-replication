#!/usr/bin/env python3
"""Build the CHIRPS map bodies used in the field-report layout.

Each panel labels national rainfall, historical national median, z-score, and
percentile with exactly the reference period used to colour the municipalities.
The map bodies use one shared Guatemala City marker; field-site markers belong
only in the separate field-site comparison figure.
"""
from __future__ import annotations

from pathlib import Path
import shutil

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import make_valid

from prepare_appendix_data import annual_means

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
MUNIS = WORKSPACE / "02_projects" / "07_Playdata" / "02_Guatemala" / "sources" / "JSON_Departamenos_Municipios_LugaresPoblados" / "Mapas-TopoJSON-Guatemala-main" / "munis.json"
DERIVED = PROJECT / "derived"
TABLES = PROJECT / "figures" / "Appendix" / "tables"
BODY = PROJECT / "figures" / ".tex_body"
OVERLEAF_ASSETS = PROJECT / "overleaf" / "assets" / "figures"
COUNTRY_FIGURES = WORKSPACE / "02_projects" / "07_Playdata" / "02_Guatemala" / "figures"
DEPARTMENT_EXPORTS = COUNTRY_FIGURES / "showing_departments"
CAPITAL_ID = 101

PGROUPS = ["0", "1-10", "11-25", "26-50", "51-75", "76-100"]
PCOLOURS = {"0": "#67000d", "1-10": "#cb181d", "11-25": "#fb6a4a", "26-50": "#fdd0a2", "51-75": "#9ecae1", "76-100": "#3182bd"}
PLABELS = {"0": "P0", "1-10": "P1--10", "11-25": "P11--25", "26-50": "P26--50", "51-75": "P51--75", "76-100": "P76--100"}
ZGROUPS = ["z_ge_0", "z_m05_to_0", "z_m10_to_m05", "z_m15_to_m10", "z_m20_to_m15", "z_m25_to_m20", "z_lt_m25"]
ZCOLOURS = {"z_ge_0": "#2171b5", "z_m05_to_0": "#fff7d6", "z_m10_to_m05": "#fdd835", "z_m15_to_m10": "#fb8c00", "z_m20_to_m15": "#ef5350", "z_m25_to_m20": "#c62828", "z_lt_m25": "#67000d"}
ZLABELS = {"z_ge_0": "z >= 0", "z_m05_to_0": "-0.5 <= z < 0", "z_m10_to_m05": "-1.0 <= z < -0.5", "z_m15_to_m10": "-1.5 <= z < -1.0", "z_m20_to_m15": "-2.0 <= z < -1.5", "z_m25_to_m20": "-2.5 <= z < -2.0", "z_lt_m25": "z < -2.5"}


def load_geometry() -> gpd.GeoDataFrame:
    geo = gpd.read_file(MUNIS)
    if geo.crs is None:
        geo = geo.set_crs("EPSG:4326")
    geo = geo.loc[~geo["id"].astype(str).eq("0") & ~geo["Departamento"].str.upper().eq("BELICE")].copy()
    geo.loc[~geo.geometry.is_valid, "geometry"] = geo.loc[~geo.geometry.is_valid, "geometry"].map(make_valid)
    geo["municipality_id"] = pd.to_numeric(geo["id"], errors="raise").astype(int)
    geo = geo.rename(columns={"Departamento": "department", "Municipio": "municipality"})
    if len(geo) != 340:
        raise ValueError("Expected 340 Guatemala municipality polygons.")
    return geo[["municipality_id", "department", "municipality", "geometry"]]


def capital_point(geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return the centroid of Guatemala City municipality, the sole map marker."""
    point = geo.loc[geo["municipality_id"].eq(CAPITAL_ID)].to_crs("EPSG:6933").copy()
    if len(point) != 1:
        raise ValueError("Could not identify Guatemala City municipality (0101).")
    point["geometry"] = point.centroid
    return point.to_crs(geo.crs)


def pgroup(value: float) -> str:
    if value == 0: return "0"
    if value <= 10: return "1-10"
    if value <= 25: return "11-25"
    if value <= 50: return "26-50"
    if value <= 75: return "51-75"
    return "76-100"


def zgroup(value: float) -> str:
    if value >= 0: return "z_ge_0"
    if value >= -0.5: return "z_m05_to_0"
    if value >= -1.0: return "z_m10_to_m05"
    if value >= -1.5: return "z_m15_to_m10"
    if value >= -2.0: return "z_m20_to_m15"
    if value >= -2.5: return "z_m25_to_m20"
    return "z_lt_m25"


def reference_years(year: int, method: str, columns: list[int]) -> list[int]:
    if method == "available":
        return list(range(1981, year))
    if method == "leave_one_out":
        return [candidate for candidate in columns if candidate != year]
    if method == "fixed_1981_2025":
        return list(range(1981, 2026))
    raise ValueError(method)


def panel(values: pd.DataFrame, national: pd.Series, year: int, method: str) -> tuple[pd.DataFrame, str]:
    refs = reference_years(year, method, list(values.columns))
    local = values[refs]
    focal = values[year]
    z = (focal - local.mean(axis=1)) / local.std(axis=1, ddof=1)
    result = pd.DataFrame({
        "municipality_id": values.index.to_numpy(),
        "pgroup": (100 * local.le(focal, axis=0).mean(axis=1)).map(pgroup).to_numpy(),
        "zgroup": z.map(zgroup).to_numpy(),
    })
    nref = national.loc[refs]
    rain = national.loc[year]
    pct = 100 * (nref <= rain).mean()
    z_national = (rain - nref.mean()) / nref.std(ddof=1)
    header = f"{year}\nNac.: {rain:.0f} mm | Med. hist.: {nref.median():.0f} mm | z = {z_national:.2f} | P{pct:.1f}"
    return result, header


def draw_capital(ax, capital: gpd.GeoDataFrame) -> None:
    capital.plot(ax=ax, marker="*", color="#111111", edgecolor="white", linewidth=.65, markersize=62, zorder=10)


def capital_handle() -> Line2D:
    return Line2D([0], [0], marker="*", color="white", markerfacecolor="#111111", markeredgecolor="white", markersize=8.5, label="Ciudad de Guatemala")


def draw(ax, geo: gpd.GeoDataFrame, info: pd.DataFrame, capital: gpd.GeoDataFrame, header: str, kind: str,
         header_size: float = 8.7, year_size: float | None = None, department_borders: bool = True) -> None:
    """Draw a municipal map, optionally overlaying department outlines for exports."""
    column, groups, colours = ("pgroup", PGROUPS, PCOLOURS) if kind == "p" else ("zgroup", ZGROUPS, ZCOLOURS)
    values = geo.merge(info, on="municipality_id", validate="one_to_one")
    for group in groups:
        selected = values.loc[values[column].eq(group)]
        if not selected.empty:
            selected.plot(ax=ax, color=colours[group], edgecolor="white", linewidth=.12, zorder=1)
    if department_borders:
        geo.dissolve(by="department").boundary.plot(ax=ax, color="#111111", linewidth=.68, zorder=7)
    draw_capital(ax, capital)
    year, statistics = header.split("\n", maxsplit=1)
    if year_size is None:
        ax.text(0, 1.017, header, transform=ax.transAxes, fontsize=header_size, fontweight="bold", va="bottom", linespacing=1.12)
    else:
        ax.text(0, 1.050, year, transform=ax.transAxes, fontsize=year_size, fontweight="bold", va="bottom")
        ax.text(0, 1.007, statistics, transform=ax.transAxes, fontsize=header_size, fontweight="bold", va="bottom")
    ax.set_axis_off()
    ax.set_aspect("equal")


def handles(kind: str) -> list:
    if kind == "p":
        return [Patch(facecolor=PCOLOURS[group], edgecolor="white", label=PLABELS[group]) for group in PGROUPS]
    return [Patch(facecolor=ZCOLOURS[group], edgecolor="white", label=ZLABELS[group]) for group in ZGROUPS]


def save(fig, stem: str, appendix: bool = False, alternate: Path | None = None) -> None:
    """Save either a report asset or a country-level department-border export."""
    if alternate is not None:
        alternate.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(alternate, bbox_inches="tight", pad_inches=.025, facecolor="white")
        plt.close(fig)
        return
    BODY.mkdir(parents=True, exist_ok=True)
    prefix = "appendix_" if appendix else ""
    path = BODY / f"{prefix}{stem}_body.pdf"
    fig.savefig(path, bbox_inches="tight", pad_inches=.025, facecolor="white")
    OVERLEAF_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, OVERLEAF_ASSETS / path.name)
    plt.close(fig)


def single(geo, capital, info, header, kind, stem) -> None:
    """Single-map panel sized for half a report page, with legible in-map text."""
    fig, ax = plt.subplots(figsize=(5.75, 6.15), facecolor="white")
    draw(ax, geo, info, capital, header, kind, header_size=12.3)
    ax.legend(handles=handles(kind) + [capital_handle()], loc="lower left", fontsize=10.2, frameon=False,
              labelspacing=.38, ncol=2, columnspacing=.8, handlelength=1.1)
    fig.subplots_adjust(left=.015, right=.985, top=.895, bottom=.03)
    save(fig, stem)


def percentile_trio(geo, capital, values, national, years, method, stem) -> None:
    """Retained as a reusable project output; the report uses the 3 x 3 family."""
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.65), facecolor="white")
    for ax, year in zip(axes, years, strict=True):
        info, header = panel(values, national, year, method)
        draw(ax, geo, info, capital, header, "p", header_size=9.5)
    fig.legend(handles=handles("p") + [capital_handle()], loc="lower center", ncol=7, fontsize=8.4,
               frameon=False, bbox_to_anchor=(.5, .008), columnspacing=.72, handlelength=1.08)
    fig.tight_layout(rect=(0, .085, 1, .95), w_pad=.16)
    save(fig, stem)


def _family_grid_main(geo, capital, values, national, kind: str, stem: str,
                      department_borders: bool = True, alternate: Path | None = None) -> None:
    """Portrait main-body family with dedicated row headings and readable headers."""
    families = [
        ([2025, 2026], "available", "Años recientes — referencia disponible antes de cada año"),
        ([2015, 2026], "leave_one_out", "Comparadores históricos — referencia común retrospectiva, sin año focal"),
        ([2015, 2026], "available", "Comparadores históricos — referencia disponible antes de cada año"),
    ]
    fig = plt.figure(figsize=(8.42, 11.15), facecolor="white")
    grid = fig.add_gridspec(6, 2, height_ratios=[.18, 1, .18, 1, .18, 1],
                            left=.036, right=.976, top=.965, bottom=.098, wspace=.035, hspace=.0)
    map_axes = []
    heading_axes = []
    for row, (years, method, label) in enumerate(families):
        heading = fig.add_subplot(grid[2 * row, :])
        heading.set_axis_off()
        heading.text(.002, .94, label, transform=heading.transAxes, ha="left", va="top",
                     fontsize=10.15, fontweight="bold", color="#333333")
        heading_axes.append(heading)
        axes = []
        for col, year in enumerate(years):
            ax = fig.add_subplot(grid[2 * row + 1, col])
            info, header = panel(values, national, year, method)
            draw(ax, geo, info, capital, compact_percentile_header(header), kind,
                 header_size=8.95, year_size=13.2, department_borders=department_borders)
            axes.append(ax)
        map_axes.append(axes)
    # The line makes the recent-year pair visually distinct from historical comparisons.
    separator_y = heading_axes[1].get_position().y1 + .004
    fig.add_artist(Line2D([.036, .976], [separator_y, separator_y], transform=fig.transFigure,
                          color="#555555", linewidth=1.0, zorder=20))
    fig.legend(handles=handles(kind) + [capital_handle()], loc="lower center", ncol=4, fontsize=10.2,
               frameon=False, bbox_to_anchor=(.5, .002), columnspacing=.93, handlelength=1.28,
               labelspacing=.42)
    save(fig, stem, alternate=alternate)


def _row_heading(fig, axes, row: int, label: str, *, size: float = 9.3) -> None:
    """Place an appendix row heading in the whitespace above its map row."""
    position = axes[row, 0].get_position()
    fig.text(.022, position.y1 + .017, label, ha="left", va="bottom", fontsize=size,
             fontweight="bold", color="#333333")


def family_grid_main_zscore(geo, capital, values, national) -> None:
    _family_grid_main(geo, capital, values, national, "z", "fig01_zscore_map_family_3x2")


def family_grid_main_percentile(geo, capital, values, national) -> None:
    # Retained only as a final-status vector asset for older report references.
    _family_grid_main(geo, capital, values, national, "p", "fig01_percentile_map_family_3x2")


def percentile_family_grid_legacy(geo, capital, values, national, *, department_borders: bool = True,
                                  alternate: Path | None = None) -> None:
    """Appendix 3x3 percentile family retaining the 2019 comparison column."""
    families = [
        ([2024, 2025, 2026], "available", "Años recientes — referencia disponible antes de cada año"),
        ([2015, 2019, 2026], "leave_one_out", "Comparadores históricos — referencia común retrospectiva, sin año focal"),
        ([2015, 2019, 2026], "available", "Comparadores históricos — referencia disponible antes de cada año"),
    ]
    fig, axes = plt.subplots(3, 3, figsize=(13.85, 9.15), facecolor="white")
    for row, (years, method, label) in enumerate(families):
        for ax, year in zip(axes[row], years, strict=True):
            info, header = panel(values, national, year, method)
            draw(ax, geo, info, capital, header, "p", header_size=9.55,
                 department_borders=department_borders)
    fig.subplots_adjust(left=.018, right=.992, top=.950, bottom=.115, wspace=.018, hspace=.47)
    for row, (_, _, label) in enumerate(families):
        _row_heading(fig, axes, row, label, size=8.85)
    fig.legend(handles=handles("p") + [capital_handle()], loc="lower center", ncol=7, fontsize=9.2,
               frameon=False, bbox_to_anchor=(.5, .015), columnspacing=.78, handlelength=1.08)
    save(fig, "fig01_percentile_map_family_3x3", alternate=alternate)


def compact_percentile_header(header: str) -> str:
    """Shorten only the repeated labels in the larger report grid."""
    year, statistics = header.split("\n", maxsplit=1)
    statistics = (statistics.replace("Nac.:", "Nac.")
                             .replace("Med. hist.:", "Med.")
                             .replace("z =", "z"))
    return f"{year}\n{statistics}"


def appendix_zscore_family(geo, capital, values, national, *, department_borders: bool = True,
                          alternate: Path | None = None) -> None:
    """Appendix 3x3 z-score analogue, preserving 2019 and the two frames."""
    families = [
        ([2024, 2025, 2026], "available", "Años recientes — referencia disponible antes de cada año"),
        ([2015, 2019, 2026], "leave_one_out", "Comparadores históricos — referencia común retrospectiva, sin año focal"),
        ([2015, 2019, 2026], "available", "Comparadores históricos — referencia disponible antes de cada año"),
    ]
    fig, axes = plt.subplots(3, 3, figsize=(13.85, 9.15), facecolor="white")
    for row, (years, method, label) in enumerate(families):
        for ax, year in zip(axes[row], years, strict=True):
            info, header = panel(values, national, year, method)
            draw(ax, geo, info, capital, header, "z", header_size=9.55,
                 department_borders=department_borders)
    fig.subplots_adjust(left=.018, right=.992, top=.950, bottom=.115, wspace=.018, hspace=.47)
    for row, (_, _, label) in enumerate(families):
        _row_heading(fig, axes, row, label, size=8.85)
    fig.legend(handles=handles("z") + [capital_handle()], loc="lower center", ncol=4, fontsize=9.2,
               frameon=False, bbox_to_anchor=(.5, .015), columnspacing=.82, handlelength=1.08)
    save(fig, "app01_chirps_zscore_map_family", appendix=True, alternate=alternate)

def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})
    geo = load_geometry()
    capital = capital_point(geo)
    annual, years = annual_means(geo)
    if years != list(range(1981, 2026)):
        raise ValueError("Expected 1981--2025 CHIRPS history.")
    values = annual.pivot(index="municipality_id", columns="year", values="rain_may_aug_mm")
    current = pd.read_csv(DERIVED / "chirps_2026_municipality.csv").set_index("municipality_id")
    values[2026] = current.reindex(values.index)["rain_2026_may_aug_mm"]
    national = pd.read_csv(TABLES / "chirps_shock_comparison_national_annual.csv").set_index("year")["national_rain_may_aug_mm"].loc[list(range(1981, 2027))]

    # Only figures referenced by main.tex are copied into the author-facing
    # Overleaf project. Earlier standalone variants remain reproducible through
    # their functions but are deliberately not regenerated as report assets.
    family_grid_main_zscore(geo, capital, values, national)
    percentile_family_grid_legacy(geo, capital, values, national)
    appendix_zscore_family(geo, capital, values, national)
    DEPARTMENT_EXPORTS.mkdir(parents=True, exist_ok=True)
    _family_grid_main(geo, capital, values, national, "z", "fig01_zscore_map_family_3x2",
                      department_borders=True,
                      alternate=DEPARTMENT_EXPORTS / "mapa_01_zscores_fronteras_departamentales.pdf")
    percentile_family_grid_legacy(geo, capital, values, national, department_borders=True,
                                  alternate=DEPARTMENT_EXPORTS / "apendice_percentiles_3x3_fronteras_departamentales.pdf")
    appendix_zscore_family(geo, capital, values, national, department_borders=True,
                           alternate=DEPARTMENT_EXPORTS / "apendice_zscores_3x3_fronteras_departamentales.pdf")
    (DEPARTMENT_EXPORTS / "README.md").write_text(
        "# Mapas con fronteras departamentales\n\n"
        "Versiones derivadas de los mapas municipales del informe Dalton. Las líneas blancas finas "
        "son fronteras municipales; las líneas negras gruesas son fronteras departamentales, disueltas "
        "a partir del mismo TopoJSON municipal. Se generan con `python3 code/build_report_maps.py`.\n",
        encoding="utf-8",
    )
    print("Built report map bodies and country-level department-border variants.")


if __name__ == "__main__":
    main()
