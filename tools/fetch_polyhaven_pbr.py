#!/usr/bin/env python3
"""Fetch a small, curated set of CC0 4K PBR surface maps from Poly Haven.

Only actual authored texture maps are downloaded. If the public API is unavailable,
the game continues with its existing procedural materials.
"""
from __future__ import annotations
import io
import json
import pathlib
import re
import urllib.parse
import urllib.request

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "external_content" / "polyhaven_pbr"
MANIFEST = OUT / "asset_manifest.json"
API = "https://api.polyhaven.com"
USER_AGENT = "WorldSandboxBangladesh-AssetBuilder/1.0 (+https://github.com/titasdev1/WorldSandboxBangladesh)"
GROUPS = {
    "road": ["asphalt", "road", "pavement"],
    "brick": ["brick", "masonry"],
    "concrete": ["concrete", "cement"],
    "plaster": ["plaster", "stucco", "painted wall"],
    "metal": ["metal plate", "metal sheet", "steel"],
    "wood": ["wood planks", "timber", "wood"],
    "ground": ["mud", "dirt", "gravel", "soil"],
}
MAP_WORDS = {
    "albedo": ("diffuse", "albedo", "basecolor", "base_color", "color"),
    "normal": ("nor_gl", "normal", "normalgl", "normal_dx"),
    "roughness": ("rough",),
    "metallic": ("metal",),
    "ao": ("ambient_occlusion", "ambient occlusion"),
    "height": ("displacement", "disp", "height"),
}

def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))

def get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()

def optimize_texture_payload(payload: bytes, surface: str, kind: str, source_suffix: str) -> tuple[bytes, str, dict]:
    """Cap dimensions and store colour/scalar maps compactly for Android packs."""
    with Image.open(io.BytesIO(payload)) as source:
        image = source.copy()
        if surface == "road" and kind == "albedo":
            cap = 4096
        elif kind in {"roughness", "metallic", "ao", "height"}:
            cap = 1024
        else:
            cap = 2048
        original_size = list(image.size)
        if max(image.size) > cap:
            ratio = cap / max(image.size)
            target = (
                max(1, round(image.width * ratio)),
                max(1, round(image.height * ratio)),
            )
            image = image.resize(target, Image.Resampling.LANCZOS)

        if kind in {"roughness", "metallic", "ao", "height"}:
            image = image.convert("L")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=91, optimize=True, progressive=True)
            suffix = ".jpg"
        elif kind == "albedo":
            image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=93, optimize=True, progressive=True)
            suffix = ".jpg"
        elif source_suffix in {".jpg", ".jpeg", ".webp"}:
            image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=96, optimize=True, progressive=True)
            suffix = ".jpg"
        else:
            image = image.convert("RGB")
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=True)
            suffix = ".png"
        result = output.getvalue()
        return result, suffix, {
            "original_bytes": len(payload),
            "optimized_bytes": len(result),
            "original_dimensions": original_size,
            "optimized_dimensions": list(image.size),
            "format": suffix.lstrip("."),
        }

def describe(item: dict) -> str:
    fields = [item.get("name", ""), item.get("description", ""), item.get("category", "")]
    fields.extend(item.get("tags", []) if isinstance(item.get("tags"), list) else [])
    return " ".join(str(x) for x in fields).lower().replace("_", " ")

def choose_assets(catalog: dict) -> dict:
    chosen = {}
    for surface, keywords in GROUPS.items():
        ranked = []
        for asset_id, item in catalog.items():
            if not isinstance(item, dict):
                continue
            text = (str(asset_id) + " " + describe(item)).lower().replace("_", " ")
            score = sum(3 if key in str(asset_id).lower().replace("_", " ") else 1 for key in keywords if key in text)
            if score:
                ranked.append((score, str(asset_id), item))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        if ranked:
            chosen[surface] = (ranked[0][1], ranked[0][2])
    return chosen

