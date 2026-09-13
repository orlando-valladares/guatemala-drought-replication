#!/usr/bin/env python3
'''Write public Honduras TeX/PNG figure pairs and a Guatemala comparison table.'''
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from build_tex_figures import run_tex, tex_document

PROJECT = Path(__file__).resolve().parents[1]
FIGURES = PROJECT / "figures"
HONDURAS = FIGURES / "Honduras"
APPENDIX = HONDURAS / "Appendix"
TABLES = APPENDIX / "tables"
BODY = FIGURES / ".tex_body"
DERIVED = PROJECT / "derived"


def publish(stem: str, title: str, subtitle: str, notes: str, paper: tuple[str,str], width: str=r"0.98\textwidth", appendix: bool=False) -> None:
    folder = APPENDIX if appendix else HONDURAS
    body = BODY / f"honduras_{stem}_body.pdf"
    if not body.exists(): raise FileNotFoundError(body)
    tex = folder / f"{stem}.tex"
    tex.write_text(tex_document(title,subtitle,notes,body.relative_to(PROJECT).with_suffix("").as_posix(),paper,width),encoding="utf-8")
    run_tex(tex,folder/f"{stem}.png")


def summary_table_tex(national: dict[str, float], departments: pd.DataFrame) -> str:
    national_row = f"Honduras & {national['rain']:.1f} & {national['p10']:.1f} & {national['median']:.1f} & {national['p90']:.1f} & P{national['percentile']:.1f} & {national['z']:.2f} \\\\"
    department_rows = "\n".join(
        f"{row.department} & {row.rain_2026_may_aug_mm:.1f} & {row.historical_p10_may_aug_mm:.1f} & {row.historical_median_may_aug_mm:.1f} & {row.historical_p90_may_aug_mm:.1f} & P{row.rainfall_historical_percentile:.1f} & {row.rainfall_z_score_vs_1981_2025:.2f} \\\\" for row in departments.itertuples(index=False)
    )
    return f'''\\documentclass[9pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[paperwidth=11.8in,paperheight=9.3in,margin=.36in]{{geometry}}
\\usepackage{{booktabs,array,xcolor,helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\setlength{{\\parindent}}{{0pt}}
\\begin{{document}}
\\thispagestyle{{empty}}
{{\\large\\bfseries Table H1. Honduras CHIRPS May--August rainfall summary statistics\\par}}
\\vspace{{2pt}}
{{\\small\\color{{black!62}} Equal-area weighted cumulative rainfall; historical reference 1981--2025; 2026 is preliminary.\\par}}
\\vspace{{7pt}}
\\renewcommand{{\\arraystretch}}{{1.20}}
\\begin{{center}}
\\begin{{tabular}}{{lrrrrrr}}
\\toprule
Area & 2026 rainfall & Historical P10 & Historical median & Historical P90 & 2026 percentile & z-score \\\\
 & (mm) & (mm) & (P50, mm) & (mm) & & \\\\
\\midrule
\\multicolumn{{7}}{{l}}{{\\textit{{Panel A. National total}}}} \\\\
{national_row}
\\addlinespace[6pt]
\\multicolumn{{7}}{{l}}{{\\textit{{Panel B. Departments, ordered by 2026 z-score}}}} \\\\
{department_rows}
\\bottomrule
\\end{{tabular}}
\\end{{center}}
\\vfill
{{\\scriptsize\\textit{{Notes.}} The first numeric column is the observed preliminary 2026 cumulative rainfall. P10, P50, and P90 are department- or country-specific percentiles of the 45 historical May--August totals. The 2026 percentile is the share of those 45 historical totals less than or equal to 2026; a low value is unusually dry. The z-score is relative to the same 1981--2025 distribution. CHIRPS measures meteorological rainfall, not crop loss.\\par}}
\\end{{document}}
'''


def write_summary_table() -> None:
    annual = pd.read_csv(TABLES / "honduras_chirps_national_annual_1981_2025.csv")
    national_summary = pd.read_csv(TABLES / "table_honduras_chirps_national_summary.csv").iloc[0]
    department = pd.read_csv(TABLES / "honduras_chirps_department_graph_data.csv").sort_values("rainfall_z_score_vs_1981_2025")
    values = annual["rain_may_aug_mm"].to_numpy(float)
    national = {
        "rain": float(national_summary.rain_2026_mm),
        "p10": float(np.quantile(values, .10)),
        "median": float(np.median(values)),
        "p90": float(np.quantile(values, .90)),
        "percentile": float(national_summary.rainfall_historical_percentile),
        "z": float(national_summary.rainfall_z_score),
    }
    national_frame = pd.DataFrame([{
        "panel": "A. National total", "area": "Honduras", "rain_2026_may_aug_mm": national["rain"],
        "historical_p10_may_aug_mm": national["p10"], "historical_median_may_aug_mm": national["median"],
        "historical_p90_may_aug_mm": national["p90"], "rainfall_historical_percentile": national["percentile"],
        "rainfall_z_score_vs_1981_2025": national["z"],
    }])
    department_frame = department[["department", "rain_2026_may_aug_mm", "historical_p10_may_aug_mm", "historical_median_may_aug_mm", "historical_p90_may_aug_mm", "rainfall_historical_percentile", "rainfall_z_score_vs_1981_2025"]].rename(columns={"department": "area"}).copy()
    department_frame.insert(0, "panel", "B. Departments")
    pd.concat([national_frame, department_frame], ignore_index=True).to_csv(TABLES / "table_honduras_chirps_summary_statistics.csv", index=False)
    tex = TABLES / "table_honduras_chirps_summary_statistics.tex"
    tex.write_text(summary_table_tex(national, department), encoding="utf-8")
    run_tex(tex, TABLES / "table_honduras_chirps_summary_statistics.png")

