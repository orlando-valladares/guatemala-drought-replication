#!/usr/bin/env python3
'''Render Honduras-only and Guatemala--Honduras CHIRPS map bodies for TeX framing.'''
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely import make_valid

from build_honduras_chirps_data import load_geography

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = next(parent for parent in PROJECT.parents if parent.name == "01_workspace")
PLAYDATA = WORKSPACE / "02_projects" / "07_Playdata"
DERIVED = PROJECT / "derived"
FIGURES = PROJECT / "figures"
HONDURAS = FIGURES / "Honduras"
TABLES = HONDURAS / "Appendix" / "tables"
BODY = FIGURES / ".tex_body"
GT_MUNIS = PLAYDATA / "02_Guatemala" / "sources" / "JSON_Departamenos_Municipios_LugaresPoblados" / "Mapas-TopoJSON-Guatemala-main" / "munis.json"

GROUPS = ["0", "1-10", "11-25", "26-50", "51-75", "76-100"]
COLOURS = {"0":"#67000d", "1-10":"#cb181d", "11-25":"#fb6a4a", "26-50":"#fdd0a2", "51-75":"#9ecae1", "76-100":"#3182bd"}
LABELS = {"0":"0: below all 45 prior totals (record low)", "1-10":"1--10: exceptionally dry", "11-25":"11--25: dry", "26-50":"26--50: below median", "51-75":"51--75: above median", "76-100":"76--100: wet relative to history"}


def guatemala_geometry() -> gpd.GeoDataFrame:
    geo = gpd.read_file(GT_MUNIS)
    if geo.crs is None: geo = geo.set_crs("EPSG:4326")
    geo = geo.loc[~geo["id"].astype(str).eq("0") & ~geo["Departamento"].str.upper().eq("BELICE")].copy()
    geo.loc[~geo.geometry.is_valid,"geometry"] = geo.loc[~geo.geometry.is_valid,"geometry"].map(make_valid)
    geo["municipality_id"] = pd.to_numeric(geo["id"], errors="raise").astype(int)
    return geo.rename(columns={"Departamento":"department","Municipio":"municipality"})[["municipality_id","department","municipality","geometry"]]


def handles() -> list[Patch]:
    return [Patch(facecolor=COLOURS[group], edgecolor="white", label=LABELS[group]) for group in GROUPS]


def draw(ax, geo: gpd.GeoDataFrame, class_column: str = "percentile_group") -> None:
    for group in GROUPS:
        value = geo.loc[geo[class_column].eq(group)]
        if not value.empty: value.plot(ax=ax, color=COLOURS[group], edgecolor="white", linewidth=.10, zorder=1)
    missing = geo.loc[~geo[class_column].isin(GROUPS)]
    if not missing.empty: missing.plot(ax=ax, facecolor="#e5e7eb", edgecolor="#737373", linewidth=.15, hatch="....", zorder=2)
    ax.set_axis_off(); ax.set_aspect("equal")


