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
    parser.add_argument("--operator-glb", type=pathlib.Path, required=True, help="Exact roster-matched rigged Field Ranger GLB used for preview only.")
    return parser.parse_args(argv)


def clear_scene() -> bpy.types.Scene:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablock in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
        for block in list(datablock):
            if block.users == 0:
                datablock.remove(block)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 180
    scene.render.fps = 30
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    # A contact-sheet preview is intentionally lighter than the exported GLB.
    # It is for art-direction review, not final-resolution film rendering.
    scene.render.resolution_percentage = 55
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 16
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
        links.new(base_node.outputs["Color"], shader.inputs["Base Color"])
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
            links.new(base_node.outputs["Color"], ao_mix.inputs["Color1"])
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


def add_operator_preview(glb_path: pathlib.Path, location: tuple[float, float, float], name: str) -> bpy.types.Object:
    """Import the exact roster-matched rig only for preview rendering.

    The operator hierarchy is removed immediately after the PNG render. The
    gameplay GLB remains an environment-only scene; Godot supplies the live
    player's HumanoidVisual in the real login/lobby.
    """
    if not glb_path.is_file() or glb_path.stat().st_size <= 0:
        raise FileNotFoundError(f"Rigged operator preview GLB is missing: {glb_path}")
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    imported = [obj for obj in bpy.context.scene.objects if obj not in before]
    if not imported:
        raise RuntimeError(f"Blender glTF importer did not create objects for {glb_path}")

    roots = [obj for obj in imported if obj.parent not in imported]
    wrapper = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(wrapper)
    wrapper.location = location
    wrapper.scale = (0.90, 0.90, 0.90)
    wrapper["preview_only"] = True
    wrapper["source_asset"] = glb_path.name
    wrapper["source_sha256"] = hashlib.sha256(glb_path.read_bytes()).hexdigest()

    for obj in roots:
        original_basis = obj.matrix_basis.copy()
        obj.parent = wrapper
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = original_basis

    # Choose a real imported idle action for the still/contact-sheet pose.
    # The exported lobby environment never receives this operator or its clips.
    idle_actions = sorted(
        (action for action in bpy.data.actions if "idle" in action.name.lower()),
        key=lambda action: ("idle" not in action.name.lower(), action.name.lower()),
    )
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if armatures and idle_actions:
        for armature in armatures:
            armature.animation_data_create()
            try:
                armature.animation_data.action = idle_actions[0]
            except (AttributeError, TypeError, RuntimeError) as exc:
                print(f"OPERATOR_PREVIEW_IDLE_WARNING: {exc}")

    bpy.context.scene["operator_preview_source"] = glb_path.name
    bpy.context.scene["operator_preview_sha256"] = wrapper["source_sha256"]
    bpy.context.scene["operator_preview_only"] = True
    print("OPERATOR_PREVIEW_IMPORTED:", json.dumps({
        "name": name,
        "source": glb_path.name,
        "sha256": wrapper["source_sha256"],
        "objects": len(imported),
        "armatures": len(armatures),
        "idle_actions": [action.name for action in idle_actions[:4]],
    }, sort_keys=True))
    return wrapper


