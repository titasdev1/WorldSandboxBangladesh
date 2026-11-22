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

    def test_first_run_login_reuses_the_persistent_cinematic_backdrop(self):
        login = function_block(self.boot, "_show_guest_login_screen")
        build = function_block(self.boot, "_build_screen")
        self.assertIn('cinematic_backdrop.name = "BootCinematicBackdrop"', build)
        self.assertIn('load("res://systems/login_backdrop_view.gd")', build)
        self.assertIn('get_node_or_null("BootCinematicBackdrop")', login)
        self.assertNotIn("SubViewportContainer.new()", login)
        self.assertLess(login.index("login_overlay.add_child(background)"), login.index("login_overlay.add_child(center)"))
        self.assertIn('guest_button.pressed.connect(_continue_as_guest)', login)
        self.assertIn('callsign_input.grab_focus()', login)

    def test_backdrop_uses_a_bounded_realtime_subviewport(self):
        self.assertIn("VIEWPORT_SIZE := Vector2i(960, 540)", self.view)
        self.assertIn("viewport.own_world_3d = true", self.view)
        self.assertIn("viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS", self.view)
        self.assertIn("viewport.gui_disable_input = true", self.view)
        self.assertIn("Control.MOUSE_FILTER_IGNORE", self.view)

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

    def test_login_shot_uses_camera_parallax_and_animated_cng_wheels(self):
        process = function_block(self.backdrop, "_process")
        timeline = function_block(self.backdrop, "_build_login_timeline")
        self.assertNotIn("_camera.position = Vector3(sin", process)
        self.assertIn('NodePath("LoginBackdropCamera:position:x")', timeline)
        self.assertIn("wheel.rotation.z -= delta * 15.2", process)
        self.assertIn("_vehicle_wheels.append(wheel)", self.backdrop)
        self.assertIn("BalconyDeck_", self.backdrop)
        self.assertIn("RoofWaterTank", self.backdrop)
        self.assertIn('sign_text.text = "SHARIATPUR  /  01"', self.backdrop)
        self.assertIn("RegionalAccentGreen", self.backdrop)
        self.assertIn("RegionalAccentRed", self.backdrop)

    def test_login_camera_and_breeze_use_cubic_animation_timeline(self):
        timeline = function_block(self.backdrop, "_build_login_timeline")
        self.assertIn('animation.loop_mode = Animation.LOOP_LINEAR', timeline)
        self.assertIn('Animation.INTERPOLATION_CUBIC', self.backdrop)
        self.assertIn('LoginArtDirectionTimeline', self.backdrop)
        self.assertIn('login/StreetReveal', self.backdrop)
        self.assertIn('get_path_to(branch)', timeline)
        self.assertIn('get_path_to(_wind_cloth_pivot)', timeline)

    def test_map_loading_keeps_the_same_live_cinematic_backdrop(self):
        build = function_block(self.boot, "_build_screen")
        self.assertIn('cinematic_backdrop.name = "BootCinematicBackdrop"', build)
        self.assertIn('load("res://systems/login_backdrop_view.gd")', build)
        self.assertIn('backdrop_shade.name = "BootCinematicShade"', build)
        self.assertIn('Color(0.008, 0.026, 0.043, 0.78)', build)
        self.assertLess(build.index("add_child(cinematic_backdrop)"), build.index("add_child(shell)"))

    def test_map_install_screen_remains_separate_from_the_animated_login_scene(self):
        install = function_block(self.boot, "_show_map_install_screen")
        self.assertNotIn("LoginBackdrop", install)
        self.assertIn('entrance.tween_property(boot_content, "modulate:a", 1.0, 0.32)', install)
        self.assertIn("_show_map_install_screen()", function_block(self.boot, "_continue_as_guest"))


    def test_login_street_prefers_authored_shariatpur_frontage_and_keeps_safe_fallback(self):
        self.assertIn('SHARIATPUR_SHOPFRONT_PATH := "res://assets/login/shariatpur_riverfront_shophouse_hero.glb"', self.backdrop)
        loader = function_block(self.backdrop, "_add_shariatpur_shopfront")
        city = function_block(self.backdrop, "_build_city_silhouette")
        self.assertIn("ResourceLoader.exists(SHARIATPUR_SHOPFRONT_PATH)", loader)
        self.assertIn('shopfront.name = "ShariatpurHeroShopfront"', loader)
        self.assertIn("shopfront.scale = Vector3.ONE * 0.42", loader)
        self.assertIn("if shariatpur_shopfront_loaded and index == 4:", city)
        self.assertIn("continue", city)


if __name__ == "__main__":
    unittest.main()
