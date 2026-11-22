import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def function_block(source: str, name: str) -> str:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"func {name}(")), -1)
    if start < 0:
        raise AssertionError(f"Missing function {name}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("func "):
        end += 1
    return "\n".join(lines[start:end])


class ASquareCinematicLobbyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = read("tools/blender/build_asquare_lobby_scene.py")
        cls.verifier = read("tools/blender/verify_asquare_lobby_scene.py")
        cls.showcase = read("systems/lobby_showcase.gd")
        cls.fx = read("systems/lobby_cinematic_fx.gd")
        cls.hud = read("hud.gd")
        cls.login = read("systems/login_backdrop.gd")
        cls.boot = read("boot.gd")
        cls.workflow = read(".github/workflows/validate-cinematic-lobby.yml")

    def test_blender_build_is_an_authored_environment_not_a_baked_game_screen(self):
        for token in (
            "A_SQUARE_CINEMATIC_COMMAND_HALL",
            "Operator dais | satin crown",
            "Panoramic smoked window",
            "BANGLADESH  •  RIVER DELTA OPERATIONS",
            "Ceiling | acoustic rib",
            "Left theatre display",
            "Right theatre display",
            "Distant river-town silhouette",
            "ANIM | Orbit ring",
            "export_animations=True",
            "export_format=\"GLB\"",
        ):
            self.assertIn(token, self.builder)
        self.assertIn("The live player rig remains outside the GLB", self.showcase)
        self.assertIn("all buttons and game state remain ordinary accessible controls", self.fx.lower())

    def test_glb_is_structurally_verified_for_scene_art_and_animation(self):
        for token in (
            "magic != b\"glTF\"",
            "len(meshes) < 55",
            "len(materials) < 8",
            "if not animations:",
            "animation_channels < 1",
            "estimated_triangles",
        ):
            self.assertIn(token, self.verifier)

    def test_live_showcase_prefers_reviewed_blender_scene_and_keeps_safe_fallback(self):
        self.assertIn("AUTHORED_COMMAND_HALL_PATH", self.showcase)
        self.assertIn("ResourceLoader.exists(AUTHORED_COMMAND_HALL_PATH)", self.showcase)
        self.assertIn("authored_pack.instantiate()", self.showcase)
        self.assertIn("func _play_authored_stage_animation()", self.showcase)
        self.assertIn("CylinderMesh.new()", self.showcase)
        self.assertIn("TorusMesh.new()", self.showcase)
        self.assertIn("SpotLight3D.new()", self.showcase)
        self.assertIn("OmniLight3D.new()", self.showcase)

    def test_lobby_has_animated_surface_and_sequenced_page_reveals(self):
        self.assertIn("lobby_cinematic_fx.gd", self.hud)
        self.assertIn("lobby_overlay.move_child(cinematic_fx, 0)", self.hud)
        page = function_block(self.hud, "_show_lobby_page")
        self.assertIn("_lobby_page_tween.set_parallel(true)", page)
        self.assertIn('"modulate:a"', page)
        self.assertIn("Tween.TRANS_BACK", page)
        self.assertIn('button.name = "FeaturedPlayNow"', self.hud)
        self.assertIn('Vector2(0.0, 108.0)', self.hud)
        self.assertIn('FIELD COMMAND', page)

    def test_login_backdrop_has_cinematic_camera_and_live_vehicle_motion(self):
        process = function_block(self.login, "_process")
        self.assertIn("_presentation_camera.position = _camera_origin + camera_drift", process)
        self.assertIn("wheel.rotation.z += delta * 5.2", process)
        self.assertIn("_vehicle_root.position.y = 0.012 + sin", process)
        self.assertIn("environment.fog_enabled = true", self.login)
        self.assertIn("environment.fog_density = 0.004", self.login)

    def test_login_to_real_loading_handoff_is_crossfaded(self):
        transition = function_block(self.boot, "_show_map_install_screen")
        self.assertIn("transition.set_parallel(true)", transition)
        self.assertIn('transition.tween_property(boot_content, "modulate:a", 1.0', transition)
        self.assertIn('transition.tween_property(outgoing_login, "modulate:a", 0.0', transition)
        self.assertIn("await transition.finished", transition)
        # This remains a local guest profile and actual map-pack installer, not fake online login.
        self.assertIn("LOCAL_GUEST", self.boot)
        self.assertIn("_verify_and_install_pack()", self.boot)

    def test_blender_and_godot_validation_are_pinned_and_artifacts_are_reviewable(self):
        for token in (
            "tools/install_blender_ci.sh",
            "build_asquare_lobby_scene.py",
            "verify_asquare_lobby_scene.py",
            "command_hall_preview.png",
            "asquare_command_hall.glb",
            "A-Square-Cinematic-Lobby-Review",
            "Godot_v4.4.1-stable_linux.x86_64.zip",
            "tests/validate_cinematic_sources.gd",
        ):
            self.assertIn(token, self.workflow)
        self.assertTrue((ROOT / "tools" / "blender" / "build_asquare_lobby_scene.py").is_file())
        self.assertTrue((ROOT / "tools" / "blender" / "verify_asquare_lobby_scene.py").is_file())


if __name__ == "__main__":
    unittest.main()