def main() -> None:
    HONDURAS.mkdir(parents=True,exist_ok=True); APPENDIX.mkdir(parents=True,exist_ok=True); TABLES.mkdir(parents=True,exist_ok=True)
    figures=[
      ("figH01a_honduras_percentile_2026","Municipal May--August rainfall rarity in Honduras","CHIRPS v3; municipality equal-area weighted cumulative rainfall; 1 May--31 August 2026 (preliminary)","Fill reports the empirical percentile of each municipality’s 2026 cumulative rainfall relative to the same calendar window in 1981--2025. Dark red 0 is distinct from 1--10: it denotes a total below all 45 prior totals. This is a meteorological measure, not crop or yield loss.",("8.5in","10.8in")),
      ("figH01b_honduras_driest_years_2015_2019_2026","Honduras municipal rainfall rarity: two driest historical national years and 2026","CHIRPS v3; municipality equal-area weighted cumulative rainfall; May--August; historical panels final and 2026 preliminary","2015 and 2019 are the two lowest Honduras national equal-area weighted May--August totals in the local 1981--2025 historical raster. Historical-year percentiles include the focal year; 2026 is benchmarked against 1981--2025.",("13.5in","6.8in")),
      ("figH01c_honduras_recent_years_2024_2025_2026","Honduras municipal rainfall rarity: the two most recent final years and 2026","CHIRPS v3; municipality equal-area weighted cumulative rainfall; May--August; 2024--2025 final and 2026 preliminary","The panels use identical municipal percentile classes. Historical-year percentiles include the focal year. The 2026 panel is preliminary and benchmarked against 1981--2025.",("13.5in","6.8in")),
      ("figH01d_guatemala_honduras_percentile_2026","Guatemala and Honduras: municipal rainfall rarity in 2026","CHIRPS v3; country-specific municipality equal-area weighted cumulative rainfall; 1 May--31 August 2026 (preliminary)","Each municipality’s percentile is benchmarked against its own country’s 1981--2025 local May--August distribution; colour classes are therefore comparable as rainfall rarity, not as absolute millimetres. Dark red 0 means a local record low.",("10.5in","8.6in")),
      ("figH01e_guatemala_honduras_driest_years_2015_2019_2026","Guatemala and Honduras: shared historically dry years and 2026","CHIRPS v3; municipality equal-area weighted cumulative rainfall; May--August; 2015--2019 final and 2026 preliminary","2015 and 2019 are the two lowest national May--August years in both local historical rasters. Every municipality is benchmarked against its own 1981--2025 distribution. The final panel is preliminary 2026.",("13.5in","6.8in")),
      ("figH02a_honduras_department_rainfall_sd_rank","Honduras departmental rainfall: historical variability and the 2026 shock","CHIRPS v3; department equal-area weighted cumulative rainfall; 1 May--31 August 2026 (preliminary); millimetres","Departments are ordered by 2026 z-score, most negative at top. Whiskers show descriptive 1981--2025 mean plus or minus one standard deviation, not confidence intervals. The aligned right column reports empirical percentile and z-score.",("10.2in","8.2in")),
      ("figH02b_honduras_department_zscore_rank","Honduras departments ranked by 2026 rainfall z-score","CHIRPS v3; department equal-area weighted cumulative rainfall; 1 May--31 August 2026 (preliminary)","A z-score is 2026 rainfall minus the department’s 1981--2025 mean, divided by its historical standard deviation. More negative values indicate drier conditions relative to that department’s distribution. Point labels report empirical percentiles.",("10.2in","8.2in")),
      ("figH03a_honduras_municipality_zscore_rank","All Honduras municipalities ranked by 2026 rainfall z-score","CHIRPS v3; 298 municipality equal-area weighted cumulative-rainfall observations; 1 May--31 August 2026 (preliminary)","All 298 municipality records are ordered by their z-score relative to their own 1981--2025 distribution. More negative values represent unusually dry conditions relative to local historical variability.",("9.0in","15.0in"),r"0.96\textwidth"),
      ("figH03b_honduras_municipality_rainfall_sd_compact","All Honduras municipalities: rainfall level, historical variability, and 2026","CHIRPS v3; municipality equal-area weighted cumulative rainfall; 1 May--31 August 2026 (preliminary); millimetres","Municipalities sort from the most negative 2026 z-score at top to the least negative at bottom. Whiskers are descriptive 1981--2025 mean plus or minus one standard deviation, not confidence intervals. The aligned right column reports municipality, department, and percentile.",("9.0in","27.0in"),r"8.0in"),
    ]
    for item in figures: publish(*item)
    appendix=[
      ("appH01_honduras_national_annual_rainfall","Honduras national May--August rainfall history","CHIRPS v3; national equal-area weighted cumulative rainfall; 1981--2025 final and 2026 preliminary; millimetres","The same 1 May--31 August window is used in every year. The 2026 point is preliminary; the series describes meteorological rainfall and not crop loss or household impacts.",("9.0in","6.4in")),
      ("appH02_honduras_municipal_zscore_distribution","Distribution of Honduras municipal 2026 rainfall z-scores","CHIRPS v3; 298 municipality equal-area weighted May--August rainfall observations; 2026 preliminary","Each z-score compares a municipality’s 2026 cumulative rainfall with its own 1981--2025 mean and standard deviation. More negative values indicate drier conditions relative to local historical variability.",("9.0in","6.4in")),
    ]
    for item in appendix: publish(*item,appendix=True)
    write_summary_table()
    print("Published Honduras TeX/PNG pairs and country/department summary table.")

if __name__ == "__main__": main()
