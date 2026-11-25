#!/usr/bin/env python3
"""Validate three genuinely distinct Ara 3D Gen operator models and their LODs.

The existing single-operator verifier remains the per-model structural gate.
This roster gate additionally compares the baked POSITION buffers so three
different file names or material palettes cannot masquerade as three people.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

from verify_ara_glb import inspect

DETAILS = ("high", "medium", "low")
MIN_TRIANGLES = {"high": 60_000, "medium": 30_000, "low": 20_000}
REQUIRED_GROUPS = ("idle", "walk", "run", "sprint", "jump", "rifle", "aim", "fire", "reload")


def read_glb(path: Path) -> tuple[dict, bytes]:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError(f"{path}: not a GLB file")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise ValueError(f"{path}: invalid GLB header")
    cursor = 12
    document = None
    binary = None
    while cursor + 8 <= declared_length:
        chunk_length, chunk_type = struct.unpack_from("<II", data, cursor)
        cursor += 8
        end = cursor + chunk_length
        if end > declared_length:
            raise ValueError(f"{path}: GLB chunk exceeds file bounds")
        chunk = data[cursor:end]
        cursor = end
        if chunk_type == 0x4E4F534A and document is None:
            document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\0"))
        elif chunk_type == 0x004E4942 and binary is None:
            binary = chunk
    if cursor != declared_length or not isinstance(document, dict) or binary is None:
        raise ValueError(f"{path}: incomplete JSON/BIN GLB")
    return document, binary


def geometry_signature(path: Path) -> str:
    """Hash baked vertex positions, excluding names and materials."""
    document, binary = read_glb(path)
    accessors = document.get("accessors", [])
    views = document.get("bufferViews", [])
    digest = hashlib.sha256()
    position_streams = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            accessor_index = primitive.get("attributes", {}).get("POSITION")
            if accessor_index is None:
                continue
            accessor = accessors[int(accessor_index)]
            if accessor.get("componentType") != 5126 or accessor.get("type") != "VEC3":
                raise ValueError(f"{path}: POSITION accessor must be float32 VEC3")
            view = views[int(accessor["bufferView"])]
            start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
            count = int(accessor.get("count", 0))
            stride = int(view.get("byteStride", 12))
            if stride < 12 or count <= 0:
                raise ValueError(f"{path}: invalid POSITION accessor layout")
            end = start + (count - 1) * stride + 12
            if start < 0 or end > len(binary):
                raise ValueError(f"{path}: POSITION data exceeds binary chunk")
            if stride == 12:
                digest.update(binary[start:end])
            else:
                for index in range(count):
                    offset = start + index * stride
                    digest.update(binary[offset:offset + 12])
            position_streams += 1
    if position_streams == 0:
        raise ValueError(f"{path}: no POSITION geometry found")
    return digest.hexdigest()


def find_one(directory: Path) -> Path:
    matches = sorted(directory.glob("*.glb"))
    if len(matches) != 1:
        raise ValueError(f"{directory}: expected exactly one GLB, found {len(matches)}")
    if matches[0].stat().st_size <= 0:
        raise ValueError(f"{matches[0]}: empty GLB")
    return matches[0]


def validate_variant(detail: str, path: Path) -> dict:
    report = inspect(path)
    errors = []
    if report["triangles"] < MIN_TRIANGLES[detail]:
        errors.append(f"{detail}: only {report['triangles']} triangles; minimum {MIN_TRIANGLES[detail]}")
    if report["mesh_count"] <= 0 or report["primitive_count"] <= 0:
        errors.append(f"{detail}: no renderable geometry")
    if report["materials"] <= 0 or report["textures"] <= 0 or report["images"] <= 0:
        errors.append(f"{detail}: textured materials/images are missing")
    if report["max_joint_count"] < 60 or report["skins"] <= 0:
        errors.append(f"{detail}: full skinned game rig is missing")
    if not report["weapon_socket"]:
        errors.append(f"{detail}: WeaponR socket is missing")
    if report["animation_count"] < 100:
        errors.append(f"{detail}: only {report['animation_count']} animation clips")
    missing = [key for key, present in report["required_animation_groups"].items() if not present]
    if missing:
        errors.append(f"{detail}: missing animation groups: {', '.join(missing)}")
    if report["facial_morph_targets"] <= 0:
        errors.append(f"{detail}: facial blend shapes are missing")
    if errors:
        raise ValueError("; ".join(errors))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="artifact root containing <operator_id>/<detail>/*.glb")
    parser.add_argument("--roster", required=True, type=Path, help="roster.json with exactly three operator profiles")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    roster_doc = json.loads(args.roster.read_text(encoding="utf-8"))
    operators = roster_doc.get("operators", [])
    errors = []
    if roster_doc.get("required_operator_count") != 3 or len(operators) != 3:
        errors.append("roster must declare exactly three operators")
    ids = [str(item.get("id", "")) for item in operators]
    if len(set(ids)) != 3 or any(not item for item in ids):
        errors.append("operator IDs must be three non-empty unique values")

    reports = []
    signatures = {}
    for operator in operators:
        operator_id = str(operator.get("id", ""))
        name = str(operator.get("name", ""))
        if not operator_id or not name:
            errors.append("each roster entry requires an id and display name")
            continue
        profile_path = Path(str(operator.get("profile", "")))
        if not profile_path.is_file():
            errors.append(f"{operator_id}: profile file is missing: {profile_path}")
            continue
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if profile.get("name") != f"asquare_operator_{operator_id}":
            errors.append(f"{operator_id}: profile name does not match roster identity")
            continue
        detail_reports = {}
        files = {}
        for detail in DETAILS:
            try:
                model_path = find_one(args.root / operator_id / detail)
                detail_reports[detail] = validate_variant(detail, model_path)
                files[detail] = {
                    "path": str(model_path.relative_to(args.root)),
                    "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
                    "bytes": model_path.stat().st_size,
                    "triangles": detail_reports[detail]["triangles"],
                    "materials": detail_reports[detail]["materials"],
                    "textures": detail_reports[detail]["textures"],
                    "joint_count": detail_reports[detail]["max_joint_count"],
                    "animation_count": detail_reports[detail]["animation_count"],
                    "weapon_socket": detail_reports[detail]["weapon_socket"],
                    "facial_morph_targets": detail_reports[detail]["facial_morph_targets"],
                }
            except (OSError, ValueError, KeyError, IndexError) as exc:
                errors.append(f"{operator_id}/{detail}: {exc}")
        if len(detail_reports) == 3:
            if not (detail_reports["high"]["triangles"] > detail_reports["medium"]["triangles"] > detail_reports["low"]["triangles"]):
                errors.append(f"{operator_id}: high/medium/low triangle LOD ordering is invalid")
            try:
                signature = geometry_signature(args.root / operator_id / "high" / Path(files["high"]["path"]).name)
                signatures[operator_id] = signature
                files["high"]["geometry_sha256"] = signature
            except (OSError, ValueError, KeyError) as exc:
                errors.append(f"{operator_id}: geometry signature failed: {exc}")
        reports.append({
            "id": operator_id,
            "name": name,
            "role": operator.get("role", ""),
            "description": operator.get("description", ""),
            "profile": str(profile_path),
            "variants": files,
        })

    if len(signatures) == 3 and len(set(signatures.values())) != 3:
        errors.append("the three high-detail operators do not have three distinct baked geometry signatures")

    summary = {
        "generator": "Ara 3D Gen",
        "generator_commit": roster_doc.get("generator_commit", ""),
        "roster_count": len(reports),
        "roster": reports,
        "geometry_signatures_unique": len(signatures) == 3 and len(set(signatures.values())) == 3,
        "validation": "FAIL" if errors else "PASS",
        "errors": errors,
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
