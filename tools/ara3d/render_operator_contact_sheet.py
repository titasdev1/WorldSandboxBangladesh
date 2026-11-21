#!/usr/bin/env python3
"""Render reviewable Blender contact sheets for the real Ara3D operator LOD GLBs.

This is a visual-review aid, not an automatic art-approval score. It imports the
actual high/medium/low candidates, preserves their materials and skeletons, and
renders front and three-quarter studio views from the pinned Blender toolchain.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--high", required=True, type=pathlib.Path)
    parser.add_argument("--medium", required=True, type=pathlib.Path)
    parser.add_argument("--low", required=True, type=pathlib.Path)
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    return parser.parse_args(argv)


def make_material(name: str, color: tuple[float, float, float, float], roughness: float = 0.72, metallic: float = 0.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Metallic"].default_value = metallic
    return material


def add_area_light(name: str, location: tuple[float, float, float], energy: float, color: tuple[float, float, float], size: float, target: Vector) -> None:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_text(body: str, name: str, location: tuple[float, float, float], size: float, material: bpy.types.Material) -> None:
    data = bpy.data.curves.new(name + "_Font", "FONT")
    data.body = body
    data.size = size
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.extrude = 0.0015
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    # Front-facing review camera is on negative Y; text normal points toward it.
    obj.rotation_euler.x = math.radians(90.0)
    data.materials.append(material)


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    bpy.context.view_layer.update()
    mins = Vector((float("inf"),) * 3)
    maxs = Vector((float("-inf"),) * 3)
    count = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            mins.x = min(mins.x, point.x)
            mins.y = min(mins.y, point.y)
            mins.z = min(mins.z, point.z)
            maxs.x = max(maxs.x, point.x)
            maxs.y = max(maxs.y, point.y)
            maxs.z = max(maxs.z, point.z)
            count += 1
    if count == 0 or maxs.z - mins.z <= 0.01:
        raise RuntimeError("Imported GLB has no measurable renderable mesh bounds.")
    return mins, maxs


def import_variant(label: str, path: pathlib.Path, center_x: float, target_height: float = 1.80) -> dict:
    if not path.is_file() or path.stat().st_size <= 20:
        raise RuntimeError(f"{label} candidate is missing or empty: {path}")
    before = set(bpy.data.objects)
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender glTF import did not finish for {label}: {result}")
    imported = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    if not meshes or not armatures:
        raise RuntimeError(f"{label} GLB did not import both meshes and its skeletal rig.")
    mins, maxs = world_bounds(imported)
    center = (mins + maxs) * 0.5
    height = maxs.z - mins.z
    scale = target_height / height

    anchor = bpy.data.objects.new(f"{label}_ReviewAnchor", None)
    bpy.context.collection.objects.link(anchor)
    anchor.matrix_world = Matrix.Identity(4)
    imported_set = set(imported)
    roots = [obj for obj in imported if obj.parent not in imported_set]
    for root in roots:
        original_world = root.matrix_world.copy()
        root.parent = anchor
        root.matrix_parent_inverse = Matrix.Identity(4)
        root.matrix_world = original_world

    target_center = Vector((center_x, 0.0, target_height * 0.5))
    anchor.scale = (scale, scale, scale)
    anchor.location = target_center - center * scale

    triangles = 0
    image_count = 0
    material_count = 0
    for obj in meshes:
        if obj.data:
            triangles += sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
            for material_slot in obj.material_slots:
                material = material_slot.material
                if not material:
                    continue
                material_count += 1
                if material.use_nodes and material.node_tree:
                    for node in material.node_tree.nodes:
                        if node.type == "TEX_IMAGE" and node.image:
                            image_count += 1

    return {
        "detail": label,
        "source": str(path),
        "source_bytes": path.stat().st_size,
        "mesh_objects": len(meshes),
        "armatures": len(armatures),
        "material_slots": material_count,
        "image_nodes": image_count,
        "triangles_blender_polygons": triangles,
        "source_bounds": {
            "min": [round(float(v), 4) for v in mins],
            "max": [round(float(v), 4) for v in maxs],
            "height": round(float(height), 4),
        },
        "preview_height_m": target_height,
    }


def configure_scene(out_dir: pathlib.Path, labels: list[str]) -> bpy.types.Camera:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 28
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.render.resolution_percentage = 100

    world = bpy.data.worlds.new("A2_Operator_Review_World") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.025, 0.034, 0.048, 1.0)
    background.inputs["Strength"].default_value = 0.42

    floor_material = make_material("A2_Review_Floor", (0.045, 0.057, 0.071, 1.0), 0.88)
    pedestal_material = make_material("A2_Review_Pedestal", (0.075, 0.092, 0.115, 1.0), 0.34, 0.48)
    label_material = make_material("A2_Review_Label", (0.82, 0.88, 0.94, 1.0), 0.55, 0.0)
    title_material = make_material("A2_Review_Title", (0.34, 0.77, 0.72, 1.0), 0.42, 0.0)

    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, -0.075))
    floor = bpy.context.object
    floor.name = "Review_Ground"
    floor.data.materials.append(floor_material)

    columns = [-2.65, 0.0, 2.65]
    for label, x in zip(labels, columns):
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=96, radius=0.78, depth=0.075,
            location=(x, 0.0, -0.015),
        )
        pedestal = bpy.context.object
        pedestal.name = f"{label}_Review_Pedestal"
        pedestal.data.materials.append(pedestal_material)
        bevel = pedestal.modifiers.new("Soft_Pedestal_Edge", "BEVEL")
        bevel.width = 0.035
        bevel.segments = 3
        pedestal.modifiers.new("Pedestal_Normals", "WEIGHTED_NORMAL")
        add_text(label.upper(), f"{label}_Review_Label", (x, -0.78, 2.12), 0.24, label_material)

    add_text("A-SQUARE  /  ORIGINAL OPERATOR  /  LOD ART REVIEW", "Review_Title", (0.0, -0.78, 2.48), 0.20, title_material)

    target = Vector((0.0, 0.0, 1.08))
    add_area_light("Key_Softbox", (0.0, -5.0, 7.2), 1050.0, (1.0, 0.88, 0.74), 5.0, target)
    add_area_light("Fill_Softbox", (-5.5, -3.0, 3.5), 700.0, (0.62, 0.76, 1.0), 4.0, target)
    add_area_light("Rim_Softbox", (1.0, 4.5, 6.0), 1250.0, (0.46, 0.72, 1.0), 3.0, target)
    add_area_light("Front_Fill", (5.0, -2.0, 2.2), 360.0, (1.0, 1.0, 1.0), 3.0, target)

    camera_data = bpy.data.cameras.new("A2_Operator_Review_Camera")
    camera = bpy.data.objects.new("A2_Operator_Review_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 8.25
    scene.camera = camera
    return camera


def render_views(camera: bpy.types.Camera, out_dir: pathlib.Path) -> list[str]:
    scene = bpy.context.scene
    target = Vector((0.0, 0.0, 1.08))
    views = [
        ("operator_lod_front.png", Vector((0.0, -13.0, 3.2))),
        ("operator_lod_three_quarter.png", Vector((4.1, -12.5, 3.5))),
    ]
    outputs: list[str] = []
    for file_name, location in views:
        camera.location = location
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(out_dir / file_name)
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        output = out_dir / file_name
        if not output.is_file() or output.stat().st_size < 20_000:
            raise RuntimeError(f"Blender rendered an empty/tiny review image: {output}")
        outputs.append(str(output))
    return outputs


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = ["high", "medium", "low"]
    paths = [args.high.resolve(), args.medium.resolve(), args.low.resolve()]
    configure_scene(out_dir, labels)
    columns = [-2.65, 0.0, 2.65]
    reports = [
        import_variant(label, path, center_x)
        for label, path, center_x in zip(labels, paths, columns)
    ]
    camera = bpy.context.scene.camera
    previews = render_views(camera, out_dir)
    report = {
        "status": "PREVIEW_RENDERED_NOT_ART_APPROVED",
        "blender_version": bpy.app.version_string,
        "renderer": "Cycles CPU",
        "variants": reports,
        "preview_images": previews,
        "review_notice": "Human visual review is still required for face, clothing fit, silhouette, materials, deformation and gameplay animation.",
    }
    report_path = out_dir / "preview_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("ARA_OPERATOR_PREVIEW_PASS:", json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
