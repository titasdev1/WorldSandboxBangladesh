import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GreenwakeChapterOneMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_data = json.loads((ROOT / "assets/world/greenwake/chapter_01_map.json").read_text(encoding="utf-8"))
        cls.builder = (ROOT / "tools/blender/build_greenwake_chapter_01.py").read_text(encoding="utf-8")
        cls.verifier = (ROOT / "tools/blender/verify_greenwake_chapter_01.py").read_text(encoding="utf-8")
        cls.production_doc = (ROOT / "docs/quality/GREENWAKE_CHAPTER_01_VERTICAL_SLICE.md").read_text(encoding="utf-8")

    def test_greenwake_is_a_distinct_fictional_bangladesh_rooted_family(self):
        data = self.map_data
        self.assertEqual(data["family"], "GREENWAKE")
        self.assertEqual(data["world_type"], "original_fictional_composite")
        self.assertFalse(data["factuality"]["surveyed_location"])
        self.assertFalse(data["factuality"]["real_historic_site"])
        self.assertIsNone(data["factuality"]["geospatial_coordinates"])
        self.assertFalse(data["factuality"]["historic_claims"])

    def test_vertical_slice_has_a_coherent_arrival_to_chapter_exit_route(self):
        sequence = self.map_data["story_sequence"]
        self.assertEqual([item["step"] for item in sequence], list(range(1, 10)))
        self.assertEqual(sequence[0]["kind"], "arrival")
        self.assertEqual(sequence[-1]["kind"], "consequence")
        landmark_ids = {item["id"] for item in self.map_data["landmarks"]}
        for item in sequence:
            self.assertIn(item["landmark_id"], landmark_ids)
        self.assertIn("old_customs_house", landmark_ids)
        self.assertIn("tidal_sluice", landmark_ids)
        self.assertIn("ridge_archive", landmark_ids)

    def test_environmental_puzzle_requires_multiple_clues_and_has_failure_feedback(self):
        puzzle = self.map_data["puzzles"][0]
        self.assertEqual(puzzle["id"], "three_tide_marks")
        self.assertGreaterEqual(len(puzzle["dependencies"]), 2)
        self.assertIn("markers align", puzzle["logic"])
        self.assertTrue(puzzle["fail_state"])
        self.assertTrue(puzzle["accessibility"])

    def test_build_pipeline_authors_original_terrain_architecture_water_and_traversal(self):
        for marker in (
            "def build_terrain", "def build_customs_house", "def build_jetty",
            "def build_rope_bridge", "def build_sluice", "def build_archive_vault",
            "def build_vegetation", "BLENDER_EXPECTED = (5, 2, 4)",
            "export_animations=True", "GREENWAKE_CH01_READY"
        ):
            self.assertIn(marker, self.builder)
        for required_node in (
            "GW_Tidal_Floodplain_and_Ridge_Terrain",
            "GW_River_Rupjhora_Monsoon_Channel",
            "GW_CustomsHouse_MainVolume",
            "GW_Sluice_GateLeaf",
            "GW_Archive_LedgerPedestal"
        ):
            self.assertIn(required_node, self.builder)

    def test_verifier_fails_closed_on_fictional_identity_and_non_playable_status(self):
        for marker in (
            'manifest.get("fictional_composite") is not True',
            'manifest.get("surveyed_location") is not False',
            'manifest.get("historic_claim") is not False',
            'manifest.get("gameplay_state") != "NOT_YET_INTEGRATED_OR_PLAYABLE"',
            "external_image_references",
            "GREENWAKE_CH01_VERIFICATION: PASS"
        ):
            self.assertIn(marker, self.verifier)

    def test_production_plan_does_not_claim_a_playable_chapter(self):
        self.assertIn("not yet playable", self.production_doc.lower())
        self.assertIn("Godot 4.4.1", self.production_doc)
        self.assertIn("Android", self.production_doc)
        self.assertIn("no AI-generated game art", self.production_doc.lower())


if __name__ == "__main__":
    unittest.main()
