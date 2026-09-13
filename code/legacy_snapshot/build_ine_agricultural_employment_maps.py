#!/usr/bin/env python3
"""Build reproducible 2018 municipal agricultural-employment maps for Dalton.

Inputs stay in the shared Guatemala source library. The script joins the
official Censo 2018 A12.2 municipal table to the existing 340 analytical
municipality polygons by INE code, calculates area in EPSG:6933, and writes
only project-derived outputs.

Run from the project root:
    python3 code/build_ine_agricultural_employment_maps.py
"""
from __future__ import annotations

from pathlib import Path
import shutil

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import make_valid

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
GUATEMALA = WORKSPACE / "02_projects" / "07_Playdata" / "02_Guatemala"
SOURCES = GUATEMALA / "sources"
INE_MUNICIPIOS = SOURCES / "INE_Rama_Economica_2018" / "censo2018_cuadro_A12_2_municipios.csv"
MUNIS = SOURCES / "JSON_Departamenos_Municipios_LugaresPoblados" / "Mapas-TopoJSON-Guatemala-main" / "munis.json"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
BODY = FIGURES / ".tex_body"
ALTERNATIVES = PROJECT / "output" / "ine_rama_economica_2018_alternatives"
OVERLEAF_ASSETS = PROJECT / "overleaf" / "assets" / "figures"
COUNTRY_FIGURES = GUATEMALA / "figures"
DEPARTMENT_EXPORTS = COUNTRY_FIGURES / "showing_departments"

NATIONAL_A = 1_393_220
NATIONAL_TOTAL = 4_971_427
CAPITAL_CODE = "0101"

# Fixed, interpretable bins, rather than data-driven classes that would change
# with a future revision of the census extract.
SHARE_BINS = [-np.inf, 10, 25, 40, 55, 70, np.inf]
SHARE_LABELS = ["<10%", "10--25%", "25--40%", "40--55%", "55--70%", "$\\geq$70%"]
DENSITY_BINS = [-np.inf, 5, 10, 20, 40, 80, np.inf]
DENSITY_LABELS = ["<5", "5--10", "10--20", "20--40", "40--80", "$\\geq$80"]
COUNT_BINS = [-np.inf, 1_000, 2_500, 5_000, 10_000, 20_000, np.inf]
COUNT_LABELS = ["<1 mil", "1--2,5 mil", "2,5--5 mil", "5--10 mil", "10--20 mil", "$\\geq$20 mil"]
GREEN = ["#ffffe5", "#d9f0a3", "#addd8e", "#78c679", "#31a354", "#006837"]


def load_municipal_data() -> pd.DataFrame:
    """Read and validate the official municipality-level A12.2 extract."""
    data = pd.read_csv(INE_MUNICIPIOS, dtype={"codigo_municipio_4d": str})
    required = {"codigo_municipio_4d", "departamento", "municipio", "total", "A", "no_especificado"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"A12.2 is missing required columns: {sorted(missing)}")
    if len(data) != 340 or data["codigo_municipio_4d"].nunique() != 340:
        raise ValueError("Expected exactly 340 unique municipality codes in A12.2.")
    if data[["total", "A"]].isna().any().any() or (data["total"] <= 0).any() or (data["A"] < 0).any():
        raise ValueError("A12.2 has missing or invalid Total/A values.")
    if int(data["A"].sum()) != NATIONAL_A or int(data["total"].sum()) != NATIONAL_TOTAL:
        raise ValueError("A12.2 national totals do not match the supplied official check totals.")
    data = data.copy()
    data["agricultural_share_pct"] = 100 * data["A"] / data["total"]
    return data


