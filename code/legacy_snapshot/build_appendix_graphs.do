version 19.5
clear all
set more off
set scheme s2color

* This do-file produces every non-map graphic in the Appendix. The companion
* Python scripts prepare only derived graph data and build maps.
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
cap mkdir "Appendix"
cap mkdir "Appendix/figures"

********************************************************************************
* A. CHIRPS three field municipalities: mean +/- sample SD, median, 2026
********************************************************************************
import delimited using "Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
keep if inlist(municipality, "Olopa", "Chahal", "Patzité")
gen site_order = cond(municipality=="Olopa", 1, cond(municipality=="Chahal", 2, 3))
sort site_order
gen low = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen high = historical_mean_may_aug_mm + historical_sd_may_aug_mm
gen ztext = "z = " + string(rainfall_z_score_vs_1981_2025, "%5.2f") + "; P" + string(rainfall_historical_percentile, "%3.0f")
gen labelx = high + 55
local ylabs
forvalues i=1/3 {
    local site = municipality[`i']
    local dep = department[`i']
    local ylabs `"`ylabs' `i' `"`site', `dep'"'"'
}
twoway ///
    (rcap low high site_order, horizontal lcolor(gs10) lwidth(medthick)) ///
    (scatter site_order historical_mean_may_aug_mm, msymbol(O) mcolor(gs7) mfcolor(gs7) msize(small)) ///
    (scatter site_order historical_median_may_aug_mm, msymbol(D) mcolor(black) mfcolor(black) msize(small)) ///
    (scatter site_order rain_2026_may_aug_mm if rainfall_historical_percentile<=10, msymbol(O) mcolor("127 0 0") mfcolor("127 0 0") msize(medium)) ///
    (scatter site_order rain_2026_may_aug_mm if rainfall_historical_percentile>10, msymbol(O) mcolor("33 113 181") mfcolor("33 113 181") msize(medium)) ///
    (scatter site_order labelx, msymbol(none) mlabel(ztext) mlabcolor(black) mlabsize(small) mlabpos(3)), ///
    yscale(reverse range(.5 3.5)) ylabel(`ylabs', angle(0) labsize(small)) ///
    xtitle("May–August cumulative rainfall (mm)") ytitle("") ///
    title("CHIRPS rainfall: 2026 versus local historical distribution", size(medsmall)) ///
    legend(order(2 "1981–2025 mean" 1 "mean ± 1 sample SD" 3 "historical median" 4 "2026 final; P≤10" 5 "2026 final; P>10") rows(2) size(vsmall)) ///
    note("CHIRPS v3 municipality area-weighted cumulative rainfall. Exact window: 1 May–31 August; historical reference: 1981–2025. 2026 is FINAL." ///
         "Whiskers are descriptive sample standard deviations, not confidence intervals. Right labels give z-score and empirical percentile.", size(vsmall))
graph export "Appendix/figures/app02_chirps_three_sites_sd.png", replace width(2400)

********************************************************************************
* B. Department ranking: z-score is the principal ordering statistic
********************************************************************************
import delimited using "Appendix/tables/chirps_department_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen y = _n
gen low = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen high = historical_mean_may_aug_mm + historical_sd_may_aug_mm
gen labelx = max(high, rain_2026_may_aug_mm) + 190
gen statlabel = "z=" + string(rainfall_z_score_vs_1981_2025, "%5.2f") + "; P" + string(rainfall_historical_percentile, "%3.0f")
local ylabs
forvalues i=1/`=_N' {
    local dep = department[`i']
    local ylabs `"`ylabs' `i' `"`dep'"'"'
}
twoway ///
    (rcap low high y, horizontal lcolor(gs10) lwidth(medthin)) ///
    (scatter y historical_mean_may_aug_mm, msymbol(O) mcolor(gs7) mfcolor(gs7) msize(tiny)) ///
    (scatter y rain_2026_may_aug_mm, msymbol(D) mcolor("127 0 0") mfcolor("127 0 0") msize(small)) ///
    (scatter y labelx, msymbol(none) mlabel(statlabel) mlabcolor(black) mlabsize(vsmall) mlabpos(3)), ///
    yscale(reverse range(.5 `=_N+.5')) ylabel(`ylabs', angle(0) labsize(vsmall)) ///
    xtitle("May–August cumulative rainfall (mm)") ytitle("") ///
    title("Department rainfall ranking by 2026 CHIRPS z-score", size(medsmall)) ///
    legend(order(2 "1981–2025 mean" 1 "mean ± 1 sample SD" 3 "2026 final") rows(1) size(vsmall)) ///
    note("CHIRPS v3, department area-weighted cumulative rainfall, 1 May–31 August; 1981–2025 reference. Departments sort from most negative z-score at the top." ///
         "Right labels: z-score and empirical percentile. 2026 is FINAL; whiskers are descriptive, not confidence intervals.", size(vsmall))
graph export "Appendix/figures/app03_chirps_department_zscore_rank.png", replace width(2600)

********************************************************************************
* C. All 340 municipalities: ranked z-score dot plot (sites highlighted)
********************************************************************************
import delimited using "Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen rank = _n
gen sitelabel = municipality + ": z=" + string(rainfall_z_score_vs_1981_2025, "%4.2f") + ", P" + string(rainfall_historical_percentile, "%3.0f")
twoway ///
    (scatter rank rainfall_z_score_vs_1981_2025 if field_site==0, msymbol(O) msize(tiny) mcolor(gs11) mfcolor(gs11)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Olopa", msymbol(D) msize(medium) mcolor("127 0 0") mfcolor("127 0 0") mlabel(sitelabel) mlabpos(3) mlabsize(small)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Chahal", msymbol(D) msize(medium) mcolor("33 113 181") mfcolor("33 113 181") mlabel(sitelabel) mlabpos(3) mlabsize(small)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Patzité", msymbol(D) msize(medium) mcolor("35 132 67") mfcolor("35 132 67") mlabel(sitelabel) mlabpos(3) mlabsize(small)), ///
    xline(-2 -1 0, lcolor(gs12 gs12 gs8) lpattern(dash dash solid)) ///
    yscale(reverse range(1 340)) ylabel(1 "most negative z" 340 "least negative z", angle(0) labsize(vsmall)) ///
    xtitle("2026 May–August rainfall z-score relative to 1981–2025") ytitle("Municipality rank") ///
    title("Municipal CHIRPS rainfall anomaly ranking", size(medsmall)) ///
    legend(order(1 "Other municipalities" 2 "Olopa" 3 "Chahal" 4 "Patzité") rows(1) size(vsmall)) ///
    note("CHIRPS v3 municipality area-weighted cumulative rainfall, 1 May–31 August; 2026 FINAL. All 340 municipalities ranked by z-score." ///
         "A z-score is standard deviations from the municipality's 1981–2025 mean; more negative means drier. Highlight labels report z-score and empirical percentile.", size(vsmall))
graph export "Appendix/figures/app04_chirps_municipality_zscore_rank.png", replace width(2400) height(2600)

********************************************************************************
* D. All 340 municipalities again, coloured by department
********************************************************************************
import delimited using "Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen rank = _n
gen sitelabel = municipality + ": z=" + string(rainfall_z_score_vs_1981_2025, "%4.2f") + ", P" + string(rainfall_historical_percentile, "%3.0f")
levelsof department, local(departments)
local colours `""31 119 180" "255 127 14" "44 160 44" "214 39 40" "148 103 189" "140 86 75" "227 119 194" "127 127 127" "188 189 34" "23 190 207" "57 106 177" "218 124 48" "98 159 90" "196 78 82" "133 122 171" "150 113 94" "219 141 192" "119 119 119" "174 199 42" "72 177 194" "77 146 33" "221 132 82""'
local plots
local legorder
local i = 0
foreach dep of local departments {
    local ++i
    local colour : word `i' of `colours'
    local plots `"`plots' (scatter rank rainfall_z_score_vs_1981_2025 if department==`"`dep'"', msymbol(O) msize(tiny) mcolor(`colour') mfcolor(`colour'))"'
    local legorder `"`legorder' `i' `"`dep'"'"'
}
twoway `plots' ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Olopa", msymbol(D) msize(medium) mcolor(black) mfcolor("127 0 0") mlabel(sitelabel) mlabpos(3) mlabsize(small)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Chahal", msymbol(D) msize(medium) mcolor(black) mfcolor("33 113 181") mlabel(sitelabel) mlabpos(3) mlabsize(small)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Patzité", msymbol(D) msize(medium) mcolor(black) mfcolor("35 132 67") mlabel(sitelabel) mlabpos(3) mlabsize(small)), ///
    xline(-2 -1 0, lcolor(gs12 gs12 gs8) lpattern(dash dash solid)) ///
    yscale(reverse range(1 340)) ylabel(1 "most negative z" 340 "least negative z", angle(0) labsize(vsmall)) ///
    xtitle("2026 May–August rainfall z-score relative to 1981–2025") ytitle("Municipality rank") ///
    title("Municipal CHIRPS ranking, coloured by department", size(medsmall)) ///
    legend(order(`legorder') cols(3) size(tiny) region(lstyle(none))) ///
    note("CHIRPS v3 municipality area-weighted cumulative rainfall, 1 May–31 August; 2026 FINAL. Z-score determines vertical rank; colour identifies department." ///
         "Highlighted labels report z-score and empirical percentile. Department colour does not imply a department-level estimate.", size(vsmall))
graph export "Appendix/figures/app05_chirps_municipality_zscore_by_department.png", replace width(2600) height(2700)

********************************************************************************
* E. CHIRPS distribution and 1981–2026 trajectories for the three sites
********************************************************************************
import delimited using "Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
histogram rainfall_z_score_vs_1981_2025, percent width(.25) color("158 202 225") lcolor(white) ///
    xline(-2 -1 0, lcolor("127 0 0" "230 85 13" gs8) lpattern(dash dash solid)) ///
    xtitle("2026 May–August rainfall z-score") ytitle("Percent of municipalities") ///
    title("Distribution of municipality rainfall anomalies", size(medsmall)) ///
    note("CHIRPS v3 municipality area-weighted cumulative rainfall, 1 May–31 August 2026 versus 1981–2025. 2026 is FINAL." ///
         "Z-score is standard deviations from each municipality's historical mean; this plot is descriptive, not a crop-loss estimate.", size(vsmall))
graph export "Appendix/figures/app06_chirps_zscore_distribution.png", replace width(2200)

import delimited using "Appendix/tables/chirps_site_annual_series.csv", clear varnames(1)
twoway ///
    (line rain_may_aug_mm year if municipality=="Olopa", lcolor("127 0 0") lwidth(medthick)) ///
    (line rain_may_aug_mm year if municipality=="Chahal", lcolor("33 113 181") lwidth(medthick)) ///
    (line rain_may_aug_mm year if municipality=="Patzité", lcolor("35 132 67") lwidth(medthick)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Olopa", mcolor("127 0 0") mfcolor("127 0 0") msymbol(D) msize(medium)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Chahal", mcolor("33 113 181") mfcolor("33 113 181") msymbol(D) msize(medium)) ///
    (scatter rain_may_aug_mm year if year==2026 & municipality=="Patzité", mcolor("35 132 67") mfcolor("35 132 67") msymbol(D) msize(medium)), ///
    xline(2026, lcolor(gs10) lpattern(dash)) xlabel(1981(5)2026, angle(45) labsize(vsmall)) ///
    xtitle("Year") ytitle("May–August cumulative rainfall (mm)") ///
    title("CHIRPS annual May–August rainfall at the three field sites", size(medsmall)) ///
    legend(order(1 "Olopa" 2 "Chahal" 3 "Patzité" 4 "2026 final observation") rows(1) size(vsmall)) ///
    note("CHIRPS v3 municipality area-weighted cumulative rainfall. Years 1981–2025 are historical; 2026 is FINAL. Exact seasonal window is 1 May–31 August.", size(vsmall))
graph export "Appendix/figures/app07_chirps_site_annual_series.png", replace width(2400)

********************************************************************************
* F. FAO ASIS: distribution and descriptive CHIRPS–ASIS comparison
********************************************************************************
import delimited using "Appendix/tables/chirps_fao_graph_data.csv", clear varnames(1)
histogram asis_value if !missing(asis_value), percent width(5) color("107 174 214") lcolor(white) ///
    xtitle("FAO ASIS municipality statistic (% valid in-season cropland area affected)") ytitle("Percent of municipalities with valid ASIS") ///
    title("Distribution of FAO ASIS agricultural vegetation stress", size(medsmall)) ///
    note("FAO ASIS Cropland, Growing Season 1, 2026 August Dekad 1. Municipality fractional-pixel, area-weighted raster statistic." ///
         "ASI measures drought-related vegetation stress, not yield loss. Five municipalities lack valid in-season cells and are excluded.", size(vsmall))
graph export "Appendix/figures/app08_fao_asis_distribution.png", replace width(2200)

twoway ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if field_site==0 & !missing(asis_value), msymbol(O) msize(tiny) mcolor(gs11) mfcolor(gs11)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Olopa", msymbol(D) msize(medium) mcolor("127 0 0") mfcolor("127 0 0") mlabel(municipality) mlabpos(3) mlabsize(small)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Chahal", msymbol(D) msize(medium) mcolor("33 113 181") mfcolor("33 113 181") mlabel(municipality) mlabpos(3) mlabsize(small)) ///
    (scatter asis_value rainfall_z_score_vs_1981_2025 if municipality=="Patzité", msymbol(D) msize(medium) mcolor("35 132 67") mfcolor("35 132 67") mlabel(municipality) mlabpos(3) mlabsize(small)), ///
    xline(0, lcolor(gs10)) xtitle("CHIRPS 2026 rainfall z-score (more negative = drier)") ///
    ytitle("FAO ASIS (% valid in-season cropland area affected)") ///
    title("Meteorological rainfall anomaly and agricultural vegetation stress", size(medsmall)) ///
    legend(order(1 "Other municipalities" 2 "Olopa" 3 "Chahal" 4 "Patzité") rows(1) size(vsmall)) ///
    note("CHIRPS v3 FINAL May–August 2026 z-score versus 1981–2025; FAO ASIS Cropland GS1, 2026 August Dekad 1. Municipality statistics." ///
         "Descriptive comparison only: neither an estimated causal relationship nor a measure of crop/yield loss.", size(vsmall))
graph export "Appendix/figures/app09_chirps_zscore_vs_fao_asis.png", replace width(2300)

********************************************************************************
* G. Scenario-budget graph (not a measured drought effect)
********************************************************************************
import delimited using "Appendix/tables/budget_scenarios_graph_data.csv", clear varnames(1)
graph bar additional_monthly_maize_cash_re, over(scenario, label(labsize(small))) ///
    bar(1, color("230 85 13")) ytitle("Additional monthly maize cash requirement (GTQ)") ///
    title("Scenario-based maize liquidity requirement", size(medsmall)) ///
    note("ENIGH rural expenditure basis and MAGA wholesale La Terminal white-maize benchmark. Low/central/high vary assumed own-production dependence and unavailable own production." ///
         "Bars are sensitivity scenarios, not observed income losses, crop losses, or causal drought effects. Transfer amount was not supplied.", size(vsmall))
graph export "Appendix/figures/app10_budget_scenarios.png", replace width(2000)

********************************************************************************
* H. MAGA nominal price variations: direct annual lines and seasonal benchmark
********************************************************************************
import delimited using "Appendix/tables/maga_white_maize_monthly_graph_data.csv", clear varnames(1)
sort year month
twoway ///
    (line monthly_mean_price_gtq_per_quint month if year==2023, lcolor("31 78 121") lwidth(medthick)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2024, lcolor("112 128 144") lwidth(medthick)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2025, lcolor("230 126 34") lwidth(medthick)) ///
    (line monthly_mean_price_gtq_per_quint month if year==2026, lcolor("174 32 18") lwidth(thick)), ///
    xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul" 8 "Aug" 9 "Sep" 10 "Oct" 11 "Nov" 12 "Dec", labsize(vsmall)) ///
    xtitle("") ytitle("GTQ per quintal") ///
    title("Wholesale white-maize price: each recent year shown directly", size(medsmall)) ///
    legend(order(1 "2023" 2 "2024" 3 "2025" 4 "2026 (through 21 Aug)") rows(1) size(vsmall)) ///
    note("MAGA daily quotes aggregated to monthly means. Series: Mayorista, La Terminal, Maíz blanco de primera, quintal, GTQ." ///
         "2026 is not a full year; this figure does not measure retail prices, local field-site prices, or drought causation.", size(vsmall))
graph export "Appendix/figures/app11_maga_maize_recent_years_nominal.png", replace width(2300)

keep if year==2026
twoway ///
    (rarea historical_seasonal_p25_gtq_per_ historical_seasonal_p75_gtq_per_ month, color("198 219 239%55") lcolor(none)) ///
    (line historical_seasonal_median_gtq_p month, lcolor(gs6) lpattern(dash) lwidth(medthick)) ///
    (line monthly_mean_price_gtq_per_quint month, lcolor("174 32 18") lwidth(thick) msymbol(O)), ///
    xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul" 8 "Aug", labsize(vsmall)) ///
    xtitle("") ytitle("GTQ per quintal") ///
    title("2026 white-maize wholesale price versus its seasonal distribution", size(medsmall)) ///
    legend(order(1 "2012–2025 same-month interquartile range" 2 "2012–2025 same-month median" 3 "2026 (through 21 Aug)") rows(2) size(vsmall)) ///
    note("MAGA daily quotes aggregated to monthly means. Series: Mayorista, La Terminal, Maíz blanco de primera, quintal, GTQ." ///
         "The comparison describes contemporaneous purchasing conditions; it does not attribute price movements to drought.", size(vsmall))
graph export "Appendix/figures/app12_maga_maize_2026_seasonal_benchmark_nominal.png", replace width(2300)

********************************************************************************
* I. MAGA series deflated by the official national CPI (constant July 2026 GTQ)
********************************************************************************
import delimited using "derived/maga_maize_prices_real_jul2026_gtq.csv", clear varnames(1)
keep if year==2026 & !missing(real_price)
twoway ///
    (rarea real_hist_p25 real_hist_p75 month, color("198 219 239%55") lcolor(none)) ///
    (line real_hist_med month, lcolor(gs6) lpattern(dash) lwidth(medthick)) ///
    (line real_price month, lcolor("174 32 18") lwidth(thick) msymbol(O)), ///
    xlabel(1 "Jan" 2 "Feb" 3 "Mar" 4 "Apr" 5 "May" 6 "Jun" 7 "Jul", labsize(vsmall)) ///
    xtitle("") ytitle("Constant July 2026 GTQ per quintal") ///
    title("2026 white-maize wholesale price, adjusted for national inflation", size(medsmall)) ///
    legend(order(1 "2012–2025 same-month interquartile range" 2 "2012–2025 same-month median" 3 "2026") rows(2) size(vsmall)) ///
    note("MAGA: Mayorista, La Terminal, Maíz blanco de primera, monthly mean. Deflated using official INE national CPI, Base 2024=100, to July 2026 GTQ." ///
         "INE CPI currently ends in July 2026: no August CPI is imputed. This is a purchasing-power adjustment, not a local retail-price or causal drought estimate.", size(vsmall))
graph export "Appendix/figures/app13_maga_maize_2026_seasonal_benchmark_real_jul2026_gtq.png", replace width(2300)

display "Appendix non-map graphs created by Stata."
