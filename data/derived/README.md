# Derived checkpoints

These compact CSVs are the release's portable, analysis-ready input layer. They are sufficient for `make reproduce` to regenerate every file in `outputs/`; no raw raster or shapefile is required for that build.

They are not substitutes for upstream raw data and do not themselves recreate zonal statistics or polygon intersections. Those steps remain documented in `code/legacy_snapshot/` while the raw-source release path is completed.

- `chirps_2026_municipality.csv`: final May--August 2026 municipal CHIRPS measures.
- `chirps_historical_comparison_2015_2019_2026_municipality.csv`: historical comparison series.
- `chirps_common_reference_zscore_2015_2019_2025_municipality.csv`: common-reference municipal z-score inputs.
- `chirps_shock_comparison_department_common_reference.csv`: common-reference department comparison inputs.
- `maga_uso_tierra_2025_*_metrics.csv`: municipality and department employment/land metrics.
- `municipal_agricultural_drought_impact_2026_2015.csv`: municipal descriptive hazard, exposure, and impact-index components.
