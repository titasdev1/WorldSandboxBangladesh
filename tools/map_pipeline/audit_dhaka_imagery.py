#!/usr/bin/env python3
"""Discover openly licensed aerial imagery intersecting the Greater Dhaka map bounds.

This is an imagery inventory, not an imagery downloader or proof of facade coverage.
Only catalog metadata and asset URLs are recorded; the source item's license is kept
with each result so downstream baking can reject unsuitable licenses.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import urllib.request
from datetime import datetime, timezone
from typing import Any

STAC_SEARCH = "https://api.imagery.hotosm.org/stac/search"
DEFAULT_BBOX = (90.30, 23.66, 90.53, 23.90)  # west, south, east, north


def request_catalog(bbox: tuple[float, float, float, float], limit: int) -> dict[str, Any]:
    payload = json.dumps({"bbox": list(bbox), "limit": limit, "collections": ["openaerialmap"]}).encode()
    request = urllib.request.Request(
        STAC_SEARCH,
        data=payload,
        headers={"User-Agent": "Project-A-Square-Dhaka-Imagery-Audit/1.0",
                 "Content-Type": "application/json", "Accept": "application/geo+json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data.get("features"), list):
        raise RuntimeError("STAC response did not contain a features list")
    return data


def summarize(item: dict[str, Any]) -> dict[str, Any]:
    props = item.get("properties") or {}
    assets = item.get("assets") or {}
    visual = assets.get("visual") or {}
    thumb = assets.get("thumbnail") or {}
    providers = item.get("providers") or []
    return {
        "id": item.get("id"),
        "collection": item.get("collection"),
        "title": props.get("title") or props.get("description") or item.get("id"),
        "bbox_west_south_east_north": item.get("bbox"),
        "datetime": props.get("datetime"),
        "gsd_metres_per_pixel": props.get("gsd"),
        "platform_type": props.get("oam:platform_type"),
        "license": props.get("license"),
        "visual_asset_url": visual.get("href"),
        "thumbnail_url": thumb.get("href"),
        "providers": providers,
        "assets": sorted(assets.keys()),
        "facade_coverage_verified": False,
        "note": "Intersection with the region bbox does not prove full-area or street-facade coverage; inspect the footprint, resolution, date, and license before use.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bbox", nargs=4, type=float, default=DEFAULT_BBOX,
                        metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out", type=pathlib.Path, default=pathlib.Path("build/dhaka-imagery-audit.json"))
    args = parser.parse_args()
    west, south, east, north = args.bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        parser.error("bbox must be west, south, east, north in valid coordinate order")
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")

    error = None
    try:
        raw = request_catalog(tuple(args.bbox), args.limit)
        items = [summarize(item) for item in raw["features"]]
        status = "CATALOG_QUERY_SUCCEEDED"
    except Exception as exc:
        items = []
        error = f"{type(exc).__name__}: {exc}"
        status = "CATALOG_QUERY_FAILED"

    output = {
        "product": "Project A-Square Dhaka imagery availability audit",
        "catalog": STAC_SEARCH,
        "queried_bbox_west_south_east_north": list(args.bbox),
        "queried_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "result_count": len(items),
        "error": error,
        "important_limit": "This inventory does not certify currentness, ground resolution, license compatibility, facade visibility, or complete coverage. Inspect each source item before baking imagery into an offline game.",
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("status", "result_count", "error", "queried_bbox_west_south_east_north")}, indent=2))
    # Catalog outage should not destroy the independent OSM map build; report it in artifact.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
