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
    "systems/game_factory.gd",
    "systems/gameplay_factory.gd",
    "systems/vehicle_gameplay_factory.gd",
    "systems/population_factory.gd",
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
city_factory_text = (ROOT / "city_asset_factory.gd").read_text(encoding="utf-8")
if "func _model_local_bounds(root: Node3D) -> AABB:" not in city_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: authored buildings are not normalized from imported mesh bounds")
if "mesh_bounds.get_endpoint(endpoint_index)" not in city_factory_text or "instance.scale = normalized_scale * variation" not in city_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: authored building scale/ground alignment is incomplete")
if "target_size.x / 8.0" in city_factory_text or "target_size.y / 12.0" in city_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: stale guessed authored-building scale heuristic remains")
map_builder_text = (ROOT / "tools/map_pipeline/build_dhaka_map.py").read_text(encoding="utf-8")
if "edge_clipped_roofs_suppressed" not in map_builder_text or "roof_within_tile" not in map_builder_text:
    raise SystemExit("PRODUCTION GATE FAILED: clipped pitched roofs may exceed map tile boundaries")
android_workflow_text = (ROOT / ".github/workflows/android.yml").read_text(encoding="utf-8")
if "EXPECTED_MAP_PIPELINE_SHA" not in android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: APK workflow does not pin the map package to current map-pipeline source")
if "path: build/canonical_release/Project-A-Square.apk" not in android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: canonical Android artifact must be a single installable APK")
map_workflow_text = (ROOT / ".github/workflows/dhaka-3d-map.yml").read_text(encoding="utf-8")
if "Dispatch Android APK build after complete Shariatpur assembly" not in map_workflow_text or "actions/workflows/android.yml/dispatches" not in map_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: complete Shariatpur map assembly is not wired to an integrated APK build")
if "city_asset_factory.configure(self)" not in world_text or "spawn_building(Vector3(x, 0, z)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: authored city building factory is not integrated into the world")
if "real_dhaka_loader.configure(self)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: real-Dhaka tile loader is not wired into the canonical world")

# The mobile movement control must be a true analog circular stick, not four
# directional buttons, and its hit rectangle must not overlap the sprint button.
hud_text = (ROOT / "hud.gd").read_text(encoding="utf-8")
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

# When the real-world district map is active, the generic starter-city
# factories must not paste their fictional grids, fixed job/shop markers,
# race rings, or outer-city traffic over mapped Shariatpur buildings/roads.
factory_specs = [
    ("systems/game_factory.gd", "_expand_ground()", "real_map_mode_fictional_grid_suppressed"),
    ("systems/gameplay_factory.gd", "_create_job_hubs()", "real_map_mode_fixed_markers_suppressed"),
    ("systems/vehicle_gameplay_factory.gd", "_add_vehicle_depots()", "real_map_mode_fixed_markers_suppressed"),
    ("systems/population_factory.gd", "_spawn_outer_traffic()", "real_map_mode_mapped_population_only"),
]
for relative_path, fictional_call, expected_status in factory_specs:
    factory_text = (ROOT / relative_path).read_text(encoding="utf-8")
    boot_start = factory_text.find("func _bootstrap()")
    map_guard = factory_text.find('if bool(world.get("real_dhaka_loaded")):', boot_start)
    generator_call = factory_text.find(fictional_call, boot_start)
    if boot_start < 0 or map_guard < 0 or generator_call < 0 or map_guard > generator_call:
        raise SystemExit(
            f"PRODUCTION GATE FAILED: {relative_path} can build fictional content before its real-map suppression guard"
        )
    if 'set_meta("real_map_overlay_suppressed", true)' not in factory_text or expected_status not in factory_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: {relative_path} does not report real-map overlay suppression")
if "get_vehicle_route_records()" not in world_text or "_spawn_mapped_traffic_vehicle(mapped_routes)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: real-map road traffic no longer uses mapped road routes")

respawn_start = world_text.find("func respawn_player():")
respawn_end = world_text.find("func try_vehicle_interaction():", respawn_start)
if respawn_start < 0 or respawn_end < 0:
    raise SystemExit("PRODUCTION GATE FAILED: canonical player respawn system is missing")
respawn_text = world_text[respawn_start:respawn_end]
for token in (
    "player.global_position = _nearest_mapped_respawn_position(player.global_position)",
    "func _nearest_mapped_respawn_position(",
    'real_dhaka_loader.call("get_nearby_road_points"',
    "best_side * 3.0",
):
    if token not in respawn_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: real-map respawn is missing mapped-road behaviour {token}")
