#!/usr/bin/env python3
"""Build a boundary-clipped, tiled 3D map for the full Dhaka Division.

Inputs are the Bangladesh OSM PBF and the open geoBoundaries ADM1 GeoJSON.
The output is a set of streamable GLB tiles plus source GeoJSON, attribution,
and a manifest that records which geometry is source-derived or inferred.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any

import osmium
import trimesh
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box, shape
from shapely.ops import nearest_points, transform

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.map_pipeline.build_dhaka_map import build_map, local_xy, extruded_polygon, color_mesh
from tools.map_pipeline.tile_grid import tile_bounds

PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
BOUNDARY_API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM1/"
DISTRICT_BOUNDARY_API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/"
INTERESTING_KEYS = {
    "building", "building:part", "entrance", "door", "highway", "shop", "amenity", "tourism", "historic",
    "leisure", "office", "healthcare", "public_transport", "landuse",
    "natural", "waterway", "railway", "man_made", "power",
}

RENDERED_FEATURE_KEYS = {
    "building_footprints", "road_ways", "water_polygons", "waterway_segments",
    "landuse_areas", "railway_ways", "mapped_trees", "mapped_utility_poles",
    "mapped_street_lamps", "named_or_tagged_interaction_seeds",
}


def tile_status_from_counts(counts: dict[str, Any]) -> str:
    """Distinguish mapped geometry from a ground-only fallback tile."""
    if any(int(counts.get(key, 0) or 0) > 0 for key in RENDERED_FEATURE_KEYS):
        return "BAKED_FROM_OSM"
    return "GROUND_ONLY_NO_RENDERABLE_FEATURES"
OSM_ATTRIBUTION = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"
def boundary_attribution_for_stage(stage: str) -> str:
    """Return attribution naming the actual administrative boundary used."""
    if stage == "shariatpur_review":
        boundary_type = "ADM2"
        boundary_name = "Shariatpur District"
    elif stage == "full_division":
        boundary_type = "ADM1"
        boundary_name = "Dhaka Division"
    else:
        raise ValueError(f"Unsupported map build stage: {stage}")
    return (
        f"Clipping boundary: {boundary_name}; source: geoBoundaries "
        f"(https://www.geoboundaries.org), gbOpen BGD {boundary_type}. "
        "See manifest for the returned dataset license."
    )


def validate_shariatpur_release_approval(path: pathlib.Path | None = None) -> dict[str, Any]:
    """Require documented Shariatpur release evidence before building other districts.

    A successful tile export is not enough: this project requires every Shariatpur
    tile, building-floor record, facade review, navigation test, and Android-device
    check to pass before the map footprint may expand.
    """
    approval_path = path or (ROOT / "tools/map_pipeline/shariatpur_release_approval.json")
    if not approval_path.is_file():
        raise RuntimeError(
            "Shariatpur release gate BLOCKED: approval evidence file is missing. "
            "Finish and independently review Shariatpur before selecting full_division."
        )
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Shariatpur release gate BLOCKED: invalid approval JSON: {exc}") from exc
    required_checks = (
        "all_tiles_have_renderable_osm_features",
        "all_building_floor_counts_independently_verified",
        "licensed_facade_imagery_visual_review_complete",
        "named_place_search_and_turn_navigation_qa_passed",
        "physical_android_integration_and_performance_passed",
    )
    checks = approval.get("checks", {}) if isinstance(approval, dict) else {}
    missing = [name for name in required_checks if checks.get(name) is not True]
    if approval.get("status") != "APPROVED" or missing:
        details = ", ".join(missing) if missing else "status is not APPROVED"
        raise RuntimeError(
            "Shariatpur release gate BLOCKED; no later tiles will be built. "
            f"Outstanding acceptance checks: {details}."
        )
    reviewed_at = str(approval.get("reviewed_at", "")).strip()
    reviewer = str(approval.get("reviewer", "")).strip()
    evidence = str(approval.get("review_evidence_url", "")).strip()
    if not reviewed_at or not reviewer or not evidence.startswith("https://"):
        raise RuntimeError(
            "Shariatpur release gate BLOCKED: approval needs reviewed_at, reviewer, "
            "and an HTTPS review_evidence_url."
        )
    return approval


def download(url: str, path: pathlib.Path, min_bytes: int = 1000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= min_bytes:
        print(f"Using cached {path} ({path.stat().st_size:,} bytes)", flush=True)
        return
    temp = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Project-A-Square-MapPipeline/1.0"})
    with urllib.request.urlopen(request, timeout=240) as response, temp.open("wb") as out:
        shutil.copyfileobj(response, out)
    if temp.stat().st_size < min_bytes:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded file is unexpectedly small: {url}")
    temp.replace(path)


def load_dhaka_boundary(path: pathlib.Path) -> tuple[Any, dict[str, Any]]:
    request = urllib.request.Request(BOUNDARY_API, headers={"User-Agent": "Project-A-Square-MapPipeline/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        metadata = json.loads(response.read().decode("utf-8"))
    if isinstance(metadata, list):
        record = next((r for r in metadata if r.get("boundaryISO") == "BGD" and r.get("boundaryType") == "ADM1"), None)
    else:
        record = metadata
    # geoBoundaries returns the Bangladesh ADM1 layer metadata; the downloaded
    # GeoJSON contains all eight division polygons, including Dhaka.
    if not record or not record.get("gjDownloadURL"):
        raise RuntimeError("geoBoundaries API did not return the Bangladesh ADM1 GeoJSON URL.")
    if not path.exists():
        download(str(record["gjDownloadURL"]), path, 1000)
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    feature = next((f for f in features if any("dhaka" == str(v).strip().lower() for v in f.get("properties", {}).values())), None)
    if feature is None:
        feature = next((f for f in features if "dhaka" in json.dumps(f.get("properties", {})).lower()), None)
    if feature is None:
        raise RuntimeError("Could not identify the Dhaka Division feature in the Bangladesh ADM1 GeoJSON.")
    geom = shape(feature["geometry"])
    if geom.is_empty or not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise RuntimeError("Dhaka Division boundary is not a valid polygon.")
    details = {
        "feature_properties": feature.get("properties", {}),
        "boundary_source": record.get("boundarySource", "geoBoundaries"),
        "boundary_year_represented": record.get("boundaryYearRepresented", "unspecified"),
        "boundary_license": record.get("boundaryLicense", "See geoBoundaries metadata"),
        "boundary_license_source": record.get("licenseSource", ""),
        "boundary_id": record.get("boundaryID", ""),
    }
    return geom, details


def has_feature(tags: Any) -> bool:
    return any(key in tags for key in INTERESTING_KEYS)


def load_shariatpur_boundary(path: pathlib.Path) -> tuple[Any, dict[str, Any]]:
    """Load the actual Shariatpur District polygon from geoBoundaries ADM2."""
    request = urllib.request.Request(
        DISTRICT_BOUNDARY_API,
        headers={"User-Agent": "Project-A-Square-MapPipeline/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        metadata = json.loads(response.read().decode("utf-8"))
    if isinstance(metadata, list):
        record = next((r for r in metadata if r.get("boundaryISO") == "BGD" and r.get("boundaryType") == "ADM2"), None)
    else:
        record = metadata
    if not record or not record.get("gjDownloadURL"):
        raise RuntimeError("geoBoundaries API did not return the Bangladesh ADM2 district GeoJSON URL.")
    if not path.exists():
        download(str(record["gjDownloadURL"]), path, 1000)
    payload = json.loads(path.read_text(encoding="utf-8"))
    features = payload.get("features", [])
    feature = next(
        (f for f in features if any(
            str(v).strip().lower() in {"shariatpur", "shariatpur district"}
            for v in f.get("properties", {}).values()
        )),
        None,
    )
    if feature is None:
        feature = next(
            (f for f in features if "shariatpur" in json.dumps(f.get("properties", {})).lower()),
            None,
        )
    if feature is None:
        raise RuntimeError("Shariatpur District was not found in the Bangladesh ADM2 boundary dataset.")
    geom = shape(feature["geometry"])
    if geom.is_empty or not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"}:
        raise RuntimeError("Shariatpur District boundary is not a valid polygon.")
    details = {
        "feature_properties": feature.get("properties", {}),
        "boundary_source": record.get("boundarySource", "geoBoundaries"),
        "boundary_year_represented": record.get("boundaryYearRepresented", "unspecified"),
        "boundary_license": record.get("boundaryLicense", "See geoBoundaries metadata"),
        "boundary_license_source": record.get("licenseSource", ""),
        "boundary_id": record.get("boundaryID", ""),
    }
    return geom, details


SHARIATPUR_PRIORITY_LAT_LON = (23.2167, 90.3500)


def order_tiles_shariatpur_first(
    tiles: list[tuple[float, float, float, float]],
    shariatpur_boundary: Any,
    priority_lat_lon: tuple[float, float] = SHARIATPUR_PRIORITY_LAT_LON,
) -> list[tuple[float, float, float, float]]:
    """Order Shariatpur District-intersecting tiles first, then the full division."""
    priority_lat, priority_lon = priority_lat_lon

    def distance(tile: tuple[float, float, float, float]) -> float:
        south, west, north, east = tile
        return (
            ((south + north) * 0.5 - priority_lat) ** 2
            + (((west + east) * 0.5 - priority_lon)
               * math.cos(math.radians(priority_lat))) ** 2
        )

    district_tiles = [
        tile for tile in tiles
        if shariatpur_boundary.intersects(box(tile[1], tile[0], tile[3], tile[2]))
    ]
    other_tiles = [tile for tile in tiles if tile not in district_tiles]
    return sorted(district_tiles, key=distance) + sorted(other_tiles, key=distance)


def select_tile_batch(
    ordered_tiles: list[tuple[float, float, float, float]],
    offset: int,
    limit: int,
) -> list[tuple[float, float, float, float]]:
    """Select a bounded, deterministic slice without dropping later division tiles."""
    if offset < 0 or limit < 1:
        raise ValueError("offset must be >= 0 and limit must be >= 1")
    return ordered_tiles[offset:offset + limit]


def build_boundary_for_stage(stage: str, division_boundary: Any, district_boundary: Any) -> Any:
    if stage == "shariatpur_review":
        return district_boundary
    if stage == "full_division":
        return division_boundary
    raise ValueError(f"Unsupported map build stage: {stage}")


def pipeline_commit_sha() -> str:
    """Return the pinned map-pipeline revision recorded in every batch manifest."""
    return os.environ.get("WSB_PIPELINE_COMMIT_SHA", os.environ.get("GITHUB_SHA", "local")).strip()


def stage_gate_reached(offset: int, shariatpur_tile_count: int, stage: str) -> bool:
    """True when a Shariatpur-only sequence has reached the review boundary."""
    if offset < 0 or shariatpur_tile_count < 0:
        raise ValueError("offset and district tile count must be >= 0")
    if stage not in {"shariatpur_review", "full_division"}:
        raise ValueError(f"Unsupported map build stage: {stage}")
    return stage == "shariatpur_review" and offset >= shariatpur_tile_count


def effective_batch_limit(offset: int, requested_limit: int, shariatpur_tile_count: int, stage: str) -> int:
    """Prevent the default Shariatpur review stage's final batch spilling into other districts."""
    if offset < 0 or requested_limit < 1 or shariatpur_tile_count < 0:
        raise ValueError("offset and district tile count must be >= 0; requested limit must be >= 1")
    if stage not in {"shariatpur_review", "full_division"}:
        raise ValueError(f"Unsupported map build stage: {stage}")
    if stage == "shariatpur_review" and offset < shariatpur_tile_count:
        return min(requested_limit, shariatpur_tile_count - offset)
    return requested_limit


