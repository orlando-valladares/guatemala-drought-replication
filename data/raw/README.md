# Raw-data layout

Raw files are intentionally excluded from Git. Place authorized upstream files in the following directories if rebuilding the research workspace beyond the processed-data reproduction:

```text
data/raw/
├── boundaries/    Guatemala ADM1/ADM2 boundaries used for zonal aggregation
├── census_2018/   INE Census 2018 published employment tables
├── chirps/        CHIRPS v3 monthly or pentad rasters
├── encovi_2023/   Authorized ENCOVI 2023 household file
├── era5_land/     ERA5-Land daily/monthly extracts
├── maga_2025/     MAGA 2025 land-cover and agricultural-territory polygons
└── modis/         MOD13A3.061 NDVI and QA layers
```

The directories are retained with `.gitkeep` files, while their contents are ignored. Canonical access information and redistribution notes are recorded in [`../metadata/source_manifest.csv`](../metadata/source_manifest.csv).

The public `make all` workflow does **not** require these files. It starts from the disclosure-safe checkpoints in `data/processed/`.
