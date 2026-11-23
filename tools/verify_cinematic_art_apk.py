#!/usr/bin/env python3
"""Verify Blender-authored login and lobby GLBs are embedded and imported in the Android APK."""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

IMPORTED_ROOT = "assets/.godot/imported/"
REQUIRED_ASSETS = (
    "assets/assets/login/shariatpur_riverfront_shophouse_hero.glb",
    "assets/assets/lobby/asquare_command_hall.glb",
)


def _resolve_imported_scene(remap_data: bytes, source_glb_name: str) -> str:
    try:
        remap_text = remap_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Import remap for {source_glb_name} is not UTF-8") from exc
    match = re.search(r'(?m)^path="res://\.godot/imported/([^"/]+\.scn)"\s*$', remap_text)
    if not match:
        raise ValueError(f"Import remap for {source_glb_name} does not name an imported .scn")
    filename = match.group(1)
    if not filename.startswith(source_glb_name + "-"):
        raise ValueError(f"Import remap for {source_glb_name} points to unexpected scene {filename}")
    return IMPORTED_ROOT + filename


def verify(apk_path: Path) -> dict:
    if not apk_path.is_file():
        raise FileNotFoundError(f"APK does not exist: {apk_path}")
    checked = []
    with zipfile.ZipFile(apk_path) as apk:
        names = set(apk.namelist())
        for source_path in REQUIRED_ASSETS:
            import_path = source_path + ".import"
            for required in (source_path, import_path):
                if required not in names:
                    raise ValueError(f"APK is missing cinematic asset entry: {required}")
            source_size = apk.getinfo(source_path).file_size
            if source_size < 100_000:
                raise ValueError(f"Cinematic GLB is unexpectedly small: {source_path} ({source_size} bytes)")
            imported_path = _resolve_imported_scene(apk.read(import_path), Path(source_path).name)
            if imported_path not in names:
                raise ValueError(f"APK is missing imported Godot scene: {imported_path}")
            imported_size = apk.getinfo(imported_path).file_size
            if imported_size <= 0:
                raise ValueError(f"Imported Godot scene is empty: {imported_path}")
            checked.append({"source":source_path,"source_bytes":source_size,
                "imported_scene":imported_path,"imported_bytes":imported_size})
    return {"status":"CINEMATIC_ART_APK_PASS","assets":checked}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.apk)
    except Exception as exc:
        raise SystemExit(f"CINEMATIC ART APK GATE FAILED: {exc}") from exc
    print("CINEMATIC_ART_APK_PASS")
    for item in report["assets"]:
        print(f"{item['source']} {item['source_bytes']} bytes -> {item['imported_scene']} {item['imported_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
