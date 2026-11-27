#!/usr/bin/env python3
"""Author original A-Square login and lobby environments in Blender 5.2.4.

Usage:
  blender --background --factory-startup --python tools/blender/build_login_lobby_environments.py -- --kind login --out build/lobby-art/login.glb --preview build/lobby-art/login.png
  blender --background --factory-startup --python tools/blender/build_login_lobby_environments.py -- --kind lobby --out build/lobby-art/lobby.glb --preview build/lobby-art/lobby.png

All meshes, materials and animation curves are authored in this repository.
No copied commercial-game assets, map-provider 3D tiles, logos or photographs
are embedded. This is an editable authored environment pass, not a claim of
photorealistic AAA completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import sys
from mathutils import Vector, Matrix, noise
import bmesh
import bpy


ROOT = pathlib.Path(__file__).resolve().parents[2]
LICENSE_TEXT = """PROJECT A-SQUARE ORIGINAL ENVIRONMENT ART
Assets: A-Square Shariatpur Riverside Login / Delta Command Lobby environments.
Authoring: Original Blender mesh, material, scene and animation scripts.
License: CC0 1.0 Universal for generated meshes, materials and animations.
No third-party meshes, photographs, game rips, logos, map-provider 3D tiles,
or restricted street-view imagery are included.
"""
METAL_DARK = (0.055, 0.080, 0.096, 1.0)
METAL_BLUE = (0.075, 0.155, 0.190, 1.0)
BRASS = (0.58, 0.37, 0.13, 1.0)
TEAL = (0.025, 0.27, 0.25, 1.0)
GLASS = (0.10, 0.28, 0.34, 1.0)
CONCRETE = (0.31, 0.34, 0.32, 1.0)
PAINT_CREAM = (0.66, 0.60, 0.47, 1.0)
RED = (0.54, 0.075, 0.045, 1.0)


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("login", "lobby"), required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    parser.add_argument("--film-output", type=pathlib.Path, help="Optional H.264 cinematic review film rendered with the actual rigged operators present.")
    parser.add_argument("--operator-glb", type=pathlib.Path, required=True, help="Exact roster-matched rigged Field Ranger GLB used for preview only.")
    parser.add_argument("--operator-glb-delta", type=pathlib.Path, help="Roster-matched Delta Recon high-LOD GLB for lobby review.")
    parser.add_argument("--operator-glb-river", type=pathlib.Path, help="Roster-matched River Scout high-LOD GLB for lobby review.")
    return parser.parse_args(argv)


def configure_eevee_reflections(scene: bpy.types.Scene) -> None:
    """Enable EEVEE screen-traced reflections for the authoring/review scene."""
    eevee = getattr(scene, "eevee", None)
    if eevee is None:
        scene["eevee_screen_space_reflections"] = False
        print("EEVEE_REFLECTIONS_WARNING: no EEVEE scene settings are available.")
        return
    try:
        eevee.use_raytracing = True
        eevee.ray_tracing_method = "SCREEN"
        scene["eevee_screen_space_reflections"] = True
        scene["eevee_reflection_method"] = "SCREEN_TRACE_WITH_PROBE_FALLBACK"
        print("EEVEE_REFLECTIONS_READY: screen-space ray tracing enabled.")
    except (AttributeError, TypeError, RuntimeError) as exc:
        scene["eevee_screen_space_reflections"] = False
        scene["eevee_reflection_warning"] = str(exc)
        print(f"EEVEE_REFLECTIONS_WARNING: {exc}")


def clear_scene() -> bpy.types.Scene:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 288
    scene.render.fps = 30
    scene.render.engine = "BLENDER_EEVEE"
    configure_eevee_reflections(scene)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    # A contact-sheet preview is intentionally lighter than the exported GLB.
    # It is for art-direction review, not final-resolution film rendering.
    scene.render.resolution_percentage = 75
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 24
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.15
    scene.view_settings.gamma = 1.0
    scene.camera = None
    return scene


def _pbr_bitmap_images(name: str, colour: tuple[float, float, float, float], scale: float) -> tuple[bpy.types.Image, bpy.types.Image, bpy.types.Image]:
    """Bake deterministic colour, roughness and tangent-normal bitmaps for glTF."""
    width = height = 128
    seed = sum(ord(char) for char in name) * 0.071
    heights: list[float] = []
    colour_pixels: list[float] = []
    rough_pixels: list[float] = []
    for y in range(height):
        v = y / max(1, height - 1)
        for x in range(width):
            u = x / max(1, width - 1)
            p = Vector((u * scale, v * scale, seed))
            broad = noise.noise(p)
            fine = noise.noise(Vector((u * scale * 5.3 + seed, v * scale * 5.3, seed * 0.37)))
            grain = noise.noise(Vector((u * scale * 18.0, v * scale * 18.0 + seed, seed * 0.61)))
            h = max(0.0, min(1.0, 0.50 + broad * 0.21 + fine * 0.11 + grain * 0.045))
            heights.append(h)
            tint = 0.76 + h * 0.42
            colour_pixels.extend((
                max(0.0, min(1.0, colour[0] * tint)),
                max(0.0, min(1.0, colour[1] * tint)),
                max(0.0, min(1.0, colour[2] * tint)),
                1.0,
            ))
            rough = max(0.05, min(1.0, 0.42 + fine * 0.18 + grain * 0.10))
            rough_pixels.extend((rough, rough, rough, 1.0))

    normal_pixels: list[float] = []
    strength = 2.8
    for y in range(height):
        for x in range(width):
            left = heights[y * width + max(0, x - 1)]
            right = heights[y * width + min(width - 1, x + 1)]
            down = heights[max(0, y - 1) * width + x]
            up = heights[min(height - 1, y + 1) * width + x]
            nx = -(right - left) * strength
            ny = -(up - down) * strength
            nz = 1.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            normal_pixels.extend((nx / length * 0.5 + 0.5, ny / length * 0.5 + 0.5, nz / length * 0.5 + 0.5, 1.0))

    images = []
    for suffix, pixels, colour_space in (
        ("BaseColor", colour_pixels, "sRGB"),
        ("Roughness", rough_pixels, "Non-Color"),
        ("Normal", normal_pixels, "Non-Color"),
    ):
        image = bpy.data.images.new(f"{name}_{suffix}", width=width, height=height, alpha=True, float_buffer=False)
        image.pixels.foreach_set(pixels)
        image.colorspace_settings.name = colour_space
        image.pack()
        images.append(image)
    return images[0], images[1], images[2]


POLYHAVEN_MANIFEST_PATH = ROOT / "external_content" / "polyhaven_pbr" / "asset_manifest.json"
_POLYHAVEN_MANIFEST: dict | None = None
_POLYHAVEN_IMAGE_CACHE: dict[str, bpy.types.Image] = {}


def _polyhaven_surface_for_material(name: str) -> str | None:
    value = name.lower()
    if "asphalt" in value or "road" in value or "pavement" in value:
        return "road"
    if "brick" in value or "masonry" in value:
        return "brick"
    if "concrete" in value or "stone" in value or "cement" in value:
        return "concrete"
    if "plaster" in value or "stucco" in value:
        return "plaster"
    if "metal" in value or "aluminium" in value or "aluminum" in value or "brass" in value or "shutter" in value:
        return "metal"
    if "wood" in value or "teak" in value or "bark" in value or "timber" in value:
        return "wood"
    if "mud" in value or "dirt" in value or "gravel" in value:
        return "ground"
    return None


def _polyhaven_manifest() -> dict:
    global _POLYHAVEN_MANIFEST
    if _POLYHAVEN_MANIFEST is not None:
        return _POLYHAVEN_MANIFEST
    try:
        if POLYHAVEN_MANIFEST_PATH.is_file():
            parsed = json.loads(POLYHAVEN_MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(parsed, dict) and parsed.get("available") is True and parsed.get("license") == "CC0-1.0":
                _POLYHAVEN_MANIFEST = parsed
                return parsed
    except (OSError, json.JSONDecodeError) as exc:
        print(f"POLYHAVEN_PBR_MANIFEST_WARNING: {exc}")
    _POLYHAVEN_MANIFEST = {}
    return _POLYHAVEN_MANIFEST


def _load_polyhaven_image(uri: str, colour_space: str) -> bpy.types.Image | None:
    if not uri.startswith("res://external_content/polyhaven_pbr/"):
        return None
    relative = uri.removeprefix("res://")
    image_path = ROOT / relative
    if not image_path.is_file():
        return None
    key = str(image_path.resolve())
    if key in _POLYHAVEN_IMAGE_CACHE:
        return _POLYHAVEN_IMAGE_CACHE[key]
    try:
        image = bpy.data.images.load(key, check_existing=True)
        image.colorspace_settings.name = colour_space
        image.pack()
        _POLYHAVEN_IMAGE_CACHE[key] = image
        return image
    except RuntimeError as exc:
        print(f"POLYHAVEN_PBR_IMAGE_WARNING: {image_path.name}: {exc}")
        return None


def _polyhaven_surface_record(name: str) -> dict:
    surface = _polyhaven_surface_for_material(name)
    surfaces = _polyhaven_manifest().get("surfaces", {})
    entry = surfaces.get(surface, {}) if isinstance(surfaces, dict) and surface else {}
    return entry if isinstance(entry, dict) else {}


def _all_used_polyhaven_sources() -> list[dict]:
    used: dict[str, dict] = {}
    for material_name in (
        "Asphalt_With_Fine_Aggregate", "Riverbank_Brickwork", "Cast_Stone_Concrete",
        "Weathered_Concrete", "Aged_Lime_Plasters", "Brushed_Antique_Brass",
        "Anodised_Aluminium", "Painted_Roller_Shutter", "Oiled_Teak",
        "Rain_Darkened_Bark",
    ):
        surface = _polyhaven_surface_for_material(material_name)
        entry = _polyhaven_surface_record(material_name)
        if surface and entry:
            used[surface] = {
                "asset_id": str(entry.get("asset_id", "")),
                "name": str(entry.get("name", "")),
                "source_url": str(entry.get("source_url", "")),
                "license": str(entry.get("license", "")),
                "maps": dict(entry.get("maps", {})),
            }
    return [{"surface": key, **value} for key, value in sorted(used.items())]


def material(
    name: str,
    colour: tuple[float, float, float, float],
    roughness: float = 0.65,
    metallic: float = 0.0,
    texture_scale: float = 0.0,
    bump_strength: float = 0.0,
    emission: float = 0.0,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = colour
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = 0.12 if metallic < 0.4 else 0.22
        shader.inputs["Coat Roughness"].default_value = 0.32
    if emission > 0.0:
        shader.inputs["Emission Color"].default_value = colour
        shader.inputs["Emission Strength"].default_value = emission
    if "Glass" in name or name.endswith("_Glass"):
        # Low-opacity, softly tinted glazing keeps the hall interior visible
        # while retaining enough reflection to read as architectural glass.
        if "Alpha" in shader.inputs:
            shader.inputs["Alpha"].default_value = 0.24
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        if hasattr(mat, "use_transparency_overlap"):
            mat.use_transparency_overlap = False
    if texture_scale > 0.0:
        # Always keep a generated fallback so the scene remains editable and
        # deterministic when the optional Poly Haven API is unavailable.
        fallback_base, fallback_rough, fallback_normal = _pbr_bitmap_images(name, colour, texture_scale)
        record = _polyhaven_surface_record(name)
        maps = record.get("maps", {}) if isinstance(record.get("maps", {}), dict) else {}
        base_image = _load_polyhaven_image(str(maps.get("albedo", "")), "sRGB") or fallback_base
        rough_image = _load_polyhaven_image(str(maps.get("roughness", "")), "Non-Color") or fallback_rough
        normal_image = _load_polyhaven_image(str(maps.get("normal", "")), "Non-Color") or fallback_normal
        metallic_image = _load_polyhaven_image(str(maps.get("metallic", "")), "Non-Color") if maps.get("metallic") else None
        ao_image = _load_polyhaven_image(str(maps.get("ao", "")), "Non-Color") if maps.get("ao") else None
        height_image = _load_polyhaven_image(str(maps.get("height", "")), "Non-Color") if maps.get("height") else None

        texcoord = nodes.new("ShaderNodeTexCoord")

        def add_image_node(label: str, image: bpy.types.Image) -> bpy.types.Node:
            image_node = nodes.new("ShaderNodeTexImage")
            image_node.label = label
            image_node.image = image
            image_node.interpolation = "Linear"
            links.new(texcoord.outputs["UV"], image_node.inputs["Vector"])
            return image_node

        base_node = add_image_node("PBR Base Colour", base_image)
        rough_node = add_image_node("PBR Roughness", rough_image)
        rough_sep = nodes.new("ShaderNodeSeparateColor")
        rough_sep.mode = "RGB"
        # Keep the chosen material palette visible while retaining real source
        # texture detail; otherwise one downloaded blue plaster map can flatten
        # every facade into nearly the same colour.
        tint_node = nodes.new("ShaderNodeRGB")
        tint_node.outputs["Color"].default_value = colour
        albedo_mix = nodes.new("ShaderNodeMixRGB")
        albedo_mix.blend_type = "MULTIPLY"
        albedo_mix.inputs["Fac"].default_value = 0.32
        links.new(base_node.outputs["Color"], albedo_mix.inputs["Color1"])
        links.new(tint_node.outputs["Color"], albedo_mix.inputs["Color2"])
        links.new(albedo_mix.outputs["Color"], shader.inputs["Base Color"])
        links.new(rough_node.outputs["Color"], rough_sep.inputs["Color"])
        links.new(rough_sep.outputs["Red"], shader.inputs["Roughness"])

        normal_node = add_image_node("PBR Tangent Normal", normal_image)
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.92
        links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])

        if metallic_image is not None:
            metal_node = add_image_node("PBR Metallic", metallic_image)
            metal_sep = nodes.new("ShaderNodeSeparateColor")
            metal_sep.mode = "RGB"
            links.new(metal_node.outputs["Color"], metal_sep.inputs["Color"])
            links.new(metal_sep.outputs["Red"], shader.inputs["Metallic"])

        if ao_image is not None:
            ao_node = add_image_node("PBR Ambient Occlusion", ao_image)
            ao_mix = nodes.new("ShaderNodeMixRGB")
            ao_mix.blend_type = "MULTIPLY"
            ao_mix.inputs["Fac"].default_value = 0.34
            links.new(albedo_mix.outputs["Color"], ao_mix.inputs["Color1"])
            links.new(ao_node.outputs["Color"], ao_mix.inputs["Color2"])
            links.new(ao_mix.outputs["Color"], shader.inputs["Base Color"])

        if height_image is not None and bump_strength > 0.0:
            height_node = add_image_node("PBR Height", height_image)
            height_sep = nodes.new("ShaderNodeSeparateColor")
            height_sep.mode = "RGB"
            bump = nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = min(0.22, bump_strength)
            bump.inputs["Distance"].default_value = 0.018
            links.new(height_node.outputs["Color"], height_sep.inputs["Color"])
            links.new(height_sep.outputs["Red"], bump.inputs["Height"])
            links.new(normal_map.outputs["Normal"], bump.inputs["Normal"])
            links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        else:
            links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])

        mat["pbr_source"] = str(record.get("source_url", "generated_mobile_fallback"))
        mat["pbr_license"] = str(record.get("license", "original_generated"))
        mat["pbr_channels"] = ",".join(sorted(maps.keys()))

    return mat

def set_parent(obj: bpy.types.Object, parent: bpy.types.Object | None) -> bpy.types.Object:
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def box(
    name: str,
    location: tuple[float, float, float],
    size: tuple[float, float, float],
    mat: bpy.types.Material,
    bevel: float = 0.025,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        mod = obj.modifiers.new(name + "_CraftedEdges", "BEVEL")
        mod.width = min(bevel, min(size) * 0.22)
        mod.segments = 3
        mod.profile = 0.5
        normal = obj.modifiers.new(name + "_WeightedNormals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
        normal.weight = 45
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=normal.name)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = False
    return set_parent(obj, parent)


def cylinder(
    name: str,
    location: tuple[float, float, float],
    radius: float,
    depth: float,
    mat: bpy.types.Material,
    vertices: int = 32,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    bevel = obj.modifiers.new(name + "_EdgeSoftening", "BEVEL")
    bevel.width = min(radius * 0.08, depth * 0.12)
    bevel.segments = 2
    normal = obj.modifiers.new(name + "_Normals", "WEIGHTED_NORMAL")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.modifier_apply(modifier=normal.name)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) <= 4
    return set_parent(obj, parent)


def sphere(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    mat: bpy.types.Material,
    segments: int = 20,
    rings: int = 12,
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = True
    return set_parent(obj, parent)


def path_curve(
    name: str,
    points: list[tuple[float, float, float]],
    mat: bpy.types.Material,
    radius: float,
    parent: bpy.types.Object | None = None,
    cyclic: bool = False,
) -> bpy.types.Object:
    data = bpy.data.curves.new(name + "_Spline", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 18
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    return set_parent(obj, parent)


def add_area_light(scene: bpy.types.Scene, name: str, location: tuple[float, float, float], target: tuple[float, float, float], power: float, colour: tuple[float, float, float], size: float) -> bpy.types.Object:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = colour
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def configure_cinematic_compositor(scene: bpy.types.Scene, warm: bool = True) -> None:
    """Author a Blender 5.2 compositor group for the riverfront and command hall.

    The grade is built from 5.2 node-group API and current node sockets:
    lift/gamma/gain, restrained highlight bloom, optical dispersion, and a
    feathered, shaped vignette. No deprecated Scene.node_tree API is used.
    """
    scene.render.use_compositing = True
    profile = "SHARIATPUR_WARM_RIVER" if warm else "DELTA_COMMAND_COOL_GRAPHITE"

    tree = bpy.data.node_groups.new("A_Square_Film_Compositor_" + profile, "CompositorNodeTree")
    scene.compositing_node_group = tree
    tree.interface.new_socket(
        name="Image",
        in_out="OUTPUT",
        socket_type="NodeSocketColor",
    )
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    def set_socket(node: bpy.types.Node, socket_name: str, value) -> bool:
        socket = node.inputs.get(socket_name)
        if socket is None:
            return False
        try:
            socket.default_value = value
            return True
        except (AttributeError, TypeError, ValueError) as exc:
            print("COMPOSITOR_SOCKET_NOTE:", json.dumps({
                "node": node.name,
                "socket": socket_name,
                "value": repr(value),
                "error": str(exc),
            }, sort_keys=True))
            return False

    render = nodes.new("CompositorNodeRLayers")
    render.name = "A_Square_Render_Layers"
    render.label = "Scene-linear render"
    render.location = (-1000, 240)

    balance = nodes.new("CompositorNodeColorBalance")
    balance.name = "A_Square_Film_Color_Balance"
    balance.label = "Warm delta / cool command grade"
    balance.location = (-760, 240)
    set_socket(balance, "Factor", 0.82)
    set_socket(balance, "Type", "Lift/Gamma/Gain")
    if warm:
        # Slight cyan bias in the deepest values, warm mid/highlight separation.
        set_socket(balance, "Base Lift", 0.005)
        set_socket(balance, "Color Lift", (0.985, 0.997, 1.018, 1.0))
        set_socket(balance, "Base Gamma", 1.0)
        set_socket(balance, "Color Gamma", (1.012, 1.002, 0.988, 1.0))
        set_socket(balance, "Base Gain", 1.0)
        set_socket(balance, "Color Gain", (1.035, 1.012, 0.982, 1.0))
    else:
        # Graphite/river-teal shadow separation; skin stays lit by warm practicals.
        set_socket(balance, "Base Lift", 0.008)
        set_socket(balance, "Color Lift", (0.978, 0.996, 1.025, 1.0))
        set_socket(balance, "Base Gamma", 1.0)
        set_socket(balance, "Color Gamma", (0.994, 1.004, 1.018, 1.0))
        set_socket(balance, "Base Gain", 1.0)
        set_socket(balance, "Color Gain", (1.012, 1.020, 1.035, 1.0))

    glow = nodes.new("CompositorNodeGlare")
    glow.name = "A_Square_Optical_Highlight_Glow"
    glow.label = "Restrained optical halation"
    glow.location = (-500, 240)
    set_socket(glow, "Type", "Fog Glow")
    set_socket(glow, "Quality", "High")
    set_socket(glow, "Highlights Threshold", 1.55 if warm else 1.75)
    set_socket(glow, "Highlights Smoothness", 0.18)
    set_socket(glow, "Clamp Highlights", True)
    set_socket(glow, "Maximum Highlights", 8.0)
    set_socket(glow, "Strength", 0.16 if warm else 0.12)
    set_socket(glow, "Saturation", 0.78)
    set_socket(glow, "Size", 0.24 if warm else 0.20)

    lens = nodes.new("CompositorNodeLensdist")
    lens.name = "A_Square_Optical_Lens_Finish"
    lens.label = "Near-invisible optical dispersion"
    lens.location = (-240, 240)
    set_socket(lens, "Type", "Radial")
    set_socket(lens, "Distortion", 0.0006)
    set_socket(lens, "Dispersion", 0.0012)
    set_socket(lens, "Jitter", False)
    set_socket(lens, "Fit", True)

    ellipse = nodes.new("CompositorNodeEllipseMask")
    ellipse.name = "A_Square_Lens_Vignette_Mask"
    ellipse.label = "Hand-shaped optical falloff"
    ellipse.location = (-500, -180)
    set_socket(ellipse, "Operation", "Add")
    set_socket(ellipse, "Value", 1.0)
    set_socket(ellipse, "Position", (0.5, 0.5))
    set_socket(ellipse, "Size", (0.87 if warm else 0.85, 0.90 if warm else 0.88))
    set_socket(ellipse, "Rotation", 0.0)

    blur = nodes.new("CompositorNodeBlur")
    blur.name = "A_Square_Vignette_Soften"
    blur.label = "Feathered vignette boundary"
    blur.location = (-240, -180)
    set_socket(blur, "Size", (120.0, 120.0))
    set_socket(blur, "Type", "Gaussian")
    set_socket(blur, "Separable", True)
    set_socket(blur, "Extend Bounds", True)

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.name = "A_Square_Vignette_Density"
    ramp.label = "Subtle edge density"
    ramp.location = (20, -160)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.905, 0.920, 0.945, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    ramp.color_ramp.interpolation = "EASE"

    multiply = nodes.new("ShaderNodeMix")
    multiply.name = "A_Square_Film_Vignette"
    multiply.label = "Optical edge density"
    multiply.location = (300, 240)
    multiply.data_type = "RGBA"
    multiply.blend_type = "MULTIPLY"
    multiply.clamp_factor = True
    multiply.clamp_result = True
    set_socket(multiply, "Factor", 0.72)
    
    output = nodes.new("NodeGroupOutput")
    output.name = "A_Square_Final_Composite"
    output.label = "Final film image"
    output.location = (580, 240)

    links.new(render.outputs["Image"], balance.inputs["Image"])
    links.new(balance.outputs["Image"], glow.inputs["Image"])
    links.new(glow.outputs["Image"], lens.inputs["Image"])
    links.new(ellipse.outputs["Mask"], blur.inputs["Image"])
    links.new(blur.outputs["Image"], ramp.inputs["Fac"])
    links.new(lens.outputs["Image"], multiply.inputs["A"])
    links.new(ramp.outputs["Color"], multiply.inputs["B"])
    links.new(multiply.outputs["Result"], output.inputs["Image"])

    scene["cinematic_compositor"] = "ASQ_FILM_GRADE_V2_BLENDER_52"
    scene["cinematic_grade_profile"] = profile
    scene["cinematic_compositor_nodes"] = len(nodes)
    scene["cinematic_optical_finish"] = (
        "AgX;lift_gamma_gain;fog_glow;subtle_lens_dispersion;"
        "gaussian_elliptical_vignette;Blender_5_2_node_group"
    )
    scene["cinematic_compositor_api"] = "scene.compositing_node_group"
    print("A_SQUARE_COMPOSITOR_READY:", json.dumps({
        "profile": profile,
        "node_group": tree.name,
        "nodes": len(nodes),
        "api": "scene.compositing_node_group",
        "glow_threshold": 1.55 if warm else 1.75,
        "glow_strength": 0.16 if warm else 0.12,
        "lens_dispersion": 0.0012,
        "vignette": "soft_elliptical_gaussian",
    }, sort_keys=True))



def world_and_lighting(scene: bpy.types.Scene, warm: bool = True) -> None:
    world = bpy.data.worlds.new("A_Square_Atmosphere")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.30, 0.39, 0.47, 1.0) if warm else (0.19, 0.27, 0.34, 1.0)
    background.inputs["Strength"].default_value = 0.52 if warm else 0.48
    scene.world = world
    # A real directional sun gives the architectural planes readable form at
    # the scale of the full street/hall instead of relying on weak nearby lamps.
    sun_data = bpy.data.lights.new("A_Square_Directional_Sun", "SUN")
    sun_data.energy = 1.8 if warm else 1.6
    sun_data.angle = math.radians(8.0)
    sun_obj = bpy.data.objects.new("A_Square_Directional_Sun", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.location = (12.0, 8.0, 16.0)
    sun_obj.rotation_euler = (Vector((0.0, -2.0, 0.0)) - sun_obj.location).to_track_quat("-Z", "Y").to_euler()
    add_area_light(scene, "Sunset_Key", (4.5, 9.5, 13.0), (0.0, -7.0, 2.0), 9800, (1.0, 0.70, 0.46), 12.0)
    add_area_light(scene, "Cool_Sky_Fill", (-10.0, 4.0, 11.0), (0.0, -4.0, 3.0), 7200, (0.42, 0.68, 0.82), 14.0)
    add_area_light(scene, "Warm_Rim", (7.0, -13.0, 9.0), (0.0, -3.0, 2.0), 5600, (1.0, 0.49, 0.28), 10.0)
    configure_cinematic_compositor(scene, warm)


def camera(
    scene: bpy.types.Scene,
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    focal_length: float = 42.0,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(name)
    data.lens = focal_length
    data.sensor_width = 36.0
    data.dof.use_dof = True
    data.dof.focus_distance = (Vector(target) - Vector(location)).length
    data.dof.aperture_fstop = 5.6
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = obj
    return obj


def add_operator_preview(
    glb_path: pathlib.Path,
    location: tuple[float, float, float],
    name: str,
    preferred_action: str = "Rifle idle (low ready)",
) -> bpy.types.Object:
    """Import the exact roster-matched rig only for preview rendering.

    The operator hierarchy is removed immediately after the PNG render. The
    gameplay GLB remains an environment-only scene; Godot supplies the live
    player's HumanoidVisual in the real login/lobby.
    """
    if not glb_path.is_file() or glb_path.stat().st_size <= 0:
        raise FileNotFoundError(f"Rigged operator preview GLB is missing: {glb_path}")
    before = set(bpy.context.scene.objects)
    actions_before = set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not imported:
        raise RuntimeError(f"Blender glTF importer did not create objects for {glb_path}")

    roots = [obj for obj in imported if obj.parent not in imported]
    wrapper = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(wrapper)
    wrapper.location = location
    wrapper.scale = (1.18, 1.18, 1.18)
    wrapper["preview_only"] = True
    wrapper["source_asset"] = glb_path.name
    wrapper["source_sha256"] = hashlib.sha256(glb_path.read_bytes()).hexdigest()

    for obj in roots:
        original_basis = obj.matrix_basis.copy()
        obj.parent = wrapper
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = original_basis

    # Only use actions imported with this exact roster member. A global action
    # lookup can accidentally bind a previous character's take to the next rig.
    imported_actions = [action for action in bpy.data.actions if action not in actions_before]
    all_idle_actions = [
        action for action in imported_actions
        if "idle" in action.name.lower()
    ]
    excluded_idle_tokens = (
        "crouch", "cover", "carry", "aim", "wall", "vehicle",
        "swim", "sprint", "reload", "injured"
    )
    neutral_idle_actions = [
        action for action in all_idle_actions
        if not any(token in action.name.lower() for token in excluded_idle_tokens)
    ]
    preferred = next(
        (
            action for action in imported_actions
            if action.name.lower().strip() == preferred_action.lower().strip()
        ),
        None,
    )
    if preferred is None:
        preferred = next(
            (
                action for action in neutral_idle_actions
                if action.name.lower().strip() in {"idle", "standing idle", "unarmed idle"}
            ),
            None,
        )
    selected_action = preferred or (neutral_idle_actions[0] if neutral_idle_actions else None)
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if armatures and selected_action:
        for armature in armatures:
            armature.animation_data_create()
            try:
                # Keep the motion as an NLA strip and repeat it across the film.
                # This lets Blender evaluate a full authored performance without
                # inventing joint physics or freezing the character at one pose.
                animation_data = armature.animation_data
                animation_data.action = None
                track = animation_data.nla_tracks.new()
                track.name = "A_Square_Cinematic_Performance"
                strip = track.strips.new(selected_action.name, 1, selected_action)
                source_span = max(1.0, float(selected_action.frame_range[1] - selected_action.frame_range[0]))
                strip.repeat = max(1.0, (bpy.context.scene.frame_end - bpy.context.scene.frame_start + 1) / source_span)
                strip.blend_in = min(10.0, source_span * 0.12)
                strip.blend_out = min(10.0, source_span * 0.12)
            except (AttributeError, TypeError, RuntimeError) as exc:
                print(f"OPERATOR_PREVIEW_ANIMATION_WARNING: {exc}")
                try:
                    armature.animation_data.action = selected_action
                except (AttributeError, TypeError, RuntimeError):
                    pass
    elif armatures:
        print("OPERATOR_PREVIEW_ANIMATION_WARNING: no authored action was found for this imported rig; rest pose retained.")

    bpy.context.scene["operator_preview_source"] = glb_path.name
    bpy.context.scene["operator_preview_sha256"] = wrapper["source_sha256"]
    bpy.context.scene["operator_preview_only"] = True
    source_records = json.loads(str(bpy.context.scene.get("operator_preview_sources_json", "[]")))
    source_records.append({
        "preview_name": name,
        "source": glb_path.name,
        "sha256": wrapper["source_sha256"],
        "selected_action": selected_action.name if selected_action else "",
    })
    bpy.context.scene["operator_preview_sources_json"] = json.dumps(source_records, sort_keys=True)
    print("OPERATOR_PREVIEW_IMPORTED:", json.dumps({
        "name": name,
        "source": glb_path.name,
        "sha256": wrapper["source_sha256"],
        "objects": len(imported),
        "armatures": len(armatures),
        "selected_action": selected_action.name if selected_action else "",
        "imported_action_count": len(imported_actions),
        "neutral_idle_actions": [action.name for action in neutral_idle_actions],
    }, sort_keys=True))
    return wrapper


def remove_operator_preview(wrapper: bpy.types.Object | None) -> None:
    if wrapper is None or wrapper.name not in bpy.data.objects:
        return
    # Delete deepest descendants first, and delete the empty wrapper last.
    # Removing the parent first would detach its children and could leave a
    # preview-only character mesh in the actual environment GLB export.
    descendants = list(wrapper.children_recursive)
    for obj in reversed(descendants):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    if wrapper.name in bpy.data.objects:
        bpy.data.objects.remove(wrapper, do_unlink=True)
    bpy.context.scene["operator_preview_removed_before_export"] = True


def animate_transform(obj: bpy.types.Object, name: str, keys: list[tuple[int, tuple[float, float, float], tuple[float, float, float]]], loop: bool = False) -> None:
    for frame, location, rotation in keys:
        obj.location = location
        obj.rotation_euler = rotation
        obj.keyframe_insert(data_path="location", frame=frame, group=name)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame, group=name)
    if obj.animation_data and obj.animation_data.action:
        obj.animation_data.action.name = name
        action = obj.animation_data.action
        for curve in getattr(action, "fcurves", []):
            for key in curve.keyframe_points:
                key.interpolation = "BEZIER"
                key.handle_left_type = "AUTO_CLAMPED"
                key.handle_right_type = "AUTO_CLAMPED"
                if loop:
                    curve.modifiers.new("CYCLES")


def animate_camera_path(
    obj: bpy.types.Object,
    name: str,
    keys: list[tuple[int, tuple[float, float, float], tuple[float, float, float]]],
) -> None:
    """Key camera position and true world-space look-at quaternions (Blender Z-up)."""
    obj.rotation_mode = "QUATERNION"
    for frame, location, target in keys:
        obj.location = location
        obj.rotation_quaternion = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y")
        obj.keyframe_insert(data_path="location", frame=frame, group=name)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)
    if obj.animation_data and obj.animation_data.action:
        obj.animation_data.action.name = name


def register_camera_cut(
    scene: bpy.types.Scene,
    camera_obj: bpy.types.Object,
    frame: int,
    marker_name: str,
) -> None:
    """Bind an authored edit cut to a camera using Blender's timeline markers."""
    marker = scene.timeline_markers.new(marker_name, frame=frame)
    marker.camera = camera_obj
    print("A_SQUARE_CAMERA_CUT:", json.dumps({
        "marker": marker_name,
        "frame": frame,
        "camera": camera_obj.name,
    }, sort_keys=True))


