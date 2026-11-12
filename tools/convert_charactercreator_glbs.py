#!/usr/bin/env python3
"""Dequantize pinned CharacterCreator GLBs for Godot 4.4.1 without reducing detail."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "external_content" / "asquare_charactercreator"
MANIFEST = OUTPUT / "asset_manifest.json"
TOOL_PACKAGE = "@gltf-transform/cli@4.2.1"
TOOL = ["npx", "--yes", TOOL_PACKAGE]
EXTENSION = "KHR_mesh_quantization"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_core_gltf_compatible(document: dict, label: str) -> None:
    required = set(document.get("extensionsRequired", []))
    used = set(document.get("extensionsUsed", []))
    if EXTENSION in required or EXTENSION in used:
        raise RuntimeError(label + ": " + EXTENSION + " remains after dequantization.")


def assert_metadata_preserved(before: dict, after: dict, label: str) -> None:
    for key in ("bone_count", "bone_names", "skin_count", "animation_count",
                "animation_names", "morph_target_count_per_primitive", "mesh_count"):
        if before.get(key) != after.get(key):
            raise RuntimeError(
                label + ": dequantization changed " + key + " from "
                + repr(before.get(key)) + " to " + repr(after.get(key)) + "."
            )


def parse_glb_json(data: bytes, label: str) -> dict:
    # Reuse the pinned fetcher's strict GLB parser and metadata logic.
    sys.path.insert(0, str(ROOT / "tools"))
    import fetch_charactercreator_hero as pipeline
    return pipeline.parse_glb(data, label)


def rig_metadata(document: dict) -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    import fetch_charactercreator_hero as pipeline
    return pipeline.rig_metadata(document)


def main() -> int:
    if not MANIFEST.is_file():
        raise SystemExit("CHARACTER CREATOR CONVERSION FAILED: asset manifest is missing.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("available") is not True:
        raise SystemExit("CHARACTER CREATOR CONVERSION FAILED: source manifest is unavailable.")

    records = manifest.get("asset_files", {})
    if not isinstance(records, dict) or not records:
        raise SystemExit("CHARACTER CREATOR CONVERSION FAILED: asset records are missing.")

    required = {
        "base_body_anim.glb",
        "hair_short02.glb",
        "clothing_tshirt.glb",
        "clothing_jacket.glb",
        "clothing_jeans.glb",
        "clothing_boots.glb",
    }
    if not required.issubset(records):
        raise SystemExit("CHARACTER CREATOR CONVERSION FAILED: one or more pinned GLBs are absent.")

    converted = []
    for filename in sorted(required):
        path = OUTPUT / filename
        if not path.is_file():
            raise SystemExit("CHARACTER CREATOR CONVERSION FAILED: missing " + filename)

        current_bytes = path.read_bytes()
        record = records[filename]
        current_sha = sha256_bytes(current_bytes)

        # Idempotence: a prior successful conversion is accepted only when the
        # final file still matches its manifest checksum and the required extension is absent.
        current_doc = parse_glb_json(current_bytes, filename)
        try:
            assert_core_gltf_compatible(current_doc, filename)
            if record.get("compatibility", {}).get("transform") == "dequantize" and record.get("sha256") == current_sha:
                current_meta = rig_metadata(current_doc)
                converted.append(filename)
                print("GODOT_GLB_COMPATIBLE: " + filename + " (already verified)")
                continue
        except RuntimeError:
            pass

        before_meta = rig_metadata(current_doc)
        temporary = path.with_name(path.name + ".dequantized.tmp.glb")
        command = TOOL + ["dequantize", str(path), str(temporary)]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=600,
        )
        if completed.returncode != 0 or not temporary.is_file():
            raise RuntimeError(
                "glTF Transform dequantize failed for " + filename + ":\n" + completed.stdout[-6000:]
            )

        output_bytes = temporary.read_bytes()
        output_doc = parse_glb_json(output_bytes, filename + " (dequantized)")
        assert_core_gltf_compatible(output_doc, filename)
        after_meta = rig_metadata(output_doc)
        assert_metadata_preserved(before_meta, after_meta, filename)

        # Confirm the runtime body/accessory remains structurally valid after conversion.
        sys.path.insert(0, str(ROOT / "tools"))
        import fetch_charactercreator_hero as pipeline
        if filename == "base_body_anim.glb":
            pipeline.verify_body(after_meta)
        else:
            base_record = records["base_body_anim.glb"]
            del base_record
            # The pinned body rig's names are used as the reference; all accessories
            # are re-checked against the converted body after its file is processed.
        path.write_bytes(output_bytes)
        temporary.unlink(missing_ok=True)

        record["source_sha256"] = current_sha
        record["sha256"] = sha256_bytes(output_bytes)
        record["size_bytes"] = len(output_bytes)
        record["compatibility"] = {
            "transform": "dequantize",
            "tool": "@gltf-transform/cli",
            "tool_version": "4.2.1",
            "removed_extension": EXTENSION,
            "geometry_resolution_reduced": False,
            "texture_resolution_reduced": False,
            "metadata_preserved": True,
        }
        converted.append(filename)
        print(
            "GODOT_GLB_COMPATIBLE: " + filename
            + " • " + str(len(current_bytes)) + " -> " + str(len(output_bytes)) + " bytes"
        )

    # Cross-check the converted accessories against the final converted body.
    sys.path.insert(0, str(ROOT / "tools"))
    import fetch_charactercreator_hero as pipeline
    body_document = parse_glb_json((OUTPUT / "base_body_anim.glb").read_bytes(), "base_body_anim.glb")
    body_names = set(pipeline.rig_metadata(body_document)["bone_names"])
    for filename in sorted(required - {"base_body_anim.glb"}):
        doc = parse_glb_json((OUTPUT / filename).read_bytes(), filename)
        pipeline.verify_accessory(pipeline.rig_metadata(doc), body_names, filename)

    manifest["godot_compatibility"] = {
        "dequantized": True,
        "target_engine": "Godot 4.4.1",
        "tool": "@gltf-transform/cli",
        "tool_version": "4.2.1",
        "extension_removed": EXTENSION,
        "geometry_resolution_reduced": False,
        "texture_resolution_reduced": False,
        "validated_assets": sorted(required),
        "validated_at_build": True,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("CHARACTER_CREATOR_GODOT_COMPATIBILITY: PASS (" + str(len(converted)) + " GLBs)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("CHARACTER CREATOR CONVERSION FAILED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise
