#!/usr/bin/env python3
"""Validate and merge bounded Dhaka Division map batches into one tile package."""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import shutil
from typing import Any

import numpy as np
import trimesh

from tools.map_pipeline.build_real_world_navigation_index import build_index


def merge_batches(batches_dir: pathlib.Path, out: pathlib.Path, stage: str = "full_division") -> dict[str, Any]:
    if stage not in {"shariatpur_review", "full_division"}:
        raise ValueError(f"Unsupported map merge stage: {stage}")
    batch_dirs = sorted(
        (path for path in batches_dir.iterdir() if path.is_dir()),
        key=lambda path: int(path.name),
    )
    if not batch_dirs:
        raise RuntimeError(f"No batch directories found under {batches_dir}")

    batches: list[tuple[int, pathlib.Path, dict[str, Any]]] = []
    for path in batch_dirs:
        manifest_path = path / "map_tiles_manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"Batch {path.name} has no map_tiles_manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        offset = int(manifest.get("tile_batch_offset", -1))
        count = int(manifest.get("tile_batch_count", len(manifest.get("tiles", []))))
        total_key = "tile_count_intersecting_build_boundary" if stage == "shariatpur_review" else "tile_count_intersecting_boundary"
        total = int(manifest.get(total_key, -1))
        if offset < 0 or count < 1 or total < 1:
            raise RuntimeError(f"Batch {path.name} has invalid offset/count/total metadata")
        if int(path.name) != offset:
            raise RuntimeError(f"Batch folder {path.name} does not match manifest offset {offset}")
        if len(manifest.get("tiles", [])) != count:
            raise RuntimeError(f"Batch {path.name} manifest tile list/count mismatch")
        batches.append((offset, path, manifest))

    batches.sort(key=lambda item: item[0])
    first = batches[0][2]
    total_tiles = int(first["tile_count_intersecting_build_boundary"] if stage == "shariatpur_review" else first["tile_count_intersecting_boundary"])
    division_total_tiles = int(first.get("tile_count_intersecting_division", first["tile_count_intersecting_boundary"]))
    tile_degrees = float(first["tile_edge_degrees"])
    pipeline_commit_sha = str(first.get("pipeline_commit_sha", "")).strip()
    if not pipeline_commit_sha:
        raise RuntimeError("Batch is missing pipeline_commit_sha; refusing to assemble an unverifiable tile sequence")
    boundary_name = first.get("administrative_boundary", {}).get("name")
    expected_boundary_name = "Shariatpur District" if stage == "shariatpur_review" else "Dhaka Division"
    if boundary_name != expected_boundary_name:
        raise RuntimeError(f"Wrong administrative boundary for {stage}: expected {expected_boundary_name}, got {boundary_name}")
    expected_offset = 0
    all_records: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    geometry_count = 0
    source_element_count = 0
    feature_counts: dict[str, int] = {}

    for offset, path, manifest in batches:
        manifest_total = int(manifest["tile_count_intersecting_build_boundary"] if stage == "shariatpur_review" else manifest["tile_count_intersecting_boundary"])
        if manifest_total != total_tiles:
            raise RuntimeError("Batches disagree on the total number of tiles for the selected build stage")
        batch_division_total = int(manifest.get("tile_count_intersecting_division", manifest["tile_count_intersecting_boundary"]))
        if batch_division_total != division_total_tiles:
            raise RuntimeError("Batches disagree on the Dhaka Division-wide tile count")
        if manifest.get("build_stage", "full_division") != stage:
            raise RuntimeError("Batches mix Shariatpur review and full-division build stages")
        if float(manifest["tile_edge_degrees"]) != tile_degrees:
            raise RuntimeError("Batches use different tile sizes; refusing to merge incompatible grids")
        if str(manifest.get("pipeline_commit_sha", "")).strip() != pipeline_commit_sha:
            raise RuntimeError("Batches were built from different pipeline commits; restart the complete tile sequence")
        if manifest.get("administrative_boundary", {}).get("name") != boundary_name:
            raise RuntimeError("Batches use different administrative boundaries")
        if offset != expected_offset:
            raise RuntimeError(f"Missing or overlapping tile batch: expected offset {expected_offset}, found {offset}")
        records = manifest.get("tiles", [])
        for record in records:
            tile_id = str(record.get("tile_id", ""))
            if not tile_id or tile_id in all_ids:
                raise RuntimeError(f"Missing or duplicate tile ID in batch {path.name}: {tile_id}")
            all_ids.add(tile_id)
            all_records.append(record)
            for feature, amount in record.get("feature_counts", {}).items():
                if isinstance(amount, (int, float)):
                    feature_counts[feature] = feature_counts.get(feature, 0) + int(amount)
        expected_offset += int(manifest["tile_batch_count"])
        geometry_count += int(manifest.get("tile_count_with_geometry", 0))
        source_element_count += int(manifest.get("source_elements_in_boundary_envelope", 0))

    if expected_offset != total_tiles or len(all_records) != total_tiles:
        raise RuntimeError(
            f"Incomplete {stage} coverage: merged {len(all_records)} of {total_tiles} expected tiles"
        )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    for _, batch_path, _ in batches:
        for source in batch_path.rglob("*"):
            if not source.is_file():
                continue
            relative = source.relative_to(batch_path)
            if relative.as_posix() in {"map_tiles_manifest.json", "ATTRIBUTION.txt"}:
                continue
            destination = out / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if destination.read_bytes() != source.read_bytes():
                    raise RuntimeError(f"Conflicting file while merging map batches: {relative}")
            else:
                shutil.copy2(source, destination)

    facade_photo_matches: list[dict[str, Any]] = []
    interior_reference_photo_matches: list[dict[str, Any]] = []
    for tile_manifest_path in sorted(out.rglob("map_manifest.json")):
        try:
            tile_manifest = json.loads(tile_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        matches = tile_manifest.get("licensed_facade_photo_matches", [])
        if isinstance(matches, list):
            facade_photo_matches.extend(item for item in matches if isinstance(item, dict))
        interior_matches = tile_manifest.get("interior_reference_photo_matches", [])
        if isinstance(interior_matches, list):
            interior_reference_photo_matches.extend(item for item in interior_matches if isinstance(item, dict))

    attribution_source = next((path / "ATTRIBUTION.txt" for _, path, _ in batches if (path / "ATTRIBUTION.txt").is_file()), None)
    if attribution_source is None:
        raise RuntimeError("No batch contains required attribution")

    manifest = dict(first)
    for key in ("tile_batch_offset", "tile_batch_count", "tile_batch_tile_ids", "source_elements_in_boundary_envelope"):
        manifest.pop(key, None)
    boundary_type = "ADM2" if stage == "shariatpur_review" else "ADM1"
    boundary_attribution = (
        f"Clipping boundary: {expected_boundary_name}; source: geoBoundaries "
        f"(https://www.geoboundaries.org), gbOpen BGD {boundary_type}. "
        "See manifest for the returned dataset license."
    )
    boundary_record = dict(manifest.get("administrative_boundary", {}))
    boundary_record.update({
        "name": expected_boundary_name,
        "source": f"geoBoundaries gbOpen BGD {boundary_type}",
        "attribution": boundary_attribution,
    })
    manifest["administrative_boundary"] = boundary_record
    # Shariatpur review packages must place the player and streamed tiles in the
    # district, not tens of kilometres away at the Greater Dhaka anchor. Full
    # division packages retain the established central-Dhaka world origin.
    region_bounds = manifest.get("region_south_west_north_east", [])
    if stage == "shariatpur_review" and isinstance(region_bounds, list) and len(region_bounds) == 4:
        south, west, north, east = (float(value) for value in region_bounds)
        manifest["game_origin_lat_lon"] = [(south + north) * 0.5, (west + east) * 0.5]
    else:
        manifest["game_origin_lat_lon"] = [23.8103, 90.4125]
    manifest.update({
        "product": (
            "Project A-Square — complete Shariatpur District boundary-clipped 3D map"
            if stage == "shariatpur_review"
            else "Project A-Square — complete Dhaka Division boundary-clipped 3D map"
        ),
        "complete_division_map": stage == "full_division",
        "complete_district_map": stage == "shariatpur_review",
        "tile_count_requested": total_tiles,
        "tile_count_intersecting_boundary": total_tiles,
        "tile_count_intersecting_division": division_total_tiles,
        "tile_count_intersecting_build_boundary": total_tiles,
        "tile_count_with_geometry": geometry_count,
        "feature_counts_across_tiles": feature_counts,
        "licensed_facade_photo_matches": facade_photo_matches,
        "licensed_facade_photo_panels_embedded": int(feature_counts.get("licensed_facade_photo_panels", 0)),
        "interior_reference_photo_matches": interior_reference_photo_matches,
        "interior_reference_photos_embedded": int(feature_counts.get("interior_reference_photos", 0)),
        "interior_reference_photo_note": "Interior reference photos are licensed, separate assets rendered only within the matching mapped building's generated in-game interior. They are not exterior textures or scans of the actual private interior.",
        "buildings_with_embedded_facade_photo_panel": int(feature_counts.get("licensed_facade_photo_panels", 0)),
        "source_elements_processed_across_batches": source_element_count,
        "map_build_batch_count": len(batches),
        "pipeline_commit_sha": pipeline_commit_sha,
        "tile_batch_offsets": [offset for offset, _, _ in batches],
        "tiles": all_records,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "completeness_note": (
            "All generated batches for every tile intersecting the Shariatpur District boundary "
            "are present. Tile geometry is clipped to the district polygon. This is geographic coverage, "
            "not proof that every real-world feature is mapped or that exteriors are photorealistic. "
            "OSM does not supply licensed facade photography, surveyed heights, actual private interiors, or real residents. Strict-name CC-licensed landmark photo panels may be embedded when downloaded and matched; they are not full photogrammetric exteriors."
            if stage == "shariatpur_review"
            else "All generated batches for every tile intersecting the Dhaka Division administrative boundary "
            "are present in this package. The map is based on mapped OpenStreetMap features and is not proof "
            "that every real-world feature is mapped. Facade photography, surveyed heights, actual interiors, "
            "and real residents are not supplied by OSM."
        ),
    })
    (out / "map_tiles_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    glbs = list(out.rglob("Dhaka_Explorable_Map.glb"))
    if len(glbs) != geometry_count:
        raise RuntimeError(f"Full package GLB count mismatch: manifest {geometry_count}, found {len(glbs)}")
    mesh_geometry_count = 0
    for glb_path in glbs:
        try:
            scene = trimesh.load(glb_path, force="scene")
        except Exception as exc:
            raise RuntimeError(f"Invalid GLB file {glb_path.relative_to(out)}: {exc}") from exc
        if not scene.geometry:
            raise RuntimeError(f"GLB contains no mesh geometry: {glb_path.relative_to(out)}")
        for geometry in scene.geometry.values():
            vertices = getattr(geometry, "vertices", None)
            if vertices is None or len(vertices) == 0 or not np.isfinite(vertices).all():
                raise RuntimeError(f"GLB contains empty or non-finite mesh data: {glb_path.relative_to(out)}")
            mesh_geometry_count += 1
    building_count = int(feature_counts.get("building_footprints", 0))
    inferred_height_count = int(feature_counts.get("buildings_with_inferred_height", 0))
    inferred_height_percent = round(100.0 * inferred_height_count / max(1, building_count), 2)
    ground_only_statuses = {
        "GROUND_ONLY_NO_RENDERABLE_FEATURES",
        "NO_MAPPED_FEATURES",
        "NO_MAPPED_ROADS_OR_BUILDINGS",
    }
    ground_only_tiles = [
        str(record.get("tile_id", "unknown"))
        for record in all_records
        if not record.get("glb") or record.get("status") in ground_only_statuses
    ]
    boundary_metadata = boundary_record.get("metadata", {})
    boundary_license = str(boundary_metadata.get("boundary_license", boundary_record.get("license", "See manifest")))
    boundary_license_source = str(boundary_metadata.get("boundary_license_source", "See manifest"))
    boundary_id = str(boundary_metadata.get("boundary_id", "unspecified"))
    attribution_text = (
        "© OpenStreetMap contributors — https://www.openstreetmap.org/copyright\n"
        + boundary_attribution + "\n"
        + "OSM data license: ODbL 1.0.\n"
        + f"Clipping boundary: {expected_boundary_name} (geoBoundaries gbOpen BGD {boundary_type}).\n"
        + f"Clipping boundary ID: {boundary_id}.\n"
        + f"Clipping boundary license: {boundary_license}. License source: {boundary_license_source}.\n"
    )
    seen_photo_attributions: set[str] = set()
    for match in interior_reference_photo_matches:
        attribution = str(match.get("attribution", "")).strip()
        license_name = str(match.get("license", "")).strip()
        license_url = str(match.get("license_url", "")).strip()
        entry = (
            f"{attribution}\nLicense: {license_name} — {license_url}\n"
            "Use restriction: INTERIOR REFERENCE ONLY; NOT AN EXTERIOR FACADE TEXTURE."
        )
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
    (out / "ATTRIBUTION.txt").write_text(attribution_text, encoding="utf-8")
    floor_evidence_source = pathlib.Path(__file__).resolve().with_name("shariatpur_floor_evidence.json")
    floor_evidence_package = out / "building_floor_evidence.json"
    if floor_evidence_source.is_file():
        shutil.copy2(floor_evidence_source, floor_evidence_package)
    navigation_index = build_index(out, floor_evidence_package if floor_evidence_package.is_file() else None)
    embedded_photo_by_osm_id = {
        "way/" + str(match.get("osm_id", "")): match
        for match in facade_photo_matches
        if str(match.get("osm_id", "")).strip()
    }
    embedded_building_count = 0
    for building in navigation_index.get("buildings", []):
        photo_match = embedded_photo_by_osm_id.get(str(building.get("osm_id", "")))
        if not isinstance(photo_match, dict):
            continue
        reference = building.setdefault("facade_reference", {})
        reference.update({
            "source_page": photo_match.get("source_page"),
            "author": photo_match.get("author"),
            "license": photo_match.get("license"),
            "license_url": photo_match.get("license_url"),
            "attribution": photo_match.get("attribution"),
            "status": "LICENSED_PHOTO_PANEL_EMBEDDED_REVIEW_REQUIRED",
            "visual_identity_verified": False,
        })
        embedded_building_count += 1
    navigation_index["counts"]["buildings_with_embedded_facade_photo_panel"] = embedded_building_count
    (out / "real_world_navigation_index.json").write_text(
        json.dumps(navigation_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    quality_report = {
        "build_stage": stage,
        "pipeline_commit_sha": pipeline_commit_sha,
        "status": "REVIEW_REQUIRED" if stage == "shariatpur_review" else "MAP_DATA_VALIDATED_VISUAL_QA_PENDING",
        "map_data_validation": "PASS",
        "checks": {
            "tile_offsets_contiguous": True,
            "tile_ids_unique": True,
            "administrative_boundary_consistent": True,
            "attribution_present": True,
            "glb_count_matches_manifest": True,
            "all_glbs_parse_and_contain_geometry": True,
            "mesh_geometry_count": mesh_geometry_count,
            "all_tiles_have_renderable_osm_features": len(ground_only_tiles) == 0,
            "ground_only_tiles_count": len(ground_only_tiles),
            "ground_only_tiles": ground_only_tiles,
            "photorealistic_facade_imagery_mapped": False,
            "licensed_facade_photo_panels_embedded": int(feature_counts.get("licensed_facade_photo_panels", 0)) > 0,
            "licensed_facade_photo_panel_count": int(feature_counts.get("licensed_facade_photo_panels", 0)),
            "interior_reference_photo_asset_count": int(feature_counts.get("interior_reference_photos", 0)),
            "interior_reference_photo_matches_manifest": len(interior_reference_photo_matches) == int(feature_counts.get("interior_reference_photos", 0)),
            "facade_photo_panel_visual_review_required": True,
            "physical_android_integration_verified": False,
            "all_building_heights_verified_or_surveyed": building_count > 0 and inferred_height_count == 0,
            "estimated_building_heights_count": inferred_height_count,
            "estimated_building_heights_percent": inferred_height_percent,
            "manual_visual_review_required": True,
            "navigation_index_written": (out / "real_world_navigation_index.json").is_file(),
            "named_road_count_in_source": navigation_index["counts"]["named_roads"],
            "unnamed_road_count_in_source": navigation_index["counts"]["unnamed_roads"],
            "buildings_with_source_floor_count": navigation_index["counts"]["buildings_with_source_floor_count"],
            "buildings_with_independently_verified_floor_count": navigation_index["counts"]["buildings_with_independently_verified_floor_count"],
            "buildings_missing_source_floor_count": navigation_index["counts"]["buildings_missing_source_floor_count"],
            "facade_references_requiring_license_review": navigation_index["counts"]["buildings_with_any_facade_reference"],
        "licensed_facade_photo_panels_embedded": int(feature_counts.get("licensed_facade_photo_panels", 0)),
        "licensed_facade_photo_match_records": len(facade_photo_matches),
        "facade_photo_panel_visual_review_required": True,
            "verified_facade_reference_count": navigation_index["counts"]["buildings_with_verified_facade_reference"],
        },
        "tiles_expected": total_tiles,
        "tiles_in_manifest": len(all_records),
        "tiles_with_geometry": len(glbs),
        "tile_coverage_percent": round(100.0 * len(all_records) / max(1, total_tiles), 2),
        "feature_counts": feature_counts,
        "note": "Tile coverage is geographic bookkeeping, not visual fidelity. Ground-only tiles prevent holes but still lack mapped OSM detail. The package is not final until licensed imagery, visual inspection, and canonical Android integration pass.",
    }
    (out / "quality_gate_report.json").write_text(
        json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "output": str(out),
        "complete_division_map": stage == "full_division",
        "complete_district_map": stage == "shariatpur_review",
        "tile_count_intersecting_boundary": total_tiles,
        "tile_count_intersecting_division": division_total_tiles,
        "tile_count_with_geometry": len(glbs),
        "mesh_geometry_count": mesh_geometry_count,
        "feature_counts": feature_counts,
        "quality_gate_status": quality_report["status"],
        "navigation_index_counts": navigation_index["counts"],
        "batch_count": len(batches),
        "glb_bytes": sum(path.stat().st_size for path in glbs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches-dir", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--stage", choices=("shariatpur_review", "full_division"), default="full_division")
    args = parser.parse_args()
    print(json.dumps(merge_batches(args.batches_dir, args.out, args.stage), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
