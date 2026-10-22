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
    "tools/fetch_quaternius_character.py",
    "tools/merge_quaternius_character.mjs",
    "tools/verify_quaternius_character.py",
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
player_scale_text = (ROOT / "player.gd").read_text(encoding="utf-8")
if "const HUMANOID_BASE_SCALE := Vector3(0.90, 0.90, 0.90)" not in player_scale_text:
    raise SystemExit("PRODUCTION GATE FAILED: shared normalized humanoid base scale is missing")
if "visual.scale = HUMANOID_BASE_SCALE * Vector3(1.0, 0.72, 1.0) if _is_crouched else HUMANOID_BASE_SCALE" not in player_scale_text:
    raise SystemExit("PRODUCTION GATE FAILED: crouch mode can corrupt the normalized character scale")
character_visual_text = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
if "scale = Vector3(0.90, 0.90, 0.90)" not in character_visual_text or "position.y = -0.065" not in character_visual_text:
    raise SystemExit("PRODUCTION GATE FAILED: character render scale/ground alignment regressed")
for token in (
    'const AUTHORED_HERO_PATH := "res://external_content/quaternius_hero/Project_A_Square_Hero.glb"',
    "func _try_load_authored_hero() -> void:",
    "func _update_authored_animation(body: CharacterBody3D, planar_speed: float) -> void:",
    "AUTHORED_HERO_READY",
    "AUTHORED_HERO_GEAR_READY",
    "AUTHORED_HERO_FALLBACK",
    "_procedural_root.visible = false",
):
    if token not in character_visual_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: rigged hero is not safely integrated into the player visual: {token}")
hero_fetcher_text = (ROOT / "tools" / "fetch_quaternius_character.py").read_text(encoding="utf-8")
hero_verifier_text = (ROOT / "tools" / "verify_quaternius_character.py").read_text(encoding="utf-8")
regular_model = "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf"
if regular_model not in hero_fetcher_text or regular_model not in hero_verifier_text:
    raise SystemExit("PRODUCTION GATE FAILED: the playable hero must use and verify the pinned free CC0 model from the Standard archive.")
for workflow_path in (".github/workflows/android.yml", ".github/workflows/validate-godot.yml"):
    workflow_text = (ROOT / workflow_path).read_text(encoding="utf-8")
    if "quaternius-hero-v3-superhero-pinned-source" not in workflow_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: {workflow_path} may restore a stale model cache.")
hero_android_workflow_text = (ROOT / ".github" / "workflows" / "android.yml").read_text(encoding="utf-8")
if "external_content/quaternius_hero/**" not in hero_android_workflow_text or "Fetch and validate the CC0 rigged player hero" not in hero_android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: canonical Android export does not fetch/import the rigged CC0 hero before Godot export")
hero_validation_workflow_text = (ROOT / ".github" / "workflows" / "validate-godot.yml").read_text(encoding="utf-8")
if "AUTHORED_HERO_GEAR_READY" not in hero_android_workflow_text or "AUTHORED_HERO_GEAR_READY" not in hero_validation_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: runtime validation does not verify the playable hero's attached gear layer.")
if "AUTHORED_HERO_READY" not in hero_android_workflow_text or "Project_A_Square_Hero.glb" not in (ROOT / "tools" / "verify_apk_contents.py").read_text(encoding="utf-8"):
    raise SystemExit("PRODUCTION GATE FAILED: authored hero activation/package verification is disconnected")
export_presets_text = (ROOT / "export_presets.cfg").read_text(encoding="utf-8")
if 'include_filter="*.photo_bytes"' not in export_presets_text:
    raise SystemExit("PRODUCTION GATE FAILED: licensed map photo bytes are not explicitly included in Android export")
