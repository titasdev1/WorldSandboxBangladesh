#!/usr/bin/env python3
"""Production repository gate for World Sandbox: Bangladesh.

This gate intentionally checks production integrity, not workflow-count progress.
It runs before the canonical Android export and fails closed on regressions such as
multiple APK-producing workflows, missing core files, malformed state metadata, or
nested archive/filler artifacts.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED = [
    "project.godot",
    "Main.tscn",
    "world.gd",
    "player.gd",
    "hud.gd",
    "vehicle.gd",
    "character_visual.gd",
    "tools/fetch_free_assets.py",
    "tools/fetch_city_assets.py",
    "city_asset_factory.gd",
    "development_state.json",
    "development_roadmap.md",
    "PRODUCTION_MASTER_DIRECTIVE.md",
    ".github/workflows/android.yml",
]

for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        raise SystemExit(f"PRODUCTION GATE FAILED: missing {rel}")

state_path = ROOT / "development_state.json"
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"PRODUCTION GATE FAILED: development_state.json is invalid: {exc}")

if state.get("canonical_repository") != "titasdev1/WorldSandboxBangladesh":
    raise SystemExit("PRODUCTION GATE FAILED: canonical repository metadata mismatch")

# There must be one APK-producing workflow: android.yml.
workflow_dir = ROOT / ".github" / "workflows"
apk_workflows = []
for p in workflow_dir.glob("*.y*ml"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"presets_to_export:\s*Android|\.apk\b|godot-export", text, re.I):
        apk_workflows.append(p.name)

if apk_workflows != ["android.yml"]:
    raise SystemExit(
        "PRODUCTION GATE FAILED: expected exactly one APK workflow (android.yml), "
        f"found {apk_workflows}"
    )

# Require visible-model systems to be wired into the canonical game path.
world_text = (ROOT / "world.gd").read_text(encoding="utf-8")
vehicle_text = (ROOT / "vehicle.gd").read_text(encoding="utf-8")
population_text = (ROOT / "systems" / "population_factory.gd").read_text(encoding="utf-8")
if "HumanoidVisual.new()" not in world_text or "HumanoidVisual.new()" not in population_text:
    raise SystemExit("PRODUCTION GATE FAILED: humanoid visual rig is not integrated into player and NPC spawn paths")
for builder in ("_build_car", "_build_cng", "_build_rickshaw", "_build_bus", "_build_motorcycle"):
    if f"func {builder}(" not in vehicle_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: missing vehicle visual builder {builder}")
if "func _try_load_authored_model()" not in vehicle_text:
    raise SystemExit("PRODUCTION GATE FAILED: optional authored vehicle loader is missing")
if "city_asset_factory.configure(self)" not in world_text or "spawn_building(Vector3(x, 0, z)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: authored city building factory is not integrated into the world")
city_factory_text = (ROOT / "city_asset_factory.gd").read_text(encoding="utf-8")
if "MANIFESTS" not in city_factory_text or "spawn_building" not in city_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: city asset factory is missing manifest-driven building placement")
asset_manifest_path = ROOT / "content" / "asset_pipeline_manifest.json"
try:
    asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"PRODUCTION GATE FAILED: asset manifest is invalid: {exc}")
if not any(
    item.get("id") == "kenney_car_kit" and item.get("license") == "CC0-1.0"
    for item in asset_manifest.get("optional_external_sources", [])
):
    raise SystemExit("PRODUCTION GATE FAILED: optional CC0 vehicle source/provenance is missing")

# Keep feature modules as repository material, but don't pretend they are all integrated.
features = sorted((ROOT / "features").glob("feature_*.gd"))
if len(features) < 90:
    raise SystemExit(f"PRODUCTION GATE FAILED: expected retained feature modules, found {len(features)}")

# Reject accidental archives checked into the game tree.
nested_zips = [
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*.zip")
    if ".git" not in p.parts
]
if nested_zips:
    raise SystemExit(f"PRODUCTION GATE FAILED: nested/filler ZIPs found: {nested_zips[:10]}")

print("PRODUCTION GATE PASSED")
print(f"Canonical project: {state['canonical_repository']}")
print(f"Retained feature modules: {len(features)}")
print("Canonical Android pipeline: .github/workflows/android.yml")
print("No workflow-count progress is treated as game progress.")