def add_facade_building(
    name: str,
    x: float,
    y: float,
    width: float,
    depth: float,
    floors: int,
    style: int,
    mats: dict[str, bpy.types.Material],
    parent: bpy.types.Object | None = None,
) -> bpy.types.Object:
    rng = random.Random(1000 + style * 73 + int(abs(x) * 12))
    height = floors * 2.42 + 0.55
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0.0)
    set_parent(root, parent)
    facade_materials = [mats["plaster"], mats["sand"], mats["brick"], mats["blue"]]
    shell_mat = facade_materials[style % len(facade_materials)]
    box(name + "_MainVolume", (x, y, height * 0.5), (width, depth, height), shell_mat, 0.05)
    box(name + "_BasePlinth", (x, y - depth * 0.012, 0.16), (width + 0.15, depth + 0.12, 0.32), mats["stone"], 0.035)
    box(name + "_RoofCoping", (x, y, height + 0.08), (width + 0.14, depth + 0.16, 0.18), mats["concrete"], 0.025)
    front_y = y + depth * 0.5 + 0.045
    # Recessed storefronts and weathered metal shutters.
    for column in range(max(2, int(width / 1.45))):
        cx = x - width * 0.5 + (column + 0.5) * width / max(2, int(width / 1.45))
        opening_w = width / max(2, int(width / 1.45)) * 0.70
        if style % 3 == 0:
            box(name + f"_ShopGlass_{column}", (cx, front_y + 0.025, 1.15), (opening_w, 0.055, 1.55), mats["glass"], 0.018)
            box(name + f"_ShopHeader_{column}", (cx, front_y + 0.06, 2.07), (opening_w + 0.06, 0.10, 0.16), mats["brass"], 0.015)
        else:
            box(name + f"_RollerShutter_{column}", (cx, front_y + 0.028, 1.05), (opening_w, 0.06, 1.30), mats["shutter"], 0.012)
            for slat in range(7):
                box(name + f"_ShutterSlat_{column}_{slat}", (cx, front_y + 0.065, 0.51 + slat * 0.16), (opening_w * 0.96, 0.016, 0.018), mats["aluminium"], 0.006)
        # Distinct local shopfront treatment: painted fascia, fabric awning,
        # striped valance, metal brackets and an individually named sign.
        sign_names = ("TEA STALL", "PHARMACY", "MOBILE REPAIR", "BAKERY", "VARIETY STORE", "FERRY TICKETS")
        sign_name = sign_names[(style * 2 + column + int(abs(x))) % len(sign_names)]
        sign_mat = mats["blue"] if style % 2 == 0 else mats["brick"]
        box(name + f"_ShopSignBoard_{column}", (cx, front_y + 0.105, 2.34), (opening_w + 0.08, 0.11, 0.35), sign_mat, 0.025)
        text_data = bpy.data.curves.new(name + f"_ShopSignText_{column}_Font", "FONT")
        text_data.body = sign_name
        text_data.size = min(0.235, max(0.13, opening_w * 0.18))
        text_data.extrude = 0.002
        text_data.bevel_depth = 0.0008
        text_data.align_x = "CENTER"
        text_data.align_y = "CENTER"
        sign_text = bpy.data.objects.new(name + f"_ShopSignText_{column}", text_data)
        bpy.context.collection.objects.link(sign_text)
        sign_text.location = (cx, front_y + 0.17, 2.34)
        sign_text.rotation_euler = (math.pi * 0.5, 0.0, math.pi)
        text_data.materials.append(mats["cream"])
        set_parent(sign_text, root)
        awning_mat = mats["canvas"] if style % 2 == 0 else mats["red"]
        awning = box(name + f"_ShopAwning_{column}", (cx, front_y + 0.34, 1.93), (opening_w + 0.20, 0.54, 0.11), awning_mat, 0.045)
        awning.rotation_euler[0] = math.radians(7.0)
        for stripe in range(4):
            stripe_x = cx - (opening_w + 0.20) * 0.42 + stripe * (opening_w + 0.20) * 0.28
            stripe_mat = mats["cream"] if stripe % 2 == 0 else mats["red"]
            stripe_obj = box(name + f"_AwningStripe_{column}_{stripe}", (stripe_x, front_y + 0.59, 1.89), (0.13, 0.018, 0.12), stripe_mat, 0.015)
            stripe_obj.rotation_euler[0] = math.radians(7.0)
        for bracket_side in (-1, 1):
            cylinder(name + f"_AwningBracket_{column}_{bracket_side}", (cx + bracket_side * (opening_w * 0.42), front_y + 0.33, 1.82), 0.018, 0.44, mats["aluminium"], 10, (math.radians(60.0), 0.0, 0.0))
    window_columns = max(2, int(width / 1.2))
    # Architectural identity differs by block: pilasters, deep corner piers,
    # upper-floor sun hoods and parapet mouldings interrupt repeated window grids.
    if style in (0, 2):
        for pier_index in range(window_columns + 1):
            px = x - width * 0.5 + pier_index * width / window_columns
            box(name + f"_FacadePier_{pier_index}", (px, front_y + 0.13, height * 0.52), (0.12, 0.20, height * 0.92), mats["trim"] if style == 0 else mats["brick"], 0.025)
            box(name + f"_PierCapital_{pier_index}", (px, front_y + 0.20, height - 0.14), (0.22, 0.26, 0.16), mats["stone"], 0.025)
    if style == 3:
        box(name + "_CornerShopCanopy", (x, front_y + 0.42, 2.10), (width + 0.45, 0.80, 0.16), mats["concrete"], 0.045)
        for canopy_post in (-1, 1):
            cylinder(name + f"_CornerCanopyPost_{canopy_post}", (x + canopy_post * width * 0.42, front_y + 0.62, 1.18), 0.035, 2.15, mats["aluminium"], 12)
    # Repeated but individually modelled windows, sills, lintels and balcony edges.
    for floor in range(1, floors + 1):
        z = 0.30 + floor * 2.42
        floor_mat = mats["warm_glass"] if (floor + style) % 4 == 0 else mats["glass"]
        for column in range(window_columns):
            cx = x - width * 0.5 + (column + 0.5) * width / window_columns
            ww = width / window_columns * (0.44 if style % 2 else 0.52)
            wh = 1.18 if floor < floors else 0.98
            box(name + f"_Window_{floor}_{column}", (cx, front_y + 0.045, z), (ww, 0.052, wh), floor_mat, 0.014)
            box(name + f"_Sill_{floor}_{column}", (cx, front_y + 0.11, z - wh * 0.52), (ww + 0.10, 0.14, 0.08), mats["stone"], 0.014)
            if style in (0, 2):
                path_curve(name + f"_ArchedLintel_{floor}_{column}", [
                    (cx - ww * 0.56, front_y + 0.09, z + wh * 0.52),
                    (cx - ww * 0.30, front_y + 0.10, z + wh * 0.70),
                    (cx, front_y + 0.10, z + wh * 0.78),
                    (cx + ww * 0.30, front_y + 0.10, z + wh * 0.70),
                    (cx + ww * 0.56, front_y + 0.09, z + wh * 0.52),
                ], mats["brass"] if style == 0 else mats["stone"], 0.027)
            else:
                box(name + f"_SunHood_{floor}_{column}", (cx, front_y + 0.20, z + wh * 0.56), (ww + 0.20, 0.34, 0.075), mats["concrete"], 0.024)
            # Deep vertical jamb strips catch side light.
            for side in (-1, 1):
                box(name + f"_Jamb_{floor}_{column}_{side}", (cx + side * ww * 0.53, front_y + 0.08, z), (0.055, 0.11, wh + 0.12), mats["trim"], 0.012)
        box(name + f"_FloorBand_{floor}", (x, front_y + 0.10, z - 0.78), (width + 0.04, 0.15, 0.10), mats["trim"], 0.015)
        if style in (1, 3) and floor % 2 == 1:
            balcony_y = front_y + 0.28
            box(name + f"_BalconySlab_{floor}", (x, balcony_y, z - 0.53), (width * 0.82, 0.62, 0.10), mats["concrete"], 0.025)
            for railing in range(9):
                rx = x - width * 0.39 + railing * width * 0.78 / 8
                cylinder(name + f"_BalconyPost_{floor}_{railing}", (rx, balcony_y + 0.25, z - 0.27), 0.018, 0.50, mats["aluminium"], 8)
            path_curve(name + f"_BalconyRail_{floor}", [
                (x - width * 0.41, balcony_y + 0.25, z - 0.04),
                (x, balcony_y + 0.25, z - 0.04),
                (x + width * 0.41, balcony_y + 0.25, z - 0.04),
            ], mats["aluminium"], 0.024)
    # Rooftop life: water tank, dish, parapet, antennas, AC units and utility lines.
    parapet = box(name + "_Parapet", (x, y, height + 0.34), (width + 0.16, depth + 0.12, 0.52), mats["concrete"], 0.025)
    tank_x = x + width * 0.26
    tank_y = y + depth * 0.12
    cylinder(name + "_WaterTank", (tank_x, tank_y, height + 0.88), 0.52, 0.92, mats["tank"], 32)
    cylinder(name + "_TankLip", (tank_x, tank_y, height + 1.36), 0.54, 0.08, mats["aluminium"], 32)
    dish = sphere(name + "_SatelliteDish", (x - width * 0.25, y + depth * 0.20, height + 0.72), (0.42, 0.10, 0.42), mats["aluminium"], 24, 12)
    dish.rotation_euler[0] = math.radians(28)
    cylinder(name + "_AntennaPole", (x - width * 0.25, y + depth * 0.20, height + 1.35), 0.025, 1.2, mats["aluminium"], 12)
    for ac in range(max(1, floors // 3)):
        ax = x - width * 0.34 + ac * 0.72
        box(name + f"_ACOutdoor_{ac}", (ax, front_y + 0.18, height * 0.70), (0.52, 0.42, 0.44), mats["aluminium"], 0.035)
        cylinder(name + f"_ACFan_{ac}", (ax, front_y + 0.41, height * 0.70), 0.15, 0.035, mats["dark"], 20, (math.pi * 0.5, 0.0, 0.0))
    return root


def add_leaf_cluster(name: str, center: Vector, radius: float, mat: bpy.types.Material, seed: int, parent: bpy.types.Object | None = None) -> bpy.types.Object:
    rng = random.Random(seed)
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for index in range(90):
        theta = rng.random() * math.tau
        phi = math.acos(2.0 * rng.random() - 1.0)
        direction = Vector((math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi)))
        base = center + direction * radius * (0.48 + rng.random() * 0.62)
        forward = Vector((math.cos(theta), math.sin(theta), rng.uniform(-0.32, 0.42))).normalized()
        side = direction.cross(forward).normalized()
        length = rng.uniform(0.16, 0.34)
        width = length * rng.uniform(0.15, 0.26)
        start = len(verts)
        verts.extend([
            tuple(base - forward * length * 0.55),
            tuple(base + forward * length * 0.45 + side * width),
            tuple(base + forward * length * 0.72),
            tuple(base + forward * length * 0.45 - side * width),
        ])
        faces.append((start, start + 1, start + 2))
        faces.append((start, start + 2, start + 3))
    mesh = bpy.data.meshes.new(name + "_LeafCardMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return set_parent(obj, parent)


def add_banyan_or_palm(name: str, x: float, y: float, height: float, mats: dict[str, bpy.types.Material], seed: int) -> None:
    rng = random.Random(seed)
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0.0)
    cylinder(name + "_TrunkCore", (x, y, height * 0.46), 0.24, height * 0.92, mats["bark"], 18)
    for branch in range(8):
        angle = math.tau * branch / 8.0
        sway = rng.uniform(-0.28, 0.28)
        path_curve(name + f"_Branch_{branch}", [
            (x, y, height * 0.48),
            (x + math.cos(angle) * 0.36, y + math.sin(angle) * 0.25, height * 0.74),
            (x + math.cos(angle) * (0.72 + sway), y + math.sin(angle) * 0.50, height * 0.92),
        ], mats["bark"], 0.075, root)
        add_leaf_cluster(name + f"_Leaves_{branch}", Vector((
            x + math.cos(angle) * 0.85, y + math.sin(angle) * 0.62, height * 0.94 + rng.uniform(-0.18, 0.25)
        )), 0.86, mats["leaf_a"] if branch % 2 else mats["leaf_b"], seed + branch, root)


def add_cng(name: str, x: float, y: float, mats: dict[str, bpy.types.Material]) -> bpy.types.Object:
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0.0)
    # Three-wheel auto-rickshaw body with curved canopy, instrument panel and open passenger cabin.
    box(name + "_LowerChassis", (x, y, 0.62), (2.65, 1.22, 0.42), mats["cng_green"], 0.18, root)
    box(name + "_Nose", (x + 1.08, y - 0.02, 0.90), (0.56, 1.12, 0.62), mats["cng_green_light"], 0.18, root)
    box(name + "_FrontApron", (x + 1.30, y - 0.01, 0.57), (0.18, 0.86, 0.44), mats["cng_dark"], 0.07, root)
    box(name + "_PassengerRearPanel", (x - 0.56, y, 1.03), (1.10, 1.06, 0.68), mats["cng_green"], 0.10, root)
    box(name + "_CanvasCanopy", (x - 0.18, y, 1.75), (1.90, 1.34, 0.16), mats["canvas"], 0.13, root)
    for side in (-1, 1):
        for col in range(2):
            cylinder(name + f"_CanopyPillar_{side}_{col}", (x - 0.68 + col * 0.95, y + side * 0.54, 1.39), 0.038, 0.70, mats["dark"], 12, parent=root)
        path_curve(name + f"_SideRail_{side}", [
            (x - 1.02, y + side * 0.54, 1.0),
            (x - 0.20, y + side * 0.54, 1.12),
            (x + 0.55, y + side * 0.54, 1.12),
        ], mats["brass"], 0.025, root)
        box(name + f"_SideBadge_{side}", (x - 0.36, y + side * 0.615, 0.79), (0.68, 0.035, 0.20), mats["cream"], 0.025, root)
    box(name + "_Windscreen", (x + 0.85, y, 1.28), (0.055, 0.85, 0.50), mats["glass"], 0.02, root)
    for side in (-1, 1):
        sphere(name + f"_Headlamp_{side}", (x + 1.38, y + side * 0.32, 0.74), (0.09, 0.13, 0.10), mats["lamp"], 16, 10, root)
        cylinder(name + f"_MirrorStem_{side}", (x + 0.78, y + side * 0.52, 1.55), 0.018, 0.48, mats["aluminium"], 10, parent=root)
        sphere(name + f"_Mirror_{side}", (x + 0.79, y + side * 0.53, 1.78), (0.10, 0.07, 0.065), mats["dark"], 12, 8, root)
    # Three wheels with sculpted tread blocks and wheel hubs.
    wheels = []
    wheel_positions = [(x + 0.92, y, 0.35), (x - 0.75, y - 0.52, 0.35), (x - 0.75, y + 0.52, 0.35)]
    for index, pos in enumerate(wheel_positions):
        hub = bpy.data.objects.new(name + f"_WheelPivot_{index}", None)
        bpy.context.collection.objects.link(hub)
        hub.location = pos
        set_parent(hub, root)
        wheel = cylinder(name + f"_Tyre_{index}", pos, 0.34, 0.16, mats["rubber"], 32, (math.pi * 0.5, 0.0, 0.0), hub)
        wheel.rotation_euler[1] = math.pi * 0.5
        cylinder(name + f"_AlloyHub_{index}", pos, 0.18, 0.18, mats["aluminium"], 24, (math.pi * 0.5, 0.0, 0.0), hub)
        cylinder(name + f"_HubCap_{index}", pos, 0.075, 0.19, mats["brass"], 20, (math.pi * 0.5, 0.0, 0.0), hub)
        wheels.append(hub)
        # Radial spokes, a machined rim lip and hub cap give the CNG wheel a
        # layered silhouette rather than one dark cylinder.
        for spoke in range(10):
            angle = math.tau * spoke / 10.0
            inner = (
                pos[0] + 0.105 * math.cos(angle),
                pos[1] - 0.095,
                pos[2] + 0.105 * math.sin(angle),
            )
            outer = (
                pos[0] + 0.292 * math.cos(angle),
                pos[1] - 0.095,
                pos[2] + 0.292 * math.sin(angle),
            )
            path_curve(name + f"_WheelSpoke_{index}_{spoke}", [inner, outer], mats["aluminium"], 0.012, root)
        cylinder(
            name + f"_RimLip_{index}",
            (pos[0], pos[1] - 0.092, pos[2]),
            0.298, 0.018, mats["brass"], 32,
            (math.pi * 0.5, 0.0, 0.0), root,
        )
        hub.rotation_mode = "XYZ"
        hub.rotation_euler = (0.0, 0.0, 0.0)
        hub.keyframe_insert(data_path="rotation_euler", frame=1, group=f"CNG_Wheel_Rotation_{index}")
        hub.rotation_euler[1] = math.tau * 3.2
        hub.keyframe_insert(data_path="rotation_euler", frame=288, group=f"CNG_Wheel_Rotation_{index}")
        if hub.animation_data and hub.animation_data.action:
            hub.animation_data.action.name = f"CNG_Wheel_Rotation_{index}"
    # Front mudguard arc, enamel pinstripe, indicators and readable plates.
    front_wheel = wheel_positions[0]
    fender_points = []
    for step in range(19):
        angle = math.pi * step / 18.0
        fender_points.append((
            front_wheel[0] + 0.405 * math.cos(angle),
            y - 0.11,
            front_wheel[2] + 0.405 * math.sin(angle),
        ))
    path_curve(name + "_Front_Mudguard_Arch", fender_points, mats["cng_green_light"], 0.075, root)
    path_curve(name + "_Body_Cream_Pinstripe", [
        (x - 0.88, y - 0.635, 0.78),
        (x - 0.25, y - 0.635, 0.82),
        (x + 0.38, y - 0.635, 0.82),
        (x + 0.86, y - 0.55, 0.92),
    ], mats["cream"], 0.018, root)
    for side in (-1, 1):
        sphere(name + f"_Front_Indicator_{side}", (x + 1.36, y + side * 0.49, 0.88), (0.085, 0.08, 0.065), mats["lamp"], 16, 10, root)
        sphere(name + f"_Rear_TailLamp_{side}", (x - 1.18, y + side * 0.50, 0.72), (0.075, 0.065, 0.11), mats["red"], 16, 10, root)
    box(name + "_Front_NumberPlate", (x + 1.405, y - 0.005, 0.49), (0.045, 0.52, 0.19), mats["white"], 0.018, root)
    box(name + "_Rear_NumberPlate", (x - 1.18, y - 0.005, 0.48), (0.045, 0.48, 0.17), mats["white"], 0.016, root)
    root["wheel_pivots"] = [obj.name for obj in wheels]
    root["asset_role"] = "Bangladesh_CNG_AutoRickshaw"
    return root