class RegionHandler(osmium.SimpleHandler):
    def __init__(self, bounds: tuple[float, float, float, float]):
        super().__init__()
        self.south, self.west, self.north, self.east = bounds
        self.elements: list[dict[str, Any]] = []
        self.bad_locations = 0

    def node(self, n: Any) -> None:
        if not has_feature(n.tags) or not n.location.valid():
            return
        lat, lon = float(n.location.lat), float(n.location.lon)
        if self.west <= lon <= self.east and self.south <= lat <= self.north:
            self.elements.append({"type": "node", "id": int(n.id), "lat": lat, "lon": lon,
                                  "tags": {tag.k: tag.v for tag in n.tags}})

    def way(self, w: Any) -> None:
        if not has_feature(w.tags):
            return
        coords = []
        try:
            for node in w.nodes:
                if node.location.valid():
                    coords.append({"lat": float(node.location.lat), "lon": float(node.location.lon)})
        except Exception:
            self.bad_locations += 1
            return
        if len(coords) < 2:
            return
        min_lon, max_lon = min(p["lon"] for p in coords), max(p["lon"] for p in coords)
        min_lat, max_lat = min(p["lat"] for p in coords), max(p["lat"] for p in coords)
        if min_lon <= self.east and max_lon >= self.west and min_lat <= self.north and max_lat >= self.south:
            self.elements.append({"type": "way", "id": int(w.id), "tags": {tag.k: tag.v for tag in w.tags},
                                  "geometry": coords, "_bbox": [min_lon, min_lat, max_lon, max_lat]})