interior_factory_text = (ROOT / "systems/interior_factory.gd").read_text(encoding="utf-8")
if "FileAccess.get_file_as_bytes(texture_path)" not in interior_factory_text or "ImageTexture.create_from_image(photo_image)" not in interior_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: interior reference photos still depend on untracked dynamic image imports")
if "var hair_mesh := SphereMesh.new()" not in character_visual_text or "hair_node.scale.y = 0.68" not in character_visual_text:
    raise SystemExit("PRODUCTION GATE FAILED: invalid tall hair capsule regressed the character silhouette")
map_builder_text = (ROOT / "tools/map_pipeline/build_dhaka_map.py").read_text(encoding="utf-8")
if "edge_clipped_roofs_suppressed" not in map_builder_text or "roof_within_tile" not in map_builder_text:
    raise SystemExit("PRODUCTION GATE FAILED: clipped pitched roofs may exceed map tile boundaries")
android_workflow_text = (ROOT / ".github/workflows/android.yml").read_text(encoding="utf-8")
if "EXPECTED_MAP_PIPELINE_SHA" in android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: obsolete map SHA check refers to an unset variable")
if "LATEST_MAP_CODE_SHA" not in android_workflow_text or "git merge-base --is-ancestor" not in android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: APK workflow does not pin the map package to current map-pipeline source")
if "path: build/canonical_release/Project-A-Square.apk" not in android_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: canonical Android artifact must be a single installable APK")
map_workflow_text = (ROOT / ".github/workflows/dhaka-3d-map.yml").read_text(encoding="utf-8")
if "Dispatch Android APK build after complete Shariatpur assembly" in map_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: map workflow contains a duplicate APK dispatch path")
if "name: Project-A-Square-Shariatpur-Review-Map-" not in map_workflow_text or "Assemble complete Shariatpur District review package" not in map_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: complete Shariatpur package is not assembled and uploaded before the central APK dispatch gate")
# The map-to-APK handoff must use an explicit sequence identity; timestamps alone
# can select a newer stale ZIP produced by another concurrent/older sequence.
for token in (
    "map_sequence_id:",
    "EXPECTED_MAP_ARTIFACT",
    'MAP_SEQUENCE_ID: ${{ inputs.map_sequence_id }}',
):
    if token not in android_workflow_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: Android map selection is not bound to the exact sequence ({token})")
if '"map_sequence_id": "${MAP_SEQUENCE_ID}"' not in map_workflow_text:
    raise SystemExit("PRODUCTION GATE FAILED: completed map sequence ID is not passed to the canonical APK workflow")
for token in (
    "name: Verify continuation matches its root batch pipeline commit",
    "pipeline_commit_sha",
    "sort -V | tail -n 1",
    "Start a new sequence instead of mixing tile batches.",
):
    if token not in map_workflow_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: map continuation source-pin validation is missing {token}")
if "city_asset_factory.configure(self)" not in world_text or "spawn_building(Vector3(x, 0, z)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: authored city building factory is not integrated into the world")
if "real_dhaka_loader.configure(self)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: real-Dhaka tile loader is not wired into the canonical world")

player_interact_source = (ROOT / "player.gd").read_text(encoding="utf-8")
for token in (
    "var camera_recoil_pitch := 0.0",
    "var first_person_pitch := 0.0",
    "first_person_pitch = clampf(first_person_pitch - event.relative.y * camera_sensitivity, -65.0, 65.0)",
    "deg_to_rad(first_person_pitch + camera_recoil_pitch)",
    "func _apply_weapon_recoil() -> void:",
    "_apply_weapon_recoil()",
    "camera_recoil_pitch + (0.72 if Input.is_action_pressed(\"aim\") else 0.98)",
    "camera_recoil_pitch = move_toward(camera_recoil_pitch, 0.0, 3.8 * delta)",
    "deg_to_rad(first_person_pitch + camera_recoil_pitch)",
):
    if token not in player_interact_source:
        raise SystemExit(f"PRODUCTION GATE FAILED: camera recoil is not fully wired for fire/aim: {token}")