def animate_location(obj: bpy.types.Object, name: str, keys: list[tuple[int, tuple[float, float, float]]], loop: bool = False) -> None:
    for frame, location in keys:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame, group=name)
    if obj.animation_data and obj.animation_data.action:
        obj.animation_data.action.name = name
        for curve in getattr(obj.animation_data.action, "fcurves", []):
            for key in curve.keyframe_points:
                key.interpolation = "BEZIER"
                key.handle_left_type = "AUTO_CLAMPED"
                key.handle_right_type = "AUTO_CLAMPED"
            if loop:
                curve.modifiers.new("CYCLES")


def configure_river_water_material(mat: bpy.types.Material) -> None:
    """Author layered river colour, roughness and multi-scale ripple normals."""
    mat.diffuse_color = (0.025, 0.135, 0.17, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (760, 80)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (480, 80)
    shader.inputs["Metallic"].default_value = 0.14
    shader.inputs["Roughness"].default_value = 0.19
    if "IOR" in shader.inputs:
        shader.inputs["IOR"].default_value = 1.333
    if "Specular IOR Level" in shader.inputs:
        shader.inputs["Specular IOR Level"].default_value = 0.72
    if "Coat Weight" in shader.inputs:
        shader.inputs["Coat Weight"].default_value = 0.28
        shader.inputs["Coat Roughness"].default_value = 0.12
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])

    coordinates = nodes.new("ShaderNodeTexCoord")
    coordinates.location = (-900, 80)

    long_wave = nodes.new("ShaderNodeTexWave")
    long_wave.location = (-660, 280)
    long_wave.wave_type = "BANDS"
    long_wave.bands_direction = "X"
    long_wave.inputs["Scale"].default_value = 3.2
    long_wave.inputs["Distortion"].default_value = 5.0
    long_wave.inputs["Detail"].default_value = 3.0
    long_wave.inputs["Detail Scale"].default_value = 1.35
    links.new(coordinates.outputs["UV"], long_wave.inputs["Vector"])

    micro_noise = nodes.new("ShaderNodeTexNoise")
    micro_noise.location = (-660, -120)
    micro_noise.inputs["Scale"].default_value = 28.0
    micro_noise.inputs["Detail"].default_value = 4.0
    micro_noise.inputs["Roughness"].default_value = 0.72
    links.new(coordinates.outputs["UV"], micro_noise.inputs["Vector"])

    colour_ramp = nodes.new("ShaderNodeValToRGB")
    colour_ramp.location = (-360, 390)
    colour_ramp.color_ramp.elements[0].position = 0.18
    colour_ramp.color_ramp.elements[0].color = (0.006, 0.045, 0.058, 1.0)
    colour_ramp.color_ramp.elements[1].position = 0.82
    colour_ramp.color_ramp.elements[1].color = (0.045, 0.235, 0.255, 1.0)
    links.new(micro_noise.outputs["Fac"], colour_ramp.inputs["Fac"])
    links.new(colour_ramp.outputs["Color"], shader.inputs["Base Color"])

    roughness_ramp = nodes.new("ShaderNodeValToRGB")
    roughness_ramp.location = (-360, 100)
    roughness_ramp.color_ramp.elements[0].position = 0.12
    roughness_ramp.color_ramp.elements[0].color = (0.105, 0.105, 0.105, 1.0)
    roughness_ramp.color_ramp.elements[1].position = 0.88
    roughness_ramp.color_ramp.elements[1].color = (0.31, 0.31, 0.31, 1.0)
    links.new(micro_noise.outputs["Fac"], roughness_ramp.inputs["Fac"])
    links.new(roughness_ramp.outputs["Color"], shader.inputs["Roughness"])

    broad_bump = nodes.new("ShaderNodeBump")
    broad_bump.location = (30, -40)
    broad_bump.inputs["Strength"].default_value = 0.18
    broad_bump.inputs["Distance"].default_value = 0.018
    links.new(long_wave.outputs["Color"], broad_bump.inputs["Height"])

    micro_bump = nodes.new("ShaderNodeBump")
    micro_bump.location = (260, -80)
    micro_bump.inputs["Strength"].default_value = 0.22
    micro_bump.inputs["Distance"].default_value = 0.006
    links.new(micro_noise.outputs["Fac"], micro_bump.inputs["Height"])
    links.new(broad_bump.outputs["Normal"], micro_bump.inputs["Normal"])
    links.new(micro_bump.outputs["Normal"], shader.inputs["Normal"])

    mat["surface_role"] = "layered_meghna_water_pbr"
    mat["surface_features"] = "long_wave_bands;micro_ripple_normal;roughness_breakup;screen_traced_reflection"


def make_material_set() -> dict[str, bpy.types.Material]:
    mats = {
        "dark": material("Graphite_Ceramic", METAL_DARK, 0.31, 0.74, 55, 0.12),
        "blue": material("Deep_River_Teal_Plaster", METAL_BLUE, 0.72, 0.08, 4.5, 0.20),
        "brass": material("Brushed_Antique_Brass", BRASS, 0.28, 0.82, 95, 0.09),
        "aluminium": material("Anodised_Aluminium", (0.39, 0.45, 0.47, 1), 0.26, 0.82, 110, 0.06),
        "glass": material("Smoked_River_Glass", GLASS, 0.17, 0.32),
        "warm_glass": material("Warm_Interior_Glass", (0.56, 0.31, 0.13, 1), 0.22, 0.22, emission=0.18),
        "plaster": material("Aged_Lime_Plasters", (0.48, 0.43, 0.35, 1), 0.91, 0.0, 7, 0.28),
        "sand": material("Warm_Sandstone", PAINT_CREAM, 0.86, 0.02, 8, 0.22),
        "brick": material("Riverbank_Brickwork", (0.36, 0.18, 0.12, 1), 0.89, 0.0, 18, 0.32),
        "stone": material("Cast_Stone_Concrete", CONCRETE, 0.91, 0.0, 28, 0.34),
        "concrete": material("Weathered_Concrete", (0.24, 0.28, 0.28, 1), 0.92, 0.0, 38, 0.36),
        "trim": material("Dark_Anodised_Window_Trim", (0.038, 0.065, 0.074, 1), 0.32, 0.76, 65, 0.08),
        "shutter": material("Painted_Roller_Shutter", (0.15, 0.22, 0.23, 1), 0.48, 0.48, 60, 0.15),
        "tank": material("Blue_Poly_Water_Tank", (0.04, 0.15, 0.20, 1), 0.41, 0.08, 16, 0.12),
        "leaf_a": material("Wet_Tropical_Foliage", (0.045, 0.18, 0.075, 1), 0.74, 0.0, 9, 0.10),
        "leaf_b": material("Sunlit_Foliage", (0.16, 0.29, 0.105, 1), 0.78, 0.0, 7, 0.10),
        "bark": material("Rain_Darkened_Bark", (0.18, 0.10, 0.055, 1), 0.92, 0.0, 22, 0.30),
        "river": material("Meghna_River_Water", (0.035, 0.15, 0.20, 1), 0.14, 0.32, 34, 0.27),
        "road": material("Asphalt_With_Fine_Aggregate", (0.075, 0.095, 0.10, 1), 0.94, 0.0, 70, 0.30),
        "rubber": material("Tyre_Rubber", (0.025, 0.028, 0.029, 1), 0.93, 0.0, 80, 0.17),
        "canvas": material("Sun_Faded_Canvas", (0.62, 0.53, 0.36, 1), 0.91, 0.0, 24, 0.22),
        "cng_green": material("CNG_Deep_Emerald_Paint", (0.035, 0.48, 0.22, 1), 0.31, 0.48, 46, 0.10),
        "cng_green_light": material("CNG_Emerald_Highlight", (0.08, 0.64, 0.31, 1), 0.29, 0.42, 38, 0.08),
        "cng_dark": material("CNG_Dark_Frame", (0.025, 0.08, 0.07, 1), 0.43, 0.68),
        "cream": material("CNG_Cream_Trim", PAINT_CREAM, 0.40, 0.24),
        "lamp": material("Warm_LED_Lamp", (0.96, 0.66, 0.31, 1), 0.20, 0.10, emission=1.8),
        "screen": material("Tactical_Screen_Emissive", (0.015, 0.32, 0.34, 1), 0.24, 0.15, emission=1.2),
        "red": material("Signal_Red_Enamel", RED, 0.38, 0.35),
        "waterline": material("Waterline_Teal", (0.06, 0.33, 0.33, 1), 0.23, 0.5, emission=0.08),
        "white": material("Warm_White_Lacquer", (0.73, 0.70, 0.61, 1), 0.34, 0.22),
        "wood": material("Oiled_Teak", (0.24, 0.12, 0.055, 1), 0.58, 0.06, 6, 0.12),
    }
    configure_river_water_material(mats["river"])
    return mats


def river_plane(mats: dict[str, bpy.types.Material], y: float, width: float, depth: float) -> bpy.types.Object:
    """Create a tessellated river with an authored, looping multi-scale swell."""
    columns = max(96, int(width * 2.0))
    rows = max(48, int(depth * 2.0))
    water_level = -0.31
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for row in range(rows + 1):
        local_y = -depth * 0.5 + depth * row / rows
        for column in range(columns + 1):
            local_x = -width * 0.5 + width * column / columns
            vertices.append((local_x, local_y, water_level))
    stride = columns + 1
    for row in range(rows):
        for column in range(columns):
            a = row * stride + column
            b = a + 1
            d = (row + 1) * stride + column
            c = d + 1
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new(f"Meghna_River_Surface_Mesh_{abs(y):.1f}m")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    water = bpy.data.objects.new("Meghna_River_Surface", mesh)
    bpy.context.collection.objects.link(water)
    water.location = (0.0, y, 0.0)
    mesh.materials.append(mats["river"])
    for polygon in mesh.polygons:
        polygon.use_smooth = True

    uv_layer = mesh.uv_layers.new(name="River_Wave_UV")
    for loop in mesh.loops:
        row, column = divmod(loop.vertex_index, stride)
        uv_layer.data[loop.index].uv = (column / columns, row / rows)

    # The four wave poses are separate authored deformations. Cycling their
    # weights produces a soft handoff rather than one identical sine bob.
    wave_keys = []
    for phase_index in range(4):
        phase = math.tau * phase_index / 4.0
        key = water.shape_key_add(name=f"River_Wave_Phase_{phase_index + 1}", from_mix=False)
        for vertex_index, (local_x, local_y, _) in enumerate(vertices):
            world_y = local_y + y
            long_swell = 0.040 * math.sin(local_x * 0.19 + world_y * 0.105 + phase)
            cross_swell = 0.018 * math.sin(local_x * 0.49 - world_y * 0.31 + phase * 1.37)
            capillary = 0.006 * math.sin(local_x * 1.48 + world_y * 0.86 - phase * 0.73)
            key.data[vertex_index].co.z = water_level + long_swell + cross_swell + capillary
        wave_keys.append(key)

    phase_frames = (1, 73, 145, 217, 289)
    for phase_step, frame in enumerate(phase_frames):
        active_phase = phase_step % 4
        for phase_index, key in enumerate(wave_keys):
            key.value = 1.0 if phase_index == active_phase else 0.0
            key.keyframe_insert(data_path="value", frame=frame, group="River_Wave_Performance")

    shape_keys = mesh.shape_keys
    if shape_keys and shape_keys.animation_data and shape_keys.animation_data.action:
        action = shape_keys.animation_data.action
        action.name = "Meghna_River_Looping_Wave_Performance"
        try:
            for curve in action.fcurves:
                for keyframe in curve.keyframe_points:
                    keyframe.interpolation = "BEZIER"
                    keyframe.handle_left_type = "AUTO_CLAMPED"
                    keyframe.handle_right_type = "AUTO_CLAMPED"
                curve.modifiers.new("CYCLES")
        except AttributeError:
            print("RIVER_WAVE_ANIMATION_WARNING: legacy F-curve API unavailable; authored keys retained.")

    water["surface_role"] = "river_water"
    water["wave_mesh_dimensions"] = f"{columns}x{rows}"
    water["wave_vertex_count"] = len(vertices)
    water["wave_phase_count"] = len(wave_keys)
    water["wave_animation"] = "four-phase cyclic shape-key swell with micro-ripple shader"
    water["reflection_intent"] = "EEVEE screen tracing with light-probe fallback"
    print("RIVER_SURFACE_READY:", json.dumps({
        "name": water.name,
        "vertices": len(vertices),
        "faces": len(faces),
        "wave_phases": len(wave_keys),
        "reflection_intent": "screen_trace",
    }, sort_keys=True))
    return water

def apply_camera_shakify(camera_obj: bpy.types.Object, scene: bpy.types.Scene) -> dict:
    """Apply Camera Shakify 0.5.1 and bake its evaluated camera movement."""
    addon_dir = pathlib.Path(os.environ.get("ASQUARE_CAMERA_SHAKIFY_DIR", ""))
    addon_commit = os.environ.get("ASQUARE_CAMERA_SHAKIFY_COMMIT", "")
    manifest_path = addon_dir / "blender_manifest.toml"
    if not addon_dir.is_dir() or not manifest_path.is_file():
        raise RuntimeError("Pinned Camera Shakify 0.5.1 authoring extension is missing.")
    try:
        import tomllib
        addon_manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Camera Shakify manifest could not be read: {exc}") from exc
    if addon_manifest.get("version") != "0.5.1":
        raise RuntimeError("Camera Shakify version pin mismatch.")
    if addon_manifest.get("blender_version_min") != "4.4.0":
        raise RuntimeError("Camera Shakify Blender compatibility metadata changed.")

    sys.path.insert(0, str(addon_dir.parent))
    import importlib
    addon = importlib.import_module("camera_shakify")
    addon.register()

    def sample_camera() -> dict[int, tuple[Vector, object]]:
        result = {}
        for frame in range(scene.frame_start, scene.frame_end + 1):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            evaluated = camera_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            matrix = evaluated.matrix_world.copy()
            result[frame] = (matrix.translation.copy(), matrix.to_quaternion().copy())
        return result

    baseline = sample_camera()
    for item in list(bpy.context.selected_objects):
        item.select_set(False)
    camera_obj.select_set(True)
    bpy.context.view_layer.objects.active = camera_obj
    created = bpy.ops.object.camera_shake_add()
    if "FINISHED" not in created or len(camera_obj.camera_shakes) != 1:
        raise RuntimeError("Camera Shakify did not create a camera shake item.")

    shake = camera_obj.camera_shakes[0]
    shake.shake_type = "INVESTIGATION"
    shake.influence = 0.42
    shake.scale = 0.34
    shake.use_manual_timing = False
    shake.speed = 0.72
    shaken = sample_camera()

    max_translation = max((shaken[f][0] - baseline[f][0]).length for f in baseline)
    max_rotation = max(baseline[f][1].rotation_difference(shaken[f][1]).angle for f in baseline)
    if max_translation < 0.00001 and max_rotation < math.radians(0.005):
        raise RuntimeError("Camera Shakify generated no measurable shake.")
    if max_translation > 0.45 or max_rotation > math.radians(6.0):
        raise RuntimeError("Camera Shakify exceeded the cinematic motion budget.")

    for constraint in list(camera_obj.constraints):
        camera_obj.constraints.remove(constraint)
    camera_obj.animation_data_clear()
    camera_obj.rotation_mode = "QUATERNION"
    baked = bpy.data.actions.new("Login_Dolly_Shake_Baked")
    camera_obj.animation_data_create()
    camera_obj.animation_data.action = baked
    for frame in sorted(shaken):
        location, rotation = shaken[frame]
        camera_obj.location = location
        camera_obj.rotation_quaternion = rotation
        camera_obj.keyframe_insert(data_path="location", frame=frame, group="Login_Dolly_Shake_Baked")
        camera_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, group="Login_Dolly_Shake_Baked")
    for curve in list(getattr(baked, "fcurves", [])):
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"

    helper_collection = bpy.data.collections.get("CameraShakify.v3")
    if helper_collection is not None:
        for helper_object in list(helper_collection.objects):
            if helper_object.animation_data:
                helper_object.animation_data_clear()
            bpy.data.objects.remove(helper_object, do_unlink=True)
        bpy.data.collections.remove(helper_collection, do_unlink=True)
    if hasattr(camera_obj, "camera_shakes"):
        camera_obj.camera_shakes.clear()
    addon.unregister()

    scene["camera_shakify_version"] = "0.5.1"
    scene["camera_shakify_source_commit"] = addon_commit
    scene["camera_shakify_preset"] = "INVESTIGATION"
    scene["camera_shakify_influence"] = 0.42
    scene["camera_shakify_scale"] = 0.34
    scene["camera_shakify_baked"] = True
    scene["camera_shakify_runtime_dependency"] = False
    scene.frame_set(90)
    report = {
        "version": "0.5.1",
        "source_commit": addon_commit,
        "preset": "INVESTIGATION",
        "max_translation_m": round(max_translation, 6),
        "max_rotation_degrees": round(math.degrees(max_rotation), 4),
        "baked": True,
        "runtime_dependency": False,
    }
    print("CAMERA_SHAKIFY_BAKE_PASS:", json.dumps(report, sort_keys=True))
    return report


def face_operator_to_camera(operator: bpy.types.Object, camera_obj: bpy.types.Object) -> None:
    direction = Vector((
        camera_obj.location.x - operator.location.x,
        camera_obj.location.y - operator.location.y,
        0.0,
    ))
    if direction.length_squared > 0.0001:
        operator.rotation_euler[2] = math.atan2(-direction.x, -direction.y)


def set_parent_local(obj: bpy.types.Object, parent: bpy.types.Object | None) -> bpy.types.Object:
    """Parent locally-authored geometry without cancelling the parent's transform."""
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse.identity()
    return obj


