#!/usr/bin/env python3
"""Author a complete Palong Bazar-inspired market-street corridor in Blender.

This is an original visual environment study based on independently recorded
place references around Sonali Bank / Palong Bazar–Nirala Road. It is not a
surveyed reconstruction of any exact property. Road/building geometry must be
snapped to verified OSM features before the asset is used as real map geometry.
No Google Maps/Street View images, 3D tiles, third-party photographs or game
assets are embedded.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
from collections import defaultdict

import bpy
from mathutils import Vector

BLENDER_EXPECTED = (5, 2, 4)
ASSET_NAME = "A2_Palong_Bazar_Market_Corridor_Study"
OBJECTS: list[bpy.types.Object] = []


def cli_args() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--textures", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def reset_scene() -> bpy.types.Object:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.images,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    root = bpy.data.objects.new(ASSET_NAME, None)
    bpy.context.scene.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root["a_square_asset"] = True
    return root


def register(obj: bpy.types.Object, role: str, root: bpy.types.Object) -> bpy.types.Object:
    obj.name = f"{role}_{len(OBJECTS):04d}"
    obj["a2_role"] = role
    matrix = obj.matrix_world.copy()
    obj.parent = root
    obj.matrix_world = matrix
    OBJECTS.append(obj)
    return obj


def _load_image(path: pathlib.Path, non_color: bool = False) -> bpy.types.Image:
    image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    image.pack()
    return image


def build_pbr_material(name: str, texture_root: pathlib.Path, folder: str,
                       tint: tuple[float, float, float] = (1.0, 1.0, 1.0),
                       metallic: float = 0.0, roughness_default: float = 0.78,
                       tint_strength: float = 0.34) -> bpy.types.Material:
    folder_path = texture_root / folder
    base_path = folder_path / "base_color.jpg"
    normal_path = folder_path / "normal.png"
    rough_path = folder_path / "roughness.png"
    if not all(p.is_file() for p in (base_path, normal_path, rough_path)):
        raise FileNotFoundError(f"Incomplete original PBR set: {folder_path}")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (700, 80)
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (430, 80)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness_default
    base_img = _load_image(base_path)
    normal_img = _load_image(normal_path, True)
    rough_img = _load_image(rough_path, True)
    base_node = nodes.new("ShaderNodeTexImage")
    base_node.image = base_img
    base_node.extension = "REPEAT"
    base_node.location = (-620, 260)
    tint_node = nodes.new("ShaderNodeMixRGB")
    tint_node.blend_type = "MULTIPLY"
    tint_node.inputs[0].default_value = tint_strength
    tint_node.inputs[2].default_value = (*tint, 1.0)
    tint_node.location = (0, 250)
    links.new(base_node.outputs["Color"], tint_node.inputs[1])
    links.new(tint_node.outputs["Color"], shader.inputs["Base Color"])
    rough_node = nodes.new("ShaderNodeTexImage")
    rough_node.image = rough_img
    rough_node.location = (-620, -10)
    links.new(rough_node.outputs["Color"], shader.inputs["Roughness"])
    normal_node = nodes.new("ShaderNodeTexImage")
    normal_node.image = normal_img
    normal_node.location = (-620, -250)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.location = (-80, -210)
    normal_map.inputs["Strength"].default_value = 0.75
    links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    mat.diffuse_color = (*tint, 1.0)
    return mat


def simple_material(name: str, color: tuple[float, float, float], rough: float = 0.65,
                    metallic: float = 0.0, emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metallic
    if emission > 0:
        shader.inputs["Emission Color"].default_value = (*color, 1.0)
        shader.inputs["Emission Strength"].default_value = emission
    return mat


def box(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
        material: bpy.types.Material | None, root: bpy.types.Object, bevel: float = 0.025,
        rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        uv_project: bool = True) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if uv_project and obj.type == "MESH":
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=1.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)
    if bevel > 0:
        mod = obj.modifiers.new("Worn eased edges", "BEVEL")
        mod.width = min(bevel, min(dimensions) * 0.18)
        mod.segments = 2
        mod.limit_method = "ANGLE"
        normal = obj.modifiers.new("Weighted architectural normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
    return register(obj, name, root)


def cylinder(name: str, location: tuple[float, float, float], radius: float, depth: float,
             material: bpy.types.Material | None, root: bpy.types.Object,
             vertices: int = 24, rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
             bevel: float = 0.012) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if bevel > 0:
        mod = obj.modifiers.new("Soft manufactured rim", "BEVEL")
        mod.width = min(bevel, depth * 0.15)
        mod.segments = 2
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return register(obj, name, root)


def sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
           material: bpy.types.Material, root: bpy.types.Object, segments: int = 16) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=max(8, segments // 2),
                                         radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return register(obj, name, root)


def curve_mesh(name: str, points: list[tuple[float, float, float]], bevel: float,
               material: bpy.types.Material, root: bpy.types.Object,
               resolution: int = 3) -> bpy.types.Object:
    data = bpy.data.curves.new(name + "_Curve", "CURVE")
    data.dimensions = "3D"
    data.resolution_u = max(2, resolution)
    data.bevel_depth = bevel
    data.bevel_resolution = 3
    poly = data.splines.new("POLY")
    poly.points.add(len(points) - 1)
    for item, point in zip(poly.points, points):
        item.co = (*point, 1.0)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.select_set(False)
    return register(obj, name, root)


def sign_material(key: str, texture_root: pathlib.Path) -> bpy.types.Material:
    path = texture_root / "signs" / f"{key}.png"
    if not path.is_file():
        raise FileNotFoundError(f"Missing shaped Bengali sign artwork: {path}")
    mat = bpy.data.materials.new("Bengali Sign " + key)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Roughness"].default_value = 0.57
    image_node = nodes.new("ShaderNodeTexImage")
    image_node.image = _load_image(path)
    links.new(image_node.outputs["Color"], shader.inputs["Base Color"])
    links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat


def sign_plane(name: str, side: int, front: float, y: float, z: float,
               width: float, height: float, material: bpy.types.Material,
               root: bpy.types.Object) -> bpy.types.Object:
    x = side * front
    vertices = [
        (x, y - width / 2, z - height / 2),
        (x, y + width / 2, z - height / 2),
        (x, y + width / 2, z + height / 2),
        (x, y - width / 2, z + height / 2),
    ]
    faces = [(0, 3, 2, 1)] if side > 0 else [(0, 1, 2, 3)]
    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name="UVMap")
    loops = mesh.loops
    for poly in mesh.polygons:
        for loop_index in poly.loop_indices:
            vi = loops[loop_index].vertex_index
            uv.data[loop_index].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][vi]
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material)
    return register(obj, name, root)


def _front(side: int, distance: float = 3.22) -> float:
    return side * distance


def make_window(side: int, y: float, z: float, width: float, height: float,
                front: float, mats: dict, root: bpy.types.Object, grille: bool = True) -> None:
    # Recessed dark glass with a deep concrete reveal, separate timber/steel frame and bars.
    x = side * (front - 0.10)
    box("Window_Recess_Shadow", (side * (front - 0.12), y, z), (0.10, width + 0.24, height + 0.25),
        mats["deep_shadow"], root, 0.014)
    box("Window_Glazing", (side * (front - 0.20), y, z),
        (0.035, width, height), mats["glass"], root, 0.008)
    frame_x = side * (front - 0.27)
    for dy in (-width / 2 - 0.08, width / 2 + 0.08):
        box("Window_Frame_Jamb", (frame_x, y + dy, z), (0.13, 0.13, height + 0.2),
            mats["painted_steel"], root, 0.012)
    for dz in (-height / 2 - 0.075, height / 2 + 0.075):
        box("Window_Frame_HeadSill", (frame_x, y, z + dz), (0.14, width + 0.28, 0.14),
            mats["aged_concrete"], root, 0.014)
    box("Window_Mullion", (side * (front - 0.24), y, z),
        (0.10, 0.055, height), mats["aged_concrete"], root, 0.009)
    if grille:
        for index in range(7):
            yy = y - width * 0.43 + index * width * 0.143
            cylinder("Window_Security_Grille_Vertical",
                     (side * (front - 0.30), yy, z), 0.018, height + 0.09,
                     mats["painted_steel"], root, vertices=8)
        cylinder("Window_Grille_Horizontal",
                 (side * (front - 0.30), y, z), 0.018, width + 0.1,
                 mats["painted_steel"], root, vertices=8, rotation=(math.pi / 2, 0, 0))


def make_balcony(side: int, y: float, z: float, width: float, front: float,
                 mats: dict, root: bpy.types.Object) -> None:
    center_x = side * (front - 0.56)
    box("Balcony_Concrete_Slab", (center_x, y, z), (1.12, width, 0.17),
        mats["aged_concrete"], root, 0.035)
    rail_x = side * (front - 1.04)
    cylinder("Balcony_Top_Rail", (rail_x, y, z + 0.92), 0.035, width,
             mats["painted_steel"], root, 12, rotation=(math.pi / 2, 0, 0))
    for yy in [y - width / 2 + 0.12 + i * 0.24 for i in range(max(2, int(width / 0.24)))]:
        cylinder("Balcony_Baluster", (rail_x, yy, z + 0.47), 0.018, 0.90,
                 mats["painted_steel"], root, 8)
    box("Balcony_Lower_Rail", (rail_x, y, z + 0.12), (0.06, width, 0.055),
        mats["painted_steel"], root, 0.012)


def make_shutter(side: int, y: float, front: float, width: float, z_bottom: float,
                 height: float, mats: dict, root: bpy.types.Object) -> None:
    x = side * (front - 0.18)
    box("Roller_Shutter_Recess", (side * (front - 0.09), y, z_bottom + height / 2),
        (0.10, width + 0.16, height + 0.14), mats["deep_shadow"], root, 0.012)
    box("Roller_Shutter_Panel", (x, y, z_bottom + height / 2),
        (0.075, width, height), mats["galvanized_shutter"], root, 0.012)
    for index in range(max(7, int(height / 0.10))):
        z = z_bottom + 0.10 + index * (height - 0.16) / max(1, int(height / 0.10) - 1)
        box("Roller_Shutter_Rib", (side * (front - 0.23), y, z),
            (0.035, width - 0.045, 0.018), mats["painted_steel"], root, 0.004)
    box("Shutter_Head_Box", (side * (front - 0.22), y, z_bottom + height + 0.095),
        (0.32, width + 0.20, 0.18), mats["painted_steel"], root, 0.04)


def make_awning(side: int, y: float, front: float, width: float, z: float,
                mats: dict, root: bpy.types.Object, stripe: bool = False) -> None:
    rotation = (0.0, -side * 0.11, 0.0)
    center_x = side * (front - 0.72)
    box("Corrugated_Awning_Frame", (center_x, y, z), (1.42, width + 0.18, 0.08),
        mats["painted_steel"], root, 0.015, rotation=rotation)
    if stripe:
        palette = [mats["awning_red"], mats["market_canvas"], mats["awning_blue"]]
        count = max(5, int(width / 0.32))
        for index in range(count):
            yy = y - width / 2 + (index + 0.5) * width / count
            box("Striped_Canvas_Awning", (side * (front - 0.76), yy, z + 0.045),
                (1.38, width / count + 0.006, 0.045), palette[index % len(palette)],
                root, 0.006, rotation=rotation)
    else:
        box("Aged_Canvas_Awning", (side * (front - 0.76), y, z + 0.042),
            (1.38, width, 0.05), mats["market_canvas"], root, 0.014, rotation=rotation)
    for yy in (y - width / 2 + 0.08, y + width / 2 - 0.08):
        curve_mesh("Awning_Support_Brace",
                   [(side * (front - 0.14), yy, z - 0.24),
                    (side * (front - 0.47), yy, z - 0.10),
                    (side * (front - 1.35), yy, z - 0.42)],
                   0.028, mats["painted_steel"], root, 2)


def make_ac_unit(side: int, y: float, z: float, front: float,
                 mats: dict, root: bpy.types.Object) -> None:
    x = side * (front - 0.22)
    box("AC_Condenser_Cabinet", (x, y, z), (0.55, 0.92, 0.48),
        mats["painted_steel"], root, 0.045)
    for index in range(8):
        yy = y - 0.29 + index * 0.083
        box("AC_Condenser_Fin", (side * (front - 0.51), yy, z),
            (0.025, 0.04, 0.30), mats["aged_concrete"], root, 0.006)
    cylinder("AC_Condenser_Fan_Ring", (side * (front - 0.535), y, z),
             0.16, 0.035, mats["painted_steel"], root, 32,
             rotation=(0, math.pi / 2, 0))


def make_water_tank(side: int, y: float, roof_z: float, mats: dict,
                    root: bpy.types.Object, color: tuple[float, float, float]) -> None:
    x = side * 5.35
    cylinder("Rooftop_Water_Tank_Body", (x, y, roof_z + 1.00), 0.78, 1.72,
             mats["water_tank"], root, 48)
    cylinder("Rooftop_Water_Tank_Rim", (x, y, roof_z + 1.88), 0.79, 0.10,
             mats["painted_steel"], root, 48)
    cylinder("Rooftop_Water_Tank_Lid", (x, y, roof_z + 1.94), 0.72, 0.07,
             mats["water_tank"], root, 48)
    for dx in (-0.46, 0.46):
        for dy in (-0.45, 0.45):
            box("Water_Tank_Support", (x + dx, y + dy, roof_z + 0.27),
                (0.11, 0.11, 0.55), mats["aged_concrete"], root, 0.012)


def add_store_interior(side: int, y: float, width: float, front: float,
                       mats: dict, root: bpy.types.Object, kind: str) -> None:
    # Only the first 0.6–1.0 m is modelled behind the frontage; the real building
    # interior/floor plan is a separate identity-linked gameplay layer.
    back_x = side * (front + 0.32)
    warm = mats["warm_light"]
    box("Shop_Interior_Back_Wall", (back_x, y, 1.55), (0.18, width, 2.9),
        mats["interior_wall"], root, 0.005)
    for shelf_y in (y - width * 0.32, y, y + width * 0.32):
        box("Shop_Left_Rack_Shelf", (side * (front + 0.02), shelf_y, 1.35),
            (0.65, 0.10, 0.08), mats["wood"], root, 0.012)
        box("Shop_Left_Rack_Shelf", (side * (front + 0.02), shelf_y, 2.02),
            (0.65, 0.10, 0.08), mats["wood"], root, 0.012)
        if kind in ("grocery", "hardware", "pharmacy"):
            for item in range(3):
                col = [mats["goods_red"], mats["goods_green"], mats["goods_gold"]][(item + int(shelf_y * 10)) % 3]
                box("Shop_Stock_Packaging", (side * (front + 0.08), shelf_y + (item - 1) * 0.14, 1.68),
                    (0.34, 0.10, 0.28), col, root, 0.016)
    box("Shop_Counter_Stone_Top", (side * (front + 0.40), y, 1.10),
        (0.88, width * 0.62, 0.12), mats["aged_concrete"], root, 0.025)
    if kind == "sweets":
        box("Sweets_Display_Case_Base", (side * (front + 0.31), y, 1.34),
            (0.55, width * 0.55, 0.36), mats["wood"], root, 0.025)
        for yy in (y - width * 0.25, y + width * 0.25):
            box("Sweets_Display_Glass", (side * (front + 0.09), yy, 1.55),
                (0.45, 0.025, 0.38), mats["glass"], root, 0.01)
        for index in range(8):
            yy = y - width * 0.23 + index * width * 0.065
            sphere("Sweet_Tray_Item", (side * (front + 0.08), yy, 1.48),
                   (0.07, 0.06, 0.045), mats["sweet_gold"], root, 12)
    # Warm shop bulbs add realistic depth through the glazing.
    cylinder("Shop_Warm_Lamp", (side * (front + 0.50), y, 2.70),
             0.09, 0.16, warm, root, 16)


def add_shop_sign(side: int, y: float, front: float, width: float, z: float,
                  key: str, sign_mats: dict, mats: dict, root: bpy.types.Object) -> None:
    sign_width = min(width * 0.94, 4.3)
    sign_height = 1.18 if key in ("haru_ghosh_sweets", "sonali_bank") else 0.95
    center_front = front - 0.17
    box("Shop_Signboard_Wood_Frame",
        (side * (front - 0.11), y, z),
        (0.20, sign_width + 0.18, sign_height + 0.16),
        mats["aged_wood"], root, 0.035)
    sign_plane("Shop_Signboard_Baked_Bengali_Face", side, center_front,
               y, z, sign_width, sign_height, sign_mats[key], root)
    for yy in (y - sign_width / 2 + 0.08, y + sign_width / 2 - 0.08):
        cylinder("Signboard_Bolt", (side * (front - 0.24), yy, z),
                 0.035, 0.02, mats["aged_concrete"], root, 8,
                 rotation=(0, math.pi / 2, 0))


def add_shop_front(side: int, y: float, width: float, height: float,
                   front: float, kind: str, sign_key: str, mats: dict,
                   sign_mats: dict, root: bpy.types.Object,
                   awning: bool = True) -> None:
    shop_width = min(width * 0.74, 4.25)
    door_width = width - shop_width
    if kind in ("bank", "fashion", "sweets", "pharmacy"):
        box("Shop_Recessed_Doorway", (side * (front - 0.10), y + width * 0.27, 1.70),
            (0.12, door_width * 0.72, 2.78), mats["deep_shadow"], root, 0.02)
        box("Shop_Entrance_Glazing", (side * (front - 0.19), y + width * 0.27, 1.66),
            (0.04, door_width * 0.55, 2.54), mats["glass"], root, 0.015)
        for yy in (y + width * 0.27 - door_width * 0.34,
                   y + width * 0.27 + door_width * 0.34):
            box("Shop_Door_Frame", (side * (front - 0.24), yy, 1.65),
                (0.11, 0.075, 2.70), mats["painted_steel"], root, 0.01)
        cylinder("Shop_Door_Handle", (side * (front - 0.30), y + width * 0.27, 1.55),
                 0.025, 0.28, mats["aged_concrete"], root, 12,
                 rotation=(math.pi / 2, 0, 0))
    else:
        make_shutter(side, y - width * 0.12, front, shop_width, 0.42, 2.30, mats, root)
        box("Shop_Deep_Interior_Glow", (side * (front - 0.08), y - width * 0.12, 1.65),
            (0.06, shop_width - 0.12, 2.25), mats["interior_wall"], root, 0.006)
    # A second narrow shutter or service opening gives each frontage a distinct rhythm.
    if kind in ("grocery", "hardware", "stationery", "pharmacy"):
        make_shutter(side, y - width * 0.38, front, max(0.8, door_width * 0.55),
                     0.44, 2.26, mats, root)
    add_store_interior(side, y, width * 0.68, front, mats, root, kind)
    add_shop_sign(side, y, front, width, 3.18, sign_key, sign_mats, mats, root)
    if awning:
        make_awning(side, y - width * 0.12, front, min(width * 0.88, 5.3),
                    2.86, mats, root, stripe=(kind in ("produce", "sweets", "grocery")))
    # Shop fascia and weathered concrete sill.
    box("Shopfront_Concrete_Sill", (side * (front - 0.10), y, 0.20),
        (0.18, width + 0.08, 0.25), mats["aged_concrete"], root, 0.02)


def add_balcony_details(side: int, y: float, z: float, width: float,
                        front: float, mats: dict, root: bpy.types.Object) -> None:
    make_balcony(side, y, z, width, front, mats, root)
    # Different privacy treatments: mixed louvres, grille, and laundry rail.
    for index in range(6):
        yy = y - width * 0.42 + index * width * 0.168
        box("Balcony_Painted_Louvre", (side * (front - 0.68), yy, z + 0.58),
            (0.07, 0.16, 0.25 + (index % 2) * 0.06), mats["aged_wood"], root, 0.01)
    curve_mesh("Balcony_Clothesline",
               [(side * (front - 0.93), y - width * 0.40, z + 1.05),
                (side * (front - 0.93), y + width * 0.40, z + 0.92)],
               0.012, mats["cable"], root, 2)


def add_building(side: int, center_y: float, width: float, floors: int,
                 kind: str, sign_key: str, base_material: str,
                 seed: int, mats: dict, sign_mats: dict,
                 root: bpy.types.Object) -> dict:
    rng = random.Random(seed)
    front = 3.24
    depth = rng.uniform(4.8, 6.2)
    floor_heights = [3.65, 2.92, 2.88, 2.75]
    height = floor_heights[0] + sum(floor_heights[1:floors])
    body_mat = mats[base_material]
    mass_center_x = side * (front + depth / 2)
    box("Attached_Mixed_Use_Concrete_Massing",
        (mass_center_x, center_y, height / 2),
        (depth, width, height), body_mat, root, 0.04)
    # Street-facing plinth and irregular repaired plaster panels.
    box("Building_Ground_Floor_Plinth",
        (side * (front - 0.025), center_y, 1.83), (0.12, width + 0.05, 3.62),
        mats["aged_concrete"] if kind == "bank" else body_mat, root, 0.018)
    for patch in range(3):
        py = center_y - width * 0.42 + patch * width * 0.38
        pz = rng.uniform(3.9, max(4.2, height - 0.8))
        pw = rng.uniform(0.45, 0.95)
        ph = rng.uniform(0.35, 0.75)
        box("Facade_Repair_Patch",
            (side * (front - 0.105), py, pz),
            (0.05, pw, ph), mats["repair_plaster"], root, 0.012)
    # Vertical concrete piers, floor bands and drain streaks break the blank wall planes.
    bay_count = max(2, int(width / 2.1))
    for index in range(bay_count + 1):
        yy = center_y - width / 2 + index * width / bay_count
        box("Facade_Concrete_Pier",
            (side * (front - 0.075), yy, height / 2),
            (0.18, 0.18, height), mats["aged_concrete"], root, 0.016)
    floor_z = 3.65
    for floor in range(1, floors):
        box("Facade_Floor_Band", (side * (front - 0.13), center_y, floor_z),
            (0.25, width + 0.22, 0.19), mats["aged_concrete"], root, 0.025)
        # Recessed windows vary in size and grouping by facade and floor.
        for bay in range(bay_count):
            yy = center_y - width / 2 + (bay + 0.5) * width / bay_count
            win_w = width / bay_count * rng.uniform(0.52, 0.68)
            win_h = rng.uniform(1.18, 1.62)
            z = floor_z + 1.02
            make_window(side, yy, z, win_w, win_h, front, mats, root,
                        grille=(kind not in ("bank",) or floor > 1))
            if rng.random() < 0.45:
                box("Concrete_Window_Chajja", (side * (front - 0.43), yy, z + win_h / 2 + 0.13),
                    (0.55, win_w + 0.27, 0.11), mats["aged_concrete"], root, 0.02)
        if floor == 1 and kind in ("fashion", "bank", "sweets"):
            add_balcony_details(side, center_y - width * 0.18, floor_z + 0.26,
                                width * 0.57, front, mats, root)
        floor_z += floor_heights[floor]
    add_shop_front(side, center_y, width, height, front, kind, sign_key,
                   mats, sign_mats, root, awning=(kind not in ("bank",)))
    # Rooftop parapet, stair head, tank, water lines and a mix of antennas.
    roof_z = height
    box("Rooftop_Front_Parapet", (side * (front - 0.08), center_y, roof_z + 0.50),
        (0.22, width + 0.18, 1.0), mats["aged_concrete"], root, 0.02)
    box("Rooftop_Stair_Head", (mass_center_x, center_y + width * 0.22, roof_z + 1.0),
        (2.05, min(2.8, width * 0.48), 2.0), body_mat, root, 0.035)
    box("Rooftop_Stair_Head_Door", (side * (front + 0.55), center_y + width * 0.22, roof_z + 0.78),
        (0.10, 0.75, 1.45), mats["deep_shadow"], root, 0.008)
    make_water_tank(side, center_y - width * 0.24, roof_z + 1.80, mats, root, (0.1, 0.2, 0.3))
    if rng.random() < 0.8:
        add_ac_y = center_y + width * rng.uniform(-0.34, 0.34)
        add_ac_unit(side, add_ac_y, floor_heights[0] + 1.9, front, mats, root)
    # Cable conduit and downpipes on every building, but vary their exact position.
    pipe_y = center_y - width * 0.43
    curve_mesh("Rainwater_Downpipe",
               [(side * (front - 0.24), pipe_y, roof_z + 0.6),
                (side * (front - 0.24), pipe_y, 2.9),
                (side * (front - 0.24), pipe_y + 0.18, 0.18)],
               0.045, mats["painted_steel"], root, 3)
    box("Utility_Meter_Cabinet", (side * (front - 0.19), pipe_y + 0.47, 1.20),
        (0.20, 0.48, 0.68), mats["aged_concrete"], root, 0.025)
    for index in range(6):
        z = 4.05 + index * 0.11
        curve_mesh("Cable_Conduit",
                   [(side * (front - 0.20), center_y - width * 0.47, z),
                    (side * (front - 0.20), center_y + width * 0.47, z + 0.03)],
                   0.018, mats["cable"], root, 2)
    return {"side": side, "center_y": center_y, "width": width, "height": height,
            "front": front, "kind": kind, "sign": sign_key}


def make_drain_and_walkway(mats: dict, root: bpy.types.Object) -> None:
    road_width = 3.9
    box("Uneven_Street_Asphalt", (0, 13.0, -0.13), (road_width, 47.0, 0.23),
        mats["wet_asphalt"], root, 0.006)
    for side in (-1, 1):
        # Drain trough and short broken concrete covers.
        x = side * 2.16
        box("Open_Roadside_Drain", (x, 13.0, -0.04), (0.25, 47.0, 0.12),
            mats["deep_shadow"], root, 0.003)
        for index in range(42):
            y = -9.6 + index * 1.11
            width = 0.78 if index % 7 else 0.40
            box("Broken_Drain_Cover_Slab", (side * 2.25, y, 0.10),
                (0.42, width, 0.14), mats["aged_concrete"], root, 0.012,
                rotation=(0, 0, math.radians((index % 3 - 1) * 2)))
        box("Patchwork_Footpath", (side * 2.78, 13.0, 0.03), (0.94, 47.0, 0.16),
            mats["aged_concrete"], root, 0.008)
        for index in range(26):
            y = -9.0 + index * 1.75
            box("Sidewalk_Repair_Tile", (side * 2.78, y, 0.12),
                (0.85, 0.018, 0.03), mats["repair_plaster"], root, 0.003)
        # Open drain slots and runoff stains.
        for index in range(60):
            y = -9.8 + index * 0.78
            box("Drain_Grille_Slot", (side * 2.16, y, 0.03),
                (0.23, 0.025, 0.025), mats["painted_steel"], root, 0.002)
    # Irregular wet patches, repaired tarmac and shallow puddles.
    random.seed(4107)
    for index in range(35):
        x = random.uniform(-1.75, 1.75)
        y = random.uniform(-8.0, 34.0)
        width = random.uniform(0.22, 1.12)
        length = random.uniform(0.45, 2.1)
        box("Asphalt_Repair_Patch", (x, y, 0.001), (width, length, 0.012),
            mats["asphalt_repair"] if index % 3 else mats["wet_asphalt"], root, 0.003,
            rotation=(0, 0, random.uniform(-0.17, 0.17)))
    for index in range(17):
        x = random.uniform(-1.65, 1.65)
        y = random.uniform(-7, 31)
        width = random.uniform(0.18, 0.85)
        length = random.uniform(0.30, 1.4)
        box("Monsoon_Road_Puddle", (x, y, 0.012), (width, length, 0.006),
            mats["puddle"], root, 0.035, rotation=(0, 0, random.uniform(-0.18, 0.18)))


def make_crate(location: tuple[float, float, float], mats: dict,
               root: bpy.types.Object, size: float = 0.55) -> None:
    x, y, z = location
    box("Market_Wood_Crate_Base", (x, y, z + size / 2),
        (size, size, size), mats["aged_wood"], root, 0.035)
    for face in range(4):
        for index in range(4):
            z0 = z + 0.08 + index * (size - 0.14) / 4
            if face == 0:
                loc = (x, y - size / 2 - 0.015, z0)
                dim = (size, 0.025, 0.065)
            elif face == 1:
                loc = (x, y + size / 2 + 0.015, z0)
                dim = (size, 0.025, 0.065)
            elif face == 2:
                loc = (x - size / 2 - 0.015, y, z0)
                dim = (0.025, size, 0.065)
            else:
                loc = (x + size / 2 + 0.015, y, z0)
                dim = (0.025, size, 0.065)
            box("Crate_Slat", loc, dim, mats["aged_wood"], root, 0.012)


def make_produce_cart(side: int, y: float, mats: dict, root: bpy.types.Object) -> None:
    # A narrow wheeled vendor table which visibly occupies the walkway edge.
    x = side * 2.68
    box("Produce_Cart_Frame", (x, y, 0.78), (0.80, 1.70, 0.13),
        mats["painted_steel"], root, 0.025)
    box("Produce_Cart_Top_Wood", (x, y, 0.90), (0.90, 1.78, 0.12),
        mats["aged_wood"], root, 0.025)
    for dx in (-0.28, 0.28):
        cylinder("Produce_Cart_Wheel", (x + side * dx, y - 0.55, 0.38),
                 0.24, 0.12, mats["rubber"], root, 20, rotation=(0, math.pi / 2, 0))
    produce_mats = [mats["produce_red"], mats["produce_green"], mats["produce_gold"]]
    random.seed(int(y * 100) + side * 9)
    for row in range(4):
        for col in range(5):
            xx = x + random.uniform(-0.30, 0.30)
            yy = y - 0.68 + col * 0.32
            zz = 1.08 + random.uniform(-0.015, 0.045)
            mat = produce_mats[(row + col + random.randrange(3)) % len(produce_mats)]
            sphere("Market_Fruit_Display", (xx, yy, zz),
                   (0.12, 0.115, random.uniform(0.09, 0.15)), mat, root, 12)
    # A patched fabric canopy with metal support rods.
    canopy_z = 2.18
    box("Vendor_Canopy", (side * 2.69, y, canopy_z), (1.36, 2.10, 0.055),
        mats["market_canvas"], root, 0.012, rotation=(0, -side * 0.06, 0))
    for xx in (side * 2.07, side * 3.29):
        for yy in (y - 0.88, y + 0.88):
            cylinder("Vendor_Canopy_Post", (xx, yy, 1.52), 0.025, 1.35,
                     mats["painted_steel"], root, 10)


def make_clothing_display(side: int, y: float, mats: dict, root: bpy.types.Object) -> None:
    x = side * 2.82
    curve_mesh("Clothing_Display_Rail",
               [(x, y - 1.12, 2.32), (x, y + 1.12, 2.32)],
               0.025, mats["painted_steel"], root)
    colours = [mats["fabric_red"], mats["fabric_blue"], mats["fabric_gold"],
               mats["fabric_green"]]
    for index in range(7):
        yy = y - 0.95 + index * 0.31
        curve_mesh("Hanger_Hook", [
            (x, yy, 2.27), (x, yy, 2.14), (x, yy - 0.09, 2.08),
            (x, yy, 2.00), (x, yy + 0.09, 2.08)
        ], 0.012, mats["painted_steel"], root, 2)
        box("Hanging_Garment_Body", (x + side * 0.09, yy, 1.45),
            (0.13, 0.30, 1.10), colours[index % len(colours)], root, 0.035)
        box("Garment_Sleeve_Left", (x + side * 0.08, yy - 0.16, 1.72),
            (0.12, 0.12, 0.45), colours[index % len(colours)], root, 0.025,
            rotation=(0.08, 0.0, -0.12))
        box("Garment_Sleeve_Right", (x + side * 0.08, yy + 0.16, 1.72),
            (0.12, 0.12, 0.45), colours[index % len(colours)], root, 0.025,
            rotation=(-0.08, 0.0, 0.12))


def make_sweet_shop_counter(side: int, y: float, mats: dict, root: bpy.types.Object) -> None:
    x = side * 2.70
    box("Sweets_Outdoor_Counter_Base", (x, y, 0.88), (0.82, 1.55, 0.72),
        mats["aged_wood"], root, 0.03)
    box("Sweets_Outdoor_Glass_Case", (x, y, 1.38), (0.72, 1.42, 0.30),
        mats["glass"], root, 0.02)
    box("Sweets_Case_Display_Shelf", (x - side * 0.38, y, 1.28),
        (0.035, 1.30, 0.045), mats["aged_concrete"], root, 0.008)
    for index in range(9):
        yy = y - 0.58 + index * 0.145
        sphere("Sweet_Tray_Laddu", (x - side * 0.20, yy, 1.40),
               (0.08, 0.075, 0.05), mats["sweet_gold"], root, 12)


def make_market_props(mats: dict, root: bpy.types.Object) -> None:
    make_produce_cart(-1, 1.7, mats, root)
    make_produce_cart(1, 9.7, mats, root)
    make_clothing_display(1, -2.1, mats, root)
    make_sweet_shop_counter(-1, 15.0, mats, root)
    # Crates, woven baskets and stools gather around stalls; placements are deliberately uneven.
    for side, y, count in [(-1, 4.8, 4), (1, 14.2, 3), (-1, 22.4, 4), (1, 27.8, 3)]:
        random.seed(int((y + 80) * 19))
        for index in range(count):
            cx = side * random.uniform(2.55, 3.05)
            cy = y + random.uniform(-1.25, 1.25)
            make_crate((cx, cy, 0.15), mats, root, random.uniform(0.35, 0.52))
        stool_x = side * random.uniform(2.45, 2.80)
        cylinder("Market_Plastic_Stool_Seat", (stool_x, y + 1.48, 0.48),
                 0.22, 0.12, mats["stool_red"] if side < 0 else mats["stool_blue"], root, 20)
        for angle in (0, 2.1, 4.2):
            leg_x = stool_x + 0.16 * math.cos(angle)
            leg_y = y + 1.48 + 0.16 * math.sin(angle)
            cylinder("Market_Plastic_Stool_Leg", (leg_x, leg_y, 0.24),
                     0.026, 0.40, mats["painted_steel"], root, 8)
    # A separate handcart, not an unrealistically clean vehicle hero.
    x = -2.72
    y = 23.5
    box("Handcart_Wood_Bed", (x, y, 0.85), (0.76, 1.35, 0.12), mats["aged_wood"], root, 0.025)
    for yy in (y - 0.48, y + 0.48):
        cylinder("Handcart_Wheel", (x, yy, 0.44), 0.27, 0.10,
                 mats["rubber"], root, 24, rotation=(math.pi / 2, 0, 0))
    curve_mesh("Handcart_Handle", [(x, y - 0.7, 0.84), (x - 0.45, y - 1.18, 0.9)],
               0.045, mats["painted_steel"], root, 2)
    make_crate((x, y + 0.03, 0.95), mats, root, 0.48)


def make_utility_poles_and_wires(mats: dict, root: bpy.types.Object) -> None:
    for side, y in [(-1, 4.2), (1, 19.0), (-1, 28.5)]:
        x = side * 3.05
        cylinder("Concrete_Utility_Pole", (x, y, 4.9), 0.12, 9.6,
                 mats["aged_concrete"], root, 20)
        for dz in (7.2, 7.8, 8.3):
            curve_mesh("Utility_Pole_Cross_Arm",
                       [(x - 0.72, y, dz), (x + 0.72, y, dz)],
                       0.035, mats["painted_steel"], root, 2)
        for dz in (7.25, 7.82, 8.35):
            box("Electrical_Junction_Box", (x + side * 0.20, y + 0.24, dz - 0.65),
                (0.48, 0.36, 0.86), mats["aged_concrete"], root, 0.03)
    # Sagging bundled service wires across the narrow street and along shopfronts.
    for index, y in enumerate([-5.8, 2.4, 10.6, 18.3, 26.0, 33.0]):
        top = 7.9 + (index % 3) * 0.62
        points = []
        for step in range(13):
            t = step / 12.0
            x = -3.55 + 7.10 * t
            z = top - 0.65 * (4 * t * (1 - t)) + math.sin(t * math.pi * 2 + index) * 0.05
            points.append((x, y, z))
        curve_mesh("Overhead_Telecom_Power_Cable", points,
                   0.025 if index % 2 else 0.018, mats["cable"], root, 2)
    for side in (-1, 1):
        for index in range(3):
            y = -5.0 + index * 12.8
            curve_mesh("Facade_Low_Service_Cable",
                       [(side * 3.18, y, 5.1 + index * 0.22),
                        (side * 3.22, y + 5.8, 5.0 + index * 0.22)],
                       0.014, mats["cable"], root, 2)


def make_small_motorcycle(side: int, y: float, mats: dict, root: bpy.types.Object) -> None:
    # Low-key parked commuter motorcycle on the edge of the carriageway, viewed in perspective.
    x = side * 1.42
    for yy in (y - 0.60, y + 0.62):
        cylinder("Motorcycle_Tyre", (x, yy, 0.42), 0.35, 0.12,
                 mats["rubber"], root, 32, rotation=(math.pi / 2, 0, 0))
        cylinder("Motorcycle_Rim", (x, yy - 0.07, 0.42), 0.20, 0.025,
                 mats["painted_steel"], root, 24, rotation=(math.pi / 2, 0, 0))
        cylinder("Motorcycle_Axle", (x, yy, 0.42), 0.055, 0.22,
                 mats["aged_concrete"], root, 12, rotation=(math.pi / 2, 0, 0))
    curve_mesh("Motorcycle_Frame",
               [(x, y - 0.58, 0.46), (x + side * 0.10, y - 0.20, 0.85),
                (x, y + 0.12, 0.72), (x, y + 0.57, 0.42)],
               0.055, mats["painted_steel"], root, 3)
    box("Motorcycle_Seat", (x, y + 0.02, 0.93), (0.28, 0.72, 0.14),
        mats["rubber"], root, 0.07)
    sphere("Motorcycle_Fuel_Tank", (x - side * 0.02, y - 0.13, 1.02),
           (0.24, 0.39, 0.25), mats["motorcycle_paint"], root, 20)
    curve_mesh("Motorcycle_Handlebar",
               [(x, y - 0.48, 1.28), (x, y - 0.30, 1.52), (x + side * 0.22, y - 0.34, 1.55)],
               0.035, mats["painted_steel"], root, 2)
    cylinder("Motorcycle_Headlamp", (x - side * 0.02, y - 0.42, 1.32),
             0.12, 0.10, mats["warm_light"], root, 20,
             rotation=(math.pi / 2, 0, 0))
    box("Motorcycle_Rear_Luggage_Rack", (x, y + 0.52, 1.04),
        (0.31, 0.27, 0.05), mats["painted_steel"], root, 0.015)


def make_façade_posters(side: int, y: float, front: float, mats: dict,
                        root: bpy.types.Object) -> None:
    poster_colours = [mats["poster_red"], mats["poster_blue"], mats["poster_yellow"]]
    for index in range(3):
        poster_y = y - 0.62 + index * 0.62
        poster_z = 2.10 + (index % 2) * 0.12
        box("Layered_Wall_Poster_Paper", (side * (front - 0.20), poster_y, poster_z),
            (0.035, 0.48, 0.72), poster_colours[index], root, 0.003)
        box("Wall_Poster_Tape", (side * (front - 0.23), poster_y, poster_z + 0.30),
            (0.012, 0.12, 0.05), mats["aged_wood"], root, 0.002)


def batch_static_meshes_by_material(root: bpy.types.Object) -> int:
    """Bake modifiers and merge static meshes by material to keep draw calls bounded."""
    groups: dict[str, list[bpy.types.Object]] = defaultdict(list)
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        if obj.animation_data is not None:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for modifier in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        obj.select_set(False)
        key = obj.data.materials[0].name if obj.data.materials else "unassigned"
        groups[key].append(obj)
    batches = 0
    for key, objects in groups.items():
        if len(objects) == 1:
            batches += 1
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        active = objects[0]
        bpy.context.view_layer.objects.active = active
        bpy.ops.object.join()
        active.name = "STATIC | " + key.replace(" ", "_")[:80]
        active.data.name = active.name + " Mesh"
        active.select_set(False)
        batches += 1
    root["static_material_batches"] = batches
    root["source_mesh_object_count"] = len(OBJECTS)
    print(f"A2_PALONG_BATCHING: source_objects={len(OBJECTS)} material_batches={batches}")
    return batches


def create_materials(texture_root: pathlib.Path) -> tuple[dict, dict]:
    mats = {}
    mats["weathered_plaster"] = build_pbr_material("PBR Weathered Lime Plaster", texture_root, "weathered_plaster", (1.0, 0.96, 0.90), roughness_default=0.84)
    mats["plaster_mint"] = build_pbr_material("PBR Faded Mint Shop Paint", texture_root, "weathered_plaster", (0.72, 0.88, 0.78), roughness_default=0.84)
    mats["plaster_yellow"] = build_pbr_material("PBR Faded Yellow Shop Paint", texture_root, "weathered_plaster", (1.0, 0.82, 0.60), roughness_default=0.84)
    mats["plaster_blue"] = build_pbr_material("PBR Faded Blue Shop Paint", texture_root, "weathered_plaster", (0.73, 0.82, 0.91), roughness_default=0.84)
    mats["aged_concrete"] = build_pbr_material("PBR Aged Cast Concrete", texture_root, "aged_concrete", (0.91, 0.90, 0.84), roughness_default=0.92)
    mats["repair_plaster"] = build_pbr_material("PBR Patch Repair Plaster", texture_root, "weathered_plaster", (0.90, 0.85, 0.73), roughness_default=0.90)
    mats["brick"] = build_pbr_material("PBR Exposed Clay Brick", texture_root, "exposed_clay_brick", (1.0, 1.0, 1.0), roughness_default=0.88)
    mats["wet_asphalt"] = build_pbr_material("PBR Monsoon Asphalt", texture_root, "wet_asphalt", (1.0, 1.0, 1.0), roughness_default=0.65)
    mats["asphalt_repair"] = build_pbr_material("PBR Asphalt Repairs", texture_root, "wet_asphalt", (0.76, 0.73, 0.67), roughness_default=0.82)
    mats["galvanized_shutter"] = build_pbr_material("PBR Galvanized Roller Shutter", texture_root, "galvanized_shutter", (0.92, 0.94, 0.92), metallic=0.52, roughness_default=0.65)
    mats["painted_steel"] = build_pbr_material("PBR Painted Utility Steel", texture_root, "painted_steel", (0.72, 0.78, 0.73), metallic=0.42, roughness_default=0.72)
    mats["aged_wood"] = build_pbr_material("PBR Aged Teak Market Wood", texture_root, "aged_wood", (1.0, 1.0, 1.0), roughness_default=0.86)
    mats["market_canvas"] = build_pbr_material("PBR Woven Market Canvas", texture_root, "market_canvas", (1.0, 0.94, 0.80), roughness_default=0.93)
    mats["awning_red"] = build_pbr_material("PBR Faded Red Canvas", texture_root, "market_canvas", (0.95, 0.54, 0.42), roughness_default=0.92)
    mats["awning_blue"] = build_pbr_material("PBR Faded Blue Canvas", texture_root, "market_canvas", (0.50, 0.69, 0.82), roughness_default=0.92)
    mats["fabric_red"] = build_pbr_material("PBR Garment Fabric Red", texture_root, "market_canvas", (0.70, 0.16, 0.12), roughness_default=0.96)
    mats["fabric_blue"] = build_pbr_material("PBR Garment Fabric Blue", texture_root, "market_canvas", (0.12, 0.25, 0.65), roughness_default=0.96)
    mats["fabric_gold"] = build_pbr_material("PBR Garment Fabric Saffron", texture_root, "market_canvas", (0.87, 0.56, 0.15), roughness_default=0.96)
    mats["fabric_green"] = build_pbr_material("PBR Garment Fabric Green", texture_root, "market_canvas", (0.12, 0.39, 0.26), roughness_default=0.96)
    mats["glass"] = simple_material("Shopfront Smoked Glass", (0.055, 0.13, 0.16), 0.17, 0.18)
    mats["deep_shadow"] = simple_material("Shop Recess Shadow", (0.018, 0.025, 0.026), 0.97)
    mats["cable"] = simple_material("Overhead Cable Rubber", (0.025, 0.032, 0.035), 0.55)
    mats["rubber"] = simple_material("Tyre Rubber", (0.018, 0.020, 0.021), 0.91)
    mats["water_tank"] = simple_material("Aged Blue Water Tank", (0.13, 0.25, 0.31), 0.56, 0.08)
    mats["warm_light"] = simple_material("Warm Interior Lamp", (1.0, 0.58, 0.25), 0.24, 0.02, 2.0)
    mats["interior_wall"] = simple_material("Dim Shop Interior", (0.11, 0.10, 0.085), 0.92)
    mats["goods_red"] = simple_material("Retail Packaging Red", (0.55, 0.10, 0.055), 0.50)
    mats["goods_green"] = simple_material("Retail Packaging Green", (0.09, 0.34, 0.18), 0.55)
    mats["goods_gold"] = simple_material("Retail Packaging Ochre", (0.72, 0.43, 0.095), 0.53)
    mats["produce_red"] = simple_material("Produce Tomato", (0.65, 0.035, 0.025), 0.26)
    mats["produce_green"] = simple_material("Produce Green Mango", (0.17, 0.38, 0.065), 0.31)
    mats["produce_gold"] = simple_material("Produce Citrus", (0.95, 0.56, 0.045), 0.27)
    mats["sweet_gold"] = simple_material("Mishti Saffron", (0.92, 0.49, 0.13), 0.28)
    mats["poster_red"] = simple_material("Faded Wall Poster Red", (0.45, 0.09, 0.055), 0.87)
    mats["poster_blue"] = simple_material("Faded Wall Poster Blue", (0.08, 0.18, 0.33), 0.85)
    mats["poster_yellow"] = simple_material("Faded Wall Poster Yellow", (0.73, 0.54, 0.19), 0.88)
    mats["stool_red"] = simple_material("Old Plastic Stool Red", (0.49, 0.08, 0.055), 0.48)
    mats["stool_blue"] = simple_material("Old Plastic Stool Blue", (0.055, 0.20, 0.40), 0.48)
    mats["motorcycle_paint"] = simple_material("Motorcycle Deep Teal Paint", (0.025, 0.17, 0.16), 0.30, 0.45)
    mats["puddle"] = simple_material("Thin Monsoon Puddle", (0.10, 0.14, 0.15), 0.08, 0.04)
    sign_keys = ["sonali_bank", "nakkhatra_fashion", "haru_ghosh_sweets", "maa_store",
                 "fresh_produce", "pharmacy", "stationery"]
    sign_mats = {key: sign_material(key, texture_root) for key in sign_keys}
    return mats, sign_mats


def build_environment(out_path: pathlib.Path, texture_root: pathlib.Path,
                      preview_path: pathlib.Path, blend_path: pathlib.Path,
                      manifest_path: pathlib.Path) -> dict:
    if bpy.app.version[:3] < BLENDER_EXPECTED:
        raise RuntimeError(f"Need Blender >= {BLENDER_EXPECTED}, got {bpy.app.version[:3]}")
    for path in (out_path, preview_path, blend_path, manifest_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    if not (texture_root / "texture_manifest.json").is_file():
        raise FileNotFoundError("Run make_palong_bazaar_textures.py before Blender authoring")
    root = reset_scene()
    mats, sign_mats = create_materials(texture_root)
    print("A2_PROGRESS: art-directing Palong Bazar street block and facades")

    make_drain_and_walkway(mats, root)

    facades = [
        (-1, -5.0, 6.8, 4, "bank", "sonali_bank", "plaster_blue", 1),
        (-1, 2.0, 5.9, 3, "sweets", "haru_ghosh_sweets", "plaster_yellow", 2),
        (-1, 8.4, 6.2, 4, "grocery", "maa_store", "plaster_mint", 3),
        (-1, 15.2, 5.7, 3, "hardware", "stationery", "weathered_plaster", 4),
        (-1, 21.4, 6.0, 4, "pharmacy", "pharmacy", "plaster_blue", 5),
        (-1, 28.0, 7.0, 3, "stationery", "stationery", "plaster_yellow", 6),
        (1, -5.5, 6.1, 3, "fashion", "nakkhatra_fashion", "plaster_mint", 7),
        (1, 1.0, 6.3, 4, "grocery", "maa_store", "weathered_plaster", 8),
        (1, 7.8, 6.8, 4, "bank", "sonali_bank", "plaster_blue", 9),
        (1, 15.1, 5.8, 3, "produce", "fresh_produce", "plaster_yellow", 10),
        (1, 21.4, 6.0, 4, "fashion", "nakkhatra_fashion", "plaster_mint", 11),
        (1, 27.9, 7.0, 3, "sweets", "haru_ghosh_sweets", "weathered_plaster", 12),
    ]
    facade_records = []
    for side, y, width, floors, kind, sign, base_mat, seed in facades:
        record = add_building(side, y, width, floors, kind, sign, base_mat,
                              seed, mats, sign_mats, root)
        facade_records.append(record)
        make_façade_posters(side, y, record["front"], mats, root)

    print("A2_PROGRESS: furnishing local market frontage, handcarts and stalls")
    make_market_props(mats, root)
    make_utility_poles_and_wires(mats, root)
    make_small_motorcycle(1, 5.1, mats, root)

    # Low-height curbside details give the scene scale: bollards, paper, water and cable ties.
    for side in (-1, 1):
        for y in (-7.0, 6.2, 18.0, 29.4):
            cylinder("Sidewalk_Bollard", (side * 2.92, y, 0.43), 0.10, 0.82,
                     mats["aged_concrete"], root, 16)
    for index in range(28):
        x = -1.7 + (index % 7) * 0.54
        y = 2.8 + (index // 7) * 1.1
        box("Discarded_Market_Carton_Flake", (x, y, 0.04),
            (0.22, 0.28, 0.015), mats["aged_wood"], root, 0.004,
            rotation=(0, 0, math.radians((index % 5 - 2) * 7)))

    # Compose the view at player eye height along the narrow commercial lane.
    camera_data = bpy.data.cameras.new("Palong Bazar Eye-Level Gameplay Camera")
    camera = bpy.data.objects.new("Palong Bazar Eye-Level Gameplay Camera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.12, -13.5, 1.72)
    target = Vector((0.1, 9.0, 4.6))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 36
    camera_data.dof.use_dof = True
    camera_data.dof.focus_distance = 19.0
    camera_data.dof.aperture_fstop = 8.0
    scene = bpy.context.scene
    scene.camera = camera

    # A large soft humid-sky source, cool ambient fill and restrained warm shop spill.
    world = bpy.data.worlds.new("Humid Shariatpur Overcast Sky") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.29, 0.34, 0.38, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.62
    key_data = bpy.data.lights.new("Overcast Softbox Sky", "AREA")
    key_data.energy = 1750
    key_data.shape = "DISK"
    key_data.size = 13.0
    key = bpy.data.objects.new("Overcast Softbox Sky", key_data)
    scene.collection.objects.link(key)
    key.location = (-7.5, -4.0, 14.0)
    key.rotation_euler = (Vector((0, 8.0, 1.0)) - key.location).to_track_quat("-Z", "Y").to_euler()
    fill_data = bpy.data.lights.new("Street Bounce Fill", "AREA")
    fill_data.energy = 680
    fill_data.shape = "DISK"
    fill_data.size = 11.0
    fill = bpy.data.objects.new("Street Bounce Fill", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (4.0, 12.0, 10.5)
    fill.rotation_euler = (Vector((0, 7.0, 2.5)) - fill.location).to_track_quat("-Z", "Y").to_euler()

    # Store source and art direction. The GLB excludes cameras/lights; Godot supplies
    # runtime camera, ambient lighting and the existing live player/operator actor.
    root["geographic_status"] = "PALONG_BAZAAR_INSPIRED_CORRIDOR_STUDY_NOT_A_SURVEY"
    root["reference_coordinate_lat_lon"] = [23.2181182, 90.3486077]
    root["approximate_market_road_width_m"] = 3.9
    root["facade_count"] = len(facade_records)
    root["original_material_texture_count"] = len(mats)
    root["no_google_map_assets_copied"] = True

    print("A2_PROGRESS: batching static market geometry by material")
    batch_count = batch_static_meshes_by_material(root)

    # Configure high-quality but bounded offline rendering.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.filepath = str(preview_path)
    scene.render.image_settings.compression = 15
    scene.camera.data.lens = 36
    print("A2_PROGRESS: render 1600x900 Palong Bazar gameplay-camera preview")
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print("A2_PROGRESS: export Palong Bazar PBR corridor GLB")
    bpy.ops.object.select_all(action="DESELECT")
    for obj in scene.objects:
        if obj.type in {"MESH", "EMPTY"}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_image_format="AUTO",
    )
    manifest = {
        "schema_version": 1,
        "asset_name": ASSET_NAME,
        "status": "AUTHORED_VISUAL_CORRIDOR_REVIEW_PENDING_GODOT_ANDROID_QA",
        "geographic_status": "PALONG_BAZAAR_INSPIRED_CORRIDOR_STUDY_NOT_A_SURVEY",
        "reference_coordinate_lat_lon": [23.2181182, 90.3486077],
        "reference_landmarks": [
            "Sonali Bank Limited, Shariatpur",
            "Palong Bazar–Nirala Road",
            "Kotowal Bari Road",
            "Palong Model Thana",
            "Shariatpur Post Office",
            "Exim Bank Shariatpur",
            "District Scouts Office"
        ],
        "road_width_reference_m": 3.9,
        "facade_count": len(facade_records),
        "facades": facade_records,
        "material_count": len(mats) + len(sign_mats),
        "static_material_batches": batch_count,
        "texture_source": "Original procedural PBR and Bengali RAQM sign artwork",
        "license": "CC0-1.0",
        "source_images_embedded": False,
        "google_maps_3d_tiles_copied": False,
        "building_height_status": "ART_DIRECTED_NOT_VERIFIED_FLOOR_SURVEY",
        "interior_status": "FRONTAGE_GLIMPSES_ONLY_NOT_REAL_INTERIOR_CAPTURE",
        "limitations": [
            "Not a surveyed reconstruction of the Sonali Bank building or any other named property",
            "Road/facade composition is an art-directed corridor study informed by public map and street-photo references",
            "Snap individual frontages to verified OSM building footprints before replacing real map geometry",
            "The scene does not supply the full playable map navigation, collision or interior-floor graph",
            "No human actors are embedded; use the game's shared animated character rigs"
        ]
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("A2_PALONG_BAZAAR_READY:" + json.dumps({
        "glb": out_path.as_posix(),
        "preview": preview_path.as_posix(),
        "blend": blend_path.as_posix(),
        "facades": len(facade_records),
        "static_batches": batch_count,
        "material_count": len(mats) + len(sign_mats),
        "coordinate": [23.2181182, 90.3486077]
    }, ensure_ascii=False))
    return manifest


def main() -> int:
    args = cli_args()
    build_environment(args.out, args.textures, args.preview, args.blend, args.manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
