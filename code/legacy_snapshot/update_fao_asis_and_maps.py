#!/usr/bin/env python3
"""Replace provisional department-level FAO ASIS outputs with municipal raster statistics.

This companion is called after build_analysis.py. It reads all raw inputs in place,
uses the FAO raster as the primary ASIS source, and never copies source files.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from rasterio.mask import mask as rio_mask
from shapely.geometry import mapping


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
GUATEMALA = WORKSPACE / "02_projects" / "07_Playdata" / "02_Guatemala"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
TABLES = PROJECT / "tables"
DOCS = PROJECT / "documentation"
RASTER = GUATEMALA / "sources" / "FAO_ASI" / "GT_FAO_ASIS_2026_AugD1_GS1_Cropland.tif"
CSV = GUATEMALA / "sources" / "FAO_ASI" / "ASI_Dekad_Season1_data.csv"

spec = importlib.util.spec_from_file_location("dalton_base", PROJECT / "code" / "build_analysis.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

SITE_ORDER = [("Olopa", "Chiquimula"), ("Chahal", "Alta Verapaz"), ("Patzité", "Quiché")]
SPECIAL_CODES = {251: "off season", 252: "no data", 253: "no season", 254: "no cropland", 255: "water"}
VALID_MIN, VALID_MAX = 0.0, 100.0


def write_csv(data: pd.DataFrame, path: Path) -> None:
    data.to_csv(path, index=False, encoding="utf-8")


def plot_sites(axis, points):
    points.plot(ax=axis, color="#111827", marker="o", markersize=20, zorder=8)
    for point in points.itertuples():
        axis.annotate(point.municipality, (point.geometry.x, point.geometry.y), xytext=(3, 3),
                      textcoords="offset points", fontsize=6.5, zorder=9,
                      bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=0.25))


def no_axes(axis):
    axis.set_axis_off()
    axis.set_aspect("equal")


def base_map(axis, geo):
    geo.plot(ax=axis, color="#efefef", edgecolor="#ffffff", linewidth=0.16, zorder=1)


def combined_map(axis, geo, sites, show_colourbar=False, figure=None):
    """SESAN outline + CHIRPS anomaly fill + municipal FAO ASIS hatching."""
    base_map(axis, geo)
    cmap = LinearSegmentedColormap.from_list(
        "dryness", ["#7f1d1d", "#dc2626", "#fb923c", "#fed7aa", "#e5e7eb", "#bfdbfe", "#2563eb"]
    )
    percentile = geo["rainfall_historical_percentile"].clip(0, 100)
    geo.assign(_plot_percentile=percentile).plot(ax=axis, column="_plot_percentile", cmap=cmap, vmin=0, vmax=100,
                                            edgecolor="#ffffff", linewidth=0.15, zorder=2)
    # At least 30% affected is a transparent, directly interpretable affected-cropland threshold.
    geo.loc[geo["asis_value"].ge(30)].plot(ax=axis, facecolor="none", edgecolor="#3b0764", hatch="////",
                                            linewidth=0.48, zorder=5)
    geo.loc[geo["asis_value"].isna()].plot(ax=axis, facecolor="none", edgecolor="#475569", hatch="....", linewidth=0.42, zorder=5)
    geo.loc[geo["corredor_seco_160"].eq(1)].boundary.plot(ax=axis, color="#111827", linewidth=0.52, zorder=6)
    plot_sites(axis, sites)
    axis.set_title("B. SESAN corridor, CHIRPS standardized anomaly, and municipal FAO ASIS", fontsize=10, fontweight="bold")
    no_axes(axis)
    if show_colourbar and figure is not None:
        sm = plt.cm.ScalarMappable(norm=Normalize(0, 100), cmap=cmap)
        cbar = figure.colorbar(sm, ax=axis, orientation="horizontal", fraction=0.038, pad=0.01, aspect=34)
        cbar.set_label("CHIRPS May--August 2026 historical rainfall percentile (0 = driest; dark red = drier)", fontsize=7)
    return [
        Line2D([0], [0], color="#111827", lw=1.1, label="SESAN Corredor Seco Ampliado (160)"),
        Patch(facecolor="white", edgecolor="#475569", hatch="....", label="No valid FAO ASIS coverage"),
        Patch(facecolor="none", edgecolor="#3b0764", hatch="////", label="FAO ASIS ≥30% of valid cropland area affected"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#111827", markersize=5, label="Field site"),
    ]


def corridor_map(axis, geo, sites):
    base_map(axis, geo)
    geo.loc[geo["corredor_seco_160"].eq(1)].plot(ax=axis, color="#d9a441", edgecolor="#ffffff", linewidth=0.15, zorder=2)
    geo.loc[geo["corredor_seco_160"].eq(1)].boundary.plot(ax=axis, color="#6b4f12", linewidth=0.42, zorder=3)
    plot_sites(axis, sites)
    axis.set_title("C. SESAN Corredor Seco Ampliado only", fontsize=9, fontweight="bold")
    no_axes(axis)
    return [Patch(facecolor="#d9a441", edgecolor="#6b4f12", label="SESAN 160 municipalities"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor="#111827", markersize=5, label="Field site")]


def overlap_map(axis, geo, sites):
    """Five mutually exclusive states separate overlap, non-overlap, and unavailable ASIS."""
    geo = geo.copy()
    dry = geo["rainfall_historical_percentile"].le(10)
    stress = geo["asis_value"].ge(30)
    available = geo["asis_value"].notna()
    geo["overlap"] = np.select(
        [~available, available & dry & stress, available & dry & ~stress, available & ~dry & stress],
        ["No valid FAO ASIS coverage", "Both: CHIRPS P≤10 and ASI≥30", "CHIRPS P≤10 only", "ASI≥30 only"],
        default="Neither threshold",
    )
    palette = {
        "No valid FAO ASIS coverage": "#94a3b8",
        "Neither threshold": "#e5e7eb",
        "CHIRPS P≤10 only": "#dc2626",
        "ASI≥30 only": "#2563eb",
        "Both: CHIRPS P≤10 and ASI≥30": "#5b2167",
    }
    for label, colour in palette.items():
        geo.loc[geo["overlap"].eq(label)].plot(ax=axis, color=colour, edgecolor="#ffffff", linewidth=0.15, zorder=2)
    plot_sites(axis, sites)
    axis.set_title("D. Meteorological drought / agricultural-stress overlap", fontsize=9, fontweight="bold")
    no_axes(axis)
    return [Patch(facecolor=colour, edgecolor="white", label=label) for label, colour in palette.items()]


def make_maps(geo, sites):
    # Requested combined A layout: B largest above C and D on the shared lower row.
    fig = plt.figure(figsize=(10.8, 12.4))
    grid = fig.add_gridspec(2, 2, height_ratios=[1.72, 1], hspace=0.10, wspace=0.04)
    ax_b = fig.add_subplot(grid[0, :])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])
    legend_b = combined_map(ax_b, geo, sites, show_colourbar=True, figure=fig)
    legend_c = corridor_map(ax_c, geo, sites)
    legend_d = overlap_map(ax_d, geo, sites)
    ax_b.legend(handles=legend_b, loc="lower left", fontsize=7, frameon=True, framealpha=0.92)
    ax_c.legend(handles=legend_c, loc="lower left", fontsize=6.5, frameon=True, framealpha=0.92)
    ax_d.legend(handles=legend_d, loc="lower left", fontsize=6.3, frameon=True, framealpha=0.92)
    fig.suptitle("A. Guatemala drought geography, 2026", fontsize=13, y=0.986, fontweight="bold")
    fig.text(0.01, 0.01,
             "Data: existing SESAN 160 municipality indicator; CHIRPS v3 final municipality rainfall, 1 May--31 August 2026; FAO ASIS raster, Cropland GS1, 2026 August Dekad 1. "
             "B maps the standardized CHIRPS anomaly as a historical percentile: 0 is the driest possible value and is dark red. D uses an unusually-dry threshold (historical percentile ≤10; a 0 percentile is worse than every 1981--2025 observation) and ASI ≥30%. "
             "ASI is a raster-derived municipality statistic: percentage of valid in-season cropland area affected, not yield loss. No causal relationship is implied.",
             fontsize=7.1, ha="left", va="bottom", wrap=True)
    fig.savefig(FIGURES / "fig01_corridor_vs_rainfall_2026.png", dpi=230, bbox_inches="tight")
    plt.close(fig)

    # Individual B/C/D maps are also provided for report layout flexibility.
    for filename, function, kwargs in [
        ("fig01b_combined_drought_layers.png", combined_map, {"show_colourbar": True}),
        ("fig01c_sesan_corridor.png", corridor_map, {}),
        ("fig01d_chirps_asis_overlap.png", overlap_map, {}),
    ]:
        fig, axis = plt.subplots(figsize=(7.2, 7.5))
        if function is combined_map:
            legend = function(axis, geo, sites, figure=fig, **kwargs)
        else:
            legend = function(axis, geo, sites)
        axis.legend(handles=legend, loc="lower left", fontsize=7, frameon=True, framealpha=0.92)
        fig.tight_layout()
        fig.savefig(FIGURES / filename, dpi=220, bbox_inches="tight")
        plt.close(fig)


def make_sd_graph(sites):
    """Alternative CHIRPS display: historical mean ± sample SD, median tick, and 2026 point."""
    ordered = sites.set_index("municipality").loc[[name for name, _ in SITE_ORDER]].reset_index()
    fig, axis = plt.subplots(figsize=(8.4, 4.6))
    y = np.arange(len(ordered))
    for i, row in enumerate(ordered.itertuples()):
        axis.errorbar(row.historical_mean_may_aug_mm, i, xerr=row.historical_sd_may_aug_mm,
                      fmt="o", color="#6b7280", ecolor="#9ca3af", elinewidth=3, capsize=5,
                      markersize=5, zorder=2)
        axis.scatter(row.historical_median_may_aug_mm, i, marker="|", s=260, color="#111827", linewidths=2, zorder=4)
        colour = "#b91c1c" if row.rainfall_historical_percentile <= 10 else "#2563eb"
        axis.scatter(row.rain_2026_may_aug_mm, i, s=72, color=colour, edgecolor="white", linewidth=0.7, zorder=5)
        axis.annotate(f"P{row.rainfall_historical_percentile:.0f}; {row.rainfall_anomaly_pct_vs_historical_median:+.1f}%",
                      (row.rain_2026_may_aug_mm, i), xytext=(7, 7), textcoords="offset points", fontsize=8)
    axis.set_yticks(y, [f"{row.municipality}, {row.department}" for row in ordered.itertuples()])
    axis.invert_yaxis()
    axis.set_xlabel("May--August cumulative rainfall (mm)")
    axis.set_title("CHIRPS rainfall: 2026 compared with historical distribution", fontsize=11)
    axis.grid(axis="x", alpha=0.22)
    axis.legend(handles=[
        Line2D([0], [0], marker="o", color="#6b7280", lw=2, markersize=5, label="1981--2025 mean ± 1 sample SD"),
        Line2D([0], [0], marker="|", color="#111827", lw=0, markersize=12, label="1981--2025 median"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#b91c1c", markersize=7, label="2026 final (red when P≤10)"),
    ], loc="lower right", fontsize=7.4, frameon=True)
    fig.text(0.01, 0.01,
             "Data: CHIRPS v3 municipality area-weighted cumulative precipitation. Exact period: 1 May--31 August, historical 1981--2025; 2026 is FINAL. "
             "Whiskers are descriptive sample standard deviations across the 45 historical annual totals, not confidence intervals; the vertical tick is the historical median.",
             fontsize=7.2, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(FIGURES / "fig02b_three_site_rainfall_sd.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_scatter(chirps, asis, sites):
    scatter = chirps.merge(asis[["municipality_id", "asis_value"]], on="municipality_id", validate="one_to_one")
    highlight = sites[["municipality_id", "municipality", "department"]].merge(
        scatter[["municipality_id", "rainfall_historical_percentile", "asis_value"]], on="municipality_id", validate="one_to_one"
    )
    fig, axis = plt.subplots(figsize=(8.1, 5.2))
    axis.scatter(scatter["rainfall_historical_percentile"], scatter["asis_value"], s=11, alpha=0.20, color="#64748b", linewidths=0)
    colours = {"Olopa": "#b91c1c", "Chahal": "#2563eb", "Patzité": "#4d7c0f"}
    for row in highlight.itertuples():
        axis.scatter(row.rainfall_historical_percentile, row.asis_value, s=58, color=colours[row.municipality], edgecolor="white", linewidth=0.7, zorder=3)
        axis.annotate(row.municipality, (row.rainfall_historical_percentile, row.asis_value), xytext=(5, 4), textcoords="offset points", fontsize=9)
    axis.set_xlabel("CHIRPS 2026 May--August historical rainfall percentile (lower = drier)")
    axis.set_ylabel("Raster-derived FAO ASIS (% valid in-season cropland area affected)")
    axis.set_title("Meteorological shock and agricultural stress: municipality descriptive comparison", fontsize=11)
    axis.grid(alpha=0.2)
    fig.text(0.01, 0.01,
             "Data: CHIRPS v3 final municipality percentile, 1 May--31 August 2026 vs 1981--2025; FAO ASIS Cropland GS1 raster, 2026 August Dekad 1, municipality area-weighted statistic. "
             "Units: percentile and percent. The scatter is descriptive only; no fitted or causal relationship is shown.",
             fontsize=7.2, ha="left", va="bottom", wrap=True)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(FIGURES / "fig03_rainfall_vs_asis.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_raster_statistics():
    crosswalk, geometry_note = base.make_crosswalk()
    outline = crosswalk.geometry.union_all()
    with rasterio.open(RASTER) as source:
        raw, transform = rio_mask(source, [mapping(outline)], crop=True, filled=False)
        array = raw[0].filled(np.nan).astype(float)
        profile = source.profile.copy()
        source_metadata = {
            "driver": source.driver,
            "crs": str(source.crs),
            "width": source.width,
            "height": source.height,
            "resolution_degrees": source.res,
            "bounds": tuple(source.bounds),
            "dtype": source.dtypes[0],
            "nodata": source.nodata,
            "tags": source.tags(),
            "band_tags": source.tags(1),
        }
    profile.update(driver="GTiff", height=array.shape[0], width=array.shape[1], transform=transform,
                   count=1, dtype="float32", nodata=-9999.0, compress="lzw")
    with rasterio.open(DERIVED / "fao_asis_2026_augd1_gs1_cropland_guatemala_clip.tif", "w", **profile) as out:
        out.write(np.where(np.isfinite(array), array, -9999.0).astype("float32"), 1)

    weights = {
        int(row.municipality_id): base.municipal_pixel_weights(transform, array.shape[1], array.shape[0], row.geometry)
        for row in crosswalk.itertuples()
    }
    records = []
    for row in crosswalk.itertuples():
        rows, cols, areas = weights[int(row.municipality_id)]
        values = array[rows, cols]
        valid = np.isfinite(values) & (values >= VALID_MIN) & (values <= VALID_MAX)
        record = {
            "municipality_id": int(row.municipality_id), "department": row.department, "municipality": row.municipality,
            "corredor_seco_160": int(row.corredor_seco_160),
            "asis_value": float(np.average(values[valid], weights=areas[valid])) if valid.any() else np.nan,
            "asis_period": "2026-08-01 (August Dekad 1; Growing Season 1; Cropland)",
            "asis_unit": "percent of valid in-season cropland area affected",
            "asis_interpretation": "Municipality area-weighted mean of valid FAO ASIS raster values. ASI denotes cropland affected by drought-related vegetation stress; it is not yield loss.",
            "asis_geographic_aggregation": "municipality (raster-derived; fractional-pixel area weighting)",
            "asis_source_raster": RASTER.name,
            "raster_valid_asi_area_share_in_municipality": float(areas[valid].sum() / areas.sum()),
            "valid_asi_pixel_count": int(valid.sum()),
        }
        for code, label in SPECIAL_CODES.items():
            record[f"raster_code_{code}_{label.replace(' ', '_')}_area_share"] = float(areas[values == code].sum() / areas.sum())
        records.append(record)
    municipal = pd.DataFrame(records)

    # Validate the raw scale and our geometry aggregation against the same-date department CSV.
    departments = crosswalk.dissolve(by="department").reset_index()
    dept_records = []
    for row in departments.itertuples():
        rows, cols, areas = base.municipal_pixel_weights(transform, array.shape[1], array.shape[0], row.geometry)
        values = array[rows, cols]
        valid = np.isfinite(values) & (values >= VALID_MIN) & (values <= VALID_MAX)
        dept_records.append({
            "department": row.department,
            "raster_asis_value_direct": float(np.average(values[valid], weights=areas[valid])) if valid.any() else np.nan,
            "raster_valid_asi_area_share": float(areas[valid].sum() / areas.sum()),
        })
    validation = pd.DataFrame(dept_records)
    csv = pd.read_csv(CSV, encoding="latin1")
    csv["Date"] = pd.to_datetime(csv["Date"])
    csv["Data"] = pd.to_numeric(csv["Data"], errors="coerce")
    csv = csv.loc[csv["Date"].eq(pd.Timestamp("2026-08-01"))].copy()
    csv["department_key"] = csv["Province"].map(base.normalize_text)
    validation["department_key"] = validation["department"].map(base.normalize_text)
    validation = validation.merge(csv[["department_key", "Province", "Data"]], on="department_key", how="left", validate="one_to_one")
    validation = validation.rename(columns={"Province": "csv_department", "Data": "csv_asis_value_same_date"})
    validation["difference_raster_minus_csv_pp"] = validation["raster_asis_value_direct"] - validation["csv_asis_value_same_date"]
    validation["absolute_difference_pp"] = validation["difference_raster_minus_csv_pp"].abs()
    direct_mae = validation["absolute_difference_pp"].mean()
    scaled_mae = (validation["raster_asis_value_direct"] * 100 - validation["csv_asis_value_same_date"]).abs().mean()
    scale = 1.0 if direct_mae <= scaled_mae else 100.0
    if scale != 1.0:
        municipal["asis_value"] *= scale
        validation["raster_asis_value_direct"] *= scale
        validation["difference_raster_minus_csv_pp"] = validation["raster_asis_value_direct"] - validation["csv_asis_value_same_date"]
        validation["absolute_difference_pp"] = validation["difference_raster_minus_csv_pp"].abs()
    municipal["raster_value_multiplier_to_percent"] = scale
    validation["raster_value_multiplier_to_percent"] = scale
    validation["comparison_note"] = "CSV is a same-date department-level validation comparator only; differences can reflect FAO versus supplied boundary geography and rasterization."
    write_csv(municipal, DERIVED / "fao_asis_2026_municipality.csv")
    write_csv(validation, DERIVED / "fao_asis_raster_department_validation.csv")
    return crosswalk, municipal, validation, source_metadata, geometry_note


def update_site_table(chirps, asis):
    sites = pd.DataFrame(SITE_ORDER, columns=["municipality", "department"])
    joined = chirps.merge(asis, on=["municipality_id", "department", "municipality", "corredor_seco_160"], validate="one_to_one")
    sites = sites.merge(joined, on=["municipality", "department"], validate="one_to_one")
    keep = [
        "municipality_id", "department", "municipality", "corredor_seco_160", "historical_mean_may_aug_mm", "historical_median_may_aug_mm", "historical_sd_may_aug_mm",
        "rain_2026_may_aug_mm", "rainfall_anomaly_pct_vs_historical_median", "rainfall_historical_percentile",
        "asis_value", "asis_period", "asis_unit", "asis_geographic_aggregation", "asis_interpretation",
        "raster_valid_asi_area_share_in_municipality", "valid_asi_pixel_count",
    ]
    output = sites[keep]
    write_csv(output, TABLES / "table_three_sites_drought.csv")
    return output


def update_docs(metadata, validation, geometry_note, sites):
    raw_values = []
    with rasterio.open(RASTER) as src:
        all_values = src.read(1)
        unique, counts = np.unique(all_values, return_counts=True)
        raw_values = list(zip(unique.tolist(), counts.tolist()))
        write_csv(pd.DataFrame(raw_values, columns=["raster_value", "cell_count"]), DERIVED / "fao_asis_2026_raster_value_counts.csv")
    municipal_for_notes = pd.read_csv(DERIVED / "fao_asis_2026_municipality.csv")
    unavailable_names = ", ".join(municipal_for_notes.loc[municipal_for_notes["asis_value"].isna(), "municipality"].tolist())
    valid_values = [value for value, _ in raw_values if VALID_MIN <= value <= VALID_MAX]
    special_text = "; ".join(f"{code} = {label}" for code, label in SPECIAL_CODES.items())
    correlation = validation["raster_asis_value_direct"].corr(validation["csv_asis_value_same_date"])
    mae = validation["absolute_difference_pp"].mean()
    max_abs = validation["absolute_difference_pp"].max()
    validation_lines = "\n".join(
        f"| {row.department} | {row.raster_asis_value_direct:.3f} | {row.csv_asis_value_same_date:.3f} | {row.difference_raster_minus_csv_pp:+.3f} |"
        for row in validation.sort_values("department").itertuples()
    )
    site_lines = "\n".join(
        f"- **{row.municipality}, {row.department}:** raster ASI {row.asis_value:.3f}%; valid in-season ASI coverage {100 * row.raster_valid_asi_area_share_in_municipality:.1f}% of municipal polygon; {row.valid_asi_pixel_count} intersecting valid cells."
        for row in sites.itertuples()
    )
    notes = f"""# FAO ASIS raster notes