def load_geometry() -> gpd.GeoDataFrame:
    """Return the existing analytical 340-municipality geometry, unmodified."""
    geo = gpd.read_file(MUNIS)
    if geo.crs is None:
        geo = geo.set_crs("EPSG:4326")
    geo = geo.loc[~geo["id"].astype(str).eq("0") & ~geo["Departamento"].str.upper().eq("BELICE")].copy()
    geo.loc[~geo.geometry.is_valid, "geometry"] = geo.loc[~geo.geometry.is_valid, "geometry"].map(make_valid)
    geo["codigo_municipio_4d"] = pd.to_numeric(geo["id"], errors="raise").astype(int).astype(str).str.zfill(4)
    if len(geo) != 340 or geo["codigo_municipio_4d"].nunique() != 340:
        raise ValueError("Expected 340 unique non-lake, non-Belize municipality polygons.")
    return geo[["codigo_municipio_4d", "Departamento", "Municipio", "geometry"]]


def municipality_metrics() -> gpd.GeoDataFrame:
    """Merge source values and calculate area and agricultural density."""
    data = load_municipal_data()
    geo = load_geometry()
    joined = geo.merge(data, on="codigo_municipio_4d", validate="one_to_one", suffixes=("_mapa", "_ine"))
    if len(joined) != 340:
        raise ValueError("The code join did not retain all 340 municipalities.")
    equal_area = joined.to_crs("EPSG:6933")
    equal_area["area_km2"] = equal_area.geometry.area / 1_000_000
    equal_area["agricultural_density_per_km2"] = equal_area["A"] / equal_area["area_km2"]
    if (equal_area["area_km2"] <= 0).any() or not np.isfinite(equal_area["agricultural_density_per_km2"]).all():
        raise ValueError("Municipal areas or agricultural densities are invalid.")
    return equal_area.to_crs("EPSG:4326")


def classify(values: pd.Series, bins: list[float], labels: list[str]) -> pd.Categorical:
    return pd.cut(values, bins=bins, labels=labels, include_lowest=True, right=True, ordered=True)


def capital_point(geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Return Guatemala City municipality's centroid, the sole map marker."""
    capital = geo.loc[geo["codigo_municipio_4d"].eq(CAPITAL_CODE)].to_crs("EPSG:6933").copy()
    if len(capital) != 1:
        raise ValueError("Could not identify Guatemala City municipality (0101).")
    capital["geometry"] = capital.geometry.centroid
    return capital.to_crs(geo.crs)


def capital_handle() -> Line2D:
    return Line2D([0], [0], marker="*", color="white", markerfacecolor="#111111", markeredgecolor="white",
                  markersize=7.6, label="Ciudad de Guatemala")


def draw_map(ax, geo: gpd.GeoDataFrame, value: str, bins: list[float], labels: list[str], panel_title: str,
             header_size: float = 8.2, department_borders: bool = True) -> list:
    """Draw a discrete municipality map matching the report's CHIRPS styling."""
    classified = classify(geo[value], bins, labels)
    plotted = geo.assign(_class=classified)
    for label, colour in zip(labels, GREEN, strict=True):
        selected = plotted.loc[plotted["_class"].eq(label)]
        if not selected.empty:
            selected.plot(ax=ax, color=colour, edgecolor="#111111", linewidth=0.16, zorder=1)
    if department_borders:
        geo.dissolve(by="Departamento").boundary.plot(ax=ax, color="#111111", linewidth=.68, zorder=7)
    capital = capital_point(geo)
    capital.plot(ax=ax, marker="*", color="#111111", edgecolor="white", linewidth=.65, markersize=54, zorder=8)
    ax.text(0, 1.012, panel_title, transform=ax.transAxes, fontsize=header_size, fontweight="bold", va="bottom", linespacing=1.14)
    ax.set_axis_off()
    ax.set_aspect("equal")
    return [Patch(facecolor=colour, edgecolor="#111111", linewidth=.45, label=label) for label, colour in zip(labels, GREEN, strict=True)] + [capital_handle()]

def add_legend(ax, handles: list, title: str, columns: int = 3, font_size: float = 6.2) -> None:
    legend = ax.legend(handles=handles, title=title, loc="lower left", fontsize=font_size, title_fontsize=font_size,
                       frameon=False, ncol=columns, columnspacing=.65, labelspacing=.32, handlelength=1.05)
    legend._legend_box.align = "left"


def save_figure(fig, pdf: Path, png: Path) -> None:
    pdf.parent.mkdir(parents=True, exist_ok=True)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    fig.savefig(png, dpi=350, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def primary_pair(geo: gpd.GeoDataFrame, national_density: float) -> Path:
    """Create the two maps that enter the Overleaf report on one page."""
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 5.85), facecolor="white")
    share_handles = draw_map(
        axes[0], geo, "agricultural_share_pct", SHARE_BINS, SHARE_LABELS,
        "a. Agricultura como proporción de la población ocupada\nCenso 2018 | Nacional: 28,0% (1.393.220 de 4.971.427)",
    )
    density_handles = draw_map(
        axes[1], geo, "agricultural_density_per_km2", DENSITY_BINS, DENSITY_LABELS,
        f"b. Densidad de trabajadores agrícolas\nCenso 2018 | Nacional: {national_density:.1f} trabajadores/km²",
    )
    add_legend(axes[0], share_handles, "Porcentaje de población ocupada")
    add_legend(axes[1], density_handles, "Trabajadores agrícolas por km²")
    fig.tight_layout(rect=(0, .01, 1, .975), w_pad=.25)
    pdf = BODY / "fig06_ine_agriculture_share_density_body.pdf"
    png = FIGURES / "fig06_ine_agriculture_share_density.png"
    save_figure(fig, pdf, png)
    shutil.copy2(pdf, OVERLEAF_ASSETS / pdf.name)
    return pdf


