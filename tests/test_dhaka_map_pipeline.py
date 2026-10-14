import json
import tempfile
import unittest
from pathlib import Path

import trimesh

from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, local_xy


class DhakaMapPipelineTests(unittest.TestCase):
    def test_default_tile_matches_existing_central_dhaka_anchor(self):
        self.assertEqual(DEFAULT_BBOX, (23.8043, 90.4065, 23.8163, 90.4185))

    def test_local_projection_is_stable_and_metric(self):
        x, y = local_xy(23.781, 90.407, 23.780, 90.407)
        self.assertAlmostEqual(x, 0.0, places=3)
        self.assertGreater(y, 100.0)
        self.assertLess(y, 120.0)

    def test_fixture_exports_nonempty_glb_and_provenance(self):
        south, west, north, east = DEFAULT_BBOX
        elements = [
            {
                "type": "way", "id": 1001,
                "tags": {"building": "yes", "building:levels": "3", "name": "Fixture House"},
                "geometry": [
                    {"lat": 23.8098, "lon": 90.4123},
                    {"lat": 23.8098, "lon": 90.4125},
                    {"lat": 23.8100, "lon": 90.4125},
                    {"lat": 23.8100, "lon": 90.4123},
                    {"lat": 23.8098, "lon": 90.4123},
                ],
            },
            {
                "type": "way", "id": 1002,
                "tags": {"highway": "residential", "name": "Fixture Road"},
                "geometry": [
                    {"lat": 23.8097, "lon": 90.4120},
                    {"lat": 23.8101, "lon": 90.4128},
                ],
            },
            {
                "type": "node", "id": 1003, "lat": 23.8099, "lon": 90.4124,
                "tags": {"shop": "convenience", "name": "Fixture Shop"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            manifest = build_map(elements, out, DEFAULT_BBOX)
            glb = (out / "Dhaka_Explorable_Map.glb").read_bytes()
            self.assertEqual(glb[:4], b"glTF")
            self.assertGreater(len(glb), 1000)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            origin_lat, origin_lon = (south + north) / 2, (west + east) / 2
            min_xy = local_xy(south, west, origin_lat, origin_lon)
            max_xy = local_xy(north, east, origin_lat, origin_lon)
            width, depth = max_xy[0] - min_xy[0], max_xy[1] - min_xy[1]
            self.assertGreaterEqual(scene.bounds[0][0], -width / 2 - 1)
            self.assertLessEqual(scene.bounds[1][0], width / 2 + 1)
            self.assertGreaterEqual(scene.bounds[0][1], -depth / 2 - 1)
            self.assertLessEqual(scene.bounds[1][1], depth / 2 + 1)
            self.assertEqual(manifest["feature_counts"]["building_footprints"], 1)
            self.assertEqual(manifest["feature_counts"]["road_ways"], 1)
            self.assertTrue((out / "Dhaka_OSM_Source.geojson").exists())
            self.assertTrue((out / "ATTRIBUTION.txt").exists())
            seeds = json.loads((out / "AI_Interior_Seeds.json").read_text())
            self.assertTrue(any(item["name"] == "Fixture House" for item in seeds))
            self.assertTrue(any(item["name"] == "Fixture Shop" for item in seeds))
            self.assertIn("OpenStreetMap", (out / "map_manifest.json").read_text())


if __name__ == "__main__":
    unittest.main()
