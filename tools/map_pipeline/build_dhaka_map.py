#!/usr/bin/env python3
"""Build an exportable, georeferenced 3D Dhaka block from OpenStreetMap geometry.

The output is an offline GLB made from real OSM road centerlines and building
footprints. OSM does not provide photorealistic street imagery or most interiors;
those must come from a separately licensed imagery provider or authored assets.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import trimesh
from shapely.geometry import LineString, MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

# First map slice: central Dhaka. Small enough for responsible Overpass use and
# useful for validating the complete export/import pipeline before scaling out.
DEFAULT_BBOX = (23.8043, 90.4065, 23.8163, 90.4185)  # south, west, north, east
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
OSM_COPYRIGHT = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"


def overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    box = f"{south},{west},{north},{east}"
    return f"""[out:json][timeout:180];
(
  way["highway"]({box});
  way["building"]({box});
  way["shop"]({box});
  way["amenity"]({box});
  node["shop"]({box});
  node["amenity"]({box});
  node["tourism"]({box});
  node["historic"]({box});
);
out body geom;"""


def fetch_osm(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    payload = urllib.parse.urlencode({"data": overpass_query(bbox)}).encode()
    errors: list[str] = []
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(3):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers={
                        "User-Agent": "WorldSandboxBangladesh-MapPipeline/1.0 (open map export; OSM attribution included)",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=210) as response:
                    data = json.loads(response.read().decode("utf-8"))
                if not isinstance(data.get("elements"), list):
                    raise ValueError("Overpass response has no elements array")
                return data
            except Exception as exc:  # retry another public instance on transient failure
                errors.append(f"{endpoint} attempt {attempt + 1}: {exc}")
                time.sleep(2 + attempt * 2)
    raise RuntimeError("Unable to fetch OSM extract. " + " | ".join(errors[-4:]))


def local_xy(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    """Local equirectangular projection in metres, adequate for this small city tile."""
    x = math.radians(lon - origin_lon) * 6378137.0 * math.cos(math.radians(origin_lat))
    y = math.radians(lat - origin_lat) * 6378137.0
    return x, y


def geometry_xy(element: dict[str, Any], origin_lat: float, origin_lon: float) -> list[tuple[float, float]]:
    return [
        local_xy(float(point["lat"]), float(point["lon"]), origin_lat, origin_lon)
        for point in element.get("geometry", [])
        if "lat" in point and "lon" in point
    ]


def color_mesh(mesh: trimesh.Trimesh, color: tuple[int, int, int, int]) -> trimesh.Trimesh:
    mesh.visual.vertex_colors = [color] * len(mesh.vertices)
    return mesh


def extruded_polygon(geom: Polygon, height: float, color: tuple[int, int, int, int], name: str) -> list[trimesh.Trimesh]:
    result: list[trimesh.Trimesh] = []
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for part in parts:
        if part.is_empty or part.area < 0.5:
            continue
        try:
            mesh = trimesh.creation.extrude_polygon(part, max(0.08, float(height)), engine="earcut")
            mesh.visual.vertex_colors = [color] * len(mesh.vertices)
            mesh.metadata["name"] = name
            result.append(mesh)
        except Exception:
            # Invalid or highly complex OSM footprints should not kill the entire tile.
            continue
    return result


def building_height(tags: dict[str, str], osm_id: int) -> tuple[float, bool]:
    raw_height = tags.get("height", "").replace(" m", "").strip()
    try:
        height = float(raw_height)
        if 2.5 <= height <= 250:
            return height, False
    except (TypeError, ValueError):
        pass
    raw_levels = tags.get("building:levels", "")
    try:
        levels = int(float(raw_levels))
        if 1 <= levels <= 70:
            return max(3.2, levels * 3.1), False
    except (TypeError, ValueError):
        pass
    # Inferred height is explicitly marked in the manifest; it is not a surveyed value.
    rng = random.Random(int(osm_id))
    return rng.uniform(6.2, 24.0), True


def building_color(tags: dict[str, str], osm_id: int) -> tuple[int, int, int, int]:
    kind = tags.get("building", "").lower()
    if kind in {"commercial", "retail", "office", "hotel"} or "shop" in tags:
        palette = [(185, 169, 145, 255), (197, 184, 161, 255), (157, 169, 174, 255)]
    elif kind in {"industrial", "warehouse", "garages"}:
        palette = [(155, 157, 151, 255), (177, 172, 158, 255)]
    elif kind in {"religious", "mosque", "church", "temple"}:
        palette = [(201, 187, 157, 255), (183, 173, 149, 255)]
    else:
        palette = [(195, 181, 162, 255), (176, 180, 171, 255), (207, 196, 179, 255),
                   (166, 175, 180, 255), (187, 166, 151, 255)]
    return palette[int(osm_id) % len(palette)]


def road_width(tags: dict[str, str]) -> float:
    highway = tags.get("highway", "residential").lower()
    widths = {
        "motorway": 14.0, "motorway_link": 8.0, "trunk": 11.0, "trunk_link": 7.0,
        "primary": 8.5, "primary_link": 6.0, "secondary": 6.5, "secondary_link": 5.0,
        "tertiary": 5.2, "tertiary_link": 4.2, "residential": 3.8, "unclassified": 3.8,
        "living_street": 3.5, "service": 2.6, "pedestrian": 2.8, "footway": 1.4,
        "path": 1.2, "cycleway": 1.6, "steps": 1.2, "track": 2.2,
    }
    return widths.get(highway, 3.5)


def make_geojson(elements: list[dict[str, Any]], origin_lat: float, origin_lon: float) -> dict[str, Any]:
    features = []
    for el in elements:
        tags = el.get("tags", {})
        geom = el.get("geometry", [])
        if not tags:
            continue
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            geometry = {"type": "Point", "coordinates": [float(el["lon"]), float(el["lat"])]}
        else:
            coords = [[float(p["lon"]), float(p["lat"])] for p in geom if "lon" in p and "lat" in p]
            if not coords:
                continue
            if el.get("type") == "way" and tags.get("building") and len(coords) >= 4 and coords[0] == coords[-1]:
                geometry = {"type": "Polygon", "coordinates": [coords]}
            elif el.get("type") == "way" and tags.get("highway") and len(coords) >= 2:
                geometry = {"type": "LineString", "coordinates": coords}
            else:
                geometry = {"type": "Point", "coordinates": coords[0]}
        features.append({
            "type": "Feature",
            "id": f"{el.get('type', 'element')}/{el.get('id', 0)}",
            "geometry": geometry,
            "properties": {"osm_type": el.get("type"), "osm_id": el.get("id"), **tags},
        })
    return {"type": "FeatureCollection", "name": "Dhaka OSM source features", "features": features}


def build_map(elements: list[dict[str, Any]], output_dir: Path,
              bbox: tuple[float, float, float, float] = DEFAULT_BBOX) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    south, west, north, east = bbox
    origin_lat, origin_lon = (south + north) / 2.0, (west + east) / 2.0
    min_xy = local_xy(south, west, origin_lat, origin_lon)
    max_xy = local_xy(north, east, origin_lat, origin_lon)
    width, depth = max_xy[0] - min_xy[0], max_xy[1] - min_xy[1]
    scene = trimesh.Scene()
    ground = trimesh.creation.box(extents=(width, depth, 0.20))
    ground.apply_translation((0.0, 0.0, -0.10))
    color_mesh(ground, (104, 119, 91, 255))
    scene.add_geometry(ground, node_name="terrain_base", geom_name="terrain_base")

    buildings = roads = inferred_heights = named_places = 0
    interior_seeds: list[dict[str, Any]] = []
    used_ids: set[tuple[str, int]] = set()
    for el in elements:
        el_type, osm_id = str(el.get("type", "")), int(el.get("id", 0))
        if (el_type, osm_id) in used_ids:
            continue
        used_ids.add((el_type, osm_id))
        tags = el.get("tags", {})
        points = geometry_xy(el, origin_lat, origin_lon)
        if not points:
            # Standalone OSM nodes are still useful as labeled interaction anchors.
            if el_type == "node" and ("shop" in tags or "amenity" in tags or "tourism" in tags):
                lat, lon = el.get("lat"), el.get("lon")
                if lat is not None and lon is not None:
                    x, y = local_xy(float(lat), float(lon), origin_lat, origin_lon)
                    interior_seeds.append({
                        "osm_id": osm_id, "name": tags.get("name", tags.get("shop", tags.get("amenity", "Unnamed place"))),
                        "category": tags.get("shop", tags.get("amenity", tags.get("tourism", "place"))),
                        "anchor_local_m": [round(x, 2), round(y, 2)],
                        "interior_status": "AI_GENERATED_LATER_NOT_PRESENT_IN_OSM",
                        "npc_seed": "Generate a locally plausible Bangladeshi shopkeeper or resident; do not claim this person's identity is real.",
                    })
                    named_places += 1
            continue
        if el_type == "way" and tags.get("building") and len(points) >= 4:
            polygon = Polygon(points)
            if points[0] != points[-1]:
                polygon = Polygon(points)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            if polygon.is_empty:
                continue
            height, inferred = building_height(tags, osm_id)
            if inferred:
                inferred_heights += 1
            for part_index, mesh in enumerate(extruded_polygon(polygon, height, building_color(tags, osm_id), f"osm_building_{osm_id}")):
                mesh.apply_translation((0.0, 0.0, 0.02))
                scene.add_geometry(mesh, node_name=f"building_{osm_id}_{part_index}", geom_name=f"building_{osm_id}_{part_index}")
            buildings += 1
            name = tags.get("name", "")
            if name or tags.get("shop") or tags.get("amenity"):
                interior_seeds.append({
                    "osm_id": osm_id, "name": name or tags.get("shop", tags.get("amenity", "Unnamed building")),
                    "category": tags.get("shop", tags.get("amenity", tags.get("building", "building"))),
                    "floors_estimate": max(1, round(height / 3.1)),
                    "height_source": "INFERRED" if inferred else ("OSM_HEIGHT_OR_LEVELS"),
                    "footprint_local_m": [[round(x, 2), round(y, 2)] for x, y in points],
                    "interior_status": "AI_GENERATED_LATER_NOT_PRESENT_IN_OSM",
                    "npc_seed": "Create fictional AI shopkeepers/residents appropriate to this place and Bangladesh; never impersonate a real person.",
                    "rooms_seed": ["entrance", "public_or_living_area", "counter_or_reception", "back_room"],
                })
            continue
        if el_type == "way" and tags.get("highway") and len(points) >= 2:
            try:
                line = LineString(points)
                if not line.is_valid or line.length < 1.0:
                    continue
                road_polygon = line.buffer(road_width(tags) / 2.0, cap_style="flat", join_style="mitre")
                parts = list(road_polygon.geoms) if isinstance(road_polygon, MultiPolygon) else [road_polygon]
                for part_index, part in enumerate(parts):
                    if part.area < 0.25:
                        continue
                    for mesh_index, mesh in enumerate(extruded_polygon(part, 0.07, (65, 68, 71, 255), f"road_{osm_id}")):
                        mesh.apply_translation((0.0, 0.0, 0.015))
                        scene.add_geometry(mesh, node_name=f"road_{osm_id}_{part_index}_{mesh_index}", geom_name=f"road_{osm_id}_{part_index}_{mesh_index}")
                roads += 1
            except Exception:
                continue

    glb_path = output_dir / "Dhaka_Explorable_Map.glb"
    glb_path.write_bytes(scene.export(file_type="glb"))
    (output_dir / "Dhaka_OSM_Source.geojson").write_text(
        json.dumps(make_geojson(elements, origin_lat, origin_lon), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (output_dir / "AI_Interior_Seeds.json").write_text(
        json.dumps(interior_seeds, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "product": "Dhaka Explorable 3D Map — first offline map slice",
        "format": "glTF 2.0 binary (.glb)",
        "source": "OpenStreetMap ways/nodes via Overpass API",
        "attribution": OSM_COPYRIGHT,
        "license": "OpenStreetMap data is available under the Open Database License (ODbL); review attribution/share-alike obligations before redistribution.",
        "bbox_south_west_north_east": list(bbox),
        "local_origin_lat_lon": [origin_lat, origin_lon],
        "projected_local_units": "metres; local equirectangular projection; Z is up",
        "extent_metres_approx": {"east_west": round(width, 1), "north_south": round(depth, 1)},
        "feature_counts": {"osm_elements": len(elements), "building_footprints": buildings, "road_ways": roads,
                           "buildings_with_inferred_height": inferred_heights, "named_or_tagged_interaction_seeds": named_places},
        "height_note": "OSM height/building:levels tags are used when present; missing heights are visually inferred and flagged, not surveyed facts.",
        "visual_fidelity_note": "Real OSM road alignments and building footprints, but not photorealistic façade imagery, surveyed heights, or street-view photography. Those require separately licensed source data.",
        "interiors_and_people": "AI_Interior_Seeds.json is a generation brief/anchor dataset, not completed interiors or actual people.",
        "engine_import": "Import Dhaka_Explorable_Map.glb as a Godot MeshInstance3D/scene; retain GeoJSON and manifest for labels, navigation and source attribution.",
    }
    (output_dir / "map_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "ATTRIBUTION.txt").write_text(
        OSM_COPYRIGHT + "\nData license: Open Database License (ODbL) 1.0.\n"
        "Source data is modified into a local 3D representation. See https://www.openstreetmap.org/copyright\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="build/dhaka-map", help="Output folder for GLB, GeoJSON, and metadata")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("SOUTH", "WEST", "NORTH", "EAST"),
                        default=DEFAULT_BBOX, help="OSM extract bounds in decimal degrees")
    parser.add_argument("--input-json", help="Use a saved Overpass JSON response instead of network access")
    args = parser.parse_args()
    bbox = tuple(args.bbox)
    if not (-90 < bbox[0] < bbox[2] < 90 and -180 < bbox[1] < bbox[3] < 180):
        parser.error("bbox must be south, west, north, east in valid coordinate order")
    if args.input_json:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    else:
        payload = fetch_osm(bbox)
    manifest = build_map(payload.get("elements", []), Path(args.out), bbox)
    print(json.dumps(manifest, indent=2))
    if manifest["feature_counts"]["building_footprints"] < 1 or manifest["feature_counts"]["road_ways"] < 1:
        raise SystemExit("Map export contains no buildings or roads; refusing to publish an empty map.")


if __name__ == "__main__":
    main()
