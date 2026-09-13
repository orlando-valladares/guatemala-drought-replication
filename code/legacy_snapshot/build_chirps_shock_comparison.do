version 19.5
clear all
set more off
set scheme s2color

* CHIRPS shock-comparison bodies.  Titles and notes are added only in main.tex.
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
cap mkdir "figures/.tex_body"
local region "graphregion(color(white) margin(medium)) plotregion(color(white) margin(small))"
capture program drop export_chirps
program define export_chirps
    args stem
    graph export "figures/.tex_body/`stem'_body.pdf", replace
end

* A3: department scale, using one retrospective 1981-2025 reference for all three shocks.
import delimited using "figures/Appendix/tables/chirps_shock_comparison_department_common_reference.csv", clear varnames(1)
sort z_2026_common
gen row = _n
gen lower = hist_mean_mm - hist_sd_mm
gen upper = hist_mean_mm + hist_sd_mm
egen data_max = rowmax(upper rain_2015_mm rain_2019_mm rain_2026_mm)
summarize data_max, meanonly
local data_right = ceil(r(max)/100)*100
local label_x = `data_right' + 175
local x_max = `label_x' + 1150
gen right_label = department + "    " + ///
    strtrim(string(z_2015_common, "%4.2f")) + "    " + ///
    strtrim(string(z_2019_common, "%4.2f")) + "    " + ///
    strtrim(string(z_2026_common, "%4.2f"))
