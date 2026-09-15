# Reproducibility contract

## Guaranteed by this repository

A clean environment with the dependencies in `environment.yml` can run `make all`. That command validates the included compact checkpoints and deterministically recreates every CSV and PNG in `outputs/`. The tests verify:

- 340 unique analytical municipalities and 22 departments;
- complete 2015 and 2026 mutually exclusive drought bands;
- internal identities `H=max(-z,0)`, `E=(d+p)/2`, and `C=H×E`; and
- existence of every documented output table and figure.

This is enough to inspect, reuse, or recalculate all released descriptive analyses without an Overleaf account or report assets.

## Not claimed by this repository

It does not currently rebuild zonal rainfall estimates from raw CHIRPS rasters, intersect MAGA land-use polygons with municipal geography, or reproduce report-ready maps. Those source files are excluded because their redistribution terms, stable public URLs, or both have not yet been confirmed. The included files in `code/legacy_snapshot/` preserve the original calculations for audit but retain personal-workspace paths and are deliberately not run by the Makefile.

## Path to a full raw rebuild

1. Confirm the exact canonical download links, versions, retrieval dates, licenses, and checksums in `data/manifest.csv`.
2. Obtain the raw inputs in the ignored `data/raw/` paths, without committing them unless redistribution is authorized.
3. Port the audited scripts from `code/legacy_snapshot/` to repository-relative paths and a documented `config/paths.yml`.
4. Produce new derived checkpoints and compare them to the tracked checkpoint values using numerical regression tests.
5. Add a separate optional `make raw-rebuild` target only after the four previous steps pass on a clean clone.

The public release should be reviewed against [`../RELEASE-CHECKLIST.md`](../RELEASE-CHECKLIST.md) before tagging a version or assigning a DOI.
