#!/usr/bin/env python3
"""Prepare derived, Stata-ready data for the Dalton Appendix.

This script reads immutable sources and existing derived CHIRPS/ASIS outputs. It
does not duplicate raw rasters or market files. It deliberately leaves graphing
to the companion Stata do-file, except for maps handled separately.
"""

from __future__ import annotations

import math
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import box
from shapely.ops import transform as shapely_transform


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
PLAYDATA = WORKSPACE / "02_projects" / "07_Playdata"
GUATEMALA = PLAYDATA / "02_Guatemala"
DERIVED = PROJECT / "derived"
APPENDIX = PROJECT / "figures" / "Appendix"
APP_TABLES = APPENDIX / "tables"
APP_DOCS = APPENDIX / "documentation"
MUNIS = GUATEMALA / "sources" / "JSON_Departamenos_Municipios_LugaresPoblados" / "Mapas-TopoJSON-Guatemala-main" / "munis.json"
HIST = PLAYDATA / "03_LatinAmerica" / "CHIRPS_Historical" / "GT_CHIRPSv3_MayAug_1981_2025.tif"


# The 2016 SESAN annex lists these municipalities in the eleven departments it
# calls the Corredor Seco. The document's prose says 66 municipalities but the
# transcribed annex has 67; we preserve the enumerated list and flag the
# discrepancy in documentation instead of inventing a 66th-rule.
LEGACY_2016_CORE: dict[str, list[str]] = {
    "Baja Verapaz": ["Cubulco", "El Chol", "Granados", "Rabinal", "Salamá", "San Jerónimo", "San Miguel Chicaj"],
    "Chimaltenango": ["San José Poaquil", "San Martín Jilotepeque", "Comalapa"],
    "Chiquimula": ["Chiquimula", "Ipala", "Jocotán", "Olopa", "Quezaltepeque", "San Jacinto", "San José La Arada", "San Juan Ermita"],
    "El Progreso": ["El Jícaro", "Guastatoya", "Morazán", "San Agustín Acasaguastlán", "San Antonio La Paz", "San Cristóbal Acasaguastlán", "Sanarate", "Sansare"],
    "Guatemala": ["Chuarrancho", "Palencia", "San José del Golfo", "San Pedro Ayampuc", "San Raymundo"],
    "Huehuetenango": ["Aguacatán", "Huehuetenango", "Malacatancito"],
    "Jalapa": ["Jalapa", "Mataquescuintla", "Monjas", "San Luis Jilotepeque", "San Manuel Chaparrón", "San Pedro Pinula"],
    "Jutiapa": ["Agua Blanca", "Asunción Mita", "Moyuta", "Santa Catarina Mita"],
    "Quiché": ["Canillá", "Chicamán", "Joyabaj", "Sacapulas", "San Andrés Sajcabajá", "San Antonio Ilotenango", "San Bartolomé Jocotenango", "San Pedro Jocopilas", "Zacualpa", "Uspantán"],
    "Totonicapán": ["Momostenango", "Santa Lucía La Reforma", "Santa María Chiquimula", "San Bartolo Aguas Calientes"],
    "Zacapa": ["Cabañas", "Estanzuela", "Gualán", "Huité", "Río Hondo", "San Diego", "Teculután", "Usumatlán", "Zacapa"],
}


def norm(value: object) -> str:
    text = unicodedata.normalize("NFD", str(value))
    return "".join(char for char in text if unicodedata.category(char) != "Mn").upper().strip()


def load_municipal_geometry() -> gpd.GeoDataFrame:
    geo = gpd.read_file(MUNIS)
    if geo.crs is None:
        geo = geo.set_crs("EPSG:4326")
    geo = geo.loc[~geo["id"].astype(str).eq("0") & ~geo["Departamento"].map(norm).eq("BELICE")].copy()
    geo.loc[~geo.geometry.is_valid, "geometry"] = geo.loc[~geo.geometry.is_valid, "geometry"].map(make_valid)
    geo["municipality_id"] = pd.to_numeric(geo["id"], errors="raise").astype(int)
    geo = geo.rename(columns={"Departamento": "department", "Municipio": "municipality"})
    if len(geo) != 340 or geo["municipality_id"].duplicated().any():
        raise ValueError("Expected exactly 340 unique analytical municipality polygons.")
    return geo[["municipality_id", "department", "municipality", "geometry"]].copy()


def pixel_weights(transform, width: int, height: int, geometry):
    """Fractional raster-cell area weights in an equal-area projection."""
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
            area = geometry_equal_area.intersection(
                shapely_transform(to_equal_area, box(x_left, y_bottom, x_right, y_top))
            ).area
            if area > 0:
                rows.append(row)
                cols.append(col)
                areas.append(area)
    if not areas:
        raise ValueError("No raster overlap for an analytical geometry.")
    return np.asarray(rows), np.asarray(cols), np.asarray(areas)


