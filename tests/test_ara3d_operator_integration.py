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
        cls.apk_verifier = read("tools/verify_apk_contents.py")
        cls.core_verifier = read("tools/verify_core_apk_contents.py")
        cls.android = read(".github/workflows/android.yml")
        cls.smoke = read("tests/ara_operator_runtime_smoke.gd")
        cls.profile = json.loads(read("tools/ara3d/asquare_operator.params.json"))
        cls.asset_workflow = read(".github/workflows/ara-operator-assets.yml")
        cls.preview_script = read("tools/ara3d/render_operator_contact_sheet.py")

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

    def test_weapon_uses_the_authored_weaponr_skeleton_bone(self):
        self.assertIn('skeleton.find_bone("WeaponR")', self.visual)
        self.assertIn('_authored_weapon_attachment.bone_name = "WeaponR"', self.visual)
        self.assertIn('_authored_weapon_attachment.add_child(_weapon_root)', self.visual)
        self.assertIn("weapon_socket_attached", self.visual)

    def test_first_person_hides_only_head_and_restores_it_for_third_person(self):
        self.assertIn('func set_first_person_view(enabled: bool)', self.visual)
        self.assertIn('find_bone("Head")', self.visual)
        self.assertIn('set_bone_pose_scale(head_index, Vector3(0.001, 0.001, 0.001))', self.visual)
        self.assertIn('visual.call("set_first_person_view", camera_view_mode == "first_person")', read("player.gd"))
        self.assertIn("first_person_body=true", self.smoke)

    def test_battle_royale_parachute_animation_states_are_bound_and_smoked(self):
        for clip in ("Skydive (free fall)", "Activate parachute (deploy)", "Use parachute (glide)", "Land parachute"):
            self.assertIn(clip, self.visual)
        for phase in ("freefall", "deploying", "gliding", "landing"):
            self.assertIn(f'"{phase}"', self.smoke)

    def test_android_pipeline_fetches_the_validated_artifact_for_current_parameter_revision(self):
        self.assertIn("workflow_id == 417330351", self.android)
        self.assertIn("actions/runs?head_sha=$PROFILE_COMMIT&per_page=100", self.android)
        self.assertNotIn("actions/workflows/ara-operator-assets.yml/runs", self.android)
        self.assertIn("actions/download-artifact@v4", self.android)
        self.assertIn("A-Square-Ara3D-Operator-Candidates", self.android)
        self.assertIn('installed = high_dir / "a_square_bangladesh_operator.glb"', self.android)
        self.assertIn("tools/ara3d/asquare_operator.params.json", self.android)
        self.assertIn("ara_operator_runtime_smoke.gd", self.android)
        self.assertIn("ARA_STATUS=$?", self.android)

    def test_android_apk_requires_the_canonical_ara_glb_and_imported_scene(self):
        for marker in (
            "assets/external_content/ara3d_operator/ara_asset_manifest.json",
            "external_content/ara3d_operator/high/a_square_bangladesh_operator.glb",
            "ara_manifest.get(\"weapon_socket\") is not True",
            "a_square_bangladesh_operator.glb-",
            "Ara 3D operator imported scene is absent or empty",
        ):
            self.assertIn(marker, self.apk_verifier)
        self.assertIn("assets/external_content/ara3d_operator/ara_asset_manifest.json", self.core_verifier)

    def test_animation_lookup_dictionary_has_no_duplicate_state_keys(self):
        start = self.visual.index("_authored_animation_lookup = {")
        end = self.visual.index("\n    }", start)
        dictionary = self.visual[start:end]
        import re
        keys = re.findall(r'^\s*"([^"]+)"\s*:', dictionary, re.MULTILINE)
        self.assertEqual(len(keys), len(set(keys)), f"duplicate animation state keys: {keys}")

    def test_ara_action_names_match_the_generated_glb_clip_labels(self):
        for clip in (
            "Hit reaction", "Pick up (ground)", "Open door", "Throw grenade",
            "Take cover", "Vault over obstacle", "Climb up ledge",
            "Swim forward (front crawl)", "Drive car", "Drive modern sports car",
            "Drive SUV", "Board sports car (driver)", "Alight from sports car (driver)",
            "Skydive (free fall)", "Activate parachute (deploy)",
            "Use parachute (glide)", "Land parachute",
        ):
            self.assertIn(clip, self.visual)

    def test_ci_renders_reviewable_blender_previews_for_all_operator_lods(self):
        self.assertIn("source tools/install_blender_ci.sh", self.asset_workflow)
        self.assertIn("render_operator_contact_sheet.py", self.asset_workflow)
        self.assertIn("build/ara_operator/previews/*.png", self.asset_workflow)
        self.assertIn("bpy.ops.import_scene.gltf", self.preview_script)
        self.assertIn("operator_lod_front.png", self.preview_script)
        self.assertIn("operator_lod_three_quarter.png", self.preview_script)
        self.assertIn("ARA_OPERATOR_PREVIEW_PASS", self.preview_script)
        self.assertIn("PREVIEW_RENDERED_NOT_ART_APPROVED", self.preview_script)

    def test_runtime_smoke_covers_rig_textures_weapon_and_real_animation(self):
        for marker in ("ARA3D_RUNTIME_PASS", "RightHand", "WeaponR", "textured_surface_count", "LOOP_LINEAR", "first_person_body=true", "BR_parachute_states=true"):
            self.assertIn(marker, self.smoke)
        self.assertTrue(self.profile["animations"])
        self.assertEqual(self.profile["detail"], "high")


if __name__ == "__main__":
    unittest.main()