if "player.position = Vector3(0, 0, -12)" not in respawn_text:
    raise SystemExit("PRODUCTION GATE FAILED: fictional fallback starter-city respawn is missing for non-map mode")

# The mapped NPC population may retry as more road tiles stream in, but it must
# never fall back to random fictional-city coordinates in real-map mode.
npc_start = world_text.find("func spawn_npcs():")
npc_end = world_text.find("\nfunc spawn_police():", npc_start)
if npc_start < 0 or npc_end < 0:
    raise SystemExit("PRODUCTION GATE FAILED: canonical NPC spawner is missing")
npc_spawn_text = world_text[npc_start:npc_end]
npc_map_guard = npc_spawn_text.find("if real_dhaka_loaded and mapped_routes.is_empty():")
npc_fake_fallback = npc_spawn_text.find("Vector3(rng.randf_range(-70, 70)")
if npc_map_guard < 0 or npc_fake_fallback < 0 or npc_map_guard > npc_fake_fallback:
    raise SystemExit("PRODUCTION GATE FAILED: real-map NPC spawner can use fictional fallback coordinates")
if 'npc.add_to_group("mapped_road_npc")' not in npc_spawn_text or "get_tree().get_nodes_in_group(\"mapped_road_npc\").size()" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: map-aware NPC fill does not prevent duplicate or missing road spawns")

# Grounding regression gate: build_environment runs before real-map selection
# and therefore must not create the old 180 m raised platform. Only the
# fictional fallback city's single 600 m plane may create procedural ground.
environment_start = world_text.find("func build_environment():")
city_start = world_text.find("func build_city():", environment_start)
if environment_start < 0 or city_start < 0:
    raise SystemExit("PRODUCTION GATE FAILED: world environment/city boundary is missing")
environment_text = world_text[environment_start:city_start]
if 'Vector3(0, -0.5, 0), Vector3(180, 1, 180)' in environment_text:
    raise SystemExit("PRODUCTION GATE FAILED: legacy 180 m raised platform is still created before real-map selection")
fallback_ground = factory_specs[0][0]
fallback_factory_text = (ROOT / fallback_ground).read_text(encoding="utf-8")
ground_start = fallback_factory_text.find("func _expand_ground()")
ground_end = fallback_factory_text.find("func _generate_outer_arterials()", ground_start)
ground_code = fallback_factory_text[ground_start:ground_end]
if 'Vector3(0, -0.04, 0), Vector3(CITY_RADIUS * 2.0, 0.08, CITY_RADIUS * 2.0)' not in ground_code:
    raise SystemExit("PRODUCTION GATE FAILED: fallback ground top must remain aligned at y=0")
ground_boot = fallback_factory_text.find("func _bootstrap()")
ground_guard = fallback_factory_text.find('if bool(world.get("real_dhaka_loaded")):', ground_boot)
ground_call = fallback_factory_text.find("_expand_ground()", ground_boot)
if ground_guard < 0 or ground_call < 0 or ground_guard > ground_call:
    raise SystemExit("PRODUCTION GATE FAILED: fallback ground can be created before real-map mode is checked")

# The Deshi mission board is a gameplay kiosk, not a surveyed building. On a
# real map it must be placed beside the loaded road graph, not at a fake city XYZ.
mission_factory_text = (ROOT / "systems" / "mission_factory.gd").read_text(encoding="utf-8")
hub_start = mission_factory_text.find("func _create_hub()")
hub_end = mission_factory_text.find("func _on_hub_entered", hub_start)
if hub_start < 0 or hub_end < 0:
    raise SystemExit("PRODUCTION GATE FAILED: Deshi job-board creation is missing")
hub_text = mission_factory_text[hub_start:hub_end]
for token in ('if bool(world.get("real_dhaka_loaded")):', 'loader.call("get_road_routes")', 'hub_position = best_point + sidewalk_side * 8.0', "hub.position = hub_position", "hub_created = true"):
    if token not in hub_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: real-map Deshi job-board placement missing {token}")
if "if not hub_created and is_instance_valid(world) and bool(world.get(\"real_dhaka_loaded\")):" not in mission_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: Deshi job board does not retry as road tiles stream in")

