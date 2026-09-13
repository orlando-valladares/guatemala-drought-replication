#!/usr/bin/env python3
'''Build the Honduras-only CHIRPS replication from immutable local sources.'''
from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import Window, from_bounds
from shapely import make_valid
from shapely.geometry import box
from shapely.ops import transform as shapely_transform

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
PLAYDATA = WORKSPACE / "02_projects" / "07_Playdata"
WORLD = PLAYDATA / "00_World"
LATAM = PLAYDATA / "03_LatinAmerica"
HISTORICAL = LATAM / "CHIRPS_Historical" / "HN_CHIRPSv3_MayAug_1981_2025.tif"
CLIMATOLOGY = LATAM / "CHIRPS_Historical" / "HN_CHIRPSv3_MayAug_climatology_1981_2025.tif"
PENTADS = LATAM / "CHIRPS_2026_May-August"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
HONDURAS = FIGURES / "Honduras"
APPENDIX = HONDURAS / "Appendix"
TABLES = APPENDIX / "tables"
DOCS = APPENDIX / "documentation"


def source_boundary(level: str) -> gpd.GeoDataFrame:
    path = WORLD / f"geoBoundariesCGAZ_{level}.zip"
    data = gpd.read_file(path, where="shapeGroup = 'HND'")
    if data.crs is None:
        data = data.set_crs("EPSG:4326")
    data = data.to_crs("EPSG:4326")
    data.loc[~data.geometry.is_valid, "geometry"] = data.loc[~data.geometry.is_valid, "geometry"].map(make_valid)
    return data


def load_geography() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    country = source_boundary("ADM0")
    department = source_boundary("ADM1")
    municipality = source_boundary("ADM2")
    if len(country) != 1 or len(department) != 18 or len(municipality) != 298:
        raise ValueError(f"Expected 1 country, 18 departments and 298 municipalities; got {len(country)}, {len(department)}, {len(municipality)}.")
    department = department.rename(columns={"shapeID": "department_id", "shapeName": "department"})
    municipality = municipality.rename(columns={"shapeID": "municipality_id", "shapeName": "municipality"})
    points = municipality[["municipality_id", "geometry"]].copy()
    points["geometry"] = points.representative_point()
    assigned = gpd.sjoin(points, department[["department_id", "department", "geometry"]], how="left", predicate="within")
    if assigned["department_id"].isna().any() or assigned["municipality_id"].duplicated().any():
        missing = assigned.loc[assigned["department_id"].isna(), "municipality_id"].tolist()
        raise ValueError(f"Every ADM2 representative point must map to exactly one ADM1 polygon; unmatched: {missing}")
    municipality = municipality.merge(assigned.drop(columns=["geometry", "index_right"]), on="municipality_id", validate="one_to_one")
    municipality = municipality[["municipality_id", "department_id", "department", "municipality", "geometry"]].copy()
    country = country.rename(columns={"shapeName": "country"})[["country", "geometry"]]
    if municipality["municipality_id"].duplicated().any() or department["department_id"].duplicated().any():
        raise ValueError("GeoBoundaries identifiers must be unique within Honduras.")
    return country, department[["department_id", "department", "geometry"]], municipality


def pixel_weights(transform, width: int, height: int, geometry) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    inverse = ~transform
    min_col, min_row = inverse * (geometry.bounds[0], geometry.bounds[3])
    max_col, max_row = inverse * (geometry.bounds[2], geometry.bounds[1])
    col_start = max(0, int(math.floor(min(min_col, max_col))))
    col_stop = min(width, int(math.ceil(max(min_col, max_col))))
    row_start = max(0, int(math.floor(min(min_row, max_row))))
    row_stop = min(height, int(math.ceil(max(min_row, max_row))))
    to_equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    target = shapely_transform(to_equal_area, geometry)
    rows, cols, areas = [], [], []
    for row in range(row_start, row_stop):
        y_top = transform.f + row * transform.e
        y_bottom = y_top + transform.e
        for col in range(col_start, col_stop):
            x_left = transform.c + col * transform.a
            x_right = x_left + transform.a
            area = target.intersection(shapely_transform(to_equal_area, box(x_left, y_bottom, x_right, y_top))).area
            if area > 0:
                rows.append(row); cols.append(col); areas.append(area)
    if not areas:
        raise ValueError("No CHIRPS cells overlap a Honduras analytical polygon.")
    return np.asarray(rows), np.asarray(cols), np.asarray(areas)


