#!/usr/bin/env python3
"""Download and reconcile Overture building footprints with mapped OSM buildings."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import MultiPolygon, Polygon, box, shape

OVERTURE_SOURCE_DATASET = "Overture Maps buildings theme"
OVERTURE_SOURCE_URL = "https://docs.overturemaps.org/getting-data/overturemaps-py/"
OVERTURE_ATTRIBUTION = (
    "Supplemental building footprints: Overture Maps Foundation Buildings theme, "
    "downloaded with the official Overture Maps Python client. Feature-level source "
    "datasets and record IDs are preserved in Overture building tags. Overture can "
    "combine multiple upstream sources; follow current attribution guidance and "
    "per-feature provenance. https://docs.overturemaps.org/getting-data/"
)
_BUILDING_CLASSES = {
    "apartments", "barn", "beach_hut", "boathouse", "bungalow", "cabin",
    "carport", "cathedral", "chapel", "church", "civic", "college",
    "commercial", "cowshed", "detached", "dormitory", "factory", "farm",
    "fire_station", "garage", "garages", "ger", "government", "greenhouse",
    "hangar", "hospital", "hotel", "house", "houseboat", "hut", "industrial",
    "kindergarten", "kiosk", "library", "mosque", "monastery", "office",
    "outbuilding", "parking", "pavilion", "post_office", "religious", "retail",
    "school", "semidetached_house", "shed", "shelter", "shrine", "silo",
    "stable", "stadium", "sty", "supermarket", "temple", "terrace", "toilets",
    "train_station", "transformer_tower", "university", "warehouse",
    "wayside_shrine", "residential", "service", "transportation",
}
_CLASS_ALIASES = {
    "dwelling_house": "house", "semi": "semidetached_house",
    "apartment": "apartments", "glasshouse": "greenhouse", "agricultural": "farm",
}


def _valid_float(value: Any, minimum: float, maximum: float) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
        return None
    return parsed


def _primary_name(names: Any) -> str:
    if isinstance(names, dict):
        primary = names.get("primary")
        if isinstance(primary, str):
            return primary.strip()
        if isinstance(primary, dict):
            for value in primary.values():
                if isinstance(value, str) and value.strip():
                    return value.strip()
        common = names.get("common")
        if isinstance(common, list):
            for record in common:
                if isinstance(record, dict):
                    value = record.get("value") or record.get("name")
                    if isinstance(value, str) and value.strip():
                        return value.strip()
    return ""


def _geojson_features(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    try:
        document = json.loads(raw)
    except json.JSONDecodeError:
        features: list[dict[str, Any]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict) and item.get("type") == "Feature":
                features.append(item)
        return features
    if isinstance(document, dict) and document.get("type") == "FeatureCollection":
        return [feature for feature in document.get("features", []) if isinstance(feature, dict)]
    if isinstance(document, dict) and document.get("type") == "Feature":
        return [document]
    raise ValueError(f"Overture output is not valid GeoJSON: {path}")


def download_overture_buildings(
    bounds: tuple[float, float, float, float],
    output_path: Path,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    """Download only a batch bbox; bounds are south, west, north, east."""
    south, west, north, east = (float(value) for value in bounds)
    if not (-90 < south < north < 90 and -180 < west < east < 180):
        raise ValueError(f"Invalid Overture bbox: {bounds}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cli = shutil.which("overturemaps")
    if not cli:
        raise RuntimeError(
            "The official overturemaps CLI is required. Install it with python -m pip install overturemaps."
        )
    command = [
        cli, "download", f"--bbox={west:.8f},{south:.8f},{east:.8f},{north:.8f}",
        "-f", "geojson", "--type=building", "-o", str(output_path),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_seconds, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Overture building download timed out after {timeout_seconds}s") from exc
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "no diagnostic output")[-3000:]
        raise RuntimeError(f"Overture building download failed ({result.returncode}): {tail}")
    if not output_path.is_file() or output_path.stat().st_size < 2:
        raise RuntimeError("Overture CLI returned success without a non-empty GeoJSON file")
    features = _geojson_features(output_path)
    try:
        client_version = importlib.metadata.version("overturemaps")
    except importlib.metadata.PackageNotFoundError:
        client_version = "unknown"
    provenance = {
        "source": "Overture Maps Foundation Buildings theme",
        "source_url": OVERTURE_SOURCE_URL,
        "query_bbox_wsen": [west, south, east, north],
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "client_version": client_version,
        "release_policy": "official client STAC latest at download time; cached for this source commit and tile batch",
        "feature_records_in_response": len(features),
        "output_file": output_path.name,
    }
    output_path.with_suffix(".provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return provenance


def read_overture_provenance(path: Path) -> dict[str, Any]:
    provenance_path = path.with_suffix(".provenance.json")
    if provenance_path.is_file():
        try:
            document = json.loads(provenance_path.read_text(encoding="utf-8"))
            if isinstance(document, dict):
                return document
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "source": "Overture Maps Foundation Buildings theme",
        "source_url": OVERTURE_SOURCE_URL,
        "release_policy": "cache metadata missing; upstream release not independently recorded",
        "output_file": path.name,
    }


def load_overture_buildings(
    path: Path,
    bounds: tuple[float, float, float, float] | None = None,
) -> list[dict[str, Any]]:
    """Convert Overture GeoJSON buildings into source-labelled map-pipeline ways."""
    if not path.is_file():
        raise FileNotFoundError(f"Overture building data is missing: {path}")
    query_bbox = None
    if bounds is not None:
        south, west, north, east = (float(value) for value in bounds)
        query_bbox = box(west, south, east, north)
    result: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for feature in _geojson_features(path):
        properties = feature.get("properties") or {}
        raw_geometry = feature.get("geometry")
        if not isinstance(properties, dict) or not isinstance(raw_geometry, dict):
            continue
        try:
            geometry = shape(raw_geometry)
        except Exception:
            continue
        if geometry.is_empty or not isinstance(geometry, (Polygon, MultiPolygon)):
            continue
        if not geometry.is_valid:
            geometry = geometry.buffer(0)
        if geometry.is_empty or (query_bbox is not None and not geometry.intersects(query_bbox)):
            continue
        source_id = str(properties.get("id") or feature.get("id") or "").strip()
        if not source_id:
            source_id = hashlib.sha256(
                json.dumps(raw_geometry, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
        raw_class = str(properties.get("class") or "").strip().lower().replace(" ", "_")
        building_class = _CLASS_ALIASES.get(raw_class, raw_class)
        subtype = str(properties.get("subtype") or "").strip().lower()
        subtype_default = {
            "residential": "residential", "commercial": "commercial",
            "industrial": "industrial", "education": "school", "medical": "hospital",
            "religious": "religious", "outbuilding": "outbuilding", "service": "service",
        }.get(subtype, "yes")
        building_value = building_class if building_class in _BUILDING_CLASSES else subtype_default
        name = _primary_name(properties.get("names"))
        height = _valid_float(properties.get("height"), 2.5, 250.0)
        floor_count = _valid_float(properties.get("num_floors", properties.get("numFloors")), 1.0, 70.0)
        sources = properties.get("sources", [])
        source_datasets = sorted({
            str(source.get("dataset", "")).strip()
            for source in sources
            if isinstance(source, dict) and str(source.get("dataset", "")).strip()
        }) if isinstance(sources, list) else []
        polygons = [geometry] if isinstance(geometry, Polygon) else list(geometry.geoms)
        for part_no, polygon in enumerate(polygons, start=1):
            if not isinstance(polygon, Polygon) or polygon.is_empty or polygon.area < 1e-12:
                continue
            identifier = int(
                hashlib.sha256(f"{source_id}:{part_no}".encode("utf-8")).hexdigest()[:11], 16
            )
            while identifier in seen_ids:
                identifier += 1
            seen_ids.add(identifier)
            tags: dict[str, str] = {
                "building": building_value, "source": "Overture Maps Foundation",
                "source_dataset": OVERTURE_SOURCE_DATASET, "overture_id": source_id,
                "overture:class": raw_class, "overture:subtype": subtype,
                "overture_source_datasets": ";".join(source_datasets),
            }
            if name:
                tags["name"] = name
            if height is not None:
                tags["overture:height"] = str(height)
            if floor_count is not None:
                tags["overture:num_floors"] = str(int(floor_count))
            for source_key, target_key in (
                ("facade_color", "building:colour"), ("roof_color", "roof:colour"),
                ("roof_shape", "roof:shape"), ("facade_material", "building:material"),
                ("roof_material", "roof:material"),
            ):
                value = properties.get(source_key)
                if isinstance(value, str) and value.strip():
                    tags[target_key] = value.strip()
            exterior = list(polygon.exterior.coords)
            if exterior[0] != exterior[-1]:
                exterior.append(exterior[0])
            element: dict[str, Any] = {
                "type": "way", "id": identifier, "tags": tags,
                "geometry": [{"lat": float(lat), "lon": float(lon)} for lon, lat in exterior],
                "_bbox": [float(polygon.bounds[0]), float(polygon.bounds[1]),
                          float(polygon.bounds[2]), float(polygon.bounds[3])],
                "_source": "overture",
            }
            if polygon.interiors:
                element["inner_rings"] = [
                    [{"lat": float(lat), "lon": float(lon)} for lon, lat in ring.coords]
                    for ring in polygon.interiors
                ]
            result.append(element)
    return result


def _element_polygon(element: dict[str, Any]) -> Polygon | None:
    if element.get("type") not in {"way", "relation"}:
        return None
    coordinates = element.get("geometry", [])
    if not isinstance(coordinates, list) or len(coordinates) < 4:
        return None
    try:
        exterior = [(float(point["lon"]), float(point["lat"])) for point in coordinates]
        holes = [
            [(float(point["lon"]), float(point["lat"])) for point in ring]
            for ring in element.get("inner_rings", [])
            if isinstance(ring, list) and len(ring) >= 4
        ]
        polygon = Polygon(exterior, holes)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if isinstance(polygon, Polygon) and not polygon.is_empty and polygon.area > 1e-12:
            return polygon
    except (KeyError, TypeError, ValueError):
        return None
    return None


def _grid_keys(bounds: tuple[float, float, float, float], cell_degrees: float) -> list[tuple[int, int]]:
    min_x, min_y, max_x, max_y = bounds
    x0, y0 = math.floor(min_x / cell_degrees), math.floor(min_y / cell_degrees)
    x1, y1 = math.floor(max_x / cell_degrees), math.floor(max_y / cell_degrees)
    if (x1 - x0 + 1) * (y1 - y0 + 1) > 4096:
        cx = math.floor(((min_x + max_x) * 0.5) / cell_degrees)
        cy = math.floor(((min_y + max_y) * 0.5) / cell_degrees)
        return [(cx + dx, cy + dy) for dx in range(-2, 3) for dy in range(-2, 3)]
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def deduplicate_overture_overlaps(
    elements: list[dict[str, Any]],
    overlap_threshold: float = 0.60,
    cell_degrees: float = 0.002,
) -> tuple[list[dict[str, Any]], int]:
    """Prefer OSM geometry where it overlaps Overture, retaining uncovered footprints."""
    if not 0.0 < overlap_threshold <= 1.0:
        raise ValueError("overlap_threshold must be in (0, 1]")
    if cell_degrees <= 0:
        raise ValueError("cell_degrees must be positive")
    spatial_index: dict[tuple[int, int], list[tuple[int, Polygon]]] = {}
    geometries: dict[int, Polygon] = {}

    def is_building(element: dict[str, Any]) -> bool:
        tags = element.get("tags", {})
        return bool(tags.get("building") or tags.get("building:part"))

    for index, element in enumerate(elements):
        tags = element.get("tags", {})
        if not is_building(element) or tags.get("source_dataset") == OVERTURE_SOURCE_DATASET:
            continue
        polygon = _element_polygon(element)
        if polygon is None:
            continue
        geometries[index] = polygon
        for cell in _grid_keys(polygon.bounds, cell_degrees):
            spatial_index.setdefault(cell, []).append((index, polygon))

    drop_indices: set[int] = set()
    dropped = 0
    for index, element in enumerate(elements):
        tags = element.get("tags", {})
        if tags.get("source_dataset") != OVERTURE_SOURCE_DATASET or not is_building(element):
            continue
        polygon = _element_polygon(element)
        if polygon is None:
            continue
        area = float(polygon.area)
        candidate_indexes: set[int] = set()
        for cell in _grid_keys(polygon.bounds, cell_degrees):
            candidate_indexes.update(item_index for item_index, _ in spatial_index.get(cell, []))
        duplicate = False
        for candidate_index in candidate_indexes:
            candidate = geometries[candidate_index]
            smaller_area = min(area, float(candidate.area))
            if smaller_area <= 1e-12:
                continue
            try:
                intersection_area = float(polygon.intersection(candidate).area)
            except Exception:
                continue
            if intersection_area / smaller_area >= overlap_threshold:
                duplicate = True
                break
        if duplicate:
            drop_indices.add(index)
            dropped += 1
            continue
        geometries[index] = polygon
        for cell in _grid_keys(polygon.bounds, cell_degrees):
            spatial_index.setdefault(cell, []).append((index, polygon))
    return [element for index, element in enumerate(elements) if index not in drop_indices], dropped
