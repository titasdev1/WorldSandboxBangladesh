#!/usr/bin/env python3
"""Audit public KartaView street-level coverage over a map package bounding box.

This stage downloads only coverage-track metadata (not photo files). Individual
photo ingestion must separately retain contributor, photo permalink, capture date
and CC BY-SA attribution before any panorama is used in a shipped build.
"""
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.openstreetcam.org/2.0/sequence/tiles"
DATASET_ATTRIBUTION = "KartaView / GrabMaps 360 Imagery Dataset and contributing photographers"
DATASET_LICENSE = "CC BY-SA 4.0"
USER_AGENT = "WorldSandboxBangladesh/1.0 (KartaView coverage audit; open-data attribution preserved)"
PUBLIC_REQUEST_LIMIT = 100


def latlon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Return standard XYZ/slippy-map x,y tile coordinates."""
    if not -85.05112878 <= lat <= 85.05112878:
        raise ValueError(f"latitude outside Web Mercator limits: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude outside geographic limits: {lon}")
    n = 1 << zoom
    x = min(n - 1, max(0, int(math.floor((lon + 180.0) / 360.0 * n))))
    lat_rad = math.radians(lat)
    y_float = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) * 0.5 * n
    y = min(n - 1, max(0, int(math.floor(y_float))))
    return x, y


def tiles_for_bbox(bbox: tuple[float, float, float, float], zoom: int) -> list[tuple[int, int, int]]:
    """Return every XYZ tile intersecting (south, west, north, east)."""
    south, west, north, east = bbox
    if not (south < north and west < east):
        raise ValueError("bbox must be ordered south, west, north, east")
    if not (0 <= zoom <= 22):
        raise ValueError("zoom must be between 0 and 22")
    x0, y0 = latlon_to_tile(north, west, zoom)
    x1, y1 = latlon_to_tile(south, east, zoom)
    return [
        (zoom, x, y)
        for y in range(min(y0, y1), max(y0, y1) + 1)
        for x in range(min(x0, x1), max(x0, x1) + 1)
    ]


def _candidate_line_lists(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    candidates = [payload.get("lines")]
    result = payload.get("result")
    if isinstance(result, dict):
        candidates.append(result.get("lines"))
        data = result.get("data")
        if isinstance(data, dict):
            candidates.append(data.get("lines"))
        elif isinstance(data, list):
            candidates.extend(item.get("lines") for item in data if isinstance(item, dict))
    return [value for value in candidates if isinstance(value, list)]


def parse_coverage_tracks(payload: Any, zoom: int, x: int, y: int) -> list[dict[str, Any]]:
    """Normalize documented KartaView track arrays into GeoJSON features."""
    lines = next(iter(_candidate_line_lists(payload)), [])
    features: list[dict[str, Any]] = []
    for line_index, line in enumerate(lines):
        if not isinstance(line, dict):
            continue
        track = line.get("track")
        if not isinstance(track, list):
            continue
        coords: list[list[float]] = []
        for point in track:
            if not isinstance(point, dict):
                continue
            try:
                lat = float(point.get("lat", point.get("latitude")))
                lon = float(point.get("lng", point.get("lon", point.get("longitude"))))
            except (TypeError, ValueError):
                continue
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                continue
            coords.append([lon, lat])
        if len(coords) < 2:
            continue
        matched_value = str(line.get("matched", "")).strip().lower()
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "source": "KartaView",
                "dataset": DATASET_ATTRIBUTION,
                "license": DATASET_LICENSE,
                "zoom": zoom,
                "tile_x": x,
                "tile_y": y,
                "line_index": line_index,
                "matched_to_osm": matched_value in {"1", "true", "yes"},
            },
        })
    return features


def _fetch_json(url: str, timeout: float = 25.0, retries: int = 2) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise OSError(f"unexpected HTTP status {response.status}")
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise ValueError("coverage tile exceeds 16 MiB safety cap")
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504} or attempt >= retries:
                break
            try:
                wait = min(30.0, max(0.0, float(exc.headers.get("Retry-After", "0"))))
            except (TypeError, ValueError):
                wait = 0.0
            time.sleep(max(wait, (2.0, 5.0)[min(attempt, 1)]))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep((2.0, 5.0)[min(attempt, 1)])
    if last_error:
        raise last_error
    raise RuntimeError("coverage request failed without a response")


def audit_coverage(
    bbox: tuple[float, float, float, float],
    zoom: int = 12,
    max_requests: int = 90,
    fetch_json=_fetch_json,
) -> dict[str, Any]:
    """Fetch bounded coverage tiles and return GeoJSON plus a reproducible report."""
    tiles = tiles_for_bbox(bbox, zoom)
    safe_cap = min(max_requests, PUBLIC_REQUEST_LIMIT)
    if safe_cap < 1:
        raise ValueError("max_requests must be positive")
    if len(tiles) > safe_cap:
        raise ValueError(
            f"bbox requires {len(tiles)} coverage requests at zoom {zoom}, above the "
            f"safe cap of {safe_cap}; lower zoom or split the area"
        )
    features: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    tiles_with_tracks = 0
    for zoom_value, x, y in tiles:
        url = f"{API_ROOT}/{x}/{y}/{zoom_value}.json"
        try:
            tile_features = parse_coverage_tracks(fetch_json(url), zoom_value, x, y)
            if tile_features:
                tiles_with_tracks += 1
                features.extend(tile_features)
        except Exception as exc:
            failures.append({"zoom": zoom_value, "x": x, "y": y, "error": str(exc)})

    bbox_polygon = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[
            [bbox[1], bbox[0]], [bbox[3], bbox[0]], [bbox[3], bbox[2]],
            [bbox[1], bbox[2]], [bbox[1], bbox[0]],
        ]]},
        "properties": {"role": "requested_audit_bbox", "source": "map manifest extent"},
    }
    geojson = {
        "type": "FeatureCollection",
        "name": "kartaview_street_level_coverage",
        "features": [bbox_polygon, *features],
    }
    report = {
        "schema_version": 1,
        "source": "KartaView public coverage tiles",
        "dataset_attribution": DATASET_ATTRIBUTION,
        "license": DATASET_LICENSE,
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "bbox_south_west_north_east": list(bbox),
        "zoom": zoom,
        "request_count": len(tiles),
        "tile_count": len(tiles),
        "tiles_with_coverage_tracks": tiles_with_tracks,
        "coverage_track_count": len(features),
        "matched_to_osm_track_count": sum(1 for f in features if f["properties"]["matched_to_osm"]),
        "unmatched_track_count": sum(1 for f in features if not f["properties"]["matched_to_osm"]),
        "failed_tile_count": len(failures),
        "failed_tiles": failures,
        "limitations": [
            "Coverage tracks indicate where street-level imagery was collected; they do not prove every building has a usable view.",
            "This audit downloads coverage metadata only, not panorama images.",
            "Individual photos must be matched to target buildings and preserve photographer, permalink, capture date and license attribution before baking.",
            "Street-level images may be old, occluded, angled away from a building, blurred, or not captured in full 360-degree mode.",
        ],
    }
    return {"geojson": geojson, "report": report}


def bbox_from_manifest(path: Path) -> tuple[float, float, float, float]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    raw = manifest.get("region_south_west_north_east")
    if not isinstance(raw, list) or len(raw) != 4:
        raise ValueError("manifest lacks region_south_west_north_east [south, west, north, east]")
    bbox = tuple(float(value) for value in raw)
    if not all(math.isfinite(value) for value in bbox):
        raise ValueError("manifest bbox contains non-finite coordinates")
    return bbox  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--manifest", type=Path, help="map_tiles_manifest.json from the assembled map")
    source.add_argument("--bbox", type=str, help="south,west,north,east")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--zoom", type=int, default=12, help="default 12 keeps district requests bounded")
    parser.add_argument("--max-requests", type=int, default=90, help="public API documents 100 requests/hour")
    parser.add_argument("--allow-partial", action="store_true", help="exit 0 if some tiles fail and failures are recorded")
    args = parser.parse_args()
    try:
        if args.manifest:
            bbox = bbox_from_manifest(args.manifest)
        else:
            values = [float(value.strip()) for value in args.bbox.split(",")]
            if len(values) != 4:
                raise ValueError("--bbox needs four comma-separated coordinates")
            bbox = tuple(values)  # type: ignore[assignment]
        result = audit_coverage(bbox, zoom=args.zoom, max_requests=args.max_requests)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "kartaview_coverage.geojson").write_text(
        json.dumps(result["geojson"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "kartaview_coverage_report.json").write_text(
        json.dumps(result["report"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "KARTAVIEW_ATTRIBUTION.txt").write_text(
        f"{DATASET_ATTRIBUTION}\nLicense: {DATASET_LICENSE} — https://creativecommons.org/licenses/by-sa/4.0/\n"
        "Coverage tracks only; no panorama images downloaded by this audit. Each panorama used in-game needs its own photographer, permalink, capture date, and license in the shipped attribution manifest.\n",
        encoding="utf-8",
    )
    report = result["report"]
    print(json.dumps({
        "request_count": report["request_count"],
        "tile_count": report["tile_count"],
        "tiles_with_coverage_tracks": report["tiles_with_coverage_tracks"],
        "coverage_track_count": report["coverage_track_count"],
        "matched_to_osm_track_count": report["matched_to_osm_track_count"],
        "failed_tile_count": report["failed_tile_count"],
        "geojson": str(args.out / "kartaview_coverage.geojson"),
        "report": str(args.out / "kartaview_coverage_report.json"),
    }, ensure_ascii=False))
    return 0 if args.allow_partial or report["failed_tile_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