def pentad_files() -> list[Path]:
    files = sorted(PENTADS.glob("chirps-v3.0.2026.*.tif"))
    expected = [PENTADS / f"chirps-v3.0.2026.{month:02d}.{pentad}.tif" for month in range(5, 9) for pentad in range(1, 7)]
    if files != expected:
        raise ValueError("Expected exactly the 24 May--August 2026 CHIRPS pentads, six per month.")
    return files


def build_cumulative(country_geometry) -> Path:
    files = pentad_files()
    output = DERIVED / "honduras_chirps_2026_may_aug_cumulative.tif"
    with rasterio.open(files[0]) as first:
        raw = from_bounds(*country_geometry.bounds, transform=first.transform)
        c0 = max(0, int(math.floor(raw.col_off)) - 1); r0 = max(0, int(math.floor(raw.row_off)) - 1)
        c1 = min(first.width, int(math.ceil(raw.col_off + raw.width)) + 1); r1 = min(first.height, int(math.ceil(raw.row_off + raw.height)) + 1)
        window = Window(c0, r0, c1 - c0, r1 - r0)
        profile = first.profile.copy()
        profile.update(driver="GTiff", count=1, dtype="float32", nodata=-9999.0, height=window.height, width=window.width, transform=first.window_transform(window), compress="deflate")
    total = np.zeros((int(window.height), int(window.width)), dtype=np.float64)
    complete = np.ones(total.shape, dtype=bool)
    for path in files:
        with rasterio.open(path) as source:
            values = source.read(1, window=window).astype(np.float64)
            valid = np.isfinite(values) & (values >= 0)
            # CHIRPS global pentads use negative ocean/fill values in this region
            # without declaring nodata. A cumulative total requires all 24 valid
            # pentads, so a partly missing cell is excluded rather than shortened.
            total[valid] += values[valid]
            complete &= valid
    total[~complete] = -9999.0
    with rasterio.open(output, "w", **profile) as destination:
        destination.write(total.astype(np.float32), 1)
        destination.set_band_description(1, "2026_MayAug_precipitation_mm_PRELIMINARY")
        destination.update_tags(data_status="PRELIMINARY", aggregation="pixelwise sum of 24 CHIRPS v3 pentads with complete-pentad requirement", period="2026-05-01 through 2026-08-31", negative_fill_values="excluded")
    return output


def extract_historical(geometries: gpd.GeoDataFrame, id_column: str) -> tuple[pd.DataFrame, list[int]]:
    with rasterio.open(HISTORICAL) as source:
        years = [int(label.split("_")[0]) for label in source.descriptions]
        if years != list(range(1981, 2026)):
            raise ValueError("Honduras historical bands must be 1981--2025.")
        cube = source.read().astype(float)
        if source.nodata is not None:
            cube[cube == source.nodata] = np.nan
        weights = {str(getattr(row, id_column)): pixel_weights(source.transform, source.width, source.height, row.geometry) for row in geometries.itertuples(index=False)}
    details = geometries.drop(columns="geometry").set_index(id_column)
    records = []
    for identifier, (rows, cols, areas) in weights.items():
        values = cube[:, rows, cols]
        annual = []
        for band in range(cube.shape[0]):
            selected = values[band]; valid = np.isfinite(selected)
            if not valid.any():
                raise ValueError(f"No valid historical CHIRPS pixels for {identifier}, year {years[band]}.")
            annual.append(float(np.average(selected[valid], weights=areas[valid])))
        for year, value in zip(years, annual, strict=True):
            record = {id_column: identifier, "year": year, "rain_may_aug_mm": value}
            record.update(details.loc[identifier].to_dict()); records.append(record)
    return pd.DataFrame(records), years


