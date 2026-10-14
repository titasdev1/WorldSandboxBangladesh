#!/usr/bin/env python3
"""Fetch one rigged Quaternius Universal Base Character for the Android build.

The upstream project is pinned to a reviewed commit. Only the selected GLTF and
its declared buffer/texture dependencies are downloaded. The project remains
buildable with its procedural fallback when the optional download is unavailable.
Quaternius Universal Base Characters are distributed under CC0 1.0.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "external_content" / "quaternius_ubc"
UPSTREAM = "mehulkapadia5/open-theft-auto"
REVISION = "b37e7f3070501dd90353c250e9ad90dffdf4c8b2"
MODEL = "assets/characters/ubc/male.gltf"
RAW_BASE = f"https://raw.githubusercontent.com/{UPSTREAM}/{REVISION}/"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
SOURCE_URL = "https://quaternius.com/packs/universalbasecharacters.html"
USER_AGENT = "WorldSandboxBangladesh-AssetBuilder/1.0"

def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        model_bytes = get(RAW_BASE + MODEL)
        model = json.loads(model_bytes.decode("utf-8"))
        dependencies = [MODEL.rsplit("/", 1)[1]]
        for item in model.get("buffers", []) + model.get("images", []):
            uri = item.get("uri")
            if uri and not uri.startswith(("http://", "https://", "data:")):
                name = pathlib.PurePosixPath(uri).name
                if name not in dependencies:
                    dependencies.append(name)

        manifest_files = []
        for name in dependencies:
            payload = model_bytes if name == dependencies[0] else get(
                RAW_BASE + "assets/characters/ubc/" + name
            )
            destination = OUT / name
            destination.write_bytes(payload)
            manifest_files.append({
                "file": name,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            })

        license_text = (
            "Character model: Quaternius Universal Base Characters — Superhero Male.\n"
            "License: CC0 1.0 Universal.\n"
            f"Official asset page: {SOURCE_URL}\n"
            f"License text: {LICENSE_URL}\n"
            f"Source project revision: {UPSTREAM}@{REVISION}\n"
            "The model is optional build-time content; procedural fallback remains available.\n"
        )
        (OUT / "LICENSE.txt").write_text(license_text, encoding="utf-8")
        manifest = {
            "available": True,
            "character": "Superhero_Male_FullBody",
            "source": SOURCE_URL,
            "upstream_repository": UPSTREAM,
            "upstream_revision": REVISION,
            "license": "CC0-1.0",
            "license_url": LICENSE_URL,
            "model": "res://external_content/quaternius_ubc/male.gltf",
            "animations_in_source": len(model.get("animations", [])),
            "files": manifest_files,
            "note": "Rigged textured humanoid; locomotion pose is driven by the runtime skeleton controller.",
        }
        (OUT / "asset_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Rigged Quaternius character prepared: {len(manifest_files)} model/dependency files")
        return 0
    except Exception as exc:
        # Do not leave a half-downloaded GLTF that Godot tries to import.
        for path in OUT.glob("*"):
            if path.is_file():
                path.unlink()
        (OUT / "asset_manifest.json").write_text(json.dumps({
            "available": False,
            "source": SOURCE_URL,
            "license": "CC0-1.0",
            "reason": str(exc)[:400],
            "note": "Procedural HumanoidVisual fallback remains active.",
        }, indent=2) + "\n", encoding="utf-8")
        print(f"WARNING: optional rigged character unavailable; procedural fallback remains active: {exc}")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
