#!/usr/bin/env python3
"""Fail closed when the medium-stage candidate is missing its authored model packs."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = {
    "kenney_car_kit": 30,
    "kenney_city_kit_commercial": 30,
    "kenney_city_kit_industrial": 20,
    "kenney_city_kit_suburban": 30,
}

def main() -> int:
    failures = []
    total = 0
    for pack, minimum in REQUIRED.items():
        manifest = ROOT / "external_content" / pack / "asset_manifest.json"
        if not manifest.is_file():
            failures.append(f"{pack}: manifest missing")
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"{pack}: invalid JSON ({exc})")
            continue
        models = data.get("models", [])
        count = len(models) if isinstance(models, list) else 0
        if data.get("available") is not True:
            failures.append(f"{pack}: unavailable ({data.get('reason', 'no reason')})")
            continue
        if count < minimum or int(data.get("model_count", count)) != count:
            failures.append(f"{pack}: {count} models, minimum {minimum}, manifest count mismatch")
            continue
        missing = []
        for model in models:
            if not isinstance(model, dict):
                missing.append("<malformed model record>")
                continue
            path = str(model.get("path", ""))
            if not path.startswith("res://"):
                missing.append(path or "<missing path>")
                continue
            local = ROOT / path[6:]
            if not local.is_file():
                missing.append(path)
        if missing:
            failures.append(f"{pack}: {len(missing)} model file(s) missing, e.g. {missing[:3]}")
            continue
        total += count
        print(f"MEDIUM_STAGE_ASSETS: {pack} PASS ({count} models)")
    if failures:
        print("MEDIUM_STAGE_ASSET_GATE: FAIL")
        for item in failures:
            print(" - " + item)
        return 2
    print(f"MEDIUM_STAGE_ASSET_GATE: PASS ({total} authored models across {len(REQUIRED)} packs)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
