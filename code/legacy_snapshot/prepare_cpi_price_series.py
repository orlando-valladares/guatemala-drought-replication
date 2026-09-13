"""Create a clearly labelled constant-price companion to the MAGA maize series.

Input sources are left unchanged.  The output expresses the already selected
MAGA wholesale series in July 2026 national-CPI quetzales.  The official INE
series currently ends in July 2026, so later MAGA observations remain missing
in the real-price field rather than being deflated with an assumed CPI.
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MAGA = ROOT / "derived" / "maga_maize_prices_clean.csv"
CPI = ROOT.parents[1] / "sources" / "INE_IPC_Empalme_Base2024_100" / "IPC_empalme_republica_base_2024_100.xlsx"
OUT = ROOT / "derived" / "maga_maize_prices_real_jul2026_gtq.csv"

MONTHS = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4,
    "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8,
    "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}
CPI_COLUMN = "Índice año Base  2024=100.00 d/"
REFERENCE_YEAR = 2026
REFERENCE_MONTH = 7


def main() -> None:
    maga = pd.read_csv(MAGA)
    cpi = pd.read_excel(CPI, usecols=["Año", "Mes", CPI_COLUMN])
    cpi = cpi.rename(columns={"Año": "year", CPI_COLUMN: "national_cpi_base_2024_100"})
    cpi["month"] = cpi["Mes"].map(MONTHS)
    cpi = cpi.dropna(subset=["month", "national_cpi_base_2024_100"])
    cpi["month"] = cpi["month"].astype(int)
    cpi = cpi[["year", "month", "national_cpi_base_2024_100"]]

    reference = cpi.loc[
        (cpi["year"] == REFERENCE_YEAR) & (cpi["month"] == REFERENCE_MONTH),
        "national_cpi_base_2024_100",
    ]
    if len(reference) != 1:
        raise ValueError("Expected exactly one July 2026 CPI observation.")
    cpi_reference = float(reference.iloc[0])

    out = maga.merge(cpi, on=["year", "month"], how="left", validate="one_to_one")
    out["real_price"] = (
        out["monthly_mean_price_gtq_per_quintal"]
        * cpi_reference
        / out["national_cpi_base_2024_100"]
    )
    hist = out.loc[out["year"] <= 2025].groupby("month")["real_price"]
    out["real_hist_med"] = out["month"].map(hist.median())
    out["real_hist_p25"] = out["month"].map(hist.quantile(0.25))
    out["real_hist_p75"] = out["month"].map(hist.quantile(0.75))
    out["real_price_reference"] = "Constant July 2026 GTQ; national INE CPI, Base 2024=100"
    out["cpi_source_coverage"] = "Official INE CPI observed through July 2026; no imputed CPI"
    out.to_csv(OUT, index=False)
    print(f"Wrote {OUT.relative_to(ROOT)} with {len(out)} rows; reference CPI={cpi_reference:.6f}.")


if __name__ == "__main__":
    main()
