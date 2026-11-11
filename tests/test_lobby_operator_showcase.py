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


class LobbyOperatorShowcaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hud = read("hud.gd")
        cls.showcase = read("systems/lobby_showcase.gd")

    def test_home_has_one_prominent_play_now_entry(self):
        home = function_block(self.hud, "_show_lobby_page")
        featured = function_block(self.hud, "_lobby_add_featured_play")
        self.assertIn('_lobby_add_featured_play()', home)
        self.assertIn('button.name = "FeaturedPlayNow"', featured)
        self.assertIn('button.pressed.connect(_show_lobby_page.bind("play"))', featured)
        self.assertIn('Vector2(0.0, 94.0)', featured)

    def test_primary_play_navigation_is_visually_prominent(self):
        lobby = function_block(self.hud, "_build_lobby_ui")
        self.assertIn('var is_play_navigation := page_id == "play"', lobby)
        self.assertIn('60.0 if is_play_navigation else 48.0', lobby)
        self.assertIn('17 if is_play_navigation else 14', lobby)
        self.assertIn('lobby_nav_buttons[page_id] = button', lobby)

    def test_navigation_selection_tracks_the_current_lobby_page(self):
        page = function_block(self.hud, "_show_lobby_page")
        self.assertIn('nav_button.button_pressed = String(page_id) == page', page)
        self.assertIn('button.toggle_mode = true', self.hud)

    def test_showcase_is_live_godot_geometry_not_a_baked_background(self):
        self.assertIn('CylinderMesh.new()', self.showcase)
        self.assertIn('TorusMesh.new()', self.showcase)
        self.assertIn('SpotLight3D.new()', self.showcase)
        self.assertIn('OmniLight3D.new()', self.showcase)
        self.assertNotIn('load("res://', self.showcase)
        self.assertNotIn('Texture2D', self.showcase)

    def test_showcase_and_player_visual_continue_while_tree_is_paused(self):
        self.assertIn('process_mode = Node.PROCESS_MODE_ALWAYS', self.showcase)
        self.assertIn('func _process(delta: float)', self.showcase)
        self.assertIn('_player.call("_update_camera")', self.showcase)
        self.assertIn('CHARACTER_IDLE_SWAY_RADIANS', self.showcase)

    def test_player_is_stopped_before_lobby_stage_takes_over(self):
        freeze = function_block(self.hud, "_freeze_player_for_lobby")
        self.assertIn('stopped_velocity.x = 0.0', freeze)
        self.assertIn('stopped_velocity.z = 0.0', freeze)
        self.assertIn('_freeze_player_for_lobby()', function_block(self.hud, "_show_mode_lobby"))
        self.assertIn('_freeze_player_for_lobby()', function_block(self.hud, "_check_combat_result"))

    def test_showcase_is_hidden_when_gameplay_resumes_and_restored_for_results(self):
        self.assertIn('lobby_showcase.call("configure", w.player)', self.hud)
        self.assertIn('lobby_showcase.call("set_enabled", true)', function_block(self.hud, "_show_mode_lobby"))
        self.assertIn('lobby_showcase.call("set_enabled", true)', function_block(self.hud, "_check_combat_result"))
        self.assertIn('lobby_showcase.call("set_enabled", false)', function_block(self.hud, "_complete_enter_selected_mode"))
        self.assertIn('lobby_showcase.call("set_enabled", false)', function_block(self.hud, "_replay_combat_round"))


if __name__ == "__main__":
    unittest.main()
