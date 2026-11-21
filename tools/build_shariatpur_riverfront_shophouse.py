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
Provenance: No third-party game assets; no Google Earth/Maps 3D or satellite tiles,
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
    parser.add_argument("--interior-preview", type=pathlib.Path, required=True)
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
        base_path = folder_path / "base_color.jpg"
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

    # Properly shaped Bengali is baked with RAQM into wide sign-face textures.
    # Do not rely on Blender's unshaped 3D text glyph sequence for conjuncts.
    for key, folder_name in (("shop_sign_face", "shop_sign"), ("interior_sign_face", "interior_sign")):
        folder_path = texture_root / folder_name
        base_path = folder_path / "base_color.jpg"
        normal_path = folder_path / "normal.png"
        rough_path = folder_path / "roughness.png"
        if not all(path.is_file() for path in (base_path, normal_path, rough_path)):
            raise FileNotFoundError(f"Missing shaped Bengali sign artwork: {folder_path}")
        mat = bpy.data.materials.new(f"A2_Baked_Bengali_{key}")
        mat.diffuse_color = (0.05, 0.24, 0.19, 1.0)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes; links = mat.node_tree.links
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial"); output.location = (560, 40)
        principled = nodes.new("ShaderNodeBsdfPrincipled"); principled.location = (300, 40)
        principled.inputs["Roughness"].default_value = 0.48
        base_img = bpy.data.images.load(str(base_path), check_existing=True)
        normal_img = bpy.data.images.load(str(normal_path), check_existing=True)
        rough_img = bpy.data.images.load(str(rough_path), check_existing=True)
        for image in (base_img, normal_img, rough_img): image.pack()
        normal_img.colorspace_settings.name = "Non-Color"
        rough_img.colorspace_settings.name = "Non-Color"
        base_node = nodes.new("ShaderNodeTexImage"); base_node.image = base_img; base_node.location = (-520, 210)
        rough_node = nodes.new("ShaderNodeTexImage"); rough_node.image = rough_img; rough_node.location = (-520, -30)
        normal_node = nodes.new("ShaderNodeTexImage"); normal_node.image = normal_img; normal_node.location = (-520, -250)
        normal_map = nodes.new("ShaderNodeNormalMap"); normal_map.location = (-90, -230)
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


