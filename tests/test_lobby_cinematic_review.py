from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/blender/render_asquare_lobby_cinematic_review.py"


class LobbyCinematicReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_review_uses_the_actual_high_detail_operator_rig(self):
        self.assertIn("bpy.ops.import_scene.gltf(filepath=str(operator_glb))", self.source)
        self.assertIn('obj.type == "ARMATURE"', self.source)
        self.assertIn('obj.type == "MESH"', self.source)
        self.assertIn("OPERATOR_PREVIEW_HEIGHT_M = 1.8", self.source)
        self.assertIn("operator_is_preview_only", self.source)

    def test_review_includes_front_both_three_quarter_and_rear_high_angles(self):
        for shot in (
            "01_hero_front",
            "02_left_three_quarter",
            "03_right_three_quarter",
            "04_rear_high_overlook",
            "05_operator_closeup",
        ):
            self.assertIn(shot, self.source)
        self.assertIn("def render_stills", self.source)

    def test_camera_orbit_is_keyframed_and_encoded_as_h264_mp4(self):
        self.assertIn("def add_orbit_camera", self.source)
        self.assertIn("camera.keyframe_insert(data_path=\\"location\\", frame=frame)", self.source)
        self.assertIn("camera.keyframe_insert(data_path=\\"rotation_euler\\", frame=frame)", self.source)
        self.assertIn('"libx264"', self.source)
        self.assertIn('"yuv420p"', self.source)
        self.assertIn("REVIEW_FRAMES = 120", self.source)

    def test_preview_only_character_and_cameras_are_not_in_game_glb(self):
        self.assertIn("operator_is_preview_only", self.source)
        self.assertIn("review cameras are not included", self.source)
        self.assertIn("production lobby GLB remains a separate live environment asset", self.source)
        self.assertNotIn("bpy.ops.export_scene.gltf", self.source)

    def test_review_records_exact_views_and_clip_metadata(self):
        self.assertIn('"still_views": stills', self.source)
        self.assertIn('"orbit_clip": orbit', self.source)
        self.assertIn('"RENDERED_REVIEW_MEDIA_NOT_ART_APPROVED"', self.source)
        self.assertIn("A2_LOBBY_CINEMATIC_REVIEW_READY:", self.source)

    def test_review_requires_pinned_blender_and_ffmpeg(self):
        self.assertIn("EXPECTED_BLENDER = (5, 2, 4)", self.source)
        self.assertIn('shutil.which("ffmpeg")', self.source)
        self.assertIn("ffmpeg is required", self.source)


if __name__ == "__main__":
    unittest.main()
