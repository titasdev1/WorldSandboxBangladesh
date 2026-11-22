#!/usr/bin/env python3
"""Create original, tileable PBR materials and Bengali market signboards.

All textures are generated from scratch. Google Maps/Street View, satellite imagery,
third-party photographs and copyrighted game art are references only and are never
copied into the shipped materials.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features


SURFACES = {
    "weathered_plaster": (2048, "plaster"),
    "aged_concrete": (2048, "concrete"),
    "exposed_clay_brick": (2048, "brick"),
    "wet_asphalt": (2048, "asphalt"),
    "galvanized_shutter": (2048, "metal"),
    "painted_steel": (1024, "paint"),
    "aged_wood": (1024, "wood"),
    "market_canvas": (1024, "fabric"),
}

SIGNS = {
    "sonali_bank": ("সোনালী ব্যাংক", "SONALI BANK LIMITED", (22, 63, 104), (244, 238, 220)),
    "nakkhatra_fashion": ("নক্ষত্র ফ্যাশন", "NAKKHATRA FASHION", (95, 30, 39), (248, 226, 191)),
    "haru_ghosh_sweets": ("হারু ঘোষ মিষ্টান্ন ভাণ্ডার", "HARU GHOSH MISHTANNO BHANDAR", (24, 69, 53), (247, 225, 172)),
    "maa_store": ("মা স্টোর", "GROCERY & DAILY NEEDS", (18, 78, 68), (245, 226, 188)),
    "fresh_produce": ("ফল ও সবজি", "FRESH FRUIT & VEGETABLES", (126, 75, 22), (255, 238, 190)),
    "pharmacy": ("ঔষধালয়", "PHARMACY", (29, 66, 104), (237, 245, 238)),
    "stationery": ("স্টেশনারি", "STATIONERY & PRINT", (86, 65, 43), (245, 223, 179)),
    "hardware": ("হার্ডওয়্যার", "HARDWARE & BUILDING MATERIALS", (71, 74, 78), (239, 222, 190)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--size", type=int, default=2048)
    return parser.parse_args()


def _smooth_noise(size: int, rng: np.random.Generator, cells: int) -> np.ndarray:
    small = rng.integers(0, 256, (cells, cells), dtype=np.uint8)
    image = Image.fromarray(small, "L").resize((size, size), Image.Resampling.BICUBIC)
    return np.asarray(image, dtype=np.float32) / 255.0


def _base_noise(size: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    coarse = _smooth_noise(size, rng, 22)
    medium = _smooth_noise(size, rng, 90)
    fine = rng.random((size, size), dtype=np.float32)
    return coarse, medium, fine


def _make_surface(kind: str, size: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    coarse, medium, fine = _base_noise(size, seed)
    yy, xx = np.mgrid[0:size, 0:size]
    x = xx.astype(np.float32) / max(1, size - 1)
    y = yy.astype(np.float32) / max(1, size - 1)
    clouds = (coarse - 0.5) * 34 + (medium - 0.5) * 22 + (fine - 0.5) * 13
    height = np.full((size, size), 0.5, dtype=np.float32)

    if kind == "plaster":
        damp = np.clip((y - 0.62) / 0.38, 0, 1) ** 1.7
        vertical = (np.sin(x * 88 + np.sin(y * 9) * 4) > 0.92).astype(np.float32)
        streaks = vertical * np.clip((y - 0.16) / 0.84, 0, 1) * 23
        patch = np.sin(x * 15 + y * 11) * 4
        base = np.stack((183 + clouds - damp * 27 - streaks + patch,
                         172 + clouds * 0.91 - damp * 23 - streaks * 0.88 + patch,
                         151 + clouds * 0.76 - damp * 20 - streaks * 0.65 + patch), axis=-1)
        height = np.clip(0.5 + (coarse - 0.5) * 0.15 + (medium - 0.5) * 0.08 + damp * 0.09, 0, 1)
        rough = 212 + clouds * 0.36 + damp * 24
    elif kind == "concrete":
        aggregate = (fine > 0.985).astype(np.float32) * rng.uniform(22, 52, (size, size))
        base = np.stack((139 + clouds * 0.78 + aggregate,
                         137 + clouds * 0.74 + aggregate * 0.92,
                         127 + clouds * 0.68 + aggregate * 0.80), axis=-1)
        height = np.clip(0.5 + (coarse - 0.5) * 0.11 + (fine - 0.5) * 0.05, 0, 1)
        rough = 224 + clouds * 0.22
    elif kind == "brick":
        row_h = max(28, size // 18)
        brick_w = max(52, size // 9)
        row = yy // row_h
        stagger = (row % 2) * (brick_w // 2)
        bx = (xx + stagger) % brick_w
        mortar = (yy % row_h < max(4, size // 220)) | (bx < max(4, size // 220))
        chip = ((fine > 0.994) & (~mortar)).astype(np.float32)
        variation = clouds * 0.55
        base = np.stack((143 + variation - chip * 58,
                         73 + variation * 0.60 - chip * 38,
                         49 + variation * 0.48 - chip * 24), axis=-1)
        mortar_rgb = np.stack((177 + clouds * 0.25, 163 + clouds * 0.22, 143 + clouds * 0.20), axis=-1)
        base = np.where(mortar[..., None], mortar_rgb, base)
        height = np.where(mortar, 0.34, np.clip(0.59 + (medium - 0.5) * 0.15 - chip * 0.14, 0, 1))
        rough = np.where(mortar, 228, 193 + clouds * 0.25)
    elif kind == "asphalt":
        speck = (fine > 0.974).astype(np.float32) * rng.uniform(18, 64, (size, size))
        tiny = (fine > 0.996).astype(np.float32) * 48
        base = np.stack((58 + clouds * 0.22 + speck + tiny,
                         59 + clouds * 0.21 + speck * 0.94 + tiny,
                         57 + clouds * 0.18 + speck * 0.78 + tiny), axis=-1)
        cracks = (np.abs(np.sin(x * 97 + np.sin(y * 31) * 5)) < 0.018) & (coarse < 0.46)
        base[cracks] *= 0.47
        height = np.clip(0.5 + (medium - 0.5) * 0.18 + speck * 0.002, 0, 1)
        rough = 192 + (fine - 0.5) * 68
    elif kind == "metal":
        grooves = (np.cos(x * size * 2 * np.pi / max(18, size // 56)) + 1) * 10
        scratch = (fine > 0.994).astype(np.float32) * 55
        rust = np.clip((coarse - 0.58) * 3.3, 0, 0.9)
        base = np.stack((111 + grooves + clouds * 0.34 + rust * 42 - scratch,
                         125 + grooves + clouds * 0.35 - rust * 17 - scratch * 0.82,
                         128 + grooves + clouds * 0.34 - rust * 34 - scratch * 0.72), axis=-1)
        height = np.clip(0.5 + grooves / 110 + (medium - 0.5) * 0.10, 0, 1)
        rough = 148 + fine * 74 + rust * 20
    elif kind == "paint":
        scratches = (fine > 0.992).astype(np.float32) * 64
        rust = np.clip((coarse - 0.69) * 4, 0, 1)
        base = np.stack((39 + clouds * 0.34 + rust * 78 - scratches,
                         79 + clouds * 0.36 + rust * 22 - scratches,
                         79 + clouds * 0.32 - rust * 7 - scratches), axis=-1)
        height = np.clip(0.5 + (medium - 0.5) * 0.1 + rust * 0.09, 0, 1)
        rough = 167 + fine * 52 + rust * 26
    elif kind == "wood":
        grain = np.sin((y * size + np.sin(x * 31) * 10) * 2 * np.pi / max(22, size // 44)) * 11
        knots = np.exp(-(((x - 0.31) / 0.05) ** 2 + ((y - 0.56) / 0.08) ** 2)) * 32
        base = np.stack((111 + grain + clouds * 0.30 - knots,
                         77 + grain * 0.72 + clouds * 0.24 - knots * 0.78,
                         49 + grain * 0.47 + clouds * 0.18 - knots * 0.52), axis=-1)
        height = np.clip(0.5 + grain / 90 + (medium - 0.5) * 0.07, 0, 1)
        rough = 198 + fine * 38
    else:
        weave = (np.sin(x * size * 2 * np.pi / 21) + np.sin(y * size * 2 * np.pi / 19)) * 2.5
        base = np.stack((117 + clouds * 0.23 + weave,
                         87 + clouds * 0.20 + weave,
                         61 + clouds * 0.18 + weave), axis=-1)
        height = np.clip(0.5 + weave / 48 + (medium - 0.5) * 0.035, 0, 1)
        rough = 220 + fine * 24

    base = np.clip(base, 0, 255).astype(np.uint8)
    rough = np.clip(rough, 0, 255).astype(np.uint8)
    return base, height.astype(np.float32), rough


def _make_normal(height: np.ndarray, target_size: int) -> Image.Image:
    dy, dx = np.gradient(height.astype(np.float32))
    nx, ny, nz = -dx * 7.0, -dy * 7.0, np.ones_like(dx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack(((nx / length * 0.5 + 0.5) * 255,
                       (ny / length * 0.5 + 0.5) * 255,
                       (nz / length * 0.5 + 0.5) * 255), axis=-1).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(normal, "RGB")
    if image.size[0] != target_size:
        image = image.resize((target_size, target_size), Image.Resampling.LANCZOS)
    return image


def _font_path() -> pathlib.Path:
    candidates = [
        pathlib.Path("/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"),
        pathlib.Path("/usr/share/fonts/truetype/noto/NotoSansBengaliUI-Regular.ttf"),
        pathlib.Path("/usr/share/fonts/opentype/noto/NotoSansBengali-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    try:
        match = subprocess.run(
            ["fc-match", "-f", "%{file}", "Noto Sans Bengali"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if match and pathlib.Path(match).is_file():
            return pathlib.Path(match)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    raise FileNotFoundError("Noto Sans Bengali is required to create shaped market signs")


def _fit_font(font_path: pathlib.Path, text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size >= 30:
        font = ImageFont.truetype(str(font_path), size, layout_engine=ImageFont.Layout.RAQM)
        if ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font, direction="ltr", language="bn")[2] <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(str(font_path), 30, layout_engine=ImageFont.Layout.RAQM)


def _make_sign(out: pathlib.Path, key: str, title: str, subtitle: str,
               background: tuple[int, int, int], foreground: tuple[int, int, int],
               font_path: pathlib.Path) -> dict:
    width, height = 1536, 512
    rng = np.random.default_rng(sum(ord(c) for c in key) + 9021)
    grain = rng.normal(0, 3.8, (height, width, 1))
    bg = np.array(background, dtype=np.float32)[None, None, :]
    yy, xx = np.mgrid[0:height, 0:width]
    vignette = np.clip(1.0 - (((xx - width / 2) / width) ** 2 + ((yy - height / 2) / height) ** 2) * 0.35, 0.62, 1.0)
    rgb = np.clip(bg * vignette[..., None] + grain, 0, 255).astype(np.uint8)
    image = Image.fromarray(rgb, "RGB")
    draw = ImageDraw.Draw(image)
    edge = (max(10, height // 34))
    gold = (207, 177, 119)
    draw.rectangle((edge, edge, width - edge, height - edge), outline=gold, width=max(5, height // 90))
    draw.line((edge * 2, height - edge * 1.7, width - edge * 2, height - edge * 1.7),
              fill=tuple(int(c * 0.73) for c in background), width=4)
    title_font = _fit_font(font_path, title, width - edge * 5, 145)
    sub_font = ImageFont.truetype(str(font_path), 58, layout_engine=ImageFont.Layout.RAQM)
    fallback = ImageFont.truetype(str(font_path), 60, layout_engine=ImageFont.Layout.RAQM)
    draw.text((width // 2 + 2, 210 + 3), title, font=title_font, fill=(0, 0, 0), anchor="mm",
              direction="ltr", language="bn", stroke_width=2, stroke_fill=(0, 0, 0))
    draw.text((width // 2, 206), title, font=title_font, fill=foreground, anchor="mm",
              direction="ltr", language="bn", stroke_width=1, stroke_fill=gold)
    subtitle_font = ImageFont.truetype(str(font_path), 42, layout_engine=ImageFont.Layout.RAQM)
    draw.text((width // 2, 394), subtitle, font=subtitle_font, fill=(229, 215, 185), anchor="mm")
    # Scuffs and hairline scratches: subtle, not a uniform synthetic grunge filter.
    for _ in range(48):
        x0 = int(rng.integers(edge, width - edge))
        y0 = int(rng.integers(edge, height - edge))
        length = int(rng.integers(5, 45))
        shade = tuple(int(c * 0.75) for c in background)
        draw.line((x0, y0, min(width - edge, x0 + length), y0 + int(rng.integers(-3, 4))),
                  fill=shade, width=int(rng.integers(1, 3)))
    folder = out / "signs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{key}.png"
    image.save(path, "PNG", optimize=True)
    return {"path": path.as_posix(), "title": title, "subtitle": subtitle,
            "width": width, "height": height, "font_layout_engine": "RAQM"}


def build(out: pathlib.Path, size: int) -> dict:
    if size < 512 or size > 4096:
        raise ValueError("Texture size must be from 512 to 4096")
    if not features.check("raqm"):
        raise RuntimeError("Pillow must be built with RAQM/HarfBuzz for Bengali shaping")
    font_path = _font_path()
    materials = {}
    for index, (key, (resolution, kind)) in enumerate(SURFACES.items()):
        res = min(size, resolution)
        base, height, rough = _make_surface(kind, res, 8200 + index * 97)
        folder = out / key
        folder.mkdir(parents=True, exist_ok=True)
        base_path = folder / "base_color.jpg"
        normal_path = folder / "normal.png"
        rough_path = folder / "roughness.png"
        Image.fromarray(base, "RGB").save(base_path, "JPEG", quality=93, optimize=True, progressive=True, subsampling=0)
        _make_normal(height, max(512, res // 2)).save(normal_path, "PNG", optimize=True, compress_level=9)
        rough_image = Image.fromarray(rough, "L")
        rough_image = rough_image.resize((max(512, res // 2), max(512, res // 2)), Image.Resampling.LANCZOS)
        rough_image.save(rough_path, "PNG", optimize=True, compress_level=9)
        materials[key] = {
            "base_color": base_path.as_posix(), "normal": normal_path.as_posix(),
            "roughness": rough_path.as_posix(), "resolution": [res, res],
            "detail_resolution": [max(512, res // 2), max(512, res // 2)]
        }

    signs = {}
    for key, values in SIGNS.items():
        signs[key] = _make_sign(out, key, *values, font_path)

    manifest = {
        "schema_version": 1,
        "asset": "Palong Bazar corridor study",
        "source": "Original procedural PBR texture/sign generation; no third-party photos used",
        "geographic_reference": {
            "area": "Palong Bazar / Sonali Bank / Palong Bazar–Nirala Road, Shariatpur, Bangladesh",
            "reference_coordinate": [23.2181182, 90.3486077],
            "road_width_reference_m": 3.7,
            "status": "VISUAL_ART_DIRECTION_REFERENCE_NOT_SURVEYED_GEOMETRY"
        },
        "license": "CC0-1.0",
        "font": {"path": font_path.as_posix(), "layout_engine": "RAQM"},
        "materials": materials,
        "signs": signs
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "texture_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "LICENSE.txt").write_text(
        "PROJECT A-SQUARE ORIGINAL PALONG BAZAAR TEXTURES AND SIGN ART\n"
        "Generated from scratch using Python, NumPy and Pillow. No Google Maps/Street View, "
        "satellite images, third-party photographs or copyrighted game art are included.\n"
        "Visual reference only: Palong Bazar market corridor, Shariatpur, Bangladesh.\n"
        "Generated textures and sign artwork: CC0 1.0 Universal.\n", encoding="utf-8")
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build(args.out, args.size)
    print("A2_PALONG_TEXTURES_READY:" + json.dumps({
        "material_count": len(manifest["materials"]),
        "sign_count": len(manifest["signs"]),
        "font_layout_engine": manifest["font"]["layout_engine"],
        "output": args.out.as_posix()
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
