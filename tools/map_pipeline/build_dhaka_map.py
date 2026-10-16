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
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
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
  way["waterway"]({box});
  way["natural"]({box});
  way["landuse"]({box});
  way["leisure"]({box});
  way["railway"]({box});
  way["shop"]({box});
  way["amenity"]({box});
  node["shop"]({box});
  node["amenity"]({box});
  node["tourism"]({box});
  node["historic"]({box});
  node["natural"="tree"]({box});
  node["power"~"pole|tower"]({box});
  node["man_made"="utility_pole"]({box});
  node["highway"="street_lamp"]({box});
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


def building_height(
    tags: dict[str, str], osm_id: int, footprint_area_m2: float | None = None
) -> tuple[float, bool]:
    """Prefer mapped height/levels; otherwise return a flagged footprint-based estimate."""
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
    kind = str(tags.get("building", "yes")).lower()
    area = max(0.0, float(footprint_area_m2 or 0.0))
    if kind in {"industrial", "warehouse", "hangar", "farm"}:
        floors = 1 if area < 900 else 2 if area < 4000 else 3
    elif kind in {"house", "detached", "semidetached_house", "terrace", "bungalow"}:
        floors = 1 if area < 45 else 2 if area < 140 else 3
    elif kind in {"apartments", "commercial", "retail", "office", "hotel", "hospital", "school", "university"}:
        floors = 2 if area < 70 else 3 if area < 180 else 5 if area < 500 else 8 if area < 1400 else 12
    elif kind in {"mosque", "religious", "church", "temple"}:
        floors = 1 if area < 250 else 2
    else:
        floors = 1 if area < 30 else 2 if area < 70 else 3 if area < 160 else 4 if area < 350 else 6 if area < 800 else 9 if area < 1800 else 12
    floor_height = (3.0, 3.1, 3.25)[abs(int(osm_id)) % 3]
    return min(60.0, max(3.0, floors * floor_height)), True


def building_height_source(tags: dict[str, str]) -> str:
    """Describe whether a height came from OSM tags or an unverified estimate."""
    raw_height = str(tags.get("height", "")).replace(" m", "").strip()
    try:
        height = float(raw_height)
        if 2.5 <= height <= 250:
            return "OSM_HEIGHT_TAG"
    except (TypeError, ValueError):
        pass
    raw_levels = str(tags.get("building:levels", "")).strip()
    try:
        levels = int(float(raw_levels))
        if 1 <= levels <= 70:
            return "OSM_BUILDING_LEVELS_TAG"
    except (TypeError, ValueError):
        pass
    return "AREA_CATEGORY_ESTIMATE_UNVERIFIED"


def building_floors_source(tags: dict[str, str]) -> str:
    raw_levels = str(tags.get("building:levels", "")).strip()
    try:
        levels = int(float(raw_levels))
        if 1 <= levels <= 70:
            return "OSM_BUILDING_LEVELS_TAG"
    except (TypeError, ValueError):
        pass
    if building_height_source(tags) == "OSM_HEIGHT_TAG":
        return "DERIVED_FROM_OSM_HEIGHT_TAG"
    return "AREA_CATEGORY_ESTIMATE_UNVERIFIED"


def _parse_color(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    text = str(value).strip().lower()
    if text.startswith("#"):
        text = text[1:]
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) == 6 and re.fullmatch(r"[0-9a-f]{6}", text):
            return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    named = {
        "white": (235, 233, 225, 255), "black": (55, 54, 52, 255),
        "red": (166, 67, 59, 255), "blue": (78, 112, 157, 255),
        "green": (93, 126, 91, 255), "yellow": (205, 183, 89, 255),
        "brown": (128, 91, 66, 255), "gray": (145, 146, 143, 255),
        "grey": (145, 146, 143, 255), "beige": (193, 179, 151, 255),
        "orange": (194, 123, 68, 255), "pink": (194, 139, 151, 255),
    }
    return named.get(text)


