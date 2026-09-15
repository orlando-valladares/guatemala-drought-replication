# Data sources and portable variables

## Source inputs

| Input | Used for | Canonical access / provenance | Included in Git? |
|---|---|---|---|
| CHIRPS v3 final monthly precipitation, May--August 1981--2026 | Municipal and department rainfall, historical moments, percentiles, and z-scores | [Climate Hazards Center: CHIRPS v3](https://www.chc.ucsb.edu/data/chirps3) | No raw rasters; final derived checkpoints are included. |
| INE Censo Nacional 2018, Cuadro A12.2 | `A`: workers in agriculture, livestock, forestry, and fishing; `T`: total occupied population | [INE Censo 2018, Cuadro A12.2](https://censo2018.ine.gob.gt/archivos/resultados_censo2018.pdf) | No raw table; analytical values are included in the checkpoints. |
| MAGA coverage and land-use polygons, 2025 | Hectares in Level 1 `Territorios agrícolas`; crop/land-use exploration | `COBUSOT_2025_10072025`, metadata date 10 July 2025; vector layer supplied to the author | No; redistribution and canonical download path remain to be confirmed. |
| Oxfam 2026 dry-corridor assessment | Available department percentages of households reporting losses | [Oxfam report landing page](https://lac.oxfam.org/informe-la-sequia-los-cultivos-y-el-corredor-seco-centroamericano/) | The derived department file retains the available values; no underlying household data are included. |
| Municipal boundaries | Zonal aggregation and original maps | Public Guatemala municipal boundary source; canonical URL and license still to be verified | No. |

## Definitions

`A/T` is agricultural dependence: agricultural workers divided by the total occupied population. The INE total retains the census's unspecified branch, matching its published denominator.

`A/ha_ag` is agricultural workers divided by MAGA's mapped Level 1 agricultural-territory area. The published scale is workers per 100 hectares. It is **not** a measure of productivity, land ownership, arable land, sown area, or crop losses.

To avoid selecting places only because they have a high agricultural share or only because they have a high workers-per-land ratio, the structural exposure index gives equal rank-based weight to each:

```text
d_i = Pctl(A_i / T_i)
p_i = Pctl(A_i / ha_ag,i)
E_i = (d_i + p_i) / 2
```

The drought hazard is `H_i = max(-z_i, 0)`, where `z_i` is the May--August precipitation z-score. The descriptive priority measure is `C_i = H_i × E_i`. `Pctl` is the empirical 0--100 percentile among units at the same geographic level. It follows that municipal and department `E` or `C` cannot be compared directly.

## Column-level guide

The machine-readable version is [`../outputs/tables/data_dictionary.csv`](../outputs/tables/data_dictionary.csv). The most reusable output files are:

- municipal analysis: [`../outputs/tables/municipal_analysis_ready.csv`](../outputs/tables/municipal_analysis_ready.csv)
- department analysis: [`../outputs/tables/department_analysis_ready.csv`](../outputs/tables/department_analysis_ready.csv)
- drought bands: [`../outputs/tables/municipal_drought_thresholds_2015_2026.csv`](../outputs/tables/municipal_drought_thresholds_2015_2026.csv)
