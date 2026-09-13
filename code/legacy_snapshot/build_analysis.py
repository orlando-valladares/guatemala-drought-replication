#!/usr/bin/env python3
"""Build the Dalton InsumoCampo descriptive climate, price, and budget outputs.

All input paths point to the existing shared source library.  The script never
writes to a sources/ directory and does not copy raw inputs into this project.
Run from any directory with: python3 code/build_analysis.py
"""

from __future__ import annotations

import math
import unicodedata
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
from rasterio.mask import mask as rio_mask
from shapely.geometry import box, mapping
from shapely.ops import transform as shapely_transform
from shapely import make_valid
from pyproj import Transformer


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
PLAYDATA = WORKSPACE / "02_projects" / "07_Playdata"
GUATEMALA = PLAYDATA / "02_Guatemala"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
TABLES = PROJECT / "tables"
DOCS = PROJECT / "documentation"

for directory in (DERIVED, FIGURES, TABLES, DOCS):
    directory.mkdir(parents=True, exist_ok=True)

MUNIS = (
    GUATEMALA
    / "sources"
    / "JSON_Departamenos_Municipios_LugaresPoblados"
    / "Mapas-TopoJSON-Guatemala-main"
    / "munis.json"
)
CHIRPS_HIST = PLAYDATA / "03_LatinAmerica" / "CHIRPS_Historical" / "GT_CHIRPSv3_MayAug_1981_2025.tif"
CHIRPS_2026 = PLAYDATA / "03_LatinAmerica" / "CHIRPS_2026_May-August"
CHIRPS_2026_FINAL_MONTHLY = CHIRPS_2026 / "final_monthly"
FAO_ASIS = GUATEMALA / "sources" / "FAO_ASI" / "ASI_Dekad_Season1_data.csv"
MAGA = (
    GUATEMALA
    / "sources"
    / "MAGA_Precios_diarios_de_diversos_productos_agrícolas_en_Guatemala_actualizado_al_2026-08-21.csv"
    / "Precios_diarios_de_diversos_productos_agrícolas_en_Guatemala_actualizado_al_2026-08-21.csv"
)
ENIGH_DIR = GUATEMALA / "sources" / "ENIGH_2021-2022"
CORRIDOR_DTA = GUATEMALA / "proyects" / "02_MSPAS_heat" / "working" / "mspas-cases-municipality-disease-2017-2024-wide.dta"
CORRIDOR_UNMATCHED = GUATEMALA / "proyects" / "02_MSPAS_heat" / "working" / "corredor-seco-unmatched-municipalities.csv"

SITE_ORDER = [("Olopa", "Chiquimula"), ("Chahal", "Alta Verapaz"), ("Patzité", "Quiché")]


def normalize_text(value: object) -> str:
    """Accent-insensitive text key used only where a supplied code is absent."""
    text = unicodedata.normalize("NFD", str(value))
    return "".join(char for char in text if unicodedata.category(char) != "Mn").upper().strip()


def weighted_summary(values: pd.Series, weights: pd.Series) -> dict[str, float]:
    """Return transparent design-weighted descriptive statistics."""
    frame = pd.DataFrame({"value": values, "weight": weights}).replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame[(frame["weight"] > 0) & (frame["value"] >= 0)].sort_values("value")
    if frame.empty:
        return {"weighted_mean": np.nan, "weighted_median": np.nan, "p25": np.nan, "p75": np.nan, "unweighted_n": 0}
    v = frame["value"].to_numpy(dtype=float)
    w = frame["weight"].to_numpy(dtype=float)
    cumulative = np.cumsum(w) / w.sum()

    def quantile(probability: float) -> float:
        return float(v[np.searchsorted(cumulative, probability, side="left")])

    return {
        "weighted_mean": float(np.average(v, weights=w)),
        "weighted_median": quantile(0.5),
        "p25": quantile(0.25),
        "p75": quantile(0.75),
        "unweighted_n": int(len(frame)),
    }


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8")


def municipal_pixel_weights(transform, width: int, height: int, geometry):
    """Exact fractional-pixel weights, calculated in EPSG:6933 equal-area CRS.

    This is an area-weighted mean of the raster's precipitation depth.  It does
    not add millimetres over pixels.
    """
    inverse = ~transform
    min_col, min_row = inverse * (geometry.bounds[0], geometry.bounds[3])
    max_col, max_row = inverse * (geometry.bounds[2], geometry.bounds[1])
    col_start = max(0, int(math.floor(min(min_col, max_col))))
    col_stop = min(width, int(math.ceil(max(min_col, max_col))))
    row_start = max(0, int(math.floor(min(min_row, max_row))))
    row_stop = min(height, int(math.ceil(max(min_row, max_row))))
    to_equal_area = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    geometry_equal_area = shapely_transform(to_equal_area, geometry)
    rows, cols, areas = [], [], []
    for row in range(row_start, row_stop):
        y_top = transform.f + row * transform.e
        y_bottom = y_top + transform.e
        for col in range(col_start, col_stop):
            x_left = transform.c + col * transform.a
            x_right = x_left + transform.a
            cell_equal_area = shapely_transform(to_equal_area, box(x_left, y_bottom, x_right, y_top))
            overlap = geometry_equal_area.intersection(cell_equal_area).area
            if overlap > 0:
                rows.append(row)
                cols.append(col)
                areas.append(overlap)
    if not areas:
        raise ValueError("A municipality had no overlap with the raster grid.")
    return np.asarray(rows), np.asarray(cols), np.asarray(areas)


def values_from_raster(data: np.ndarray, weights: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]]) -> pd.Series:
    """Calculate a fractionally area-weighted mean for each municipality."""
    values = {}
    for municipality_id, (rows, cols, areas) in weights.items():
        selected = data[rows, cols]
        valid = np.isfinite(selected)
        values[municipality_id] = np.average(selected[valid], weights=areas[valid]) if valid.any() else np.nan
    return pd.Series(values, name="value")


