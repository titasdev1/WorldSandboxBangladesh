import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def function_block(source: str, function_name: str) -> str:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"func {function_name}(")), -1)
    if start < 0:
        raise AssertionError(f"Missing GDScript function: {function_name}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("func "):
        end += 1
    return "\n".join(lines[start:end])


class MobileInteractionFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.player = read("player.gd")
        cls.world = read("world.gd")
        cls.loader = read("real_dhaka_tile_loader.gd")
        cls.hud = read("hud.gd")
        cls.vehicle = read("vehicle.gd")
        cls.interior = read("systems/interior_factory.gd")
        cls.map_view = read("district_map_display.gd")
        cls.pack_verifier = read("tools/verify_map_pack.gd")
        cls.boot = read("boot.gd")

    def test_vehicle_interaction_precedes_building_and_vendor_interactions(self):
        block = function_block(self.player, "interact")
        self.assertLess(block.index("try_vehicle_interaction"), block.index("try_street_vendor"))
        self.assertLess(block.index("try_vehicle_interaction"), block.index("try_open_interior_door"))
        self.assertLess(block.index("try_open_interior_door"), block.index("try_interior_interaction"))
        self.assertIn("func try_vehicle_interaction() -> bool:", self.world)

    def test_mapped_entry_door_must_open_before_interior_entry(self):
        open_door = function_block(self.world, "try_open_interior_door")
        enter = function_block(self.world, "try_interior_interaction")
        self.assertIn('get_node_or_null("DoorHinge")', open_door)
        self.assertIn('set_meta("door_open", true)', open_door)
        self.assertIn('bool(entry.get_meta("door_open", false))', enter)
        self.assertIn('tween_property(hinge, "rotation:y"', open_door)

    def test_streamer_builds_a_visible_door_at_each_interaction_anchor(self):
        self.assertIn("_add_entry_door(anchor, seed)", self.loader)
        door = function_block(self.loader, "_add_entry_door")
        self.assertIn('hinge.name = "DoorHinge"', door)
        self.assertIn("StaticBody3D.new()", door)
        self.assertIn("DoorHandle", door)

    def test_interior_closes_and_relocks_the_same_entry_door(self):
        opening = function_block(self.interior, "open_interior")
        closing = function_block(self.interior, "_close_interior")
        self.assertIn("entry_anchor: Node3D = null", opening)
        self.assertIn("active_entry_anchor = entry_anchor", opening)
        self.assertIn('set_meta("door_open", false)', closing)
        self.assertIn('tween_property(door_hinge, "rotation:y"', closing)

    def test_vehicle_has_separate_first_and_third_person_cameras(self):
        self.assertIn("var vehicle_first_person_camera: Camera3D", self.vehicle)
        self.assertIn("func toggle_vehicle_camera_mode() -> String:", self.vehicle)
        self.assertIn("func _apply_vehicle_camera_mode() -> void:", self.vehicle)
        self.assertIn("vehicle_first_person_camera.make_current()", self.vehicle)
        self.assertIn("vehicle_camera.make_current()", self.vehicle)

    def test_hud_uses_vehicle_mode_switch_and_prioritizes_drive_prompt(self):
        toggle = function_block(self.hud, "_toggle_camera_view")
        prompt = function_block(self.hud, "_update_interaction_prompt")
        self.assertIn("toggle_vehicle_camera_mode", toggle)
        self.assertLess(prompt.index("occupied_vehicle"), prompt.index("nearest_vehicle"))
        self.assertLess(prompt.index("nearest_vehicle"), prompt.index("get_interior_interaction_label"))

    def test_minimap_clips_world_roads_and_navigation_to_map_viewport(self):
        self.assertIn("func _clip_segment_to_rect(", self.map_view)
        self.assertIn("_draw_clipped_line(a, b, map_rect", self.map_view)
        self.assertIn("_draw_clipped_line(panel_a, panel_b, map_rect", self.map_view)

    def test_minimap_tap_expands_to_district_overview_and_tap_again_closes(self):
        ready = function_block(self.map_view, "_ready")
        gui = function_block(self.map_view, "_gui_input")
        relayout = function_block(self.map_view, "relayout")
        expanded = function_block(self.map_view, "set_expanded")
        self.assertIn("Control.MOUSE_FILTER_STOP", ready)
        self.assertIn("InputEventMouseButton", gui)
        self.assertIn("InputEventScreenTouch", gui)
        self.assertIn("_toggle_expanded_from_input()", gui)
        self.assertIn("set_expanded(not expanded)", function_block(self.map_view, "_toggle_expanded_from_input"))
        self.assertIn("get_district_overview_road_routes", self.map_view)
        self.assertIn("get_world_bounds", self.map_view)
        self.assertIn("TAP MAP TO CLOSE", self.map_view)
        self.assertIn("viewport_size.x * 0.90", relayout)
        self.assertIn("viewport_size.y * 0.84", relayout)
        self.assertIn("relayout(get_viewport_rect().size)", expanded)

    def test_touch_jump_is_queued_for_the_next_physics_tick(self):
        touch_button = function_block(self.hud, "add_touch_button")
        queue_handler = function_block(self.hud, "_queue_player_jump")
        self.assertIn('if action_name == "jump"', touch_button)
        self.assertIn("_queue_player_jump", touch_button)
        self.assertIn('w.player.call("queue_jump")', queue_handler)
        self.assertIn("var _jump_requested := false", self.player)
        self.assertIn("func queue_jump() -> void:", self.player)
        self.assertIn('var jump_requested_now := _jump_requested or Input.is_action_just_pressed("jump")', self.player)

    def test_expanded_map_distinguishes_tap_from_pinch_and_applies_zoom(self):
        gui = function_block(self.map_view, "_gui_input")
        pinch = function_block(self.map_view, "_update_pinch_zoom")
        self.assertIn("InputEventScreenDrag", gui)
        self.assertIn("_touch_sequence_used_pinch", gui)
        self.assertIn("_begin_pinch_zoom()", gui)
        self.assertIn("_update_pinch_zoom()", gui)
        self.assertIn("_map_zoom = clampf", pinch)
        self.assertIn("MAP_ZOOM_MIN", self.map_view)
        self.assertIn("MAP_ZOOM_MAX", self.map_view)
        self.assertIn("PINCH TO ZOOM", self.map_view)
        self.assertIn("TAP MAP TO CLOSE", self.map_view)

    def test_district_overview_uses_bounded_route_sampling(self):
        overview = function_block(self.loader, "get_district_overview_road_routes")
        self.assertIn("_navigation_display_routes", overview)
        self.assertIn("safe_limit", overview)
        self.assertIn("stride", overview)
        self.assertIn("sampled.append(routes[index])", overview)

    def test_place_search_supports_close_spelling_candidates(self):
        search = function_block(self.loader, "search_named_place")
        search_pass = function_block(self.loader, "_search_named_place_pass")
        distance = function_block(self.loader, "_named_search_edit_distance")
        self.assertIn("_normalize_named_search", search)
        self.assertIn("_search_named_place_pass(normalized, limit, false)", search)
        self.assertIn("_search_named_place_pass(normalized, limit, true)", search)
        self.assertIn('match_kind = "close-spelling"', search_pass)
        self.assertIn("allowed_distance", search_pass)
        self.assertIn("previous[b.length()]", distance)
        self.assertIn('"alt_name"', search_pass)

    def test_teleport_panel_displays_and_selects_name_suggestions(self):
        self.assertIn("PlaceSearchSuggestions", self.hud)
        self.assertIn("_refresh_named_place_suggestions", self.hud)
        self.assertIn("_select_named_place_suggestion", self.hud)
        self.assertIn("_resolve_teleport_selection", self.hud)
        self.assertIn("lat_lon_to_world", function_block(self.hud, "_navigate_to_named_place"))
        self.assertIn("teleport_status.text = \"Selected \"", self.hud)

    def test_large_map_pack_is_chunked_verified_and_reassembled_before_mount(self):
        self.assertIn('get("schema_version", 0)) != 2', self.boot)
        self.assertIn('downloaded_metadata.get("parts", [])', self.boot)
        self.assertIn("ALLOWED_ASSET_BASE_URL + \".part%03d\"", self.boot)
        self.assertIn("func _verify_and_append_part() -> bool:", self.boot)
        self.assertIn("context.update(chunk)", self.boot)
        self.assertIn("output.store_buffer(chunk)", self.boot)
        self.assertIn("func _verify_and_install_pack() -> bool:", self.boot)
        self.assertIn('context.finish().hex_encode().to_lower() != expected_sha256', self.boot)
        self.assertIn("MERGED_PART_PATH", self.boot)
        self.assertIn('ProjectSettings.load_resource_pack', self.loader)

    def test_pck_verifier_uses_the_actual_manifest_schema(self):
        self.assertIn('manifest.get("tile_batch_count", tiles.size())', self.pack_verifier)
        self.assertIn('manifest.get("tile_count_intersecting_boundary", tiles.size())', self.pack_verifier)
        self.assertNotIn('manifest.get("tile_count_total", -1)', self.pack_verifier)


if __name__ == "__main__":
    unittest.main()
