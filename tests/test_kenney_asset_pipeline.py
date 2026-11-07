import json
import tempfile
import unittest
from pathlib import Path

from tools.kenney_pack_utils import (
    VERIFIED_DOWNLOAD_FALLBACKS,
    find_download_zip,
    write_fallback_manifest,
)
from tools.verify_medium_stage_assets import REQUIRED


class KenneyAssetPipelineTests(unittest.TestCase):
    def test_city_pack_fallback_is_valid_json_with_a_real_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset_manifest.json"
            write_fallback_manifest(path, "https://kenney.nl/assets/city-kit-commercial", "network unavailable")
            contents = path.read_text(encoding="utf-8")
            parsed = json.loads(contents)
            self.assertTrue(contents.endswith("\n"))
            self.assertFalse(contents.endswith("\\n"))
            self.assertFalse(parsed["available"])
            self.assertEqual(parsed["model_count"], 0)
            self.assertEqual(parsed["models"], [])
            self.assertIn("network unavailable", parsed["reason"])

    def test_download_resolver_finds_current_slug_archive_from_official_page(self):
        page = '<a href="/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz">Download</a>'
        self.assertEqual(find_download_zip(page, "car-kit"),
                         "https://kenney.nl/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz")

    def test_download_resolver_rejects_unrelated_or_external_archives(self):
        page = '<a href="https://example.com/car-kit.zip">external</a><a href="/media/pages/assets/city-kit-roads/abc/roads.zip">wrong</a>'
        with self.assertRaises(ValueError):
            find_download_zip(page, "unlisted-pack")

    def test_verified_dynamic_download_fallbacks_cover_all_required_cc0_packs(self):
        expected = {
            "car-kit", "city-kit-commercial", "city-kit-industrial", "city-kit-suburban"
        }
        self.assertEqual(set(VERIFIED_DOWNLOAD_FALLBACKS), expected)
        for slug, url in VERIFIED_DOWNLOAD_FALLBACKS.items():
            with self.subTest(slug=slug):
                self.assertEqual(find_download_zip("<html>dynamic link omitted</html>", slug), url)
                self.assertTrue(url.startswith(f"https://kenney.nl/media/pages/assets/{slug}/"))
                self.assertTrue(url.endswith(".zip"))

    def test_medium_stage_gate_requires_all_four_authored_packs(self):
        self.assertEqual(set(REQUIRED), {
            "kenney_car_kit", "kenney_city_kit_commercial",
            "kenney_city_kit_industrial", "kenney_city_kit_suburban"
        })
        self.assertEqual(REQUIRED["kenney_car_kit"], 30)


if __name__ == "__main__":
    unittest.main()
