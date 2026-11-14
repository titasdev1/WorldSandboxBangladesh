import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CharacterMovementAnimationTests(unittest.TestCase):
    def test_jump_and_land_clips_are_selected_by_vertical_motion(self):
        source = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
        start = source.index("func _update_authored_animation(")
        end = source.index("\nfunc _material(", start)
        block = source[start:end]
        self.assertIn('body.velocity.y > 0.65', block)
        self.assertIn('state = "jump"', block)
        self.assertIn('state = "fall"', block)
        self.assertIn('state = "land"', block)
        self.assertIn('body.get_meta("just_landed", false)', block)

    def test_featured_operator_uses_modular_human_and_rig_following_gear(self):
        source = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
        self.assertIn("CHARACTER_CREATOR_HERO_PATH", source)
        self.assertIn("_attach_charactercreator_layers", source)
        self.assertIn("_sync_charactercreator_layer_skeletons", source)
        self.assertIn("set_bone_pose(", source)
        self.assertIn("BoneAttachment3D.new()", source)
        self.assertIn("CHARACTER_CREATOR_HERO_READY", source)
        self.assertIn("CHARACTER_CREATOR_COMBAT_GEAR_READY", source)

    def test_authored_operator_load_is_not_blocked_forever_by_map_navigation(self):
        source = (ROOT / "character_visual.gd").read_text(encoding="utf-8")
        start = source.index("func _begin_staged_authored_hero_load()")
        end = source.index("\nfunc _poll_authored_hero_load()", start)
        block = source[start:end]
        self.assertIn("MAX_AUTHORED_HERO_MAP_WAIT_MS := 15000", source)
        self.assertIn("Time.get_ticks_msec() - wait_started_ms < MAX_AUTHORED_HERO_MAP_WAIT_MS", block)
        self.assertIn("AUTHORED_HERO_STAGING_LIMIT", block)
        self.assertIn('ResourceLoader.load_threaded_request(_selected_authored_hero_path, "PackedScene")', block)
        self.assertNotIn("while is_inside_tree():", block)

    def test_jump_has_a_short_buffer_and_coyote_window(self):
        source = (ROOT / "player.gd").read_text(encoding="utf-8")
        self.assertIn("var _jump_buffer_time := 0.0", source)
        self.assertIn("var _coyote_time := 0.0", source)
        self.assertIn("JUMP_BUFFER_SECONDS := 0.16", source)
        self.assertIn("_jump_buffer_time = JUMP_BUFFER_SECONDS", source)
        self.assertIn("_coyote_time = 0.12", source)
        self.assertIn("if _jump_buffer_time > 0.0 and _coyote_time > 0.0", source)
        self.assertIn('set_meta("just_landed", landed_now)', source)


if __name__ == "__main__":
    unittest.main()