def building_color(tags: dict[str, str], osm_id: int) -> tuple[int, int, int, int]:
    """Prefer explicit mapped facade colours; category colours are fallbacks."""
    for key in ("building:colour", "building:color", "facade:colour", "facade:color", "colour", "color"):
        parsed = _parse_color(tags.get(key))
        if parsed:
            return parsed
    kind = tags.get("building", "").lower()
    if kind in {"commercial", "retail", "office", "hotel"} or "shop" in tags:
        return (177, 180, 181, 255)
    if kind in {"industrial", "warehouse", "garages"}:
        return (164, 167, 163, 255)
    if kind in {"religious", "mosque", "church", "temple"}:
        return (190, 184, 166, 255)
    return (183, 178, 171, 255)


def roof_color(tags: dict[str, str], osm_id: int) -> tuple[int, int, int, int]:
    """Use mapped roof colour/material where available; otherwise neutral fallback."""
    for key in ("roof:colour", "roof:color"):
        parsed = _parse_color(tags.get(key))
        if parsed:
            return parsed
    material = str(tags.get("roof:material", "")).lower()
    if material in {"metal", "metal_sheet", "steel", "tin"}:
        return (112, 119, 121, 255)
    if material in {"tile", "terracotta"}:
        return (153, 91, 65, 255)
    if material in {"concrete", "concrete_slab"}:
        return (151, 150, 143, 255)
    return building_color(tags, osm_id)

def road_width(tags: dict[str, str]) -> float:
    raw_width = str(tags.get("width", "")).replace(" m", "").strip()
    try:
        mapped_width = float(raw_width)
        if 1.0 <= mapped_width <= 50.0:
            return mapped_width
    except (TypeError, ValueError):
        pass
    highway = tags.get("highway", "residential").lower()
    widths = {
        "motorway": 14.0, "motorway_link": 8.0, "trunk": 11.0, "trunk_link": 7.0,
        "primary": 8.5, "primary_link": 6.0, "secondary": 6.5, "secondary_link": 5.0,
        "tertiary": 5.2, "tertiary_link": 4.2, "residential": 3.8, "unclassified": 3.8,
        "living_street": 3.5, "service": 2.6, "pedestrian": 2.8, "footway": 1.4,
        "path": 1.2, "cycleway": 1.6, "steps": 1.2, "track": 2.2,
    }
    return widths.get(highway, 3.5)


def road_color(tags: dict[str, str]) -> tuple[int, int, int, int]:
    surface = tags.get("surface", "").lower()
    highway = tags.get("highway", "").lower()
    if surface in {"ground", "dirt", "earth", "gravel", "unpaved", "mud", "sand"}:
        return (126, 112, 91, 255)
    if surface in {"concrete", "concrete:plates", "paving_stones", "sett", "asphalt"}:
        return (63, 67, 70, 255)
    if highway in {"footway", "path", "steps", "cycleway", "pedestrian"}:
        return (116, 117, 111, 255)
    return (78, 79, 78, 255)


def is_water_area(tags: dict[str, str]) -> bool:
    return (
        tags.get("natural", "").lower() == "water"
        or tags.get("waterway", "").lower() in {"riverbank", "dock", "boatyard"}
        or tags.get("landuse", "").lower() in {"reservoir", "basin"}
    )


def surface_color(tags: dict[str, str]) -> tuple[int, int, int, int] | None:
    """Return a restrained ground-surface colour for mapped water and land-use polygons."""
    if is_water_area(tags):
        return (52, 121, 158, 255)
    natural = tags.get("natural", "").lower()
    landuse = tags.get("landuse", "").lower()
    leisure = tags.get("leisure", "").lower()
    if natural in {"wood", "forest"} or landuse == "forest":
        return (62, 101, 64, 255)
    if natural in {"wetland", "marsh", "mud", "scrub"}:
        return (91, 119, 86, 255)
    if natural in {"grassland", "heath"} or landuse in {"grass", "meadow", "village_green"}:
        return (102, 137, 78, 255)
    if leisure in {"park", "garden", "playground", "pitch", "golf_course", "recreation_ground"}:
        return (86, 132, 74, 255)
    if landuse == "aquaculture":
        return (77, 126, 139, 255)
    if landuse in {"farmland", "farmyard", "orchard", "plant_nursery", "allotments"}:
        return (126, 139, 83, 255)
    if landuse in {"residential", "commercial", "retail"}:
        return (124, 126, 111, 255)
    if landuse in {"industrial", "construction", "brownfield"}:
        return (130, 126, 116, 255)
    if landuse in {"cemetery", "religious"}:
        return (96, 126, 91, 255)
    return None


