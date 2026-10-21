#!/usr/bin/env python3
"""Verify that the selected world-map resources and core art packs are inside the exported APK.

An APK ZIP-integrity test alone does not prove that the game/map assets were exported.
This check inspects the Android APK's actual asset table and fails the build if the
selected district's tile scenes, manifests, navigation index, or core asset manifests
are missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from pathlib import PurePosixPath
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
    "assets/external_content/quaternius_hero/asset_manifest.json",
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

            # Check the explicit licensed interior reference photo actually ships
            # inside the selected tile, matches its checksum, and is linked to an
            # interior seed. This prevents ZIP metadata passing while the runtime
            # lacks the asset or a photo is accidentally reused as a facade panel.
            interior_matches = manifest.get("interior_reference_photo_matches", [])
            if args.map_package == "shariatpur_review" and not interior_matches:
                raise SystemExit("APK CONTENT GATE FAILED: current Shariatpur package has no verified interior reference photo.")
            facade_ids = {
                str(item.get("image_id", ""))
                for item in manifest.get("licensed_facade_photo_matches", [])
                if isinstance(item, dict)
            }
            verified_interior_photos = 0
            for match in interior_matches:
                if not isinstance(match, dict):
                    raise SystemExit("APK CONTENT GATE FAILED: malformed interior-reference match record.")
                if str(match.get("use", "")) != "INTERIOR_REFERENCE_ONLY":
                    raise SystemExit("APK CONTENT GATE FAILED: an interior image lacks the strict interior-only restriction.")
                image_id = str(match.get("image_id", ""))
                license_name = str(match.get("license", ""))
                if not image_id or license_name not in {"CC BY 4.0", "CC BY-SA 4.0"}:
                    raise SystemExit("APK CONTENT GATE FAILED: interior reference photo has missing identity or an unapproved license.")
                if image_id in facade_ids:
                    raise SystemExit("APK CONTENT GATE FAILED: an interior photo is also listed as an exterior facade photo.")
                tile_id = str(match.get("tile_id", ""))
                relative = PurePosixPath(str(match.get("asset_relative_path", "")))
                if (not tile_id or relative.is_absolute() or not relative.parts or
                        any(part in {"", ".", ".."} for part in relative.parts)):
                    raise SystemExit("APK CONTENT GATE FAILED: unsafe or missing interior photo asset path.")
                photo_path = MAP_ROOT + tile_id + "/" + relative.as_posix()
                if photo_path not in names:
                    raise SystemExit(f"APK CONTENT GATE FAILED: licensed interior photo asset missing from APK: {photo_path}")
                photo_data = apk.read(photo_path)
                expected_hash = str(match.get("sha256", "")).strip().lower()
                actual_hash = hashlib.sha256(photo_data).hexdigest()
                if len(expected_hash) != 64 or actual_hash != expected_hash:
                    raise SystemExit(f"APK CONTENT GATE FAILED: licensed interior photo checksum mismatch: {photo_path}")
                seed_path = MAP_ROOT + tile_id + "/AI_Interior_Seeds.json"
                if seed_path not in names:
                    raise SystemExit(f"APK CONTENT GATE FAILED: matching tile has no interior seeds file: {seed_path}")
                seeds = json.loads(apk.read(seed_path).decode("utf-8"))
                matching_seed = next(
                    (seed for seed in seeds if isinstance(seed, dict)
                     and str(seed.get("osm_id", "")) == str(match.get("osm_id", ""))),
                    None,
                ) if isinstance(seeds, list) else None
                photo_seed = matching_seed.get("interior_reference_photo", {}) if isinstance(matching_seed, dict) else {}
                if not isinstance(photo_seed, dict) or str(photo_seed.get("image_id", "")) != image_id:
                    raise SystemExit("APK CONTENT GATE FAILED: licensed photo asset is not connected to its exact mapped building's runtime interior seed.")
                if str(photo_seed.get("use", "")) != "INTERIOR_REFERENCE_ONLY" or str(photo_seed.get("asset_relative_path", "")) != relative.as_posix():
                    raise SystemExit("APK CONTENT GATE FAILED: interior seed does not constrain the image to the intended runtime interior.")
                verified_interior_photos += 1
            if int(manifest.get("interior_reference_photos_embedded", 0)) != verified_interior_photos:
                raise SystemExit("APK CONTENT GATE FAILED: interior photo match count disagrees with verified packaged assets.")

            tile_manifests = [p for p in names if p.startswith(MAP_ROOT) and p.endswith("/map_manifest.json")]
            tile_glb_imports = [p for p in names if p.startswith(MAP_ROOT) and p.endswith("/Dhaka_Explorable_Map.glb.import")]
            imported_scenes = [p for p in names if p.startswith(IMPORTED_ROOT) and p.rsplit("/", 1)[-1].startswith("Dhaka_Explorable_Map.glb-") and p.endswith(".scn")]
            if len(tile_manifests) != len(tiles):
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(tile_manifests)} tile manifests embedded for {len(tiles)} tile records")
            if len(tile_glb_imports) != expected:
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(tile_glb_imports)} GLB import remaps embedded; manifest expects {expected}")
            if len(imported_scenes) != expected:
                raise SystemExit(f"APK CONTENT GATE FAILED: {len(imported_scenes)} imported GLB scenes embedded; manifest expects {expected}")

            # Verify licensed exterior panels against the APK's actual tile
            # manifests and GLB files. The merged summary alone is not sufficient:
            # every currently approved Shariatpur landmark photo must be present,
            # mapped to a specific feature ID, and shipped in that tile's GLB.
            facade_matches = manifest.get("licensed_facade_photo_matches", [])
            if not isinstance(facade_matches, list):
                raise SystemExit("APK CONTENT GATE FAILED: exterior photo match index is malformed.")
            declared_panel_count = int(manifest.get("licensed_facade_photo_panels_embedded", 0))
            facade_image_ids = {
                str(item.get("image_id", "")).strip()
                for item in facade_matches if isinstance(item, dict)
                and str(item.get("image_id", "")).strip()
            }
            if args.map_package == "shariatpur_review":
                required_facade_ids = {
                    str(value).strip()
                    for value in manifest.get("approved_facade_photo_ids_required", [])
                    if str(value).strip()
                }
                declared_embedded_ids = {
                    str(value).strip()
                    for value in manifest.get("approved_facade_photo_ids_embedded", [])
                    if str(value).strip()
                }
                if not required_facade_ids:
                    raise SystemExit("APK CONTENT GATE FAILED: Shariatpur manifest has no required approved exterior-photo ID list.")
                if not required_facade_ids.issubset(facade_image_ids) or not required_facade_ids.issubset(declared_embedded_ids):
                    missing_facades = sorted(required_facade_ids - facade_image_ids)
                    raise SystemExit("APK CONTENT GATE FAILED: approved Shariatpur exterior photo coverage is incomplete: " + ", ".join(missing_facades))
                if declared_embedded_ids != facade_image_ids:
                    raise SystemExit("APK CONTENT GATE FAILED: embedded exterior-photo IDs disagree with exact-building match records.")
                if declared_panel_count < len(required_facade_ids) or declared_panel_count != len(facade_matches):
                    raise SystemExit("APK CONTENT GATE FAILED: exterior photo panel count disagrees with packaged attribution records.")
                required_photo_fields = ("image_id", "osm_id", "source_page", "author", "license", "license_url", "attribution")
                malformed_facades = [
                    item for item in facade_matches
                    if not isinstance(item, dict)
                    or any(not str(item.get(field, "")).strip() for field in required_photo_fields)
                    or str(item.get("license", "")).strip() not in {"CC BY 4.0", "CC BY-SA 4.0"}
                ]
                if malformed_facades:
                    raise SystemExit("APK CONTENT GATE FAILED: an exterior panel lacks exact building identity or valid open-license attribution.")

                tile_photo_matches: dict[tuple[str, str], str] = {}
                for tile_manifest_path in tile_manifests:
                    tile_data = json.loads(apk.read(tile_manifest_path).decode("utf-8"))
                    tile_dir = str(PurePosixPath(tile_manifest_path).parent)
                    tile_id = PurePosixPath(tile_manifest_path).parent.name
                    tile_matches = tile_data.get("licensed_facade_photo_matches", [])
                    tile_counts = tile_data.get("feature_counts", {})
                    if not isinstance(tile_matches, list) or not isinstance(tile_counts, dict):
                        raise SystemExit(f"APK CONTENT GATE FAILED: malformed map/photo manifest in tile {tile_id}.")
                    if int(tile_counts.get("licensed_facade_photo_panels", 0)) < len(tile_matches):
                        raise SystemExit(f"APK CONTENT GATE FAILED: tile {tile_id} reports fewer baked photo panels than attribution records.")
                    for tile_match in tile_matches:
                        if not isinstance(tile_match, dict):
                            continue
                        pair = (str(tile_match.get("image_id", "")).strip(), str(tile_match.get("osm_id", "")).strip())
                        tile_photo_matches[pair] = tile_dir

                for photo_match in facade_matches:
                    pair = (str(photo_match.get("image_id", "")).strip(), str(photo_match.get("osm_id", "")).strip())
                    tile_dir = tile_photo_matches.get(pair, "")
                    if not tile_dir:
                        raise SystemExit(f"APK CONTENT GATE FAILED: photo {pair[0]} is absent from all packaged tile-level match manifests.")
                    glb_path = tile_dir + "/Dhaka_Explorable_Map.glb"
                    if glb_path not in names or glb_path + ".import" not in names:
                        raise SystemExit(f"APK CONTENT GATE FAILED: tile-specific GLB/remap missing for licensed exterior photo {pair[0]}.")

            missing_art = [p for p in REQUIRED_ASSET_MANIFESTS if p not in names]
            if missing_art:
                raise SystemExit("APK CONTENT GATE FAILED: art pack manifests absent from APK: " + ", ".join(missing_art))

            # When CI successfully assembles the authored player, prove that the
            # exact licensed GLB bytes, Godot import remap and imported scene are in
            # the candidate APK. A ZIP containing the source archive alone is not enough.
            hero_manifest_path = "assets/external_content/quaternius_hero/asset_manifest.json"
            hero_manifest = json.loads(apk.read(hero_manifest_path).decode("utf-8"))
            hero_available = hero_manifest.get("available") is True
            hero_imported_scene_count = 0
            if hero_available:
                hero_resource_path = "assets/external_content/quaternius_hero/Project_A_Square_Hero.glb"
                hero_import_meta_path = hero_resource_path + ".import"
                if hero_resource_path not in names:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero GLB resource is absent from the APK.")
                hero_data = apk.read(hero_resource_path)
                hero_sha = hashlib.sha256(hero_data).hexdigest()
                if hero_sha != str(hero_manifest.get("hero_glb_sha256", "")).lower():
                    raise SystemExit("APK CONTENT GATE FAILED: packaged hero GLB checksum does not match its build manifest.")
                if hero_import_meta_path not in names:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero is present as a file but lacks its Godot import remap.")
                hero_scenes = [
                    path for path in names
                    if path.startswith(IMPORTED_ROOT)
                    and path.rsplit("/", 1)[-1].startswith("Project_A_Square_Hero.glb-")
                    and path.endswith(".scn")
                ]
                hero_imported_scene_count = len(hero_scenes)
                if hero_imported_scene_count < 1:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero GLB was not imported into a scene used by Godot.")
                if int(hero_manifest.get("animation_count", 0)) < 30:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero manifest reports fewer than 30 merged animation clips.")

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
                f"Licensed exterior façade panels in packaged manifest: {declared_panel_count}",
                f"Approved exterior photo IDs present: {len(required_facade_ids & facade_image_ids)}/{len(required_facade_ids)}" if args.map_package == "shariatpur_review" else "Approved Shariatpur photo coverage: not applicable",
                f"Interior reference photo assets SHA-256 verified and linked to runtime seeds: {verified_interior_photos}/{len(interior_matches)}",
                f"Core art pack manifests present: {len(REQUIRED_ASSET_MANIFESTS)}/{len(REQUIRED_ASSET_MANIFESTS)}",
                f"Authored CC0 hero packaged/imported: {'yes' if hero_available else 'no — procedural fallback'}",
                f"Authored hero imported Godot scenes: {hero_imported_scene_count}",
                f"Authored hero animation clips: {int(hero_manifest.get('animation_count', 0)) if hero_available else 0}",
                "Limit: authored-model packaging success is not proof of CODM-level realism or on-device animation quality.",
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
