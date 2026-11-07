#!/usr/bin/env python3
"""Fetch Kenney's official CC0 3D Car Kit for the Android build.

The download link is resolved from the official asset page at build time; no
stale revision-specific URL is hardcoded. A valid fallback manifest is written
on failure, and the medium-stage asset gate prevents silent placeholder builds.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import urllib.request
import zipfile

_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.kenney_pack_utils import find_download_zip, write_fallback_manifest, write_manifest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "external_content" / "kenney_car_kit"
MANIFEST = OUT / "asset_manifest.json"
PAGE_URL = "https://kenney.nl/assets/car-kit"
ALLOWED = {".gltf", ".glb", ".bin", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".license"}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "WorldSandboxBangladesh-AssetBuilder/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        page = get(PAGE_URL).decode("utf-8", "replace")
        zip_url = find_download_zip(page, "car-kit")
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
                    destination = OUT.joinpath(*rel.parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as src, destination.open("wb") as dst:
                        dst.write(src.read())
                    extracted.append(destination)

        models = []
        for path in sorted(extracted):
            if path.suffix.lower() not in {".gltf", ".glb"}:
                continue
            relative = path.relative_to(ROOT).as_posix()
            models.append({"name": path.stem, "path": "res://" + relative, "format": path.suffix.lower()[1:]})
        if not models:
            raise ValueError("official archive contained no GLTF/GLB models")

        data = {
            "available": True,
            "source": PAGE_URL,
            "download_url": zip_url,
            "creator": "Kenney",
            "license": "CC0-1.0",
            "attribution_required": False,
            "model_count": len(models),
            "models": models,
            "note": "CNG and rickshaw remain project-authored vehicle models.",
        }
        write_manifest(MANIFEST, data)
        print(f"CC0 vehicle assets prepared: {len(models)} GLTF/GLB models")
        return 0
    except Exception as exc:
        data = write_fallback_manifest(MANIFEST, PAGE_URL, str(exc))
        print(f"WARNING: vehicle art unavailable; recorded valid fallback manifest: {data['reason']}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
