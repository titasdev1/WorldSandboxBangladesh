#!/usr/bin/env python3
"""Structural acceptance gate for authored A-Square login/lobby GLB scenes."""
from __future__ import annotations
import argparse, json, pathlib, struct, sys

def read_glb(path: pathlib.Path):
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"glTF":
        raise ValueError(f"{path}: invalid GLB header")
    version, total = struct.unpack_from("<II", raw, 4)
    if version != 2 or total != len(raw):
        raise ValueError(f"{path}: GLB version/length mismatch")
    cursor, document, binary = 12, None, None
    while cursor + 8 <= total:
        size, kind = struct.unpack_from("<II", raw, cursor)
        cursor += 8
        chunk = raw[cursor:cursor + size]
        if len(chunk) != size:
            raise ValueError(f"{path}: truncated chunk")
        cursor += size
        if kind == 0x4E4F534A and document is None:
            document = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\0"))
        elif kind == 0x004E4942 and binary is None:
            binary = chunk
    if cursor != total or not isinstance(document, dict) or binary is None:
        raise ValueError(f"{path}: JSON/BIN chunk missing")
    return document, binary

def triangle_count(document: dict) -> int:
    accessors = document.get("accessors", [])
    total = 0
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                continue
            position_id = primitive.get("attributes", {}).get("POSITION")
            if position_id is None:
                raise ValueError("Mesh primitive has no POSITION attribute")
            vertices = int(accessors[int(position_id)].get("count", 0))
            index_id = primitive.get("indices")
            indices = int(accessors[int(index_id)].get("count", 0)) if index_id is not None else vertices
            if indices % 3:
                raise ValueError("Triangle index count is not divisible by three")
            total += indices // 3
    return total

def validate(kind: str, path: pathlib.Path) -> dict:
    doc, _binary = read_glb(path)
    meshes = doc.get("meshes", [])
    materials = doc.get("materials", [])
    textures = doc.get("textures", [])
    images = doc.get("images", [])
    animations = doc.get("animations", [])
    nodes = doc.get("nodes", [])
    cameras = doc.get("cameras", [])
    triangles = triangle_count(doc)
    errors = []
    if len(meshes) < 12:
        errors.append(f"only {len(meshes)} mesh batches; expected at least 12")
    if len(materials) < 12:
        errors.append(f"only {len(materials)} PBR materials; expected at least 12")
    if len(images) < 12 or len(textures) < 12:
        errors.append(f"only {len(images)} embedded images / {len(textures)} textures")
    if any("bufferView" not in image for image in images):
        errors.append("one or more PBR images are not embedded in the GLB binary")
    if triangles < 12000:
        errors.append(f"only {triangles} triangles; expected detailed environment geometry")
    if len(animations) < 2:
        errors.append(f"only {len(animations)} animation clips")
    if len(nodes) < 24:
        errors.append(f"only {len(nodes)} scene nodes")
    names = [str(node.get("name", "")) for node in nodes]
    manifest_path = path.with_suffix(".manifest.json")
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    operator_preview_source = str(manifest.get("operator_preview_source", ""))
    operator_preview_sha256 = str(manifest.get("operator_preview_sha256", ""))
    if not operator_preview_source or len(operator_preview_sha256) != 64:
        errors.append("the preview was not rendered with a verified rigged operator source asset")
    if manifest.get("operator_preview_removed_before_export") is not True:
        errors.append("the rigged operator preview was not removed before environment GLB export")
    if any("Field_Ranger_Preview" in str(node.get("name", "")) for node in nodes):
        errors.append("preview-only rigged operator nodes remain inside the environment GLB")
    if kind == "login":
        if not cameras:
            errors.append("login scene does not export its cinematic camera")
        if not any("Login" in name or "CNG" in name for name in names):
            errors.append("login scene is missing Bangladesh traffic/camera naming markers")
        camera_node_ids = {
            index for index, node in enumerate(nodes)
            if "Login_Cinematic_Camera" in str(node.get("name", ""))
        }
        animated_camera = any(
            int(channel.get("target", {}).get("node", -1)) in camera_node_ids
            for animation in animations
            for channel in animation.get("channels", [])
        )
        shake = manifest.get("camera_shakify", {})
        if not animated_camera:
            errors.append("login cinematic camera has no exported animated transform channel")
        if (
            shake.get("version") != "0.5.1"
            or shake.get("baked") is not True
            or shake.get("runtime_dependency") is not False
            or "Login_Dolly_Shake_Baked" not in [
                animation.get("name", "") for animation in animations
            ]
        ):
            errors.append("Camera Shakify 0.5.1 animation was not baked into a runtime-independent camera action")
    if kind == "lobby":
        if not any("Hall" in name or "Command" in name for name in names):
            errors.append("lobby scene is missing its authored command-hall structure")
        roster_previews = manifest.get("operator_preview_sources", [])
        profile_names = {str(item.get("preview_name", "")) for item in roster_previews}
        source_hashes = [str(item.get("sha256", "")) for item in roster_previews]
        required_profiles = {
            "Lobby_Field_Ranger_Preview",
            "Lobby_Delta_Recon_Preview",
            "Lobby_River_Scout_Preview",
        }
        if not required_profiles.issubset(profile_names):
            errors.append("lobby preview does not contain all three named operator profiles")
        if len(source_hashes) != 3 or len(set(source_hashes)) != 3:
            errors.append("lobby preview operator GLBs are not three distinct source assets")
    return {
        "kind": kind, "path": str(path), "bytes": path.stat().st_size,
        "node_count": len(nodes), "mesh_batch_count": len(meshes),
        "material_count": len(materials), "texture_count": len(textures),
        "embedded_image_count": sum("bufferView" in image for image in images),
        "animation_count": len(animations),
        "animation_names": [animation.get("name", "") for animation in animations],
        "camera_count": len(cameras), "triangle_count": triangles,
        "status": "FAIL" if errors else "PASS", "errors": errors,
        "visual_art_approval": "NOT_GRANTED_BY_STRUCTURAL_VALIDATION",
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("login", "lobby"), required=True)
    parser.add_argument("--glb", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = validate(args.kind, args.glb)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1 if result["status"] != "PASS" else 0

if __name__ == "__main__":
    sys.exit(main())
