#!/usr/bin/env python3
"""Source-level regression gates for the Blender cinematic authoring pipeline.

These tests intentionally parse the authoring source without importing bpy, so
they run in ordinary GitHub Actions Python before the paid/heavy Blender render.
They protect the exact bug that previously removed skinned imported operators.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

BUILDER = Path("tools/blender/build_login_lobby_environments.py")


def load_source() -> tuple[str, ast.Module, dict[str, ast.FunctionDef]]:
    source = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(BUILDER))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    return source, tree, functions


class CinematicPipelineRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source, cls.tree, cls.functions = load_source()

    def function_text(self, name: str) -> str:
        node = self.functions.get(name)
        self.assertIsNotNone(node, f"missing authoring function: {name}")
        return ast.get_source_segment(self.source, node) or ""

    def test_static_batching_never_merges_armature_deformed_meshes(self) -> None:
        body = self.function_text("consolidate_static_meshes")
        self.assertIn('"ARMATURE"', body)
        self.assertIn("deforming_modifier_types", body)
        self.assertIn("obj.data.shape_keys is not None", body)
        self.assertIn("under_armature", body)

    def test_triangulation_preserves_skinned_and_morph_target_meshes(self) -> None:
        body = self.function_text("triangulate_all_meshes")
        self.assertIn("obj.data.shape_keys is not None", body)
        self.assertIn('"ARMATURE"', body)
        self.assertIn("MESH_DEFORM", body)

    def test_each_operator_uses_only_its_imported_actions(self) -> None:
        body = self.function_text("add_operator_preview")
        self.assertIn("actions_before = set(bpy.data.actions)", body)
        self.assertIn("action not in actions_before", body)
        self.assertIn("imported_actions", body)
        self.assertIn("nla_tracks.new()", body)
        self.assertIn("strip.repeat", body)
        self.assertIn("bpy.context.scene.frame_end", body)
        self.assertNotIn("(scene.frame_end", body)

    def test_live_rig_gate_is_required_for_every_preview_actor(self) -> None:
        body = self.function_text("validate_preview_rigs")
        self.assertIn("wrapper.children_recursive", body)
        self.assertIn('modifier.type == "ARMATURE"', body)
        self.assertIn("raise RuntimeError", body)

    def test_mp4_render_is_a_real_animation_render_and_h264(self) -> None:
        body = self.function_text("render_film_preview")
        self.assertIn('file_format = "FFMPEG"', body)
        self.assertIn('media_type = "VIDEO"', body)
        self.assertIn('media_type = "IMAGE"', body)
        self.assertLess(body.index('media_type = "VIDEO"'), body.index('file_format = "FFMPEG"'))
        self.assertLess(body.index('media_type = "IMAGE"'), body.index('file_format = "PNG"'))
        self.assertIn('format = "MPEG4"', body)
        self.assertIn('codec = "H264"', body)
        self.assertIn("scene.render.resolution_percentage = 50", body)
        self.assertIn("EDITORIAL_PREVIEW_800x450", body)
        self.assertIn("eevee.taa_render_samples = 16", body)
        self.assertIn("scene.render.resolution_percentage = 75", body)
        self.assertIn("bpy.ops.render.render(animation=True)", body)
        self.assertIn("expected_output.stat().st_size < 100_000", body)

    def test_operators_render_before_they_are_removed_from_environment_glb(self) -> None:
        body = self.function_text("main")
        rig_gate = body.index("validate_preview_rigs(operator_previews)")
        film_render = body.index("render_film_preview(scene, args.film_output)")
        still_render = body.index("bpy.ops.render.render(write_still=True)")
        removal = body.index("remove_operator_preview(operator_preview)")
        export = body.index("bpy.ops.export_scene.gltf(")
        self.assertLess(rig_gate, film_render)
        self.assertLess(film_render, still_render)
        self.assertLess(still_render, removal)
        self.assertLess(removal, export)

    def test_login_and_lobby_use_distinct_character_performance_choices(self) -> None:
        login = self.function_text("build_login")
        lobby = self.function_text("build_lobby")
        self.assertIn('"Look around"', login)
        self.assertIn('"Rifle idle (low ready)"', lobby)
        self.assertIn('"Pistol idle (low ready)"', lobby)
        self.assertIn('"Look around"', lobby)


    def test_river_surface_is_tessellated_and_has_looped_shape_key_waves(self) -> None:
        body = self.function_text("river_plane")
        self.assertIn("mesh.from_pydata", body)
        self.assertIn("water.location = (0.0, y, 0.0)", body)
        self.assertIn("uv_layers.new", body)
        self.assertIn("shape_key_add", body)
        self.assertIn("River_Wave_Phase_", body)
        self.assertIn("key.keyframe_insert", body)
        self.assertIn("curve.modifiers.new(\"CYCLES\")", body)

    def test_water_shader_and_eevee_reflections_are_authored(self) -> None:
        reflection = self.function_text("configure_eevee_reflections")
        self.assertIn("use_raytracing = True", reflection)
        self.assertIn('ray_tracing_method = "SCREEN"', reflection)
        water = self.function_text("configure_river_water_material")
        self.assertIn("ShaderNodeTexWave", water)
        self.assertIn("ShaderNodeTexNoise", water)
        self.assertIn("ShaderNodeBump", water)
        self.assertIn('shader.inputs["IOR"].default_value = 1.333', water)



    def test_lobby_camera_portal_removes_obstructing_centre_glazing(self) -> None:
        body = self.function_text("build_lobby")
        self.assertIn('if abs(x) < 7.0:', body)
        self.assertIn('if abs(glass_x) <= 6.9:', body)
        self.assertIn('"Lobby_Hero_Portal_Header"', body)
        self.assertIn('"Lobby_Hero_Portal_Threshold"', body)
        self.assertIn("scene.camera = cam", body)

    def test_lobby_film_cuts_to_each_distinct_operator_portrait(self) -> None:
        helper = self.function_text("register_camera_cut")
        body = self.function_text("build_lobby")
        self.assertIn("scene.timeline_markers.new", helper)
        self.assertIn("marker.camera = camera_obj", helper)
        for marker_name in (
            "B1_COMMAND_HALL_ESTABLISHING",
            "B2_FIELD_RANGER_PORTRAIT",
            "B3_DELTA_RECON_PORTRAIT",
            "B4_RIVER_SCOUT_PORTRAIT",
            "B5_THREE_OPERATOR_GROUP",
            "B6_SELECTED_OPERATOR_HANDOFF",
        ):
            self.assertIn(marker_name, body)
        self.assertIn("Lobby_Field_Ranger_Portrait_Camera", body)
        self.assertIn("Lobby_Delta_Recon_Portrait_Camera", body)
        self.assertIn("Lobby_River_Scout_Portrait_Camera", body)
        self.assertIn("Lobby_Selected_Operator_Closeup_Camera", body)



    def test_login_film_has_five_distinct_editorial_shots(self) -> None:
        body = self.function_text("build_login")
        for marker_name in (
            "A1_SHARIATPUR_RIVER_ESTABLISHING",
            "A2_LOCAL_CNG_STREET_PORTRAIT",
            "A3_LAUNCH_WAKE_AND_REFLECTION",
            "A4_FIELD_RANGER_HUMAN_PORTRAIT",
            "A5_ORIGINAL_A_SQUARE_TITLE_REVEAL",
        ):
            self.assertIn(marker_name, body)
        self.assertIn("Login_CNG_Street_Portrait_Camera", body)
        self.assertIn("Login_Launch_Waterline_Camera", body)
        self.assertIn("Login_Field_Ranger_Portrait_Camera", body)
        self.assertIn("Login_A_Square_Title_Reveal_Camera", body)

    def test_login_reveals_original_delta_wordmark_and_tagline(self) -> None:
        body = self.function_text("build_login")
        self.assertIn('"ASQ_Delta_Emblem_Outer"', body)
        self.assertIn('"ASQ_Delta_River_Tributary_Left"', body)
        self.assertIn('"ASQ_Delta_River_Tributary_Right"', body)
        self.assertIn('wordmark_data.body = "A-SQUARE"', body)
        self.assertIn('tagline_data.body = "THE DELTA IS OUR WORLD"', body)
        self.assertIn('keyframe_insert(data_path="scale"', body)
        self.assertIn("face_operator_to_camera(operator_preview, ranger_cut)", body)



    def test_shariatpur_centre_store_is_a_custom_mesh_art_asset(self) -> None:
        body = self.function_text("add_crafted_riverfront_corner_store")
        self.assertIn("authored_xz_prism", body)
        self.assertIn("authored_xy_slab", body)
        self.assertIn("authored_lathe", body)
        self.assertIn("Curved_Balcony_Stone_Deck", body)
        self.assertIn("Forged_Balcony_Handrail", body)
        self.assertIn("Recessed_Arched_Shop_Window", body)
        self.assertIn("Deep_Interior_Back_Wall", body)
        self.assertIn("visible_interior", body)
        self.assertNotIn("box(", body)
        self.assertNotIn("cylinder(", body)
        self.assertNotIn("sphere(", body)

    def test_hero_store_replaces_the_centre_repeated_facade(self) -> None:
        body = self.function_text("build_login")
        self.assertIn("if i == 2:", body)
        self.assertIn("add_crafted_riverfront_corner_store", body)
        self.assertIn("Shariatpur_MixedUse_Block_", body)

    def test_hero_awning_has_cloth_topology_and_secondary_animation(self) -> None:
        body = self.function_text("add_crafted_riverfront_corner_store")
        self.assertIn("awning_cols, awning_rows = 28, 8", body)
        self.assertIn("Canvas_Gust_Anticipation", body)
        self.assertIn("breeze.keyframe_insert", body)
        self.assertIn('awning_obj.data.materials.append(mats["red"])', body)
        self.assertIn("polygon.material_index = 1 if column % 4 in (0, 1) else 0", body)
        self.assertIn("Awning_Stitched_Seam_", body)

    def test_hero_facade_has_true_openings_and_inhabited_roof_details(self) -> None:
        body = self.function_text("add_crafted_riverfront_corner_store")
        self.assertIn("include_front_face=False", body)
        self.assertIn("include_back_face=False", body)
        self.assertIn("Upper_Arched_Window_", body)
        self.assertIn("Interior_Wood_Shelf_", body)
        self.assertIn("Tea_Jar_", body)
        self.assertIn("Rice_Sack_", body)
        self.assertIn("Ribbed_Poly_Water_Tank", body)
        self.assertIn("Roof_Feed_Pipe", body)



    def test_hero_store_keeps_local_geometry_at_the_requested_block_coordinate(self) -> None:
        parent = self.function_text("set_parent_local")
        body = self.function_text("add_crafted_riverfront_corner_store")
        self.assertIn("obj.matrix_parent_inverse.identity()", parent)
        self.assertIn("return set_parent_local(obj, parent)", self.function_text("authored_mesh"))
        self.assertIn("local_path_curve(", body)
        self.assertIn('root["placement_rule"]', body)
        self.assertLess(body.index("arch_left = -2.12"), body.index("ground_panels = ["))



    def test_hero_awning_animation_supports_blender_52_layered_actions(self) -> None:
        body = self.function_text("add_crafted_riverfront_corner_store")
        self.assertIn("try:", body)
        self.assertIn("awning_curves = awning_action.fcurves", body)
        self.assertIn("except AttributeError:", body)
        self.assertIn("Blender layered Action; native shape-key interpolation retained.", body)
        self.assertIn("breeze.keyframe_insert", body)



    def test_cng_hero_is_built_from_authored_profiles_not_primitive_blocks(self) -> None:
        body = self.function_text("add_handcrafted_cng")
        self.assertIn("authored_xz_prism", body)
        self.assertIn("authored_xy_slab", body)
        self.assertIn("authored_mesh", body)
        self.assertIn("local_path_curve", body)
        self.assertNotIn("box(", body)
        self.assertNotIn("cylinder(", body)
        self.assertNotIn("sphere(", body)
        self.assertIn("Sculpted_Lower_Body_Shell", body)
        self.assertIn("Laminated_Windscreen", body)
        self.assertIn("Passenger_Footwell_Stamped_Floor", body)
        self.assertIn("Rear_Bench_Cushion", body)

    def test_cng_hero_has_three_custom_treaded_wheels_and_independent_axles(self) -> None:
        body = self.function_text("add_handcrafted_cng")
        self.assertIn('("Front", (1.10, 0.0, 0.375), True)', body)
        self.assertIn('("Rear_Near", (-0.91, -0.55, 0.375), False)', body)
        self.assertIn('("Rear_Far", (-0.91, 0.55, 0.375), False)', body)
        self.assertIn("make_treaded_tyre", body)
        self.assertIn("_Tread_Blocks", body)
        self.assertIn("tread_count = 44", body)
        self.assertIn("CNG_Front_Steering", body)
        self.assertIn("CNG_Suspension_Body_Performance", body)
        self.assertIn("name_text.location = (-0.24, 0.625, 0.85)", body)
        self.assertIn("name_text.rotation_euler = (-math.pi * 0.5, 0.0, 0.0)", body)

    def test_cng_canopy_has_custom_cloth_topology_and_gust_animation(self) -> None:
        body = self.function_text("add_handcrafted_cng")
        self.assertIn("canopy_cols, canopy_rows = 26, 12", body)
        self.assertIn("CNG_Canopy_Gust", body)
        self.assertIn("gust.keyframe_insert", body)
        self.assertIn("CNG_Canopy_Wind", body)
        self.assertIn("Canopy_Transverse_Bow_", body)
        self.assertIn("Canopy_Rear_Valance", body)

    def test_login_uses_handcrafted_cng_asset(self) -> None:
        body = self.function_text("build_login")
        self.assertIn('add_handcrafted_cng("Shariatpur_Emerald_CNG_Hero"', body)
        self.assertNotIn('add_cng("Shariatpur_Emerald_CNG"', body)



    def test_launch_hero_uses_variable_station_hull_and_authored_cabin(self) -> None:
        body = self.function_text("add_handcrafted_launch")
        self.assertIn("stations = [", body)
        self.assertIn("seven_variable_breadth_stations", body)
        self.assertIn("Lofted_Meghna_Hull", body)
        self.assertIn("Shaped_Deck_Planking", body)
        self.assertIn("Cabin_Laminated_Window_", body)
        self.assertIn("Cabin_Bow_Windscreen", body)
        self.assertIn("Cabin_Cambered_Roof", body)
        self.assertIn("Bow_Handrail_", body)
        self.assertIn("Propeller_Blade_", body)
        self.assertNotIn("box(", body)
        self.assertNotIn("cylinder(", body)
        self.assertNotIn("sphere(", body)

    def test_launch_buoyancy_and_propeller_have_separate_animation_tracks(self) -> None:
        body = self.function_text("add_handcrafted_launch")
        self.assertIn("Launch_Buoyancy_Performance", body)
        self.assertIn("Launch_Propeller_Performance", body)
        self.assertIn("Hull_Chine_Strake_", body)
        self.assertIn("Hull_Boot_Stripe_", body)
        self.assertIn("Hull_Rubber_Fender_", body)

    def test_launch_wake_is_a_following_surface_effect_not_world_origin_lines(self) -> None:
        wake = self.function_text("add_launch_wake")
        body = self.function_text("build_login")
        self.assertIn("Surface_Ribbon_", wake)
        self.assertIn("authored_mesh(", wake)
        self.assertIn('wake.shape_key_add(name="Stern_Turbulence"', wake)
        self.assertIn("Wake_Dissipation", wake)
        self.assertIn("Launch_Wake_Follows_Hull", wake)
        self.assertIn("motion: list[tuple[int, tuple[float, float, float]]]", wake)
        self.assertIn('add_launch_wake("River_Launch_Stern_Wake", launch_motion, mats)', body)
        self.assertNotIn("path_curve(", wake)



    def test_film_compositor_uses_blender_52_node_group_and_current_nodes(self) -> None:
        body = self.function_text("configure_cinematic_compositor")
        self.assertIn("scene.render.use_compositing = True", body)
        self.assertIn('bpy.data.node_groups.new("A_Square_Film_Compositor_" + profile, "CompositorNodeTree")', body)
        self.assertIn("scene.compositing_node_group = tree", body)
        self.assertIn('"CompositorNodeColorBalance"', body)
        self.assertIn('"CompositorNodeGlare"', body)
        self.assertIn('"CompositorNodeLensdist"', body)
        self.assertIn('"CompositorNodeEllipseMask"', body)
        self.assertIn('"CompositorNodeBlur"', body)
        self.assertIn('"ShaderNodeValToRGB"', body)
        self.assertIn('"ShaderNodeMix"', body)
        self.assertIn('"NodeGroupOutput"', body)
        self.assertNotIn("scene.node_tree", body)
        self.assertNotIn("scene.use_nodes", body)
        self.assertIn('links.new(multiply.outputs["Result"], output.inputs["Image"])', body)

    def test_compositor_smoke_script_checks_both_profiles_in_blender(self) -> None:
        script = Path("tools/blender/test_compositor_api.py").read_text(encoding="utf-8")
        self.assertIn("validate_profile(bpy.context.scene, True)", script)
        self.assertIn('validate_profile(lobby_scene, False)', script)
        self.assertIn("COMPOSITOR_SMOKE_GATE:ALL_PROFILES_PASS", script)
        self.assertIn('"NodeGroupOutput"', script)

    def test_login_and_lobby_lighting_both_apply_distinct_compositor_profiles(self) -> None:
        body = self.function_text("world_and_lighting")
        self.assertIn("configure_cinematic_compositor(scene, warm)", body)
        compositor = self.function_text("configure_cinematic_compositor")
        self.assertIn("SHARIATPUR_WARM_RIVER", compositor)
        self.assertIn("DELTA_COMMAND_COOL_GRAPHITE", compositor)
        self.assertIn('"Color Lift"', compositor)
        self.assertIn('"Color Gamma"', compositor)
        self.assertIn('"Color Gain"', compositor)



if __name__ == "__main__":
    unittest.main()
