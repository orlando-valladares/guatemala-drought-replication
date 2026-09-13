version 19.5
clear all
set more off
set scheme s2color
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
cap mkdir "figures"
cap mkdir "figures/Appendix"
cap mkdir "figures/Appendix/tables"
cap mkdir "figures/.tex_body"
local region "graphregion(color(white) margin(medium)) plotregion(color(white) margin(small))"
capture program drop export_main
program define export_main
    args stem height
    if "`height'" == "" graph display, xsize(9) ysize(6)
    else graph display, xsize(8) ysize(`height')
    graph export "figures/.tex_body/`stem'_body.pdf", replace
end
* Fig. 02a: rainfall scale with a fixed, aligned department/P/z column.
import delimited using "figures/Appendix/tables/chirps_department_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen row = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
egen data_max = rowmax(upper rain_2026_may_aug_mm)
summarize data_max, meanonly
local data_right = ceil(r(max)/100)*100
local label_x = `data_right' + 160
local x_max = `label_x' + 650
gen right_label = department + "   P" + strtrim(string(rainfall_historical_percentile, "%4.1f")) + "   z=" + strtrim(string(rainfall_z_score_vs_1981_2025, "%5.2f"))
gen label_x = `label_x'
twoway ///
    (rcap lower upper row, horizontal lcolor(gs11) lwidth(medthin)) ///
    (scatter row historical_mean_may_aug_mm, msymbol(Oh) mcolor(gs6) msize(small)) ///
    (scatter row historical_median_may_aug_mm, msymbol(Dh) mcolor(gs3) msize(small)) ///
    (scatter row rain_2026_may_aug_mm, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(small)) ///
    (scatter row label_x, msymbol(none) mlabel(right_label) mlabpos(3) mlabsize(vsmall) mlabcolor(black)), ///
    `region' ///
    yscale(reverse range(.4 `=_N+.8')) ylabel(none) ///
    xscale(range(0 `x_max')) xlabel(0(500)`data_right', labsize(small)) ///
    xtitle("May-August cumulative rainfall (mm)", size(small)) ytitle("") ///
    text(.48 `label_x' "Department     percentile     z-score", place(e) size(vsmall) color(gs6)) ///
    legend(order(2 "1981-2025 mean" 1 "mean +/- 1 SD" 3 "historical median" 4 "2026 final") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_main "fig02a_chirps_department_rainfall_sd_rank" ""
* Fig. 02b: same departments, with z-score as the vertical axis.
import delimited using "figures/Appendix/tables/chirps_department_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen position = _n
gen lower = min(rainfall_z_score_vs_1981_2025, 0)
gen upper = max(rainfall_z_score_vs_1981_2025, 0)
gen p_label = "P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
local xlabels
forvalues i = 1/`=_N' {
    local dep = department[`i']
    local xlabels `"`xlabels' `i' `"`dep'"'"'
}
twoway ///
    (rcap lower upper position, lcolor(gs10) lwidth(medthin)) ///
    (scatter rainfall_z_score_vs_1981_2025 position, msymbol(O) msize(small) mcolor("150 0 24") mfcolor("150 0 24") mlabel(p_label) mlabpos(12) mlabsize(vsmall) mlabcolor(gs5)), ///
    `region' ///
    yline(0, lcolor(gs8) lpattern(dash) lwidth(thin)) ///
    ylabel(-3(1)1, angle(0) labsize(small) nogrid) ///
    xlabel(`xlabels', angle(45) labsize(vsmall) noticks) ///
    xtitle("") ytitle("2026 May–August rainfall z-score", size(small)) ///
    legend(off)
export_main "fig02b_chirps_department_zscore_rank" ""
* Fig. 03a: all municipalities, compact z-score rank with field sites identified.
import delimited using "figures/Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen rank = _n
gen site_label = municipality + ": z=" + strtrim(string(rainfall_z_score_vs_1981_2025, "%4.2f")) + ", P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
twoway ///
    (scatter rank rainfall_z_score_vs_1981_2025 if field_site==0, msymbol(O) msize(tiny) mcolor(gs11) mfcolor(gs11)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Olopa", msymbol(D) msize(medsmall) mcolor("150 0 24") mfcolor("150 0 24") mlabel(site_label) mlabpos(3) mlabsize(small) mlabcolor(black)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Chahal", msymbol(S) msize(medsmall) mcolor(black) mfcolor(white) mlabel(site_label) mlabpos(3) mlabsize(small) mlabcolor(black)) ///
    (scatter rank rainfall_z_score_vs_1981_2025 if municipality=="Patzité", msymbol(T) msize(medsmall) mcolor(black) mfcolor(gs5) mlabel(site_label) mlabpos(3) mlabsize(small) mlabcolor(black)), ///
    `region' ///
    xline(-2 -1 0, lcolor(gs11 gs9 gs7) lpattern(dash dash solid) lwidth(vthin vthin thin)) ///
    yscale(reverse range(1 340)) ylabel(1 "most negative" 340 "least negative", angle(0) labsize(vsmall) nogrid) ///
    xtitle("2026 May–August rainfall z-score relative to 1981–2025", size(small)) ytitle("Municipality rank", size(small)) ///
    legend(order(1 "Other municipalities" 2 "Olopa" 3 "Chahal" 4 "Patzité") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_main "fig03a_chirps_municipality_zscore_rank" 14
* Fig. 03b: all municipalities, rainfall scale with SDs, tight right-side labels.
import delimited using "figures/Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen row = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
egen data_max = rowmax(upper rain_2026_may_aug_mm)
summarize data_max, meanonly
local data_right = ceil(r(max)/100)*100
local label_x = `data_right' + 100
local x_max = `label_x' + 1000
gen right_label = municipality + ", " + department + "  P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
gen label_x = `label_x'
twoway ///
    (rcap lower upper row, horizontal lcolor(gs12) lwidth(vthin)) ///
    (scatter row historical_mean_may_aug_mm, msymbol(Oh) mcolor(gs7) msize(tiny)) ///
    (scatter row rain_2026_may_aug_mm, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(tiny)) ///
    (scatter row label_x, msymbol(none) mlabel(right_label) mlabpos(3) mlabsize(tiny) mlabcolor(gs3)), ///
    `region' ///
    yscale(reverse range(.4 340.8)) ylabel(none) ///
    xscale(range(0 `x_max')) xlabel(0(500)`data_right', labsize(small)) ///
    xtitle("May–August cumulative rainfall (mm)", size(small)) ytitle("") ///
    text(.35 `label_x' "Municipality, department, percentile", place(e) size(tiny) color(gs6)) ///
    legend(order(2 "1981–2025 mean" 1 "mean ± 1 SD" 3 "2026 final") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_main "fig03b_chirps_municipality_rainfall_sd_compact" 28
display "Main CHIRPS figure bodies created by Stata for TeX framing."
