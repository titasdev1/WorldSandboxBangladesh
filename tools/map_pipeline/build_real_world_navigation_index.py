#!/usr/bin/env python3
"""Build an auditable road/building metadata index from the map pipeline's source GeoJSON.

This intentionally uses only source geometry/tags already present in the map package.
It never invents road names, floor counts, coordinates, or facade-photo rights.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def _tags(feature: dict[str, Any]) -> dict[str, Any]:
    props = feature.get("properties") or {}
    tags = props.get("tags")
    if isinstance(tags, dict):
        return tags
    # Some GeoJSON exporters flatten OSM tags into properties.
    return {str(k): v for k, v in props.items() if isinstance(v, (str, int, float, bool))}


def _iter_features(path: Path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        for feature in payload.get("features", []):
            if isinstance(feature, dict):
                yield feature
    elif isinstance(payload, dict) and payload.get("type") == "Feature":
        yield payload


def _coords(geometry: dict[str, Any] | None) -> list[tuple[float, float]]:
    if not isinstance(geometry, dict):
        return []
    found: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, (list, tuple)):
            if len(value) >= 2 and all(isinstance(v, (int, float)) for v in value[:2]):
                lon, lat = float(value[0]), float(value[1])
                # GeoJSON WGS84 coordinates are longitude, latitude.
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    found.append((lon, lat))
                return
            for child in value:
                visit(child)

    visit(geometry.get("coordinates"))
    return found



def _line_paths(geometry: dict[str, Any] | None) -> list[list[list[float]]]:
    """Preserve road polylines for an offline routing graph (WGS84 lon/lat)."""
    if not isinstance(geometry, dict):
        return []
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    raw_paths = [coordinates] if kind == "LineString" else (coordinates if kind == "MultiLineString" else [])
    result: list[list[list[float]]] = []
    for path in raw_paths:
        if not isinstance(path, list):
            continue
        points: list[list[float]] = []
        for point in path:
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                lon, lat = point[0], point[1]
                if isinstance(lon, (int, float)) and isinstance(lat, (int, float)) and -180 <= lon <= 180 and -90 <= lat <= 90:
                    points.append([round(float(lon), 7), round(float(lat), 7)])
        if len(points) >= 2:
            result.append(points)
    return result

def _centroid(coords: list[tuple[float, float]]) -> dict[str, float] | None:
    if not coords:
        return None
    # A transparent vertex mean is stable and dependency-free. It is an approximate
    # label point, not a surveyed entrance or a true polygon centroid.
    return {
        "longitude": round(sum(p[0] for p in coords) / len(coords), 7),
        "latitude": round(sum(p[1] for p in coords) / len(coords), 7),
        "coordinate_method": "source_geometry_vertex_mean_approximation",
    }


def _positive_number(value: Any) -> float | None:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None



def _validated_floor_evidence(path: Path | None) -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
    if path is None or not path.is_file():
        return {}, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [{"osm_id": "", "reason": f"cannot read evidence registry: {exc}"}]
    records = payload.get("records", []) if isinstance(payload, dict) else []
    verified: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, str]] = []
    allowed_sources = {
        "official_plan", "official_building_profile", "licensed_street_imagery",
        "owner_photograph", "field_survey", "building_documentation",
    }
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            rejected.append({"osm_id": "", "reason": "record is not an object"})
            continue
        osm_id = str(record.get("osm_id", "")).strip()
        floor_count = record.get("floor_count")
        source_url = str(record.get("evidence_source_url", "")).strip()
        source_type = str(record.get("evidence_source_type", "")).strip()
        reviewer = str(record.get("reviewer", "")).strip()
        reviewed_at = str(record.get("reviewed_at", "")).strip()
        notes = str(record.get("evidence_notes", "")).strip()
        valid_count = isinstance(floor_count, int) and not isinstance(floor_count, bool) and 1 <= floor_count <= 200
        try:
            datetime.date.fromisoformat(reviewed_at)
            valid_date = len(reviewed_at) == 10
        except ValueError:
            valid_date = False
        if not osm_id:
            reason = "missing osm_id"
        elif not valid_count:
            reason = "floor_count must be an integer from 1 to 200"
        elif not source_url.startswith("https://"):
            reason = "evidence_source_url must be HTTPS"
        elif source_type not in allowed_sources:
            reason = "evidence_source_type is not an approved evidence class"
        elif not reviewer:
            reason = "missing human reviewer"
        elif not valid_date:
            reason = "reviewed_at must use YYYY-MM-DD"
        elif not notes:
            reason = "missing evidence_notes"
        elif str(record.get("verification_status", "")) != "INDEPENDENTLY_VERIFIED":
            reason = "verification_status must explicitly be INDEPENDENTLY_VERIFIED"
        else:
            verified[osm_id] = record
            continue
        rejected.append({"osm_id": osm_id, "reason": reason})
    return verified, rejected

def build_index(source: Path, floor_evidence_path: Path | None = None) -> dict[str, Any]:
    roads: dict[str, dict[str, Any]] = {}
    buildings: dict[str, dict[str, Any]] = {}
    places: dict[str, dict[str, Any]] = {}
    source_files = 0
    for path in sorted(source.rglob("*.geojson")):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue
        source_files += 1
        for feature in _iter_features(path):
            tags = _tags(feature)
            geom = feature.get("geometry")
            coords = _coords(geom)
            props = feature.get("properties") or {}
            osm_id = str(props.get("osm_id", props.get("id", feature.get("id", ""))))
            if not osm_id:
                osm_id = f"{path.name}:{len(roads) + len(buildings)}"
            center = _centroid(coords)
            highway = tags.get("highway")
            if highway and coords:
                key = f"way/{osm_id}"
                roads[key] = {
                    "osm_id": key,
                    "name": tags.get("name"),
                    "name_bn": tags.get("name:bn"),
                    "official_name": tags.get("official_name"),
                    "ref": tags.get("ref"),
                    "highway_class": highway,
                    "coordinates": center,
                    "geometry_paths": _line_paths(geom),
                    "source_file": str(path.relative_to(source)),
                    "name_status": "NAMED" if tags.get("name") or tags.get("name:bn") or tags.get("ref") else "UNNAMED_IN_SOURCE",
                }
            place_keys = ("amenity", "shop", "tourism", "leisure", "office", "healthcare", "education", "public_transport", "railway", "historic", "craft", "emergency")
            if center and any(tags.get(k) for k in place_keys) and any(tags.get(k) for k in ("name", "name:bn", "official_name", "brand")):
                key = str(feature.get("id", osm_id))
                places[key] = {
                    "osm_id": key,
                    "name": tags.get("name"),
                    "name_bn": tags.get("name:bn"),
                    "official_name": tags.get("official_name"),
                    "brand": tags.get("brand"),
                    "categories": {k: tags[k] for k in place_keys if tags.get(k)},
                    "coordinates": center,
                    "source_file": str(path.relative_to(source)),
                }
            if "building" in tags and coords:
                key = f"way/{osm_id}"
                levels = _positive_number(tags.get("building:levels"))
                roof_levels = _positive_number(tags.get("roof:levels"))
                height = _positive_number(tags.get("height"))
                evidence = "OSM_BUILDING_LEVELS" if levels is not None else (
                    "OSM_HEIGHT_ONLY" if height is not None else "MISSING_SOURCE_LEVELS_AND_HEIGHT"
                )
                buildings[key] = {
                    "osm_id": key,
                    "name": tags.get("name"),
                    "name_bn": tags.get("name:bn"),
                    "official_name": tags.get("official_name"),
                    "building_type": tags.get("building"),
                    "levels": int(levels) if levels is not None and levels.is_integer() else levels,
                    "roof_levels": roof_levels,
                    "height_m": height,
                    "min_height_m": _positive_number(tags.get("min_height")),
                    "coordinates": center,
                    "source_file": str(path.relative_to(source)),
                    "floor_count_source": evidence,
                    "floor_count_tagged_in_source": levels is not None,
                    "floor_count_independently_verified": False,
                    "facade_reference": {
                        "image_url": tags.get("image"),
                        "wikimedia_commons": tags.get("wikimedia_commons"),
                        "mapillary_reference": tags.get("mapillary"),
                        "facade_material": tags.get("facade:material", tags.get("building:material")),
                        "facade_colour": tags.get("facade:colour", tags.get("building:colour", tags.get("building:color"))),
                        "roof_shape": tags.get("roof:shape"),
                        "roof_material": tags.get("roof:material"),
                        "roof_colour": tags.get("roof:colour", tags.get("roof:color")),
                        "license": None,
                        "attribution": None,
                        "status": "REFERENCE_REQUIRES_LICENSE_REVIEW" if any(tags.get(k) for k in ("image", "wikimedia_commons", "mapillary")) else "NO_FACADE_REFERENCE_IN_SOURCE",
                    },
                }
    verified_evidence, rejected_evidence = _validated_floor_evidence(floor_evidence_path)
    for building in buildings.values():
        evidence = verified_evidence.get(str(building["osm_id"]))
        if evidence is None:
            continue
        building["floor_count_independently_verified"] = True
        building["independently_verified_floor_count"] = int(evidence["floor_count"])
        building["floor_count_verification"] = {
            "status": "INDEPENDENTLY_VERIFIED",
            "evidence_source_url": evidence["evidence_source_url"],
            "evidence_source_type": evidence["evidence_source_type"],
            "reviewer": evidence["reviewer"],
            "reviewed_at": evidence["reviewed_at"],
            "evidence_notes": evidence["evidence_notes"],
        }
    named_roads = sum(1 for road in roads.values() if road["name_status"] == "NAMED")
    level_tagged = sum(1 for building in buildings.values() if building["floor_count_tagged_in_source"])
    independently_verified = sum(1 for building in buildings.values() if building["floor_count_independently_verified"])
    return {
        "schema_version": 1,
        "purpose": "real-world navigation, road labels, coordinate lookup, and floor-count evidence",
        "coordinate_system": "WGS84 longitude/latitude from source GeoJSON; point is approximate geometry vertex mean",
        "source_files_scanned": source_files,
        "floor_evidence_validation": {
            "accepted_registry_records": len(verified_evidence),
            "applied_to_mapped_buildings": independently_verified,
            "rejected_registry_records": rejected_evidence,
        },
        "counts": {
            "roads": len(roads),
            "named_roads": named_roads,
            "unnamed_roads": len(roads) - named_roads,
            "buildings": len(buildings),
            "named_places": len(places),
            "buildings_with_source_floor_count": level_tagged,
            "buildings_with_independently_verified_floor_count": independently_verified,
            "buildings_missing_source_floor_count": len(buildings) - level_tagged,
            "buildings_with_any_facade_reference": sum(1 for building in buildings.values() if building["facade_reference"]["status"] == "REFERENCE_REQUIRES_LICENSE_REVIEW"),
            "buildings_with_verified_facade_reference": 0,
        },
        "roads": sorted(roads.values(), key=lambda item: item["osm_id"]),
        "buildings": sorted(buildings.values(), key=lambda item: item["osm_id"]),
        "places": sorted(places.values(), key=lambda item: item["osm_id"]),
        "limitations": [
            "OSM name/level tags are source evidence, not guaranteed complete or independently surveyed; independently verified floor-count total remains zero until checked against reliable references.",
            "Coordinate labels are approximate feature points, not surveyed entrances.",
            "Missing floor counts must be researched from permitted street imagery, building photos, plans, or field evidence; do not silently guess.",
            "Facade imagery must be individually rights-cleared for in-game use. Google Maps imagery may be used only as permitted for reference and must not be scraped or redistributed.",
            "This index is metadata output; runtime road-label, teleport, and building rendering integration still requires a separate tested game change.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Map package directory containing source GeoJSON")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path")
    parser.add_argument("--floor-evidence", type=Path, help="Human-reviewed evidence registry; only validated records are applied")
    args = parser.parse_args()
    if not args.source.is_dir():
        parser.error(f"source directory does not exist: {args.source}")
    evidence_path = args.floor_evidence
    if evidence_path is None and (args.source / "building_floor_evidence.json").is_file():
        evidence_path = args.source / "building_floor_evidence.json"
    report = build_index(args.source, evidence_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
