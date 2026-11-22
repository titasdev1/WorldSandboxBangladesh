#!/usr/bin/env python3
"""Author the A-Square cinematic operator stage in Blender and export a Godot GLB.

Original project-owned set dressing: no third-party meshes or textures are bundled.
The scene is designed as a hero-character stage, not as gameplay geometry.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0,
             roughness: float = 0.5, emission: float = 0.0) -> bpy.types.Material:
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    if node:
        node.inputs["Base Color"].default_value = color
        node.inputs["Metallic"].default_value = metallic
        node.inputs["Roughness"].default_value = roughness
        if emission > 0.0:
            node.inputs["Emission Color"].default_value = color
            node.inputs["Emission Strength"].default_value = emission
    return mat


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    if obj.type == "MESH":
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def bevel(obj: bpy.types.Object, width: float, segments: int = 4) -> bpy.types.Object:
    mod = obj.modifiers.new("Soft machined edges", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.profile = 0.5
    obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return obj


def cube(name: str, loc: tuple[float, float, float], scale: tuple[float, float, float],
         mat: bpy.types.Material, edge: float = 0.0) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    if edge:
        bevel(obj, edge, 5)
    return obj


def curve(name: str, points: list[tuple[float, float, float]], radius: float,
          mat: bpy.types.Material, cyclic: bool = False) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 24
    data.bevel_depth = radius
    data.bevel_resolution = 4
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for bp, co in zip(spline.bezier_points, points):
        bp.co = co
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def cylinder(name: str, loc: tuple[float, float, float], radius: float,
             depth: float, mat: bpy.types.Material, vertices: int = 96) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth,
                                        location=loc)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    bevel(obj, min(0.035, depth * 0.22), 3)
    return obj


def torus(name: str, loc: tuple[float, float, float], major: float, minor: float,
          mat: bpy.types.Material, rotation: tuple[float, float, float] = (0, 0, 0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_segments=128, minor_segments=16,
                                     major_radius=major, minor_radius=minor,
                                     location=loc, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return obj


def text_mesh(name: str, body: str, loc: tuple[float, float, float],
              size: float, mat: bpy.types.Material,
              rotation: tuple[float, float, float] = (0, 0, 0)) -> bpy.types.Object:
    data = bpy.data.curves.new(name, "FONT")
    data.body = body
    data.size = size
    data.extrude = 0.002
    data.bevel_depth = 0.001
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = rotation
    data.materials.append(mat)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = name
    obj.select_set(False)
    return obj


def build_scene(out: Path, preview: Path, blend: Path) -> dict:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)

    graphite = material("A2 | Obsidian graphite", (0.018, 0.035, 0.052, 1), 0.72, 0.27)
    slate = material("A2 | Deep river slate", (0.055, 0.105, 0.125, 1), 0.48, 0.34)
    bronze = material("A2 | Warm brushed bronze", (0.52, 0.315, 0.12, 1), 0.82, 0.26)
    ivory = material("A2 | Bone porcelain", (0.78, 0.74, 0.63, 1), 0.16, 0.34)
    teal = material("A2 | River teal enamel", (0.035, 0.27, 0.29, 1), 0.58, 0.23)
    cyan = material("A2 | Luminous cyan", (0.12, 0.78, 0.83, 1), 0.24, 0.24, 2.4)
    amber = material("A2 | Luminous amber", (0.94, 0.53, 0.19, 1), 0.28, 0.28, 1.45)
    blackglass = material("A2 | Black glass", (0.008, 0.021, 0.029, 1), 0.64, 0.12)

    # Wide, low, architectural platform with a layered silhouette.
    cube("A2 | Stage foundation", (0, -0.36, 0), (11.6, 0.52, 7.2), graphite, 0.20)
    cube("A2 | Satin deck", (0, -0.075, 0), (11.18, 0.16, 6.82), slate, 0.13)
    cube("A2 | Front brass reveal", (0, -0.24, 3.58), (10.2, 0.06, 0.035), bronze, 0.014)
    cube("A2 | Side reveal L", (-5.74, -0.24, 0), (0.035, 0.06, 6.4), bronze, 0.014)
    cube("A2 | Side reveal R", (5.74, -0.24, 0), (0.035, 0.06, 6.4), bronze, 0.014)

    # The operator dais is a separate, raised, nested form with calm lighting.
    cylinder("A2 | Hero plinth lower", (0, 0.035, 0), 1.56, 0.20, graphite)
    cylinder("A2 | Hero plinth bronze", (0, 0.145, 0), 1.49, 0.045, bronze)
    cylinder("A2 | Hero plinth upper", (0, 0.195, 0), 1.39, 0.075, blackglass)
    torus("A2 | Plinth cyan ring", (0, 0.238, 0), 1.25, 0.018, cyan)
    torus("A2 | Plinth outer brass ring", (0, 0.105, 0), 1.52, 0.015, amber)

    # Two asymmetrical architectural wings create a cinematic frame without
    # competing with the full-height operator silhouette.
    cube("A2 | Left monolith", (-4.3, 2.1, -2.45), (0.44, 4.25, 0.52), graphite, 0.11)
    cube("A2 | Left inner reveal", (-4.03, 2.1, -2.15), (0.035, 3.6, 0.04), cyan, 0.012)
    cube("A2 | Right monolith", (4.3, 2.32, -2.55), (0.34, 4.65, 0.48), teal, 0.10)
    cube("A2 | Right inner reveal", (4.08, 2.3, -2.24), (0.035, 3.95, 0.04), amber, 0.012)
    cube("A2 | Crown beam", (0, 4.26, -2.55), (8.82, 0.26, 0.48), graphite, 0.12)
    cube("A2 | Crown brass inlay", (0, 4.1, -2.28), (7.35, 0.035, 0.028), bronze, 0.01)

    # River-line motif: two sweeping inlaid curves across the lower stage.
    curve("A2 | Padma river cyan inlay",
          [(-4.9, -0.035, 2.6), (-3.1, -0.025, 2.0), (-1.2, -0.025, 2.5),
           (0.6, -0.025, 1.9), (2.5, -0.025, 2.35), (4.9, -0.035, 1.65)],
          0.025, cyan)
    curve("A2 | Padma river bronze inlay",
          [(-4.5, -0.026, 2.94), (-2.8, -0.026, 2.4), (-0.8, -0.026, 2.82),
           (1.4, -0.026, 2.15), (3.3, -0.026, 2.7), (4.8, -0.026, 2.1)],
          0.012, bronze)
    # Back halo provides separation behind the character head/shoulders.
    torus("A2 | Hero halo ring", (0, 2.42, -2.02), 1.78, 0.027, cyan,
          rotation=(math.pi / 2, 0, 0))
    torus("A2 | Hero halo outer ring", (0, 2.42, -2.08), 2.05, 0.012, bronze,
          rotation=(math.pi / 2, 0, 0))

    # Deep vertical ribs with alternating finishes establish a restrained
    # architectural backdrop that reads as a set rather than UI decoration.
    for index, x in enumerate((-2.95, -2.0, -1.0, 0.0, 1.0, 2.0, 2.95)):
        height = 2.65 + (0.34 if index % 2 == 0 else 0.0)
        rib = cube("A2 | Backdrop rib %02d" % index, (x, 1.77 + height * 0.5, -2.62),
                   (0.055, height, 0.10), ivory if index in (0, 6) else slate, 0.018)
        rib.rotation_euler[1] = -0.10 if index < 3 else (0.10 if index > 3 else 0.0)

    # Engraved title and location line, with readable 3D lettering.
    text_mesh("A2 | Main stage wordmark", "A SQUARE", (-1.78, 3.77, -2.18), 0.38, ivory)
    text_mesh("A2 | Sector identity", "BANGLADESH  /  SHARIATPUR", (-1.38, 3.48, -2.17), 0.17, cyan)

    # Small illuminated markers are intentionally sparse and asymmetric.
    for name, loc, mat in (
        ("A2 | Marker amber left", (-3.75, 0.22, 0.9), amber),
        ("A2 | Marker cyan right", (3.72, 0.22, 0.6), cyan),
        ("A2 | Marker amber back", (3.25, 0.22, -1.0), amber),
    ):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.075, location=loc)
        marker = bpy.context.object
        marker.name = name
        assign(marker, mat)

    # Preview-only camera and softboxes. They are not included in the GLB.
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1440
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.025, 0.035, 0.045)
    scene.view_settings.view_transform = "AgX"
    scene.camera = None

    def point_camera(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.camera_add(location=(9.8, 7.4, 15.8))
    camera = bpy.context.object
    camera.name = "A2 | Preview camera"
    camera.data.lens = 58
    point_camera(camera, (0, 1.8, -0.1))
    scene.camera = camera

    for name, loc, energy, size, color in (
        ("A2 | Key softbox", (1.5, 8.5, 7.0), 1850, 7.0, (0.76, 0.88, 1.0)),
        ("A2 | Warm rim", (6.0, 5.0, -3.0), 1250, 5.0, (1.0, 0.61, 0.34)),
        ("A2 | Cool fill", (-7.0, 4.0, 0.2), 1050, 5.5, (0.3, 0.78, 0.89)),
    ):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.data.color = color
        point_camera(light, (0, 1.3, -0.3))

    preview.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(preview)
    bpy.ops.render.render(write_still=True)

    # Only the authored meshes are exported; preview camera/softboxes remain in .blend.
    export_objects = [obj for obj in scene.objects if obj.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(out),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    report = {
        "asset": "A-Square Cinematic Operator Stage",
        "source": "original Blender-authored geometry and materials",
        "license": "CC0-1.0 (original project-authored asset; no third-party content)",
        "file": out.name,
        "bytes": out.stat().st_size,
        "mesh_objects": len(export_objects),
        "triangles": sum(len(poly.vertices) - 2 for obj in export_objects for poly in obj.data.polygons),
        "preview": preview.name,
        "blend_source": blend.name,
        "style": ["obsidian graphite", "river teal", "warm brass", "cyan emissive", "Padma river inlay"],
    }
    out.with_name("lobby_stage_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("A2_CINEMATIC_LOBBY_STAGE_READY:" + json.dumps(report, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--blend", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    build_scene(args.out, args.preview, args.blend)


if __name__ == "__main__":
    main()
