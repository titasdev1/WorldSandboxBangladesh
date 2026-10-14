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
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "content" / "realworld" / "area.geojson"
CHUNK_DIR = ROOT / "content" / "realworld" / "chunks"
# Approximately a 1.3 km x 1.2 km central-Dhaka starter district; neighboring chunks extend exploration.
SOUTH, WEST, NORTH, EAST = 23.8043, 90.4065, 23.8163, 90.4185
MAX_FEATURES = 1400
ROAD_LIMIT = 400
CHUNK_MAX_FEATURES = 600
CHUNK_ROAD_LIMIT = 180
CHUNK_OFFSETS = {"north": (0.0120, 0.0), "south": (-0.0120, 0.0), "east": (0.0, 0.0120), "west": (0.0, -0.0120)}
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "WorldSandboxBangladesh/1.0 (open-source game prototype; OSM attribution preserved)"

def fetch_overpass(bounds: tuple[float, float, float, float] | None = None, timeout_seconds: int = 45, attempts_per_endpoint: int = 1, endpoints: tuple[str, ...] = OVERPASS_ENDPOINTS) -> dict:
    south, west, north, east = bounds or (SOUTH, WEST, NORTH, EAST)
    bbox = f"{south},{west},{north},{east}"
    query = (
        f"[out:json][timeout:{timeout_seconds}];("
        f'way["highway"]({bbox});'
        f'way["building"]({bbox});'
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
                if attempt == 0:
                    time.sleep(2)
    raise RuntimeError(f"all Overpass endpoints failed: {last_error}")

def to_feature(element: dict) -> dict | None:
    if element.get("type") != "way" or not isinstance(element.get("geometry"), list):
        return None
    tags = element.get("tags", {})
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
    for element in response["elements"]:
        feature = to_feature(element)
        if feature is None:
            continue
        props = feature["properties"]
        if "highway" in props:
            roads.append(feature)
        elif "building" in props:
            buildings.append(feature)
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
    selected = roads[:road_limit] + buildings[:max_features - road_limit]
    return selected[:max_features], min(len(roads), road_limit), min(len(buildings), max_features - road_limit)

def main() -> int:
    try:
        response = fetch_overpass()
    except Exception as exc:
        # Optional source: do not make a release impossible during an Overpass outage.
        print(f"ERROR: required central-Dhaka OSM download unavailable; refusing to publish a fallback-only map: {exc}")
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
        },
        "features": features,
    }
    OUTPUT.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Dhaka OSM district prepared: {len(features)} features "
          f"({document['metadata']['roads']} roads, {document['metadata']['buildings']} buildings)")

    # Four contiguous neighboring chunks expand the playable map beyond the starter district.
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    for stale in CHUNK_DIR.glob("*.geojson"):
        stale.unlink()
    for chunk_name, (lat_shift, lon_shift) in CHUNK_OFFSETS.items():
        bounds = (SOUTH + lat_shift, WEST + lon_shift, NORTH + lat_shift, EAST + lon_shift)
        try:
            chunk_response = fetch_overpass(bounds, timeout_seconds=20, attempts_per_endpoint=1, endpoints=OVERPASS_ENDPOINTS)
            chunk_features, chunk_roads, chunk_buildings = prepare_features(
                chunk_response, CHUNK_MAX_FEATURES, CHUNK_ROAD_LIMIT
            )
        except Exception as exc:
            print(f"WARNING: optional Dhaka chunk '{chunk_name}' unavailable: {exc}")
            continue
        if not chunk_features:
            print(f"WARNING: optional Dhaka chunk '{chunk_name}' returned no usable features")
            continue
        chunk_output = CHUNK_DIR / f"{chunk_name}.geojson"
        chunk_document = {
            "type": "FeatureCollection",
            "name": f"Dhaka {chunk_name} district chunk",
            "metadata": {
                "source": "OpenStreetMap contributors",
                "license": "ODbL-1.0",
                "attribution": "© OpenStreetMap contributors",
                "bbox": [bounds[1], bounds[0], bounds[3], bounds[2]],
                "district_scope": f"Adjacent Dhaka exploration chunk: {chunk_name}",
                "feature_count": len(chunk_features),
                "roads": chunk_roads,
                "buildings": chunk_buildings,
            },
            "features": chunk_features,
        }
        chunk_output.write_text(json.dumps(chunk_document, separators=(",", ":")) + "\n", encoding="utf-8")
        print(f"Dhaka OSM chunk '{chunk_name}': {len(chunk_features)} features")

    print(f"Source: © OpenStreetMap contributors; ODbL-1.0. Output: {OUTPUT.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
