#!/usr/bin/env python3
"""Fail if prohibited report/raw artifacts enter the replication repository."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROHIBITED_DIRS={"overleaf", ".git"}
PROHIBITED_SUFFIXES={".tex", ".tif", ".tiff", ".shp", ".shx", ".dbf", ".prj", ".pdf"}
violations=[]
for path in ROOT.rglob("*"):
    if any(part in PROHIBITED_DIRS for part in path.relative_to(ROOT).parts):
        if ".git" not in path.relative_to(ROOT).parts:
            violations.append(str(path.relative_to(ROOT)))
    elif path.is_file() and path.suffix.lower() in PROHIBITED_SUFFIXES:
        violations.append(str(path.relative_to(ROOT)))
if violations:
    raise SystemExit("Prohibited release artifacts:\n- " + "\n- ".join(sorted(violations)))
print("Release hygiene check passed: no Overleaf, TeX, raw geospatial, or PDF artifacts found.")
