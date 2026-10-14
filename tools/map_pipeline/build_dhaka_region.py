#!/usr/bin/env python3
"""Build a tiled, georeferenced 3D map of Dhaka from a Bangladesh OSM PBF.

Downloads the Geofabrik Bangladesh extract once, extracts mapped ways/nodes for
the requested bounds, and bakes independent GLB tiles. Each tile keeps its own
geographic origin in map_tiles_manifest.json so the game can place/stream tiles
without losing real-world alignment.

Requires: osmium (pyosmium), shapely, trimesh, mapbox-earcut.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import urllib.request
from typing import Any

import osmium
from shapely.geometry import box
from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map

PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
# Greater Dhaka working boundary: deliberately explicit and editable.
DEFAULT_REGION = (23.66, 90.30, 23.90, 90.53)  # south, west, north, east
INTERESTING_KEYS = {
    "building", "highway", "shop", "amenity", "tourism", "historic",
    "leisure", "office", "healthcare", "public_transport", "landuse",
    "natural", "waterway", "railway", "man_made",
}


def has_feature(tags: Any) -> bool:
    return any(key in tags for key in INTERESTING_KEYS)


class RegionHandler(osmium.SimpleHandler):
    def __init__(self, bbox: tuple[float, float, float, float]):
        super().__init__()
        self.south, self.west, self.north, self.east = bbox
        self.bounds = box(self.west, self.south, self.east, self.north)
        self.elements: list[dict[str, Any]] = []
        self.bad_locations = 0

    def node(self, n: Any) -> None:
        if not has_feature(n.tags) or not n.location.valid():
            return
        lat, lon = float(n.location.lat), float(n.location.lon)
        if self.west <= lon <= self.east and self.south <= lat <= self.north:
            self.elements.append({
                "type": "node", "id": int(n.id), "lat": lat, "lon": lon,
                "tags": dict(n.tags),
            })

    def way(self, w: Any) -> None:
        if not has_feature(w.tags):
            return
        coords = []
        try:
            for node in w.nodes:
                if not node.location.valid():
                    continue
                coords.append({"lat": float(node.location.lat), "lon": float(node.location.lon)})
        except Exception:
            self.bad_locations += 1
            return
        if len(coords) < 2:
            return
        min_lon = min(p["lon"] for p in coords)
        max_lon = max(p["lon"] for p in coords)
        min_lat = min(p["lat"] for p in coords)
        max_lat = max(p["lat"] for p in coords)
        if not box(min_lon, min_lat, max_lon, max_lat).intersects(self.bounds):
            return
        self.elements.append({
            "type": "way", "id": int(w.id), "tags": dict(w.tags), "geometry": coords,
        })


def download_pbf(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 100_000_000:
        print(f"Using cached PBF: {path} ({path.stat().st_size:,} bytes)")
        return
    temp = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(PBF_URL, headers={"User-Agent": "Project-A-Square-DhakaMap/1.0"})
    print(f"Downloading Bangladesh OSM extract from {PBF_URL}", flush=True)
    with urllib.request.urlopen(request, timeout=180) as response, temp.open("wb") as out:
        total = int(response.headers.get("Content-Length", "0"))
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total and downloaded % (25 * 1024 * 1024) < len(chunk):
                print(f"Downloaded {downloaded:,}/{total:,} bytes", flush=True)
    if temp.stat().st_size < 100_000_000:
        raise RuntimeError("Downloaded OSM PBF is unexpectedly small; refusing to build an incomplete map.")
    temp.replace(path)


def tile_bounds(region: tuple[float, float, float, float], tile_degrees: float):
    south, west, north, east = region
    lat = south
    while lat < north - 1e-9:
        next_lat = min(north, lat + tile_degrees)
        lon = west
        while lon < east - 1e-9:
            next_lon = min(east, lon + tile_degrees)
            yield (round(lat, 7), round(lon, 7), round(next_lat, 7), round(next_lon, 7))
            lon = next_lon
        lat = next_lat


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", nargs=4, type=float, default=DEFAULT_REGION,
                        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
                        help="coverage bounds in decimal degrees")
    parser.add_argument("--tile-degrees", type=float, default=0.02,
                        help="tile edge in degrees (default ~2 km; smaller tiles improve streaming)")
    parser.add_argument("--pbf", type=pathlib.Path, default=pathlib.Path("build/osm/bangladesh-latest.osm.pbf"))
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/dhaka-region-map"))
    parser.add_argument("--max-tiles", type=int, default=0, help="debug limit; 0 builds every tile")
    args = parser.parse_args()
    south, west, north, east = tuple(args.region)
    if not (-90 < south < north < 90 and -180 < west < east < 180):
        parser.error("region must be south, west, north, east in valid coordinate order")
    if not 0.005 <= args.tile_degrees <= 0.05:
        parser.error("--tile-degrees must be between 0.005 and 0.05 degrees")

    download_pbf(args.pbf)
    handler = RegionHandler((south, west, north, east))
    print("Extracting mapped OSM nodes and ways in the Dhaka region…", flush=True)
    handler.apply_file(str(args.pbf), locations=True)
    if not handler.elements:
        raise RuntimeError("No mapped OSM features were extracted; refusing to publish an empty map.")
    print(f"Extracted {len(handler.elements):,} mapped source elements; invalid way locations: {handler.bad_locations}", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    tiles = list(tile_bounds((south, west, north, east), args.tile_degrees))
    if args.max_tiles > 0:
        tiles = tiles[:args.max_tiles]
    tile_records = []
    for index, bbox in enumerate(tiles, start=1):
        tile_s, tile_w, tile_n, tile_e = bbox
        # Only pass candidate elements touching this tile; build_map clips actual geometry.
        candidates = []
        tile_box = box(tile_w, tile_s, tile_e, tile_n)
        for element in handler.elements:
            if element["type"] == "node":
                if tile_w <= element["lon"] <= tile_e and tile_s <= element["lat"] <= tile_n:
                    candidates.append(element)
                continue
            geom = element.get("geometry", [])
            if not geom:
                continue
            min_lon = min(p["lon"] for p in geom)
            max_lon = max(p["lon"] for p in geom)
            min_lat = min(p["lat"] for p in geom)
            max_lat = max(p["lat"] for p in geom)
            if box(min_lon, min_lat, max_lon, max_lat).intersects(tile_box):
                candidates.append(element)
        tile_id = f"tile_{tile_s:.4f}_{tile_w:.4f}".replace(".", "p")
        tile_dir = args.out / tile_id
        print(f"[{index}/{len(tiles)}] {tile_id}: {len(candidates):,} candidate features", flush=True)
        manifest = build_map(candidates, tile_dir, bbox)
        counts = manifest.get("feature_counts", {})
        if counts.get("building_footprints", 0) == 0 and counts.get("road_ways", 0) == 0:
            # Keep empty-tile metadata for coverage transparency, but don't list a GLB as playable.
            tile_records.append({
                "tile_id": tile_id, "bbox_south_west_north_east": list(bbox),
                "status": "NO_MAPPED_ROADS_OR_BUILDINGS", "feature_counts": counts,
            })
            continue
        tile_records.append({
            "tile_id": tile_id,
            "bbox_south_west_north_east": list(bbox),
            "origin_lat_lon": manifest["local_origin_lat_lon"],
            "extent_metres_approx": manifest["extent_metres_approx"],
            "glb": f"{tile_id}/Dhaka_Explorable_Map.glb",
            "geojson": f"{tile_id}/Dhaka_OSM_Source.geojson",
            "interior_seeds": f"{tile_id}/AI_Interior_Seeds.json",
            "feature_counts": counts,
            "status": "BAKED_FROM_OSM",
        })

    region_manifest = {
        "product": "Project A-Square — tiled Greater Dhaka real-data map",
        "source": "Geofabrik Bangladesh OpenStreetMap PBF extract",
        "source_url": PBF_URL,
        "attribution": "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright",
        "license": "ODbL 1.0; review attribution/share-alike obligations before redistribution",
        "region_south_west_north_east": [south, west, north, east],
        "tile_edge_degrees": args.tile_degrees,
        "tile_count_requested": len(tiles),
        "tile_count_with_geometry": sum(1 for tile in tile_records if tile["status"] == "BAKED_FROM_OSM"),
        "source_elements_in_region": len(handler.elements),
        "missing_way_locations": handler.bad_locations,
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "coordinate_note": "Each GLB is local to its own origin_lat_lon; use the tile manifest to position tiles consistently. Do not stack tile origins at (0,0).",
        "completeness_note": "This is the mapped OSM representation of the stated boundary, not proof that every real-world feature is mapped. OSM does not supply complete facade photography, surveyed heights, indoor layouts, or real shopkeeper identities.",
        "tiles": tile_records,
    }
    (args.out / "map_tiles_manifest.json").write_text(json.dumps(region_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "ATTRIBUTION.txt").write_text(
        "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright\n"
        "Data license: Open Database License (ODbL) 1.0.\n"
        "Map geometry is derived from OpenStreetMap data. Review ODbL obligations before redistribution.\n",
        encoding="utf-8",
    )
    summary = {
        "output": str(args.out),
        "tile_count_requested": len(tiles),
        "tile_count_with_geometry": region_manifest["tile_count_with_geometry"],
        "source_elements_in_region": len(handler.elements),
    }
    print(json.dumps(summary, indent=2))
    if region_manifest["tile_count_with_geometry"] == 0:
        raise SystemExit("No tiles contained real mapped roads/buildings; refusing to publish empty map.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
