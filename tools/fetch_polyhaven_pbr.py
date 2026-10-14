#!/usr/bin/env python3
"""Fetch a small, curated set of CC0 4K PBR surface maps from Poly Haven.

Only actual authored texture maps are downloaded. If the public API is unavailable,
the game continues with its existing procedural materials.
"""
from __future__ import annotations
import json
import pathlib
import re
import urllib.parse
import urllib.request

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
}

def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.loads(response.read().decode("utf-8"))

def get_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()

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
    for kind, words in MAP_WORDS.items():
        if any(word in joined for word in words):
            return kind
    return None

def resolution_score(path, surface: str) -> int:
    joined = "/".join(path).lower()
    preferred = ("8k", "8k") if surface == "road" else ("4k", "4k")
    if preferred[0] in joined:
        return 0
    if "4k" in joined:
        return 1
    if "2k" in joined:
        return 2
    if "1k" in joined:
        return 3
    return 9

def write_manifest(surfaces: dict, note: str = "") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps({
        "available": bool(surfaces),
        "source": "https://polyhaven.com/",
        "api": API,
        "license": "CC0-1.0",
        "attribution_required_for_downloaded_assets": False,
        "resolution_policy": "Prefer 4K PBR maps; prefer 8K for road surfaces when available.",
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
                    candidates.setdefault(kind, []).append((resolution_score(path, surface), path, url, suffix))
                maps = {}
                for kind, options in candidates.items():
                    options.sort(key=lambda row: (row[0], len(row[1])))
                    rank, path, url, suffix = options[0]
                    if rank > 3:
                        continue
                    filename = kind + suffix
                    destination = OUT / asset_id / filename
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    payload = get_bytes(url)
                    if not payload or len(payload) < 1024:
                        continue
                    destination.write_bytes(payload)
                    maps[kind] = "res://" + destination.relative_to(ROOT).as_posix()
                if "albedo" in maps:
                    surfaces[surface] = {
                        "asset_id": asset_id,
                        "name": str(metadata.get("name", asset_id)),
                        "source_url": "https://polyhaven.com/a/" + asset_id,
                        "license": "CC0-1.0",
                        "maps": maps,
                    }
                    print(f"Prepared {surface}: {asset_id} ({', '.join(sorted(maps))})")
            except Exception as exc:
                print(f"WARNING: could not prepare {surface} texture: {exc}")
        write_manifest(surfaces, "Only downloaded CC0 files are included; missing maps use procedural fallbacks.")
        print(f"Poly Haven CC0 PBR surfaces prepared: {len(surfaces)}")
        return 0
    except Exception as exc:
        write_manifest({}, "Optional download unavailable; procedural materials remain active. " + str(exc)[:300])
        print(f"WARNING: Poly Haven API unavailable; using procedural materials: {exc}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
