import json
import tempfile
import unittest
from pathlib import Path

import trimesh

from tools.map_pipeline.merge_dhaka_division_batches import merge_batches


def write_batch(root: Path, offset: int, records: list[dict], total: int, geometry_count: int, stage: str = "full_division", division_total: int | None = None) -> None:
    batch = root / str(offset)
    batch.mkdir(parents=True)
    for record in records:
        if record.get("status") == "BAKED_FROM_OSM":
            tile_dir = batch / record["tile_id"]
            tile_dir.mkdir(parents=True)
            (tile_dir / "Dhaka_Explorable_Map.glb").write_bytes(trimesh.Scene(trimesh.creation.box()).export(file_type="glb"))
            (tile_dir / "map_manifest.json").write_text(json.dumps({
                "feature_counts": record.get("feature_counts", {}),
                "licensed_facade_photo_matches": record.get("licensed_facade_photo_matches", []),
            }), encoding="utf-8")
    manifest = {
        "product": "test batch",
        "administrative_boundary": {"name": "Shariatpur District" if stage == "shariatpur_review" else "Dhaka Division"},
        "tile_edge_degrees": 0.05,
        "pipeline_commit_sha": "test-sha",
        "build_stage": stage,
        "tile_count_intersecting_boundary": total,
        "tile_count_intersecting_division": division_total if stage == "shariatpur_review" and division_total is not None else total,
        "tile_count_intersecting_build_boundary": total,
        "tile_count_with_geometry": geometry_count,
        "tile_batch_offset": offset,
        "tile_batch_count": len(records),
        "tile_batch_tile_ids": [record["tile_id"] for record in records],
        "source_elements_in_boundary_envelope": 10,
        "region_south_west_north_east": [22.0, 89.0, 25.0, 92.0],
        "tiles": records,
    }
    (batch / "map_tiles_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (batch / "ATTRIBUTION.txt").write_text("© OpenStreetMap contributors\n", encoding="utf-8")


class MergeDhakaDivisionBatchesTests(unittest.TestCase):
    def test_merges_complete_offsets_and_keeps_empty_tiles_in_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM", "feature_counts": {"building_footprints": 3, "road_ways": 2}},
                {"tile_id": "tile_b", "status": "EMPTY", "feature_counts": {"building_footprints": 0, "road_ways": 0}},
            ], total=3, geometry_count=1)
            write_batch(batches, 2, [
                {"tile_id": "tile_c", "status": "BAKED_FROM_OSM", "feature_counts": {"building_footprints": 4}},
            ], total=3, geometry_count=1)
            output = root / "full"
            summary = merge_batches(batches, output)
            manifest = json.loads((output / "map_tiles_manifest.json").read_text())
            self.assertTrue(summary["complete_division_map"])
            self.assertEqual(manifest["tile_count_intersecting_boundary"], 3)
            self.assertEqual(manifest["tile_count_with_geometry"], 2)
            self.assertEqual(manifest["feature_counts_across_tiles"]["building_footprints"], 7)
            self.assertEqual(manifest["feature_counts_across_tiles"]["road_ways"], 2)
            self.assertEqual(len(manifest["tiles"]), 3)
            self.assertEqual(manifest["tile_batch_offsets"], [0, 2])
            self.assertEqual(len(list(output.rglob("Dhaka_Explorable_Map.glb"))), 2)
            self.assertTrue((output / "ATTRIBUTION.txt").is_file())

    def test_merges_complete_shariatpur_stage_as_district_not_division(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "sp_a", "status": "BAKED_FROM_OSM",
                 "feature_counts": {"building_footprints": 3, "buildings_with_inferred_height": 2, "licensed_facade_photo_panels": 3},
                 "licensed_facade_photo_matches": [
                     {"image_id": "manasha_temple_back_view_01",
                      "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                      "author": "Shuvajit BD", "license": "CC BY-SA 4.0"},
                     {"image_id": "rudrakar_moth_35",
                      "source_page": "https://commons.wikimedia.org/wiki/File:Rudrakar_Moth_35.jpg",
                      "author": "Radman Siddiki", "license": "CC BY 4.0"},
                     {"image_id": "kartikpur_jomidar_bari_123242",
                      "source_page": "https://commons.wikimedia.org/wiki/File:Kartikpur_Jomidar_Bari_(123242).jpg",
                      "author": "Moheen Reeyad", "license": "CC BY-SA 4.0"},
                 ]},
                {"tile_id": "sp_b", "status": "EMPTY"},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            write_batch(batches, 2, [
                {"tile_id": "sp_c", "status": "BAKED_FROM_OSM",
                 "feature_counts": {"building_footprints": 1, "buildings_with_inferred_height": 1}},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            # Model a real in-progress sequence: earlier batches have the legacy
            # division-wide count in tile_count_intersecting_boundary, while newer
            # batches report district and division totals separately.
            legacy_manifest_path = batches / "0" / "map_tiles_manifest.json"
            legacy_manifest = json.loads(legacy_manifest_path.read_text())
            legacy_manifest.pop("tile_count_intersecting_division")
            legacy_manifest["tile_count_intersecting_boundary"] = 10
            legacy_manifest_path.write_text(json.dumps(legacy_manifest), encoding="utf-8")
            output = root / "shariatpur"
            summary = merge_batches(batches, output, "shariatpur_review")
            manifest = json.loads((output / "map_tiles_manifest.json").read_text())
            self.assertTrue(summary["complete_district_map"])
            self.assertFalse(summary["complete_division_map"])
            self.assertTrue(manifest["complete_district_map"])
            self.assertFalse(manifest["complete_division_map"])
            self.assertEqual(manifest["tile_count_intersecting_boundary"], 3)
            self.assertEqual(manifest["tile_count_intersecting_division"], 10)
            self.assertEqual(manifest["game_origin_lat_lon"], [23.5, 90.5])
            self.assertEqual(len(manifest["tiles"]), 3)
            self.assertIn("BGD ADM2", manifest["administrative_boundary"]["attribution"])
            attribution = (output / "ATTRIBUTION.txt").read_text(encoding="utf-8")
            self.assertIn("BGD ADM2", attribution)
            self.assertNotIn("BGD ADM1", attribution)
            report = json.loads((output / "quality_gate_report.json").read_text())
            self.assertEqual(report["status"], "REVIEW_REQUIRED")
            self.assertFalse(report["checks"]["photorealistic_facade_imagery_mapped"])
            self.assertTrue(report["checks"]["manual_visual_review_required"])
            self.assertTrue(report["checks"]["all_glbs_parse_and_contain_geometry"])
            self.assertGreater(report["checks"]["mesh_geometry_count"], 0)
            self.assertFalse(report["checks"]["all_building_heights_verified_or_surveyed"])
            self.assertEqual(report["checks"]["licensed_facade_photo_panel_count"], 3)
            self.assertTrue(report["checks"]["licensed_facade_photo_panels_embedded"])
            self.assertEqual(report["checks"]["estimated_building_heights_count"], 3)
            self.assertEqual(report["checks"]["estimated_building_heights_percent"], 75.0)

    def test_refuses_shariatpur_package_with_zero_embedded_exterior_photo_panels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "sp_a", "status": "BAKED_FROM_OSM",
                 "feature_counts": {"building_footprints": 3, "licensed_facade_photo_panels": 0}},
                {"tile_id": "sp_b", "status": "EMPTY"},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            write_batch(batches, 2, [
                {"tile_id": "sp_c", "status": "BAKED_FROM_OSM",
                 "feature_counts": {"building_footprints": 1, "licensed_facade_photo_panels": 0}},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            with self.assertRaisesRegex(RuntimeError, "zero embedded licensed exterior photo panels"):
                merge_batches(batches, root / "should_not_publish", "shariatpur_review")

    def test_refuses_partial_approved_shariatpur_exterior_photo_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "sp_a", "status": "BAKED_FROM_OSM",
                 "feature_counts": {"building_footprints": 3, "licensed_facade_photo_panels": 1},
                 "licensed_facade_photo_matches": [{
                     "image_id": "manasha_temple_back_view_01",
                     "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                     "author": "Shuvajit BD", "license": "CC BY-SA 4.0",
                 }]},
            ], total=1, geometry_count=1, stage="shariatpur_review", division_total=10)
            with self.assertRaisesRegex(RuntimeError, "approved exterior photo panel coverage is incomplete"):
                merge_batches(batches, root / "should_not_publish", "shariatpur_review")

    def test_merges_interior_reference_photo_manifest_asset_and_license_restriction(self):
        import hashlib

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(
                batches, 0,
                [{"tile_id": "sp_mosque", "status": "BAKED_FROM_OSM",
                  "feature_counts": {"building_footprints": 1, "interior_reference_photos": 1, "licensed_facade_photo_panels": 3},
                  "licensed_facade_photo_matches": [
                      {"image_id": "manasha_temple_back_view_01",
                       "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                       "author": "Shuvajit BD", "license": "CC BY-SA 4.0"},
                      {"image_id": "rudrakar_moth_35",
                       "source_page": "https://commons.wikimedia.org/wiki/File:Rudrakar_Moth_35.jpg",
                       "author": "Radman Siddiki", "license": "CC BY 4.0"},
                      {"image_id": "kartikpur_jomidar_bari_123242",
                       "source_page": "https://commons.wikimedia.org/wiki/File:Kartikpur_Jomidar_Bari_(123242).jpg",
                       "author": "Moheen Reeyad", "license": "CC BY-SA 4.0"},
                  ]}],
                total=1, geometry_count=1, stage="shariatpur_review", division_total=10,
            )
            tile = batches / "0" / "sp_mosque"
            photo = tile / "landmark_reference_photos" / "mosque-interior.jpg"
            photo.parent.mkdir(parents=True)
            photo_bytes = b"licensed-interior-photo-fixture-bytes"
            photo.write_bytes(photo_bytes)
            match = {
                "osm_id": 12345,
                "building_name": "বুড়িরহাট ঐতিহাসিক জামে মসজিদ",
                "image_id": "burirhat_mosque_interior_01",
                "tile_id": "sp_mosque",
                "asset_relative_path": "landmark_reference_photos/mosque-interior.jpg",
                "sha256": hashlib.sha256(photo_bytes).hexdigest(),
                "source_page": "https://commons.wikimedia.org/wiki/File:Bibir_Hat_Mosque_01.jpg",
                "author": "Radman Siddiki",
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY-SA 4.0",
                "use": "INTERIOR_REFERENCE_ONLY",
                "visual_identity_verified": True,
            }
            exterior_matches = [
                {"image_id": "manasha_temple_back_view_01",
                 "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                 "author": "Shuvajit BD", "license": "CC BY-SA 4.0"},
                {"image_id": "rudrakar_moth_35",
                 "source_page": "https://commons.wikimedia.org/wiki/File:Rudrakar_Moth_35.jpg",
                 "author": "Radman Siddiki", "license": "CC BY 4.0"},
                {"image_id": "kartikpur_jomidar_bari_123242",
                 "source_page": "https://commons.wikimedia.org/wiki/File:Kartikpur_Jomidar_Bari_(123242).jpg",
                 "author": "Moheen Reeyad", "license": "CC BY-SA 4.0"},
            ]
            (tile / "map_manifest.json").write_text(json.dumps({
                "interior_reference_photo_matches": [match],
                "licensed_facade_photo_matches": exterior_matches,
            }), encoding="utf-8")

            output = root / "shariatpur"
            merge_batches(batches, output, "shariatpur_review")
            manifest = json.loads((output / "map_tiles_manifest.json").read_text(encoding="utf-8"))
            report = json.loads((output / "quality_gate_report.json").read_text(encoding="utf-8"))
            attribution = (output / "ATTRIBUTION.txt").read_text(encoding="utf-8")

            self.assertEqual(manifest["interior_reference_photos_embedded"], 1)
            self.assertEqual(manifest["interior_reference_photo_matches"][0]["image_id"], "burirhat_mosque_interior_01")
            self.assertEqual(manifest["interior_reference_photo_matches"][0]["use"], "INTERIOR_REFERENCE_ONLY")
            self.assertEqual(manifest["licensed_facade_photo_matches"][0]["image_id"], "manasha_temple_back_view_01")
            self.assertEqual((output / "sp_mosque" / "landmark_reference_photos" / "mosque-interior.jpg").read_bytes(), photo_bytes)
            self.assertIn("INTERIOR REFERENCE ONLY", attribution)
            self.assertIn("CC BY-SA 4.0", attribution)
            self.assertTrue(report["checks"]["interior_reference_photo_matches_manifest"])
            self.assertEqual(report["checks"]["interior_reference_photo_asset_count"], 1)

    def test_refuses_missing_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 2, [{"tile_id": "tile_c", "status": "BAKED_FROM_OSM"}], total=3, geometry_count=1)
            with self.assertRaisesRegex(RuntimeError, "Missing or overlapping"):
                merge_batches(batches, root / "full")


    def test_refuses_duplicate_tile_ids_across_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_duplicate", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            write_batch(batches, 1, [
                {"tile_id": "tile_duplicate", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            with self.assertRaisesRegex(RuntimeError, "duplicate tile ID"):
                merge_batches(batches, root / "full")

    def test_refuses_mixed_tile_sizes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            write_batch(batches, 1, [
                {"tile_id": "tile_b", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            manifest_path = batches / "1" / "map_tiles_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["tile_edge_degrees"] = 0.08
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "different tile sizes"):
                merge_batches(batches, root / "full")

    def test_refuses_missing_pipeline_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [{"tile_id": "tile_a", "status": "BAKED_FROM_OSM"}], total=1, geometry_count=1)
            manifest_path = batches / "0" / "map_tiles_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest.pop("pipeline_commit_sha")
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(RuntimeError, "missing pipeline_commit_sha"):
                merge_batches(batches, root / "out")

    def test_refuses_mixed_pipeline_commits(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            write_batch(batches, 1, [
                {"tile_id": "tile_b", "status": "BAKED_FROM_OSM"},
            ], total=2, geometry_count=1)
            manifest_path = batches / "1" / "map_tiles_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["pipeline_commit_sha"] = "different-test-sha"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "different pipeline commits"):
                merge_batches(batches, root / "full")

    def test_refuses_missing_attribution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM"},
            ], total=1, geometry_count=1)
            (batches / "0" / "ATTRIBUTION.txt").unlink()
            with self.assertRaisesRegex(RuntimeError, "required attribution"):
                merge_batches(batches, root / "full")

    def test_refuses_manifest_glb_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 0, [
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM"},
            ], total=1, geometry_count=0)
            with self.assertRaisesRegex(RuntimeError, "GLB count mismatch"):
                merge_batches(batches, root / "full")


if __name__ == "__main__":
    unittest.main()
