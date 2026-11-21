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

    base = Image.fromarray(np.dstack((rgb,np.full((size,size),255,dtype=np.uint8))),"RGBA")
    dy,dx=np.gradient(height.astype(np.float32))
    nx,ny,nz=-dx*5.0,-dy*5.0,np.ones_like(dx)
    length=np.sqrt(nx*nx+ny*ny+nz*nz)
    normal=np.stack(((nx/length*0.5+0.5)*255,(ny/length*0.5+0.5)*255,
                     (nz/length*0.5+0.5)*255,np.full_like(nx,255)),axis=-1).clip(0,255).astype(np.uint8)
    rough=np.clip(rough,0,255).astype(np.uint8)
    rough_img=np.dstack((rough,rough,rough,np.full_like(rough,255)))
    folder=out/SURFACES[key]
    folder.mkdir(parents=True,exist_ok=True)
    for name,image in (("base_color",base),("normal",Image.fromarray(normal,"RGBA")),
                       ("roughness",Image.fromarray(rough_img,"RGBA"))):
        image.save(folder/f"{name}.png",format="PNG",optimize=True,compress_level=7)
    return {"name":SURFACES[key],"resolution":[size,size],
            "maps":{kind:(folder/f"{kind}.png").as_posix()
                    for kind in ("base_color","normal","roughness")}}


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
    manifest={"schema_version":1,"project":"Project A-Square",
              "asset":"Shariatpur river-town shopfront hero","license":"CC0-1.0",
              "source":"Original deterministic PBR texture artwork; no external image textures",
              "resolution_policy":f"{args.size}px PBR master maps for mobile LOD variants",
              "surfaces":[{"name":SURFACES[k],"resolution":[args.size,args.size],
                           "maps":{m:(args.out/SURFACES[k]/f"{m}.png").as_posix()
                                   for m in ("base_color","normal","roughness")}} for k in SURFACES]}
    (args.out/"texture_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"A2_SHARIATPUR_TEXTURES_READY: surfaces={len(SURFACES)} resolution={args.size} output={args.out}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
