from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools.select_shariatpur_art_target import select


class ShariatpurArtTargetSelectionTests(unittest.TestCase):
    def test_selects_shop_with_real_osm_footprint_door_and_nearby_world_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "source"
            out = pathlib.Path(tmp) / "out"
            root.mkdir()
            tile_id = "shariatpur_2321_9035"
            tile = root / tile_id
            tile.mkdir()
            (root / "ATTRIBUTION.txt").write_text("OpenStreetMap ODbL attribution\n")
            footprint = [[-6.0, -5.0], [6.0, -5.0], [6.0, 5.0], [-6.0, 5.0]]
            seed = {
                "osm_id": 987654,
                "name": "Local Grocery",
                "category": "convenience",
                "building_tags": {"building": "retail", "shop": "convenience", "name:bn": "মুদির দোকান"},
                "footprint_local_m": footprint,
                "door_anchor_local_m": [0.0, -5.0],
                "door_outward_xy": [0.0, -1.0],
                "door_placement_source": "MAPPED_ENTRANCE_NODE",
                "ground_elevation_m": 2.15,
                "height_metres": 6.2,
                "height_source": "OSM height tag",
                "floors_estimate": 2,
                "floors_source": "OSM building:levels tag",
                "geometry_confidence": "OSM_FOOTPRINT_FROM_SOURCE_DATA",
            }
            (tile / "AI_Interior_Seeds.json").write_text(json.dumps([seed]))
            (tile / "Dhaka_Explorable_Map.glb").write_bytes(b"test-glb")
            (tile / "Dhaka_OSM_Source.geojson").write_text(json.dumps({"type":"FeatureCollection","features":[]}))
            (tile / "map_manifest.json").write_text(json.dumps({"tile_id":tile_id}))
            tiles = [{
                "tile_id": tile_id,
                "origin_lat_lon": [23.2167, 90.3500],
                "glb": f"{tile_id}/Dhaka_Explorable_Map.glb",
                "geojson": f"{tile_id}/Dhaka_OSM_Source.geojson",
                "interior_seeds": f"{tile_id}/AI_Interior_Seeds.json",
                "status": "BAKED_FROM_OSM",
            }]
            # Keep the source manifest's 60-tile count; only one tile is materialized
            # in this fixture because the selector skips records without seed files.
            for i in range(1, 60):
                tiles.append({
                    "tile_id": f"empty_{i}",
                    "origin_lat_lon": [23.2167, 90.3500],
                    "glb": f"empty_{i}/Dhaka_Explorable_Map.glb",
                    "geojson": f"empty_{i}/Dhaka_OSM_Source.geojson",
                    "interior_seeds": f"empty_{i}/AI_Interior_Seeds.json",
                    "status": "BAKED_FROM_OSM",
                })
            manifest = {
                "build_stage": "shariatpur_review",
                "administrative_boundary": {"name":"Shariatpur"},
                "game_origin_lat_lon": [23.2500, 90.3800],
                "tiles": tiles,
                "tile_batch_count": 60,
                "tile_count_total": 60,
                "tile_count_with_geometry": 60,
                "tile_count_intersecting_boundary": 60,
                "complete_district_map": True,
            }
            (root / "map_tiles_manifest.json").write_text(json.dumps(manifest))
            result = select(root, out, 12.28, 9.875, 44264284704, "7a0d583", "44257499872")

            selected = result["selected_building"]
            self.assertEqual(selected["osm_id"], "987654")
            self.assertEqual(selected["tile_id"], tile_id)
            self.assertEqual(selected["door_placement_source"], "MAPPED_ENTRANCE_NODE")
            self.assertAlmostEqual(selected["ground_elevation_m"], 2.15)
            self.assertGreater(selected["distance_from_source_map_origin_m"], 2200.0)

            subset_path = out / "selected-map" / "map_tiles_manifest.json"
            subset = json.loads(subset_path.read_text())
            self.assertEqual(len(subset["tiles"]), 1)
            self.assertFalse(subset["complete_district_map"])
            self.assertEqual(subset["validation_subset"]["source_tile_count"], 60)
            self.assertAlmostEqual(subset["game_origin_lat_lon"][0], selected["latitude"])
            self.assertAlmostEqual(subset["game_origin_lat_lon"][1], selected["longitude"])
            self.assertTrue((out / "selected-map" / tile_id / "Dhaka_Explorable_Map.glb").is_file())
            self.assertTrue((out / "selected-map" / tile_id / "AI_Interior_Seeds.json").is_file())
            self.assertTrue((out / "shariatpur_art_target.json").is_file())

    def test_rejects_a_curated_approximate_landmark_as_generic_retail_art_target(self):
        from tools.select_shariatpur_art_target import _score
        seed = {
            "osm_id": -62900001,
            "category": "retail",
            "building_tags": {"building":"retail","shop":"convenience"},
            "footprint_local_m": [[0,0],[12,0],[12,10],[0,10]],
            "door_anchor_local_m": [0,1],
            "door_outward_xy": [0,-1],
            "geometry_confidence": "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED",
        }
        self.assertIsNone(_score(seed,12.28,9.875))


if __name__ == "__main__":
    unittest.main()
