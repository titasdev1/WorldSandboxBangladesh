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
    "real_dhaka_tile_loader.gd",
    "player.gd",
    "hud.gd",
    "virtual_stick.gd",
    "vehicle.gd",
    "character_visual.gd",
    "tools/fetch_free_assets.py",
    "tools/fetch_city_assets.py",
    "city_asset_factory.gd",
    "systems/mission_factory.gd",
    "systems/interior_factory.gd",
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
if "real_dhaka_loader.configure(self)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: real-Dhaka tile loader is not wired into the canonical world")

# The mobile movement control must be a true analog circular stick, not four
# directional buttons, and its hit rectangle must not overlap the sprint button.
if 'stick.set_script(load("res://virtual_stick.gd"))' not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: circular analog movement stick is not wired into the live HUD")
stick_text = (ROOT / "virtual_stick.gd").read_text(encoding="utf-8")
for token in ("func _gui_input(", "InputEventScreenTouch", "InputEventScreenDrag", "func _release_stick()", "_sync_actions()"):
    if token not in stick_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: analog movement stick is missing {token}")
stick_position_match = re.search(r"stick\.position = Vector2\(([^)]+)\)", hud_text)
stick_size_match = re.search(r"stick\.size = Vector2\(([^)]+)\)", hud_text)
sprint_match = re.search(r'add_touch_button\("SPRINT", Vector2\(([^)]+)\), Vector2\(([^)]+)\)', hud_text)
if not stick_position_match or not stick_size_match or not sprint_match:
    raise SystemExit("PRODUCTION GATE FAILED: movement stick/sprint touch geometry cannot be verified")
def _parse_vector2(text_value: str) -> tuple[float, float]:
    try:
        x_value, y_value = (float(item.strip()) for item in text_value.split(","))
    except Exception as exc:
        raise SystemExit(f"PRODUCTION GATE FAILED: invalid touch-control Vector2: {text_value!r}") from exc
    return x_value, y_value
stick_x, stick_y = _parse_vector2(stick_position_match.group(1))
stick_w, stick_h = _parse_vector2(stick_size_match.group(1))
sprint_x, sprint_y = _parse_vector2(sprint_match.group(1))
sprint_w, sprint_h = _parse_vector2(sprint_match.group(2))
if not (sprint_x >= stick_x + stick_w or sprint_x + sprint_w <= stick_x or
        sprint_y >= stick_y + stick_h or sprint_y + sprint_h <= stick_y):
    raise SystemExit("PRODUCTION GATE FAILED: sprint button overlaps the movement stick hit area")

# Main.tscn owns one mission factory; dynamic clones duplicate the 4,000-job
# catalogue and target markers and can create hidden CPU/memory load on mobile.
main_scene_text = (ROOT / "Main.tscn").read_text(encoding="utf-8")
if '[node name="MissionFactory" type="Node3D" parent="."]' not in main_scene_text or 'path="res://systems/mission_factory.gd"' not in main_scene_text:
    raise SystemExit("PRODUCTION GATE FAILED: Main.tscn must own the canonical MissionFactory node")
if "side_mission_factory" in world_text or "mission_factory_node" in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: duplicate runtime MissionFactory instances are forbidden")
hud_text = (ROOT / "hud.gd").read_text(encoding="utf-8")
if 'get_node_or_null("MissionFactory")' not in hud_text or "DESHI JOB %04d/4000" not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: Deshi mission catalogue is not visible in the HUD")
if 'load("res://systems/interior_factory.gd").new()' not in world_text or "try_interior_interaction" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: generated building interiors are not wired into the canonical world")
player_text = (ROOT / "player.gd").read_text(encoding="utf-8")
if "func toggle_camera_view_mode()" not in player_text or 'camera_view_mode == "first_person"' not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: first-person/third-person camera modes are not implemented")
if "CameraViewToggle" not in hud_text or "_toggle_camera_view" not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: first-person/third-person toggle is not exposed in the touch HUD")
if 'add_touch_button("AIM"' not in hud_text or 'Input.is_action_pressed("aim")' not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: hold-to-aim zoom is not integrated into the player and touch HUD")
if "CombatCrosshair" not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: combat reticle is missing from the HUD")
if "camera.global_transform.basis.z.normalized()" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: firing direction is not aligned with the active camera aim")
if 'Input.is_action_pressed("fire")' not in player_text or 'Input.is_action_just_pressed("reload")' not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: automatic fire and manual reload controls are missing")
if 'add_touch_button("RELOAD"' not in hud_text or 'reload={' not in (ROOT / "project.godot").read_text(encoding="utf-8"):
    raise SystemExit("PRODUCTION GATE FAILED: reload is not available through the mobile HUD and input map")