def textured_quad(role: str, loc: tuple[float,float,float], width: float, height: float,
                 mat: bpy.types.Material) -> bpy.types.Object:
    """Front-facing, true-aspect UV quad for baked typography and sign graphics."""
    vertices = [
        (-width*0.5, 0.0, -height*0.5),
        ( width*0.5, 0.0, -height*0.5),
        ( width*0.5, 0.0,  height*0.5),
        (-width*0.5, 0.0,  height*0.5),
    ]
    mesh = bpy.data.meshes.new(role + "_Mesh")
    mesh.from_pydata(vertices, [], [(0,1,2,3)])
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    uv_by_vertex = {0:(0.0,0.0),1:(1.0,0.0),2:(1.0,1.0),3:(0.0,1.0)}
    for polygon in mesh.polygons:
        for loop_index in polygon.loop_indices:
            vertex_index = mesh.loops[loop_index].vertex_index
            uv_layer.data[loop_index].uv = uv_by_vertex[vertex_index]
    obj = bpy.data.objects.new(role, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    return _register(obj, role, mat)


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
    coords = list(points); spline.points.add(max(0,len(coords)-1))
    for point, xyz in zip(spline.points, coords): point.co = (*xyz,1.0)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(role, data); bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj = _register(obj, role, mat)
    _cube_uv(obj)
    return obj


def text_mesh(role: str, body: str, loc: tuple[float,float,float], size: float,
              mat: bpy.types.Material, font_path: str = "") -> bpy.types.Object:
    data = bpy.data.curves.new(role + "_font", "FONT")
    data.body = body; data.size = size; data.align_x = "CENTER"; data.align_y = "CENTER"
    data.extrude = 0.008; data.bevel_depth = 0.002; data.bevel_resolution = 2
    if font_path and pathlib.Path(font_path).is_file():
        data.font = bpy.data.fonts.load(font_path)
    obj = bpy.data.objects.new(role, data); bpy.context.collection.objects.link(obj)
    obj.location = loc; obj.rotation_euler.x = math.radians(90)
    bpy.ops.object.select_all(action="DESELECT"); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj = bpy.context.object
    obj = _register(obj, role, mat)
    if mat.name != "A2_Warm_Ivory_Sign_Lettering":
        _cube_uv(obj)
    return obj


def find_bengali_font() -> str:
    try:
        found = subprocess.run(["fc-match", "Noto Sans Bengali", "-f", "%{file}"],
                               capture_output=True, text=True, check=False).stdout.strip()
        if found and pathlib.Path(found).is_file(): return found
    except Exception:
        pass
    for candidate in ("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
                      "/usr/share/fonts/truetype/noto/NotoSansBengaliUI-Regular.ttf"):
        if pathlib.Path(candidate).is_file(): return candidate
    return ""


def make_window(x: float, z: float, width: float, height: float, mats: dict[str,bpy.types.Material], balcony: bool=False) -> None:
    face_y = -4.34
    # Deep reveal, glazed sash, perimeter frame and a fine metal security grille.
    box("Window_Recess_Shadow", (x,face_y+0.07,z), (width+0.24,0.13,height+0.26), mats["brick"], 0.018)
    box("Window_Glass_LowE", (x,face_y-0.018,z), (width,0.045,height), mats["glass"], 0.008)
    frame = 0.085
    for side in (-1,1):
        box("Window_Teak_Frame", (x+side*(width/2+frame/2),face_y-0.075,z), (frame,0.12,height+0.20), mats["wood"], 0.012)
    for zz in (-1,1):
        box("Window_Teak_SillHead", (x,face_y-0.075,z+zz*(height/2+frame/2)), (width+0.20,0.12,frame), mats["wood"], 0.012)
    if balcony:
        for ix in range(7):
            xx = x - width*0.42 + ix*width*0.14
            curve("Balcony_Door_Glazing_Mullion", ((xx,face_y-0.11,z-height*0.46),(xx,face_y-0.11,z+height*0.46)), 0.018, mats["steel"])
    else:
        for ix in range(5):
            xx=x-width*0.34+ix*width*0.17
            curve("Window_Security_Grill_Vertical", ((xx,face_y-0.13,z-height*0.47),(xx,face_y-0.13,z+height*0.47)), 0.017, mats["steel"])
        for iz in (-0.24,0.24):
            curve("Window_Security_Grill_Crossbar", ((x-width*0.47,face_y-0.13,z+iz*height),(x+width*0.47,face_y-0.13,z+iz*height)), 0.015, mats["steel"])
        # Shallow projecting shade and drip edge.
        box("Window_Cement_Chajja", (x,face_y-0.25,z+height*0.58), (width+0.5,0.52,0.12), mats["plaster"], 0.035)


def _add_side_window(x_wall: float, center_y: float, center_z: float,
                    width: float, height: float, side: float,
                    mats: dict[str,bpy.types.Material]) -> None:
    """Build a recessed side-elevation window with a projecting rain chajja."""
    face_x = x_wall + side * 0.15
    frame = 0.075
    box("Side_Window_Recess", (face_x,center_y,center_z),
        (0.16,width+0.24,height+0.24),mats["brick"],0.018)
    box("Side_Window_Glazing", (face_x+side*0.035,center_y,center_z),
        (0.055,width,height),mats["glass"],0.008)
    for sign in (-1,1):
        box("Side_Window_Teak_Jamb", (face_x+side*0.075,center_y+sign*(width*0.5+frame*0.5),center_z),
            (0.11,frame,height+0.18),mats["wood"],0.012)
        box("Side_Window_Teak_HeadSill", (face_x+side*0.075,center_y,center_z+sign*(height*0.5+frame*0.5)),
            (0.11,width+0.18,frame),mats["wood"],0.012)
    for i in range(5):
        yy=center_y-width*0.40+i*width*0.20
        curve("Side_Window_Security_Grille",(
            (face_x+side*0.14,yy,center_z-height*0.46),
            (face_x+side*0.14,yy,center_z+height*0.46)),0.016,mats["steel"])
    for zoff in (-0.25,0.25):
        curve("Side_Window_Grille_Crossbar",(
            (face_x+side*0.14,center_y-width*0.46,center_z+zoff*height),
            (face_x+side*0.14,center_y+width*0.46,center_z+zoff*height)),0.014,mats["steel"])
    box("Side_Window_Concrete_Chajja",
        (face_x+side*0.25,center_y,center_z+height*0.60),
        (0.54,width+0.42,0.11),mats["concrete"],0.028)
    # Small rust line below the sill breaks the otherwise uninterrupted wall plane.
    curve("Side_Window_Rain_Streak",(
        (face_x+side*0.085,center_y+width*0.31,center_z-height*0.58),
        (face_x+side*0.086,center_y+width*0.29,center_z-height*0.94)),0.009,mats["brick"])


def _add_shop_interior(mats: dict[str,bpy.types.Material], font_path: str) -> None:
    """Authored grocery-shop interior fitted behind the real front entrance."""
    # The room shares the exterior building's coordinate space and ground floor.
    box("Shop_Interior_Ceramic_Floor",(0.0,0.02,0.105),(10.45,7.78,0.16),mats["concrete"],0.018)
    for x in [(-4.92+i*0.62) for i in range(17)]:
        curve("Interior_Floor_Grout_X",((x,-3.78,0.192),(x,3.78,0.192)),0.006,mats["brick"])
    for y in [(-3.65+i*0.62) for i in range(13)]:
        curve("Interior_Floor_Grout_Y",((-5.12,y,0.193),(5.12,y,0.193)),0.006,mats["brick"])
    box("Shop_Entrance_Coirmat",(4.10,-3.72,0.205),(1.05,0.52,0.035),mats["wood"],0.018)

    # Long left-wall grocery rack: powder-coated uprights and teak shelves.
    for x in (-4.78,-4.22):
        for y in (-2.82,-0.48,1.86):
            box("Shop_Left_Rack_Upright",(x,y,1.45),(0.075,0.075,2.60),mats["steel"],0.012)
    for z in (0.58,1.38,2.18,2.88):
        box("Shop_Left_Rack_Shelf",(-4.50,-0.48,z),(0.62,4.85,0.10),mats["wood"],0.018)
    for row_z in (0.83,1.62,2.42):
        for i in range(8):
            y=-2.58+i*0.60
            if i%3==0:
                cylinder("Shop_Left_Rack_Tin",( -4.48,y,row_z+0.17),0.105,0.34,mats["steel"],16)
            elif i%3==1:
                box("Shop_Left_Rack_Packet",(-4.48,y,row_z+0.17),(0.23,0.22,0.34),mats["sign"],0.018)
            else:
                cylinder("Shop_Left_Rack_Jar",(-4.48,y,row_z+0.14),0.085,0.27,mats["glass"],16)

    # Rear-wall counter and stocked shelves, leaving a clear path from the entrance.
    for x in (-2.85,-0.10,2.65):
        box("Shop_Rear_Rack_Pillar",(x,3.54,1.72),(0.10,0.13,3.18),mats["steel"],0.012)
    for z in (0.63,1.42,2.22,3.02):
        box("Shop_Rear_Rack_Shelf",(0.0,3.48,z),(5.75,0.42,0.10),mats["wood"],0.018)
    for row_z in (0.86,1.65,2.45):
        for i in range(12):
            x=-2.55+i*0.46
            if i%4==0:
                box("Shop_Rear_Stock_Carton",(x,3.28,row_z+0.16),(0.31,0.30,0.30),mats["brick"],0.018)
            elif i%4==1:
                cylinder("Shop_Rear_Stock_Tin",(x,3.25,row_z+0.17),0.095,0.33,mats["steel"],16)
            elif i%4==2:
                cylinder("Shop_Rear_Stock_Bottle",(x,3.27,row_z+0.14),0.075,0.27,mats["glass"],14)
            else:
                box("Shop_Rear_Stock_Packet",(x,3.28,row_z+0.17),(0.22,0.22,0.35),mats["sign"],0.012)

    # Timber-and-concrete service counter, glass display case and weighing scale.
    box("Shop_Counter_KickPlinth",(-1.52,-1.10,0.22),(2.85,0.92,0.22),mats["brick"],0.025)
    box("Shop_Counter_Timber_Front",(-1.52,-1.10,0.66),(2.85,0.86,0.72),mats["wood"],0.028)
    for x in (-2.40,-1.52,-0.64):
        box("Shop_Counter_Front_Panel",(x,-1.545,0.68),(0.72,0.035,0.58),mats["plaster"],0.012)
    box("Shop_Counter_Stone_Top",(-1.52,-1.10,1.07),(3.02,1.02,0.12),mats["concrete"],0.025)
    box("Shop_Glass_Display_Base",(-1.52,-1.00,1.36),(1.86,0.68,0.42),mats["wood"],0.025)
    box("Shop_Glass_Display_Front",(-1.52,-1.34,1.67),(1.84,0.035,0.32),mats["glass"],0.008)
    box("Shop_Glass_Display_Side_L",(-2.44,-1.00,1.67),(0.035,0.66,0.32),mats["glass"],0.008)
    box("Shop_Glass_Display_Side_R",(-0.60,-1.00,1.67),(0.035,0.66,0.32),mats["glass"],0.008)
    for x in (-2.12,-1.72,-1.32,-0.92):
        box("Shop_Display_Goods",(x,-1.05,1.55),(0.26,0.32,0.11),mats["sign"],0.012)
    box("Shop_Weighing_Scale_Base",(-0.30,-1.02,1.18),(0.34,0.30,0.10),mats["steel"],0.018)
    box("Shop_Weighing_Scale_Pan",(-0.30,-1.02,1.25),(0.26,0.22,0.04),mats["concrete"],0.012)
    box("Shop_Price_Receipt_Book",(-2.58,-1.06,1.16),(0.26,0.32,0.05),mats["sign"],0.012)

    # Rice/dal sacks, beverage cooler and stacked returnable crates.
    for x,y in ((-3.75,2.48),(-3.12,2.52),(-3.47,1.92)):
        sack=cylinder("Shop_Rice_Sack",(x,y,0.56),0.27,0.92,mats["wood"],20)
        # Cylindrical woven-sack approximation; keep original scale baked by cylinder dimensions.
    box("Shop_Beverage_Cooler_Housing",(3.60,1.55,1.34),(1.10,0.88,2.58),mats["steel"],0.035)
    box("Shop_Beverage_Cooler_Glass",(3.60,1.08,1.43),(0.84,0.035,2.05),mats["glass"],0.012)
    for z in (0.72,1.18,1.64,2.10):
        box("Shop_Cooler_Shelf",(3.60,1.04,z),(0.78,0.035,0.045),mats["steel"],0.006)
    for x in (2.85,3.55):
        box("Shop_Returnable_Crate",(x,2.78,0.42),(0.58,0.52,0.68),mats["steel"],0.025)
        for row in range(4):
            curve("Shop_Crate_Vent_Slot",((x-0.24,2.49,0.24+row*0.14),(x+0.24,2.49,0.24+row*0.14)),0.012,mats["wood"])

    # Locally familiar polypropylene chairs, low stool and ceiling fan.
    for x,y in ((-2.95,-2.55),(2.55,-2.40)):
        box("Shop_Plastic_Chair_Seat",(x,y,0.48),(0.62,0.58,0.12),mats["sign"],0.035)
        box("Shop_Plastic_Chair_Back",(x,y+0.22,0.91),(0.62,0.12,0.78),mats["sign"],0.035)
        for dx in (-0.24,0.24):
            for dy in (-0.20,0.20):
                box("Shop_Plastic_Chair_Leg",(x+dx,y+dy,0.24),(0.06,0.06,0.42),mats["steel"],0.012)
    cylinder("Shop_Ceiling_Fan_Rod",(1.78,0.92,3.32),0.025,0.56,mats["steel"],12)
    cylinder("Shop_Ceiling_Fan_Hub",(1.78,0.92,3.03),0.10,0.12,mats["steel"],20)
    for i in range(3):
        angle=2.0*math.pi*i/3.0
        curve("Shop_Ceiling_Fan_Blade",(
            (1.78,0.92,3.05),
            (1.78+math.cos(angle)*0.64,0.92+math.sin(angle)*0.64,3.05)),
            0.055,mats["steel"])
    for x in (-2.7,1.3,4.0):
        box("Shop_Ceiling_LED_Housing",(x,0.0,3.58),(1.05,0.13,0.08),mats["glass"],0.018)
        box("Shop_Ceiling_LED_Diffuser",(x,-0.01,3.535),(0.90,0.10,0.018),mats["concrete"],0.006)

    # Shop interior uses the same shaped Bengali lettering pipeline as the exterior.
    box("Shop_Interior_Bangla_Signboard",(0.0,3.82,3.28),(3.35,0.10,0.84),mats["sign"],0.022)
    textured_quad("Shop_Interior_Baked_Bengali_Face",(0.0,3.763,3.28),3.25,0.74,mats["interior_sign_face"])
    # A short low counter return and a small wall shelf add depth at the entrance.
    box("Shop_Interior_Entry_Side_Counter",(2.25,-2.80,0.72),(1.08,0.55,1.32),mats["wood"],0.035)
    box("Shop_Interior_Entry_Side_Top",(2.25,-2.80,1.42),(1.18,0.62,0.12),mats["concrete"],0.022)


def build_shopfront(mats: dict[str,bpy.types.Material]) -> None:
    # Local coordinates: the public frontage faces -Y; the building sits on z=0.
    # Side and rear shell are intentionally open at the front to preserve the
    # option of later fitting a verified interior shell behind the same entrance.
    box("Building_Rear_Wall", (0,4.12,4.55), (11.2,0.32,9.1), mats["plaster"], 0.05)
    for x in (-5.47,5.47):
        box("Building_Side_Wall", (x,0,4.55), (0.26,8.25,9.1), mats["plaster"], 0.045)
        # Brick plinth wraps onto both side walls to create a damp-season base.
        box("Brick_Damp_Course", (x,0,0.72), (0.30,8.32,1.40), mats["brick"], 0.018)

    # Ground-floor shops: two metal shutters, a timber/glass entry and strong piers.
    for x in (-3.65,0.05,3.70):
        box("Ground_Floor_Pier", (x,-4.10,1.92), (0.38,0.42,3.84), mats["plaster"], 0.045)
        box("Pier_Brick_Base", (x,-4.115,0.38), (0.42,0.45,0.76), mats["brick"], 0.018)
    for x in (-1.82,1.86):
        shutter_width=3.05; shutter_height=2.78; shutter_z=1.76
        box("Roller_Shutter_Recess", (x,-4.22,shutter_z), (shutter_width+0.18,0.15,shutter_height+0.20), mats["brick"], 0.02)
        box("Roller_Shutter_Leaf_Back", (x,-4.31,shutter_z), (shutter_width,0.08,shutter_height), mats["steel"], 0.015)
        for row in range(20):
            z=0.48+row*0.135
            box("Roller_Shutter_Rib", (x,-4.365,z), (shutter_width-0.04,0.025,0.048), mats["steel"], 0.012)
        for side in (-1,1):
            box("Shutter_Guide_Rail", (x+side*(shutter_width/2+0.06),-4.38,1.75), (0.10,0.09,2.86), mats["wood"], 0.012)
        cylinder("Shutter_Lock", (x+shutter_width*0.31,-4.395,0.40), 0.038,0.04,mats["steel"],12,"Y")

    # A real timber-framed door and transom at the right end of the frontage.
    door_x=4.72
    box("Shop_Entrance_Deep_Reveal", (door_x,-4.17,1.68), (1.10,0.18,3.22), mats["brick"], 0.02)
    box("Shop_Entrance_Teak_Leaf", (door_x,-4.29,1.57), (0.86,0.08,2.92), mats["wood"], 0.035)
    box("Shop_Entrance_Glass_Panel", (door_x,-4.345,2.18), (0.56,0.025,1.25), mats["glass"], 0.008)
    for side in (-1,1):
        box("Door_Stile", (door_x+side*0.31,-4.37,2.18), (0.045,0.025,1.35), mats["steel"], 0.006)
    cylinder("Door_Handle", (door_x-0.28,-4.405,1.48), 0.035,0.10,mats["steel"],16,"Y")
    box("Door_Threshold", (door_x,-4.40,0.08), (1.20,0.45,0.16), mats["concrete"] if "concrete" in mats else mats["plaster"], 0.025)

    # Upper floor slab, an irregularly layered cornice and the floor band.
    box("First_Floor_Slab", (0,-0.05,3.93), (11.0,8.55,0.28), mats["concrete"], 0.05)
    box("Upper_Floor_Fascia", (0,-4.12,4.12), (11.25,0.38,0.32), mats["brick"], 0.035)
    # Build real wall returns around each window opening rather than placing a dark
    # rectangle over a solid wall. The window reveals therefore have actual depth.
    def window_bay(cx: float, opening_w: float, opening_h: float) -> None:
        bay_w, bay_h, bay_cz = 2.40, 3.40, 5.96
        side_w = max(0.18, (bay_w-opening_w)*0.5)
        side_x = opening_w*0.5 + side_w*0.5
        for side in (-1,1):
            box("Upper_Facade_Window_Return", (cx+side*side_x,-4.10,bay_cz),
                (side_w,0.34,bay_h), mats["plaster"],0.035)
        lower_h = (bay_h-opening_h)*0.5
        for side in (-1,1):
            box("Upper_Facade_Window_Spandrel", (cx,-4.10,bay_cz+side*(opening_h*0.5+lower_h*0.5)),
                (opening_w,0.34,lower_h), mats["plaster"],0.035)
    window_bay(-4.08,1.38,1.76)
    window_bay(0.0,1.70,2.20)
    window_bay(4.08,1.38,1.76)
    for cx in (-2.04,2.04):
        box("Upper_Facade_Interbay_Pier", (cx,-4.10,5.96), (1.68,0.34,3.40), mats["plaster"],0.04)
    # Window openings are recessed between facade bays. The centre is a balcony door.
    make_window(-4.08,5.95,1.38,1.76,mats,False)
    make_window(0.0,5.95,1.70,2.20,mats,True)
    make_window(4.08,5.95,1.38,1.76,mats,False)

    # Small balcony, with rounded handrail, anchored slab and vertical balusters.
    balcony_w=3.00
    box("Balcony_Slab", (0,-4.72,4.63), (balcony_w,0.92,0.18), mats["concrete"], 0.06)
    for side in (-1,1):
        curve("Balcony_End_Rail", ((side*balcony_w/2,-5.12,4.72),(side*balcony_w/2,-5.12,5.60)), 0.038, mats["steel"])
    for i in range(13):
        x=-balcony_w*0.47+i*balcony_w*0.0783
        curve("Balcony_Baluster", ((x,-5.12,4.72),(x,-5.12,5.56)), 0.021, mats["steel"])
    curve("Balcony_Top_Rail", ((-balcony_w/2,-5.12,5.58),(balcony_w/2,-5.12,5.58)), 0.045, mats["steel"])
    box("Balcony_Planter_Ledge", (0,-5.22,4.86), (1.28,0.26,0.17), mats["brick"], 0.04)

    # Shop awning: weathered sheet roof, stiffeners, valance and brackets.
    box("Corrugated_Awning_Canopy", (0.0,-4.92,3.35), (7.8,1.28,0.12), mats["steel"], 0.035)
    for x in [(-3.65+i*0.36) for i in range(21)]:
        curve("Awning_Corrugation", ((x,-5.54,3.40),(x,-4.30,3.40)), 0.012,mats["steel"])
    box("Awning_Front_Valance", (0,-5.55,3.18), (7.85,0.09,0.36), mats["wood"], 0.025)
    for x in (-3.45,3.45):
        curve("Awning_Bracket", ((x,-4.23,3.32),(x,-5.38,3.18),(x,-5.38,2.90)), 0.035,mats["steel"])

    # Wide sign face is a single RAQM-shaped Bengali texture with true aspect UVs.
    box("Shop_Signboard_Back", (0,-4.48,3.88), (4.55,0.20,1.08), mats["sign"], 0.045)
    textured_quad("Shop_Signboard_Baked_Bengali_Face", (0,-4.588,3.88), 4.42, 0.98, mats["shop_sign_face"])
    for side in (-1,1):
        box("Signboard_Brass_Fixing", (side*2.20,-4.60,3.88), (0.055,0.035,0.96), mats["steel"], 0.012)

    # Upper veranda soffit, parapet and roof stair head.
    box("Roof_Deck", (0,0,7.78), (11.15,8.4,0.28), mats["concrete"], 0.05)
    box("Roof_Parapet_Front", (0,-4.05,8.20), (11.25,0.28,0.84), mats["plaster"],0.035)
    box("Roof_Parapet_Left", (-5.48,0,8.20), (0.28,8.4,0.84), mats["plaster"],0.035)
    box("Roof_Parapet_Right", (5.48,0,8.20), (0.28,8.4,0.84), mats["plaster"],0.035)
    box("Roof_Parapet_Coping", (0,-4.05,8.66), (11.45,0.40,0.12), mats["brick"],0.025)
    box("Stair_Head_Room", (3.35,1.85,8.65), (3.0,3.4,1.75), mats["plaster"],0.055)
    box("Stair_Head_Door", (3.35,0.09,8.58), (0.80,0.06,1.45), mats["wood"],0.018)
    for x in (2.25,2.70,3.15,3.60,4.05,4.50):
        curve("Rooftop_Service_Grille", ((x,0.02,8.05),(x,0.02,9.0)),0.018,mats["steel"])
    curve("Rooftop_Service_Rail", ((2.20,0.02,8.98),(4.55,0.02,8.98)),0.028,mats["steel"])

    # Water storage tank, support feet, fill pipe and vent — common rooftop utility cues.
    cylinder("Blue_Water_Tank_Body", (-2.55,1.55,8.83),0.78,1.62,mats["glass"],48)
    cylinder("Water_Tank_Lid", (-2.55,1.55,9.66),0.80,0.12,mats["steel"],48)
    for x in (-2.97,-2.13):
        for y in (1.13,1.97):
            box("Water_Tank_Support",(x,y,8.08),(0.12,0.12,0.80),mats["steel"],0.018)
    curve("Water_Tank_Fill_Pipe", ((-2.55,1.55,9.72),(-2.55,1.55,10.05),(-1.90,1.55,10.05)),0.035,mats["steel"])
    cylinder("Tank_Vent",(-2.55,1.55,9.97),0.055,0.42,mats["steel"],12)

    # Air-conditioning condenser with real grille depth and fan cage.
    box("AC_Condenser_Housing", (5.62,-3.36,5.25), (1.00,0.42,0.78), mats["steel"],0.055)
    for i in range(13):
        z=4.93+i*0.052
        curve("AC_Condenser_Fin", ((5.13,-3.60,z),(6.11,-3.60,z)),0.009,mats["steel"])
    cylinder("AC_Fan_Rim", (5.63,-3.62,5.26),0.255,0.04,mats["steel"],32,"Y")
    cylinder("AC_Fan_Hub", (5.63,-3.66,5.26),0.065,0.06,mats["wood"],20,"Y")
    for i in range(5):
        angle=2*math.pi*i/5
        curve("AC_Fan_Blade", ((5.63,-3.67,5.26),
                                (5.63+math.cos(angle)*0.12,-3.67,5.26+math.sin(angle)*0.12),
                                (5.63+math.cos(angle+0.55)*0.25,-3.67,5.26+math.sin(angle+0.55)*0.25)),0.025,mats["steel"])
    curve("AC_Coolant_Conduit", ((5.25,-3.70,4.98),(5.20,-3.76,4.45),(5.50,-3.76,4.12)),0.028,mats["steel"])

    # Meter cabinet, service cable, old drain and downpipe along the right edge.
    box("Utility_Meter_Cabinet", (5.59,-3.92,2.82), (0.40,0.20,0.62), mats["wood"],0.03)
    box("Electric_Meter_Glass", (5.59,-4.04,2.84), (0.25,0.03,0.30), mats["glass"],0.015)
    for x in (5.46,5.72):
        cylinder("Meter_Conduit",(x,-4.06,2.38),0.025,0.58,mats["steel"],12)
    curve("Facade_Service_Cable", ((5.5,-4.02,3.18),(5.5,-4.10,3.55),(4.7,-4.12,3.62),(3.7,-4.11,3.64),(2.2,-4.10,3.62)),0.018,mats["steel"])
    curve("Roof_Edge_Conduit", ((4.95,-4.08,7.45),(5.30,-4.08,7.65),(5.35,-4.08,8.15),(5.35,-4.08,8.62)),0.024,mats["steel"])
    curve("Rainwater_Downpipe", ((-5.27,-4.08,8.58),(-5.27,-4.08,7.8),(-5.30,-4.08,4.3),(-5.27,-4.08,0.18)),0.045,mats["steel"])
    for z in (1.0,3.0,5.0,7.0):
        curve("Downpipe_Clips", ((-5.34,-4.12,z),(-5.19,-4.12,z)),0.025,mats["steel"])

    # Front elevation wall lights, number plate, grille, drain and threshold details.
    for x in (-4.15,4.15):
        box("Wall_Light_Base", (x,-4.37,3.20), (0.16,0.08,0.23), mats["steel"],0.022)
        cylinder("Wall_Light_Diffuser", (x,-4.43,3.03),0.105,0.13,mats["glass"],20,"Y")
    box("Street_Number_Plate", (-5.02,-4.34,2.48), (0.35,0.08,0.42), mats["wood"],0.02)
    text_mesh("Street_Number", "17", (-5.02,-4.40,2.49),0.22,mats["letter"],font)
    # Drain grille aligned with the kerb at the frontage; gameplay collision comes from the map layer.
    box("Front_Drain_Frame", (0,-5.05,0.055), (2.6,0.54,0.10), mats["steel"],0.025)
    for x in [(-1.18+i*0.24) for i in range(11)]:
        box("Drain_Grille_Slot", (x,-5.05,0.115), (0.045,0.48,0.025), mats["wood"],0.004)
    for x in (-5.1,-3.0,0.0,3.0,5.1):
        box("Facade_Foundation_Stone", (x,-4.15,0.12), (0.52,0.38,0.24), mats["concrete"],0.025)

    # Side elevations and shop interior are separately authored, not generated from random boxes.
    for side_x,side in ((-5.47,-1.0),(5.47,1.0)):
        for y,z in ((-2.42,5.92),(0.10,5.92),(2.62,5.92)):
            _add_side_window(side_x,y,z,1.18,1.46,side,mats)
        # Side-wall damp marks and cable saddles make the long elevation read as used concrete.
        for i in range(9):
            y=-3.45+i*0.82
            box("Side_Wall_Damp_Stain",(side_x+side*0.148,y,1.18+(i%3)*0.17),
                (0.018,0.16+(i%2)*0.10,0.56+(i%3)*0.18),mats["concrete"],0.004)
        curve("Side_Elevation_Service_Cable",(
            (side_x+side*0.17,-3.70,3.55),(side_x+side*0.17,-2.6,3.58),
            (side_x+side*0.17,-0.8,3.60),(side_x+side*0.17,1.8,3.57),
            (side_x+side*0.17,3.7,3.62)),0.018,mats["steel"])
    _add_shop_interior(mats,find_bengali_font())

    # Rooftop service aerial with braced mast and simple dish.
    cylinder("Aerial_Mast",(4.85,2.9,9.24),0.028,1.6,mats["steel"],12)
    for z in (8.75,9.20,9.66):
        curve("Aerial_Crossbar", ((4.35,2.9,z),(5.35,2.9,z)),0.018,mats["steel"])
    curve("Aerial_Dish_Rim", ((4.15,2.65,9.15),(4.28,2.43,9.15),(4.52,2.32,9.15),(4.75,2.43,9.15),(4.88,2.65,9.15)),0.018,mats["steel"])


def combine_asset() -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in ASSET_OBJECTS: obj.select_set(True)
    active=ASSET_OBJECTS[0]
    bpy.context.view_layer.objects.active=active
    bpy.ops.object.join()
    root=bpy.context.object
    root.name=ASSET_NAME
    root.data.name=ASSET_NAME+"_Mesh"
    bpy.context.scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    root["a2_asset_id"]="shariatpur_riverfront_shophouse_hero"
    root["a2_asset_category"]="Bangladesh river-town mixed-use shopfront"
    root["a2_geographic_status"]="AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING"
    root["a2_gameplay_rule"]="Visual shell only; use OSM footprint, separate collision, entrance and floor graph"
    root["a2_texture_policy"]="2K base-colour JPEG quality 92; 1K lossless normal and roughness; embedded GLB images"
    root["a2_interior"]="Original same-building grocery-shop interior shell, display and furnishings included as authored visual geometry"

    for polygon in root.data.polygons: polygon.use_smooth=False
    return root


def render_preview(root: bpy.types.Object, preview_path: pathlib.Path) -> None:
    # Temporary studio deck and lights are not part of the exported asset.
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0,0,-0.07))
    floor=bpy.context.object; floor.name="PREVIEW_ONLY_StudioFloor"
    floor_mat=bpy.data.materials.new("PREVIEW_ONLY_WarmNeutralDeck"); floor_mat.diffuse_color=(0.18,0.20,0.19,1); floor_mat.roughness=0.92
    floor.data.materials.append(floor_mat)
    world=bpy.data.worlds.new("A2_Preview_StudioWorld"); world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.17,0.21,0.22,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.38
    bpy.context.scene.world=world

    def area(name, loc, energy, colour, size, target=(0,0,4.5)):
        data=bpy.data.lights.new(name,"AREA"); data.energy=energy; data.color=colour; data.shape="DISK"; data.size=size
        obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=loc
        direction=Vector(target)-obj.location; obj.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
        return obj
    area("PREVIEW_Key_Softbox",(2,-12,15),2100,(1.0,0.82,0.66),9)
    area("PREVIEW_Cool_Fill",(-12,-5,8),1450,(0.60,0.76,1.0),8)
    area("PREVIEW_Rim",(3,8,12),2300,(1.0,0.88,0.70),7)
    cam_data=bpy.data.cameras.new("PREVIEW_Front_ThreeQuarter_Camera")
    cam=bpy.data.objects.new("PREVIEW_Front_ThreeQuarter_Camera",cam_data); bpy.context.collection.objects.link(cam)
    cam.location=(14,-22,12.8); target=Vector((0,-0.1,4.7)); cam.rotation_euler=(target- cam.location).to_track_quat("-Z","Y").to_euler()
    cam_data.type="ORTHO"; cam_data.ortho_scale=17.5
    scene=bpy.context.scene; scene.camera=cam
    # GitHub-hosted headless runners do not expose a dependable EEVEE GPU context.
    # Cycles on CPU gives us a deterministic PBR preview with real material response.
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1400; scene.render.resolution_y=1100; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"; scene.render.film_transparent=False
    scene.view_settings.view_transform="AgX"
    scene.render.filepath=str(preview_path)
    # The GLB remains a single mesh; preview-only ground, camera and lights are deselected.
    bpy.ops.object.select_all(action="DESELECT"); root.select_set(True); bpy.context.view_layer.objects.active=root
    bpy.ops.render.render(write_still=True)
    for obj in (floor,cam):
        bpy.data.objects.remove(obj,do_unlink=True)
    for obj in list(bpy.data.objects):
        if obj.name.startswith("PREVIEW_"):
            bpy.data.objects.remove(obj,do_unlink=True)


