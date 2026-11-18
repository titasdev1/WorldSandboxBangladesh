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


def verify_asset(glb_path: pathlib.Path, licence_path: pathlib.Path) -> dict[str, Any]:
    # Validate the container before checking secondary metadata. This keeps a
    # corrupt GLB from being misreported as a licence or arbitrary file-size
    # problem, and lets structural checks—not a guessed byte threshold—decide
    # whether the exported canopy contains the required assembly.
    if not glb_path.is_file():
        raise ValueError(f"parachute GLB is missing: {glb_path}")
    glb_bytes = glb_path.read_bytes()
    document = parse_glb(glb_bytes)
    if not licence_path.is_file():
        raise ValueError(f"parachute CC0 licence file is missing: {licence_path}")
    licence = licence_path.read_text(encoding="utf-8", errors="replace")
    if LICENSE_MARKER not in licence or "A-Square Ram-Air Canopy and Harness" not in licence:
        raise ValueError("generated parachute licence does not identify the original CC0 asset")
    node_names = {
        str(node.get("name", ""))
        for node in document.get("nodes", [])
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
    animation_names = {
        str(animation.get("name", ""))
        for animation in animations
        if isinstance(animation, dict)
    }
    if EXPECTED_ANIMATION not in animation_names:
        raise ValueError(f"parachute GLB is missing animation {EXPECTED_ANIMATION}")
    meshes = document.get("meshes", [])
    if len(meshes) < 20:
        raise ValueError(f"parachute GLB has too few mesh objects: {len(meshes)}")
    if any("player" in str(node.get("name", "")).lower() for node in document.get("nodes", []) if isinstance(node, dict)):
        raise ValueError("parachute assembly unexpectedly contains a duplicate player mesh")
    return {
        "validation": "PASS",
        "file": str(glb_path),
        "bytes": glb_path.stat().st_size,
        "node_count": len(document.get("nodes", [])),
        "mesh_count": len(meshes),
        "material_count": len(document.get("materials", [])),
        "animation_names": sorted(animation_names),
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
