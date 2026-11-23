from __future__ import annotations

import hashlib
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import fetch_polyhaven_pbr_materials as fetcher


class FakeResponse:
    def __init__(self, data: bytes, status: int = 200):
        self.data = data
        self.status = status
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        if size < 0:
            size = len(self.data) - self.offset
        value = self.data[self.offset:self.offset + size]
        self.offset += len(value)
        return value


class PolyHavenMaterialFetcherTests(unittest.TestCase):
    def test_selects_2k_diffuse_normal_and_roughness_records(self):
        files = {
            "Diffuse": {
                "8k": {"jpg": {"url": "https://example.test/8k.jpg", "md5": "a" * 32, "size": 800}},
                "2k": {"jpg": {"url": "https://example.test/2k.jpg", "md5": "b" * 32, "size": 200}},
            },
            "nor_gl": {
                "8k": {"png": {"url": "https://example.test/8k_normal.png", "md5": "c" * 32, "size": 800}},
                "2k": {"png": {"url": "https://example.test/2k_normal.png", "md5": "d" * 32, "size": 200}},
            },
            "Rough": {
                "2k": {"jpg": {"url": "https://example.test/2k_rough.jpg", "md5": "e" * 32, "size": 200}},
            },
        }
        for semantic, filename in (
            ("base_color", "2k.jpg"),
            ("normal", "2k.png"),
            ("roughness", "2k.jpg"),
        ):
            selected, record = fetcher.select_map_record(files, semantic, "2k")
            self.assertEqual(filename, selected)
            self.assertIn("https://example.test/2k", record["url"])

    def test_download_checks_api_size_and_md5_before_renaming(self):
        data = b"real pbr scan bytes"
        digest = hashlib.md5(data).hexdigest()
        record = {
            "url": "https://example.test/material.png",
            "md5": digest,
            "size": len(data),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            target = pathlib.Path(temp_dir) / "material.png"
            with mock.patch.object(fetcher.urllib.request, "urlopen",
                                   return_value=FakeResponse(data)):
                downloaded = fetcher.download_verified(record, target)
            self.assertTrue(target.is_file())
            self.assertEqual(data, target.read_bytes())
            self.assertEqual(digest, downloaded["md5"])
            self.assertEqual(len(data), downloaded["bytes"])
            self.assertFalse(target.with_suffix(".png.part").exists())

    def test_rejects_bad_hash_without_leaving_partial_file(self):
        data = b"wrong scan bytes"
        record = {
            "url": "https://example.test/material.png",
            "md5": "0" * 32,
            "size": len(data),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            target = pathlib.Path(temp_dir) / "material.png"
            with mock.patch.object(fetcher.urllib.request, "urlopen",
                                   return_value=FakeResponse(data)):
                with self.assertRaises(RuntimeError):
                    fetcher.download_verified(record, target)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix(".png.part").exists())

    def test_fixed_asset_whitelist_contains_six_photographic_pbr_sets(self):
        self.assertEqual(6, len(fetcher.ASSET_TARGETS))
        self.assertEqual("plastered_wall_04", fetcher.ASSET_TARGETS["weathered_plaster"])
        self.assertEqual("worn_brick_wall", fetcher.ASSET_TARGETS["exposed_clay_brick"])
        self.assertEqual("worn_asphalt", fetcher.ASSET_TARGETS["wet_asphalt"])
        self.assertEqual("corrugated_iron_02", fetcher.ASSET_TARGETS["galvanized_shutter"])
        self.assertTrue(fetcher.USER_AGENT.startswith("A-Square-WorldSandboxBangladesh"))

    def test_build_records_cc0_provider_credit_and_map_hashes(self):
        catalogue = {
            asset_id: {"type": 1, "name": asset_id.replace("_", " ").title(),
                       "description": "A photo-scanned material", "authors": {"Test Author": "Photography"}}
            for asset_id in fetcher.ASSET_TARGETS.values()
        }
        files = {}
        for asset_id in fetcher.ASSET_TARGETS.values():
            files[asset_id] = {
                "Diffuse": {"2k": {"jpg": {"url": "https://example.test/diff.jpg",
                                            "md5": "a" * 32, "size": 1}}},
                "nor_gl": {"2k": {"png": {"url": "https://example.test/nor.png",
                                           "md5": "b" * 32, "size": 1}}},
                "Rough": {"2k": {"jpg": {"url": "https://example.test/rough.jpg",
                                          "md5": "c" * 32, "size": 1}}},
            }
        def fake_fetch(url):
            if url.endswith("/assets"):
                return catalogue
            return files[url.rsplit("/", 1)[-1]]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            with mock.patch.object(fetcher, "fetch_json", side_effect=fake_fetch), \
                 mock.patch.object(fetcher, "download_verified",
                                   side_effect=lambda rec, path: {
                                       "path": str(path), "bytes": 1, "md5": rec["md5"], "source_url": rec["url"]
                                   }):
                manifest = fetcher.build(root, "2k")
            self.assertEqual("Poly Haven", manifest["provider"])
            self.assertEqual("Powered by Poly Haven", manifest["provider_credit"])
            self.assertEqual("CC0-1.0", manifest["asset_license"])
            self.assertEqual(6, len(manifest["materials"]))
            self.assertTrue((root / "polyhaven_material_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