gen label_x = `label_x'
twoway ///
    (rcap lower upper row, horizontal lcolor(gs11) lwidth(medthin)) ///
    (scatter row hist_mean_mm, msymbol(Oh) mcolor(gs6) msize(small)) ///
    (scatter row hist_median_mm, msymbol(Dh) mcolor(gs3) msize(small)) ///
    (scatter row rain_2015_mm, msymbol(T) mcolor(gs8) mfcolor(gs8) msize(small)) ///
    (scatter row rain_2019_mm, msymbol(D) mcolor(gs8) mfcolor(gs8) msize(small)) ///
    (scatter row rain_2026_mm, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(small)) ///
    (scatter row label_x, msymbol(none) mlabel(right_label) mlabpos(3) mlabsize(vsmall) mlabcolor(black)), ///
    `region' ///
    yscale(reverse range(.4 `=_N+.8')) ylabel(none) ///
    xscale(range(0 `x_max')) xlabel(0(500)`data_right', labsize(small)) ///
    xtitle("Precipitación acumulada de mayo a agosto (mm)", size(small)) ytitle("") ///
    text(.48 `label_x' "Departamento          z 2015       z 2019       z 2026", place(e) size(vsmall) color(gs6)) ///
    legend(order(2 "media 1981-2025" 1 "media +/- 1 DE" 3 "mediana histórica" 4 "2015 final" 5 "2019 final" 6 "2026 final") rows(2) size(vsmall) region(lcolor(none) fcolor(none)))
export_chirps "appendix_app11_chirps_national_shock_sd"

* A4: full national annual time series with the three selected events identified.
import delimited using "figures/Appendix/tables/chirps_shock_comparison_national_annual.csv", clear varnames(1)
sort year
gen hist_low = national_reference_mean_mm - national_reference_sd_mm
gen hist_high = national_reference_mean_mm + national_reference_sd_mm
gen event_label = string(year) if is_comparison_year==1
twoway ///
    (rarea hist_low hist_high year if year<=2025, color("217 237 247%55") lcolor(none)) ///
    (line national_reference_mean_mm year if year<=2025, lcolor(gs6) lpattern(dash) lwidth(medthin)) ///
    (line national_rain_may_aug_mm year, lcolor(gs9) lwidth(medthin)) ///
    (scatter national_rain_may_aug_mm year if year==2015, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(medsmall) mlabel(event_label) mlabpos(6) mlabsize(vsmall)) ///
    (scatter national_rain_may_aug_mm year if year==2019, msymbol(D) mcolor("217 95 14") mfcolor("217 95 14") msize(medsmall) mlabel(event_label) mlabpos(6) mlabsize(vsmall)) ///
    (scatter national_rain_may_aug_mm year if year==2026, msymbol(T) mcolor("117 107 177") mfcolor("117 107 177") msize(medsmall) mlabel(event_label) mlabpos(6) mlabsize(vsmall)), ///
    `region' xlabel(1981(5)2026, angle(45) labsize(vsmall)) ylabel(, angle(0) nogrid labsize(small)) ///
    xtitle("Año", size(small)) ytitle("Precipitación acumulada de mayo a agosto (mm)", size(small)) ///
    legend(order(1 "media histórica +/- 1 DE" 2 "media histórica, 1981-2025" 3 "total nacional" 4 "2015" 5 "2019" 6 "2026 final") rows(2) size(vsmall) region(lcolor(none) fcolor(none)))
export_chirps "appendix_app12_chirps_national_annual"

* A5: distributions of municipality-level z-scores, with each event's then-available reference period.
import delimited using "figures/Appendix/tables/chirps_shock_comparison_municipality.csv", clear varnames(1)
twoway ///
    (kdensity rainfall_z_score_at_time if year==2015, lcolor("150 0 24") lwidth(medthick)) ///
    (kdensity rainfall_z_score_at_time if year==2019, lcolor("217 95 14") lpattern(dash) lwidth(medthick)) ///
    (kdensity rainfall_z_score_at_time if year==2026, lcolor("117 107 177") lpattern(shortdash) lwidth(medthick)), ///
    `region' xline(-2, lcolor("150 0 24") lpattern(dash) lwidth(vthin)) xline(-1, lcolor("217 95 14") lpattern(dash) lwidth(vthin)) xline(0, lcolor(gs7) lwidth(thin)) ///
    xlabel(-5(1)2, labsize(small)) ylabel(, angle(0) nogrid labsize(small)) ///
    xtitle("Z-score municipal de lluvia (más negativo = más seco)", size(small)) ytitle("Densidad", size(small)) ///
    legend(order(1 "2015 (final)" 2 "2019 (final)" 3 "2026 (final)") rows(1) size(vsmall) region(lcolor(none) fcolor(none)))
export_chirps "appendix_app13_chirps_municipal_zscore_comparison"

* A6: geographic concentration, categorised using the historical record available at each shock.
import delimited using "figures/Appendix/tables/chirps_shock_comparison_concentration.csv", clear varnames(1)
drop municipalities
replace percentile_group_at_time = subinstr(percentile_group_at_time, "-", "_", .)
reshape wide share_percent, i(year) j(percentile_group_at_time) string
rename share_percent0 p0
rename share_percent1_10 p1_10
rename share_percent11_25 p11_25
rename share_percent26_50 p26_50
rename share_percent51_75 p51_75
capture rename share_percent76_100 p76_100
capture confirm variable p76_100
if _rc gen p76_100 = 0
graph bar (asis) p0 p1_10 p11_25 p26_50 p51_75 p76_100, over(year, label(labsize(small))) stack ///
    `region' yscale(range(0 100)) ylabel(0(20)100, angle(0) nogrid labsize(small)) ///
    ytitle("Porcentaje de municipios", size(small)) ///
    legend(order(1 "P0" 2 "P1-10" 3 "P11-25" 4 "P26-50" 5 "P51-75" 6 "P76-100") rows(2) size(vsmall) region(lcolor(none) fcolor(none))) ///
    bar(1, color("103 0 13")) bar(2, color("203 24 29")) bar(3, color("251 106 74")) bar(4, color("253 208 162")) bar(5, color("158 202 225")) bar(6, color("49 130 189"))
export_chirps "appendix_app14_chirps_geographic_concentration"

display "CHIRPS historical-shock comparison graph bodies created."
