#!/usr/bin/env python3
"""Verify that the selected world-map resources and core art packs are inside the exported APK.

An APK ZIP-integrity test alone does not prove that the game/map assets were exported.
This check inspects the Android APK's actual asset table and fails the build if the
selected district's tile scenes, manifests, navigation index, or core asset manifests
are missing.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import zipfile


MAP_ROOT = "assets/assets/world/dhaka_tiles/"
IMPORTED_ROOT = "assets/.godot/imported/"
REQUIRED_ASSET_MANIFESTS = (
    "assets/external_content/kenney_car_kit/asset_manifest.json",
    "assets/external_content/kenney_city_kit_commercial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_industrial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_suburban/asset_manifest.json",
    "assets/external_content/polyhaven_pbr/asset_manifest.json",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True, type=pathlib.Path)
    parser.add_argument("--map-package", required=True, choices=("greater_dhaka", "shariatpur_review"))
    args = parser.parse_args()

    if not args.apk.is_file():
        raise SystemExit(f"APK CONTENT GATE FAILED: APK does not exist: {args.apk}")

    try:
        with zipfile.ZipFile(args.apk) as apk:
            names = set(apk.namelist())
            manifest_path = MAP_ROOT + "map_tiles_manifest.json"
            navigation_path = MAP_ROOT + "real_world_navigation_index.json"
            missing = [p for p in (manifest_path, navigation_path) if p not in names]
            if missing:
                raise SystemExit("APK CONTENT GATE FAILED: missing map resources: " + ", ".join(missing))

            manifest = json.loads(apk.read(manifest_path).decode("utf-8"))
            navigation = json.loads(apk.read(navigation_path).decode("utf-8"))
            tiles = manifest.get("tiles", [])
            expected = int(manifest.get("tile_count_with_geometry", 0))
            if not isinstance(tiles, list) or expected < 1 or len(tiles) != int(manifest.get("tile_count_total", len(tiles))):
                raise SystemExit("APK CONTENT GATE FAILED: tile manifest is empty or internally inconsistent")
            if len(tiles) != 60:
                raise SystemExit(f"APK CONTENT GATE FAILED: expected current 60-tile district package, found {len(tiles)} tile records")
            if args.map_package == "shariatpur_review":
                if manifest.get("build_stage") != "shariatpur_review" or not manifest.get("complete_district_map"):
                    raise SystemExit("APK CONTENT GATE FAILED: APK does not contain the selected Shariatpur review district package")

            tile_manifests = [p for p in names if p.startswith(MAP_ROOT) and p.endswith("/map_manifest.json")]
            tile_glb_imports = [p for p in names if p.startswith(MAP_ROOT) and p.endswith("/Dhaka_Explorable_Map.glb.import")]
            imported_scenes = [p for p in names if p.startswith(IMPORTED_ROOT) and p.rsplit("/", 1)[-1].startswith("Dhaka_Explorable_Map.glb-") and p.endswith(".scn")]
            if len(tile_manifests) != len(tiles):
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(tile_manifests)} tile manifests embedded for {len(tiles)} tile records")
            if len(tile_glb_imports) != expected:
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(tile_glb_imports)} GLB import remaps embedded; manifest expects {expected}")
            if len(imported_scenes) != expected:
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(imported_scenes)} imported GLB scenes embedded; manifest expects {expected}")

            missing_art = [p for p in REQUIRED_ASSET_MANIFESTS if p not in names]
            if missing_art:
                raise SystemExit("APK CONTENT GATE FAILED: art pack manifests absent from APK: " + ", ".join(missing_art))

            counts = navigation.get("counts", {})
            named_places = int(counts.get("named_places", 0))
            named_roads = int(counts.get("named_roads", 0))
            if named_places < 1 or named_roads < 1:
                raise SystemExit("APK CONTENT GATE FAILED: packaged navigation index has no named places or named roads")

            verified_floors = int(counts.get("buildings_with_independently_verified_floor_count", 0))
            source_floors = int(counts.get("buildings_with_source_floor_count", 0))
            lines = [
                "APK content integration: PASS",
                f"APK: {args.apk.name} ({args.apk.stat().st_size:,} bytes)",
                f"Selected map package: {args.map_package}",
                f"Tile records/manifests: {len(tiles)}/{len(tile_manifests)}",
                f"GLB import remaps: {len(tile_glb_imports)}/{expected}",
                f"Imported GLB scenes: {len(imported_scenes)}/{expected}",
                f"Named places in packaged navigation index: {named_places}",
                f"Named roads in packaged navigation index: {named_roads}",
                f"Buildings with source floor counts: {source_floors}",
                f"Independently verified floor counts: {verified_floors}",
                f"Core art pack manifests present: {len(REQUIRED_ASSET_MANIFESTS)}/{len(REQUIRED_ASSET_MANIFESTS)}",
                "Limit: archive presence is not proof of correct in-game rendering or physical-device performance.",
            ]
            output = "\n".join(lines) + "\n"
            print(output, end="")
            report_path = pathlib.Path("build/apk-content-verification.txt")
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(output, encoding="utf-8")
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SystemExit(f"APK CONTENT GATE FAILED: could not inspect APK contents: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
