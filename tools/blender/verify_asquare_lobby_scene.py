#!/usr/bin/env python3
"""Fail-closed structural verifier for the Blender-authored A-Square lobby GLB."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def read_glb(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is too small to contain a header and JSON chunk")
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total_length != len(raw):
        raise ValueError("Invalid GLB magic, version or total byte length")
    offset = 12
    document = None
    while offset + 8 <= len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset:offset + chunk_length]
        if len(chunk) != chunk_length:
            raise ValueError("GLB chunk length exceeds the file boundary")
        if chunk_type == 0x4E4F534A:
            document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
            break
        offset += chunk_length
    if not isinstance(document, dict):
        raise ValueError("GLB does not contain a readable JSON document")
    return document


def verify(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Missing lobby stage: {path}")
    document = read_glb(path)
    meshes = document.get("meshes", [])
    nodes = document.get("nodes", [])
    materials = document.get("materials", [])
    animations = document.get("animations", [])
    scenes = document.get("scenes", [])
    if len(meshes) < 8:
        raise ValueError(f"Expected at least eight material-batched meshes, only {len(meshes)} meshes")
    if len(nodes) < 12:
        raise ValueError(f"Expected stage root, batched art and animated accents, only {len(nodes)} nodes")
    if len(materials) < 8:
        raise ValueError(f"Expected authored surface families, only {len(materials)} materials")
    if not scenes:
        raise ValueError("GLB contains no scene")
    if not animations:
        raise ValueError("Lobby environment has no exported animation")
    animation_channels = sum(len(item.get("channels", [])) for item in animations)
    if animation_channels < 1:
        raise ValueError("Lobby animation has no animated channels")
    named_nodes = {str(node.get("name", "")) for node in nodes}
    expected = [
        "A_SQUARE_CINEMATIC_COMMAND_HALL",
        "ANIM | Orbit ring",
        "ANIM | Operator halo outer",
    ]
    missing = [name for name in expected if name not in named_nodes]
    if missing:
        raise ValueError("Missing authored scene elements: " + ", ".join(missing))
    triangles = 0
    accessors = document.get("accessors", [])
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            index_accessor = primitive.get("indices")
            if index_accessor is not None and index_accessor < len(accessors):
                triangles += int(accessors[index_accessor].get("count", 0)) // 3
            elif "POSITION" in primitive.get("attributes", {}):
                accessor_index = primitive["attributes"]["POSITION"]
                if accessor_index < len(accessors):
                    triangles += int(accessors[accessor_index].get("count", 0)) // 3
    if triangles < 3000:
        raise ValueError(f"Unexpectedly sparse lobby stage: {triangles} estimated triangles")
    static_batches = sum(1 for name in named_nodes if name.startswith("STATIC | "))
    if static_batches < 8:
        raise ValueError(f"Static geometry was not batched by material: only {static_batches} batches")
    extensions = set(document.get("extensionsUsed", [])) | set(document.get("extensionsRequired", []))
    if "KHR_lights_punctual" in extensions:
        raise ValueError("Mobile lobby GLB must not ship embedded punctual lights")
    return {
        "validation": "PASS",
        "asset": path.name,
        "bytes": path.stat().st_size,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "materials": len(materials),
        "animations": len(animations),
        "animation_channels": animation_channels,
        "estimated_triangles": triangles,
        "static_material_batches": static_batches,
        "draw_call_mesh_batches": len(meshes),
        "embedded_punctual_lights": 0,
        "scope": "authored environment only; live operator and UI remain in Godot",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = verify(args.glb)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("A2_LOBBY_STAGE_VERIFICATION: PASS")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
