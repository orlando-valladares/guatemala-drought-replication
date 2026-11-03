# Code

`python/build_figures.py` is the public reproduction entry point. It reads only files committed under `data/processed/` and writes the four publication figures to `out/figures/pdf/` and `out/figures/png/`.

Run it directly:

```bash
python3 code/python/build_figures.py
```

or run the complete release workflow from the repository root:

```bash
make all
```

The original multi-project research workspace included extraction code for large rasters and locally authorized source files. Those scripts depended on private absolute paths and were deliberately not copied into this cleaned public package. Raw-file expectations and provenance are documented in [`data/raw/README.md`](../data/raw/README.md).