def local_path_curve(
    name: str,
    points: list[tuple[float, float, float]],
    mat: bpy.types.Material,
    radius: float,
    parent: bpy.types.Object | None = None,
    cyclic: bool = False,
) -> bpy.types.Object:
    """Create a curve whose coordinates follow the local space of its authored parent."""
    data = bpy.data.curves.new(name + "_LocalSpline", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 18
    data.bevel_depth = radius
    data.bevel_resolution = 4
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    return set_parent_local(obj, parent)


def authored_mesh(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    mat: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    smooth: bool = False,
) -> bpy.types.Object:
    """Create an editable, hand-authored surface mesh without primitive operators."""
    mesh = bpy.data.meshes.new(name + "_SculptedMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(clean_customdata=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    for polygon in mesh.polygons:
        polygon.use_smooth = smooth
    return set_parent_local(obj, parent)


def authored_xz_prism(
    name: str,
    contour: list[tuple[float, float]],
    front_y: float,
    back_y: float,
    mat: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    bevel: float = 0.0,
    include_front_face: bool = True,
    include_back_face: bool = True,
) -> bpy.types.Object:
    """Extrude an irregular artist-drawn elevation contour along the depth axis."""
    count = len(contour)
    vertices = [(x, front_y, z) for x, z in contour]
    vertices.extend((x, back_y, z) for x, z in contour)
    faces: list[tuple[int, ...]] = []
    if include_front_face:
        faces.append(tuple(range(count)))
    if include_back_face:
        faces.append(tuple(range(count * 2 - 1, count - 1, -1)))
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count + j, count + i))
    obj = authored_mesh(name, vertices, faces, mat, parent, False)
    if bevel > 0.0:
        edge = obj.modifiers.new(name + "_HandFinishedEdges", "BEVEL")
        edge.width = bevel
        edge.segments = 3
        edge.profile = 0.5
        normals = obj.modifiers.new(name + "_CraftedNormals", "WEIGHTED_NORMAL")
        normals.keep_sharp = True
        normals.weight = 35
    return obj


def authored_xy_slab(
    name: str,
    contour: list[tuple[float, float]],
    lower_z: float,
    upper_z: float,
    mat: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    bevel: float = 0.0,
) -> bpy.types.Object:
    """Extrude a custom plan-view contour vertically for shaped balconies and canopies."""
    count = len(contour)
    vertices = [(x, y, upper_z) for x, y in contour]
    vertices.extend((x, y, lower_z) for x, y in contour)
    faces: list[tuple[int, ...]] = [
        tuple(range(count)),
        tuple(range(count * 2 - 1, count - 1, -1)),
    ]
    for i in range(count):
        j = (i + 1) % count
        faces.append((i, j, count + j, count + i))
    obj = authored_mesh(name, vertices, faces, mat, parent, False)
    if bevel > 0.0:
        edge = obj.modifiers.new(name + "_SoftWornEdge", "BEVEL")
        edge.width = bevel
        edge.segments = 3
        obj.modifiers.new(name + "_WeightedSurfaceNormals", "WEIGHTED_NORMAL")
    return obj


def authored_lathe(
    name: str,
    profile: list[tuple[float, float]],
    mat: bpy.types.Material,
    parent: bpy.types.Object | None = None,
    segments: int = 48,
    rib_amount: float = 0.0,
) -> bpy.types.Object:
    """Turn a hand-drawn radius/height profile into a lathed, optionally ribbed surface."""
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int, int]] = []
    for ring, (z, radius) in enumerate(profile):
        for segment in range(segments):
            angle = math.tau * segment / segments
            rib = 1.0 + rib_amount * math.sin(angle * 12.0 + ring * 0.15)
            r = radius * rib
            vertices.append((math.cos(angle) * r, math.sin(angle) * r, z))
    for ring in range(len(profile) - 1):
        for segment in range(segments):
            a = ring * segments + segment
            b = ring * segments + (segment + 1) % segments
            c = (ring + 1) * segments + (segment + 1) % segments
            d = (ring + 1) * segments + segment
            faces.append((a, b, c, d))
    return authored_mesh(name, vertices, faces, mat, parent, True)


def add_crafted_riverfront_corner_store(
    x: float,
    y: float,
    width: float,
    depth: float,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """Build the hero shop as a bespoke mesh/curve composition, not a primitive kit."""
    name = "Shariatpur_Meghna_Corner_Store_Hero"
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0.0)

    half = width * 0.5
    front = depth * 0.5
    back = -depth * 0.5
    facade_top = 7.38

    # Irregular roofline, subtle corner offsets and hand-shaped massing give the
    # building a unique silhouette before any signs, windows or surface detail.
    body_contour = [
        (-half, 0.0), (half, 0.0), (half, 6.76),
        (half - 0.22, 6.98), (half - 0.56, 6.93),
        (1.42, 7.20), (0.94, 7.08), (0.35, 7.42),
        (-0.26, 7.19), (-0.84, 7.34), (-1.42, 7.04),
        (-half + 0.48, 7.12), (-half, 6.82),
    ]
    authored_xz_prism(
        name + "_Irregular_Masonry_Mass",
        body_contour, front, back, mats["sand"], root, 0.035,
        include_front_face=False, include_back_face=False,
    )
    authored_xz_prism(
        name + "_Deep_Interior_Back_Wall",
        body_contour, back + 0.055, back - 0.015, mats["dark"], root,
    )

    # The front elevation is assembled around genuine negative-space openings.
    # These custom wall panels form piers, lintels and upper infill; the shop
    # glazing and doors are not simply pasted over a solid box.
    arch_left = -2.12
    arch_right = -0.10
    arch_spring = 2.20
    arch_crown = 2.76

    ground_panels = [
        [(-half, 0.0), (arch_left - 0.08, 0.0), (arch_left - 0.08, 3.78), (-half, 3.78)],
        [(arch_right + 0.08, 0.0), (0.66, 0.0), (0.66, 2.92), (arch_right + 0.08, 2.92)],
        [(1.93, 0.0), (half, 0.0), (half, 3.78), (1.93, 3.78)],
        [(-half, 2.80), (half, 2.80), (half, 3.02), (-half, 3.02)],
        [(-half, 3.56), (half, 3.56), (half, 3.82), (-half, 3.82)],
    ]
    for index, panel in enumerate(ground_panels):
        authored_xz_prism(
            name + f"_Ground_Facade_Pier_{index}",
            panel, front + 0.055, front - 0.015, mats["sand"] if index % 2 else mats["brick"], root, 0.012,
        )
    upper_piers = [
        (-half, -2.22), (-1.02, -0.58), (0.60, 1.00), (2.20, half),
    ]
    for index, (left, right) in enumerate(upper_piers):
        authored_xz_prism(
            name + f"_Upper_Architectural_Pier_{index}",
            [(left, 3.80), (right, 3.80), (right, 7.05), (left, 7.05)],
            front + 0.055, front - 0.015, mats["sand"], root, 0.012,
        )
    # Upper lintels frame the arch windows without closing their apertures.
    for index, (z0, z1) in enumerate(((3.78, 4.02), (5.30, 5.52), (6.85, 7.05))):
        authored_xz_prism(
            name + f"_Upper_Window_Lintel_Band_{index}",
            [(-half, z0), (half, z0), (half, z1), (-half, z1)],
            front + 0.065, front - 0.010, mats["stone"], root, 0.018,
        )

    # Deep shop recesses: two different arches, one broad service hatch and a
    # narrow timber door. Their custom profiles are intentionally not mirrored.
    arch_left = -2.12
    arch_right = -0.10
    arch_spring = 2.20
    arch_crown = 2.76
    left_arch = [
        (arch_left, 0.32), (arch_right, 0.32), (arch_right, arch_spring),
        (arch_right - 0.12, 2.43), (-0.53, 2.63), (-0.94, arch_crown),
        (-1.39, 2.62), (-1.82, 2.44), (arch_left, arch_spring),
    ]
    authored_xz_prism(
        name + "_Recessed_Arched_Shop_Window",
        left_arch, front + 0.065, front + 0.020, mats["dark"], root,
    )
    local_path_curve(name + "_Arched_Shop_Stone_Moulding", [
        (arch_left, front + 0.11, 0.28),
        (arch_left, front + 0.11, arch_spring),
        (-1.91, front + 0.11, 2.49),
        (-1.50, front + 0.11, arch_crown),
        (-1.05, front + 0.11, 2.57),
        (arch_right - 0.06, front + 0.11, arch_spring),
        (arch_right, front + 0.11, 0.28),
    ], mats["stone"], 0.095, root)
    local_path_curve(name + "_Inner_Arch_Brass_Inlay", [
        (-1.94, front + 0.13, 0.45),
        (-1.94, front + 0.13, 2.18),
        (-1.76, front + 0.13, 2.42),
        (-1.36, front + 0.13, 2.62),
        (-0.94, front + 0.13, 2.42),
        (-0.28, front + 0.13, 2.18),
        (-0.28, front + 0.13, 0.45),
    ], mats["brass"], 0.022, root)

    # The glazing is broken into separate panes, leaving the shop interior
    # visible. The lower kick-panel and upper transom follow the arched opening.
    glass_shapes = [
        [(-1.84, 0.55), (-1.42, 0.55), (-1.42, 2.23), (-1.62, 2.42), (-1.84, 2.22)],
        [(-1.33, 0.55), (-0.87, 0.55), (-0.87, 2.23), (-1.10, 2.42), (-1.33, 2.23)],
        [(-0.78, 0.55), (-0.38, 0.55), (-0.38, 2.22), (-0.56, 2.39), (-0.78, 2.22)],
    ]
    for pane, shape in enumerate(glass_shapes):
        authored_xz_prism(
            name + f"_Arched_Glass_Pane_{pane + 1}",
            shape, front + 0.145, front + 0.12, mats["glass"], root,
        )
        for edge_x in (shape[0][0], shape[1][0]):
            local_path_curve(name + f"_Pane_Mullion_{pane}_{edge_x:.2f}", [
                (edge_x, front + 0.17, 0.48),
                (edge_x, front + 0.17, 2.18),
            ], mats["aluminium"], 0.018, root)

    # A side entrance with a non-square head, inset panels, handle and stone step.
    door_profile = [
        (0.72, 0.18), (1.84, 0.18), (1.84, 2.36),
        (1.62, 2.52), (0.95, 2.48), (0.72, 2.28),
    ]
    authored_xz_prism(
        name + "_Handmade_Timber_Door",
        door_profile, front + 0.10, front + 0.04, mats["wood"], root, 0.018,
    )
    for panel_z, panel_h in ((0.63, 0.56), (1.45, 0.80), (2.08, 0.30)):
        panel_profile = [
            (0.86, panel_z), (1.70, panel_z),
            (1.70, panel_z + panel_h), (0.86, panel_z + panel_h),
        ]
        authored_xz_prism(
            name + f"_Door_Raised_Panel_{panel_z:.2f}",
            panel_profile, front + 0.145, front + 0.138, mats["sand"], root,
        )
    authored_lathe(
        name + "_Door_Bronze_Handle",
        [(0.0, 0.015), (0.06, 0.024), (0.13, 0.018), (0.18, 0.010)],
        mats["brass"], root, 20,
    ).location = (1.57, front + 0.19, 1.36)
    authored_xy_slab(
        name + "_Worn_Threshold_Stone",
        [(0.55, front - 0.08), (2.02, front - 0.08), (2.08, front + 0.38),
         (1.88, front + 0.44), (0.62, front + 0.36)],
        0.03, 0.20, mats["stone"], root, 0.025,
    )

    # A painted sign fascia with individual lettering and a small side-mounted
    # swinging ticket board; no flat generic text overlay.
    fascia = [(-2.30, 2.96), (2.20, 2.96), (2.12, 3.60), (-2.22, 3.60)]
    authored_xz_prism(
        name + "_Hand_Painted_Fascia",
        fascia, front + 0.20, front + 0.12, mats["blue"], root, 0.035,
    )
    local_path_curve(name + "_Fascia_Gold_Border", [
        (-2.18, front + 0.25, 3.06), (-1.05, front + 0.25, 3.03),
        (0.90, front + 0.25, 3.03), (2.08, front + 0.25, 3.07),
        (2.08, front + 0.25, 3.49), (0.0, front + 0.25, 3.52),
        (-2.18, front + 0.25, 3.49), (-2.18, front + 0.25, 3.06),
    ], mats["brass"], 0.018, root)

    sign_data = bpy.data.curves.new(name + "_Sign_Lettering_Font", "FONT")
    sign_data.body = "MEGHNA  /  GENERAL STORE"
    sign_data.size = 0.34
    sign_data.extrude = 0.004
    sign_data.bevel_depth = 0.0015
    sign_data.align_x = "CENTER"
    sign_data.align_y = "CENTER"
    sign_text = bpy.data.objects.new(name + "_Sign_Lettering", sign_data)
    bpy.context.collection.objects.link(sign_text)
    sign_text.location = (-0.04, front + 0.27, 3.29)
    sign_text.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    sign_data.materials.append(mats["cream"])
    set_parent_local(sign_text, root)

    # Folded awning: a dense cloth-like grid with uneven sag, soft creases and
    # alternating hand-painted canvas panels. Shape keys add a restrained breeze.
    awning_cols, awning_rows = 28, 8
    awning_vertices: list[tuple[float, float, float]] = []
    awning_faces: list[tuple[int, int, int, int]] = []
    awning_width = 4.90
    awning_start_y = front + 0.25
    awning_end_y = front + 1.18
    for row in range(awning_rows + 1):
        v = row / awning_rows
        for col in range(awning_cols + 1):
            u = col / awning_cols
            local_x = -awning_width * 0.5 + awning_width * u
            local_y = awning_start_y + (awning_end_y - awning_start_y) * v
            fold = math.sin(u * math.pi * 12.0) * 0.035 * (0.30 + v)
            sag = 0.12 * math.sin(u * math.pi) + 0.05 * math.sin(v * math.pi)
            z = 3.04 - 0.44 * v - sag + fold
            awning_vertices.append((local_x, local_y, z))
    stride = awning_cols + 1
    for row in range(awning_rows):
        for col in range(awning_cols):
            a = row * stride + col
            b = a + 1
            d = (row + 1) * stride + col
            c = d + 1
            awning_faces.append((a, b, c, d))
    awning_obj = authored_mesh(
        name + "_Sculpted_Canvas_Awning",
        awning_vertices, awning_faces, mats["canvas"], root, True,
    )
    awning_obj.data.materials.append(mats["red"])
    for polygon in awning_obj.data.polygons:
        column = polygon.index % awning_cols
        polygon.material_index = 1 if column % 4 in (0, 1) else 0
    # Painted stripe panels are separate material regions; the front hem is
    # stitched as an irregular line rather than a flat rectangular valance.
    for seam in range(1, 7):
        u = seam / 7.0
        seam_x = -awning_width * 0.5 + awning_width * u
        local_path_curve(name + f"_Awning_Stitched_Seam_{seam}", [
            (seam_x, awning_start_y + 0.04, 3.00),
            (seam_x + 0.015 * math.sin(seam), (awning_start_y + awning_end_y) * 0.5, 2.77),
            (seam_x, awning_end_y - 0.035, 2.52),
        ], mats["sand"], 0.008, root)
    breeze = awning_obj.shape_key_add(name="Canvas_Gust_Anticipation", from_mix=False)
    for index, vertex in enumerate(awning_vertices):
        x_local, y_local, z_local = vertex
        u = (x_local + awning_width * 0.5) / awning_width
        v = (y_local - awning_start_y) / (awning_end_y - awning_start_y)
        breeze.data[index].co.z = z_local + 0.055 * math.sin(u * math.pi * 5.0 + v * 2.0)
    for frame, value in ((1, 0.0), (24, 1.0), (48, 0.25), (72, 0.0), (289, 0.4)):
        breeze.value = value
        breeze.keyframe_insert(data_path="value", frame=frame, group="Awning_Wind_Performance")
    awning_keys = awning_obj.data.shape_keys
    if awning_keys and awning_keys.animation_data and awning_keys.animation_data.action:
        awning_action = awning_keys.animation_data.action
        awning_action.name = "MEGHNA_STORE_CANVAS_GUST"
        # Blender 5.2 uses layered/slotted Actions; the legacy Action.fcurves
        # collection is absent. Preserve keyed Bezier performance natively on
        # the new API, and refine handles only on Blender versions exposing it.
        try:
            awning_curves = awning_action.fcurves
        except AttributeError:
            print("AWNING_CURVE_API_NOTE: Blender layered Action; native shape-key interpolation retained.")
        else:
            for curve in awning_curves:
                for point in curve.keyframe_points:
                    point.interpolation = "BEZIER"
                    point.handle_left_type = "AUTO_CLAMPED"
                    point.handle_right_type = "AUTO_CLAMPED"

    # Scalloped edge is a hand-drawn curve with a different drop per panel.
    scallop_points = []
    for index in range(25):
        u = index / 24.0
        scallop_points.append((
            -awning_width * 0.5 + awning_width * u,
            awning_end_y + 0.01,
            2.42 - 0.035 * math.sin(u * math.pi * 12.0),
        ))
    local_path_curve(name + "_Scalloped_Canvas_Valance", scallop_points, mats["red"], 0.055, root)
    for side in (-1, 1):
        local_path_curve(name + f"_Forged_Awning_Support_{side}", [
            (side * 2.36, front + 0.22, 3.00),
            (side * 2.48, front + 0.50, 2.80),
            (side * 2.48, front + 0.92, 2.64),
        ], mats["aluminium"], 0.032, root)

    # Upper windows: individually arched openings with thick plaster reveals,
    # hand-bent grilles, drainage sills and sun-faded shutters.
    for index, cx in enumerate((-1.62, 0.02, 1.60)):
        z0 = 4.66 + (0.06 if index == 1 else 0.0)
        arch = [
            (cx - 0.48, z0 - 0.66), (cx + 0.48, z0 - 0.66),
            (cx + 0.48, z0 + 0.22), (cx + 0.33, z0 + 0.48),
            (cx, z0 + 0.62), (cx - 0.34, z0 + 0.47),
            (cx - 0.48, z0 + 0.20),
        ]
        authored_xz_prism(
            name + f"_Upper_Arched_Window_{index}",
            arch, front + 0.085, front + 0.035, mats["glass"], root,
        )
        local_path_curve(name + f"_Upper_Window_Stone_Arch_{index}", [
            (cx - 0.56, front + 0.14, z0 - 0.68),
            (cx - 0.56, front + 0.14, z0 + 0.20),
            (cx - 0.35, front + 0.14, z0 + 0.52),
            (cx, front + 0.14, z0 + 0.72),
            (cx + 0.35, front + 0.14, z0 + 0.52),
            (cx + 0.56, front + 0.14, z0 + 0.20),
            (cx + 0.56, front + 0.14, z0 - 0.68),
        ], mats["stone"], 0.065, root)
        for bar in (-0.24, 0.0, 0.24):
            local_path_curve(name + f"_Window_Grille_{index}_{bar:.2f}", [
                (cx + bar, front + 0.17, z0 - 0.60),
                (cx + bar, front + 0.17, z0 + 0.36),
            ], mats["aluminium"], 0.014, root)
        local_path_curve(name + f"_Window_Crossbar_{index}", [
            (cx - 0.45, front + 0.17, z0 - 0.02),
            (cx, front + 0.17, z0 - 0.06),
            (cx + 0.45, front + 0.17, z0 - 0.02),
        ], mats["aluminium"], 0.017, root)

    # A curved upper balcony with a hand-forged rail, tapered spindles and a
    # central cast-iron floral medallion, unique to this corner elevation.
    balcony_contour = [
        (-1.75, front + 0.05), (1.76, front + 0.05),
        (1.68, front + 0.35), (1.44, front + 0.63),
        (1.08, front + 0.82), (0.55, front + 0.95),
        (0.0, front + 1.00), (-0.58, front + 0.95),
        (-1.10, front + 0.80), (-1.48, front + 0.56),
        (-1.70, front + 0.28),
    ]
    authored_xy_slab(
        name + "_Curved_Balcony_Stone_Deck",
        balcony_contour, 4.12, 4.30, mats["concrete"], root, 0.035,
    )
    rail_points = [
        (-1.68, front + 0.08, 4.98), (-1.46, front + 0.42, 4.99),
        (-1.10, front + 0.69, 5.00), (-0.54, front + 0.90, 5.02),
        (0.0, front + 0.95, 5.04), (0.56, front + 0.89, 5.02),
        (1.11, front + 0.68, 5.00), (1.48, front + 0.38, 4.99),
        (1.68, front + 0.08, 4.98),
    ]
    local_path_curve(name + "_Forged_Balcony_Handrail", rail_points, mats["brass"], 0.042, root)
    for index in range(17):
        u = index / 16.0
        px = -1.62 + 3.24 * u
        py = front + 0.10 + 0.83 * math.sin(math.pi * u)
        top_z = 4.96 + 0.08 * math.sin(math.pi * u)
        local_path_curve(name + f"_Forged_Baluster_{index:02d}", [
            (px, py, 4.34), (px, py + 0.012, 4.54),
            (px + 0.025 * math.sin(u * math.tau), py, 4.75),
            (px, py, top_z),
        ], mats["aluminium"], 0.019 if index % 2 else 0.026, root)
    local_path_curve(name + "_Balcony_Floral_Spiral_Left", [
        (-0.45, front + 0.91, 4.55), (-0.30, front + 0.91, 4.71),
        (-0.10, front + 0.91, 4.60), (-0.23, front + 0.91, 4.47),
        (-0.38, front + 0.91, 4.55),
    ], mats["brass"], 0.027, root)
    local_path_curve(name + "_Balcony_Floral_Spiral_Right", [
        (0.45, front + 0.91, 4.55), (0.30, front + 0.91, 4.71),
        (0.10, front + 0.91, 4.60), (0.23, front + 0.91, 4.47),
        (0.38, front + 0.91, 4.55),
    ], mats["brass"], 0.027, root)

    # Shop interior: deep shelves, folded awnings of stock, tea jars, rice sacks
    # and warm practical light visible through the arched glazing.
    for shelf, z in enumerate((0.82, 1.30, 1.83)):
        local_path_curve(name + f"_Interior_Wood_Shelf_{shelf}", [
            (-1.74, front - 0.32, z), (-1.15, front - 0.35, z - 0.015),
            (-0.54, front - 0.32, z),
        ], mats["wood"], 0.052, root)
        for jar in range(4):
            jx = -1.65 + jar * 0.27
            jar_obj = authored_lathe(
                name + f"_Tea_Jar_{shelf}_{jar}",
                [(0.0, 0.055), (0.07, 0.075), (0.25, 0.078),
                 (0.31, 0.060), (0.34, 0.045)],
                mats["warm_glass"], root, 18,
            )
            jar_obj.location = (jx, front - 0.31, z + 0.035)
        for bag in range(3):
            bx = 0.18 + bag * 0.38
            sack_profile = [
                (0.0, 0.14), (0.07, 0.19), (0.24, 0.18),
                (0.42, 0.11), (0.47, 0.045),
            ]
            bag_obj = authored_lathe(
                name + f"_Rice_Sack_{shelf}_{bag}",
                sack_profile, mats["canvas"] if bag % 2 else mats["sand"], root, 24, 0.05,
            )
            bag_obj.location = (bx, front - 0.31, z + 0.04)
    for side in (-1, 1):
        local_path_curve(name + f"_Interior_Support_Post_{side}", [
            (side * 0.14, front - 0.18, 0.45),
            (side * 0.14, front - 0.18, 2.70),
        ], mats["wood"], 0.055, root)

    # The projecting balcony underside carries damp streaks, chipped paint and
    # irregular mineral deposits rather than a uniformly clean grey surface.
    for streak in range(13):
        sx = -2.05 + streak * 0.32
        length = 0.22 + (streak % 4) * 0.12
        local_path_curve(name + f"_Rain_Stain_{streak:02d}", [
            (sx, front + 0.015, 3.88),
            (sx + 0.025 * math.sin(streak), front + 0.018, 3.88 - length * 0.5),
            (sx - 0.018 * math.cos(streak), front + 0.020, 3.88 - length),
        ], mats["brick"] if streak % 3 else mats["stone"], 0.012 + (streak % 3) * 0.003, root)

    # The roof tank is turned from an irregular profile with ring ribs; thin
    # pipework, cable clips and an old antenna make the roof feel inhabited.
    tank_profile = [
        (0.0, 0.45), (0.08, 0.56), (0.22, 0.59), (0.34, 0.54),
        (0.98, 0.50), (1.08, 0.58), (1.16, 0.55), (1.24, 0.42),
    ]
    tank = authored_lathe(
        name + "_Ribbed_Poly_Water_Tank",
        tank_profile, mats["tank"], root, 64, 0.028,
    )
    tank.location = (1.55, back + 0.55, 7.52)
    cap = authored_lathe(
        name + "_Water_Tank_Collar",
        [(0.0, 0.50), (0.05, 0.57), (0.12, 0.54), (0.15, 0.42)],
        mats["aluminium"], root, 48,
    )
    cap.location = (1.55, back + 0.55, 8.69)
    local_path_curve(name + "_Roof_Feed_Pipe", [
        (1.55, back + 0.55, 7.56), (1.30, back + 0.30, 6.95),
        (1.22, back + 0.26, 5.85), (1.22, back + 0.26, 0.25),
    ], mats["aluminium"], 0.038, root)
    local_path_curve(name + "_Roof_Telephone_Cable", [
        (-2.45, back + 0.18, 7.20), (-1.70, back + 0.10, 7.55),
        (-0.82, back + 0.08, 7.33), (0.12, back + 0.12, 7.52),
        (1.20, back + 0.18, 7.31),
    ], mats["dark"], 0.018, root)

    root["placement_rule"] = "root_at_authored_shariatpur_block_coordinate;children_in_local_space"
    root["asset_role"] = "hero_local_corner_store"
    root["art_method"] = "hand_authored_mesh_profiles;arched_recesses;curved_balcony;cloth_grid;lathed_utility_assets;visible_shop_interior"
    root["silhouette_review"] = "irregular_roofline;offset_upper_openings;curved_awning;deep_balcony"
    root["surface_story"] = "sun_fade;rain_streaks;mineral_deposits;worn_stone;painted_signage"
    root["animation"] = "cloth_awning_gust;secondary_sign_and_fabric_motion"
    print("CRAFTED_HERO_BUILDING_READY:", json.dumps({
        "name": root.name,
        "method": root["art_method"],
        "visible_interior": True,
        "animated_awning": True,
        "facade_profile_points": len(body_contour),
    }, sort_keys=True))
    return root


