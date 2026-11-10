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

    def test_jump_has_a_short_buffer_and_coyote_window(self):
        source = (ROOT / "player.gd").read_text(encoding="utf-8")
        self.assertIn("var _jump_buffer_time := 0.0", source)
        self.assertIn("var _coyote_time := 0.0", source)
        self.assertIn("_jump_buffer_time = 0.16", source)
        self.assertIn("_coyote_time = 0.12", source)
        self.assertIn("if _jump_buffer_time > 0.0 and _coyote_time > 0.0", source)
        self.assertIn('set_meta("just_landed", landed_now)', source)


if __name__ == "__main__":
    unittest.main()
