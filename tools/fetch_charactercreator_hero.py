#!/usr/bin/env python3
"""Fetch a pinned, editable CharacterCreator humanoid asset set for Project A-Square.

Only the upstream exported GLB data and license records are fetched. The upstream
GPL source code is not copied or executed by the game build. All binary GLB inputs
are pinned by Git blob SHA-1 at one immutable upstream commit and re-checked before
they are accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "external_content" / "asquare_charactercreator"
SOURCE_REPO = "https://github.com/kblood/CharacterCreator"
SOURCE_COMMIT = "852e48f316b90a0937234886630e4fb4cdfd1f78"
RAW_BASE = f"https://raw.githubusercontent.com/kblood/CharacterCreator/{SOURCE_COMMIT}/"
LICENSE = "CC0-1.0"

# Git blob object IDs pin the exact upstream bytes, not merely the mutable branch.
ASSETS = {
    "base_body_anim.glb": {
        "path": "output/base_body_anim.glb",
        "blob_sha1": "bdbdab04eb85903e46c56ff56c7a1ea0cbe9c78b",
        "role": "rigged humanoid body, face, skin materials and 12 baked motion clips",
    },
    "hair_short02.glb": {
        "path": "output/hair_short02.glb",
        "blob_sha1": "55243e1eb018ca44bd890f9acacb8c874eeb96f8",
        "role": "short hair mesh fitted to the exported humanoid rig",
    },
    "clothing_tshirt.glb": {
        "path": "output/clothing_tshirt.glb",
        "blob_sha1": "ce7966dfd52c4bc6158e1e3b21969e6a63b066da",
        "role": "skinned base shirt layer",
    },
    "clothing_jacket.glb": {
        "path": "output/clothing_jacket.glb",
        "blob_sha1": "6f1d075b1c041a67e15af98395769e0c5fa915b9",
        "role": "skinned outer jacket layer to be recoloured and customised",
    },
    "clothing_jeans.glb": {
        "path": "output/clothing_jeans.glb",
        "blob_sha1": "10b38785efef7196bc9903c9d8cdf236d28dc584",
        "role": "skinned lower-body clothing layer",
    },
    "clothing_boots.glb": {
        "path": "output/clothing_boots.glb",
        "blob_sha1": "7fea477d6496c9ccbfc4694a06ecebe9ed80abec",
        "role": "skinned footwear layer",
    },
}
TEXT_FILES = {
    "LICENSE-NOTES.md": {
        "path": "LICENSE-NOTES.md",
        "blob_sha1": "4dad3599865b2faf00a22ff152e05395df76a7da",
    },
    "asset_licenses.json": {
        "path": "output/asset_licenses.json",
        "blob_sha1": "298c63ecb119536207e122c77b37737e2427e08c",
    },
}

USER_AGENT = "Project-A-Square-Character-Pipeline/1.0"


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_bytes(relative_path: str) -> bytes:
    url = RAW_BASE + relative_path
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/octet-stream,text/plain,*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read()
            if not data:
                raise RuntimeError(f"Upstream returned an empty file: {relative_path}")
            return data
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            if attempt < 3:
                delay = (3, 9, 20)[attempt]
                print(f"Retrying {relative_path} after {delay}s: {exc}", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Could not download {relative_path}: {last_error}")


def parse_glb(data: bytes, label: str) -> dict:
    if len(data) < 20:
        raise RuntimeError(f"{label}: GLB is too short.")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise RuntimeError(f"{label}: expected a glTF 2.0 binary.")
    if declared_length != len(data):
        raise RuntimeError(f"{label}: GLB length header does not match downloaded bytes.")
    json_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    if chunk_type != b"JSON" or json_length <= 0 or 20 + json_length > len(data):
        raise RuntimeError(f"{label}: first GLB chunk is not a valid JSON chunk.")
    try:
        return json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\0"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}: malformed GLB JSON chunk: {exc}") from exc


def rig_metadata(document: dict) -> dict:
    nodes = document.get("nodes", [])
    skins = document.get("skins", [])
    joint_indices: set[int] = set()
    for skin in skins:
        joint_indices.update(int(index) for index in skin.get("joints", []))
    bone_names = sorted(
        str(nodes[index].get("name", ""))
        for index in joint_indices
        if 0 <= index < len(nodes) and nodes[index].get("name")
    )
    animations = [
        str(item.get("name", ""))
        for item in document.get("animations", [])
        if item.get("name")
    ]
    morph_count = max(
        (
            len(primitive.get("targets", []))
            for mesh in document.get("meshes", [])
            for primitive in mesh.get("primitives", [])
        ),
        default=0,
    )
    return {
        "node_count": len(nodes),
        "skin_count": len(skins),
        "bone_count": len(bone_names),
        "bone_names": bone_names,
        "animation_names": animations,
        "animation_count": len(animations),
        "morph_target_count_per_primitive": morph_count,
        "mesh_count": len(document.get("meshes", [])),
    }


def verify_body(metadata: dict) -> None:
    required_bones = {"hand_r", "spine_02", "spine_03", "pelvis", "thigh_l", "thigh_r", "foot_l", "foot_r"}
    missing_bones = sorted(required_bones - set(metadata["bone_names"]))
    if metadata["bone_count"] < 50 or missing_bones:
        raise RuntimeError(
            f"Body rig failed: {metadata['bone_count']} bones; missing {missing_bones}."
        )
    normalized = {
        name.casefold().replace("_", "").replace("-", "").replace(" ", "")
        for name in metadata["animation_names"]
    }
    required_motions = {"idle", "walk", "run", "jump", "fall", "land"}
    missing_motions = sorted(required_motions - normalized)
    if metadata["animation_count"] < 10 or missing_motions:
        raise RuntimeError(
            f"Body animation set failed: {metadata['animation_count']} clips; missing {missing_motions}."
        )
    if metadata["morph_target_count_per_primitive"] < 50:
        raise RuntimeError(
            f"Body morph set failed: only {metadata['morph_target_count_per_primitive']} targets on a primitive."
        )


def verify_accessory(metadata: dict, body_bones: set[str], label: str) -> None:
    if metadata["skin_count"] < 1 or metadata["bone_count"] < 1:
        raise RuntimeError(f"{label}: accessory is not attached to a skin rig.")
    shared = set(metadata["bone_names"]) & body_bones
    if not shared:
        raise RuntimeError(f"{label}: accessory does not share named bones with the body rig.")
    if label.startswith("clothing") and len(shared) < 20:
        raise RuntimeError(f"{label}: clothing rig has too few shared bones ({len(shared)}).")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch every pinned upstream asset.")
    parser.add_argument("--required", action="store_true", help="Fail rather than leave an unavailable manifest.")
    args = parser.parse_args()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT / "asset_manifest.json"
    if not args.force and manifest_path.is_file():
        try:
            cached = json.loads(manifest_path.read_text(encoding="utf-8"))
            if cached.get("available") is True and all(
                (OUTPUT / name).is_file()
                and git_blob_sha1((OUTPUT / name).read_bytes()) == spec["blob_sha1"]
                for name, spec in ASSETS.items()
            ):
                print("Pinned CharacterCreator assets already verified.")
                return 0
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    try:
        downloaded: dict[str, bytes] = {}
        for filename, spec in {**ASSETS, **TEXT_FILES}.items():
            data = fetch_bytes(spec["path"])
            actual_blob = git_blob_sha1(data)
            if actual_blob != spec["blob_sha1"]:
                raise RuntimeError(
                    f"Upstream blob mismatch for {filename}: expected {spec['blob_sha1']}, got {actual_blob}."
                )
            downloaded[filename] = data
            print(f"Verified upstream Git blob {filename} ({len(data):,} bytes).", flush=True)

        body_doc = parse_glb(downloaded["base_body_anim.glb"], "base_body_anim.glb")
        body_meta = rig_metadata(body_doc)
        verify_body(body_meta)
        body_bones = set(body_meta["bone_names"])

        asset_records = {}
        for filename, spec in ASSETS.items():
            data = downloaded[filename]
            if filename == "base_body_anim.glb":
                metadata = body_meta
            else:
                metadata = rig_metadata(parse_glb(data, filename))
                verify_accessory(metadata, body_bones, filename)
            target = OUTPUT / filename
            target.write_bytes(data)
            asset_records[filename] = {
                "source_path": spec["path"],
                "git_blob_sha1": spec["blob_sha1"],
                "sha256": sha256_bytes(data),
                "size_bytes": len(data),
                "role": spec["role"],
                "license": LICENSE,
                "rig": {
                    "bone_count": metadata["bone_count"],
                    "skin_count": metadata["skin_count"],
                },
            }

        for filename, data in downloaded.items():
            if filename in TEXT_FILES:
                (OUTPUT / filename).write_bytes(data)

        manifest = {
            "schema_version": 1,
            "available": True,
            "asset_family": "Project A-Square custom humanoid candidate",
            "source_repository": SOURCE_REPO,
            "source_commit": SOURCE_COMMIT,
            "generated_asset_license": LICENSE,
            "upstream_generator_code_license": "GPL-3.0-or-later; not copied into this game build",
            "attribution_required_for_generated_assets": False,
            "asset_files": asset_records,
            "body": body_meta,
            "acceptance_notes": [
                "This is an editable rigged human base and modular clothing set, not a final CODM-quality operator.",
                "The clothing catalogue is documented upstream as prototype quality; inspect seams, clipping and animation deformation in Godot.",
                "The exported rig is documented as 53 bones with 92 morph targets and 12 clips; exact values are checked against the fetched GLB before integration.",
                "Aim, firing, reload, weapon-specific locomotion, tactical wardrobe design and physical-device visual QA remain separate requirements.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "available": True,
            "assets": {name: record["size_bytes"] for name, record in asset_records.items()},
            "bone_count": body_meta["bone_count"],
            "animation_count": body_meta["animation_count"],
            "morph_targets": body_meta["morph_target_count_per_primitive"],
            "animations": body_meta["animation_names"],
        }, indent=2))
        return 0
    except Exception as exc:
        manifest_path.write_text(
            json.dumps({
                "schema_version": 1,
                "available": False,
                "source_repository": SOURCE_REPO,
                "source_commit": SOURCE_COMMIT,
                "error": f"{type(exc).__name__}: {exc}",
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"CHARACTER CREATOR ASSET PIPELINE FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1 if args.required else 0


if __name__ == "__main__":
    raise SystemExit(main())
