#!/usr/bin/env python3
"""Prepare a reusable OSM PBF extract for bounded Dhaka Division tile builds.

The expensive Bangladesh-wide PBF download/extract happens once per pinned
cache version. Subsequent tile batches scan only the Dhaka Division envelope.
The tile builder still clips final features and terrain to the actual division
polygon; this rectangular extract is an input optimization, not map geometry.
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
    args.out.unlink(missing_ok=True)
    bbox = f"{min_lon:.8f},{min_lat:.8f},{max_lon:.8f},{max_lat:.8f}"
    command = [
        osmium, "extract", "--bbox", bbox, "--strategy", "smart", "--overwrite",
        str(args.source_pbf), "-o", str(args.out),
    ]
    print("Preparing reusable Dhaka Division OSM extract.", flush=True)
    print(json.dumps({
        "source_pbf": str(args.source_pbf),
        "source_pbf_bytes": args.source_pbf.stat().st_size,
        "division_bbox_west_south_east_north": [min_lon, min_lat, max_lon, max_lat],
        "output_pbf": str(args.out),
        "boundary_properties": metadata.get("feature_properties", {}),
        "command": command,
    }, ensure_ascii=False, indent=2), flush=True)
    subprocess.run(command, check=True)
    if not args.out.is_file() or args.out.stat().st_size < 10_000_000:
        raise RuntimeError("Regional OSM PBF is missing or unexpectedly small; refusing to cache an incomplete extract.")
    print(json.dumps({
        "status": "prepared",
        "output": str(args.out),
        "output_bytes": args.out.stat().st_size,
        "reduction_ratio": round(args.out.stat().st_size / args.source_pbf.stat().st_size, 4),
        "division_bbox_west_south_east_north": [min_lon, min_lat, max_lon, max_lat],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
