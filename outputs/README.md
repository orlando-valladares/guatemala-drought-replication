# Reproduced analytical outputs

Run `make reproduce` from the repository root to rebuild every file in this directory from the compact CSV checkpoints in `data/derived/`.

## Tables

- `municipal_analysis_ready.csv`: 340 municipalities, ordered by the 2026 descriptive impact index.
- `department_analysis_ready.csv`: 22 departments, ordered by the same level-specific index; it retains the author-supplied Oxfam loss percentages where available.
- `municipal_drought_thresholds_2015_2026.csv`: mutually exclusive z-score bands for 2015 and 2026. Agricultural workers are summed over municipalities in a band; departmental counts classify departments by their own aggregate precipitation z-score.
- `data_dictionary.csv`: definitions, units, and sources for the portable analytical columns.

## Figures

The three PNG figures are deliberately non-cartographic alternatives for reuse without redistributing a boundary layer. They display the comparison between 2015 and 2026, the municipal relationship between structural exposure and hazard, and the analogous department view. They are descriptive, not predictions of losses or causal effects.

For the underlying assumptions and source boundaries, see `docs/data-sources.md` and `docs/reproducibility.md`.
