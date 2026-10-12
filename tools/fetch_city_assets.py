#!/usr/bin/env python3
"""Fetch official Kenney CC0 city-building packs for the Android build.

Downloads only authored assets and their dependencies. Every pack is optional:
if upstream is unavailable, the procedural world remains playable.
"""
from __future__ import annotations
import html
import json
import pathlib
import re
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKS = [
    ("city-kit-suburban", "https://kenney.nl/assets/city-kit-suburban", "https://kenney.nl/assets/city-kit-suburban"),
    ("city-kit-commercial", "https://kenney.nl/assets/city-kit-commercial", "https://kenney.nl/assets/city-kit-commercial"),
    ("city-kit-industrial", "https://kenney.nl/assets/city-kit-industrial", "https://kenney.nl/assets/city-kit-industrial"),
]
ALLOWED = {".gltf", ".glb", ".bin", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".license"}

def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "WorldSandboxBangladesh-CC0-AssetBuilder/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()

def find_zip(page: str, slug: str) -> str:
    page = html.unescape(page)
    patterns = [
        rf"""https?://(?:www[.])?kenney[.]nl/media/pages/assets/{re.escape(slug)}/[^\\s"'<>]+?[.]zip""",
        rf"""["']([^"']*media/pages/assets/{re.escape(slug)}/[^"']+?[.]zip)["']""",
        r"""href=["']([^"']+?[.]zip)["']""",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, page, flags=re.I):
            url = match if isinstance(match, str) else match[0]
            if url.startswith("//"):
                url = "https:" + url
            elif url.startswith("/"):
                url = "https://kenney.nl" + url
            if url.startswith("http") and url.lower().endswith(".zip"):
                return url
    raise RuntimeError("Official page did not expose a direct ZIP link; no guessed URL was used.")

def process_pack(slug: str, page_url: str, source_url: str) -> dict:
    out = ROOT / "external_content" / ("kenney_" + slug.replace("-", "_"))
    out.mkdir(parents=True, exist_ok=True)
    try:
        page = get(page_url).decode("utf-8", "replace")
        zip_url = find_zip(page, slug)
        payload = get(zip_url)
        if not payload.startswith(b"PK"):
            raise ValueError("official download did not return a ZIP archive")
        extracted = []
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(payload)
            tmp.flush()
            with zipfile.ZipFile(tmp.name) as archive:
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    rel = pathlib.PurePosixPath(item.filename)
                    if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() not in ALLOWED:
                        continue
                    destination = out.joinpath(*rel.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as src, destination.open("wb") as dst:
                        dst.write(src.read())
                    extracted.append(destination)
        models = []
        for path in sorted(extracted):
            if path.suffix.lower() not in {".gltf", ".glb"}:
                continue
            models.append({
                "name": path.stem,
                "path": "res://" + path.relative_to(ROOT).as_posix(),
                "format": path.suffix.lower()[1:],
            })
        if not models:
            raise ValueError("downloaded pack had no GLTF/GLB models")
        data = {
            "available": True, "source": source_url, "download_url": zip_url,
            "creator": "Kenney", "license": "CC0-1.0",
            "attribution_required": False, "model_count": len(models), "models": models,
        }
        (out / "asset_manifest.json").write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")
        print(f"{slug}: prepared {len(models)} authored CC0 models")
        return data
    except Exception as exc:
        data = {
            "available": False, "source": source_url, "license": "CC0-1.0",
            "attribution_required": False, "model_count": 0, "models": [],
            "note": "Optional pack unavailable; procedural fallback stays enabled.",
            "reason": str(exc)[:300],
        }
        (out / "asset_manifest.json").write_text(json.dumps(data, indent=2) + "\\n", encoding="utf-8")
        print(f"WARNING: {slug} unavailable; keeping procedural fallback: {exc}")
        return data

def main() -> int:
    total = 0
    for slug, page, source in PACKS:
        data = process_pack(slug, page, source)
        total += int(data.get("model_count", 0))
    print(f"CC0 city model count: {total}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
