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
        self.assertLess(prompt.index("nearby_vehicle"), prompt.index("get_interior_interaction_label"))

    def test_minimap_clips_world_roads_and_navigation_to_map_viewport(self):
        self.assertIn("func _clip_segment_to_rect(", self.map_view)
        self.assertIn("_draw_clipped_line(a, b, map_rect", self.map_view)
        self.assertIn("_draw_clipped_line(panel_a, panel_b, map_rect", self.map_view)

    def test_pck_verifier_uses_the_actual_manifest_schema(self):
        self.assertIn('manifest.get("tile_batch_count", tiles.size())', self.pack_verifier)
        self.assertIn('manifest.get("tile_count_intersecting_boundary", tiles.size())', self.pack_verifier)
        self.assertNotIn('manifest.get("tile_count_total", -1)', self.pack_verifier)


if __name__ == "__main__":
    unittest.main()