def make_crosswalk() -> tuple[gpd.GeoDataFrame, str]:
    polygons = gpd.read_file(MUNIS)
    if polygons.crs is None:
        polygons = polygons.set_crs("EPSG:4326")
    raw_count = len(polygons)
    lakes = polygons[polygons["id"].astype(str).eq("0")]
    belize = polygons[polygons["Departamento"].map(normalize_text).eq("BELICE")]
    municipal = polygons.loc[~polygons.index.isin(lakes.index) & ~polygons.index.isin(belize.index)].copy()
    invalid_before_repair = municipal.loc[~municipal.geometry.is_valid, ["id", "Municipio"]].copy()
    # Repair the supplied invalid polygon in memory only; raw TopoJSON remains untouched.
    if not invalid_before_repair.empty:
        municipal["geometry"] = municipal.geometry.map(make_valid)
    municipal["municipality_id"] = pd.to_numeric(municipal["id"], errors="raise").astype(int)
    if len(municipal) != 340:
        raise AssertionError(f"Expected 340 analytical Guatemala municipalities; found {len(municipal)}.")
    if municipal["municipality_id"].duplicated().any() or not municipal.geometry.is_valid.all():
        raise AssertionError("Municipality IDs must be unique and analytical geometries valid.")

    corridor = pd.read_stata(CORRIDOR_DTA, columns=["ine_code", "corredor_seco_160"])
    corridor_codes = set(pd.to_numeric(corridor.loc[corridor["corredor_seco_160"] == 1, "ine_code"], errors="coerce").dropna().astype(int))
    unmatched = pd.read_csv(CORRIDOR_UNMATCHED)
    corridor_codes.update(pd.to_numeric(unmatched["ine_code"], errors="raise").astype(int).tolist())
    municipal["corredor_seco_160"] = municipal["municipality_id"].isin(corridor_codes).astype(int)
    if municipal["corredor_seco_160"].sum() != 160:
        raise AssertionError("The SESAN baseline must contain exactly 160 municipalities.")

    municipal = municipal.rename(columns={"Departamento": "department", "Municipio": "municipality"})
    municipal["geometry_reference"] = "munis.json / properties.id (TopoJSON municipality polygon)"
    ordered = municipal[["municipality_id", "department", "municipality", "corredor_seco_160", "geometry_reference", "geometry"]].copy()
    ordered = ordered.sort_values("municipality_id").reset_index(drop=True)
    write_csv(ordered.drop(columns="geometry"), DERIVED / "municipality_crosswalk.csv")
    discrepancy = (
        f"The supplied TopoJSON has {raw_count} features: 340 Guatemala municipality polygons, "
        f"{len(lakes)} lake features with id 0 ({', '.join(lakes['Municipio'])}), and {len(belize)} Belize feature. "
        "The 340 non-lake, non-Belize polygons constitute the analytical set; none were silently dropped."
    )
    if not invalid_before_repair.empty:
        discrepancy += f" The supplied {', '.join(invalid_before_repair['Municipio'])} polygon (id {', '.join(invalid_before_repair['id'].astype(str))}) was invalid and was repaired in memory with Shapely make_valid for calculations only."
    return ordered, discrepancy