def waterway_width(tags: dict[str, str]) -> float:
    """Use mapped water width when available; otherwise a clearly approximate type default."""
    for key in ("width", "width:waterway"):
        raw = str(tags.get(key, "")).replace(" m", "").strip()
        try:
            width = float(raw)
            if 0.5 <= width <= 3000.0:
                return width
        except (TypeError, ValueError):
            pass
    return {
        "river": 180.0,
        "tidal_channel": 20.0,
        "canal": 12.0,
        "stream": 2.4,
        "drain": 1.4,
        "ditch": 0.9,
    }.get(tags.get("waterway", "").lower(), 2.0)


def flat_surface_mesh(geometry: Any, color: tuple[int, int, int, int], name: str) -> list[trimesh.Trimesh]:
    """Bake mapped water/land-use areas as thin, low-cost surfaces just above the ground."""
    if isinstance(geometry, (MultiPolygon, GeometryCollection)):
        parts = [part for part in geometry.geoms if isinstance(part, Polygon)]
    else:
        parts = [geometry] if isinstance(geometry, Polygon) else []
    result: list[trimesh.Trimesh] = []
    for part in parts:
        if part.is_empty or part.area < 1.0:
            continue
        try:
            mesh = trimesh.creation.extrude_polygon(part, 0.008, engine="earcut")
            mesh.apply_translation((0.0, 0.0, 0.004))
            mesh.visual.vertex_colors = [color] * len(mesh.vertices)
            mesh.metadata["name"] = name
            result.append(mesh)
        except Exception:
            # One malformed or overly complex land-use polygon must not abort the district bake.
            continue
    return result


def road_elevation(tags: dict[str, str]) -> float:
    """Give mapped bridges/layered roads a modest lift above water and ground surfaces."""
    layer_raw = str(tags.get("layer", "0")).strip()
    try:
        layer = int(layer_raw)
    except (TypeError, ValueError):
        layer = 0
    if layer > 0:
        return 0.015 + min(3.0, float(layer) * 0.5)
    if tags.get("bridge", "").lower() not in {"", "no", "false", "0"}:
        return 0.65
    return 0.015


_WINDOW_BOX_TEMPLATE = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
_WINDOW_GLASS_PALETTE = (
    (49, 82, 96, 255),
    (59, 94, 108, 255),
    (70, 104, 116, 255),
)