def leaves(node, path=()):
    if isinstance(node, dict):
        if isinstance(node.get("url"), str):
            yield path, node
        else:
            for key, value in node.items():
                yield from leaves(value, path + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from leaves(value, path + (str(index),))

def map_kind(path) -> str | None:
    joined = "/".join(path).lower()
    tokens = set(re.findall(r"[a-z0-9]+", joined))
    # AO is commonly a standalone channel name; matching the substring "ao"
    # would also misclassify unrelated filenames.
    if "ao" in tokens or "occlusion" in tokens or "ambientocclusion" in joined:
        return "ao"
    for kind, words in MAP_WORDS.items():
        if kind == "ao":
            continue
        if any(word in joined for word in words):
            return kind
    return None


def resolution_score(path, surface: str, kind: str | None = None) -> int:
    """Rank mobile-budget maps; only road base-colour may use the 4K tier."""
    joined = "/".join(path).lower()
    allowed = ("4k", "2k", "1k", "512") if surface == "road" and kind in (None, "albedo") else ("2k", "1k", "512")
    for rank, resolution in enumerate(allowed):
        if resolution in joined:
            return rank
    return 99

def write_manifest(surfaces: dict, note: str = "") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "available": bool(surfaces),
        "source": "https://polyhaven.com/",
        "api": API,
        "license": "CC0-1.0",
        "attribution_required_for_downloaded_assets": False,
        "resolution_policy": "Mobile bundle: road albedo up to 4K; other albedo/normal maps up to 2K; scalar roughness/metallic/AO/height maps capped at 1K. 8K maps are excluded.",
        "surfaces": surfaces,
        "note": note,
    }, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    surfaces = {}
    try:
        catalog = get_json(API + "/assets?type=textures")
        selected = choose_assets(catalog)
        for surface, (asset_id, metadata) in selected.items():
            try:
                files = get_json(API + "/files/" + urllib.parse.quote(asset_id, safe=""))
                candidates = {}
                for path, item in leaves(files):
                    kind = map_kind(path)
                    if not kind:
                        continue
                    url = str(item["url"])
                    suffix = pathlib.PurePosixPath(urllib.parse.urlparse(url).path).suffix.lower()
                    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
                        continue
                    score = resolution_score(path, surface, kind)
                    if score < 99:
                        candidates.setdefault(kind, []).append((score, path, url, suffix))
                maps = {}
                map_optimizations = {}
                for kind, options in candidates.items():
                    options.sort(key=lambda row: (row[0], len(row[1])))
                    rank, path, url, suffix = options[0]
                    if rank > 3:
                        continue
                    raw_payload = get_bytes(url)
                    if not raw_payload or len(raw_payload) < 1024:
                        continue
                    payload, optimized_suffix, optimization = optimize_texture_payload(
                        raw_payload, surface, kind, suffix
                    )
                    filename = kind + optimized_suffix
                    destination = OUT / asset_id / filename
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(payload)
                    maps[kind] = "res://" + destination.relative_to(ROOT).as_posix()
                    map_optimizations[kind] = optimization
                if "albedo" in maps:
                    surfaces[surface] = {
                        "asset_id": asset_id,
                        "name": str(metadata.get("name", asset_id)),
                        "source_url": "https://polyhaven.com/a/" + asset_id,
                        "license": "CC0-1.0",
                        "maps": maps,
                        "map_optimizations": map_optimizations,
                    }
                    print(f"Prepared {surface}: {asset_id} ({', '.join(sorted(maps))})")
            except Exception as exc:
                print(f"WARNING: could not prepare {surface} texture: {exc}")
        write_manifest(surfaces, "Only downloaded CC0 files are included; road albedo is capped at 4K, other albedo/normal maps at 2K, scalar roughness/metallic/AO/height maps at 1K. Normal maps remain lossless where sourced as PNG.")
        print(f"Poly Haven CC0 PBR surfaces prepared: {len(surfaces)}")
        return 0
    except Exception as exc:
        write_manifest({}, "Optional download unavailable; procedural materials remain active. " + str(exc)[:300])
        print(f"WARNING: Poly Haven API unavailable; using procedural materials: {exc}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