def save(fig, stem: str) -> None:
    BODY.mkdir(parents=True, exist_ok=True)
    fig.savefig(BODY / f"honduras_{stem}_body.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def hnd_values(year: int, geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    data = pd.read_csv(DERIVED / "honduras_chirps_historical_comparison_municipality.csv")
    return geo.merge(data.loc[data.year.eq(year),["municipality_id","percentile_group"]], on="municipality_id", validate="one_to_one")


def gt_values(year: int, geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    data = pd.read_csv(DERIVED / "chirps_historical_comparison_2015_2019_2026_municipality.csv")
    return geo.merge(data.loc[data.year.eq(year),["municipality_id","percentile_group"]], on="municipality_id", validate="one_to_one")


def honduras_current(geo: gpd.GeoDataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.45,7.95), facecolor="white")
    draw(ax,hnd_values(2026,geo))
    ax.legend(handles=handles(),loc="lower left",fontsize=7.0,frameon=False,labelspacing=.45,handlelength=1.25)
    fig.tight_layout(); save(fig,"figH01a_honduras_percentile_2026")


def hnd_comparison(geo: gpd.GeoDataFrame, years: list[int], stem: str) -> None:
    national = pd.read_csv(DERIVED / "honduras_chirps_national_annual_1981_2025.csv").set_index("year")
    current = pd.read_csv(TABLES / "table_honduras_chirps_national_summary.csv").iloc[0]
    fig, axes = plt.subplots(1,3,figsize=(13.0,5.1),facecolor="white")
    for ax,year,panel in zip(axes,years,["(a)","(b)","(c)"],strict=True):
        draw(ax,hnd_values(year,geo))
        if year==2026: label=f"{panel} {year} (preliminary): {current.rain_2026_mm:.0f} mm; P{current.rainfall_historical_percentile:.1f}"
        else:
            historic=national.loc[year,"rain_may_aug_mm"]; p=100*(national.rain_may_aug_mm<=historic).mean(); label=f"{panel} {year} (final): {historic:.0f} mm; P{p:.1f}"
        ax.text(0,1.015,label,transform=ax.transAxes,fontsize=8.3,fontweight="bold")
    fig.legend(handles=handles(),loc="lower center",ncol=3,fontsize=7.1,frameon=False,bbox_to_anchor=(.5,.06),columnspacing=1.1,handlelength=1.25)
    fig.tight_layout(rect=(0,.09,1,1),w_pad=.15); save(fig,stem)


def combined_current(gt: gpd.GeoDataFrame, hn: gpd.GeoDataFrame, gt_country, hn_country) -> None:
    fig, ax=plt.subplots(figsize=(9.8,7.8),facecolor="white")
    draw(ax,pd.concat([gt_values(2026,gt),hnd_values(2026,hn)],ignore_index=True))
    gpd.GeoSeries([gt_country,hn_country],crs="EPSG:4326").boundary.plot(ax=ax,color="#111111",linewidth=.65,zorder=5)
    ax.legend(handles=handles()+[Line2D([0],[0],color="#111111",lw=.65,label="International boundary")],loc="lower left",fontsize=7.0,frameon=False,labelspacing=.4,handlelength=1.25)
    fig.tight_layout(); save(fig,"figH01d_guatemala_honduras_percentile_2026")


def combined_historical(gt: gpd.GeoDataFrame, hn: gpd.GeoDataFrame, gt_country, hn_country) -> None:
    fig, axes=plt.subplots(1,3,figsize=(13.0,5.1),facecolor="white")
    for ax,year,panel in zip(axes,[2015,2019,2026],["(a)","(b)","(c)"],strict=True):
        draw(ax,pd.concat([gt_values(year,gt),hnd_values(year,hn)],ignore_index=True))
        gpd.GeoSeries([gt_country,hn_country],crs="EPSG:4326").boundary.plot(ax=ax,color="#111111",linewidth=.55,zorder=5)
        ax.text(0,1.015,f"{panel} {year}" + (" (preliminary)" if year==2026 else " (final)"),transform=ax.transAxes,fontsize=8.3,fontweight="bold")
    fig.legend(handles=handles()+[Line2D([0],[0],color="#111111",lw=.55,label="International boundary")],loc="lower center",ncol=3,fontsize=7.0,frameon=False,bbox_to_anchor=(.5,.06),columnspacing=1.05,handlelength=1.25)
    fig.tight_layout(rect=(0,.09,1,1),w_pad=.15); save(fig,"figH01e_guatemala_honduras_driest_years_2015_2019_2026")


def main() -> None:
    country, _, hn = load_geography()
    gt = guatemala_geometry()
    honduras_current(hn)
    hnd_comparison(hn,[2015,2019,2026],"figH01b_honduras_driest_years_2015_2019_2026")
    hnd_comparison(hn,[2024,2025,2026],"figH01c_honduras_recent_years_2024_2025_2026")
    combined_current(gt,hn,gt.geometry.union_all(),country.geometry.iloc[0])
    combined_historical(gt,hn,gt.geometry.union_all(),country.geometry.iloc[0])
    print("Built five Honduras/combined map bodies for TeX framing.")

if __name__ == "__main__": main()
