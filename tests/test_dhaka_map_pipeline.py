import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import trimesh
from shapely.geometry import shape

from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, building_height, local_xy, facade_photo_panel, match_facade_photo


class DhakaMapPipelineTests(unittest.TestCase):
    def test_relation_area_stitches_outer_segments_and_preserves_inner_holes(self):
        from tools.map_pipeline.build_dhaka_map import relation_area_polygons
        from shapely.geometry import Polygon, Point

        def coords(points):
            return [{"lat": lat, "lon": lon} for lat, lon in points]

        outer_a = [(23.80, 90.40), (23.80, 90.42), (23.82, 90.42)]
        outer_b = [(23.82, 90.42), (23.82, 90.40), (23.80, 90.40)]
        inner = [(23.805, 90.405), (23.805, 90.415), (23.815, 90.415),
                 (23.815, 90.405), (23.805, 90.405)]
        relation = {
            "type": "relation",
            "members": [
                {"type": "way", "role": "outer", "geometry": coords(outer_a)},
                {"type": "way", "role": "outer", "geometry": coords(outer_b)},
                {"type": "way", "role": "inner", "geometry": coords(inner)},
            ],
        }
        origin_lat, origin_lon = 23.81, 90.41
        bounds = Polygon([
            local_xy(23.79, 90.39, origin_lat, origin_lon),
            local_xy(23.79, 90.43, origin_lat, origin_lon),
            local_xy(23.83, 90.43, origin_lat, origin_lon),
            local_xy(23.83, 90.39, origin_lat, origin_lon),
        ])
        result = relation_area_polygons(relation, origin_lat, origin_lon, bounds)
        self.assertEqual(len(result), 1)
        self.assertGreater(result[0].area, 0)
        hole_x, hole_y = local_xy(23.81, 90.41, origin_lat, origin_lon)
        self.assertFalse(result[0].contains(Point(hole_x, hole_y)))

    def test_relation_area_skips_unclosed_member_rings(self):
        from tools.map_pipeline.build_dhaka_map import relation_area_polygons
        from shapely.geometry import Polygon

        relation = {"type": "relation", "members": [{
            "type": "way", "role": "outer", "geometry": [
                {"lat": 23.80, "lon": 90.40}, {"lat": 23.80, "lon": 90.42},
            ],
        }]}
        bounds = Polygon([(0, 0), (1000, 0), (1000, 1000), (0, 1000)])
        self.assertEqual(relation_area_polygons(relation, 23.81, 90.41, bounds), [])

    def test_default_tile_matches_existing_central_dhaka_anchor(self):
        self.assertEqual(DEFAULT_BBOX, (23.8043, 90.4065, 23.8163, 90.4185))

    def test_overpass_query_includes_mapped_entrance_nodes(self):
        from tools.map_pipeline.build_dhaka_map import overpass_query
        query = overpass_query(DEFAULT_BBOX)
        self.assertIn('node["entrance"]', query)
        self.assertIn('node["door"]', query)

    def test_overpass_query_requests_multipolygon_landcover_and_water(self):
        from tools.map_pipeline.build_dhaka_map import overpass_query

        query = overpass_query(DEFAULT_BBOX)
        for selector in (
            'relation["natural"]',
            'relation["landuse"]',
            'relation["leisure"]',
            'relation["water"]',
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, query)

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

    def test_midrise_balcony_geometry_is_deterministic_and_source_aware(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_map import facade_balcony_geometry

        footprint = box(10.0, 10.0, 30.0, 30.0)
        tile_bounds = box(0.0, 0.0, 100.0, 100.0)
        tags = {"building": "apartments", "building:levels": "4"}
        balcony_a = facade_balcony_geometry(footprint, 12.4, 102, tags, tile_bounds)
        balcony_b = facade_balcony_geometry(footprint, 12.4, 102, tags, tile_bounds)
        self.assertIsNotNone(balcony_a)
        self.assertIsNotNone(balcony_b)
        self.assertEqual(balcony_a[2], 6)
        self.assertEqual(balcony_a[2], balcony_b[2])
        self.assertTrue((balcony_a[1].vertices == balcony_b[1].vertices).all(),
                        "The same OSM building ID must produce reproducible balcony geometry")
        self.assertGreaterEqual(balcony_a[1].bounds[0][0], tile_bounds.bounds[0] - 0.01)
        self.assertGreaterEqual(balcony_a[1].bounds[0][1], tile_bounds.bounds[1] - 0.01)
        self.assertLessEqual(balcony_a[1].bounds[1][0], tile_bounds.bounds[2] + 0.01)
        self.assertLessEqual(balcony_a[1].bounds[1][1], tile_bounds.bounds[3] + 0.01)
        self.assertIsNone(facade_balcony_geometry(
            footprint, 12.4, 102, {"building": "warehouse", "building:levels": "4"}, tile_bounds
        ), "Industrial warehouses must not get residential balcony details")
        self.assertIsNone(facade_balcony_geometry(
            footprint, 12.4, 102, {"building": "apartments", "building:levels": "4", "balcony": "no"}, tile_bounds
        ), "An explicit balcony=no tag must be respected")

    def test_facade_window_density_uses_wall_length_and_keeps_single_storey_homes_visible(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_map import facade_window_geometry

        footprint = box(10.0, 10.0, 30.0, 30.0)
        tile_bounds = box(0.0, 0.0, 100.0, 100.0)
        single_storey = facade_window_geometry(footprint, 3.0, 101, tile_bounds, {"building": "house"})
        two_floor = facade_window_geometry(footprint, 6.2, 101, tile_bounds, {"building": "apartments"})
        five_floor = facade_window_geometry(footprint, 15.5, 102, tile_bounds, {"building": "apartments"})
        self.assertIsNotNone(single_storey, "Ordinary one-storey homes should not render as blank blocks")
        self.assertGreater(single_storey[3], 0)
        self.assertGreater(two_floor[3], 8, "Long walls should receive multiple windows per floor")
        self.assertGreater(five_floor[3], two_floor[3], "Taller buildings should retain repeated floor rhythms")
        self.assertLessEqual(five_floor[3], 96, "Per-building window geometry must remain bounded for mobile rendering")
        self.assertIsNone(facade_window_geometry(footprint, 6.2, 101, tile_bounds, {"building": "house", "window": "no"}))
        self.assertIsNone(facade_window_geometry(footprint, 6.2, 101, tile_bounds, {"building": "house", "window": "false"}))

    def test_small_homes_get_windows_on_short_walls_too(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_map import facade_window_geometry

        tile_bounds = box(-20.0, -20.0, 50.0, 50.0)
        small_home = box(5.0, 5.0, 8.0, 8.0)
        result = facade_window_geometry(small_home, 3.0, 221, tile_bounds, {"building": "house"})
        self.assertIsNotNone(result, "Small one-room homes should still receive visible windows")
        self.assertGreaterEqual(result[3], 4, "Short walls should receive details on several faces")

    def test_window_panels_distribute_across_four_sides_of_a_small_home(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_map import facade_window_geometry

        tile_bounds = box(-20.0, -20.0, 50.0, 50.0)
        home = box(5.0, 5.0, 15.0, 12.0)
        result = facade_window_geometry(home, 3.0, 223, tile_bounds, {"building": "house"})
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result[3], 8,
                                "One-storey home panels should be distributed across all four exterior walls")

    def test_facade_floor_bands_scale_with_building_floor_count_cue(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_map import facade_window_geometry

        footprint = box(10.0, 10.0, 30.0, 30.0)
        tile_bounds = box(0.0, 0.0, 100.0, 100.0)
        two_floor = facade_window_geometry(footprint, 6.2, 101, tile_bounds)
        five_floor = facade_window_geometry(footprint, 15.5, 102, tile_bounds)
        self.assertIsNotNone(two_floor)
        self.assertIsNotNone(five_floor)
        self.assertGreater(five_floor[3], two_floor[3],
                           "Facade geometry should show more vertical floor bands for taller/tagged buildings")

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
            self.assertIn("facade_balcony_units", manifest["feature_counts"])
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

    def test_pipeline_commit_is_recorded_in_map_manifest(self):
        elements = [{
            "type": "way", "id": 71234,
            "tags": {"building": "yes"},
            "geometry": [
                {"lat": 23.8098, "lon": 90.4123}, {"lat": 23.8098, "lon": 90.4125},
                {"lat": 23.8100, "lon": 90.4125}, {"lat": 23.8100, "lon": 90.4123},
                {"lat": 23.8098, "lon": 90.4123},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"WSB_PIPELINE_COMMIT_SHA": "fixture-commit-123"}):
            manifest = build_map(elements, Path(tmp), DEFAULT_BBOX)
            self.assertEqual(manifest["pipeline_commit_sha"], "fixture-commit-123")
            saved = json.loads((Path(tmp) / "map_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["pipeline_commit_sha"], "fixture-commit-123")

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
            {
                "type": "way", "id": 2105,
                "tags": {"natural": "wood", "name": "Mapped Woodland"},
                "geometry": [
                    {"lat": 23.8060, "lon": 90.4130}, {"lat": 23.8060, "lon": 90.4150},
                    {"lat": 23.8075, "lon": 90.4150}, {"lat": 23.8075, "lon": 90.4130},
                    {"lat": 23.8060, "lon": 90.4130},
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
            self.assertGreater(counts["procedural_vegetation_trees"], 0)
            self.assertGreaterEqual(counts["vegetation_mesh_batches"], 1)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(any(name.startswith("mapped_surface_") for name in scene.geometry))
            self.assertTrue(any(name.startswith("procedural_vegetation_") for name in scene.geometry))
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
            self.assertEqual(manifest["feature_counts"]["licensed_facade_photo_panels"], 0)
            self.assertEqual(manifest["licensed_facade_photo_matches"], [])
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


    def test_facade_alias_matching_normalizes_unicode_and_whitespace_but_stays_exact(self):
        from tools.map_pipeline.build_dhaka_map import normalize_facade_name

        catalog = {
            normalize_facade_name("বিবির হাট মসজিদ"): {"metadata": {"id": "bibir_hat_mosque_01"}},
            normalize_facade_name("Bibir Hat Mosque"): {"metadata": {"id": "bibir_hat_mosque_01"}},
        }
        self.assertIsNotNone(match_facade_photo({"name": "  BIBIR   HAT MOSQUE  "}, catalog))
        self.assertIsNotNone(match_facade_photo({"name:bn": "বিবির  হাট মসজিদ"}, catalog))
        self.assertIsNone(match_facade_photo({"name": "nearby mosque"}, catalog))
        self.assertEqual(normalize_facade_name("A\u200b  B"), "a b")

    def test_shariatpur_catalog_enables_verified_landmark_exteriors_and_keeps_mosque_interior_blocked(self):
        catalog_path = Path(__file__).resolve().parents[1] / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(catalog["images"]), 3)
        by_id = {image["id"]: image for image in catalog["images"]}
        approved = [
            image for image in catalog["images"]
            if image.get("facade_eligible") is True
            and image.get("view_type") == "exterior"
            and image.get("visual_qa") == "passed"
            and image.get("license") in {"CC BY 4.0", "CC BY-SA 4.0"}
        ]
        self.assertGreaterEqual(len(approved), 3)
        bibir = by_id["bibir_hat_mosque_01"]
        self.assertIs(bibir.get("facade_eligible"), False)
        self.assertTrue(bibir.get("interior_reference_eligible"))
        rudrakar = by_id["rudrakar_moth_35"]
        self.assertIs(rudrakar.get("facade_eligible"), True)
        self.assertEqual(rudrakar.get("view_type"), "exterior")
        self.assertEqual(rudrakar.get("visual_qa"), "passed")
        self.assertEqual(rudrakar.get("license"), "CC BY 4.0")
        self.assertEqual(rudrakar.get("target_location_lat_lon"), [23.1830, 90.3459])
        kartikpur = by_id["kartikpur_jomidar_bari_123242"]
        self.assertIs(kartikpur.get("facade_eligible"), True)
        self.assertEqual(kartikpur.get("view_type"), "exterior")
        self.assertEqual(kartikpur.get("visual_qa"), "passed")
        self.assertEqual(kartikpur.get("license"), "CC BY-SA 4.0")
        self.assertEqual(kartikpur.get("target_location_lat_lon"), [23.252441, 90.472991])
        manasha = by_id["manasha_temple_back_view_01"]
        self.assertIs(manasha.get("facade_eligible"), True)
        self.assertEqual(manasha.get("view_type"), "exterior")
        self.assertEqual(manasha.get("visual_qa"), "passed")
        self.assertEqual(manasha.get("license"), "CC BY-SA 4.0")
        self.assertIn("Shuvajit BD", manasha.get("attribution", ""))
        self.assertEqual(manasha.get("target_location_lat_lon"), [23.2004, 90.3484])
        self.assertEqual(manasha.get("target_match_radius_metres"), 45.0)
        self.assertIn("interior photograph", " ".join(catalog.get("limitations", [])).lower())

    def test_each_approved_heritage_exterior_photo_matches_its_own_exact_name_alias(self):
        from tools.map_pipeline.build_dhaka_map import normalize_facade_name
        catalog_path = Path(__file__).resolve().parents[1] / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        images = json.loads(catalog_path.read_text(encoding="utf-8"))["images"]
        for image_id in ("manasha_temple_back_view_01", "rudrakar_moth_35", "kartikpur_jomidar_bari_123242"):
            photo = next(item for item in images if item["id"] == image_id)
            aliases = {normalize_facade_name(alias): {"metadata": photo} for alias in photo["match_names"]}
            match = match_facade_photo({"name": photo["match_names"][0]}, aliases)
            self.assertIsNotNone(match, image_id)
            self.assertEqual(match["metadata"]["id"], image_id)
            self.assertTrue(photo["source_page"].startswith("https://commons.wikimedia.org/wiki/File:"))
            self.assertIn(photo["license"], {"CC BY 4.0", "CC BY-SA 4.0"})
        kartikpur = next(item for item in images if item["id"] == "kartikpur_jomidar_bari_123242")
        self.assertEqual(kartikpur["author"], "Moheen Reeyad")
        self.assertIn("CC BY-SA 4.0", kartikpur["attribution"])


    def test_verified_manasha_exterior_photo_matches_only_its_explicit_name_aliases(self):
        from tools.map_pipeline.build_dhaka_map import normalize_facade_name
        catalog_path = Path(__file__).resolve().parents[1] / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        photo = next(item for item in catalog_data["images"] if item["id"] == "manasha_temple_back_view_01")
        aliases = {normalize_facade_name(alias): {"metadata": photo} for alias in photo["match_names"]}
        self.assertEqual(match_facade_photo({"name:bn": "মনসা মন্দির, শরীয়তপুর"}, aliases)["metadata"]["id"], "manasha_temple_back_view_01")
        self.assertEqual(match_facade_photo({"name": "Manasha Temple"}, aliases)["metadata"]["id"], "manasha_temple_back_view_01")
        self.assertEqual(match_facade_photo({"name": "ধানুকা মনসাবাড়ি"}, aliases)["metadata"]["id"], "manasha_temple_back_view_01")
        self.assertIsNone(match_facade_photo({"name": "nearby temple"}, aliases))


    def test_unverified_or_interior_photos_are_not_loaded_as_facade_textures(self):
        from PIL import Image
        from tools.map_pipeline.build_dhaka_map import load_facade_photo_catalog

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photos = root / "photos"
            photos.mkdir()
            Image.new("RGB", (32, 24), (30, 70, 90)).save(photos / "candidate.jpg")
            catalog_path = root / "catalog.json"
            catalog = {"images": [{
                "id": "interior_photo",
                "file_name": "candidate.jpg",
                "match_names": ["Exact Landmark"],
                "facade_eligible": False,
                "view_type": "interior",
                "visual_qa": "passed",
            }]}
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photos),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                self.assertEqual(load_facade_photo_catalog(), {})
                catalog["images"][0].update({
                    "facade_eligible": True,
                    "view_type": "exterior",
                    "visual_qa": "passed",
                })
                catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
                self.assertIn("exact landmark", load_facade_photo_catalog())


    def test_official_burirhat_name_matches_the_specific_licensed_mosque_photo(self):
        from tools.map_pipeline.build_dhaka_map import normalize_facade_name

        catalog_path = Path(__file__).resolve().parents[1] / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        photo = next(item for item in catalog_data["images"] if item["id"] == "bibir_hat_mosque_01")
        aliases = {
            normalize_facade_name(alias): {"metadata": photo}
            for alias in photo["match_names"]
        }
        mapped_name = "বুড়িরহাট ঐতিহাসিক জামে মসজিদ"
        match = match_facade_photo({"name": mapped_name}, aliases)
        self.assertIsNotNone(match)
        self.assertEqual(match["metadata"]["id"], "bibir_hat_mosque_01")
        self.assertIn("official_shariatpur_district_directory", photo["identity_evidence"])
        # The adjacent Eidgah is not the mosque footprint and must never inherit its photo.
        self.assertIsNone(match_facade_photo({"name": mapped_name + " ঈদগাহ"}, aliases))


    def test_licensed_facade_photo_panel_is_textured_and_exact_name_only(self):
        from PIL import Image
        from shapely.geometry import Polygon

        image = Image.new("RGB", (640, 480), (180, 120, 80))
        polygon = Polygon([(0, 0), (18, 0), (18, 9), (0, 9)])
        panel = facade_photo_panel(polygon, 6.0, image, 77, "fixture_photo")
        self.assertIsNotNone(panel)
        self.assertEqual(len(panel.vertices), 4)
        self.assertEqual(panel.visual.kind, "texture")
        self.assertEqual(panel.visual.uv.shape, (4, 2))

        catalog = {
            "bibir hat mosque": {"metadata": {"id": "bibir_hat_mosque_01"}, "image": image},
        }
        self.assertIsNotNone(match_facade_photo({"name": "Bibir Hat Mosque"}, catalog))
        self.assertIsNone(match_facade_photo({"name": "nearby mosque"}, catalog))
        self.assertIsNone(match_facade_photo({"amenity": "place_of_worship"}, catalog))



    def test_metric_roof_models_follow_tags_and_flag_inferred_rural_home_roofs(self):
        from shapely.geometry import Polygon
        from tools.map_pipeline.build_dhaka_map import (
            building_height, procedural_roof_mesh, roof_shape_for_building,
        )

        gabled_shape, gabled_source = roof_shape_for_building(
            {"building": "house", "roof:shape": "gabled"}, 75.0, 3.2
        )
        self.assertEqual(gabled_shape, "gabled")
        self.assertEqual(gabled_source, "OSM_ROOF_SHAPE_TAG")
        polygon = Polygon([(0, 0), (9, 0), (9, 6), (0, 6)])
        roof = procedural_roof_mesh(polygon, 3.2, gabled_shape, 5101)
        self.assertIsNotNone(roof)
        self.assertFalse(roof.is_watertight)  # The roof shell is an outer skin; walls/ceiling are separate geometry.
        self.assertGreater(float(roof.vertices[:, 2].max()), 3.28)
        self.assertTrue(__import__("numpy").isfinite(roof.vertices).all())
        self.assertEqual(roof.metadata["roof_shape"], "gabled")

        inferred_shape, inferred_source = roof_shape_for_building({"building": "house"}, 90.0, 3.2)
        self.assertEqual(inferred_shape, "gabled")
        self.assertEqual(inferred_source, "INFERRED_SMALL_LOW_RISE_HOME_NO_ROOF_SHAPE_TAG")

        # A large portion of mapped local houses have only building=yes. Infer a
        # pitched roof for the small/low-rise subset so they are not blank cuboids.
        generic_shape, generic_source = roof_shape_for_building(
            {"building": "yes"}, 60.0, 6.2
        )
        self.assertEqual(generic_shape, "gabled")
        self.assertEqual(
            generic_source,
            "INFERRED_UNTYPED_SMALL_LOW_RISE_BUILDING_AS_LOCAL_HOME",
        )
        generic_mesh = procedural_roof_mesh(polygon, 6.2, generic_shape, 5102)
        self.assertIsNotNone(generic_mesh)

        # Do not invent residential roofs for a shop or overwrite explicit vertical data.
        self.assertEqual(
            roof_shape_for_building({"building": "yes", "shop": "convenience"}, 45.0, 3.2),
            ("flat", "FLAT_CAP_DEFAULT_NO_ROOF_SHAPE_SOURCE"),
        )
        self.assertEqual(
            roof_shape_for_building({"building": "yes", "building:levels": "2"}, 60.0, 6.2),
            ("flat", "FLAT_CAP_DEFAULT_NO_ROOF_SHAPE_SOURCE"),
        )
        self.assertEqual(roof_shape_for_building({"building": "apartments", "roof:shape": "flat"}, 180.0, 6.2),
                         ("flat", "OSM_ROOF_SHAPE_TAG"))

    def test_mapped_entrance_node_controls_door_location_and_provenance(self):
        from tools.map_pipeline.build_dhaka_map import build_map

        elements = [
            {
                "type": "way",
                "id": 445567,
                "tags": {"building": "house", "building:levels": "1", "name:bn": "ম্যাপ করা বাড়ি"},
                "geometry": [
                    {"lat": 23.8096, "lon": 90.4118},
                    {"lat": 23.8096, "lon": 90.4121},
                    {"lat": 23.8098, "lon": 90.4121},
                    {"lat": 23.8098, "lon": 90.4118},
                    {"lat": 23.8096, "lon": 90.4118},
                ],
            },
            {
                "type": "node",
                "id": 99001,
                "lat": 23.8096,
                "lon": 90.41195,
                "tags": {"entrance": "main"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            manifest = build_map(elements, out, DEFAULT_BBOX)
            counts = manifest["feature_counts"]
            self.assertEqual(counts["facade_door_panels"], 1)
            self.assertEqual(counts["doors_from_mapped_entrance_nodes"], 1)
            self.assertEqual(counts["inferred_doors"], 0)
            seeds = json.loads((out / "AI_Interior_Seeds.json").read_text(encoding="utf-8"))
            seed = next(item for item in seeds if item["osm_id"] == 445567)
            self.assertEqual(seed["door_placement_source"], "OSM_ENTRANCE_NODE:99001:main")
            self.assertEqual(seed["door_entrance_node_osm_id"], "99001")
            self.assertEqual(len(seed["door_anchor_local_m"]), 2)
            self.assertAlmostEqual(sum(v * v for v in seed["door_outward_xy"]), 1.0, delta=0.001)

    def test_mapped_buildings_export_metric_doors_and_runtime_entry_anchors(self):
        from tools.map_pipeline.build_dhaka_map import build_map

        elements = [{
            "type": "way",
            "id": 445566,
            "tags": {"building": "house", "building:levels": "1", "name:bn": "পরীক্ষামূলক বাড়ি"},
            "geometry": [
                {"lat": 23.8096, "lon": 90.4118},
                {"lat": 23.8096, "lon": 90.4121},
                {"lat": 23.8098, "lon": 90.4121},
                {"lat": 23.8098, "lon": 90.4118},
                {"lat": 23.8096, "lon": 90.4118},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            manifest = build_map(elements, out, DEFAULT_BBOX)
            self.assertEqual(manifest["feature_counts"]["facade_door_panels"], 1)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(any(name.startswith("facade_doors_") for name in scene.geometry))
            seeds = json.loads((out / "AI_Interior_Seeds.json").read_text(encoding="utf-8"))
            seed = next(item for item in seeds if item["osm_id"] == 445566)
            self.assertEqual(seed["door_placement_source"], "PROCEDURAL_LONGEST_EXTERIOR_EDGE_NO_MAPPED_ENTRANCE_NODE")
            self.assertEqual(len(seed["door_anchor_local_m"]), 2)
            self.assertAlmostEqual(sum(v * v for v in seed["door_outward_xy"]), 1.0, delta=0.001)

    def test_interior_reference_catalog_is_separate_from_exterior_facade_catalog(self):
        from PIL import Image
        from tools.map_pipeline.build_dhaka_map import (
            load_facade_photo_catalog, load_interior_reference_catalog, match_named_image,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            Image.new("RGB", (640, 480), (110, 90, 70)).save(photo_dir / "mosque-interior.jpg", format="JPEG")
            catalog_path = root / "catalog.json"
            catalog = {"images": [{
                "id": "burirhat_mosque_interior_01",
                "subject": "Burirhat Historical Jame Mosque interior",
                "match_names": ["বুড়িরহাট ঐতিহাসিক জামে মসজিদ"],
                "file_name": "mosque-interior.jpg",
                "facade_eligible": False,
                "view_type": "unverified",
                "visual_qa": "pending",
                "interior_reference_eligible": True,
                "interior_view_type": "interior",
                "interior_visual_qa": "passed",
                "source_page": "https://commons.wikimedia.org/wiki/File:Bibir_Hat_Mosque_01.jpg",
                "author": "Radman Siddiki",
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY-SA 4.0",
            }]}
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photo_dir),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                self.assertEqual(load_facade_photo_catalog(), {})
                interior_catalog = load_interior_reference_catalog()
                match = match_named_image({"name:bn": "বুড়িরহাট ঐতিহাসিক জামে মসজিদ"}, interior_catalog)
                self.assertIsNotNone(match)
                self.assertTrue(match["metadata"]["interior_reference_eligible"])
                self.assertEqual(match["metadata"]["interior_view_type"], "interior")
                self.assertEqual(match["metadata"]["interior_visual_qa"], "passed")
                self.assertEqual(match["metadata"]["license"], "CC BY-SA 4.0")

    def test_interior_photo_is_baked_as_a_separate_asset_linked_to_its_mapped_building(self):
        from PIL import Image
        import hashlib
        from tools.map_pipeline.build_dhaka_map import build_map

        elements = [{
            "type": "way",
            "id": 1155880717,
            "tags": {
                "building": "mosque",
                "building:levels": "1",
                "name:bn": "বুড়িরহাট ঐতিহাসিক জামে মসজিদ",
            },
            "geometry": [
                {"lat": 23.8092, "lon": 90.4115},
                {"lat": 23.8092, "lon": 90.4120},
                {"lat": 23.8097, "lon": 90.4120},
                {"lat": 23.8097, "lon": 90.4115},
                {"lat": 23.8092, "lon": 90.4115},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            Image.new("RGB", (640, 480), (110, 90, 70)).save(photo_dir / "mosque-interior.jpg", format="JPEG")
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps({"images": [{
                "id": "burirhat_mosque_interior_01",
                "subject": "Burirhat Historical Jame Mosque interior",
                "match_names": ["বুড়িরহাট ঐতিহাসিক জামে মসজিদ"],
                "file_name": "mosque-interior.jpg",
                "facade_eligible": False,
                "view_type": "unverified",
                "visual_qa": "pending",
                "interior_reference_eligible": True,
                "interior_view_type": "interior",
                "interior_visual_qa": "passed",
                "source_page": "https://commons.wikimedia.org/wiki/File:Bibir_Hat_Mosque_01.jpg",
                "author": "Radman Siddiki",
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY-SA 4.0",
            }]}), encoding="utf-8")
            out = root / "map"
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photo_dir),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                manifest = build_map(elements, out, DEFAULT_BBOX)

            relative = Path("landmark_reference_photos/mosque-interior.jpg.photo_bytes")
            baked = out / relative
            self.assertTrue(baked.is_file())
            self.assertEqual(baked.read_bytes(), (photo_dir / "mosque-interior.jpg").read_bytes())
            self.assertEqual(manifest["feature_counts"]["licensed_facade_photo_panels"], 0)
            self.assertEqual(manifest["feature_counts"]["interior_reference_photos"], 1)
            match = manifest["interior_reference_photo_matches"][0]
            self.assertEqual(match["use"], "INTERIOR_REFERENCE_ONLY")
            self.assertEqual(match["license"], "CC BY-SA 4.0")
            self.assertEqual(match["sha256"], hashlib.sha256(baked.read_bytes()).hexdigest())
            seeds = json.loads((out / "AI_Interior_Seeds.json").read_text(encoding="utf-8"))
            seed = next(item for item in seeds if item["osm_id"] == 1155880717)
            self.assertEqual(seed["interior_reference_photo"]["image_id"], "burirhat_mosque_interior_01")
            self.assertEqual(seed["interior_reference_photo"]["asset_relative_path"], relative.as_posix())
            self.assertEqual(seed["interior_reference_photo"]["image_format"], "jpg")
            self.assertEqual(seed["interior_reference_photo"]["use"], "INTERIOR_REFERENCE_ONLY")
            self.assertEqual(manifest["licensed_facade_photo_matches"], [])

    def test_named_landmark_photo_is_embedded_in_glb_with_license_provenance(self):
        from PIL import Image

        south, west, north, east = DEFAULT_BBOX
        elements = [{
            "type": "way",
            "id": 88001,
            "tags": {"building": "mosque", "building:levels": "1", "name": "Bibir Hat Mosque"},
            "geometry": [
                {"lat": 23.8092, "lon": 90.4115},
                {"lat": 23.8092, "lon": 90.4120},
                {"lat": 23.8097, "lon": 90.4120},
                {"lat": 23.8097, "lon": 90.4115},
                {"lat": 23.8092, "lon": 90.4115},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            Image.new("RGB", (640, 480), (180, 120, 80)).save(photo_dir / "bibir.jpg", format="JPEG")
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps({
                "images": [{
                    "id": "bibir_hat_mosque_01",
                    "subject": "Bibir Hat Mosque, Shariatpur",
                    "match_names": ["Bibir Hat Mosque"],
                    "file_name": "bibir.jpg",
                    "facade_eligible": True,
                    "view_type": "exterior",
                    "visual_qa": "passed",
                    "source_page": "https://commons.wikimedia.org/wiki/File:Bibir_Hat_Mosque_01.jpg",
                    "author": "Radman Siddiki",
                    "license": "CC BY-SA 4.0",
                    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                    "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY-SA 4.0",
                }]
            }), encoding="utf-8")
            out = root / "map"
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photo_dir),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                manifest = build_map(elements, out, DEFAULT_BBOX)
            self.assertEqual(manifest["feature_counts"]["licensed_facade_photo_panels"], 1)
            self.assertEqual(manifest["licensed_facade_photo_matches"][0]["license"], "CC BY-SA 4.0")
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            photo_meshes = [mesh for name, mesh in scene.geometry.items() if "licensed_facade_photo" in name]
            self.assertEqual(len(photo_meshes), 1)
            self.assertEqual(photo_meshes[0].visual.kind, "texture")
            attribution = (out / "ATTRIBUTION.txt").read_text(encoding="utf-8")
            self.assertIn("Radman Siddiki", attribution)
            self.assertIn("CC BY-SA 4.0", attribution)



    def test_worship_site_polygon_does_not_suppress_missing_physical_manasha_building(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_division import add_curated_manasha_footprint

        lat, lon = 23.2004, 90.3484
        half = 0.00005
        site_only = {
            "type": "way",
            "id": 88008,
            "tags": {"amenity": "place_of_worship", "religion": "hindu"},
            "geometry": [
                {"lat": lat - half, "lon": lon - half},
                {"lat": lat - half, "lon": lon + half},
                {"lat": lat + half, "lon": lon + half},
                {"lat": lat + half, "lon": lon - half},
                {"lat": lat - half, "lon": lon - half},
            ],
        }
        clip = box(90.30, 23.18, 90.40, 23.24)
        result = add_curated_manasha_footprint([site_only], clip)
        curated = [item for item in result if item.get("id") == -62000085]
        self.assertEqual(
            len(curated), 1,
            "A religious-site polygon without a building outline cannot receive an exterior photo panel",
        )
        self.assertEqual(curated[0]["tags"]["source:geometry"], "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED")

    def test_mapped_physical_temple_footprint_prevents_duplicate_curated_landmark(self):
        from shapely.geometry import box
        from tools.map_pipeline.build_dhaka_division import add_curated_manasha_footprint

        lat, lon = 23.2004, 90.3484
        half = 0.00005
        physical_temple = {
            "type": "way",
            "id": 88009,
            "tags": {"building": "temple", "amenity": "place_of_worship", "religion": "hindu"},
            "geometry": [
                {"lat": lat - half, "lon": lon - half},
                {"lat": lat - half, "lon": lon + half},
                {"lat": lat + half, "lon": lon + half},
                {"lat": lat + half, "lon": lon - half},
                {"lat": lat - half, "lon": lon - half},
            ],
        }
        result = add_curated_manasha_footprint([physical_temple], box(90.30, 23.18, 90.40, 23.24))
        self.assertEqual(len(result), 1, "An existing physical temple footprint must not get duplicated")

    def test_verified_coordinate_photo_embeds_when_temple_footprint_has_no_matching_name(self):
        from PIL import Image

        target_lat, target_lon = 23.2004, 90.3484
        half_size = 0.00006
        bbox = (target_lat - 0.002, target_lon - 0.002, target_lat + 0.002, target_lon + 0.002)
        elements = [{
            "type": "way",
            "id": 88009,
            "tags": {"building": "temple", "amenity": "place_of_worship"},
            "geometry": [
                {"lat": target_lat - half_size, "lon": target_lon - half_size},
                {"lat": target_lat - half_size, "lon": target_lon + half_size},
                {"lat": target_lat + half_size, "lon": target_lon + half_size},
                {"lat": target_lat + half_size, "lon": target_lon - half_size},
                {"lat": target_lat - half_size, "lon": target_lon - half_size},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo_dir = root / "photos"
            photo_dir.mkdir()
            Image.new("RGB", (640, 480), (160, 92, 72)).save(photo_dir / "manasha.jpg", format="JPEG")
            catalog_path = root / "catalog.json"
            catalog_path.write_text(json.dumps({
                "images": [{
                    "id": "manasha_temple_back_view_01",
                    "subject": "Manasha Temple, Shariatpur",
                    "match_names": ["Dhanuka Manasha Bari"],
                    "file_name": "manasha.jpg",
                    "facade_eligible": True,
                    "view_type": "exterior",
                    "visual_qa": "passed",
                    "target_location_lat_lon": [target_lat, target_lon],
                    "target_location_source": "https://ghurifiri.bd/places/dhanuka-manasha-bari-shariatpur",
                    "target_match_radius_metres": 45.0,
                    "target_tag_groups": [
                        {"amenity": "place_of_worship"},
                        {"building": "temple"},
                        {"historic": "temple"},
                    ],
                    "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                    "author": "Shuvajit BD",
                    "license": "CC BY-SA 4.0",
                    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                    "attribution": "Photo: Shuvajit BD / Wikimedia Commons, CC BY-SA 4.0",
                }]
            }), encoding="utf-8")
            out = root / "map"
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photo_dir),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                manifest = build_map(elements, out, bbox)

            self.assertEqual(manifest["feature_counts"]["licensed_facade_photo_panels"], 1)
            self.assertEqual(
                manifest["facade_photo_diagnostics"]["loaded_eligible_image_ids"],
                ["manasha_temple_back_view_01"],
            )
            self.assertEqual(
                manifest["facade_photo_diagnostics"]["embedded_panel_image_ids"],
                ["manasha_temple_back_view_01"],
            )
            self.assertEqual(manifest["facade_photo_diagnostics"]["loaded_but_unmatched_image_ids"], [])
            self.assertEqual(manifest["facade_photo_diagnostics"]["embedded_panel_count"], 1)
            photo_match = manifest["licensed_facade_photo_matches"][0]
            self.assertEqual(photo_match["match_method"], "verified_coordinate_compatible_tagged_landmark")
            self.assertEqual(photo_match["license"], "CC BY-SA 4.0")
            self.assertLessEqual(photo_match["match_distance_m"], 45.0)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            photo_meshes = [mesh for name, mesh in scene.geometry.items() if "licensed_facade_photo" in name]
            self.assertEqual(len(photo_meshes), 1)
            self.assertEqual(photo_meshes[0].visual.kind, "texture")
            attribution = (out / "ATTRIBUTION.txt").read_text(encoding="utf-8")
            self.assertIn("Shuvajit BD", attribution)
            self.assertIn("CC BY-SA 4.0", attribution)

    def test_clipped_tile_edge_house_suppresses_overhanging_pitched_roof(self):
        """Partial houses must not export rotated-roof corners beyond their tile."""
        import math
        from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, local_xy

        south, west, north, east = DEFAULT_BBOX
        origin_lat, origin_lon = (south + north) / 2.0, (west + east) / 2.0
        min_xy = local_xy(south, west, origin_lat, origin_lon)
        max_xy = local_xy(north, east, origin_lat, origin_lon)
        width, depth = max_xy[0] - min_xy[0], max_xy[1] - min_xy[1]

        # A 16 x 10 m house is rotated and straddles the north tile edge by
        # about 1.5 m. Its clipped footprint is valid, but the rotated rectangle
        # can reconstruct the uncropped pitched roof outside the tile.
        center_x, center_y = width / 2.0 - 25.0, depth / 2.0 - 5.0
        half_length, half_width, angle = 8.0, 5.0, 0.20
        c, s = math.cos(angle), math.sin(angle)
        local_corners = []
        for dx, dy in [(-half_length, -half_width), (half_length, -half_width),
                       (half_length, half_width), (-half_length, half_width)]:
            local_corners.append((center_x + dx * c - dy * s, center_y + dx * s + dy * c))

        def geographic(point):
            x, y = point
            lat = origin_lat + math.degrees(y / 6378137.0)
            lon = origin_lon + math.degrees(x / (6378137.0 * math.cos(math.radians(origin_lat))))
            return {"lat": lat, "lon": lon}

        coords = [geographic(point) for point in local_corners]
        coords.append(coords[0])
        elements = [{
            "type": "way", "id": 790021,
            "tags": {"building": "house", "building:levels": "1"},
            "geometry": coords,
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map"
            manifest = build_map(elements, out, DEFAULT_BBOX)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            counts = manifest["feature_counts"]

            self.assertGreater(counts["edge_clipped_roofs_suppressed"], 0)
            self.assertEqual(counts["modeled_roofs"], 0)
            self.assertGreater(counts["building_footprints"], 0)
            self.assertGreaterEqual(float(scene.bounds[0][0]), -width / 2.0 - 0.01)
            self.assertLessEqual(float(scene.bounds[1][0]), width / 2.0 + 0.01)
            self.assertGreaterEqual(float(scene.bounds[0][2]), -depth / 2.0 - 0.01)
            self.assertLessEqual(float(scene.bounds[1][2]), depth / 2.0 + 0.01)

    def test_procedural_vegetation_at_tile_edge_does_not_extend_export_bounds(self):
        """A green polygon touching a tile edge must not place crowns outside the tile."""
        from tools.map_pipeline.build_dhaka_map import DEFAULT_BBOX, build_map, local_xy

        south, west, north, east = DEFAULT_BBOX
        elements = [{
            "type": "way",
            "id": 730021,
            "tags": {"landuse": "forest"},
            "geometry": [
                {"lat": south, "lon": west},
                {"lat": south, "lon": east},
                {"lat": north, "lon": east},
                {"lat": north, "lon": west},
                {"lat": south, "lon": west},
            ],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map"
            manifest = build_map(elements, out, DEFAULT_BBOX)
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            origin_lat, origin_lon = (south + north) / 2.0, (west + east) / 2.0
            min_xy = local_xy(south, west, origin_lat, origin_lon)
            max_xy = local_xy(north, east, origin_lat, origin_lon)
            width = max_xy[0] - min_xy[0]
            depth = max_xy[1] - min_xy[1]

            self.assertGreater(manifest["feature_counts"]["procedural_vegetation_trees"], 0)
            self.assertGreaterEqual(float(scene.bounds[0][0]), -width / 2.0 - 0.01)
            self.assertLessEqual(float(scene.bounds[1][0]), width / 2.0 + 0.01)
            self.assertGreaterEqual(float(scene.bounds[0][2]), -depth / 2.0 - 0.01)
            self.assertLessEqual(float(scene.bounds[1][2]), depth / 2.0 + 0.01)


if __name__ == "__main__":
    unittest.main()
