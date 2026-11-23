#!/usr/bin/env python3
"""Author an original Greenwake Chapter 01 river-port environment in Blender 5.2.4.

This is a fictional Bangladesh-rooted adventure environment, not a surveyed
location and not a reconstruction of any real historic site. All meshes,
materials, lettering and set dressing are authored in this script. No AI-made
images/models, ripped game assets or Google map imagery are used.

Run:
  blender --background --factory-startup --python tools/blender/build_greenwake_chapter_01.py -- \
    --out build/greenwake/chapter_01.glb \
    --preview build/greenwake/chapter_01_preview.png \
    --blend build/greenwake/chapter_01.blend \
    --manifest build/greenwake/asset_manifest.json
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
from mathutils import Vector

BLENDER_EXPECTED = (5, 2, 4)
FRAME_START = 1
FRAME_END = 120
OBJECTS = []


def cli_args():
    raw = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--preview", type=pathlib.Path, required=True)
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--textures", type=pathlib.Path, required=False, default=None,
                        help="Optional verified Poly Haven CC0 PBR bundle root")
    return parser.parse_args(raw)


def ensure_version():
    actual = tuple(bpy.app.version[:3])
    if actual != BLENDER_EXPECTED:
        raise RuntimeError(f"Expected Blender {BLENDER_EXPECTED}, got {actual}")


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)
    root = bpy.data.objects.new("GW_CH01_RUPJHORA_LOST_PORT", None)
    bpy.context.scene.collection.objects.link(root)
    root["a_square_asset"] = True
    root["fictional_composite"] = True
    OBJECTS.clear()
    return root


def register(obj, role, root):
    obj["greenwake_role"] = role
    obj["a_square_original_asset"] = True
    obj.parent = root
    OBJECTS.append(obj)
    return obj


def material(name, color, roughness=0.75, metallic=0.0,
             noise_scale=18.0, bump_strength=0.12, variation=0.18):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic

    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = noise_scale
    tex.inputs["Detail"].default_value = 4.0
    tex.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    low = tuple(max(0.0, min(1.0, c * (1.0 - variation))) for c in color) + (1.0,)
    high = tuple(max(0.0, min(1.0, c * (1.0 + variation))) for c in color) + (1.0,)
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = low
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = high
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.04
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    mat["source"] = "Original A-Square procedural Blender material"
    mat["photographic_scan"] = False
    return mat


PBR_ASSIGNMENTS = {
    "stone": "aged_concrete",
    "stone_trim": "aged_concrete",
    "brick": "exposed_clay_brick",
    "limewash": "weathered_plaster",
    "timber": "aged_wood",
    "wet_timber": "aged_wood",
    "crate": "aged_wood",
    "iron": "galvanized_shutter",
    "path": "wet_asphalt",
}


def ensure_mesh_uvs():
    """Add stable local-planar UVs to generated meshes that have no UV layer."""
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.data is None or len(obj.data.vertices) == 0:
            continue
        if len(obj.data.uv_layers) > 0:
            continue
        uv = obj.data.uv_layers.new(name="UVMap")
        xs = [v.co.x for v in obj.data.vertices]
        ys = [v.co.y for v in obj.data.vertices]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_span = max(x_max - x_min, 1e-5)
        y_span = max(y_max - y_min, 1e-5)
        for loop in obj.data.loops:
            co = obj.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = ((co.x - x_min) / x_span, (co.y - y_min) / y_span)


def apply_verified_pbr(material_block, textures_root: pathlib.Path, material_key: str, manifest: dict):
    """Replace the procedural base/normal/roughness with verified embedded CC0 scan maps."""
    material_record = manifest.get("materials", {}).get(material_key)
    if not isinstance(material_record, dict):
        raise RuntimeError(f"Verified Poly Haven material is missing: {material_key}")
    maps = material_record.get("maps", {})
    required = ("base_color", "normal", "roughness")
    for semantic in required:
        if semantic not in maps:
            raise RuntimeError(f"Verified Poly Haven {material_key} lacks {semantic} map")

    def packed_image(semantic: str, non_color: bool):
        record = maps[semantic]
        source_path = pathlib.Path(record["path"])
        if not source_path.is_absolute():
            source_path = pathlib.Path.cwd() / source_path
        if not source_path.is_file():
            candidate = textures_root / "polyhaven" / material_key / (semantic + source_path.suffix)
            if candidate.is_file():
                source_path = candidate
        if not source_path.is_file():
            raise RuntimeError(f"Poly Haven PBR file is missing: {source_path}")
        image = bpy.data.images.load(str(source_path), check_existing=True)
        if non_color:
            image.colorspace_settings.name = "Non-Color"
        image.pack()
        return image, record

    nodes = material_block.node_tree.nodes
    links = material_block.node_tree.links
    shader = nodes.get("Principled BSDF")
    if shader is None:
        raise RuntimeError(f"Material has no Principled BSDF: {material_block.name}")

    for link in list(links):
        if link.to_node == shader and link.to_socket.name in {"Base Color", "Roughness", "Normal"}:
            links.remove(link)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.label = "A-Square UV coordinates"
    base_image, base_record = packed_image("base_color", False)
    base = nodes.new("ShaderNodeTexImage")
    base.name = f"PolyHaven_{material_key}_BaseColor"
    base.label = f"CC0 {material_key} base colour"
    base.image = base_image
    links.new(texcoord.outputs["UV"], base.inputs["Vector"])
    links.new(base.outputs["Color"], shader.inputs["Base Color"])

    rough_image, rough_record = packed_image("roughness", True)
    rough = nodes.new("ShaderNodeTexImage")
    rough.name = f"PolyHaven_{material_key}_Roughness"
    rough.label = f"CC0 {material_key} roughness"
    rough.image = rough_image
    links.new(texcoord.outputs["UV"], rough.inputs["Vector"])
    rough_bw = nodes.new("ShaderNodeRGBToBW")
    links.new(rough.outputs["Color"], rough_bw.inputs["Color"])
    links.new(rough_bw.outputs["Val"], shader.inputs["Roughness"])

    normal_image, normal_record = packed_image("normal", True)
    normal = nodes.new("ShaderNodeTexImage")
    normal.name = f"PolyHaven_{material_key}_Normal"
    normal.label = f"CC0 {material_key} tangent-space normal"
    normal.image = normal_image
    links.new(texcoord.outputs["UV"], normal.inputs["Vector"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.8
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])

    material_block["source"] = "Poly Haven CC0-1.0 photographic PBR scan"
    material_block["pbr_provider"] = "Poly Haven"
    material_block["pbr_asset_id"] = material_record.get("asset_id", "")
    material_block["pbr_author"] = json.dumps(material_record.get("authors", {}), ensure_ascii=False)
    material_block["pbr_license"] = "CC0-1.0"
    material_block["photographic_scan"] = True
    return {
        "material": material_block.name,
        "polyhaven_material_key": material_key,
        "asset_id": material_record.get("asset_id"),
        "asset_name": material_record.get("asset_name"),
        "authors": material_record.get("authors", {}),
        "license": "CC0-1.0",
        "maps": {
            "base_color": {"path": base_record["path"], "md5": base_record["md5"], "bytes": base_record["bytes"]},
            "normal": {"path": normal_record["path"], "md5": normal_record["md5"], "bytes": normal_record["bytes"]},
            "roughness": {"path": rough_record["path"], "md5": rough_record["md5"], "bytes": rough_record["bytes"]},
        }
    }


def load_pbr_library(textures_root: pathlib.Path | None, mats: dict) -> dict:
    """Apply only the semantically matched licensed scan sets; other surfaces stay original."""
    if textures_root is None:
        return {"provider": "A-Square original procedural materials only", "license": "project-authored", "materials": {}}
    manifest_path = textures_root / "polyhaven_material_manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"Verified Poly Haven manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("provider") != "Poly Haven" or manifest.get("asset_license") != "CC0-1.0":
        raise RuntimeError("Poly Haven provenance manifest has unexpected provider or license")
    applied = {}
    ensure_mesh_uvs()
    for material_key, pbr_key in PBR_ASSIGNMENTS.items():
        applied[material_key] = apply_verified_pbr(mats[material_key], textures_root, pbr_key, manifest)
    return {
        "provider": "Poly Haven",
        "provider_credit": manifest.get("provider_credit", "Powered by Poly Haven"),
        "license": "CC0-1.0",
        "api_terms": manifest.get("api_terms"),
        "asset_license_url": manifest.get("asset_license_url"),
        "materials": applied,
    }


def box(name, location, dimensions, mat, root, bevel=0.08, role="architecture"):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("Hand-finished softened edges", "BEVEL")
        mod.width = min(bevel, min(dimensions) * 0.2)
        mod.segments = 3
        norm = obj.modifiers.new("Weighted architectural normals", "WEIGHTED_NORMAL")
        norm.keep_sharp = True
    return register(obj, role, root)


def cylinder(name, location, radius, depth, mat, root, vertices=32,
             rotation=(0.0, 0.0, 0.0), role="prop"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius,
        depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    if mat:
        obj.data.materials.append(mat)
    bevel = obj.modifiers.new("Edge glint", "BEVEL")
    bevel.width = min(0.025, depth * 0.15, radius * 0.15)
    bevel.segments = 2
    obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return register(obj, role, root)


def uv_sphere(name, location, scale, mat, root, segments=20, rings=12, role="foliage"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    if mat:
        obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return register(obj, role, root)


def curve(name, points, bevel_depth, mat, root, role="detail", cyclic=False, resolution=2):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = max(2, resolution)
    data.bevel_depth = bevel_depth
    data.bevel_resolution = 3
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return register(obj, role, root)


def mesh_object(name, vertices, faces, mat, root, role="environment", smooth=False):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    return register(obj, role, root)


def terrain_height(x, y):
    channel_centre = 10.5 * math.sin(y * 0.027) + 2.5 * math.sin(y * 0.083)
    half_width = 8.5 + 1.2 * math.sin(y * 0.049)
    distance = abs(x - channel_centre)
    flood_bank = max(0.0, distance - half_width)
    height = -0.8 + min(2.0, flood_bank * 0.22)
    west_rise = 2.1 * math.exp(-((x + 37.0) / 14.0) ** 2)
    eastern_ridge = 7.0 * math.exp(-((x - 43.0) / 17.0) ** 2) * (0.72 + 0.28 * math.sin(y * 0.07))
    low_ripples = 0.18 * math.sin(x * 0.23 + y * 0.16) * math.sin(y * 0.11)
    return height + west_rise + eastern_ridge + low_ripples


def build_terrain(root, ground_mat, water_mat):
    nx, ny = 112, 96
    xmin, xmax = -62.0, 62.0
    ymin, ymax = -52.0, 52.0
    vertices = []
    faces = []
    for j in range(ny + 1):
        y = ymin + (ymax - ymin) * j / ny
        for i in range(nx + 1):
            x = xmin + (xmax - xmin) * i / nx
            vertices.append((x, y, terrain_height(x, y)))
    stride = nx + 1
    for j in range(ny):
        for i in range(nx):
            a = j * stride + i
            faces.append((a, a + 1, a + stride + 1, a + stride))
    terrain = mesh_object("GW_Tidal_Floodplain_and_Ridge_Terrain", vertices, faces,
                          ground_mat, root, "terrain", True)
    for poly in terrain.data.polygons:
        poly.use_smooth = True

    water_vertices = []
    water_faces = []
    wx, wy = 72, 116
    for j in range(wy + 1):
        y = ymin + (ymax - ymin) * j / wy
        centre = 10.5 * math.sin(y * 0.027) + 2.5 * math.sin(y * 0.083)
        width = 8.1 + 0.6 * math.sin(y * 0.049)
        for i in range(wx + 1):
            u = i / wx
            x = centre + (u * 2.0 - 1.0) * width
            wave = 0.025 * math.sin(y * 0.6 + x * 0.4)
            water_vertices.append((x, y, -0.34 + wave))
    row = wx + 1
    for j in range(wy):
        for i in range(wx):
            a = j * row + i
            water_faces.append((a, a + 1, a + row + 1, a + row))
    river = mesh_object("GW_River_Rupjhora_Monsoon_Channel", water_vertices,
                        water_faces, water_mat, root, "water", True)
    return terrain, river


def build_mangrove_tree(root, x, y, scale, bark, leaf_a, leaf_b, index):
    ground = terrain_height(x, y)
    trunk_height = 5.2 * scale
    trunk_x = x
    trunk_y = y
    curve(f"GW_MangroveTrunk_{index:02d}",
          [(trunk_x, trunk_y, ground),
           (trunk_x + 0.18 * scale, trunk_y, ground + 1.5 * scale),
           (trunk_x - 0.12 * scale, trunk_y + 0.12 * scale, ground + 3.0 * scale),
           (trunk_x + 0.12 * scale, trunk_y, ground + trunk_height)],
          0.22 * scale, bark, root, "mangrove_trunk", False, 4)
    for side in range(5):
        a = math.tau * side / 5.0
        dx, dy = math.cos(a), math.sin(a)
        curve(f"GW_MangrovePropRoot_{index:02d}_{side}",
              [(x + dx * 0.05 * scale, y + dy * 0.05 * scale, ground + 0.4 * scale),
               (x + dx * 0.65 * scale, y + dy * 0.65 * scale, ground + 0.10 * scale),
               (x + dx * 1.25 * scale, y + dy * 1.25 * scale, ground + 0.02 * scale)],
              0.075 * scale, bark, root, "mangrove_root", False, 3)
    for branch in range(7):
        a = math.tau * branch / 7.0
        dx, dy = math.cos(a), math.sin(a)
        z = ground + (3.6 + (branch % 3) * 0.36) * scale
        bx, by = x + dx * 1.6 * scale, y + dy * 1.4 * scale
        curve(f"GW_MangroveBranch_{index:02d}_{branch}",
              [(x, y, ground + 2.7 * scale), (bx * 0.5 + x * 0.5, by * 0.5 + y * 0.5, z),
               (bx, by, z + 0.35 * scale)],
              0.075 * scale, bark, root, "branch", False, 3)
        for leaf in range(4):
            t = leaf / 3.0
            lx = x + dx * (1.0 + t * 1.8) * scale + math.sin(leaf * 2.3) * 0.32 * scale
            ly = y + dy * (0.9 + t * 1.6) * scale + math.cos(leaf * 1.7) * 0.28 * scale
            lz = z + 0.18 * scale + (leaf % 2) * 0.22 * scale
            uv_sphere(f"GW_MangroveCanopy_{index:02d}_{branch}_{leaf}",
                      (lx, ly, lz), (0.72 * scale, 0.42 * scale, 0.30 * scale),
                      leaf_a if (branch + leaf) % 2 == 0 else leaf_b,
                      root, 16, 10, "foliage")


def build_archway(root, x, y, z, stone, trim):
    # A hand-built stone portal with an open arch, not a single cuboid doorway.
    box("GW_ArchivePortal_LeftPier", (x - 1.35, y, z + 1.75), (0.48, 0.55, 3.5), stone, root, 0.06)
    box("GW_ArchivePortal_RightPier", (x + 1.35, y, z + 1.75), (0.48, 0.55, 3.5), stone, root, 0.06)
    points = []
    for i in range(17):
        theta = math.pi * i / 16.0
        points.append((x + 1.35 * math.cos(theta), y, z + 3.0 + 1.35 * math.sin(theta)))
    curve("GW_ArchivePortal_StoneArch", points, 0.22, trim, root, "portal_arch", False, 3)
    for side in [-1, 1]:
        for course in range(4):
            box(f"GW_ArchivePortal_Quoin_{side}_{course}",
                (x + side * 1.35, y - 0.33, z + 0.48 + course * 0.84),
                (0.56, 0.12, 0.7), trim if course % 2 == 0 else stone, root, 0.025, "masonry_detail")


def build_customs_house(root, mats):
    x, y = -21.0, 8.0
    z = terrain_height(x, y)
    # Raised foundations follow the local bank; floor levels are fictional set design.
    box("GW_CustomsHouse_StonePlinth", (x, y, z + 0.55), (18.0, 10.5, 1.1), mats["stone"], root, 0.16)
    box("GW_CustomsHouse_MainVolume", (x, y, z + 4.15), (16.7, 9.2, 6.2), mats["limewash"], root, 0.12)
    box("GW_CustomsHouse_RaisedUpperStorey", (x, y, z + 8.25), (15.1, 8.1, 2.1), mats["brick"], root, 0.08)
    # Timber floor beams and a deep shaded verandah.
    for side in [-1, 1]:
        box(f"GW_CustomsHouse_VerandahBeam_{side}", (x + side * 8.4, y - 5.05, z + 2.7),
            (0.26, 0.28, 4.3), mats["timber"], root, 0.04)
        box(f"GW_CustomsHouse_VerandahRail_{side}", (x + side * 8.4, y - 5.05, z + 3.8),
            (0.18, 0.24, 0.12), mats["iron"], root, 0.025)
    for floor in range(2):
        base_z = z + 2.4 + floor * 3.05
        width = 12.2 if floor == 0 else 10.5
        for side in [-1, 1]:
            for window in range(3):
                wx = x + side * (2.2 + window * 1.75)
                box(f"GW_CustomsHouse_WindowRecess_{floor}_{side}_{window}",
                    (wx, y - 4.66, base_z), (1.12, 0.10, 1.55 if floor == 0 else 1.1),
                    mats["shadow"], root, 0.03, "window_recess")
                for bar in range(4):
                    bx = wx - 0.42 + bar * 0.28
                    box(f"GW_CustomsHouse_WindowGrille_{floor}_{side}_{window}_{bar}",
                        (bx, y - 4.79, base_z), (0.035, 0.07, 1.42 if floor == 0 else 0.98),
                        mats["iron"], root, 0.01, "iron_grille")
        # Bengali sign and timber fascia on the main facade.
    box("GW_CustomsHouse_BengaliSignBoard", (x, y - 4.92, z + 1.72),
        (6.2, 0.20, 0.72), mats["timber"], root, 0.035, "signage")
    # Roof parapet, stair head, tank and drain stacks.
    box("GW_CustomsHouse_RoofDeck", (x, y, z + 9.45), (15.6, 8.7, 0.28), mats["stone"], root, 0.06)
    for side in [-1, 1]:
        box(f"GW_CustomsHouse_Parapet_{side}", (x + side * 7.55, y, z + 9.95),
            (0.25, 8.65, 0.82), mats["brick"], root, 0.03)
    box("GW_CustomsHouse_StairHead", (x + 4.5, y + 2.1, z + 10.2),
        (3.0, 3.6, 1.2), mats["limewash"], root, 0.08)
    cylinder("GW_CustomsHouse_RooftopWaterTank", (x - 4.6, y + 1.9, z + 10.55),
             1.15, 1.35, mats["iron"], root, 32, role="roof_prop")
    for side in [-1, 1]:
        curve(f"GW_CustomsHouse_RainDownpipe_{side}",
              [(x + side * 7.4, y - 4.6, z + 8.6), (x + side * 7.4, y - 4.6, z + 4.0),
               (x + side * 7.4, y - 4.6, z + 0.6)],
              0.065, mats["iron"], root, "rain_pipe")
    # Hand-made timber shutters with inset slats.
    for door_i in range(2):
        dx = x - 3.1 + door_i * 6.2
        box(f"GW_CustomsHouse_ShutterFrame_{door_i}", (dx, y - 4.88, z + 1.2),
            (2.1, 0.22, 2.25), mats["iron"], root, 0.04, "shutter")
        for slat in range(9):
            box(f"GW_CustomsHouse_ShutterSlat_{door_i}_{slat}",
                (dx, y - 5.02, z + 0.28 + slat * 0.22),
                (1.85, 0.06, 0.09), mats["rust"], root, 0.012, "shutter_slat")
    return (x, y, z)


def build_port_service_path(root, mats):
    """A narrow repaired service strip on the fictional west bank, not a district road."""
    points = [(-30.5, 13.5), (-28.5, 8.0), (-26.0, 1.5), (-23.0, -4.5),
              (-20.0, -9.5), (-17.5, -15.5), (-15.5, -21.0)]
    half_width = 1.35
    left = []
    right = []
    for index, (x, y) in enumerate(points):
        if index == 0:
            dx, dy = points[1][0] - x, points[1][1] - y
        elif index == len(points) - 1:
            dx, dy = x - points[index - 1][0], y - points[index - 1][1]
        else:
            dx = points[index + 1][0] - points[index - 1][0]
            dy = points[index + 1][1] - points[index - 1][1]
        length = max(math.hypot(dx, dy), 1e-5)
        nx, ny = -dy / length, dx / length
        lx, ly = x + nx * half_width, y + ny * half_width
        rx, ry = x - nx * half_width, y - ny * half_width
        left.append((lx, ly, terrain_height(lx, ly) + 0.10))
        right.append((rx, ry, terrain_height(rx, ry) + 0.10))
    vertices = left + right
    count = len(points)
    faces = []
    for i in range(count - 1):
        faces.append((i, i + 1, count + i + 1, count + i))
    mesh_object("GW_WestBank_Repaired_Tar_Service_Path", vertices, faces,
                mats["path"], root, "service_path", False)
    curve("GW_ServicePath_Stone_Edge_Left",
          [(x, y, z + 0.08) for x, y, z in left], 0.075, mats["stone_trim"], root, "path_kerb")
    curve("GW_ServicePath_Stone_Edge_Right",
          [(x, y, z + 0.08) for x, y, z in right], 0.075, mats["stone_trim"], root, "path_kerb")
    # Broken patch seams and tar repairs make the modern maintenance strip read as used.
    for index in (1, 3, 5):
        x, y = points[index]
        z = terrain_height(x, y) + 0.16
        curve(f"GW_ServicePath_PatchSeam_{index}",
              [(x - 0.52, y - 0.12, z), (x - 0.22, y + 0.05, z + 0.006),
               (x + 0.36, y + 0.10, z)],
              0.018, mats["shadow"], root, "asphalt_patch")
    return points


def build_jetty(root, mats):
    x0, y0 = 11.0, -3.0
    base_z = -0.06
    # Weathered uneven planks with a few missing boards make a broken edge readable.
    for i in range(22):
        x = x0 - 5.8 + i * 0.55
        for row in range(5):
            if (i in (4, 13, 18) and row in (2, 3)) or (i == 8 and row == 0):
                continue
            y = y0 - 2.25 + row * 1.02
            plank = box(f"GW_Jetty_DeckPlank_{i:02d}_{row}",
                (x, y, base_z + 0.28 + 0.025 * math.sin(i * 0.7 + row)),
                (0.51, 0.94, 0.14), mats["timber"], root, 0.025, "dock_plank")
            plank.rotation_euler[2] = 0.015 * math.sin(i + row)
    for i in range(9):
        x = x0 - 5.2 + i * 1.3
        for row in [-1, 1]:
            y = y0 + row * 2.35
            cylinder(f"GW_Jetty_Pile_{i}_{row}", (x, y, -0.38), 0.22, 2.4,
                     mats["wet_timber"], root, 16, role="dock_piling")
            cylinder(f"GW_Jetty_PileCap_{i}_{row}", (x, y, 0.82), 0.27, 0.18,
                     mats["timber"], root, 16, role="dock_cap")
    for side in [-1, 1]:
        curve(f"GW_Jetty_Rail_{side}",
              [(x0 - 5.7, y0 + side * 2.25, 1.25),
               (x0 - 2.0, y0 + side * 2.25, 1.10),
               (x0 + 1.6, y0 + side * 2.25, 1.16),
               (x0 + 5.7, y0 + side * 2.25, 0.88)],
              0.065, mats["wet_timber"], root, "dock_rail")
    return (x0, y0, base_z)


def build_boat(root, mats, x, y, z, name, scale=1.0, yaw=0.0):
    stations = [
        (-3.8, 0.0, 0.25), (-2.9, 1.0, 0.0), (-1.0, 1.25, -0.1),
        (1.5, 1.2, -0.08), (3.2, 0.7, 0.12), (3.8, 0.0, 0.40)
    ]
    vertices = []
    for sx, half_w, centre_z in stations:
        for k in range(5):
            t = k / 4.0
            yy = (t * 2.0 - 1.0) * half_w
            zz = centre_z - 0.52 * math.sin(t * math.pi)
            vertices.append((sx * scale, yy * scale, zz * scale))
    faces = []
    for i in range(len(stations) - 1):
        for j in range(4):
            a = i * 5 + j
            faces.append((a, a + 1, a + 6, a + 5))
    hull = mesh_object(name + "_CarvedWoodHull", vertices, faces, mats["wet_timber"], root, "boat_hull", True)
    hull.location = (x, y, z)
    hull.rotation_euler[2] = yaw
    for rib in range(8):
        sx = (-2.9 + rib * 0.82) * scale
        curve(name + f"_Rib_{rib}",
              [(x + sx, y - 0.85 * scale, z + 0.20 * scale),
               (x + sx, y, z - 0.18 * scale),
               (x + sx, y + 0.85 * scale, z + 0.20 * scale)],
              0.055 * scale, mats["timber"], root, "boat_rib")
    box(name + "_CargoCrate", (x - 0.5 * scale, y, z + 0.65 * scale),
        (1.15 * scale, 0.85 * scale, 0.78 * scale), mats["crate"], root, 0.06, "boat_cargo")
    return hull


def build_rope_bridge(root, mats):
    # A narrow crossing above a tidal side channel; planks are individually modelled.
    for i in range(25):
        x = -1.0 + i * 0.54
        y = 21.0 + 1.4 * math.sin(i / 24.0 * math.pi)
        z = terrain_height(x, y) + 2.3
        plank = box(f"GW_RopeBridge_Deck_{i:02d}", (x, y, z),
                    (0.48, 1.15, 0.15), mats["wet_timber"], root, 0.035, "bridge_deck")
        plank.rotation_euler[1] = 0.045 * math.sin(i * 0.8)
    for side in [-1, 1]:
        points = []
        for i in range(25):
            x = -1.0 + i * 0.54
            y = 21.0 + 1.4 * math.sin(i / 24.0 * math.pi) + side * 0.64
            z = terrain_height(x, y - side * 0.4) + 3.2 - 0.85 * math.sin(i / 24.0 * math.pi)
            points.append((x, y, z))
        curve(f"GW_RopeBridge_Rope_{side}", points, 0.075, mats["rope"], root, "bridge_rope", False, 3)
        for i in range(0, 25, 4):
            p = points[i]
            curve(f"GW_RopeBridge_Tie_{side}_{i}",
                  [(p[0], p[1], p[2] - 0.1), (p[0], p[1] - side * 0.12, p[2] - 0.75)],
                  0.035, mats["rope"], root, "bridge_rope_tie")
    return True


def build_sluice(root, mats):
    x, y = 30.5, -13.5
    z = terrain_height(x, y)
    box("GW_Sluice_MasonryBase", (x, y, z + 0.75), (13.5, 3.5, 1.5), mats["stone"], root, 0.14)
    for side in [-1, 1]:
        box(f"GW_Sluice_MasonryPier_{side}", (x + side * 5.0, y, z + 2.9),
            (1.2, 4.0, 4.8), mats["brick"], root, 0.12)
        for course in range(5):
            box(f"GW_Sluice_PierCourse_{side}_{course}",
                (x + side * 5.0, y - 2.05, z + 1.1 + course * 0.72),
                (1.25, 0.14, 0.08), mats["stone_trim"], root, 0.015, "masonry_detail")
    # A heavy timber gate and iron guides.
    box("GW_Sluice_GateLeaf", (x, y - 0.1, z + 2.3), (8.2, 0.35, 3.0), mats["wet_timber"], root, 0.08)
    for i in range(11):
        box(f"GW_Sluice_GateBoard_{i:02d}", (x - 3.8 + i * 0.76, y - 0.32, z + 2.3),
            (0.10, 0.12, 2.8), mats["timber"], root, 0.018, "gate_detail")
    cylinder("GW_Sluice_WinchAxle", (x, y - 0.9, z + 4.6), 0.16, 7.0,
             mats["iron"], root, 24, (0.0, math.pi / 2.0, 0.0), "mechanism")
    for side in [-1, 1]:
        cylinder(f"GW_Sluice_WinchWheel_{side}", (x + side * 3.65, y - 0.9, z + 4.6),
                 1.25, 0.16, mats["rust"], root, 48, (0.0, math.pi / 2.0, 0.0), "mechanism")
        for spoke in range(10):
            a = math.tau * spoke / 10.0
            px = x + side * 3.75
            py = y - 0.9 + math.cos(a) * 0.78
            pz = z + 4.6 + math.sin(a) * 0.78
            box(f"GW_Sluice_WinchSpoke_{side}_{spoke}", (px, py, pz),
                (0.13, 0.13, 1.52), mats["iron"], root, 0.025, "mechanism_spoke").rotation_euler[0] = -a
    # Four hanging chains lead down to the gate eyes.
    for i in range(4):
        cx = x - 2.7 + i * 1.8
        points = [(cx, y - 0.95, z + 4.2 - j * 0.32) for j in range(12)]
        curve(f"GW_Sluice_Chain_{i}", points, 0.035, mats["iron"], root, "chain", False, 2)
    return (x, y, z)


def build_archive_vault(root, mats):
    x, y = 40.0, 7.0
    z = terrain_height(x, y)
    # The archive is embedded in a ridge cut, presented as a fictional trade-era vault.
    box("GW_Archive_RidgeCut_Lintel", (x, y + 2.0, z + 4.2), (12.5, 5.0, 1.2), mats["stone"], root, 0.2)
    box("GW_Archive_RidgeCut_LeftWing", (x - 5.8, y + 2.0, z + 2.1), (1.0, 5.0, 4.2), mats["earth"], root, 0.18)
    box("GW_Archive_RidgeCut_RightWing", (x + 5.8, y + 2.0, z + 2.1), (1.0, 5.0, 4.2), mats["earth"], root, 0.18)
    build_archway(root, x, y - 0.7, z + 0.1, mats["stone"], mats["stone_trim"])
    for step in range(8):
        box(f"GW_Archive_DescentStep_{step}", (x, y - 1.1 - step * 0.55, z + 0.2 - step * 0.15),
            (3.6, 0.82, 0.24), mats["stone_trim"], root, 0.045, "stair")
    # Interior chamber visible through the portal; it is an authored fictional game space.
    box("GW_Archive_ChamberFloor", (x, y - 8.6, z - 1.45), (9.0, 8.0, 0.34), mats["stone"], root, 0.08)
    for side in [-1, 1]:
        box(f"GW_Archive_ChamberWall_{side}", (x + side * 4.55, y - 8.6, z + 0.45),
            (0.35, 8.1, 3.7), mats["stone"], root, 0.1)
        for slot in range(4):
            box(f"GW_Archive_Niche_{side}_{slot}",
                (x + side * 4.30, y - 5.8 - slot * 1.75, z + 1.0),
                (0.10, 0.72, 1.25), mats["shadow"], root, 0.025, "archive_niche")
    box("GW_Archive_LedgerPedestal", (x, y - 7.1, z - 0.25),
        (1.6, 1.2, 1.15), mats["stone_trim"], root, 0.12, "puzzle_prop")
    box("GW_Archive_LedgerCase", (x, y - 7.1, z + 0.42),
        (1.15, 0.72, 0.16), mats["iron"], root, 0.035, "puzzle_prop")
    return (x, y, z)


def build_vegetation(root, mats):
    index = 0
    for x, y, scale in [
        (-35, -28, 1.0), (-28, -17, 0.82), (-39, 2, 1.08), (-31, 26, 0.9),
        (22, -33, 1.0), (28, -24, 0.75), (24, 18, 1.05), (31, 30, 0.86),
        (6, 42, 0.9), (-14, 37, 0.84), (-48, -7, 0.74)
    ]:
        build_mangrove_tree(root, x, y, scale, mats["bark"], mats["foliage_a"],
                            mats["foliage_b"], index)
        index += 1
    # Reed beds and broadleaf plants are grouped along the floodplain.
    for cluster in range(12):
        cx = -46 + (cluster % 6) * 15.0
        cy = -43 + (cluster // 6) * 76.0
        z = terrain_height(cx, cy)
        for blade in range(13):
            a = math.tau * blade / 13.0
            r = 0.32 + 0.16 * (blade % 3)
            bx, by = cx + math.cos(a) * r, cy + math.sin(a) * r
            top = (bx + math.cos(a) * 0.3, by + math.sin(a) * 0.3, z + 1.2 + (blade % 4) * 0.16)
            curve(f"GW_ReedCluster_{cluster}_{blade}",
                  [(bx, by, z), (bx + math.cos(a) * 0.15, by + math.sin(a) * 0.15, z + 0.6), top],
                  0.035, mats["reed"], root, "wetland_reed", False, 2)
    # A few broadleaf plants near the path provide a close-camera scale cue.
    for p in range(20):
        x = -28.0 + (p % 5) * 2.0
        y = 29.0 + (p // 5) * 2.4
        z = terrain_height(x, y)
        for leaf in range(5):
            a = math.tau * leaf / 5.0
            end = (x + math.cos(a) * 1.1, y + math.sin(a) * 0.8, z + 0.8 + 0.2 * (leaf % 2))
            curve(f"GW_BroadleafPetiole_{p}_{leaf}",
                  [(x, y, z + 0.10), end],
                  0.035, mats["foliage_a"], root, "broadleaf", False, 2)


def add_hero_wayfinding(root, mats):
    # Bangla/English labels are original A-Square interface art, not real historic signage.
    labels = [
        ("ARRIVAL / GHAT", (-4.0, -6.0, 2.0)),
        ("CUSTOMS HOUSE", (-21.0, 1.0, 11.0)),
        ("TIDAL GATE", (30.5, -16.0, terrain_height(30.5, -13.5) + 5.2)),
        ("LOST ARCHIVE", (40.0, 3.8, terrain_height(40.0, 7.0) + 5.2))
    ]
    for index, (text, pos) in enumerate(labels):
        # These are subtle in-world clue markers for art review, not navigation labels.
        cylinder(f"GW_WayfindingMarker_{index}", (pos[0], pos[1], pos[2] - 0.2),
                 0.16, 0.05, mats["lantern"], root, 16, role="wayfinding")
    return labels


def animate_beacon(root, mats):
    pole = cylinder("GW_RiverSignal_BeaconPole", (-7.0, 34.0, 8.8), 0.12, 5.8,
                    mats["iron"], root, 24, role="signal_beacon")
    lens = uv_sphere("GW_RiverSignal_BeaconLens", (-7.0, 34.0, 11.8),
                     (0.3, 0.3, 0.3), mats["lantern"], root, 20, 12, "signal_light")
    lens.keyframe_insert(data_path="location", frame=1)
    lens.location.z += 0.08
    lens.keyframe_insert(data_path="location", frame=60)
    lens.location.z -= 0.08
    lens.keyframe_insert(data_path="location", frame=120)
    # Turn one original signal vane slowly over the 120-frame loop.
    vane = box("GW_RiverSignal_Vane", (-7.0, 34.0, 12.3), (1.7, 0.08, 0.22),
               mats["rust"], root, 0.04, "animated_signal")
    for frame, angle in [(1, 0.0), (60, math.radians(15)), (120, 0.0)]:
        vane.rotation_euler.z = angle
        vane.keyframe_insert(data_path="rotation_euler", frame=frame)
    return pole, lens, vane


def build_camera_and_lights(scene, root, mats):
    camera_data = bpy.data.cameras.new("GW_Chapter01_HeroCamera")
    camera = bpy.data.objects.new("GW_Chapter01_HeroCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (-74.0, -88.0, 62.0)
    target = Vector((2.0, 0.0, 2.8))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 45.0
    scene.camera = camera
    camera.parent = root

    for name, loc, color, energy, size in [
        ("GW_Warm_Dawn_Key", (-35, -25, 52), (1.0, 0.72, 0.48), 4200, 18),
        ("GW_Cool_River_Fill", (34, -2, 28), (0.43, 0.66, 0.82), 2600, 24),
        ("GW_Archive_Rim", (46, 28, 22), (0.75, 0.82, 1.0), 3000, 14)
    ]:
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.shape = "DISK"
        ld.size = size
        light = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(light)
        light.location = loc
        light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
        light.parent = root

    world = bpy.data.worlds.new("GW_Monsoon_Dawn_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.25, 0.32, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.world = world


def build_scene(textures_root: pathlib.Path | None = None):
    scene = bpy.context.scene
    root = reset_scene()
    mats = {
        "ground": material("GW_Mud_Silt_Floodplain", (0.19, 0.21, 0.16), 0.94, 0.0, 12.0, 0.25, 0.28),
        "water": material("GW_Monsoon_River_Water", (0.045, 0.12, 0.14), 0.18, 0.18, 6.0, 0.035, 0.12),
        "stone": material("GW_Aged_Riverstone", (0.32, 0.31, 0.27), 0.89, 0.0, 22.0, 0.22, 0.24),
        "stone_trim": material("GW_Cut_Stone_Details", (0.46, 0.42, 0.33), 0.72, 0.0, 26.0, 0.14, 0.15),
        "brick": material("GW_Burnished_River_Brick", (0.35, 0.15, 0.10), 0.83, 0.0, 36.0, 0.2, 0.26),
        "limewash": material("GW_Faded_Limewash", (0.63, 0.56, 0.42), 0.84, 0.0, 28.0, 0.14, 0.20),
        "timber": material("GW_Aged_Sal_Timber", (0.23, 0.13, 0.07), 0.72, 0.0, 18.0, 0.22, 0.22),
        "wet_timber": material("GW_Wet_Jetty_Wood", (0.12, 0.10, 0.065), 0.34, 0.0, 22.0, 0.16, 0.23),
        "iron": material("GW_Blackened_Iron", (0.07, 0.09, 0.095), 0.31, 0.72, 34.0, 0.09, 0.16),
        "rust": material("GW_Rust_Oxide", (0.27, 0.09, 0.035), 0.62, 0.38, 32.0, 0.16, 0.26),
        "shadow": material("GW_Deep_Recess_Shadow", (0.018, 0.025, 0.024), 0.96, 0.0, 4.0, 0.0, 0.0),
        "rope": material("GW_Coiled_Hemp_Rope", (0.38, 0.28, 0.15), 0.91, 0.0, 55.0, 0.1, 0.18),
        "bark": material("GW_Mangrove_Bark", (0.16, 0.105, 0.06), 0.9, 0.0, 35.0, 0.2, 0.3),
        "foliage_a": material("GW_Monsoon_Foliage_A", (0.055, 0.18, 0.085), 0.8, 0.0, 8.0, 0.08, 0.24),
        "foliage_b": material("GW_Monsoon_Foliage_B", (0.12, 0.24, 0.09), 0.76, 0.0, 10.0, 0.06, 0.2),
        "reed": material("GW_Wetland_Reed", (0.42, 0.36, 0.14), 0.82, 0.0, 28.0, 0.07, 0.22),
        "crate": material("GW_Trade_Crate_Wood", (0.28, 0.19, 0.10), 0.79, 0.0, 26.0, 0.13, 0.2),
        "earth": material("GW_Exposed_Ridge_Earth", (0.19, 0.16, 0.11), 0.96, 0.0, 22.0, 0.2, 0.24),
        "lantern": material("GW_Warm_Signal_Lantern", (0.88, 0.48, 0.12), 0.22, 0.05, 5.0, 0.0, 0.1),
        "path": material("GW_Wet_Bitumen_Service_Path", (0.11, 0.13, 0.13), 0.88, 0.02, 22.0, 0.18, 0.14),
    }
    pbr_provenance = load_pbr_library(textures_root, mats)
    terrain, river = build_terrain(root, mats["ground"], mats["water"])
    service_path = build_port_service_path(root, mats)
    house = build_customs_house(root, mats)
    jetty = build_jetty(root, mats)
    build_boat(root, mats, 8.0, -5.0, 0.65, "GW_Delta_Ferry", 0.9, math.radians(7))
    build_boat(root, mats, -7.5, -23.0, 0.25, "GW_Fishing_Shallop", 0.58, math.radians(-12))
    build_rope_bridge(root, mats)
    sluice = build_sluice(root, mats)
    archive = build_archive_vault(root, mats)
    build_vegetation(root, mats)
    labels = add_hero_wayfinding(root, mats)
    animate_beacon(root, mats)
    build_camera_and_lights(scene, root, mats)

    scene.frame_start = FRAME_START
    scene.frame_end = FRAME_END
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 75
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.view_settings.view_transform = "AgX"
    scene.render.film_transparent = False
    scene.camera.data.dof.use_dof = True
    scene.camera.data.dof.focus_distance = 125.0
    scene.camera.data.dof.aperture_fstop = 8.0
    scene.world.color = (0.08, 0.1, 0.12)
    scene.render.filepath = "//greenwake_chapter_01_preview.png"
    scene.frame_set(1)
    return root, mats, {"terrain": terrain, "river": river, "house": house, "jetty": jetty,
                        "sluice": sluice, "archive": archive, "labels": labels,
                        "service_path": service_path, "pbr_provenance": pbr_provenance}


def export_glb(path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "CURVE", "EMPTY", "LIGHT", "CAMERA"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = bpy.context.scene.camera
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        export_apply=True,
        export_animations=True,
        export_skins=False,
        export_cameras=False,
        export_lights=False,
        export_image_format="AUTO",
        export_yup=True,
    )


def main():
    args = cli_args()
    ensure_version()
    root, mats, landmarks = build_scene(args.textures)
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    args.blend.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    # Export the complete scene and preserve the editable source before rendering
    # the review still. A headless render failure must not erase the authored GLB.
    ensure_mesh_uvs()
    bpy.ops.file.pack_all()
    export_glb(args.out)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend))
    bpy.context.scene.render.filepath = str(args.preview)
    print("GREENWAKE_RENDER_START: Cycles CPU, 16 samples, denoising enabled")
    bpy.ops.render.render(write_still=True)

    mesh_objects = [o for o in OBJECTS if o.type == "MESH"]
    triangles = sum(max(0, len(poly.vertices) - 2) for obj in mesh_objects for poly in obj.data.polygons)
    manifest = {
        "schema_version": 1,
        "asset_id": "greenwake_chapter_01_rupjhora_lost_port",
        "asset_name": "Rupjhora Lost Port",
        "family": "GREENWAKE",
        "chapter": 1,
        "setting": "fictional Bangladesh river-delta trade-port and monsoon wetland composite",
        "status": "UNREVIEWED_DEVELOPMENT_STUDY",
        "fictional_composite": True,
        "surveyed_location": False,
        "geospatial_coordinates": None,
        "historic_claim": False,
        "source_policy": "original Blender-authored geometry; Poly Haven CC0-1.0 PBR scans with manifest and hash verification; original procedural water/terrain/vegetation; no AI generated media, no copied game assets, no Google imagery",
        "pbr_provenance": landmarks.get("pbr_provenance", {}),
        "engine_target": "Godot 4.4.1",
        "authoring_tool": "Blender 5.2.4 LTS",
        "license": "A-Square project-authored original asset; no third-party mesh or texture content",
        "triangles": triangles,
        "mesh_objects": len(mesh_objects),
        "materials": sorted(m.name for m in mats.values()),
        "animations": ["GW_RiverSignal_Beacon"],
        "route": [
            "Arrival Ghat", "Trade Quarter", "Old Customs House", "Mangrove Walk",
            "Broken Jetty", "Tidal Sluice", "Ridge Archive", "Chapter Exit"
        ],
        "landmarks": {
            "customs_house_foot": list(landmarks["house"]),
            "jetty_origin": list(landmarks["jetty"]),
            "sluice_origin": list(landmarks["sluice"]),
            "archive_entrance": list(landmarks["archive"])
        },
        "gameplay_state": "NOT_YET_INTEGRATED_OR_PLAYABLE",
        "unknowns": [
            "fictional composite; not a real surveyed place",
            "no historical claims",
            "no Android visual or performance sign-off",
            "collision, navigation, triggers, puzzles and save/checkpoint logic are separate integration work"
        ],
        "files": {
            "glb": args.out.name,
            "preview": args.preview.name,
            "blend": args.blend.name
        }
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GREENWAKE_CH01_READY:" + json.dumps({
        "glb": str(args.out), "triangles": triangles, "mesh_objects": len(mesh_objects),
        "materials": len(mats), "manifest": str(args.manifest)
    }))


if __name__ == "__main__":
    main()