## Raster verification

The new source is `{RASTER.name}`. It is a single-band GeoTIFF in **EPSG:4326**, 500 × 500 cells, nominal resolution **0.0088°** (about 1 km), with bounds `({metadata['bounds'][0]}, {metadata['bounds'][1]})` to `({metadata['bounds'][2]}, {metadata['bounds'][3]})`. Those bounds cover Guatemala, and every one of the 340 analytical Guatemala municipality polygons intersects the clipped raster. The filename identifies Guatemala, Cropland, Growing Season 1, 2026 August Dekad 1; the GeoTIFF has no temporal/season fields in its embedded tags, so these labels are confirmed from the supplied filename rather than internal metadata.

The source reports **no GDAL nodata value**. It contains {len(raw_values)} unique numeric values; exact value--cell counts are saved in `derived/fao_asis_2026_raster_value_counts.csv`. Valid ASI values are {min(valid_values):.1f} to {max(valid_values):.1f}, including 0 (valid: no affected cropland in the represented unit). The special codes are: {special_text}. These codes are excluded from municipal means. There are no 255 values in this raster. FAO documentation states that ASI is based on the share of arable-area pixels whose seasonally weighted mean VHI is below 35; it is a drought-related vegetation-stress measure, **not yield loss**. The raster's direct 0--100 values are used as percentages: the same-date department CSV validation favours multiplier {validation['raster_value_multiplier_to_percent'].iloc[0]:.0f}, rather than a further ×100 scaling.

