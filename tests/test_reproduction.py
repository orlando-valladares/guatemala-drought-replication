#!/usr/bin/env python3
"""Regression checks for the portable derived-data build."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"


def main() -> None:
    expected_tables = {
        "municipal_analysis_ready.csv",
        "department_analysis_ready.csv",
        "municipal_drought_thresholds_2015_2026.csv",
        "data_dictionary.csv",
    }
    absent = [name for name in expected_tables if not (TABLES / name).is_file()]
    if absent:
        raise SystemExit("Run `make reproduce` first; missing: " + ", ".join(absent))

    municipal = pd.read_csv(TABLES / "municipal_analysis_ready.csv", dtype={"codigo_municipio_4d": str})
    departments = pd.read_csv(TABLES / "department_analysis_ready.csv")
    thresholds = pd.read_csv(TABLES / "municipal_drought_thresholds_2015_2026.csv")
    dictionary = pd.read_csv(TABLES / "data_dictionary.csv")

    assert municipal.shape[0] == 340
    assert municipal["codigo_municipio_4d"].nunique() == 340
    assert departments.shape[0] == 22
    assert departments["department"].nunique() == 22
    assert thresholds.shape[0] == 12
    assert thresholds.groupby("year")["municipalities"].sum().to_dict() == {2015: 340, 2026: 340}
    assert thresholds.groupby("year")["departments_department_zscore"].sum().to_dict() == {2015: 22, 2026: 22}
    assert municipal["C_impact_2026"].is_monotonic_decreasing
    assert departments["C_impact_2026"].is_monotonic_decreasing
    assert np.allclose(
        municipal["C_impact_2026"],
        municipal["H_2026"] * municipal["E_structural_exposure"],
    )
    assert np.allclose(
        departments["C_impact_2026"],
        departments["H_2026"] * departments["E_structural_exposure"],
    )
    assert {"H_2026", "E_structural_exposure", "C_impact_2026"}.issubset(set(dictionary["variable"]))
    for filename in [
        "municipal_zscore_2015_vs_2026.png",
        "municipal_exposure_and_hazard_2026.png",
        "department_exposure_and_hazard_2026.png",
    ]:
        path = FIGURES / filename
        assert path.is_file() and path.stat().st_size > 20_000, filename
    print("Reproduction checks passed: outputs are complete and internally consistent.")


if __name__ == "__main__":
    main()
