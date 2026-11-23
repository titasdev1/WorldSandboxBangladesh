#!/usr/bin/env python3
"""Fail-closed verification for the source-aligned Palong Model Thana Blender export."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def read_glb(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError(f"GLB is too small: {path}")
    magic, version, declared = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared != len(raw):
        raise ValueError(f"Invalid GLB header/length: {path}")
    offset = 12
    document = None
    binary_chunks = 0
    while offset + 8 <= len(raw):
        length, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        data = raw[offset:offset + length]
        if len(data) != length:
            raise ValueError(f"Truncated GLB chunk: {path}")
        if kind == 0x4E4F534A:
            document = json.loads(data.decode("utf-8").rstrip(" \t\r\n\x00"))
        elif kind == 0x004E4942:
            binary_chunks += 1
        offset += length
    if not isinstance(document, dict) or binary_chunks < 1:
        raise ValueError(f"GLB JSON/BIN chunks are missing: {path}")
    return document


def inspect_glb(path: Path, minimum_triangles: int = 1000) -> dict:
    doc = read_glb(path)
    if doc.get("asset", {}).get("version") != "2.0":
        raise ValueError(f"{path.name}: not glTF 2.0")
    meshes = doc.get("meshes", [])
    nodes = doc.get("nodes", [])
    materials = doc.get("materials", [])
    images = doc.get("images", [])
    textures = doc.get("textures", [])
    scenes = doc.get("scenes", [])
    accessors = doc.get("accessors", [])
    triangles = 0
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            index = primitive.get("indices")
            if isinstance(index, int) and 0 <= index < len(accessors):
                triangles += int(accessors[index].get("count", 0)) // 3
            else:
                position = primitive.get("attributes", {}).get("POSITION")
                if isinstance(position, int) and 0 <= position < len(accessors):
                    triangles += int(accessors[position].get("count", 0)) // 3
    external_images = [i.get("uri") for i in images if isinstance(i.get("uri"), str) and not i["uri"].startswith("data:")]
    non_embedded = [i for i in images if "bufferView" not in i and not str(i.get("uri", "")).startswith("data:")]
    if not scenes or not nodes or not meshes:
        raise ValueError(f"{path.name}: missing scene, nodes or meshes")
    if len(materials) < 6:
        raise ValueError(f"{path.name}: too few materials ({len(materials)})")
    if len(images) < 9 or len(textures) < 9:
        raise ValueError(f"{path.name}: expected embedded 3x3 PBR library, got images={len(images)} textures={len(textures)}")
    if external_images or non_embedded:
        raise ValueError(f"{path.name}: external or non-embedded textures: {external_images} / {len(non_embedded)}")
    if triangles < minimum_triangles:
        raise ValueError(f"{path.name}: mesh density below structural floor ({triangles} triangles)")
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "materials": len(materials),
        "embedded_images": len(images),
        "embedded_textures": len(textures),
        "triangles": triangles,
        "external_images": 0,
        "structural_status": "PASS"
    }


def verify(args) -> dict:
    required = [args.shell, args.gate, args.manifest, args.blend, args.shell_preview, args.gate_preview, args.pbr_manifest]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"Required Palong Thana review file missing: {path}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pbr_manifest = json.loads(args.pbr_manifest.read_text(encoding="utf-8"))

    if manifest.get("osm_id") != "601571171" or manifest.get("source_feature") != "way/601571171001":
        raise ValueError("Thana asset is not bound to exact OSM way 601571171")
    if manifest.get("tile") != "tile_23p1835_90p3053":
        raise ValueError("Thana asset came from an unexpected source tile")
    if not (160.0 <= float(manifest.get("footprint_area_m2", 0)) <= 190.0):
        raise ValueError("Mapped footprint area outside expected range")
    if manifest.get("storey_status") != "UNVERIFIED_ART_DIRECTION_ONLY":
        raise ValueError("Unverified floor status must remain explicit")
    if manifest.get("height_status") != "UNVERIFIED_ART_DIRECTION_ONLY":
        raise ValueError("Unverified height status must remain explicit")
    if manifest.get("entrance_osm_node_id") is not None:
        raise ValueError("No mapped entrance node is confirmed; keep it null")
    if manifest.get("gate_site_coordinate") is not None or manifest.get("gate_placement") != "DETACHED_LOCAL_ORIGIN_NOT_GEOGRAPHICALLY_PLACED":
        raise ValueError("Entrance gate concept must remain detached from the real map")
    if manifest.get("google_maps_or_street_view_used") is not False or manifest.get("source_photo_pixels_embedded") is not False:
        raise ValueError("Unlicensed map/street-view imagery or press-photo pixels must not enter the asset")
    if manifest.get("pbr_provider") != "Poly Haven" or manifest.get("pbr_license") != "CC0-1.0":
        raise ValueError("Palong Thana asset must use verified Poly Haven CC0 PBR maps")
    if pbr_manifest.get("provider") != "Poly Haven" or pbr_manifest.get("asset_license") != "CC0-1.0":
        raise ValueError("PBR provenance manifest provider/license mismatch")

    shell_report = inspect_glb(args.shell, minimum_triangles=1000)
    gate_report = inspect_glb(args.gate, minimum_triangles=300)
    from PIL import Image
    for path in (args.shell_preview, args.gate_preview):
        with Image.open(path) as image:
            width, height = image.size
            if width < 1200 or height < 700:
                raise ValueError(f"Preview resolution too small: {path.name} {width}x{height}")
            if path.stat().st_size < 40000:
                raise ValueError(f"Preview too small to inspect: {path.name}")
    return {
        "schema_version": 1,
        "status": "STRUCTURAL_AND_PROVENANCE_PASS_VISUAL_AND_DEVICE_REVIEW_REQUIRED",
        "source_identity": "OpenStreetMap way/601571171",
        "source_tile": "tile_23p1835_90p3053",
        "footprint_area_m2": manifest["footprint_area_m2"],
        "floor_count": None,
        "entrance_node": None,
        "gate_world_position": None,
        "pbr_provider": "Poly Haven",
        "pbr_license": "CC0-1.0",
        "shell": shell_report,
        "detached_gate_concept": gate_report,
        "limitations": manifest.get("limitations", []),
        "android_approved": False,
        "visual_approved": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--blend", type=Path, required=True)
    parser.add_argument("--shell-preview", type=Path, required=True)
    parser.add_argument("--gate-preview", type=Path, required=True)
    parser.add_argument("--pbr-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PALONG_THANA_HERO_VERIFICATION: PASS")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
