from __future__ import annotations

import unittest

from tools.audit_openaerialmap_coverage import (
    SHARIATPUR_BBOX, build_report, quality_tier, search_items, summarize_item,
)


def item(item_id="scene-1", license_name="CC BY 4.0", gsd=0.08):
    return {
        "type": "Feature", "id": item_id, "collection": "openaerialmap",
        "bbox": [90.2, 23.1, 90.3, 23.2],
        "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {
            "title": "Shariatpur sample ortho", "datetime": "2026-05-02T00:00:00Z",
            "gsd": gsd, "license": license_name, "provider": "Test provider",
        },
        "assets": {"visual": {"href": "https://example.invalid/visual.tif"}},
        "links": [],
    }


class OpenAerialMapAuditTests(unittest.TestCase):
    def test_search_uses_shariatpur_bbox_and_collection(self):
        calls = []

        def fake(url, method, payload):
            calls.append((url, method, payload))
            return {"features": [], "links": []}

        rows, pages, truncated = search_items(fake)
        self.assertEqual(rows, [])
        self.assertEqual(pages, 1)
        self.assertFalse(truncated)
        self.assertEqual(calls[0][1], "POST")
        self.assertEqual(calls[0][2]["collections"], ["openaerialmap"])
        self.assertEqual(tuple(calls[0][2]["bbox"]), SHARIATPUR_BBOX)

    def test_high_resolution_cc_by_item_is_candidate_not_automatic_approval(self):
        row = summarize_item(item())
        self.assertEqual(row["review_tier"], "VERY_HIGH_DETAIL_REVIEW")
        self.assertEqual(row["integration_status"], "NOT_DOWNLOADED_NOT_APPROVED")
        self.assertEqual(row["gsd_m"], 0.08)
        self.assertEqual(row["license"], "CC-BY-4.0")

    def test_unknown_or_restricted_license_is_held(self):
        self.assertEqual(summarize_item(item(license_name="CC BY-NC 4.0"))["review_tier"], "HOLD_LICENSE_REVIEW")
        self.assertEqual(summarize_item(item(license_name=""))["review_tier"], "HOLD_LICENSE_REVIEW")

    def test_missing_ground_sample_distance_is_held(self):
        self.assertEqual(summarize_item(item(gsd=None))["review_tier"], "HOLD_GSD_UNVERIFIED")

    def test_resolution_tiers_do_not_call_medium_resolution_photorealistic(self):
        self.assertEqual(quality_tier("CC-BY-4.0", 0.25, True), "HIGH_DETAIL_REVIEW")
        self.assertEqual(quality_tier("CC-BY-4.0", 0.8, True), "MEDIUM_DETAIL_REVIEW")
        self.assertEqual(quality_tier("CC-BY-4.0", 4.0, True), "REGIONAL_REFERENCE_ONLY")

    def test_report_is_fail_closed_and_does_not_claim_coverage_percent(self):
        report = build_report([item()], 1, False)
        self.assertEqual(
            report["release_gate"],
            "BLOCKED_PENDING_PER_ITEM_LICENSE_GSD_GEOMETRY_ALIGNMENT_AND_VISUAL_QA",
        )
        self.assertIn("does not establish percent of district coverage", report["limitations"][0])

    def test_pagination_follows_only_allowlisted_api_links(self):
        calls = []

        def fake(url, method, payload):
            calls.append((url, method, payload))
            if len(calls) == 1:
                return {
                    "features": [item("a")],
                    "links": [{
                        "rel": "next",
                        "href": "https://api.imagery.hotosm.org/stac/search?token=next",
                        "method": "GET",
                    }],
                }
            return {"features": [item("b")], "links": []}

        rows, pages, truncated = search_items(fake)
        self.assertEqual(pages, 2)
        self.assertEqual({row["id"] for row in rows}, {"a", "b"})
        self.assertFalse(truncated)

    def test_pagination_refuses_untrusted_host(self):
        def fake(url, method, payload):
            return {"features": [], "links": [{"rel": "next", "href": "https://example.com/steal"}]}

        with self.assertRaises(ValueError):
            search_items(fake)


if __name__ == "__main__":
    unittest.main()
