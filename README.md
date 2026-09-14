# Guatemala drought replication package

This repository is a replication workspace for a Guatemala May--August 2026 drought analysis, removing proprietary information,

## Current status

This is a reproducibility scaffold, not yet the final public release. It contains:

- a frozen snapshot of the analytical scripts in `code/legacy_snapshot/`;
- compact derived checkpoints in `data/derived/`;
- a portable data manifest, methods notes, environment specification, and release checklist; and
- a release hygiene check that confirms no Overleaf or raw geospatial files were added.

The legacy scripts still encode the original personal-workspace paths. Porting them to `config/paths.yml`, adding official download URLs/checksums, and validating a clean-machine rebuild are the next implementation steps. Do not interpret this repository as a claim that those scripts are already one-command reproducible.

## Scope

Core analytical outputs use CHIRPS v3 precipitation, Guatemala municipal boundaries, INE Censo 2018 employment data, and MAGA 2025 land-cover polygons. The impact index is descriptive. At each reported geographical level, it is defined as:

```text
H_i = max(-z_i, 0)
d_i = Pctl(A_i / T_i)
p_i = Pctl(A_i / ha_ag,i)
E_i = (d_i + p_i) / 2
C_i = H_i × E_i
```

`A` is agricultural employment in the INE 2018 table, `T` is total occupied population, and `ha_ag` is MAGA 2025 mapped agricultural land. `Pctl` is the empirical 0--100 percentile within the displayed municipal or department distribution. `H` measures drought severity, `E` structural agricultural exposure, and `C` their descriptive combination; none estimates crop losses or a causal effect.

## Setup

```bash
conda env create -f environment.yml
conda activate guatemala-drought-replication
make check-release
```

Place permitted source inputs outside Git under a local `data/raw/` tree following `data/manifest.csv`. The required public/restricted access decisions are in `RELEASE-CHECKLIST.md`.

## Repository boundaries

- No `.tex`, `overleaf/`, report assets, author metadata from the report, or Overleaf Git history belong here.
- No raw MAGA land-cover shapefile, CHIRPS rasters, ENIGH microdata, MSPAS inputs, or compiled figure PDFs belong here unless their redistribution terms are confirmed.
- Derived checkpoints are included only to document the current numerical state and support later regression tests.
