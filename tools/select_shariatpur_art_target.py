#!/usr/bin/env python3
"""Select one real Shariatpur retail footprint and assemble a validation-only map subset.

This never changes the source 60-tile review map. It copies one mapped tile into a
separate Godot smoke-test project, records the exact OSM feature/door/height
provenance and clearly marks the output as a one-tile validation subset.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import sys
from typing import Any

EARTH_RADIUS_M = 6_378_137.0
DEFAULT_ASSET_WIDTH_M = 12.28
DEFAULT_ASSET_DEPTH_M = 9.875


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _footprint_bounds(points: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(points, list) or len(points) < 3:
        return None
    xy: list[tuple[float, float]] = []
    for point in points:
        if not (isinstance(point, list) and len(point) >= 2):
            return None
        try:
            xy.append((float(point[0]), float(point[1])))
        except (TypeError, ValueError):
            return None
    xs = [p[0] for p in xy]
    ys = [p[1] for p in xy]
    bounds = min(xs), min(ys), max(xs), max(ys)
    if bounds[2] - bounds[0] < 2.5 or bounds[3] - bounds[1] < 2.5:
        return None
    return bounds


def _score(seed: dict[str, Any], width: float, depth: float) -> tuple[float, dict[str, Any]] | None:
    footprint = _footprint_bounds(seed.get("footprint_local_m"))
    if footprint is None:
        return None
    min_x, min_y, max_x, max_y = footprint
    sx, sy = max_x - min_x, max_y - min_y
    if min(sx, sy) < 3.0 or max(sx, sy) > 50.0:
        return None

    tags = seed.get("building_tags", {})
    if not isinstance(tags, dict):
        tags = {}
    category = str(seed.get("category", "")).strip().lower()
    shop = str(tags.get("shop", "")).strip().lower()
    building = str(tags.get("building", "")).strip().lower()
    amenity = str(tags.get("amenity", "")).strip().lower()
    if not (shop or category in {"retail", "commercial"} or building in {"retail", "commercial"}):
        return None

    # Do not use approximate curated landmark footprints as a generic shop target.
    confidence = str(seed.get("geometry_confidence", ""))
    if "CURATED_APPROXIMATE" in confidence or "NOT_SURVEYED" in confidence:
        return None

    door_anchor = seed.get("door_anchor_local_m")
    door_outward = seed.get("door_outward_xy")
    has_door = (
        isinstance(door_anchor, list) and len(door_anchor) >= 2
        and isinstance(door_outward, list) and len(door_outward) >= 2
    )
    if not has_door:
        return None

    target_long, target_short = max(width, depth), min(width, depth)
    actual_long, actual_short = max(sx, sy), min(sx, sy)
    area_ratio_penalty = abs(math.log(max(0.01, (sx * sy) / (width * depth))))
    shape_penalty = abs(math.log(max(0.01, (actual_long / actual_short) / (target_long / target_short))))
    scale_penalty = abs(math.log(max(0.01, actual_long / target_long))) + abs(math.log(max(0.01, actual_short / target_short)))
    category_bonus = 0.0 if shop else (0.12 if category == "retail" or building == "retail" else 0.22)
    score = area_ratio_penalty * 0.48 + shape_penalty * 0.35 + scale_penalty * 0.28 + category_bonus

    center_x, center_y = (min_x + max_x) * 0.5, (min_y + max_y) * 0.5
    return score, {
        "osm_id": str(seed.get("osm_id", "")),
        "name": str(seed.get("name", "")),
        "category": category,
        "building_tags": tags,
        "footprint_local_m": seed["footprint_local_m"],
        "footprint_bounds_local_m": [round(min_x, 3), round(min_y, 3), round(max_x, 3), round(max_y, 3)],
        "footprint_dimensions_m": [round(sx, 3), round(sy, 3)],
        "footprint_area_bbox_m2": round(sx * sy, 3),
        "center_local_m": [round(center_x, 3), round(center_y, 3)],
        "door_anchor_local_m": door_anchor,
        "door_outward_xy": door_outward,
        "door_placement_source": seed.get("door_placement_source", ""),
        "ground_elevation_m": seed.get("ground_elevation_m", 0.0),
        "height_metres": seed.get("height_metres"),
        "height_source": seed.get("height_source", ""),
        "floors_estimate": seed.get("floors_estimate"),
        "floors_source": seed.get("floors_source", ""),
        "geometry_confidence": confidence,
        "source_dataset": tags.get("source_dataset", "OpenStreetMap"),
        "match_score": round(score, 6),
    }


def _local_to_geo(x: float, y: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    lat = origin_lat + math.degrees(y / EARTH_RADIUS_M)
    cos_lat = max(0.01, math.cos(math.radians(origin_lat)))
    lon = origin_lon + math.degrees(x / (EARTH_RADIUS_M * cos_lat))
    return lat, lon


def select(map_root: pathlib.Path, out_dir: pathlib.Path, asset_width: float, asset_depth: float,
           source_run_id: int, source_commit: str, sequence_id: str) -> dict[str, Any]:
    manifest_path = map_root / "map_tiles_manifest.json"
    if not manifest_path.is_file():
        # Permit a single nested directory from Actions artifact extraction.
        matches = list(map_root.rglob("map_tiles_manifest.json"))
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected exactly one map_tiles_manifest.json under {map_root}, found {len(matches)}")
        manifest_path = matches[0]
        map_root = manifest_path.parent
    manifest = _read_json(manifest_path)
    tiles = manifest.get("tiles", [])
    if not isinstance(tiles, list) or len(tiles) != 60:
        raise ValueError(f"Expected the preserved 60-tile Shariatpur source, found {len(tiles) if isinstance(tiles, list) else 'malformed'}")
    if str(manifest.get("build_stage", "")).lower() != "shariatpur_review":
        raise ValueError(f"Refusing non-Shariatpur source map: build_stage={manifest.get('build_stage')!r}")

    candidates: list[dict[str, Any]] = []
    for tile in tiles:
        if not isinstance(tile, dict):
            continue
        tile_id = str(tile.get("tile_id", "")).strip()
        seed_rel = str(tile.get("interior_seeds", "")).strip()
        if not tile_id or not seed_rel:
            continue
        seed_path = map_root / seed_rel
        if not seed_path.is_file():
            continue
        try:
            seeds = _read_json(seed_path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(seeds, list):
            continue
        origin = tile.get("origin_lat_lon", [])
        if not (isinstance(origin, list) and len(origin) == 2):
            continue
        origin_lat, origin_lon = float(origin[0]), float(origin[1])
        for seed in seeds:
            if not isinstance(seed, dict):
                continue
            scored = _score(seed, asset_width, asset_depth)
            if scored is None:
                continue
            score, details = scored
            center = details["center_local_m"]
            lat, lon = _local_to_geo(float(center[0]), float(center[1]), origin_lat, origin_lon)
            candidates.append({
                "tile": tile,
                "tile_id": tile_id,
                "seed": seed,
                "score": score,
                "details": {
                    **details,
                    "latitude": round(lat, 7),
                    "longitude": round(lon, 7),
                    "tile_origin_lat_lon": origin,
                },
            })
    if not candidates:
        raise RuntimeError("No OSM/Overture retail footprint with a mapped entrance and usable geometry was found.")

    candidates.sort(key=lambda item: item["score"])
    winner = candidates[0]
    tile = winner["tile"]
    tile_id = winner["tile_id"]
    tile_dir = map_root / tile_id
    required_relative = [
        str(tile.get("glb", "")),
        str(tile.get("geojson", "")),
        str(tile.get("interior_seeds", "")),
        f"{tile_id}/map_manifest.json",
        "ATTRIBUTION.txt",
    ]
    for rel in required_relative:
        if not rel or not (map_root / rel).is_file():
            raise FileNotFoundError(f"Selected source tile is missing a required file: {rel}")

    out_dir.mkdir(parents=True, exist_ok=True)
    target_root = out_dir / "selected-map"
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    # Copy only the one target GLB, road GeoJSON, seed file, tile manifest and
    # attribution. Preserve original relative paths so Godot's existing loader
    # and real door/collision code are exercised without mutating the 60-tile base.
    for rel in required_relative:
        if rel == "ATTRIBUTION.txt":
            shutil.copy2(map_root / rel, target_root / rel)
            continue
        destination = target_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(map_root / rel, destination)

    subset_manifest = dict(manifest)
    subset_manifest["tiles"] = [tile]
    subset_manifest["tile_batch_count"] = 1
    subset_manifest["tile_count_total"] = 1
    subset_manifest["tile_count_with_geometry"] = 1
    subset_manifest["tile_count_intersecting_boundary"] = 1
    subset_manifest["complete_district_map"] = False
    subset_manifest["validation_subset"] = {
        "kind": "ONE_TILE_ART_AND_DOOR_SMOKE_ONLY",
        "source_tile_count": 60,
        "source_run_id": source_run_id,
        "source_commit": source_commit,
        "map_sequence_id": sequence_id,
        "source_map_manifest_sha256": __import__("hashlib").sha256(manifest_path.read_bytes()).hexdigest(),
        "note": "Validation-only copy. The full 60-tile map remains unchanged and is not replaced by this subset.",
    }
    (target_root / "map_tiles_manifest.json").write_text(
        json.dumps(subset_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report = {
        "status": "REAL_SHARIATPUR_RETAIL_FOOTPRINT_SELECTED_REQUIRES_VISUAL_MATCH_REVIEW",
        "source_map": {
            "run_id": source_run_id,
            "commit": source_commit,
            "map_sequence_id": sequence_id,
            "original_tile_count": 60,
            "map_manifest": "map_tiles_manifest.json",
        },
        "asset": {
            "id": "shariatpur_riverfront_shophouse_hero",
            "dimensions_m": [asset_width, asset_depth],
            "license": "CC0-1.0",
        },
        "selected_building": {
            "tile_id": tile_id,
            "glb": tile.get("glb"),
            "geojson": tile.get("geojson"),
            "interior_seeds": tile.get("interior_seeds"),
            **winner["details"],
        },
        "candidate_count": len(candidates),
        "top_candidates": [
            {"tile_id": item["tile_id"], **item["details"]}
            for item in candidates[:10]
        ],
        "limitations": [
            "A source OSM footprint and entrance are selected; this does not prove the authored façade visually matches a particular shop.",
            "Floor count remains source-tagged or estimated unless independently verified evidence is attached.",
            "The output is a one-tile runtime smoke subset and must never replace the complete 60-tile Shariatpur pack.",
        ],
    }
    report_path = out_dir / "shariatpur_art_target.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("A2_SHARIATPUR_REAL_FOOTPRINT_SELECTED: " + json.dumps(report["selected_building"], ensure_ascii=False))
    print(f"A2_SHARIATPUR_CANDIDATE_COUNT: {len(candidates)}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-root", type=pathlib.Path, required=True)
    parser.add_argument("--out-dir", type=pathlib.Path, required=True)
    parser.add_argument("--asset-width", type=float, default=DEFAULT_ASSET_WIDTH_M)
    parser.add_argument("--asset-depth", type=float, default=DEFAULT_ASSET_DEPTH_M)
    parser.add_argument("--source-run-id", type=int, default=44264284704)
    parser.add_argument("--source-commit", default="7a0d5831816e870004a1b45ac4d1f800d25653e1")
    parser.add_argument("--sequence-id", default="44257499872")
    args = parser.parse_args()
    try:
        report = select(args.map_root, args.out_dir, args.asset_width, args.asset_depth,
                        args.source_run_id, args.source_commit, args.sequence_id)
        print(f"A2_SHARIATPUR_ONE_TILE_MAP_SUBSET_READY: {args.out_dir / 'selected-map'}")
        return 0
    except Exception as exc:
        print(f"A2_SHARIATPUR_ART_TARGET_FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
