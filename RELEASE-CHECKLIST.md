# Public-release checklist

## Decisions required from the author

- [ ] Confirm public/private/embargoed status and the exact release scope (Guatemala core only versus Honduras, FAO ASIS, prices, ENIGH and SESAN extensions).
- [ ] Select a code license and, if appropriate, a distinct data/derived-data license.
- [ ] Approve public author list, citation text and whether to mint a DOI.
- [ ] Confirm whether each upstream dataset can be redistributed; otherwise approve canonical download links and access instructions.
- [ ] Supply or approve a citable public source for the Oxfam department-loss values.
- [ ] Decide how to distribute any large frozen source archive (for example, Zenodo or a GitHub Release rather than normal Git).

## Implementation work remaining

- [ ] Replace legacy workspace paths with `config/paths.yml`.
- [ ] Add official source URLs, retrieval dates, checksums and licenses to `data/manifest.csv`.
- [ ] Replace the current cross-project SESAN dependency with a small documented input.
- [ ] Write an ordered build command and test it from a clean clone.
- [ ] Add numerical regression tests against `data/derived/` checkpoints.
- [ ] Audit repository history and files for private names, report prose, credentials, raw data and Overleaf artifacts before release.
