#!/usr/bin/env python3
"""Guard the public replication repository against report and raw-data leakage."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_DIRS = {"overleaf", ".git", ".venv"}
PROHIBITED_SUFFIXES = {".tex", ".tif", ".tiff", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".pdf"}
REQUIRED_FILES = {
    "README.md",
    "CITATION.cff",
    "environment.yml",
    "data/manifest.csv",
    "scripts/build_derived_outputs.py",
    "scripts/check_release.py",
    "tests/test_reproduction.py",
    "docs/data-sources.md",
    "docs/reproducibility.md",
}
violations = []
for path in ROOT.rglob("*"):
    relative = path.relative_to(ROOT)
    parts = relative.parts
    if any(part in PROHIBITED_DIRS for part in parts):
        if ".git" not in parts:
            violations.append(str(relative))
        continue
    if path.is_file() and path.suffix.lower() in PROHIBITED_SUFFIXES:
        violations.append(str(relative))
for required in REQUIRED_FILES:
    if not (ROOT / required).is_file():
        violations.append(f"missing required file: {required}")
if violations:
    raise SystemExit("Prohibited or missing release artifacts:\n- " + "\n- ".join(sorted(violations)))
print("Release hygiene check passed: no Overleaf, TeX, raw geospatial, or PDF artifacts found; required reproducibility files are present.")
