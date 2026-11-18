from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BattleRoyaleParachuteAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "tools" / "build_battle_royale_parachute.py").read_text(encoding="utf-8")

    def test_authors_a_full_28_cell_inflated_ram_air_canopy(self):
        self.assertIn("cell_count: int = 28", self.source)
        self.assertIn("airfoil_thickness", self.source)
        self.assertIn("create_canopy_mesh", self.source)
        self.assertIn("create_canopy_structure", self.source)
        self.assertIn("Canopy_28_Inflated_Fabric_Cells", self.source)

    def test_includes_suspension_lines_risers_and_full_harness_assembly(self):
        for marker in ("Suspension_Line_", "Main_Riser_", "Riser_Carabiner_", "Harness_Seat_Pan", "Harness_Back_Protector", "Harness_Central_Buckle"):
            self.assertIn(marker, self.source)

    def test_contains_a_wind_sway_animation_and_no_operator_placeholder_mesh(self):
        self.assertIn("A2_Parachute_Canopy_Wind_Sway", self.source)
        self.assertIn('"player_mesh_included": False', self.source)
        self.assertIn("export_animations=True", self.source)
        deployment = (ROOT / "systems" / "battle_royale_deployment.gd").read_text(encoding="utf-8")
        self.assertIn('find_children("*", "AnimationPlayer", true, false)', deployment)
        self.assertNotIn('find_child("*", "AnimationPlayer", true, false)', deployment)

    def test_generated_asset_is_original_and_cc0(self):
        self.assertIn("CC0 1.0 Universal", self.source)
        self.assertIn("No third-party meshes, logos, national insignia", self.source)
        self.assertIn("A2_RamAir_Parachute_Root", self.source)
        self.assertIn('"model_count": 1', self.source)
        self.assertIn('"license": "CC0-1.0"', self.source)
        self.assertIn('"asset_manifest.json"', self.source)


if __name__ == "__main__":
    unittest.main()
