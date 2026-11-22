#!/usr/bin/env python3
"""Build an original, animated A-Square lobby command hall in Blender.

The set is a game-ready stage, not a baked screenshot: the operator remains a
live Godot character and all lobby values/buttons remain real Godot UI.
Run with Blender 5.2.4:
  blender --background --factory-startup --python tools/blender/build_asquare_lobby_scene.py -- \
    --out build/asquare_lobby/asquare_command_hall.glb \
    --preview build/asquare_lobby/command_hall_preview.png \
    --blend build/asquare_lobby/asquare_command_hall.blend
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BLENDER_EXPECTED = (5, 2, 4)
FRAME_START = 1
FRAME_END = 120


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--blend", required=True)
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    collection = bpy.data.collections.get("A-Square Lobby Art")
    if collection is None:
        collection = bpy.data.collections.new("A-Square Lobby Art")
        bpy.context.scene.collection.children.link(collection)
    return collection


def link_art(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)
    obj["a_square_art_asset"] = True
    return obj


def create_material(name, color, metallic=0.0, roughness=0.5, emission=None,
                    noise=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission[0], 1.0)
        shader.inputs["Emission Strength"].default_value = emission[1]
    if noise > 0:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 5.0
        tex.inputs["Detail"].default_value = 3.0
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = noise
        bump.inputs["Distance"].default_value = 0.035
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return material


def parent_to_art(obj, root):
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()
    return obj


def box(name, location, dimensions, material, bevel=0.04, root=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("Soft manufactured edges", "BEVEL")
        modifier.width = min(bevel, min(dimensions) * 0.22)
        modifier.segments = 3
        modifier.profile = 0.5
        modifier2 = obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
        modifier2.keep_sharp = True
    if root:
        parent_to_art(obj, root)
    return obj


def cylinder(name, location, radius, depth, material, vertices=64, root=None):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    bevel = obj.modifiers.new("Machined rim", "BEVEL")
    bevel.width = min(0.035, depth * 0.18)
    bevel.segments = 3
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    if root:
        parent_to_art(obj, root)
    return obj


def torus(name, location, major, minor, material, root=None):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=96, minor_segments=12,
        location=location, major_radius=major, minor_radius=minor
    )
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    if root:
        parent_to_art(obj, root)
    return obj


def text_mesh(name, body, location, size, material, root, align="CENTER"):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    curve.extrude = 0.002
    curve.bevel_depth = 0.0008
    curve.align_x = align
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler[0] = math.radians(90.0)  # vertical panel; front faces the player at -Y
    if material:
        obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj.name = name
    obj.select_set(False)
    parent_to_art(obj, root)
    return obj


def key_rotation(obj, frames, root=None):
    for frame, angle in frames:
        obj.rotation_euler[2] = angle
        obj.keyframe_insert(data_path="rotation_euler", frame=frame, index=2)
    if obj.animation_data and obj.animation_data.action:
        action = obj.animation_data.action
        # Blender 5.2 may expose layered actions; default keyframes remain valid
        # and the glTF exporter bakes the animated transform range.
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for channelbag in strip.channelbags:
                        for curve in channelbag.fcurves:
                            for point in curve.keyframe_points:
                                point.interpolation = "LINEAR"
        except (AttributeError, TypeError):
            try:
                for curve in action.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"
            except AttributeError:
                pass
    return obj


def add_area_light(name, location, target, color, power, size, root):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    parent_to_art(obj, root)
    return obj


def add_spot(name, location, target, color, power, angle, root):
    data = bpy.data.lights.new(name, "SPOT")
    data.energy = power
    data.color = color
    data.spot_size = math.radians(angle)
    data.spot_blend = 0.55
    data.shadow_soft_size = 0.32
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    parent_to_art(obj, root)
    return obj


def make_screen(name, x, z, width, height, frame_mat, screen_mat, accent_mat, root):
    # All screens face the lobby camera (+Y); text is authored mesh, not raster UI.
    box(name + "_outer_frame", (x, 6.8, z), (width + 0.28, 0.18, height + 0.28),
        frame_mat, 0.09, root)
    box(name + "_glass", (x, 6.68, z), (width, 0.055, height),
        screen_mat, 0.035, root)
    for row in range(3):
        for col in range(4):
            w = width * (0.12 if col == 0 else 0.15)
            h = height * 0.055
            bx = x - width * 0.40 + col * width * 0.22
            bz = z - height * 0.28 + row * height * 0.23
            box(f"{name}_data_{row}_{col}", (bx, 6.63, bz), (w, 0.025, h),
                accent_mat if (row + col) % 3 == 0 else frame_mat, 0.012, root)
    # small illuminated status rail
    box(name + "_status_rail", (x, 6.59, z - height * 0.43),
        (width * 0.72, 0.025, 0.028), accent_mat, 0.01, root)


def build_scene(out_path: Path, preview_path: Path, blend_path: Path):
    version = bpy.app.version[:3]
    if version < BLENDER_EXPECTED:
        raise RuntimeError(f"Need Blender >= {BLENDER_EXPECTED}, got {version}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    collection = clear_scene()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples = 48
    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.fps = 24
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.camera = None

    # Original A-Square art direction: graphite command deck, warm brass,
    # restrained delta-teal signal lighting and a panoramic Bengal river-delta view.
    graphite = create_material("01 | Graphite ceramic", (0.035, 0.055, 0.067), 0.68, 0.28, noise=0.10)
    dark = create_material("02 | Deep shadow alloy", (0.012, 0.022, 0.032), 0.76, 0.24)
    steel = create_material("03 | Brushed gunmetal", (0.14, 0.19, 0.21), 0.82, 0.32, noise=0.045)
    concrete = create_material("04 | Satin basalt", (0.10, 0.14, 0.15), 0.16, 0.74, noise=0.20)
    gold = create_material("05 | Warm brass", (0.54, 0.34, 0.12), 0.78, 0.26)
    teal = create_material("06 | Delta signal", (0.025, 0.36, 0.39), 0.24, 0.24, ((0.04, 0.83, 0.91), 2.7))
    amber = create_material("07 | Mission amber", (0.62, 0.36, 0.08), 0.32, 0.30, ((1.0, 0.48, 0.12), 1.9))
    glass = create_material("08 | Smoked glass", (0.012, 0.07, 0.09), 0.38, 0.13, ((0.02, 0.18, 0.22), 0.20))
    white = create_material("09 | Warm ivory lettering", (0.78, 0.84, 0.80), 0.12, 0.3, ((0.38, 0.46, 0.43), 0.25))
    river = create_material("10 | Delta water", (0.018, 0.12, 0.15), 0.42, 0.18, ((0.015, 0.12, 0.17), 0.42))
    city = create_material("11 | Distant river-town silhouette", (0.12, 0.17, 0.18), 0.08, 0.88)
    screen = create_material("12 | Dark display glass", (0.006, 0.018, 0.028), 0.22, 0.12)

    root = bpy.data.objects.new("A_SQUARE_CINEMATIC_COMMAND_HALL", None)
    collection.objects.link(root)
    root.empty_display_type = "CIRCLE"
    root.empty_display_size = 0.6
    root["design_note"] = "Original Bangladesh-rooted tactical command hall; live operator and all UI are provided by Godot."

    # Stage floor and perimeter. The middle remains clear for the live operator.
    box("Command deck | floating plinth", (0, 0, -0.42), (23, 18, 0.75), dark, 0.22, root)
    box("Basalt floor | main field", (0, 0, 0.0), (21.8, 16.8, 0.16), concrete, 0.10, root)
    for x in (-9.9, -7.0, -4.0, 4.0, 7.0, 9.9):
        box(f"Floor inlay | lateral {x}", (x, 0.0, 0.09), (0.025, 15.9, 0.012), steel, 0.003, root)
    for y in (-7.6, -5.0, 5.0, 7.6):
        box(f"Floor inlay | depth {y}", (0.0, y, 0.092), (21.0, 0.025, 0.012), steel, 0.003, root)

    # The hero operator turntable, designed as layered machined metal instead of primitives alone.
    cylinder("Operator dais | lower armour", (0, 0, 0.00), 2.28, 0.14, dark, root=root)
    cylinder("Operator dais | satin crown", (0, 0, 0.075), 2.12, 0.055, graphite, root=root)
    torus("Dais | outer brass rim", (0, 0, 0.108), 2.12, 0.024, gold, root)
    torus("Dais | cyan inner light", (0, 0, 0.112), 1.88, 0.019, teal, root)
    torus("Dais | inner machined groove", (0, 0, 0.114), 1.66, 0.010, steel, root)
    for i in range(24):
        angle = 2 * math.pi * i / 24
        obj = box(f"Dais index | {i:02d}",
                  (1.98 * math.cos(angle), 1.98 * math.sin(angle), 0.118),
                  (0.13, 0.035, 0.018), amber if i % 6 == 0 else steel, 0.008, root)
        obj.rotation_euler[2] = angle

    rotating_ring = torus("Animated | orbiting command ring", (0, 0, 0.16), 2.48, 0.018, teal, root)
    rotating_ring.name = "ANIM | Orbit ring"
    key_rotation(rotating_ring, [(FRAME_START, 0.0), (FRAME_END, math.tau)])

    # Panoramic windows reveal a fictionalized but Bangladesh-rooted river-delta skyline.
    for side in (-1, 1):
        x = side * 7.9
        box(f"Window mullion | {side}", (x, 7.65, 4.0), (0.16, 0.20, 7.0), steel, 0.035, root)
        box(f"Window lower rail | {side}", (x, 7.65, 0.62), (3.25, 0.26, 0.18), gold, 0.025, root)
    box("Panoramic smoked window", (0, 7.72, 4.0), (15.7, 0.16, 6.9), glass, 0.07, root)
    box("River horizon | outside glass", (0, 9.0, 0.45), (34, 0.20, 4.4), river, 0.05, root)
    for i in range(21):
        x = -12.2 + i * 1.22
        width = 0.58 + (i % 4) * 0.16
        height = 1.2 + ((i * 7) % 6) * 0.52
        z = 0.58 + height * 0.5
        box(f"River town | silhouette {i:02d}", (x, 8.82, z),
            (width, 0.34, height), city, 0.025, root)
        # tiny warm windows form a believable distant nightfall skyline
        for j in range(max(1, int(height / 0.60))):
            box(f"River town | lit window {i:02d}-{j:02d}",
                (x - width * 0.18, 8.62, 0.78 + j * 0.58),
                (0.09, 0.025, 0.10), amber if (i + j) % 4 == 0 else teal,
                0.008, root)

    # Ceiling trusses, ribs and continuous edge lighting give the space depth.
    box("Ceiling | central canopy", (0, 0.4, 8.25), (20.8, 15.2, 0.34), dark, 0.12, root)
    for i in range(13):
        x = -9.0 + i * 1.5
        box(f"Ceiling | acoustic rib {i:02d}", (x, 0.0, 8.48), (0.055, 15.0, 0.24), steel, 0.022, root)
    for side in (-1, 1):
        box(f"Ceiling | delta light rail {side}", (side * 9.85, 0.0, 8.0),
            (0.08, 14.5, 0.08), teal, 0.025, root)
        box(f"Side wall | armour {side}", (side * 10.55, 0.0, 3.8),
            (0.34, 16.2, 7.2), graphite, 0.12, root)
        for j in range(7):
            y = -6.3 + j * 2.1
            box(f"Side wall | luminous fin {side}-{j}", (side * 10.30, y, 3.4),
                (0.045, 0.055, 4.9), teal if j % 3 == 0 else steel, 0.012, root)

    # Sculpted data walls and angled displays flank the operator.
    make_screen("Left theatre display", -6.9, 4.4, 4.6, 2.7, gold, screen, teal, root)
    make_screen("Right theatre display", 6.9, 4.4, 4.6, 2.7, gold, screen, amber, root)
    text_mesh("Main wordmark", "A²  /  A-SQUARE", (0, 6.56, 7.15), 0.68, white, root)
    text_mesh("World line", "BANGLADESH  •  RIVER DELTA OPERATIONS", (0, 6.55, 6.42),
              0.19, teal, root)
    text_mesh("Sector marker", "SECTOR 01  /  SHARIATPUR", (-8.5, 6.52, 2.5),
              0.16, white, root, "LEFT")
    text_mesh("Mission marker", "FIELD COMMAND", (8.5, 6.52, 2.5),
              0.16, white, root, "RIGHT")

    # Side console silhouettes are pushed away from the operator silhouette.
    for side in (-1, 1):
        x = side * 7.2
        console = box(f"Console | lower armour {side}", (x, -2.1, 1.05),
                      (4.4, 1.65, 1.45), dark, 0.16, root)
        console.rotation_euler[2] = side * math.radians(-7)
        box(f"Console | brushed surface {side}", (x, -2.1, 1.81),
            (4.1, 1.45, 0.10), steel, 0.06, root)
        for j in range(6):
            bx = x - 1.55 + j * 0.62
            box(f"Console | status key {side}-{j}", (bx, -2.1, 1.88),
                (0.32, 0.08, 0.025), teal if j % 3 else amber, 0.012, root)

    # Original Bangladesh red/green accent: a slim textile-like hanging strip,
    # not a copied game faction emblem or imported national graphic.
    box("Delta green vertical banner", (-9.68, 2.8, 5.9), (0.06, 0.72, 2.4), teal, 0.018, root)
    cylinder("Banner red seal", (-9.60, 2.78, 5.9), 0.22, 0.045, amber, 48, root)

    # Animated small beacons are layered around the stage perimeter.
    beacon_root = bpy.data.objects.new("ANIM | Perimeter beacons", None)
    collection.objects.link(beacon_root)
    parent_to_art(beacon_root, root)
    for i in range(8):
        a = 2 * math.pi * i / 8
        x, y = 8.9 * math.cos(a), 6.9 * math.sin(a)
        obj = cylinder(f"Beacon | {i:02d}", (x, y, 0.22), 0.08, 0.18,
                       teal if i % 2 == 0 else amber, 24, beacon_root)
        if i % 2:
            obj.scale = (0.78, 0.78, 1.4)

    # Distant ceiling spotlights create a live hero-character lighting pocket.
    add_area_light("Hero | cool softbox", (0, -3.6, 7.5), (0, 0, 1.2), (0.55, 0.80, 1.0), 1250, 5.2, root)
    add_area_light("Hero | warm shoulder", (4.5, 1.8, 6.6), (0, 0, 1.3), (1.0, 0.55, 0.26), 950, 3.8, root)
    add_area_light("Hero | teal rim", (-4.2, 2.8, 5.2), (0, 0, 1.4), (0.12, 0.78, 0.86), 1150, 3.4, root)
    add_spot("Deck | left sweep", (-7.4, -2.0, 7.2), (0, 0, 0), (0.13, 0.62, 0.80), 1250, 48, root)
    add_spot("Deck | right sweep", (7.4, -1.0, 7.4), (0, 0, 0), (1.0, 0.52, 0.22), 1150, 44, root)

    # A wide cinematic camera is for the review render only. Godot owns its own
    # camera, touch-safe framing and UI; the GLB camera is not forced at runtime.
    camera_data = bpy.data.cameras.new("Review Camera | command hall")
    camera = bpy.data.objects.new("Review Camera | command hall", camera_data)
    collection.objects.link(camera)
    camera.location = (15.7, -21.8, 11.2)
    camera.rotation_euler = (Vector((0.0, 0.2, 3.55)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 39
    scene.camera = camera

    world = bpy.data.worlds.new("A-Square | blue-hour world") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.009, 0.021, 0.034, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.32

    # Low-count original light accents animate independently so the lobby never
    # looks like a still render; the operator animation stays on the live rig.
    scene.frame_set(FRAME_START)
    for obj in (rotating_ring,):
        for frame, angle in ((1, 0.0), (31, math.pi * 0.5), (61, math.pi), (91, math.pi * 1.5), (120, math.tau - 0.001)):
            obj.rotation_euler[2] = angle
            obj.keyframe_insert(data_path="rotation_euler", frame=frame, index=2)
        try:
            for layer in obj.animation_data.action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for point in curve.keyframe_points:
                                point.interpolation = "LINEAR"
        except (AttributeError, TypeError):
            try:
                for curve in obj.animation_data.action.fcurves:
                    for point in curve.keyframe_points:
                        point.interpolation = "LINEAR"
            except AttributeError:
                pass

    scene.frame_set(1)
    scene.render.filepath = str(preview_path)
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.resolution_percentage = 100
    bpy.ops.render.render(write_still=True)

    # Export the authored set as GLB. The player/operator is deliberately not
    # included; Godot mounts its current rig at the center dais.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(
        filepath=str(out_path),
        export_format="GLB",
        export_animations=True,
        export_lights=True,
        export_cameras=False,
        export_apply=True,
        export_yup=True,
        export_materials="EXPORT",
    )
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"A2_LOBBY_STAGE_READY: {out_path}")
    print(f"A2_LOBBY_PREVIEW_READY: {preview_path}")
    print(f"A2_LOBBY_BLEND_READY: {blend_path}")


def main():
    if bpy.app.version[:3] != BLENDER_EXPECTED:
        print(f"NOTE: scene authored with Blender {bpy.app.version_string}; expected {BLENDER_EXPECTED} LTS")
    args = arguments()
    build_scene(Path(args.out), Path(args.preview), Path(args.blend))


if __name__ == "__main__":
    main()
