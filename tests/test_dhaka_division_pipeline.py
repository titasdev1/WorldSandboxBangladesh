import tempfile
import unittest
from pathlib import Path

from shapely.geometry import Polygon, box, shape
from tools.map_pipeline.build_dhaka_division import (
    _clip_elements, _source_geometry, _replace_ground_with_boundary,
    order_tiles_shariatpur_first, select_tile_batch, SHARIATPUR_PRIORITY_LAT_LON, has_feature,
)
from tools.map_pipeline.build_dhaka_map import build_map


class DhakaDivisionPipelineTests(unittest.TestCase):
    def test_osm_extract_includes_trees_power_grid_and_street_lamps(self):
        self.assertTrue(has_feature({"natural": "tree"}))
        self.assertTrue(has_feature({"power": "pole"}))
        self.assertTrue(has_feature({"power": "tower"}))
        self.assertTrue(has_feature({"highway": "street_lamp"}))
        self.assertTrue(has_feature({"man_made": "utility_pole"}))

    def test_shariatpur_is_first_but_all_division_tiles_remain_in_order(self):
        tiles = [
            (23.80, 90.40, 23.85, 90.45),  # central Dhaka
            (23.20, 90.325, 23.25, 90.375),  # Shariatpur town
            (24.00, 90.50, 24.05, 90.55),  # farther division tile
        ]
        shariatpur_boundary = box(90.30, 23.20, 90.38, 23.27)
        ordered = order_tiles_shariatpur_first(tiles, shariatpur_boundary)
        self.assertEqual(ordered[0], tiles[1])
        self.assertEqual(set(ordered), set(tiles))
        self.assertEqual(len(select_tile_batch(ordered, 0, 2)), 2)
        self.assertEqual(select_tile_batch(ordered, 2, 2), [tiles[2]])
        self.assertEqual(SHARIATPUR_PRIORITY_LAT_LON, (23.2167, 90.3500))

    def test_tile_batches_reject_invalid_limits(self):
        with self.assertRaises(ValueError):
            select_tile_batch([], -1, 2)
        with self.assertRaises(ValueError):
            select_tile_batch([], 0, 0)

    def test_boundary_clip_removes_outside_nodes_and_clips_crossing_road(self):
        boundary = box(90.0, 23.0, 90.1, 23.1)
        elements = [
            {"type": "node", "id": 1, "lat": 23.05, "lon": 90.05, "tags": {"shop": "convenience"}},
            {"type": "node", "id": 2, "lat": 23.2, "lon": 90.2, "tags": {"shop": "convenience"}},
            {"type": "way", "id": 3, "tags": {"highway": "residential"},
             "geometry": [{"lat": 23.05, "lon": 89.9}, {"lat": 23.05, "lon": 90.2}]},
        ]
        clipped = _clip_elements(elements, boundary)
        self.assertEqual(sum(e["type"] == "node" for e in clipped), 1)
        roads = [e for e in clipped if e["type"] == "way"]
        self.assertEqual(len(roads), 1)
        geom = _source_geometry(roads[0])
        self.assertGreaterEqual(geom.bounds[0], 90.0 - 1e-9)
        self.assertLessEqual(geom.bounds[2], 90.1 + 1e-9)

    def test_boundary_clip_keeps_building_inside_division_polygon(self):
        boundary = box(90.0, 23.0, 90.1, 23.1)
        elements = [{
            "type": "way", "id": 11,
            "tags": {"building": "yes", "building:levels": "2"},
            "geometry": [
                {"lat": 23.04, "lon": 89.98},
                {"lat": 23.04, "lon": 90.03},
                {"lat": 23.08, "lon": 90.03},
                {"lat": 23.08, "lon": 89.98},
                {"lat": 23.04, "lon": 89.98},
            ],
        }]
        clipped = _clip_elements(elements, boundary)
        self.assertEqual(len(clipped), 1)
        geom = _source_geometry(clipped[0])
        self.assertTrue(boundary.covers(geom))
        self.assertAlmostEqual(geom.area, 0.0012, places=6)

    def test_boundary_ground_mesh_is_written_as_valid_glb(self):
        bbox = (23.0, 90.0, 23.1, 90.1)
        boundary = Polygon([
            (90.01, 23.01), (90.09, 23.01), (90.09, 23.09),
            (90.01, 23.09), (90.01, 23.01)
        ])
        elements = [{
            "type": "way", "id": 12,
            "tags": {"building": "yes", "building:levels": "2"},
            "geometry": [
                {"lat": 23.02, "lon": 90.02},
                {"lat": 23.02, "lon": 90.04},
                {"lat": 23.04, "lon": 90.04},
                {"lat": 23.04, "lon": 90.02},
                {"lat": 23.02, "lon": 90.02},
            ],
        }, {
            "type": "way", "id": 13,
            "tags": {"highway": "residential"},
            "geometry": [{"lat": 23.02, "lon": 90.01}, {"lat": 23.02, "lon": 90.09}],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build_map(elements, out, bbox)
            glb = out / "Dhaka_Explorable_Map.glb"
            _replace_ground_with_boundary(glb, boundary, bbox)
            data = glb.read_bytes()
            self.assertEqual(data[:4], b"glTF")
            self.assertGreater(len(data), 1000)
            import trimesh
            scene = trimesh.load(glb, force="scene")
            self.assertTrue(any(name.startswith("terrain_base") for name in scene.geometry),
                            "Division-clipped ground must retain the name used by the game's collision builder")


if __name__ == "__main__":
    unittest.main()
