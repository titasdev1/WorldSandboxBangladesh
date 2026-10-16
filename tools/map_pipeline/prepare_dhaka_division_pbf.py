#!/usr/bin/env python3
"""Prepare a reusable, tag-filtered OSM PBF for Dhaka Division tile builds.

The Bangladesh-wide source is downloaded once, clipped to the Dhaka Division
envelope, then filtered to mapped feature classes used by the GLB builder.
The cached output retains way-reference nodes, so each small tile batch scans
far fewer irrelevant OSM objects. Final geometry is still clipped to the true
administrative polygon in build_dhaka_division.py.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.map_pipeline.build_dhaka_division import PBF_URL, download, load_dhaka_boundary

# Keep aligned with INTERESTING_KEYS in build_dhaka_division.py. nwr selectors
# preserve tagged nodes/ways/relations; osmium tags-filter also retains nodes
# referenced by selected ways unless the -R option is explicitly supplied.
FEATURE_KEYS = (
    "building", "highway", "shop", "amenity", "tourism", "historic",
    "leisure", "office", "healthcare", "public_transport", "landuse",
    "natural", "waterway", "railway", "man_made", "power",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pbf", type=pathlib.Path,
                        default=pathlib.Path("build/osm/bangladesh-latest.osm.pbf"))
    parser.add_argument("--boundary", type=pathlib.Path,
                        default=pathlib.Path("build/boundaries/dhaka-division.geojson"))
    parser.add_argument("--out", type=pathlib.Path,
                        default=pathlib.Path("build/osm/dhaka-division-envelope.osm.pbf"))
    args = parser.parse_args()

    osmium = shutil.which("osmium")
    if not osmium:
        raise SystemExit("Missing osmium-tool executable. Install osmium-tool before preparing the regional PBF.")

    boundary, metadata = load_dhaka_boundary(args.boundary)
    min_lon, min_lat, max_lon, max_lat = boundary.bounds
    download(PBF_URL, args.source_pbf, 100_000_000)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    regional = args.out.with_name(args.out.stem + ".regional" + args.out.suffix)
    filtered = args.out.with_name(args.out.stem + ".filtered" + args.out.suffix)
    for path in (regional, filtered, args.out):
        path.unlink(missing_ok=True)

    bbox = f"{min_lon:.8f},{min_lat:.8f},{max_lon:.8f},{max_lat:.8f}"
    extract_command = [
        osmium, "extract", "--bbox", bbox, "--strategy", "smart", "--overwrite",
        str(args.source_pbf), "-o", str(regional),
    ]
    filter_command = [
        osmium, "tags-filter", str(regional),
        *(f"nwr/{key}" for key in FEATURE_KEYS),
        "--overwrite", "-o", str(filtered),
    ]
    print("Preparing reusable Dhaka Division OSM extract, then filtering to game-relevant tags.", flush=True)
    print(json.dumps({
        "source_pbf": str(args.source_pbf),
        "source_pbf_bytes": args.source_pbf.stat().st_size,
        "division_bbox_west_south_east_north": [min_lon, min_lat, max_lon, max_lat],
        "output_pbf": str(args.out),
        "boundary_properties": metadata.get("feature_properties", {}),
        "extract_command": extract_command,
        "tag_filter_command": filter_command,
        "feature_keys": FEATURE_KEYS,
    }, ensure_ascii=False, indent=2), flush=True)

    subprocess.run(extract_command, check=True)
    if not regional.is_file() or regional.stat().st_size < 10_000_000:
        raise RuntimeError("Regional OSM PBF is missing or unexpectedly small; refusing to filter an incomplete extract.")
    subprocess.run(filter_command, check=True)
    if not filtered.is_file() or filtered.stat().st_size < 1_000_000:
        raise RuntimeError("Filtered OSM PBF is missing or unexpectedly small; refusing to cache an incomplete extract.")
    filtered.replace(args.out)
    regional_bytes = regional.stat().st_size
    regional.unlink(missing_ok=True)
    print(json.dumps({
        "status": "prepared_and_filtered",
        "output": str(args.out),
        "output_bytes": args.out.stat().st_size,
        "regional_extract_bytes": regional_bytes,
        "filtered_vs_regional_ratio": round(args.out.stat().st_size / regional_bytes, 4),
        "source_vs_filtered_ratio": round(args.out.stat().st_size / args.source_pbf.stat().st_size, 4),
        "division_bbox_west_south_east_north": [min_lon, min_lat, max_lon, max_lat],
        "filtered_keys": FEATURE_KEYS,
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
