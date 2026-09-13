'''Frame figure bodies with reproducible LaTeX titles, subtitles, and notes.

Stata produces all non-map vector bodies; Python produces the map bodies. This
script writes one public .tex source and one public PNG per figure. LaTeX PDFs,
logs, and vector bodies stay in figures/.tex_body/ so the deliverable library
contains only the user-facing TeX/PNG pairs.
'''
from __future__ import annotations

import csv
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
FIGURES = PROJECT / "figures"
APPENDIX = FIGURES / "Appendix"
TABLES = APPENDIX / "tables"
BODY = FIGURES / ".tex_body"
BUILD = BODY / "tex"


def tex_escape(text: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in text)


def tex_document(title: str, subtitle: str, notes: str, graphic: str, paper: tuple[str, str], width: str) -> str:
    width_paper, height_paper = paper
    return f'''\\documentclass[10pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[paperwidth={width_paper},paperheight={height_paper},margin=0.30in]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{xcolor}}
\\usepackage{{helvet}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\setlength{{\\parindent}}{{0pt}}
\\begin{{document}}
\\thispagestyle{{empty}}
{{\\large\\bfseries {tex_escape(title)}\\par}}
\\vspace{{2pt}}
{{\\small\\color{{black!62}} {tex_escape(subtitle)}\\par}}
\\vspace{{6pt}}
\\begin{{center}}
\\includegraphics[width={width}]{{{graphic}}}
\\end{{center}}
\\vspace{{2pt}}
{{\\scriptsize\\textit{{Notes.}} {tex_escape(notes)}\\par}}
\\end{{document}}
'''


def table_fragment(rows: list[dict[str, str]]) -> str:
    panel_titles = {
        "A": "Panel A. Guatemala y Corredor Seco",
        "B": "Panel B. Departamentos",
        "C": "Panel C. Municipios de campo",
    }
    lines: list[str] = []
    current_panel = ""
    current_section = ""
    for row in rows:
        panel = row["panel"]
        if panel != current_panel:
            if current_panel:
                lines.append(r"\addlinespace[3pt]")
            lines.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\textit{{{panel_titles[panel]}}}}} \\")
            current_panel = panel
            current_section = ""
        section = row["section"]
        if section and section != current_section:
            lines.append(r"\addlinespace[2pt]")
            lines.append(rf"\multicolumn{{6}}{{@{{}}l}}{{\hspace{{0.18in}}\textit{{{tex_escape(section)}}}}} \\")
            current_section = section
        label = tex_escape(row["area"])
        if int(float(row["indent"])):
            label = r"\hspace{0.18in}" + label
        historic = rf"\shortstack[r]{{{float(row['historical_mean_mm']):.1f}\\({float(row['historical_sd_mm']):.1f})}}"
        lines.append(
            f"{label} & {historic} & {float(row['rain_2026_mm']):.1f} & "
            f"{float(row['deviation_pct_vs_historical_mean']):.1f}\\% & "
            f"{float(row['z_score_2026']):.2f} & {tex_escape(row['historical_rank_display'])} \\\\"
        )
    data_rows = "\n".join(lines)
    return rf'''\begingroup
\setstretch{{1.0}}
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{0.96}}
\begin{{longtable}}{{@{{}}p{{1.72in}}rrrrr@{{}}}}
\multicolumn{{6}}{{c}}{{\footnotesize\textbf{{Tabla A1. Estadísticas resumen de precipitación CHIRPS de mayo a agosto}}}} \\
\multicolumn{{6}}{{c}}{{\scriptsize Referencia histórica: 1981--2025 (45 agregados anuales); 2026 es final.}} \\
\vspace{{2pt}}\\
\toprule
Área & \shortstack{{Lluvia histórica\\(mm)}} & \shortstack{{Lluvia 2026\\(mm)}} & \shortstack{{$\Delta$ vs. media\\histórica (\%)}} & \shortstack{{z-score\\2026}} & \shortstack{{Rango\\histórico}} \\
\midrule
\endfirsthead
\multicolumn{{6}}{{c}}{{\scriptsize\textit{{Tabla A1. Estadísticas resumen de precipitación CHIRPS de mayo a agosto (continúa)}}}} \\
\toprule
Área & \shortstack{{Lluvia histórica\\(mm)}} & \shortstack{{Lluvia 2026\\(mm)}} & \shortstack{{$\Delta$ vs. media\\histórica (\%)}} & \shortstack{{z-score\\2026}} & \shortstack{{Rango\\histórico}} \\
\midrule
\endhead
\bottomrule
\endfoot
\bottomrule
\endlastfoot
{data_rows}
\multicolumn{{6}}{{@{{}}p{{\textwidth}}@{{}}}}{{\scriptsize\RaggedRight\textit{{Notas.}} Fuente: CHIRPS v3. Para cada área y año, la precipitación acumulada de mayo--agosto se agrega directamente del ráster con celdas ponderadas por área; las estadísticas históricas se calculan después sobre los 45 agregados anuales de 1981--2025. La primera línea de ``Lluvia histórica'' es la media y el número entre paréntesis es la desviación estándar. El z-score es la diferencia entre la lluvia de 2026 y su media histórica, dividida por la desviación estándar histórica. El rango ordena 2026 entre 46 temporadas, de menor a mayor lluvia (1 = menor). ``Corredor Seco'' es la definición base SESAN; ``Corredor Seco ampliado'' es la lista actual de 160 municipios. Son clasificaciones anidadas, no categorías mutuamente excluyentes.}} \\
\end{{longtable}}
\endgroup
'''



