#!/usr/bin/env python3
"""Audit all public HOTOSM STAC imagery collections intersecting Shariatpur.

Discovery only: this script never downloads imagery or approves it for shipping.
Every item remains subject to exact district clipping, source/licence review,
visual QA, georeferencing validation, and attribution before integration.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

API_URL = "https://api.imagery.hotosm.org/stac/search"
COLLECTIONS_URL = "https://api.imagery.hotosm.org/stac/collections/"
# Approximate search envelope [west, south, east, north]; not the clip boundary.
SHARIATPUR_BBOX = (90.16, 23.00, 90.50, 23.35)
PAGE_LIMIT = 100
MAX_PAGES = 20
USER_AGENT = "Project-A-Square-Shariatpur-Imagery-Audit/1.0 (+https://github.com/titasdev1/WorldSandboxBangladesh)"
LICENSE_ALIASES = {
    "cc by 4.0": "CC-BY-4.0", "cc-by-4.0": "CC-BY-4.0",
    "cc by-sa 4.0": "CC-BY-SA-4.0", "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc0-1.0": "CC0-1.0", "cc0 1.0": "CC0-1.0",
    "public domain": "PUBLIC-DOMAIN", "pdm 1.0": "PUBLIC-DOMAIN",
}
ALLOWED_LICENSES = {"CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "PUBLIC-DOMAIN"}


def normalize_license(value: Any) -> str:
    raw = " ".join(str(value or "").strip().lower().split())
    return LICENSE_ALIASES.get(raw, raw.upper().replace(" ", "-") if raw else "UNKNOWN")


def numeric_gsd(properties: dict[str, Any], item: dict[str, Any]) -> float | None:
    candidates = [properties.get("gsd"), properties.get("eo:gsd"), item.get("gsd")]
    assets = item.get("assets", {})
    if isinstance(assets, dict):
        for asset in assets.values():
            if isinstance(asset, dict):
                bands = asset.get("raster:bands", [])
                if isinstance(bands, list):
                    candidates.extend(
                        band.get("spatial_resolution")
                        for band in bands if isinstance(band, dict)
                    )
    for candidate in candidates:
        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue
        if math.isfinite(value) and value > 0:
            return value
    return None


def asset_summary(assets: Any, collection_id: str = "") -> dict[str, Any]:
    if not isinstance(assets, dict):
        assets = {}
    terrain_collection = "dem" in collection_id.casefold() or "elevation" in collection_id.casefold()
    visual_keys = {"visual", "image", "visual.tif", "visual_cog"}
    visual = any(
        key in assets and isinstance(assets[key], dict) and assets[key].get("href")
        for key in visual_keys
    )
    data_asset = assets.get("data") if isinstance(assets.get("data"), dict) else {}
    data_available = bool(data_asset.get("href"))
    if data_available and not terrain_collection:
        roles = data_asset.get("roles", [])
        visual = visual or not roles or "visual" in roles
    return {
        "visual_asset_available": visual,
        "terrain_asset_available": data_available and terrain_collection,
        "pmtiles_available": isinstance(assets.get("pmtiles"), dict) and bool(assets["pmtiles"].get("href")),
        "asset_keys": sorted(str(key) for key in assets),
    }


def quality_tier(license_name: str, gsd: float | None, visual_available: bool) -> str:
    if license_name not in ALLOWED_LICENSES:
        return "HOLD_LICENSE_REVIEW"
    if gsd is None:
        return "HOLD_GSD_UNVERIFIED"
    if not visual_available:
        return "HOLD_NO_VISUAL_ASSET"
    if gsd <= 0.10:
        return "VERY_HIGH_DETAIL_REVIEW"
    if gsd <= 0.30:
        return "HIGH_DETAIL_REVIEW"
    if gsd <= 1.00:
        return "MEDIUM_DETAIL_REVIEW"
    return "REGIONAL_REFERENCE_ONLY"


def summarize_item(item: dict[str, Any], collection_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    collection_metadata = collection_metadata if isinstance(collection_metadata, dict) else {}
    license_value = item.get("license") or properties.get("license") or collection_metadata.get("license")
    license_name = normalize_license(license_value)
    gsd = numeric_gsd(properties, item)
    collection_id = str(item.get("collection") or "")
    assets = asset_summary(item.get("assets"), collection_id)
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        raise ValueError("STAC item is missing its id")
    links = item.get("links") if isinstance(item.get("links"), list) else []
    self_url = next(
        (link.get("href") for link in links
         if isinstance(link, dict) and link.get("rel") == "self"), None
    )
    return {
        "id": item_id,
        "collection": collection_id,
        "collection_title": collection_metadata.get("title"),
        "collection_license_raw": str(collection_metadata.get("license") or ""),
        "title": str(properties.get("title") or properties.get("description") or item_id),
        "datetime": properties.get("datetime") or properties.get("start_datetime") or properties.get("end_datetime"),
        "provider": properties.get("provider") or properties.get("platform") or properties.get("constellation"),
        "gsd_m": gsd,
        "license": license_name,
        "license_raw": str(license_value or ""),
        "bbox_wsen": item.get("bbox"),
        "geometry_present": isinstance(item.get("geometry"), dict),
        **assets,
        "review_tier": quality_tier(license_name, gsd, assets["visual_asset_available"]),
        "integration_status": "NOT_DOWNLOADED_NOT_APPROVED",
        "item_url": self_url,
    }


def _default_fetch_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json, application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("STAC response was not a JSON object")
    return parsed


def fetch_collection_metadata(
    collection_ids: list[str], fetch_json: Callable[..., dict[str, Any]] = _default_fetch_json
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    metadata: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for collection_id in sorted(set(collection_ids)):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", collection_id):
            errors[collection_id] = "collection id contains unexpected characters"
            continue
        url = COLLECTIONS_URL + urllib.parse.quote(collection_id, safe=".-_")
        try:
            record = fetch_json(url, "GET", None)
            if not isinstance(record, dict):
                raise ValueError("collection endpoint did not return an object")
            metadata[collection_id] = record
        except (OSError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
            errors[collection_id] = f"{type(exc).__name__}: {exc}"
    return metadata, errors


def search_items(fetch_json: Callable[..., dict[str, Any]] = _default_fetch_json) -> tuple[list[dict[str, Any]], int, bool]:
    payload: dict[str, Any] = {
        "bbox": list(SHARIATPUR_BBOX), "limit": PAGE_LIMIT,
    }
    url, method, request_body = API_URL, "POST", payload
    items_by_id: dict[str, dict[str, Any]] = {}
    page_count, truncated = 0, False
    for page_index in range(MAX_PAGES):
        page = fetch_json(url, method, request_body)
        page_count += 1
        features = page.get("features", [])
        if not isinstance(features, list):
            raise ValueError("STAC response is missing a features array")
        for item in features:
            if isinstance(item, dict) and str(item.get("id", "")).strip():
                items_by_id[str(item["id"])] = item
        links = page.get("links", []) if isinstance(page.get("links"), list) else []
        next_link = next(
            (link for link in links if isinstance(link, dict) and link.get("rel") == "next"), None
        )
        if not next_link:
            break
        if page_index == MAX_PAGES - 1:
            truncated = True
            break
        url = str(next_link.get("href") or "")
        if not url.startswith("https://api.imagery.hotosm.org/"):
            raise ValueError("STAC pagination link left the allowlisted OpenAerialMap API host")
        method = str(next_link.get("method") or "GET").upper()
        request_body = next_link.get("body") if method == "POST" and isinstance(next_link.get("body"), dict) else None
    return list(items_by_id.values()), page_count, truncated


def build_report(
    items: list[dict[str, Any]], page_count: int, truncated: bool,
    collection_metadata: dict[str, dict[str, Any]] | None = None,
    collection_metadata_errors: dict[str, str] | None = None,
) -> dict[str, Any]:
    collection_metadata = collection_metadata or {}
    collection_metadata_errors = collection_metadata_errors or {}
    rows = [summarize_item(item, collection_metadata.get(str(item.get("collection") or ""))) for item in items]
    rows.sort(key=lambda row: (row["gsd_m"] is None, row["gsd_m"] or float("inf"), row["id"]))
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["review_tier"]] = counts.get(row["review_tier"], 0) + 1
    return {
        "schema_version": 1,
        "audit": "SHARIATPUR_OPENAERIALMAP_STAC_DISCOVERY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog_api": API_URL,
        "catalog_scope": "ALL_COLLECTIONS_EXPOSED_BY_HOTOSM_STAC_API",
        "collection_metadata": {
            collection_id: {
                "title": record.get("title"),
                "description": record.get("description"),
                "license_raw": record.get("license"),
                "license": normalize_license(record.get("license")),
                "providers": record.get("providers"),
            }
            for collection_id, record in sorted(collection_metadata.items())
        },
        "collection_metadata_errors": collection_metadata_errors,
        "collection_item_counts": {
            collection: sum(1 for row in rows if str(row.get("collection") or "UNKNOWN") == collection)
            for collection in sorted({str(row.get("collection") or "UNKNOWN") for row in rows})
        },
        "search_bbox_wsen": list(SHARIATPUR_BBOX),
        "boundary_note": "Approximate search envelope only; use the official Shariatpur district polygon for exact clipping and coverage percentages.",
        "pages_read": page_count,
        "pagination_truncated": truncated,
        "item_count": len(rows),
        "visual_imagery_item_count": sum(1 for row in rows if row["visual_asset_available"]),
        "terrain_only_item_count": sum(1 for row in rows if row["terrain_asset_available"] and not row["visual_asset_available"]),
        "high_detail_review_candidate_count": sum(1 for row in rows if row["review_tier"] in {"VERY_HIGH_DETAIL_REVIEW", "HIGH_DETAIL_REVIEW"}),
        "review_tier_counts": counts,
        "items": rows,
        "release_gate": "BLOCKED_PENDING_PER_ITEM_LICENSE_GSD_GEOMETRY_ALIGNMENT_AND_VISUAL_QA",
        "limitations": [
            "This report does not establish percent of district coverage.",
            "Aerial orthophotos can improve roofs, ground and broad visual context; they do not supply street-facing facades, doors, interiors, floor counts or collision geometry.",
            "Every item requires exact license, source attribution, acquisition date, footprint, GSD, georeferencing and visual-quality review before download or use.",
            "No imagery was downloaded, baked, redistributed or promoted by this audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("build/shariatpur_openaerialmap_audit.json"))
    args = parser.parse_args()
    try:
        items, pages, truncated = search_items()
        collection_ids = sorted({str(item.get("collection")) for item in items if item.get("collection")})
        collection_metadata, collection_errors = fetch_collection_metadata(collection_ids)
        report = build_report(items, pages, truncated, collection_metadata, collection_errors)
    except (OSError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"OPENAERIALMAP_AUDIT_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit": report["audit"], "item_count": report["item_count"],
        "collection_item_counts": report["collection_item_counts"],
        "visual_imagery_item_count": report["visual_imagery_item_count"],
        "terrain_only_item_count": report["terrain_only_item_count"],
        "high_detail_review_candidate_count": report["high_detail_review_candidate_count"],
        "review_tier_counts": report["review_tier_counts"],
        "pagination_truncated": report["pagination_truncated"],
        "report": str(args.out), "release_gate": report["release_gate"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
