#!/usr/bin/env python3
"""Create original tileable PBR textures for the Shariatpur streetfront.

The textures are generated from scratch; no external image textures, satellite
tiles, street-view photos or proprietary game art are copied into the asset.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SURFACES = {
    "plaster": "weathered_teal_plaster",
    "brick": "local_clay_brick",
    "steel": "galvanized_rust_wear",
    "concrete": "weathered_cast_concrete",
    "glass": "smoked_shop_glass",
    "wood": "aged_teak_wood",
    "signboard": "painted_signboard",
}


def noise_field(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    fine = rng.random((size, size), dtype=np.float32)
    coarse = Image.fromarray(rng.integers(0, 256, (48, 48), dtype=np.uint8)).resize(
        (size, size), Image.Resampling.BICUBIC
    )
    return fine * 0.34 + np.asarray(coarse, dtype=np.float32) / 255.0 * 0.66


def make_maps(out: pathlib.Path, key: str, size: int) -> dict:
    rng = np.random.default_rng(8127 + list(SURFACES).index(key) * 31)
    n = noise_field(size, 8127 + list(SURFACES).index(key))
    yy, xx = np.mgrid[0:size, 0:size]
    y = yy.astype(np.float32) / max(1, size - 1)

    if key == "plaster":
        grime = np.clip((y - 0.48) / 0.52, 0, 1) ** 1.5
        ripple = np.sin(xx * 0.021 + np.sin(yy * 0.009) * 1.8) * 2.2
        variation = (n - 0.5) * 28 + ripple
        rgb = np.stack((174 + variation - grime*24, 185 + variation - grime*22,
                        163 + variation - grime*19), axis=-1)
        height = np.clip(0.5 + (n-0.5)*0.18 + grime*0.10, 0, 1)
        rough = np.clip(208 + (n-0.5)*38 + grime*16, 0, 255)
    elif key == "brick":
        mortar = ((yy % max(20,size//22)) < max(2,size//300)) | (
            ((xx + (yy//max(20,size//22) % 2)*max(20,size//44)) % max(40,size//11)) < max(2,size//300)
        )
        variation = (n - 0.5) * 36
        rgb = np.stack((139+variation, 67+variation*0.68, 44+variation*0.43),axis=-1)
        rgb[mortar] = (174,160,142)
        height = np.where(mortar,0.36,0.56+(n-0.5)*0.18)
        rough = np.where(mortar,220,195+(n-0.5)*32)
    elif key == "steel":
        groove = (np.cos(xx * (2*np.pi/max(16,size//64))) + 1)*8
        rust = np.clip((n-0.60)*3.0,0,0.9)
        rgb = np.stack((104+groove+(n-0.5)*22+rust*48,
                        119+groove+(n-0.5)*24-rust*18,
                        119+groove+(n-0.5)*25-rust*35),axis=-1)
        height = np.clip(0.52+groove/100+(n-0.5)*0.12,0,1)
        rough = np.clip(132+n*68+rust*38,0,255)
    elif key == "concrete":
        ripple = np.sin(xx*0.034+np.sin(yy*0.012)*2)*2.5
        v = (n-0.5)*32+ripple
        rgb = np.stack((139+v,140+v*0.96,133+v*0.88),axis=-1)
        height = np.clip(0.5+(n-0.5)*0.15,0,1)
        rough = np.clip(222+(n-0.5)*26,0,255)
    elif key == "glass":
        reflection = np.clip((xx+yy*0.28)/(size*1.28),0,1)
        stripe = (np.sin((xx+yy*0.32)*2*np.pi/(size/5.5))>0.94)
        rgb = np.stack((23+n*9+reflection*24,43+n*12+reflection*34,
                        55+n*16+reflection*42),axis=-1)
        rgb[stripe] += (18,24,28)
        height = np.clip(0.5+(n-0.5)*0.025,0,1)
        rough = np.clip(42+n*24+reflection*12,0,255)
    elif key == "wood":
        grain = np.sin((yy+np.sin(xx/37.0)*8)*2*np.pi/(size/55))*7
        rgb = np.stack((103+grain+(n-0.5)*22,68+grain*0.7+(n-0.5)*17,
                        43+grain*0.45+(n-0.5)*13),axis=-1)
        height = np.clip(0.5+grain/80+(n-0.5)*0.08,0,1)
        rough = np.clip(190+n*35,0,255)
    else:
        rgb = np.broadcast_to(np.array([14,75,67],dtype=np.float32),(size,size,3)).copy()
        # Gold frame and a painted field. The Bangla title is added below as real typography.
        height = np.full((size,size),0.5,dtype=np.float32)
        rough = np.full((size,size),96,dtype=np.float32)
    rgb = np.clip(rgb,0,255).astype(np.uint8)

    if key == "signboard":
        sign = Image.fromarray(np.dstack((rgb,np.full((size,size),255,dtype=np.uint8))),"RGBA")
        draw = ImageDraw.Draw(sign)
        border=max(9,size//90)
        draw.rectangle((border,border,size-border,size-border),outline=(213,184,119,255),width=border)
        font_path=""
        try:
            found=subprocess.run(["fc-match","Noto Sans Bengali","-f","%{file}"],capture_output=True,text=True,check=False).stdout.strip()
            if found and pathlib.Path(found).is_file(): font_path=found
        except Exception: pass
        font=ImageFont.truetype(font_path,max(24,size//13)) if font_path else ImageFont.load_default()
        small=ImageFont.truetype(font_path,max(16,size//34)) if font_path else ImageFont.load_default()
        draw.text((size//2,size//2), "মা স্টোর  •  শরীয়তপুর", font=font, fill=(245,226,183,255), anchor="mm")
        draw.text((size//2,int(size*0.78)), "MAA STORE  /  SHARIATPUR", font=small, fill=(220,210,183,255), anchor="mm")
        rgb=np.asarray(sign,dtype=np.uint8)[:,:,:3]
        height=np.full((size,size),0.5,dtype=np.float32)
        rough=np.full((size,size),96,dtype=np.float32)

    # Keep the 2K colour master while lowering auxiliary maps to 1K for
    # mobile memory/asset size. Base colour uses high-quality JPEG; normal and
    # roughness remain lossless PNG to protect shading data.
    base = Image.fromarray(rgb, "RGB")
    dy,dx=np.gradient(height.astype(np.float32))
    nx,ny,nz=-dx*5.0,-dy*5.0,np.ones_like(dx)
    length=np.sqrt(nx*nx+ny*ny+nz*nz)
    normal=np.stack(((nx/length*0.5+0.5)*255,(ny/length*0.5+0.5)*255,
                     (nz/length*0.5+0.5)*255),axis=-1).clip(0,255).astype(np.uint8)
    rough=np.clip(rough,0,255).astype(np.uint8)
    normal_size=max(512,size//2)
    if normal_size != size:
        normal=Image.fromarray(normal,"RGB").resize((normal_size,normal_size),Image.Resampling.LANCZOS)
        rough_img=Image.fromarray(rough,"L").resize((normal_size,normal_size),Image.Resampling.LANCZOS)
    else:
        normal=Image.fromarray(normal,"RGB")
        rough_img=Image.fromarray(rough,"L")
    folder=out/SURFACES[key]
    folder.mkdir(parents=True,exist_ok=True)
    base_path=folder/"base_color.jpg"
    normal_path=folder/"normal.png"
    rough_path=folder/"roughness.png"
    base.save(base_path,format="JPEG",quality=92,optimize=True,progressive=True,subsampling=0)
    normal.save(normal_path,format="PNG",optimize=True,compress_level=9)
    rough_img.save(rough_path,format="PNG",optimize=True,compress_level=9)
    return {
        "name":SURFACES[key],
        "base_color_resolution":[size,size],
        "normal_roughness_resolution":[normal_size,normal_size],
        "maps":{"base_color":base_path.as_posix(),"normal":normal_path.as_posix(),"roughness":rough_path.as_posix()},
        "formats":{"base_color":"JPEG_QUALITY_92","normal":"PNG_LOSSLESS","roughness":"PNG_LOSSLESS"},
    }


def make_bengali_sign_art(out: pathlib.Path, name: str, title: str, subtitle: str, width: int = 2048, height: int = 512) -> dict:
    """Create shaped, high-resolution Bengali sign artwork with RAQM/HarfBuzz."""
    out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(271828 + sum(ord(ch) for ch in name))
    yy,xx=np.mgrid[0:height,0:width]
    vertical=yy.astype(np.float32)/max(1,height-1)
    grain=rng.normal(0,1.8,(height,width)).astype(np.float32)
    light=np.clip(1.0-0.10*vertical+grain/255.0,0.82,1.06)
    base=np.zeros((height,width,3),dtype=np.uint8)
    base[:,:,0]=np.clip(12*light,0,255).astype(np.uint8)
    base[:,:,1]=np.clip(67*light,0,255).astype(np.uint8)
    base[:,:,2]=np.clip(56*light,0,255).astype(np.uint8)
    image=Image.fromarray(base,"RGB").convert("RGBA")
    draw=ImageDraw.Draw(image)
    gold=(207,174,105,255)
    ivory=(250,235,201,255)
    dark=(7,37,31,255)
    outer=max(9,width//170)
    inner=max(4,width//360)
    draw.rounded_rectangle((outer,outer,width-outer,height-outer),radius=height//18,outline=gold,width=outer)
    draw.rounded_rectangle((outer*2,outer*2,width-outer*2,height-outer*2),radius=height//24,outline=(154,125,73,255),width=inner)
    for x in (outer*3,width-outer*3):
        for y in (outer*3,height-outer*3):
            draw.ellipse((x-5,y-5,x+5,y+5),fill=gold)
    font_path=""
    try:
        found=subprocess.run(["fc-match","Noto Sans Bengali","-f","%{file}"],capture_output=True,text=True,check=False).stdout.strip()
        if found and pathlib.Path(found).is_file():
            font_path=found
    except Exception:
        pass
    if font_path:
        title_font=ImageFont.truetype(font_path,int(height*0.38),layout_engine=ImageFont.Layout.RAQM)
        subtitle_font=ImageFont.truetype(font_path,int(height*0.15),layout_engine=ImageFont.Layout.RAQM)
    else:
        title_font=ImageFont.load_default()
        subtitle_font=ImageFont.load_default()
    # RAQM shapes conjuncts, vowel marks and reph before baking the texture.
    draw.text((width//2,int(height*0.43)),title,font=title_font,fill=ivory,anchor="mm",
              direction="ltr",language="bn",stroke_width=1,stroke_fill=dark)
    draw.text((width//2,int(height*0.76)),subtitle,font=subtitle_font,fill=gold,anchor="mm",
              direction="ltr",language="bn")
    rgb=np.asarray(image.convert("RGB"),dtype=np.uint8)
    color=Image.fromarray(rgb,"RGB")
    folder=out/name
    folder.mkdir(parents=True,exist_ok=True)
    color_path=folder/"base_color.jpg"
    normal_path=folder/"normal.png"
    rough_path=folder/"roughness.png"
    color.save(color_path,format="JPEG",quality=94,optimize=True,progressive=True,subsampling=0)
    normal_size=(width//2,height//2)
    flat_normal=np.zeros((normal_size[1],normal_size[0],3),dtype=np.uint8)
    flat_normal[:,:,:]=(128,128,255)
    Image.fromarray(flat_normal,"RGB").save(normal_path,format="PNG",optimize=True,compress_level=9)
    Image.new("L",normal_size,110).save(rough_path,format="PNG",optimize=True,compress_level=9)
    return {
        "name":name,
        "base_color_resolution":[width,height],
        "normal_roughness_resolution":list(normal_size),
        "maps":{"base_color":color_path.as_posix(),"normal":normal_path.as_posix(),"roughness":rough_path.as_posix()},
        "formats":{"base_color":"JPEG_QUALITY_94_BAKED_RAqm_BENGALI","normal":"PNG_LOSSLESS","roughness":"PNG_LOSSLESS"},
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=pathlib.Path,required=True)
    parser.add_argument("--size",type=int,default=2048)
    parser.add_argument("--surface",choices=tuple(SURFACES))
    args=parser.parse_args()
    if args.size not in (512,1024,2048,4096):
        raise SystemExit("Texture size must be 512, 1024, 2048 or 4096")
    args.out.mkdir(parents=True,exist_ok=True)
    if args.surface:
        make_maps(args.out,args.surface,args.size)
        return 0
    # Isolate each high-resolution surface bake so runner memory stays bounded.
    for key in SURFACES:
        subprocess.run([sys.executable,str(pathlib.Path(__file__).resolve()),
                        "--out",str(args.out),"--size",str(args.size),"--surface",key],check=True)
    sign_art=[
        make_bengali_sign_art(args.out,"shop_sign","মা স্টোর","শরীয়তপুর  •  নিত্যপ্রয়োজনীয় পণ্য"),
        make_bengali_sign_art(args.out,"interior_sign","চাল  •  ডাল  •  তেল  •  মসলা","খুচরা বিক্রয়"),
    ]
    manifest={"schema_version":3,"project":"Project A-Square",
              "asset":"Shariatpur river-town shopfront hero","license":"CC0-1.0",
              "source":"Original deterministic PBR texture artwork; no external image textures",
              "resolution_policy":"2K base colour JPEG quality 92; 1K lossless PNG normal and roughness maps.",
              "bengali_sign_art":sign_art,
              "surfaces":[
                  {"name":SURFACES[k],
                   "base_color_resolution":[args.size,args.size],
                   "normal_roughness_resolution":[max(512,args.size//2),max(512,args.size//2)],
                   "maps":{"base_color":(args.out/SURFACES[k]/"base_color.jpg").as_posix(),
                           "normal":(args.out/SURFACES[k]/"normal.png").as_posix(),
                           "roughness":(args.out/SURFACES[k]/"roughness.png").as_posix()},
                   "formats":{"base_color":"JPEG_QUALITY_92","normal":"PNG_LOSSLESS","roughness":"PNG_LOSSLESS"}}
                  for k in SURFACES]}
    (args.out/"texture_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"A2_SHARIATPUR_TEXTURES_READY: surfaces={len(SURFACES)} resolution={args.size} output={args.out}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