def annual_means(geometries: gpd.GeoDataFrame) -> tuple[pd.DataFrame, list[int]]:
    """Extract May--August annual rainfall for each supplied geometry."""
    with rasterio.open(HIST) as source:
        years = [int(label.split("_")[0]) for label in source.descriptions]
        if years != list(range(1981, 2026)):
            raise ValueError("Historical CHIRPS band descriptions are not 1981--2025.")
        cube = source.read().astype(float)
        if source.nodata is not None:
            cube[cube == source.nodata] = np.nan
        weights = {
            int(row.municipality_id): pixel_weights(source.transform, source.width, source.height, row.geometry)
            for row in geometries.itertuples()
        }
    records: list[dict[str, object]] = []
    details = geometries.drop(columns="geometry").set_index("municipality_id")
    for municipality_id, (rows, cols, areas) in weights.items():
        values = cube[:, rows, cols]
        annual = np.array([
            np.average(values[year][np.isfinite(values[year])], weights=areas[np.isfinite(values[year])])
            for year in range(cube.shape[0])
        ])
        for year, value in zip(years, annual, strict=True):
            record = {"municipality_id": municipality_id, "year": year, "rain_may_aug_mm": float(value)}
            record.update(details.loc[municipality_id].to_dict())
            records.append(record)
    return pd.DataFrame(records), years


def corridor_flags(geo: gpd.GeoDataFrame, chirps: pd.DataFrame) -> pd.DataFrame:
    listed = {(norm(department), norm(municipality)) for department, municipalities in LEGACY_2016_CORE.items() for municipality in municipalities}
    output = geo.drop(columns="geometry").merge(
        chirps[["municipality_id", "corredor_seco_160"]], on="municipality_id", validate="one_to_one"
    )
    output["legacy_sesan_core_2016"] = [
        int((norm(row.department), norm(row.municipality)) in listed) for row in output.itertuples()
    ]
    n_core = int(output["legacy_sesan_core_2016"].sum())
    if n_core != len(listed):
        unmatched = sorted(listed - {(norm(row.department), norm(row.municipality)) for row in output.itertuples()})
        raise ValueError(f"Could not match all legacy corridor municipalities: {unmatched}")
    output["sesan_expanded_only_2025"] = (
        output["corredor_seco_160"].eq(1) & output["legacy_sesan_core_2016"].eq(0)
    ).astype(int)
    output["corridor_map_class"] = np.select(
        [output["legacy_sesan_core_2016"].eq(1), output["sesan_expanded_only_2025"].eq(1)],
        ["Legacy SESAN core (solid outline)", "Current expanded-only (dashed outline)"],
        default="Outside these lists",
    )
    return output


def department_series(geo: gpd.GeoDataFrame, chirps: pd.DataFrame) -> pd.DataFrame:
    """Department statistics use annual totals from department-dissolved polygons."""
    dissolved = geo.dissolve(by="department", as_index=False)
    dissolved["municipality_id"] = np.arange(1, len(dissolved) + 1)
    annual, years = annual_means(dissolved[["municipality_id", "department", "geometry"]].assign(municipality=""))
    current = geo.merge(chirps[["municipality_id", "rain_2026_may_aug_mm"]], on="municipality_id").dissolve(by="department", aggfunc="first")
    # Do not average municipality precipitation: extract 2026 from the cumulative raster using the dissolved polygons.
    cumulative = DERIVED / "chirps_2026_may_aug_cumulative.tif"
    rows: list[dict[str, object]] = []
    with rasterio.open(cumulative) as source:
        image = source.read(1).astype(float)
        image[image == source.nodata] = np.nan
        for item in dissolved.itertuples():
            r, c, a = pixel_weights(source.transform, source.width, source.height, item.geometry)
            selected = image[r, c]
            valid = np.isfinite(selected)
            current_rain = float(np.average(selected[valid], weights=a[valid]))
            past = annual.loc[annual.department.eq(item.department), "rain_may_aug_mm"].to_numpy(float)
            rows.append({
                "department": item.department,
                "historical_mean_may_aug_mm": past.mean(),
                "historical_median_may_aug_mm": np.median(past),
                "historical_sd_may_aug_mm": past.std(ddof=1),
                "rain_2026_may_aug_mm": current_rain,
                "rainfall_historical_percentile": 100 * np.mean(past <= current_rain),
                "rainfall_z_score_vs_1981_2025": (current_rain - past.mean()) / past.std(ddof=1),
            })
    result = pd.DataFrame(rows).sort_values("rainfall_z_score_vs_1981_2025").reset_index(drop=True)
    result["z_rank"] = np.arange(1, len(result) + 1)
    return result


