import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RealWorldReferencePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = (ROOT / "REAL_WORLD_REFERENCE_POLICY.md").read_text(encoding="utf-8")
        cls.map_pipeline = (ROOT / "MAP_PIPELINE.md").read_text(encoding="utf-8")

    def test_google_imagery_cannot_feed_offline_reconstruction_assets(self):
        for term in ("image analysis", "machine interpretation", "3D models", "terrain", "offline"):
            self.assertIn(term.lower(), self.policy.lower())
        self.assertIn("not the source for our offline mesh package", self.policy)

    def test_live_provider_visualisation_is_separate_from_redistributable_world(self):
        self.assertIn("Optional live photorealistic map visualisation", self.policy)
        self.assertIn("not the source for our offline mesh package", self.policy)
        self.assertIn("attribution", self.policy.lower())

    def test_incomplete_street_level_coverage_is_reported_as_a_gap(self):
        self.assertIn("one OSM-matched track", self.policy)
        self.assertIn("zero qualifying 360-degree photos", self.policy)
        self.assertIn("do not invent", self.policy.lower())

    def test_building_evidence_and_interior_linkage_are_required(self):
        for term in ("verified floors", "actual entry side", "threshold", "collision", "exit position", "MISSING_EVIDENCE"):
            self.assertIn(term.lower(), self.policy.lower())

    def test_pipeline_document_links_to_the_policy(self):
        self.assertIn("REAL_WORLD_REFERENCE_POLICY.md", self.map_pipeline)


if __name__ == "__main__":
    unittest.main()
