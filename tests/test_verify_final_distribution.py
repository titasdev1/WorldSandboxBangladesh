import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.verify_final_distribution import build_report


class VerifyFinalDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.apk = self.root / "world_sandbox_bangladesh.apk"
        self.apk.write_bytes(b"signed-apk-fixture")
        self.map_dir = self.root / "MapPacks"
        self.map_dir.mkdir()
        self.part_a = self.map_dir / "map.part001"
        self.part_b = self.map_dir / "map.part002"
        self.part_a.write_bytes(b"first-map-part")
        self.part_b.write_bytes(b"second-map-part")
        self.metadata = self.map_dir / "map.json"
        parts = [self.part_a, self.part_b]
        self.metadata.write_text(json.dumps({
            "asset_filename": "Shariatpur.pck",
            "size_bytes": sum(p.stat().st_size for p in parts),
            "sha256": hashlib.sha256(b"full-pack-reference").hexdigest(),
            "parts": [{
                "asset_filename": p.name,
                "size_bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            } for p in parts],
        }), encoding="utf-8")
        self.checksum = self.root / "apk-sha256.txt"
        self.checksum.write_text(
            f"{hashlib.sha256(self.apk.read_bytes()).hexdigest()}  {self.apk.name}\n",
            encoding="utf-8",
        )
        self.core_report = self.root / "core-report.txt"
        self.core_report.write_text(
            "Core APK modularity: PASS\n"
            "District-map resources bundled in core APK: 0\n"
            "Imported district GLB scenes bundled in core APK: 0\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_report_uses_signed_apk_hash_and_verified_map_parts(self):
        report = build_report(
            self.apk, self.metadata, self.map_dir, self.checksum, self.core_report
        )
        actual_hash = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        self.assertIn(f"Core APK SHA-256 (signed upload): {actual_hash}", report)
        self.assertIn("Signed APK checksum cross-check against apk-sha256.txt: PASS", report)
        self.assertIn("Every map-part size and SHA-256: PASS", report)

    def test_rejects_stale_pre_sign_checksum(self):
        self.checksum.write_text("0" * 64 + "  unsigned.apk\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match"):
            build_report(
                self.apk, self.metadata, self.map_dir, self.checksum, self.core_report
            )

    def test_rejects_corrupt_map_part(self):
        self.part_a.write_bytes(b"corrupted")
        with self.assertRaisesRegex(ValueError, "wrong-sized|SHA-256 mismatch"):
            build_report(
                self.apk, self.metadata, self.map_dir, self.checksum, self.core_report
            )


if __name__ == "__main__":
    unittest.main()
