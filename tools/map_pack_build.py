#!/usr/bin/env python3
"""Prepare a separate full-resolution Godot PCK for the selected real-world map."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESET_PATH = ROOT / "export_presets.cfg"
MAP_ROOT = ROOT / "assets" / "world" / "dhaka_tiles"
RAW_SUFFIXES = {".json", ".geojson", ".txt", ".photo_bytes"}
MAP_PACK_BASE = "Project-A-Square"
DEFAULT_MAX_PART_BYTES = 256 * 1024 * 1024  # 256 MiB: restart-friendly mobile download pieces.


def _manifest() -> dict[str, Any]:
    path = MAP_ROOT / "map_tiles_manifest.json"
    if not path.is_file():
        raise SystemExit(f"MAP PACK EXPORT FAILED: missing selected map manifest: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"MAP PACK EXPORT FAILED: invalid selected map manifest: {exc}") from exc
    tiles = data.get("tiles")
    if not isinstance(tiles, list) or not tiles:
        raise SystemExit("MAP PACK EXPORT FAILED: manifest must contain at least one tile record")

    # Map packs are regional content, not a fixed 60-tile district product.
    # Keep validating identities and any declared count so a partial/corrupt
    # regional manifest cannot silently produce an apparently complete pack.
    seen_ids: set[str] = set()
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise SystemExit(f"MAP PACK EXPORT FAILED: tile record {index} is not an object")
        tile_id = str(tile.get("tile_id", tile.get("id", tile.get("glb", "")))).strip()
        if not tile_id:
            raise SystemExit(f"MAP PACK EXPORT FAILED: tile record {index} has no stable identity")
        if tile_id in seen_ids:
            raise SystemExit(f"MAP PACK EXPORT FAILED: duplicate tile identity: {tile_id}")
        seen_ids.add(tile_id)

    declared_count = data.get("tile_count_total")
    if declared_count is not None:
        try:
            declared_count = int(declared_count)
        except (TypeError, ValueError) as exc:
            raise SystemExit("MAP PACK EXPORT FAILED: tile_count_total must be an integer") from exc
        if declared_count != len(tiles):
            raise SystemExit(
                f"MAP PACK EXPORT FAILED: manifest declares {declared_count} tiles but contains {len(tiles)}"
            )
    return data


def _safe_relative(value: str, suffix: str | None = None) -> str:
    value = value.strip().replace("\\", "/")
    path = Path(value)
    if not value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SystemExit(f"MAP PACK EXPORT FAILED: unsafe map resource path: {value!r}")
    if suffix and path.suffix.lower() != suffix:
        raise SystemExit(f"MAP PACK EXPORT FAILED: unexpected resource extension: {value!r}")
    return path.as_posix()


def _section(text: str, name: str) -> tuple[str, str, str]:
    pattern = re.compile(rf"(?ms)(^\[{re.escape(name)}\]\n.*?)(?=^\[|\Z)")
    match = pattern.search(text)
    if not match:
        return text, "", ""
    return text[:match.start()], match.group(1), text[match.end():]


def _set_key(block: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if pattern.search(block):
        return pattern.sub(f"{key}={value}", block, count=1)
    return block.rstrip() + f"\n{key}={value}\n"


def _map_slug(manifest: dict[str, Any]) -> str:
    boundary = manifest.get("administrative_boundary", {})
    name = str(boundary.get("name", "")) if isinstance(boundary, dict) else ""
    if str(manifest.get("build_stage", "")).lower() == "shariatpur_review" or "shariatpur" in name.lower():
        return "Shariatpur"
    if "dhaka" in name.lower():
        return "Greater-Dhaka"

    # New regional packs must carry a useful region name or stable region ID.
    # Never silently label an unrelated country/region as Greater Dhaka.
    raw_name = (
        str(manifest.get("display_name", "")).strip()
        or str(manifest.get("region_name", "")).strip()
        or name.strip()
        or str(manifest.get("region_id", "")).strip()
    )
    slug = re.sub(r"[^A-Za-z0-9]+", "-", raw_name).strip("-")
    if not slug:
        raise SystemExit("MAP PACK EXPORT FAILED: new regional manifest requires region_name, display_name, or region_id")
    return slug


def _map_pack_id(manifest: dict[str, Any]) -> str:
    boundary = manifest.get("administrative_boundary", {})
    name = str(boundary.get("name", "")) if isinstance(boundary, dict) else ""
    if str(manifest.get("build_stage", "")).lower() == "shariatpur_review" or "shariatpur" in name.lower():
        return "bangladesh.shariatpur"
    if "dhaka" in name.lower():
        return "bangladesh.greater-dhaka"

    explicit_id = str(manifest.get("map_pack_id", "")).strip()
    if explicit_id:
        pack_id = explicit_id.lower()
    else:
        country = str(manifest.get("country_code", "")).strip().lower()
        region = str(manifest.get("region_code", manifest.get("region_id", ""))).strip().lower()
        if not country or not region:
            raise SystemExit(
                "MAP PACK EXPORT FAILED: new regional manifests require map_pack_id or both country_code and region_code"
            )
        pack_id = f"{country}.{region}"
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,95}", pack_id):
        raise SystemExit(f"MAP PACK EXPORT FAILED: invalid map_pack_id: {pack_id!r}")
    return pack_id


def configure_pack_preset() -> None:
    manifest = _manifest()
    slug = _map_slug(manifest)
    project_paths: list[str] = []
    for tile in manifest["tiles"]:
        if not isinstance(tile, dict):
            raise SystemExit("MAP PACK EXPORT FAILED: malformed tile record")
        glb = _safe_relative(str(tile.get("glb", "")), ".glb")
        if not (MAP_ROOT / glb).is_file():
            raise SystemExit(f"MAP PACK EXPORT FAILED: missing GLB source: {glb}")
        project_paths.append("res://assets/world/dhaka_tiles/" + glb)

    raw_files = sorted(
        p.relative_to(ROOT).as_posix()
        for p in MAP_ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in RAW_SUFFIXES
    )
    if "assets/world/dhaka_tiles/map_tiles_manifest.json" not in raw_files:
        raise SystemExit("MAP PACK EXPORT FAILED: map manifest is not included in the data-file list")
    if "assets/world/dhaka_tiles/real_world_navigation_index.json" not in raw_files:
        raise SystemExit("MAP PACK EXPORT FAILED: compact navigation index is not included in the data-file list")
    # Explicit file paths avoid depending on wildcard recursion differences between
    # Godot versions. These are source-side JSON/GeoJSON/license bytes only; meshes
    # and their imported dependencies are selected through export_files below.
    include_filter = ",".join(raw_files)
    export_files = "PackedStringArray(" + ", ".join(json.dumps(p) for p in project_paths) + ")"

    original = PRESET_PATH.read_text(encoding="utf-8")
    # Replace an earlier generated preset if this helper is rerun on a workspace.
    before, old_preset, after = _section(original, "preset.1")
    if old_preset:
        original = before + after
    before, old_options, after = _section(original, "preset.1.options")
    if old_options:
        original = before + after
    # Rebuild from preset 0 without touching its full-map verification settings.
    preset = (
        '\n[preset.1]\n'
        'name="Project A-Square Map Pack"\n'
        'platform="Android"\n'
        'runnable=false\n'
        'dedicated_server=false\n'
        'custom_features=""\n'
        'export_filter="resources"\n'
        f'export_files={export_files}\n'
        f'include_filter={json.dumps(include_filter)}\n'
        'exclude_filter=""\n'
        f'export_path="./build/MapPacks/Project-A-Square-{slug}-Map.pck"\n'
        'encryption_include_filters=""\n'
        'encryption_exclude_filters=""\n'
        'encrypt_pck=false\n'
        'encrypt_directory=false\n'
        '\n[preset.1.options]\n'
        'encrypt_pck=false\n'
        'encrypt_directory=false\n'
    )
    PRESET_PATH.write_text(original.rstrip() + "\n" + preset, encoding="utf-8")
    print(f"Configured separate PCK preset for {len(project_paths)} GLB tiles and {len(raw_files)} data/license files.")
    print("Original Android preset remains full-map for the deep integration check.")


def prepare_core_export() -> None:
    """Exclude the already-verified map from the final small, installable core APK."""
    text = PRESET_PATH.read_text(encoding="utf-8")
    before, block, after = _section(text, "preset.0")
    if not block:
        raise SystemExit("CORE APK PREPARATION FAILED: preset.0 is missing")
    block = _set_key(block, "include_filter", '"assets/world/external_map_pack_required.flag"')
    block = _set_key(
        block,
        "exclude_filter",
        '"assets/world/dhaka_tiles/**,.godot/imported/Dhaka_Explorable_Map.glb-*,build/**"',
    )
    # Ensure network permission is included for the in-game signed map download.
    options_before, options, options_after = _section(text, "preset.0.options")
    if not options:
        raise SystemExit("CORE APK PREPARATION FAILED: Android preset options are missing")
    options = _set_key(options, "permissions/internet", "true")
    # Replace the sections by slicing the current text, avoiding any unrelated
    # export preset edits. Keep the generated map-pack preset intact.
    current = text
    _, current_block, rest = _section(current, "preset.0")
    current = current[:current.index(current_block)] + block + rest if current_block else current
    _, options_block, rest = _section(current, "preset.0.options")
    current = current[:current.index(options_block)] + options + rest if options_block else current
    PRESET_PATH.write_text(current, encoding="utf-8")
    # Verify the actual values written before attempting the second export.
    check = PRESET_PATH.read_text(encoding="utf-8")
    _, block_check, _ = _section(check, "preset.0")
    if 'exclude_filter="assets/world/dhaka_tiles/**,.godot/imported/Dhaka_Explorable_Map.glb-*,build/**"' not in block_check:
        raise SystemExit("CORE APK PREPARATION FAILED: map exclusion filter was not written")
    if 'include_filter="assets/world/external_map_pack_required.flag"' not in block_check:
        raise SystemExit("CORE APK PREPARATION FAILED: map-only raw-file inclusion was not cleared")
    print("Core export preset now excludes district map sources and imported map scenes; map PCK keeps original resolution.")
    

def write_metadata(
    pack_path: Path,
    output_path: Path,
    release_tag: str,
    max_part_bytes: int = DEFAULT_MAX_PART_BYTES,
) -> None:
    """Split a complete PCK into GitHub-release-safe pieces and describe them.

    The final runtime file is still one byte-identical PCK. The game downloads
    each bounded part, verifies it, then reassembles it in private app storage.
    """
    manifest = _manifest()
    if not pack_path.is_file() or pack_path.stat().st_size <= 0:
        raise SystemExit(f"MAP PACK METADATA FAILED: map pack missing or empty: {pack_path}")
    if max_part_bytes <= 0 or max_part_bytes >= 2 * 1024 * 1024 * 1024:
        raise SystemExit("MAP PACK METADATA FAILED: each release part must be smaller than GitHub's 2 GiB asset limit.")
    boundary = manifest.get("administrative_boundary", {})
    map_name = str(boundary.get("name", "")) if isinstance(boundary, dict) else ""
    slug = _map_slug(manifest)
    pack_id = _map_pack_id(manifest)

    filename = f"{MAP_PACK_BASE}-{slug}-Map.pck"
    base_url = f"https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/{release_tag}/{filename}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Remove stale split parts before producing the current pack manifest.
    for stale in output_path.parent.glob(filename + ".part*"):
        stale.unlink()

    parts: list[dict[str, Any]] = []
    full_digest = hashlib.sha256()
    full_size = 0
    part_index = 1
    with pack_path.open("rb") as source:
        while True:
            part_name = f"{filename}.part{part_index:03d}"
            part_path = output_path.parent / part_name
            part_digest = hashlib.sha256()
            part_size = 0
            with part_path.open("wb") as target:
                while part_size < max_part_bytes:
                    chunk = source.read(min(4 * 1024 * 1024, max_part_bytes - part_size))
                    if not chunk:
                        break
                    target.write(chunk)
                    part_digest.update(chunk)
                    full_digest.update(chunk)
                    part_size += len(chunk)
                    full_size += len(chunk)
            if part_size == 0:
                part_path.unlink(missing_ok=True)
                break
            parts.append({
                "index": part_index,
                "asset_filename": part_name,
                "asset_url": base_url + f".part{part_index:03d}",
                "size_bytes": part_size,
                "sha256": part_digest.hexdigest(),
            })
            print(f"Map PCK part {part_index}: {part_name} ({part_size:,} bytes, SHA-256 {part_digest.hexdigest()})")
            part_index += 1

    original_size = pack_path.stat().st_size
    if full_size != original_size or not parts:
        raise SystemExit(f"MAP PACK METADATA FAILED: split size {full_size:,} does not match source PCK size {original_size:,}.")
    # Never attach the >2 GiB single-file PCK to GitHub Releases. Only these
    # individual pieces are release assets; the game reconstructs the exact PCK.
    metadata = {
        "schema_version": 2,
        "map_pack_id": pack_id,
        "display_name": slug.replace("-", " "),
        "asset_filename": filename,
        "release_tag": release_tag,
        "size_bytes": full_size,
        "sha256": full_digest.hexdigest(),
        "part_count": len(parts),
        "parts": parts,
        "tile_count": len(manifest["tiles"]),
        "build_stage": manifest.get("build_stage", ""),
        "country_code": manifest.get("country_code", ""),
        "region_code": manifest.get("region_code", manifest.get("region_id", "")),
        "administrative_boundary": boundary,
        "region_south_west_north_east": manifest.get("region_south_west_north_east", []),
        "game_origin_lat_lon": manifest.get("game_origin_lat_lon", []),
        "map_detail_policy": "full-resolution exported resources; original PCK bytes are reassembled without recompression or downscaling",
        "runtime_note": "The game downloads SHA-256-verified parts into private app storage and reassembles one byte-identical PCK before mounting it on the next launch.",
    }
    output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote map pack metadata: {output_path} ({full_size:,} bytes in {len(parts)} GitHub-safe parts, SHA-256 {metadata['sha256']})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure-pack-preset", action="store_true")
    parser.add_argument("--prepare-core-export", action="store_true")
    parser.add_argument("--write-metadata", action="store_true")
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--release-tag", default="shariatpur-review-candidate")
    parser.add_argument("--max-part-bytes", type=int, default=DEFAULT_MAX_PART_BYTES)
    args = parser.parse_args()
    if args.configure_pack_preset:
        configure_pack_preset()
    if args.prepare_core_export:
        prepare_core_export()
    if args.write_metadata:
        if args.pack is None or args.out is None:
            parser.error("--write-metadata requires --pack and --out")
        write_metadata(args.pack, args.out, args.release_tag, args.max_part_bytes)
    if not (args.configure_pack_preset or args.prepare_core_export or args.write_metadata):
        parser.error("choose an operation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