def facade_window_geometry(
    geometry: Any,
    height: float,
    osm_id: int,
    tile_bounds: Polygon,
) -> tuple[tuple[int, int, int, int], np.ndarray, np.ndarray, int] | None:
    """Build capped, low-poly window panels as one mesh chunk per building."""
    if height < 3.2 or geometry.is_empty:
        return None
    parts = list(geometry.geoms) if isinstance(geometry, MultiPolygon) else [geometry]
    window_centers: list[tuple[float, float, float, float, float]] = []
    floor_rows = min(2, max(1, int(height // 3.2)))
    for part in parts:
        if not isinstance(part, Polygon) or part.area < 20.0:
            continue
        edges: list[tuple[float, tuple[float, float], tuple[float, float], float, float, float]] = []
        coords = list(part.exterior.coords)
        for p1, p2 in zip(coords, coords[1:]):
            dx, dy = float(p2[0] - p1[0]), float(p2[1] - p1[1])
            length = math.hypot(dx, dy)
            if length < 5.0:
                continue
            mid_x, mid_y = (float(p1[0]) + float(p2[0])) * 0.5, (float(p1[1]) + float(p2[1])) * 0.5
            if tile_bounds.boundary.distance(Point(mid_x, mid_y)) < 1.0:
                continue
            nx, ny = -dy / length, dx / length
            if part.contains(Point(mid_x + nx * 0.25, mid_y + ny * 0.25)):
                nx, ny = -nx, -ny
            angle = math.atan2(dy, dx)
            edges.append((length, (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1])), nx, ny, angle))
        # Two longest exterior walls provide visible detail without multiplying draw calls.
        edges.sort(key=lambda edge: edge[0], reverse=True)
        for edge in edges[:2]:
            length, p1, p2, nx, ny, angle = edge
            window_count = min(2, max(1, int(length / 4.5)))
            window_width = min(0.95, max(0.55, length / (window_count + 1) * 0.4))
            for row in range(floor_rows):
                center_z = 0.02 + 1.65 + float(row) * 3.0
                if center_z + 0.45 >= height + 0.02:
                    continue
                for index in range(window_count):
                    fraction = float(index + 1) / float(window_count + 1)
                    cx = p1[0] + (p2[0] - p1[0]) * fraction + nx * 0.035
                    cy = p1[1] + (p2[1] - p1[1]) * fraction + ny * 0.035
                    window_centers.append((cx, cy, center_z, window_width, angle))
                    if len(window_centers) >= 8:
                        break
                if len(window_centers) >= 8:
                    break
            if len(window_centers) >= 8:
                break
        if len(window_centers) >= 8:
            break
    if not window_centers:
        return None

    params = np.asarray(window_centers, dtype=np.float32)
    count = len(params)
    vertices = np.tile(_WINDOW_BOX_TEMPLATE.vertices, (count, 1)).astype(np.float32)
    vertices[:, 0] *= np.repeat(params[:, 3], 8)
    vertices[:, 1] *= 0.055
    vertices[:, 2] *= 0.9
    angles = np.repeat(params[:, 4], 8)
    cos_angles, sin_angles = np.cos(angles), np.sin(angles)
    rotated_x = vertices[:, 0] * cos_angles - vertices[:, 1] * sin_angles
    rotated_y = vertices[:, 0] * sin_angles + vertices[:, 1] * cos_angles
    vertices[:, 0] = rotated_x + np.repeat(params[:, 0], 8)
    vertices[:, 1] = rotated_y + np.repeat(params[:, 1], 8)
    vertices[:, 2] += np.repeat(params[:, 2], 8)
    faces = np.tile(_WINDOW_BOX_TEMPLATE.faces, (count, 1)).astype(np.int32)
    faces += np.repeat(np.arange(count, dtype=np.int32) * 8, 12).reshape(-1, 1)
    color = _WINDOW_GLASS_PALETTE[osm_id % len(_WINDOW_GLASS_PALETTE)]
    return color, vertices, faces, count


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
            is_closed_way = el.get("type") == "way" and len(coords) >= 4 and coords[0] == coords[-1]
            if is_closed_way and (tags.get("building") or surface_color(tags) is not None):
                source_geom = Polygon(coords)
                if not source_geom.is_valid:
                    source_geom = source_geom.buffer(0)
            elif el.get("type") == "way" and (
                tags.get("highway") or tags.get("waterway") or tags.get("railway")
            ) and len(coords) >= 2:
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
    water_polygons = waterway_segments = landuse_areas = railway_ways = bridge_ways = facade_windows = 0
    surface_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    building_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    roof_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    facade_vertices_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    facade_faces_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    facade_vertex_counts: dict[tuple[int, int, int, int], int] = {}
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
            height, inferred = building_height(tags, osm_id, polygon.area)
            if inferred:
                inferred_heights += 1
            facade_color = building_color(tags, osm_id)
            for mesh in extruded_polygon(polygon, height, facade_color, f"osm_building_{osm_id}"):
                mesh.apply_translation((0.0, 0.0, 0.02))
                building_meshes_by_color.setdefault(facade_color, []).append(mesh)
            # Roof caps are batched by mapped colour to reduce mobile draw calls.
            mapped_roof_color = roof_color(tags, osm_id)
            for roof_mesh in extruded_polygon(polygon, 0.055, mapped_roof_color, f"osm_roof_{osm_id}"):
                roof_mesh.apply_translation((0.0, 0.0, height + 0.025))
                roof_meshes_by_color.setdefault(mapped_roof_color, []).append(roof_mesh)
            window_geometry = facade_window_geometry(polygon, height, osm_id, tile_bounds)
            if window_geometry is not None:
                window_color, window_vertices, window_faces, window_count = window_geometry
                vertex_offset = facade_vertex_counts.get(window_color, 0)
                facade_vertices_by_color.setdefault(window_color, []).append(window_vertices)
                facade_faces_by_color.setdefault(window_color, []).append(window_faces + vertex_offset)
                facade_vertex_counts[window_color] = vertex_offset + len(window_vertices)
                facade_windows += window_count
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
                "floors_estimate": max(1, round(height / 3.1)),
                "floors_source": building_floors_source(tags),
                "height_metres": round(height, 2),
                "height_source": building_height_source(tags),
                "facade_status": "PROCEDURAL_LOW_POLY_WINDOW_PANELS; MAPPED_COLOUR_TAGS_IF_PRESENT; OTHERWISE_APPROXIMATE_CATEGORY_COLOUR",
                "geometry_confidence": "OSM_FOOTPRINT; HEIGHT_IS_TAGGED_OR_FLAGGED_AREA_CATEGORY_ESTIMATE",
                "building_tags": {
                    key: tags[key] for key in (
                        "building", "building:levels", "height", "building:material",
                        "building:colour", "building:color", "facade:material",
                        "facade:colour", "facade:color", "roof:shape", "roof:material",
                        "roof:colour", "roof:color", "name", "name:bn", "name:en",
                        "official_name", "brand", "shop", "amenity", "tourism",
                        "addr:street", "addr:housenumber", "addr:place",
                        "image", "wikimedia_commons", "mapillary"
                    ) if key in tags
                },
                "signage_text": {
                    key: tags[key] for key in ("name:bn", "name:en", "name", "official_name", "brand")
                    if key in tags
                },
                "exterior_reference": {
                    "image_tag": tags.get("image", ""),
                    "wikimedia_commons": tags.get("wikimedia_commons", ""),
                    "mapillary_reference": tags.get("mapillary", ""),
                    "downloaded_or_embedded": False,
                    "note": "References only; verify access and reuse rights before runtime use."
                },
                "footprint_local_m": footprint_for_anchor,
                "interior_status": "FICTIONAL_BUILDING_SPECIFIC_INTERIOR_GENERATED_AT_RUNTIME",
                "npc_seed": "Generate fictional residents/workers from this building's own mapped name, category, address and exterior tags; never imply actual occupants.",
                "rooms_seed": ["entrance", "public_or_living_area", "counter_or_reception", "back_room"],
                "interior_generation_key": f"osm:{el_type}/{osm_id}",
            })
            if has_specific_place_tags:
                named_places += 1
            continue
        if el_type == "way" and len(points) >= 4 and points[0] == points[-1]:
            color = surface_color(tags)
            if color is not None:
                try:
                    polygon = Polygon(points)
                    if not polygon.is_valid:
                        polygon = polygon.buffer(0)
                    polygon = polygon.intersection(tile_bounds)
                    surface_meshes = flat_surface_mesh(polygon, color, f"osm_surface_{osm_id}")
                    for mesh in surface_meshes:
                        surface_meshes_by_color.setdefault(color, []).append(mesh)
                    if surface_meshes:
                        if is_water_area(tags):
                            water_polygons += 1
                        else:
                            landuse_areas += 1
                    continue
                except Exception:
                    pass

        if el_type == "way" and tags.get("waterway") and len(points) >= 2:
            try:
                line = LineString(points).intersection(tile_bounds)
                if line.is_empty or line.length < 1.0:
                    continue
                water_polygon = line.buffer(
                    waterway_width(tags) / 2.0, cap_style="flat", join_style="round"
                ).intersection(tile_bounds)
                water_meshes = flat_surface_mesh(water_polygon, (52, 121, 158, 255), f"osm_waterway_{osm_id}")
                for mesh in water_meshes:
                    surface_meshes_by_color.setdefault((52, 121, 158, 255), []).append(mesh)
                if water_meshes:
                    waterway_segments += 1
            except Exception:
                continue
            continue

        if el_type == "way" and tags.get("railway", "").lower() in {"rail", "light_rail", "tram", "narrow_gauge"} and len(points) >= 2:
            try:
                line = LineString(points).intersection(tile_bounds)
                if line.is_empty or line.length < 1.0:
                    continue
                rail_bed = line.buffer(2.2 / 2.0, cap_style="flat", join_style="round").intersection(tile_bounds)
                rail_color = (75, 78, 80, 255)
                rail_meshes = flat_surface_mesh(rail_bed, rail_color, f"osm_railway_{osm_id}")
                for mesh in rail_meshes:
                    surface_meshes_by_color.setdefault(rail_color, []).append(mesh)
                if rail_meshes:
                    railway_ways += 1
            except Exception:
                continue
            continue

        if el_type == "way" and tags.get("highway") and len(points) >= 2:
            try:
                line = LineString(points).intersection(tile_bounds)
                if line.is_empty or line.length < 1.0:
                    continue
                road_polygon = line.buffer(road_width(tags) / 2.0, cap_style="flat", join_style="mitre").intersection(tile_bounds)
                parts = list(road_polygon.geoms) if isinstance(road_polygon, MultiPolygon) else [road_polygon]
                lift = road_elevation(tags)
                for part_index, part in enumerate(parts):
                    if part.area < 0.25:
                        continue
                    for mesh_index, mesh in enumerate(extruded_polygon(part, 0.07, road_color(tags), f"road_{osm_id}")):
                        mesh.apply_translation((0.0, 0.0, lift))
                        scene.add_geometry(mesh, node_name=f"road_{osm_id}_{part_index}_{mesh_index}", geom_name=f"road_{osm_id}_{part_index}_{mesh_index}")
                roads += 1
                if tags.get("bridge", "").lower() not in {"", "no", "false", "0"}:
                    bridge_ways += 1
            except Exception:
                continue

    # Batch the dominant building and roof geometry by material colour. This keeps
    # the mapped silhouettes and height variation while avoiding thousands of
    # separate draw calls when a rural/urban tile streams onto a mobile device.
    for color, meshes in building_meshes_by_color.items():
        if not meshes:
            continue
        combined = color_mesh(trimesh.util.concatenate(meshes), color)
        color_name = "".join(f"{channel:02x}" for channel in color)
        scene.add_geometry(combined, node_name=f"mapped_buildings_{color_name}", geom_name=f"mapped_buildings_{color_name}")

    for color, meshes in roof_meshes_by_color.items():
        if not meshes:
            continue
        combined = color_mesh(trimesh.util.concatenate(meshes), color)
        color_name = "".join(f"{channel:02x}" for channel in color)
        scene.add_geometry(combined, node_name=f"mapped_roofs_{color_name}", geom_name=f"mapped_roofs_{color_name}")

    for color, meshes in surface_meshes_by_color.items():
        if not meshes:
            continue
        combined = trimesh.util.concatenate(meshes)
        color_name = "".join(f"{channel:02x}" for channel in color[:3])
        scene.add_geometry(combined, node_name=f"mapped_surface_{color_name}", geom_name=f"mapped_surface_{color_name}")

    for color, vertex_chunks in facade_vertices_by_color.items():
        if not vertex_chunks:
            continue
        vertices = np.concatenate(vertex_chunks, axis=0)
        faces = np.concatenate(facade_faces_by_color[color], axis=0)
        combined = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        color_mesh(combined, color)
        color_name = "".join(f"{channel:02x}" for channel in color[:3])
        scene.add_geometry(combined, node_name=f"facade_windows_{color_name}", geom_name=f"facade_windows_{color_name}")

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
                           "mapped_utility_poles": utility_poles, "mapped_street_lamps": street_lamps, "facade_window_panels": facade_windows, "building_mesh_batches": len(building_meshes_by_color), "roof_mesh_batches": len(roof_meshes_by_color),
                            "water_polygons": water_polygons, "waterway_segments": waterway_segments,
                            "landuse_areas": landuse_areas, "railway_ways": railway_ways, "bridge_ways": bridge_ways},
        "height_note": "OSM height/building:levels tags are used when present; otherwise footprint-area/building-category estimates with deterministic floor-height variation are flagged as inferred, not surveyed facts.",
        "hydrography_note": "Mapped OSM water polygons are kept to their source outlines. River/canal centerlines without mapped widths use type-based approximate widths and are not survey-grade water boundaries.",
         "visual_fidelity_note": "Real OSM road alignments, building footprints, mapped water and land-use surfaces, and tagged bridges are included. Sufficiently large buildings receive lightweight procedural low-poly window panels; building and roof meshes are batched by material colour to reduce mobile draw calls. Explicit facade/roof colour tags are used where available. Bangla/English names and exterior image references are preserved per building. This is not photorealistic street imagery; that requires separately licensed source data.",
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