interior_text = (ROOT / "systems" / "interior_factory.gd").read_text(encoding="utf-8")
if "CeilingFanAnimated" not in interior_text or "open_interior" not in interior_text:
    raise SystemExit("PRODUCTION GATE FAILED: generated interior runtime/animated dressing is missing")
loader_text = (ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
for token in ("map_tiles_manifest.json", "LOAD_RADIUS_M", "UNLOAD_RADIUS_M", "_geo_to_world", "create_trimesh_collision"):
    if token not in loader_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: real-Dhaka tile streamer missing {token}")
if "func _mount_external_map_packs()" not in loader_text or "ProjectSettings.load_resource_pack(ProjectSettings.globalize_path(pack_path), true)" not in loader_text or 'user://map_packs' not in loader_text:
    raise SystemExit("PRODUCTION GATE FAILED: external map PCK patches are not supported by the canonical loader")
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

# Require the 4,000-entry Deshi side-job system to be wired into the actual world/HUD.
mission_factory_path = ROOT / "systems" / "mission_factory.gd"
if not mission_factory_path.is_file():
    raise SystemExit("PRODUCTION GATE FAILED: missing systems/mission_factory.gd")
mission_factory_text = mission_factory_path.read_text(encoding="utf-8")
hud_text = (ROOT / "hud.gd").read_text(encoding="utf-8")
if 'get_node_or_null("MissionFactory")' not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: HUD does not read the canonical side-mission state")
inventory_text = (ROOT / "inventory_system.gd").read_text(encoding="utf-8")
shop_text = (ROOT / "shop_system.gd").read_text(encoding="utf-8")
vehicle_text = (ROOT / "vehicle.gd").read_text(encoding="utf-8")
player_text = (ROOT / "player.gd").read_text(encoding="utf-8")
save_text = (ROOT / "save_system.gd").read_text(encoding="utf-8")
if 'load("res://inventory_system.gd").new()' not in world_text or 'load("res://shop_system.gd").new()' not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: live inventory/shop services are not attached to the canonical world")
if "func buy(" not in shop_text or "func sell(" not in shop_text or "func use(" not in shop_text or 'bag.call("add"' not in shop_text:
    raise SystemExit("PRODUCTION GATE FAILED: market transactions must buy, sell and use items against real inventory")
if "func _build_shop_ui()" not in hud_text or 'shop_button.text = "SHOP"' not in hud_text or "func _shop_action(" not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: market actions are not reachable from the gameplay HUD")
if "var stamina := 100.0" not in player_text or "var sprinting :=" not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: sprint stamina is not simulated")
if "var fuel := 100.0" not in vehicle_text or "func refuel(amount: float)" not in vehicle_text or "func refuel_nearest_vehicle(" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: vehicle fuel/refuelling loop is incomplete")
if '"inventory": inventory_state' not in save_text or 'restore_persistence_state", saved_inventory' not in save_text:
    raise SystemExit("PRODUCTION GATE FAILED: inventory is not saved and restored")
for token in ("MISSIONS_PER_CATALOGUE := 4000", "func _generate_catalogue()", "func _make_target_positions(", "get_road_routes"):
    if token not in mission_factory_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: Deshi mission system missing {token}")

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