def render_interior_preview(root: bpy.types.Object, preview_path: pathlib.Path) -> None:
    """Render a separate interior-facing camera pass for actual layout review."""
    scene=bpy.context.scene
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1500
    scene.render.resolution_y=1000
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.view_settings.view_transform="AgX"
    world=bpy.data.worlds.new("PREVIEW_Interior_World")
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.12,0.13,0.12,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.22
    scene.world=world

    def interior_area(name: str, loc: tuple[float,float,float], energy: float,
                      colour: tuple[float,float,float], size: float,
                      target: tuple[float,float,float]) -> None:
        data=bpy.data.lights.new(name,"AREA")
        data.energy=energy
        data.color=colour
        data.shape="DISK"
        data.size=size
        obj=bpy.data.objects.new(name,data)
        bpy.context.collection.objects.link(obj)
        obj.location=loc
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()

    interior_area("PREVIEW_Interior_Key",(0.0,-1.4,3.55),520,(1.0,0.79,0.58),3.0,(0.0,1.0,1.1))
    interior_area("PREVIEW_Interior_Fill",(-3.8,1.8,3.15),360,(0.72,0.83,1.0),2.5,(-1.0,1.0,1.2))
    interior_area("PREVIEW_Interior_Back",(3.4,2.7,3.2),300,(1.0,0.89,0.72),2.0,(1.0,1.5,1.1))
    camera_data=bpy.data.cameras.new("PREVIEW_Interior_Review_Camera")
    camera=bpy.data.objects.new("PREVIEW_Interior_Review_Camera",camera_data)
    bpy.context.collection.objects.link(camera)
    # Three-quarter entrance view: show the counter, cooler, rear stock wall,
    # side rack and clear walking aisle instead of filling the frame with one shelf.
    camera.location=(4.65,-4.65,2.05)
    target=Vector((-0.85,1.55,1.55))
    camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
    camera_data.type="PERSP"
    camera_data.lens=30
    camera_data.clip_start=0.05
    camera_data.clip_end=60
    scene.camera=camera
    scene.render.filepath=str(preview_path)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.render.render(write_still=True)
    for obj in list(bpy.data.objects):
        if obj.name.startswith("PREVIEW_"):
            bpy.data.objects.remove(obj,do_unlink=True)


