#!/usr/bin/env python3
"""Validate the generated A-Square ram-air canopy GLB and CC0 licence."""
from __future__ import annotations

import argparse
import json
import pathlib
import struct
from typing import Any

MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
EXPECTED_ANIMATION = "A2_Parachute_Canopy_Wind_Sway"
REQUIRED_NODES = (
    "A2_RamAir_Parachute_Root",
    "Canopy_Wind_Sway_Root",
    "Canopy_28_Inflated_Fabric_Cells",
    "Main_Riser_L",
    "Main_Riser_R",
    "Harness_Seat_Pan",
    "Harness_Back_Protector",
    "Harness_Central_Buckle",
)
LICENSE_MARKER = "CC0 1.0 Universal"


def parse_glb(data: bytes) -> dict[str, Any]:
    if len(data) < 20:
        raise ValueError("GLB is shorter than its header and first chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != MAGIC or version != 2 or declared_length != len(data):
        raise ValueError("invalid GLB v2 header or declared length")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != JSON_CHUNK or chunk_length > len(data) - 20:
        raise ValueError("first GLB chunk must be a bounded JSON chunk")
    try:
        document = json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip(" \t\r\n\0"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid GLB JSON chunk: {exc}") from exc
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("GLB JSON does not declare glTF 2.0")
    return document


MIN_CANOPY_TRIANGLES = 25_000
CANOPY_ANIMATION_NODE = "Canopy_Wind_Sway_Root"


def count_glb_triangles(document: dict[str, Any]) -> int:
    """Count triangle primitives from glTF accessors, including strips and fans."""
    accessors = document.get("accessors", [])
    total = 0
    for mesh in document.get("meshes", []):
        if not isinstance(mesh, dict):
            continue
        for primitive in mesh.get("primitives", []):
            if not isinstance(primitive, dict):
                continue
            mode = int(primitive.get("mode", 4))
            if mode not in (4, 5, 6):
                continue
            if "indices" in primitive:
                accessor_index = primitive["indices"]
            else:
                accessor_index = primitive.get("attributes", {}).get("POSITION")
            if not isinstance(accessor_index, int) or not 0 <= accessor_index < len(accessors):
                raise ValueError("GLB triangle primitive references a missing accessor")
            element_count = int(accessors[accessor_index].get("count", 0))
            if mode == 4:
                if element_count % 3:
                    raise ValueError("GLB triangle-list index count is not divisible by three")
                total += element_count // 3
            else:
                total += max(0, element_count - 2)
    return total


def verify_asset(glb_path: pathlib.Path, licence_path: pathlib.Path) -> dict[str, Any]:
    # Validate the container before checking secondary metadata. This keeps a
    # corrupt GLB from being misreported as a licence or arbitrary file-size
    # problem; acceptance is based on the actual mesh, rig and animation content.
    if not glb_path.is_file():
        raise ValueError(f"parachute GLB is missing: {glb_path}")
    glb_bytes = glb_path.read_bytes()
    document = parse_glb(glb_bytes)
    if not licence_path.is_file():
        raise ValueError(f"parachute CC0 licence file is missing: {licence_path}")
    licence = licence_path.read_text(encoding="utf-8", errors="replace")
    if LICENSE_MARKER not in licence or "A-Square Ram-Air Canopy and Harness" not in licence:
        raise ValueError("generated parachute licence does not identify the original CC0 asset")
    nodes = document.get("nodes", [])
    node_names = {
        str(node.get("name", ""))
        for node in nodes
        if isinstance(node, dict)
    }
    missing = [name for name in REQUIRED_NODES if name not in node_names]
    if missing:
        raise ValueError(f"parachute GLB is missing required assembly nodes: {missing}")
    if not any(name.startswith("Suspension_Line_") for name in node_names):
        raise ValueError("parachute GLB contains no suspension lines")
    if not any(name.startswith("Riser_Carabiner_") for name in node_names):
        raise ValueError("parachute GLB contains no riser carabiners")

    animations = document.get("animations", [])
    expected_animation = next(
        (item for item in animations if isinstance(item, dict) and item.get("name") == EXPECTED_ANIMATION),
        None,
    )
    if expected_animation is None:
        raise ValueError(f"parachute GLB is missing animation {EXPECTED_ANIMATION}")
    canopy_node_indices = {
        index for index, node in enumerate(nodes)
        if isinstance(node, dict) and node.get("name") == CANOPY_ANIMATION_NODE
    }
    canopy_rotation_channels = [
        channel for channel in expected_animation.get("channels", [])
        if isinstance(channel, dict)
        and isinstance(channel.get("target"), dict)
        and channel["target"].get("node") in canopy_node_indices
        and channel["target"].get("path") == "rotation"
    ]
    if not canopy_rotation_channels:
        raise ValueError("parachute GLB has no canopy rotation animation channel")
    samplers = expected_animation.get("samplers", [])
    if any(not isinstance(channel.get("sampler"), int) or not 0 <= channel["sampler"] < len(samplers)
           for channel in canopy_rotation_channels):
        raise ValueError("parachute canopy animation channel references a missing sampler")

    meshes = document.get("meshes", [])
    if len(meshes) < 20:
        raise ValueError(f"parachute GLB has too few mesh objects: {len(meshes)}")
    triangle_count = count_glb_triangles(document)
    if triangle_count < MIN_CANOPY_TRIANGLES:
        raise ValueError(
            f"parachute GLB has too few render triangles: {triangle_count} "
            f"(minimum {MIN_CANOPY_TRIANGLES})"
        )
    if any("player" in str(node.get("name", "")).lower() for node in nodes if isinstance(node, dict)):
        raise ValueError("parachute assembly unexpectedly contains a duplicate player mesh")
    return {
        "validation": "PASS",
        "file": str(glb_path),
        "bytes": glb_path.stat().st_size,
        "node_count": len(nodes),
        "mesh_count": len(meshes),
        "triangle_count": triangle_count,
        "material_count": len(document.get("materials", [])),
        "animation_names": sorted(str(item.get("name", "")) for item in animations if isinstance(item, dict)),
        "canopy_rotation_channels": len(canopy_rotation_channels),
        "license": "CC0-1.0",
        "required_nodes": list(REQUIRED_NODES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glb", type=pathlib.Path, required=True)
    parser.add_argument("--license", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args()
    try:
        report = verify_asset(args.glb, args.license)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
