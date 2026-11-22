from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, features

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PalongBazaarEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texture_script = (ROOT / "tools/make_palong_bazaar_textures.py").read_text(encoding="utf-8")
        cls.builder = (ROOT / "tools/blender/build_palong_bazaar_environment.py").read_text(encoding="utf-8")
        cls.verifier = (ROOT / "tools/verify_palong_bazaar_environment.py").read_text(encoding="utf-8")
        cls.workflow = (ROOT / ".github/workflows/validate-blender-assets.yml").read_text(encoding="utf-8")
        cls.hud = (ROOT / "hud.gd").read_text(encoding="utf-8")

    def test_reference_is_a_real_palong_market_corridor_not_a_named_building_survey(self):
        for marker in (
            "Sonali Bank Limited",
            "Palong Bazar–Nirala Road",
            "Kotowal Bari Road",
            "23.2181182",
            "90.3486077",
            "PALONG_BAZAAR_INSPIRED_CORRIDOR_STUDY_NOT_A_SURVEY",
            "No Google Maps/Street View",
            "CC0 1.0 Universal",
        ):
            self.assertIn(marker, self.builder + self.texture_script)
        self.assertIn("3.7", self.builder)
        self.assertIn("12", self.builder)  # Twelve separate, authored frontage records.

    def test_street_slice_contains_varied_frontages_and_grounded_market_props(self):
        for marker in (
            "Attached_Mixed_Use_Concrete_Massing",
            "Window_Recess_Shadow",
            "Window_Security_Grille_Vertical",
            "Balcony_Concrete_Slab",
            "Rooftop_Water_Tank_Body",
            "Corrugated_Tin_Awning_Canopy",
            "Roller_Shutter_Rib",
            "Bank_Entrance_Security_Gate_Bar",
            "Overhead_Telecom_Power_Cable",
            "Open_Roadside_Drain",
            "Broken_Drain_Cover_Slab",
            "Monsoon_Road_Puddle",
            "Market_Wood_Crate_Base",
            "Produce_Cart_Frame",
            "Clothing_Display_Rail",
            "Sweets_Outdoor_Glass_Case",
            "Motorcycle_Tyre",
            "CNG_Tyre_Rubber",
            "CNG_Passenger_Floor",
            "CNG_Windscreen_Glass",
            "CNG_Roof_Canopy",
            "CNG_Side_Mirror",
            "CNG_Round_Headlamp_Lens",
            "make_cng_auto_rickshaw(0.48, 11.9",
            "Compose the view at player eye height",
        ):
            self.assertIn(marker, self.builder)
        self.assertIn('facades = [', self.builder)
        self.assertIn('("sweets", "haru_ghosh_sweets"', self.builder)
        self.assertIn('("fashion", "nakkhatra_fashion"', self.builder)
        self.assertIn('("bank", "sonali_bank"', self.builder)

    def test_bengali_sign_art_requires_raqm_and_original_local_wording(self):
        self.assertIn('ImageFont.Layout.RAQM', self.texture_script)
        self.assertIn("নক্ষত্র ফ্যাশন", self.texture_script)
        self.assertIn("হার্ডওয়্যার", self.texture_script)
        self.assertIn("হারু ঘোষ মিষ্টান্ন ভাণ্ডার", self.texture_script)
        self.assertIn("সোনালী ব্যাংক", self.texture_script)
        self.assertIn("source_images_embedded", self.builder)
        self.assertIn("polyhaven_material_manifest.json", self.builder)
        self.assertIn("Poly Haven CC0 photographic scans", self.builder)
        self.assertIn("google_maps_3d_tiles_copied", self.builder)
        self.assertIn("fetch_polyhaven_pbr_materials.py", self.workflow)
        self.assertIn("Powered by Poly Haven", self.workflow)

    def test_texture_builder_generates_embedded_pbr_maps_and_shaped_signs(self):
        if not features.check("raqm"):
            self.skipTest("Pillow build does not expose RAQM")
        from tools.make_palong_bazaar_textures import build

        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            manifest = build(root, 512)
            self.assertEqual(8, len(manifest["materials"]))
            self.assertEqual(8, len(manifest["signs"]))
            self.assertEqual("RAQM", manifest["font"]["layout_engine"])
            for material in manifest["materials"].values():
                for key in ("base_color", "normal", "roughness"):
                    self.assertTrue(pathlib.Path(material[key]).is_file())
            for sign in manifest["signs"].values():
                path = pathlib.Path(sign["path"])
                self.assertTrue(path.is_file())
                self.assertEqual("RAQM", sign["font_layout_engine"])
                self.assertEqual((1536, 512), Image.open(path).size)
            stored = json.loads((root / "texture_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("CC0-1.0", stored["license"])
            self.assertIn("No Google Maps/Street View",
                          (root / "LICENSE.txt").read_text(encoding="utf-8"))

    def test_blender_scene_is_game_camera_authored_and_batches_static_geometry(self):
        for marker in (
            'scene.render.engine = "CYCLES"',
            'scene.cycles.device = "CPU"',
            "scene.cycles.samples = 64",
            "camera.location = (0.12, -13.5, 1.72)",
            "static_material_batches",
            "batch_static_meshes_by_material",
            'export_format="GLB"',
            "1920",
            "1080",
            "Godot",
        ):
            self.assertIn(marker, self.builder)
        self.assertIn("export_lights=False", self.builder)
        self.assertIn("export_cameras=False", self.builder)

    def test_lobby_visibly_credits_polyhaven_environment_scans(self):
        self.assertIn("WorldMaterialAttribution", self.hud)
        self.assertIn("POWERED BY POLY HAVEN (CC0)", self.hud)

    def test_verifier_rejects_flat_or_unembedded_visual_asset(self):
        for marker in (
            "STRUCTURAL_PASS_VISUAL_APPROVAL_GODOT_ANDROID_AND_MAP_SNAP_REQUIRED",
            "embedded_image_count",
            "triangle_count_from_glb_accessors",
            "preview_mean_channel_stddev",
            "at least ten individually art-directed market frontages",
            "source_images_embedded",
            "google_maps_3d_tiles_copied",
            "Poly Haven provider/CC0 provenance",
            "photo-scanned PBR sets",
            "Powered by Poly Haven",
            "130 MiB",
        ):
            self.assertIn(marker, self.verifier)

    def test_blender_workflow_builds_and_uploads_palong_bazaar_review_package(self):
        for marker in (
            "make_palong_bazaar_textures.py",
            "build_palong_bazaar_environment.py",
            "verify_palong_bazaar_environment.py",
            "Palong-Bazaar-Market-Corridor-Study",
            "palong_bazaar_preview.png",
            "palong_bazaar_environment.blend",
            "palong_bazaar_market_corridor.glb",
        ):
            self.assertIn(marker, self.workflow)

    def test_generated_outputs_pass_verification_when_present(self):
        output = pathlib.Path(os.environ.get("A2_PALONG_BAZAAR_OUTPUT", ROOT / "build/palong-bazaar"))
        glb = output / "palong_bazaar_market_corridor.glb"
        manifest = output / "asset_manifest.json"
        license_file = output / "LICENSE.txt"
        preview = output / "palong_bazaar_preview.png"
        if not all(path.is_file() for path in (glb, manifest, license_file, preview)):
            self.skipTest("Blender output is generated by the GitHub Actions authoring job")
        report = output / "verification.json"
        subprocess.run([
            sys.executable, str(ROOT / "tools/verify_palong_bazaar_environment.py"),
            "--glb", str(glb), "--manifest", str(manifest), "--license", str(license_file),
            "--preview", str(preview), "--out", str(report),
        ], check=True)
        checked = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(
            "STRUCTURAL_PASS_VISUAL_APPROVAL_GODOT_ANDROID_AND_MAP_SNAP_REQUIRED",
            checked["status"],
        )


if __name__ == "__main__":
    unittest.main()
