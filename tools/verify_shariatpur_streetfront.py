#!/usr/bin/env python3
"""Fail-closed structural verifier for the Shariatpur streetfront Blender asset."""
from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys

JSON_CHUNK = 0x4E4F534A


def read_glb_json(path: pathlib.Path) -> tuple[dict, int]:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is too small to contain a valid header and JSON chunk")
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total_length != len(raw):
        raise ValueError(f"Invalid GLB header: magic={magic!r}, version={version}, declared={total_length}, actual={len(raw)}")
    json_length, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != JSON_CHUNK or 20 + json_length > len(raw):
        raise ValueError("GLB first chunk is not a valid JSON chunk")
    document = json.loads(raw[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\x00"))
    return document, len(raw)


def verify(glb_path: pathlib.Path, manifest_path: pathlib.Path, license_path: pathlib.Path,
           preview_path: pathlib.Path, output_path: pathlib.Path) -> dict:
    for path in (glb_path, manifest_path, license_path, preview_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required asset output is missing: {path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    gltf, byte_count = read_glb_json(glb_path)
    license_text = license_path.read_text(encoding="utf-8")

    materials = gltf.get("materials", [])
    images = gltf.get("images", [])
    textures = gltf.get("textures", [])
    meshes = gltf.get("meshes", [])
    nodes = gltf.get("nodes", [])
    scenes = gltf.get("scenes", [])
    primitives = [primitive for mesh in meshes for primitive in mesh.get("primitives", [])]
    triangles = 0
    for primitive in primitives:
        indices = primitive.get("indices")
        accessors = gltf.get("accessors", [])
        if isinstance(indices, int) and indices < len(accessors):
            triangles += int(accessors[indices].get("count", 0)) // 3
        else:
            position_accessor = primitive.get("attributes", {}).get("POSITION")
            if isinstance(position_accessor, int) and position_accessor < len(accessors):
                triangles += int(accessors[position_accessor].get("count", 0)) // 3

    failures = []
    if gltf.get("asset", {}).get("version") != "2.0": failures.append("GLB is not glTF 2.0")
    if len(meshes) < 1 or not primitives: failures.append("No exported building mesh primitives")
    if len(materials) < 7: failures.append(f"Only {len(materials)} materials; expected seven PBR surfaces plus lettering")
    if len(images) < 18 or len(textures) < 18: failures.append(f"Embedded texture library incomplete: images={len(images)}, textures={len(textures)}")
    if any("bufferView" not in image for image in images): failures.append("At least one GLB image is external rather than embedded")
    if not nodes or not scenes: failures.append("GLB has no scene nodes")
    if triangles < 8000: failures.append(f"Mesh detail is below the 8,000-triangle minimum: {triangles}")
    if "CC0 1.0 Universal" not in license_text: failures.append("CC0 license text is missing")
    if manifest.get("license") != "CC0-1.0": failures.append("Manifest does not identify CC0-1.0")
    if manifest.get("geographic_status") != "AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING": failures.append("Geographic status is not explicit")
    if manifest.get("engine_target") != "Godot 4.4.1": failures.append("Engine target does not preserve Godot 4.4.1")
    if manifest.get("mesh_object_count") != 1: failures.append("Asset should be exported as one combined mesh object")
    bounds = manifest.get("bounds_metres", {})
    if not (float(bounds.get("width", 0)) >= 10.0 and float(bounds.get("depth", 0)) >= 7.0 and float(bounds.get("height", 0)) >= 8.5):
        failures.append(f"Unexpected hero asset dimensions: {bounds}")
    if preview_path.stat().st_size < 40_000: failures.append("Rendered preview is absent or implausibly small")
    feature_inventory = manifest.get("feature_inventory", [])
    for required in ("recessed timber and grilled windows", "Bengali shop sign and district lettering",
                     "corrugated awning and brackets", "rooftop water tank and service pipes",
                     "utility meter, drain, downpipe and facade cables"):
        if required not in feature_inventory: failures.append(f"Feature inventory omits: {required}")
    if failures:
        raise RuntimeError("SHARIATPUR_STREETFRONT_VERIFY_FAIL: " + " | ".join(failures))

    report = {
        "status": "STRUCTURAL_PASS_VISUAL_APPROVAL_AND_ANDROID_RUNTIME_STILL_REQUIRED",
        "asset_file": glb_path.name,
        "glb_bytes": byte_count,
        "triangle_count_from_glb_accessors": triangles,
        "mesh_count": len(meshes),
        "primitive_count": len(primitives),
        "material_count": len(materials),
        "embedded_image_count": len(images),
        "embedded_texture_count": len(textures),
        "scene_node_count": len(nodes),
        "preview_bytes": preview_path.stat().st_size,
        "bounds_metres": bounds,
        "license": manifest.get("license"),
        "geographic_status": manifest.get("geographic_status"),
        "limitations": ["Not a survey or photographic reconstruction of a named building",
                        "No collision, navigation, verified floor graph or real entrance supplied",
                        "Requires visual review in Godot 4.4.1 and Android device performance testing"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("A2_SHARIATPUR_STREETFRONT_STRUCTURAL_PASS: " + json.dumps(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--license", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        verify(args.glb, args.manifest, args.license, args.preview, args.out)
    except Exception as exc:
        print(f"A2_SHARIATPUR_STREETFRONT_STRUCTURAL_FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