def primary_single(geo: gpd.GeoDataFrame, value: str, bins: list[float], labels: list[str], panel_title: str,
                   legend_title: str, stem: str, *, department_borders: bool = True, destination: Path | None = None) -> Path:
    """Create one legible half-page agricultural map for the report or a country export."""
    fig, ax = plt.subplots(figsize=(6.1, 6.35), facecolor="white")
    handles = draw_map(ax, geo, value, bins, labels, panel_title, header_size=12.0, department_borders=department_borders)
    add_legend(ax, handles, legend_title, columns=4, font_size=10.0)
    fig.subplots_adjust(left=.025, right=.975, top=.91, bottom=.025)
    if destination is not None:
        save_figure(fig, destination, destination.with_suffix('.png'))
        return destination
    pdf = BODY / f"{stem}_body.pdf"
    png = FIGURES / f"{stem}.png"
    save_figure(fig, pdf, png)
    OVERLEAF_ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf, OVERLEAF_ASSETS / pdf.name)
    return pdf


def primary_singles(geo: gpd.GeoDataFrame, national_density: float) -> list[Path]:
    """The report's three distinct readings: share, density, and absolute A."""
    return [
        primary_single(
            geo, "agricultural_share_pct", SHARE_BINS, SHARE_LABELS,
            "Agricultura como proporción de la población ocupada\nCenso 2018 | Nacional: 28,0% (1.393.220 de 4.971.427)",
            "Porcentaje de población ocupada", "fig06a_ine_agriculture_share",
        ),
        primary_single(
            geo, "agricultural_density_per_km2", DENSITY_BINS, DENSITY_LABELS,
            f"Densidad de trabajadores agrícolas\nCenso 2018 | Nacional: {national_density:.1f} trabajadores/km²",
            "Trabajadores agrícolas por km²", "fig06b_ine_agriculture_density",
            destination=ALTERNATIVES / "mapa_densidad_trabajadores_agricolas_km2.pdf",
        ),
        primary_single(
            geo, "A", COUNT_BINS, COUNT_LABELS,
            "Cantidad absoluta de trabajadores agrícolas\nCenso 2018 | Nacional: 1.393.220 personas",
            "Personas", "fig06c_ine_agriculture_count",
        ),
    ]

