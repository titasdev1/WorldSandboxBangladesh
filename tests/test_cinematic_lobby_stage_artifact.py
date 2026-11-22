import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "cinematic-lobby-stage"


class CinematicLobbyStageArtifactTests(unittest.TestCase):
    def test_blender_authored_stage_is_exported_with_a_review_render(self):
        glb = ROOT / "external_content" / "a_square_cinematic_lobby_stage.glb"
        preview = BUILD / "a_square_cinematic_lobby_stage_preview.png"
        blend = BUILD / "a_square_cinematic_lobby_stage.blend"
        manifest_path = BUILD / "lobby_stage_manifest.json"
        self.assertTrue(glb.is_file(), "Blender lobby GLB was not exported")
        self.assertGreater(glb.stat().st_size, 80_000)
        self.assertTrue(preview.is_file(), "Blender review render was not created")
        self.assertGreater(preview.stat().st_size, 20_000)
        self.assertTrue(blend.is_file(), "Editable Blender source was not saved")
        self.assertTrue(manifest_path.is_file(), "Asset manifest is missing")
        report = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(report.get("mesh_objects", 0), 28)
        self.assertGreater(report.get("triangles", 0), 5_000)
        self.assertIn("original Blender-authored", report.get("source", ""))
        self.assertEqual("CC0-1.0 (original project-authored asset; no third-party content)", report.get("license"))
        self.assertIn("Padma river inlay", report.get("style", []))


if __name__ == "__main__":
    unittest.main()