Five municipalities have **no valid in-season ASIS cells** and thus a missing, not zero, `asis_value`: {unavailable_names}. They are visibly marked as ASIS unavailable in the overlap map.
The Guatemala-clipped derived raster is `derived/fao_asis_2026_augd1_gs1_cropland_guatemala_clip.tif`; source pixels are otherwise unchanged.

## Municipal statistic

`asis_value` is the fractional-pixel, equal-area weighted mean of raster values 0--100 within each municipality, excluding special codes 251--255. The result is a municipality-level spatial statistic from the supplied ASIS raster. `raster_valid_asi_area_share_in_municipality` is the share of the municipality occupied by valid, in-season ASI raster cells; it is reported to make sparse crop/season coverage visible and is not itself a cropland share estimate.

{site_lines}

## Department CSV validation only

The existing CSV is retained unchanged as an independent **same-date (2026-08-01) department-level comparator**; it is not used to fill or replace municipality values. Raster-derived department means versus CSV values have Pearson correlation {correlation:.3f}, mean absolute difference {mae:.3f} percentage points, and maximum absolute difference {max_abs:.3f} points.

| Department | Raster-derived ASI | CSV ASI | Raster − CSV (pp) |
| --- | ---: | ---: | ---: |
{validation_lines}

## Geography discrepancy

