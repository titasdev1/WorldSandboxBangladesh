import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def block(source: str, start: str, end: str) -> str:
    a = source.index(start)
    b = source.index(end, a)
    return source[a:b]


class AraOperatorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visual = read("character_visual.gd")
        cls.android = read(".github/workflows/android.yml")
        cls.smoke = read("tests/ara_operator_runtime_smoke.gd")
        cls.profile = json.loads(read("tools/ara3d/asquare_operator.params.json"))

    def test_validated_ara_glb_is_preferred_over_older_humanoid_candidates(self):
        self.assertIn('const ARA_HERO_PATH := "res://external_content/ara3d_operator/high/a_square_bangladesh_operator.glb"', self.visual)
        choose = block(self.visual, "func _try_load_authored_hero()", "func _begin_staged_authored_hero_load()")
        self.assertLess(choose.index("ResourceLoader.exists(ARA_HERO_PATH)"), choose.index("ResourceLoader.exists(CHARACTER_CREATOR_HERO_PATH)"))
        self.assertIn('_authored_hero_source = "Ara3D"', choose)

    def test_rifle_animation_states_are_bound_and_looping_locomotion_is_configured(self):
        for clip in ("Rifle idle (low ready)", "Rifle walk (aiming)", "Rifle run", "Rifle sprint", "Rifle aim idle", "Rifle fire (full auto)", "Rifle reload", "Crouch aim idle", "Crouch walk (aiming)"):
            self.assertIn(clip, self.visual)
        self.assertIn("Animation.LOOP_LINEAR", self.visual)
        self.assertIn('"aim_walk"', self.visual)
        self.assertIn('"sprint"', self.visual)

    def test_weapon_uses_authored_right_hand_socket_when_ara_is_active(self):
        self.assertIn('find_child("WeaponR", true, false)', self.visual)
        self.assertIn('authored_socket.add_child(_weapon_root)', self.visual)
        self.assertIn("weapon_socket_attached", self.visual)

    def test_android_pipeline_fetches_the_validated_artifact_for_current_parameter_revision(self):
        self.assertIn("workflow_id == 417330351", self.android)
        self.assertIn("actions/runs?head_sha=$PROFILE_COMMIT&per_page=100", self.android)
        self.assertNotIn("actions/workflows/ara-operator-assets.yml/runs", self.android)
        self.assertIn("actions/download-artifact@v4", self.android)
        self.assertIn("A-Square-Ara3D-Operator-Candidates", self.android)
        self.assertIn("tools/ara3d/asquare_operator.params.json", self.android)
        self.assertIn("ara_operator_runtime_smoke.gd", self.android)

    def test_runtime_smoke_covers_rig_textures_weapon_and_real_animation(self):
        for marker in ("ARA3D_RUNTIME_PASS", "RightHand", "WeaponR", "textured_surface_count", "LOOP_LINEAR"):
            self.assertIn(marker, self.smoke)
        self.assertTrue(self.profile["animations"])
        self.assertEqual(self.profile["detail"], "high")


if __name__ == "__main__":
    unittest.main()
