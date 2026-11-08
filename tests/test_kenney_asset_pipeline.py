import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.kenney_pack_utils import (
    VERIFIED_DOWNLOAD_FALLBACKS,
    download_zip,
    find_download_zip,
    write_fallback_manifest,
)
from tools.verify_medium_stage_assets import REQUIRED


class FakeResponse:
    def __init__(self, payload, url, content_type="application/zip"):
        self.payload = payload
        self.url = url
        self.status = 200
        self.headers = {
            "Content-Type": content_type,
            "Content-Encoding": "",
        }

    def read(self, size=-1):
        if size < 0:
            return self.payload
        return self.payload[:size]

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def sample_zip():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("models/test.glb", b"glTF")
    return stream.getvalue()


class KenneyAssetPipelineTests(unittest.TestCase):
    def test_fallback_manifest_is_valid_json_with_a_real_newline(self):
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

    def test_download_resolver_parses_real_html_href_whitespace_and_relative_url(self):
        page = '<a class="download" href = "/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz">Download</a>'
        self.assertEqual(
            find_download_zip(page, "car-kit"),
            "https://kenney.nl/media/pages/assets/car-kit/abc123/kenney_car-kit.zip?token=xyz",
        )

    def test_download_resolver_parses_inline_zip_urls(self):
        page = '<script>window.pack="https://kenney.nl/media/pages/assets/city-kit-suburban/abc/pack.zip";</script>'
        self.assertEqual(
            find_download_zip(page, "city-kit-suburban"),
            "https://kenney.nl/media/pages/assets/city-kit-suburban/abc/pack.zip",
        )

    def test_download_resolver_rejects_unrelated_or_external_archives(self):
        page = '<a href="https://example.com/car-kit.zip">external</a><a href="/media/pages/assets/city-kit-roads/abc/roads.zip">wrong</a>'
        with self.assertRaises(ValueError):
            find_download_zip(page, "unlisted-pack")

    def test_official_fallbacks_cover_all_required_cc0_packs(self):
        expected = {
            "car-kit", "city-kit-commercial", "city-kit-industrial", "city-kit-suburban"
        }
        self.assertEqual(set(VERIFIED_DOWNLOAD_FALLBACKS), expected)
        for slug, url in VERIFIED_DOWNLOAD_FALLBACKS.items():
            with self.subTest(slug=slug):
                self.assertEqual(find_download_zip("<html>download link omitted</html>", slug), url)
                self.assertTrue(url.startswith(f"https://kenney.nl/media/pages/assets/{slug}/"))
                self.assertTrue(url.endswith(".zip"))

    def test_download_uses_browser_headers_and_checks_actual_zip_bytes(self):
        url = VERIFIED_DOWNLOAD_FALLBACKS["car-kit"]
        referer = "https://kenney.nl/assets/car-kit"
        response = FakeResponse(sample_zip(), url)
        with patch("urllib.request.urlopen", return_value=response) as mocked:
            payload, metadata = download_zip(url, referer=referer)
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Referer"), referer)
        self.assertIn("Mozilla/5.0", request.get_header("User-agent"))
        self.assertIn("application/zip", request.get_header("Accept"))
        self.assertEqual(metadata["status"], 200)
        self.assertEqual(metadata["content_type"], "application/zip")
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(payload)))

    def test_download_rejects_html_with_response_diagnostics(self):
        url = VERIFIED_DOWNLOAD_FALLBACKS["car-kit"]
        response = FakeResponse(b"<!doctype html><title>Access denied</title>", url, "text/html")
        with patch("urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "content_type='text/html'.*Access denied"):
                download_zip(url, referer="https://kenney.nl/assets/car-kit")

    def test_medium_stage_gate_requires_all_four_authored_packs(self):
        self.assertEqual(set(REQUIRED), {
            "kenney_car_kit", "kenney_city_kit_commercial",
            "kenney_city_kit_industrial", "kenney_city_kit_suburban"
        })
        self.assertEqual(REQUIRED["kenney_car_kit"], 30)


if __name__ == "__main__":
    unittest.main()