def remove_operator_preview(wrapper: bpy.types.Object | None) -> None:
    if wrapper is None or wrapper.name not in bpy.data.objects:
        return
    objects = list(wrapper.children_recursive)
    objects.append(wrapper)
    for obj in reversed(objects):
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


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
        hub.rotation_mode = "XYZ"
        hub.rotation_euler = (0.0, 0.0, 0.0)
        hub.keyframe_insert(data_path="rotation_euler", frame=1, group=f"CNG_Wheel_Rotation_{index}")
        hub.rotation_euler[1] = math.tau * 2.0
        hub.keyframe_insert(data_path="rotation_euler", frame=180, group=f"CNG_Wheel_Rotation_{index}")
        if hub.animation_data and hub.animation_data.action:
            hub.animation_data.action.name = f"CNG_Wheel_Rotation_{index}"
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
        "cng_green": material("CNG_Deep_Emerald_Paint", (0.012, 0.30, 0.19, 1), 0.31, 0.48, 46, 0.10),
        "cng_green_light": material("CNG_Emerald_Highlight", (0.025, 0.46, 0.27, 1), 0.29, 0.42, 38, 0.08),
        "cng_dark": material("CNG_Dark_Frame", (0.025, 0.08, 0.07, 1), 0.43, 0.68),
        "cream": material("CNG_Cream_Trim", PAINT_CREAM, 0.40, 0.24),
        "lamp": material("Warm_LED_Lamp", (0.96, 0.66, 0.31, 1), 0.20, 0.10, emission=1.8),
        "screen": material("Tactical_Screen_Emissive", (0.015, 0.32, 0.34, 1), 0.24, 0.15, emission=1.2),
        "red": material("Signal_Red_Enamel", RED, 0.38, 0.35),
        "waterline": material("Waterline_Teal", (0.06, 0.33, 0.33, 1), 0.23, 0.5, emission=0.08),
        "white": material("Warm_White_Lacquer", (0.73, 0.70, 0.61, 1), 0.34, 0.22),
        "wood": material("Oiled_Teak", (0.24, 0.12, 0.055, 1), 0.58, 0.06, 6, 0.12),
    }
    return mats


def river_plane(mats: dict[str, bpy.types.Material], y: float, width: float, depth: float) -> bpy.types.Object:
    water = box("Meghna_River_Surface", (0.0, y, -0.40), (width, depth, 0.18), mats["river"], 0.0)
    water["surface_role"] = "river_water"
    return water


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
    for i, args in enumerate([
        (-15.8, -10.0, 5.6, 3.8, 4, 0),
        (-9.2, -11.8, 4.2, 3.2, 5, 2),
        (-3.5, -12.3, 5.0, 3.7, 3, 1),
        (3.0, -11.2, 5.4, 3.4, 6, 3),
        (10.0, -11.8, 4.5, 3.3, 4, 0),
        (16.2, -10.0, 5.4, 3.8, 5, 2),
    ]):
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
    cng = add_cng("Shariatpur_Emerald_CNG", -5.0, 6.3, mats)
    animate_location(cng, "Login_CNG_Pass", [(1, (-14.0, 6.3, 0.0)), (90, (-2.0, 6.3, 0.0)), (180, (12.0, 6.3, 0.0))], True)
    boat = bpy.data.objects.new("River_Launch", None)
    bpy.context.collection.objects.link(boat)
    boat.location = (7.0, -17.0, 0.10)
    box("Launch_Hull", (7.0, -17.0, 0.35), (5.3, 1.22, 0.78), mats["blue"], 0.18, boat)
    box("Launch_Deck", (7.0, -17.0, 0.79), (4.8, 1.08, 0.12), mats["wood"], 0.04, boat)
    box("Launch_Cabin", (6.35, -17.0, 1.55), (2.35, 0.92, 1.38), mats["cream"], 0.08, boat)
    for side in (-1, 1):
        box(f"Launch_Window_{side}", (6.35, -17.0 + side * 0.48, 1.63), (1.75, 0.045, 0.60), mats["glass"], 0.018, boat)
        path_curve(f"Launch_Rail_{side}", [(4.6, -17.0 + side * 0.56, 1.07), (7.6, -17.0 + side * 0.56, 1.07), (9.2, -17.0 + side * 0.40, 0.95)], mats["aluminium"], 0.032, boat)
    animate_location(boat, "River_Launch_Glide", [(1, (10.0, -17.0, 0.10)), (180, (6.0, -17.0, 0.10))], True)
    # Login camera: a Z-up, river-facing composition from the near road toward
    # the varied shopfronts, tree canopy and Meghna launch. Every keyframe stores
    # a real look-at quaternion so animation never drifts into the sky or road.
    cam = camera(scene, "Login_Cinematic_Camera", (5.0, 18.0, 8.6), (0.0, -4.5, 2.4), 27.0)
    animate_camera_path(cam, "Login_Dolly_Reveal", [
        (1, (8.0, 20.0, 9.0), (0.0, -5.0, 3.0)),
        (90, (5.0, 18.0, 8.6), (0.0, -4.5, 2.4)),
        (180, (1.5, 15.0, 7.0), (-3.0, 4.0, 1.8)),
    ])
    scene.render.filepath = "//login_preview.png"
    operator_preview = add_operator_preview(operator_glb, (-4.0, 6.3, 0.05), "Login_Field_Ranger_Preview")
    operator_preview.rotation_euler[2] = math.pi
    return operator_preview


