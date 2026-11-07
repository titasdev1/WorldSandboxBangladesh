#!/usr/bin/env python3
"""Safe helpers for retrieving and writing official Kenney asset manifests."""
from __future__ import annotations

import html
import json
import pathlib
import re
from urllib.parse import urljoin, urlparse


# Verified direct download links exposed by the official Kenney asset pages.
# These are CC0 packs; refresh them from the corresponding page if Kenney rotates
# its media paths. The page parser remains the preferred source.
VERIFIED_DOWNLOAD_FALLBACKS = {
    "car-kit": "https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip",
    "city-kit-commercial": "https://kenney.nl/media/pages/assets/city-kit-commercial/a742d900eb-1753115042/kenney_city-kit-commercial_2.1.zip",
    "city-kit-industrial": "https://kenney.nl/media/pages/assets/city-kit-industrial/0ec35b139d-1788171848/kenney_city-kit-industrial_2.0.zip",
    "city-kit-suburban": "https://kenney.nl/media/pages/assets/city-kit-suburban/2c871b7af2-1745479373/kenney_city-kit-suburban_20.zip",
}


def write_manifest(manifest_path: pathlib.Path, data: dict) -> None:
    """Write one complete, round-trippable JSON manifest atomically."""
    manifest_path = pathlib.Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    # Fail before replacing the existing manifest if the payload is not JSON-safe.
    json.loads(encoded)
    temporary = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    temporary.write_text(encoded + "\n", encoding="utf-8")
    temporary.replace(manifest_path)


def write_fallback_manifest(manifest_path: pathlib.Path, source_url: str, reason: str) -> dict:
    """Write an explicit, valid fallback record when an upstream pack is unavailable."""
    data = {
        "available": False,
        "source": source_url,
        "license": "CC0-1.0",
        "attribution_required": False,
        "model_count": 0,
        "models": [],
        "note": "Optional pack unavailable; procedural fallback stays enabled.",
        "reason": str(reason)[:300],
    }
    write_manifest(manifest_path, data)
    return data


def find_download_zip(page_html: str, slug: str) -> str:
    """Find an official Kenney ZIP, using a verified page-derived URL if needed."""
    safe_slug = re.sub(r"[^a-z0-9-]", "", str(slug).lower())
    if not safe_slug:
        raise ValueError("Kenney asset slug is empty or invalid.")

    page = html.unescape(str(page_html))
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", page, flags=re.I)
    # Some asset pages expose the download URL in inline metadata rather than an anchor.
    inline_urls = re.findall(
        r"""https?://(?:www\.)?kenney\.nl/media/pages/assets/[^"'<>\s]+?\.zip(?:\?[^"'<>\s]*)?""",
        page,
        flags=re.I,
    )
    candidates = hrefs + inline_urls

    for candidate in candidates:
        url = urljoin("https://kenney.nl/", html.unescape(candidate.strip()))
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        expected_prefix = f"/media/pages/assets/{safe_slug}/"
        if host not in {"kenney.nl", "www.kenney.nl"}:
            continue
        if not path.startswith(expected_prefix) or not path.endswith(".zip"):
            continue
        return url

    # Kenney's public pages currently render the "Continue without donating"
    # link dynamically. The raw HTML fetched by urllib in CI omits that anchor,
    # even though the official page exposes a valid direct ZIP when followed.
    # Use only exact URLs independently observed from the official page's link.
    fallback = VERIFIED_DOWNLOAD_FALLBACKS.get(safe_slug)
    if fallback:
        parsed = urlparse(fallback)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "kenney.nl"
            and parsed.path.lower().startswith(f"/media/pages/assets/{safe_slug}/")
            and parsed.path.lower().endswith(".zip")
        ):
            return fallback

    raise ValueError(f"Official Kenney page did not expose a ZIP archive for '{safe_slug}'.")
