#!/usr/bin/env python3
"""Build an exportable, georeferenced 3D Dhaka block from OpenStreetMap geometry.

The output is an offline GLB made from real OSM road centerlines and building
footprints. OSM does not provide photorealistic street imagery or most interiors;
those must come from a separately licensed imagery provider or authored assets.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import math
import os
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
  relation["natural"]({box});
  relation["landuse"]({box});
  relation["leisure"]({box});
  relation["water"]({box});
  way["railway"]({box});
  way["shop"]({box});
  way["amenity"]({box});
  node["shop"]({box});
  node["amenity"]({box});
  node["entrance"]({box});
  node["door"]({box});
  node["tourism"]({box});
  node["historic"]({box});
  node["natural"="tree"]({box});
  node["power"~"pole|tower"]({box});
  node["man_made"="utility_pole"]({box});
  node["highway"="street_lamp"]({box});
);
out body geom;"""


def relation_area_polygons(
    element: dict[str, Any], origin_lat: float, origin_lon: float, tile_bounds: Polygon
) -> list[Polygon]:
    """Build clipped multipolygon rings from OSM relation outer/inner member ways.

    OSM land-cover and water areas are often relations rather than closed ways.
    Stitch member segments by shared endpoints, retaining inner rings as holes.
    Incomplete or invalid rings are skipped instead of fabricating geometry.
    """
    members = element.get("members", [])
    if not isinstance(members, list):
        return []

    def stitched_rings(role: str) -> list[list[tuple[float, float]]]:
        segments: list[list[tuple[float, float]]] = []
        for member in members:
            if member.get("type") != "way" or member.get("role") != role:
                continue
            geometry = member.get("geometry", [])
            coords = [
                local_xy(float(point["lat"]), float(point["lon"]), origin_lat, origin_lon)
                for point in geometry
                if "lat" in point and "lon" in point
            ]
            if len(coords) >= 2:
                segments.append(coords)
        rings: list[list[tuple[float, float]]] = []
        while segments:
            ring = segments.pop(0)
            while len(ring) >= 3 and ring[0] != ring[-1]:
                match = None
                reverse = False
                for index, segment in enumerate(segments):
                    if ring[-1] == segment[0]:
                        match = index
                        break
                    if ring[-1] == segment[-1]:
                        match = index
                        reverse = True
                        break
                if match is None:
                    break
                segment = segments.pop(match)
                ring.extend(reversed(segment[:-1]) if reverse else segment[1:])
            if len(ring) >= 4 and ring[0] == ring[-1]:
                rings.append(ring)
        return rings

    outer_rings = stitched_rings("outer")
    inner_rings = stitched_rings("inner")
    polygons: list[Polygon] = []
    for outer in outer_rings:
        shell = Polygon(outer)
        if shell.is_empty or shell.area < 0.5:
            continue
        holes = []
        for inner in inner_rings:
            hole = Polygon(inner)
            if not hole.is_empty and shell.contains(hole.representative_point()):
                holes.append(inner)
        polygon = Polygon(outer, holes)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        clipped = polygon.intersection(tile_bounds)
        parts = list(clipped.geoms) if isinstance(clipped, MultiPolygon) else [clipped]
        polygons.extend(
            part for part in parts
            if isinstance(part, Polygon) and not part.is_empty and part.area >= 0.5
        )
    return polygons


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



def normalize_facade_name(value: Any) -> str:
    """Normalize Unicode and spacing without weakening exact landmark-name matching."""
    import unicodedata

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\u200b", "").replace("\ufeff", "")
    return " ".join(text.split()).casefold()


def load_facade_photo_catalog() -> dict[str, dict[str, Any]]:
    """Load only locally downloaded, allowlisted photos; map aliases to exact matches."""
    catalog_path = Path(os.environ.get("WSB_FACADE_IMAGE_CATALOG", "tools/map_pipeline/shariatpur_facade_images.json"))
    image_dir = Path(os.environ.get("WSB_FACADE_IMAGE_DIR", "build/facade-images"))
    if not catalog_path.is_file() or not image_dir.is_dir():
        return {}
    try:
        from PIL import Image
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in catalog.get("images", []):
        # Rights and name matching are not enough to prove a photograph is the
        # correct exterior view. Only use images with explicit visual QA approval.
        if item.get("facade_eligible") is not True:
            continue
        if str(item.get("view_type", "")).strip().lower() != "exterior":
            continue
        if str(item.get("visual_qa", "")).strip().lower() != "passed":
            continue
        filename = str(item.get("file_name", "")).strip()
        path = image_dir / filename
        if not filename or not path.is_file():
            continue
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                image.load()
        except Exception:
            continue
        record = {"image": image, "metadata": item}
        for alias in item.get("match_names", []):
            normalized = normalize_facade_name(alias)
            if normalized:
                result[normalized] = record
    return result


def load_interior_reference_catalog() -> dict[str, dict[str, Any]]:
    """Load explicitly licensed interior photos for exact-name in-game interiors only."""
    catalog_path = Path(os.environ.get("WSB_FACADE_IMAGE_CATALOG", "tools/map_pipeline/shariatpur_facade_images.json"))
    image_dir = Path(os.environ.get("WSB_FACADE_IMAGE_DIR", "build/facade-images"))
    if not catalog_path.is_file() or not image_dir.is_dir():
        return {}
    try:
        from PIL import Image
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in catalog.get("images", []):
        if item.get("interior_reference_eligible") is not True:
            continue
        if str(item.get("interior_view_type", "")).strip().lower() != "interior":
            continue
        if str(item.get("interior_visual_qa", "")).strip().lower() != "passed":
            continue
        if str(item.get("license", "")).strip() not in {"CC BY 4.0", "CC BY-SA 4.0"}:
            continue
        filename = str(item.get("file_name", "")).strip()
        path = image_dir / filename
        if not filename or not path.is_file():
            continue
        try:
            with Image.open(path) as source:
                image = source.convert("RGB")
                image.load()
        except Exception:
            continue
        record = {"image": image, "metadata": item, "path": path}
        for alias in item.get("match_names", []):
            normalized = normalize_facade_name(alias)
            if normalized:
                result[normalized] = record
    return result


