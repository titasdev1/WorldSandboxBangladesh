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
    manifest = {
        "product": "test batch",
        "administrative_boundary": {"name": "Shariatpur District" if stage == "shariatpur_review" else "Dhaka Division"},
        "tile_edge_degrees": 0.05,
        "build_stage": stage,
        "tile_count_intersecting_boundary": division_total if stage == "shariatpur_review" and division_total is not None else total,
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
                {"tile_id": "sp_a", "status": "BAKED_FROM_OSM"},
                {"tile_id": "sp_b", "status": "EMPTY"},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            write_batch(batches, 2, [
                {"tile_id": "sp_c", "status": "BAKED_FROM_OSM"},
            ], total=3, geometry_count=1, stage="shariatpur_review", division_total=10)
            output = root / "shariatpur"
            summary = merge_batches(batches, output, "shariatpur_review")
            manifest = json.loads((output / "map_tiles_manifest.json").read_text())
            self.assertTrue(summary["complete_district_map"])
            self.assertFalse(summary["complete_division_map"])
            self.assertTrue(manifest["complete_district_map"])
            self.assertFalse(manifest["complete_division_map"])
            self.assertEqual(manifest["tile_count_intersecting_boundary"], 3)
            self.assertEqual(manifest["tile_count_intersecting_division"], 10)
            self.assertEqual(len(manifest["tiles"]), 3)
            report = json.loads((output / "quality_gate_report.json").read_text())
            self.assertEqual(report["status"], "REVIEW_REQUIRED")
            self.assertFalse(report["checks"]["photorealistic_facade_imagery_mapped"])
            self.assertTrue(report["checks"]["manual_visual_review_required"])
            self.assertTrue(report["checks"]["all_glbs_parse_and_contain_geometry"])
            self.assertGreater(report["checks"]["mesh_geometry_count"], 0)

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
