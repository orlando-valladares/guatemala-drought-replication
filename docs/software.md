# Software and portability status

Python geospatial work uses GeoPandas, Rasterio, Shapely, PyProj, NumPy, Pandas and Matplotlib; the initial Conda specification is `environment.yml`. Some legacy non-map figures use Stata `.do` files. Stata is proprietary and is not included in the environment specification; a release must state the tested Stata version and any user-written packages.

The legacy snapshot deliberately retains its original hard-coded workspace assumptions for audit. The release milestone is to move every path to `config/paths.yml`, then validate the pipeline in a new directory containing only this repository plus the permitted raw-data tree.
