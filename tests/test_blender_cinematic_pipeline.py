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
        self.assertIn('format = "MPEG4"', body)
        self.assertIn('codec = "H264"', body)
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


if __name__ == "__main__":
    unittest.main()
