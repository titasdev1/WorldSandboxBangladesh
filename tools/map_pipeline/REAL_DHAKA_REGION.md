# Greater Dhaka real-data map build

The map-only pipeline now has a regional build path separate from gameplay and Android APK export.

## Build locally or in GitHub Actions

Install Python packages:

    python -m pip install osmium shapely trimesh mapbox-earcut
    python tools/map_pipeline/build_dhaka_region.py --out build/dhaka-region-map

The builder downloads Geofabrik's Bangladesh OpenStreetMap PBF extract once, extracts mapped roads, building footprints and tagged places within the declared regional boundary, and bakes small standalone GLB tiles. It also emits source GeoJSON, a tile manifest, AI interior anchor seeds, and attribution. The default region is approximately 23.66–23.90°N, 90.30–90.53°E; edit DEFAULT_REGION only when a different coverage boundary is deliberately chosen.

The GitHub workflow **Build Real Dhaka Map Tiles** can be started manually and publishes the resulting map package as a workflow artifact. This is a map artifact, not an APK and not a second game.

## Tile placement

Every GLB is authored in a local coordinate frame. Use map_tiles_manifest.json to read each tile's origin_lat_lon, bounds, and GLB path. Do not load every GLB at world origin; calculate the common world transform from geographic coordinates or the shared regional projection before rendering/streaming.

## Accuracy policy

This pipeline uses actual mapped OSM geometry. It does not invent a road grid to fill gaps. It cannot honestly guarantee that every shop, house, restaurant, height, facade, or indoor room is mapped. OSM feature coverage varies. Buildings without mapped height or floor-count data receive a visibly inferred fallback height, recorded in the tile manifest.

For a navigation-memory game, the next validation pass must compare road junctions, block boundaries, waterways, landmarks, and building placement against current, authorized reference imagery. Exact facade likeness and street-level appearance require a suitable licensed imagery source; AI people and interiors are fictional and must not be presented as the real owners or residents.

## Source and attribution

OpenStreetMap contributors / Geofabrik Bangladesh extract:
- https://download.geofabrik.de/asia/bangladesh.html
- https://www.openstreetmap.org/copyright

OSM data is under ODbL 1.0. Review attribution and share-alike obligations before redistributing the derived database or map package.
