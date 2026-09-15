#!/usr/bin/env python3
"""Build portable analytical outputs from the included derived checkpoints.

This build deliberately does not reconstruct raster zonal statistics or MAGA
polygon intersections. Those raw inputs are not redistributed here. Instead it
validates and republishes the frozen, analysis-ready municipal and departmental
checkpoints that underlie the reported drought/exposure results.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
OUTPUT_TABLES = ROOT / "outputs" / "tables"
OUTPUT_FIGURES = ROOT / "outputs" / "figures"

BANDS = [
    ("z < -2.5", -np.inf, -2.5),
    ("-2.5 <= z < -2.0", -2.5, -2.0),
    ("-2.0 <= z < -1.5", -2.0, -1.5),
    ("-1.5 <= z < -1.0", -1.5, -1.0),
    ("-1.0 <= z < 0", -1.0, 0.0),
    ("z >= 0", 0.0, np.inf),
]

MUNICIPAL_REQUIRED = {
    "codigo_municipio_4d", "Departamento", "Municipio", "agricultural_land_ha",
    "A", "total", "agricultural_share_pct", "ag_workers_per_100_agricultural_ha",
    "historical_median_may_aug_mm", "historical_sd_may_aug_mm",
    "rain_2026_may_aug_mm", "z_2015_common", "z_2026_common", "H_2026",
    "H_2015", "d_i_dependency_pctile", "p_i_land_worker_pctile",
    "E_i_structural_exposure", "C_i_impact_2026", "C_i_impact_2015",
}
DEPARTMENT_REQUIRED = {
    "Departamento", "agricultural_land_ha", "agricultural_workers", "total_workers",
    "ag_workers_per_100_agricultural_ha", "agricultural_share_pct", "rain_2026_mm",
    "hist_median_mm", "hist_sd_mm", "z_2015_common", "z_2026_common", "H_2026",
    "H_2015", "d_i_dependency_pctile", "p_i_land_worker_pctile",
    "E_i_structural_exposure", "C_i_impact_2026", "C_i_impact_2015",
}


def read_csv(name: str, **kwargs: object) -> pd.DataFrame:
    """Read one included checkpoint with stable municipal-code formatting."""
    return pd.read_csv(DERIVED / name, **kwargs)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    municipal = read_csv(
        "municipal_agricultural_drought_impact_2026_2015.csv",
        dtype={"codigo_municipio_4d": str},
    )
    municipal["codigo_municipio_4d"] = municipal["codigo_municipio_4d"].str.zfill(4)
    departments = read_csv("maga_uso_tierra_2025_department_metrics.csv")
    historical = read_csv(
        "chirps_common_reference_zscore_2015_2019_2025_municipality.csv",
        dtype={"municipality_id": str},
    )
    historical["municipality_id"] = historical["municipality_id"].str.zfill(4)
    return municipal, departments, historical


def validate_inputs(
    municipal: pd.DataFrame, departments: pd.DataFrame, historical: pd.DataFrame
) -> None:
    """Fail early when a checkpoint is incomplete or no longer internally coherent."""
    missing_municipal = MUNICIPAL_REQUIRED.difference(municipal.columns)
    missing_department = DEPARTMENT_REQUIRED.difference(departments.columns)
    if missing_municipal:
        raise ValueError(f"Municipal checkpoint is missing: {sorted(missing_municipal)}")
    if missing_department:
        raise ValueError(f"Department checkpoint is missing: {sorted(missing_department)}")
    if len(municipal) != 340 or municipal["codigo_municipio_4d"].nunique() != 340:
        raise ValueError("Expected exactly 340 unique analytical municipalities.")
    if len(departments) != 22 or departments["Departamento"].nunique() != 22:
        raise ValueError("Expected exactly 22 departments.")
    if set(historical["year"].unique()) != {2015, 2019, 2025}:
        raise ValueError("Historical comparison checkpoint must contain 2015, 2019, and 2025.")
    if historical.groupby("year")["municipality_id"].nunique().to_dict() != {2015: 340, 2019: 340, 2025: 340}:
        raise ValueError("Every historical comparison year must cover all 340 municipalities.")
    for frame, columns, name in [
        (municipal, ["A", "total", "agricultural_land_ha", "rain_2026_may_aug_mm"], "municipal"),
        (departments, ["agricultural_workers", "total_workers", "agricultural_land_ha", "rain_2026_mm"], "department"),
    ]:
        if frame[columns].isna().any().any():
            raise ValueError(f"{name.title()} checkpoint has missing values in core inputs.")
    if not np.allclose(municipal["H_2026"], np.maximum(-municipal["z_2026_common"], 0)):
        raise ValueError("Municipal H_2026 is inconsistent with max(-z_2026, 0).")
    if not np.allclose(municipal["E_i_structural_exposure"], (municipal["d_i_dependency_pctile"] + municipal["p_i_land_worker_pctile"]) / 2):
        raise ValueError("Municipal E is inconsistent with (d + p) / 2.")
    if not np.allclose(municipal["C_i_impact_2026"], municipal["H_2026"] * municipal["E_i_structural_exposure"]):
        raise ValueError("Municipal C_2026 is inconsistent with H x E.")
    if not np.allclose(departments["H_2026"], np.maximum(-departments["z_2026_common"], 0)):
        raise ValueError("Department H_2026 is inconsistent with max(-z_2026, 0).")
    if not np.allclose(departments["E_i_structural_exposure"], (departments["d_i_dependency_pctile"] + departments["p_i_land_worker_pctile"]) / 2):
        raise ValueError("Department E is inconsistent with (d + p) / 2.")
    if not np.allclose(departments["C_i_impact_2026"], departments["H_2026"] * departments["E_i_structural_exposure"]):
        raise ValueError("Department C_2026 is inconsistent with H x E.")


def band_mask(values: pd.Series, low: float, high: float) -> pd.Series:
    if np.isneginf(low):
        return values < high
    if np.isposinf(high):
        return values >= low
    return (values >= low) & (values < high)


def department_concentration(frame: pd.DataFrame, mask: pd.Series, limit: int = 4) -> str:
    total = frame.groupby("Departamento", observed=True).size().rename("n_total")
    affected = frame.loc[mask].groupby("Departamento", observed=True).size().rename("n_band")
    ranked = pd.concat([total, affected], axis=1).fillna(0)
    ranked["share"] = ranked["n_band"] / ranked["n_total"]
    ranked = ranked.loc[ranked["n_band"] > 0].sort_values(["share", "n_band"], ascending=False).head(limit)
    if ranked.empty:
        return "none"
    return "; ".join(
        f"{department} {int(row.n_band)}/{int(row.n_total)} ({row.share:.0%})"
        for department, row in ranked.iterrows()
    )


def build_threshold_table(
    municipal: pd.DataFrame, departments: pd.DataFrame, historical: pd.DataFrame
) -> pd.DataFrame:
    rainfall_2015 = historical.loc[historical["year"] == 2015, ["municipality_id", "rain_may_aug_mm"]].rename(
        columns={"municipality_id": "codigo_municipio_4d", "rain_may_aug_mm": "rain_2015_may_aug_mm"}
    )
    frame = municipal.merge(rainfall_2015, on="codigo_municipio_4d", how="left", validate="one_to_one")
    if frame["rain_2015_may_aug_mm"].isna().any():
        raise ValueError("2015 rainfall did not merge to every municipality.")

    records: list[dict[str, object]] = []
    for year in (2026, 2015):
        z_column = f"z_{year}_common"
        rainfall_column = "rain_2026_may_aug_mm" if year == 2026 else "rain_2015_may_aug_mm"
        department_z = f"z_{year}_common"
        for label, low, high in BANDS:
            mask = band_mask(frame[z_column], low, high)
            department_count = int(band_mask(departments[department_z], low, high).sum())
            subset = frame.loc[mask]
            records.append({
                "year": year,
                "z_band": label,
                "municipalities": int(mask.sum()),
                "agricultural_workers_ine_2018": int(subset["A"].sum()),
                "departments_department_zscore": department_count,
                "median_rainfall_mm": round(float(subset[rainfall_column].median()), 3) if len(subset) else np.nan,
                "median_historical_sd_mm": round(float(subset["historical_sd_may_aug_mm"].median()), 3) if len(subset) else np.nan,
                "median_agricultural_dependence_pct": round(float(subset["agricultural_share_pct"].median()), 3) if len(subset) else np.nan,
                "median_ag_workers_per_100_agricultural_ha": round(float(subset["ag_workers_per_100_agricultural_ha"].median()), 3) if len(subset) else np.nan,
                "top_departmental_concentration": department_concentration(frame, mask),
            })
    return pd.DataFrame.from_records(records)


def municipal_analysis_table(municipal: pd.DataFrame) -> pd.DataFrame:
    result = municipal.rename(columns={
        "Departamento": "department",
        "Municipio": "municipality",
        "A": "agricultural_workers_ine_2018",
        "total": "total_workers_ine_2018",
        "agricultural_land_ha": "mapped_agricultural_land_ha_maga_2025",
        "agricultural_share_pct": "agricultural_dependence_pct",
        "ag_workers_per_100_agricultural_ha": "ag_workers_per_100_mapped_agricultural_ha",
        "historical_median_may_aug_mm": "historical_median_rainfall_mm_1981_2025",
        "historical_sd_may_aug_mm": "historical_sd_rainfall_mm_1981_2025",
        "rain_2026_may_aug_mm": "rainfall_2026_may_aug_mm",
        "z_2015_common": "z_2015_common_1981_2025",
        "z_2026_common": "z_2026_common_1981_2025",
        "d_i_dependency_pctile": "d_dependency_percentile",
        "p_i_land_worker_pctile": "p_density_percentile",
        "E_i_structural_exposure": "E_structural_exposure",
        "C_i_impact_2026": "C_impact_2026",
        "C_i_impact_2015": "C_impact_2015",
    })
    columns = [
        "codigo_municipio_4d", "department", "municipality", "rainfall_2026_may_aug_mm",
        "historical_median_rainfall_mm_1981_2025", "historical_sd_rainfall_mm_1981_2025",
        "z_2026_common_1981_2025", "H_2026", "agricultural_workers_ine_2018",
        "total_workers_ine_2018", "agricultural_dependence_pct",
        "mapped_agricultural_land_ha_maga_2025", "ag_workers_per_100_mapped_agricultural_ha",
        "d_dependency_percentile", "p_density_percentile", "E_structural_exposure",
        "C_impact_2026", "z_2015_common_1981_2025", "H_2015", "C_impact_2015",
    ]
    result = result.loc[:, columns].sort_values("C_impact_2026", ascending=False).reset_index(drop=True)
    result.insert(0, "rank_2026_C", np.arange(1, len(result) + 1))
    return result


def department_analysis_table(departments: pd.DataFrame) -> pd.DataFrame:
    result = departments.rename(columns={
        "Departamento": "department",
        "agricultural_workers": "agricultural_workers_ine_2018",
        "total_workers": "total_workers_ine_2018",
        "agricultural_land_ha": "mapped_agricultural_land_ha_maga_2025",
        "agricultural_share_pct": "agricultural_dependence_pct",
        "ag_workers_per_100_agricultural_ha": "ag_workers_per_100_mapped_agricultural_ha",
        "rain_2026_mm": "rainfall_2026_may_aug_mm",
        "hist_median_mm": "historical_median_rainfall_mm_1981_2025",
        "hist_sd_mm": "historical_sd_rainfall_mm_1981_2025",
        "z_2015_common": "z_2015_common_1981_2025",
        "z_2026_common": "z_2026_common_1981_2025",
        "d_i_dependency_pctile": "d_dependency_percentile",
        "p_i_land_worker_pctile": "p_density_percentile",
        "E_i_structural_exposure": "E_structural_exposure",
        "C_i_impact_2026": "C_impact_2026",
        "C_i_impact_2015": "C_impact_2015",
    })
    columns = [
        "department", "rainfall_2026_may_aug_mm", "historical_median_rainfall_mm_1981_2025",
        "historical_sd_rainfall_mm_1981_2025", "z_2026_common_1981_2025", "H_2026",
        "agricultural_workers_ine_2018", "total_workers_ine_2018", "agricultural_dependence_pct",
        "mapped_agricultural_land_ha_maga_2025", "ag_workers_per_100_mapped_agricultural_ha",
        "d_dependency_percentile", "p_density_percentile", "E_structural_exposure", "C_impact_2026",
        "z_2015_common_1981_2025", "H_2015", "C_impact_2015", "oxfam_households_with_losses_pct",
    ]
    result = result.loc[:, columns].sort_values("C_impact_2026", ascending=False).reset_index(drop=True)
    result.insert(0, "rank_2026_C", np.arange(1, len(result) + 1))
    return result


def data_dictionary() -> pd.DataFrame:
    return pd.DataFrame([
        ("codigo_municipio_4d", "municipality", "Four-digit municipal identifier.", "code", "Municipal boundaries/checkpoint"),
        ("rainfall_2026_may_aug_mm", "municipality/department", "Area-weighted May--August 2026 CHIRPS precipitation.", "mm", "CHIRPS v3"),
        ("historical_median_rainfall_mm_1981_2025", "municipality/department", "Median May--August precipitation in the common 1981--2025 reference.", "mm", "CHIRPS v3"),
        ("z_2026_common_1981_2025", "municipality/department", "2026 rainfall standardized using the common 1981--2025 historical distribution.", "standard deviations", "CHIRPS v3"),
        ("agricultural_workers_ine_2018", "municipality/department", "People occupied in agriculture, livestock, forestry, and fishing.", "people", "INE Censo 2018, A12.2"),
        ("total_workers_ine_2018", "municipality/department", "Total occupied population, including the unspecified branch.", "people", "INE Censo 2018, A12.2"),
        ("agricultural_dependence_pct", "municipality/department", "100 times agricultural workers divided by total occupied population.", "percent", "INE Censo 2018, A12.2"),
        ("mapped_agricultural_land_ha_maga_2025", "municipality/department", "Area of MAGA Level 1 ‘Territorios agrícolas’ polygons, aggregated to the unit.", "hectares", "MAGA land cover/use 2025"),
        ("ag_workers_per_100_mapped_agricultural_ha", "municipality/department", "100 times agricultural workers divided by mapped agricultural hectares; not productivity, arable land, or crop losses.", "workers per 100 ha", "INE 2018 + MAGA 2025"),
        ("d_dependency_percentile", "municipality/department", "Empirical percentile of agricultural dependence within the same geographical level.", "0--100 percentile", "Derived"),
        ("p_density_percentile", "municipality/department", "Empirical percentile of workers per 100 mapped agricultural hectares within the same geographical level.", "0--100 percentile", "Derived"),
        ("E_structural_exposure", "municipality/department", "Structural agricultural exposure: (d + p) / 2.", "0--100 index", "Derived"),
        ("H_2026", "municipality/department", "Drought hazard: max(-z_2026, 0).", "standard-deviation magnitude", "Derived from CHIRPS v3"),
        ("C_impact_2026", "municipality/department", "Descriptive impact priority: H_2026 times E. It is not a causal estimate or loss forecast.", "index", "Derived"),
    ], columns=["variable", "level", "description", "unit", "source"])


def save_figures(analysis: pd.DataFrame, departments: pd.DataFrame) -> None:
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=(7.1, 5.7), layout="constrained")
    values = analysis["C_impact_2026"]
    points = ax.scatter(
        analysis["z_2015_common_1981_2025"], analysis["z_2026_common_1981_2025"],
        c=values, cmap="Reds", s=26, edgecolor="white", linewidth=0.25, alpha=0.9,
    )
    ax.axhline(-2, color="#666666", linewidth=0.8, linestyle="--")
    ax.axvline(-2, color="#666666", linewidth=0.8, linestyle="--")
    bounds = (-4.2, 1.1)
    ax.plot(bounds, bounds, color="#222222", linewidth=0.8, linestyle=":")
    ax.set(xlim=bounds, ylim=bounds, xlabel="Z-score municipal, 2015 (referencia 1981–2025)",
           ylabel="Z-score municipal, 2026 (referencia 1981–2025)",
           title="Municipios: severidad de la sequía, 2015 frente a 2026")
    colorbar = fig.colorbar(points, ax=ax, pad=0.02)
    colorbar.set_label("Índice descriptivo C, 2026")
    fig.savefig(OUTPUT_FIGURES / "municipal_zscore_2015_vs_2026.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.1, 5.7), layout="constrained")
    size = 15 + 75 * np.sqrt(analysis["agricultural_workers_ine_2018"] / analysis["agricultural_workers_ine_2018"].max())
    points = ax.scatter(
        analysis["E_structural_exposure"], analysis["H_2026"], c=analysis["C_impact_2026"],
        s=size, cmap="Reds", edgecolor="#333333", linewidth=0.25, alpha=0.82,
    )
    ax.set(xlim=(-2, 102), ylim=(-0.05, max(analysis["H_2026"].max() + 0.2, 3.2)),
           xlabel="Exposición estructural E = (d + p) / 2 (percentil 0–100)",
           ylabel="Peligro hídrico H = max(-z, 0)",
           title="Municipios: exposición agrícola y peligro de sequía, 2026")
    colorbar = fig.colorbar(points, ax=ax, pad=0.02)
    colorbar.set_label("Índice descriptivo C = H × E")
    fig.savefig(OUTPUT_FIGURES / "municipal_exposure_and_hazard_2026.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.3, 6.0), layout="constrained")
    ordered = departments.sort_values("C_i_impact_2026", ascending=False)
    points = ax.scatter(
        ordered["E_i_structural_exposure"], ordered["H_2026"], c=ordered["C_i_impact_2026"],
        cmap="Reds", s=75, edgecolor="#333333", linewidth=0.35,
    )
    for row in ordered.itertuples():
        ax.annotate(row.Departamento, (row.E_i_structural_exposure, row.H_2026),
                    xytext=(4, 3), textcoords="offset points", fontsize=7.4)
    ax.set(xlim=(-2, 102), ylim=(-0.05, max(ordered["H_2026"].max() + 0.2, 3.2)),
           xlabel="Exposición estructural E (percentil 0–100)",
           ylabel="Peligro hídrico H = max(-z, 0)",
           title="Departamentos: exposición agrícola y peligro de sequía, 2026")
    colorbar = fig.colorbar(points, ax=ax, pad=0.02)
    colorbar.set_label("Índice descriptivo C = H × E")
    fig.savefig(OUTPUT_FIGURES / "department_exposure_and_hazard_2026.png", dpi=220)
    plt.close(fig)


def write_outputs_readme() -> None:
    text = """# Reproduced analytical outputs

