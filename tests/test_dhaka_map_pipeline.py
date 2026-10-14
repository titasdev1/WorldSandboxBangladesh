import json
import tempfile
import unittest
from pathlib import Path

import trimesh
from shapely.geometry import shape

from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, building_height, local_xy
from tools.map_pipeline.tile_grid import tile_bounds


class DhakaMapPipelineTests(unittest.TestCase):
    def test_greater_dhaka_tile_grid_covers_region_without_gaps(self):
        region = (23.66, 90.30, 23.90, 90.53)
        tiles = list(tile_bounds(region, 0.02))
        self.assertEqual(len(tiles), 144)
        self.assertEqual(tiles[0], (23.66, 90.3, 23.68, 90.32))
        self.assertEqual(tiles[-1], (23.88, 90.52, 23.9, 90.53))
        self.assertTrue(all(south < north and west < east for south, west, north, east in tiles))
        # Tiles are row-major; adjacent tiles share edges exactly.
        self.assertEqual(tiles[0][1], region[1])
        self.assertEqual(tiles[-1][3], region[3])
        for i in range(1, len(tiles)):
            previous = tiles[i - 1]
            current = tiles[i]
            if abs(previous[0] - current[0]) < 1e-9:
                self.assertAlmostEqual(previous[3], current[1], places=6)
            else:
                self.assertAlmostEqual(previous[2], current[0], places=6)

    def test_default_tile_matches_existing_central_dhaka_anchor(self):
        self.assertEqual(DEFAULT_BBOX, (23.8043, 90.4065, 23.8163, 90.4185))

    def test_unmapped_building_height_is_not_fabricated_as_a_tall_building(self):
        height, inferred = building_height({"building": "yes"}, 999999)
        self.assertEqual(height, 3.2)
        self.assertTrue(inferred)

    def test_tagged_building_levels_are_preserved_as_source_data(self):
        height, inferred = building_height({"building:levels": "5"}, 1001)
        self.assertAlmostEqual(height, 15.5)
        self.assertFalse(inferred)

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
            # GLB must use Y-up: X is east-west, Y is elevation, Z is north-south.
            self.assertGreaterEqual(scene.bounds[0][0], -width / 2 - 1)
            self.assertLessEqual(scene.bounds[1][0], width / 2 + 1)
            self.assertGreaterEqual(scene.bounds[0][2], -depth / 2 - 1)
            self.assertLessEqual(scene.bounds[1][2], depth / 2 + 1)
            self.assertGreater(scene.bounds[1][1], scene.bounds[0][1])
            self.assertLess(scene.bounds[1][1], 260)
            self.assertEqual(manifest["feature_counts"]["building_footprints"], 1)
            self.assertEqual(manifest["feature_counts"]["road_ways"], 1)
            self.assertTrue((out / "Dhaka_OSM_Source.geojson").exists())
            source = json.loads((out / "Dhaka_OSM_Source.geojson").read_text())
            south, west, north, east = DEFAULT_BBOX
            for feature in source["features"]:
                bounds = shape(feature["geometry"]).bounds
                self.assertGreaterEqual(bounds[0], west - 1e-9)
                self.assertGreaterEqual(bounds[1], south - 1e-9)
                self.assertLessEqual(bounds[2], east + 1e-9)
                self.assertLessEqual(bounds[3], north + 1e-9)
            self.assertTrue((out / "ATTRIBUTION.txt").exists())
            seeds = json.loads((out / "AI_Interior_Seeds.json").read_text())
            self.assertTrue(any(item["name"] == "Fixture House" for item in seeds))
            self.assertTrue(any(item["name"] == "Fixture Shop" for item in seeds))
            self.assertIn("OpenStreetMap", (out / "map_manifest.json").read_text())


if __name__ == "__main__":
    unittest.main()
