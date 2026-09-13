version 19.5
clear all
set more off
set scheme s2color
local root "/home/orlando-valladares/01_workspace/02_projects/07_Playdata/02_Guatemala/proyects/03_Dalton_InsumoCampo"
cd "`root'"
local region "graphregion(color(white) margin(medium)) plotregion(color(white) margin(small))"

* Field sites with the common historical benchmark and all three shock years.
import delimited using "figures/Appendix/tables/chirps_municipality_graph_data.csv", clear varnames(1)
keep if inlist(municipality, "Olopa", "Chahal", "Patzité")
keep municipality_id department municipality historical_mean_may_aug_mm historical_median_may_aug_mm historical_sd_may_aug_mm rain_2026_may_aug_mm rainfall_z_score_vs_1981_2025 rainfall_historical_percentile
rename rain_2026_may_aug_mm rain_2026_common
rename rainfall_z_score_vs_1981_2025 z_2026_common
rename rainfall_historical_percentile p_2026_common
tempfile base
save `base'

import delimited using "figures/Appendix/tables/chirps_shock_comparison_municipality.csv", clear varnames(1)
keep if inlist(municipality, "Olopa", "Chahal", "Patzité") & inlist(year, 2015, 2019)
keep municipality_id year rain_may_aug_mm rainfall_z_score_at_time rainfall_percentile_at_time
reshape wide rain_may_aug_mm rainfall_z_score_at_time rainfall_percentile_at_time, i(municipality_id) j(year)
tempfile shocks
save `shocks'

use `base', clear
merge 1:1 municipality_id using `shocks', nogen
rename rain_may_aug_mm2015 rain_2015
rename rain_may_aug_mm2019 rain_2019
rename rainfall_z_score_at_time2015 z_2015
rename rainfall_z_score_at_time2019 z_2019
rename rainfall_percentile_at_time2015 p_2015
rename rainfall_percentile_at_time2019 p_2019
sort z_2026_common
gen order = _n
gen lower = historical_mean_may_aug_mm - historical_sd_may_aug_mm
gen upper = historical_mean_may_aug_mm + historical_sd_may_aug_mm
gen label_x = upper + 125
gen stat_label = "2015 z=" + strtrim(string(z_2015, "%4.2f")) + "; 2019 z=" + strtrim(string(z_2019, "%4.2f")) + "; 2026 z=" + strtrim(string(z_2026_common, "%4.2f"))
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
    (scatter order rain_2015, msymbol(T) mcolor("217 95 14") mfcolor("217 95 14") msize(medsmall)) ///
    (scatter order rain_2019, msymbol(S) mcolor("33 113 181") mfcolor(white) msize(medsmall)) ///
    (scatter order rain_2026_common, msymbol(O) mcolor("150 0 24") mfcolor("150 0 24") msize(medsmall)) ///
    (scatter order label_x, msymbol(none) mlabel(stat_label) mlabpos(3) mlabsize(small) mlabcolor(black)), ///
    `region' yscale(reverse range(.5 3.5)) ylabel(`ylabs', angle(0) labsize(small) nogrid) ///
    xscale(range(0 2250)) xlabel(0(500)2000, labsize(small)) ///
    xtitle("Lluvia acumulada de mayo a agosto (mm)", size(small)) ytitle("") ///
    legend(order(2 "Media histórica" 1 "Media +/- 1 DE" 3 "Mediana histórica" 4 "2015" 5 "2019" 6 "2026 final") rows(2) size(vsmall) region(lcolor(none) fcolor(none)))
graph export "figures/.tex_body/appendix_app02_chirps_three_sites_sd_body.pdf", replace