def add_handcrafted_cng(
    name: str,
    x: float,
    y: float,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """A locally modelled Bangladesh three-wheeler with custom shell, cloth, wheels and rigged motion."""
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0.0)

    # The lower body is an extruded hand-drawn side elevation. Upper body mass
    # is deliberately interrupted around the passenger opening and windscreen.
    side_profile = [
        (-1.34, 0.33), (-1.30, 0.72), (-1.12, 0.95), (-0.76, 1.02),
        (-0.30, 1.00), (0.12, 0.93), (0.45, 0.96), (0.77, 1.22),
        (1.14, 1.18), (1.42, 0.92), (1.48, 0.52), (1.22, 0.36),
        (0.50, 0.30), (-0.45, 0.29),
    ]
    authored_xz_prism(
        name + "_Sculpted_Lower_Body_Shell",
        side_profile, 0.56, -0.56, mats["cng_green"], root, 0.035,
    )

    # A lower sill is a separate formed panel with a shallow belly and wheel
    # clearance cut into its silhouette.
    sill_profile = [
        (-1.25, 0.48), (-1.02, 0.42), (-0.72, 0.47), (-0.50, 0.58),
        (0.20, 0.56), (0.55, 0.48), (1.25, 0.53), (1.35, 0.62),
        (0.91, 0.70), (0.40, 0.72), (-0.43, 0.70), (-0.94, 0.66),
    ]
    authored_xz_prism(
        name + "_Lower_Handformed_Sill",
        sill_profile, 0.585, -0.585, mats["cng_dark"], root, 0.018,
    )

    # A shaped bonnet and front apron create an identifiable nose, rather than
    # a rectangular body with a flat front face.
    bonnet_profile = [
        (0.70, 0.62), (1.42, 0.63), (1.56, 0.76), (1.48, 1.06),
        (1.24, 1.29), (0.96, 1.32), (0.78, 1.12),
    ]
    authored_xz_prism(
        name + "_Sloped_Front_Bonnet",
        bonnet_profile, 0.47, -0.47, mats["cng_green_light"], root, 0.026,
    )
    apron_profile = [
        (1.31, 0.38), (1.56, 0.42), (1.58, 0.88),
        (1.47, 1.03), (1.31, 0.88),
    ]
    authored_xz_prism(
        name + "_Front_Apron_Stamped_Panel",
        apron_profile, 0.44, -0.44, mats["cng_dark"], root, 0.018,
    )

    # Raised front crease, lower character lines and enamel piping catch the
    # sunset key in a way a toy-green block cannot.
    for side in (-1, 1):
        local_path_curve(name + f"_Bonnet_Crease_{side}", [
            (0.78, side * 0.478, 1.13),
            (1.02, side * 0.482, 1.22),
            (1.30, side * 0.445, 1.04),
            (1.48, side * 0.425, 0.80),
        ], mats["cream"], 0.018, root)
        local_path_curve(name + f"_Side_Enamel_Pinstripe_{side}", [
            (-1.17, side * 0.575, 0.78),
            (-0.78, side * 0.590, 0.73),
            (-0.18, side * 0.592, 0.76),
            (0.42, side * 0.590, 0.78),
            (0.83, side * 0.555, 0.92),
        ], mats["cream"], 0.020, root)
        local_path_curve(name + f"_Side_Upper_Beltline_{side}", [
            (-1.05, side * 0.565, 0.98),
            (-0.42, side * 0.565, 1.00),
            (0.14, side * 0.55, 0.99),
        ], mats["brass"], 0.014, root)

    # Passenger cabin is an open architectural frame. The seat, footwell and
    # inner trim remain visible through the sides; no solid box closes it.
    floor_contour = [
        (-1.22, -0.52), (0.48, -0.52), (0.74, -0.38),
        (0.82, 0.30), (0.48, 0.49), (-1.18, 0.49),
        (-1.31, 0.26),
    ]
    authored_xy_slab(
        name + "_Passenger_Footwell_Stamped_Floor",
        floor_contour, 0.72, 0.83, mats["dark"], root, 0.028,
    )
    seat_profile = [
        (-1.10, 0.86), (-0.26, 0.86), (-0.13, 1.05),
        (-0.24, 1.23), (-0.92, 1.25), (-1.12, 1.08),
    ]
    authored_xz_prism(
        name + "_Rear_Bench_Cushion",
        seat_profile, 0.39, -0.39, mats["canvas"], root, 0.075,
    )
    backrest_profile = [
        (-1.12, 1.04), (-0.90, 1.10), (-0.86, 1.58),
        (-0.98, 1.72), (-1.27, 1.61), (-1.31, 1.27),
    ]
    authored_xz_prism(
        name + "_Rear_Bench_Backrest",
        backrest_profile, 0.41, -0.41, mats["canvas"], root, 0.055,
    )
    for seam in (-0.72, -0.26, 0.22):
        local_path_curve(name + f"_Seat_Stitch_{seam:.2f}", [
            (seam, -0.408, 0.94),
            (seam + 0.025, -0.409, 1.03),
            (seam, -0.408, 1.14),
        ], mats["sand"], 0.007, root)
    for side in (-1, 1):
        local_path_curve(name + f"_Passenger_Grab_Rail_{side}", [
            (-1.18, side * 0.58, 0.92),
            (-0.92, side * 0.62, 1.14),
            (-0.42, side * 0.62, 1.12),
            (0.12, side * 0.60, 1.04),
        ], mats["aluminium"], 0.032, root)
        local_path_curve(name + f"_Doorway_Entry_Trim_{side}", [
            (-1.20, side * 0.60, 0.86),
            (-1.14, side * 0.62, 1.52),
            (-0.91, side * 0.62, 1.66),
        ], mats["brass"], 0.024, root)

    # Instrument cowl and driver controls are modelled as separate objects.
    dash_profile = [
        (0.48, 1.02), (0.92, 1.07), (1.03, 1.23),
        (0.91, 1.37), (0.57, 1.31),
    ]
    authored_xz_prism(
        name + "_Driver_Dashboard_Cowl",
        dash_profile, 0.39, -0.39, mats["cng_dark"], root, 0.034,
    )
    local_path_curve(name + "_Steering_Column", [
        (0.48, -0.015, 1.14), (0.40, -0.015, 1.45), (0.28, -0.015, 1.54),
    ], mats["aluminium"], 0.036, root)
    local_path_curve(name + "_Steering_Handlebar", [
        (0.12, -0.30, 1.55), (0.28, -0.015, 1.56), (0.12, 0.30, 1.55),
    ], mats["dark"], 0.035, root)
    for side in (-1, 1):
        local_path_curve(name + f"_Brake_Lever_{side}", [
            (0.18, side * 0.25, 1.55),
            (0.02, side * 0.36, 1.49),
            (-0.08, side * 0.43, 1.42),
        ], mats["aluminium"], 0.012, root)

    # Windscreen is a curved, slanted custom panel across the vehicle width,
    # with separate laminated glass and a four-sided aluminium frame.
    windscreen_vertices = [
        (0.84, -0.435, 1.18), (1.10, -0.435, 1.72),
        (1.10, 0.435, 1.72), (0.84, 0.435, 1.18),
        (0.86, -0.415, 1.18), (1.12, -0.415, 1.72),
        (1.12, 0.415, 1.72), (0.86, 0.415, 1.18),
    ]
    windscreen_faces = [
        (0, 1, 2, 3), (4, 7, 6, 5),
        (0, 4, 5, 1), (1, 5, 6, 2),
        (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    authored_mesh(
        name + "_Laminated_Windscreen",
        windscreen_vertices, windscreen_faces, mats["glass"], root, True,
    )
    local_path_curve(name + "_Windscreen_Upper_Frame", [
        (1.10, -0.45, 1.73), (1.115, 0.0, 1.76), (1.10, 0.45, 1.73),
    ], mats["aluminium"], 0.033, root)
    local_path_curve(name + "_Windscreen_Lower_Frame", [
        (0.84, -0.46, 1.18), (0.84, 0.0, 1.15), (0.84, 0.46, 1.18),
    ], mats["dark"], 0.030, root)

    # Curved canopy support arches and the hand-formed roof skin are distinct.
    for side in (-1, 1):
        local_path_curve(name + f"_Canopy_A_Pillar_{side}", [
            (0.84, side * 0.53, 1.13),
            (0.76, side * 0.56, 1.52),
            (0.40, side * 0.62, 1.92),
        ], mats["dark"], 0.038, root)
        local_path_curve(name + f"_Canopy_Rear_Post_{side}", [
            (-1.18, side * 0.53, 0.99),
            (-1.11, side * 0.60, 1.43),
            (-0.88, side * 0.66, 1.91),
        ], mats["dark"], 0.036, root)
        local_path_curve(name + f"_Canopy_Side_Bow_{side}", [
            (-1.15, side * 0.63, 1.90),
            (-0.46, side * 0.66, 2.01),
            (0.34, side * 0.63, 2.00),
        ], mats["aluminium"], 0.024, root)
    # Three transverse bows follow a slight crown to shed rain.
    for bow, bx in enumerate((-0.98, -0.32, 0.30)):
        local_path_curve(name + f"_Canopy_Transverse_Bow_{bow}", [
            (bx, -0.65, 1.93),
            (bx + 0.08, 0.0, 2.10),
            (bx, 0.65, 1.93),
        ], mats["dark"], 0.023, root)

    canopy_cols, canopy_rows = 26, 12
    canopy_vertices: list[tuple[float, float, float]] = []
    canopy_faces: list[tuple[int, int, int, int]] = []
    canopy_length, canopy_width = 1.68, 1.36
    for row in range(canopy_rows + 1):
        v = row / canopy_rows
        for col in range(canopy_cols + 1):
            u = col / canopy_cols
            local_x = -1.08 + canopy_length * u
            local_y = -canopy_width * 0.5 + canopy_width * v
            crown = 0.13 * math.cos((v - 0.5) * math.pi)
            long_sag = 0.045 * math.sin(math.pi * u)
            folds = 0.018 * math.sin(u * math.pi * 10.0 + v * 4.5)
            canopy_vertices.append((local_x, local_y, 1.96 + crown - long_sag + folds))
    stride = canopy_cols + 1
    for row in range(canopy_rows):
        for col in range(canopy_cols):
            a = row * stride + col
            b = a + 1
            d = (row + 1) * stride + col
            cc = d + 1
            canopy_faces.append((a, b, cc, d))
    canopy_obj = authored_mesh(
        name + "_Sculpted_Canvas_Roof",
        canopy_vertices, canopy_faces, mats["canvas"], root, True,
    )
    canopy_obj.data.materials.append(mats["red"])
    for poly in canopy_obj.data.polygons:
        col = poly.index % canopy_cols
        poly.material_index = 1 if col % 6 in (0, 1) else 0
    gust = canopy_obj.shape_key_add(name="CNG_Canopy_Gust", from_mix=False)
    for index, vertex in enumerate(canopy_vertices):
        px, py, pz = vertex
        gust.data[index].co.z = pz + 0.04 * math.sin(px * 6.0 + py * 4.0)
    for frame, value in ((1, 0.0), (62, 0.85), (120, 0.2), (184, 0.7), (288, 0.0)):
        gust.value = value
        gust.keyframe_insert(data_path="value", frame=frame, group="CNG_Canopy_Wind")
    if canopy_obj.data.shape_keys and canopy_obj.data.shape_keys.animation_data:
        action = canopy_obj.data.shape_keys.animation_data.action
        if action:
            action.name = "CNG_CANOPY_WIND_PERFORMANCE"

    local_path_curve(name + "_Canopy_Front_Seam", [
        (0.62, -0.68, 1.91), (0.73, 0.0, 2.03), (0.62, 0.68, 1.91),
    ], mats["sand"], 0.010, root)
    local_path_curve(name + "_Canopy_Rear_Valance", [
        (-1.10, -0.68, 1.88), (-1.22, -0.32, 1.90),
        (-1.24, 0.0, 1.91), (-1.22, 0.32, 1.90),
        (-1.10, 0.68, 1.88),
    ], mats["red"], 0.042, root)

    # Hand-built three-wheel set: each tyre is a toroidal mesh with a layered
    # sidewall, tread blocks and independent axle pivot. Wheels are not
    # displaced cylinders, and their rotation follows the long street pass.
    def make_treaded_tyre(wheel_parent: bpy.types.Object, wheel_name: str) -> bpy.types.Object:
        major_radius, tube_radius = 0.325, 0.058
        segments, cross_segments = 72, 16
        vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int, int]] = []
        for ring in range(segments):
            theta = math.tau * ring / segments
            for cross in range(cross_segments):
                phi = math.tau * cross / cross_segments
                radial = major_radius + tube_radius * math.cos(phi)
                vertices.append((
                    radial * math.cos(theta),
                    tube_radius * math.sin(phi),
                    radial * math.sin(theta),
                ))
        for ring in range(segments):
            next_ring = (ring + 1) % segments
            for cross in range(cross_segments):
                next_cross = (cross + 1) % cross_segments
                a = ring * cross_segments + cross
                b = next_ring * cross_segments + cross
                cc = next_ring * cross_segments + next_cross
                d = ring * cross_segments + next_cross
                faces.append((a, b, cc, d))
        tyre = authored_mesh(
            wheel_name + "_Sculpted_Tyre_Torus",
            vertices, faces, mats["rubber"], wheel_parent, True,
        )
        tyre["tire_geometry"] = "hand_tessellated_torus;72x16_segments"
        return tyre

    wheel_specs = [
        ("Front", (1.10, 0.0, 0.375), True),
        ("Rear_Near", (-0.91, -0.55, 0.375), False),
        ("Rear_Far", (-0.91, 0.55, 0.375), False),
    ]
    wheel_pivots: list[bpy.types.Object] = []
    for wheel_index, (label, position, is_front) in enumerate(wheel_specs):
        steering = bpy.data.objects.new(name + f"_{label}_Steering_Pivot", None)
        bpy.context.collection.objects.link(steering)
        steering.location = position
        set_parent_local(steering, root)

        axle = bpy.data.objects.new(name + f"_{label}_Axle_Rotation", None)
        bpy.context.collection.objects.link(axle)
        set_parent_local(axle, steering)
        make_treaded_tyre(axle, name + f"_{label}_Tyre")
        wheel_pivots.append(axle)

        # Forged sidewall rings and a machined multi-part hub face.
        for side in (-1, 1):
            rim = authored_lathe(
                name + f"_{label}_Rim_{side}",
                [(0.0, 0.19), (0.035, 0.24), (0.075, 0.27),
                 (0.11, 0.245), (0.145, 0.18), (0.17, 0.12)],
                mats["aluminium"], axle, 56,
            )
            rim.rotation_euler[0] = math.pi * 0.5
            rim.location = (0.0, side * 0.035, 0.0)
            cap = authored_lathe(
                name + f"_{label}_Brass_Hub_Cap_{side}",
                [(0.0, 0.055), (0.025, 0.092), (0.060, 0.078), (0.085, 0.04)],
                mats["brass"], axle, 32,
            )
            cap.rotation_euler[0] = math.pi * 0.5
            cap.location = (0.0, side * 0.16, 0.0)
            for spoke in range(10):
                angle = math.tau * spoke / 10.0
                local_path_curve(name + f"_{label}_Spoke_{side}_{spoke}", [
                    (0.065 * math.cos(angle), side * 0.145, 0.065 * math.sin(angle)),
                    (0.235 * math.cos(angle + 0.08), side * 0.145, 0.235 * math.sin(angle + 0.08)),
                ], mats["aluminium"], 0.012, axle)

        # Raised tread bars are one custom mesh with curved angular segments.
        tread_vertices: list[tuple[float, float, float]] = []
        tread_faces: list[tuple[int, int, int, int]] = []
        tread_count = 44
        for tread in range(tread_count):
            theta = math.tau * tread / tread_count
            half_angle = 0.032
            r_outer = 0.385
            r_inner = 0.355
            y_half = 0.040
            points = []
            for r, a, yy in (
                (r_inner, theta - half_angle, -y_half),
                (r_inner, theta - half_angle, y_half),
                (r_inner, theta + half_angle, y_half),
                (r_inner, theta + half_angle, -y_half),
                (r_outer, theta - half_angle, -y_half),
                (r_outer, theta - half_angle, y_half),
                (r_outer, theta + half_angle, y_half),
                (r_outer, theta + half_angle, -y_half),
            ):
                points.append((r * math.cos(a), yy, r * math.sin(a)))
            base = len(tread_vertices)
            tread_vertices.extend(points)
            tread_faces.extend([
                (base + 4, base + 5, base + 6, base + 7),
                (base + 0, base + 1, base + 5, base + 4),
                (base + 1, base + 2, base + 6, base + 5),
                (base + 2, base + 3, base + 7, base + 6),
                (base + 3, base + 0, base + 4, base + 7),
            ])
        tread_obj = authored_mesh(
            name + f"_{label}_Tread_Blocks",
            tread_vertices, tread_faces, mats["rubber"], axle, False,
        )
        tread_obj["tread_count"] = tread_count

        axle.rotation_mode = "XYZ"
        axle.rotation_euler = (0.0, 0.0, 0.0)
        axle.keyframe_insert(data_path="rotation_euler", frame=1, group=f"CNG_{label}_Wheel_Rotation")
        axle.rotation_euler[1] = -math.tau * 15.0
        axle.keyframe_insert(data_path="rotation_euler", frame=288, group=f"CNG_{label}_Wheel_Rotation")
        if axle.animation_data and axle.animation_data.action:
            axle.animation_data.action.name = f"CNG_{label}_WHEEL_PERFORMANCE"

        if is_front:
            steering.rotation_euler[2] = 0.0
            steering.keyframe_insert(data_path="rotation_euler", frame=1, group="CNG_Front_Steering")
            steering.rotation_euler[2] = math.radians(3.5)
            steering.keyframe_insert(data_path="rotation_euler", frame=108, group="CNG_Front_Steering")
            steering.rotation_euler[2] = math.radians(-2.0)
            steering.keyframe_insert(data_path="rotation_euler", frame=216, group="CNG_Front_Steering")
            steering.rotation_euler[2] = 0.0
            steering.keyframe_insert(data_path="rotation_euler", frame=288, group="CNG_Front_Steering")

    # Front mudguard and fork are shaped as independent curves and mesh flares.
    front_fender_points = []
    for i in range(25):
        angle = math.pi * i / 24.0
        front_fender_points.append((
            1.10 + 0.435 * math.cos(angle),
            -0.16,
            0.375 + 0.435 * math.sin(angle),
        ))
    local_path_curve(name + "_Front_Wheel_Mudguard", front_fender_points, mats["cng_green_light"], 0.062, root)
    local_path_curve(name + "_Front_Fork_Left", [
        (1.06, -0.14, 0.79), (1.12, -0.18, 0.55), (1.10, -0.18, 0.38),
    ], mats["aluminium"], 0.035, root)
    local_path_curve(name + "_Front_Fork_Right", [
        (1.06, 0.14, 0.79), (1.12, 0.18, 0.55), (1.10, 0.18, 0.38),
    ], mats["aluminium"], 0.035, root)

    # Front lighting is a small assembly of lathed housings and glass lenses.
    for side in (-1, 1):
        lamp_housing = authored_lathe(
            name + f"_Headlamp_Housing_{side}",
            [(0.0, 0.11), (0.04, 0.16), (0.12, 0.17), (0.18, 0.13), (0.20, 0.08)],
            mats["aluminium"], root, 36,
        )
        lamp_housing.rotation_euler[1] = math.pi * 0.5
        lamp_housing.location = (1.53, side * 0.29, 0.88)
        lens = authored_lathe(
            name + f"_Warm_Headlamp_Lens_{side}",
            [(0.0, 0.07), (0.018, 0.125), (0.028, 0.14)],
            mats["lamp"], root, 36,
        )
        lens.rotation_euler[1] = math.pi * 0.5
        lens.location = (1.70, side * 0.29, 0.88)

    # Side mirrors, grab handles and rear lamps are attached to the real cabin
    # structure; their geometry follows body movement and wind response.
    for side in (-1, 1):
        local_path_curve(name + f"_Mirror_Stem_{side}", [
            (0.88, side * 0.46, 1.49),
            (0.98, side * 0.62, 1.72),
            (1.04, side * 0.70, 1.78),
        ], mats["aluminium"], 0.018, root)
        mirror = authored_lathe(
            name + f"_Side_Mirror_Frame_{side}",
            [(0.0, 0.10), (0.04, 0.14), (0.09, 0.13), (0.12, 0.08)],
            mats["dark"], root, 28,
        )
        mirror.rotation_euler[0] = math.pi * 0.5
        mirror.location = (1.04, side * 0.70, 1.80)

        local_path_curve(name + f"_Rear_Lamp_Bezel_{side}", [
            (-1.28, side * 0.52, 0.68), (-1.31, side * 0.56, 0.85),
            (-1.10, side * 0.56, 0.89),
        ], mats["red"], 0.036, root)

    # Hand-painted side medallion and registration panel.
    side_plate = [
        [(-0.80, 0.78), (0.28, 0.78), (0.38, 0.90), (0.25, 1.00), (-0.75, 0.98)],
    ]
    authored_xz_prism(
        name + "_Side_Enamel_Registration_Badge",
        side_plate[0], 0.592, 0.616, mats["cream"], root, 0.012,
    )
    name_data = bpy.data.curves.new(name + "_Side_Brand_Font", "FONT")
    name_data.body = "SHARIATPUR"
    name_data.size = 0.14
    name_data.extrude = 0.0015
    name_data.align_x = "CENTER"
    name_text = bpy.data.objects.new(name + "_Side_Brand_Lettering", name_data)
    bpy.context.collection.objects.link(name_text)
    name_text.location = (-0.24, 0.625, 0.85)
    name_text.rotation_euler = (-math.pi * 0.5, 0.0, 0.0)
    name_data.materials.append(mats["blue"])
    set_parent_local(name_text, root)

    # Secondary suspension response: chassis roll, pitch and vertical settle
    # are independent of wheel rotation and are not a generic constant bob.
    root.rotation_mode = "XYZ"
    for frame, pitch, roll in (
        (1, 0.0, 0.0), (72, math.radians(-0.8), math.radians(0.4)),
        (108, math.radians(0.5), math.radians(-0.6)),
        (144, 0.0, 0.0), (216, math.radians(-0.4), math.radians(0.3)),
        (288, 0.0, 0.0),
    ):
        root.rotation_euler = (pitch, 0.0, roll)
        root.keyframe_insert(data_path="rotation_euler", frame=frame, group="CNG_Suspension_Body_Performance")

    root["asset_role"] = "Bangladesh_three_wheel_CNG_hero"
    root["geometry_method"] = "hand_drawn_side_profiles;custom_treaded_torus_wheels;curved_tubular_frame;sculpted_cloth_roof"
    root["wheel_layout"] = "single_front_steer;dual_rear_drive"
    root["wheel_count"] = 3
    root["tread_blocks_per_wheel"] = 44
    root["secondary_animation"] = "independent_wheel_rotation;front_steer;canopy_gust;body_pitch_roll_settle"
    root["material_story"] = "emerald_enamel;cream_pinstripe;matte_tread;anodised_alloy;weathered_canvas"
    return root


