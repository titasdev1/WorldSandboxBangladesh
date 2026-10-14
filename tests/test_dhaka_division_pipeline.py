import tempfile
import unittest
from pathlib import Path

from shapely.geometry import Polygon, box, shape
from tools.map_pipeline.build_dhaka_division import _clip_elements, _source_geometry, _replace_ground_with_boundary
from tools.map_pipeline.build_dhaka_map import build_map


class DhakaDivisionPipelineTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
