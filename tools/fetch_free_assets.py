#!/usr/bin/env python3
"""Fetch a small, openly licensed vehicle art pack for CI builds.

The project retains procedural fallbacks so the game remains buildable if the
upstream download is unavailable. Downloaded files are build inputs, not fake
size padding, and the source/licence are written into the generated manifest.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "external_content" / "kenney_car_kit"
MANIFEST = OUT / "asset_manifest.json"
URL = "https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip"
ALLOWED = {".gltf", ".glb", ".bin", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".obj", ".mtl", ".license"}

def write_fallback(reason: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {
        "available": False,
        "source": "https://kenney.nl/assets/car-kit",
        "license": "CC0-1.0",
        "attribution_required": False,
        "models": [],
        "note": "Procedural vehicle meshes remain active because the optional asset pack was not available in this build.",
        "reason": reason[:400],
    }
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": "WorldSandboxBangladesh-AssetBuilder/1.0"})
        with urllib.request.urlopen(request, timeout=35) as response:
            payload = response.read()
        if not payload.startswith(b"PK"):
            raise ValueError("upstream response was not a ZIP archive")
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(payload)
            tmp.flush()
            with zipfile.ZipFile(tmp.name) as archive:
                extracted = []
                for item in archive.infolist():
                    if item.is_dir():
                        continue
                    rel = pathlib.PurePosixPath(item.filename)
                    if rel.is_absolute() or ".." in rel.parts:
                        continue
                    suffix = pathlib.PurePosixPath(item.filename).suffix.lower()
                    if suffix not in ALLOWED:
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
            models.append({
                "name": path.stem,
                "path": "res://" + relative,
                "format": path.suffix.lower().lstrip("."),
            })
        if not models:
            raise ValueError("archive downloaded but contained no GLTF/GLB models")
        data = {
            "available": True,
            "source": "https://kenney.nl/assets/car-kit",
            "download_url": URL,
            "creator": "Kenney",
            "license": "CC0-1.0",
            "attribution_required": False,
            "model_count": len(models),
            "models": models,
            "note": "Original CC0 vehicle models; CNG and rickshaw remain custom procedural models.",
        }
        MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"CC0 vehicle assets prepared: {len(models)} GLTF/GLB models")
        return 0
    except Exception as exc:
        write_fallback(str(exc))
        print(f"WARNING: optional Kenney CC0 vehicle pack unavailable; using procedural fallback: {exc}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
