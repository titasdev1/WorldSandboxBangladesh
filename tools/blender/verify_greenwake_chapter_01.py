#!/usr/bin/env python3
"""Fail-closed structural and provenance verifier for Greenwake Chapter 01 GLB."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


REQUIRED_NODES = [
    "GW_Tidal_Floodplain_and_Ridge_Terrain",
    "GW_River_Rupjhora_Monsoon_Channel",
    "GW_CustomsHouse_MainVolume",
    "GW_Jetty_DeckPlank_00_0",
    "GW_RopeBridge_Deck_00",
    "GW_Sluice_GateLeaf",
    "GW_Archive_LedgerPedestal",
    "GW_MangroveTrunk_00",
    "GW_RiverSignal_Vane",
]


def read_glb(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is too small to contain a valid header")
    magic, version, total = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total != len(raw):
        raise ValueError("GLB header, version or file length is invalid")
    offset = 12
    doc = None
    while offset + 8 <= len(raw):
        length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset:offset + length]
        if len(chunk) != length:
            raise ValueError("GLB chunk extends beyond the file")
        if chunk_type == 0x4E4F534A:
            doc = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
            break
        offset += length
    if not isinstance(doc, dict):
        raise ValueError("GLB JSON document is missing")
    return doc


def triangle_count(doc: dict) -> int:
    accessors = doc.get("accessors", [])
    total = 0
    for mesh in doc.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            idx = primitive.get("indices")
            if isinstance(idx, int) and 0 <= idx < len(accessors):
                total += int(accessors[idx].get("count", 0)) // 3
            else:
                pos = primitive.get("attributes", {}).get("POSITION")
                if isinstance(pos, int) and 0 <= pos < len(accessors):
                    total += int(accessors[pos].get("count", 0)) // 3
    return total


def verify(glb: Path, manifest_path: Path, preview: Path | None = None) -> dict:
    if not glb.is_file() or not manifest_path.is_file():
        raise ValueError("Required Greenwake GLB or manifest is missing")
    doc = read_glb(glb)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    nodes = doc.get("nodes", [])
    meshes = doc.get("meshes", [])
    materials = doc.get("materials", [])
    animations = doc.get("animations", [])
    scenes = doc.get("scenes", [])
    names = {str(n.get("name", "")) for n in nodes}

    if manifest.get("asset_id") != "greenwake_chapter_01_rupjhora_lost_port":
        raise ValueError("Unexpected Greenwake asset ID")
    if manifest.get("family") != "GREENWAKE" or manifest.get("chapter") != 1:
        raise ValueError("GLB is not assigned to Greenwake Chapter 01")
    if manifest.get("fictional_composite") is not True or manifest.get("surveyed_location") is not False:
        raise ValueError("The fictional/surveyed status must be explicit and fail-closed")
    if manifest.get("historic_claim") is not False or manifest.get("geospatial_coordinates") is not None:
        raise ValueError("Do not make unsupported historical or geographic claims")
    if manifest.get("gameplay_state") != "NOT_YET_INTEGRATED_OR_PLAYABLE":
        raise ValueError("The authoring artifact must not claim to be a playable chapter")
    if "AI generated" not in manifest.get("source_policy", ""):
        raise ValueError("Source policy must explicitly exclude AI-generated substitute art")
    if not scenes or len(nodes) < 80 or len(meshes) < 20 or len(materials) < 12:
        raise ValueError("Environment scene is too sparse for a chapter art-study export")

    missing = [n for n in REQUIRED_NODES if n not in names]
    if missing:
        raise ValueError("Missing named hero/environment structures: " + ", ".join(missing))
    triangles = triangle_count(doc)
    if triangles < 20000:
        raise ValueError(f"Environment mesh density unexpectedly low: {triangles} triangles")
    channels = sum(len(a.get("channels", [])) for a in animations)
    if not animations or channels < 2:
        raise ValueError("Environment animation channels are missing")
    # Require licensed photographic surface maps to be embedded in the GLB. The
    # image bytes must travel with the asset; no file:// or remote texture paths.
    pbr = manifest.get("pbr_provenance", {})
    pbr_materials = pbr.get("materials", {})
    expected_pbr_materials = {"stone", "stone_trim", "brick", "limewash", "timber", "wet_timber", "crate", "iron"}
    if pbr.get("provider") != "Poly Haven" or pbr.get("license") != "CC0-1.0":
        raise ValueError("Greenwake hero materials must carry verified Poly Haven CC0 provenance")
    if not expected_pbr_materials.issubset(set(pbr_materials)):
        raise ValueError("One or more required Greenwake surfaces lack a CC0 PBR assignment")
    for key, record in pbr_materials.items():
        if record.get("license") != "CC0-1.0" or len(record.get("maps", {})) != 3:
            raise ValueError(f"Invalid PBR provenance for material {key}")
        if not record.get("asset_id") or not record.get("authors"):
            raise ValueError(f"Missing source identity/author for PBR material {key}")
        for map_record in record["maps"].values():
            if not map_record.get("md5") or int(map_record.get("bytes", 0)) <= 0:
                raise ValueError(f"Missing verified hash/size for PBR material {key}")

    images = doc.get("images", [])
    external_images = [
        image.get("uri") for image in images
        if isinstance(image.get("uri"), str) and not image["uri"].startswith("data:")
    ]
    if external_images:
        raise ValueError("Unexpected external image dependencies in the GLB")
    if len(images) < 18 or any("bufferView" not in image and not str(image.get("uri", "")).startswith("data:") for image in images):
        raise ValueError("The exported GLB does not embed all verified PBR image maps")
    if preview is not None and (not preview.is_file() or preview.stat().st_size < 10000):
        raise ValueError("Rendered preview PNG is missing or implausibly small")

    return {
        "validation": "PASS",
        "asset": glb.name,
        "bytes": glb.stat().st_size,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "materials": len(materials),
        "triangles": triangles,
        "animations": len(animations),
        "animation_channels": channels,
        "external_image_references": 0,
        "embedded_pbr_images": len(doc.get("images", [])),
        "pbr_provider": pbr.get("provider"),
        "pbr_license": pbr.get("license"),
        "pbr_material_assignments": sorted(pbr_materials),
        "fictional_composite": True,
        "playable": False,
        "required_nodes": REQUIRED_NODES,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=False)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.glb, args.manifest, args.preview)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GREENWAKE_CH01_VERIFICATION: PASS")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