def write_documentation(flags: pd.DataFrame) -> None:
    legacy_n = int(flags["legacy_sesan_core_2016"].sum())
    expanded_n = int(flags["corredor_seco_160"].sum())
    expanded_only_n = int(flags["sesan_expanded_only_2025"].sum())
    text = f"""# Corridor definitions used in the maps

The existing project indicator identifies **{expanded_n} current SESAN Corredor Seco Ampliado municipalities**. It remains the authoritative current expanded indicator and is shown with a **dashed outline** when it is outside the older list.

To meet the request to distinguish the non-expanded corridor, the maps also use the municipality list in the annex of SESAN's 2016 *Estrategia de Respuesta para la Atención del Hambre Estacional*. The document describes 11 core departments and says this corridor contains 66 municipalities, but its enumerated annex matches **{legacy_n}** current municipality polygons. The map uses the enumerated list—not an invented rule—as the **legacy/core, solid-outline** layer. This one-municipality count inconsistency is documented rather than silently resolved.

The expanded-only layer contains **{expanded_only_n}** municipalities. The two lists need not be interpreted as a physical drought boundary: both are administrative prioritisation lists, not measured 2026 rainfall.

Sources (accessed 2026-09-04):

- [SESAN 2016 strategy, Annex 1](https://portal.sesan.gob.gt/wp-content/uploads/2021/06/ESTRATEGIA-HAMBRE-ESTACIONAL-2016.pdf)
- [SESAN/CONASAN current 160-municipality description](https://portal.sesan.gob.gt/2023/05/18/que-es-el-plan-para-la-atencion-del-hambre-estacional/)

No source polygons were downloaded or copied. The two indicators are matched to the existing 340-polygon municipality crosswalk by department and municipality name, with accent-insensitive matching.
"""
    (APP_DOCS / "corridor_definitions.md").write_text(text, encoding="utf-8")


def main() -> None:
    APP_TABLES.mkdir(parents=True, exist_ok=True)
    APP_DOCS.mkdir(parents=True, exist_ok=True)
    geo = load_municipal_geometry()
    chirps = pd.read_csv(DERIVED / "chirps_2026_municipality.csv")
    asis = pd.read_csv(DERIVED / "fao_asis_2026_municipality.csv")
    if "raster_valid_asi_area_share_in_municipality" not in asis.columns:
        # The supplied ASIS CSV is department-level; no raster coverage field
        # exists unless the optional raster workflow has been run.
        asis["raster_valid_asi_area_share_in_municipality"] = np.nan
    flags = corridor_flags(geo, chirps)
    flags.to_csv(APP_TABLES / "table_corridor_definitions.csv", index=False)
    write_documentation(flags)

    municipal = chirps.merge(
        flags[["municipality_id", "legacy_sesan_core_2016", "sesan_expanded_only_2025", "corridor_map_class"]],
        on="municipality_id", validate="one_to_one"
    ).merge(
        asis[["municipality_id", "asis_value", "raster_valid_asi_area_share_in_municipality"]],
        on="municipality_id", validate="one_to_one"
    )
    municipal = municipal.sort_values("rainfall_z_score_vs_1981_2025").reset_index(drop=True)
    municipal["z_rank"] = np.arange(1, len(municipal) + 1)
    municipal["field_site"] = municipal["municipality"].isin(["Olopa", "Chahal", "Patzité"]).astype(int)
    municipal.to_csv(APP_TABLES / "chirps_municipality_graph_data.csv", index=False)

    annual, years = annual_means(geo)
    site_annual = annual.loc[annual["municipality"].isin(["Olopa", "Chahal", "Patzité"])].copy()
    current = municipal.loc[municipal["field_site"].eq(1), ["municipality_id", "department", "municipality", "rain_2026_may_aug_mm"]].copy()
    current = current.rename(columns={"rain_2026_may_aug_mm": "rain_may_aug_mm"}).assign(year=2026, data_status="FINAL")
    site_annual = pd.concat([site_annual.assign(data_status="FINAL"), current], ignore_index=True, sort=False)
    site_annual.to_csv(APP_TABLES / "chirps_site_annual_series.csv", index=False)

    departments = department_series(geo, chirps)
    departments.to_csv(APP_TABLES / "chirps_department_graph_data.csv", index=False)
    municipal[["municipality_id", "department", "municipality", "rainfall_z_score_vs_1981_2025", "rainfall_historical_percentile", "asis_value", "raster_valid_asi_area_share_in_municipality", "field_site"]].to_csv(
        APP_TABLES / "chirps_fao_graph_data.csv", index=False
    )

    price = pd.read_csv(DERIVED / "maga_maize_prices_clean.csv")
    price.to_csv(APP_TABLES / "maga_white_maize_monthly_graph_data.csv", index=False)
    pd.read_csv(PROJECT / "tables" / "table_budget_scenarios.csv").to_csv(APP_TABLES / "budget_scenarios_graph_data.csv", index=False)

    print(f"Wrote Appendix graph data: {len(municipal)} municipalities, {len(departments)} departments, {len(site_annual)} site-year observations.")
    print(f"Corridor indicators: legacy enumerated core={int(flags.legacy_sesan_core_2016.sum())}; current expanded={int(flags.corredor_seco_160.sum())}; expanded-only={int(flags.sesan_expanded_only_2025.sum())}.")


if __name__ == "__main__":
    main()
