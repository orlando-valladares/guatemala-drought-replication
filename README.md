# Guatemala drought replication package

This repository is the non-Overleaf replication workspace for the Guatemala May--August 2026 drought analysis. It intentionally excludes the field-report prose, J-PAL template, Overleaf history, raw rasters, survey microdata, and all large source archives.

## Current status

This is a reproducibility scaffold, not yet the final public release. It contains:

- a frozen snapshot of the analytical scripts in `code/legacy_snapshot/`;
- compact derived checkpoints in `data/derived/`;
- a portable data manifest, methods notes, environment specification, and release checklist; and
- a release hygiene check that confirms no Overleaf or raw geospatial files were added.

The legacy scripts still encode the original personal-workspace paths. Porting them to `config/paths.yml`, adding official download URLs/checksums, and validating a clean-machine rebuild are the next implementation steps. Do not interpret this repository as a claim that those scripts are already one-command reproducible.

## Scope

Core analytical outputs use CHIRPS v3 precipitation, Guatemala municipal boundaries, INE Censo 2018 employment data, and MAGA 2025 land-cover polygons. The impact index is descriptive:

```text
max(-z, 0) × (100 × agricultural workers / mapped agricultural hectares)
```

It ranks joint drought severity and agricultural-employment exposure; it is neither an estimate of crop loss nor a causal effect.

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