def _source_geometry(element: dict[str, Any]):
    if element["type"] == "node":
        return Point(float(element["lon"]), float(element["lat"]))
    coords = [(float(p["lon"]), float(p["lat"])) for p in element.get("geometry", [])]
    tags = element.get("tags", {})
    is_area = any(key in tags for key in ("building", "landuse", "natural", "leisure", "water", "amenity", "shop"))
    if is_area and len(coords) >= 4 and coords[0] == coords[-1]:
        holes = [
            [(float(p["lon"]), float(p["lat"])) for p in ring]
            for ring in element.get("inner_rings", [])
            if len(ring) >= 4
        ]
        geom = Polygon(coords, holes)
        return geom if geom.is_valid else geom.buffer(0)
    if len(coords) >= 2:
        return LineString(coords)
    return Point(coords[0]) if coords else GeometryCollection()


def _parts(geom: Any, expected: str) -> list[Any]:
    if geom.is_empty:
        return []
    if expected == "polygon":
        if isinstance(geom, Polygon):
            return [geom]
        if isinstance(geom, (MultiPolygon, GeometryCollection)):
            return [g for g in geom.geoms if isinstance(g, Polygon) and not g.is_empty]
    else:
        if isinstance(geom, LineString):
            return [geom]
        if isinstance(geom, (MultiLineString, GeometryCollection)):
            return [g for g in geom.geoms if isinstance(g, LineString) and not g.is_empty]
    return []


