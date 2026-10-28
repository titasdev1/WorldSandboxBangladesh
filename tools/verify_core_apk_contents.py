#!/usr/bin/env python3
"""Fail unless the final core APK is modular and does not embed the district map."""
from __future__ import annotations

import argparse
import pathlib
import zipfile

MAP_PREFIX = "assets/assets/world/dhaka_tiles/"
IMPORTED_MAP_PREFIX = "assets/.godot/imported/Dhaka_Explorable_Map.glb-"
FLAG_PATH = "assets/assets/world/external_map_pack_required.flag"
REQUIRED_CORE_ASSETS = (
    "assets/external_content/kenney_car_kit/asset_manifest.json",
    "assets/external_content/kenney_city_kit_commercial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_industrial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_suburban/asset_manifest.json",
    "assets/external_content/polyhaven_pbr/asset_manifest.json",
    "assets/external_content/quaternius_hero/asset_manifest.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=pathlib.Path)
    parser.add_argument("--max-bytes", type=int, default=1_000_000_000)
    args = parser.parse_args()
    apk_path = args.apk
    if not apk_path.is_file():
        raise SystemExit(f"CORE APK GATE FAILED: missing APK: {apk_path}")
    size = apk_path.stat().st_size
    if size > args.max_bytes:
        raise SystemExit(f"CORE APK GATE FAILED: APK is {size:,} bytes; map resources are still bloating the core package (limit {args.max_bytes:,}).")
    try:
        with zipfile.ZipFile(apk_path) as apk:
            names = set(apk.namelist())
            missing = [name for name in (FLAG_PATH, *REQUIRED_CORE_ASSETS) if name not in names]
            if missing:
                raise SystemExit("CORE APK GATE FAILED: missing core/pack-management resources: " + ", ".join(missing))
            flag = apk.read(FLAG_PATH).decode("utf-8", errors="replace")
            if "map pack" not in flag.lower():
                raise SystemExit("CORE APK GATE FAILED: external map-pack marker has unexpected contents.")
            map_entries = sorted(name for name in names if name.startswith(MAP_PREFIX))
            if map_entries:
                raise SystemExit(f"CORE APK GATE FAILED: {len(map_entries)} bundled district-map entries remain; sample: {map_entries[:5]}")
            imported_map_entries = sorted(name for name in names if name.startswith(IMPORTED_MAP_PREFIX))
            if imported_map_entries:
                raise SystemExit(f"CORE APK GATE FAILED: {len(imported_map_entries)} imported GLB map resources remain; sample: {imported_map_entries[:5]}")
            if any(name.endswith(".geojson") for name in names):
                raise SystemExit("CORE APK GATE FAILED: raw map GeoJSON remains embedded in the core APK.")
            print("Core APK modularity: PASS")
            print(f"APK: {apk_path.name} ({size:,} bytes)")
            print(f"District-map resources bundled in core APK: {len(map_entries)}")
            print(f"Imported district GLB scenes bundled in core APK: {len(imported_map_entries)}")
            print(f"Core/hero manifests present: {len(REQUIRED_CORE_ASSETS)}/{len(REQUIRED_CORE_ASSETS)}")
            print("Map detail is kept in a separately verified PCK; this gate does not claim phone-device launch is proven.")
    except (OSError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"CORE APK GATE FAILED: cannot inspect APK: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
