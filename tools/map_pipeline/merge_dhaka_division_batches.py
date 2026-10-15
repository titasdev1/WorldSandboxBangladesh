#!/usr/bin/env python3
"""Validate and merge bounded Dhaka Division map batches into one tile package."""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import shutil
from typing import Any


def merge_batches(batches_dir: pathlib.Path, out: pathlib.Path) -> dict[str, Any]:
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
        total = int(manifest.get("tile_count_intersecting_boundary", -1))
        if offset < 0 or count < 1 or total < 1:
            raise RuntimeError(f"Batch {path.name} has invalid offset/count/total metadata")
        if int(path.name) != offset:
            raise RuntimeError(f"Batch folder {path.name} does not match manifest offset {offset}")
        if len(manifest.get("tiles", [])) != count:
            raise RuntimeError(f"Batch {path.name} manifest tile list/count mismatch")
        batches.append((offset, path, manifest))

    batches.sort(key=lambda item: item[0])
    first = batches[0][2]
    total_tiles = int(first["tile_count_intersecting_boundary"])
    tile_degrees = float(first["tile_edge_degrees"])
    boundary_name = first.get("administrative_boundary", {}).get("name")
    expected_offset = 0
    all_records: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    geometry_count = 0
    source_element_count = 0

    for offset, path, manifest in batches:
        if int(manifest["tile_count_intersecting_boundary"]) != total_tiles:
            raise RuntimeError("Batches disagree on the total number of division-intersecting tiles")
        if float(manifest["tile_edge_degrees"]) != tile_degrees:
            raise RuntimeError("Batches use different tile sizes; refusing to merge incompatible grids")
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
        expected_offset += int(manifest["tile_batch_count"])
        geometry_count += int(manifest.get("tile_count_with_geometry", 0))
        source_element_count += int(manifest.get("source_elements_in_boundary_envelope", 0))

    if expected_offset != total_tiles or len(all_records) != total_tiles:
        raise RuntimeError(
            f"Incomplete division coverage: merged {len(all_records)} of {total_tiles} expected tiles"
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

    attribution_source = next((path / "ATTRIBUTION.txt" for _, path, _ in batches if (path / "ATTRIBUTION.txt").is_file()), None)
    if attribution_source is None:
        raise RuntimeError("No batch contains required attribution")
    shutil.copy2(attribution_source, out / "ATTRIBUTION.txt")

    manifest = dict(first)
    for key in ("tile_batch_offset", "tile_batch_count", "tile_batch_tile_ids"):
        manifest.pop(key, None)
    manifest.update({
        "product": "Project A-Square — complete Dhaka Division boundary-clipped 3D map",
        "complete_division_map": True,
        "tile_count_requested": total_tiles,
        "tile_count_intersecting_boundary": total_tiles,
        "tile_count_with_geometry": geometry_count,
        "source_elements_in_boundary_envelope": source_element_count,
        "tile_batch_count": len(batches),
        "tile_batch_offsets": [offset for offset, _, _ in batches],
        "tiles": all_records,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "completeness_note": (
            "All generated batches for every tile intersecting the Dhaka Division administrative boundary "
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
    return {
        "output": str(out),
        "complete_division_map": True,
        "tile_count_intersecting_boundary": total_tiles,
        "tile_count_with_geometry": len(glbs),
        "batch_count": len(batches),
        "glb_bytes": sum(path.stat().st_size for path in glbs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches-dir", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(merge_batches(args.batches_dir, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
