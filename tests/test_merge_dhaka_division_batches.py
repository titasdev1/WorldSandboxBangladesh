import json
import tempfile
import unittest
from pathlib import Path

from tools.map_pipeline.merge_dhaka_division_batches import merge_batches


def write_batch(root: Path, offset: int, records: list[dict], total: int, geometry_count: int) -> None:
    batch = root / str(offset)
    batch.mkdir(parents=True)
    for record in records:
        if record.get("status") == "BAKED_FROM_OSM":
            tile_dir = batch / record["tile_id"]
            tile_dir.mkdir(parents=True)
            (tile_dir / "Dhaka_Explorable_Map.glb").write_bytes(b"glb-" + record["tile_id"].encode())
    manifest = {
        "product": "test batch",
        "administrative_boundary": {"name": "Dhaka Division"},
        "tile_edge_degrees": 0.05,
        "tile_count_intersecting_boundary": total,
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
                {"tile_id": "tile_a", "status": "BAKED_FROM_OSM"},
                {"tile_id": "tile_b", "status": "EMPTY"},
            ], total=3, geometry_count=1)
            write_batch(batches, 2, [
                {"tile_id": "tile_c", "status": "BAKED_FROM_OSM"},
            ], total=3, geometry_count=1)
            output = root / "full"
            summary = merge_batches(batches, output)
            manifest = json.loads((output / "map_tiles_manifest.json").read_text())
            self.assertTrue(summary["complete_division_map"])
            self.assertEqual(manifest["tile_count_intersecting_boundary"], 3)
            self.assertEqual(manifest["tile_count_with_geometry"], 2)
            self.assertEqual(len(manifest["tiles"]), 3)
            self.assertEqual(manifest["tile_batch_offsets"], [0, 2])
            self.assertEqual(len(list(output.rglob("Dhaka_Explorable_Map.glb"))), 2)
            self.assertTrue((output / "ATTRIBUTION.txt").is_file())

    def test_refuses_missing_batches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batches = root / "batches"
            batches.mkdir()
            write_batch(batches, 2, [{"tile_id": "tile_c", "status": "BAKED_FROM_OSM"}], total=3, geometry_count=1)
            with self.assertRaisesRegex(RuntimeError, "Missing or overlapping"):
                merge_batches(batches, root / "full")


if __name__ == "__main__":
    unittest.main()