player_interact_start = player_interact_source.find("func interact():")
player_interact_end = player_interact_source.find("func take_damage(", player_interact_start)
player_interact_text = player_interact_source[player_interact_start:player_interact_end]
map_interact_guard = player_interact_text.find('if not bool(world.get("real_dhaka_loaded")):')
if map_interact_guard < 0:
    raise SystemExit("PRODUCTION GATE FAILED: player interaction lacks a real-map guard for starter-city interactions")
for marker in ("Vector3(42, 0, 42)", "Vector3(30, 0, -30)"):
    if player_interact_text.find(marker) < map_interact_guard:
        raise SystemExit(f"PRODUCTION GATE FAILED: fictional starter-city money marker is not confined to fallback mode: {marker}")

# Load the HUD source before any responsive-layout assertions reference it.
hud_text = (ROOT / "hud.gd").read_text(encoding="utf-8")
# Mobile aspect expansion must preserve circular controls and keep touch targets reachable.
project_text = (ROOT / "project.godot").read_text(encoding="utf-8")
if 'window/stretch/aspect="expand"' not in project_text:
    raise SystemExit("PRODUCTION GATE FAILED: mobile canvas does not expand its logical viewport to screen aspect")
if "func _relayout_mobile_controls() -> void:" not in hud_text or "get_viewport().size_changed.connect(_relayout_mobile_controls)" not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: mobile HUD does not reflow when viewport aspect changes")
for token in ('get_viewport().get_visible_rect().size', 'view_width - 200.0', 'view_width - 265.0', 'view_height - 248.0', 'ModeLobby/LobbyPanel', 'touch_action_buttons'):
    if token not in hud_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: responsive mobile HUD is missing {token}")
# The mobile movement control must be a true analog circular stick, not four
# directional buttons, and its hit rectangle must not overlap the sprint button.
hud_text = (ROOT / "hud.gd").read_text(encoding="utf-8")
if 'stick.set_script(load("res://virtual_stick.gd"))' not in hud_text:
    raise SystemExit("PRODUCTION GATE FAILED: circular analog movement stick is not wired into the live HUD")
stick_text = (ROOT / "virtual_stick.gd").read_text(encoding="utf-8")
for token in (
    "func _gui_input(",
    "InputEventScreenTouch",
    "InputEventScreenDrag",
    "func _viewport_to_local(viewport_position: Vector2) -> Vector2:",
    "get_global_transform_with_canvas().affine_inverse() * viewport_position",
    "_update_stick(_viewport_to_local(event.position))",
    "get_local_mouse_position()",
    "func _release_stick()",
    "_sync_actions()",
):
    if token not in stick_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: analog movement stick is missing coordinate-safe input behavior {token}")
if "Rect2(Vector2.ZERO, size).has_point(event.position)" in stick_text or "_update_stick(event.position)" in stick_text:
    raise SystemExit("PRODUCTION GATE FAILED: raw viewport touch positions are still used as local joystick coordinates")
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

world_spawn_start = world_text.find("func spawn_player():")
world_spawn_end = world_text.find("func spawn_traffic():", world_spawn_start)
world_spawn_text = world_text[world_spawn_start:world_spawn_end]
if "if real_dhaka_loaded and is_instance_valid(real_dhaka_loader):" not in world_spawn_text or "initial_spawn = _nearest_mapped_respawn_position(initial_spawn)" not in world_spawn_text:
    raise SystemExit("PRODUCTION GATE FAILED: initial player spawn can bypass real-world road placement")

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
for token in (
    'if stage == "shariatpur_review":',
    'feature_counts.get("licensed_facade_photo_panels", 0)',
    "Shariatpur review assembly blocked: zero embedded licensed exterior photo panels.",
    "Shariatpur review assembly blocked: photo panel count has no matching licensed-photo records.",
    'required_photo_fields = ("image_id", "source_page", "author", "license")',
):
    if token not in map_merger_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: Shariatpur assembly accepts zero/anonymous exterior photo panels; missing {token}")
