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

    def test_boot_opens_the_lobby_before_optional_district_download(self):
        boot_flow = function_block(self.boot, "_run_boot_sequence")
        guest_handoff = function_block(self.boot, "_continue_as_guest")
        launch = function_block(self.boot, "_launch_main_lobby")
        project = read("project.godot")
        manager = read("systems/content_download_manager.gd")
        for token in (
            "BOOT_SPLASH_DURATION_SECONDS",
            "func _run_boot_sequence()",
            "func _create_intro_overlay()",
            "func _show_guest_login_screen()",
            "CONTINUE AS GUEST",
            "ONLINE SIGN-IN IS NOT CONNECTED IN THIS BUILD",
            "user://a_square_guest_profile.json",
            "WSB_AUTOSTART_MAP_FOR_SMOKE",
        ):
            self.assertIn(token, self.boot)
        self.assertIn('call_deferred("_launch_main_lobby")', boot_flow)
        self.assertIn("_launch_main_lobby()", guest_handoff)
        self.assertNotIn("_show_map_install_screen()", boot_flow)
        self.assertNotIn("_show_map_install_screen()", guest_handoff)
        self.assertIn('change_scene_to_file("res://Main.tscn")', launch)
        self.assertIn('[autoload]', project)
        self.assertIn('ContentDownloadManager="*res://systems/content_download_manager.gd"', project)
        self.assertIn("func get_shariatpur_state() -> Dictionary:", manager)
        self.assertIn("func start_shariatpur_download() -> bool:", manager)
        self.assertIn("_find_verified_resume_index()", manager)
        self.assertIn("_verify_and_append_part()", manager)
        self.assertIn("_verify_and_install_pack()", manager)
        self.assertIn("expected_sha256", manager)
        self.assertIn("create_tween()", self.boot)
        self.assertIn('login_overlay.name = "LocalGuestLogin"', self.boot)
        self.assertIn("func _load_guest_identity() -> Dictionary:", self.boot)
        self.assertIn("func get_display_name() -> String:", self.profile)
        self.assertIn('profile.call("get_display_name")', self.hud)

    def test_lobby_has_a_real_downloads_destination_and_resumable_map_action(self):
        lobby = function_block(self.hud, "_build_lobby_ui")
        pages = function_block(self.hud, "_show_lobby_page")
        downloads = function_block(self.hud, "_build_downloads_page")
        start = function_block(self.hud, "_start_shariatpur_download")
        restart = function_block(self.hud, "_restart_to_apply_shariatpur")
        self.assertIn('["DOWNLOADS", "downloads", "res://assets/ui/icons/downloads.svg"]', lobby)
        self.assertIn('elif page == "downloads":', pages)
        self.assertIn('ContentDownloadManager.get_shariatpur_state()', downloads)
        self.assertIn('Callable(self, "_start_shariatpur_download")', downloads)
        self.assertIn('Callable(self, "_restart_to_apply_shariatpur")', downloads)
        self.assertIn('ContentDownloadManager.start_shariatpur_download()', start)
        self.assertIn('change_scene_to_file("res://Main.tscn")', restart)
        icon_path = ROOT / "assets" / "ui" / "icons" / "downloads.svg"
        self.assertTrue(icon_path.is_file())
        self.assertIn('viewBox="0 0 64 64"', icon_path.read_text(encoding="utf-8"))

    def test_map_loader_waits_for_explicit_player_world_entry(self):
        loader = read("real_dhaka_tile_loader.gd")
        configure = function_block(loader, "configure")
        self.assertIn("waiting for explicit map entry", configure)
        self.assertIn("func start_map_streaming() -> void:", loader)
        self.assertIn('call_deferred("start_map_streaming")', configure)

    def test_home_has_one_prominent_play_now_entry(self):
        home = function_block(self.hud, "_show_lobby_page")
        featured = function_block(self.hud, "_lobby_add_featured_play")
        self.assertIn('_lobby_add_featured_play()', home)
        self.assertIn('button.name = "FeaturedPlayNow"', featured)
        self.assertIn('button.pressed.connect(_show_lobby_page.bind("play"))', featured)
        self.assertIn('Vector2(0.0, 94.0)', featured)

    def test_play_screen_uses_tiered_experience_cards_and_truthful_locked_modes(self):
        pages = function_block(self.hud, "_show_lobby_page")
        card = function_block(self.hud, "_lobby_add_experience_card")
        self.assertIn('elif page == "play":', pages)
        for title in ("JIBONJATRA", "DESHI STORIES", "CITY SANDBOX", "STREET LIFE", "LAST STAND", "COMBAT LAB", "STREET SKIRMISH", "SOLO DROP", "QUICK PLAY", "RANKED", "ZOMBIES"):
            self.assertIn('"' + title + '"', pages)
        self.assertIn('func _lobby_add_experience_grid() -> GridContainer:', self.hud)
        self.assertIn('grid.columns = 2', self.hud)
        self.assertIn('card.custom_minimum_size = Vector2(226.0 if compact else 0.0, 116.0 if compact else 126.0)', card)
        self.assertIn('action.disabled = not available', card)
        self.assertIn('action.text = "OPEN" if available else "LOCKED"', card)
        self.assertIn('if available and callback.is_valid():', card)

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
        for icon_name in ("home", "play", "downloads", "loadout", "operator", "events", "store", "clan", "profile"):
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
        self.assertIn("AUTHORED_COMMAND_HALL_PATH", self.showcase)
        self.assertIn("ResourceLoader.exists(AUTHORED_COMMAND_HALL_PATH)", self.showcase)
        self.assertIn("authored_pack.instantiate()", self.showcase)
        self.assertIn("func _play_authored_stage_animation()", self.showcase)
        self.assertIn("CylinderMesh.new()", self.showcase)  # procedural fallback remains
        self.assertNotIn("Texture2D", self.showcase)


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

    def test_command_hangar_has_authored_backdrop_panels_and_cinematic_lighting(self):
        for token in (
            "CommandHangarFloor",
            "HangarHeaderBeam",
            "RearCommandWall",
            "CommandDisplayGlass",
            "TelemetryPanel_",
            "VerticalHangarHalo",
            "WarmOperatorRim",
            "TelemetryScan",
            "RegionalMarkerGreen",
            "RegionalMarkerRed",
        ):
            self.assertIn(token, self.showcase)
        self.assertIn('_stage_timeline.name = "LobbyArtDirectionTimeline"', self.showcase)
        self.assertIn('animation.loop_mode = Animation.LOOP_LINEAR', self.showcase)
        self.assertIn('Animation.INTERPOLATION_CUBIC', self.showcase)
        self.assertIn('track_insert_key(track_index, keyframe.x, keyframe.y)', self.showcase)
        self.assertIn('_stage_timeline.play("lobby/PresentationIdle")', self.showcase)
        self.assertIn('_camera_timeline.name = "LobbyCameraDirector"', self.showcase)
        self.assertIn('_camera_timeline.root_node = NodePath("../../../Player")', self.showcase)
        self.assertIn('NodePath("camera_yaw")', self.showcase)
        self.assertIn('_camera_timeline.play("lobby/CameraHeroSweep")', self.showcase)
        self.assertIn("LOBBY_IDLE_ACTION_INTERVAL_SECONDS := 11.5", self.showcase)

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


    def test_blender_authored_hall_plays_animation_with_mobile_safe_lighting(self):
        stage = function_block(self.showcase, "_try_build_authored_command_hall")
        animator = function_block(self.showcase, "_play_authored_stage_animation")
        lights = function_block(self.showcase, "_build_authored_stage_lighting")
        self.assertIn("AUTHORED_COMMAND_HALL_PATH", stage)
        self.assertIn('find_child("ANIM | Operator halo outer"', stage)
        self.assertIn("authored_player.play(selected_name)", animator)
        self.assertIn("Animation.LOOP_LINEAR", animator)
        self.assertIn("_key_light.shadow_enabled = false", lights)
        self.assertIn("_fill_light.shadow_enabled = false", lights)
        self.assertIn("_rim_light.shadow_enabled = false", lights)


    def test_home_landing_uses_a_featured_deployment_and_experience_card_hierarchy(self):
        page = function_block(self.hud, "_show_lobby_page")
        home_start = page.index('if page == "home":')
        play_start = page.index('elif page == "play":', home_start)
        home = page[home_start:play_start]
        self.assertIn('_lobby_add_featured_play()', home)
        self.assertIn('var world_grid := _lobby_add_experience_grid()', home)
        self.assertIn('"JIBONJATRA"', home)
        self.assertIn('"DESHI STORIES"', home)
        self.assertIn('"CITY SANDBOX"', home)
        self.assertIn('"COMBAT LAB"', home)
        self.assertIn('"WORLD INTELLIGENCE"', home)
        self.assertIn('"No real-player server is connected', home)
        self.assertNotIn('_lobby_add_action("SHARIATPUR WORLD"', home)

    def test_lobby_page_sections_reveal_with_a_staggered_cinematic_fade(self):
        page = function_block(self.hud, "_show_lobby_page")
        reveal = function_block(self.hud, "_animate_lobby_page_reveal")
        self.assertIn("_animate_lobby_page_reveal()", page)
        self.assertIn('item.modulate.a = 0.0', reveal)
        self.assertIn('tween_property(item, "modulate:a", 1.0, 0.18)', reveal)
        self.assertIn('set_delay(minf(float(index) * 0.028, 0.22))', reveal)


if __name__ == "__main__":
    unittest.main()