{geometry_note} The FAO raster encodes values spatially but does not supply an administrative-boundary layer or municipality identifiers. Therefore this project cannot verify one-to-one equivalence between FAO's internal administrative geography and the supplied TopoJSON/INE-style municipality geography. The municipal values above are overlay statistics using the existing 340-polygon analytical boundary; the department comparison provides a diagnostic, not a boundary equivalence test.
"""
    (DOCS / "fao_asis_notes.md").write_text(notes, encoding="utf-8")

    methods_path = DOCS / "methods_notes.md"
    methods = methods_path.read_text(encoding="utf-8")
    start = methods.find("## FAO ASIS")
    end = methods.find("## MAGA maize price")
    replacement = """## FAO ASIS

The primary ASIS source is the supplied near-real-time Guatemala Cropland GS1 raster for 2026 August Dekad 1. Municipality values are fractional-pixel equal-area means of valid raster values; special codes 251--255 are excluded. The older FAO department CSV is retained only as a same-date validation comparison and is not used to assign municipality values. See [fao_asis_notes.md](fao_asis_notes.md) for metadata, encoding, coverage and geographic-boundary limitations.

"""
    if start != -1 and end != -1:
        methods = methods[:start] + replacement + methods[end:]
    (DOCS / "methods_notes.md").write_text(methods, encoding="utf-8")

    brief = f"""# Results brief

