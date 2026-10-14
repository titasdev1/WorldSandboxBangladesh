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
# Approximately a 2 km x 2 km central-Dhaka starter district.
SOUTH, WEST, NORTH, EAST = 23.8003, 90.4025, 23.8203, 90.4225
MAX_FEATURES = 1800
ROAD_LIMIT = 500
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
USER_AGENT = "WorldSandboxBangladesh/1.0 (open-source game prototype; OSM attribution preserved)"

def fetch_overpass() -> dict:
    bbox = f"{SOUTH},{WEST},{NORTH},{EAST}"
    query = (
        "[out:json][timeout:60];("
        f'way["highway"]({bbox});'
        f'way["building"]({bbox});'
        ");out tags geom;"
    )
    payload = query.encode("utf-8")
    last_error: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(2):
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
                with urllib.request.urlopen(request, timeout=90) as response:
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
    properties = {
        key: tags[key]
        for key in ("highway", "building", "name", "height", "building:levels",
                    "shop", "amenity", "landuse", "surface", "oneway")
        if key in tags
    }
    properties["osm_id"] = int(element.get("id", 0))
    properties["source"] = "OpenStreetMap"
    return {"type": "Feature", "id": f"way/{element.get('id', 0)}",
            "properties": properties, "geometry": geometry}

def main() -> int:
    try:
        response = fetch_overpass()
    except Exception as exc:
        # Optional source: do not make a release impossible during an Overpass outage.
        print(f"WARNING: Dhaka OSM download unavailable; build will use its fallback map: {exc}")
        return 0

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

    # Preserve road connectivity first, then prioritize shops and named buildings.
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
    features = roads[:ROAD_LIMIT] + buildings[:MAX_FEATURES - ROAD_LIMIT]
    if len(features) > MAX_FEATURES:
        features = features[:MAX_FEATURES]
    if not features:
        print("WARNING: no usable OSM road/building features returned; keeping fallback map")
        return 0

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
            "roads": min(len(roads), ROAD_LIMIT),
            "buildings": min(len(buildings), MAX_FEATURES - ROAD_LIMIT),
        },
        "features": features,
    }
    OUTPUT.write_text(json.dumps(document, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Dhaka OSM district prepared: {len(features)} features "
          f"({document['metadata']['roads']} roads, {document['metadata']['buildings']} buildings)")
    print(f"Source: © OpenStreetMap contributors; ODbL-1.0. Output: {OUTPUT.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