def three_map_alternative(geo: gpd.GeoDataFrame, national_density: float) -> None:
    """Map alternative: absolute workers, density, and employment share together."""
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.35), facecolor="white")
    specifications = [
        ("A", COUNT_BINS, COUNT_LABELS, "a. Trabajadores agrícolas\nCenso 2018 | Nacional: 1.393.220", "Personas"),
        ("agricultural_density_per_km2", DENSITY_BINS, DENSITY_LABELS, f"b. Densidad agrícola\nNacional: {national_density:.1f} trabajadores/km²", "Trabajadores por km²"),
        ("agricultural_share_pct", SHARE_BINS, SHARE_LABELS, "c. Agricultura en la población ocupada\nNacional: 28,0%", "Porcentaje"),
    ]
    for axis, (value, bins, labels, title, legend_title) in zip(axes, specifications, strict=True):
        handles = draw_map(axis, geo, value, bins, labels, title)
        add_legend(axis, handles, legend_title, columns=2)
    fig.tight_layout(rect=(0, .01, 1, .975), w_pad=.18)
    save_figure(fig, ALTERNATIVES / "01_tres_mapas_agricultura_2018.pdf", ALTERNATIVES / "01_tres_mapas_agricultura_2018.png")


def distribution_alternative(geo: gpd.GeoDataFrame, national_density: float) -> None:
    """Distributional alternative that makes the three map variables comparable."""
    fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.75), facecolor="white")
    series = [
        ("A", "Trabajadores agrícolas", "Personas", None),
        ("agricultural_density_per_km2", "Densidad agrícola", "Trabajadores por km²", national_density),
        ("agricultural_share_pct", "Agricultura en población ocupada", "Porcentaje", 100 * NATIONAL_A / NATIONAL_TOTAL),
    ]
    for ax, (value, title, xlabel, national) in zip(axes, series, strict=True):
        ax.hist(geo[value], bins=20, color="#31a354", edgecolor="white", linewidth=.55)
        if national is not None:
            ax.axvline(national, color="#252525", linewidth=1.05, linestyle="--", label=f"Nacional: {national:.1f}")
            ax.legend(frameon=False, fontsize=7.0, loc="upper right")
        ax.set_title(title, fontsize=9, fontweight="bold", pad=7)
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_ylabel("Municipios", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#d9d9d9", linewidth=.45, zorder=0)
    fig.tight_layout(w_pad=1.8)
    save_figure(fig, ALTERNATIVES / "02_distribuciones_agricultura_2018.pdf", ALTERNATIVES / "02_distribuciones_agricultura_2018.png")


def scatter_alternative(geo: gpd.GeoDataFrame, national_density: float) -> None:
    """Alternative showing why share and density are not interchangeable measures."""
    fig, ax = plt.subplots(figsize=(7.0, 5.2), facecolor="white")
    sizes = 12 + 86 * np.sqrt(geo["A"] / geo["A"].max())
    ax.scatter(geo["agricultural_share_pct"], geo["agricultural_density_per_km2"], s=sizes,
               color="#31a354", edgecolor="white", linewidth=.45, alpha=.82)
    national_share = 100 * NATIONAL_A / NATIONAL_TOTAL
    ax.axvline(national_share, color="#252525", linewidth=1.0, linestyle="--")
    ax.axhline(national_density, color="#252525", linewidth=1.0, linestyle="--")
    ax.set_yscale("log")
    ax.set_xlim(0, 90)
    ax.set_xlabel("Agricultura como porcentaje de la población ocupada", fontsize=9)
    ax.set_ylabel("Trabajadores agrícolas por km² (escala logarítmica)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="both", color="#d9d9d9", linewidth=.45, zorder=0)
    ax.text(.01, .02, "Tamaño del punto: número absoluto de trabajadores agrícolas", transform=ax.transAxes, fontsize=7.1)
    fig.tight_layout()
    save_figure(fig, ALTERNATIVES / "03_participacion_vs_densidad_agricultura_2018.pdf", ALTERNATIVES / "03_participacion_vs_densidad_agricultura_2018.png")


def write_outputs(geo: gpd.GeoDataFrame, national_density: float) -> None:
    """Write a compact derived data file and documentation for the alternatives."""
    DERIVED.mkdir(parents=True, exist_ok=True)
    ALTERNATIVES.mkdir(parents=True, exist_ok=True)
    columns = ["codigo_municipio_4d", "codigo_departamento", "departamento", "municipio", "total", "A", "no_especificado",
               "area_km2", "agricultural_share_pct", "agricultural_density_per_km2"]
    geo[columns].sort_values("codigo_municipio_4d").to_csv(DERIVED / "ine_rama_economica_2018_municipality_metrics.csv", index=False)
    (ALTERNATIVES / "README.md").write_text(
        "# Alternativas cartográficas — rama económica agrícola, Censo 2018\n\n"
        "Estos archivos son alternativas reproducibles a la pareja de mapas incluida en Overleaf. "
        "Se generan con `python3 code/build_ine_agricultural_employment_maps.py`.\n\n"
        "- `01_tres_mapas_agricultura_2018`: cantidad absoluta, densidad y participación.\n"
        "- `02_distribuciones_agricultura_2018`: histogramas municipales de las tres medidas.\n"
        "- `03_participacion_vs_densidad_agricultura_2018`: por qué participación y densidad no son equivalentes; tamaño del punto es A.\n\n"
        "## Definiciones\n\n"
        "La fuente es el Censo Nacional 2018, cuadro A12.2, población ocupada por rama de actividad económica. "
        "`A` es agricultura, ganadería, silvicultura y pesca. `Total` incluye la rama no especificada, por lo que "
        "`participación = 100 × A / Total`. `densidad = A / km²`, donde km² es el área municipal calculada en EPSG:6933.\n\n"
        f"Validación nacional: {NATIONAL_A:,} personas en A de {NATIONAL_TOTAL:,} en Total (28,0%); "
        f"densidad sobre los {geo['area_km2'].sum():,.1f} km² de los 340 polígonos analíticos: {national_density:.1f} trabajadores/km².\n"
    )


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})
    geo = municipality_metrics()
    national_density = NATIONAL_A / geo.to_crs("EPSG:6933").geometry.area.sum() * 1_000_000
    if not np.isclose(national_density, geo["A"].sum() / geo["area_km2"].sum()):
        raise AssertionError("National density check failed.")
    write_outputs(geo, national_density)
    primary = primary_singles(geo, national_density)
    three_map_alternative(geo, national_density)
    distribution_alternative(geo, national_density)
    scatter_alternative(geo, national_density)
    DEPARTMENT_EXPORTS.mkdir(parents=True, exist_ok=True)
    specs = [
        ("agricultural_share_pct", SHARE_BINS, SHARE_LABELS, "Agricultura como proporción de la población ocupada\nCenso 2018 | Nacional: 28,0%", "Porcentaje de población ocupada", "figura_06_participacion_agricola_fronteras_departamentales"),
        ("agricultural_density_per_km2", DENSITY_BINS, DENSITY_LABELS, f"Densidad de trabajadores agrícolas\nCenso 2018 | Nacional: {national_density:.1f} trabajadores/km²", "Trabajadores agrícolas por km²", "alternativa_densidad_por_km2_fronteras_departamentales"),
        ("A", COUNT_BINS, COUNT_LABELS, "Cantidad absoluta de trabajadores agrícolas\nCenso 2018 | Nacional: 1.393.220 personas", "Personas", "apendice_cantidad_trabajadores_fronteras_departamentales"),
    ]
    for value,bins,labels,title,legend,stem in specs:
        primary_single(geo,value,bins,labels,title,legend,stem,department_borders=True,destination=DEPARTMENT_EXPORTS/f"{stem}.pdf")
    (DEPARTMENT_EXPORTS / "README.md").write_text(
        "# Mapas con fronteras departamentales\n\n"
        "Versiones derivadas de los mapas municipales del informe Dalton. Las líneas delgadas identifican municipios; "
        "las líneas negras gruesas son fronteras departamentales. Los activos CHIRPS se generan con `build_report_maps.py`; "
        "los activos de empleo agrícola se generan con este script; las capas MAGA crudas se generan con `build_maga_land_use_maps.py`.\n",
        encoding="utf-8",
    )
    print("Built report map bodies and agricultural department-border variants.")
    print(f"National check: A={NATIONAL_A:,}; Total={NATIONAL_TOTAL:,}; density={national_density:.2f}/km².")


if __name__ == "__main__":
    main()
