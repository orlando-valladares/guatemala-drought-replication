"""Prepare reproducible CHIRPS inputs for the main maps and summary table.

The selected historical comparators are 2015 and 2019: the two lowest national
area-weighted May--August totals in the project's 1981--2025 CHIRPS raster.
Historical-percentile values for these final CHIRPS years are calculated within
the full 1981--2025 distribution, including the focal year. The 2026 statistic
uses the final 2026 monthly calculation against that same distribution.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from prepare_appendix_data import annual_means, load_municipal_geometry, pixel_weights


PROJECT = Path(__file__).resolve().parents[1]
DERIVED = PROJECT / "derived"
APP_TABLES = PROJECT / "figures" / "Appendix" / "tables"
HISTORICAL_YEARS = [2015, 2019, 2024, 2025]
COMPARISON_YEARS = [2015, 2019, 2024, 2025, 2026]


def national_history(geometry) -> tuple[pd.DataFrame, float]:
    """Area-weighted Guatemala totals from the original historical and 2026 rasters."""
    historical_path = PROJECT.parents[2] / "03_LatinAmerica" / "CHIRPS_Historical" / "GT_CHIRPSv3_MayAug_1981_2025.tif"
    with rasterio.open(historical_path) as source:
        years = [int(description.split("_")[0]) for description in source.descriptions]
        rows, cols, weights = pixel_weights(source.transform, source.width, source.height, geometry)
        cube = source.read().astype(float)
        if source.nodata is not None:
            cube[cube == source.nodata] = np.nan
        values = []
        for index in range(len(years)):
            selected = cube[index, rows, cols]
            valid = np.isfinite(selected)
            values.append(float(np.average(selected[valid], weights=weights[valid])))
    current_path = DERIVED / "chirps_2026_may_aug_cumulative.tif"
    with rasterio.open(current_path) as source:
        values_2026 = source.read(1).astype(float)
        if source.nodata is not None:
            values_2026[values_2026 == source.nodata] = np.nan
        rows, cols, weights = pixel_weights(source.transform, source.width, source.height, geometry)
        selected = values_2026[rows, cols]
        valid = np.isfinite(selected)
        current = float(np.average(selected[valid], weights=weights[valid]))
    return pd.DataFrame({"year": years, "national_rain_may_aug_mm": values}), current


def main() -> None:
    APP_TABLES.mkdir(parents=True, exist_ok=True)
    geo = load_municipal_geometry()
    annual, years = annual_means(geo)
    if years != list(range(1981, 2026)):
        raise ValueError("Expected CHIRPS historical years 1981--2025.")
    current = pd.read_csv(DERIVED / "chirps_2026_municipality.csv")
    stats = current.set_index("municipality_id")
    annual_wide = annual.pivot(index="municipality_id", columns="year", values="rain_may_aug_mm")
    records: list[pd.DataFrame] = []
    for year in HISTORICAL_YEARS:
        rain = annual_wide[year]
        past = annual_wide.to_numpy(float)
        percentile = 100 * (past <= rain.to_numpy(float)[:, None]).mean(axis=1)
        block = stats[["department", "municipality", "historical_mean_may_aug_mm", "historical_sd_may_aug_mm"]].reindex(annual_wide.index).copy()
        block["year"] = year
        block["rain_may_aug_mm"] = rain
        block["historical_percentile"] = percentile
        block["rainfall_z_score"] = (rain - block["historical_mean_may_aug_mm"]) / block["historical_sd_may_aug_mm"]
        block["data_status"] = "FINAL historical CHIRPS"
        records.append(block.reset_index())
    recent = current[[
        "municipality_id", "department", "municipality", "historical_mean_may_aug_mm",
        "historical_sd_may_aug_mm", "rain_2026_may_aug_mm",
        "rainfall_historical_percentile", "rainfall_z_score_vs_1981_2025",
    ]].copy()
    recent = recent.rename(columns={
        "rain_2026_may_aug_mm": "rain_may_aug_mm",
        "rainfall_historical_percentile": "historical_percentile",
        "rainfall_z_score_vs_1981_2025": "rainfall_z_score",
    })
    recent["year"] = 2026
    recent["data_status"] = "FINAL"
    records.append(recent)
    comparisons = pd.concat(records, ignore_index=True).sort_values(["year", "municipality_id"])
    comparisons["percentile_group"] = pd.cut(
        comparisons["historical_percentile"],
        bins=[-0.001, 0, 10, 25, 50, 75, 100.001],
        labels=["0", "1-10", "11-25", "26-50", "51-75", "76-100"],
    ).astype(str)
    comparisons.to_csv(DERIVED / "chirps_historical_comparison_2015_2019_2026_municipality.csv", index=False)

    national, national_2026 = national_history(geo.geometry.union_all())
    historical_national = national["national_rain_may_aug_mm"].to_numpy(float)
    national_rows = national.loc[national["year"].isin(HISTORICAL_YEARS)].copy()
    national_rows["national_historical_percentile"] = [
        100 * np.mean(historical_national <= value) for value in national_rows["national_rain_may_aug_mm"]
    ]
    national_rows["data_status"] = "FINAL historical CHIRPS"
    national_rows = pd.concat([national_rows, pd.DataFrame([{
        "year": 2026,
        "national_rain_may_aug_mm": national_2026,
        "national_historical_percentile": 100 * np.mean(historical_national <= national_2026),
        "data_status": "FINAL",
    }])], ignore_index=True)
    national_rows = national_rows.sort_values("year")
    national_rows.to_csv(APP_TABLES / "table_chirps_historical_comparison_years.csv", index=False)

    fields = current.loc[current["municipality"].isin(["Olopa", "Chahal", "Patzité"]), [
        "department", "municipality", "historical_mean_may_aug_mm",
        "historical_sd_may_aug_mm", "rain_2026_may_aug_mm",
        "rainfall_z_score_vs_1981_2025",
    ]].copy()
    fields = fields.rename(columns={
        "historical_mean_may_aug_mm": "historical_mean_mm",
        "historical_sd_may_aug_mm": "historical_sd_mm",
        "rain_2026_may_aug_mm": "rain_2026_mm",
        "rainfall_z_score_vs_1981_2025": "z_score_2026",
    })
    fields.insert(0, "area", fields["municipality"] + ", " + fields["department"])
    fields.insert(1, "historical_observations", 45)
    national_summary = pd.DataFrame([{
        "area": "Guatemala (area-weighted national total)",
        "historical_observations": 45,
        "historical_mean_mm": historical_national.mean(),
        "historical_sd_mm": historical_national.std(ddof=1),
        "rain_2026_mm": national_2026,
        "z_score_2026": (national_2026 - historical_national.mean()) / historical_national.std(ddof=1),
        "department": "National",
        "municipality": "Guatemala",
    }])
    summary = pd.concat([fields, national_summary], ignore_index=True)
    summary = summary[["area", "historical_observations", "historical_mean_mm", "historical_sd_mm", "rain_2026_mm", "z_score_2026"]]
    summary.to_csv(APP_TABLES / "table_chirps_summary_statistics.csv", index=False)
    markdown = [
        "# CHIRPS summary statistics",
        "",
        "CHIRPS v3 municipality area-weighted May–August rainfall. Historical reference: 1981–2025 (45 observations). 2026 is final.",
        "",
        "| Area | N | Historical mean (mm) | Historical SD (mm) | 2026 rainfall (mm) | 2026 z-score |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        markdown.append(f"| {row.area} | {row.historical_observations} | {row.historical_mean_mm:.1f} | {row.historical_sd_mm:.1f} | {row.rain_2026_mm:.1f} | {row.z_score_2026:.2f} |")
    markdown += [
        "",
        "The Guatemala row is an area-weighted national statistic extracted from the raster; it is not an unweighted average of municipality values.",
    ]
    (APP_TABLES / "table_chirps_summary_statistics.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print("Prepared 2015/2019/2026 and 2024/2025/2026 municipality comparison maps and CHIRPS summary table.")
    print(national_rows.to_string(index=False, float_format=lambda value: f"{value:.1f}"))


if __name__ == "__main__":
    main()
