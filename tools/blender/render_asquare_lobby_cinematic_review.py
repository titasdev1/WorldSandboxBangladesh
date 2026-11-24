#!/usr/bin/env python3
"""Render an operator-led, multi-angle A-Square lobby review in Blender.

The exported game lobby remains a live Godot scene. This review project loads the
editable Blender command hall and the current rigged Ara operator GLB, creates
four full-angle stills plus a short authored camera orbit, then encodes the
orbit to MP4. The operator is preview-only and is never merged into the lobby
environment GLB or shipped as a baked scene image.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys

import bpy
from mathutils import Vector

EXPECTED_BLENDER = (5, 2, 4)
REVIEW_FPS = 24
REVIEW_FRAMES = 120
OPERATOR_PREVIEW_HEIGHT_M = 1.8
DAIS_TOP_Z = 0.14


def parse_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument("--operator-glb", type=pathlib.Path, required=True)
    parser.add_argument("--review-dir", type=pathlib.Path, required=True)
    return parser.parse_args(raw)


def require_inputs(args):
    if tuple(bpy.app.version[:3]) != EXPECTED_BLENDER:
        raise RuntimeError(f"Expected Blender {EXPECTED_BLENDER}, got {bpy.app.version_string}")
    if not args.blend.is_file():
        raise FileNotFoundError(f"Lobby Blender source is missing: {args.blend}")
    if not args.operator_glb.is_file():
        raise FileNotFoundError(f"High-detail Ara operator GLB is missing: {args.operator_glb}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to encode the review camera orbit")


def load_scene(path: pathlib.Path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    if bpy.context.scene is None:
        raise RuntimeError("Could not restore the editable A-Square command hall scene")
    return bpy.context.scene


def create_collection(name: str):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def add_operator_preview(operator_glb: pathlib.Path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(operator_glb))
    imported = [obj for obj in bpy.data.objects if obj not in before]
    if not imported:
        raise RuntimeError("Ara operator GLB imported no Blender objects")
    armatures = [obj for obj in imported if obj.type == "ARMATURE"]
    meshes = [obj for obj in imported if obj.type == "MESH"]
    if not armatures or not meshes:
        raise RuntimeError(f"Operator preview requires both armature and mesh; got {len(armatures)} armatures / {len(meshes)} meshes")

    world_corners = []
    for obj in meshes:
        world_corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not world_corners:
        raise RuntimeError("Imported operator has no measurable mesh bounds")
    min_z = min(v.z for v in world_corners)
    max_z = max(v.z for v in world_corners)
    centre_x = (min(v.x for v in world_corners) + max(v.x for v in world_corners)) * 0.5
    centre_y = (min(v.y for v in world_corners) + max(v.y for v in world_corners)) * 0.5
    source_height = max_z - min_z
    if source_height < 0.5:
        raise RuntimeError(f"Operator GLB bounds are invalid: height={source_height:.3f}")

    root = bpy.data.objects.new("PREVIEW ONLY | Ara operator root", None)
    root.empty_display_type = "PLAIN_AXES"
    root["preview_only"] = True
    root["source_glb"] = operator_glb.name
    root["source_license"] = "See Ara3D ASSET-LICENSES.txt; character base CC0 and motion source terms apply"
    collection = create_collection("PREVIEW ONLY | Live operator review")
    collection.objects.link(root)

    for obj in imported:
        for old_collection in list(obj.users_collection):
            old_collection.objects.unlink(obj)
        collection.objects.link(obj)
        world_matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = world_matrix

    scale = OPERATOR_PREVIEW_HEIGHT_M / source_height
    root.scale = (scale, scale, scale)
    root.location = (-centre_x * scale, -centre_y * scale, DAIS_TOP_Z - min_z * scale)
    root.rotation_euler.z = 0.0

    # Prefer a rifle low-ready or standing idle action so the lobby still reads
    # as a live operator showcase rather than a static mannequin pose.
    preferred = ("rifle idle", "idle_breathe", "idle", "standing idle")
    actions = list(bpy.data.actions)
    chosen = None
    for token in preferred:
        chosen = next((a for a in actions if token in a.name.lower()), None)
        if chosen:
            break
    if chosen is not None:
        for armature in armatures:
            armature.animation_data_create()
            armature.animation_data.action = chosen
    else:
        chosen = None

    for obj in imported:
        obj["preview_only"] = True
    report = {
        "source_glb": operator_glb.name,
        "preview_height_m": OPERATOR_PREVIEW_HEIGHT_M,
        "source_height_blender_units": round(source_height, 5),
        "mesh_objects": len(meshes),
        "armature_count": len(armatures),
        "animation_action": chosen.name if chosen else None,
        "available_action_count": len(actions),
        "preview_only": True
    }
    print("A2_LOBBY_OPERATOR_PREVIEW_READY:" + json.dumps(report))
    return root, report


def point_camera(camera, location, target, lens=40.0):
    camera.location = Vector(location)
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = lens
    camera.data.dof.use_dof = False


def add_still_camera(name, location, target, lens, collection):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    point_camera(obj, location, target, lens)
    return obj


def smooth_action(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if action is None:
        return
    try:
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for curve in channelbag.fcurves:
                        for point in curve.keyframe_points:
                            point.interpolation = "BEZIER"
                            point.handle_left_type = "AUTO_CLAMPED"
                            point.handle_right_type = "AUTO_CLAMPED"
    except (AttributeError, TypeError):
        try:
            for curve in action.fcurves:
                for point in curve.keyframe_points:
                    point.interpolation = "BEZIER"
                    point.handle_left_type = "AUTO_CLAMPED"
                    point.handle_right_type = "AUTO_CLAMPED"
        except AttributeError:
            pass


def add_orbit_camera(collection):
    scene = bpy.context.scene
    data = bpy.data.cameras.new("A-Square cinematic orbit camera")
    camera = bpy.data.objects.new("A-Square cinematic orbit camera", data)
    collection.objects.link(camera)
    camera.data.lens = 40
    target = (0.0, 0.6, 3.1)
    keys = [
        (1, (0.0, -23.0, 6.1)),
        (31, (-12.0, -19.0, 6.0)),
        (61, (-18.0, -1.5, 6.6)),
        (91, (11.0, 17.0, 8.2)),
        (120, (0.0, -14.5, 4.9)),
    ]
    for frame, location in keys:
        point_camera(camera, location, target, 40.0 if frame < 120 else 48.0)
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
        camera.data.keyframe_insert(data_path="lens", frame=frame)
    smooth_action(camera)
    return camera


def render_stills(scene, collection, review_dir: pathlib.Path):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"

    shots = [
        ("01_hero_front", (0.0, -23.0, 6.1), (0.0, 0.6, 3.1), 36),
        ("02_left_three_quarter", (-13.5, -17.5, 6.3), (0.0, 0.4, 3.0), 42),
        ("03_right_three_quarter", (13.5, -17.5, 6.3), (0.0, 0.4, 3.0), 42),
        ("04_rear_high_overlook", (3.0, 18.0, 10.5), (0.0, 0.5, 2.8), 45),
        ("05_operator_closeup", (-4.6, -11.8, 4.2), (0.0, 0.0, 3.1), 58),
    ]
    images = []
    for shot_name, location, target, lens in shots:
        camera = add_still_camera(f"Review {shot_name}", location, target, lens, collection)
        scene.camera = camera
        scene.frame_set(48)
        output = review_dir / f"lobby_{shot_name}.png"
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        if not output.is_file() or output.stat().st_size < 50000:
            raise RuntimeError(f"Lobby review still was not rendered correctly: {output}")
        images.append({"file": output.name, "bytes": output.stat().st_size, "camera": camera.name})
    return images


def render_orbit(scene, camera, review_dir: pathlib.Path):
    frame_dir = review_dir / "orbit_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    scene.camera = camera
    scene.frame_start = 1
    scene.frame_end = REVIEW_FRAMES
    scene.render.fps = REVIEW_FPS
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 10
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(frame_dir / "frame_")
    for frame in range(1, REVIEW_FRAMES + 1):
        scene.frame_set(frame)
        scene.render.filepath = str(frame_dir / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)

    output = review_dir / "A-Square-Lobby-Operator-Orbit.mp4"
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(REVIEW_FPS), "-start_number", "1",
        "-i", str(frame_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output)
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    if not output.is_file() or output.stat().st_size < 100000:
        raise RuntimeError("Cinematic orbit MP4 is missing or implausibly small")
    shutil.rmtree(frame_dir)
    return {"file": output.name, "bytes": output.stat().st_size,
            "fps": REVIEW_FPS, "frames": REVIEW_FRAMES,
            "duration_seconds": REVIEW_FRAMES / REVIEW_FPS,
            "resolution": "1280x720"}


def main():
    args = parse_args()
    require_inputs(args)
    args.review_dir.mkdir(parents=True, exist_ok=True)
    scene = load_scene(args.blend)
    review_collection = create_collection("REVIEW CAMERAS | Not exported to game")
    operator_root, operator_report = add_operator_preview(args.operator_glb)
    stills = render_stills(scene, review_collection, args.review_dir)
    orbit_camera = add_orbit_camera(review_collection)
    orbit = render_orbit(scene, orbit_camera, args.review_dir)

    review_blend = args.review_dir / "A-Square-Lobby-Cinematic-Review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(review_blend))
    manifest = {
        "schema_version": 1,
        "asset_id": "a_square_lobby_operator_cinematic_review",
        "status": "RENDERED_REVIEW_MEDIA_NOT_ART_APPROVED",
        "engine_target": "Godot 4.4.1",
        "authoring_tool": "Blender 5.2.4 LTS",
        "operator_preview": operator_report,
        "operator_is_preview_only": True,
        "still_views": stills,
        "orbit_clip": orbit,
        "editable_blend": review_blend.name,
        "live_ui_and_navigation": "Godot runtime; not baked into the render or video",
        "game_export": "The production lobby GLB remains a separate live environment asset; preview-only operator and review cameras are not included."
    }
    manifest_path = args.review_dir / "cinematic_review_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("A2_LOBBY_CINEMATIC_REVIEW_READY:" + json.dumps({
        "still_count": len(stills), "orbit_clip": orbit,
        "operator_action": operator_report["animation_action"],
        "manifest": str(manifest_path), "review_blend": str(review_blend)
    }))


if __name__ == "__main__":
    main()
