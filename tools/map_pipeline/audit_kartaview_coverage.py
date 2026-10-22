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
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.openstreetcam.org/2.0/sequence/tiles"
PHOTO_API_ROOT = "https://api.openstreetcam.org/2.0/photo/"
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


def _photo_items(payload: Any) -> list[dict[str, Any]]:
    """Extract photo items from documented KartaView API response variants."""
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    candidates = [result.get("data")] if isinstance(result, dict) else []
    candidates.append(payload.get("data"))
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            for key in ("photos", "items", "results"):
                value = candidate.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
    return []


def _inside_bbox(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> bool:
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


def _haversine_metres(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    earth_radius = 6_371_000.0
    d_lat = math.radians(lat_b - lat_a)
    d_lon = math.radians(lon_b - lon_a)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat_a))
        * math.cos(math.radians(lat_b))
        * math.sin(d_lon / 2.0) ** 2
    )
    return 2.0 * earth_radius * math.asin(min(1.0, math.sqrt(a)))


def _photo_grid_points(
    bbox: tuple[float, float, float, float],
    grid_size: int,
    max_queries: int,
) -> list[tuple[float, float]]:
    if grid_size <= 0 or max_queries <= 0:
        return []
    if grid_size > 10:
        raise ValueError("photo grid size must not exceed 10")
    south, west, north, east = bbox
    points = [
        (
            south + (row + 0.5) * (north - south) / grid_size,
            west + (col + 0.5) * (east - west) / grid_size,
        )
        for row in range(grid_size)
        for col in range(grid_size)
    ]
    count = min(len(points), max_queries)
    if count >= len(points):
        return points
    if count == 1:
        return [points[len(points) // 2]]
    indices = sorted({round(i * (len(points) - 1) / (count - 1)) for i in range(count)})
    return [points[index] for index in indices]


def discover_360_photo_candidates(
    bbox: tuple[float, float, float, float],
    grid_size: int = 0,
    max_queries: int = 0,
    radius_m: int = 500,
    fetch_json=_fetch_json,
    photo_grid_size: int = 0,
    max_photo_queries: int = 0,
    photo_radius_m: int = 500,
) -> dict[str, Any]:
    """Probe a bounded grid for 360-degree photo metadata; never downloads image bytes."""
    if radius_m < 1 or radius_m > 500:
        raise ValueError("photo query radius must be between 1 and 500 metres")
    sample_points = _photo_grid_points(bbox, grid_size, max_queries)
    by_id: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    outside_bbox_count = 0
    response_photo_count = 0
    for index, (sample_lat, sample_lon) in enumerate(sample_points):
        query = urllib.parse.urlencode({
            "lat": f"{sample_lat:.7f}",
            "lng": f"{sample_lon:.7f}",
            "radius": str(radius_m),
            "zoomLevel": "18",
            "join": "sequence",
            "orderBy": "id",
            "orderDirection": "desc",
            "searchFieldOfView": "360",
        })
        try:
            payload = fetch_json(PHOTO_API_ROOT + "?" + query)
        except Exception as exc:
            failures.append({
                "sample_index": index,
                "sample_lat": sample_lat,
                "sample_lon": sample_lon,
                "error": str(exc),
            })
            continue
        for item in _photo_items(payload):
            response_photo_count += 1
            sequence = item.get("sequence") if isinstance(item.get("sequence"), dict) else {}
            try:
                lat = float(item.get("lat", item.get("latitude")))
                lon = float(item.get("lng", item.get("lon", item.get("longitude"))))
                fov = float(item.get("fieldOfView", item.get("field_of_view", 0)))
            except (TypeError, ValueError):
                continue
            projection = str(item.get("projection", "")).strip().upper()
            if fov < 350.0 or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            if not _inside_bbox(lat, lon, bbox):
                outside_bbox_count += 1
                continue
            photo_id = str(item.get("id", item.get("photoId", ""))).strip()
            sequence_id = str(sequence.get("id", item.get("sequenceId", ""))).strip()
            if not photo_id:
                continue
            record = {
                "photo_id": photo_id,
                "sequence_id": sequence_id,
                "contributor_id": str(item.get("userId", sequence.get("userId", ""))).strip(),
                "latitude": lat,
                "longitude": lon,
                "field_of_view_degrees": fov,
                "projection": projection,
                "heading_degrees": item.get("heading"),
                "captured_at": item.get("captureDate", item.get("dateTaken", item.get("capturedAt"))),
                "uploaded_at": item.get("dateAdded"),
                "photo_url_candidate": str(item.get("fileurl", item.get("fileUrl", item.get("photoUrl", "")))).strip(),
                "source_page_url": str(item.get("permalink", item.get("sourcePage", ""))).strip(),
                "license": DATASET_LICENSE,
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution_required": True,
                "query_sample_lat_lon": [sample_lat, sample_lon],
                "distance_from_query_metres": round(
                    _haversine_metres(sample_lat, sample_lon, lat, lon), 2
                ),
            }
            existing = by_id.get(photo_id)
            if existing is None or record["distance_from_query_metres"] < existing["distance_from_query_metres"]:
                by_id[photo_id] = record
    candidates = sorted(by_id.values(), key=lambda item: (
        item["latitude"], item["longitude"], item["photo_id"]
    ))
    return {
        "sample_points": [{"latitude": lat, "longitude": lon} for lat, lon in sample_points],
        "query_count": len(sample_points),
        "photo_rows_returned": response_photo_count,
        "unique_360_photo_candidates_inside_bbox": len(candidates),
        "360_photo_candidates_outside_bbox": outside_bbox_count,
        "query_failures": failures,
        "candidates": candidates,
    }


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


def _clip_segment_to_bbox(
    start: list[float],
    end: list[float],
    bbox: tuple[float, float, float, float],
) -> tuple[list[float], list[float]] | None:
    """Liang-Barsky clipping of one lon/lat segment to a bounding rectangle."""
    south, west, north, east = bbox
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    p_values = (-dx, dx, -dy, dy)
    q_values = (x0 - west, east - x0, y0 - south, north - y0)
    u0, u1 = 0.0, 1.0
    for p, q in zip(p_values, q_values):
        if abs(p) < 1e-15:
            if q < 0:
                return None
            continue
        ratio = q / p
        if p < 0:
            if ratio > u1:
                return None
            u0 = max(u0, ratio)
        else:
            if ratio < u0:
                return None
            u1 = min(u1, ratio)
    if u0 > u1:
        return None
    clipped_start = [x0 + u0 * dx, y0 + u0 * dy]
    clipped_end = [x0 + u1 * dx, y0 + u1 * dy]
    return clipped_start, clipped_end


def clip_polyline_to_bbox(
    coordinates: list[list[float]],
    bbox: tuple[float, float, float, float],
) -> list[list[list[float]]]:
    """Clip a polyline to bbox; retain separate inside segments when it exits/re-enters."""
    output: list[list[list[float]]] = []
    current: list[list[float]] = []
    epsilon = 1e-9
    for start, end in zip(coordinates, coordinates[1:]):
        clipped = _clip_segment_to_bbox(start, end, bbox)
        if clipped is None:
            if len(current) >= 2:
                output.append(current)
            current = []
            continue
        clipped_start, clipped_end = clipped
        joins_previous = bool(current) and (
            abs(current[-1][0] - clipped_start[0]) <= epsilon
            and abs(current[-1][1] - clipped_start[1]) <= epsilon
        )
        if not joins_previous:
            if len(current) >= 2:
                output.append(current)
            current = [clipped_start]
        if not current or (
            abs(current[-1][0] - clipped_end[0]) > epsilon
            or abs(current[-1][1] - clipped_end[1]) > epsilon
        ):
            current.append(clipped_end)
    if len(current) >= 2:
        output.append(current)
    return output


def parse_coverage_tracks(
    payload: Any,
    zoom: int,
    x: int,
    y: int,
    bbox: tuple[float, float, float, float] | None = None,
) -> list[dict[str, Any]]:
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
        clipped_segments = [coords] if bbox is None else clip_polyline_to_bbox(coords, bbox)
        if not clipped_segments:
            continue
        if len(clipped_segments) == 1:
            geometry = {"type": "LineString", "coordinates": clipped_segments[0]}
        else:
            geometry = {"type": "MultiLineString", "coordinates": clipped_segments}
        matched_value = str(line.get("matched", "")).strip().lower()
        features.append({
            "type": "Feature",
            "geometry": geometry,
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
    sample_points = _photo_grid_points(bbox, photo_grid_size, max_photo_queries)
    total_requests = len(tiles) + len(sample_points)
    if total_requests > safe_cap:
        raise ValueError(
            f"coverage plus 360-photo scan requires {total_requests} requests, above the "
            f"safe cap of {safe_cap}; lower zoom or reduce photo-grid queries"
        )
    features: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    tiles_with_tracks = 0
    for zoom_value, x, y in tiles:
        url = f"{API_ROOT}/{x}/{y}/{zoom_value}.json"
        try:
            tile_features = parse_coverage_tracks(fetch_json(url), zoom_value, x, y, bbox)
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
    photo_scan = discover_360_photo_candidates(
        bbox, grid_size=photo_grid_size, max_queries=max_photo_queries,
        radius_m=photo_radius_m, fetch_json=fetch_json,
    )
    report = {
        "schema_version": 1,
        "source": "KartaView public coverage tiles + bounded photo metadata scan",
        "dataset_attribution": DATASET_ATTRIBUTION,
        "license": DATASET_LICENSE,
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "bbox_south_west_north_east": list(bbox),
        "zoom": zoom,
        "request_count": total_requests,
        "coverage_tile_request_count": len(tiles),
        "photo_query_count": photo_scan["query_count"],
        "photo_rows_returned": photo_scan["photo_rows_returned"],
        "unique_360_photo_candidates_inside_bbox": photo_scan["unique_360_photo_candidates_inside_bbox"],
        "360_photo_candidates_outside_bbox": photo_scan["360_photo_candidates_outside_bbox"],
        "photo_query_failures": photo_scan["query_failures"],
        "photo_sample_points": photo_scan["sample_points"],
        "tile_count": len(tiles),
        "tiles_with_coverage_tracks": tiles_with_tracks,
        "coverage_track_count": len(features),
        "matched_to_osm_track_count": sum(1 for f in features if f["properties"]["matched_to_osm"]),
        "unmatched_track_count": sum(1 for f in features if not f["properties"]["matched_to_osm"]),
        "failed_tile_count": len(failures),
        "failed_tiles": failures,
        "limitations": [
            "Coverage tracks indicate where street-level imagery was collected; they do not prove every building has a usable view.",
            "This audit downloads coverage and 360-photo metadata only, not panorama image bytes.",
            "Grid photo queries are sparse probes, not evidence that every building has a matching facade photograph.",
            "Individual photos must be matched to target buildings and preserve photographer, permalink, capture date and license attribution before baking.",
            "Street-level images may be old, occluded, angled away from a building, blurred, or not captured in full 360-degree mode.",
        ],
    }
    photo_features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [candidate["longitude"], candidate["latitude"]],
            },
            "properties": {
                key: value for key, value in candidate.items()
                if key not in {"latitude", "longitude"}
            },
        }
        for candidate in photo_scan["candidates"]
    ]
    photo_geojson = {
        "type": "FeatureCollection",
        "name": "kartaview_360_photo_candidates",
        "features": photo_features,
    }
    return {
        "geojson": geojson,
        "report": report,
        "photo_candidates": photo_scan,
        "photo_geojson": photo_geojson,
    }


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
    parser.add_argument("--photo-grid", type=int, default=0, help="optional grid size for nearby 360-photo probes")
    parser.add_argument("--photo-max-queries", type=int, default=0, help="maximum photo endpoint queries; shares the request cap")
    parser.add_argument("--photo-radius-m", type=int, default=500, help="nearby-photo query radius (1-500 m)")
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
        result = audit_coverage(
            bbox, zoom=args.zoom, max_requests=args.max_requests,
            photo_grid_size=args.photo_grid, max_photo_queries=args.photo_max_queries,
            photo_radius_m=args.photo_radius_m,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "kartaview_coverage.geojson").write_text(
        json.dumps(result["geojson"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "kartaview_coverage_report.json").write_text(
        json.dumps(result["report"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "kartaview_360_photo_candidates.json").write_text(
        json.dumps(result["photo_candidates"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "kartaview_360_photo_candidates.geojson").write_text(
        json.dumps(result["photo_geojson"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "KARTAVIEW_ATTRIBUTION.txt").write_text(
        f"{DATASET_ATTRIBUTION}\nLicense: {DATASET_LICENSE} — https://creativecommons.org/licenses/by-sa/4.0/\n"
        "Coverage tracks and sampled 360-photo metadata only; no panorama image bytes downloaded by this audit. Each panorama used in-game needs its own photographer, permalink, capture date, and license in the shipped attribution manifest.\n",
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
        "photo_query_count": report["photo_query_count"],
        "unique_360_photo_candidates_inside_bbox": report["unique_360_photo_candidates_inside_bbox"],
        "photo_query_failures": len(report["photo_query_failures"]),
        "geojson": str(args.out / "kartaview_coverage.geojson"),
        "report": str(args.out / "kartaview_coverage_report.json"),
        "photo_candidates": str(args.out / "kartaview_360_photo_candidates.json"),
    }, ensure_ascii=False))
    return 0 if args.allow_partial or (report["failed_tile_count"] == 0 and not report["photo_query_failures"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
