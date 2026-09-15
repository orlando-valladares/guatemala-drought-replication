# Guatemala drought replication package

This repository is the clean, non-Overleaf replication package for the Guatemala May--August 2026 drought analysis. It contains portable analytical checkpoints, a deterministic build, validation checks, reusable analytical tables, and non-cartographic figures. It intentionally excludes proprietary information, report prose, the J-PAL template, author metadata from the report, Overleaf history, raw rasters, raw land-use polygons, and survey microdata.

## What one command reproduces

```bash
conda env create -f environment.yml
conda activate guatemala-drought-replication
make all
```

`make all` reads only the tracked CSV checkpoints in `data/derived/`, validates the numerical identities and coverage, then recreates:

- a municipality-level analysis-ready CSV (340 municipalities);
- a department-level analysis-ready CSV (22 departments);
- the 2015/2026 mutually exclusive drought-threshold summary table;
- a plain-language data dictionary; and
- three reusable PNG figures showing the 2015--2026 comparison and the relationship between drought hazard and agricultural exposure.

The expected final line is `Release hygiene check passed...`. To recreate outputs without tests, run `make reproduce`; to re-run only validations, run `make test`.

## Reuse the data

Start with [`outputs/tables/data_dictionary.csv`](outputs/tables/data_dictionary.csv), then choose the unit you need:

- [`outputs/tables/municipal_analysis_ready.csv`](outputs/tables/municipal_analysis_ready.csv): every analytical municipality, ordered by the 2026 descriptive index.
- [`outputs/tables/department_analysis_ready.csv`](outputs/tables/department_analysis_ready.csv): every department, retaining the available author-supplied Oxfam percentages.
- [`outputs/tables/municipal_drought_thresholds_2015_2026.csv`](outputs/tables/municipal_drought_thresholds_2015_2026.csv): mutually exclusive severity bands. Agricultural workers are summed over municipalities in each band; the department count instead uses each department's own aggregate precipitation z-score.

The portable variables are documented in detail in [`docs/data-sources.md`](docs/data-sources.md). The impact index is descriptive:

```text
H_i = max(-z_i, 0)
d_i = Pctl(A_i / T_i)
p_i = Pctl(A_i / ha_ag,i)
E_i = (d_i + p_i) / 2
C_i = H_i × E_i
```

It does not estimate causal effects, crop losses, land productivity, or land tenure. Percentiles are calculated independently within the displayed municipal or department distribution, so cross-level `E` and `C` values must not be compared directly.

## What is and is not reproduced

The included derived checkpoints faithfully reproduce the published analytical tables and portable alternative-use outputs. The full raw-data pipeline is **not** run by this release because the original CHIRPS rasters, municipal boundary layer, and MAGA polygon file are not redistributed here. The original scripts are retained, clearly marked, in [`code/legacy_snapshot/`](code/legacy_snapshot/); they are audit material, not the public build.

For source acquisition, data limitations, and the path to a future raw rebuild, see [`docs/reproducibility.md`](docs/reproducibility.md) and [`data/manifest.csv`](data/manifest.csv). Before a public release, complete the decisions in [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md), especially the code/data license and the upstream redistribution review.

## Repository map

```text
code/legacy_snapshot/   Original audited scripts; not portable or executed
data/derived/           Small, tracked analytical checkpoints
data/raw/               Empty local location for authorized raw inputs; ignored by Git
docs/                   Methods, data provenance, and reproducibility boundaries
outputs/                Deterministically regenerated tables and figures
scripts/                Build and release-hygiene checks
tests/                  Output and numerical-consistency tests
```

## Citation and scope

Citation metadata is in [`CITATION.cff`](CITATION.cff). No license has been selected yet; reuse is not authorized until the author chooses one. See [`LICENSE.md`](LICENSE.md).
