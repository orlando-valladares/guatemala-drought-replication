version 19.5
clear all
set more off
set scheme s2color
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
cap mkdir "figures/Honduras"
cap mkdir "figures/Honduras/Appendix"
cap mkdir "figures/.tex_body"
local region "graphregion(color(white) margin(medium)) plotregion(color(white) margin(small))"
capture program drop export_hn
program define export_hn
    args stem height
    if "`height'" == "" graph display, xsize(9) ysize(6)
    else graph display, xsize(8) ysize(`height')
    graph export "figures/.tex_body/honduras_`stem'_body.pdf", replace
end
* Fig H02a: rainfall scale with 1981--2025 mean +/- SD, aligned P/z labels.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_department_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen row = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
egen maximum = rowmax(upper rain_2026_may_aug_mm)
summarize maximum, meanonly
local data_right = ceil(r(max)/100)*100
local label_x = `data_right' + 135
local x_max = `label_x' + 570
gen right_label = department + "   P" + strtrim(string(rainfall_historical_percentile, "%4.1f")) + "   z=" + strtrim(string(rainfall_z_score_vs_1981_2025, "%5.2f"))
gen label_x = `label_x'
twoway ///
 (rcap lower upper row, horizontal lcolor(gs11) lwidth(medthin)) ///
 (scatter row historical_mean_may_aug_mm, msymbol(Oh) mcolor(gs6) msize(small)) ///
 (scatter row historical_median_may_aug_mm, msymbol(Dh) mcolor(gs3) msize(small)) ///
 (scatter row rain_2026_may_aug_mm, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(small)) ///
 (scatter row label_x, msymbol(none) mlabel(right_label) mlabpos(3) mlabsize(vsmall) mlabcolor(black)), ///
 `region' yscale(reverse range(.4 `=_N+.8')) ylabel(none) ///
 xscale(range(0 `x_max')) xlabel(0(500)`data_right', labsize(small)) ///
 xtitle("May-August cumulative rainfall (mm)", size(small)) ytitle("") ///
 text(.48 `label_x' "Department     percentile     z-score", place(e) size(vsmall) color(gs6)) ///
 legend(order(2 "1981-2025 mean" 1 "mean +/- 1 SD" 3 "historical median" 4 "2026 preliminary") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_hn "figH02a_honduras_department_rainfall_sd_rank" ""
* Fig H02b: departmental z-score ranking.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_department_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen position = _n
gen lower = min(rainfall_z_score_vs_1981_2025, 0)
gen upper = max(rainfall_z_score_vs_1981_2025, 0)
gen p_label = "P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
local xlabels
forvalues i=1/`=_N' {
 local dep = department[`i']
 local xlabels `"`xlabels' `i' `"`dep'"'"'
}
twoway ///
 (rcap lower upper position, lcolor(gs10) lwidth(medthin)) ///
 (scatter rainfall_z_score_vs_1981_2025 position, msymbol(O) msize(small) mcolor("150 0 24") mfcolor("150 0 24") mlabel(p_label) mlabpos(12) mlabsize(vsmall) mlabcolor(gs5)), ///
 `region' yline(0,lcolor(gs8) lpattern(dash) lwidth(thin)) ///
 ylabel(-3(1)1,angle(0) labsize(small) nogrid) xlabel(`xlabels',angle(45) labsize(vsmall) noticks) ///
 xtitle("") ytitle("2026 May-August rainfall z-score",size(small)) legend(off)
export_hn "figH02b_honduras_department_zscore_rank" ""
* Fig H03a: municipality z-score rank.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen rank = _n
twoway ///
 (scatter rank rainfall_z_score_vs_1981_2025, msymbol(O) msize(tiny) mcolor(gs10) mfcolor(gs10)), ///
 `region' xline(-2,lcolor(gs11) lpattern(dash) lwidth(vthin)) xline(-1,lcolor(gs9) lpattern(dash) lwidth(vthin)) xline(0,lcolor(gs7) lpattern(solid) lwidth(thin)) ///
 yscale(reverse range(1 298)) ylabel(1 "most negative" 298 "least negative",angle(0) labsize(vsmall) nogrid) ///
 xtitle("2026 May-August rainfall z-score relative to 1981-2025",size(small)) ytitle("Municipality rank",size(small)) legend(off)
export_hn "figH03a_honduras_municipality_zscore_rank" 13
* Fig H03b: compact municipality rainfall-level / SD view.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_municipality_graph_data.csv", clear varnames(1)
sort rainfall_z_score_vs_1981_2025
gen row = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
egen maximum = rowmax(upper rain_2026_may_aug_mm)
summarize maximum, meanonly
local data_right = ceil(r(max)/100)*100
local label_x = `data_right' + 80
local x_max = `label_x' + 900
gen right_label = municipality + ", " + department + "  P" + strtrim(string(rainfall_historical_percentile, "%4.1f"))
gen label_x = `label_x'
twoway ///
 (rcap lower upper row,horizontal lcolor(gs12) lwidth(vthin)) ///
 (scatter row historical_mean_may_aug_mm,msymbol(Oh) mcolor(gs7) msize(tiny)) ///
 (scatter row rain_2026_may_aug_mm,msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(tiny)) ///
 (scatter row label_x,msymbol(none) mlabel(right_label) mlabpos(3) mlabsize(tiny) mlabcolor(gs3)), ///
 `region' yscale(reverse range(.4 298.8)) ylabel(none) ///
 xscale(range(0 `x_max')) xlabel(0(500)`data_right',labsize(small)) ///
 xtitle("May-August cumulative rainfall (mm)",size(small)) ytitle("") ///
 text(.35 `label_x' "Municipality, department, percentile",place(e) size(tiny) color(gs6)) ///
 legend(order(2 "1981-2025 mean" 1 "mean +/- 1 SD" 3 "2026 preliminary") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_hn "figH03b_honduras_municipality_rainfall_sd_compact" 25
* Appendix H01: national annual rainfall history.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_national_annual_1981_2025.csv", clear varnames(1)
preserve
import delimited using "figures/Honduras/Appendix/tables/table_honduras_chirps_national_summary.csv", clear varnames(1)
summarize rain_2026_mm, meanonly
local current = r(mean)
restore
set obs `=_N+1'
replace year = 2026 in L
replace rain_may_aug_mm = `current' in L
twoway ///
 (line rain_may_aug_mm year if year<2026,lcolor(gs5) lwidth(medthick)) ///
 (scatter rain_may_aug_mm year if year==2026,msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(medsmall)), ///
 `region' xline(2026,lcolor(gs9) lpattern(dash) lwidth(vthin)) ///
 xlabel(1981(5)2026,angle(45) labsize(vsmall)) ylabel(,angle(0) nogrid labsize(small)) ///
 xtitle("Year") ytitle("May-August cumulative rainfall (mm)",size(small)) ///
 legend(order(1 "1981-2025 final" 2 "2026 preliminary") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_hn "appH01_honduras_national_annual_rainfall" ""
* Appendix H02: distribution of municipal z-scores.
import delimited using "figures/Honduras/Appendix/tables/honduras_chirps_municipality_graph_data.csv", clear varnames(1)
histogram rainfall_z_score_vs_1981_2025, percent width(.25) color("158 202 225") lcolor(white) ///
 `region' xline(-2,lcolor("150 0 24") lpattern(dash) lwidth(vthin)) xline(-1,lcolor("217 95 14") lpattern(dash) lwidth(vthin)) xline(0,lcolor(gs7) lpattern(solid) lwidth(thin)) ///
 xtitle("2026 May-August rainfall z-score",size(small)) ytitle("Percent of municipalities",size(small)) ///
 ylabel(,angle(0) nogrid labsize(small)) legend(off)
export_hn "appH02_honduras_municipal_zscore_distribution" ""
display "Honduras CHIRPS Stata figure bodies created for TeX framing."