def _to_element(original: dict[str, Any], geom: Any, part_no: int) -> dict[str, Any]:
    item = {"type": original["type"], "id": int(original["id"]) * 1000 + part_no,
            "tags": dict(original.get("tags", {}))}
    item["tags"]["source_osm_id"] = str(original["id"])
    if original["type"] == "node":
        item["lat"], item["lon"] = float(geom.y), float(geom.x)
    else:
        coords = list(geom.exterior.coords) if isinstance(geom, Polygon) else list(geom.coords)
        if isinstance(geom, Polygon) and coords[0] != coords[-1]:
            coords.append(coords[0])
        item["geometry"] = [{"lat": float(lat), "lon": float(lon)} for lon, lat in coords]
        if isinstance(geom, Polygon) and geom.interiors:
            item["inner_rings"] = [
                [{"lat": float(lat), "lon": float(lon)} for lon, lat in ring.coords]
                for ring in geom.interiors
            ]
    return item


def _clip_elements(elements: list[dict[str, Any]], clip_shape: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags", {})
        geom = _source_geometry(element)
        if geom.is_empty:
            continue
        clipped = geom.intersection(clip_shape)
        if clipped.is_empty:
            continue
        if element["type"] == "node":
            if clip_shape.covers(geom):
                result.append(element)
            continue
        expected = "polygon" if isinstance(geom, (Polygon, MultiPolygon)) else "line"
        for i, part in enumerate(_parts(clipped, expected), start=1):
            if expected == "polygon" and part.area < 1e-10:
                continue
            if expected == "line" and part.length < 1e-7:
                continue
            result.append(_to_element(element, part, i))
    return result



MANASHA_TARGET_LAT_LON = (23.2004, 90.3484)
MANASHA_PHOTO_MATCH_RADIUS_M = 45.0
MANASHA_APPROXIMATE_FOOTPRINT_SOURCE = "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED"


def add_curated_manasha_footprint(elements: list[dict[str, Any]], clip_shape: Any) -> list[dict[str, Any]]:
    """Add a disclosed landmark placeholder only when its compatible mapped footprint is missing.

    The published coordinate locates the landmark but does not survey its wall outline.
    This fallback is deliberately marked approximate and pending local review.
    """
    target_lat, target_lon = MANASHA_TARGET_LAT_LON
    target = Point(target_lon, target_lat)
    if clip_shape is None or clip_shape.is_empty or not clip_shape.covers(target):
        return elements

    aliases = {
        "manasha temple, shariatpur", "manasha temple", "manasa temple, shariatpur",
        "মনসা মন্দির, শরীয়তপুর", "মনসা মন্দির", "ধানুকার মানসা মন্দির",
        "dhanuka manasha bari", "dhanuka manasa bari", "dhanuka mansa bari",
        "dhanuka manasa temple", "dhanuka manasha temple", "ধানুকা মনসাবাড়ি",
        "ধানুকা মনসাবাড়ি", "ধানুকা মনসা বাড়ি", "ধানুকা মনসা বাড়ি",
        "ধানুকা মনসা মন্দির", "ধানুকা মনসামন্দির", "মনসাবাড়ি", "মনসাবাড়ি",
        "মনসা বাড়ি", "মনসা বাড়ি", "ধানুকা মনসা বাড়ি, শরীয়তপুর", "ধানুকার মনসা মন্দির",
    }
    compatible_groups = (
        {"amenity": "place_of_worship"}, {"building": "temple"}, {"historic": "temple"},
        {"historic": "monument", "religion": "hindu"}, {"religion": "hindu"},
    )

    def distance_to_target_metres(geometry: Any) -> float:
        nearest = nearest_points(geometry, target)[0]
        east = (float(nearest.x) - target_lon) * 111320.0 * math.cos(math.radians(target_lat))
        north = (float(nearest.y) - target_lat) * 110574.0
        return math.hypot(east, north)

    for element in elements:
        if element.get("type") not in {"way", "relation"}:
            continue
        tags = element.get("tags", {})
        if not tags:
            continue
        normalized_names = {
            " ".join(str(tags.get(key, "")).split()).casefold()
            for key in ("name", "name:bn", "name:en", "official_name")
        }
        is_named_target = bool(normalized_names.intersection(aliases))
        is_compatible = any(
            all(str(tags.get(key, "")).strip().casefold() == expected for key, expected in group.items())
            for group in compatible_groups
        )
        if not (is_named_target or is_compatible):
            continue
        try:
            geometry = _source_geometry(element)
        except (KeyError, TypeError, ValueError):
            continue
        if geometry.is_empty or not isinstance(geometry, (Polygon, MultiPolygon)):
            continue
        if distance_to_target_metres(geometry) <= MANASHA_PHOTO_MATCH_RADIUS_M:
            return elements

    # Eight by six metres is a temporary authored placeholder, not a surveyed outline.
    half_width_m, half_depth_m = 4.0, 3.0
    half_lon = half_width_m / (111320.0 * math.cos(math.radians(target_lat)))
    half_lat = half_depth_m / 110574.0
    footprint = box(
        target_lon - half_lon, target_lat - half_lat,
        target_lon + half_lon, target_lat + half_lat,
    ).intersection(clip_shape)
    if not isinstance(footprint, Polygon) or footprint.is_empty or footprint.area < 1e-10:
        return elements
    ring = [{"lat": float(lat), "lon": float(lon)} for lon, lat in footprint.exterior.coords]
    feature = {
        "type": "way",
        "id": -62000085,
        "tags": {
            "building": "temple",
            "building:levels": "1",
            "building:levels:estimate": "1",
            "building:levels:source": "CURATED_APPROXIMATE_NOT_SURVEYED",
            "height": "4.5 m",
            "height:source": "CURATED_APPROXIMATE_NOT_SURVEYED",
            "historic": "temple",
            "amenity": "place_of_worship",
            "religion": "hindu",
            "name": "Manasha Temple, Shariatpur",
            "name:en": "Manasha Temple, Shariatpur",
            "name:bn": "মনসা মন্দির, শরীয়তপুর",
            "official_name": "Dhanuka Manasha Bari",
            "source:geometry": MANASHA_APPROXIMATE_FOOTPRINT_SOURCE,
            "source:geometry:url": "https://commons.wikimedia.org/wiki/Category:Manasha_Temple,_Shariatpur",
            "source:location": "Published place coordinate; approximate footprint dimensions have not been surveyed.",
            "source:location:url": "https://ghurifiri.bd/places/dhanuka-manasha-bari-shariatpur",
        },
        "geometry": ring,
    }
    return [*elements, feature]


def _replace_ground_with_boundary(path: pathlib.Path, boundary_tile: Any, bbox: tuple[float, float, float, float]) -> None:
    """Clip the tile ground itself to the division polygon, not just its features."""
    if boundary_tile.is_empty:
        return
    south, west, north, east = bbox
    origin_lat, origin_lon = (south + north) / 2.0, (west + east) / 2.0
    def project_ring(coords):
        return [(local_xy(lat, lon, origin_lat, origin_lon)[0],
                 local_xy(lat, lon, origin_lat, origin_lon)[1]) for lon, lat in coords]
    if isinstance(boundary_tile, Polygon):
        polys = [boundary_tile]
    elif isinstance(boundary_tile, MultiPolygon):
        polys = list(boundary_tile.geoms)
    else:
        polys = [g for g in getattr(boundary_tile, "geoms", []) if isinstance(g, Polygon)]
    projected = []
    for poly in polys:
        outer = project_ring(poly.exterior.coords)
        holes = [project_ring(ring.coords) for ring in poly.interiors]
        projected.append(Polygon(outer, holes))
    if not projected:
        return
    scene = trimesh.load(path, force="scene")
    try:
        scene.delete_geometry("terrain_base")
    except Exception:
        pass
    ground_shapes = projected
    for i, poly in enumerate(ground_shapes):
        if poly.is_empty or poly.area < 0.5:
            continue
        for j, mesh in enumerate(extruded_polygon(poly, 0.2, (104, 119, 91, 255), f"division_ground_{i}")):
            mesh.apply_translation((0.0, 0.0, -0.1))
            axes = [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0],
                    [0.0, -1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
            mesh.apply_transform(axes)
            scene.add_geometry(mesh, node_name=f"terrain_base_division_ground_{i}_{j}", geom_name=f"terrain_base_division_ground_{i}_{j}")
    path.write_bytes(scene.export(file_type="glb"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=pathlib.Path, default=pathlib.Path("build/osm/bangladesh-latest.osm.pbf"))
    parser.add_argument("--boundary", type=pathlib.Path, default=pathlib.Path("build/boundaries/dhaka-division.geojson"))
    parser.add_argument("--district-boundary", type=pathlib.Path, default=pathlib.Path("build/boundaries/bangladesh-districts.geojson"))
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/dhaka-division"))
    parser.add_argument("--tile-degrees", type=float, default=0.05)
    parser.add_argument("--tile-offset", type=int, default=0,
                        help="Zero-based offset in the Shariatpur-first, full-division tile order")
    parser.add_argument("--max-tiles", type=int, default=2,
                        help="Maximum tiles in this bounded batch; use 2 to keep each run below six hours")
    parser.add_argument("--stage", choices=("shariatpur_review", "full_division"),
                        default="shariatpur_review",
                        help="Stop after Shariatpur for quality review unless full_division is explicitly selected")
    args = parser.parse_args()
    if args.stage == "full_division":
        approval = validate_shariatpur_release_approval()
        print("Shariatpur release gate APPROVED by %s on %s; evidence: %s" % (
            approval["reviewer"], approval["reviewed_at"], approval["review_evidence_url"]
        ), flush=True)
    if not 0.01 <= args.tile_degrees <= 0.08:
        parser.error("--tile-degrees must be between 0.01 and 0.08 degrees")
    if args.tile_offset < 0:
        parser.error("--tile-offset must be zero or greater")
    if args.max_tiles < 1:
        parser.error("--max-tiles must be at least 1; build the division as sequential batches")
    boundary, boundary_properties = load_dhaka_boundary(args.boundary)
    shariatpur_boundary, shariatpur_properties = load_shariatpur_boundary(args.district_boundary)
    min_lon, min_lat, max_lon, max_lat = boundary.bounds
    bounds = (min_lat, min_lon, max_lat, max_lon)
    full_tiles = list(tile_bounds(bounds, args.tile_degrees))
    tiles = []
    for tile in full_tiles:
        s, w, n, e = tile
        if boundary.intersects(box(w, s, e, n)):
            tiles.append(tile)
    total_tiles = len(tiles)
    # Shariatpur is first in the sequence; the remaining offsets still span
    # every tile intersecting the entire Dhaka Division boundary.
    priority_lat, priority_lon = SHARIATPUR_PRIORITY_LAT_LON
    shariatpur_tile_count = sum(
        1 for tile in tiles
        if shariatpur_boundary.intersects(box(tile[1], tile[0], tile[3], tile[2]))
    )
    ordered_tiles = order_tiles_shariatpur_first(tiles, shariatpur_boundary)
    build_boundary = build_boundary_for_stage(args.stage, boundary, shariatpur_boundary)
    build_boundary_properties = shariatpur_properties if args.stage == "shariatpur_review" else boundary_properties
    build_boundary_name = "Shariatpur District" if args.stage == "shariatpur_review" else "Dhaka Division"
    boundary_attribution = boundary_attribution_for_stage(args.stage)
    if stage_gate_reached(args.tile_offset, shariatpur_tile_count, args.stage):
        # A stale/queued dispatch from the previous workflow version must not
        # accidentally bake non-Shariatpur tiles. Emit an explicit successful
        # gate marker so the workflow can stop without treating it as a build failure.
        args.out.mkdir(parents=True, exist_ok=True)
        output_manifest = {
            "product": "Project A-Square — Shariatpur review gate marker",
            "source": "Geofabrik Bangladesh OpenStreetMap PBF",
            "source_url": PBF_URL,
            "attribution": OSM_ATTRIBUTION,
            "license": "OSM data: ODbL 1.0. Administrative boundary licenses are recorded from geoBoundaries API metadata.",
            "administrative_boundary": {
                "name": build_boundary_name,
                "source": "geoBoundaries gbOpen BGD ADM2" if args.stage == "shariatpur_review" else "geoBoundaries gbOpen BGD ADM1",
                "properties": build_boundary_properties.get("feature_properties", {}),
                "metadata": build_boundary_properties,
                "license": build_boundary_properties.get("boundary_license", "See geoBoundaries metadata"),
                "attribution": boundary_attribution,
            },
            "region_south_west_north_east": list((build_boundary.bounds[1], build_boundary.bounds[0], build_boundary.bounds[3], build_boundary.bounds[2])),
            "tile_edge_degrees": args.tile_degrees,
        "pipeline_commit_sha": pipeline_commit_sha(),
            "build_stage": args.stage,
            "stage_gate_reached": True,
            "tile_count_intersecting_boundary": shariatpur_tile_count if args.stage == "shariatpur_review" else total_tiles,
            "tile_count_intersecting_division": total_tiles,
            "tile_batch_offset": args.tile_offset,
            "tile_batch_count": 0,
            "tile_batch_tile_ids": [],
            "tile_order_priority": {
                "name": "Shariatpur District first",
                "seed_lat_lon": [priority_lat, priority_lon],
                "district_boundary_source": "geoBoundaries gbOpen BGD ADM2",
                "district_boundary_properties": shariatpur_properties.get("feature_properties", {}),
                "district_boundary_license": shariatpur_properties.get("boundary_license", "See geoBoundaries metadata"),
                "district_boundary_license_source": shariatpur_properties.get("boundary_license_source", ""),
                "district_boundary_id": shariatpur_properties.get("boundary_id", ""),
                "tiles_intersecting_shariatpur_district": shariatpur_tile_count,
            },
            "tile_count_with_geometry": 0,
            "source_elements_in_boundary_envelope": 0,
            "missing_way_locations": 0,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "completeness_note": "No tiles were built. This marker prevents a stale Shariatpur-review dispatch from spilling into other districts.",
            "tiles": [],
        }
        (args.out / "map_tiles_manifest.json").write_text(
            json.dumps(output_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (args.out / "ATTRIBUTION.txt").write_text(
            OSM_ATTRIBUTION + "\n" + boundary_attribution + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"stage_gate_reached": True, "tile_batch_count": 0,
                          "shariatpur_tile_count": shariatpur_tile_count}, indent=2))
        return 0
    effective_limit = effective_batch_limit(
        args.tile_offset, args.max_tiles, shariatpur_tile_count, args.stage
    )
    tiles = select_tile_batch(ordered_tiles, args.tile_offset, effective_limit)
    if not tiles:
        raise RuntimeError(
            f"No tiles remain at offset {args.tile_offset}; total intersecting tiles: {total_tiles}."
        )
    print(
        f"Full Dhaka Division intersects {total_tiles} tiles at {args.tile_degrees}°; "
        f"building batch offsets {args.tile_offset}–{args.tile_offset + len(tiles) - 1} "
        f"({len(tiles)} tiles); {shariatpur_tile_count} tiles intersect Shariatpur District and are first.",
        flush=True,
    )
    # In bounded test mode, extract only the selected tiles instead of storing
    # every mapped feature in the entire division in memory.
    if args.max_tiles > 0:
        extract_bounds = (min(t[0] for t in tiles), min(t[1] for t in tiles),
                          max(t[2] for t in tiles), max(t[3] for t in tiles))
    else:
        extract_bounds = bounds
    if args.pbf.name == "dhaka-division-envelope.osm.pbf":
        if not args.pbf.is_file() or args.pbf.stat().st_size < 10_000_000:
            raise RuntimeError(
                "Prepared Dhaka Division PBF is missing or too small. Run "
                "tools/map_pipeline/prepare_dhaka_division_pbf.py first."
            )
        print(f"Using cached regional OSM extract {args.pbf} ({args.pbf.stat().st_size:,} bytes)", flush=True)
    else:
        download(PBF_URL, args.pbf, 100_000_000)
    handler = RegionHandler(extract_bounds)
    print("Extracting OSM features for selected Dhaka Division tiles…", flush=True)
    handler.apply_file(str(args.pbf), locations=True)
    print(f"Extracted {len(handler.elements):,} source elements; invalid ways: {handler.bad_locations}", flush=True)
    if not handler.elements:
        raise RuntimeError("No mapped OSM features found in the selected Dhaka Division tile bounds.")
    args.out.mkdir(parents=True, exist_ok=True)
    cols = max(1, math.ceil((max_lon - min_lon) / args.tile_degrees))
    tile_index_by_grid = {}
    for i, (s, w, n, e) in enumerate(tiles):
        col = max(0, min(cols - 1, int(math.floor((w - min_lon) / args.tile_degrees))))
        row = max(0, int(math.floor((s - min_lat) / args.tile_degrees)))
        tile_index_by_grid[(row, col)] = i
    candidates: list[list[dict[str, Any]]] = [[] for _ in tiles]
    for el in handler.elements:
        if el["type"] == "node":
            x0 = x1 = float(el["lon"])
            y0 = y1 = float(el["lat"])
        else:
            bb = el.get("_bbox")
            if not bb:
                continue
            x0, y0, x1, y1 = map(float, bb)
        c0 = max(0, min(cols - 1, int(math.floor((x0 - min_lon) / args.tile_degrees))))
        c1 = max(0, min(cols - 1, int(math.floor((x1 - min_lon) / args.tile_degrees))))
        r0 = max(0, int(math.floor((y0 - min_lat) / args.tile_degrees)))
        r1 = max(0, int(math.floor((y1 - min_lat) / args.tile_degrees)))
        for row in range(r0, r1 + 1):
            for col in range(c0, c1 + 1):
                index = tile_index_by_grid.get((row, col))
                if index is not None:
                    candidates[index].append(el)
    tile_records = []
    for index, bbox in enumerate(tiles, start=1):
        s, w, n, e = bbox
        tile_id = f"tile_{s:.4f}_{w:.4f}".replace(".", "p")
        tile_dir = args.out / tile_id
        tile_polygon = box(w, s, e, n)
        boundary_tile = build_boundary.intersection(tile_polygon)
        clipped = _clip_elements(candidates[index - 1], boundary_tile)
        clipped = add_curated_manasha_footprint(clipped, boundary_tile)
        tile_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(tiles)}] {tile_id}: {len(clipped):,} clipped source + curated features", flush=True)
        # Always bake a ground mesh for every tile. A tile with no mapped OSM
        # features must not become a hole in the explorable world.
        manifest = build_map(clipped, tile_dir, bbox)
        counts = manifest.get("feature_counts", {})
        if int(counts.get("curated_approximate_landmark_footprints", 0)) > 0:
            if int(counts.get("licensed_facade_photo_panels", 0)) < 1:
                raise RuntimeError(
                    "Curated Manasha landmark exists in this tile but the licensed exterior photo panel was not embedded."
                )
        glb_path = tile_dir / "Dhaka_Explorable_Map.glb"
        _replace_ground_with_boundary(glb_path, boundary_tile, bbox)
        tile_records.append({
            "tile_id": tile_id, "bbox_south_west_north_east": list(bbox),
            "origin_lat_lon": manifest["local_origin_lat_lon"],
            "extent_metres_approx": manifest["extent_metres_approx"],
            "glb": f"{tile_id}/Dhaka_Explorable_Map.glb",
            "geojson": f"{tile_id}/Dhaka_OSM_Source.geojson",
            "interior_seeds": f"{tile_id}/AI_Interior_Seeds.json",
            "feature_counts": counts, "status": tile_status_from_counts(counts),
            "curated_landmark_geometry_confidence": (
                "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED"
                if int(counts.get("curated_approximate_landmark_footprints", 0)) > 0
                else "SOURCE_DERIVED_FEATURES_ONLY"
            ),
        })
    valid = sum("glb" in t for t in tile_records)
    output_manifest = {
        "product": "Project A-Square — " + build_boundary_name + " boundary-clipped 3D map tile batch",
        "source": "Geofabrik Bangladesh OpenStreetMap PBF plus a disclosed curated landmark fallback where the source footprint is missing",
        "source_url": PBF_URL,
        "curated_landmark_fallback_note": "The Manasha Temple fallback is an approximate, unsurveyed footprint positioned using a published place coordinate. It is pending local outline/placement review and is not an OSM building survey.",
        "attribution": OSM_ATTRIBUTION,
        "license": "OSM data: ODbL 1.0. Administrative boundary license is recorded from geoBoundaries API metadata in administrative_boundary.metadata.boundary_license.",
        "administrative_boundary": {"name": build_boundary_name,
                                   "source": "geoBoundaries gbOpen BGD ADM2" if args.stage == "shariatpur_review" else "geoBoundaries gbOpen BGD ADM1",
                                   "properties": build_boundary_properties.get("feature_properties", {}),
                                   "metadata": build_boundary_properties,
                                   "license": build_boundary_properties.get("boundary_license", "See geoBoundaries metadata"),
                                   "attribution": boundary_attribution},
        "region_south_west_north_east": list((build_boundary.bounds[1], build_boundary.bounds[0],
                                                build_boundary.bounds[3], build_boundary.bounds[2])),
        "tile_edge_degrees": args.tile_degrees,
        "pipeline_commit_sha": pipeline_commit_sha(),
        "build_stage": args.stage,
        "tile_count_intersecting_boundary": shariatpur_tile_count if args.stage == "shariatpur_review" else total_tiles,
        "tile_count_intersecting_division": total_tiles,
        "tile_count_intersecting_build_boundary": shariatpur_tile_count if args.stage == "shariatpur_review" else total_tiles,
        "tile_batch_offset": args.tile_offset,
        "tile_batch_count": len(tiles),
        "tile_batch_tile_ids": [r["tile_id"] for r in tile_records],
        "tile_order_priority": {"name": "Shariatpur District first", "seed_lat_lon": [priority_lat, priority_lon],
                                "district_boundary_source": "geoBoundaries gbOpen BGD ADM2",
                                "district_boundary_properties": shariatpur_properties.get("feature_properties", {}),
                                "district_boundary_license": shariatpur_properties.get("boundary_license", "See geoBoundaries metadata"),
                                "district_boundary_license_source": shariatpur_properties.get("boundary_license_source", ""),
                                "district_boundary_id": shariatpur_properties.get("boundary_id", ""),
                                "tiles_intersecting_shariatpur_district": shariatpur_tile_count,
                                "note": "All Shariatpur-intersecting tiles are emitted first; later offsets continue through every remaining Dhaka Division tile."},
        "tile_count_with_geometry": valid,
        "source_elements_in_boundary_envelope": len(handler.elements),
        "missing_way_locations": handler.bad_locations,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "coordinate_note": "Each GLB has its own geographic origin; use manifest origins for streaming. Tiles and ground are clipped to the selected administrative boundary.",
        "completeness_note": "This artifact is one bounded batch from the complete Dhaka Division tile order. Collect all batch offsets to cover the full division. OSM mapped features only; not proof every real-world feature is mapped. Facades, heights, interiors, and imagery remain incomplete unless source data provides them.",
        "tiles": tile_records,
    }
    (args.out / "map_tiles_manifest.json").write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    boundary_license_text = str(build_boundary_properties.get("boundary_license", "See geoBoundaries metadata"))
    boundary_type = "ADM2" if args.stage == "shariatpur_review" else "ADM1"
    (args.out / "ATTRIBUTION.txt").write_text(
        OSM_ATTRIBUTION + "\n" + boundary_attribution + "\n"
        + "OSM data license: ODbL 1.0.\n"
        + f"Clipping boundary: {build_boundary_name} (geoBoundaries gbOpen BGD {boundary_type}).\n"
        + f"Clipping boundary ID: {build_boundary_properties.get('boundary_id', 'unspecified')}.\n"
        + f"Clipping boundary license: {boundary_license_text}. "
        + f"License source: {build_boundary_properties.get('boundary_license_source', 'See manifest')}.\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.out), "tiles": len(tiles), "tiles_with_geometry": valid,
                      "source_elements": len(handler.elements), "bounds": list(bounds)}, indent=2))
    if valid == 0:
        raise SystemExit("No mapped road/building tiles were produced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