def add_handcrafted_launch(
    name: str,
    x: float,
    y: float,
    z: float,
    mats: dict[str, bpy.types.Material],
) -> bpy.types.Object:
    """A custom multi-station river launch with buoyant hull, cabin apertures and wake performance."""
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, z)

    # The hull is a lofted series of changing transverse stations. Each station
    # carries keel, bilge, chine and gunwale points, creating a pointed bow and
    # a broader, lower stern instead of a rectangular box.
    stations = [
        (-2.72, 0.10, -0.36, 0.12, 0.56),
        (-2.30, 0.42, -0.38, 0.02, 0.58),
        (-1.60, 0.68, -0.39, -0.04, 0.60),
        (-0.50, 0.82, -0.38, -0.06, 0.62),
        (0.80, 0.80, -0.34, 0.00, 0.66),
        (1.75, 0.70, -0.27, 0.10, 0.72),
        (2.48, 0.50, -0.18, 0.24, 0.82),
    ]
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    section_points = [
        (0.00, 0.00), (0.52, 0.30), (0.96, 0.73),
        (1.00, 1.00), (-1.00, 1.00), (-0.96, 0.73),
        (-0.52, 0.30),
    ]
    for station_x, half_width, keel_z, chine_z, deck_z in stations:
        for lateral, height_blend in section_points:
            y_pos = lateral * half_width
            if abs(lateral) < 0.01:
                z_pos = keel_z
            elif abs(lateral) < 0.6:
                z_pos = keel_z + (chine_z - keel_z) * (height_blend / 0.30)
            elif abs(lateral) < 0.99:
                z_pos = chine_z
            else:
                z_pos = deck_z
            vertices.append((station_x, y_pos, z_pos))
    ring_size = len(section_points)
    for station in range(len(stations) - 1):
        for point in range(ring_size):
            a = station * ring_size + point
            b = station * ring_size + (point + 1) % ring_size
            cc = (station + 1) * ring_size + (point + 1) % ring_size
            d = (station + 1) * ring_size + point
            faces.append((a, b, cc, d))
    faces.append(tuple(range(ring_size - 1, -1, -1)))
    last = (len(stations) - 1) * ring_size
    faces.append(tuple(last + i for i in range(ring_size)))
    hull = authored_mesh(name + "_Lofted_Meghna_Hull", vertices, faces, mats["blue"], root, True)
    hull["hull_method"] = "seven_variable_breadth_stations;bilge_chine_keel_gunwale_loft"
    hull["waterline_target"] = -0.31

    # The strakes follow the chine and waterline, with a raised bow edge and a
    # darker lower boot stripe to show the hull's immersion and wear history.
    for side in (-1, 1):
        chine_points = [
            (sx, side * (width - 0.025), cz)
            for sx, width, kz, cz, dz in stations[1:-1]
        ]
        local_path_curve(name + f"_Hull_Chine_Strake_{side}", chine_points, mats["aluminium"], 0.026, root)
        waterline_points = [
            (sx, side * (width - 0.012), kz + (cz - kz) * 0.36)
            for sx, width, kz, cz, dz in stations[1:-1]
        ]
        local_path_curve(name + f"_Hull_Boot_Stripe_{side}", waterline_points, mats["cng_dark"], 0.030, root)
        rub_rail = [
            (sx, side * (width - 0.035), dz + 0.055)
            for sx, width, kz, cz, dz in stations[1:-1]
        ]
        local_path_curve(name + f"_Upper_Rubbing_Strake_{side}", rub_rail, mats["cream"], 0.022, root)

    # Hand-shaped deck plan, raised gunwale lips and a worn bow landing area.
    deck_outline = [
        (-2.48, -0.34), (-2.18, -0.54), (-1.50, -0.76), (-0.50, -0.84),
        (0.75, -0.80), (1.65, -0.69), (2.35, -0.48), (2.47, 0.0),
        (2.35, 0.48), (1.65, 0.69), (0.75, 0.80), (-0.50, 0.84),
        (-1.50, 0.76), (-2.18, 0.54), (-2.48, 0.34),
    ]
    authored_xy_slab(
        name + "_Shaped_Deck_Planking",
        deck_outline, 0.54, 0.66, mats["wood"], root, 0.028,
    )
    for side in (-1, 1):
        local_path_curve(name + f"_Bow_Gunwale_{side}", [
            (-2.58, side * 0.18, 0.62),
            (-2.20, side * 0.53, 0.66),
            (-1.45, side * 0.75, 0.67),
            (-0.45, side * 0.82, 0.66),
            (0.85, side * 0.78, 0.68),
            (1.78, side * 0.66, 0.75),
            (2.40, side * 0.45, 0.86),
        ], mats["aluminium"], 0.034, root)

    # Cabin lower wall panels, built around open window bands. Each glazing
    # aperture remains a real opening with a separate framed glass surface.
    for side in (-1, 1):
        lower_side = [
            [(-1.52, 0.70), (0.58, 0.70), (0.58, 1.14), (-1.52, 1.14)],
        ]
        authored_xz_prism(
            name + f"_Cabin_Side_Lower_Panel_{side}",
            lower_side[0], side * 0.50, side * 0.55, mats["cream"], root, 0.014,
        )
        upper_sill = [
            (-1.50, 1.07), (-0.95, 1.07), (-0.92, 1.17),
            (0.42, 1.17), (0.54, 1.06),
        ]
        local_path_curve(name + f"_Cabin_Side_Window_Sill_{side}", [
            (px, side * 0.56, pz) for px, pz in upper_sill
        ], mats["wood"], 0.035, root)
        roof_edge = [
            (-1.47, side * 0.55, 2.10),
            (-0.92, side * 0.57, 2.16),
            (-0.18, side * 0.57, 2.17),
            (0.51, side * 0.54, 2.12),
        ]
        local_path_curve(name + f"_Cabin_Roof_Edge_{side}", roof_edge, mats["aluminium"], 0.030, root)

        # Four cabin glazing modules, each with a thick frame and a slightly
        # varied pane proportion so the side is not a repeated glass rectangle.
        panes = [
            (-1.35, -0.89, 1.22, 1.93),
            (-0.78, -0.30, 1.22, 1.96),
            (-0.17, 0.34, 1.22, 1.91),
        ]
        for pane, (x0, x1, z0, z1) in enumerate(panes):
            y_front = side * 0.548
            y_back = side * 0.526
            glass_vertices = [
                (x0, y_front, z0), (x1, y_front, z0 + 0.02),
                (x1 - 0.02, y_front, z1), (x0 + 0.02, y_front, z1 - 0.02),
                (x0, y_back, z0), (x1, y_back, z0 + 0.02),
                (x1 - 0.02, y_back, z1), (x0 + 0.02, y_back, z1 - 0.02),
            ]
            glass_faces = [
                (0, 1, 2, 3), (4, 7, 6, 5),
                (0, 4, 5, 1), (1, 5, 6, 2),
                (2, 6, 7, 3), (3, 7, 4, 0),
            ]
            authored_mesh(
                name + f"_Cabin_Laminated_Window_{side}_{pane}",
                glass_vertices, glass_faces, mats["glass"], root, True,
            )
            for x_edge in (x0, x1):
                local_path_curve(name + f"_Cabin_Window_Post_{side}_{pane}_{x_edge:.2f}", [
                    (x_edge, side * 0.575, z0),
                    (x_edge + 0.012, side * 0.575, (z0 + z1) * 0.5),
                    (x_edge, side * 0.575, z1),
                ], mats["aluminium"], 0.024, root)
            local_path_curve(name + f"_Cabin_Window_Top_{side}_{pane}", [
                (x0, side * 0.575, z1), ((x0 + x1) * 0.5, side * 0.575, z1 + 0.012),
                (x1, side * 0.575, z1),
            ], mats["cream"], 0.018, root)

        # Lower cabin moulding and a narrow rub line connect glazing to hull.
        local_path_curve(name + f"_Cabin_Belt_Moulding_{side}", [
            (-1.52, side * 0.565, 1.10), (-0.50, side * 0.57, 1.12),
            (0.60, side * 0.54, 1.08),
        ], mats["brass"], 0.018, root)

    # Fore and aft cabin walls use shaped openings and a front windscreen.
    front_window_vertices = [
        (-1.34, -0.44, 1.15), (-1.48, -0.42, 1.94),
        (-1.48, 0.42, 1.94), (-1.34, 0.44, 1.15),
        (-1.31, -0.42, 1.15), (-1.45, -0.40, 1.94),
        (-1.45, 0.40, 1.94), (-1.31, 0.42, 1.15),
    ]
    front_window_faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    authored_mesh(
        name + "_Cabin_Bow_Windscreen",
        front_window_vertices, front_window_faces, mats["glass"], root, True,
    )
    for side in (-1, 1):
        local_path_curve(name + f"_Cabin_Bow_Mullion_{side}", [
            (-1.50, side * 0.44, 1.94), (-1.47, side * 0.44, 1.54),
            (-1.34, side * 0.45, 1.15),
        ], mats["aluminium"], 0.026, root)

    # The cabin roof is a shallow cambered surface with shaped edges and
    # corrugation detail; a raised centre crown lets rain run off.
    roof_cols, roof_rows = 24, 12
    roof_vertices: list[tuple[float, float, float]] = []
    roof_faces: list[tuple[int, int, int, int]] = []
    for row in range(roof_rows + 1):
        v = row / roof_rows
        py = -0.59 + v * 1.18
        for col in range(roof_cols + 1):
            u = col / roof_cols
            px = -1.56 + u * 2.22
            crown = 0.10 * math.cos((v - 0.5) * math.pi)
            edge_sag = 0.018 * math.sin(u * math.pi * 5.0)
            roof_vertices.append((px, py, 2.10 + crown + edge_sag))
    stride = roof_cols + 1
    for row in range(roof_rows):
        for col in range(roof_cols):
            a = row * stride + col
            b = a + 1
            d = (row + 1) * stride + col
            cc = d + 1
            roof_faces.append((a, b, cc, d))
    roof = authored_mesh(name + "_Cabin_Cambered_Roof", roof_vertices, roof_faces, mats["cream"], root, True)
    roof["roof_geometry"] = "cambered_grid;24x12;hand_tuned_edge_sag"

    # Interior bench and trim establish passenger scale through the glazing.
    authored_xy_slab(
        name + "_Cabin_Passenger_Bench_Seat",
        [(-1.16, -0.39), (0.36, -0.39), (0.42, -0.28),
         (0.38, 0.28), (0.30, 0.40), (-1.10, 0.40), (-1.20, 0.24)],
        0.92, 1.07, mats["wood"], root, 0.06,
    )
    for side in (-1, 1):
        local_path_curve(name + f"_Cabin_Interior_Grab_Handle_{side}", [
            (-1.08, side * 0.37, 1.13), (-0.62, side * 0.38, 1.16),
            (-0.25, side * 0.36, 1.14),
        ], mats["brass"], 0.014, root)
        local_path_curve(name + f"_Cabin_Interior_Seat_Back_Stitch_{side}", [
            (-0.95, side * 0.35, 1.12), (-0.90, side * 0.35, 1.34),
            (-0.62, side * 0.35, 1.38),
        ], mats["sand"], 0.009, root)

    # Roof equipment: navigation lamp, horn, short mast, horn trumpet and
    # a hand-lettered launch name with no generic floating UI text.
    mast = local_path_curve(name + "_Roof_Antenna_Mast", [
        (0.38, 0.28, 2.18), (0.46, 0.31, 2.56), (0.49, 0.32, 2.88),
    ], mats["aluminium"], 0.018, root)
    local_path_curve(name + "_Roof_Horn", [
        (-0.25, -0.22, 2.18), (-0.10, -0.24, 2.34),
        (0.06, -0.26, 2.39),
    ], mats["brass"], 0.032, root)
    beacon = authored_lathe(
        name + "_Roof_Navigation_Lantern",
        [(0.0, 0.06), (0.04, 0.11), (0.15, 0.09), (0.21, 0.05)],
        mats["lamp"], root, 32,
    )
    beacon.location = (-0.52, -0.36, 2.31)

    sign_data = bpy.data.curves.new(name + "_Cabin_Nameboard_Font", "FONT")
    sign_data.body = "MEGHNA  /  LAUNCH"
    sign_data.size = 0.19
    sign_data.extrude = 0.002
    sign_data.align_x = "CENTER"
    sign_obj = bpy.data.objects.new(name + "_Cabin_Nameboard", sign_data)
    bpy.context.collection.objects.link(sign_obj)
    sign_obj.location = (-0.44, -0.595, 1.93)
    sign_obj.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    sign_data.materials.append(mats["blue"])
    set_parent_local(sign_obj, root)

    # Deck rails, stanchions, mooring cleats and rope coils vary with the deck
    # contour rather than running as a single rectangular outline.
    for side in (-1, 1):
        rail_points = [
            (-2.45, side * 0.27, 1.06),
            (-2.08, side * 0.55, 1.05),
            (-1.55, side * 0.73, 1.03),
            (-1.32, side * 0.76, 1.02),
        ]
        local_path_curve(name + f"_Bow_Handrail_{side}", rail_points, mats["aluminium"], 0.032, root)
        for index, (px, py, pz) in enumerate(rail_points[1:-1]):
            local_path_curve(name + f"_Bow_Rail_Stanchion_{side}_{index}", [
                (px, py, 0.62), (px, py, 0.84), (px, py, pz),
            ], mats["brass"], 0.019, root)
        aft_rail = [
            (0.62, side * 0.78, 0.87),
            (1.45, side * 0.68, 0.88),
            (2.24, side * 0.50, 0.93),
        ]
        local_path_curve(name + f"_Aft_Deck_Rail_{side}", aft_rail, mats["aluminium"], 0.032, root)
        for index, (px, py, pz) in enumerate(aft_rail):
            local_path_curve(name + f"_Aft_Rail_Stanchion_{side}_{index}", [
                (px, py, 0.60), (px, py, pz - 0.04),
            ], mats["brass"], 0.018, root)
        local_path_curve(name + f"_Mooring_Rope_{side}", [
            (2.15, side * 0.46, 0.83),
            (2.36, side * 0.62, 0.78),
            (2.47, side * 0.58, 0.68),
        ], mats["wood"], 0.026, root)

    # Rubber fenders, cleats and a stern boarding step.
    for side in (-1, 1):
        fender = authored_lathe(
            name + f"_Hull_Rubber_Fender_{side}",
            [(0.0, 0.06), (0.05, 0.095), (0.15, 0.095), (0.20, 0.06)],
            mats["rubber"], root, 32,
        )
        fender.rotation_euler[0] = math.pi * 0.5
        fender.location = (0.12, side * 0.88, 0.42)
        local_path_curve(name + f"_Mooring_Cleat_{side}", [
            (2.12, side * 0.51, 0.83),
            (2.22, side * 0.61, 0.91),
            (2.29, side * 0.51, 0.83),
        ], mats["aluminium"], 0.027, root)
    authored_xy_slab(
        name + "_Stern_Boarding_Step",
        [(1.64, -0.55), (2.54, -0.38), (2.58, 0.38), (1.64, 0.55)],
        0.34, 0.48, mats["wood"], root, 0.025,
    )

    # Stern shaft and a three-blade propeller are custom meshes that rotate
    # independently. The propeller is intentionally visible only in the wake
    # shot where it helps communicate the vessel's direction of travel.
    local_path_curve(name + "_Propeller_Shaft", [
        (2.13, 0.0, -0.06), (2.52, 0.0, -0.12), (2.76, 0.0, -0.22),
    ], mats["aluminium"], 0.034, root)
    prop = bpy.data.objects.new(name + "_Propeller_Pivot", None)
    bpy.context.collection.objects.link(prop)
    prop.location = (2.76, 0.0, -0.22)
    set_parent_local(prop, root)
    for blade in range(3):
        angle = math.tau * blade / 3.0
        points = [
            (0.0, 0.0, 0.0),
            (0.08 * math.cos(angle - 0.25), 0.0, 0.08 * math.sin(angle - 0.25)),
            (0.34 * math.cos(angle + 0.18), 0.08, 0.34 * math.sin(angle + 0.18)),
            (0.29 * math.cos(angle + 0.36), 0.11, 0.29 * math.sin(angle + 0.36)),
            (0.06 * math.cos(angle + 0.15), 0.03, 0.06 * math.sin(angle + 0.15)),
        ]
        blade_mesh = authored_mesh(
            name + f"_Propeller_Blade_{blade}",
            points, [(0, 1, 2, 3, 4)], mats["aluminium"], prop, False,
        )
        blade_mesh["blade_index"] = blade
    prop.rotation_mode = "XYZ"
    prop.keyframe_insert(data_path="rotation_euler", frame=1, group="Launch_Propeller_Performance")
    prop.rotation_euler[0] = math.tau * 7.0
    prop.keyframe_insert(data_path="rotation_euler", frame=288, group="Launch_Propeller_Performance")

    # The launch gets a low-amplitude buoyant performance distinct from its
    # forward glide. Camera timing and hull movement are authored separately.
    root.rotation_mode = "XYZ"
    for frame, pitch, roll, yaw in (
        (1, 0.0, 0.0, 0.0),
        (72, math.radians(0.8), math.radians(-0.5), math.radians(0.5)),
        (144, math.radians(-0.4), math.radians(0.6), math.radians(-0.8)),
        (216, math.radians(0.5), math.radians(-0.4), math.radians(0.6)),
        (288, 0.0, 0.0, 0.0),
    ):
        root.rotation_euler = (roll, pitch, yaw)
        root.keyframe_insert(data_path="rotation_euler", frame=frame, group="Launch_Buoyancy_Performance")

    root["asset_role"] = "Bangladesh_local_passenger_launch"
    root["geometry_method"] = "variable_breadth_hull_loft;custom_deck;open_cabin_windows;cambered_roof;lathed_fenders"
    root["hull_stations"] = len(stations)
    root["waterline_target"] = -0.31
    root["animation"] = "buoyancy_roll_yaw;stern_propeller;wake_and_reflection_shot"
    root["material_story"] = "painted_hull;wet_boot_stripe;timber_deck;aluminium_rails;laminated_glass"
    return root


def add_launch_wake(
    name: str,
    motion: list[tuple[int, tuple[float, float, float]]],
    mats: dict[str, bpy.types.Material],
) -> list[bpy.types.Object]:
    """Create widening, deforming water-surface wakes that follow the launch stern."""
    wake_root = bpy.data.objects.new(name + "_Wake_Root", None)
    bpy.context.collection.objects.link(wake_root)
    wake_root["effect_role"] = "launch_stern_surface_wake"
    wake_root["motion_source"] = "same_authored_path_as_River_Launch_Glide"

    # The wake root tracks the launch's stern along its actual authored route.
    # The geometry itself is behind the stern, widening and fading as it travels.
    for frame, position in motion:
        px, py, pz = position
        wake_root.location = (px + 2.48, py, pz - 0.365)
        wake_root.keyframe_insert(data_path="location", frame=frame, group="Launch_Wake_Follows_Hull")

    wakes: list[bpy.types.Object] = []
    length_samples = 22
    width_samples = 7
    base_lengths = (3.2, 3.7, 4.1)
    base_widths = (0.16, 0.28, 0.42)

    for side in (-1, 1):
        for layer, (wake_length, max_width) in enumerate(zip(base_lengths, base_widths)):
            vertices: list[tuple[float, float, float]] = []
            faces: list[tuple[int, int, int, int]] = []
            for row in range(length_samples + 1):
                t = row / length_samples
                x = 0.10 + wake_length * t
                envelope = (0.12 + 0.88 * (t ** 0.82))
                width = max_width * envelope
                for col in range(width_samples + 1):
                    u = col / width_samples
                    lateral = (u * 2.0 - 1.0)
                    broken_edge = (
                        math.sin(t * math.pi * (5.0 + layer) + side * 0.7)
                        * 0.018
                        * (0.25 + t)
                    )
                    y = side * (0.10 + lateral * width + broken_edge)
                    ripple = (
                        math.sin(t * 14.0 + u * 9.0 + layer * 0.8)
                        * 0.009
                        + math.sin(t * 27.0 - u * 13.0)
                        * 0.004
                    )
                    z = ripple + (0.002 * side * lateral)
                    vertices.append((x, y, z))
            stride = width_samples + 1
            for row in range(length_samples):
                for col in range(width_samples):
                    a = row * stride + col
                    b = a + 1
                    d = (row + 1) * stride + col
                    cc = d + 1
                    faces.append((a, b, cc, d))

            wake = authored_mesh(
                name + f"_Surface_Ribbon_{side}_{layer}",
                vertices, faces, mats["waterline"], wake_root, True,
            )
            wake.data.materials.append(mats["cream"])
            for polygon in wake.data.polygons:
                col = polygon.index % width_samples
                # Only the outermost edge catches broken whitewater highlights.
                polygon.material_index = 1 if col in (0, width_samples - 1) and layer == 0 else 0

            turbulence = wake.shape_key_add(name="Stern_Turbulence", from_mix=False)
            dissipation = wake.shape_key_add(name="Wake_Dissipation", from_mix=False)
            for index, (vx, vy, vz) in enumerate(vertices):
                row = index // stride
                col = index % stride
                t = row / length_samples
                u = col / width_samples
                turbulence.data[index].co.z = vz + (
                    0.035 * math.sin(t * 24.0 + u * 11.0 + layer)
                    * (1.0 - t * 0.45)
                )
                dissipation.data[index].co.y = vy * (1.0 + 0.14 * t)
                dissipation.data[index].co.z = vz - 0.006 * t

            for frame, value in ((1, 0.0), (28, 0.9), (96, 0.55), (176, 0.18), (288, 0.0)):
                turbulence.value = value
                turbulence.keyframe_insert(data_path="value", frame=frame, group="Launch_Wake_Turbulence")
            for frame, value in ((1, 0.0), (96, 0.0), (176, 0.6), (288, 1.0)):
                dissipation.value = value
                dissipation.keyframe_insert(data_path="value", frame=frame, group="Launch_Wake_Dissipation")

            wake["wake_profile"] = "tapered_surface_ribbon_with_broken_edges"
            wake["wake_length"] = wake_length
            wake["wake_max_width"] = max_width
            wake["surface_topology"] = f"{length_samples}x{width_samples}"
            wakes.append(wake)

    wake_root["wake_surface_count"] = len(wakes)
    print("LAUNCH_WAKE_SURFACES_READY:", json.dumps({
        "root": wake_root.name,
        "surface_count": len(wakes),
        "motion_keys": len(motion),
        "topology_per_surface": [length_samples, width_samples],
    }, sort_keys=True))
    return wakes


