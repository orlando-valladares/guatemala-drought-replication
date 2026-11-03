# Guatemala drought replication

[Explore the figures](https://orlando-valladares.github.io/guatemala-drought-replication/) · [Read the draft report](docs/downloads/Guatemala_Drought_Draft.pdf) · [Browse the processed data](data/README.md)

This repository accompanies the descriptive brief on Guatemala's 2026 *Primera* drought. It combines CHIRPS v3 rainfall, ERA5-Land, the 2018 Population Census, ENCOVI 2023, MODIS vegetation, and MAGA agricultural-territory boundaries. The public package is organized around the four figures in the report and the disclosure-safe analytical files needed to reproduce them.

## Main results

- CHIRPS records **757.1 mm** nationally during May–August 2026, or **−1.92 standard deviations** relative to 1981–2025.
- ERA5-Land records **574.5 mm**, or **−2.49 standard deviations** relative to 1950–2025.
- In both products, **16 of 22 departments** fall below the extreme-drought threshold (`z < −2`).
- The fixed 2018 Census distribution places **54.6%** of agricultural workers in extreme-drought departments under CHIRPS and **60.1%** under ERA5-Land.

These are descriptive exposure measures. They are not observed 2026 employment counts, crop-loss estimates, causal effects, or forecasts.

## Start here

| Order | Path | Purpose |
|---:|---|---|
| 1 | [`data/README.md`](data/README.md) | Data inventory, provenance, geography, and restrictions |
| 2 | [`code/python/build_figures.py`](code/python/build_figures.py) | Rebuilds all four publication figures |
| 3 | [`tests/test_release.py`](tests/test_release.py) | Validates row counts, headline statistics, and release files |
| 4 | [`out/report/Guatemala_Drought_Draft.pdf`](out/report/Guatemala_Drought_Draft.pdf) | Current draft report |
| 5 | [`docs/`](docs/) | Static figure gallery served by GitHub Pages |

## Reproduce

Python 3.11 or later is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
make all
```

`make all` rebuilds the four figures from `data/processed/`, synchronizes their PDF and PNG versions into the Pages gallery, and runs the validation suite. No network access or private raw data are required for this processed-data reproduction.

## Repository layout

```text
code/python/      Self-contained figure builder and release utilities
data/raw/         Documented placeholders for upstream files; raw data are not committed
data/processed/   Public analytical checkpoints and simplified publication geography
data/metadata/    Variable dictionary and source manifest
out/figures/      Exact PDF and PNG figure outputs
out/report/       Current report draft
docs/             GitHub Pages figure gallery and downloadable assets
tests/            Numerical, structural, and release-hygiene checks
```

The previous legacy-script archive, visual-regression screenshots, build logs, duplicate `.dta` files, and exploratory offline dashboard were intentionally removed. This release keeps one documented path for the figures rather than multiple historical pipelines.

## Raw-data boundary

The complete upstream reconstruction requires large CHIRPS, ERA5-Land, and MODIS files plus source datasets whose redistribution terms differ. The expected raw layout and acquisition notes are documented in [`data/raw/README.md`](data/raw/README.md). Raw files are ignored by Git; the repository includes only aggregate, disclosure-safe processed data.

## Citation and reuse

Citation metadata are available in [`CITATION.cff`](CITATION.cff). Source datasets retain their original terms. The repository's current code-license status is recorded in [`LICENSE.md`](LICENSE.md).

Analysis by Orlando Valladares. Repository reorganized on 3 November 2026.
