#!/usr/bin/env python3
"""Fetch a small, real OpenStreetMap district around central Dhaka as GeoJSON.

The resulting dataset is generated at build time, not checked into Git. The
first playable slice is deliberately bounded to keep Android memory and build
sizes under control; later districts should be streamed as separate chunks.
OpenStreetMap data is © OpenStreetMap contributors and is available under ODbL.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "content" / "realworld" / "area.geojson"
CHUNK_DIR = ROOT / "content" / "realworld" / "chunks"
# Central Dhaka anchor. Runtime chunks cover a roughly 23 km x 23 km real-map
# region around it, with 3.3 km cells clipped from the Bangladesh OSM PBF extract.
SOUTH, WEST, NORTH, EAST = 23.8043, 90.4065, 23.8163, 90.4185
ORIGIN_LAT, ORIGIN_LON = 23.8103, 90.4125
CITY_CELL_DEGREES = 0.016
CITY_GRID_RADIUS = 6
MAX_FEATURES = 1800
ROAD_LIMIT = 400
CHUNK_MAX_FEATURES = 1800
CHUNK_ROAD_LIMIT = 300
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "WorldSandboxBangladesh/1.0 (open-source game prototype; OSM attribution preserved)"

def fetch_overpass(bounds: tuple[float, float, float, float] | None = None, timeout_seconds: int = 45, attempts_per_endpoint: int = 2, endpoints: tuple[str, ...] = OVERPASS_ENDPOINTS) -> dict:
    south, west, north, east = bounds or (SOUTH, WEST, NORTH, EAST)
    bbox = f"{south},{west},{north},{east}"
    query = (
        f"[out:json][timeout:{timeout_seconds}];("
        f'way["highway"]({bbox});'
        f'way["building"]({bbox});'
        f'node["shop"]({bbox});'
        f'node["amenity"]({bbox});'
        f'node["office"]({bbox});'
        f'node["tourism"]({bbox});'
        ");out tags geom;"
    )
    payload = query.encode("utf-8")
    last_error: Exception | None = None
    for endpoint in endpoints:
        for attempt in range(attempts_per_endpoint):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
                    raise ValueError("Overpass response did not contain an elements array")
                return data
            except Exception as exc:
                last_error = exc
                # Public Overpass servers are frequently busy. Retry transient failures
                # before moving to the next independent mirror, with bounded backoff.
                if attempt + 1 < attempts_per_endpoint:
                    time.sleep(min(8, 2 ** (attempt + 1)))
    raise RuntimeError(f"all Overpass endpoints failed: {last_error}")

def to_feature(element: dict) -> dict | None:
    element_type = element.get("type")
    tags = element.get("tags", {})
    if element_type == "node":
        if not isinstance(tags, dict) or not any(key in tags for key in ("shop", "amenity", "office", "tourism", "brand", "name", "name:bn")):
            return None
        if "lon" not in element or "lat" not in element:
            return None
        properties = {
            key: tags[key]
            for key in (
                "name", "name:bn", "brand", "shop", "amenity", "office",
                "tourism", "cuisine", "opening_hours", "addr:street",
                "addr:housenumber", "phone", "website", "wheelchair",
            ) if key in tags
        }
        properties["osm_id"] = int(element.get("id", 0))
        properties["source"] = "OpenStreetMap"
        return {"type": "Feature", "id": f"node/{element.get('id', 0)}",
                "properties": properties,
                "geometry": {"type": "Point", "coordinates": [float(element["lon"]), float(element["lat"])]}}
    if element_type != "way" or not isinstance(element.get("geometry"), list):
        return None
    if not isinstance(tags, dict):
        return None
    coords = []
    for point in element["geometry"]:
        if not isinstance(point, dict) or "lon" not in point or "lat" not in point:
            continue
        coords.append([float(point["lon"]), float(point["lat"])])
    if tags.get("highway") and len(coords) >= 2:
        geometry = {"type": "LineString", "coordinates": coords}
    elif tags.get("building") and len(coords) >= 4 and coords[0] == coords[-1]:
        geometry = {"type": "Polygon", "coordinates": [coords]}
    else:
        return None
    # Preserve useful OSM semantics so the runtime can build distinct
    # facades, roof finishes, named storefronts, and locally labelled places.
    # Keep this allow-list bounded instead of copying arbitrary tag payloads.
    properties = {
        key: tags[key]
        for key in (
            "highway", "building", "building:part", "building:use",
            "building:levels", "height", "min_height", "building:material",
            "building:colour", "building:color", "roof:shape", "roof:material",
            "roof:colour", "roof:color", "name", "name:bn", "brand",
            "addr:street", "addr:housenumber", "shop", "amenity", "landuse",
            "surface", "oneway", "leisure", "tourism", "office", "craft",
            "healthcare", "cuisine", "opening_hours", "building:architecture",
        )
        if key in tags
    }
    properties["osm_id"] = int(element.get("id", 0))
    properties["source"] = "OpenStreetMap"
    return {"type": "Feature", "id": f"way/{element.get('id', 0)}",
            "properties": properties, "geometry": geometry}

def prepare_features(response: dict, max_features: int, road_limit: int) -> tuple[list[dict], int, int]:
    roads: list[dict] = []
    buildings: list[dict] = []
    places: list[dict] = []
    for element in response["elements"]:
        feature = to_feature(element)
        if feature is None:
            continue
        props = feature["properties"]
        if "highway" in props:
            roads.append(feature)
        elif "building" in props:
            buildings.append(feature)
        elif any(key in props for key in ("shop", "amenity", "office", "tourism", "brand", "name", "name:bn")):
            places.append(feature)
    roads.sort(key=lambda f: (
        {"primary": 0, "secondary": 1, "tertiary": 2, "residential": 3,
         "unclassified": 4, "service": 5}.get(f["properties"].get("highway"), 6),
        f["properties"].get("osm_id", 0),
    ))
    buildings.sort(key=lambda f: (
        0 if f["properties"].get("shop") else 1,
        0 if f["properties"].get("name") else 1,
        f["properties"].get("osm_id", 0),
    ))
    places.sort(key=lambda f: (
        0 if f["properties"].get("name:bn") else 1,
        0 if f["properties"].get("name") else 1,
        f["properties"].get("osm_id", 0),
    ))
    place_limit = min(max_features // 4, 400)
    building_limit = max(0, max_features - road_limit - place_limit)
    selected = roads[:road_limit] + buildings[:building_limit] + places[:place_limit]
    return selected[:max_features], min(len(roads), road_limit), min(len(buildings), building_limit)

def fetch_geofabrik(bounds: tuple[float, float, float, float]) -> dict:
    """Reliable regional fallback: clip the free Bangladesh OSM PBF locally with osmium."""
    osmium = shutil.which("osmium")
    if not osmium:
        raise RuntimeError("osmium-tool is unavailable; cannot process Geofabrik PBF fallback")
    cache_dir = pathlib.Path("/tmp/world-sandbox-osm-cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    pbf_path = cache_dir / "bangladesh-latest.osm.pbf"
    if not pbf_path.exists() or pbf_path.stat().st_size < 10_000_000:
        partial = pbf_path.with_suffix(".download")
        request = urllib.request.Request(
            "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf",
            headers={"User-Agent": USER_AGENT},
        )
        print("Downloading free Bangladesh OSM regional extract from Geofabrik (PBF)…")
        with urllib.request.urlopen(request, timeout=600) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if partial.stat().st_size < 10_000_000:
            raise RuntimeError("Geofabrik PBF download was unexpectedly small")
        partial.replace(pbf_path)
    south, west, north, east = bounds
    extract = cache_dir / f"dhaka-{south:.4f}-{west:.4f}-{north:.4f}-{east:.4f}.pbf"
    exported = extract.with_suffix(".geojson")
    subprocess.run(
        [osmium, "extract", "-b", f"{west},{south},{east},{north}", "--strategy=complete_ways",
         str(pbf_path), "-o", str(extract), "--overwrite"],
        check=True, timeout=240,
    )
    subprocess.run([osmium, "export", str(extract), "-o", str(exported), "--overwrite"],
                   check=True, timeout=240)
    document = json.loads(exported.read_text(encoding="utf-8"))
    elements = []
    for feature in document.get("features", []):
        geometry = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        raw_id = str(props.get("@id", feature.get("id", "")))
        element_type, _, element_id = raw_id.partition("/")
        if not element_id.isdigit():
            element_id = str(feature.get("id", "0")).split("/")[-1]
        tags = {str(k): v for k, v in props.items() if not str(k).startswith("@") and v is not None}
        coords = geometry.get("coordinates")
        kind = geometry.get("type")
        if kind == "Point" and isinstance(coords, list) and len(coords) >= 2:
            elements.append({"type": "node", "id": int(element_id) if element_id.isdigit() else 0,
                             "lon": coords[0], "lat": coords[1], "tags": tags})
        elif kind == "LineString" and isinstance(coords, list):
            elements.append({"type": "way", "id": int(element_id) if element_id.isdigit() else 0,
                             "geometry": [{"lon": p[0], "lat": p[1]} for p in coords], "tags": tags})
        elif kind == "Polygon" and isinstance(coords, list) and coords:
            outer = coords[0]
            elements.append({"type": "way", "id": int(element_id) if element_id.isdigit() else 0,
                             "geometry": [{"lon": p[0], "lat": p[1]} for p in outer], "tags": tags})
        elif kind == "MultiPolygon" and isinstance(coords, list):
            for part_index, polygon in enumerate(coords):
                if not isinstance(polygon, list) or not polygon:
                    continue
                outer = polygon[0]
                if not isinstance(outer, list) or len(outer) < 4:
                    continue
                elements.append({"type": "way", "id": int(element_id) if element_id.isdigit() else 0,
                                 "geometry": [{"lon": p[0], "lat": p[1]} for p in outer],
                                 "tags": {**tags, "_multipolygon_part": part_index}})
    if not elements:
        raise RuntimeError("Geofabrik extract produced no usable OSM features for requested bounds")
    print(f"Geofabrik/osmium fallback: {len(elements)} mapped elements clipped to {bounds}")
    return {"elements": elements}


def element_intersects_bounds(element: dict, bounds: tuple[float, float, float, float]) -> bool:
    south, west, north, east = bounds
    points: list[tuple[float, float]] = []
    if element.get("type") == "node":
        if "lon" in element and "lat" in element:
            points.append((float(element["lon"]), float(element["lat"])))
    else:
        for point in element.get("geometry", []):
            if isinstance(point, dict) and "lon" in point and "lat" in point:
                points.append((float(point["lon"]), float(point["lat"])))
    if not points:
        return False
    min_lon = min(point[0] for point in points)
    max_lon = max(point[0] for point in points)
    min_lat = min(point[1] for point in points)
    max_lat = max(point[1] for point in points)
    return max_lon >= west and min_lon <= east and max_lat >= south and min_lat <= north


def main() -> int:
    try:
        # Prefer the regional PBF extract: one dependable source serves both the
        # central district and the city-scale grid without waiting on busy mirrors.
        response = fetch_geofabrik((SOUTH, WEST, NORTH, EAST))
    except Exception as exc:
        print(f"WARNING: regional PBF unavailable for central Dhaka: {exc}; trying Overpass")
        try:
            response = fetch_overpass(timeout_seconds=25, attempts_per_endpoint=1)
        except Exception as fallback_exc:
            print(f"ERROR: both Geofabrik/osmium and Overpass sources failed; refusing fallback-only map: {fallback_exc}")
            return 1

    features, road_count, building_count = prepare_features(response, MAX_FEATURES, ROAD_LIMIT)
    if not features:
        print("ERROR: central-Dhaka OSM query returned no usable road/building features; refusing to publish a fallback-only map")
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "type": "FeatureCollection",
        "name": "Dhaka starter district",
        "metadata": {
            "source": "OpenStreetMap contributors",
            "license": "ODbL-1.0",
            "attribution": "© OpenStreetMap contributors",
            "bbox": [WEST, SOUTH, EAST, NORTH],
            "district_scope": "Central Dhaka starter slice; not the whole city",
            "feature_count": len(features),
            "roads": road_count,
            "buildings": building_count,
            "named_places": sum(1 for f in features if f["geometry"]["type"] == "Point"),
        },
        "features": features,
    }
    OUTPUT.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Dhaka OSM district prepared: {len(features)} features "
          f"({document['metadata']['roads']} roads, {document['metadata']['buildings']} buildings)")

    # Build a city-scale streaming grid from a free regional OSM PBF source.
    # 13x13 cells at 0.016 degrees each cover roughly 23 km around central Dhaka.
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    for stale in CHUNK_DIR.glob("*.geojson"):
        stale.unlink()
    manifest = {"source": "OpenStreetMap contributors", "license": "ODbL-1.0",
                "attribution": "© OpenStreetMap contributors", "grid": []}
    city_bounds = (
        ORIGIN_LAT - (CITY_GRID_RADIUS + 0.5) * CITY_CELL_DEGREES,
        ORIGIN_LON - (CITY_GRID_RADIUS + 0.5) * CITY_CELL_DEGREES,
        ORIGIN_LAT + (CITY_GRID_RADIUS + 0.5) * CITY_CELL_DEGREES,
        ORIGIN_LON + (CITY_GRID_RADIUS + 0.5) * CITY_CELL_DEGREES,
    )
    try:
        city_response = fetch_geofabrik(city_bounds)
        print(f"Regional OSM extract ready for grid: {len(city_response['elements'])} elements")
    except Exception as pbf_exc:
        print(f"WARNING: regional PBF extraction unavailable: {pbf_exc}; per-cell Overpass fallback will be used")
        city_response = {"elements": []}
    for row in range(-CITY_GRID_RADIUS, CITY_GRID_RADIUS + 1):
        for col in range(-CITY_GRID_RADIUS, CITY_GRID_RADIUS + 1):
            chunk_name = f"grid_{row + CITY_GRID_RADIUS:02d}_{col + CITY_GRID_RADIUS:02d}"
            center_lat = ORIGIN_LAT + row * CITY_CELL_DEGREES
            center_lon = ORIGIN_LON + col * CITY_CELL_DEGREES
            bounds = (center_lat - CITY_CELL_DEGREES / 2,
                      center_lon - CITY_CELL_DEGREES / 2,
                      center_lat + CITY_CELL_DEGREES / 2,
                      center_lon + CITY_CELL_DEGREES / 2)
            cell_elements = [element for element in city_response["elements"]
                             if element_intersects_bounds(element, bounds)]
            chunk_response = {"elements": cell_elements}
            if not cell_elements:
                print(f"WARNING: regional extract has no features in {chunk_name}; trying Overpass")
                try:
                    chunk_response = fetch_overpass(bounds, timeout_seconds=25, attempts_per_endpoint=1,
                                                    endpoints=OVERPASS_ENDPOINTS)
                except Exception as exc:
                    if row == 0 and col == 0:
                        print(f"ERROR: central real Dhaka grid cell {chunk_name} unavailable: {exc}")
                        return 1
                    print(f"WARNING: unmapped outer cell {chunk_name}; preserving it as an empty streaming cell: {exc}")
                    chunk_response = {"elements": []}
            chunk_features, chunk_roads, chunk_buildings = prepare_features(
                chunk_response, CHUNK_MAX_FEATURES, CHUNK_ROAD_LIMIT
            )
            if not chunk_features and row == 0 and col == 0:
                print(f"ERROR: central real Dhaka grid cell {chunk_name} has no usable features")
                return 1
            if not chunk_features:
                print(f"INFO: grid cell {chunk_name} contains no mapped OSM features; writing empty cell")
            chunk_output = CHUNK_DIR / f"{chunk_name}.geojson"
            chunk_document = {
                "type": "FeatureCollection",
                "name": f"Dhaka real-world grid {row},{col}",
                "metadata": {
                    "source": "OpenStreetMap contributors", "license": "ODbL-1.0",
                    "attribution": "© OpenStreetMap contributors",
                    "bbox": [bounds[1], bounds[0], bounds[3], bounds[2]],
                    "district_scope": "Real OSM city-scale streaming grid cell",
                    "feature_count": len(chunk_features), "roads": chunk_roads,
                    "buildings": chunk_buildings,
                    "named_places": sum(1 for f in chunk_features if f["geometry"]["type"] == "Point"),
                },
                "features": chunk_features,
            }
            chunk_output.write_text(json.dumps(chunk_document, separators=(",", ":")) + "\n", encoding="utf-8")
            import math
            meters_lon = 111320.0 * math.cos(math.radians(ORIGIN_LAT))
            manifest["grid"].append({
                "id": chunk_name, "path": f"res://content/realworld/chunks/{chunk_name}.geojson",
                "latitude": center_lat, "longitude": center_lon,
                "x": (center_lon - ORIGIN_LON) * meters_lon,
                "z": -(center_lat - ORIGIN_LAT) * 111132.0,
                "features": len(chunk_features), "roads": chunk_roads, "buildings": chunk_buildings,
            })
            print(f"Dhaka grid {chunk_name}: {len(chunk_features)} features")
    manifest_path = ROOT / "content" / "realworld" / "chunks_manifest.json"
    manifest_path.write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"City-scale grid generated: {len(manifest['grid'])} real OSM chunks; manifest: {manifest_path.relative_to(ROOT)}")
    print(f"Source: © OpenStreetMap contributors; ODbL-1.0. Output: {OUTPUT.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