def build_login(scene: bpy.types.Scene, mats: dict[str, bpy.types.Material], operator_glb: pathlib.Path) -> bpy.types.Object:
    scene["scene_role"] = "A-Square Login — Shariatpur Riverfront"
    world_and_lighting(scene, True)
    # Ground layers and asphalt apron with actual roughness/bump material detail.
    box("Riverfront_Earth_Bank", (0.0, -1.5, -0.42), (44.0, 26.0, 0.72), mats["stone"], 0.0)
    box("Two_Lane_Local_Asphalt", (0.0, 3.3, 0.02), (42.0, 6.0, 0.22), mats["road"], 0.01)
    box("Pavement_Tiled_Promenade", (0.0, -0.2, 0.08), (42.0, 2.4, 0.26), mats["stone"], 0.025)
    # Curb, drainage channel, tactile paving and lane reflectors.
    for side in (-1, 1):
        box(f"Road_Curb_{side}", (0.0, 0.05 + side * 3.1, 0.18), (42.0, 0.18, 0.32), mats["white"], 0.025)
        box(f"Road_Drainage_{side}", (0.0, 0.05 + side * 3.38, 0.03), (42.0, 0.28, 0.08), mats["dark"], 0.015)
    for i in range(24):
        x = -19.0 + i * 1.65
        box(f"Lane_Reflector_{i}", (x, 3.3, 0.15), (0.86, 0.055, 0.018), mats["cream"], 0.008)
        if i % 2 == 0:
            box(f"Pavement_Joint_{i}", (x, -0.2, 0.215), (0.025, 2.25, 0.008), mats["dark"], 0.002)
    # River and stepped ghat with wet stone and mooring hardware.
    river_plane(mats, -21.5, 70, 34)
    for tier in range(5):
        z = -0.08 - tier * 0.22
        y = -3.1 - tier * 0.86
        box(f"River_Ghat_Step_{tier}", (0.0, y, z), (34.0 - tier * 0.8, 1.0, 0.30), mats["stone"], 0.04)
    for x in (-13, -7, 0, 7, 13):
        cylinder(f"Ghat_Mooring_Bollard_{x}", (x, -6.0, 0.35), 0.12, 0.65, mats["dark"], 20)
        path_curve(f"Ghat_Mooring_Rope_{x}", [(x, -5.9, 0.50), (x + 0.8, -7.2, 0.18), (x + 1.7, -8.4, 0.12)], mats["wood"], 0.035)
    # Varied low-rise and mid-rise Bangladeshi mixed-use blocks, not one repeated box silhouette.
    blocks = [
        (-15.8, -10.0, 5.6, 3.8, 4, 0),
        (-9.2, -11.8, 4.2, 3.2, 5, 2),
        (-3.5, -12.3, 5.0, 3.7, 3, 1),
        (3.0, -11.2, 5.4, 3.4, 6, 3),
        (10.0, -11.8, 4.5, 3.3, 4, 0),
        (16.2, -10.0, 5.4, 3.8, 5, 2),
    ]
    for i, args in enumerate(blocks):
        if i == 2:
            add_crafted_riverfront_corner_store(args[0], args[1], args[2], args[3], mats)
        else:
            add_facade_building(f"Shariatpur_MixedUse_Block_{i+1}", *args, mats)
    # Palm/banyan canopy framing the street, individual leaf cards and exposed limbs.
    add_banyan_or_palm("Banyan_Left", -19.0, -2.0, 6.6, mats, 45)
    add_banyan_or_palm("Banyan_Right", 19.0, -2.4, 6.0, mats, 85)
    add_banyan_or_palm("River_Tree_Midground", -13.0, -9.5, 7.2, mats, 95)
    # Concrete street lamps with glazed lanterns and cabling.
    for i, x in enumerate((-16, -9, -2, 5, 12, 18)):
        cylinder(f"StreetLamp_{i}_Column", (x, 1.0, 3.55), 0.075, 7.0, mats["aluminium"], 16)
        path_curve(f"StreetLamp_{i}_Arm", [(x, 1, 6.75), (x + 0.3, 1, 7.12), (x + 0.82, 1, 7.20)], mats["dark"], 0.055)
        sphere(f"StreetLamp_{i}_Lantern", (x + 0.82, 1, 7.08), (0.24, 0.18, 0.12), mats["lamp"], 16, 8)
    # Local three-wheeler and a small motor launch on the river.
    cng = add_handcrafted_cng("Shariatpur_Emerald_CNG_Hero", 3.0, 3.3, mats)
    animate_location(cng, "Login_CNG_Pass", [
        (1, (-15.0, 3.3, 0.0)),
        (72, (-9.0, 3.3, 0.0)),
        (144, (-2.0, 3.3, 0.0)),
        (216, (7.0, 3.3, 0.0)),
        (288, (15.0, 3.3, 0.0)),
    ], True)
    boat = add_handcrafted_launch("River_Launch_Hero", 7.0, -17.0, 0.10, mats)
    launch_motion = [
        (1, (10.0, -17.0, 0.10)),
        (72, (9.2, -17.0, 0.17)),
        (144, (8.2, -17.0, 0.10)),
        (216, (7.1, -17.0, 0.16)),
        (288, (6.0, -17.0, 0.10)),
    ]
    animate_location(boat, "River_Launch_Glide", launch_motion, True)
    launch_wakes = add_launch_wake("River_Launch_Stern_Wake", launch_motion, mats)
    scene["launch_wake_lines"] = len(launch_wakes)
    # The login film is edited as five separate, motivated shots. Each camera
    # has its own lens and subject distance; timeline markers perform real cuts.
    # The camera never tries to show the river, street, launch, actor and title
    # all at once.
    cam = camera(scene, "Login_Cinematic_Camera", (0.0, 20.0, 7.5), (-4.0, -18.0, 1.2), 42.0)
    animate_camera_path(cam, "Login_Riverfront_Establishing_Move", [
        (1, (13.0, -7.8, 5.2), (6.0, -22.0, 0.1)),
        (58, (10.5, -8.6, 4.6), (6.8, -22.5, 0.05)),
        (227, (0.0, 20.0, 7.5), (-4.0, -18.0, 1.2)),
        (288, (0.0, 18.0, 6.0), (-1.8, -3.0, 2.0)),
    ])

    cng_cut = camera(scene, "Login_CNG_Street_Portrait_Camera", (-12.4, 10.4, 3.15), (-9.4, 3.3, 1.25), 58.0)
    animate_camera_path(cng_cut, "Login_CNG_Tracking_Pass", [
        (59, (-12.4, 10.4, 3.15), (-9.4, 3.3, 1.25)),
        (108, (-8.8, 9.4, 2.85), (-5.2, 3.3, 1.15)),
    ])

    launch_cut = camera(scene, "Login_Launch_Waterline_Camera", (15.2, -8.8, 3.75), (8.6, -17.0, 0.88), 58.0)
    animate_camera_path(launch_cut, "Login_Launch_Tracking_Pass", [
        (109, (15.2, -8.8, 3.75), (8.6, -17.0, 0.88)),
        (160, (13.5, -9.6, 3.45), (7.8, -17.0, 0.95)),
    ])

    ranger_cut = camera(scene, "Login_Field_Ranger_Portrait_Camera", (-4.7, 12.6, 2.55), (-3.0, 8.0, 1.32), 66.0)
    animate_camera_path(ranger_cut, "Login_Field_Ranger_Portrait_Dolly", [
        (161, (-4.9, 12.9, 2.62), (-3.0, 8.0, 1.34)),
        (226, (-4.2, 12.2, 2.48), (-3.0, 8.0, 1.34)),
    ])

    # Original A-Square delta/river mark: an authored three-tributary motif,
    # not a spinning primitive or a borrowed game emblem. The strokes reveal
    # in a staggered rhythm, then the wordmark and tagline settle underneath.
    logo_rotation = Vector((0.0, 1.0, 0.0)).to_track_quat("Z", "Y")
    logo_paths = [
        (
            "ASQ_Delta_Emblem_Outer",
            [(-0.94, 0.54, 0.0), (-0.53, -0.10, 0.0), (0.0, -0.88, 0.0),
             (0.53, -0.10, 0.0), (0.94, 0.54, 0.0)],
            mats["brass"], 0.040, 232, 253,
        ),
        (
            "ASQ_Delta_River_Tributary_Left",
            [(-0.45, 0.45, 0.0), (-0.16, 0.12, 0.0), (0.0, -0.28, 0.0)],
            mats["waterline"], 0.026, 237, 257,
        ),
        (
            "ASQ_Delta_River_Tributary_Right",
            [(0.45, 0.45, 0.0), (0.16, 0.12, 0.0), (0.0, -0.28, 0.0)],
            mats["waterline"], 0.026, 241, 261,
        ),
        (
            "ASQ_Delta_Lower_Current",
            [(-0.62, 0.47, 0.0), (0.0, 0.23, 0.0), (0.62, 0.47, 0.0)],
            mats["brass"], 0.018, 245, 263,
        ),
    ]
    for name, points, line_material, radius, first_frame, last_frame in logo_paths:
        stroke = path_curve(name, points, line_material, radius)
        stroke.location = (0.0, 5.4, 3.85)
        stroke.rotation_mode = "QUATERNION"
        stroke.rotation_quaternion = logo_rotation
        stroke.scale = (0.001, 0.001, 0.001)
        stroke.keyframe_insert(data_path="scale", frame=first_frame, group="ASQ_Delta_Mark_Reveal")
        stroke.scale = (1.0, 1.0, 1.0)
        stroke.keyframe_insert(data_path="scale", frame=last_frame, group="ASQ_Delta_Mark_Reveal")
        if stroke.animation_data and stroke.animation_data.action:
            stroke.animation_data.action.name = name + "_Draw_On"

    wordmark_data = bpy.data.curves.new("A_Square_Wordmark_Font", "FONT")
    wordmark_data.body = "A-SQUARE"
    wordmark_data.size = 0.64
    wordmark_data.extrude = 0.010
    wordmark_data.bevel_depth = 0.002
    wordmark_data.align_x = "CENTER"
    wordmark_data.align_y = "CENTER"
    wordmark = bpy.data.objects.new("A_Square_Original_Wordmark", wordmark_data)
    scene.collection.objects.link(wordmark)
    wordmark_data.materials.append(mats["cream"])
    wordmark.location = (0.0, 5.4, 2.55)
    wordmark.rotation_mode = "QUATERNION"
    wordmark.rotation_quaternion = logo_rotation
    wordmark.scale = (0.78, 0.78, 0.78)
    wordmark.keyframe_insert(data_path="scale", frame=246, group="ASQ_Wordmark_Resolve")
    wordmark.scale = (1.0, 1.0, 1.0)
    wordmark.keyframe_insert(data_path="scale", frame=264, group="ASQ_Wordmark_Resolve")
    if wordmark.animation_data and wordmark.animation_data.action:
        wordmark.animation_data.action.name = "ASQ_Wordmark_Resolve"

    tagline_data = bpy.data.curves.new("A_Square_Tagline_Font", "FONT")
    tagline_data.body = "THE DELTA IS OUR WORLD"
    tagline_data.size = 0.145
    tagline_data.extrude = 0.002
    tagline_data.align_x = "CENTER"
    tagline = bpy.data.objects.new("A_Square_Original_Tagline", tagline_data)
    scene.collection.objects.link(tagline)
    tagline_data.materials.append(mats["waterline"])
    tagline.location = (0.0, 5.38, 2.12)
    tagline.rotation_mode = "QUATERNION"
    tagline.rotation_quaternion = logo_rotation
    tagline.scale = (0.001, 0.001, 0.001)
    tagline.keyframe_insert(data_path="scale", frame=252, group="ASQ_Tagline_Resolve")
    tagline.scale = (1.0, 1.0, 1.0)
    tagline.keyframe_insert(data_path="scale", frame=270, group="ASQ_Tagline_Resolve")
    if tagline.animation_data and tagline.animation_data.action:
        tagline.animation_data.action.name = "ASQ_Tagline_Resolve"

    title_cut = camera(scene, "Login_A_Square_Title_Reveal_Camera", (0.2, 14.0, 4.1), (0.0, 5.4, 3.18), 52.0)
    animate_camera_path(title_cut, "Login_A_Square_Title_Reveal_Dolly", [
        (227, (0.2, 14.5, 4.25), (0.0, 5.4, 3.18)),
        (288, (0.2, 13.4, 4.0), (0.0, 5.4, 3.18)),
    ])

    register_camera_cut(scene, cam, 1, "A1_SHARIATPUR_RIVER_ESTABLISHING")
    register_camera_cut(scene, cng_cut, 59, "A2_LOCAL_CNG_STREET_PORTRAIT")
    register_camera_cut(scene, launch_cut, 109, "A3_LAUNCH_WAKE_AND_REFLECTION")
    register_camera_cut(scene, ranger_cut, 161, "A4_FIELD_RANGER_HUMAN_PORTRAIT")
    register_camera_cut(scene, title_cut, 227, "A5_ORIGINAL_A_SQUARE_TITLE_REVEAL")
    scene.camera = cam
    apply_camera_shakify(cam, scene)
    scene.render.filepath = "//login_preview.png"
    operator_preview = add_operator_preview(
        operator_glb, (-3.0, 8.0, 0.05), "Login_Field_Ranger_Preview",
        "Look around",
    )
    face_operator_to_camera(operator_preview, ranger_cut)
    return operator_preview


