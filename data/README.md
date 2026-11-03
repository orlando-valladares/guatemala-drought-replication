# Published data

This directory separates upstream files from the processed analytical checkpoints used by the report.

## Processed-data inventory

| File | Unit | Main use |
|---|---|---|
| `processed/monthly_rainfall_1981_2026.csv` | month–year | Figure 1 monthly rainfall distribution |
| `processed/chirps_distribution_inputs.csv` | municipality–year | Figure 2 density inputs and audit trail |
| `processed/chirps_distribution_curves.csv` | curve point | Figure 2 plotted density curves |
| `processed/climate_exposure_annual.csv` | product–year–window | Figure 3 historical exposure |
| `processed/figure4_municipal.geojson` | municipality | Figure 4 panel a geometry and CHIRPS values |
| `processed/figure4_department.geojson` | department | Figure 4 department geometry and label points |
| `processed/appendix_A3_department.csv` | national/department | Figure 4 panels b–d and Appendix Table A3 |
| `processed/department_rainfall_1981_2026.csv` | department–year | Department CHIRPS history |
| `processed/era5_land_national_1950_2026.csv` | year | National ERA5-Land robustness series |
| `processed/modis_cropland_anomaly_2026.csv` | national/department | MODIS agricultural-mask robustness measure |
| `processed/municipal_analysis_ready.csv` | municipality | Reusable municipal analysis table |
| `processed/department_analysis_ready.csv` | department | Reusable department analysis table |
| `processed/municipal_drought_thresholds_2015_2026.csv` | year–severity band | Threshold summary |

Variable definitions are in [`metadata/data_dictionary.csv`](metadata/data_dictionary.csv). Provenance and redistribution notes are in [`metadata/source_manifest.csv`](metadata/source_manifest.csv).

## Geography and denominators

CHIRPS municipal results use 340 Census-linked municipalities. Department results use Guatemala's 22 departments. Agricultural exposure applies the fixed spatial distribution of workers in industry A—agriculture, livestock, forestry, and fishing—from the 2018 Census. It does not reconstruct employment in each historical year.

CHIRPS and ERA5-Land are kept as separate products. CHIRPS begins in 1981; ERA5-Land begins in 1950. Their standardized anomalies use each product's own reference distribution.

## Restrictions

No household microdata, Census person records, credentials, API keys, or raw restricted files are included. ENCOVI appears only as department and national poverty aggregates. Oxfam percentages describe purposively selected communities and are not representative national estimates.
