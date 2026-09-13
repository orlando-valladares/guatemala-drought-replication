#!/usr/bin/env python3
"""Build the CHIRPS appendix summary table from raster-level annual aggregates.

Each reported area is first aggregated directly from the CHIRPS raster with
fractional equal-area cell weights. Historical moments are then computed across
its 45 annual May--August aggregates (1981--2025), never from municipal means
or municipal z-scores.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

from prepare_appendix_data import annual_means, corridor_flags, load_municipal_geometry, pixel_weights


PROJECT = Path(__file__).resolve().parents[1]
DERIVED = PROJECT / "derived"
TABLES = PROJECT / "figures" / "Appendix" / "tables"


def areas_for_table() -> gpd.GeoDataFrame:
    municipalities = load_municipal_geometry()
    current = pd.read_csv(DERIVED / "chirps_2026_municipality.csv")
    flags = corridor_flags(municipalities, current[["municipality_id", "corredor_seco_160"]])
    flagged = municipalities.merge(
        flags[["municipality_id", "corredor_seco_160", "legacy_sesan_core_2016"]],
        on="municipality_id", validate="one_to_one",
    )
    records: list[dict[str, object]] = [
        {
            "municipality_id": 9001,
            "department": "National",
            "municipality": "Guatemala",
            "panel": "A",
            "panel_order": 1,
            "section": "",
            "sort_order": 1,
            "area": "Guatemala",
            "indent": 0,
            "geometry": flagged.geometry.union_all(),
        },
        {
            "municipality_id": 9002,
            "department": "Corredor Seco",
            "municipality": "Corredor Seco",
            "panel": "A",
            "panel_order": 1,
            "section": "Definición base del Corredor Seco",
            "sort_order": 2,
            "area": "Corredor Seco",
            "indent": 1,
            "geometry": flagged.loc[flagged.legacy_sesan_core_2016.eq(1)].geometry.union_all(),
        },
        {
            "municipality_id": 9003,
            "department": "Corredor Seco ampliado",
            "municipality": "Corredor Seco ampliado",
            "panel": "A",
            "panel_order": 1,
            "section": "Definición ampliada del Corredor Seco",
            "sort_order": 3,
            "area": "Corredor Seco ampliado",
            "indent": 1,
            "geometry": flagged.loc[flagged.corredor_seco_160.eq(1)].geometry.union_all(),
        },
    ]
    departments = flagged.dissolve(by="department", as_index=False).sort_values("department")
    for index, item in enumerate(departments.itertuples(), start=1):
        records.append({
            "municipality_id": 9100 + index,
            "department": item.department,
            "municipality": item.department,
            "panel": "B",
            "panel_order": 2,
            "section": "",
            "sort_order": index,
            "area": item.department,
            "indent": 0,
            "geometry": item.geometry,
        })
    field_order = [("Olopa", "Chiquimula"), ("Patzité", "Quiché"), ("Chahal", "Alta Verapaz")]
    for index, (municipality, department) in enumerate(field_order, start=1):
        match = flagged.loc[flagged.municipality.eq(municipality) & flagged.department.eq(department)]
        if len(match) != 1:
            raise ValueError(f"Expected one polygon for {municipality}, {department}.")
        item = match.iloc[0]
        records.append({
            "municipality_id": 9200 + index,
            "department": department,
            "municipality": municipality,
            "panel": "C",
            "panel_order": 3,
            "section": "",
            "sort_order": index,
            "area": f"{municipality}, {department}",
            "indent": 0,
            "geometry": item.geometry,
        })
    return gpd.GeoDataFrame(records, geometry="geometry", crs=flagged.crs)


def current_rainfall(areas: gpd.GeoDataFrame) -> dict[int, float]:
    source_path = DERIVED / "chirps_2026_may_aug_cumulative.tif"
    output: dict[int, float] = {}
    with rasterio.open(source_path) as source:
        image = source.read(1).astype(float)
        if source.nodata is not None:
            image[image == source.nodata] = np.nan
        for item in areas.itertuples():
            rows, cols, weights = pixel_weights(source.transform, source.width, source.height, item.geometry)
            values = image[rows, cols]
            valid = np.isfinite(values)
            if not valid.any():
                raise ValueError(f"No valid 2026 CHIRPS cells for {item.area}.")
            output[int(item.municipality_id)] = float(np.average(values[valid], weights=weights[valid]))
    return output


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    areas = areas_for_table()
    annual, years = annual_means(areas)
    if years != list(range(1981, 2026)):
        raise ValueError("Expected 45 final historical annual CHIRPS values, 1981--2025.")
    current = current_rainfall(areas)
    rows: list[dict[str, object]] = []
    for item in areas.itertuples():
        historic = annual.loc[annual.municipality_id.eq(item.municipality_id), "rain_may_aug_mm"].to_numpy(float)
        value = current[int(item.municipality_id)]
        mean = float(historic.mean())
        sd = float(historic.std(ddof=1))
        if sd <= 0:
            raise ValueError(f"Non-positive historical SD for {item.area}.")
        rank = int(1 + np.sum(historic < value))
        rows.append({
            "panel": item.panel,
            "panel_order": item.panel_order,
            "section": item.section,
            "sort_order": item.sort_order,
            "area": item.area,
            "indent": item.indent,
            "historical_observations": len(historic),
            "historical_mean_mm": mean,
            "historical_sd_mm": sd,
            "rain_2026_mm": value,
            "deviation_pct_vs_historical_mean": 100 * (value - mean) / mean,
            "z_score_2026": (value - mean) / sd,
            "historical_rank_low_to_high_of_46": rank,
            "historical_rank_display": f"{rank}/46",
            "data_status": "FINAL",
        })
    result = pd.DataFrame(rows)
    department_mask = result.panel.eq("B")
    result.loc[department_mask, "sort_order"] = result.loc[department_mask, "z_score_2026"].rank(
        method="first", ascending=True
    ).astype(int)
    result = result.sort_values(["panel_order", "sort_order"]).reset_index(drop=True)
    if len(result) != 28 or result.panel.value_counts().to_dict() != {"B": 22, "A": 3, "C": 3}:
        raise ValueError("Unexpected table composition.")
    result.to_csv(TABLES / "table_chirps_summary_statistics.csv", index=False)
    summary = result[["panel", "area", "historical_mean_mm", "historical_sd_mm", "rain_2026_mm", "z_score_2026", "historical_rank_display"]]
    markdown = ["# CHIRPS rainfall summary statistics", "", "The canonical machine-readable table is `table_chirps_summary_statistics.csv`.", "", "Historical reference: 1981--2025 (45 annual aggregates); 2026 is final.", ""]
    markdown += ["| Panel | Area | Historical mean (mm) | Historical SD (mm) | 2026 rainfall (mm) | 2026 z-score | Historical rank |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in summary.itertuples(index=False):
        markdown.append(f"| {row.panel} | {row.area} | {row.historical_mean_mm:.1f} | {row.historical_sd_mm:.1f} | {row.rain_2026_mm:.1f} | {row.z_score_2026:.2f} | {row.historical_rank_display} |")
    (TABLES / "table_chirps_summary_statistics.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(summary.to_string(index=False, float_format=lambda value: f"{value:.2f}"))


if __name__ == "__main__":
    main()
