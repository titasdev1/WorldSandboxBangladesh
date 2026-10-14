#!/usr/bin/env python3
"""Offline regression tests for the build-time Dhaka OSM converter."""
from __future__ import annotations

import unittest

from tools.fetch_dhaka_map import element_intersects_bounds, to_feature


class DhakaFeatureConversionTests(unittest.TestCase):
    def test_highway_way_preserves_geometry_and_road_tags(self) -> None:
        element = {
            "type": "way",
            "id": 123,
            "tags": {"highway": "residential", "name": "Example Road", "oneway": "yes"},
            "geometry": [{"lon": 90.41, "lat": 23.81}, {"lon": 90.411, "lat": 23.811}],
        }
        feature = to_feature(element)
        self.assertIsNotNone(feature)
        assert feature is not None
        self.assertEqual(feature["geometry"]["type"], "LineString")
        self.assertEqual(feature["properties"]["highway"], "residential")
        self.assertEqual(feature["properties"]["name"], "Example Road")
        self.assertEqual(feature["properties"]["oneway"], "yes")
        self.assertEqual(feature["properties"]["osm_id"], 123)
        self.assertEqual(len(feature["geometry"]["coordinates"]), 2)

    def test_closed_building_way_preserves_shop_metadata(self) -> None:
        element = {
            "type": "way",
            "id": 456,
            "tags": {"building": "retail", "shop": "supermarket", "name": "Local Market",
                     "building:levels": "3"},
            "geometry": [
                {"lon": 90.41, "lat": 23.81}, {"lon": 90.411, "lat": 23.81},
                {"lon": 90.411, "lat": 23.811}, {"lon": 90.41, "lat": 23.81},
            ],
        }
        feature = to_feature(element)
        self.assertIsNotNone(feature)
        assert feature is not None
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        self.assertEqual(feature["properties"]["shop"], "supermarket")
        self.assertEqual(feature["properties"]["name"], "Local Market")
        self.assertEqual(feature["properties"]["building:levels"], "3")

    def test_shop_node_preserves_exact_name_and_position(self) -> None:
        feature = to_feature({
            "type": "node", "id": 991,
            "lon": 90.4123, "lat": 23.8107,
            "tags": {"shop": "convenience", "name": "Example Mart", "name:bn": "উদাহরণ মার্ট"}
        })
        self.assertIsNotNone(feature)
        assert feature is not None
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(feature["geometry"]["coordinates"], [90.4123, 23.8107])
        self.assertEqual(feature["properties"]["name"], "Example Mart")
        self.assertEqual(feature["properties"]["name:bn"], "উদাহরণ মার্ট")

    def test_non_way_and_unusable_geometry_are_ignored(self) -> None:
        self.assertIsNone(to_feature({"type": "relation", "tags": {"building": "yes"}, "geometry": []}))
        self.assertIsNone(to_feature({"type": "way", "tags": {"building": "yes"},
                                      "geometry": [{"lon": 90.41, "lat": 23.81}]}))

    def test_grid_clipping_keeps_features_crossing_cell_edges(self) -> None:
        bounds = (23.80, 90.40, 23.83, 90.43)
        crossing_road = {
            "type": "way", "id": 321,
            "geometry": [{"lon": 90.39, "lat": 23.81}, {"lon": 90.41, "lat": 23.81}],
        }
        outside_road = {
            "type": "way", "id": 322,
            "geometry": [{"lon": 90.35, "lat": 23.70}, {"lon": 90.36, "lat": 23.71}],
        }
        self.assertTrue(element_intersects_bounds(crossing_road, bounds))
        self.assertFalse(element_intersects_bounds(outside_road, bounds))

    def test_grid_manifest_dimensions_cover_city_scale_area(self) -> None:
        from tools.fetch_dhaka_map import CITY_CELL_DEGREES, CITY_GRID_RADIUS
        self.assertEqual(2 * CITY_GRID_RADIUS + 1, 13)
        self.assertGreater((2 * CITY_GRID_RADIUS + 1) * CITY_CELL_DEGREES, 0.20)

    def test_unclosed_building_ring_is_ignored(self) -> None:
        element = {
            "type": "way",
            "id": 789,
            "tags": {"building": "yes"},
            "geometry": [
                {"lon": 90.41, "lat": 23.81}, {"lon": 90.411, "lat": 23.81},
                {"lon": 90.411, "lat": 23.811}, {"lon": 90.41, "lat": 23.811},
            ],
        }
        self.assertIsNone(to_feature(element))


if __name__ == "__main__":
    unittest.main()
