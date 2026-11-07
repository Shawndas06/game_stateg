The physical land outline in land.geojson is Natural Earth 1:110m land.
Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson
Natural Earth data is in the public domain: https://www.naturalearthdata.com/about/terms-of-use/
Only physical geography is used; contemporary political boundaries are not shown.
Feature properties were removed, geometry was not modified.

bithynia-geography.json uses Natural Earth 1:10m land and lakes from the same
repository (ne_10m_land.geojson, ne_10m_lakes.geojson). Rings were clipped to
27.3..32 E / 38..42.6 N and coordinates rounded to five decimal places.
This is physical geography, not a reconstruction of historical borders.

The Mediterranean overview displays the original assets/map/generated_map.png
from this project; Vite packages that original file as a hashed build asset.
The chapter's mountains and trees are cartographic decoration, not elevation
or vegetation survey data.

Canvas campaign landscape: map-landscape.json is derived from Natural Earth
10m geography regions (Range/mtn) and 50m rivers/lake centerlines (River only),
filtered to the existing map extent and rounded to .001 degree. Sources:
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_10m_geography_regions_polys.geojson
https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_rivers_lake_centerlines.geojson
Both are public domain under Natural Earth's terms above. Offline reproduction:
python scripts/build_landscape.py DIRECTORY_WITH_SOURCE_JSONS
Source SHA256: b7b26e50ea917d3696aec87f932def2bf5f890f5770e441d59c162c6f4c92a77
and f286e0ce978fde999ca2d7a78c764be08542e19b63cded52b05c12d5173ccc51.
Wooded belts are schematic cartographic decoration, not reconstructed 1299
forest boundaries. Four local relief ellipses schematize Uludag, Sundiken,
Samanli and Domanic where global range polygons omit local detail; they are
illustrations, not surveyed contours. These thematic layers do not change movement/simulation.
The Canvas landscape is cached with the static terrain buffer at all qualities;
land clipping and lake overpainting prevent decorations in water. Historical
settlement coordinates and shoreline data are unchanged.
