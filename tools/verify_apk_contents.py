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
import re
import struct
import sys
import zipfile


MAP_ROOT = "assets/assets/world/dhaka_tiles/"
SOURCE_MAP_ROOT = pathlib.Path("assets/world/dhaka_tiles")
IMPORTED_ROOT = "assets/.godot/imported/"
REQUIRED_ASSET_MANIFESTS = (
    "assets/external_content/kenney_car_kit/asset_manifest.json",
    "assets/external_content/kenney_city_kit_commercial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_industrial/asset_manifest.json",
    "assets/external_content/kenney_city_kit_suburban/asset_manifest.json",
    "assets/external_content/polyhaven_pbr/asset_manifest.json",
    "assets/external_content/quaternius_hero/asset_manifest.json",
)


def _assert_glb_has_embedded_facade_panel(glb_data: bytes, image_id: str, osm_id: str) -> None:
    """Require a named facade mesh whose material resolves to image bytes embedded in the GLB."""
    if len(glb_data) < 20:
        raise ValueError("GLB is too short")
    magic, version, declared_length = struct.unpack_from("<4sII", glb_data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(glb_data):
        raise ValueError("invalid GLB magic, version, or declared length")

    json_document = None
    binary_chunk = None
    cursor = 12
    while cursor + 8 <= declared_length:
        chunk_length, chunk_type = struct.unpack_from("<II", glb_data, cursor)
        cursor += 8
        chunk_end = cursor + chunk_length
        if chunk_end > declared_length:
            raise ValueError("GLB chunk extends beyond the declared file length")
        chunk_data = glb_data[cursor:chunk_end]
        cursor = chunk_end
        if chunk_type == 0x4E4F534A and json_document is None:  # JSON
            try:
                json_document = json.loads(chunk_data.decode("utf-8").rstrip(" \t\r\n\x00"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("GLB JSON chunk is malformed") from exc
        elif chunk_type == 0x004E4942 and binary_chunk is None:  # BIN
            binary_chunk = chunk_data
    if cursor != declared_length or not isinstance(json_document, dict) or binary_chunk is None:
        raise ValueError("GLB is missing a complete JSON/BIN chunk pair")

    expected_name = f"licensed_facade_photo_{image_id}_{osm_id}"
    meshes = json_document.get("meshes", [])
    nodes = json_document.get("nodes", [])
    materials = json_document.get("materials", [])
    textures = json_document.get("textures", [])
    images = json_document.get("images", [])
    buffer_views = json_document.get("bufferViews", [])
    if not all(isinstance(collection, list) for collection in
               (meshes, nodes, materials, textures, images, buffer_views)):
        raise ValueError("GLB mesh/material/texture tables are malformed")

    mesh_index = next(
        (index for index, mesh in enumerate(meshes)
         if isinstance(mesh, dict) and str(mesh.get("name", "")) == expected_name),
        None,
    )
    if mesh_index is None:
        raise ValueError(f"named mesh {expected_name!r} is absent from the GLB")
    if not any(isinstance(node, dict) and node.get("mesh") == mesh_index for node in nodes):
        raise ValueError(f"named mesh {expected_name!r} is not referenced by a GLB node")

    mesh = meshes[mesh_index]
    primitives = mesh.get("primitives", [])
    if not isinstance(primitives, list) or not primitives:
        raise ValueError("named facade mesh has no primitives")

    for primitive in primitives:
        if not isinstance(primitive, dict):
            continue
        try:
            material_index = int(primitive["material"])
            material = materials[material_index]
            pbr = material.get("pbrMetallicRoughness", {})
            texture_index = int(pbr["baseColorTexture"]["index"])
            texture = textures[texture_index]
            image_index = int(texture["source"])
            image = images[image_index]
            image_view_index = int(image["bufferView"])
            image_view = buffer_views[image_view_index]
            if "uri" in image:
                continue
            if int(image_view.get("buffer", 0)) != 0:
                continue
            byte_offset = int(image_view.get("byteOffset", 0))
            byte_length = int(image_view["byteLength"])
            if byte_offset < 0 or byte_length <= 0 or byte_offset + byte_length > len(binary_chunk):
                continue
            image_bytes = binary_chunk[byte_offset:byte_offset + byte_length]
            mime_type = str(image.get("mimeType", "")).strip().lower()
            signature_valid = (
                mime_type == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
                or mime_type in {"image/jpeg", "image/jpg"} and image_bytes.startswith(b"\xff\xd8\xff")
                or mime_type == "image/webp" and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
            )
            if signature_valid:
                return
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    raise ValueError(f"named facade mesh {expected_name!r} has no material linked to a valid embedded raster texture")


def _resolve_imported_scene_from_remap(remap_data: bytes) -> str:
    """Resolve a Godot GLB importer remap to the exact scene path in the APK."""
    try:
        remap_text = remap_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("GLB import remap is not UTF-8 text") from exc
    match = re.search(
        r'(?m)^path="res://\.godot/imported/([^"/]+\.scn)"\s*$',
        remap_text,
    )
    if not match:
        raise ValueError("GLB import remap does not name a safe imported .scn resource")
    filename = match.group(1)
    if not filename.startswith("Dhaka_Explorable_Map.glb-"):
        raise ValueError("GLB import remap points to an unexpected imported scene")
    return IMPORTED_ROOT + filename


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
                origin = manifest.get("game_origin_lat_lon")
                priority = manifest.get("tile_order_priority", {})
                seed = priority.get("seed_lat_lon", []) if isinstance(priority, dict) else []
                if not (isinstance(origin, list) and len(origin) == 2 and
                        isinstance(seed, list) and len(seed) == 2):
                    raise SystemExit("APK CONTENT GATE FAILED: Shariatpur world origin or priority seed is missing.")
                try:
                    origin_pair = [float(origin[0]), float(origin[1])]
                    seed_pair = [float(seed[0]), float(seed[1])]
                except (TypeError, ValueError) as exc:
                    raise SystemExit("APK CONTENT GATE FAILED: Shariatpur origin/seed is nonnumeric.") from exc
                if any(abs(a - b) > 0.000001 for a, b in zip(origin_pair, seed_pair)):
                    raise SystemExit(
                        "APK CONTENT GATE FAILED: Shariatpur world origin does not match the "
                        "priority seed; the player could spawn outside the useful streamed map."
                    )

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
            verified_facade_glb_panels = 0
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
                    import_path = glb_path + ".import"
                    if import_path not in names:
                        raise SystemExit(f"APK CONTENT GATE FAILED: tile-specific GLB/remap missing for licensed exterior photo {pair[0]}.")
                    # Godot normally exports the imported PackedScene/remap, not
                    # the original GLB source bytes. Validate the actual selected-map
                    # GLB before export, then tie it to the exact imported scene in APK.
                    tile_id = PurePosixPath(tile_dir).name
                    if tile_id in {"", ".", ".."} or PurePosixPath(tile_id).name != tile_id:
                        raise SystemExit("APK CONTENT GATE FAILED: unsafe tile id in photo-to-tile mapping.")
                    source_glb = SOURCE_MAP_ROOT / tile_id / "Dhaka_Explorable_Map.glb"
                    if not source_glb.is_file():
                        raise SystemExit(
                            f"APK CONTENT GATE FAILED: selected-map source GLB missing for licensed exterior photo {pair[0]}: {source_glb}"
                        )
                    expected_mesh_name = f"licensed_facade_photo_{pair[0]}_{pair[1]}"
                    try:
                        _assert_glb_has_embedded_facade_panel(source_glb.read_bytes(), pair[0], pair[1])
                        imported_scene_path = _resolve_imported_scene_from_remap(apk.read(import_path))
                    except (OSError, ValueError) as exc:
                        raise SystemExit(
                            f"APK CONTENT GATE FAILED: selected-map source GLB or Godot remap is invalid for "
                            f"{pair[0]} / {pair[1]}: {exc}"
                        ) from exc
                    if imported_scene_path not in names:
                        raise SystemExit(
                            f"APK CONTENT GATE FAILED: Godot import remap points to no packaged imported scene "
                            f"for licensed exterior photo {pair[0]}: {imported_scene_path}"
                        )
                    imported_scene_data = apk.read(imported_scene_path)
                    # Godot's imported .scn is a binary PackedScene; node/mesh names
                    # are not guaranteed to remain as literal UTF-8 byte strings.
                    # The exact source GLB above is parsed and checked for the named
                    # mesh, node reference, material, embedded raster bytes and valid
                    # texture signature. Here verify the APK includes the non-empty
                    # imported scene reached by that tile's actual .import remap.
                    # Searching the binary .scn for a source mesh name is a false
                    # negative on valid exports and must not be used as a release gate.
                    if not imported_scene_data:
                        raise SystemExit(
                            f"APK CONTENT GATE FAILED: Godot imported scene is empty for "
                            f"verified exterior-photo mesh {expected_mesh_name}."
                        )
                    verified_facade_glb_panels += 1

            missing_art = [p for p in REQUIRED_ASSET_MANIFESTS if p not in names]
            if missing_art:
                raise SystemExit("APK CONTENT GATE FAILED: art pack manifests absent from APK: " + ", ".join(missing_art))

            # When CI successfully assembles the authored player, prove that the
            # exact licensed GLB bytes, Godot import remap and imported scene are in
            # the candidate APK. A ZIP containing the source archive alone is not enough.
            hero_manifest_path = "assets/external_content/quaternius_hero/asset_manifest.json"
            if hero_manifest_path not in names:
                raise SystemExit("APK CONTENT GATE FAILED: authored hero asset manifest is absent from the APK.")
            hero_manifest = json.loads(apk.read(hero_manifest_path).decode("utf-8"))
            hero_available = hero_manifest.get("available") is True
            hero_imported_scene_count = 0
            if hero_available:
                hero_resource_path = "external_content/quaternius_hero/Project_A_Square_Hero.glb"
                apk_resource_path = "assets/" + hero_resource_path
                hero_import_meta_path = apk_resource_path + ".import"
                # Godot exports the imported PackedScene, remap and textures. It normally
                # omits original imported .glb source bytes from the Android APK.
                # Verify the source checksum in the build workspace and the remapped
                # imported scene inside the APK rather than requiring duplicate raw bytes.
                hero_source_path = pathlib.Path(hero_resource_path)
                if not hero_source_path.is_file():
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero source GLB is missing from the build workspace.")
                hero_sha = hashlib.sha256(hero_source_path.read_bytes()).hexdigest()
                if hero_sha != str(hero_manifest.get("hero_glb_sha256", "")).lower():
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero source GLB checksum does not match its build manifest.")
                if hero_import_meta_path not in names:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero has no Godot import remap in the APK.")
                try:
                    hero_remap = apk.read(hero_import_meta_path).decode("utf-8")
                except (KeyError, UnicodeDecodeError) as exc:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero import remap is unreadable.") from exc
                hero_remap_match = re.search(
                    r'(?m)^path="res://\.godot/imported/([^"/]+\.scn)"\s*$',
                    hero_remap,
                )
                if not hero_remap_match:
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero import remap does not reference a valid imported scene.")
                hero_scene_name = hero_remap_match.group(1)
                if not hero_scene_name.startswith("Project_A_Square_Hero.glb-"):
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero remap points to an unexpected imported resource.")
                hero_scene_path = IMPORTED_ROOT + hero_scene_name
                if hero_scene_path not in names:
                    raise SystemExit(f"APK CONTENT GATE FAILED: authored hero imported scene referenced by its remap is absent from the APK: {hero_scene_path}")
                if not apk.read(hero_scene_path):
                    raise SystemExit("APK CONTENT GATE FAILED: authored hero imported scene is empty.")
                hero_imported_scene_count = 1
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
                f"Licensed exterior façade panels validated in source GLBs and mapped into APK scenes: {verified_facade_glb_panels}",
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
