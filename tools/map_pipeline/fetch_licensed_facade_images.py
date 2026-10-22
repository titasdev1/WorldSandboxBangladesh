#!/usr/bin/env python3
"""Download only allowlisted, openly licensed Shariatpur facade reference photos."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_LICENSES = {"CC BY 4.0", "CC BY-SA 4.0"}
ALLOWED_HOSTS = {"commons.wikimedia.org", "upload.wikimedia.org", "thumb.wikimedia.org"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


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
        if not image_id or not filename or not url:
            failures.append({"id": image_id, "error": "missing required catalog field"})
            continue
        if license_name not in ALLOWED_LICENSES:
            failures.append({"id": image_id, "error": f"license is not allowlisted: {license_name}"})
            continue
        if urlparse(url).hostname not in ALLOWED_HOSTS:
            failures.append({"id": image_id, "error": "download host is not allowlisted"})
            continue
        target = output_dir / filename
        # Wikimedia Commons may temporarily rate-limit repeated CI jobs. Try the
        # direct upload host as well as Special:FilePath, with bounded backoff;
        # never treat a missing download as an embedded panel.
        candidate_urls = [url]
        if urlparse(url).hostname == "commons.wikimedia.org":
            canonical_name = filename.replace(" ", "_")
            digest = hashlib.md5(canonical_name.encode("utf-8")).hexdigest()
            from urllib.parse import quote
            encoded_name = quote(canonical_name, safe="()_,.-")
            candidate_urls.insert(
                0,
                "https://upload.wikimedia.org/wikipedia/commons/thumb/"
                f"{digest[0]}/{digest[:2]}/{encoded_name}/1024px-{encoded_name}",
            )
        last_error: Exception | None = None
        data = b""
        content_type = ""
        final_host = ""
        for candidate_url in candidate_urls:
            for attempt in range(3):
                try:
                    request = urllib.request.Request(
                        candidate_url,
                        headers={
                            "User-Agent": "WorldSandboxBangladesh/1.1 (open-license asset pipeline; Wikimedia Commons attribution is packaged)",
                            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=45) as response:
                        final_host = urlparse(response.geturl()).hostname or ""
                        content_type = response.headers.get_content_type()
                        data = response.read(MAX_IMAGE_BYTES + 1)
                    last_error = None
                    break
                except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
                    last_error = exc
                    retry_after = 0
                    if isinstance(exc, urllib.error.HTTPError):
                        try:
                            retry_after = min(20, int(exc.headers.get("Retry-After", "0")))
                        except (TypeError, ValueError):
                            retry_after = 0
                    if attempt < 2:
                        time.sleep(max(retry_after, (2, 6)[attempt]))
            if last_error is None:
                break
        if last_error is not None:
            raise last_error
        if final_host not in ALLOWED_HOSTS:
            raise ValueError(f"redirected to non-allowlisted host: {final_host}")
        if not content_type.startswith("image/"):
            raise ValueError(f"unexpected content type: {content_type}")
        if not data or len(data) > MAX_IMAGE_BYTES:
            raise ValueError(f"image size outside allowed range: {len(data)} bytes")
        if not data.startswith(b"\xff\xd8\xff") and not data.startswith(b"\x89PNG\r\n\x1a\n") and not data.startswith(b"RIFF"):
            raise ValueError("downloaded payload does not look like a supported raster image")
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
            attribution_lines.extend([str(item.get("attribution", "")), f"License: {license_name} — {item.get('license_url', '')}", ""])
        except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
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
    (output_dir / "ATTRIBUTION.txt").write_text("\n".join(attribution_lines).rstrip() + "\n", encoding="utf-8")
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
    parser.add_argument("--allow-missing", action="store_true", help="Record unavailable images but keep the map build alive.")
    args = parser.parse_args()
    if not args.catalog.is_file():
        parser.error(f"catalog does not exist: {args.catalog}")
    report = download_catalog(args.catalog, args.out, args.allow_missing)
    return 0 if args.allow_missing or report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