Run `make reproduce` from the repository root to rebuild every file in this directory from the compact CSV checkpoints in `data/derived/`.

## Tables

- `municipal_analysis_ready.csv`: 340 municipalities, ordered by the 2026 descriptive impact index.
- `department_analysis_ready.csv`: 22 departments, ordered by the same level-specific index; it retains the author-supplied Oxfam loss percentages where available.
- `municipal_drought_thresholds_2015_2026.csv`: mutually exclusive z-score bands for 2015 and 2026. Agricultural workers are summed over municipalities in a band; departmental counts classify departments by their own aggregate precipitation z-score.
- `data_dictionary.csv`: definitions, units, and sources for the portable analytical columns.

## Figures

The three PNG figures are deliberately non-cartographic alternatives for reuse without redistributing a boundary layer. They display the comparison between 2015 and 2026, the municipal relationship between structural exposure and hazard, and the analogous department view. They are descriptive, not predictions of losses or causal effects.

For the underlying assumptions and source boundaries, see `docs/data-sources.md` and `docs/reproducibility.md`.
"""
    (ROOT / "outputs" / "README.md").write_text(text)


def main() -> None:
    OUTPUT_TABLES.mkdir(parents=True, exist_ok=True)
    OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
    municipal, departments, historical = load_inputs()
    validate_inputs(municipal, departments, historical)

    build_threshold_table(municipal, departments, historical).to_csv(
        OUTPUT_TABLES / "municipal_drought_thresholds_2015_2026.csv", index=False
    )
    municipal_analysis_table(municipal).to_csv(
        OUTPUT_TABLES / "municipal_analysis_ready.csv", index=False
    )
    department_analysis_table(departments).to_csv(
        OUTPUT_TABLES / "department_analysis_ready.csv", index=False
    )
    data_dictionary().to_csv(OUTPUT_TABLES / "data_dictionary.csv", index=False)
    save_figures(municipal_analysis_table(municipal), departments)
    write_outputs_readme()
    print("Rebuilt portable outputs: 340 municipalities, 22 departments, 12 threshold rows, and 3 figures.")


if __name__ == "__main__":
    main()
