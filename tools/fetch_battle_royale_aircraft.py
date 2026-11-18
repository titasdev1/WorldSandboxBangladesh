#!/usr/bin/env python3
"""Fetch the CC0 Cargo Plane model used by the offline solo BR deployment scene.

The source publishes a full-detail (2K) and light (1K) GLB. Both are retained so
the game can use the authored plane in the deployment cinematic and choose the
appropriate LOD on lower-memory Android devices. The original license and source
manifest are preserved beside the models.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "external_content" / "battle_royale_aircraft"
MANIFEST = OUT / "asset_manifest.json"
BASE = "https://grab3d.com/dl/cargo-plane/"
FILES = {
    "cargo_plane_high": {
        "url": BASE + "cargo-plane.glb",
        "filename": "cargo-plane.glb",
        "triangles": 29788,
        "texture_px": 2048,
        "max_bytes": 8 * 1024 * 1024,
    },
    "cargo_plane_low": {
        "url": BASE + "cargo-plane-light.glb",
        "filename": "cargo-plane-light.glb",
        "triangles": 20619,
        "texture_px": 1024,
        "max_bytes": 5 * 1024 * 1024,
    },
}
LICENSE_URL = BASE + "LICENSE.txt"
SOURCE_MANIFEST_URL = BASE + "manifest.json"
USER_AGENT = "Project-A-Square-AssetPipeline/1.0 (licensed CC0 game asset ingestion)"


def fetch_bytes(url: str, max_bytes: int) -> tuple[bytes, dict]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "grab3d.com":
        raise ValueError(f"asset URL is not on the official Grab3D HTTPS host: {url}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream,text/plain,application/json,*/*"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        final = urllib.parse.urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "grab3d.com":
            raise ValueError(f"asset redirected outside the official Grab3D host: {response.geturl()}")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"asset exceeded its {max_bytes}-byte safety cap: {url}")
        return data, {
            "url": url,
            "final_url": response.geturl(),
            "status": int(response.status),
            "content_type": response.headers.get("Content-Type", ""),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }


def parse_glb(data: bytes) -> dict:
    if len(data) < 20:
        raise ValueError("GLB is shorter than its header and JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise ValueError("GLB header/magic/version/length is invalid")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A or json_length < 2 or 20 + json_length > len(data):
        raise ValueError("GLB first chunk is not a valid JSON chunk")
    document = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\x00"))
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("GLB JSON does not declare glTF 2.0")
    nodes = [node for node in document.get("nodes", []) if isinstance(node, dict)]
    meshes = [mesh for mesh in document.get("meshes", []) if isinstance(mesh, dict)]
    names = [str(node.get("name", "")) for node in nodes]
    lower_names = [name.casefold() for name in names]
    return {
        "node_count": len(nodes),
        "mesh_count": len(meshes),
        "material_count": len(document.get("materials", [])),
        "image_count": len(document.get("images", [])),
        "named_parts": names,
        "has_ramp": any("ramp" in name for name in lower_names),
        "has_cargo_door": any("door" in name and ("cargo" in name or "plane" in name) for name in lower_names),
        "propeller_nodes": sum(1 for name in lower_names if "prop" in name),
        "wheel_nodes": sum(1 for name in lower_names if "wheel" in name),
        "skins": len(document.get("skins", [])),
    }


def write_json(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    license_bytes, license_response = fetch_bytes(LICENSE_URL, 64 * 1024)
    license_text = license_bytes.decode("utf-8", "replace")
    if "CC0 1.0 Universal" not in license_text or "creativecommons.org/publicdomain/zero/1.0" not in license_text:
        raise ValueError("downloaded asset license is not the expected CC0 1.0 text")
    (OUT / "LICENSE.txt").write_bytes(license_bytes)

    source_bytes, source_response = fetch_bytes(SOURCE_MANIFEST_URL, 128 * 1024)
    source_manifest = json.loads(source_bytes.decode("utf-8"))
    if source_manifest.get("extras", {}).get("license") != "CC0-1.0":
        raise ValueError("source manifest does not declare CC0-1.0")
    (OUT / "source_manifest.json").write_bytes(source_bytes)

    models = []
    diagnostics = {}
    for key, spec in FILES.items():
        payload, response = fetch_bytes(str(spec["url"]), int(spec["max_bytes"]))
        glb = parse_glb(payload)
        if glb["mesh_count"] < 1 or glb["node_count"] < 1:
            raise ValueError(f"{key} contains no usable mesh/node scene")
        if key == "cargo_plane_high" and not glb["has_ramp"]:
            raise ValueError("full-detail cargo plane is missing the source-described rear cargo ramp node")
        destination = OUT / str(spec["filename"])
        destination.write_bytes(payload)
        record = {
            "name": key,
            "file": str(spec["filename"]),
            "path": "res://external_content/battle_royale_aircraft/" + str(spec["filename"]),
            "format": "glb",
            "lod": "high" if key == "cargo_plane_high" else "light",
            "license": "CC0-1.0",
            "triangles_source_reported": int(spec["triangles"]),
            "texture_px_source_reported": int(spec["texture_px"]),
            "bytes": len(payload),
            "sha256": response["sha256"],
            "source_response": response,
            "gltf_validation": {k: v for k, v in glb.items() if k != "named_parts"},
        }
        models.append(record)
        diagnostics[key] = record["gltf_validation"]
        print("BATTLE_ROYALE_AIRCRAFT_LOD_READY:", json.dumps(record, sort_keys=True))

    manifest = {
        "schema_version": 1,
        "available": True,
        "source": "https://grab3d.com/models/vehicles/cargo-plane",
        "creator": "Grab3D",
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution_required": False,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "asset_purpose": "offline solo BR plane entry, flyover and parachute deployment sequence",
        "model_count": len(models),
        "models": models,
        "source_manifest_response": source_response,
        "license_response": license_response,
        "authored_parts": {
            "rear_ramp_node": "cargo-plane_cargo_ramp",
            "rear_door_node": "cargo-plane_cargo_door",
            "four_separate_propellers": True,
            "six_separate_wheels": True,
            "ramp_animation": "close around local X by 28.4 degrees before flight",
            "door_animation": "close around local X by 40 degrees before flight",
        },
        "notes": [
            "Original CC0 aircraft model, not copied from a commercial game.",
            "Full 2K / 29,788-triangle model is reserved for the active BR deployment scene.",
            "Light 1K / 20,619-triangle model is available for distant LOD and lower-memory devices.",
            "Propeller and landing gear animations must be driven in Godot; model parts are separate authored nodes.",
        ],
    }
    write_json(MANIFEST, manifest)
    print("BATTLE_ROYALE_AIRCRAFT_MANIFEST_READY:", json.dumps({
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "model_count": len(models),
        "high": diagnostics["cargo_plane_high"],
        "low": diagnostics["cargo_plane_low"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
