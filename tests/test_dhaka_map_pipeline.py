import json
import tempfile
import unittest
from pathlib import Path

import trimesh
from shapely.geometry import shape

from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, building_height, local_xy


class DhakaMapPipelineTests(unittest.TestCase):
    def test_default_tile_matches_existing_central_dhaka_anchor(self):
        self.assertEqual(DEFAULT_BBOX, (23.8043, 90.4065, 23.8163, 90.4185))

    def test_unmapped_building_height_is_not_fabricated_as_a_tall_building(self):
        height, inferred = building_height({"building": "yes"}, 999999)
        self.assertGreaterEqual(height, 3.0)
        self.assertLessEqual(height, 3.25)
        self.assertTrue(inferred)

    def test_height_provenance_does_not_label_estimates_as_placeholder_surveys(self):
        from tools.map_pipeline.build_dhaka_map import building_height_source, building_floors_source

        self.assertEqual(building_height_source({"building": "yes"}), "AREA_CATEGORY_ESTIMATE_UNVERIFIED")
        self.assertEqual(building_floors_source({"building": "yes"}), "AREA_CATEGORY_ESTIMATE_UNVERIFIED")
        self.assertEqual(building_height_source({"height": "18 m"}), "OSM_HEIGHT_TAG")
        self.assertEqual(building_floors_source({"height": "18 m"}), "DERIVED_FROM_OSM_HEIGHT_TAG")
        self.assertEqual(building_height_source({"building:levels": "5"}), "OSM_BUILDING_LEVELS_TAG")
        self.assertEqual(building_floors_source({"building:levels": "5"}), "OSM_BUILDING_LEVELS_TAG")

    def test_tagged_building_levels_are_preserved_as_source_data(self):
        height, inferred = building_height({"building:levels": "5"}, 1001)
        self.assertAlmostEqual(height, 15.5)
        self.assertFalse(inferred)

    def test_area_and_category_estimate_varies_untagged_building_silhouettes(self):
        small, small_inferred = building_height({"building": "yes"}, 101, 24.0)
        large, large_inferred = building_height({"building": "yes"}, 102, 420.0)
        self.assertTrue(small_inferred)
        self.assertTrue(large_inferred)
        self.assertGreater(large, small)

    def test_explicit_building_height_still_overrides_area_estimate(self):
        height, inferred = building_height({"building": "yes", "height": "18 m"}, 103, 24.0)
        self.assertEqual(height, 18.0)
        self.assertFalse(inferred)

    def test_mapped_facade_and_roof_colours_are_respected(self):
        from tools.map_pipeline.build_dhaka_map import building_color, roof_color
        self.assertEqual(building_color({"building:colour": "#123456"}, 1), (18, 52, 86, 255))
        self.assertEqual(roof_color({"roof:colour": "red"}, 1), (166, 67, 59, 255))

    def test_interior_seed_preserves_bangla_signage_and_image_references(self):
        elements = [{
            "type": "way", "id": 9191,
            "tags": {"building": "retail", "name": "Shop", "name:bn": "দোকান",
                     "image": "https://example.invalid/facade.jpg", "roof:colour": "#aabbcc"},
            "geometry": [
                {"lat": 23.8098, "lon": 90.4123}, {"lat": 23.8098, "lon": 90.4125},
                {"lat": 23.8100, "lon": 90.4125}, {"lat": 23.8100, "lon": 90.4123},
                {"lat": 23.8098, "lon": 90.4123},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_map(elements, Path(tmp), DEFAULT_BBOX)
            seeds = json.loads((Path(tmp) / "AI_Interior_Seeds.json").read_text(encoding="utf-8"))
            self.assertGreater(manifest["feature_counts"]["facade_window_panels"], 0)
            scene = trimesh.load(Path(tmp) / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(any(name.startswith("facade_windows_") for name in scene.geometry))
            self.assertIn("PROCEDURAL_LOW_POLY_WINDOW_PANELS", seeds[0]["facade_status"])
            self.assertEqual(seeds[0]["signage_text"]["name:bn"], "দোকান")
            self.assertEqual(seeds[0]["height_source"], "AREA_CATEGORY_ESTIMATE_UNVERIFIED")
            self.assertEqual(seeds[0]["floors_source"], "AREA_CATEGORY_ESTIMATE_UNVERIFIED")
            self.assertIsInstance(seeds[0]["floors_estimate"], int)
            self.assertEqual(seeds[0]["exterior_reference"]["image_tag"], "https://example.invalid/facade.jpg")
            self.assertFalse(seeds[0]["exterior_reference"]["downloaded_or_embedded"])

    def test_empty_tile_still_exports_ground_geometry_instead_of_a_hole(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            manifest = build_map([], out, DEFAULT_BBOX)
            self.assertTrue((out / "Dhaka_Explorable_Map.glb").is_file())
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(scene.geometry)
            self.assertEqual(manifest["feature_counts"]["building_footprints"], 0)
            self.assertEqual(manifest["feature_counts"]["road_ways"], 0)
            source = json.loads((out / "Dhaka_OSM_Source.geojson").read_text(encoding="utf-8"))
            self.assertEqual(source["features"], [])

    def test_mapped_water_landuse_and_bridges_are_baked_and_exported(self):
        from tools.map_pipeline.build_dhaka_map import waterway_width

        elements = [
            {
                "type": "way", "id": 2101,
                "tags": {"natural": "water", "name": "Mapped Pond"},
                "geometry": [
                    {"lat": 23.8092, "lon": 90.4100}, {"lat": 23.8092, "lon": 90.4110},
                    {"lat": 23.8100, "lon": 90.4110}, {"lat": 23.8100, "lon": 90.4100},
                    {"lat": 23.8092, "lon": 90.4100},
                ],
            },
            {
                "type": "way", "id": 2102,
                "tags": {"waterway": "river", "name": "Mapped River"},
                "geometry": [
                    {"lat": 23.8090, "lon": 90.4120}, {"lat": 23.8100, "lon": 90.4150},
                ],
            },
            {
                "type": "way", "id": 2103,
                "tags": {"landuse": "farmland", "name": "Mapped Field"},
                "geometry": [
                    {"lat": 23.8105, "lon": 90.4100}, {"lat": 23.8105, "lon": 90.4120},
                    {"lat": 23.8115, "lon": 90.4120}, {"lat": 23.8115, "lon": 90.4100},
                    {"lat": 23.8105, "lon": 90.4100},
                ],
            },
            {
                "type": "way", "id": 2104,
                "tags": {"highway": "primary", "bridge": "yes", "width": "8"},
                "geometry": [
                    {"lat": 23.8120, "lon": 90.4070}, {"lat": 23.8120, "lon": 90.4170},
                ],
            },
        ]
        self.assertEqual(waterway_width({"waterway": "river", "width": "35"}), 35.0)
        self.assertEqual(waterway_width({"waterway": "river"}), 180.0)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            manifest = build_map(elements, out, DEFAULT_BBOX)
            counts = manifest["feature_counts"]
            self.assertEqual(counts["water_polygons"], 1)
            self.assertEqual(counts["waterway_segments"], 1)
            self.assertEqual(counts["landuse_areas"], 2)  # farmland + mapped woodland
            self.assertEqual(counts["bridge_ways"], 1)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(any(name.startswith("mapped_surface_") for name in scene.geometry))
            source = json.loads((out / "Dhaka_OSM_Source.geojson").read_text(encoding="utf-8"))
            by_id = {feature["properties"]["osm_id"]: feature["geometry"]["type"] for feature in source["features"]}
            self.assertEqual(by_id[2101], "Polygon")
            self.assertEqual(by_id[2102], "LineString")
            self.assertEqual(by_id[2103], "Polygon")
            self.assertIn("water polygons", manifest["hydrography_note"])

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
            {
                "type": "way", "id": 1004,
                "tags": {"building": "yes"},
                "geometry": [
                    {"lat": 23.8102, "lon": 90.4126},
                    {"lat": 23.8102, "lon": 90.4128},
                    {"lat": 23.8104, "lon": 90.4128},
                    {"lat": 23.8104, "lon": 90.4126},
                    {"lat": 23.8102, "lon": 90.4126},
                ],
            },
            {
                "type": "node", "id": 1005, "lat": 23.8101, "lon": 90.4127,
                "tags": {"natural": "tree"},
            },
            {
                "type": "node", "id": 1006, "lat": 23.8101, "lon": 90.4128,
                "tags": {"power": "pole"},
            },
            {
                "type": "node", "id": 1007, "lat": 23.8101, "lon": 90.4129,
                "tags": {"highway": "street_lamp"},
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
            self.assertEqual(manifest["feature_counts"]["building_footprints"], 2)
            building_batches = [name for name in scene.geometry if name.startswith("mapped_buildings_")]
            roof_batches = [name for name in scene.geometry if name.startswith("mapped_roofs_")]
            self.assertGreaterEqual(len(building_batches), 1)
            self.assertLessEqual(len(building_batches), 4)
            self.assertGreaterEqual(len(roof_batches), 1)
            self.assertLessEqual(len(roof_batches), 4)
            self.assertEqual(manifest["feature_counts"]["building_mesh_batches"], len(building_batches))
            self.assertEqual(manifest["feature_counts"]["roof_mesh_batches"], len(roof_batches))
            self.assertFalse(any(name.startswith("building_") for name in scene.geometry))
            self.assertEqual(manifest["feature_counts"]["road_ways"], 1)
            self.assertEqual(manifest["feature_counts"]["interior_anchors"], 3)
            self.assertEqual(manifest["feature_counts"]["mapped_trees"], 1)
            self.assertEqual(manifest["feature_counts"]["mapped_utility_poles"], 1)
            self.assertEqual(manifest["feature_counts"]["mapped_street_lamps"], 1)
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
            generic = next(item for item in seeds if item.get("anchor_kind") == "generic_building")
            self.assertEqual(generic["category"], "building")
            self.assertEqual(len(generic["footprint_local_m"]), 4)
            self.assertIn("OpenStreetMap", (out / "map_manifest.json").read_text())


if __name__ == "__main__":
    unittest.main()
