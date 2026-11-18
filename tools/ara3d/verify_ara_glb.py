#!/usr/bin/env python3
"""Structural and animation-content validation for Ara 3D Gen GLB exports."""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


def load_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError(f"{path}: not a GLB file")
    version, length = struct.unpack_from("<II", data, 4)
    if version != 2 or length != len(data):
        raise ValueError(f"{path}: invalid GLB header (version={version}, length={length}, actual={len(data)})")
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or 20 + chunk_len > len(data):
        raise ValueError(f"{path}: first chunk is not valid JSON")
    return json.loads(data[20 : 20 + chunk_len].decode("utf-8").rstrip(" \t\r\n\0"))


def inspect(path: Path) -> dict:
    doc = load_glb(path)
    accessors = doc.get("accessors", [])
    meshes = doc.get("meshes", [])
    primitives = [p for m in meshes for p in m.get("primitives", [])]
    triangles = 0
    for primitive in primitives:
        if primitive.get("mode", 4) != 4:
            continue
        if "indices" in primitive:
            count = int(accessors[primitive["indices"]].get("count", 0))
        else:
            count = int(accessors[primitive["attributes"]["POSITION"]].get("count", 0))
        triangles += count // 3
    skins = doc.get("skins", [])
    joint_counts = [len(s.get("joints", [])) for s in skins]
    nodes = doc.get("nodes", [])
    node_names = {str(n.get("name", "")) for n in nodes}
    animations = doc.get("animations", [])
    animation_names = [str(a.get("name", "")) for a in animations]
    folded_names = [n.casefold() for n in animation_names]
    targets = sum(len(p.get("targets", [])) for p in primitives)
    textures = len(doc.get("textures", []))
    images = len(doc.get("images", []))
    materials = len(doc.get("materials", []))
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "triangles": triangles,
        "mesh_count": len(meshes),
        "primitive_count": len(primitives),
        "materials": materials,
        "textures": textures,
        "images": images,
        "skins": len(skins),
        "max_joint_count": max(joint_counts, default=0),
        "weapon_socket": "WeaponR" in node_names,
        "facial_morph_targets": targets,
        "animation_count": len(animations),
        "required_animation_groups": {
            key: any(key in name for name in folded_names)
            for key in ("idle", "walk", "run", "sprint", "jump", "rifle", "aim", "fire", "reload")
        },
        "animation_names": animation_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--high", required=True, type=Path)
    parser.add_argument("--medium", required=True, type=Path)
    parser.add_argument("--low", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    reports = {detail: inspect(path) for detail, path in (
        ("high", args.high), ("medium", args.medium), ("low", args.low)
    )}
    errors = []
    for detail, report in reports.items():
        if report["triangles"] <= 0 or report["mesh_count"] <= 0:
            errors.append(f"{detail}: missing renderable geometry")
        if report["materials"] <= 0 or report["textures"] <= 0 or report["images"] <= 0:
            errors.append(f"{detail}: expected textured materials are missing")
        if report["max_joint_count"] < 60:
            errors.append(f"{detail}: expected the full game skeleton, found {report['max_joint_count']} joints")
        if not report["weapon_socket"]:
            errors.append(f"{detail}: WeaponR socket is missing")
        if report["animation_count"] < 100:
            errors.append(f"{detail}: expected a substantial animation library, found {report['animation_count']} clips")
        missing = [k for k, ok in report["required_animation_groups"].items() if not ok]
        if missing:
            errors.append(f"{detail}: missing animation groups: {', '.join(missing)}")
        if report["facial_morph_targets"] <= 0:
            errors.append(f"{detail}: no facial morph targets exported")

    if reports["high"]["triangles"] <= reports["medium"]["triangles"]:
        errors.append("LOD order: high-detail model is not more detailed than medium")
    if reports["medium"]["triangles"] <= reports["low"]["triangles"]:
        errors.append("LOD order: medium-detail model is not more detailed than low")

    summary = {
        "generator": "Ara 3D Gen",
        "generator_commit": "4122e90633fda0384c6611115b64a15102e5463d",
        "profile": "A-Square Bangladesh-style tactical operator",
        "validation": "FAIL" if errors else "PASS",
        "errors": errors,
        "variants": reports,
        "license": {
            "generator_code": "MIT",
            "MakeHuman_character_data": "CC0 1.0",
            "motion_capture": "CMU Graphics Lab Motion Capture Database; attribution required, not for resale as a standalone motion asset"
        }
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
