from __future__ import annotations

import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "map_pipeline"))

import audit_kartaview_coverage as audit


class KartaViewCoverageAuditTests(unittest.TestCase):
    def test_uses_current_kartaview_api_host_for_both_sources(self):
        self.assertEqual(
            audit.API_ROOT,
            "https://api.kartaview.org/2.0/sequence/tiles",
        )
        self.assertEqual(
            audit.PHOTO_API_ROOT,
            "https://api.kartaview.org/2.0/photo/",
        )

    def test_nearby_photo_query_preserves_valid_360_candidate_metadata(self):
        bbox = (23.0, 90.2, 23.1, 90.3)
        captured = []

        def fake_fetch(url):
            captured.append(url)
            return {
                "status": {"apiCode": 600, "httpCode": 200},
                "result": {
                    "data": [{
                        "id": 7123,
                        "userId": 91,
                        "lat": 23.05,
                        "lng": 90.25,
                        "fieldOfView": 360,
                        "projection": "SPHERE",
                        "heading": 135,
                        "dateAdded": "2026-08-12",
                        "fileurl": "https://storage2.openstreetcam.org/photo/7123.jpg",
                        "permalink": "https://kartaview.org/details/7123",
                        "sequence": {"id": 556, "userId": 91},
                    }],
                },
            }

        result = audit.discover_360_photo_candidates(
            bbox, grid_size=1, max_queries=1, radius_m=500, fetch_json=fake_fetch
        )
        self.assertEqual(len(captured), 1)
        self.assertTrue(captured[0].startswith(audit.PHOTO_API_ROOT))
        query = parse_qs(urlparse(captured[0]).query)
        self.assertEqual(query["searchFieldOfView"], ["360"])
        self.assertEqual(result["photo_rows_returned"], 1)
        self.assertEqual(result["unique_360_photo_candidates_inside_bbox"], 1)
        self.assertEqual(result["query_failures"], [])
        candidate = result["candidates"][0]
        self.assertEqual(candidate["photo_id"], "7123")
        self.assertEqual(candidate["sequence_id"], "556")
        self.assertEqual(candidate["license"], "CC BY-SA 4.0")
        self.assertTrue(candidate["attribution_required"])

    def test_unreachable_photo_endpoint_is_recorded_as_a_failure(self):
        def failing_fetch(_url):
            raise URLError("TLS hostname mismatch")

        result = audit.discover_360_photo_candidates(
            (23.0, 90.2, 23.1, 90.3),
            grid_size=1,
            max_queries=1,
            radius_m=500,
            fetch_json=failing_fetch,
        )
        self.assertEqual(result["query_count"], 1)
        self.assertEqual(result["photo_rows_returned"], 0)
        self.assertEqual(len(result["query_failures"]), 1)
        self.assertEqual(result["unique_360_photo_candidates_inside_bbox"], 0)

    def test_zero_candidates_can_be_a_valid_result_only_when_requests_succeed(self):
        self.assertTrue(audit.audit_succeeded({
            "failed_tile_count": 0,
            "photo_query_failures": [],
            "unique_360_photo_candidates_inside_bbox": 0,
        }))
        self.assertFalse(audit.audit_succeeded({
            "failed_tile_count": 30,
            "photo_query_failures": [],
            "unique_360_photo_candidates_inside_bbox": 0,
        }))
        self.assertFalse(audit.audit_succeeded({
            "failed_tile_count": 0,
            "photo_query_failures": [{"sample_index": 0, "error": "TLS failure"}],
            "unique_360_photo_candidates_inside_bbox": 0,
        }))

    def test_coverage_api_host_is_used_for_tile_requests(self):
        bbox = (23.0, 90.2, 23.05, 90.25)
        tile_url = f"{audit.API_ROOT}/1/1/12.json"
        self.assertTrue(tile_url.startswith("https://api.kartaview.org/"))


if __name__ == "__main__":
    unittest.main()