def extract_current(geometries: gpd.GeoDataFrame, id_column: str, cumulative: Path) -> pd.DataFrame:
    with rasterio.open(cumulative) as source:
        image = source.read(1).astype(float)
        if source.nodata is not None:
            image[image == source.nodata] = np.nan
        records = []
        details = geometries.drop(columns="geometry").set_index(id_column)
        for row in geometries.itertuples(index=False):
            identifier = str(getattr(row, id_column))
            rows, cols, areas = pixel_weights(source.transform, source.width, source.height, row.geometry)
            selected = image[rows, cols]; valid = np.isfinite(selected)
            record = {
                id_column: identifier,
                "rain_2026_may_aug_mm": float(np.average(selected[valid], weights=areas[valid])) if valid.any() else np.nan,
                "valid_2026_pixel_area_share": float(areas[valid].sum() / areas.sum()),
            }
            record.update(details.loc[identifier].to_dict()); records.append(record)
    return pd.DataFrame(records)


def summarize(annual: pd.DataFrame, current: pd.DataFrame, id_column: str) -> pd.DataFrame:
    pivot = annual.pivot(index=id_column, columns="year", values="rain_may_aug_mm")
    values = pivot.to_numpy(float)
    summary = pd.DataFrame(index=pivot.index)
    summary["historical_mean_may_aug_mm"] = values.mean(axis=1)
    summary["historical_median_may_aug_mm"] = np.median(values, axis=1)
    summary["historical_sd_may_aug_mm"] = values.std(axis=1, ddof=1)
    summary["historical_min_may_aug_mm"] = values.min(axis=1)
    summary["historical_max_may_aug_mm"] = values.max(axis=1)
    summary["historical_p10_may_aug_mm"] = np.quantile(values, .10, axis=1)
    summary["historical_p20_may_aug_mm"] = np.quantile(values, .20, axis=1)
    summary["historical_p80_may_aug_mm"] = np.quantile(values, .80, axis=1)
    summary["historical_p90_may_aug_mm"] = np.quantile(values, .90, axis=1)
    now = current.set_index(id_column)["rain_2026_may_aug_mm"].reindex(summary.index)
    summary["rain_2026_may_aug_mm"] = now
    summary["rainfall_anomaly_pct_vs_historical_median"] = 100 * (now - summary["historical_median_may_aug_mm"]) / summary["historical_median_may_aug_mm"]
    percentile = np.full(len(summary), np.nan)
    has_current = now.notna().to_numpy()
    percentile[has_current] = 100 * (values[has_current] <= now.to_numpy(float)[has_current, None]).mean(axis=1)
    summary["rainfall_historical_percentile"] = percentile
    summary["rainfall_z_score_vs_1981_2025"] = (now - summary["historical_mean_may_aug_mm"]) / summary["historical_sd_may_aug_mm"]
    detail = current.set_index(id_column).drop(columns="rain_2026_may_aug_mm")
    output = detail.join(summary).reset_index(); output["data_status"] = "PRELIMINARY"
    return output


def pgroup(values: pd.Series) -> pd.Series:
    output = pd.Series("No valid 2026 cells", index=values.index, dtype="object")
    valid = values.notna()
    output.loc[valid] = pd.cut(values.loc[valid], [-.001, 0, 10, 25, 50, 75, 100.001], labels=["0", "1-10", "11-25", "26-50", "51-75", "76-100"]).astype(str)
    return output


