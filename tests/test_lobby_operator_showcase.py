import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def function_block(source: str, function_name: str) -> str:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"func {function_name}(")), -1)
    if start < 0:
        raise AssertionError(f"Missing GDScript function: {function_name}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("func "):
        end += 1
    return "\n".join(lines[start:end])


class LobbyOperatorShowcaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hud = read("hud.gd")
        cls.showcase = read("systems/lobby_showcase.gd")
        cls.visual = read("character_visual.gd")
        cls.boot = read("boot.gd")
        cls.profile = read("career_profile.gd")


    def test_godot_validation_job_has_one_unambiguous_timeout(self):
        workflow = read(".github/workflows/validate-godot.yml")
        match = re.search(
            r"(?ms)^  validate:\n(?P<job>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
            workflow,
        )
        self.assertIsNotNone(match, "Missing Godot validation job")
        timeout_values = re.findall(
            r"(?m)^    timeout-minutes:\s*(\d+)\s*$",
            match.group("job"),
        )
        self.assertEqual(["40"], timeout_values)

    def test_graphics_presets_apply_mobile_renderer_controls(self):
        settings = function_block(self.hud, "_apply_quality")
        fps = function_block(self.hud, "_apply_fps")
        for token in (
            "viewport.scaling_3d_scale = scales[profile]",
            "viewport.msaa_3d = msaa_modes[profile]",
            "Viewport.MSAA_DISABLED",
            "Viewport.MSAA_2X",
            "Viewport.MSAA_4X",
            "sun.shadow_enabled = shadows_enabled",
            "sun.directional_shadow_max_distance = shadow_distances[profile]",
            "environment.fog_enabled = profile >= 1",
            "environment.glow_enabled = glow_enabled",
            "environment.glow_hdr_threshold = 0.9",
        ):
            self.assertIn(token, settings)
        self.assertIn("Engine.max_fps = limits[clampi(index, 0, 5)]", fps)
        self.assertIn("[30, 60, 90, 120, 144, 0]", fps)
        self.assertIn("Mobile", settings)

    def test_boot_has_animated_intro_local_guest_login_and_verified_map_handoff(self):
        for token in (
            "BOOT_SPLASH_DURATION_SECONDS",
            "func _run_boot_sequence()",
            "func _create_intro_overlay()",
            "func _show_guest_login_screen()",
            "CONTINUE AS GUEST",
            "ONLINE SIGN-IN IS NOT CONNECTED IN THIS BUILD",
            "user://a_square_guest_profile.json",
            "_show_map_install_screen()",
            "WSB_AUTOSTART_MAP_FOR_SMOKE",
        ):
            self.assertIn(token, self.boot)
        self.assertIn("create_tween()", self.boot)
        self.assertIn('login_overlay.name = "LocalGuestLogin"', self.boot)
        self.assertIn("func _load_guest_identity() -> Dictionary:", self.boot)
        self.assertIn("profile_type", self.boot)
        self.assertIn("func get_display_name() -> String:", self.profile)
        self.assertIn('profile.call("get_display_name")', self.hud)
        # The existing split-PCK installer remains the verified map-entry route.
        self.assertIn("func _verify_and_install_pack() -> bool:", self.boot)
        self.assertIn("expected_sha256", self.boot)

    def test_home_has_one_prominent_play_now_entry(self):
        home = function_block(self.hud, "_show_lobby_page")
        featured = function_block(self.hud, "_lobby_add_featured_play")
        self.assertIn('_lobby_add_featured_play()', home)
        self.assertIn('button.name = "FeaturedPlayNow"', featured)
        self.assertIn('button.pressed.connect(_show_lobby_page.bind("play"))', featured)
        self.assertIn('Vector2(0.0, 94.0)', featured)

    def test_primary_play_navigation_is_visually_prominent(self):
        lobby = function_block(self.hud, "_build_lobby_ui")
        self.assertIn('var is_play_navigation := page_id == "play"', lobby)
        self.assertIn('60.0 if is_play_navigation else 48.0', lobby)
        self.assertIn('17 if is_play_navigation else 14', lobby)
        self.assertIn('lobby_nav_buttons[page_id] = button', lobby)

    def test_navigation_selection_tracks_the_current_lobby_page(self):
        page = function_block(self.hud, "_show_lobby_page")
        lobby = function_block(self.hud, "_build_lobby_ui")
        self.assertIn('nav_button.button_pressed = String(page_id) == page', page)
        self.assertIn('button.toggle_mode = true', self.hud)
        self.assertIn('button.icon = load(String(item[2])) as Texture2D', lobby)
        self.assertIn('button.tooltip_text = String(item[0]).capitalize()', lobby)
        for icon_name in ("home", "play", "loadout", "operator", "events", "store", "clan", "profile"):
            self.assertIn(f'"res://assets/ui/icons/{icon_name}.svg"', lobby)
            icon_path = ROOT / "assets" / "ui" / "icons" / f"{icon_name}.svg"
            self.assertTrue(icon_path.is_file(), f"Missing lobby navigation icon: {icon_name}")
            icon = icon_path.read_text(encoding="utf-8")
            self.assertIn('viewBox="0 0 64 64"', icon)
            self.assertIn("<path", icon)

    def test_operator_page_exposes_live_appearance_presets_on_player_visual(self):
        operator_page = function_block(self.hud, "_show_lobby_page")
        selector = function_block(self.hud, "_select_operator_preset")
        visual = read("character_visual.gd")
        self.assertIn('elif page == "operator":', operator_page)
        for preset in ("field_tactical", "urban_patrol", "civilian_explorer"):
            self.assertIn(preset, operator_page)
            self.assertIn(preset, visual)
        self.assertIn('operator_visual.call("apply_operator_preset", preset_id)', selector)
        self.assertIn('layer_root.visible = not (String(layer_name) == "clothing_jacket" and not jacket_visible)', visual)
        self.assertIn('func get_operator_preset_name() -> String:', visual)
        self.assertIn("Separate selectable body models", operator_page)

    def test_showcase_is_live_godot_geometry_not_a_baked_background(self):
        self.assertIn('CylinderMesh.new()', self.showcase)
        self.assertIn('TorusMesh.new()', self.showcase)
        self.assertIn('SpotLight3D.new()', self.showcase)
        self.assertIn('OmniLight3D.new()', self.showcase)
        self.assertNotIn('load("res://', self.showcase)
        self.assertNotIn('Texture2D', self.showcase)


    def test_lobby_requests_authored_idle_choreography_without_assuming_every_rig_has_each_clip(self):
        self.assertIn('LOBBY_IDLE_ACTIONS: Array[String] = ["idle_look", "idle_fidget", "idle_breathe"]', self.showcase)
        action_request = function_block(self.showcase, "_request_next_lobby_idle_action")
        self.assertIn('has_method("play_action")', action_request)
        self.assertIn('call("play_action", action_name)', action_request)
        self.assertIn("== true:", action_request)
        process = function_block(self.showcase, "_process")
        self.assertIn("_request_next_lobby_idle_action()", process)
        self.assertIn('"idle_look"', read("character_visual.gd"))
        self.assertIn('"idle_fidget"', read("character_visual.gd"))
        self.assertIn('"idle_breathe"', read("character_visual.gd"))

    def test_authored_locomotion_uses_per_operator_ground_and_aim_blend_spaces(self):
        builder = function_block(self.visual, "_build_authored_locomotion_blend_space")
        ground_setter = function_block(self.visual, "_set_authored_locomotion_blend")
        aim_setter = function_block(self.visual, "_set_authored_aim_blend")
        updater = function_block(self.visual, "_update_authored_animation")
        self.assertIn("AnimationNodeBlendSpace1D.new()", builder)
        self.assertIn("ground_space.sync = true", builder)
        self.assertIn("AnimationNodeBlendSpace2D.new()", builder)
        self.assertIn("aim_space.sync = true", builder)
        self.assertIn("AnimationNodeStateMachine.new()", builder)
        self.assertIn('state_machine.add_node("GroundLocomotion", ground_space', builder)
        self.assertIn('state_machine.add_node("AimLocomotion", aim_space', builder)
        self.assertIn('state_machine.add_transition("GroundLocomotion", "AimLocomotion"', builder)
        self.assertIn('state_machine.add_transition("AimLocomotion", "GroundLocomotion"', builder)
        self.assertIn('get_path_to(_authored_animation_player)', builder)
        self.assertIn('parameters/Locomotion/GroundLocomotion/blend_position', ground_setter)
        self.assertIn('clampf(planar_speed, 0.0, _authored_locomotion_blend_max_speed)', ground_setter)
        self.assertIn('parameters/Locomotion/AimLocomotion/blend_position', aim_setter)
        self.assertIn('global_basis.orthonormalized()', aim_setter)
        self.assertIn('facing_basis.inverse()', aim_setter)
        self.assertIn('Vector2(local_velocity.x, -local_velocity.z)', aim_setter)
        self.assertIn('_set_authored_locomotion_blend(planar_speed)', updater)
        self.assertIn('_set_authored_aim_blend(body)', updater)
        self.assertIn('requested_action.is_empty()', updater)
        self.assertIn('_authored_locomotion_tree.active = false', function_block(self.visual, "_play_authored_animation"))

    def test_showcase_and_player_visual_continue_while_tree_is_paused(self):
        self.assertIn('process_mode = Node.PROCESS_MODE_ALWAYS', self.showcase)
        self.assertIn('func _process(delta: float)', self.showcase)
        self.assertIn('_player.call("_update_camera")', self.showcase)
        self.assertIn('CHARACTER_IDLE_SWAY_RADIANS', self.showcase)

    def test_showcase_is_created_after_world_player_spawn(self):
        process = function_block(self.hud, "_process")
        ensure = function_block(self.hud, "_ensure_lobby_showcase")
        self.assertIn('_ensure_lobby_showcase()', process)
        self.assertIn('is_instance_valid(w.player)', ensure)
        self.assertIn('get_node_or_null("HumanoidVisual")', ensure)
        self.assertIn('lobby_showcase.call("configure", w.player)', ensure)

    def test_player_is_stopped_before_lobby_stage_takes_over(self):
        freeze = function_block(self.hud, "_freeze_player_for_lobby")
        self.assertIn('stopped_velocity.x = 0.0', freeze)
        self.assertIn('stopped_velocity.z = 0.0', freeze)
        self.assertIn('_freeze_player_for_lobby()', function_block(self.hud, "_show_mode_lobby"))
        self.assertIn('_freeze_player_for_lobby()', function_block(self.hud, "_check_combat_result"))

    def test_showcase_is_hidden_when_gameplay_resumes_and_restored_for_results(self):
        self.assertIn('lobby_showcase.call("configure", w.player)', self.hud)
        self.assertIn('lobby_showcase.call("set_enabled", true)', function_block(self.hud, "_show_mode_lobby"))
        self.assertIn('lobby_showcase.call("set_enabled", true)', function_block(self.hud, "_check_combat_result"))
        self.assertIn('lobby_showcase.call("set_enabled", false)', function_block(self.hud, "_complete_enter_selected_mode"))
        self.assertIn('lobby_showcase.call("set_enabled", false)', function_block(self.hud, "_replay_combat_round"))


    def test_login_can_open_base_lobby_without_waiting_for_optional_district_pack(self):
        refresh = function_block(self.boot, "_refresh_pack_state")
        enter = function_block(self.boot, "_enter_world")
        transition = function_block(self.boot, "_create_loading_transition")
        self.assertIn("enter_button.disabled = false", refresh)
        self.assertIn("ENTER BASE LOBBY", refresh)
        self.assertIn("district_ready := _is_local_pack_ready()", enter)
        self.assertIn("_create_loading_transition(district_ready)", enter)
        self.assertIn("get_tree().change_scene_to_file", enter)
        self.assertIn("STARTING BASE WORLD", transition)

    def test_lobby_mode_cards_have_editorial_hierarchy_and_real_callbacks(self):
        grid = function_block(self.hud, "_lobby_add_mode_grid")
        home = function_block(self.hud, "_show_lobby_page")
        self.assertIn("GridContainer.new()", grid)
        self.assertIn("ModeCard_%02d", grid)
        self.assertIn("eyebrow.text", grid)
        self.assertIn("title.text", grid)
        self.assertIn("detail.text", grid)
        self.assertIn("card.pressed.connect(callback)", grid)
        self.assertIn("JIBONJATRA", home)
        self.assertIn("DESHI STORIES", home)
        self.assertIn("BATTLE ROYALE", home)

    def test_operator_stage_uses_layered_art_direction_and_tweened_camera_passes(self):
        stage = function_block(self.showcase, "_build_stage")
        choreography = function_block(self.showcase, "_start_cinematic_choreography")
        process = function_block(self.showcase, "_process")
        for token in ("HeroBackdrop", "PortalLeftPillar", "PortalRightPillar", "PortalCrown", "DeckOuterBrassInlay", "LobbyBrandMark", "WarmShoulderRim", "CoolShoulderRim"):
            self.assertIn(token, stage)
        self.assertIn("Tween.TRANS_CUBIC", choreography)
        self.assertIn("Tween.TRANS_LINEAR", choreography)
        self.assertIn("_start_cinematic_choreography()", function_block(self.showcase, "set_enabled"))
        self.assertNotIn("sin(_elapsed * 0.22)", process)
        self.assertIn("_request_next_lobby_idle_action()", process)


if __name__ == "__main__":
    unittest.main()
