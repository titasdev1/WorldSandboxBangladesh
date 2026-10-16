import json
import tempfile
import unittest
from pathlib import Path

from tools.map_pipeline.verify_map_batch_artifact import accept_batch, validate_batch


def write_candidate(root: Path, *, source_commit: str = "fixture-sha", offset: int = 0,
                    stage: str = "shariatpur_review", glb_bytes: bytes = b"glTF-fixture",
                    generated_utc: str = "2026-01-01T00:00:00Z") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    tile_dir = root / "tile_fixture"
    tile_dir.mkdir()
    (tile_dir / "Dhaka_Explorable_Map.glb").write_bytes(glb_bytes)
    (tile_dir / "Dhaka_OSM_Source.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
    )
    (tile_dir / "AI_Interior_Seeds.json").write_text("[]", encoding="utf-8")
    (root / "ATTRIBUTION.txt").write_text("fixture attribution\n", encoding="utf-8")
    boundary = "Shariatpur District" if stage == "shariatpur_review" else "Dhaka Division"
    total_key = "tile_count_intersecting_build_boundary" if stage == "shariatpur_review" else "tile_count_intersecting_boundary"
    manifest = {
        "build_stage": stage,
        "pipeline_commit_sha": source_commit,
        "tile_edge_degrees": 0.05,
        "tile_batch_offset": offset,
        "tile_batch_count": 1,
        "tile_batch_tile_ids": ["tile_fixture"],
        "tile_count_intersecting_boundary": 1,
        "tile_count_intersecting_build_boundary": 1,
        "tile_count_intersecting_division": 9,
        "tile_count_with_geometry": 1,
        total_key: 1,
        "source_elements_in_boundary_envelope": 1,
        "generated_utc": generated_utc,
        "administrative_boundary": {
            "name": boundary,
            "metadata": {"boundary_id": "fixture-boundary"},
        },
        "tiles": [{
            "tile_id": "tile_fixture",
            "bbox_south_west_north_east": [23.1, 90.1, 23.15, 90.15],
            "origin_lat_lon": [23.125, 90.125],
            "glb": "tile_fixture/Dhaka_Explorable_Map.glb",
            "geojson": "tile_fixture/Dhaka_OSM_Source.geojson",
            "interior_seeds": "tile_fixture/AI_Interior_Seeds.json",
            "feature_counts": {"building_footprints": 1},
            "status": "BAKED_FROM_OSM",
        }],
    }
    (root / "map_tiles_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return root


class VerifyMapBatchArtifactTests(unittest.TestCase):
    def test_accepts_first_provenanced_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = write_candidate(base / "candidate")
            destination = base / "batches" / "0"
            result = accept_batch(candidate, destination, 0, "shariatpur_review", "fixture-sha")
            self.assertEqual(result, "batch accepted")
            self.assertTrue((destination / "map_tiles_manifest.json").is_file())

    def test_accepts_identical_duplicate_and_replaces_destination_atomically_by_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = write_candidate(base / "first", generated_utc="2026-01-01T00:00:00Z")
            destination = base / "batches" / "0"
            accept_batch(first, destination, 0, "shariatpur_review", "fixture-sha")
            duplicate = write_candidate(base / "duplicate", generated_utc="2026-01-02T00:00:00Z")
            result = accept_batch(duplicate, destination, 0, "shariatpur_review", "fixture-sha")
            self.assertIn("identical duplicate", result)
            saved = json.loads((destination / "map_tiles_manifest.json").read_text())
            self.assertEqual(saved["generated_utc"], "2026-01-02T00:00:00Z")

    def test_rejects_conflicting_duplicate_tile_content_without_overwriting_good_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = write_candidate(base / "first", glb_bytes=b"glTF-good")
            destination = base / "batches" / "0"
            accept_batch(first, destination, 0, "shariatpur_review", "fixture-sha")
            before = (destination / "tile_fixture" / "Dhaka_Explorable_Map.glb").read_bytes()
            conflicting = write_candidate(base / "conflicting", glb_bytes=b"glTF-different")
            with self.assertRaisesRegex(ValueError, "Conflicting artifacts"):
                accept_batch(conflicting, destination, 0, "shariatpur_review", "fixture-sha")
            self.assertEqual((destination / "tile_fixture" / "Dhaka_Explorable_Map.glb").read_bytes(), before)

    def test_rejects_wrong_offset_stage_or_pipeline_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = write_candidate(Path(tmp) / "candidate")
            with self.assertRaisesRegex(ValueError, "offset mismatch"):
                validate_batch(candidate, 8, "shariatpur_review", "fixture-sha")
            with self.assertRaisesRegex(ValueError, "stage mismatch"):
                validate_batch(candidate, 0, "full_division", "fixture-sha")
            with self.assertRaisesRegex(ValueError, "pinned source commit"):
                validate_batch(candidate, 0, "shariatpur_review", "different-sha")

    def test_rejects_path_traversal_in_tile_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = write_candidate(Path(tmp) / "candidate")
            manifest_path = candidate / "map_tiles_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["tiles"][0]["glb"] = "../outside.glb"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unsafe artifact path"):
                validate_batch(candidate, 0, "shariatpur_review", "fixture-sha")


if __name__ == "__main__":
    unittest.main()
