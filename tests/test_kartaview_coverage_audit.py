import unittest
from unittest.mock import Mock

from tools.map_pipeline.audit_kartaview_coverage import (
    audit_coverage,
    latlon_to_tile,
    parse_coverage_tracks,
    tiles_for_bbox,
)


class KartaViewCoverageAuditTests(unittest.TestCase):
    def test_xyz_tile_coordinates_are_stable_at_shariatpur(self):
        x, y = latlon_to_tile(23.183, 90.3459, 12)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertIn((12, x, y), tiles_for_bbox((23.18, 90.34, 23.19, 90.35), 12))

    def test_bbox_tiles_are_bounded(self):
        tiles = tiles_for_bbox((23.18, 90.34, 23.19, 90.35), 12)
        self.assertTrue(tiles)
        self.assertTrue(all(z == 12 for z, _, _ in tiles))
        self.assertLessEqual(len(tiles), 4)

    def test_parse_tracks_preserves_order_and_match_status(self):
        payload = {"lines": [
            {"matched": "1", "track": [
                {"lat": "23.18", "lng": "90.34"},
                {"lat": "23.181", "lng": "90.341"},
            ]},
            {"matched": "0", "track": [
                {"lat": "23.19", "lng": "90.35"},
                {"lat": "23.191", "lng": "90.351"},
            ]},
        ]}
        features = parse_coverage_tracks(payload, 12, 100, 200)
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0]["geometry"]["coordinates"], [[90.34, 23.18], [90.341, 23.181]])
        self.assertTrue(features[0]["properties"]["matched_to_osm"])
        self.assertFalse(features[1]["properties"]["matched_to_osm"])
        self.assertEqual(features[0]["properties"]["license"], "CC BY-SA 4.0")

    def test_audit_respects_request_cap_and_reports_coverage(self):
        fake = Mock(return_value={"lines": [{
            "matched": "1",
            "track": [{"lat": "23.18", "lng": "90.34"}, {"lat": "23.181", "lng": "90.341"}],
        }]})
        result = audit_coverage((23.18, 90.34, 23.19, 90.35), zoom=12, max_requests=10, fetch_json=fake)
        self.assertEqual(fake.call_count, result["report"]["tile_count"])
        self.assertLessEqual(fake.call_count, 10)
        self.assertEqual(result["report"]["tiles_with_coverage_tracks"], result["report"]["tile_count"])
        self.assertEqual(result["report"]["coverage_track_count"], result["report"]["tile_count"])

    def test_audit_records_failures_instead_of_faking_empty_coverage(self):
        def failed(_url):
            raise OSError("rate limited")
        result = audit_coverage((23.18, 90.34, 23.19, 90.35), zoom=12, max_requests=10, fetch_json=failed)
        self.assertEqual(result["report"]["failed_tile_count"], result["report"]["tile_count"])
        self.assertEqual(result["report"]["coverage_track_count"], 0)

    def test_outside_tracks_are_not_counted_as_shariatpur_coverage(self):
        payload = {"lines": [{
            "matched": "1",
            "track": [
                {"lat": "23.3995", "lng": "90.1880"},
                {"lat": "23.3990", "lng": "90.2140"},
            ],
        }]}
        bbox = (23.003880881, 90.220512089, 23.451613610, 90.607763484)
        self.assertEqual(parse_coverage_tracks(payload, 12, 3074, 1774, bbox), [])

    def test_edge_crossing_track_is_clipped_to_bbox_boundary(self):
        payload = {"lines": [{
            "matched": "1",
            "track": [
                {"lat": "23.3995", "lng": "90.2140"},
                {"lat": "23.3990", "lng": "90.2300"},
            ],
        }]}
        bbox = (23.003880881, 90.220512089, 23.451613610, 90.607763484)
        features = parse_coverage_tracks(payload, 12, 3074, 1774, bbox)
        self.assertEqual(len(features), 1)
        first, last = features[0]["geometry"]["coordinates"]
        self.assertAlmostEqual(first[0], 90.220512089, places=9)
        self.assertAlmostEqual(last[0], 90.2300, places=6)
        self.assertGreaterEqual(first[1], bbox[0])
        self.assertLessEqual(last[1], bbox[2])

    def test_too_many_tile_requests_fail_before_network_calls(self):
        fake = Mock()
        with self.assertRaisesRegex(ValueError, "above the safe cap"):
            audit_coverage((20.0, 88.0, 26.0, 94.0), zoom=12, max_requests=10, fetch_json=fake)
        fake.assert_not_called()


if __name__ == "__main__":
    unittest.main()
