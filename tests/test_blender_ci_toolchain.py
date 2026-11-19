import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BlenderCIToolchainTests(unittest.TestCase):
    def test_installer_pins_supported_lts_and_checks_official_checksum(self):
        installer = (ROOT / "tools/install_blender_ci.sh").read_text(encoding="utf-8")
        self.assertIn('BLENDER_VERSION="${BLENDER_VERSION:-5.2.4}"', installer)
        self.assertIn("download.blender.org/release/", installer)
        self.assertIn("sha256sum --check expected.sha256", installer)
        self.assertIn("refusing unverified archive", installer)
        self.assertIn("Unexpected Blender version", installer)
        self.assertIn('export PATH="${BLENDER_DIR}:${PATH}"', installer)

    def test_blender_workflows_share_the_pinned_installer(self):
        for relative in (
            ".github/workflows/android.yml",
            ".github/workflows/validate-blender-assets.yml",
        ):
            workflow = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("tools/install_blender_ci.sh", workflow)
            self.assertIn("source tools/install_blender_ci.sh", workflow)
            self.assertIn("Blender 5.2.4 LTS", workflow)
            self.assertNotIn("apt-get install -y blender", workflow)


if __name__ == "__main__":
    unittest.main()
