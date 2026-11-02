import json
import tempfile
import unittest
from pathlib import Path

from tools.kenney_pack_utils import find_download_zip, write_fallback_manifest


class KenneyAssetPipelineTests(unittest.TestCase):
    def test_city_pack_fallback_is_valid_json_with_a_real_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset_manifest.json"
            write_fallback_manifest(
                path,
                "https://kenney.nl/assets/city-kit-commercial",
                "network unavailable",
            )
            contents = path.read_text(encoding="utf-8")
            parsed = json.loads(contents)
            self.assertTrue(contents.endswith("\n"))
            self.assertFalse(contents.endswith("\\n"))
            self.assertFalse(parsed["available"])
            self.assertEqual(parsed["model_count"], 0)
            self.assertEqual(parsed["models"], [])
            self.assertIn("network unavailable", parsed["reason"])

    def test_download_resolver_finds_current_slug_archive_from_official_page(self):
        page = """
        <html><a href="/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz">
        Download</a></html>
        """
        self.assertEqual(
            find_download_zip(page, "car-kit"),
            "https://kenney.nl/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz",
        )

    def test_download_resolver_rejects_unrelated_or_external_archives(self):
        page = """
        <a href="https://example.com/car-kit.zip">external</a>
        <a href="/media/pages/assets/city-kit-roads/abc123/roads.zip">wrong pack</a>
        """
        with self.assertRaises(ValueError):
            find_download_zip(page, "car-kit")


if __name__ == "__main__":
    unittest.main()
