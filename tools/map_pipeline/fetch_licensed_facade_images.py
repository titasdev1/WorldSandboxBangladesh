#!/usr/bin/env python3
"""Download only allowlisted, openly licensed Shariatpur facade reference photos."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_LICENSES = {"CC BY 4.0", "CC BY-SA 4.0"}
ALLOWED_HOSTS = {"commons.wikimedia.org", "upload.wikimedia.org", "thumb.wikimedia.org"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
USER_AGENT = (
    "WorldSandboxBangladesh/1.2 (open-license asset pipeline; "
    "Wikimedia Commons attribution is packaged)"
)


def wikimedia_thumbnail_url(item: dict) -> str | None:
    """Build a Commons thumbnail URL from the *remote source filename*, not our local alias."""
    source_page = str(item.get("source_page", "")).strip()
    parsed = urlparse(source_page)
    if parsed.hostname != "commons.wikimedia.org":
        return None
    prefix = "/wiki/File:"
    if not parsed.path.startswith(prefix):
        return None
    source_name = urllib.parse.unquote(parsed.path[len(prefix):]).replace(" ", "_")
    if not source_name or "/" in source_name or "\\" in source_name:
        return None
    digest = hashlib.md5(source_name.encode("utf-8")).hexdigest()
    encoded_name = urllib.parse.quote(source_name, safe="()_,.-")
    return (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/"
        f"{digest[0]}/{digest[:2]}/{encoded_name}/1024px-{encoded_name}"
    )


def validate_image_response(response, data: bytes) -> tuple[str, str]:
    final_host = urlparse(response.geturl()).hostname or ""
    content_type = response.headers.get_content_type()
    if final_host not in ALLOWED_HOSTS:
        raise ValueError(f"redirected to non-allowlisted host: {final_host}")
    if not content_type.startswith("image/"):
        raise ValueError(f"unexpected content type: {content_type}")
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"image size outside allowed range: {len(data)} bytes")
    if not (
        data.startswith(b"\xff\xd8\xff")
        or data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"RIFF")
    ):
        raise ValueError("downloaded payload does not look like a supported raster image")
    return final_host, content_type


def fetch_image(candidate_url: str) -> bytes:
    """Fetch one candidate with bounded retry for transient HTTP/network errors."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                candidate_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read(MAX_IMAGE_BYTES + 1)
                validate_image_response(response, data)
                return data
        except urllib.error.HTTPError as exc:
            last_error = exc
            # A 404/permission error is not transient. Move to the fallback URL.
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
            try:
                retry_after = min(20, max(0, int(exc.headers.get("Retry-After", "0"))))
            except (TypeError, ValueError):
                retry_after = 0
            if attempt < 2:
                time.sleep(max(retry_after, (2, 6)[attempt]))
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep((2, 6)[attempt])
        except ValueError:
            # Invalid content should immediately try the next URL, not be retried.
            raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("image download failed without a response")


def download_catalog(catalog_path: Path, output_dir: Path, allow_missing: bool) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []
    attribution_lines = [
        "Shariatpur landmark facade references",
        "Each photo below retains its own source and license. CC BY-SA photos must remain available under compatible share-alike terms.",
        "Do not treat these references as generic textures or as proof that every building has been visually verified.",
        "",
    ]
    for item in catalog.get("images", []):
        image_id = str(item.get("id", "")).strip()
        filename = str(item.get("file_name", "")).strip()
        url = str(item.get("download_url", "")).strip()
        license_name = str(item.get("license", "")).strip()
        try:
            if not image_id or not filename or not url:
                raise ValueError("missing required catalog field")
            if license_name not in ALLOWED_LICENSES:
                raise ValueError(f"license is not allowlisted: {license_name}")
            if urlparse(url).hostname not in ALLOWED_HOSTS:
                raise ValueError("download host is not allowlisted")

            target = output_dir / filename
            candidates = []
            direct_url = wikimedia_thumbnail_url(item)
            if direct_url:
                candidates.append(direct_url)
            if url not in candidates:
                candidates.append(url)

            last_error: Exception | None = None
            data: bytes | None = None
            for candidate_url in candidates:
                try:
                    data = fetch_image(candidate_url)
                    last_error = None
                    break
                except (OSError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
                    last_error = exc
            if data is None:
                raise last_error or RuntimeError("all download candidates failed")

            target.write_bytes(data)
            record = {
                "id": image_id,
                "subject": item.get("subject"),
                "path": str(target),
                "source_page": item.get("source_page"),
                "author": item.get("author"),
                "license": license_name,
                "license_url": item.get("license_url"),
                "attribution": item.get("attribution"),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "download_status": "DOWNLOADED",
            }
            results.append(record)
            attribution_lines.extend([
                str(item.get("attribution", "")),
                f"License: {license_name} — {item.get('license_url', '')}",
                "",
            ])
        except (OSError, urllib.error.URLError, TimeoutError, ValueError, RuntimeError) as exc:
            failures.append({"id": image_id, "error": str(exc)})

    eligible_exterior_count = sum(
        1 for item in catalog.get("images", [])
        if item.get("facade_eligible") is True
        and str(item.get("view_type", "")).strip().lower() == "exterior"
        and str(item.get("visual_qa", "")).strip().lower() == "passed"
        and str(item.get("license", "")).strip() in ALLOWED_LICENSES
    )
    interior_reference_only_count = sum(
        1 for item in catalog.get("images", [])
        if item.get("interior_reference_eligible") is True
        and not (
            item.get("facade_eligible") is True
            and str(item.get("view_type", "")).strip().lower() == "exterior"
            and str(item.get("visual_qa", "")).strip().lower() == "passed"
        )
    )
    report = {
        "schema_version": 1,
        "catalog": str(catalog_path),
        "downloaded_count": len(results),
        "eligible_exterior_count": eligible_exterior_count,
        "interior_reference_only_count": interior_reference_only_count,
        "failed_count": len(failures),
        "downloaded": results,
        "failures": failures,
        "limitations": catalog.get("limitations", []),
    }
    (output_dir / "facade_image_download_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "ATTRIBUTION.txt").write_text(
        "\n".join(attribution_lines).rstrip() + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "downloaded_count": len(results),
        "eligible_exterior_count": eligible_exterior_count,
        "interior_reference_only_count": interior_reference_only_count,
        "failed_count": len(failures),
        "failures": failures,
    }, ensure_ascii=False))
    if failures and not allow_missing:
        return report
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Record unavailable images but keep the map build alive.",
    )
    args = parser.parse_args()
    if not args.catalog.is_file():
        parser.error(f"catalog does not exist: {args.catalog}")
    report = download_catalog(args.catalog, args.out, args.allow_missing)
    return 0 if args.allow_missing or report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