# The verified Burirhat mosque interior photo must travel through map baking,
# seed metadata, runtime rendering, and APK-byte verification. It may not be
# counted as an exterior facade photo.
map_builder_text = (ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
map_merger_text = (ROOT / "tools" / "map_pipeline" / "merge_dhaka_division_batches.py").read_text(encoding="utf-8")
interior_factory_text = (ROOT / "systems" / "interior_factory.gd").read_text(encoding="utf-8")
apk_verifier_text = (ROOT / "tools" / "verify_apk_contents.py").read_text(encoding="utf-8")
for token in (
    "def load_interior_reference_catalog(",
    "interior_reference_eligible",
    "interior_photo_reference",
    "interior_reference_photo_matches",
    '"sha256": hashlib.sha256(image_bytes).hexdigest()',
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: map baker is missing licensed interior-photo support: {token}")
if "interior_reference_photo_matches" not in map_merger_text or "INTERIOR REFERENCE ONLY" not in map_merger_text:
    raise SystemExit("PRODUCTION GATE FAILED: complete map assembly omits interior-photo licensing/provenance.")
for token in (
    "func _add_licensed_interior_photo_reference(",
    'active_seed.get("interior_reference_photo", {})',
    'ResourceLoader.load(texture_path) as Texture2D',
    'panel.set_meta("use", "INTERIOR_REFERENCE_ONLY")',
):
    if token not in interior_factory_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: interior runtime photo rendering is missing {token}")
for token in (
    'hashlib.sha256(photo_data).hexdigest()',
    "interior_reference_photo_matches",
    "INTERIOR_REFERENCE_ONLY",
    "matching tile has no interior seeds file",
):
    if token not in apk_verifier_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: APK does not verify the real interior-photo asset: {token}")
catalog_text = (ROOT / "tools" / "map_pipeline" / "shariatpur_facade_images.json").read_text(encoding="utf-8")
if '"facade_eligible": false' not in catalog_text or '"interior_reference_eligible": true' not in catalog_text:
    raise SystemExit("PRODUCTION GATE FAILED: mosque interior photo must remain blocked from exterior facades and separately approved for interior reference use")

# Keep mapped doors, actual interaction-anchor placement and hero readability
# connected to the generated metric world (without scaling real footprints).
map_builder_text = (ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
map_loader_text = (ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
character_text = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
player_text = (ROOT / "player.gd").read_text(encoding="utf-8")
world_text = (ROOT / "world.gd").read_text(encoding="utf-8")
for token in (
    "def facade_door_geometry(",
    '"door_anchor_local_m": door_anchor_local_m',
    '"door_outward_xy": door_outward_xy',
    '"facade_door_panels": facade_doors',
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: mapped-building door geometry is missing {token}")
placement_start = map_loader_text.find("func _interior_anchor_placement(")
placement_end = map_loader_text.find("func _add_walkable_collisions(", placement_start)
if placement_start < 0 or placement_end <= placement_start:
    raise SystemExit("PRODUCTION GATE FAILED: map loader entrance-anchor method is missing.")
placement_code = map_loader_text[placement_start:placement_end]
if 'seed.get("door_anchor_local_m", [])' not in placement_code or 'seed.get("door_outward_xy", [])' not in placement_code:
    raise SystemExit("PRODUCTION GATE FAILED: generated building interactions are not aligned to the baked door position.")
for token in (
    "def roof_shape_for_building(",
    "def procedural_roof_mesh(",
    '"roof_shape_model": roof_shape_model',
    '"modeled_roofs": modeled_roofs',
    "INFERRED_SMALL_LOW_RISE_HOME_NO_ROOF_SHAPE_TAG",
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: map bake is missing source-aware house roof geometry: {token}")
if "@export var is_player_character := false" not in character_text or "func _add_clothing_and_face_detail() -> void:" not in character_text:
    raise SystemExit("PRODUCTION GATE FAILED: the hero character detail pass is missing.")
for token in ("LeftEyeWhite", "NoseBridge", "ChestPocket_%s", "ShoeSole", "RadioBody", "WristWatch"):
    if token not in character_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: hero visual detail missing {token}.")
if "visual.is_player_character = true" not in world_text or "camera_distance := 4.8 if Input.is_action_pressed" not in player_text or "else 7.4" not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: hero-detail selection or mobile-readable camera distance was lost.")

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
if "func _unhandled_input(event):" not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: camera-look touch input must not steal gestures from HUD controls")
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