interior_factory_text = (ROOT / "systems" / "interior_factory.gd").read_text(encoding="utf-8")
apk_verifier_text = (ROOT / "tools" / "verify_apk_contents.py").read_text(encoding="utf-8")
if "active_root.rotation.y = atan2(horizontal_exit_direction.x, horizontal_exit_direction.z)" not in interior_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: generated interior entry is not aligned to the mapped exterior doorway")
for token in (
    "func _infer_interior_scale() -> Vector3:",
    "active_root.scale = room_scale",
    'active_seed.get("footprint_local_m", [])',
    'active_seed.get("height_metres", 3.1 * level_count)',
    "var room_dimensions := _infer_room_dimensions()",
    "horizontal_exit_direction * (room_dimensions.y * room_scale.z * 0.5)",
    "resident.scale = Vector3(",
    "clampf(3.0 * room_interaction_scale, 0.9, 3.0)",
):
    if token not in interior_factory_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: footprint/floor-specific interior scaling is missing {token}")
if "roam_points.append(root.to_global(point))" not in (ROOT / "systems" / "interior_resident.gd").read_text(encoding="utf-8"):
    raise SystemExit("PRODUCTION GATE FAILED: interior resident roam points ignore the actual room transform")
if "player.global_position = active_root.to_global(Vector3(0, 0.25, 1.5))" not in interior_factory_text:
    raise SystemExit("PRODUCTION GATE FAILED: player interior spawn is not coupled to the doorway-facing room transform")
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
    'FileAccess.get_file_as_bytes(texture_path)',
    'ImageTexture.create_from_image(photo_image)',
    'photo_image.load_jpg_from_buffer(photo_bytes)',
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

# A Shariatpur APK may not rely on a nonzero summary counter alone. Keep the
# packaged-asset verifier responsible for proving all three approved IDs are
# present in per-tile metadata with exact building identity and valid licensing.
for token in (
    "approved_facade_photo_ids_required",
    "approved_facade_photo_ids_embedded",
    "approved Shariatpur exterior photo coverage is incomplete",
    "tile-specific GLB/remap missing for licensed exterior photo",
    "license_url",
    "Licensed exterior façade panels in packaged manifest:",
):
    if token not in apk_verifier_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: APK does not fully verify licensed exterior photos: {token}")
catalog_text = (ROOT / "tools" / "map_pipeline" / "shariatpur_facade_images.json").read_text(encoding="utf-8")
catalog_data = json.loads(catalog_text)
catalog_images = catalog_data.get("images", [])
bibir_photo = next((item for item in catalog_images if item.get("id") == "bibir_hat_mosque_01"), {})
eligible_exterior_photos = [
    item for item in catalog_images
    if item.get("facade_eligible") is True
    and str(item.get("view_type", "")).lower() == "exterior"
    and str(item.get("visual_qa", "")).lower() == "passed"
    and str(item.get("license", "")) in {"CC BY 4.0", "CC BY-SA 4.0"}
]
if bibir_photo.get("facade_eligible") is not False or bibir_photo.get("interior_reference_eligible") is not True:
    raise SystemExit("PRODUCTION GATE FAILED: interior mosque photo must remain restricted to the exact interior reference use")
manasha_exterior = next((item for item in eligible_exterior_photos if item.get("id") == "manasha_temple_back_view_01"), None)
if manasha_exterior is None:
    raise SystemExit("PRODUCTION GATE FAILED: no visually reviewed, licensed exterior facade photo is enabled for the Shariatpur map")
if manasha_exterior.get("target_location_lat_lon") != [23.2004, 90.3484] or float(manasha_exterior.get("target_match_radius_metres", 0)) != 45.0:
    raise SystemExit("PRODUCTION GATE FAILED: Manasha exterior photograph lacks its bounded geographic target")
