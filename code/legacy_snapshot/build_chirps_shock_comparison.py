#!/usr/bin/env python3
"""Build reproducible, non-causal CHIRPS shock-comparison inputs and map body.

The contemporaneous measure evaluates each historical shock only against
rainfall observed before it: 2015 against 1981--2014, 2019 against 1981--2018,
and final 2026 against 1981--2025.  The existing fixed-reference map is
deliberately retained separately, since it answers a different question.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
import rasterio

from prepare_appendix_data import annual_means, load_municipal_geometry, pixel_weights
from prepare_chirps_main_outputs import national_history


PROJECT = Path(__file__).resolve().parents[1]
DERIVED = PROJECT / "derived"
TABLES = PROJECT / "figures" / "Appendix" / "tables"
BODY = PROJECT / "figures" / ".tex_body"
YEARS = [2015, 2019, 2026]
GROUPS = ["0", "1-10", "11-25", "26-50", "51-75", "76-100"]
COLOURS = {
    "0": "#67000d", "1-10": "#cb181d", "11-25": "#fb6a4a",
    "26-50": "#fdd0a2", "51-75": "#9ecae1", "76-100": "#3182bd",
}
LABELS = {
    "0": "0: lower than every earlier year", "1-10": "1--10: exceptionally dry",
    "11-25": "11--25: dry", "26-50": "26--50: below median",
    "51-75": "51--75: above median", "76-100": "76--100: wet relative to history",
}


def percentile_group(value: float) -> str:
    if value == 0:
        return "0"
    if value <= 10:
        return "1-10"
    if value <= 25:
        return "11-25"
    if value <= 50:
        return "26-50"
    if value <= 75:
        return "51-75"
    return "76-100"


def calculate() -> tuple[pd.DataFrame, pd.DataFrame]:
    geo = load_municipal_geometry()
    annual, years = annual_means(geo)
    wide = annual.pivot(index="municipality_id", columns="year", values="rain_may_aug_mm")
    current = pd.read_csv(DERIVED / "chirps_2026_municipality.csv").set_index("municipality_id")
    rows: list[pd.DataFrame] = []
    for year in YEARS:
        prior = wide.loc[:, list(range(1981, year))]
        rain = current["rain_2026_may_aug_mm"] if year == 2026 else wide[year]
        result = current[["department", "municipality"]].copy()
        result["year"] = year
        result["rain_may_aug_mm"] = rain
        result["reference_start"] = 1981
        result["reference_end"] = year - 1
        result["reference_n"] = prior.shape[1]
        result["reference_mean_mm"] = prior.mean(axis=1)
        result["reference_median_mm"] = prior.median(axis=1)
        result["reference_sd_mm"] = prior.std(axis=1, ddof=1)
        result["rainfall_percentile_at_time"] = 100 * (prior.le(rain, axis=0)).mean(axis=1)
        result["rainfall_z_score_at_time"] = (rain - result["reference_mean_mm"]) / result["reference_sd_mm"]
        result["percentile_group_at_time"] = result["rainfall_percentile_at_time"].map(percentile_group)
        result["data_status"] = "FINAL"
        rows.append(result.reset_index())
    municipal = pd.concat(rows, ignore_index=True).sort_values(["year", "municipality_id"])

    national, rain_2026 = national_history(geo.geometry.union_all())
    national_rows: list[dict[str, object]] = []
    for year in YEARS:
        prior = national.loc[national.year.lt(year), "national_rain_may_aug_mm"].to_numpy(float)
        rain = rain_2026 if year == 2026 else float(national.loc[national.year.eq(year), "national_rain_may_aug_mm"].iloc[0])
        subsample = municipal.loc[municipal.year.eq(year)]
        national_rows.append({
            "year": year, "data_status": "FINAL",
            "reference_start": 1981, "reference_end": year - 1, "reference_n": len(prior),
            "national_rain_may_aug_mm": rain,
            "national_reference_mean_mm": prior.mean(),
            "national_reference_sd_mm": prior.std(ddof=1),
            "national_rainfall_percentile_at_time": 100 * np.mean(prior <= rain),
            "national_rainfall_z_score_at_time": (rain - prior.mean()) / prior.std(ddof=1),
            "municipal_median_z_score_at_time": subsample.rainfall_z_score_at_time.median(),
            "municipal_share_percentile_0_at_time": 100 * subsample.rainfall_percentile_at_time.eq(0).mean(),
            "municipal_share_percentile_le10_at_time": 100 * subsample.rainfall_percentile_at_time.le(10).mean(),
            "municipal_n": len(subsample),
        })
    national_all = national.copy()
    national_all["national_reference_mean_mm"] = national_all.national_rain_may_aug_mm.mean()
    national_all["national_reference_sd_mm"] = national_all.national_rain_may_aug_mm.std(ddof=1)
    national_all["is_comparison_year"] = national_all.year.isin(YEARS).astype(int)
    national_all = pd.concat([national_all, pd.DataFrame([{
        "year": 2026, "national_rain_may_aug_mm": rain_2026,
        "national_reference_mean_mm": national_all.national_rain_may_aug_mm.mean(),
        "national_reference_sd_mm": national_all.national_rain_may_aug_mm.std(ddof=1),
        "is_comparison_year": 1,
    }])], ignore_index=True)
    national_all["data_status"] = "FINAL"
    return municipal, pd.DataFrame(national_rows), national_all


def map_body(geo: gpd.GeoDataFrame, municipal: pd.DataFrame, summary: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.1), facecolor="white")
    for panel, (ax, year) in enumerate(zip(axes, YEARS, strict=True)):
        values = geo.merge(
            municipal.loc[municipal.year.eq(year), ["municipality_id", "percentile_group_at_time"]],
            on="municipality_id", validate="one_to_one",
        )
        for group in GROUPS:
            item = values.loc[values.percentile_group_at_time.eq(group)]
            if not item.empty:
                item.plot(ax=ax, color=COLOURS[group], edgecolor="white", linewidth=.10)
        item = summary.loc[summary.year.eq(year)].iloc[0]
        status = "final"
        ax.text(0, 1.015, f"({chr(97 + panel)}) {year} ({status}); {item.national_rain_may_aug_mm:.0f} mm", transform=ax.transAxes, fontsize=8.3, fontweight="bold")
        ax.set_axis_off()
        ax.set_aspect("equal")
    handles = [Patch(facecolor=COLOURS[group], edgecolor="white", label=LABELS[group]) for group in GROUPS]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=7.1, frameon=False, bbox_to_anchor=(.5, .06), columnspacing=1.1, handlelength=1.25)
    fig.tight_layout(rect=(0, .09, 1, 1), w_pad=.15)
    BODY.mkdir(parents=True, exist_ok=True)
    fig.savefig(BODY / "fig01f_chirps_driest_years_contemporaneous_body.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)



def department_common_reference(geo: gpd.GeoDataFrame) -> pd.DataFrame:
    """Department shocks on one fixed 1981--2025 reference, as in Figure 2."""
    department_geo = geo.dissolve(by="department", as_index=False)
    department_geo["municipality_id"] = np.arange(1, len(department_geo) + 1)
    department_geo["municipality"] = ""
    annual, years = annual_means(
        department_geo[["municipality_id", "department", "municipality", "geometry"]]
    )
    if years != list(range(1981, 2026)):
        raise ValueError("Expected the complete 1981--2025 department history.")
    historic = annual.groupby("department", as_index=False).agg(
        hist_mean_mm=("rain_may_aug_mm", "mean"),
        hist_median_mm=("rain_may_aug_mm", "median"),
        hist_sd_mm=("rain_may_aug_mm", "std"),
    )
    wide = annual.pivot(index="department", columns="year", values="rain_may_aug_mm")
    result = historic.set_index("department")
    for year in (2015, 2019):
        result[f"rain_{year}_mm"] = wide[year]
        result[f"z_{year}_common"] = (wide[year] - result.hist_mean_mm) / result.hist_sd_mm
        result[f"p_{year}_common"] = 100 * wide.le(wide[year], axis=0).mean(axis=1)

    cumulative = DERIVED / "chirps_2026_may_aug_cumulative.tif"
    current_rows: list[dict[str, float | str]] = []
    with rasterio.open(cumulative) as source:
        image = source.read(1).astype(float)
        if source.nodata is not None:
            image[image == source.nodata] = np.nan
        for item in department_geo.itertuples():
            rows, cols, areas = pixel_weights(source.transform, source.width, source.height, item.geometry)
            values = image[rows, cols]
            valid = np.isfinite(values)
            current_rows.append({
                "department": item.department,
                "rain_2026_mm": float(np.average(values[valid], weights=areas[valid])),
            })
    current = pd.DataFrame(current_rows).set_index("department")
    result["rain_2026_mm"] = current.rain_2026_mm
    result["z_2026_common"] = (result.rain_2026_mm - result.hist_mean_mm) / result.hist_sd_mm
    result["p_2026_common"] = 100 * wide.le(result.rain_2026_mm, axis=0).mean(axis=1)
    return result.reset_index().sort_values("z_2026_common").reset_index(drop=True)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    municipal, summary, national_all = calculate()
    municipal.to_csv(TABLES / "chirps_shock_comparison_municipality.csv", index=False)
    summary.to_csv(TABLES / "table_chirps_shock_comparison_summary.csv", index=False)
    national_all.to_csv(TABLES / "chirps_shock_comparison_national_annual.csv", index=False)
    concentration = (municipal.groupby(["year", "percentile_group_at_time"], observed=False).size().rename("municipalities").reset_index())
    concentration["share_percent"] = 100 * concentration.municipalities / 340
    concentration.to_csv(TABLES / "chirps_shock_comparison_concentration.csv", index=False)
    geo = load_municipal_geometry()
    department_common_reference(geo).to_csv(
        TABLES / "chirps_shock_comparison_department_common_reference.csv", index=False
    )
    map_body(geo, municipal, summary)
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
