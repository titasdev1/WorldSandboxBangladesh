#!/usr/bin/env python3
"""Author a detailed, original Shariatpur river-town shopfront in Blender 5.2.4 LTS.

The asset is a curated visual archetype, not a claimed scan of a particular real
building. Its geometry, signage, PBR textures and composition are authored for
Project A-Square. It must be snapped to a verified OSM building footprint before
runtime placement and must not replace map navigation/collision data.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import subprocess
import sys
from typing import Iterable

import bpy
from mathutils import Vector

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSET_NAME = "A2_Shariatpur_Riverfront_Shophouse_HERO"
LICENSE_TEXT = """PROJECT A-SQUARE ORIGINAL ASSET
Asset: Shariatpur River-Town Shopfront — Hero Architecture Archetype
Authoring: Original geometry, composition, signage and materials authored with
Blender 5.2.4 LTS and the source tools shipped in this repository.
Copyright: Project A-Square / WorldSandboxBangladesh contributors.
License: CC0 1.0 Universal for the generated mesh, textures, materials and preview.
Provenance: No third-party game assets, satellite tiles, Google Earth/Maps 3D,
Mapillary/KartaView imagery or copyrighted building photographs are included.
Geographic status: A Bangladesh-rooted fictionalised architectural archetype.
It is not a surveyed copy of a specific Shariatpur building. Snap to a verified
OSM footprint and retain separate collision, doorway, floor and navigation data.
"""


def args_from_cli() -> argparse.Namespace:
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--textures", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def load_materials(texture_root: pathlib.Path) -> dict[str, bpy.types.Material]:
    profiles = {
        "plaster": ("weathered_teal_plaster", 0.91, 0.0),
        "brick": ("local_clay_brick", 0.92, 0.0),
        "steel": ("galvanized_rust_wear", 0.72, 0.28),
        "concrete": ("weathered_cast_concrete", 0.93, 0.0),
        "glass": ("smoked_shop_glass", 0.18, 0.12),
        "wood": ("aged_teak_wood", 0.83, 0.0),
        "sign": ("painted_signboard", 0.48, 0.08),
    }
    result: dict[str, bpy.types.Material] = {}
    for key, (folder, roughness_default, metallic_default) in profiles.items():
        folder_path = texture_root / folder
        base_path = folder_path / "base_color.png"
        normal_path = folder_path / "normal.png"
        rough_path = folder_path / "roughness.png"
        if not all(p.is_file() for p in (base_path, normal_path, rough_path)):
            raise FileNotFoundError(f"Missing PBR texture set for {key}: {folder_path}")
        mat = bpy.data.materials.new(f"A2_PBR_{key}")
        mat.diffuse_color = {
            "plaster": (0.62,0.70,0.62,1), "brick": (0.52,0.22,0.14,1),
            "steel": (0.42,0.46,0.45,1), "glass": (0.06,0.12,0.16,1),
            "wood": (0.38,0.24,0.14,1), "sign": (0.08,0.30,0.26,1), "concrete": (0.52,0.53,0.50,1),
        }[key]
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (620, 80)
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        principled.location = (340, 80)
        principled.inputs["Roughness"].default_value = roughness_default
        principled.inputs["Metallic"].default_value = metallic_default
        base_img = bpy.data.images.load(str(base_path), check_existing=True)
        normal_img = bpy.data.images.load(str(normal_path), check_existing=True)
        rough_img = bpy.data.images.load(str(rough_path), check_existing=True)
        for image in (base_img, normal_img, rough_img):
            image.pack()
        normal_img.colorspace_settings.name = "Non-Color"
        rough_img.colorspace_settings.name = "Non-Color"
        base_node = nodes.new("ShaderNodeTexImage"); base_node.image = base_img; base_node.location = (-620, 250)
        rough_node = nodes.new("ShaderNodeTexImage"); rough_node.image = rough_img; rough_node.location = (-620, -20)
        normal_node = nodes.new("ShaderNodeTexImage"); normal_node.image = normal_img; normal_node.location = (-620, -290)
        normal_map = nodes.new("ShaderNodeNormalMap"); normal_map.location = (-120, -270)
        links.new(base_node.outputs["Color"], principled.inputs["Base Color"])
        links.new(rough_node.outputs["Color"], principled.inputs["Roughness"])
        links.new(normal_node.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
        result[key] = mat
    lettering = bpy.data.materials.new("A2_Warm_Ivory_Sign_Lettering")
    lettering.diffuse_color = (0.92, 0.82, 0.61, 1.0)
    lettering.use_nodes = True
    lettering.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.92, 0.82, 0.61, 1.0)
    lettering.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.22
    lettering.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.43
    result["letter"] = lettering
    return result


ASSET_OBJECTS: list[bpy.types.Object] = []


def _register(obj: bpy.types.Object, role: str, material: bpy.types.Material | None = None) -> bpy.types.Object:
    obj.name = f"{role}_{len(ASSET_OBJECTS):03d}"
    obj["a2_role"] = role
    if material is not None:
        obj.data.materials.clear()
        obj.data.materials.append(material)
    ASSET_OBJECTS.append(obj)
    return obj


def _cube_uv(obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if obj.type == "MESH":
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.cube_project(cube_size=1.0)
        bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


def box(role: str, loc: tuple[float,float,float], dims: tuple[float,float,float], mat: bpy.types.Material,
        bevel: float = 0.025) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        mod = obj.modifiers.new("Soft machined and weathered edges", "BEVEL")
        mod.width = min(bevel, min(dims) * 0.22)
        mod.segments = 3
        mod.limit_method = "ANGLE"
        normal = obj.modifiers.new("Weighted architectural normals", "WEIGHTED_NORMAL")
        normal.keep_sharp = True
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.modifier_apply(modifier=normal.name)
    obj = _register(obj, role, mat)
    _cube_uv(obj)
    return obj


def cylinder(role: str, loc: tuple[float,float,float], radius: float, depth: float,
             mat: bpy.types.Material, vertices: int = 24, axis: str = "Z") -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    if axis == "Y": obj.rotation_euler.x = math.radians(90)
    elif axis == "X": obj.rotation_euler.y = math.radians(90)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bevel = obj.modifiers.new("Rounded pipe lip", "BEVEL"); bevel.width = min(0.018, radius*0.12); bevel.segments = 2
    bpy.context.view_layer.objects.active = obj; bpy.ops.object.modifier_apply(modifier=bevel.name)
    obj = _register(obj, role, mat)
    _cube_uv(obj)
    return obj


def curve(role: str, points: Iterable[tuple[float,float,float]], radius: float,
          mat: bpy.types.Material, cyclic: bool = False) -> bpy.types.Object:
    data = bpy.data.curves.new(role + "_curve", "CURVE")
    data.dimensions = "3D"; data.resolution_u = 12; data.bevel_depth = radius; data.bevel_resolution = 3
    spline = data.splines.new("POLY")
