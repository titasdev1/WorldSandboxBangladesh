from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ShariatpurStreetfrontAuthoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = (ROOT / "tools/build_shariatpur_riverfront_shophouse.py").read_text(encoding="utf-8")
        cls.texture_builder = (ROOT / "tools/make_shariatpur_frontage_textures.py").read_text(encoding="utf-8")
        cls.verifier = (ROOT / "tools/verify_shariatpur_streetfront.py").read_text(encoding="utf-8")
        cls.workflow = (ROOT / ".github/workflows/validate-blender-assets.yml").read_text(encoding="utf-8")

    def test_asset_is_an_original_authored_bangladesh_architecture_archetype(self):
        for marker in (
            "Shariatpur River-Town Shopfront",
            "AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING",
            "Godot 4.4.1",
            "CC0 1.0 Universal",
            "No third-party game assets",
            "no Google Earth/Maps 3D",
        ):
            self.assertIn(marker, self.builder)
        self.assertIn("Blender 5.2.4 LTS", self.builder)

    def test_frontage_contains_designed_architectural_and_local_detail(self):
        for marker in (
            "Roller_Shutter_Rib", "Balcony_Baluster", "Corrugated_Awning_Canopy",
            "Water_Tank_Lid", "AC_Condenser_Fin", "Utility_Meter_Cabinet",
            "Rainwater_Downpipe", "Window_Security_Grill_Vertical",
            "Bengali_Shop_Name", "মা স্টোর", "শরীয়তপুর", "Roof_Parapet_Coping",
            "Shop_Interior_Ceramic_Floor", "Shop_Left_Rack_Shelf", "Shop_Rear_Stock_Carton",
            "Shop_Counter_Stone_Top", "Shop_Beverage_Cooler_Glass", "Shop_Ceiling_Fan_Blade",
            "Side_Window_Security_Grille", "Side_Window_Concrete_Chajja", "Side_Wall_Damp_Stain",
        ):
            self.assertIn(marker, self.builder)
        self.assertIn("window_bay", self.builder)
        self.assertIn("_add_shop_interior(mats,find_bengali_font())", self.builder)
        self.assertIn("AUTHORED_VISUAL_INTERIOR_INCLUDED_NOT_A_SURVEYED_PRIVATE_FLOOR_PLAN", self.builder)
        self.assertIn("Window_Recess_Shadow", self.builder)
        self.assertNotIn("teleport", self.builder.lower())

    def test_original_pbr_textures_are_2k_and_include_maps_for_each_material(self):
        self.assertIn("default=2048", self.texture_builder)
        self.assertIn('format="JPEG",quality=92', self.texture_builder)
        self.assertIn("normal_size=max(512,size//2)", self.texture_builder)
        for material in (
            "weathered_teal_plaster", "local_clay_brick", "galvanized_rust_wear",
            "weathered_cast_concrete", "smoked_shop_glass", "aged_teak_wood", "painted_signboard",
        ):
            self.assertIn(material, self.texture_builder + self.builder)
        for kind in ("base_color", "normal", "roughness"):
            self.assertIn(kind, self.texture_builder)
        self.assertIn("no external image textures", self.texture_builder)
        self.assertIn("2K base colour JPEG quality 92; 1K lossless PNG normal and roughness maps", self.texture_builder)
        self.assertIn("45 MiB budget", self.verifier)

    def test_glb_verifier_requires_embedded_pbr_maps_and_review_preview(self):
        for marker in ("glTF", "bufferView", "material", "embedded", "preview", "Godot 4.4.1",
                       "AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING", "triangle_count_from_glb_accessors"):
            self.assertIn(marker, self.verifier)
        self.assertIn("STRUCTURAL_PASS_VISUAL_APPROVAL_AND_ANDROID_RUNTIME_STILL_REQUIRED", self.verifier)

    def test_blender_524_uses_supported_eevee_render_engine(self):
        self.assertIn('scene.render.engine="CYCLES"', self.builder)
        self.assertIn('scene.cycles.device="CPU"', self.builder)
        self.assertIn("A2_PROGRESS: render CPU PBR preview", self.builder)
        self.assertNotIn("BLENDER_EEVEE_NEXT", self.builder)

    def test_blender_workflow_builds_and_uploads_the_streetfront_asset(self):
        for marker in (
            "build_shariatpur_riverfront_shophouse.py",
            "make_shariatpur_frontage_textures.py",
            "verify_shariatpur_streetfront.py",
            "Shariatpur-Riverfront-Shopfront",
            "streetfront_preview.png",
            "streetfront_verification.json",
        ):
            self.assertIn(marker, self.workflow)
        self.assertIn("Noto Sans Bengali", self.workflow)

    def test_generated_asset_outputs_pass_structural_verification_when_present(self):
        output = pathlib.Path(os.environ.get("A2_STREETFRONT_OUTPUT", ROOT / "build/shariatpur-streetfront"))
        glb = output / "shariatpur_riverfront_shophouse_hero.glb"
        manifest = output / "asset_manifest.json"
        license_file = output / "LICENSE.txt"
        preview = output / "streetfront_preview.png"
        if not all(path.is_file() for path in (glb, manifest, license_file, preview)):
            self.skipTest("Blender output is generated by the GitHub Actions authoring job")
        report = output / "streetfront_verification.json"
        subprocess.run([
            sys.executable, str(ROOT / "tools/verify_shariatpur_streetfront.py"),
            "--glb", str(glb), "--manifest", str(manifest), "--license", str(license_file),
            "--preview", str(preview), "--out", str(report),
        ], check=True)
        checked = json.loads(report.read_text(encoding="utf-8"))
        self.assertIn("STRUCTURAL_PASS", checked["status"])


if __name__ == "__main__":
    unittest.main()