required_exterior_photo_ids = {
    "manasha_temple_back_view_01",
    "rudrakar_moth_35",
    "kartikpur_jomidar_bari_123242",
}
available_exterior_photo_ids = {str(item.get("id", "")) for item in eligible_exterior_photos}
if not required_exterior_photo_ids.issubset(available_exterior_photo_ids):
    missing = sorted(required_exterior_photo_ids - available_exterior_photo_ids)
    raise SystemExit(f"PRODUCTION GATE FAILED: reviewed Shariatpur exterior photo catalog is incomplete: {missing}")
for image_id, expected_license, expected_location in (
    ("rudrakar_moth_35", "CC BY 4.0", [23.1830, 90.3459]),
    ("kartikpur_jomidar_bari_123242", "CC BY-SA 4.0", [23.252441, 90.472991]),
):
    item = next(photo for photo in eligible_exterior_photos if photo.get("id") == image_id)
    if item.get("license") != expected_license or item.get("target_location_lat_lon") != expected_location:
        raise SystemExit(f"PRODUCTION GATE FAILED: {image_id} lacks its source/license/geographic-anchor metadata")



# Require the missing Manasha landmark to be represented transparently at its published location,
# and require the licensed exterior photograph to be baked before accepting that tile.
division_builder_text = (ROOT / "tools" / "map_pipeline" / "build_dhaka_division.py").read_text(encoding="utf-8")
for token in (
    "def add_curated_manasha_footprint(",
    'MANASHA_APPROXIMATE_FOOTPRINT_SOURCE = "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED"',
    "clipped = add_curated_manasha_footprint(clipped, boundary_tile)",
    "Curated Manasha landmark exists in this tile but the licensed exterior photo panel was not embedded.",
    "nearest_points(geometry, target)",
    'has_physical_building = str(tags.get("building", "")).strip().lower() not in {"", "no", "false", "0"}',
    'is_manasha_target_tile = args.stage == "shariatpur_review" and tile_polygon.covers(manasha_target_point)',
    "Approved Manasha exterior photo anchor falls outside Shariatpur District clipping boundary",
    "Manasha target tile is missing its licensed exterior photo panel",
):
    if token not in division_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: guarded Manasha photo/footprint integration missing {token}")
if division_builder_text.index("clipped = add_curated_manasha_footprint(clipped, boundary_tile)") > division_builder_text.index("manifest = build_map(clipped, tile_dir, bbox)"):
    raise SystemExit("PRODUCTION GATE FAILED: curated landmark must be included before GLB and GeoJSON baking")

# The Manasha exterior photo must either match source geometry at the named site or
# use the explicitly labeled fallback. A zero-panel landmark tile is never accepted.
division_builder_text = (ROOT / "tools" / "map_pipeline" / "build_dhaka_division.py").read_text(encoding="utf-8")
for token in (
    "def add_curated_manasha_footprint(",
    'MANASHA_APPROXIMATE_FOOTPRINT_SOURCE = "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED"',
    "clipped = add_curated_manasha_footprint(clipped, boundary_tile)",
    "Curated Manasha landmark exists in this tile but the licensed exterior photo panel was not embedded.",
):
    if token not in division_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: guarded Manasha photo/footprint integration missing {token}")
if division_builder_text.index("clipped = add_curated_manasha_footprint(clipped, boundary_tile)") > division_builder_text.index("manifest = build_map(clipped, tile_dir, bbox)"):
    raise SystemExit("PRODUCTION GATE FAILED: curated landmark must enter the feature list before GLB and GeoJSON baking")

# Approved photo sources must become texture meshes at their own target tile, not
# merely appear in the downloaded-image catalog or its diagnostic report.
for token in (
    "def add_curated_heritage_photo_footprints(",
    "def curated_exterior_photo_ids_in_tile(",
    'CURATED_HERITAGE_FOOTPRINT_SOURCE = "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED"',
    "clipped = add_curated_heritage_photo_footprints(clipped, boundary_tile)",
    "missing_curated_photo_ids = sorted(set(curated_photo_target_ids) - embedded_photo_ids)",
    "downloaded images and catalogue eligibility do not count as embedding.",
):
    if token not in division_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: location-bound exterior-photo baking is missing {token}")