def table_document(fragment: str) -> str:
    return rf'''\documentclass[12pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[paperwidth=8.5in,paperheight=11in,margin=0.75in]{{geometry}}
\usepackage{{booktabs,array,xcolor,helvet,ragged2e,setspace,longtable}}
\renewcommand{{\familydefault}}{{\sfdefault}}
\setlength{{\parindent}}{{0pt}}
\begin{{document}}
\thispagestyle{{empty}}
{fragment}
\end{{document}}
'''

def run_tex(tex_path: Path, png_path: Path) -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    source = tex_path.relative_to(PROJECT)
    output_dir = BUILD.relative_to(PROJECT)
    result = subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={output_dir}", str(source)],
        cwd=PROJECT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise RuntimeError(f"LaTeX failed for {tex_path.name}:\\n{result.stdout[-4000:]}")
    pdf = BUILD / f"{tex_path.stem}.pdf"
    if not pdf.exists():
        raise FileNotFoundError(pdf)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = png_path.with_suffix("")
    result = subprocess.run(["pdftoppm", "-png", "-r", "300", "-singlefile", str(pdf), str(prefix)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode or not png_path.exists():
        raise RuntimeError(f"PNG conversion failed for {tex_path.name}: {result.stdout}")


def run_table_tex(tex_path: Path, png_path: Path) -> None:
    """Compile a potentially multi-page table and make one complete PNG preview."""
    run_tex(tex_path, png_path)
    pdf = BUILD / f"{tex_path.stem}.pdf"
    prefix = BUILD / f"{tex_path.stem}_page"
    result = subprocess.run(
        ["pdftoppm", "-png", "-r", "300", str(pdf), str(prefix)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    pages = sorted(BUILD.glob(f"{tex_path.stem}_page-*.png"))
    if result.returncode or not pages:
        raise RuntimeError(f"Multi-page PNG conversion failed for {tex_path.name}: {result.stdout}")
    if len(pages) == 1:
        pages[0].replace(png_path)
        return
    from PIL import Image
    images = [Image.open(page).convert("RGB") for page in pages]
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    combined = Image.new("RGB", (width, height), "white")
    offset = 0
    for image in images:
        combined.paste(image, ((width - image.width) // 2, offset))
        offset += image.height
        image.close()
    combined.save(png_path)
    combined.close()
    for page in pages:
        page.unlink(missing_ok=True)
    if not png_path.exists():
        raise RuntimeError(f"PNG assembly failed for {tex_path.name}.")


def publish(
    stem: str,
    title: str,
    subtitle: str,
    notes: str,
    paper: tuple[str, str],
    width: str = r"0.98\textwidth",
    appendix: bool = False,
    body_appendix: bool | None = None,
) -> None:
    folder = APPENDIX if appendix else FIGURES
    use_appendix_body = appendix if body_appendix is None else body_appendix
    body_name = ("appendix_" if use_appendix_body else "") + stem + "_body.pdf"
    body = BODY / body_name
    if not body.exists():
        raise FileNotFoundError(f"Missing figure body: {body}")
    tex_path = folder / f"{stem}.tex"
    tex_path.write_text(tex_document(title, subtitle, notes, body.relative_to(PROJECT).with_suffix("").as_posix(), paper, width), encoding="utf-8")
    run_tex(tex_path, folder / f"{stem}.png")


def main() -> None:
    main_figures = [
        ("fig01a_chirps_percentile_2026", "Municipal May--August rainfall rarity in Guatemala", "CHIRPS v3; municipality area-weighted cumulative rainfall; 1 May--31 August 2026 (final)", "Fill reports the empirical percentile of each municipality’s 2026 cumulative rainfall relative to the same calendar window in 1981--2025. Dark red 0 is deliberately distinct from 1--10: it denotes a total below all 45 prior totals. This is a meteorological measure, not crop or yield loss.", ("8.5in", "10.8in")),
        ("fig01b_chirps_driest_years_2015_2019_2026", "Municipal rainfall rarity: 2015, 2019 and 2026 on a retrospective common scale", "CHIRPS v3; municipality area-weighted cumulative rainfall; May--August; 2015--2019 final and 2026 final", "Each focal year is compared with all other annual totals in 1981--2026, excluding itself. A zero percentile is lower rainfall than each of the other 45 totals. This retrospective reference includes final 2026 when comparing 2015 and 2019, so it is not a contemporaneous-record measure.", ("13.5in", "6.8in")),
        ("fig01g_chirps_common_reference_zscore_2015_2019_2025", "Municipal May--August rainfall z-scores: 2015, 2019 and 2025", "CHIRPS v3; municipality area-weighted cumulative rainfall; common 1981--2025 municipal reference; millimetres", "Each panel uses the same local 1981--2025 historical mean and standard deviation. Blue indicates z-scores at or above zero; increasingly warm colours indicate increasingly negative standardized rainfall anomalies. This is a meteorological comparison, not crop or yield loss.", ("13.5in", "6.8in")),
        ("fig01d_sesan_corridor_definitions", "SESAN dry-corridor definitions used in this report", "Administrative priority lists; Guatemala municipality polygons; not a measured drought surface", "Solid line: municipalities in the older/core list transcribed from the SESAN 2016 annex (67 matched polygons). Dashed line: municipalities in the existing current 160-municipality expanded indicator but outside the older list (93). The 2016 prose says 66 municipalities; its enumerated annex matches 67 polygons, so the discrepancy is retained.", ("8.5in", "10.8in")),
        ("fig01e_chirps_sesan_overlap_2026", "2026 rainfall rarity and SESAN dry-corridor definitions", "CHIRPS v3 municipality rainfall, 1 May--31 August 2026 (final); SESAN administrative outlines", "Fill: municipality area-weighted CHIRPS cumulative-rainfall percentile relative to 1981--2025. Lines: SESAN administrative priority lists. Their overlap is descriptive; it neither establishes causality nor measures crop or yield loss.", ("8.5in", "10.8in")),
        ("fig02a_chirps_department_rainfall_sd_rank", "Departmental rainfall: historical variability and the 2026 shock", "CHIRPS v3; department area-weighted cumulative rainfall; 1 May--31 August 2026 (final); millimetres", "Departments are ordered by their 2026 z-score, from most negative at top. Whiskers show the descriptive 1981--2025 mean plus or minus one standard deviation, not confidence intervals. The aligned right column reports empirical percentile and z-score.", ("10.2in", "8.2in")),
        ("fig02b_chirps_department_zscore_rank", "Departmental ranking by 2026 rainfall z-score", "CHIRPS v3; department area-weighted cumulative rainfall; 1 May--31 August 2026 (final)", "A z-score is the 2026 rainfall total minus the department’s 1981--2025 mean, divided by its historical standard deviation. More negative values indicate drier conditions relative to that department’s own distribution. Point labels report empirical percentiles.", ("10.2in", "8.2in")),
        ("fig03a_chirps_municipality_zscore_rank", "All Guatemala municipalities ranked by 2026 rainfall z-score", "CHIRPS v3; municipality area-weighted cumulative rainfall; 1 May--31 August 2026 (final)", "All 340 analytical municipalities are ordered by their z-score relative to their own 1981--2025 distribution. The three field municipalities are highlighted; their labels include z-score and empirical percentile.", ("9.0in", "16.0in"), r"0.96\textwidth"),
        ("fig03b_chirps_municipality_rainfall_sd_compact", "All Guatemala municipalities: rainfall level, historical variability, and 2026", "CHIRPS v3; municipality area-weighted cumulative rainfall; 1 May--31 August 2026 (final); millimetres", "Municipalities are sorted from the most negative 2026 z-score at top to the least negative at bottom. Whiskers show descriptive 1981--2025 mean plus or minus one standard deviation, not confidence intervals. The aligned right column reports municipality, department, and percentile.", ("9.0in", "30.0in"), r"8.0in"),
    ]
    for spec in main_figures:
        publish(*spec)
    recent_years_appendix = (
        "fig01c_chirps_recent_years_2024_2025_2026",
        "Municipal rainfall rarity: the two most recent final years and 2026",
        "CHIRPS v3; municipality area-weighted cumulative rainfall; May--August; 2024--2025 final and 2026 final",
        "Each panel ranks rainfall only against years available at the time: 1981--2023 for 2024, 1981--2024 for 2025, and 1981--2025 for 2026. A zero percentile is lower rainfall than every earlier available year. Field municipalities are labelled in the 2026 panel.",
        ("13.5in", "6.8in"),
    )
    publish(*recent_years_appendix, appendix=True, body_appendix=False)
    for suffix in (".tex", ".png"):
        (FIGURES / f"fig01c_chirps_recent_years_2024_2025_2026{suffix}").unlink(missing_ok=True)

    appendix_figures = [
        ("app01_fao_asis_municipality_map", "FAO ASIS agricultural vegetation stress", "Cropland; Growing Season 1; August Dekad 1, 2026; municipality fractional-pixel area-weighted raster statistic", "Unit: percentage of valid in-season cropland area affected by drought-related vegetation stress under FAO’s methodology. ASIS is not a percentage of crop or yield loss. Municipalities with no valid in-season raster cells are hatched.", ("8.5in", "10.8in")),
        ("app02_chirps_three_sites_sd", "Field municipalities on their own historical rainfall scales", "CHIRPS v3; municipality area-weighted cumulative rainfall; 1 May--31 August 2026 (final); millimetres", "Whiskers show each municipality’s descriptive 1981--2025 mean plus or minus one standard deviation, not confidence intervals. Labels report the 2026 z-score and empirical historical percentile.", ("9.0in", "6.4in")),
        ("app03_chirps_zscore_distribution", "Distribution of municipal 2026 rainfall z-scores", "CHIRPS v3; 340 municipality area-weighted May--August rainfall observations; 2026 final", "Each z-score compares a municipality’s 2026 cumulative rainfall with its own 1981--2025 mean and standard deviation. More negative values indicate drier conditions relative to local historical variability.", ("9.0in", "6.4in")),
        ("app04_chirps_site_annual_series", "Historical May--August rainfall at the three field sites", "CHIRPS v3; municipality area-weighted cumulative rainfall; 1981--2025 final and 2026 final; millimetres", "The identical 1 May--31 August window is used in every year. The final point for each municipality is final 2026; this time series describes rainfall, not crop loss.", ("9.0in", "6.4in")),
        ("app05_fao_asis_distribution", "Distribution of municipal FAO ASIS values", "FAO ASIS Cropland, Growing Season 1, August Dekad 1, 2026; municipality fractional-pixel area-weighted statistic", "ASIS reports the percentage of valid in-season cropland area affected by drought-related vegetation stress under the FAO method. It is a vegetation-stress measure, not a percentage yield loss.", ("9.0in", "6.4in")),
        ("app06_chirps_zscore_vs_fao_asis", "Meteorological rainfall rarity and agricultural vegetation stress", "CHIRPS May--August 2026 z-score (final) and FAO ASIS Cropland GS1, August Dekad 1, 2026", "Descriptive municipal comparison only. CHIRPS measures meteorological rainfall; ASIS measures drought-related vegetation stress in valid in-season cropland. Neither axis should be interpreted as crop or yield loss, and the figure does not estimate a causal relationship.", ("9.0in", "6.4in")),
        ("app07_budget_scenarios", "Illustrative monthly maize-liquidity scenarios", "ENIGH rural expenditure basis and MAGA La Terminal wholesale white-maize benchmark; GTQ per month; scenario-based", "Low, central, and high cases vary transparent assumptions about own production and the fraction unavailable. They are not observed crop loss, agricultural-income loss, or causal drought effects.", ("9.0in", "6.4in")),
        ("app08_maga_maize_recent_years_nominal", "Recent wholesale white-maize prices", "MAGA La Terminal daily quotes aggregated to monthly means; first-quality white maize; GTQ per quintal; nominal", "The series is wholesale La Terminal, not retail or field-site pricing. 2026 is incomplete through 21 August. It describes contemporaneous purchasing conditions and does not attribute price changes to drought.", ("9.0in", "6.4in")),
        ("app09_maga_maize_2026_seasonal_benchmark_nominal", "2026 wholesale white-maize price against its seasonal history", "MAGA La Terminal monthly mean; first-quality white maize; GTQ per quintal; nominal; 2026 through 21 August", "The band and median use the same calendar month in 2012--2025. The series is a wholesale benchmark, not a local retail price or an estimate of a drought-induced price effect.", ("9.0in", "6.4in")),
        ("app10_maga_maize_2026_seasonal_benchmark_real_jul2026_gtq", "2026 wholesale white-maize price against seasonal history, CPI-adjusted", "MAGA La Terminal monthly mean deflated by official national INE CPI; constant July-2026 GTQ per quintal", "The CPI currently ends in July 2026, so August is not deflated or imputed. The band and median use the same calendar month in 2012--2025; this remains a wholesale benchmark rather than a field-site retail price.", ("9.0in", "6.4in")),
    ]
    for spec in appendix_figures:
        publish(*spec, appendix=True)
    with (TABLES / "table_chirps_summary_statistics.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    fragment = table_fragment(rows)
    table_body = TABLES / "table_chirps_summary_statistics_body.tex"
    table_body.write_text(fragment, encoding="utf-8")
    table_tex = TABLES / "table_chirps_summary_statistics.tex"
    table_tex.write_text(table_document(fragment), encoding="utf-8")
    run_table_tex(table_tex, TABLES / "table_chirps_summary_statistics.png")
    print("Published TeX/PNG pairs for 20 figures and the CHIRPS summary-statistics table.")


if __name__ == "__main__":
    main()
