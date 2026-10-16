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
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import trimesh
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box, mapping, shape
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
    if isinstance(geom, (MultiPolygon, GeometryCollection)):
        parts = [part for part in geom.geoms if isinstance(part, Polygon)]
    else:
        parts = [geom]
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
    # Do not invent a different height for every unmapped building. A low,
    # neutral placeholder keeps geometry usable while the manifest/seed marks
    # it as unverified; real height must come from tagged/surveyed data.
    return 3.2, True


def building_color(tags: dict[str, str], osm_id: int) -> tuple[int, int, int, int]:
    """Stable category color, never pseudo-random per-building facade color.

    These are map-rendering placeholders, NOT claims about the real facade.
    Exact facade appearance requires licensed street-level imagery or surveyed
    building-specific material data.
    """
    kind = tags.get("building", "").lower()
    if kind in {"commercial", "retail", "office", "hotel"} or "shop" in tags:
        return (177, 180, 181, 255)
    if kind in {"industrial", "warehouse", "garages"}:
        return (164, 167, 163, 255)
    if kind in {"religious", "mosque", "church", "temple"}:
        return (190, 184, 166, 255)
    return (183, 178, 171, 255)


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


def make_geojson(
    elements: list[dict[str, Any]],
    origin_lat: float,
    origin_lon: float,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    """Export only source features clipped to the requested geographic tile."""
    south, west, north, east = bbox
    tile = box(west, south, east, north)
    features = []
    for el in elements:
        tags = el.get("tags", {})
        geom = el.get("geometry", [])
        if not tags:
            continue
        if el.get("type") == "node" and "lat" in el and "lon" in el:
            source_geom = Point(float(el["lon"]), float(el["lat"]))
        else:
            coords = [(float(p["lon"]), float(p["lat"])) for p in geom if "lon" in p and "lat" in p]
            if not coords:
                continue
            if el.get("type") == "way" and tags.get("building") and len(coords) >= 4 and coords[0] == coords[-1]:
                source_geom = Polygon(coords)
                if not source_geom.is_valid:
                    source_geom = source_geom.buffer(0)
            elif el.get("type") == "way" and tags.get("highway") and len(coords) >= 2:
                source_geom = LineString(coords)
            else:
                source_geom = Point(coords[0])
        clipped = source_geom.intersection(tile)
        if clipped.is_empty:
            continue
        if clipped.geom_type in {"GeometryCollection", "MultiLineString", "MultiPolygon"}:
            parts = [g for g in clipped.geoms if not g.is_empty and g.geom_type in {"Polygon", "LineString", "Point"}]
            if not parts:
                continue
            if len(parts) == 1:
                clipped = parts[0]
            else:
                # Keep multi-part clipping valid GeoJSON without extending past the tile.
                geometry = mapping(clipped)
                features.append({
                    "type": "Feature",
                    "id": f"{el.get('type', 'element')}/{el.get('id', 0)}",
                    "geometry": geometry,
                    "properties": {"osm_type": el.get("type"), "osm_id": el.get("id"), **tags},
                })
                continue
        features.append({
            "type": "Feature",
            "id": f"{el.get('type', 'element')}/{el.get('id', 0)}",
            "geometry": mapping(clipped),
            "properties": {"osm_type": el.get("type"), "osm_id": el.get("id"), **tags},
        })
    return {"type": "FeatureCollection", "name": "Dhaka OSM source features (clipped to tile)", "features": features}


def add_node_environment_prop(scene: trimesh.Scene, x: float, y: float,
                              tags: dict[str, str], osm_id: int) -> str:
    """Add simple, clearly approximate 3D props at mapped OSM tree/pole/light nodes."""
    if tags.get("natural", "").lower() == "tree":
        trunk = trimesh.creation.cylinder(radius=0.13, height=2.2, sections=7)
        trunk.apply_translation((x, y, 1.1))
        color_mesh(trunk, (105, 76, 51, 255))
        canopy = trimesh.creation.icosphere(subdivisions=1, radius=1.05)
        canopy.apply_scale((1.0, 1.0, 1.15))
        canopy.apply_translation((x, y, 2.8))
        color_mesh(canopy, (58, 105, 61, 255))
        scene.add_geometry(trunk, node_name=f"osm_tree_trunk_{osm_id}", geom_name=f"osm_tree_trunk_{osm_id}")
        scene.add_geometry(canopy, node_name=f"osm_tree_canopy_{osm_id}", geom_name=f"osm_tree_canopy_{osm_id}")
        return "tree"

    power_kind = tags.get("power", "").lower()
    is_utility_pole = power_kind in {"pole", "tower"} or tags.get("man_made", "").lower() == "utility_pole"
    is_street_lamp = tags.get("highway", "").lower() == "street_lamp" or tags.get("man_made", "").lower() == "street_lamp"
    if not is_utility_pole and not is_street_lamp:
        return ""

    raw_height = tags.get("height", "").replace(" m", "").strip()
    try:
        height = float(raw_height)
        if not 3.0 <= height <= 35.0:
            raise ValueError
    except (TypeError, ValueError):
        height = 9.0 if power_kind == "tower" else (6.5 if is_utility_pole else 5.5)

    pole_radius = 0.17 if power_kind == "tower" else (0.11 if is_utility_pole else 0.075)
    pole = trimesh.creation.cylinder(radius=pole_radius, height=height, sections=8)
    pole.apply_translation((x, y, height / 2.0))
    color_mesh(pole, (111, 119, 121, 255))
    scene.add_geometry(pole, node_name=f"osm_utility_pole_{osm_id}", geom_name=f"osm_utility_pole_{osm_id}")

    if is_utility_pole:
        arm = trimesh.creation.box(extents=(2.0 if power_kind == "tower" else 1.25, 0.12, 0.12))
        arm.apply_translation((x, y, height * 0.82))
        color_mesh(arm, (91, 99, 101, 255))
        scene.add_geometry(arm, node_name=f"osm_power_crossarm_{osm_id}", geom_name=f"osm_power_crossarm_{osm_id}")
        for insulator_index, dx in enumerate((-0.72, 0.0, 0.72)):
            insulator = trimesh.creation.cylinder(radius=0.07, height=0.24, sections=6)
            insulator.apply_translation((x + dx, y, height * 0.82 + 0.16))
            color_mesh(insulator, (204, 205, 194, 255))
            scene.add_geometry(insulator, node_name=f"osm_power_insulator_{osm_id}_{insulator_index}", geom_name=f"osm_power_insulator_{osm_id}_{insulator_index}")
    else:
        arm = trimesh.creation.box(extents=(0.75, 0.07, 0.07))
        arm.apply_translation((x + 0.32, y, height - 0.1))
        color_mesh(arm, (80, 88, 90, 255))
        scene.add_geometry(arm, node_name=f"osm_streetlamp_arm_{osm_id}", geom_name=f"osm_streetlamp_arm_{osm_id}")
        lamp = trimesh.creation.box(extents=(0.36, 0.20, 0.12))
        lamp.apply_translation((x + 0.65, y, height - 0.16))
        color_mesh(lamp, (236, 220, 160, 255))
        scene.add_geometry(lamp, node_name=f"osm_streetlamp_head_{osm_id}", geom_name=f"osm_streetlamp_head_{osm_id}")
    return "utility_pole" if is_utility_pole else "street_lamp"


def build_map(elements: list[dict[str, Any]], output_dir: Path,
              bbox: tuple[float, float, float, float] = DEFAULT_BBOX) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    south, west, north, east = bbox
    origin_lat, origin_lon = (south + north) / 2.0, (west + east) / 2.0
    min_xy = local_xy(south, west, origin_lat, origin_lon)
    max_xy = local_xy(north, east, origin_lat, origin_lon)
    width, depth = max_xy[0] - min_xy[0], max_xy[1] - min_xy[1]
    tile_bounds = Polygon([(-width / 2, -depth / 2), (width / 2, -depth / 2),
                           (width / 2, depth / 2), (-width / 2, depth / 2)])
    scene = trimesh.Scene()
    ground = trimesh.creation.box(extents=(width, depth, 0.20))
    ground.apply_translation((0.0, 0.0, -0.10))
    color_mesh(ground, (104, 119, 91, 255))
    scene.add_geometry(ground, node_name="terrain_base", geom_name="terrain_base")

    buildings = roads = inferred_heights = named_places = 0
    trees = utility_poles = street_lamps = 0
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
            # Standalone mapped nodes can provide both environment props and interaction anchors.
            if el_type == "node":
                lat, lon = el.get("lat"), el.get("lon")
                if lat is not None and lon is not None:
                    x, y = local_xy(float(lat), float(lon), origin_lat, origin_lon)
                    # Keep multi-metre props inside the tile; a neighbouring tile owns edge-adjacent nodes.
                    prop_kind = ""
                    if abs(x) <= width / 2.0 - 1.1 and abs(y) <= depth / 2.0 - 1.1:
                        prop_kind = add_node_environment_prop(scene, x, y, tags, osm_id)
                    if prop_kind == "tree":
                        trees += 1
                    elif prop_kind == "utility_pole":
                        utility_poles += 1
                    elif prop_kind == "street_lamp":
                        street_lamps += 1
                    if "shop" in tags or "amenity" in tags or "tourism" in tags:
                        interior_seeds.append({
                            "osm_id": osm_id,
                            "name": tags.get("name", tags.get("shop", tags.get("amenity", "Unnamed place"))),
                            "category": tags.get("shop", tags.get("amenity", tags.get("tourism", "place"))),
                            "anchor_local_m": [round(x, 2), round(y, 2)],
                            "interior_status": "FICTIONAL_GAME_INTERIOR_GENERATED_AT_RUNTIME",
                            "npc_seed": "Generate a locally plausible fictional Bangladeshi shopkeeper or resident; do not claim this person's identity is real.",
                        })
                        named_places += 1
            continue
        if el_type == "way" and tags.get("building") and len(points) >= 4:
            polygon = Polygon(points)
            if points[0] != points[-1]:
                polygon = Polygon(points)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            polygon = polygon.intersection(tile_bounds)
            if polygon.is_empty or polygon.area < 0.5:
                continue
            height, inferred = building_height(tags, osm_id)
            if inferred:
                inferred_heights += 1
            for part_index, mesh in enumerate(extruded_polygon(polygon, height, building_color(tags, osm_id), f"osm_building_{osm_id}")):
                mesh.apply_translation((0.0, 0.0, 0.02))
                scene.add_geometry(mesh, node_name=f"building_{osm_id}_{part_index}", geom_name=f"building_{osm_id}_{part_index}")
            buildings += 1
            name = tags.get("name", "")
            has_specific_place_tags = bool(name or tags.get("shop") or tags.get("amenity") or tags.get("tourism"))
            building_kind = str(tags.get("building", "building")).lower()
            if tags.get("shop"):
                interior_category = str(tags["shop"])
            elif tags.get("amenity"):
                interior_category = str(tags["amenity"])
            elif building_kind in {"house", "residential", "apartments", "detached", "semidetached_house", "terrace", "dormitory"}:
                interior_category = "residential"
            elif building_kind in {"commercial", "retail", "office", "industrial", "warehouse", "school", "hospital", "hotel", "church", "mosque", "temple"}:
                interior_category = building_kind
            else:
                interior_category = "building"
            if has_specific_place_tags:
                footprint_for_anchor = [[round(x, 2), round(y, 2)] for x, y in points]
            else:
                # A compact bbox is sufficient to position a generic entrance; the GLB
                # retains the actual OSM footprint. Avoid duplicating every polygon vertex
                # for every unnamed building in the streamed seed JSON.
                min_x, min_y, max_x, max_y = polygon.bounds
                footprint_for_anchor = [
                    [round(min_x, 2), round(min_y, 2)], [round(max_x, 2), round(min_y, 2)],
                    [round(max_x, 2), round(max_y, 2)], [round(min_x, 2), round(max_y, 2)],
                ]
            interior_seeds.append({
                "osm_id": osm_id,
                "name": name or tags.get("shop", tags.get("amenity", "Unnamed building")),
                "category": interior_category,
                "anchor_kind": "named_or_tagged" if has_specific_place_tags else "generic_building",
                "floors_estimate": None if inferred else max(1, round(height / 3.1)),
                "height_metres": round(height, 2),
                "height_source": "UNVERIFIED_PLACEHOLDER_3_2M" if inferred else "OSM_HEIGHT_OR_LEVELS",
                "facade_status": "NO_VERIFIED_FACADE_TEXTURE",
                "geometry_confidence": "OSM_FOOTPRINT; VERIFY_ON_GROUND_OR_WITH_LICENSED_IMAGERY",
                "footprint_local_m": footprint_for_anchor,
                "interior_status": "FICTIONAL_GAME_INTERIOR_GENERATED_AT_RUNTIME",
                "npc_seed": "Create fictional residents/workers appropriate to the mapped building category; never imply actual occupants.",
                "rooms_seed": ["entrance", "public_or_living_area", "counter_or_reception", "back_room"],
            })
            if has_specific_place_tags:
                named_places += 1
            continue
        if el_type == "way" and tags.get("highway") and len(points) >= 2:
            try:
                line = LineString(points).intersection(tile_bounds)
                if line.is_empty or line.length < 1.0:
                    continue
                road_polygon = line.buffer(road_width(tags) / 2.0, cap_style="flat", join_style="mitre").intersection(tile_bounds)
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

    scene_bounds = scene.bounds
    if (scene_bounds[0][0] < -width / 2 - 1 or scene_bounds[1][0] > width / 2 + 1 or
            scene_bounds[0][1] < -depth / 2 - 1 or scene_bounds[1][1] > depth / 2 + 1):
        raise RuntimeError("Export geometry extends beyond the requested tile; refusing to publish an oversized map.")
    # Convert the internal Z-up extrusion coordinates (X=east, Y=north, Z=up)
    # to glTF/Godot coordinates (X=east, Y=up, Z=south). Without this transform,
    # the imported city can stand on its side despite having valid GLB geometry.
    gltf_axes = [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, -1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    scene.apply_transform(gltf_axes)
    glb_path = output_dir / "Dhaka_Explorable_Map.glb"
    glb_path.write_bytes(scene.export(file_type="glb"))
    (output_dir / "Dhaka_OSM_Source.geojson").write_text(
        json.dumps(make_geojson(elements, origin_lat, origin_lon, bbox), ensure_ascii=False, separators=(",", ":")),
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
                           "buildings_with_inferred_height": inferred_heights, "named_or_tagged_interaction_seeds": named_places,
                           "interior_anchors": len(interior_seeds), "mapped_trees": trees,
                           "mapped_utility_poles": utility_poles, "mapped_street_lamps": street_lamps},
        "height_note": "OSM height/building:levels tags are used when present; missing heights are visually inferred and flagged, not surveyed facts.",
        "visual_fidelity_note": "Real OSM road alignments and building footprints, but not photorealistic façade imagery, surveyed heights, or street-view photography. Those require separately licensed source data.",
        "interiors_and_people": "AI_Interior_Seeds.json includes anchors for every mapped building footprint plus named/tagged places; the game generates fictional interiors and residents at runtime, not actual private interiors or real people.",
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
