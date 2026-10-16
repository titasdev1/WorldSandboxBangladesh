#!/usr/bin/env python3
"""Validate one map-batch artifact and safely deduplicate repeated batch offsets.

The workflow may see multiple successful artifact uploads for the same sequence
and offset (for example, a retried or manually repeated dispatch).  Never merge
those directories by overlaying their files: only accept a duplicate when its
stable tile outputs and provenance are identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any


BOUNDARY_BY_STAGE = {
    "shariatpur_review": "Shariatpur District",
    "full_division": "Dhaka Division",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(root: Path, relative: Any, tile_id: str, required: bool) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        if required:
            raise ValueError(f"Tile {tile_id} is missing a required artifact path")
        return None
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError(f"Unsafe artifact path for tile {tile_id}: {relative}")
    path = root.joinpath(*posix.parts)
    if not path.is_file():
        if required:
            raise ValueError(f"Tile {tile_id} references missing file: {relative}")
        return None
    return path


def validate_batch(
    root: Path,
    expected_offset: int,
    expected_stage: str,
    expected_source_commit: str = "",
) -> tuple[dict[str, Any], str]:
    manifest_path = root / "map_tiles_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"{root} has no map_tiles_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    stage = str(manifest.get("build_stage", ""))
    if stage != expected_stage:
        raise ValueError(f"Batch stage mismatch: expected {expected_stage}, found {stage!r}")
    if stage not in BOUNDARY_BY_STAGE:
        raise ValueError(f"Unsupported batch stage: {stage!r}")
    offset = int(manifest.get("tile_batch_offset", -1))
    if offset != expected_offset:
        raise ValueError(f"Batch offset mismatch: expected {expected_offset}, found {offset}")
    source_commit = str(manifest.get("pipeline_commit_sha", "")).strip()
    if not source_commit:
        raise ValueError("Batch is missing pipeline_commit_sha")
    if expected_source_commit and source_commit != expected_source_commit:
        raise ValueError(
            "Batch pipeline_commit_sha does not match the sequence's pinned source commit"
        )
    boundary = manifest.get("administrative_boundary", {})
    if boundary.get("name") != BOUNDARY_BY_STAGE[stage]:
        raise ValueError(
            f"Wrong administrative boundary for {stage}: {boundary.get('name')!r}"
        )
    if not (root / "ATTRIBUTION.txt").is_file():
        raise ValueError("Batch is missing required ATTRIBUTION.txt")

    records = manifest.get("tiles")
    if not isinstance(records, list) or not records:
        raise ValueError("Batch manifest has no tile records")
    count = int(manifest.get("tile_batch_count", -1))
    if count != len(records):
        raise ValueError(f"Batch manifest count mismatch: count={count}, records={len(records)}")
    ids = [str(record.get("tile_id", "")).strip() for record in records]
    if any(not tile_id for tile_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("Batch contains missing or duplicate tile IDs")
    declared_ids = manifest.get("tile_batch_tile_ids")
    if declared_ids is not None and list(declared_ids) != ids:
        raise ValueError("tile_batch_tile_ids does not match manifest tile order")

    total_key = (
        "tile_count_intersecting_build_boundary"
        if stage == "shariatpur_review"
        else "tile_count_intersecting_boundary"
    )
    total = int(manifest.get(total_key, -1))
    if total < 1 or offset + count > total:
        raise ValueError(f"Invalid batch range: offset={offset}, count={count}, total={total}")
    if int(manifest.get("tile_count_intersecting_division", -1)) < 1:
        raise ValueError("Batch lacks a valid Dhaka Division tile total")

    actual_glbs = list(root.rglob("Dhaka_Explorable_Map.glb"))
    expected_glbs = int(manifest.get("tile_count_with_geometry", -1))
    if len(actual_glbs) != expected_glbs:
        raise ValueError(
            f"Batch GLB count mismatch: manifest={expected_glbs}, actual={len(actual_glbs)}"
        )

    stable = {
        "build_stage": stage,
        "pipeline_commit_sha": source_commit,
        "tile_edge_degrees": manifest.get("tile_edge_degrees"),
        "tile_batch_offset": offset,
        "tile_batch_count": count,
        "tile_count_intersecting_boundary": manifest.get("tile_count_intersecting_boundary"),
        "tile_count_intersecting_build_boundary": manifest.get("tile_count_intersecting_build_boundary"),
        "tile_count_intersecting_division": manifest.get("tile_count_intersecting_division"),
        "tile_count_with_geometry": expected_glbs,
        "boundary_name": boundary.get("name"),
        "boundary_id": boundary.get("metadata", {}).get("boundary_id"),
        "source_elements_in_boundary_envelope": manifest.get("source_elements_in_boundary_envelope"),
        "attribution_sha256": _sha256(root / "ATTRIBUTION.txt"),
        "tiles": [],
    }
    for record in records:
        tile_id = str(record["tile_id"])
        glb = _safe_file(root, record.get("glb"), tile_id, True)
        geojson = _safe_file(root, record.get("geojson"), tile_id, True)
        seeds = _safe_file(root, record.get("interior_seeds"), tile_id, False)
        stable["tiles"].append({
            "tile_id": tile_id,
            "bbox": record.get("bbox_south_west_north_east"),
            "origin": record.get("origin_lat_lon"),
            "status": record.get("status"),
            "feature_counts": record.get("feature_counts", {}),
            "glb_sha256": _sha256(glb) if glb else None,
            "geojson_sha256": _sha256(geojson) if geojson else None,
            "interior_seeds_sha256": _sha256(seeds) if seeds else None,
        })

    fingerprint = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return manifest, fingerprint


def accept_batch(
    candidate: Path,
    destination: Path,
    expected_offset: int,
    expected_stage: str,
    expected_source_commit: str = "",
) -> str:
    _, candidate_fingerprint = validate_batch(
        candidate, expected_offset, expected_stage, expected_source_commit
    )
    if destination.exists():
        _, existing_fingerprint = validate_batch(
            destination, expected_offset, expected_stage, expected_source_commit
        )
        if existing_fingerprint != candidate_fingerprint:
            raise ValueError(
                f"Conflicting artifacts for batch offset {expected_offset}; "
                "tile outputs or provenance differ. Refusing to assemble a mixed sequence."
            )
        shutil.rmtree(destination)
        shutil.copytree(candidate, destination)
        return "identical duplicate accepted; newest candidate selected"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, destination)
    return "batch accepted"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-offset", type=int, required=True)
    parser.add_argument(
        "--expected-stage", choices=tuple(BOUNDARY_BY_STAGE), required=True
    )
    parser.add_argument("--expected-source-commit", default="")
    args = parser.parse_args()
    print(accept_batch(
        args.candidate.resolve(),
        args.destination.resolve(),
        args.expected_offset,
        args.expected_stage,
        args.expected_source_commit.strip(),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
