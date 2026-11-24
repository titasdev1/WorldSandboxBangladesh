#!/usr/bin/env python3
"""Fetch real, CC0 photographic PBR scan maps from Poly Haven.

This build-stage downloader uses Poly Haven's public API with a unique User-Agent,
validates every downloaded map with the API-provided MD5, and writes a provenance
manifest. The maps are used in place of procedural-noise substitutes for major
architectural/road surfaces. Bengali shop signage remains original A-Square artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import urllib.error
import urllib.request


API = "https://api.polyhaven.com"
USER_AGENT = "A-Square-WorldSandboxBangladesh-AssetPipeline/1.0 (+https://github.com/titasdev1/WorldSandboxBangladesh)"

ASSET_TARGETS = {
    "weathered_plaster": "plastered_wall_04",
    "aged_concrete": "concrete",
    "exposed_clay_brick": "worn_brick_wall",
    "wet_asphalt": "worn_asphalt",
    "galvanized_shutter": "corrugated_iron_02",
    "aged_wood": "rough_wood",
}

MAP_ALIASES = {
    "base_color": {"diffuse", "diff", "albedo", "color", "colour"},
    "normal": {"nor_gl", "normal_gl", "normal"},
    "roughness": {"rough", "roughness"},
    "metallic": {"metal", "metallic"},
    "ao": {"ao", "ambient_occlusion"},
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"Poly Haven API returned HTTP {response.status} for {url}")
        return json.loads(response.read().decode("utf-8"))


def _walk_file_records(node, path=()):
    if isinstance(node, dict):
        if isinstance(node.get("url"), str) and isinstance(node.get("md5"), str):
            yield path, node
            return
        for key, value in node.items():
            yield from _walk_file_records(value, path + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_file_records(value, path + (str(index),))


def _resolution_score(path: tuple[str, ...], preferred: str) -> tuple[int, int]:
    joined = "/".join(path).lower()
    if preferred in joined:
        pref_score = 0
    else:
        pref_score = 1
    available = next((r for r in ("16k", "8k", "4k", "2k", "1k") if r in joined), "")
    size_order = {"16k": 5, "8k": 4, "4k": 3, "2k": 2, "1k": 1, "": 0}
    return pref_score, -size_order[available]


def select_map_record(files: dict, semantic: str, preferred_resolution: str) -> tuple[str, dict]:
    aliases = MAP_ALIASES[semantic]
    candidates = []
    for path, record in _walk_file_records(files):
        lowered = [part.lower().replace("-", "_").replace(" ", "_") for part in path]
        if not any(any(alias in part for alias in aliases) for part in lowered):
            continue
        ext = next((part for part in lowered if part in {"png", "jpg", "jpeg", "exr", "tif", "tiff"}), "")
        if semantic == "base_color":
            if ext not in {"jpg", "jpeg", "png"}:
                continue
        elif semantic == "normal":
            if ext != "png":
                continue
        elif ext not in {"png", "jpg", "jpeg"}:
            continue
        candidates.append((path, record, ext))
    if not candidates:
        raise RuntimeError(f"Poly Haven API did not expose a supported {semantic} map")
    candidates.sort(key=lambda item: _resolution_score(item[0], preferred_resolution))
    path, record, ext = candidates[0]
    if "2k" not in "/".join(path).lower() and "1k" in "/".join(path).lower():
        # 1K is accepted only when the asset API has no 2K/4K/8K version.
        resolution = "1k"
    else:
        resolution = next((r for r in ("8k", "4k", "2k", "1k") if r in "/".join(path).lower()), "unknown")
    return f"{resolution}.{ext}", record


def download_verified(record: dict, destination: pathlib.Path) -> dict:
    url = str(record["url"])
    expected_md5 = str(record["md5"]).lower()
    expected_size = int(record.get("size", 0))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.md5()
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=90) as response, temp.open("wb") as output:
            if response.status != 200:
                raise RuntimeError(f"Poly Haven asset request returned HTTP {response.status}: {url}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        actual_md5 = digest.hexdigest()
        if expected_size and size != expected_size:
            raise RuntimeError(f"Size mismatch for {destination.name}: expected {expected_size}, got {size}")
        if actual_md5 != expected_md5:
            raise RuntimeError(f"MD5 mismatch for {destination.name}: expected {expected_md5}, got {actual_md5}")
        temp.replace(destination)
        return {"path": destination.as_posix(), "bytes": size, "md5": actual_md5, "source_url": url}
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def build(out: pathlib.Path, resolution: str = "2k") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    asset_catalogue = fetch_json(API + "/assets")
    provenance = {
        "schema_version": 1,
        "provider": "Poly Haven",
        "provider_credit": "Powered by Poly Haven",
        "user_agent": USER_AGENT,
        "asset_license": "CC0-1.0",
        "api_terms": "https://polyhaven.com/our-api",
        "asset_license_url": "https://polyhaven.com/license",
        "materials": {},
    }
    for material_name, asset_id in ASSET_TARGETS.items():
        metadata = asset_catalogue.get(asset_id)
        if not isinstance(metadata, dict):
            raise RuntimeError(f"Poly Haven asset ID not found in /assets catalogue: {asset_id}")
        if int(metadata.get("type", -1)) != 1:
            raise RuntimeError(f"Poly Haven asset is not a texture: {asset_id}")
        files = fetch_json(f"{API}/files/{asset_id}")
        material_folder = out / "polyhaven" / material_name
        material_folder.mkdir(parents=True, exist_ok=True)
        records = {}
        for semantic in ("base_color", "normal", "roughness"):
            selected_name, record = select_map_record(files, semantic, resolution)
            ext = selected_name.rsplit(".", 1)[-1]
            destination = material_folder / f"{semantic}.{ext}"
            downloaded = download_verified(record, destination)
            downloaded["api_map_path"] = selected_name
            records[semantic] = downloaded
        provenance["materials"][material_name] = {
            "asset_id": asset_id,
            "asset_name": metadata.get("name"),
            "description": metadata.get("description"),
            "category": metadata.get("category"),
            "authors": metadata.get("authors", {}),
            "license": "CC0-1.0",
            "texture_resolution_requested": resolution,
            "maps": records,
        }

    target = out / "polyhaven_material_manifest.json"
    target.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    print("A2_POLYHAVEN_PBR_READY:" + json.dumps({
        "provider": provenance["provider"],
        "material_count": len(provenance["materials"]),
        "map_count": sum(len(item["maps"]) for item in provenance["materials"].values()),
        "resolution": resolution,
        "manifest": target.as_posix()
    }))
    return provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--resolution", choices=("1k", "2k", "4k"), default="2k")
    args = parser.parse_args()
    build(args.out, args.resolution)


if __name__ == "__main__":
    main()
