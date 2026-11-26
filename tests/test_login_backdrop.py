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


class LoginBackdropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boot = read("boot.gd")
        cls.view = read("systems/login_backdrop_view.gd")
        cls.backdrop = read("systems/login_backdrop.gd")
        cls.actor = read("systems/login_operator_actor.gd")

    def test_first_run_login_mounts_live_backdrop_before_shade_and_controls(self):
        login = function_block(self.boot, "_show_guest_login_screen")
        self.assertIn('backdrop.name = "LoginBackdrop"', login)
        self.assertIn('load("res://systems/login_backdrop_view.gd")', login)
        self.assertLess(login.index("login_overlay.add_child(backdrop)"), login.index("login_overlay.add_child(shade)"))
        self.assertLess(login.index("login_overlay.add_child(shade)"), login.index("login_overlay.add_child(panel)"))
        self.assertIn('guest_button.pressed.connect(_continue_as_guest)', login)
        self.assertIn('tagline.text = "A living world. Your story."', login)
        self.assertIn('callsign_input.grab_focus()', login)
        self.assertNotIn("Create a local guest profile to save", login)

    def test_backdrop_uses_a_bounded_realtime_subviewport(self):
        self.assertIn("VIEWPORT_SIZE := Vector2i(960, 540)", self.view)
        self.assertIn("viewport.own_world_3d = true", self.view)
        self.assertIn("viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS", self.view)
        self.assertIn("viewport.gui_disable_input = true", self.view)
        self.assertIn("Control.MOUSE_FILTER_IGNORE", self.view)

    def test_login_and_loading_use_the_original_vector_brand_emblem(self):
        boot = read("boot.gd")
        mark = read("assets/ui/brand/a_square_mark.svg")
        self.assertIn('brand_mark := TextureRect.new()', boot)
        self.assertIn('map_brand := TextureRect.new()', boot)
        self.assertIn('res://assets/ui/brand/a_square_mark.svg', boot)
        self.assertIn('viewBox="0 0 512 512"', mark)
        self.assertIn("linearGradient", mark)
        self.assertIn("river", mark.lower())
    def test_authored_login_scene_mounts_the_existing_player_visual(self):
        view = self.view
        host = read("systems/authored_login_operator_host.gd")
        self.assertIn('load("res://systems/authored_login_operator_host.gd")', view)
        self.assertIn('operator_host.name = "LoginOperatorPresentationHost"', view)
        self.assertIn('actor.name = "LoginOperatorActor"', host)
        self.assertIn('visual.name = "HumanoidVisual"', host)
        self.assertIn('visual.set("is_player_character", true)', host)
        self.assertIn('var real_dhaka_loaded := false', host)
        self.assertIn('LoginOperatorPresentationHost/LoginOperatorActor/HumanoidVisual', read("tests/login_backdrop_runtime_smoke.gd"))

    def test_authored_login_scene_is_preferred_and_its_clips_loop(self):
        self.assertIn('const AUTHORED_SCENE_PATH := "res://external_content/lobby_art/a_square_login_riverside.glb"', self.view)
        self.assertIn("func _load_authored_login_scene(viewport: SubViewport) -> bool:", self.view)
        self.assertIn('camera.current = true', self.view)
        self.assertIn("func _start_scene_animations(root: Node) -> void:", self.view)
        self.assertIn("clip.loop_mode = Animation.LOOP", self.view)
        self.assertIn("LOGIN_ART_SCENE_READY", self.view)
        self.assertIn("LOGIN_ART_SCENE_NOT_INSTALLED", self.view)

    def test_bangladesh_street_set_has_moving_cng_and_swaying_tree_leaves(self):
        self.assertIn('_vehicle_root.name = "MovingCNGAutoRickshaw"', self.backdrop)
        self.assertIn('cng_label.text = "CNG"', self.backdrop)
        process = function_block(self.backdrop, "_process")
        self.assertIn("_vehicle_root.position.x = fposmod", process)
        self.assertIn("branch.rotation.z = sin", process)
        self.assertIn("branch.rotation.x = cos", process)
        self.assertIn("viewport", self.view.lower())

    def test_operator_reuses_the_existing_rigged_character_and_idle_state_machine(self):
        self.assertIn('load("res://character_visual.gd")', self.backdrop)
        self.assertIn('_operator_visual.set("is_player_character", true)', self.backdrop)
        self.assertIn('actor.set_script(load("res://systems/login_operator_actor.gd"))', self.backdrop)
        self.assertIn("var reload_time := 0.0", self.actor)
        self.assertIn("var _is_crouched := false", self.actor)
        self.assertIn("move_and_slide()", self.actor)
        self.assertIn("_wind_cloth_pivot.rotation.z = sin", function_block(self.backdrop, "_process"))

    def test_map_install_screen_remains_separate_from_the_animated_login_scene(self):
        install = function_block(self.boot, "_show_map_install_screen")
        self.assertNotIn("LoginBackdrop", install)
        self.assertIn('entrance.tween_property(boot_content, "modulate:a", 1.0, 0.32)', install)
        self.assertIn("_show_map_install_screen()", function_block(self.boot, "_continue_as_guest"))


if __name__ == "__main__":
    unittest.main()