curated_photo_catalog = json.loads(
    (ROOT / "tools" / "map_pipeline" / "shariatpur_facade_images.json").read_text(encoding="utf-8")
)
for image_id in ("rudrakar_moth_35", "kartikpur_jomidar_bari_123242"):
    photo = next((item for item in curated_photo_catalog.get("images", []) if item.get("id") == image_id), {})
    if not photo.get("curated_feature_id") or not photo.get("curated_building_tags"):
        raise SystemExit(f"PRODUCTION GATE FAILED: {image_id} has no explicitly identified photo-host fallback")
    dimensions = photo.get("curated_footprint_dimensions_metres", [])
    if not (isinstance(dimensions, list) and len(dimensions) == 2 and all(isinstance(v, (int, float)) and 4 <= v <= 30 for v in dimensions)):
        raise SystemExit(f"PRODUCTION GATE FAILED: {image_id} has no bounded review-only footprint dimensions")
    if "not surveyed" not in str(photo.get("curated_footprint_dimensions_note", "")).lower():
        raise SystemExit(f"PRODUCTION GATE FAILED: {image_id} approximate footprint is not explicitly labeled unsurveyed")

# Keep mapped doors, actual interaction-anchor placement and hero readability
# connected to the generated metric world (without scaling real footprints).
map_builder_text = (ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
for token in (
    'catalog.get("__geo_targets__", [])',
    "def match_facade_photo(",
    "target_tag_groups",
    "geometry.distance(target_point)",
    "match_facade_photo(tags, facade_photo_catalog, polygon, origin_lat, origin_lon)",
    '"match_method": facade_photo.get("match_method", "exact_name_alias")',
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: bounded landmark photo placement is missing {token}")
map_loader_text = (ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
character_text = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
player_text = (ROOT / "player.gd").read_text(encoding="utf-8")
world_text = (ROOT / "world.gd").read_text(encoding="utf-8")
for token in (
    "const MAX_INTERIOR_ANCHORS_PER_TILE := 256",
    "const INTERIOR_ANCHOR_RADIUS_M := 90.0",
    "const INTERIOR_ANCHOR_REFRESH_DISTANCE_M := 12.0",
    "const MAX_BUILDING_COLLISIONS_PER_TILE := 320",
    "const BUILDING_COLLISION_RADIUS_M := 55.0",
    "if distance_sq > BUILDING_COLLISION_RADIUS_M * BUILDING_COLLISION_RADIUS_M:",
):
    if token not in map_loader_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: nearby building interaction/collision streaming is missing {token}")
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
    "def facade_balcony_geometry(",
    '"facade_balcony_units": facade_balconies',
    'node_name=f"facade_balconies_{color_name}"',
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: per-building balcony geometry is missing {token}")
for token in (
    'tags.get("height:source", "")).strip() == "CURATED_APPROXIMATE_NOT_SURVEYED"',
    'return "CURATED_APPROXIMATE_NOT_SURVEYED"',
    '"feature_geometry_source": str(tags.get("source:geometry", "OSM_FOOTPRINT"))',
    '"curated_approximate_landmark_footprints": sum(',
    "def facade_window_geometry(",
    "max_window_panels = min(96, max(12, floor_rows * 16))",
    'tags.get("window", "")',
    "selected_edges = edges[:4]",
    "if not isinstance(part, Polygon) or part.area < 6.0:",
    "if length < 2.2:",
    "window_count = min(8, max(1, int(length / 3.2)))",
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: source-aware multi-window facade geometry is missing {token}")
for token in (
    "def roof_shape_for_building(",
    "def procedural_roof_mesh(",
    '"roof_shape_model": roof_shape_model',
    '"modeled_roofs": modeled_roofs',
    "INFERRED_SMALL_LOW_RISE_HOME_NO_ROOF_SHAPE_TAG",
    "generic_low_rise_home = (",
    "footprint_area_m2 <= 70.0",
    "INFERRED_UNTYPED_SMALL_LOW_RISE_BUILDING_AS_LOCAL_HOME",
    "generic_home_exclusions = (",
):
    if token not in map_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: map bake is missing source-aware house roof geometry: {token}")
if "@export var is_player_character := false" not in character_text or "func _add_clothing_and_face_detail() -> void:" not in character_text:
    raise SystemExit("PRODUCTION GATE FAILED: the hero character detail pass is missing.")
for token in ("LeftEyeWhite", "NoseBridge", "ChestPocket_%s", "ShoeSole", "RadioBody", "WristWatch"):
    if token not in character_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: hero visual detail missing {token}.")
for token in (
    "func _build_authored_combat_gear() -> void:",
    '"AuthoredCombatGear"',
    "gear.scale = Vector3(",
    "1.0 / maxf(absf(scale.x), 0.01)",
    '"GearPlateCarrier"',
    '"GearMagazinePouch_%d" % index',
    '"GearKneePad_%s" % side_label',
    '"GearBackpack"',
    '_build_authored_combat_gear()',
):
    if token not in character_visual_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: the rigged hero lost visible attached equipment detail: {token}")
if "visual.is_player_character = true" not in world_text or "camera_distance := 4.8 if Input.is_action_pressed" not in player_text or "else 7.4" not in player_text:
    raise SystemExit("PRODUCTION GATE FAILED: hero-detail selection or mobile-readable camera distance was lost.")
for token in (
    "func _build_player_weapon() -> void:",
    "PlayerRifleRoot",
    "RifleReceiver",
    "RifleMagazine",
    "RifleBarrel",
    "RifleOpticLens",
    "MuzzleFlash",
    "func play_muzzle_flash() -> void:",
    "mesh.radial_segments = 24",
):
    if token not in character_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: visible combat-hero detail is missing {token}")
if 'hero_visual.call("play_muzzle_flash")' not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: visible muzzle flash is not connected to the live fire action.")
for token in (
    "var _weapon_recoil_offset := 0.0",
    "_weapon_recoil_offset = minf(_weapon_recoil_offset + 0.06, 0.11)",
    "_weapon_recoil_offset = move_toward(_weapon_recoil_offset, 0.0, delta * 0.85)",
):
    if token not in character_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: weapon recoil animation is missing {token}")
if "func _spawn_bullet_impact(point: Vector3, surface_normal: Vector3) -> void:" not in world_text or "_spawn_bullet_impact(hit.position, hit.normal)" not in world_text:
    raise SystemExit("PRODUCTION GATE FAILED: bullet impacts are not connected to live surface ray hits.")

# Offline combat needs line-of-sight ranged enemy fire, a readable wind-up and tracer feedback.
combat_enemy_text = (ROOT / "systems" / "combat_enemy.gd").read_text(encoding="utf-8")
for token in (
    "const MAX_RANGED_ATTACK_DISTANCE := 24.0",
    "const PREFERRED_FIRING_DISTANCE := 11.0",
    "const RANGED_SHOT_WINDUP := 0.42",
    "func _ray_to_player(player: CharacterBody3D) -> Dictionary:",
    "PhysicsRayQueryParameters3D.create(origin, target)",
    "query.exclude = [get_rid()]",
    'sight_hit.get("collider") == player',
    "func _fire_at_player(player: CharacterBody3D) -> void:",
    "func _emit_bullet_tracer(start: Vector3, finish: Vector3) -> void:",
    'tracer.name = "EnemyBulletTracer"',
    'world.event_text = "UNDER FIRE • BREAK LINE OF SIGHT"',
    "world._spawn_bullet_impact(hit.position, hit.normal)",
):
    if token not in combat_enemy_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: tactical offline enemy combat is missing {token}")

# Offline combat must create entities rather than merely display mode names.
combat_controller_text = (ROOT / "systems" / "combat_mode_controller.gd").read_text(encoding="utf-8")
for token in (
    "func _spawn_enemy(at: Vector3, is_practice_target: bool) -> void:",
    'entity.set_script(load("res://systems/combat_enemy.gd") as Script)',
    'entity.add_to_group("combat_enemy")',
    'entity.set("combat_controller", self)',
    "visual.has_combat_weapon = not is_practice_target",
):
    if token not in combat_controller_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: offline combat entity spawning is missing {token}")
for token in (
    "@export var has_combat_weapon := false",
    "if is_player_character or has_combat_weapon:",
    "if has_combat_weapon:",
    "EnemyTacticalVest",
    'var ai_shot_pending: bool = bool(body.get("_shot_pending"))',
):
    if token not in character_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: enemy rifle rig/pose is missing {token}")
if 'visual.call("play_muzzle_flash")' not in (ROOT / "systems" / "combat_enemy.gd").read_text(encoding="utf-8"):
    raise SystemExit("PRODUCTION GATE FAILED: enemy muzzle flash is not attached to shots")

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
combat_controller_text = (ROOT / "systems" / "combat_mode_controller.gd").read_text(encoding="utf-8")
if combat_controller_text.count("func _spawn_enemy(") != 1:
    raise SystemExit("PRODUCTION GATE FAILED: combat modes must use one canonical enemy-spawn function")
if 'target_goal = 6\n        alive_enemies = target_goal' not in combat_controller_text:
    raise SystemExit("PRODUCTION GATE FAILED: Combat Lab target count is not initialized")
if "visual.has_combat_weapon = not is_practice_target" not in combat_controller_text:
    raise SystemExit("PRODUCTION GATE FAILED: armed combat enemies are missing their authored rifle rig")
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

# Overture is a bounded supplemental source, not a fabricated replacement for OSM.
overture_text = (ROOT / "tools" / "map_pipeline" / "overture_buildings.py").read_text(encoding="utf-8")
for token in (
    "def download_overture_buildings(",
    "def load_overture_buildings(",
    "def deduplicate_overture_overlaps(",
    'OVERTURE_SOURCE_DATASET = "Overture Maps buildings theme"',
    "source_datasets",
):
    if token not in overture_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: Overture supplement is missing {token}")
for token in (
    "download_overture_buildings(extract_bounds, args.overture_buildings)",
    "load_overture_buildings(args.overture_buildings, extract_bounds)",
    "deduplicate_overture_overlaps(clipped)",
    "overture_building_footprints_added",
    "OVERTURE_ATTRIBUTION",
):
    if token not in division_builder_text:
        raise SystemExit(f"PRODUCTION GATE FAILED: tile-specific Overture integration is missing {token}")
if 'item["tags"]["source_osm_id"] = str(original["id"])' not in division_builder_text or 'item["tags"]["source_overture_id"]' not in division_builder_text:
    raise SystemExit("PRODUCTION GATE FAILED: Overture IDs are being mislabelled as OSM IDs")
map_workflow = (ROOT / ".github" / "workflows" / "dhaka-3d-map.yml").read_text(encoding="utf-8")
if "pip install osmium shapely trimesh mapbox-earcut pillow overturemaps" not in map_workflow:
    raise SystemExit("PRODUCTION GATE FAILED: map workflow does not install the official Overture client")
if "overture-buildings-" not in map_workflow or "path: build/overture/" not in map_workflow:
    raise SystemExit("PRODUCTION GATE FAILED: Overture per-batch cache is missing")

print("PRODUCTION GATE PASSED")
print(f"Canonical project: {state['canonical_repository']}")
print(f"Retained feature modules: {len(features)}")
print("Canonical Android pipeline: .github/workflows/android.yml")
print("No workflow-count progress is treated as game progress.")