def build_lobby(scene: bpy.types.Scene, mats: dict[str, bpy.types.Material], operator_glb: pathlib.Path) -> bpy.types.Object:
    scene["scene_role"] = "A-Square Delta Command — Operator Lobby"
    world_and_lighting(scene, False)
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
    # Hall: dark steel ribs, high glazing, transom framing, roof louvres and light baffles.
    for i, x in enumerate((-14, -10.5, -7, -3.5, 0, 3.5, 7, 10.5, 14)):
        cylinder(f"Hall_Structural_Pillar_{i}", (x, -4.0, 4.65), 0.13, 9.0, mats["dark"], 24)
        box(f"Hall_Glass_Bay_{i}", (x + 1.70, -4.0, 4.25), (3.18, 0.09, 7.65), mats["glass"], 0.015)
        box(f"Hall_Transom_{i}", (x + 1.70, -4.10, 6.25), (3.18, 0.15, 0.085), mats["aluminium"], 0.016)
        box(f"Hall_Sill_{i}", (x + 1.70, -4.11, 0.75), (3.18, 0.16, 0.16), mats["aluminium"], 0.018)
    # Monumental canopy with a stepped soffit and warm reflected panels.
    box("Hall_Roof_Upper_Shell", (0.0, 0.1, 9.1), (32.0, 19.0, 0.48), mats["dark"], 0.12)
    box("Hall_Roof_Soffit", (0.0, 0.0, 8.78), (29.0, 16.0, 0.17), mats["blue"], 0.06)
    for i in range(27):
        x = -13.0 + i * 1.0
        box(f"Roof_Louvre_{i}", (x, 0.0, 8.61), (0.045, 15.4, 0.09), mats["aluminium"], 0.018)
    for side in (-1, 1):
        box(f"Hall_Roof_Fascia_{side}", (0.0, side * 8.8, 8.86), (31.0, 0.42, 0.35), mats["brass"], 0.06)
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
    animate_location(ferry, "Lobby_Ferry_Drift", [(1, (-12.0, 22.0, 0.0)), (180, (1.0, 22.0, 0.0))], True)
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
    fan.keyframe_insert(data_path="rotation_euler", frame=180, group="Lobby_Fan_Loop")
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
    # Operator-safe camera from the riverfront entrance through the glass hall.
    # The view includes floor contact, the overhead architecture, displays and
    # the ferry/river depth behind the hall; no primitive podium fills the frame.
    cam = camera(scene, "Lobby_Art_Review_Camera", (-7.0, 7.5, 3.8), (0.0, 0.0, 1.35), 38.0)
    animate_camera_path(cam, "Lobby_Camera_Inspection_Arc", [
        (1, (-8.0, 7.2, 3.6), (0.0, -0.2, 1.35)),
        (90, (-7.0, 7.5, 3.8), (0.0, 0.0, 1.35)),
        (180, (-6.0, 7.8, 3.7), (0.0, 0.5, 1.40)),
    ])



def consolidate_static_meshes(scene: bpy.types.Scene) -> None:
    """Collapse static meshes by material and animation parent to keep draw calls bounded."""
    groups: dict[tuple[str, str], list[bpy.types.Object]] = {}
    for obj in list(scene.objects):
        if obj.type != "MESH" or obj.animation_data is not None:
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
        operator_preview = build_login(scene, mats, args.operator_glb)
    else:
        operator_preview = build_lobby(scene, mats, args.operator_glb)
    consolidate_static_meshes(scene)
    scene.frame_set(90)
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.preview)
    bpy.ops.render.render(write_still=True)
    # Operator model is a render subject only; the engine scene uses the actual
    # player's HumanoidVisual and must not contain a second baked-in operator.
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
