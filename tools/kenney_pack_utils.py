#!/usr/bin/env python3
"""Safe helpers for retrieving and writing official Kenney asset manifests."""
from __future__ import annotations

import gzip
import html
import io
import json
import pathlib
import re
import urllib.error
import urllib.request
import zipfile
from urllib.parse import urljoin, urlparse


# These exact official-host ZIP paths produced valid, complete model packs in
# Android build #964 (2026-11-08). Keep them as verified fallbacks because the
# current Kenney asset pages expose a Download button but omit the ZIP href
# from their static HTML response.
VERIFIED_DOWNLOAD_FALLBACKS = {
    "car-kit": "https://kenney.nl/media/pages/assets/car-kit/1a312ec241-1775131960/kenney_car-kit.zip",
    "city-kit-commercial": "https://kenney.nl/media/pages/assets/city-kit-commercial/a742d900eb-1753115042/kenney_city-kit-commercial_2.1.zip",
    "city-kit-industrial": "https://kenney.nl/media/pages/assets/city-kit-industrial/0ec35b139d-1788171848/kenney_city-kit-industrial_2.0.zip",
    "city-kit-suburban": "https://kenney.nl/media/pages/assets/city-kit-suburban/2c871b7af2-1745479373/kenney_city-kit-suburban_20.zip",
}


# No hard-coded download URLs: only links extracted from the matching official
# asset page are eligible. This prevents stale/guessed paths from entering builds.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def fetch_bytes(
    url: str,
    *,
    referer: str | None = None,
    accept: str = "*/*",
    timeout: int = 45,
) -> tuple[bytes, dict]:
    """Fetch with ordinary browser headers and return response metadata."""
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": accept,
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            metadata = {
                "status": getattr(response, "status", response.getcode()),
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type", ""),
                "content_encoding": response.headers.get("Content-Encoding", ""),
                "bytes": len(payload),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(240)
        preview = body.decode("utf-8", "replace").replace("\n", " ")[:180]
        raise RuntimeError(
            f"HTTP {exc.code} fetching {exc.geturl()}; "
            f"content_type={exc.headers.get('Content-Type', '')!r}; "
            f"response_preview={preview!r}"
        ) from exc

    if metadata["content_encoding"].lower() == "gzip":
        payload = gzip.decompress(payload)
        metadata["bytes_after_decompression"] = len(payload)
    return payload, metadata


def download_zip(url: str, *, referer: str, timeout: int = 60) -> tuple[bytes, dict]:
    """Download and validate a ZIP; fail with response details, never HTML silently."""
    payload, metadata = fetch_bytes(
        url,
        referer=referer,
        accept="application/zip, application/octet-stream;q=0.9, */*;q=0.8",
        timeout=timeout,
    )
    final_host = (urlparse(metadata["final_url"]).hostname or "").lower()
    if final_host not in {"kenney.nl", "www.kenney.nl"}:
        raise ValueError(
            f"Kenney download redirected outside the official host: {metadata['final_url']}"
        )
    if not zipfile.is_zipfile(io.BytesIO(payload)):
        preview = payload[:160].decode("utf-8", "replace").replace("\n", " ")[:120]
        prefix = payload[:16].hex()
        raise ValueError(
            "official download response is not a valid ZIP archive "
            f"(status={metadata['status']}, content_type={metadata['content_type']!r}, "
            f"final_url={metadata['final_url']!r}, bytes={metadata['bytes']}, "
            f"prefix_hex={prefix}, preview={preview!r})"
        )
    return payload, metadata


def write_manifest(manifest_path: pathlib.Path, data: dict) -> None:
    """Write one complete, round-trippable JSON manifest atomically."""
    manifest_path = pathlib.Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
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
        "reason": str(reason)[:600],
    }
    write_manifest(manifest_path, data)
    return data


def find_download_zip(page_html: str, slug: str) -> str:
    """Find a ZIP link belonging to the requested official Kenney asset page."""
    safe_slug = re.sub(r"[^a-z0-9-]", "", str(slug).lower())
    if not safe_slug:
        raise ValueError("Kenney asset slug is empty or invalid.")

    page = html.unescape(str(page_html))
    # These are intentionally single-backslash regex tokens: \s and \. are regex
    # operators, not literal backslash characters in the HTML source.
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", page, flags=re.I)
    inline_urls = re.findall(
        r"""https?://(?:www\.)?kenney\.nl/media/pages/assets/[^"'<> \t\r\n]+?\.zip(?:\?[^"'<> \t\r\n]*)?""",
        page,
        flags=re.I,
    )

    for candidate in hrefs + inline_urls:
        url = urljoin("https://kenney.nl/", html.unescape(candidate.strip()))
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path.lower()
        expected_prefix = f"/media/pages/assets/{safe_slug}/"
        if host not in {"kenney.nl", "www.kenney.nl"}:
            continue
        if path.startswith(expected_prefix) and path.endswith(".zip"):
            return url

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
