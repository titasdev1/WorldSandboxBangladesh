#!/usr/bin/env python3
"""Report real Android APK and downloaded-asset sizes separately.

This prevents confusing the GitHub artifact container with the APK itself and
makes optional asset-pipeline regressions visible in CI logs.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "external_content"
BUILD_ROOT = ROOT / "build"
REPORT_PATH = BUILD_ROOT / "asset_build_report.json"


def bytes_for(path: pathlib.Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def manifest_summary() -> dict:
    summary = {
        "asset_root_bytes": bytes_for(ASSET_ROOT) if ASSET_ROOT.exists() else 0,
        "asset_files_total": 0,
        "asset_files_by_pack": {},
        "model_count_by_pack": {},
        "pbr_surface_count": 0,
        "pbr_map_count": 0,
        "pbr_map_bytes": 0,
        "manifests": [],
    }
    if not ASSET_ROOT.exists():
        return summary

    for pack in sorted(p for p in ASSET_ROOT.iterdir() if p.is_dir()):
        files = [p for p in pack.rglob("*") if p.is_file()]
        summary["asset_files_by_pack"][pack.name] = len(files)
        summary["asset_files_total"] += len(files)
        summary["asset_files_by_pack"][pack.name + "_bytes"] = sum(p.stat().st_size for p in files)
        manifest_path = pack / "asset_manifest.json"
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            summary["manifests"].append({"path": manifest_path.relative_to(ROOT).as_posix(), "error": str(exc)})
            continue
        summary["manifests"].append({
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "available": data.get("available"),
            "license": data.get("license"),
            "model_count": data.get("model_count", len(data.get("models", [])) if isinstance(data.get("models"), list) else 0),
            "surface_count": len(data.get("surfaces", {})) if isinstance(data.get("surfaces"), dict) else 0,
            "note": data.get("note", ""),
        })
        model_count = data.get("model_count")
        if model_count is None and isinstance(data.get("models"), list):
            model_count = len(data["models"])
        if model_count is not None:
            summary["model_count_by_pack"][pack.name] = int(model_count)
        surfaces = data.get("surfaces", {})
        if isinstance(surfaces, dict):
            summary["pbr_surface_count"] += len(surfaces)
            for surface in surfaces.values():
                maps = surface.get("maps", {}) if isinstance(surface, dict) else {}
                if not isinstance(maps, dict):
                    continue
                for resource_path in maps.values():
                    if not isinstance(resource_path, str) or not resource_path.startswith("res://"):
                        continue
                    path = ROOT / resource_path[6:]
                    if path.is_file():
                        summary["pbr_map_count"] += 1
                        summary["pbr_map_bytes"] += path.stat().st_size
    return summary


def main() -> int:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    apk_files = sorted(p for p in BUILD_ROOT.rglob("*.apk") if p.is_file())
    report = {
        "report_version": 1,
        "project": "World Sandbox: Bangladesh / Project A-Square",
        "measurement_note": "APK bytes are measured directly from .apk files. GitHub Actions artifact-container bytes are a separate metric and must not be substituted here.",
        "apk_files": [
            {"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size}
            for p in apk_files
        ],
        "apk_total_bytes": sum(p.stat().st_size for p in apk_files),
        "assets": manifest_summary(),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("=== ASSET / APK SIZE AUDIT (bytes are exact file sizes) ===")
    print(json.dumps(report, indent=2))
    print(f"Saved report: {REPORT_PATH.relative_to(ROOT).as_posix()}")
    if not apk_files:
        print("WARNING: no APK files found; report currently describes source assets only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
