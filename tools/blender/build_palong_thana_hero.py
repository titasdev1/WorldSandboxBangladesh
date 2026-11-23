#!/usr/bin/env python3
"""Build a source-aligned Palong Model Thana shell and a detached gate concept.

The OSM footprint is exact source geometry. Facade bays, two-storey massing and
materials are explicit art-direction choices rather than survey claims. The gate
is exported separately at local origin until its real site position is matched.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any

R = 6_378_137.0
OSM_ID = "601571171"
NAME_BN = "পালং মডেল থানা"

def local_xy(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float,float]:
    return (math.radians(lon-lon0)*R*math.cos(math.radians(lat0)),
            math.radians(lat-lat0)*R)

def area2(points: list[tuple[float,float]]) -> float:
    return sum(points[i][0]*points[(i+1)%len(points)][1] -
               points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))

def read_source(geojson: Path, tile_manifest: Path) -> dict[str,Any]:
    src=json.loads(geojson.read_text(encoding="utf-8"))
    tile=json.loads(tile_manifest.read_text(encoding="utf-8"))
    origin=tile.get("local_origin_lat_lon")
    if not isinstance(origin,list) or len(origin)!=2:
        raise ValueError("Tile manifest has no local_origin_lat_lon")
    lat0,lon0=map(float,origin)
    matches=[f for f in src.get("features",[])
             if str(f.get("properties",{}).get("source_osm_id",""))==OSM_ID]
    if len(matches)!=1:
        raise ValueError(f"Expected one source OSM way {OSM_ID}; found {len(matches)}")
    f=matches[0]; props=f.get("properties",{}); geom=f.get("geometry",{})
    if geom.get("type")!="Polygon" or len(geom.get("coordinates",[]))!=1:
        raise ValueError("Thana source geometry must be one exterior Polygon ring")
    ll=[(float(p[0]),float(p[1])) for p in geom["coordinates"][0]]
    xy=[local_xy(lat,lon,lat0,lon0) for lon,lat in ll]
    if len(xy)<5 or xy[0]!=xy[-1]:
        raise ValueError("Thana exterior ring is not closed")
    ring=xy[:-1]; a=abs(area2(ring))/2
    if a<10: raise ValueError(f"Implausible footprint area: {a:.2f} m2")
    cx=sum(p[0] for p in ring)/len(ring); cy=sum(p[1] for p in ring)/len(ring)
    return {"ring":xy,"ring_ll":ll,"area":a,"center":(cx,cy),
            "origin":[lat0,lon0],"source_feature":str(props.get("osm_type","way"))+"/"+str(props.get("osm_id","")),
            "tags":{k:v for k,v in props.items() if k not in {"osm_id","osm_type","source_osm_id"}},
            "name":props.get("name","Palong Model Thana"),"name_bn":props.get("name:bn",NAME_BN),
            "tile":tile}

def read_pbr(path: Path|None) -> dict[str,Any]|None:
    if path is None: return None
    d=json.loads(path.read_text(encoding="utf-8"))
    if d.get("provider")!="Poly Haven" or d.get("asset_license")!="CC0-1.0":
        raise ValueError("PBR manifest must be Poly Haven / CC0-1.0")
    mats=d.get("materials",{})
    for name in ("weathered_plaster","aged_concrete","exposed_clay_brick"):
        if name not in mats: raise ValueError(f"Missing PBR material {name}")
        for semantic in ("base_color","normal","roughness"):
            rec=mats[name].get("maps",{}).get(semantic,{})
            img=Path(str(rec.get("path","")))
            if not img.is_file(): raise FileNotFoundError(img)
            if rec.get("md5") and hashlib.md5(img.read_bytes()).hexdigest()!=rec["md5"]:
                raise ValueError(f"PBR MD5 mismatch: {name}/{semantic}")
    return {"provider":d["provider"],"license":d["asset_license"],"path":str(path),"materials":mats}

def build_manifest(g:dict[str,Any]) -> dict[str,Any]:
    pts=g["ring"][:-1]; xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return {
      "schema_version":1,"asset_id":"palong_model_thana_hero_01",
      "status":"SOURCE_JOINED_ART_DIRECTED_ASSET_REVIEW_REQUIRED",
      "identity":{"name":g["name"],"name_bn":g["name_bn"],"osm_type":"way","osm_id":OSM_ID,
                  "source_feature":g["source_feature"],"tags":g["tags"]},
      "geography":{"tile_id":"tile_23p1835_90p3053","origin_lat_lon":g["origin"],
        "centroid_local_xy_m":[round(g["center"][0],3),round(g["center"][1],3)],
        "footprint_lon_lat":g["ring_ll"],"footprint_area_m2":round(g["area"],2),
        "footprint_local_xy_m":[[round(x,3),round(y,3)] for x,y in g["ring"]],
        "bbox_local_xy_m":[min(xs),min(ys),max(xs),max(ys)],
        "ground_elevation_m":None,"ground_status":"NO_DEM_OR_SURVEYED_LEVEL",
        "entrance_osm_node_id":None,"entrance_status":"UNVERIFIED_NO_MAPPED_ENTRANCE"},
      "art_direction":{"design_storeys":2,"storeys_status":"UNVERIFIED_ART_DIRECTION_ONLY",
        "height_m":7.2,"height_status":"UNVERIFIED_ART_DIRECTION_ONLY",
        "facade_status":"ORIGINAL_REPRESENTATIVE_ART_NOT_SURVEYED",
        "interior_status":"NOT_AUTHORED_NO_VERIFIED_ENTRY_OR_FLOOR_GRAPH"},
      "gate_concept":{"asset":"palong_thana_entrance_gate_concept.glb","site_coordinate":None,
        "placement":"DETACHED_LOCAL_ORIGIN_NOT_GEOGRAPHICALLY_PLACED",
        "visual_cues":["red-brick arch","Bengali identity sign","metal gate/fencing"],
        "evidence":["https://www.jagonews24.com/country/news/805575",
                    "https://www.prothomalo.com/bangladesh/district/9dk8y7bpff"]},
      "imagery_policy":{"google_maps_or_street_view_used":False,
        "press_photo_pixels_embedded":False,"press_photo_used_as_texture":False},
      "limits":["Only the OSM footprint is source-aligned; facade details are authored interpretation.",
        "Two storeys and 7.2 m height are unverified design values, not measurements.",
        "The detached gateway must not be placed in the live map until its real entrance position is matched.",
        "The PWD two-storey record is not joined to this OSM footprint.",
        "No interior or ground elevation is claimed."]}

def build_blender(args:argparse.Namespace) -> dict[str,Any]:
    import bpy
    from mathutils import Vector
    g=read_source(args.source_geojson,args.tile_manifest); manifest=build_manifest(g)
    pbr=read_pbr(args.pbr_manifest)
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    paths={k:out/v for k,v in {
      "blend":"palong_thana_authoring.blend","shell":"palong_thana_shell.glb",
      "gate":"palong_thana_entrance_gate_concept.glb","shell_preview":"palong_thana_shell_preview.png",
      "gate_preview":"palong_thana_gate_concept_preview.png"}.items()}
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        if c.name!="Collection":
            try: bpy.data.collections.remove(c)
            except RuntimeError: pass
    scene=bpy.context.scene
    building=bpy.data.collections.new("01 | SOURCE-ALIGNED THANA SHELL")
    gate=bpy.data.collections.new("02 | DETACHED GATE CONCEPT — POSITION UNVERIFIED")
    stage=bpy.data.collections.new("90 | PREVIEW ONLY — NOT EXPORTED")
    for c in (building,gate,stage): scene.collection.children.link(c)

    def material(name,color,rough=.8,metal=0.0,pbr_name=None,repeat=6.0):
        m=bpy.data.materials.new(name); m.diffuse_color=color; m.use_nodes=True
        n=m.node_tree.nodes; l=m.node_tree.links; p=n.get("Principled BSDF")
        p.inputs["Base Color"].default_value=color; p.inputs["Roughness"].default_value=rough
        p.inputs["Metallic"].default_value=metal
        record=pbr["materials"].get(pbr_name) if pbr and pbr_name else None
        if record:
            tc=n.new("ShaderNodeTexCoord"); mp=n.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value=(repeat,repeat,repeat); l.new(tc.outputs["Generated"],mp.inputs["Vector"])
            maps=record["maps"]
            for sem,out_socket,space in (("base_color","Base Color","sRGB"),("normal","Normal","Non-Color"),("roughness","Roughness","Non-Color")):
                image=bpy.data.images.load(str(maps[sem]["path"]),check_existing=True)
                image.colorspace_settings.name=space; image.pack()
                tex=n.new("ShaderNodeTexImage"); tex.image=image; tex.extension="REPEAT"
                l.new(mp.outputs["Vector"],tex.inputs["Vector"])
                if sem=="normal":
                    normal=n.new("ShaderNodeNormalMap"); normal.inputs["Strength"].default_value=.78
                    l.new(tex.outputs["Color"],normal.inputs["Color"]); l.new(normal.outputs["Normal"],p.inputs[out_socket])
                else: l.new(tex.outputs["Color"],p.inputs[out_socket])
        else:
            noise=n.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value=38; noise.inputs["Detail"].default_value=3
            bump=n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value=.15; bump.inputs["Distance"].default_value=.025
            l.new(noise.outputs["Fac"],bump.inputs["Height"]); l.new(bump.outputs["Normal"],p.inputs["Normal"])
        return m

    mats={
      "wall":material("Weathered institutional plaster",(0.66,.61,.51,1),.9,pbr_name="weathered_plaster",repeat=7),
      "concrete":material("Aged cement and concrete",(.43,.43,.39,1),.92,pbr_name="aged_concrete",repeat=7),
      "brick":material("Hand-laid red clay brick",(.35,.10,.055,1),.92,pbr_name="exposed_clay_brick",repeat=3),
      "trim":material("Pale limewashed concrete",(.76,.72,.63,1),.86,pbr_name="aged_concrete",repeat=8),
      "steel":material("Dark painted gate steel",(.045,.065,.06,1),.62,.55),
      "glass":material("Smoked blue-grey glazing",(.02,.055,.07,1),.22,.1),
      "shadow":material("Deep window recess",(.008,.012,.012,1),.98),
      "sign":material("Teal sign enamel",(.04,.15,.18,1),.35,.15),
      "gold":material("Warm sign border",(.72,.50,.18,1),.35,.6),
      "ink":material("Ivory sign lettering",(.96,.90,.73,1),.4)
    }

    def box(collection,name,center,size,mat,angle=0.0,bevel=.02):
        hx,hy,hz=[v*.5 for v in size]; verts=[]
        for z in (-hz,hz):
            for y in (-hy,hy):
                for x in (-hx,hx):
                    rx=x*math.cos(angle)-y*math.sin(angle); ry=x*math.sin(angle)+y*math.cos(angle)
                    verts.append((center[0]+rx,center[1]+ry,center[2]+z))
        faces=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
        me=bpy.data.meshes.new(name+" Mesh"); me.from_pydata(verts,[],faces); me.materials.append(mat); me.update()
        ob=bpy.data.objects.new(name,me); collection.objects.link(ob)
        if bevel>0:
            mod=ob.modifiers.new("Soft edge highlight","BEVEL"); mod.width=min(bevel,min(size)*.18); mod.segments=2
            ob.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
        return ob

    def facade_box(a,b,t,norm,z,w,d,h,mat,angle,name):
        c=(a[0]+(b[0]-a[0])*t+norm[0]*d*.1,a[1]+(b[1]-a[1])*t+norm[1]*d*.1,z)
        return box(building,name,c,(w,d,h),mat,angle,.01)

    ring=g["ring"]; pts=ring[:-1]; orientation=area2(pts)
    h=7.2
    verts=[(x,y,z) for z in (0,h) for x,y in pts]; count=len(pts)
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    mesh=bpy.data.meshes.new("Exact OSM way 601571171 footprint"); mesh.from_pydata(verts,[],faces)
    mesh.materials.append(mats["wall"]); mesh.update()
    shell=bpy.data.objects.new("Palong Model Thana | exact OSM footprint shell",mesh); building.objects.link(shell)
    bevel=shell.modifiers.new("Small render edge wear","BEVEL"); bevel.width=.035; bevel.segments=2
    shell.modifiers.new("Weighted normals","WEIGHTED_NORMAL")

    for i,a in enumerate(pts):
        b=pts[(i+1)%count]; dx=b[0]-a[0]; dy=b[1]-a[1]; length=math.hypot(dx,dy)
        ang=math.atan2(dy,dx)
        if orientation<0: nx,ny=-dy/length,dx/length; local_ang=ang
        else: nx,ny=dy/length,-dx/length; local_ang=ang+math.pi
        norm=(nx,ny)
        facade_box(a,b,.5,norm,.25,length,.18,.24,mats["concrete"],local_ang,"Ground plinth")
        facade_box(a,b,.5,norm,3.35,length+.12,.22,.16,mats["trim"],local_ang,"Floor band")
        bays=max(1,int(length/3.4))
        for z,wh in ((1.90,1.30),(5.02,1.20)):
            for j in range(bays):
                t=(j+.5)/bays; ww=min(1.38,length/bays*.55)
                facade_box(a,b,t,norm,z,ww+.18,.13,wh+.18,mats["shadow"],local_ang,"Window reveal")
                facade_box(a,b,t,norm,z,ww-.08,.07,wh-.08,mats["glass"],local_ang,"Smoked glazing")
                for sign in (-1,1):
                    jamb=facade_box(a,b,t,norm,z,.09,.16,wh+.10,mats["trim"],local_ang,"Window jamb")
                    jamb.location.x+=sign*(ww*.5+.005)*math.cos(local_ang)
                    jamb.location.y+=sign*(ww*.5+.005)*math.sin(local_ang)
                for sign in (-1,1):
                    facade_box(a,b,t,norm,z+sign*(wh*.5+.04),ww+.12,.17,.09,mats["trim"],local_ang,"Window lintel/sill")
                for k in range(5):
                    off=(k/4-.5)*(ww-.12)
                    bar=facade_box(a,b,t,norm,z,.032,.09,wh-.04,mats["steel"],local_ang,"Window security bar")
                    bar.location.x+=off*math.cos(local_ang); bar.location.y+=off*math.sin(local_ang)
                facade_box(a,b,t,norm,z,ww-.05,.08,.03,mats["steel"],local_ang,"Window grille crossbar")
        mid=((a[0]+b[0])*.5+nx*.03,(a[1]+b[1])*.5+ny*.03)
        box(building,"Roof parapet",(mid[0],mid[1],h+.43),(length+.1,.22,.86),mats["trim"],local_ang,.025)
        box(building,"Parapet coping",(mid[0],mid[1],h+.88),(length+.2,.28,.10),mats["concrete"],local_ang,.018)
        box(building,"Facade corner pier",(a[0]+nx*.06,a[1]+ny*.06,h*.5),(.24,.22,h),mats["trim"],local_ang,.025)

    # Detached gateway: its site coordinate and orientation remain unknown.
    for side in (-1,1):
        x=side*2.0
        box(gate,"Brick gate pier",(x,0,2.55),(.82,.72,5.1),mats["brick"],0,.045)
        box(gate,"Stone pier plinth",(x,-.02,.36),(.94,.84,.72),mats["trim"],0,.03)
        box(gate,"Stone pier cap",(x,-.02,5.20),(1.02,.9,.24),mats["trim"],0,.04)
        for z in (1.1,2.3,3.5,4.7):
            box(gate,"Pier cement band",(x,-.39,z),(.88,.08,.07),mats["trim"],0,.01)
    inner,outer,spring,depth=1.52,1.97,2.55,.68
    for i in range(19):
        a0=math.pi*i/19+.012; a1=math.pi*(i+1)/19-.012; v=[]
        for y in (-depth/2,depth/2):
            for r,a in ((inner,a0),(inner,a1),(outer,a1),(outer,a0)):
                v.append((r*math.cos(a),y,spring+r*math.sin(a)))
        me=bpy.data.meshes.new(f"Brick arch {i:02d} Mesh")
        me.from_pydata(v,[],[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
        me.materials.append(mats["brick"]); me.update()
        ob=bpy.data.objects.new(f"Brick arch voussoir {i:02d}",me); gate.objects.link(ob)
        mod=ob.modifiers.new("Soft brick arris","BEVEL"); mod.width=.012; mod.segments=2
    for side in (-1,1):
        x=side*.72
        box(gate,"Gate leaf shadow",(x,-.47,1.3),(1.3,.05,2.0),mats["shadow"])
        for k in range(11):
            xx=x+(k-5)*.112
            box(gate,"Forged vertical gate bar",(xx,-.53,1.31),(.032,.07,2.0),mats["steel"])
        for z in (.42,1.22,2.17):
            box(gate,"Forged horizontal rail",(x,-.535,z),(1.35,.075,.075),mats["steel"])
    box(gate,"Bengali nameboard",(0,-.43,4.92),(3.2,.12,.54),mats["sign"],bevel=.04)
    for z in (4.64,5.20):
        box(gate,"Nameboard brass border",(0,-.50,z),(3.12,.05,.035),mats["gold"],bevel=.008)
    for x in (-1.56,1.56):
        box(gate,"Nameboard brass side",(x,-.50,4.92),(.035,.05,.54),mats["gold"],bevel=.008)
    textdata=bpy.data.curves.new("Bengali station title","FONT"); textdata.body=NAME_BN; textdata.size=.34
    textdata.align_x="CENTER"; textdata.align_y="CENTER"; textdata.extrude=.004
    if args.bengali_font and Path(args.bengali_font).is_file():
        try: textdata.font=bpy.data.fonts.load(args.bengali_font)
        except Exception: pass
    txt=bpy.data.objects.new("পালং মডেল থানা | original text",textdata); gate.objects.link(txt)
    txt.location=(0,-.57,4.98); txt.rotation_euler=(math.pi/2,0,0); textdata.materials.append(mats["ink"])
    for side in (-1,1):
        for j in range(7):
            x=side*(2.55+j*.48)
            box(gate,"Detached concept fence upright",(x,0,1.05),(.07,.09,2.1),mats["steel"])
        for z in (.25,1.78):
            box(gate,"Detached concept fence rail",(side*4,0,z),(3.5,.1,.075),mats["steel"])

    # Preview-only ground, cameras and lights are deliberately not exported.
    cx,cy=g["center"]
    box(stage,"Shell preview ground",(cx,cy,-.14),(58,48,.2),mats["concrete"],bevel=0)
    box(stage,"Gate preview ground",(0,0,-.14),(15,10,.2),mats["concrete"],bevel=0)
    def look(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    camdata=bpy.data.cameras.new("Review camera"); cam=bpy.data.objects.new("Review camera",camdata); scene.collection.objects.link(cam)
    camdata.lens=52; scene.camera=cam
    keydata=bpy.data.lights.new("Soft overcast key","AREA"); keydata.energy=1800; keydata.shape="DISK"; keydata.size=14
    key=bpy.data.objects.new("Soft overcast key",keydata); scene.collection.objects.link(key)
    filldata=bpy.data.lights.new("Cool fill","AREA"); filldata.energy=680; filldata.shape="DISK"; filldata.size=10
    fill=bpy.data.objects.new("Cool fill",filldata); scene.collection.objects.link(fill)
    scene.world=bpy.data.worlds.new("Shariatpur overcast") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world.use_nodes=True; scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.36,.42,.46,1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.55
    scene.render.engine="CYCLES"; scene.cycles.samples=48; scene.cycles.use_denoising=True
    scene.render.resolution_x=1600; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
    scene.view_settings.view_transform="AgX"; scene.view_settings.look="AgX - Medium High Contrast"
    scene.render.image_settings.file_format="PNG"; scene.render.image_settings.color_mode="RGBA"
    cam.location=(cx+25,cy-21,15); look(cam,(cx,cy,3.3)); key.location=(cx-9,cy-10,19); look(key,(cx,cy,3))
    fill.location=(cx+9,cy+7,14); look(fill,(cx,cy,3))
    scene.render.filepath=str(out/"palong_thana_shell_preview.png"); bpy.ops.render.render(write_still=True)
    cam.location=(8,-13,7); look(cam,(0,0,2.4)); key.location=(-7,-6,12); look(key,(0,0,2.4))
    fill.location=(6,5,9); look(fill,(0,0,2.4))
    scene.render.filepath=str(out/"palong_thana_gate_concept_preview.png"); bpy.ops.render.render(write_still=True)

    def export_collection(collection,path):
        bpy.ops.object.select_all(action="DESELECT")
        for ob in collection.objects: ob.select_set(True)
        bpy.context.view_layer.objects.active=next(iter(collection.objects),None)
        bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,
          export_apply=True,export_texcoords=True,export_normals=True,export_materials="EXPORT",
          export_cameras=False,export_lights=False)
    shell=out/"palong_thana_shell.glb"; gate_glb=out/"palong_thana_entrance_gate_concept.glb"
    export_collection(building,shell); export_collection(gate,gate_glb)
    blend=out/"palong_thana_authoring.blend"; bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    manifest={
      "schema_version":1,"asset_id":"palong_model_thana_hero_01",
      "status":"SOURCE_JOINED_ART_DIRECTED_ASSET_REVIEW_REQUIRED",
      "osm_id":OSM_ID,"source_feature":"way/601571171001","tile":"tile_23p1835_90p3053",
      "footprint_area_m2":round(g["area"],2),"footprint_local_xy_m":g["ring"],
      "centroid_local_xy_m":g["center"],
      "design_storeys":2,"storey_status":"UNVERIFIED_ART_DIRECTION_ONLY",
      "design_height_m":7.2,"height_status":"UNVERIFIED_ART_DIRECTION_ONLY",
      "entrance_osm_node_id":None,"ground_elevation_m":None,"interior":"NOT_AUTHORED",
      "gate_site_coordinate":None,"gate_placement":"DETACHED_LOCAL_ORIGIN_NOT_GEOGRAPHICALLY_PLACED",
      "pbr_provider":pbr["provider"] if pbr else "PROCEDURAL_FALLBACK",
      "pbr_license":pbr["license"] if pbr else "ORIGINAL_PROCEDURAL_MATERIALS",
      "pbr_manifest":str(args.pbr_manifest) if pbr else None,
      "cc0_scanned_materials_embedded":bool(pbr),
      "google_maps_or_street_view_used":False,
      "source_photo_pixels_embedded":False,
      "outputs":{"blend":blend.name,"shell":shell.name,"gate_concept":gate_glb.name,
        "shell_preview":"palong_thana_shell_preview.png","gate_preview":"palong_thana_gate_concept_preview.png"},
      "limitations":["OSM footprint is source-aligned; facade bays and height are authored art direction.",
        "The PWD two-storey record has not been matched to this footprint.","No verified entrance, interior or terrain elevation.",
        "Do not position the detached gate in the game world without an independent site/entrance match."]
    }
    (out/"asset_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("A2_PALONG_THANA_HERO_READY:"+json.dumps({"shell":shell.name,"gate":gate_glb.name,
      "area_m2":manifest["footprint_area_m2"],"pbr":bool(pbr),"gate_position":manifest["gate_placement"]},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-geojson",required=True,type=Path)
    p.add_argument("--tile-manifest",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    p.add_argument("--bengali-font",default="/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf")
    p.add_argument("--pbr-manifest",type=Path)
    args=p.parse_args()
    build_blender(args)

if __name__=="__main__": main()