def comparison_table(annual: pd.DataFrame, summary: pd.DataFrame, dry_years: list[int]) -> pd.DataFrame:
    pivot = annual.pivot(index="municipality_id", columns="year", values="rain_may_aug_mm")
    stats = summary.set_index("municipality_id")
    rows = []
    for year in sorted(set(dry_years + [2024, 2025])):
        rain = pivot[year]; values = pivot.to_numpy(float)
        block = stats[["department", "municipality", "historical_mean_may_aug_mm", "historical_sd_may_aug_mm"]].copy()
        block["year"] = year; block["rain_may_aug_mm"] = rain
        block["historical_percentile"] = 100 * (values <= rain.to_numpy(float)[:, None]).mean(axis=1)
        block["rainfall_z_score"] = (rain - block["historical_mean_may_aug_mm"]) / block["historical_sd_may_aug_mm"]
        block["data_status"] = "FINAL historical CHIRPS"; rows.append(block.reset_index())
    recent = summary[["municipality_id", "department", "municipality", "historical_mean_may_aug_mm", "historical_sd_may_aug_mm", "rain_2026_may_aug_mm", "rainfall_historical_percentile", "rainfall_z_score_vs_1981_2025"]].rename(columns={"rain_2026_may_aug_mm":"rain_may_aug_mm", "rainfall_historical_percentile":"historical_percentile", "rainfall_z_score_vs_1981_2025":"rainfall_z_score"}).copy()
    recent["year"] = 2026; recent["data_status"] = "PRELIMINARY"; rows.append(recent)
    output = pd.concat(rows, ignore_index=True).sort_values(["year", "municipality_id"])
    output["percentile_group"] = pgroup(output["historical_percentile"])
    return output


def climatology_check(geometries: gpd.GeoDataFrame, summary: pd.DataFrame) -> dict[str, float]:
    with rasterio.open(CLIMATOLOGY) as source:
        cube = source.read().astype(float)
        check = []
        for row in geometries.itertuples(index=False):
            rows, cols, weights = pixel_weights(source.transform, source.width, source.height, row.geometry)
            check.append({"municipality_id":row.municipality_id, "median":float(np.average(cube[0,rows,cols],weights=weights)), "mean":float(np.average(cube[1,rows,cols],weights=weights)), "sd":float(np.average(cube[2,rows,cols],weights=weights))})
    merged = summary.merge(pd.DataFrame(check), on="municipality_id", validate="one_to_one")
    return {"mean":float(np.abs(merged.historical_mean_may_aug_mm-merged["mean"]).max()), "median":float(np.abs(merged.historical_median_may_aug_mm-merged["median"]).max()), "sd":float(np.abs(merged.historical_sd_may_aug_mm-merged["sd"]).max())}