## Read this first: CHIRPS and FAO ASIS

CHIRPS v3 identifies unusual **meteorological rainfall** over 1 May--31 August 2026 relative to each municipality's 1981--2025 distribution; lower percentiles are drier and 2026 is final. FAO ASIS is a distinct, raster-derived municipality measure of the percentage of valid in-season cropland area affected by drought-related vegetation stress. It is not yield or crop loss.

{site_lines}

The department CSV is retained only to validate raster scaling and broad geographic consistency; its details and the remaining FAO-boundary limitation are in [fao_asis_notes.md](fao_asis_notes.md).

## Budget exercise

The maize cash changes in `table_budget_scenarios.csv` remain sensitivity scenarios, not causal effects and not crop-loss estimates. No program transfer amount is in the supplied documentation, so no transfer-absorption percentage is calculated.
"""
    (DOCS / "results_brief.md").write_text(brief, encoding="utf-8")

    manifest_path = DOCS / "data_manifest.csv"
    manifest = pd.read_csv(manifest_path)
    manifest = manifest.loc[manifest["data_id"].ne("fao_asis")].copy()
    new_row = pd.DataFrame([{
        "data_id": "fao_asis_raster", "path": str(RASTER.relative_to(WORKSPACE)), "status": "source, read-only",
        "unit_observation": "raster cell", "coverage": "Guatemala extent; 2026 August Dekad 1; Cropland GS1",
        "finest_granularity": "0.0088-degree raster (about 1 km)", "notes": "Primary ASIS source; no copy made."
    }, {
        "data_id": "fao_asis_department_csv_validation", "path": str(CSV.relative_to(WORKSPACE)), "status": "source, read-only validation comparator",
        "unit_observation": "department x dekad", "coverage": "2026-08-01 comparison", "finest_granularity": "department",
        "notes": "Retained for validation only; not used to replace municipality ASI values."
    }])
    manifest = pd.concat([manifest, new_row], ignore_index=True)
    write_csv(manifest, manifest_path)


def main():
    # The user requested deletion of the preceding derived municipality CSV; it is removed before the raster-derived replacement is written.
    old = DERIVED / "fao_asis_2026_municipality.csv"
    if old.exists():
        old.unlink()
    crosswalk, asis, validation, metadata, geometry_note = build_raster_statistics()
    chirps = pd.read_csv(DERIVED / "chirps_2026_municipality.csv")
    sites = update_site_table(chirps, asis)
    geometry = crosswalk.merge(chirps[["municipality_id", "rainfall_anomaly_pct_vs_historical_median", "rainfall_historical_percentile"]], on="municipality_id", validate="one_to_one")
    geometry = geometry.merge(asis[["municipality_id", "asis_value"]], on="municipality_id", validate="one_to_one")
    points = crosswalk.to_crs("EPSG:6933").copy()
    points["geometry"] = points.centroid
    points = points.to_crs("EPSG:4326")
    site_points = points.merge(pd.DataFrame(SITE_ORDER, columns=["municipality", "department"]), on=["municipality", "department"])
    make_maps(geometry, site_points)
    make_sd_graph(sites)
    make_scatter(chirps, asis, sites)
    update_docs(metadata, validation, geometry_note, sites)
    print("Updated FAO ASIS outputs from raster.")
    print("Raster validation: direct-scale MAE =", round(validation["absolute_difference_pp"].mean(), 3), "pp; correlation =", round(validation["raster_asis_value_direct"].corr(validation["csv_asis_value_same_date"]), 3))
    print(sites[["municipality", "asis_value", "raster_valid_asi_area_share_in_municipality"]].to_string(index=False))


if __name__ == "__main__":
    main()
