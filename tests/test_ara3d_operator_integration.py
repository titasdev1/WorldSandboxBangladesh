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


def function_block(source: str, function_name: str) -> str:
    """Return one GDScript function, stopping before the next top-level func."""
    marker = f"func {function_name}("
    start = source.index(marker)
    end = source.find("\nfunc ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


class AraOperatorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visual = read("character_visual.gd")
        cls.apk_verifier = read("tools/verify_apk_contents.py")
        cls.core_verifier = read("tools/verify_core_apk_contents.py")
        cls.android = read(".github/workflows/android.yml")
        cls.smoke = read("tests/ara_operator_runtime_smoke.gd")
        cls.profile = json.loads(read("tools/ara3d/asquare_operator.params.json"))
        cls.roster = json.loads(read("tools/ara3d/roster.json"))
        cls.asset_workflow = read(".github/workflows/ara-operator-assets.yml")
        cls.preview_script = read("tools/ara3d/render_operator_contact_sheet.py")

    def test_validated_ara_glb_is_preferred_over_older_humanoid_candidates(self):
        self.assertIn('const ARA_HERO_PATH := "res://external_content/ara3d_operator/high/a_square_bangladesh_operator.glb"', self.visual)
        choose = block(self.visual, "func _try_load_authored_hero()", "func _begin_staged_authored_hero_load()")
        self.assertLess(choose.index("ResourceLoader.exists(ARA_HERO_PATH)"), choose.index("ResourceLoader.exists(CHARACTER_CREATOR_HERO_PATH)"))
        self.assertIn('_authored_hero_source = "Ara3D"', choose)

    def test_locomotion_blend_spaces_are_read_from_nested_state_machine(self):
        builder = function_block(self.visual, "_build_authored_locomotion_blend_space")
        hero_loader = function_block(self.visual, "_build_authored_hero")
        self.assertIn("AnimationNodeBlendTree.new()", builder)
        self.assertIn('blend_tree.add_node("Locomotion", state_machine', builder)
        self.assertIn("var layered_root := _authored_locomotion_tree.tree_root as AnimationNodeBlendTree", hero_loader)
        self.assertIn('layered_root.get_node("Locomotion") as AnimationNodeStateMachine', hero_loader)
        self.assertIn('locomotion_machine.get_node("GroundLocomotion")', hero_loader)
        self.assertIn('locomotion_machine.get_node("AimLocomotion")', hero_loader)
        self.assertNotIn("_authored_locomotion_tree.tree_root as AnimationNodeStateMachine", hero_loader)

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
        self.assertIn("contents/tools/ara3d/roster.json", self.android)
        self.assertIn("roster_blob_sha=$CURRENT_ROSTER_SHA", self.android)
        self.assertIn("actions/runs?branch=${BRANCH}&per_page=100", self.android)
        self.assertNotIn("actions/workflows/ara-operator-assets.yml/runs", self.android)
        self.assertIn("actions/download-artifact@v4", self.android)
        self.assertIn("A-Square-Ara3D-Operator-Candidates", self.android)
        self.assertIn('legacy_target = high_dir / "a_square_bangladesh_operator.glb"', self.android)
        self.assertIn("tools/ara3d/roster.json", self.android)
        self.assertIn("verify_ara_roster.py", self.android)
        self.assertIn("roster_manifest.json", self.android)
        self.assertIn("roster_dir / f\"{operator_id}.glb\"", self.android)
        self.assertIn("three independently rigged high-detail Ara operators", self.android)
        self.assertIn("ara_operator_runtime_smoke.gd", self.android)
        self.assertIn("ARA_STATUS=$?", self.android)

    def test_roster_defines_three_unique_operator_profiles_and_runtime_glb_paths(self):
        self.assertEqual(3, self.roster["required_operator_count"])
        self.assertEqual(3, len(self.roster["operators"]))
        operator_ids = [item["id"] for item in self.roster["operators"]]
        self.assertEqual(3, len(set(operator_ids)))
        for operator_id in ("field_ranger", "delta_recon", "river_scout"):
            profile = json.loads(read(f"tools/ara3d/profiles/{operator_id}.json"))
            self.assertEqual(f"asquare_operator_{operator_id}", profile["name"])
            self.assertTrue(profile["animations"])
            self.assertEqual("high", profile["detail"])
            self.assertIn(f'res://external_content/ara3d_operator/roster/{operator_id}.glb', self.visual)
        self.assertIn("geometry_signature(path", read("tools/ara3d/verify_ara_roster.py"))
        self.assertIn("geometry_signatures_unique", read("tools/ara3d/verify_ara_roster.py"))

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
        self.assertIn('for OPERATOR_ID in field_ranger delta_recon river_scout', self.asset_workflow)
        self.assertIn("build/ara_operator/*/previews/*.png", self.asset_workflow)
        self.assertIn("verify_ara_roster.py", self.asset_workflow)
        self.assertIn("bpy.ops.import_scene.gltf", self.preview_script)
        self.assertIn("operator_lod_front.png", self.preview_script)
        self.assertIn("operator_lod_three_quarter.png", self.preview_script)
        self.assertIn("ARA_OPERATOR_PREVIEW_PASS", self.preview_script)
        self.assertIn("PREVIEW_RENDERED_NOT_ART_APPROVED", self.preview_script)
        self.assertIn("A-Square-Ara3D-Operator-Candidates", self.asset_workflow)



    def test_rifle_fire_is_a_filtered_upper_body_oneshot_over_locomotion(self):
        builder = function_block(self.visual, "_build_authored_locomotion_blend_space")
        fire_request = function_block(self.visual, "_request_authored_fire_layer")
        updater = function_block(self.visual, "_update_authored_animation")
        self.assertIn("AnimationNodeBlendTree.new()", builder)
        self.assertIn("AnimationNodeOneShot.new()", builder)
        self.assertIn("fire_overlay.filter_enabled = true", builder)
        self.assertIn("fire_overlay.set_filter_path(track_path, true)", builder)
        self.assertIn('blend_tree.connect_node("RifleFire", 0, "Locomotion")', builder)
        self.assertIn('blend_tree.connect_node("RifleFire", 1, "RifleFireClip")', builder)
        self.assertIn('blend_tree.connect_node("output", 0, "RifleFire")', builder)
        self.assertIn("parameters/RifleFire/request", fire_request)
        self.assertIn("parameters/RifleFire/active", fire_request)
        self.assertIn("_request_authored_fire_layer()", updater)
        self.assertIn("not _authored_fire_layer_ready", updater)
        self.assertIn("fire_overlay.is_path_filtered(track_path)", self.smoke)
        self.assertIn("parameters/Locomotion/GroundLocomotion/blend_position", self.smoke)

    def test_aiming_uses_camera_relative_2d_directional_locomotion(self):
        self.assertIn("AnimationNodeStateMachine.new()", self.visual)
        self.assertIn("AnimationNodeBlendSpace2D.new()", self.visual)
        self.assertIn("AnimationNodeBlendTree.new()", self.visual)
        self.assertIn('state_machine.add_node("GroundLocomotion", ground_space', self.visual)
        self.assertIn('state_machine.add_node("AimLocomotion", aim_space', self.visual)
        self.assertIn('state_machine.add_transition("GroundLocomotion", "AimLocomotion"', self.visual)
        self.assertIn('state_machine.add_transition("AimLocomotion", "GroundLocomotion"', self.visual)
        self.assertIn("var facing_basis := global_basis.orthonormalized()", self.visual)
        self.assertIn("var local_velocity := facing_basis.inverse() * Vector3(body.velocity.x, 0.0, body.velocity.z)", self.visual)
        self.assertIn("Vector2(local_velocity.x, -local_velocity.z)", self.visual)
        self.assertIn("parameters/Locomotion/AimLocomotion/blend_position", self.visual)
        self.assertIn("parameters/Locomotion/GroundLocomotion/blend_position", self.visual)
        for state in ("strafe_left", "strafe_right", "walk_back", "aim_walk"):
            self.assertIn(f'"{state}"', self.visual)
        for direction in ("Vector2(-1.0, 0.0)", "Vector2(1.0, 0.0)", "Vector2(0.0, 1.0)", "Vector2(0.0, -1.0)"):
            self.assertIn(direction, self.visual)
        self.assertIn('"AimLocomotion"', self.smoke)
        self.assertIn('"backward"', self.smoke)
        self.assertIn("parameters/Locomotion/AimLocomotion/blend_position", self.smoke)


    def test_directional_state_transition_smoke_advances_animation_tree_deterministically(self):
        self.assertIn("AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL", self.smoke)
        self.assertIn("locomotion_tree.advance(1.0 / 60.0)", self.smoke)
        self.assertIn("get_fading_from_node()", self.smoke)
        self.assertIn("get_travel_path()", self.smoke)
        self.assertIn("for frame_index in range(18)", self.smoke)
    def test_directional_blend_smoke_allows_small_exponential_filter_residual(self):
        self.assertIn("absf(actual_aim_blend.x - aim_case[1].x) > 0.0001", self.smoke)
        self.assertIn("absf(actual_aim_blend.y - aim_case[1].y) > 0.0001", self.smoke)

    def test_state_machine_smoke_settles_each_crossfade_before_reversing(self):
        travel = block(self.visual, "func _travel_authored_locomotion_state", "func _set_authored_locomotion_blend")
        self.assertIn("get_current_node()", travel)
        self.assertIn("current_state.is_empty()", travel)
        self.assertIn("playback.start(state_name)", travel)
        self.assertIn("playback.travel(state_name)", travel)
        self.assertIn("get_fading_from_node()", self.smoke)
        self.assertIn("aim_transition_settled", self.smoke)
        self.assertIn("reached_ground", self.smoke)
        self.assertIn("visual.set_process(false)", self.smoke)
    def test_runtime_smoke_covers_rig_textures_weapon_and_real_animation(self):
        for marker in ("ARA3D_RUNTIME_PASS", "RightHand", "WeaponR", "textured_surface_count", "LOOP_LINEAR", "first_person_body=true", "BR_parachute_states=true"):
            self.assertIn(marker, self.smoke)
        self.assertTrue(self.profile["animations"])
        self.assertEqual(self.profile["detail"], "high")


if __name__ == "__main__":
    unittest.main()
