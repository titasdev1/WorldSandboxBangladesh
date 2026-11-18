#!/usr/bin/env python3
"""Build an original, mobile-friendly A-Square ram-air parachute assembly.

Run with Blender:
  blender --background --python tools/build_battle_royale_parachute.py -- --out external_content/battle_royale_parachute/a_square_ram_air_canopy.glb

The model is authored from fabric-cell surfaces, structural ribs, suspension
lines, risers and a reinforced harness. It deliberately contains no logos,
text, flags or copied commercial-game insignia.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import sys
from typing import Iterable

import bpy
from mathutils import Vector


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "external_content" / "battle_royale_parachute" / "a_square_ram_air_canopy.glb"
LICENSE_TEXT = """PROJECT A-SQUARE ORIGINAL ASSET
Asset: A-Square Ram-Air Canopy and Harness
Authoring: Original Blender procedural/manual asset script in this repository.
Copyright: Project A-Square / WorldSandboxBangladesh contributors.
License: CC0 1.0 Universal for the generated mesh, materials and animation.
No third-party meshes, logos, national insignia, commercial-game assets or
Google/Mapillary/KartaView imagery are included in this generated asset.
"""


def parse_args() -> argparse.Namespace:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    return parser.parse_args(args)


def make_material(name: str, colour: tuple[float, float, float, float], roughness: float = 0.86, metallic: float = 0.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = colour
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = colour
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metallic
        if "Sheen Weight" in principled.inputs:
            principled.inputs["Sheen Weight"].default_value = 0.18
        if "Sheen Roughness" in principled.inputs:
            principled.inputs["Sheen Roughness"].default_value = 0.8
    return material


def parent_to(obj: bpy.types.Object, parent: bpy.types.Object) -> None:
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def add_curve(
    name: str,
    points: Iterable[tuple[float, float, float]],
    material: bpy.types.Material,
    bevel: float,
    parent: bpy.types.Object,
    cyclic: bool = False,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    point_list = list(points)
    spline.points.add(len(point_list) - 1)
    for point, coordinate in zip(spline.points, point_list):
        point.co = (*coordinate, 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    parent_to(obj, parent)
    return obj


def create_cube(
    name: str,
    location: tuple[float, float, float],
    scale: tuple[float, float, float],
    material: bpy.types.Material,
    parent: bpy.types.Object,
    bevel: float = 0.025,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new(name + "_SoftEdges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
        obj.modifiers.new(name + "_WeightedNormals", "WEIGHTED_NORMAL")
    obj.data.materials.append(material)
    parent_to(obj, parent)
    return obj


def create_torus(
    name: str,
    location: tuple[float, float, float],
    major_radius: float,
    minor_radius: float,
    material: bpy.types.Material,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(
        major_segments=24,
        minor_segments=8,
        location=location,
        major_radius=major_radius,
        minor_radius=minor_radius,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    parent_to(obj, parent)
    return obj


def airfoil_thickness(chord_u: float) -> float:
    x = max(0.0, min(1.0, chord_u))
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return 5.0 * 0.115 * (
        0.2969 * math.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x * x * x
        - 0.1015 * x * x * x * x
    )


def canopy_point(span_x: float, chord_u: float, upper: bool) -> Vector:
    half_span = 5.5
    span_factor = max(0.0, 1.0 - (span_x / half_span) ** 2)
    chord = 2.55 * (0.78 + 0.22 * math.sqrt(span_factor))
    y = (chord_u - 0.5) * chord
    arch = 0.50 * span_factor
    thickness = airfoil_thickness(chord_u) * chord
    z = 6.15 + arch + (thickness if upper else -thickness * 0.72)
    # A small trailing-edge reflex is used to keep the airfoil recognisably
    # inflated instead of looking like a flat umbrella.
    reflex = 0.12 * max(0.0, chord_u - 0.72) ** 2
    return Vector((span_x, y, z + reflex))


def create_canopy_mesh(
    parent: bpy.types.Object,
    materials: list[bpy.types.Material],
    cell_count: int = 28,
    chord_steps: int = 28,
    span_steps_per_cell: int = 3,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    material_indices: list[int] = []
    uv_faces: list[list[tuple[float, float]]] = []
    half_span = 5.5

    # Individual upper and lower cell panels give the ram-air wing real volume;
    # each span cell receives its own material boundary and seam edge.
    for cell in range(cell_count):
        x0 = -half_span + 2.0 * half_span * cell / cell_count
        x1 = -half_span + 2.0 * half_span * (cell + 1) / cell_count
        for upper in (True, False):
            base = len(vertices)
            for span_step in range(span_steps_per_cell + 1):
                span_x = x0 + (x1 - x0) * span_step / span_steps_per_cell
                for chord_step in range(chord_steps + 1):
                    chord_u = chord_step / chord_steps
                    vertices.append(tuple(canopy_point(span_x, chord_u, upper)))
            for span_step in range(span_steps_per_cell):
                for chord_step in range(chord_steps):
                    a = base + span_step * (chord_steps + 1) + chord_step
                    b = a + chord_steps + 1
                    faces.append((a, a + 1, b + 1, b) if upper else (a, b, b + 1, a + 1))
                    material_indices.append(cell % len(materials))
                    uv_faces.append([
                        (cell / cell_count, chord_step / chord_steps),
                        (cell / cell_count, (chord_step + 1) / chord_steps),
                        ((cell + 1) / cell_count, (chord_step + 1) / chord_steps),
                        ((cell + 1) / cell_count, chord_step / chord_steps),
                    ])

    mesh = bpy.data.meshes.new("A2_RamAir_28Cell_FabricMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.clear()
    for material in materials:
        mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new("Canopy_28_Inflated_Fabric_Cells", mesh)
    bpy.context.collection.objects.link(obj)
    parent_to(obj, parent)
    for polygon, material_index in zip(mesh.polygons, material_indices):
        polygon.material_index = material_index
        polygon.use_smooth = True

    uv_layer = mesh.uv_layers.new(name="Canopy_Fabric_UV")
    for polygon, uv_set in zip(mesh.polygons, uv_faces):
        for loop_index, uv in zip(polygon.loop_indices, uv_set):
            uv_layer.data[loop_index].uv = uv
    return obj


def create_canopy_structure(parent: bpy.types.Object, rib_material: bpy.types.Material, seam_material: bpy.types.Material) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    half_span = 5.5
    # 29 structural ribs, following the underside of each inflated airfoil cell.
    for rib_index in range(29):
        x = -half_span + 2.0 * half_span * rib_index / 28.0
        points = []
        for step in range(33):
            chord_u = step / 32.0
            p = canopy_point(x, chord_u, False)
            p.z -= 0.015
            points.append(tuple(p))
        objects.append(add_curve(
            f"Canopy_Rib_{rib_index:02d}",
            points,
            rib_material if rib_index % 4 == 0 else seam_material,
            0.012 if rib_index % 4 == 0 else 0.006,
            parent,
        ))

    # Reinforced leading and trailing hems are separate continuous textile seams.
    for chord_u, name in ((0.04, "Leading_Edge_Reinforcement"), (0.96, "Trailing_Edge_Hem")):
        points = [tuple(canopy_point(-half_span + 2.0 * half_span * i / 96.0, chord_u, True)) for i in range(97)]
        objects.append(add_curve(name, points, rib_material, 0.025, parent))
    return objects


def create_suspension_system(parent: bpy.types.Object, line_material: bpy.types.Material, riser_material: bpy.types.Material, metal_material: bpy.types.Material) -> list[bpy.types.Object]:
    objects: list[bpy.types.Object] = []
    half_span = 4.9
    span_stations = [-4.7, -3.55, -2.35, -1.15, 0.0, 1.15, 2.35, 3.55, 4.7]
    chord_rows = [0.15, 0.46, 0.74, 0.91]
    harness_left = (-0.32, 0.12, 1.35)
    harness_right = (0.32, 0.12, 1.35)
    for station_index, span_x in enumerate(span_stations):
        for row_index, chord_u in enumerate(chord_rows):
            start = canopy_point(span_x, chord_u, False)
            target = harness_left if station_index <= len(span_stations) // 2 else harness_right
            target = (target[0] + (station_index - 4) * 0.035, target[1], target[2])
            middle = (start + Vector(target)) * 0.5
            middle.z += 0.12 + 0.045 * row_index
            objects.append(add_curve(
                f"Suspension_Line_{station_index:02d}_{row_index}",
                [tuple(start), tuple(middle), target],
                line_material,
                0.0075 if row_index < 2 else 0.006,
                parent,
            ))

    # The risers are broad, separate webbing strips rather than a single wire.
    for side, x in (("L", -0.31), ("R", 0.31)):
        points = [
            (x, 0.15, 1.28),
            (x * 1.15, 0.17, 2.5),
            (x * 0.95, 0.05, 4.2),
            (x * 0.75, -0.10, 5.55),
        ]
        objects.append(add_curve(f"Main_Riser_{side}", points, riser_material, 0.045, parent))
        objects.append(create_torus(
            f"Riser_Carabiner_{side}",
            (x, 0.13, 1.68),
            0.09, 0.025, metal_material, parent
        ))
    return objects


def create_harness(parent: bpy.types.Object, webbing: bpy.types.Material, fabric: bpy.types.Material, metal: bpy.types.Material) -> list[bpy.types.Object]:
    objects = []
    # Harness seat and dorsal panel are ergonomic, bevelled and proportioned
    # for a 1.8 m operator; the live rig is attached at the harness anchor.
    objects.append(create_cube("Harness_Seat_Pan", (0.0, 0.12, 0.62), (0.72, 0.56, 0.16), webbing, parent, 0.08))
    objects.append(create_cube("Harness_Back_Protector", (0.0, 0.27, 1.18), (0.62, 0.22, 0.82), fabric, parent, 0.10))
    objects.append(create_cube("Harness_Lumbar_Pad", (0.0, 0.29, 0.90), (0.67, 0.24, 0.28), webbing, parent, 0.09))
    for side, x in (("L", -0.31), ("R", 0.31)):
        points = [
            (x, 0.36, 1.50),
            (x * 0.8, 0.37, 1.14),
            (x * 0.93, 0.31, 0.72),
            (x, 0.07, 0.62),
        ]
        objects.append(add_curve(f"Harness_Shoulder_Webbing_{side}", points, webbing, 0.055, parent))
        objects.append(create_cube(f"Harness_Adjuster_Buckle_{side}", (x * 0.90, 0.345, 1.0), (0.14, 0.045, 0.10), metal, parent, 0.018))
        objects.append(create_cube(f"Harness_Leg_Loop_{side}", (x * 0.86, 0.0, 0.38), (0.10, 0.55, 0.08), webbing, parent, 0.035))
    objects.append(add_curve(
        "Harness_Chest_Cross_Straps",
        [(-0.33, 0.40, 1.31), (-0.18, 0.44, 1.18), (0.0, 0.445, 1.16), (0.18, 0.44, 1.18), (0.33, 0.40, 1.31)],
        webbing, 0.045, parent
    ))
    objects.append(create_cube("Harness_Central_Buckle", (0.0, 0.46, 1.17), (0.19, 0.055, 0.16), metal, parent, 0.025))
    objects.append(create_cube("Reserve_Parachute_Pack", (0.0, 0.42, 1.70), (0.44, 0.28, 0.32), fabric, parent, 0.075))
    return objects


def animate_wing(root: bpy.types.Object, wing: bpy.types.Object) -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 120
    scene.render.fps = 30
    for frame, angle, roll in ((1, -0.012, -0.008), (30, 0.018, 0.012), (60, 0.0, 0.0), (90, -0.018, -0.012), (120, -0.012, -0.008)):
        wing.rotation_euler.y = angle
        wing.rotation_euler.x = roll
        wing.keyframe_insert(data_path="rotation_euler", frame=frame, group="Canopy_Wind_Sway")
    action = wing.animation_data.action if wing.animation_data else None
    if action:
        action.name = "A2_Parachute_Canopy_Wind_Sway"
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = "BEZIER"
            fcurve.modifiers.new("CYCLES")


def build_asset(output_path: pathlib.Path) -> dict:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    root = bpy.data.objects.new("A2_RamAir_Parachute_Root", None)
    bpy.context.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root["asset_role"] = "player_attached_ram_air_canopy"
    root["license"] = "CC0-1.0"
    root["origin"] = "Harness attachment point, centered behind operator"

    wing_root = bpy.data.objects.new("Canopy_Wind_Sway_Root", None)
    bpy.context.collection.objects.link(wing_root)
    parent_to(wing_root, root)

    fabric_olive = make_material("A2_Fabric_Olive", (0.19, 0.24, 0.17, 1.0))
    fabric_sand = make_material("A2_Fabric_Sand", (0.58, 0.53, 0.39, 1.0))
    fabric_orange = make_material("A2_Fabric_Rescue_Orange", (0.80, 0.19, 0.055, 1.0))
    fabric_graphite = make_material("A2_Fabric_Graphite", (0.085, 0.105, 0.10, 1.0))
    rib_material = make_material("A2_Reinforced_Rib", (0.12, 0.15, 0.12, 1.0))
    seam_material = make_material("A2_Stitching", (0.73, 0.68, 0.52, 1.0))
    line_material = make_material("A2_Suspension_Cord", (0.88, 0.82, 0.66, 1.0))
    webbing_material = make_material("A2_Harness_Webbing", (0.105, 0.125, 0.095, 1.0))
    metal_material = make_material("A2_Anodized_Aluminium", (0.38, 0.42, 0.39, 1.0), 0.32, 0.72)

    canopy = create_canopy_mesh(
        wing_root,
        [fabric_olive, fabric_sand, fabric_graphite, fabric_orange],
    )
    create_canopy_structure(wing_root, rib_material, seam_material)
    create_suspension_system(root, line_material, webbing_material, metal_material)
    create_harness(root, webbing_material, fabric_graphite, metal_material)
    animate_wing(root, wing_root)

    scene = bpy.context.scene
    scene.view_settings.view_transform = "AgX"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 60

    # Export the actual rigged-player attachment assembly, with no operator mesh.
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = root
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(output_path),
        export_format="GLB",
        export_animations=True,
        export_skins=False,
        export_morph=False,
        export_cameras=False,
        export_lights=False,
        export_apply=False,
        export_materials="EXPORT",
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_yup=True,
    )
    triangle_count = sum(len(obj.data.polygons) for obj in bpy.context.scene.objects if obj.type == "MESH")
    return {
        "file": str(output_path),
        "bytes": output_path.stat().st_size,
        "mesh_objects": sum(1 for obj in bpy.context.scene.objects if obj.type == "MESH"),
        "triangles": triangle_count,
        "fabric_cells": 28,
        "suspension_lines": 36,
        "license": "CC0-1.0",
        "animation": "A2_Parachute_Canopy_Wind_Sway",
        "player_mesh_included": False,
    }


def main() -> int:
    args = parse_args()
    output = args.out if args.out.is_absolute() else (ROOT / args.out)
    report = build_asset(output)
    print("A2_PARACHUTE_ASSET_READY:", json.dumps(report, sort_keys=True))
    license_path = output.with_name("LICENSE.txt")
    license_path.write_text(LICENSE_TEXT, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
