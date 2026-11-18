#!/usr/bin/env python3
"""Fetch official Kenney CC0 city-building packs for the Android build."""
from __future__ import annotations

import pathlib
import sys
import tempfile
import zipfile

_PROJECT_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.kenney_pack_utils import (
    download_zip,
    fetch_bytes,
    find_download_zip,
    write_fallback_manifest,
    write_manifest,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKS = [
    ("city-kit-suburban", "https://kenney.nl/assets/city-kit-suburban", "https://kenney.nl/assets/city-kit-suburban"),
    ("city-kit-commercial", "https://kenney.nl/assets/city-kit-commercial", "https://kenney.nl/assets/city-kit-commercial"),
    ("city-kit-industrial", "https://kenney.nl/assets/city-kit-industrial", "https://kenney.nl/assets/city-kit-industrial"),
]
ALLOWED = {".gltf", ".glb", ".bin", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".license"}


def find_zip(page: str, slug: str) -> str:
    """Backward-compatible wrapper retained for the existing asset tests."""
    return find_download_zip(page, slug)


def process_pack(slug: str, page_url: str, source_url: str) -> dict:
    out = ROOT / "external_content" / ("kenney_" + slug.replace("-", "_"))
    out.mkdir(parents=True, exist_ok=True)
    try:
        page_bytes, page_response = fetch_bytes(
            page_url,
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )
        page = page_bytes.decode("utf-8", "replace")
        zip_url = find_download_zip(page, slug)
        payload, response = download_zip(zip_url, referer=page_url)

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
            raise ValueError("downloaded pack had no GLTF/GLB models after safe extraction")

        data = {
            "available": True,
            "source": source_url,
            "download_url": zip_url,
            "creator": "Kenney",
            "license": "CC0-1.0",
            "attribution_required": False,
            "model_count": len(models),
            "models": models,
            "download_response": response,
            "asset_page_response": page_response,
        }
        write_manifest(out / "asset_manifest.json", data)
        print(
            f"{slug}: prepared {len(models)} authored CC0 models; "
            f"ZIP bytes={response['bytes']}; content-type={response['content_type']!r}"
        )
        return data
    except Exception as exc:
        data = write_fallback_manifest(out / "asset_manifest.json", source_url, str(exc))
        print(f"WARNING: {slug} unavailable; recorded diagnostic fallback manifest: {data['reason']}")
        return data


def main() -> int:
    total = 0
    failed = []
    for slug, page, source in PACKS:
        data = process_pack(slug, page, source)
        total += int(data.get("model_count", 0))
        if not bool(data.get("available", False)):
            failed.append(slug)
    print(f"CC0 city model count: {total}")
    if failed:
        print("City packs unavailable (the medium-stage gate will reject this build): " + ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
