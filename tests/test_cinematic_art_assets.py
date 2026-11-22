from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.verify_cinematic_art_apk import verify


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class CinematicArtPipelineTests(unittest.TestCase):
    def test_blender_command_hall_batches_static_meshes_and_keeps_animation(self):
        builder = read("tools/blender/build_asquare_lobby_scene.py")
        verifier = read("tools/blender/verify_asquare_lobby_scene.py")
        self.assertIn("BLENDER_EXPECTED = (5, 2, 4)", builder)
        self.assertIn("def merge_static_meshes_by_material(root):", builder)
        self.assertIn("obj.animation_data is not None", builder)
        self.assertIn("export_animations=True", builder)
        self.assertIn("export_lights=False", builder)
        self.assertIn("A2_LOBBY_MOBILE_BATCHING", builder)
        self.assertIn("static_batches < 8", builder)
        self.assertIn("STATIC | ", verifier)
        self.assertIn("KHR_lights_punctual", verifier)
        self.assertIn("ANIM | Orbit ring", verifier)
        self.assertIn("ANIM | Operator halo outer", verifier)

    def test_login_mounts_shariatpur_hero_and_keeps_procedural_fallback(self):
        login = read("systems/login_backdrop.gd")
        self.assertIn("SHARIATPUR_SHOPFRONT_PATH", login)
        self.assertIn("ShariatpurHeroShopfront", login)
        self.assertIn("ResourceLoader.exists(SHARIATPUR_SHOPFRONT_PATH)", login)
        self.assertIn("if shariatpur_shopfront_loaded and index == 4:", login)
        self.assertIn("keeping procedural skyline fallback", login)

    def test_lobby_mounts_blender_stage_and_keeps_godot_fallback(self):
        lobby = read("systems/lobby_showcase.gd")
        self.assertIn("AUTHORED_COMMAND_HALL_PATH", lobby)
        self.assertIn("ResourceLoader.exists(AUTHORED_COMMAND_HALL_PATH)", lobby)
        self.assertIn("authored_pack.instantiate()", lobby)
        self.assertIn("func _play_authored_stage_animation()", lobby)
        self.assertIn("func _build_authored_stage_lighting()", lobby)
        self.assertIn("var floor_material := _surface", lobby)

    def test_android_pipeline_builds_assets_smokes_them_and_checks_apk(self):
        android = read(".github/workflows/android.yml")
        self.assertIn("tools/blender/build_asquare_lobby_scene.py", android)
        self.assertIn("tools/verify_cinematic_art_apk.py", android)
        self.assertIn("tests/cinematic_art_runtime_smoke.gd", android)
        self.assertIn("verify_cinematic_art_apk.py --apk", android)
        self.assertIn("assets/login/shariatpur_riverfront_shophouse_hero.glb", android)
        self.assertIn("assets/lobby/asquare_command_hall.glb", android)

    def test_apk_verifier_accepts_complete_synthetic_godot_import_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = pathlib.Path(tmp) / "test.apk"
            required = [
                "assets/assets/login/shariatpur_riverfront_shophouse_hero.glb",
                "assets/assets/lobby/asquare_command_hall.glb",
            ]
            with zipfile.ZipFile(apk, "w") as archive:
                for source in required:
                    archive.writestr(source, b"g" * 200_000)
                    base = pathlib.Path(source).name
                    imported_name = f"{base}-0123456789abcdef.scn"
                    remap = f'[remap]\npath="res://.godot/imported/{imported_name}"\n'
                    archive.writestr(source + ".import", remap.encode())
                    archive.writestr("assets/.godot/imported/" + imported_name, b"scene")
            report = verify(apk)
            self.assertEqual("CINEMATIC_ART_APK_PASS", report["status"])
            self.assertEqual(2, len(report["assets"]))


if __name__ == "__main__":
    unittest.main()
