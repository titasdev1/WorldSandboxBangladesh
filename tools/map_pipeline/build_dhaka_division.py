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
import pathlib
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from typing import Any

import osmium
import trimesh
from shapely.geometry import GeometryCollection, LineString, MultiLineString, MultiPolygon, Point, Polygon, box, shape
from shapely.ops import transform

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.map_pipeline.build_dhaka_map import build_map, local_xy, extruded_polygon, color_mesh
from tools.map_pipeline.tile_grid import tile_bounds

PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
BOUNDARY_API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM1/"
DISTRICT_BOUNDARY_API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM2/"
INTERESTING_KEYS = {
    "building", "highway", "shop", "amenity", "tourism", "historic",
    "leisure", "office", "healthcare", "public_transport", "landuse",
    "natural", "waterway", "railway", "man_made",
}
OSM_ATTRIBUTION = "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright"
BOUNDARY_ATTRIBUTION = "Administrative boundary source: geoBoundaries (https://www.geoboundaries.org), gbOpen BGD ADM1. See manifest for the returned dataset license."


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
    if tags.get("building") and len(coords) >= 4 and coords[0] == coords[-1]:
        geom = Polygon(coords)
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
        expected = "polygon" if tags.get("building") and isinstance(geom, (Polygon, MultiPolygon)) else "line"
        for i, part in enumerate(_parts(clipped, expected), start=1):
            if expected == "polygon" and part.area < 1e-10:
                continue
            if expected == "line" and part.length < 1e-7:
                continue
            result.append(_to_element(element, part, i))
    return result


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
    args = parser.parse_args()
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
    tiles = select_tile_batch(ordered_tiles, args.tile_offset, args.max_tiles)
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
        boundary_tile = boundary.intersection(tile_polygon)
        clipped = _clip_elements(candidates[index - 1], boundary_tile)
        if not clipped:
            tile_records.append({"tile_id": tile_id, "bbox_south_west_north_east": list(bbox),
                                 "status": "NO_MAPPED_FEATURES", "feature_counts": {}})
            continue
        print(f"[{index}/{len(tiles)}] {tile_id}: {len(clipped):,} clipped features", flush=True)
        manifest = build_map(clipped, tile_dir, bbox)
        counts = manifest.get("feature_counts", {})
        if counts.get("building_footprints", 0) == 0 and counts.get("road_ways", 0) == 0:
            shutil.rmtree(tile_dir, ignore_errors=True)
            tile_records.append({"tile_id": tile_id, "bbox_south_west_north_east": list(bbox),
                                 "status": "NO_MAPPED_ROADS_OR_BUILDINGS", "feature_counts": counts})
            continue
        glb_path = tile_dir / "Dhaka_Explorable_Map.glb"
        _replace_ground_with_boundary(glb_path, boundary_tile, bbox)
        tile_records.append({
            "tile_id": tile_id, "bbox_south_west_north_east": list(bbox),
            "origin_lat_lon": manifest["local_origin_lat_lon"],
            "extent_metres_approx": manifest["extent_metres_approx"],
            "glb": f"{tile_id}/Dhaka_Explorable_Map.glb",
            "geojson": f"{tile_id}/Dhaka_OSM_Source.geojson",
            "interior_seeds": f"{tile_id}/AI_Interior_Seeds.json",
            "feature_counts": counts, "status": "BAKED_FROM_OSM",
        })
    valid = sum(t["status"] == "BAKED_FROM_OSM" for t in tile_records)
    output_manifest = {
        "product": "Project A-Square — Dhaka Division boundary-clipped 3D map tile batch",
        "source": "Geofabrik Bangladesh OpenStreetMap PBF",
        "source_url": PBF_URL,
        "attribution": OSM_ATTRIBUTION,
        "license": "OSM data: ODbL 1.0. Administrative boundary license is recorded from geoBoundaries API metadata in administrative_boundary.metadata.boundary_license.",
        "administrative_boundary": {"name": "Dhaka Division", "source": "geoBoundaries gbOpen BGD ADM1",
                                   "properties": boundary_properties.get("feature_properties", {}), "metadata": boundary_properties, "license": boundary_properties.get("boundary_license", "See geoBoundaries metadata"),
                                   "attribution": BOUNDARY_ATTRIBUTION},
        "region_south_west_north_east": list(bounds),
        "tile_edge_degrees": args.tile_degrees,
        "tile_count_intersecting_boundary": total_tiles,
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
    boundary_license_text = str(boundary_properties.get("boundary_license", "See geoBoundaries metadata"))
    (args.out / "ATTRIBUTION.txt").write_text(
        OSM_ATTRIBUTION + "\n" + BOUNDARY_ATTRIBUTION + "\n"
        + "OSM data license: ODbL 1.0.\n"
        + f"geoBoundaries Dhaka Division boundary license: {boundary_license_text}.\n"
        + f"Shariatpur District boundary used for tile ordering only: geoBoundaries gbOpen BGD ADM2, "
        + f"boundary ID {shariatpur_properties.get('boundary_id', 'unspecified')}.\n"
        + f"Shariatpur district-boundary license: {shariatpur_properties.get('boundary_license', 'See geoBoundaries metadata')}. "
        + f"License source: {shariatpur_properties.get('boundary_license_source', 'See manifest')}.\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.out), "tiles": len(tiles), "tiles_with_geometry": valid,
                      "source_elements": len(handler.elements), "bounds": list(bounds)}, indent=2))
    if valid == 0:
        raise SystemExit("No mapped road/building tiles were produced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
