#!/usr/bin/env python3
"""Verify the optional merged CC0 player model and its minimum animation coverage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "external_content" / "quaternius_hero"
MANIFEST = ASSET_ROOT / "asset_manifest.json"
HERO = ASSET_ROOT / "Project_A_Square_Hero.glb"
REPORT = ASSET_ROOT / "merge_report.json"
EXPECTED_CHARACTER_MODEL_MEMBER = "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", action="store_true", help="Treat an unavailable optional model as a release-blocking error.")
    args = parser.parse_args()
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        message = f"Quaternius hero manifest missing or invalid: {exc}"
        print(("ERROR: " if args.required else "WARNING: ") + message)
        return 1 if args.required else 0

    if manifest.get("available") is not True:
        reason = str(manifest.get("reason", "pinned CC0 model has not been fetched"))
        message = f"Authored hero unavailable; game will use its procedural fallback. {reason}"
        print(("ERROR: " if args.required else "WARNING: ") + message)
        return 1 if args.required else 0

    if manifest.get("character_model_member") != EXPECTED_CHARACTER_MODEL_MEMBER:
        print("ERROR: cached hero does not match the pinned, verified Superhero Male CC0 source; rebuild the character asset.")
        return 1

    if not HERO.is_file() or HERO.read_bytes()[:4] != b"glTF":
        print("ERROR: authored hero GLB is missing or not a binary glTF.")
        return 1
    digest = sha256(HERO)
    if digest != manifest.get("hero_glb_sha256"):
        print("ERROR: authored hero GLB SHA-256 differs from asset manifest.")
        return 1
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: merged animation report is missing or invalid: {exc}")
        return 1
    names = [str(name) for name in report.get("animation_names", [])]
    folded = [name.casefold() for name in names]
    required_motion = {
        "idle": any("idle" in name for name in folded),
        "walk": any("walk" in name for name in folded),
        "run": any(("run" in name or "sprint" in name) and "turn" not in name for name in folded),
    }
    if int(report.get("animation_clip_count", 0)) < 30 or not all(required_motion.values()):
        print(f"ERROR: merged hero animation coverage is too small: {required_motion}; {len(names)} clips.")
        return 1
    print(json.dumps({
        "available": True,
        "hero_glb": str(HERO.relative_to(ROOT)),
        "hero_glb_size_bytes": HERO.stat().st_size,
        "hero_glb_sha256": digest,
        "animation_count": len(names),
        "required_motion": required_motion,
        "license": manifest.get("license"),
        "character_model_member": manifest.get("character_model_member"),
        "character_archetype": manifest.get("character_archetype"),
        "runtime_fallback": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