def build_chirps(crosswalk: gpd.GeoDataFrame) -> pd.DataFrame:
    # May--July are official CHIRPS v3 final monthly files from CHC's
    # /monthly/latam/tifs/ endpoint. August is the supplied final monthly
    # raster. Keeping these inputs distinct from original preliminary pentads
    # prevents an accidental mixed-status seasonal total.
    monthly = [
        CHIRPS_2026_FINAL_MONTHLY / f"chirps-v3.0.2026.{month:02d}.tif"
        for month in range(5, 9)
    ]
    missing = [str(path) for path in monthly if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required final CHIRPS monthly input(s): " + "; ".join(missing))

    national_outline = crosswalk.geometry.union_all()
    clipped_arrays, clip_transform, clip_profile = [], None, None
    for month in monthly:
        with rasterio.open(month) as source:
            clipped, transform = rio_mask(source, [mapping(national_outline)], crop=True, filled=False)
            array = clipped[0].filled(np.nan).astype("float64")
            if clip_transform is None:
                clip_transform, clip_profile = transform, source.profile.copy()
            elif array.shape != clipped_arrays[0].shape or not np.allclose(tuple(transform), tuple(clip_transform)):
                raise AssertionError("Clipped final CHIRPS monthly rasters are not grid-aligned; resampling was not permitted.")
            clipped_arrays.append(array)
    stack = np.stack(clipped_arrays)
    cumulative = np.where(np.isfinite(stack).any(axis=0), np.nansum(stack, axis=0), np.nan)
    profile = clip_profile.copy()
    profile.update(driver="GTiff", height=cumulative.shape[0], width=cumulative.shape[1], transform=clip_transform,
                   count=1, dtype="float32", nodata=-9999.0, compress="lzw")
    with rasterio.open(DERIVED / "chirps_2026_may_aug_cumulative.tif", "w", **profile) as destination:
        destination.write(np.where(np.isfinite(cumulative), cumulative, -9999.0).astype("float32"), 1)

    weights_2026 = {
        int(row.municipality_id): municipal_pixel_weights(clip_transform, cumulative.shape[1], cumulative.shape[0], row.geometry)
        for row in crosswalk.itertuples()
    }
    rain_2026 = values_from_raster(cumulative, weights_2026).rename("rain_2026_may_aug_mm")

    with rasterio.open(CHIRPS_HIST) as source:
        if source.count != 45:
            raise AssertionError("Historical CHIRPS file must contain 45 annual May--August bands (1981--2025).")
        years = [int(description.split("_")[0]) for description in source.descriptions]
        if years != list(range(1981, 2026)):
            raise AssertionError("Historical CHIRPS bands do not describe 1981--2025 in sequence.")
        history = source.read().astype("float64")
        weights_hist = {
            int(row.municipality_id): municipal_pixel_weights(source.transform, source.width, source.height, row.geometry)
            for row in crosswalk.itertuples()
        }
    historical_rows = []
    for municipality_id, (rows, cols, areas) in weights_hist.items():
        annual_values = []
        for band in history:
            selected = band[rows, cols]
            valid = np.isfinite(selected)
            annual_values.append(float(np.average(selected[valid], weights=areas[valid])))
        annual = np.asarray(annual_values)
        historical_rows.append({
            "municipality_id": municipality_id,
            "historical_mean_may_aug_mm": annual.mean(),
            "historical_median_may_aug_mm": np.median(annual),
            "historical_sd_may_aug_mm": annual.std(ddof=1),
            "historical_min_may_aug_mm": annual.min(),
            "historical_max_may_aug_mm": annual.max(),
            "historical_p10_may_aug_mm": np.percentile(annual, 10),
            "historical_p20_may_aug_mm": np.percentile(annual, 20),
            "historical_p80_may_aug_mm": np.percentile(annual, 80),
            "historical_p90_may_aug_mm": np.percentile(annual, 90),
            "_annual_values": annual,
        })
    historical = pd.DataFrame(historical_rows)
    write_csv(historical.drop(columns="_annual_values"), DERIVED / "chirps_historical_municipality.csv")

    results = crosswalk.drop(columns="geometry").merge(historical.drop(columns="_annual_values"), on="municipality_id", validate="one_to_one")
    results = results.merge(rain_2026.rename_axis("municipality_id").reset_index(), on="municipality_id", validate="one_to_one")
    results["rainfall_anomaly_pct_vs_historical_median"] = 100 * (
        (results["rain_2026_may_aug_mm"] - results["historical_median_may_aug_mm"])
        / results["historical_median_may_aug_mm"]
    )
    historical_lookup = historical.set_index("municipality_id")["_annual_values"].to_dict()
    results["rainfall_historical_percentile"] = [
        100 * np.mean(historical_lookup[row.municipality_id] <= row.rain_2026_may_aug_mm)
        for row in results.itertuples()
    ]
    results["rainfall_z_score_vs_1981_2025"] = (
        (results["rain_2026_may_aug_mm"] - results["historical_mean_may_aug_mm"])
        / results["historical_sd_may_aug_mm"]
    )
    results["chirps_2026_status"] = "FINAL"
    results = results.drop(columns="geometry_reference")
    write_csv(results, DERIVED / "chirps_2026_municipality.csv")
    return results


def build_fao_asis(crosswalk: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # The supplied file is a Latin-1 CSV extract.  There is no FAO GeoTIFF in the existing source library.
    asis = pd.read_csv(FAO_ASIS, encoding="latin1")
    asis["Date"] = pd.to_datetime(asis["Date"])
    asis["Year_clean"] = pd.to_numeric(asis["Year"], errors="coerce")
    asis["Data"] = pd.to_numeric(asis["Data"], errors="coerce")
    latest_date = asis["Date"].max()
    latest = asis.loc[asis["Date"].eq(latest_date)].copy()
    if latest["Province"].nunique() != 22:
        raise AssertionError("Latest supplied FAO ASIS date must cover 22 departments.")
    latest["department_key"] = latest["Province"].map(normalize_text)
    value_by_department = latest.set_index("department_key")["Data"].to_dict()
    output = crosswalk.drop(columns="geometry").copy()
    output["asis_value"] = output["department"].map(normalize_text).map(value_by_department)
    output["asis_period"] = f"{latest_date.date().isoformat()} (August dekad 3; latest supplied record)"
    output["asis_interpretation"] = (
        "Parent-department ASI only: percent of Crop Area at department scale with mean VHI below 35. "
        "It is not a municipality-specific value and not percentage yield loss."
    )
    output["asis_geographic_aggregation"] = "department (repeated by municipality for merge convenience; not municipal ASI)"
    output["asis_source_format"] = "supplied FAO-ASIS CSV extract; no GeoTIFF supplied"
    output = output.drop(columns="geometry_reference")
    write_csv(output, DERIVED / "fao_asis_2026_municipality.csv")
    return output, latest


def build_maga_prices() -> tuple[pd.DataFrame, pd.Series]:
    prices = pd.read_csv(MAGA)
    series = prices.loc[
        (prices["Actor"] == "Mayorista")
        & (prices["Mercado"] == "La Terminal")
        & (prices["Producto"] == "Maíz blanco, de primera")
        & (prices["Medida"] == "Quintal")
        & (prices["Moneda"] == "GTQ")
    ].copy()
    series["date"] = pd.to_datetime(series["Fecha"])
    series["price_gtq_per_quintal"] = pd.to_numeric(series["Precio"], errors="coerce")
    series = series.dropna(subset=["price_gtq_per_quintal"])
    series["year"] = series["date"].dt.year
    series["month"] = series["date"].dt.month
    monthly = (
        series.groupby(["year", "month"], as_index=False)
        .agg(
            monthly_mean_price_gtq_per_quintal=("price_gtq_per_quintal", "mean"),
            daily_observations=("price_gtq_per_quintal", "size"),
            first_observation=("date", "min"),
            last_observation=("date", "max"),
        )
        .sort_values(["year", "month"])
    )
    historical = monthly.loc[monthly["year"] < 2026]
    seasonal = historical.groupby("month")["monthly_mean_price_gtq_per_quintal"].agg(
        historical_seasonal_median_gtq_per_quintal="median",
        historical_seasonal_p25_gtq_per_quintal=lambda value: value.quantile(0.25),
        historical_seasonal_p75_gtq_per_quintal=lambda value: value.quantile(0.75),
    ).reset_index()
    monthly = monthly.merge(seasonal, on="month", validate="many_to_one")
    monthly["pct_deviation_vs_historical_seasonal_median"] = 100 * (
        (monthly["monthly_mean_price_gtq_per_quintal"] - monthly["historical_seasonal_median_gtq_per_quintal"])
        / monthly["historical_seasonal_median_gtq_per_quintal"]
    )
    monthly["series_description"] = "Wholesale, La Terminal; white maize, first quality; GTQ per quintal"
    monthly["geographic_interpretation"] = "National/central-market benchmark only; not municipality retail price"
    write_csv(monthly, DERIVED / "maga_maize_prices_clean.csv")
    august_2026 = monthly.loc[(monthly["year"] == 2026) & (monthly["month"] == 8)]
    if len(august_2026) != 1:
        raise AssertionError("A usable August 2026 MAGA white-maize series is required for the scenario.")
    return monthly, august_2026.iloc[0]


def build_enigh_summary() -> tuple[pd.DataFrame, dict[str, float | str]]:
    households = pd.read_excel(ENIGH_DIR / "consolidado-hogares.xlsx", sheet_name="CONSOLIDADO HOGARES")
    rural = households.loc[households["AREA"].eq(2)].copy()
    stats_rows = []
    measures = {
        "monthly_total_household_expenditure_gtq": ("gas_total", "Gasto total; treated as the supplied consolidated monthly household total"),
        "monthly_food_expenditure_gtq": ("alimentos", "Gasto en alimentos; treated as the supplied consolidated monthly household total"),
        "household_size_persons": ("B1PPB04", "Número de integrantes en el hogar"),
        "household_income_gtq": ("ing_total", "Ingreso total; supplied consolidated household total"),
        "agricultural_income_gtq": ("gan_agro", "Ganancia agropecuaria; supplied consolidated household total"),
    }
    for measure, (column, label) in measures.items():
        summary = weighted_summary(pd.to_numeric(rural[column], errors="coerce"), pd.to_numeric(rural["PONDERADOR"], errors="coerce"))
        stats_rows.append({
            "domain": "Guatemala rural (AREA = 2)", "measure": measure, "source_variable": column,
            "official_dictionary_label": label, **summary,
        })

    # The dictionary identifies expenditure and the maize item code, but contains no quantity field.
    daily = pd.read_excel(ENIGH_DIR / "enigh_gastosdiarios.xlsx", sheet_name="ENIGH_GastosDiarios_20232710")
    id_columns = ["DEPTO", "MUPIO", "HOGAR"]
    rural_ids = rural[id_columns + ["PONDERADOR"]].copy()
    day_counts = daily.groupby(id_columns)["B2P01B03"].nunique().rename("diary_days").reset_index()
    white_maize = daily.loc[daily["B2P01B07"].astype(str).str.strip().eq("01.1.1.1.6.1")].copy()
    white_maize["expense"] = pd.to_numeric(white_maize["B2P01B12"], errors="coerce").fillna(0)
    white_maize = white_maize.groupby(id_columns, as_index=False)["expense"].sum().rename(columns={"expense": "white_maize_diary_expense_gtq"})
    maize_households = rural_ids.merge(day_counts, on=id_columns, how="left", validate="one_to_one")
    maize_households = maize_households.merge(white_maize, on=id_columns, how="left", validate="one_to_one")
    maize_households["white_maize_diary_expense_gtq"] = maize_households["white_maize_diary_expense_gtq"].fillna(0)
    maize_households["diary_days"] = maize_households["diary_days"].fillna(7)
    maize_households["estimated_monthly_white_maize_expenditure_gtq"] = (
        maize_households["white_maize_diary_expense_gtq"] * 30.4375 / maize_households["diary_days"]
    )
    maize_stats = weighted_summary(
        maize_households["estimated_monthly_white_maize_expenditure_gtq"], maize_households["PONDERADOR"]
    )
    stats_rows.append({
        "domain": "Guatemala rural (AREA = 2)",
        "measure": "estimated_monthly_purchased_white_maize_expenditure_gtq",
        "source_variable": "B2P01B07 = 01.1.1.1.6.1; B2P01B12",
        "official_dictionary_label": "Maíz blanco; Gasto en quetzales y centavos. Seven-day diary total annualized to 30.4375 days.",
        **maize_stats,
    })
    summary = pd.DataFrame(stats_rows)
    write_csv(summary, DERIVED / "enigh_household_summary.csv")
    total_expenditure_median = summary.loc[
        summary["measure"].eq("monthly_total_household_expenditure_gtq"), "weighted_median"
    ].iloc[0]
    maize_median = maize_stats["weighted_median"]
    if maize_median > 0:
        q_value, q_basis = maize_median, "weighted median of rural estimated monthly purchased white-maize expenditure"
    else:
        q_value, q_basis = maize_stats["weighted_mean"], "weighted mean of rural estimated monthly purchased white-maize expenditure (median was zero)"
    return summary, {
        "q_value": float(q_value),
        "q_basis": q_basis,
        "normal_expenditure": float(total_expenditure_median),
        "rural_households": int(len(rural)),
        "maize_positive_households": int((maize_households["estimated_monthly_white_maize_expenditure_gtq"] > 0).sum()),
        "diary_days_min": int(maize_households["diary_days"].min()),
        "diary_days_max": int(maize_households["diary_days"].max()),
    }


def build_budget(august_price: pd.Series, enigh: dict[str, float | str]) -> pd.DataFrame:
    p0 = float(august_price["historical_seasonal_median_gtq_per_quintal"])
    p1 = float(august_price["monthly_mean_price_gtq_per_quintal"])
    q_value = float(enigh["q_value"])
    normal_expenditure = float(enigh["normal_expenditure"])
    price_ratio = p1 / p0
    transfer_amount = np.nan  # Program materials in the workspace describe a TMC but supply no amount.
    scenarios = pd.DataFrame([
        {"scenario": "low", "own_production_share_s": 0.25, "unavailable_own_production_fraction_L": 0.25},
        {"scenario": "central", "own_production_share_s": 0.50, "unavailable_own_production_fraction_L": 0.50},
        {"scenario": "high", "own_production_share_s": 0.75, "unavailable_own_production_fraction_L": 0.75},
    ])
    # Expenditure-basis analogue: q is normal purchased expenditure = Q(1-s)p0.
    # Current cash cost is Q(1-s+sL)p1.  Neither s nor L is observed.
    scenarios["additional_monthly_maize_cash_requirement_gtq"] = q_value * (
        ((1 - scenarios["own_production_share_s"] + scenarios["own_production_share_s"] * scenarios["unavailable_own_production_fraction_L"])
         / (1 - scenarios["own_production_share_s"])) * price_ratio - 1
    )
    scenarios["additional_cash_requirement_pct_normal_household_expenditure"] = (
        100 * scenarios["additional_monthly_maize_cash_requirement_gtq"] / normal_expenditure
    )
    scenarios["additional_cash_requirement_pct_program_transfer"] = np.nan
    scenarios["price_p0_historical_seasonal_median_gtq_per_quintal"] = p0
    scenarios["price_p1_august_2026_gtq_per_quintal"] = p1
    scenarios["price_ratio_p1_over_p0"] = price_ratio
    scenarios["q_expenditure_basis_gtq_per_month"] = q_value
    scenarios["normal_household_expenditure_gtq_per_month"] = normal_expenditure
    scenarios["program_transfer_amount_gtq"] = transfer_amount
    scenarios["geographic_scope"] = "All three sites: national rural ENIGH basis and national wholesale MAGA benchmark"
    scenarios["interpretation"] = (
        "Sensitivity scenario, not measured crop loss and not a causal drought effect. Transfer percentage is unavailable because no amount was supplied."
    )
    write_csv(scenarios, TABLES / "table_budget_scenarios.csv")
    parameters = pd.DataFrame([
        {"parameter": "q", "value": q_value, "unit": "GTQ per household-month", "source": "ENIGH 2021-2022, rural households, white-maize diary", "observed_or_assumed": "observed", "notes": str(enigh["q_basis"])},
        {"parameter": "s_low / s_central / s_high", "value": "0.25 / 0.50 / 0.75", "unit": "share", "source": "No defensible own-production share in supplied ENIGH files", "observed_or_assumed": "assumed", "notes": "Sensitivity range; not estimated from ASIS."},
        {"parameter": "L_low / L_central / L_high", "value": "0.25 / 0.50 / 0.75", "unit": "share", "source": "No crop-loss estimate in supplied inputs", "observed_or_assumed": "assumed", "notes": "Sensitivity range; deliberately not inferred from ASIS."},
        {"parameter": "p0", "value": p0, "unit": "GTQ per quintal", "source": "MAGA: La Terminal wholesale white maize, first quality; August monthly medians, 2012-2025", "observed_or_assumed": "observed", "notes": "Historical seasonal benchmark."},
        {"parameter": "p1", "value": p1, "unit": "GTQ per quintal", "source": "MAGA: La Terminal wholesale white maize, first quality; August 2026 daily observations through 2026-08-21", "observed_or_assumed": "observed", "notes": "Contemporaneous wholesale benchmark, not local retail price."},
        {"parameter": "p1 / p0", "value": price_ratio, "unit": "ratio", "source": "Calculated from MAGA series", "observed_or_assumed": "calculated", "notes": "Applied as a price-index proxy to the ENIGH expenditure basis."},
        {"parameter": "normal household expenditure", "value": normal_expenditure, "unit": "GTQ per household-month", "source": "ENIGH 2021-2022 consolidated rural households, gas_total", "observed_or_assumed": "observed", "notes": "Weighted median; data dictionary calls gas_total Gasto total."},
        {"parameter": "T", "value": "", "unit": "GTQ per transfer", "source": "Existing Beca documentation", "observed_or_assumed": "unavailable", "notes": "Documentation confirms a conditional transfer but provides no amount; transfer ratios are intentionally blank."},
    ])
    write_csv(parameters, TABLES / "table_budget_parameters.csv")
    return scenarios


def site_table(chirps: pd.DataFrame, asis: pd.DataFrame) -> pd.DataFrame:
    joined = chirps.merge(
        asis[["municipality_id", "asis_value", "asis_period", "asis_interpretation", "asis_geographic_aggregation"]],
        on="municipality_id", validate="one_to_one"
    )
    sites = pd.DataFrame(SITE_ORDER, columns=["municipality", "department"])
    sites = sites.merge(joined, on=["municipality", "department"], validate="one_to_one")
    output = sites[[
        "municipality_id", "department", "municipality", "corredor_seco_160", "historical_median_may_aug_mm",
        "rain_2026_may_aug_mm", "rainfall_anomaly_pct_vs_historical_median", "rainfall_historical_percentile",
        "asis_value", "asis_period", "asis_geographic_aggregation", "asis_interpretation",
    ]]
    write_csv(output, TABLES / "table_three_sites_drought.csv")
    return output


def add_figure_note(figure, text: str) -> None:
    figure.text(0.01, 0.012, text, ha="left", va="bottom", fontsize=7.5, wrap=True)


def site_points(crosswalk: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    points = crosswalk.to_crs("EPSG:6933").copy()
    points["geometry"] = points.centroid
    return points.to_crs("EPSG:4326")


def figures(crosswalk: gpd.GeoDataFrame, chirps: pd.DataFrame, asis: pd.DataFrame,
            sites: pd.DataFrame, scenarios: pd.DataFrame, monthly_prices: pd.DataFrame) -> None:
    geometry = crosswalk.merge(chirps[["municipality_id", "rainfall_historical_percentile"]], on="municipality_id")
    points = site_points(crosswalk)
    site_gdf = points.merge(pd.DataFrame(SITE_ORDER, columns=["municipality", "department"]), on=["municipality", "department"])

    # Figure 1
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.7))
    base_color = "#e8e8e8"
    geometry.plot(ax=axes[0], color=base_color, edgecolor="white", linewidth=0.2)
    geometry.loc[geometry["corredor_seco_160"].eq(1)].plot(ax=axes[0], color="#d08c60", edgecolor="white", linewidth=0.2)
    geometry.loc[geometry["corredor_seco_160"].eq(1)].boundary.plot(ax=axes[0], color="#8d4f2f", linewidth=0.35)
    site_gdf.plot(ax=axes[0], color="#152238", marker="o", markersize=25, zorder=3)
    for point in site_gdf.itertuples():
        axes[0].annotate(point.municipality, (point.geometry.x, point.geometry.y), xytext=(3, 3), textcoords="offset points", fontsize=7)
    axes[0].set_title("A. SESAN Corredor Seco Ampliado (160 municipalities)", fontsize=10)
    geometry.plot(ax=axes[1], column="rainfall_historical_percentile", cmap="YlOrBr", vmin=0, vmax=100, edgecolor="white", linewidth=0.18)
    geometry.loc[geometry["corredor_seco_160"].eq(1)].boundary.plot(ax=axes[1], color="#374151", linewidth=0.32)
    site_gdf.plot(ax=axes[1], color="#152238", marker="o", markersize=25, zorder=3)
    for point in site_gdf.itertuples():
        axes[1].annotate(point.municipality, (point.geometry.x, point.geometry.y), xytext=(3, 3), textcoords="offset points", fontsize=7)
    axes[1].set_title("B. CHIRPS 2026 May--August rainfall percentile", fontsize=10)
    colourbar = fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0, 100), cmap="YlOrBr"), ax=axes[1], fraction=0.045, pad=0.02)
    colourbar.set_label("Percentile within municipal 1981--2025 distribution\n(lower = drier)", fontsize=7)
    for axis in axes:
        axis.set_axis_off()
    fig.legend(handles=[Line2D([0], [0], color="#8d4f2f", lw=1, label="SESAN 160 outline"),
                        Line2D([0], [0], marker="o", color="w", markerfacecolor="#152238", markersize=5, label="Field site")],
               loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, 0.06))
    add_figure_note(fig, "Data: supplied TopoJSON municipality polygons; SESAN 160 indicator embedded in existing MSPAS analytic file; CHIRPS v3 final monthly inputs. Geographic aggregation: municipality. Exact period: 1 May--31 August 2026. Unit in panel B: empirical percentile of cumulative mm against 1981--2025. 2026 CHIRPS is FINAL.")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(FIGURES / "fig01_corridor_vs_rainfall_2026.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 2
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.6), sharey=True)
    for axis, row in zip(axes, sites.itertuples()):
        values = [row.historical_median_may_aug_mm, row.rain_2026_may_aug_mm]
        bars = axis.bar([0, 1], values, color=["#9ca3af", "#2a6f97"], width=0.6)
        axis.set_xticks([0, 1], ["1981--2025\nmedian", "2026\nfinal"])
        axis.set_title(f"{row.municipality}, {row.department}", fontsize=10)
        for bar in bars:
            axis.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{bar.get_height():.0f}", ha="center", va="bottom", fontsize=8)
        axis.text(0.5, 0.89, f"Anomaly: {row.rainfall_anomaly_pct_vs_historical_median:+.1f}%\nPercentile: {row.rainfall_historical_percentile:.1f}", transform=axis.transAxes, ha="center", va="top", fontsize=9,
                  bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#d1d5db"))
        axis.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Cumulative precipitation (mm)")
    add_figure_note(fig, "Data: CHIRPS v3 municipality area-weighted mean. Exact period: 1 May--31 August each year; 1981--2025 historical reference. Unit: cumulative millimetres; annotations show standardized percentage anomaly and empirical percentile (lower = drier). 2026 is FINAL.")
    fig.tight_layout(rect=(0, 0.10, 1, 1))
    fig.savefig(FIGURES / "fig02_three_site_rainfall.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 3. The CSV supports only department-level ASI; display that constraint explicitly.
    scatter = chirps.merge(asis[["municipality_id", "asis_value"]], on="municipality_id", validate="one_to_one")
    scatter_sites = sites[["municipality_id", "municipality", "department"]].merge(scatter[["municipality_id", "rainfall_historical_percentile", "asis_value"]], on="municipality_id", validate="one_to_one")
    fig, axis = plt.subplots(figsize=(8.1, 5.2))
    axis.scatter(scatter["rainfall_historical_percentile"], scatter["asis_value"], s=10, alpha=0.18, color="#6b7280", linewidths=0)
    colours = {"Olopa": "#b22222", "Chahal": "#1f77b4", "Patzité": "#4d7c0f"}
    for row in scatter_sites.itertuples():
        axis.scatter(row.rainfall_historical_percentile, row.asis_value, s=52, color=colours[row.municipality], edgecolor="white", linewidth=0.6, zorder=3)
        axis.annotate(row.municipality, (row.rainfall_historical_percentile, row.asis_value), xytext=(5, 4), textcoords="offset points", fontsize=9)
    axis.set_xlabel("CHIRPS 2026 May--August historical rainfall percentile (municipality; lower = drier)")
    axis.set_ylabel("FAO ASI: % crop area with mean VHI < 35\n(parent department, not municipality)")
    axis.set_title("Meteorological rainfall versus available agricultural-stress indicator", fontsize=11)
    axis.grid(alpha=0.2)
    add_figure_note(fig, "Data: CHIRPS v3 final municipality rainfall percentile, 1 May--31 August 2026, against 1981--2025; supplied FAO-ASIS CSV, 2026-08-21 (August dekad 3). Unit: percentile and percent crop area with mean VHI below 35. Each faint municipality inherits only its parent department's ASI: this is a geographic-context display, not a municipality-level relationship or causal estimate. 2026 CHIRPS is FINAL.")
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(FIGURES / "fig03_rainfall_vs_asis.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 4
    fig, axis = plt.subplots(figsize=(8.3, 5.0))
    bars = axis.bar(scenarios["scenario"].str.title(), scenarios["additional_monthly_maize_cash_requirement_gtq"], color=["#9ecae1", "#3182bd", "#08519c"], width=0.62)
    for bar, row in zip(bars, scenarios.itertuples()):
        axis.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"Q{bar.get_height():.0f}\n({row.additional_cash_requirement_pct_normal_household_expenditure:.1f}% of normal expenditure)", ha="center", va="bottom", fontsize=8)
    axis.set_ylabel("Modeled monthly change in maize cash requirement (GTQ)")
    axis.set_title("Household liquidity sensitivity: expenditure-basis scenarios", fontsize=11)
    axis.grid(axis="y", alpha=0.2)
    add_figure_note(fig, "Data: ENIGH 2021--2022, Guatemala rural households (weighted expenditure basis); MAGA wholesale La Terminal white-maize price, August 2026 compared with 2012--2025 August seasonal median. Unit: GTQ per household-month; bars are scenario-based, not measured drought effects. Own-production share s and unavailable fraction L are assumptions; no crop loss is inferred from ASI. Transfer amount T was not supplied, so a transfer-share estimate is not shown.")
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    fig.savefig(FIGURES / "fig04_transfer_absorption.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Figure 5: justified single market / unit / transaction-level series.
    historic = monthly_prices.loc[monthly_prices["year"] < 2026]
    current = monthly_prices.loc[monthly_prices["year"] == 2026]
    seasonal = historic.groupby("month")["monthly_mean_price_gtq_per_quintal"].agg(median="median", p25=lambda x: x.quantile(.25), p75=lambda x: x.quantile(.75)).reset_index()
    fig, axis = plt.subplots(figsize=(8.5, 4.8))
    axis.fill_between(seasonal["month"], seasonal["p25"], seasonal["p75"], color="#cbd5e1", label="2012--2025 seasonal interquartile range")
    axis.plot(seasonal["month"], seasonal["median"], color="#64748b", lw=2, label="2012--2025 seasonal median")
    axis.plot(current["month"], current["monthly_mean_price_gtq_per_quintal"], color="#b45309", marker="o", lw=2.2, label="2026 monthly mean")
    axis.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    axis.set_xlim(0.7, 12.3)
    axis.set_ylabel("GTQ per quintal")
    axis.set_title("Wholesale white-maize price benchmark: La Terminal", fontsize=11)
    axis.grid(axis="y", alpha=0.2)
    axis.legend(fontsize=8, frameon=False)
    add_figure_note(fig, "Data: MAGA daily prices aggregated to monthly means. Geographic aggregation: La Terminal wholesale market, Guatemala City; not a municipality or retail price. Product/unit: white maize, first quality, GTQ per quintal. Exact 2026 coverage: January--21 August 2026. It describes contemporaneous household purchasing conditions; it does not attribute price changes to drought.")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(FIGURES / "fig05_maize_prices.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def documentation(crosswalk_discrepancy: str, fao_latest: pd.DataFrame, sites: pd.DataFrame,
                  scenarios: pd.DataFrame, enigh: dict[str, float | str]) -> None:
    latest_date = pd.to_datetime(fao_latest["Date"]).max().date().isoformat()
    fao_notes = f"""# FAO ASIS notes

## What is actually supplied

The existing input is `ASI_Dekad_Season1_data.csv`, a FAO-ASIS CSV extract. No Guatemala FAO GeoTIFF was found in the supplied source library, so GeoTIFF metadata, nominal 1-km resolution, and a municipal zonal statistic cannot be independently inspected or calculated. This is a material discrepancy from the requested input description.

The CSV fields identify `Agricultural Stress Index (ASI)`, `Land_Type = Crop Area`, and the unit `% of area with Mean VHI below 35`. The latest supplied record is **{latest_date}**, August dekad 3, rather than the expected approximately August dekad 1. The extract has no `Season` field, so its Season 1 label is inferred only from its filename and cannot be independently verified from record metadata.

## Interpretation used here

ASI is the percentage of **crop area at the file's reported geographic level** whose mean Vegetation Health Index (VHI) is below 35. It signals drought-related vegetation stress under FAO's methodology. It is **not** a percentage yield loss, crop loss, or household-income loss.

The supplied file is department-level (22 provinces). For the requested municipality rows, `asis_value` is the latest parent-department value repeated solely to retain a tidy municipality merge. It is always labelled department-level and must not be interpreted as an Olopa-, Chahal-, or Patzité-specific measurement.
"""
    (DOCS / "fao_asis_notes.md").write_text(fao_notes, encoding="utf-8")

    methods = f"""# Methods notes

## Analytical scope

This is a descriptive consistency check, not a test of a causal drought mechanism. The evidentiary sequence is meteorological rainfall (CHIRPS), observed vegetation stress (FAO ASIS), contemporaneous maize prices (MAGA), and the scale of a rural household budget (ENIGH). It does not establish that drought changed income, prices, transfer use, or asset investment.

## Municipality crosswalk

The analytical identifier is the existing TopoJSON `properties.id` municipality code (`municipality_id`). It is joined by code wherever one is supplied. The SESAN 160 indicator comes from the existing MSPAS project analytic file: 158 coded records plus two documented unmatched SESAN municipalities (La Blanca 1230 and San José La Máquina 1021), yielding exactly 160 codes. {crosswalk_discrepancy}

## CHIRPS

The historical GeoTIFF has 45 bands labelled 1981--2025 and represents each year's 1 May--31 August cumulative rainfall. The 2026 seasonal total combines four official final CHIRPS v3 monthly rasters (May, June, July, and August). Each monthly raster is clipped in memory to the Guatemala outline before pixelwise summation; no resampling occurs. Municipal values are fractional-pixel, equal-area (EPSG:6933) area-weighted means of cumulative millimetres. They are never sums across pixels.

The standardized statistic is the empirical percentile: share of the 45 historical municipal totals less than or equal to 2026. Low values are unusually dry. All 2026 CHIRPS results are labelled **FINAL**.

## FAO ASIS

See [fao_asis_notes.md](fao_asis_notes.md). The valid supplied ASIS geography is department, not municipality. The Figure 3 dot cloud repeats a parent department value by municipality only to show the geographical mismatch; it is not a municipal stress relationship and has no fitted line.

## MAGA maize price

The only clean long 2026 series selected is wholesale (`Actor = Mayorista`) white maize, first quality, in `La Terminal`, GTQ per quintal. No wholesale/retail records or physical units are combined. It is a defensible national/central-market benchmark, but not a municipality-level or retail price. Monthly price is the mean of nonmissing daily quotes; the historical same-month benchmark is the median of monthly means in 2012--2025. The series describes contemporaneous purchasing conditions and does not attribute price changes to drought.

## ENIGH and budget exercise

Dictionary labels were read before use. Official `PONDERADOR` weights are used. `AREA = 2` defines rural households. The available documentation does not establish municipality or department inference, so results are national rural descriptive statistics, not municipality estimates. White maize uses documented item code `01.1.1.1.6.1` and diary expenditure field `B2P01B12`; the files contain no physical quantity field. The diary total is converted to a 30.4375-day expenditure basis. The central q basis is {enigh['q_basis']}.

The expenditure-basis analogue defines normal purchased expenditure as `q = Q(1-s)p0`, then calculates current cash cost as `Q(1-s+sL)p1`. Thus the change is `q * [((1-s+sL)/(1-s)) * (p1/p0) - 1]`. Own-produced share `s` and unavailable fraction `L` are transparent low/central/high assumptions; neither is inferred from FAO ASIS. No agricultural-earnings term is included. Program documentation confirms a conditional transfer but gives no amount `T`, therefore transfer-share cells are deliberately blank.
"""
    (DOCS / "methods_notes.md").write_text(methods, encoding="utf-8")

    latest_summary = fao_latest["Data"].agg(["min", "median", "max"])
    site_lines = "\n".join(
        f"- **{row.municipality}, {row.department}:** {row.rain_2026_may_aug_mm:.0f} mm; {row.rainfall_anomaly_pct_vs_historical_median:+.1f}% versus historical median; {row.rainfall_historical_percentile:.1f}th percentile; parent-department ASI {row.asis_value:.3f}% (not municipal)."
        for row in sites.itertuples()
    )
    brief = f"""# Results brief

## Read this first: CHIRPS and FAO ASIS

CHIRPS v3 shows how unusual cumulative **meteorological rainfall** was in each municipality over 1 May--31 August 2026 relative to that municipality's 1981--2025 distribution. Lower percentiles are drier; 2026 is final. FAO ASIS instead measures the share of crop area with mean VHI below 35, a vegetation-stress measure. It is not yield loss. The supplied FAO extract is only department-level, so it cannot establish municipality-specific agricultural stress.

{site_lines}

Across the 22 departments in the latest supplied ASIS extract ({latest_date}), values range from {latest_summary['min']:.3f}% to {latest_summary['max']:.3f}% (unweighted department median {latest_summary['median']:.3f}%). This is not a national crop-area-weighted ASI because the supplied extract has no crop-area weights.

## Budget exercise

The estimated maize cash changes in `table_budget_scenarios.csv` are sensitivity scenarios, not causal effects and not crop-loss estimates. They use a national rural ENIGH expenditure basis and a wholesale MAGA benchmark. No program transfer amount is in the supplied documentation, so no transfer-absorption percentage is calculated.
"""
    (DOCS / "results_brief.md").write_text(brief, encoding="utf-8")

    manifest = pd.DataFrame([
        {"data_id": "municipality_boundaries", "path": str(MUNIS.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "polygon", "coverage": "Guatemala; 340 municipalities plus documented non-municipal features", "finest_granularity": "municipality", "notes": "No copy made."},
        {"data_id": "sesan_corridor_160", "path": str(CORRIDOR_DTA.relative_to(WORKSPACE)), "status": "existing derived indicator, read-only", "unit_observation": "municipality", "coverage": "160 SESAN municipalities", "finest_granularity": "municipality", "notes": "Existing MSPAS build supplies indicator; two documented unmatched codes added from its companion CSV."},
        {"data_id": "chirps_historical", "path": str(CHIRPS_HIST.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "raster cell / annual band", "coverage": "Guatemala; 1981-2025 May-August", "finest_granularity": "0.05-degree raster", "notes": "No copy made."},
        {"data_id": "chirps_2026", "path": str(CHIRPS_2026.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "raster cell / month", "coverage": "May-August 2026; four official final monthly rasters", "finest_granularity": "0.05-degree raster", "notes": "No copy made."},
        {"data_id": "fao_asis", "path": str(FAO_ASIS.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "department x dekad", "coverage": "Guatemala; latest 2026-08-21", "finest_granularity": "department", "notes": "CSV supplied; no GeoTIFF present."},
        {"data_id": "maga_prices", "path": str(MAGA.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "market x product x date", "coverage": "2012-01-03 to 2026-08-21", "finest_granularity": "daily market observation", "notes": "No copy made."},
        {"data_id": "enigh", "path": str(ENIGH_DIR.relative_to(WORKSPACE)), "status": "source, read-only", "unit_observation": "household / diary record", "coverage": "ENIGH 2021-2022", "finest_granularity": "household", "notes": "No microdata copy made."},
        {"data_id": "dalton_outputs", "path": str(PROJECT.relative_to(WORKSPACE)), "status": "derived", "unit_observation": "municipality, month, or scenario", "coverage": "As documented in methods", "finest_granularity": "varies", "notes": "Derived outputs only; no raw input duplication."},
    ])
    write_csv(manifest, DOCS / "data_manifest.csv")


def main() -> None:
    crosswalk, discrepancy = make_crosswalk()
    chirps = build_chirps(crosswalk)
    asis, fao_latest = build_fao_asis(crosswalk)
    monthly_prices, august_price = build_maga_prices()
    _, enigh = build_enigh_summary()
    scenarios = build_budget(august_price, enigh)
    sites = site_table(chirps, asis)
    figures(crosswalk, chirps, asis, sites, scenarios, monthly_prices)
    documentation(discrepancy, fao_latest, sites, scenarios, enigh)
    print("Completed Dalton InsumoCampo outputs.")


if __name__ == "__main__":
    main()
