version 19.5
clear all
set more off
set scheme s2color
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
cap mkdir "figures/Appendix"
cap mkdir "figures/.tex_body"
local region "graphregion(color(white) margin(medium)) plotregion(color(white) margin(small))"
capture program drop export_app
program define export_app
    args stem
    graph export "figures/.tex_body/appendix_`stem'_body.pdf", replace
end
* Appendix 02: the three field municipalities on their historical rainfall scales.
import delimited using "figures/Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
keep if inlist(municipality, "Olopa", "Chahal", "Patzité")
sort rainfall_z_score_vs_1981_2025
gen order = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
gen label_x = upper + 65
gen stat_label = "z=" + strtrim(string(rainfall_z_score_vs_1981_2025, "%4.2f")) + "; P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
local ylabs
forvalues i = 1/3 {
    local site = municipality[`i']
    local dep = department[`i']
    local ylabs `"`ylabs' `i' `"`site', `dep'"'"'
}
twoway ///
    (rcap lower upper order, horizontal lcolor(gs10) lwidth(medthin)) ///
    (scatter order historical_mean_may_aug_mm, msymbol(Oh) mcolor(gs6) msize(small)) ///
    (scatter order historical_median_may_aug_mm, msymbol(Dh) mcolor(gs3) msize(small)) ///
    (scatter order rain_2026_may_aug_mm, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(medsmall)) ///
    (scatter order label_x, msymbol(none) mlabel(stat_label) mlabpos(3) mlabsize(small) mlabcolor(black)), ///
    `region' yscale(reverse range(.5 3.5)) ylabel(`ylabs', angle(0) labsize(small) nogrid) ///
    xscale(range(0 2250)) xlabel(0(500)2000, labsize(small)) ///
    xtitle("May-August cumulative rainfall (mm)", size(small)) ytitle("") ///
    legend(order(2 "1981-2025 mean" 1 "mean +/- 1 SD" 3 "historical median" 4 "2026 final") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app02_chirps_three_sites_sd"
* Appendix 03: national distribution of municipality-specific z-scores.
import delimited using "figures/Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
histogram rainfall_z_score_vs_1981_2025, percent width(.25) color("158 202 225") lcolor(white) ///
    `region' xline(-2 -1 0, lcolor("150 0 24" "217 95 14" gs7) lpattern(dash dash solid) lwidth(vthin vthin thin)) ///
    xtitle("2026 May–August rainfall z-score", size(small)) ytitle("Percent of municipalities", size(small)) ///
    ylabel(, angle(0) nogrid labsize(small)) legend(off)
export_app "app03_chirps_zscore_distribution"
* Appendix 04: historical site trajectories.
import delimited using "figures/Appendix/tables/chirps_site_annual_series.csv", clear varnames(1)
twoway ///
    (line rain_may_aug_mm year if municipality=="Olopa", lcolor("150 0 24") lwidth(medthick)) ///
    (line rain_may_aug_mm year if municipality=="Chahal", lcolor(black) lpattern(dash) lwidth(medthick)) ///
    (line rain_may_aug_mm year if municipality=="Patzité", lcolor(gs5) lpattern(shortdash) lwidth(medthick)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Olopa", msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(small)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Chahal", msymbol(S) mcolor(black) mfcolor(white) msize(small)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Patzité", msymbol(T) mcolor(gs5) mfcolor(gs5) msize(small)), ///
    `region' xline(2026, lcolor(gs9) lpattern(dash) lwidth(vthin)) ///
    xlabel(1981(5)2026, angle(45) labsize(vsmall)) ylabel(, angle(0) nogrid labsize(small)) ///
    xtitle("Year") ytitle("May–August cumulative rainfall (mm)", size(small)) ///
    legend(order(1 "Olopa" 2 "Chahal" 3 "Patzité" 4 "2026 final") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app04_chirps_site_annual_series"
* Appendix 05–06: FAO ASIS distribution and descriptive CHIRPS relationship.
import delimited using "figures/Appendix/tables/chirps_fao_graph_data.csv", clear varnames(1)
histogram asis_value if !missing(asis_value), percent width(5) color("107 174 214") lcolor(white) ///
    `region' xtitle("FAO ASIS (% valid in-season cropland area affected)", size(small)) ytitle("Percent of municipalities", size(small)) ///
    ylabel(, angle(0) nogrid labsize(small)) legend(off)
export_app "app05_fao_asis_distribution"
twoway ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if field_site==0 & !missing(asis_value), msymbol(O) msize(tiny) mcolor(gs11) mfcolor(gs11)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Olopa", msymbol(D) msize(medsmall) mcolor("150 0 24") mfcolor("150 0 24") mlabel(municipality) mlabpos(3) mlabsize(small)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Chahal", msymbol(S) msize(medsmall) mcolor(black) mfcolor(white) mlabel(municipality) mlabpos(3) mlabsize(small)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Patzité", msymbol(T) msize(medsmall) mcolor(gs5) mfcolor(gs5) mlabel(municipality) mlabpos(3) mlabsize(small)), ///
    `region' xline(0, lcolor(gs8) lpattern(dash) lwidth(vthin)) ///
    xtitle("CHIRPS 2026 rainfall z-score (more negative = drier)", size(small)) ytitle("FAO ASIS (% valid in-season cropland area affected)", size(small)) ///
    ylabel(, angle(0) nogrid labsize(small)) ///
    legend(order(1 "Other municipalities" 2 "Olopa" 3 "Chahal" 4 "Patzité") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app06_chirps_zscore_vs_fao_asis"
* Appendix 07: scenario-based liquidity exercise.
import delimited using "figures/Appendix/tables/budget_scenarios_graph_data.csv", clear varnames(1)
graph bar additional_monthly_maize_cash_re, over(scenario, label(labsize(small))) bar(1, color("217 95 14")) ///
    `region' ytitle("Additional monthly maize cash requirement (GTQ)", size(small)) ylabel(, angle(0) nogrid labsize(small)) legend(off)
export_app "app07_budget_scenarios"
* Appendix 08–10: MAGA price variants, nominal and CPI-adjusted.
import delimited using "figures/Appendix/tables/maga_white_maize_monthly_graph_data.csv", clear varnames(1)
sort year month
twoway ///
    (line monthly_mean_price_gtq_per_quint month if year==2023, lcolor(gs3) lpattern(solid) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2024, lcolor(gs6) lpattern(dash) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2025, lcolor("217 95 14") lpattern(shortdash) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2026, lcolor("150 0 24") lpattern(solid) lwidth(medthick)), ///
    `region' xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul" 8 "Aug" 9 "Sep" 10 "Oct" 11 "Nov" 12 "Dec", labsize(vsmall)) ///
    ylabel(, angle(0) nogrid labsize(small)) xtitle("") ytitle("GTQ per quintal", size(small)) ///
    legend(order(1 "2023" 2 "2024" 3 "2025" 4 "2026 (through 21 Aug)") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app08_maga_maize_recent_years_nominal"
local historical_lines
forvalues yr=2012/2022 {
    local historical_lines `"`historical_lines' (line monthly_mean_price_gtq_per_quint month if year==`yr', lcolor(gs13) lwidth(vthin))"'
}
quietly summarize monthly_mean_price_gtq_per_quint if year==2026 & month==8, meanonly
local aug_2026 = r(mean)
quietly summarize historical_seasonal_median_gtq_p if year==2026 & month==8, meanonly
local aug_median = r(mean)
local aug_dev : display %4.1f 100 * (`aug_2026' - `aug_median') / `aug_median'
local aug_label "+`aug_dev'% vs Aug. median"
twoway ///
    `historical_lines' ///
    (line monthly_mean_price_gtq_per_quint month if year==2023, lcolor(gs7) lpattern(dot) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2024, lcolor(gs9) lpattern(dash) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2025, lcolor("217 95 14") lpattern(shortdash) lwidth(medthin)) ///
    (line historical_seasonal_median_gtq_p month if year==2026, lcolor(gs3) lpattern(dash) lwidth(medthin)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2026, lcolor("150 0 24") lwidth(medthick) msymbol(O) msize(small)) ///
    (pci `aug_median' 7.85 `aug_2026' 7.85, lcolor("150 0 24") lpattern(dash) lwidth(medthin)), ///
    `region' text(174 5.10 "`aug_label'", place(e) size(vsmall) color("150 0 24")) ///
    xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul" 8 "Aug", labsize(vsmall)) ///
    ylabel(, angle(0) nogrid labsize(small)) xtitle("") ytitle("GTQ per quintal", size(small)) ///
    legend(order(1 "2012-2022 individual years" 12 "2023" 13 "2024" 14 "2025" 15 "2012-2025 same-month median" 16 "2026 (through 21 Aug)") rows(2) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app09_maga_maize_2026_seasonal_benchmark_nominal"
import delimited using "derived/maga_maize_prices_real_jul2026_gtq.csv", clear varnames(1)
keep if year==2026 & !missing(real_price)
twoway ///
    (rarea real_hist_p25 real_hist_p75 month, color("198 219 239%55") lcolor(none)) ///
    (line real_hist_med month, lcolor(gs5) lpattern(dash) lwidth(medthin)) ///
    (line real_price month, lcolor("150 0 24") lwidth(medthick) msymbol(O) msize(small)), ///
    `region' xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul", labsize(vsmall)) ///
    ylabel(, angle(0) nogrid labsize(small)) xtitle("") ytitle("Constant July-2026 GTQ per quintal", size(small)) ///
    legend(order(1 "2012–2025 same-month IQR" 2 "2012–2025 same-month median" 3 "2026") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_app "app10_maga_maize_2026_seasonal_benchmark_real_jul2026_gtq"
display "Publication-ready Appendix figures created by Stata."
