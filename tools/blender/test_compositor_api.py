#!/usr/bin/env python3
"""Fast Blender 5.2 compositor API smoke test; no rendering or assets required."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import bpy


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "blender" / "build_login_lobby_environments.py"

spec = importlib.util.spec_from_file_location("asquare_blender_authoring", SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError("COMPOSITOR_SMOKE_GATE: cannot load Blender authoring module.")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def validate_profile(scene: bpy.types.Scene, warm: bool) -> None:
    module.configure_cinematic_compositor(scene, warm)
    tree = scene.compositing_node_group
    if tree is None:
        raise RuntimeError("COMPOSITOR_SMOKE_GATE: scene has no compositing node group.")
    required_types = {
        "CompositorNodeRLayers",
        "CompositorNodeColorBalance",
        "CompositorNodeGlare",
        "CompositorNodeLensdist",
        "CompositorNodeEllipseMask",
        "CompositorNodeBlur",
        "ShaderNodeValToRGB",
        "ShaderNodeMix",
        "NodeGroupOutput",
    }
    found = {node.bl_idname for node in tree.nodes}
    missing = sorted(required_types - found)
    if missing:
        raise RuntimeError(f"COMPOSITOR_SMOKE_GATE: missing node types: {missing}")
    output = next((node for node in tree.nodes if node.bl_idname == "NodeGroupOutput"), None)
    if output is None or output.inputs.get("Image") is None:
        raise RuntimeError("COMPOSITOR_SMOKE_GATE: Color Image output interface is missing.")
    if not any(link.to_node == output and link.to_socket.name == "Image" for link in tree.links):
        raise RuntimeError("COMPOSITOR_SMOKE_GATE: final image is not linked to Group Output.")
    if not scene.render.use_compositing:
        raise RuntimeError("COMPOSITOR_SMOKE_GATE: render.use_compositing is disabled.")
    print("COMPOSITOR_SMOKE_GATE:PASS", {
        "profile": scene.get("cinematic_grade_profile"),
        "node_group": tree.name,
        "node_count": len(tree.nodes),
        "link_count": len(tree.links),
        "blender_version": bpy.app.version_string,
    })


if tuple(bpy.app.version) < (5, 2, 0):
    raise RuntimeError(f"COMPOSITOR_SMOKE_GATE: expected Blender 5.2+, got {bpy.app.version_string}")

validate_profile(bpy.context.scene, True)
lobby_scene = bpy.data.scenes.new("A_Square_Compositor_Smoke_Lobby")
validate_profile(lobby_scene, False)
print("COMPOSITOR_SMOKE_GATE:ALL_PROFILES_PASS")