def build_lobby(
    scene: bpy.types.Scene,
    mats: dict[str, bpy.types.Material],
    operator_glb: pathlib.Path,
    delta_operator_glb: pathlib.Path,
    river_operator_glb: pathlib.Path,
) -> list[bpy.types.Object]:
    scene["scene_role"] = "A-Square Delta Command — Operator Lobby"
    world_and_lighting(scene, False)
    # Dedicated face/equipment lighting; the operators must read clearly against the hall.
    add_area_light(scene, "Operator_Hero_Key", (-3.0, -7.0, 8.0), (0.0, 0.0, 1.5), 9200, (1.0, 0.82, 0.66), 7.0)
    add_area_light(scene, "Operator_Hero_Fill", (6.0, -5.0, 5.0), (0.0, 0.0, 1.5), 5100, (0.48, 0.70, 0.88), 8.5)
    add_area_light(scene, "Operator_Hero_Rim", (0.0, 8.0, 9.0), (0.0, 0.0, 1.5), 6500, (1.0, 0.55, 0.32), 6.5)
    # A river-facing command terminal with a real roof profile, glass curtain wall and structural rhythm.
    box("Command_Terminal_Foundation", (0.0, 0.0, -0.28), (38.0, 25.0, 0.60), mats["dark"], 0.12)
    box("Command_Hall_Interior_Deck", (0.0, 0.0, 0.04), (30.0, 18.0, 0.18), mats["concrete"], 0.04)
    # Individual floor inlays and guide strips replace a glowing toy podium.
    for i in range(17):
        x = -14.0 + i * 1.75
        box(f"Deck_Inlay_{i}", (x, -0.2, 0.145), (1.42, 15.5, 0.018), mats["trim"], 0.007)
    for side in (-1, 1):
        box(f"Deck_Brass_Boundary_{side}", (0.0, side * 7.9, 0.18), (30.0, 0.065, 0.028), mats["brass"], 0.016)
    # Character mark is a restrained, inset metal medallion, not a stack of rotating primitives.
    cylinder("Operator_Inset_Delta_Mark", (0.0, 0.0, 0.20), 1.30, 0.055, mats["brass"], 96)
    cylinder("Operator_Inset_Matte_Surface", (0.0, 0.0, 0.235), 1.20, 0.035, mats["dark"], 96)
    path_curve("Operator_Inset_Compass_Trace", [
        (-0.8, 0.0, 0.26), (-0.34, 0.26, 0.26), (0.0, 0.92, 0.26),
        (0.34, 0.26, 0.26), (0.8, 0.0, 0.26), (0.0, -0.92, 0.26),
        (-0.8, 0.0, 0.26)
    ], mats["waterline"], 0.024, cyclic=True)
    for operator_index, x in enumerate((-3.35, 3.35)):
        cylinder(f"Operator_Roster_Podium_{operator_index}", (x, 0.0, 0.20), 0.88, 0.055, mats["brass"], 72)
        cylinder(f"Operator_Roster_Podium_Inset_{operator_index}", (x, 0.0, 0.235), 0.81, 0.032, mats["dark"], 72)
        path_curve(
            f"Operator_Roster_Podium_Trace_{operator_index}",
            [(x - 0.52, 0.0, 0.26), (x, 0.58, 0.26), (x + 0.52, 0.0, 0.26), (x, -0.58, 0.26), (x - 0.52, 0.0, 0.26)],
            mats["waterline"], 0.018, cyclic=True,
        )
    # A broad camera portal replaces the washed-out foreground curtain wall.
    # The outer steel piers remain as a frame; four central glazed bays are
    # deliberately omitted so the roster reads clearly from the review camera.
    for i, x in enumerate((-14, -10.5, -7, -3.5, 0, 3.5, 7, 10.5, 14)):
        if abs(x) < 7.0:
            continue
        cylinder(f"Hall_Structural_Pillar_{i}", (x, -4.0, 4.65), 0.13, 9.0, mats["dark"], 24)
        glass_x = x + 1.70
        if abs(glass_x) <= 6.9:
            continue
        box(f"Hall_Glass_Bay_{i}", (glass_x, -4.0, 4.25), (3.18, 0.09, 7.65), mats["glass"], 0.015)
        box(f"Hall_Transom_{i}", (glass_x, -4.10, 6.25), (3.18, 0.15, 0.085), mats["aluminium"], 0.016)
        box(f"Hall_Sill_{i}", (glass_x, -4.11, 0.75), (3.18, 0.16, 0.16), mats["aluminium"], 0.018)
    box("Lobby_Hero_Portal_Header", (0.0, -4.06, 8.03), (14.05, 0.30, 0.32), mats["dark"], 0.075)
    box("Lobby_Hero_Portal_Header_Inlay", (0.0, -4.225, 7.84), (13.60, 0.035, 0.045), mats["brass"], 0.012)
    box("Lobby_Hero_Portal_Threshold", (0.0, -4.0, 0.22), (13.65, 0.52, 0.075), mats["brass"], 0.018)
    # Monumental canopy with a stepped soffit and warm reflected panels.
    box("Hall_Roof_Upper_Shell", (0.0, 0.1, 9.1), (32.0, 19.0, 0.48), mats["dark"], 0.12)
    box("Hall_Roof_Soffit", (0.0, 0.0, 8.78), (29.0, 16.0, 0.17), mats["blue"], 0.06)
    for i in range(27):
        x = -13.0 + i * 1.0
        box(f"Roof_Louvre_{i}", (x, 0.0, 8.61), (0.045, 15.4, 0.09), mats["aluminium"], 0.018)
    for side in (-1, 1):
        box(f"Hall_Roof_Fascia_{side}", (0.0, side * 8.8, 8.86), (31.0, 0.42, 0.35), mats["brass"], 0.06)
    # Panoramic tactical information wall and a full-height riverfront glass curtain.
    for i, x in enumerate((-14.0, -10.5, -7.0, -3.5, 0.0, 3.5, 7.0, 10.5, 14.0)):
        box(f"Riverfront_Back_Glass_Bay_{i}", (x, 13.15, 4.35), (3.12, 0.10, 7.55), mats["glass"], 0.018)
        box(f"Riverfront_Back_Glass_Transom_{i}", (x, 13.08, 6.35), (3.12, 0.14, 0.09), mats["aluminium"], 0.018)
        box(f"Riverfront_Back_Glass_Sill_{i}", (x, 13.06, 0.72), (3.12, 0.14, 0.15), mats["aluminium"], 0.018)
    box("Panoramic_Tactical_Display_Housing", (0.0, 12.72, 5.35), (17.0, 0.36, 2.55), mats["dark"], 0.10)
    box("Panoramic_Tactical_Display_Glass", (0.0, 12.50, 5.35), (16.45, 0.055, 2.12), mats["screen"], 0.035)
    for i in range(18):
        x = -7.70 + i * 0.90
        box(f"Tactical_Display_Data_Rail_{i}", (x, 12.455, 4.78 + (i % 4) * 0.18), (0.56, 0.018, 0.032), mats["waterline"], 0.009)
    # Equipment alcoves and wall-mounted tactical displays, designed as believable hardware.
    for i, x in enumerate((-11.5, -6.0, 6.0, 11.5)):
        box(f"Command_Display_Housing_{i}", (x, -3.35, 4.25), (2.55, 0.42, 1.65), mats["dark"], 0.11)
        box(f"Command_Display_Glass_{i}", (x, -3.59, 4.29), (2.25, 0.045, 1.30), mats["screen"], 0.035)
        for row in range(4):
            box(f"Display_Data_Rail_{i}_{row}", (x, -3.63, 3.82 + row * 0.27), (1.72 - row * 0.13, 0.025, 0.045), mats["waterline"], 0.008)
        cylinder(f"Display_Lens_{i}", (x + 0.88, -3.66, 4.62), 0.07, 0.045, mats["brass"], 16, (math.pi * 0.5, 0.0, 0.0))
    # Two staffed command workstations: metal desk frames, timber worktops,
    # multi-screen consoles, control pads, task lighting and operator chairs.
    for station, x in enumerate((-10.0, 10.0)):
        station_y = 1.5
        box(f"Command_Worktop_{station}", (x, station_y, 1.18), (3.8, 1.45, 0.16), mats["wood"], 0.075)
        box(f"Command_Worktop_Inset_{station}", (x, station_y - 0.05, 1.27), (3.1, 1.12, 0.035), mats["dark"], 0.018)
        for leg_x in (-1.58, 1.58):
            for leg_y in (-0.50, 0.50):
                cylinder(f"Workstation_Leg_{station}_{leg_x}_{leg_y}", (x + leg_x, station_y + leg_y, 0.58), 0.065, 1.12, mats["aluminium"], 14)
        for screen_index in range(2):
            screen_x = x - 0.75 + screen_index * 1.50
            box(f"Command_Monitor_Housing_{station}_{screen_index}", (screen_x, station_y - 0.48, 2.18), (1.30, 0.14, 0.88), mats["dark"], 0.065)
            box(f"Command_Monitor_Glass_{station}_{screen_index}", (screen_x, station_y - 0.565, 2.20), (1.12, 0.035, 0.68), mats["screen"], 0.025)
            cylinder(f"Command_Monitor_Stand_{station}_{screen_index}", (screen_x, station_y - 0.46, 1.70), 0.045, 0.65, mats["aluminium"], 12)
            for rail in range(3):
                box(f"Monitor_UI_Rail_{station}_{screen_index}_{rail}", (screen_x, station_y - 0.59, 1.97 + rail * 0.13), (0.76 - rail * 0.08, 0.018, 0.025), mats["waterline"], 0.006)
        box(f"Command_Control_Deck_{station}", (x, station_y + 0.38, 1.32), (1.22, 0.42, 0.065), mats["aluminium"], 0.025)
        for button_index in range(12):
            bx = x - 0.52 + (button_index % 6) * 0.205
            by = station_y + 0.26 + (button_index // 6) * 0.16
            cylinder(f"Control_Button_{station}_{button_index}", (bx, by, 1.37), 0.035, 0.035, mats["red"] if button_index % 5 == 0 else mats["waterline"], 12)
        # Seat silhouette is upholstered and supported by a metal frame.
        chair_x = x
        chair_y = station_y + 1.65
        cylinder(f"Operator_Chair_Post_{station}", (chair_x, chair_y, 0.55), 0.09, 0.75, mats["dark"], 16)
        cylinder(f"Operator_Chair_Base_{station}", (chair_x, chair_y, 0.20), 0.34, 0.08, mats["aluminium"], 24)
        box(f"Operator_Chair_Seat_{station}", (chair_x, chair_y, 0.95), (1.12, 0.98, 0.18), mats["blue"], 0.12)
        box(f"Operator_Chair_Back_{station}", (chair_x, chair_y + 0.43, 1.55), (1.12, 0.22, 1.18), mats["blue"], 0.13)
        for arm_side in (-1, 1):
            cylinder(f"Operator_Chair_ArmSupport_{station}_{arm_side}", (chair_x + arm_side * 0.55, chair_y, 1.22), 0.035, 0.52, mats["aluminium"], 10)
            box(f"Operator_Chair_ArmPad_{station}_{arm_side}", (chair_x + arm_side * 0.55, chair_y, 1.50), (0.20, 0.72, 0.09), mats["dark"], 0.035)

    # Container service bay, cargo, crates and workshop fittings.
    for i, x in enumerate((-12.0, 11.0)):
        container = box(f"Service_Container_{i}", (x, 5.8, 1.65), (6.0, 3.0, 3.2), mats["blue"] if i == 0 else mats["brick"], 0.10)
        for rib in range(15):
            rx = x - 2.78 + rib * 0.397
            box(f"Container_Rib_{i}_{rib}", (rx, 4.25, 1.65), (0.045, 0.08, 2.82), mats["aluminium"], 0.016)
        for top in range(2):
            box(f"Container_Top_Rail_{i}_{top}", (x, 5.8, 3.34 + top * 0.08), (6.05, 3.08, 0.08), mats["dark"], 0.022)
    for i, pos in enumerate([(-7.0, 6.0), (-5.2, 6.1), (7.0, 6.2), (8.8, 6.0)]):
        box(f"Flight_Case_{i}", (pos[0], pos[1], 0.72), (1.3, 0.88, 1.22), mats["dark"], 0.08)
        for edge in (-1, 1):
            box(f"Flight_Case_Trim_{i}_{edge}", (pos[0] + edge * 0.56, pos[1] - 0.46, 0.73), (0.05, 0.035, 1.05), mats["aluminium"], 0.015)
    # Shipyard gantry and crane silhouetted outside the glass.
    for i, x in enumerate((-17.0, 17.0)):
        cylinder(f"Port_Crane_Leg_{i}", (x, 11.5, 4.0), 0.18, 8.0, mats["red"], 20)
        box(f"Port_Crane_Foot_{i}", (x, 11.5, 0.25), (1.3, 1.1, 0.50), mats["dark"], 0.08)
    box("Port_Crane_Bridge", (0.0, 11.5, 8.0), (36.0, 0.48, 0.42), mats["red"], 0.08)
    path_curve("Port_Crane_Hoist", [(3.0, 11.5, 7.8), (3.0, 11.5, 4.4), (3.0, 11.5, 3.8)], mats["dark"], 0.055)
    box("Port_Crane_SpreadBeam", (3.0, 11.5, 3.75), (2.8, 0.65, 0.16), mats["red"], 0.04)
    # River beyond the terminal and a working ferry on the horizon.
    river_plane(mats, 22.0, 75, 28)
    for i, x in enumerate((-16, -8, 0, 8, 16)):
        cylinder(f"Riverfront_Light_Pole_{i}", (x, 12.0, 2.8), 0.06, 5.2, mats["aluminium"], 14)
        sphere(f"Riverfront_Light_{i}", (x, 12.0, 5.43), (0.15, 0.15, 0.12), mats["lamp"], 14, 8)
    ferry = bpy.data.objects.new("Meghna_Service_Ferry", None)
    bpy.context.collection.objects.link(ferry)
    ferry.location = (-5.0, 22.0, 0.0)
    box("Ferry_Hull", (-5.0, 22.0, 0.38), (9.0, 1.8, 0.80), mats["blue"], 0.18, ferry)
    box("Ferry_Main_Deck", (-5.0, 22.0, 0.87), (8.2, 1.65, 0.12), mats["wood"], 0.035, ferry)
    box("Ferry_Cabin", (-5.0, 22.0, 1.80), (4.1, 1.4, 1.70), mats["cream"], 0.08, ferry)
    box("Ferry_Wheelhouse_Glass", (-5.0, 22.0, 2.0), (3.55, 0.06, 0.88), mats["glass"], 0.018, ferry)
    animate_location(ferry, "Lobby_Ferry_Drift", [
        (1, (-12.0, 22.0, 0.0)), (144, (-5.5, 22.0, 0.05)),
        (288, (1.0, 22.0, 0.0)),
    ], True)
    # Suspended cable trays, work lamps, ventilation and rotating fans.
    for i in range(6):
        x = -12.5 + i * 5.0
        cylinder(f"Ceiling_Hanger_{i}", (x, 0.0, 7.7), 0.035, 1.8, mats["aluminium"], 12)
        box(f"Ceiling_Light_Casing_{i}", (x, 0.0, 7.05), (2.15, 0.52, 0.12), mats["white"], 0.045)
        box(f"Ceiling_Light_Diffuser_{i}", (x, -0.01, 6.97), (1.92, 0.34, 0.035), mats["lamp"], 0.018)
    fan = bpy.data.objects.new("Ceiling_Fan_Rotor", None)
    bpy.context.collection.objects.link(fan)
    fan.location = (0.0, 2.0, 7.15)
    cylinder("Fan_Motor", (0.0, 2.0, 7.30), 0.18, 0.45, mats["dark"], 24, parent=fan)
    for blade in range(4):
        a = blade * math.pi * 0.5
        blade_obj = box(f"Fan_Blade_{blade}", (math.cos(a) * 0.60, 2.0 + math.sin(a) * 0.60, 7.15), (0.92, 0.22, 0.055), mats["aluminium"], 0.03, fan)
        blade_obj.rotation_euler[2] = a
    fan.rotation_euler[2] = 0.0
    fan.keyframe_insert(data_path="rotation_euler", frame=1, group="Lobby_Fan_Loop")
    fan.rotation_euler[2] = math.tau
    fan.keyframe_insert(data_path="rotation_euler", frame=288, group="Lobby_Fan_Loop")
    if fan.animation_data and fan.animation_data.action:
        # Blender 5.2 uses layered Actions rather than the legacy Action.fcurves
        # collection. Leave the keyed fan track intact here; the Godot importer
        # marks this environmental clip as looping when the GLB is instantiated.
        fan.animation_data.action.name = "Lobby_Fan_Loop"
    # Tactical display antennas and satellite dishes on a mezzanine.
    for i, x in enumerate((-13.0, 13.0)):
        cylinder(f"Telemetry_Mast_{i}", (x, 3.8, 5.2), 0.045, 4.6, mats["aluminium"], 14)
        for level in range(3):
            cylinder(f"Telemetry_Collar_{i}_{level}", (x, 3.8, 4.0 + level * 1.2), 0.11, 0.045, mats["brass"], 18)
        dish = sphere(f"Telemetry_Dish_{i}", (x, 3.8, 7.6), (0.52, 0.18, 0.52), mats["aluminium"], 24, 14)
        dish.rotation_euler[0] = math.radians(26)
    # An editorial sequence of camera cuts makes each operator a readable
    # subject. A wide frame establishes the hall; portrait lenses then give each
    # roster member their own moment; the film returns to the group before
    # settling on the default selected operator for the UI hand-off.
    cam = camera(scene, "Lobby_Art_Review_Camera", (0.0, -10.4, 3.85), (0.0, 0.1, 1.45), 44.0)
    animate_camera_path(cam, "Lobby_Group_Dolly_Performance", [
        (1, (-0.7, -11.2, 4.15), (0.0, 0.0, 1.45)),
        (48, (-0.25, -10.5, 3.85), (0.0, 0.1, 1.45)),
        (163, (0.0, -10.3, 3.75), (0.0, 0.1, 1.45)),
        (220, (0.35, -10.0, 3.7), (0.0, 0.1, 1.5)),
    ])

    field_cut = camera(scene, "Lobby_Field_Ranger_Portrait_Camera", (0.0, -7.4, 2.85), (0.0, 0.0, 1.45), 70.0)
    animate_camera_path(field_cut, "Lobby_Field_Ranger_Portrait_Dolly", [
        (49, (0.20, -7.8, 2.95), (0.0, 0.0, 1.45)),
        (86, (-0.10, -7.35, 2.8), (0.0, 0.0, 1.45)),
    ])
    delta_cut = camera(scene, "Lobby_Delta_Recon_Portrait_Camera", (-3.35, -7.4, 2.85), (-3.35, 0.0, 1.45), 70.0)
    animate_camera_path(delta_cut, "Lobby_Delta_Recon_Portrait_Dolly", [
        (87, (-3.10, -7.8, 2.95), (-3.35, 0.0, 1.45)),
        (124, (-3.45, -7.35, 2.8), (-3.35, 0.0, 1.45)),
    ])
    river_cut = camera(scene, "Lobby_River_Scout_Portrait_Camera", (3.35, -7.4, 2.85), (3.35, 0.0, 1.45), 70.0)
    animate_camera_path(river_cut, "Lobby_River_Scout_Portrait_Dolly", [
        (125, (3.60, -7.8, 2.95), (3.35, 0.0, 1.45)),
        (162, (3.25, -7.35, 2.8), (3.35, 0.0, 1.45)),
    ])
    selected_cut = camera(scene, "Lobby_Selected_Operator_Closeup_Camera", (-0.65, -6.3, 2.55), (-0.2, 0.0, 1.52), 78.0)
    animate_camera_path(selected_cut, "Lobby_Selected_Operator_Hero_Dolly", [
        (221, (-0.85, -6.6, 2.65), (-0.2, 0.0, 1.52)),
        (288, (-0.45, -6.15, 2.52), (-0.2, 0.0, 1.52)),
    ])

    register_camera_cut(scene, cam, 1, "B1_COMMAND_HALL_ESTABLISHING")
    register_camera_cut(scene, field_cut, 49, "B2_FIELD_RANGER_PORTRAIT")
    register_camera_cut(scene, delta_cut, 87, "B3_DELTA_RECON_PORTRAIT")
    register_camera_cut(scene, river_cut, 125, "B4_RIVER_SCOUT_PORTRAIT")
    register_camera_cut(scene, cam, 163, "B5_THREE_OPERATOR_GROUP")
    register_camera_cut(scene, selected_cut, 221, "B6_SELECTED_OPERATOR_HANDOFF")
    # Three independent roster GLBs; all temporary review subjects are removed before export.
    previews = []
    field_preview = add_operator_preview(
        operator_glb, (0.0, 0.0, 0.24), "Lobby_Field_Ranger_Preview",
        "Rifle idle (low ready)",
    )
    field_preview.scale = (0.96, 0.96, 0.96)
    face_operator_to_camera(field_preview, cam)
    previews.append(field_preview)
    delta_preview = add_operator_preview(
        delta_operator_glb, (-3.35, 0.0, 0.24), "Lobby_Delta_Recon_Preview",
        "Pistol idle (low ready)",
    )
    delta_preview.scale = (0.88, 0.88, 0.88)
    face_operator_to_camera(delta_preview, cam)
    previews.append(delta_preview)
    river_preview = add_operator_preview(
        river_operator_glb, (3.35, 0.0, 0.24), "Lobby_River_Scout_Preview",
        "Look around",
    )
    river_preview.scale = (0.88, 0.88, 0.88)
    face_operator_to_camera(river_preview, cam)
    previews.append(river_preview)
    scene.camera = cam
    return previews



def consolidate_static_meshes(scene: bpy.types.Scene) -> None:
    """Batch only truly static meshes; never destroy skinned character geometry."""
    groups: dict[tuple[str, str], list[bpy.types.Object]] = {}
    deforming_modifier_types = {"ARMATURE", "MESH_DEFORM", "SURFACE_DEFORM", "LATTICE", "HOOK"}
    for obj in list(scene.objects):
        if obj.type != "MESH" or obj.animation_data is not None:
            continue
        # Imported skinned GLB meshes commonly have animation on their Armature
        # object, not on the mesh object itself. Merging them by material bakes
        # away vertex groups/deformation and can make the character disappear.
        if any(modifier.type in deforming_modifier_types for modifier in obj.modifiers):
            continue
        ancestor = obj.parent
        under_armature = False
        while ancestor is not None:
            if ancestor.type == "ARMATURE":
                under_armature = True
                break
            ancestor = ancestor.parent
        if under_armature or obj.data.shape_keys is not None:
            continue
        if len(obj.data.materials) != 1 or obj.data.materials[0] is None:
            continue
        parent_key = obj.parent.name if obj.parent else "__WORLD_STATIC__"
        groups.setdefault((parent_key, obj.data.materials[0].name), []).append(obj)

    for (parent_name, material_name), objects in groups.items():
        if len(objects) < 2:
            continue
        parent = bpy.data.objects.get(parent_name) if parent_name != "__WORLD_STATIC__" else None
        material_slot = bpy.data.materials.get(material_name)
        if material_slot is None:
            continue
        bm = bmesh.new()
        for obj in objects:
            source_mesh = obj.data.copy()
            if parent is None:
                source_mesh.transform(obj.matrix_world)
            else:
                source_mesh.transform(obj.matrix_local)
            bm.from_mesh(source_mesh)
            bpy.data.meshes.remove(source_mesh)
        # Explicitly triangulate merged quads/ngons before glTF tangent export.
        if bm.faces:
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
        combined_mesh = bpy.data.meshes.new(f"Batch_{parent_name}_{material_name}")
        bm.to_mesh(combined_mesh)
        bm.free()
        combined_mesh.materials.append(material_slot)
        combined_mesh.update()
        combined = bpy.data.objects.new(f"Batch_{parent_name}_{material_name}", combined_mesh)
        scene.collection.objects.link(combined)
        if parent is not None:
            combined.parent = parent
            combined.matrix_parent_inverse = Matrix.Identity(4)
            combined.location = (0.0, 0.0, 0.0)
            combined.rotation_euler = (0.0, 0.0, 0.0)
            combined.scale = (1.0, 1.0, 1.0)
        for polygon in combined_mesh.polygons:
            polygon.use_smooth = False
        for obj in objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def validate_preview_rigs(previews: list[bpy.types.Object]) -> None:
    """Fail closed if static optimization has removed a roster operator's skin."""
    for wrapper in previews:
        skinned_meshes = [
            obj for obj in wrapper.children_recursive
            if obj.type == "MESH" and any(modifier.type == "ARMATURE" for modifier in obj.modifiers)
        ]
        if not skinned_meshes:
            raise RuntimeError(
                f"PREVIEW_RIG_GATE: {wrapper.name} has no surviving armature-deformed mesh."
            )
        print("PREVIEW_RIG_GATE:PASS", json.dumps({
            "preview": wrapper.name,
            "skinned_mesh_count": len(skinned_meshes),
            "source": str(wrapper.get("source_asset", "")),
            "sha256": str(wrapper.get("source_sha256", "")),
        }, sort_keys=True))


def render_film_preview(scene: bpy.types.Scene, output: pathlib.Path) -> pathlib.Path:
    """Render the complete 12-second cinematic with live roster rigs present."""
    output.parent.mkdir(parents=True, exist_ok=True)
    expected_output = output.with_suffix(".mp4")
    scene.render.filepath = str(output.with_suffix(""))
    # Blender 5.0+ filters file_format by media_type: choose VIDEO first.
    scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.use_file_extension = True
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.video_bitrate = 8000
    scene.render.ffmpeg.maxrate = 12000
    scene.render.fps = 24
    # Editorial review profile only: 1600x900 at 50% = 800x450, both even.
    # This keeps the 288-frame blocking/acting review practical on CPU EEVEE.
    # Master stills/final film renders use a separate full-quality profile.
    scene["film_review_profile"] = "EDITORIAL_PREVIEW_800x450_6SAMPLES"
    eevee = getattr(scene, "eevee", None)
    previous_render_samples = None
    if eevee is not None and hasattr(eevee, "taa_render_samples"):
        previous_render_samples = eevee.taa_render_samples
        eevee.taa_render_samples = 6
    scene.render.resolution_percentage = 50
    print("A_SQUARE_FILM_RENDER_START:", json.dumps({
        "path": str(expected_output),
        "resolution": [scene.render.resolution_x * 50 // 100, scene.render.resolution_y * 50 // 100],
        "fps": scene.render.fps,
        "frames": scene.frame_end - scene.frame_start + 1,
        "profile": scene["film_review_profile"],
        "eevee_render_samples": getattr(eevee, "taa_render_samples", None),
    }, sort_keys=True))
    try:
        bpy.ops.render.render(animation=True)
    finally:
        if eevee is not None and previous_render_samples is not None:
            eevee.taa_render_samples = previous_render_samples
    if not expected_output.is_file() or expected_output.stat().st_size < 100_000:
        raise RuntimeError(f"FILM_RENDER_GATE: H.264 MP4 was not produced: {expected_output}")
    report = {
        "path": str(expected_output),
        "bytes": expected_output.stat().st_size,
        "frames": scene.frame_end - scene.frame_start + 1,
        "fps": scene.render.fps,
        "duration_seconds": round((scene.frame_end - scene.frame_start + 1) / scene.render.fps, 3),
        "codec": "H.264",
        "operator_rigs_visible": True,
        "audio": "silent_review_render",
    }
    print("A_SQUARE_FILM_RENDER_PASS:", json.dumps(report, sort_keys=True))
    # Restore the still-image mode in the correct order before the PNG render.
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 75
    scene.frame_set(144)
    return expected_output

def triangulate_all_meshes(scene: bpy.types.Scene) -> None:
    """Triangulate only static meshes; preserve rigging and facial shape keys."""
    for obj in list(scene.objects):
        if obj.type != "MESH" or obj.data.shape_keys is not None:
            continue
        if any(modifier.type in {"ARMATURE", "MESH_DEFORM", "SURFACE_DEFORM", "LATTICE", "HOOK"} for modifier in obj.modifiers):
            continue
        if not any(len(poly.vertices) > 3 for poly in obj.data.polygons):
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        if bm.faces:
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()


def create_manifest(scene: bpy.types.Scene, args: argparse.Namespace) -> dict:
    mesh_count = sum(1 for obj in scene.objects if obj.type == "MESH")
    triangles = sum(len(poly.vertices) - 2 for obj in scene.objects if obj.type == "MESH" for poly in obj.data.polygons)
    materials = {slot.name for obj in scene.objects if obj.type == "MESH" for slot in obj.data.materials if slot}
    animations = sorted({obj.animation_data.action.name for obj in scene.objects if obj.animation_data and obj.animation_data.action})
    return {
        "asset_id": f"asquare_{args.kind}_environment_v1",
        "scene_role": scene.get("scene_role", ""),
        "authoring": "tools/blender/build_login_lobby_environments.py",
        "blender_version": bpy.app.version_string,
        "license": "CC0-1.0",
        "source_assets": _all_used_polyhaven_sources(),
        "operator_preview_source": str(scene.get("operator_preview_source", "")),
        "operator_preview_sha256": str(scene.get("operator_preview_sha256", "")),
        "operator_preview_sources": json.loads(str(scene.get("operator_preview_sources_json", "[]"))),
        "operator_preview_removed_before_export": scene.get("operator_preview_removed_before_export", False) is True,
        "camera_shakify": {
            "version": str(scene.get("camera_shakify_version", "")),
            "source_commit": str(scene.get("camera_shakify_source_commit", "")),
            "preset": str(scene.get("camera_shakify_preset", "")),
            "influence": float(scene.get("camera_shakify_influence", 0.0)),
            "scale": float(scene.get("camera_shakify_scale", 0.0)),
            "baked": scene.get("camera_shakify_baked", False) is True,
            "runtime_dependency": scene.get("camera_shakify_runtime_dependency", True) is True,
        },
        "operator_preview_license": {
            "generator_source": "https://github.com/olatunde85/3d-gen",
            "generator_code_license": "MIT",
            "character_mesh_morph_skin_hair_clothing_license": "CC0-1.0",
            "motion_capture": "CMU Graphics Lab Motion Capture Database; not for resale as a standalone converted motion asset",
            "preview_only": True,
        },
        "pbr_license": "CC0-1.0 Poly Haven maps where present; CC0-1.0 original generated fallback maps otherwise",
        "mesh_object_count": mesh_count,
        "triangle_count": triangles,
        "material_count": len(materials),
        "animation_clips": animations,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps,
        "output": args.out.name,
        "preview": args.preview.name,
        "status": "AUTHORED_CANDIDATE_NEEDS_ENGINE_AND_DEVICE_REVIEW",
    }


def main() -> int:
    args = parse_args()
    scene = clear_scene()
    mats = make_material_set()
    if args.kind == "login":
        operator_previews = [build_login(scene, mats, args.operator_glb)]
    else:
        if args.operator_glb_delta is None or args.operator_glb_river is None:
            raise ValueError("Lobby art review requires all three roster-matched operator GLBs.")
        operator_previews = build_lobby(
            scene, mats, args.operator_glb,
            args.operator_glb_delta, args.operator_glb_river,
        )
    consolidate_static_meshes(scene)
    validate_preview_rigs(operator_previews)
    triangulate_all_meshes(scene)
    validate_preview_rigs(operator_previews)
    scene.frame_set(144)
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.film_output is not None:
        render_film_preview(scene, args.film_output)
    scene.frame_set(144)
    scene.render.filepath = str(args.preview)
    bpy.ops.render.render(write_still=True)
    # Operator model is a render subject only; the engine scene uses the actual
    # player's HumanoidVisual and must not contain a second baked-in operator.
    for operator_preview in operator_previews:
        remove_operator_preview(operator_preview)
    bpy.ops.export_scene.gltf(
        filepath=str(args.out),
        export_format="GLB",
        export_animations=True,
        export_cameras=(args.kind == "login"),
        export_lights=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_yup=True,
        export_frame_range=True,
        export_frame_step=1,
        export_force_sampling=True,
        export_animation_mode="ACTIONS",
        export_skins=True,
        export_morph=True,
        export_apply=True,
    )
    manifest = create_manifest(scene, args)
    manifest_path = args.out.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("A_SQUARE_LOBBY_ART_READY:", json.dumps(manifest, sort_keys=True))
    print("ASSET_LICENSE:", LICENSE_TEXT.replace("\n", " | "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