def main() -> None:
    for folder in [DERIVED, TABLES, DOCS]: folder.mkdir(parents=True, exist_ok=True)
    country, dept_geo, muni_geo = load_geography()
    cumulative = build_cumulative(country.geometry.iloc[0])
    muni_annual, _ = extract_historical(muni_geo, "municipality_id")
    muni_current = extract_current(muni_geo, "municipality_id", cumulative)
    municipality = summarize(muni_annual, muni_current, "municipality_id")
    municipality["rainfall_percentile_group"] = pgroup(municipality.rainfall_historical_percentile)
    municipality = municipality.sort_values("rainfall_z_score_vs_1981_2025").reset_index(drop=True); municipality["z_rank"] = np.arange(1,len(municipality)+1)
    dept_annual, _ = extract_historical(dept_geo, "department_id")
    dept_current = extract_current(dept_geo, "department_id", cumulative)
    department = summarize(dept_annual, dept_current, "department_id").sort_values("rainfall_z_score_vs_1981_2025").reset_index(drop=True); department["z_rank"] = np.arange(1,len(department)+1)
    nat_geo = country.assign(national_id="HND")[["national_id","country","geometry"]]
    nat_annual, _ = extract_historical(nat_geo, "national_id")
    nat_current = extract_current(nat_geo, "national_id", cumulative)
    national = summarize(nat_annual, nat_current, "national_id")
    dry = nat_annual.sort_values("rain_may_aug_mm").head(2).year.astype(int).tolist()
    comparisons = comparison_table(muni_annual, municipality, dry)
    validation = climatology_check(muni_geo, municipality)
    municipality.to_csv(DERIVED/"honduras_chirps_2026_municipality.csv",index=False)
    department.to_csv(DERIVED/"honduras_chirps_2026_department.csv",index=False)
    muni_geo.drop(columns="geometry").to_csv(DERIVED/"honduras_municipality_crosswalk.csv",index=False)
    comparisons.to_csv(DERIVED/"honduras_chirps_historical_comparison_municipality.csv",index=False)
    nat_annual.assign(data_status="FINAL historical CHIRPS").to_csv(DERIVED/"honduras_chirps_national_annual_1981_2025.csv",index=False)
    municipality.to_csv(TABLES/"honduras_chirps_municipality_graph_data.csv",index=False)
    department.to_csv(TABLES/"honduras_chirps_department_graph_data.csv",index=False)
    nat_annual.assign(data_status="FINAL historical CHIRPS").to_csv(TABLES/"honduras_chirps_national_annual_1981_2025.csv",index=False)
    r=national.iloc[0]
    pd.DataFrame([{"country":"Honduras","historical_observations":45,"historical_mean_mm":r.historical_mean_may_aug_mm,"historical_median_mm":r.historical_median_may_aug_mm,"historical_sd_mm":r.historical_sd_may_aug_mm,"rain_2026_mm":r.rain_2026_may_aug_mm,"rainfall_anomaly_pct_vs_historical_median":r.rainfall_anomaly_pct_vs_historical_median,"rainfall_historical_percentile":r.rainfall_historical_percentile,"rainfall_z_score":r.rainfall_z_score_vs_1981_2025,"municipalities":len(municipality),"record_low_municipalities":int(municipality.rainfall_historical_percentile.eq(0).sum()),"record_low_municipalities_share_pct":100*float(municipality.rainfall_historical_percentile.eq(0).mean()),"two_driest_historical_years":", ".join(map(str,dry)),"data_status":"PRELIMINARY"}]).to_csv(TABLES/"table_honduras_chirps_national_summary.csv",index=False)
    note = f'''# Honduras CHIRPS replication notes

This Honduras-only CHIRPS replication uses immutable local `HN_CHIRPSv3_MayAug_1981_2025.tif` annual May--August totals and the same 24 global preliminary CHIRPS v3 pentads used for Guatemala (1 May--31 August 2026). The clipped 2026 cumulative raster is a derived pixelwise sum; raw files are unchanged.

GeoBoundaries CGAZ provides 1 Honduras ADM0 polygon, 18 ADM1 departments, and 298 ADM2 municipality polygons. `shapeID` is retained as the analytical identifier. Municipality-to-department attribution is a spatial representative-point join, not a name join; every one of the 298 records maps once to an ADM1 department.

Rainfall is a fractional-pixel EPSG:6933 equal-area weighted mean of cumulative millimetres, never a sum of pixels. The historical distribution is 1981--2025 and uses sample SD. The 2026 percentile is the share of historical local totals less than or equal to preliminary 2026; a zero denotes a local record low.

The two lowest Honduras national area-weighted historical May--August totals are {dry[0]} and {dry[1]}. The supplied three-band climatology is a validation input, not a replacement for annual data needed for percentiles. Maximum municipality-level absolute differences from annual-band aggregates: mean {validation['mean']:.4f} mm; median {validation['median']:.4f} mm; SD {validation['sd']:.4f} mm. Any SD residual can reflect provider population-versus-sample convention.

All 2026 results are PRELIMINARY. The global preliminary pentads contain undeclared negative ocean/fill values around small islands; a 2026 cell is used only when all 24 pentads are non-negative and finite. Units with no complete-cell coverage remain missing, never percentile zero. CHIRPS is a meteorological rainfall measure, not crop loss or household impact.
'''
    (DOCS/"honduras_chirps_notes.md").write_text(note,encoding="utf-8")
    print(f"Honduras CHIRPS derived: {len(municipality)} municipalities; {len(department)} departments; national 2026={r.rain_2026_may_aug_mm:.1f} mm; dry years={dry}.")

if __name__ == "__main__": main()
