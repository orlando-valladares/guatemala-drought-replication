#!/usr/bin/env python3
"""Prepare explicit percentile references for the two CHIRPS map comparisons.

``available at the time`` compares each year only with earlier observations.
``common retrospective leave-one-out`` compares each focal year with all other
1981--2026 observations, excluding the focal year. All four 2026 monthly inputs are final CHIRPS v3 files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from prepare_appendix_data import annual_means, load_municipal_geometry


PROJECT = Path(__file__).resolve().parents[1]
DERIVED = PROJECT / "derived"
TABLES = PROJECT / "figures" / "Appendix" / "tables"
AT_TIME_YEARS = [2015, 2019, 2024, 2025, 2026]
LEAVE_ONE_OUT_YEARS = [2015, 2019, 2026]


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


def records_for_reference(
    values: pd.DataFrame,
    metadata: pd.DataFrame,
    years: list[int],
    reference_type: str,
) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for year in years:
        if reference_type == "available_at_time":
            reference_years = list(range(1981, year))
        elif reference_type == "common_leave_one_out":
            reference_years = [candidate for candidate in values.columns if candidate != year]
        else:
            raise ValueError(f"Unknown reference type: {reference_type}")
        focal = values[year]
        reference = values[reference_years]
        result = metadata.copy()
        result["year"] = year
        result["rain_may_aug_mm"] = focal
        result["reference_type"] = reference_type
        result["reference_start"] = min(reference_years)
        result["reference_end"] = max(reference_years)
        result["reference_n"] = len(reference_years)
        result["rainfall_percentile"] = 100 * reference.le(focal, axis=0).mean(axis=1)
        result["percentile_group"] = result["rainfall_percentile"].map(percentile_group)
        result["focal_data_status"] = "FINAL"
        result["reference_includes_2026_final"] = int(year != 2026 and 2026 in reference_years)
        records.append(result.reset_index())
    return pd.concat(records, ignore_index=True).sort_values(["year", "municipality_id"])


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    geometry = load_municipal_geometry()
    annual, years = annual_means(geometry)
    if years != list(range(1981, 2026)):
        raise ValueError("Expected final historical CHIRPS years 1981--2025.")
    historical = annual.pivot(index="municipality_id", columns="year", values="rain_may_aug_mm")
    current = pd.read_csv(DERIVED / "chirps_2026_municipality.csv").set_index("municipality_id")
    values = historical.copy()
    values[2026] = current.reindex(values.index)["rain_2026_may_aug_mm"]
    metadata = current.reindex(values.index)[["department", "municipality"]]
    if values.isna().any().any() or metadata.isna().any().any():
        raise ValueError("Expected complete municipality values and metadata.")

    at_time = records_for_reference(values, metadata, AT_TIME_YEARS, "available_at_time")
    leave_one_out = records_for_reference(values, metadata, LEAVE_ONE_OUT_YEARS, "common_leave_one_out")
    at_time.to_csv(TABLES / "chirps_reference_available_each_year_municipality.csv", index=False)
    leave_one_out.to_csv(TABLES / "chirps_common_reference_leave_one_out_municipality.csv", index=False)

    zscore_rows: list[pd.DataFrame] = []
    for year in [2015, 2019, 2025]:
        focal = historical[year]
        result = metadata.copy()
        result["year"] = year
        result["rain_may_aug_mm"] = focal
        result["reference_start"] = 1981
        result["reference_end"] = 2025
        result["reference_n"] = 45
        result["historical_mean_mm"] = historical.mean(axis=1)
        result["historical_sd_mm"] = historical.std(axis=1, ddof=1)
        result["rainfall_z_score_common"] = (focal - result["historical_mean_mm"]) / result["historical_sd_mm"]
        result["focal_data_status"] = "FINAL"
        zscore_rows.append(result.reset_index())
    pd.concat(zscore_rows, ignore_index=True).sort_values(["year", "municipality_id"]).to_csv(
        TABLES / "chirps_common_reference_zscore_2015_2019_2025_municipality.csv", index=False
    )

    for label, table in [("available_at_time", at_time), ("common_leave_one_out", leave_one_out)]:
        counts = table.groupby("year").agg(
            municipalities=("municipality_id", "size"),
            p0_municipalities=("rainfall_percentile", lambda x: int(x.eq(0).sum())),
            p0_percent=("rainfall_percentile", lambda x: 100 * x.eq(0).mean()),
        )
        print(f"{label}\n{counts.to_string(float_format=lambda value: f'{value:.2f}')}")


if __name__ == "__main__":    main()