def match_named_image(tags: dict[str, str], catalog: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Match a licensed image to the exact mapped building name; never use fuzzy nearest-place guesses."""
    for key in ("name", "name:bn", "official_name", "name:en"):
        value = normalize_facade_name(tags.get(key, ""))
        if value and value in catalog:
            return catalog[value]
    return None


def match_facade_photo(tags: dict[str, str], catalog: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Use strict aliases only; do not assign a landmark photo to a guessed building."""
    return match_named_image(tags, catalog)


def facade_photo_panel(
    polygon: Polygon | MultiPolygon,
    building_height_m: float,
    image: Any,
    osm_id: int,
    image_id: str,
) -> trimesh.Trimesh | None:
    """Place a licensed landmark photograph as a textured panel on its named building wall."""
    if isinstance(polygon, MultiPolygon):
        parts = [part for part in polygon.geoms if isinstance(part, Polygon) and not part.is_empty]
        if not parts:
            return None
        part = max(parts, key=lambda item: item.area)
    else:
        part = polygon
    coordinates = list(part.exterior.coords)
    if len(coordinates) < 4:
        return None
    best = None
    best_length = 0.0
    for index in range(1, len(coordinates)):
        start = np.asarray(coordinates[index - 1], dtype=np.float64)
        end = np.asarray(coordinates[index], dtype=np.float64)
        delta = end - start
        length = float(np.linalg.norm(delta))
        if length > best_length:
            best = (start, end, delta / max(length, 1e-9), length)
            best_length = length
    if best is None or best_length < 2.0:
        return None
    start, end, tangent, wall_length = best
    midpoint = (start + end) * 0.5
    normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
    centroid = np.asarray([part.centroid.x, part.centroid.y], dtype=np.float64)
    if float(np.dot(normal, midpoint - centroid)) < 0.0:
        normal *= -1.0
    try:
        image_width, image_height = image.size
        aspect = float(image_width) / max(1.0, float(image_height))
    except Exception:
        return None
    panel_height = min(max(1.6, float(building_height_m) * 0.78), max(1.0, float(building_height_m) - 0.35))
    panel_width = min(wall_length * 0.82, panel_height * aspect)
    if panel_width < 1.0 or panel_height < 1.0:
        return None
    center = midpoint + normal * 0.065
    left = center - tangent * (panel_width * 0.5)
    right = center + tangent * (panel_width * 0.5)
    z_bottom = 0.22
    z_top = z_bottom + panel_height
    vertices = np.asarray([
        [left[0], left[1], z_bottom],
        [right[0], right[1], z_bottom],
        [right[0], right[1], z_top],
        [left[0], left[1], z_top],
    ], dtype=np.float64)
    faces = np.asarray([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    material = trimesh.visual.material.PBRMaterial(
        name=f"LicensedFacadePhoto_{image_id}",
        baseColorTexture=image,
        metallicFactor=0.0,
        roughnessFactor=1.0,
    )
    panel = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    panel.visual = trimesh.visual.texture.TextureVisuals(
        uv=np.asarray([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]], dtype=np.float64),
        material=material,
    )
    panel.metadata["name"] = f"licensed_facade_photo_{image_id}_{osm_id}"
    return panel

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

def roof_shape_for_building(tags: dict[str, str], footprint_area_m2: float, height_m: float) -> tuple[str, str]:
    """Prefer OSM roof-shape tags; infer pitched roofs only for small low-rise homes."""
    raw = str(tags.get("roof:shape", "")).strip().lower().replace("-", "_").replace(" ", "_")
    if raw in {"flat", "terrace"}:
        return "flat", "OSM_ROOF_SHAPE_TAG"
    if raw in {"gabled", "saltbox"}:
        return "gabled", "OSM_ROOF_SHAPE_TAG" if raw == "gabled" else "OSM_SALTB0X_APPROXIMATED_AS_GABLED"
    if raw in {"hipped", "half_hipped"}:
        return "hipped", "OSM_ROOF_SHAPE_TAG"
    if raw in {"skillion", "lean_to"}:
        return "skillion", "OSM_ROOF_SHAPE_TAG"
    kind = str(tags.get("building", "")).strip().lower()
    material = str(tags.get("roof:material", "")).strip().lower().replace(" ", "_")
    low_rise_home = kind in {
        "house", "detached", "semidetached_house", "terrace", "bungalow", "residential"
    } and footprint_area_m2 <= 350.0 and height_m <= 6.0
    likely_tin_home = material in {
        "metal", "metal_sheet", "steel", "tin", "corrugated_metal", "corrugated_steel"
    } and footprint_area_m2 <= 500.0 and height_m <= 6.0
    if low_rise_home:
        return "gabled", "INFERRED_SMALL_LOW_RISE_HOME_NO_ROOF_SHAPE_TAG"
    if likely_tin_home:
        return "gabled", "INFERRED_SMALL_TIN_ROOF_NO_ROOF_SHAPE_TAG"
    if raw:
        return "flat", "OSM_ROOF_SHAPE_TAG_NOT_RENDERED:" + raw
    return "flat", "FLAT_CAP_DEFAULT_NO_ROOF_SHAPE_SOURCE"


def procedural_roof_color(tags: dict[str, str], osm_id: int, shape_source: str) -> tuple[int, int, int, int]:
    """Preserve explicit roof data; use a separate labelled palette only when it is absent."""
    if any(str(tags.get(key, "")).strip() for key in ("roof:colour", "roof:color", "roof:material")):
        return roof_color(tags, osm_id)
    if shape_source.startswith("INFERRED_") or shape_source == "OSM_ROOF_SHAPE_TAG" or shape_source == "OSM_SALTB0X_APPROXIMATED_AS_GABLED":
        palette = (
            (104, 111, 112, 255), (124, 129, 127, 255), (88, 98, 101, 255),
            (137, 113, 92, 255), (102, 105, 99, 255),
        )
        return palette[abs(int(osm_id)) % len(palette)]
    return roof_color(tags, osm_id)


def procedural_roof_mesh(geometry: Any, wall_height_m: float, shape_name: str, osm_id: int) -> trimesh.Trimesh | None:
    """Create a low-cost metric roof shell when a mapped footprint supports the shape."""
    if shape_name not in {"gabled", "hipped", "skillion"} or geometry.is_empty:
        return None
    parts = list(geometry.geoms) if isinstance(geometry, MultiPolygon) else [geometry]
    valid_parts = [part for part in parts if isinstance(part, Polygon) and not part.is_empty and part.area >= 8.0]
    if not valid_parts:
        return None
    part = max(valid_parts, key=lambda item: item.area)
    rotated = part.minimum_rotated_rectangle
    if rotated.is_empty or rotated.area <= 0.0 or part.area / rotated.area < 0.74:
        return None
    pts = [(float(x), float(y)) for x, y in list(rotated.exterior.coords)[:-1]]
    if len(pts) != 4:
        return None
    lengths = [
        math.hypot(pts[(i + 1) % 4][0] - pts[i][0], pts[(i + 1) % 4][1] - pts[i][1])
        for i in range(4)
    ]
    if max(lengths) < 3.0 or min(lengths) < 2.2:
        return None
    if lengths[0] >= lengths[1]:
        a, b, c, d = pts
    else:
        a, b, c, d = pts[1], pts[2], pts[3], pts[0]
    left_mid = ((a[0] + d[0]) * 0.5, (a[1] + d[1]) * 0.5)
    right_mid = ((b[0] + c[0]) * 0.5, (b[1] + c[1]) * 0.5)
    short_width = min(math.hypot(b[0] - a[0], b[1] - a[1]),
                      math.hypot(c[0] - b[0], c[1] - b[1]))
    pitch = min(1.45, max(0.48, short_width * 0.27))
    eave_z = float(wall_height_m) + 0.08
    ridge_z = eave_z + pitch
    vertices = np.asarray([
        [a[0], a[1], eave_z], [b[0], b[1], eave_z],
        [c[0], c[1], eave_z], [d[0], d[1], eave_z],
        [left_mid[0], left_mid[1], ridge_z], [right_mid[0], right_mid[1], ridge_z],
    ], dtype=np.float64)
    if shape_name == "skillion":
        vertices[2, 2] = eave_z + pitch
        vertices[3, 2] = eave_z + pitch
        faces = np.asarray([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
    elif shape_name == "hipped":
        long_vec = np.asarray([right_mid[0] - left_mid[0], right_mid[1] - left_mid[1]])
        length = float(np.linalg.norm(long_vec))
        if length > 1e-5:
            unit = long_vec / length
            inset = min(short_width * 0.48, length * 0.22)
            vertices[4, 0:2] = np.asarray(left_mid) + unit * inset
            vertices[5, 0:2] = np.asarray(right_mid) - unit * inset
        faces = np.asarray([
            [0, 1, 5], [0, 5, 4],
            [3, 2, 5], [3, 5, 4],
            [0, 4, 3], [1, 2, 5],
        ], dtype=np.int64)
    else:
        faces = np.asarray([
            [0, 1, 5], [0, 5, 4],
            [3, 5, 2], [3, 4, 5],
            [0, 4, 3], [1, 2, 5],
        ], dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    try:
        mesh.fix_normals()
    except Exception:
        # Open roof shells are not watertight solids. Preserve valid triangles
        # if a trimesh release cannot orient an open multi-face shell.
        pass
    if not np.isfinite(mesh.vertices).all() or mesh.area < 1.0:
        return None
    mesh.metadata["roof_shape"] = shape_name
    mesh.metadata["source_osm_id"] = int(osm_id)
    return mesh


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


def vegetation_kind(tags: dict[str, str]) -> str:
    """Classify mapped green polygons for conservative, clearly procedural vegetation."""
    natural = tags.get("natural", "").lower()
    landuse = tags.get("landuse", "").lower()
    leisure = tags.get("leisure", "").lower()
    if natural in {"wood", "forest"} or landuse == "forest":
        return "forest"
    if landuse == "orchard":
        return "orchard"
    if natural in {"scrub", "wetland", "marsh"}:
        return "scrub"
    if leisure in {"park", "garden", "recreation_ground", "golf_course"}:
        return "park"
    if landuse in {"farmland", "farmyard", "plant_nursery", "allotments"}:
        return "farmland"
    return ""


def procedural_tree_sites(
    polygon: Polygon | MultiPolygon,
    osm_id: int,
    kind: str,
    max_trees: int = 90,
) -> list[tuple[float, float]]:
    """Return deterministic low-poly tree locations constrained to a mapped green polygon."""
    if polygon.is_empty or max_trees <= 0:
        return []
    spacing_by_kind = {
        "forest": 23.0,
        "orchard": 13.0,
        "scrub": 34.0,
        "park": 30.0,
        "farmland": 58.0,
    }
    spacing = spacing_by_kind.get(kind, 38.0)
    rng = np.random.default_rng(abs(int(osm_id)) % (2**32))
    parts = list(polygon.geoms) if isinstance(polygon, MultiPolygon) else [polygon]
    sites: list[tuple[float, float]] = []
    for part in sorted(parts, key=lambda item: item.area, reverse=True):
        if not isinstance(part, Polygon) or part.is_empty or part.area < 90.0:
            continue
        min_x, min_y, max_x, max_y = part.bounds
        offset_x = float(rng.uniform(0.0, spacing))
        offset_y = float(rng.uniform(0.0, spacing))
        x_values = np.arange(min_x + offset_x, max_x, spacing)
        y_values = np.arange(min_y + offset_y, max_y, spacing)
        for x in x_values:
            for y in y_values:
                if not part.contains(Point(float(x), float(y))):
                    continue
                jitter_x = float(rng.uniform(-spacing * 0.16, spacing * 0.16))
                jitter_y = float(rng.uniform(-spacing * 0.16, spacing * 0.16))
                candidate = (float(x + jitter_x), float(y + jitter_y))
                if part.contains(Point(candidate)):
                    sites.append(candidate)
                    if len(sites) >= max_trees:
                        return sites
    if not sites and polygon.area >= 250.0:
        point = polygon.representative_point()
        return [(float(point.x), float(point.y))]
    return sites


def make_procedural_tree_meshes(
    x: float, y: float, osm_id: int, kind: str
) -> list[tuple[tuple[int, int, int, int], trimesh.Trimesh]]:
    """Create a tiny two-part tree; caller batches meshes by colour for mobile rendering."""
    canopy_colors = {
        "forest": (48, 91, 53, 255),
        "orchard": (79, 119, 58, 255),
        "scrub": (91, 117, 72, 255),
        "park": (62, 116, 60, 255),
        "farmland": (85, 126, 61, 255),
    }
    rng = np.random.default_rng(abs(int(osm_id)) % (2**32) + int(abs(x * 17 + y * 31)))
    scale = float(rng.uniform(0.82, 1.22))
    trunk_height = (1.35 if kind in {"scrub", "farmland"} else 1.9) * scale
    trunk = trimesh.creation.cylinder(radius=0.11 * scale, height=trunk_height, sections=5)
    trunk.apply_translation((x, y, trunk_height * 0.5))
    if kind == "orchard":
        canopy = trimesh.creation.icosphere(subdivisions=1, radius=0.82 * scale)
        canopy.apply_translation((x, y, trunk_height + 0.62 * scale))
    else:
        canopy_height = (1.65 if kind == "scrub" else 2.5) * scale
        canopy_radius = (0.75 if kind == "scrub" else 1.35) * scale
        canopy = trimesh.creation.cone(radius=canopy_radius, height=canopy_height, sections=5)
        canopy.apply_translation((x, y, trunk_height + canopy_height * 0.42))
    trunk_color = (103, 77, 53, 255)
    color_mesh(trunk, trunk_color)
    color_mesh(canopy, canopy_colors.get(kind, canopy_colors["park"]))
    return [(trunk_color, trunk), (canopy_colors.get(kind, canopy_colors["park"]), canopy)]


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
_DOOR_COLOR_PALETTE = (
    (91, 60, 39, 255),
    (111, 73, 47, 255),
    (72, 81, 74, 255),
    (86, 65, 55, 255),
    (67, 76, 85, 255),
)


def facade_door_geometry(
    geometry: Any,
    height: float,
    osm_id: int,
    tile_bounds: Polygon,
    mapped_entrance: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Create a metric door on an actual footprint wall; prefer an OSM entrance node."""
    if geometry.is_empty or height < 2.2:
        return None
    parts = list(geometry.geoms) if isinstance(geometry, MultiPolygon) else [geometry]
    preferred_edges = []
    all_edges = []
    for part in parts:
        if not isinstance(part, Polygon) or part.is_empty:
            continue
        coords = list(part.exterior.coords)
        for p1, p2 in zip(coords, coords[1:]):
            dx, dy = float(p2[0] - p1[0]), float(p2[1] - p1[1])
            length = math.hypot(dx, dy)
            if length < 2.8:
                continue
            mid_x, mid_y = (float(p1[0]) + float(p2[0])) * 0.5, (float(p1[1]) + float(p2[1])) * 0.5
            nx, ny = -dy / length, dx / length
            if part.contains(Point(mid_x + nx * 0.25, mid_y + ny * 0.25)):
                nx, ny = -nx, -ny
            angle = math.atan2(dy, dx)
            edge = (length, (float(p1[0]), float(p1[1])), (float(p2[0]), float(p2[1])), nx, ny, angle)
            all_edges.append(edge)
            if tile_bounds.boundary.distance(Point(mid_x, mid_y)) >= 0.7:
                preferred_edges.append(edge)
    candidates = preferred_edges or all_edges
    if not candidates:
        return None

    door_width = 1.05
    door_height = min(2.12, max(1.75, height * 0.68))
    selected_entrance: dict[str, Any] | None = None
    edge_projection_distance = INF
    selected_edge = None
    if isinstance(mapped_entrance, dict):
        entrance_point = Point(float(mapped_entrance["x"]), float(mapped_entrance["y"]))
        # Snap a mapped entrance-node to its nearest footprint wall. It is
        # accepted only when it is genuinely close to that building outline;
        # otherwise retain the conservative inferred-door fallback.
        for edge in candidates:
            length, p1, p2, nx, ny, angle = edge
            edge_line = LineString([p1, p2])
            distance = edge_line.distance(entrance_point)
            if distance < edge_projection_distance:
                edge_projection_distance = distance
                selected_edge = edge
        if selected_edge is not None and edge_projection_distance <= 2.2:
            selected_entrance = mapped_entrance

    if selected_edge is None or selected_entrance is None:
        # No reliable mapped entrance node: create a clearly-labelled procedural cue.
        selected_edge = max(candidates, key=lambda edge: edge[0])
    length, p1, p2, nx, ny, angle = selected_edge

    if selected_entrance is not None:
        entrance_point = Point(float(selected_entrance["x"]), float(selected_entrance["y"]))
        edge_line = LineString([p1, p2])
        projected = edge_line.interpolate(edge_line.project(entrance_point))
        projected_distance = edge_line.project(projected)
        # Keep the entire generated leaf within the wall segment.
        projected_distance = min(max(door_width * 0.60, projected_distance), length - door_width * 0.60)
        fraction = projected_distance / length
        placement_source = (
            "OSM_ENTRANCE_NODE:%s:%s"
            % (str(selected_entrance.get("osm_id", "")), str(selected_entrance.get("entrance", selected_entrance.get("door", ""))))
        )
        entrance_node_osm_id = str(selected_entrance.get("osm_id", ""))
    else:
        distance_from_start = min(max(1.0, length * 0.18), length * 0.28)
        fraction = distance_from_start / length
        placement_source = "PROCEDURAL_LONGEST_EXTERIOR_EDGE_NO_MAPPED_ENTRANCE_NODE"
        entrance_node_osm_id = ""

    cx = p1[0] + (p2[0] - p1[0]) * fraction + nx * 0.048
    cy = p1[1] + (p2[1] - p1[1]) * fraction + ny * 0.048
    params = np.asarray([cx, cy, door_height * 0.5 + 0.025, door_width, door_height, angle], dtype=np.float32)
    vertices = _WINDOW_BOX_TEMPLATE.vertices.astype(np.float32).copy()
    vertices[:, 0] *= params[3]
    vertices[:, 1] *= 0.06
    vertices[:, 2] *= params[4]
    cos_angle, sin_angle = math.cos(float(params[5])), math.sin(float(params[5]))
    rotated_x = vertices[:, 0] * cos_angle - vertices[:, 1] * sin_angle
    rotated_y = vertices[:, 0] * sin_angle + vertices[:, 1] * cos_angle
    vertices[:, 0] = rotated_x + params[0]
    vertices[:, 1] = rotated_y + params[1]
    vertices[:, 2] += params[2]
    return {
        "color": _DOOR_COLOR_PALETTE[abs(int(osm_id)) % len(_DOOR_COLOR_PALETTE)],
        "vertices": vertices,
        "faces": _WINDOW_BOX_TEMPLATE.faces.astype(np.int32).copy(),
        "door_count": 1,
        "door_height_m": round(float(door_height), 2),
        "door_width_m": round(float(door_width), 2),
        "anchor_local_m": [round(float(cx - nx * 0.048), 3), round(float(cy - ny * 0.048), 3)],
        "outward_xy": [round(float(nx), 5), round(float(ny), 5)],
        "placement_source": placement_source,
        "entrance_node_osm_id": entrance_node_osm_id,
    }

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
    # Preserve visible vertical floor rhythm instead of flattening every building to
    # one or two window rows. This is still a facade cue, not proof of surveyed floors;
    # the source floor count and confidence remain in the per-building metadata.
    floor_rows = min(12, max(1, int(round(height / 3.1))))
    max_window_panels = max(8, floor_rows * 2)
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
                    if len(window_centers) >= max_window_panels:
                        break
                if len(window_centers) >= max_window_panels:
                    break
            if len(window_centers) >= max_window_panels:
                break
        if len(window_centers) >= max_window_panels:
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
    facade_photo_catalog = load_facade_photo_catalog()
    interior_reference_catalog = load_interior_reference_catalog()
    facade_photo_matches: list[dict[str, Any]] = []
    interior_reference_photo_matches: list[dict[str, Any]] = []
    facade_photo_panels = 0
    interior_reference_photos_embedded = 0
    ground = trimesh.creation.box(extents=(width, depth, 0.20))
    ground.apply_translation((0.0, 0.0, -0.10))
    color_mesh(ground, (104, 119, 91, 255))
    scene.add_geometry(ground, node_name="terrain_base", geom_name="terrain_base")

    buildings = roads = inferred_heights = named_places = 0
    trees = utility_poles = street_lamps = 0
    water_polygons = waterway_segments = landuse_areas = railway_ways = bridge_ways = facade_windows = 0
    facade_doors = 0
    doors_from_mapped_entrance_nodes = 0
    inferred_doors = 0
    modeled_roofs = 0
    inferred_roofs = 0
    gabled_roofs = 0
    hipped_roofs = 0
    skillion_roofs = 0
    surface_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    building_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    roof_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    facade_vertices_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    facade_faces_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    facade_vertex_counts: dict[tuple[int, int, int, int], int] = {}
    door_vertices_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    door_faces_by_color: dict[tuple[int, int, int, int], list[np.ndarray]] = {}
    door_vertex_counts: dict[tuple[int, int, int, int], int] = {}
    vegetation_meshes_by_color: dict[tuple[int, int, int, int], list[trimesh.Trimesh]] = {}
    vegetation_polygons: list[tuple[Polygon | MultiPolygon, int, str]] = []
    blocked_vegetation_polygons: list[Polygon | MultiPolygon] = []
    interior_seeds: list[dict[str, Any]] = []
    mapped_entrance_nodes: list[dict[str, Any]] = []
    for candidate in elements:
        candidate_tags = candidate.get("tags", {})
        if candidate.get("type") != "node" or ("entrance" not in candidate_tags and "door" not in candidate_tags):
            continue
        if candidate.get("lat") is None or candidate.get("lon") is None:
            continue
        entrance_kind = str(candidate_tags.get("entrance", candidate_tags.get("door", ""))).strip().lower()
        if entrance_kind in {"", "no", "false", "0", "wall"}:
            continue
        entrance_x, entrance_y = local_xy(
            float(candidate["lat"]), float(candidate["lon"]), origin_lat, origin_lon
        )
        mapped_entrance_nodes.append({
            "osm_id": str(candidate.get("id", "")),
            "x": entrance_x,
            "y": entrance_y,
            "entrance": str(candidate_tags.get("entrance", "")),
            "door": str(candidate_tags.get("door", "")),
        })
    used_ids: set[tuple[str, int]] = set()
    for el in elements:
        el_type, osm_id = str(el.get("type", "")), int(el.get("id", 0))
        if (el_type, osm_id) in used_ids:
            continue
        used_ids.add((el_type, osm_id))
        tags = el.get("tags", {})
        points = geometry_xy(el, origin_lat, origin_lon)
        if not points:
            # Multipolygon relations commonly carry mapped forest, farmland, park,
            # wetland and water boundaries. Include them rather than leaving these
            # large real-world surfaces as untextured ground.
            if el_type == "relation" and any(
                key in tags for key in ("natural", "landuse", "leisure", "water")
            ):
                color = surface_color(tags)
                if color is not None:
                    for polygon in relation_area_polygons(el, origin_lat, origin_lon, tile_bounds):
                        for mesh in flat_surface_mesh(polygon, color, f"osm_relation_surface_{osm_id}"):
                            surface_meshes_by_color.setdefault(color, []).append(mesh)
                        if is_water_area(tags):
                            water_polygons += 1
                            blocked_vegetation_polygons.append(polygon)
                        else:
                            landuse_areas += 1
                            green_kind = vegetation_kind(tags)
                            if green_kind:
                                vegetation_polygons.append((polygon, osm_id, green_kind))
                continue
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
            inner_rings = [
                [local_xy(float(point["lat"]), float(point["lon"]), origin_lat, origin_lon)
                 for point in ring if "lat" in point and "lon" in point]
                for ring in el.get("inner_rings", [])
            ]
            polygon = Polygon(points, [ring for ring in inner_rings if len(ring) >= 4])
            if points[0] != points[-1]:
                polygon = Polygon(points)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            polygon = polygon.intersection(tile_bounds)
            if polygon.is_empty or polygon.area < 0.5:
                continue
            blocked_vegetation_polygons.append(polygon)
            height, inferred = building_height(tags, osm_id, polygon.area)
            if inferred:
                inferred_heights += 1
            facade_color = building_color(tags, osm_id)
            for mesh in extruded_polygon(polygon, height, facade_color, f"osm_building_{osm_id}"):
                mesh.apply_translation((0.0, 0.0, 0.02))
                building_meshes_by_color.setdefault(facade_color, []).append(mesh)
            facade_photo = match_facade_photo(tags, facade_photo_catalog)
            if facade_photo is not None:
                photo_metadata: dict[str, Any] = facade_photo["metadata"]
                photo_panel = facade_photo_panel(
                    polygon, height, facade_photo["image"], osm_id, str(photo_metadata.get("id", "licensed_photo"))
                )
                if photo_panel is not None:
                    scene.add_geometry(
                        photo_panel,
                        node_name=f"licensed_facade_photo_{photo_metadata.get('id')}_{osm_id}",
                        geom_name=f"licensed_facade_photo_{photo_metadata.get('id')}_{osm_id}",
                    )
                    facade_photo_panels += 1
                    match_record = {
                        "osm_id": osm_id,
                        "building_name": tags.get("name", tags.get("name:bn", tags.get("official_name", ""))),
                        "image_id": photo_metadata.get("id"),
                        "subject": photo_metadata.get("subject"),
                        "source_page": photo_metadata.get("source_page"),
                        "author": photo_metadata.get("author"),
                        "license": photo_metadata.get("license"),
                        "license_url": photo_metadata.get("license_url"),
                        "attribution": photo_metadata.get("attribution"),
                        "status": "EMBEDDED_TEXTURE_PANEL_REQUIRES_VISUAL_REVIEW",
                    }
                    facade_photo_matches.append(match_record)
            # Keep a cap for every building, adding pitched silhouettes when source
            # tags exist or a small low-rise house needs a clearly labelled inference.
            roof_shape_model, roof_shape_source = roof_shape_for_building(tags, polygon.area, height)
            mapped_roof_color = procedural_roof_color(tags, osm_id, roof_shape_source)
            for roof_mesh in extruded_polygon(polygon, 0.055, mapped_roof_color, f"osm_roof_{osm_id}"):
                roof_mesh.apply_translation((0.0, 0.0, height + 0.025))
                roof_meshes_by_color.setdefault(mapped_roof_color, []).append(roof_mesh)
            if roof_shape_source.startswith("INFERRED_"):
                inferred_roofs += 1
            pitched_roof = procedural_roof_mesh(polygon, height, roof_shape_model, osm_id)
            if pitched_roof is not None:
                color_mesh(pitched_roof, mapped_roof_color)
                roof_meshes_by_color.setdefault(mapped_roof_color, []).append(pitched_roof)
                modeled_roofs += 1
                if roof_shape_model == "gabled":
                    gabled_roofs += 1
                elif roof_shape_model == "hipped":
                    hipped_roofs += 1
                elif roof_shape_model == "skillion":
                    skillion_roofs += 1
            nearest_mapped_entrance: dict[str, Any] | None = None
            nearest_entrance_distance = 2.2
            for entrance_candidate in mapped_entrance_nodes:
                entrance_point = Point(float(entrance_candidate["x"]), float(entrance_candidate["y"]))
                boundary_distance = polygon.boundary.distance(entrance_point)
                if boundary_distance <= nearest_entrance_distance:
                    nearest_entrance_distance = boundary_distance
                    nearest_mapped_entrance = entrance_candidate
            door_info = facade_door_geometry(
                polygon, height, osm_id, tile_bounds, nearest_mapped_entrance
            )
            door_anchor_local_m: list[float] = []
            door_outward_xy: list[float] = []
            door_placement_source = "NO_PROCEDURAL_DOOR_ANCHOR"
            door_entrance_node_osm_id = ""
            if door_info is not None:
                door_color = door_info["color"]
                door_vertices = door_info["vertices"]
                door_faces = door_info["faces"]
                vertex_offset = door_vertex_counts.get(door_color, 0)
                door_vertices_by_color.setdefault(door_color, []).append(door_vertices)
                door_faces_by_color.setdefault(door_color, []).append(door_faces + vertex_offset)
                door_vertex_counts[door_color] = vertex_offset + len(door_vertices)
                facade_doors += int(door_info["door_count"])
                door_anchor_local_m = list(door_info["anchor_local_m"])
                door_outward_xy = list(door_info["outward_xy"])
                door_placement_source = str(door_info["placement_source"])
                door_entrance_node_osm_id = str(door_info.get("entrance_node_osm_id", ""))
                if door_entrance_node_osm_id:
                    doors_from_mapped_entrance_nodes += 1
                else:
                    inferred_doors += 1
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
            interior_photo_reference: dict[str, Any] | None = None
            interior_photo = match_named_image(tags, interior_reference_catalog)
            if interior_photo is not None:
                photo_metadata: dict[str, Any] = interior_photo["metadata"]
                source_photo = Path(str(interior_photo.get("path", "")))
                photo_filename = str(photo_metadata.get("file_name", "")).strip()
                if source_photo.is_file() and photo_filename:
                    relative_photo_path = "landmark_reference_photos/" + photo_filename
                    photo_destination = output_dir / relative_photo_path
                    photo_destination.parent.mkdir(parents=True, exist_ok=True)
                    if not photo_destination.is_file():
                        photo_destination.write_bytes(source_photo.read_bytes())
                    image_bytes = photo_destination.read_bytes()
                    interior_photo_reference = {
                        "image_id": str(photo_metadata.get("id", "")),
                        "asset_relative_path": relative_photo_path,
                        "source_page": str(photo_metadata.get("source_page", "")),
                        "author": str(photo_metadata.get("author", "")),
                        "license": str(photo_metadata.get("license", "")),
                        "license_url": str(photo_metadata.get("license_url", "")),
                        "attribution": str(photo_metadata.get("attribution", "")),
                        "sha256": hashlib.sha256(image_bytes).hexdigest(),
                        "use": "INTERIOR_REFERENCE_ONLY",
                        "visual_identity_verified": True,
                    }
                    interior_reference_photo_matches.append({
                        "osm_id": osm_id,
                        "building_name": tags.get("name", tags.get("name:bn", tags.get("official_name", ""))),
                        "image_id": interior_photo_reference["image_id"],
                        "tile_id": output_dir.name,
                        **interior_photo_reference,
                    })
                    interior_reference_photos_embedded += 1
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
                "door_anchor_local_m": door_anchor_local_m,
                "door_outward_xy": door_outward_xy,
                "door_placement_source": door_placement_source,
                "door_entrance_node_osm_id": door_entrance_node_osm_id,
                "roof_shape_model": roof_shape_model,
                "roof_shape_source": roof_shape_source,
                "interior_status": "FICTIONAL_BUILDING_SPECIFIC_INTERIOR_GENERATED_AT_RUNTIME",
                "npc_seed": "Generate fictional residents/workers from this building's own mapped name, category, address and exterior tags; never imply actual occupants.",
                "rooms_seed": ["entrance", "public_or_living_area", "counter_or_reception", "back_room"],
                "interior_generation_key": f"osm:{el_type}/{osm_id}",
                "interior_reference_photo": interior_photo_reference,
            })
            if has_specific_place_tags:
                named_places += 1
            continue
        if el_type == "way" and len(points) >= 4 and points[0] == points[-1]:
            color = surface_color(tags)
            if color is not None:
                try:
                    inner_rings = [
                        [local_xy(float(point["lat"]), float(point["lon"]), origin_lat, origin_lon)
                         for point in ring if "lat" in point and "lon" in point]
                        for ring in el.get("inner_rings", [])
                    ]
                    polygon = Polygon(points, [ring for ring in inner_rings if len(ring) >= 4])
                    if not polygon.is_valid:
                        polygon = polygon.buffer(0)
                    polygon = polygon.intersection(tile_bounds)
                    surface_meshes = flat_surface_mesh(polygon, color, f"osm_surface_{osm_id}")
                    for mesh in surface_meshes:
                        surface_meshes_by_color.setdefault(color, []).append(mesh)
                    if surface_meshes:
                        if is_water_area(tags):
                            water_polygons += 1
                            blocked_vegetation_polygons.append(polygon)
                        else:
                            landuse_areas += 1
                            green_kind = vegetation_kind(tags)
                            if green_kind:
                                vegetation_polygons.append((polygon, osm_id, green_kind))
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
                if not water_polygon.is_empty:
                    blocked_vegetation_polygons.append(water_polygon)
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
                if not rail_bed.is_empty:
                    blocked_vegetation_polygons.append(rail_bed)
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
                if not road_polygon.is_empty:
                    blocked_vegetation_polygons.append(road_polygon)
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

    # OSM rarely maps individual trees consistently across rural Bangladesh.
    # Fill only mapped forest/orchard/park/scrub/farm polygons with bounded,
    # deterministic low-poly vegetation. This adds landscape texture without
    # inventing tree positions outside mapped green land-use areas.
    procedural_trees = 0
    per_tile_tree_budget = 700
    blocked_union = unary_union(blocked_vegetation_polygons) if blocked_vegetation_polygons else GeometryCollection()
    for polygon, osm_id, kind in vegetation_polygons:
        if procedural_trees >= per_tile_tree_budget:
            break
        # Keep procedural props out of building footprints, mapped water, rail beds,
        # and road corridors even when land-use polygons overlap those features.
        safe_polygon = polygon.difference(blocked_union) if not blocked_union.is_empty else polygon
        if safe_polygon.is_empty:
            continue
        if not safe_polygon.is_valid:
            safe_polygon = safe_polygon.buffer(0)
        if safe_polygon.is_empty:
            continue
        kind_budget = {"forest": 90, "orchard": 130, "scrub": 42, "park": 48, "farmland": 22}.get(kind, 30)
        sites = procedural_tree_sites(safe_polygon, osm_id, kind, min(kind_budget, per_tile_tree_budget - procedural_trees))
        for tree_index, (tree_x, tree_y) in enumerate(sites):
            for tree_color, tree_mesh in make_procedural_tree_meshes(
                tree_x, tree_y, osm_id * 1009 + tree_index, kind
            ):
                vegetation_meshes_by_color.setdefault(tree_color, []).append(tree_mesh)
            procedural_trees += 1
            if procedural_trees >= per_tile_tree_budget:
                break

    for color, meshes in vegetation_meshes_by_color.items():
        if not meshes:
            continue
        combined = color_mesh(trimesh.util.concatenate(meshes), color)
        color_name = "".join(f"{channel:02x}" for channel in color)
        scene.add_geometry(combined, node_name=f"procedural_vegetation_{color_name}", geom_name=f"procedural_vegetation_{color_name}")

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

    for color, vertex_chunks in door_vertices_by_color.items():
        if not vertex_chunks:
            continue
        vertices = np.concatenate(vertex_chunks, axis=0)
        faces = np.concatenate(door_faces_by_color[color], axis=0)
        combined = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        color_mesh(combined, color)
        color_name = "".join(f"{channel:02x}" for channel in color[:3])
        scene.add_geometry(combined, node_name=f"facade_doors_{color_name}", geom_name=f"facade_doors_{color_name}")

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
        # CI pins this value before each bake so the batch assembler can prove
        # every tile in a sequence came from the same pipeline revision.
        "pipeline_commit_sha": os.environ.get("WSB_PIPELINE_COMMIT_SHA", "").strip(),
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
                           "interior_anchors": len(interior_seeds), "licensed_facade_photo_panels": facade_photo_panels, "interior_reference_photos": interior_reference_photos_embedded, "mapped_trees": trees,
                           "mapped_utility_poles": utility_poles, "mapped_street_lamps": street_lamps, "facade_window_panels": facade_windows, "facade_door_panels": facade_doors, "doors_from_mapped_entrance_nodes": doors_from_mapped_entrance_nodes, "inferred_doors": inferred_doors, "modeled_roofs": modeled_roofs, "inferred_roof_shapes": inferred_roofs, "gabled_roofs": gabled_roofs, "hipped_roofs": hipped_roofs, "skillion_roofs": skillion_roofs, "building_mesh_batches": len(building_meshes_by_color), "roof_mesh_batches": len(roof_meshes_by_color), "procedural_vegetation_trees": procedural_trees, "vegetation_mesh_batches": len(vegetation_meshes_by_color),
                            "water_polygons": water_polygons, "waterway_segments": waterway_segments,
                            "landuse_areas": landuse_areas, "railway_ways": railway_ways, "bridge_ways": bridge_ways},
        "licensed_facade_photo_matches": facade_photo_matches,
        "interior_reference_photo_matches": interior_reference_photo_matches,
        "interior_reference_photo_note": "Explicitly licensed interior photos are copied as separate runtime assets and shown only inside the exact-name mapped building's fictional generated interior. They are never applied to an exterior facade.",
        "facade_photo_note": "Only exact OSM name aliases from the rights-reviewed catalog receive a photo panel. These are licensed reference-photo panels, not full photogrammetric facade reconstruction; visual identity, orientation, and building match must be reviewed.",
        "height_note": "OSM height/building:levels tags are used when present; otherwise footprint-area/building-category estimates with deterministic floor-height variation are flagged as inferred, not surveyed facts.",
        "hydrography_note": "Mapped OSM water polygons are kept to their source outlines. River/canal centerlines without mapped widths use type-based approximate widths and are not survey-grade water boundaries.",
         "visual_fidelity_note": "Real OSM road alignments, building footprints, mapped water and land-use surfaces, and tagged bridges are included. Mapped forest, orchard, park, scrub and farm polygons receive bounded deterministic low-poly tree props where individual OSM tree nodes are sparse; vegetation remains procedural rather than a surveyed inventory. Sufficiently large buildings receive lightweight procedural low-poly window panels; building, roof and vegetation meshes are batched by material colour to reduce mobile draw calls. Explicit facade/roof colour tags are used where available. Bangla/English names and exterior image references are preserved per building. This is not photorealistic street imagery; that requires separately licensed source data.",
        "interiors_and_people": "AI_Interior_Seeds.json includes anchors for every mapped building footprint plus named/tagged places; the game generates fictional interiors and residents at runtime, not actual private interiors or real people.",
        "engine_import": "Import Dhaka_Explorable_Map.glb as a Godot MeshInstance3D/scene; retain GeoJSON and manifest for labels, navigation and source attribution.",
    }
    (output_dir / "map_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    attribution_text = (
        OSM_COPYRIGHT + "\nData license: Open Database License (ODbL) 1.0.\n"
        "Source data is modified into a local 3D representation. See https://www.openstreetmap.org/copyright\n"
    )
    seen_photo_attributions: set[str] = set()
    for match in interior_reference_photo_matches:
        attribution = str(match.get("attribution", "")).strip()
        license_name = str(match.get("license", "")).strip()
        license_url = str(match.get("license_url", "")).strip()
        entry = f"{attribution}\nLicense: {license_name} — {license_url}\nUse: interior reference only; not an exterior facade texture."
        if attribution and entry not in seen_photo_attributions:
            seen_photo_attributions.add(entry)
            attribution_text += "\n" + entry + "\n"
    for match in facade_photo_matches:
        attribution = str(match.get("attribution", "")).strip()
        license_name = str(match.get("license", "")).strip()
        license_url = str(match.get("license_url", "")).strip()
        entry = f"{attribution}\nLicense: {license_name} — {license_url}"
        if attribution and entry not in seen_photo_attributions:
            seen_photo_attributions.add(entry)
            attribution_text += "\n" + entry + "\n"
    (output_dir / "ATTRIBUTION.txt").write_text(attribution_text, encoding="utf-8")
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
