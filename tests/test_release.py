#!/usr/bin/env python3
"""Validate the public Guatemala drought replication release."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import geopandas as gpd
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
PDF = ROOT / "out" / "figures" / "pdf"
PNG = ROOT / "out" / "figures" / "png"


class LocalAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src", "data-image"} and value:
                self.references.add(value)


def main() -> None:
    monthly = pd.read_csv(DATA / "monthly_rainfall_1981_2026.csv")
    curves = pd.read_csv(DATA / "chirps_distribution_curves.csv")
    climate = pd.read_csv(DATA / "climate_exposure_annual.csv")
    appendix = pd.read_csv(DATA / "appendix_A3_department.csv")
    municipal = gpd.read_file(DATA / "figure4_municipal.geojson")
    department = gpd.read_file(DATA / "figure4_department.geojson")

    assert monthly.year.min() == 1981 and monthly.year.max() == 2026
    monthly_counts = monthly.groupby("year").month.nunique()
    assert monthly_counts.loc[1981:2025].eq(12).all()
    assert monthly_counts.loc[2026] == 9
    assert curves.shape[0] == 2 * 3 * 421
    assert curves.groupby(["population", "series"]).size().eq(421).all()
    assert curves.pdf.ge(0).all() and curves.cdf.between(0, 1).all()

    primera = climate.loc[climate.window.eq("Primera (May--Aug)")]
    assert len(primera.loc[primera["product"].eq("CHIRPS")]) == 46
    assert len(primera.loc[primera["product"].eq("ERA5-Land")]) == 77
    latest = primera.loc[primera.year.eq(2026)].set_index("product")
    assert latest.extreme_departments.to_dict() == {"CHIRPS": 16, "ERA5-Land": 16}
    assert np.isclose(latest.loc["CHIRPS", "national_rain_mm"], 757.0910236)
    assert np.isclose(latest.loc["ERA5-Land", "national_rain_mm"], 574.5329365)
    assert np.isclose(latest.loc["CHIRPS", "agricultural_worker_share_pct"], 54.5882201)
    assert np.isclose(latest.loc["ERA5-Land", "agricultural_worker_share_pct"], 60.1459210)

    assert len(appendix) == 23 and appendix.department.nunique() == 23
    national = appendix.loc[appendix.national_row.eq(1)].iloc[0]
    assert np.isclose(national.chirps_z_2026, -1.9206947)
    assert np.isclose(national.era5_rain_z_2026, -2.4860942)
    assert np.isclose(national.era5_temp_hist_mean, 22.9439, atol=1e-3)
    assert len(municipal) == 340 and len(department) == 22
    assert municipal.geometry.notna().all() and department.geometry.notna().all()

    stems = [
        "figure-1-monthly-rainfall",
        "figure-2-rainfall-anomaly",
        "figure-3-extreme-drought-exposure",
        "figure-4-four-map-assemblage",
    ]
    for stem in stems:
        assert (PDF / f"{stem}.pdf").stat().st_size > 10_000
        assert (PNG / f"{stem}.png").stat().st_size > 25_000
        assert (ROOT / "docs" / "figures" / f"{stem}.pdf").is_file()
        assert (ROOT / "docs" / "figures" / f"{stem}.png").is_file()

    report = ROOT / "out" / "report" / "Guatemala_Drought_Draft.pdf"
    assert report.stat().st_size > 500_000
    assert (ROOT / "docs" / "downloads" / report.name).is_file()

    parser = LocalAssetParser()
    parser.feed((ROOT / "docs" / "index.html").read_text(encoding="utf-8"))
    missing_links = []
    for reference in parser.references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or reference.startswith("#"):
            continue
        if not (ROOT / "docs" / unquote(parsed.path)).is_file():
            missing_links.append(reference)
    assert not missing_links, f"Missing gallery assets: {sorted(missing_links)}"
    print("Release checks passed: data, figures, gallery assets, and report are complete.")


if __name__ == "__main__":
    main()
