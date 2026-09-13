# Methods notes

## Analytical scope

This is a descriptive consistency check, not a test of a causal drought mechanism. The evidentiary sequence is meteorological rainfall (CHIRPS), observed vegetation stress (FAO ASIS), contemporaneous maize prices (MAGA), and the scale of a rural household budget (ENIGH). It does not establish that drought changed income, prices, transfer use, or asset investment.

## Municipality crosswalk

The analytical identifier is the existing TopoJSON `properties.id` municipality code (`municipality_id`). It is joined by code wherever one is supplied. The SESAN 160 indicator comes from the existing MSPAS project analytic file: 158 coded records plus two documented unmatched SESAN municipalities (La Blanca 1230 and San José La Máquina 1021), yielding exactly 160 codes. The supplied TopoJSON has 343 features: 340 Guatemala municipality polygons, 2 lake features with id 0 (Lago de Amatitlán, Lago de Atitlán), and 1 Belize feature. The 340 non-lake, non-Belize polygons constitute the analytical set; none were silently dropped. The supplied Livingston polygon (id 1802) was invalid and was repaired in memory with Shapely make_valid for calculations only.

## CHIRPS

The historical GeoTIFF has 45 bands labelled 1981--2025 and represents each year's 1 May--31 August cumulative rainfall. The 2026 seasonal total combines four official final CHIRPS v3 monthly rasters (May, June, July, and August). Each monthly raster is clipped in memory to the Guatemala outline before pixelwise summation; no resampling occurs. Municipal values are fractional-pixel, equal-area (EPSG:6933) area-weighted means of cumulative millimetres. They are never sums across pixels.

The standardized statistic is the empirical percentile: share of the 45 historical municipal totals less than or equal to 2026. Low values are unusually dry. All 2026 CHIRPS results are labelled **FINAL**.

## FAO ASIS

See [fao_asis_notes.md](fao_asis_notes.md). The valid supplied ASIS geography is department, not municipality. The Figure 3 dot cloud repeats a parent department value by municipality only to show the geographical mismatch; it is not a municipal stress relationship and has no fitted line.

## MAGA maize price

The only clean long 2026 series selected is wholesale (`Actor = Mayorista`) white maize, first quality, in `La Terminal`, GTQ per quintal. No wholesale/retail records or physical units are combined. It is a defensible national/central-market benchmark, but not a municipality-level or retail price. Monthly price is the mean of nonmissing daily quotes; the historical same-month benchmark is the median of monthly means in 2012--2025. The series describes contemporaneous purchasing conditions and does not attribute price changes to drought.

## ENIGH and budget exercise

Dictionary labels were read before use. Official `PONDERADOR` weights are used. `AREA = 2` defines rural households. The available documentation does not establish municipality or department inference, so results are national rural descriptive statistics, not municipality estimates. White maize uses documented item code `01.1.1.1.6.1` and diary expenditure field `B2P01B12`; the files contain no physical quantity field. The diary total is converted to a 30.4375-day expenditure basis. The central q basis is weighted mean of rural estimated monthly purchased white-maize expenditure (median was zero).

The expenditure-basis analogue defines normal purchased expenditure as `q = Q(1-s)p0`, then calculates current cash cost as `Q(1-s+sL)p1`. Thus the change is `q * [((1-s+sL)/(1-s)) * (p1/p0) - 1]`. Own-produced share `s` and unavailable fraction `L` are transparent low/central/high assumptions; neither is inferred from FAO ASIS. No agricultural-earnings term is included. Program documentation confirms a conditional transfer but gives no amount `T`, therefore transfer-share cells are deliberately blank.

## Actualización 2026-09-13: exposición agrícola en dos canales

La Tabla A1 del informe conserva el índice por tierra: $\max(-z_{2026},0)\times(100A/\mathrm{ha}^{ag})$. Añade un índice de dependencia: $\max(-z_{2026},0)\times(A/Total)$, donde `Total` es el total del cuadro A12.2 del INE e incluye la rama no especificada. Como ambos índices usan unidades distintas, el compuesto departamental es el promedio simple de sus percentiles (0--100); se usa sólo para ordenar departamentos y no estima pérdidas ni causalidad. Los checkpoints departamental y municipal incluyen los campos de ambos componentes y el compuesto; el cuadro suplementario municipal se ordena por este último. Los porcentajes Oxfam no se incluyen en este paquete hasta disponer de una fuente citable.
