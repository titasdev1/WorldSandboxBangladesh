import json
import tempfile
import unittest
from pathlib import Path

from tools.map_pipeline.build_real_world_navigation_index import build_index, runtime_navigation_projection


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
                            "highway": "primary", "name": "Palong Road", "name:bn": "পালং সড়ক", "oneway": "yes", "motorcar": "yes", "motor_vehicle": "no", "motor_vehicle:conditional": "delivery @ (06:00-10:00)", "foot:conditional": "no @ (wet)", "bicycle": "designated", "sidewalk": "both", "surface": "asphalt", "smoothness": "good", "lit": "yes"
                        }},
                        "geometry": {"type": "LineString", "coordinates": [[90.35, 23.22], [90.36, 23.23]]},
                    },
                    {
                        "type": "Feature", "id": "node/909",
                        "properties": {"osm_id": 909, "tags": {
                            "amenity": "school", "name": "Palong Model School", "name:bn": "পালং মডেল স্কুল"
                        }},
                        "geometry": {"type": "Point", "coordinates": [90.356, 23.222]},
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
        self.assertEqual(report["roads"][0]["oneway"], "yes")
        self.assertEqual(report["roads"][0]["motorcar"], "yes")
        self.assertEqual(report["roads"][0]["motor_vehicle"], "no")
        self.assertEqual(report["roads"][0]["motor_vehicle_conditional"], "delivery @ (06:00-10:00)")
        self.assertEqual(report["roads"][0]["foot_conditional"], "no @ (wet)")
        self.assertEqual(report["roads"][0]["bicycle"], "designated")
        self.assertEqual(report["roads"][0]["sidewalk"], "both")
        self.assertEqual(report["roads"][0]["smoothness"], "good")
        self.assertEqual(report["roads"][0]["lit"], "yes")
        self.assertEqual(report["roads"][0]["surface"], "asphalt")
        self.assertAlmostEqual(report["roads"][0]["coordinates"]["longitude"], 90.355)
        self.assertEqual(report["roads"][0]["geometry_paths"], [[[90.35, 23.22], [90.36, 23.23]]])
        self.assertEqual(report["counts"]["named_places"], 1)
        self.assertEqual(report["places"][0]["name"], "Palong Model School")
        self.assertEqual(report["places"][0]["name_bn"], "পালং মডেল স্কুল")
        self.assertAlmostEqual(report["places"][0]["coordinates"]["latitude"], 23.222)
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


    def test_only_explicit_human_reviewed_floor_evidence_counts_as_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tile.geojson").write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature", "id": "way/202",
                    "properties": {"osm_id": 202, "tags": {"building": "apartments", "building:levels": "5"}},
                    "geometry": {"type": "Polygon", "coordinates": [[
                        [90.35, 23.22], [90.351, 23.22], [90.351, 23.221],
                        [90.35, 23.221], [90.35, 23.22]
                    ]]},
                }],
            }), encoding="utf-8")
            evidence_path = root / "building_floor_evidence.json"
            evidence_path.write_text(json.dumps({
                "schema_version": 1,
                "records": [{
                    "osm_id": "way/202",
                    "floor_count": 5,
                    "evidence_source_url": "https://example.org/building-plan",
                    "evidence_source_type": "official_building_profile",
                    "reviewer": "map-reviewer",
                    "reviewed_at": "2026-10-17",
                    "evidence_notes": "Official plan lists five occupied storeys; roof levels excluded.",
                    "verification_status": "INDEPENDENTLY_VERIFIED",
                }],
            }), encoding="utf-8")
            report = build_index(root, evidence_path)
        building = report["buildings"][0]
        self.assertTrue(building["floor_count_independently_verified"])
        self.assertEqual(building["independently_verified_floor_count"], 5)
        self.assertEqual(report["counts"]["buildings_with_independently_verified_floor_count"], 1)
        self.assertEqual(report["floor_evidence_validation"]["rejected_registry_records"], [])



    def test_indexes_building_parts_and_keeps_way_relation_ids_distinct(self):
        polygon = {"type": "Polygon", "coordinates": [[
            [90.35, 23.22], [90.351, 23.22], [90.351, 23.221],
            [90.35, 23.221], [90.35, 23.22]
        ]]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tile.geojson").write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "id": "way/202",
                     "properties": {"osm_id": 202, "tags": {"building": "apartments"}},
                     "geometry": polygon},
                    {"type": "Feature", "id": "relation/202",
                     "properties": {"osm_id": 202, "tags": {"building": "yes"}},
                     "geometry": polygon},
                    {"type": "Feature", "id": "way/404",
                     "properties": {"osm_id": 404, "tags": {"building:part": "wall"}},
                     "geometry": polygon},
                ],
            }), encoding="utf-8")
            report = build_index(root)
        self.assertEqual(report["counts"]["buildings"], 3)
        self.assertEqual(
            {item["osm_id"] for item in report["buildings"]},
            {"way/202", "relation/202", "way/404"},
        )
        self.assertEqual(
            next(item for item in report["buildings"] if item["osm_id"] == "way/404")["building_type"],
            "wall",
        )


    def test_runtime_projection_keeps_named_and_verified_buildings_but_preserves_total_counts(self):
        report = {
            "counts": {
                "buildings": 370110,
                "buildings_with_independently_verified_floor_count": 1,
            },
            "buildings": [
                {"osm_id": "way/1", "name": "Named Shop", "floor_count_independently_verified": False},
                {"osm_id": "way/2", "name": None, "floor_count_independently_verified": False},
                {"osm_id": "way/3", "name": None, "floor_count_independently_verified": True},
            ],
            "roads": [{"osm_id": "way/10"}],
            "places": [{"osm_id": "node/11"}],
        }
        runtime = runtime_navigation_projection(report)
        self.assertEqual(runtime["counts"]["buildings"], 370110)
        self.assertEqual(runtime["counts"]["searchable_buildings"], 2)
        self.assertEqual(
            {building["osm_id"] for building in runtime["buildings"]},
            {"way/1", "way/3"},
        )
        self.assertEqual(len(runtime["roads"]), 1)
        self.assertEqual(len(runtime["places"]), 1)
        self.assertEqual(len(report["buildings"]), 3, "full audit report must remain unchanged")
        self.assertEqual(runtime["runtime_projection"]["total_mapped_buildings"], 370110)



if __name__ == "__main__":
    unittest.main()
