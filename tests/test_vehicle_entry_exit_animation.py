import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class VehicleEntryExitAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vehicle = read("vehicle.gd")
        cls.player = read("player.gd")
        cls.smoke = read("tests/vehicle_entry_exit_animation_smoke.gd")

    def test_vehicle_entry_plays_the_authored_board_clip_before_hiding_player(self):
        entry = self.vehicle[
            self.vehicle.index("func enter_player("):
            self.vehicle.index("func _complete_enter_player(")
        ]
        self.assertIn('_play_entry_exit_action(p, "board_vehicle")', entry)
        self.assertIn("_queue_vehicle_transition(action_duration", entry)
        self.assertNotIn("p.visible = false", entry)

    def test_vehicle_exit_plays_authored_alight_clip_before_releasing_player(self):
        exit_block = self.vehicle[
            self.vehicle.index("func exit_player("):
            self.vehicle.index("func _complete_exit_player(")
        ]
        self.assertIn('_play_entry_exit_action(p, "alight_vehicle")', exit_block)
        self.assertIn("_queue_vehicle_transition(action_duration", exit_block)
        self.assertIn("p.visible = true", exit_block)
        self.assertIn("body.freeze = true", exit_block)

    def test_transition_guard_prevents_double_entry_and_double_exit(self):
        self.assertIn("var _vehicle_transitioning := false", self.vehicle)
        self.assertIn("if occupied or _vehicle_transitioning", self.vehicle)
        self.assertIn("if not occupied or _vehicle_transitioning", self.vehicle)
        self.assertIn("if _vehicle_transitioning:", self.vehicle)

    def test_action_duration_comes_from_the_imported_clip_not_a_fixed_fake_delay(self):
        self.assertIn('_authored_animation_lookup', self.vehicle)
        self.assertIn('animation_player.get_animation(animation_name)', self.vehicle)
        self.assertIn('clampf(clip.length, 0.35, 2.8)', self.vehicle)

    def test_vehicle_keeps_the_driver_rig_inside_the_car_and_uses_a_looping_steering_pose(self):
        completion = self.vehicle[
            self.vehicle.index("func _complete_enter_player("):
            self.vehicle.index("func toggle_vehicle_camera_mode(")
        ]
        self.assertIn("p.reparent(body,true)", completion)
        self.assertIn('p.set_meta("vehicle_cockpit_active", true)', completion)
        self.assertIn('visual.call("set_vehicle_driver_pose", true, vehicle_type)', completion)
        self.assertIn('p.camera.make_current()', completion)
        self.assertIn("func set_vehicle_driver_pose(", read("character_visual.gd"))
        self.assertIn("clip.loop_mode = Animation.LOOP_LINEAR", read("character_visual.gd"))
        self.assertIn("vehicle_cockpit_yaw_offset", read("player.gd"))

    def test_runtime_smoke_exercises_both_transitions_and_camera_restore(self):
        for marker in ("VEHICLE_ENTRY_EXIT_ANIMATION_PASS", "board_vehicle", "drive_car_loop=true", "alight_vehicle", "first_person", "duplicate board input"):
            self.assertIn(marker, self.smoke)
        self.assertIn('player.call("set_camera_view_mode", "first_person")', self.smoke)
        self.assertIn('vehicle.call("exit_player")', self.smoke)


if __name__ == "__main__":
    unittest.main()
