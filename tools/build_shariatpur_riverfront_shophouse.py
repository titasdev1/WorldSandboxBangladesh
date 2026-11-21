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

    # Signboard with Bengali local identity and a legible English sub-line.
    box("Shop_Signboard_Back", (0,-4.48,3.82), (4.55,0.20,0.92), mats["sign"], 0.045)
    for side in (-1,1):
        box("Signboard_Border", (side*2.18,-4.60,3.82), (0.045,0.03,0.80), mats["steel"], 0.008)
    font=find_bengali_font()
    text_mesh("Bengali_Shop_Name", "মা স্টোর", (0,-4.605,3.90), 0.56,mats["letter"],font)
    text_mesh("Bengali_District_Name", "শরীয়তপুর", (0,-4.608,3.55), 0.22,mats["letter"],font)
    box("Shop_Name_Small_Plaque", (0,-4.55,4.40), (3.10,0.11,0.18), mats["wood"],0.02)
    text_mesh("English_Shop_Subtitle", "DAILY NEEDS  •  RIVER TOWN", (0,-4.62,4.41), 0.105,mats["letter"],font)

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