def main() -> int:
    args=args_from_cli()
    args.out.parent.mkdir(parents=True,exist_ok=True); args.preview.parent.mkdir(parents=True,exist_ok=True); args.interior_preview.parent.mkdir(parents=True,exist_ok=True)
    print("A2_PROGRESS: reset scene", flush=True)
    reset_scene()
    print("A2_PROGRESS: load seven PBR material families", flush=True)
    mats=load_materials(args.textures)
    print("A2_PROGRESS: author building facade and local details", flush=True)
    build_shopfront(mats)
    print("A2_PROGRESS: combine one hero mesh", flush=True)
    root=combine_asset()
    # Triangle count is the final evaluated source mesh count, not an arbitrary target claim.
    triangles=sum(len(poly.vertices)-2 for poly in root.data.polygons)
    bounds=root.dimensions.copy()
    if min(bounds.x,bounds.y,bounds.z) <= 0:
        raise RuntimeError(f"Invalid model bounds: {tuple(bounds)}")
    bpy.context.scene.render.resolution_percentage=100
    print("A2_PROGRESS: render CPU PBR exterior preview", flush=True)
    render_preview(root,args.preview)
    print("A2_PROGRESS: render authored shop interior review preview", flush=True)
    render_interior_preview(root,args.interior_preview)
    print("A2_PROGRESS: export embedded GLB", flush=True)
    bpy.ops.object.select_all(action="DESELECT"); root.select_set(True); bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(args.out),export_format="GLB",use_selection=True,
                              export_apply=True,export_materials="EXPORT",export_image_format="AUTO",
                              export_tangents=True)
    license_path=args.out.parent/"LICENSE.txt"; license_path.write_text(LICENSE_TEXT,encoding="utf-8")
    texture_manifest=args.textures/"texture_manifest.json"
    texture_info=json.loads(texture_manifest.read_text(encoding="utf-8")) if texture_manifest.is_file() else {}
    manifest={
        "schema_version":1,"asset_id":"shariatpur_riverfront_shophouse_hero","asset_name":ASSET_NAME,
        "description":"Original, detailed Bangladesh river-town mixed-use shopfront archetype for the Shariatpur visual slice.",
        "geographic_status":"AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING",
        "runtime_placement":"Must be matched to a verified OSM building footprint and scaled only within documented tolerance; do not replace OSM navigation/collision/door graphs.",
        "license":"CC0-1.0","license_file":"LICENSE.txt","source":"Original Blender authoring script and original PBR texture generator in this repository.",
        "engine_target":"Godot 4.4.1","authoring_tool":"Blender 5.2.4 LTS","format":"glb",
        "bounds_metres":{"width":round(float(bounds.x),3),"depth":round(float(bounds.y),3),"height":round(float(bounds.z),3)},
        "triangle_count":triangles,"mesh_object_count":1,
        "materials":[m.name for m in root.data.materials],"texture_manifest":str(texture_manifest),
        "texture_resolution_policy":"2K base-colour JPEG quality 92; 1K lossless normal and roughness PNGs; embedded in GLB.",
        "interior_status":"AUTHORED_VISUAL_INTERIOR_INCLUDED_NOT_A_SURVEYED_PRIVATE_FLOOR_PLAN",
        "feature_inventory":["recessed timber and grilled windows","two ribbed shop roller shutters","RAQM-shaped baked Bengali exterior and interior sign faces","upper balcony with metal balusters","corrugated awning and brackets","roof parapet and stair head","rooftop water tank and service pipes","AC condenser and cooling fan grille","utility meter, drain, downpipe and facade cables","wall lights and foundation stonework","authored grocery interior with shelving, counter, display case, stocked goods and Bengali shop signage","detailed side elevations with recessed grilled windows, rain chajjas and service wiring"],
        "texture_surfaces":[item.get("name") for item in texture_info.get("surfaces",[])],
        "bengali_sign_art":[item.get("name") for item in texture_info.get("bengali_sign_art",[])],
        "quality_status":"CI_STRUCTURAL_VALIDATION_PENDING_VISUAL_AND_ANDROID_REVIEW",
        "asset_file":args.out.name,"preview_file":args.preview.name,
    }
    manifest_path=args.out.parent/"asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A2_SHARIATPUR_STREETFRONT_READY: " + json.dumps({"asset":str(args.out),"triangles":triangles,
          "bounds":manifest["bounds_metres"],"materials":len(root.data.materials),"preview":str(args.preview)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
