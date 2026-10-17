import json
import tempfile
import unittest
from pathlib import Path

from tools.map_pipeline.build_real_world_navigation_index import build_index


class RealWorldNavigationIndexTests(unittest.TestCase):
    def test_preserves_real_names_coordinates_and_floor_evidence_without_fabrication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tile.geojson").write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature", "id": "way/101",
                        "properties": {"osm_id": 101, "tags": {
                            "highway": "primary", "name": "Palong Road", "name:bn": "পালং সড়ক"
                        }},
                        "geometry": {"type": "LineString", "coordinates": [[90.35, 23.22], [90.36, 23.23]]},
                    },
                    {
                        "type": "Feature", "id": "way/202",
                        "properties": {"osm_id": 202, "tags": {
                            "building": "apartments", "building:levels": "5", "height": "16", "image": "https://example.invalid/building.jpg"
                        }},
                        "geometry": {"type": "Polygon", "coordinates": [[[90.35, 23.22], [90.351, 23.22],
                            [90.351, 23.221], [90.35, 23.221], [90.35, 23.22]]]},
                    },
                    {
                        "type": "Feature", "id": "way/303",
                        "properties": {"osm_id": 303, "tags": {"building": "yes"}},
                        "geometry": {"type": "Polygon", "coordinates": [[[90.35, 23.22], [90.351, 23.22],
                            [90.351, 23.221], [90.35, 23.221], [90.35, 23.22]]]},
                    },
                ],
            }), encoding="utf-8")
            report = build_index(root)
        self.assertEqual(report["counts"]["roads"], 1)
        self.assertEqual(report["counts"]["named_roads"], 1)
        self.assertEqual(report["roads"][0]["name"], "Palong Road")
        self.assertEqual(report["roads"][0]["name_bn"], "পালং সড়ক")
        self.assertAlmostEqual(report["roads"][0]["coordinates"]["longitude"], 90.355)
        self.assertEqual(report["counts"]["buildings_with_source_floor_count"], 1)
        known = next(b for b in report["buildings"] if b["osm_id"] == "way/202")
        unknown = next(b for b in report["buildings"] if b["osm_id"] == "way/303")
        self.assertEqual(known["levels"], 5)
        self.assertTrue(known["floor_count_tagged_in_source"])
        self.assertFalse(known["floor_count_independently_verified"])
        self.assertEqual(known["facade_reference"]["image_url"], "https://example.invalid/building.jpg")
        self.assertEqual(known["facade_reference"]["status"], "REFERENCE_REQUIRES_LICENSE_REVIEW")
        self.assertEqual(report["counts"]["buildings_with_any_facade_reference"], 1)
        self.assertEqual(report["counts"]["buildings_with_independently_verified_floor_count"], 0)
        self.assertIsNone(unknown["levels"])
        self.assertFalse(unknown["floor_count_tagged_in_source"])
        self.assertFalse(unknown["floor_count_independently_verified"])
        self.assertEqual(unknown["facade_reference"]["status"], "NO_FACADE_REFERENCE_IN_SOURCE")


if __name__ == "__main__":
    unittest.main()
