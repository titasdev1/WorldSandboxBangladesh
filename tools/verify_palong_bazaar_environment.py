#!/usr/bin/env python3
"""Fail-closed verifier for the original Palong Bazar corridor review asset."""
from __future__ import annotations

import argparse
import json
import pathlib
import struct
from PIL import Image, ImageStat

JSON_CHUNK = 0x4E4F534A


def args_from_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--license", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    return parser.parse_args()


def read_glb(path: pathlib.Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is too small")
    magic, version, length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or length != len(raw):
        raise ValueError(f"Invalid GLB header: {magic!r} v{version}, declared={length}, actual={len(raw)}")
    chunk_len, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != JSON_CHUNK or 20 + chunk_len > len(raw):
        raise ValueError("GLB does not begin with a valid glTF JSON chunk")
    return json.loads(raw[20:20 + chunk_len].decode("utf-8").rstrip(" \t\r\n\x00"))


def verify(glb_path, manifest_path, license_path, preview_path, out_path):
    for path in (glb_path, manifest_path, license_path, preview_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required corridor output is missing: {path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    polyhaven_manifest_path = pathlib.Path(str(manifest.get("texture_provenance_manifest", "")))
    if not polyhaven_manifest_path.is_absolute():
        polyhaven_manifest_path = pathlib.Path.cwd() / polyhaven_manifest_path
    if not polyhaven_manifest_path.is_file():
        raise FileNotFoundError(f"Poly Haven PBR provenance is required: {polyhaven_manifest_path}")
    polyhaven_manifest = json.loads(polyhaven_manifest_path.read_text(encoding="utf-8"))
    gltf = read_glb(glb_path)
    raw_bytes = glb_path.stat().st_size
    images = gltf.get("images", [])
    textures = gltf.get("textures", [])
    materials = gltf.get("materials", [])
    meshes = gltf.get("meshes", [])
    nodes = gltf.get("nodes", [])
    accessors = gltf.get("accessors", [])
    primitives = [p for mesh in meshes for p in mesh.get("primitives", [])]
    triangle_count = 0
    tangent_count = 0
    embedded_images = 0
    for image in images:
        if isinstance(image.get("bufferView"), int):
            embedded_images += 1
    for primitive in primitives:
        attrs = primitive.get("attributes", {})
        if "TANGENT" in attrs:
            tangent_count += 1
        index = primitive.get("indices")
        if isinstance(index, int) and index < len(accessors):
            triangle_count += int(accessors[index].get("count", 0)) // 3
        else:
            pos = attrs.get("POSITION")
            if isinstance(pos, int) and pos < len(accessors):
                triangle_count += int(accessors[pos].get("count", 0)) // 3

    preview = Image.open(preview_path).convert("RGB")
    mean = sum(ImageStat.Stat(preview).mean) / 3.0
    std = sum(ImageStat.Stat(preview).stddev) / 3.0
    report = {
        "status": "STRUCTURAL_PASS_VISUAL_APPROVAL_GODOT_ANDROID_AND_MAP_SNAP_REQUIRED",
        "asset": manifest.get("asset_name"),
        "geographic_status": manifest.get("geographic_status"),
        "license": manifest.get("license"),
        "glb_bytes": raw_bytes,
        "mesh_count": len(meshes),
        "node_count": len(nodes),
        "primitive_count": len(primitives),
        "triangle_count_from_glb_accessors": triangle_count,
        "material_count": len(materials),
        "texture_count": len(textures),
        "image_count": len(images),
        "embedded_image_count": embedded_images,
        "tangent_primitive_count": tangent_count,
        "facade_count": manifest.get("facade_count", 0),
        "static_material_batches": manifest.get("static_material_batches", 0),
        "preview_resolution": list(preview.size),
        "preview_mean_luminance": round(mean, 2),
        "preview_mean_channel_stddev": round(std, 2),
        "source_images_embedded": manifest.get("source_images_embedded"),
        "google_maps_3d_tiles_copied": manifest.get("google_maps_3d_tiles_copied"),
        "pbr_material_provider": polyhaven_manifest.get("provider"),
        "pbr_material_credit": polyhaven_manifest.get("provider_credit"),
        "pbr_scan_material_count": len(polyhaven_manifest.get("materials", {})),
        "road_width_reference_m": manifest.get("road_width_reference_m"),
        "limitations": manifest.get("limitations", []),
    }
    failures = []
    license_text = license_path.read_text(encoding="utf-8")
    if gltf.get("asset", {}).get("version") != "2.0":
        failures.append("Asset is not glTF 2.0")
    if not meshes or not primitives or triangle_count < 25000:
        failures.append(f"Insufficient exported geometry: meshes={len(meshes)}, triangles={triangle_count}")
    if len(materials) < 20:
        failures.append(f"Expected a varied PBR material set, found {len(materials)}")
    if len(textures) < 20 or len(images) < 20 or embedded_images != len(images):
        failures.append(f"Embedded PBR/sign texture set incomplete: textures={len(textures)}, images={len(images)}, embedded={embedded_images}")
    if len(manifest.get("facades", [])) < 10 or int(manifest.get("facade_count", 0)) < 10:
        failures.append("Expected at least ten individually art-directed market frontages")
    if int(manifest.get("static_material_batches", 0)) < 15:
        failures.append("Static mesh material batching report is missing or implausibly low")
    if raw_bytes > 130 * 1024 * 1024:
        failures.append(f"Mobile review GLB exceeds 130 MiB budget: {raw_bytes} bytes")
    if preview.size != (1600, 900):
        failures.append(f"Preview should be 1600x900, got {preview.size}")
    if mean < 24 or std < 24:
        failures.append(f"Preview appears blank/flat: mean={mean:.1f}, std={std:.1f}")
    if manifest.get("geographic_status") != "PALONG_BAZAAR_INSPIRED_CORRIDOR_STUDY_NOT_A_SURVEY":
        failures.append("Geographic status must not overstate surveyed accuracy")
    if manifest.get("source_images_embedded") is not False or manifest.get("google_maps_3d_tiles_copied") is not False:
        failures.append("Reference imagery/Google 3D data must not be embedded")
    if manifest.get("license") != "CC0-1.0" or "CC0 1.0 Universal" not in license_text:
        failures.append("Original asset licence is missing or unexpected")
    if polyhaven_manifest.get("provider") != "Poly Haven" or polyhaven_manifest.get("asset_license") != "CC0-1.0":
        failures.append("Poly Haven provider/CC0 provenance is missing or unexpected")
    if polyhaven_manifest.get("provider_credit") != "Powered by Poly Haven":
        failures.append("Required Poly Haven provider credit is missing")
    pbr_sets = polyhaven_manifest.get("materials", {})
    if len(pbr_sets) < 6:
        failures.append(f"Expected at least six photo-scanned PBR sets, found {len(pbr_sets)}")
    for material_name, pbr in pbr_sets.items():
        if pbr.get("license") != "CC0-1.0":
            failures.append(f"Poly Haven material {material_name} is missing a CC0 licence record")
        maps = pbr.get("maps", {})
        for semantic in ("base_color", "normal", "roughness"):
            record = maps.get(semantic, {})
            path = pathlib.Path(str(record.get("path", "")))
            if not path.is_file() or not record.get("md5"):
                failures.append(f"Poly Haven material {material_name} lacks verified {semantic} map file")
    if "No Google Maps/Street View" not in license_text and "No Google Maps/Street View" not in manifest_path.read_text(encoding="utf-8"):
        failures.append("Source provenance/licence statement does not exclude copied map imagery")

    if failures:
        report["status"] = "FAIL"
        report["failures"] = failures
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit("PALONG_BAZAAR_VERIFY_FAIL: " + "; ".join(failures))
    print("A2_PALONG_BAZAAR_VERIFY_PASS")
    return report


def main():
    args = args_from_cli()
    verify(args.glb, args.manifest, args.license, args.preview, args.out)


if __name__ == "__main__":
    main()
