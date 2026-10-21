#!/usr/bin/env python3
"""Fetch and merge the CC0 Quaternius hero and in-place animation libraries.

The upstream archives are downloaded from the publishers' official itch.io pages.
Only the character's GLTF dependencies and the two Standard animation GLBs are kept
in the temporary build folder. The final game resource is one textured, rigged GLB.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import http.cookiejar
import json
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "external_content" / "quaternius_hero"
HERO_GLB = OUTPUT / "Project_A_Square_Hero.glb"
MANIFEST = OUTPUT / "asset_manifest.json"
MERGE_REPORT = OUTPUT / "merge_report.json"

PACKS = (
    {
        "key": "base_characters",
        "page": "https://quaternius.itch.io/universal-base-characters",
        "upload_id": 15861669,
        "sha256": "fdbf1804c90dfc1ea03e992bff7da2dfd1a79318e13270a660180f9308455f40",
        "required_member_suffix": "Base Characters/Godot - UE/Regular_Male_FullBody.gltf",
    },
    {
        "key": "animation_library_1",
        "page": "https://quaternius.itch.io/universal-animation-library",
        "upload_id": 17958403,
        "sha256": "cc73fc4e495b82958207316596317a3f40b9fa38065bde1027937452da537724",
        "required_member_suffix": "Unreal-Godot/UAL1_Standard.glb",
    },
    {
        "key": "animation_library_2",
        "page": "https://quaternius.itch.io/universal-animation-library-2",
        "upload_id": 17958478,
        "sha256": "4008ea208a604773a2b2177d965f0f5d3195498b5bf838c3f5785d68e95f2a68",
        "required_member_suffix": "Unreal-Godot/UAL2_Standard.glb",
    },
)
USER_AGENT = "Project-A-Square-CC0-CharacterBuilder/1.0"
LICENSE = "CC0-1.0"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def request_bytes(opener, url: str, *, data: bytes | None = None, referer: str = "") -> bytes:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/json,application/octet-stream,*/*",
    }
    if referer:
        headers["Referer"] = referer
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with opener.open(req, timeout=90) as response:
        return response.read()


def csrf_token(page: str) -> str:
    patterns = (
        r"""name=["']csrf_token["'][^>]*value=["']([^"']+)""",
        r"""value=["']([^"']+)["'][^>]*name=["']csrf_token["']""",
    )
    for pattern in patterns:
        match = re.search(pattern, page, flags=re.I)
        if match:
            return html.unescape(match.group(1))
    raise RuntimeError("The publisher's download page did not contain a CSRF token.")


def download_itch_archive(pack: dict, destination: pathlib.Path) -> None:
    """Use itch.io's anonymous download flow and then verify the pinned archive hash."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page_url = str(pack["page"])
    first_page = request_bytes(opener, page_url).decode("utf-8", "replace")
    first_token = csrf_token(first_page)
    gate_json = request_bytes(
        opener,
        urllib.parse.urljoin(page_url.rstrip("/") + "/", "download_url"),
        data=urllib.parse.urlencode({"csrf_token": first_token}).encode("utf-8"),
        referer=page_url,
    )
    gate_payload = json.loads(gate_json.decode("utf-8", "replace"))
    gate_url = gate_payload.get("url") or gate_payload.get("download_url")
    if not gate_url:
        raise RuntimeError(f"Publisher did not return a download URL for {pack['key']}.")
    gate_url = urllib.parse.urljoin(page_url, str(gate_url))
    gate_page = request_bytes(opener, gate_url, referer=page_url).decode("utf-8", "replace")
    upload_id = str(pack["upload_id"])
    if not re.search(r"""data-upload_id=["']""" + re.escape(upload_id) + r"""["']""", gate_page, flags=re.I):
        # Some itch pages do not render the button's upload ID, but the pinned upload
        # ID is still source-controlled and the second CSRF token remains mandatory.
        if "download" not in gate_page.casefold() and "file" not in gate_page.casefold():
            raise RuntimeError(f"The itch.io gate page did not look like a download page for {pack['key']}.")
    second_token = csrf_token(gate_page)
    file_url = page_url.rstrip("/") + f"/file/{upload_id}?source=game_download&after_download_lightbox=1&as_props=1"
    file_json = request_bytes(
        opener,
        file_url,
        data=urllib.parse.urlencode({"csrf_token": second_token}).encode("utf-8"),
        referer=gate_url,
    )
    file_payload = json.loads(file_json.decode("utf-8", "replace"))
    signed_url = file_payload.get("url") or file_payload.get("download_url")
    if not signed_url:
        raise RuntimeError(f"itch.io did not return the signed file URL for {pack['key']}.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(str(signed_url), headers={"User-Agent": USER_AGENT, "Referer": gate_url})
    with opener.open(req, timeout=180) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    if sha256_file(destination) != pack["sha256"]:
        raise RuntimeError(f"SHA-256 mismatch for {pack['key']}; pinned source archive changed or was incomplete.")
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError(f"ZIP integrity check failed for {pack['key']}.")


def find_archive_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.replace("\\\\", "/").casefold().endswith(suffix.casefold())]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one archive member ending in {suffix!r}; found {len(matches)}.")
    return matches[0]


def extract_character_dependencies(archive_path: pathlib.Path, destination: pathlib.Path) -> pathlib.Path:
    """Extract one GLTF and its referenced files, resolving archive-relative texture locations safely."""
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = archive.namelist()
        model_member = find_archive_member(archive, str(PACKS[0]["required_member_suffix"]))
        model_folder = posixpath.dirname(model_member)
        parts = model_member.split("/")
        standard_root_index = next((i for i, part in enumerate(parts) if "standard" in part.casefold()), None)
        if standard_root_index is None:
            raise RuntimeError("Cannot identify the Standard pack root in the hero archive.")
        pack_root = "/".join(parts[: standard_root_index + 1]) + "/"
        pack_files = [
            name for name in archive_names
            if name.startswith(pack_root) and not name.endswith("/")
        ]
        names_by_casefold = {name.casefold(): name for name in pack_files}
        model_data = json.loads(archive.read(model_member).decode("utf-8"))
        # target archive path -> actual archive path. Copy dependencies to the path
        # declared by the GLTF even when the publisher stores the source texture in
        # a shared Textures folder or uses different filename capitalization.
        required: dict[str, str] = {model_member: model_member}
        dependencies = [
            item.get("uri", "") for item in model_data.get("buffers", [])
        ] + [
            item.get("uri", "") for item in model_data.get("images", [])
        ]
        for uri in dependencies:
            if not uri or uri.startswith("data:"):
                continue
            if urllib.parse.urlparse(uri).scheme:
                raise RuntimeError(f"External network image dependency is not allowed in character GLTF: {uri}")
            target_member = posixpath.normpath(posixpath.join(model_folder, urllib.parse.unquote(uri)))
            if not target_member.startswith(pack_root) or target_member.startswith("../") or "/../" in target_member:
                raise RuntimeError(f"Character dependency escapes its licensed archive folder: {uri}")
            source_member = names_by_casefold.get(target_member.casefold())
            if source_member is None:
                filename = posixpath.basename(target_member).casefold()
                candidates = [
                    name for name in pack_files
                    if posixpath.basename(name).casefold() == filename
                ]
                if len(candidates) == 1:
                    source_member = candidates[0]
                elif len(candidates) > 1:
                    target_parts = posixpath.dirname(target_member).casefold().split("/")
                    scored = []
                    for candidate in candidates:
                        candidate_parts = posixpath.dirname(candidate).casefold().split("/")
                        shared = 0
                        for left, right in zip(target_parts, candidate_parts):
                            if left != right:
                                break
                            shared += 1
                        scored.append((shared, candidate))
                    best_score = max(score for score, _ in scored)
                    best = [candidate for score, candidate in scored if score == best_score]
                    if best_score >= 1 and len(best) == 1:
                        source_member = best[0]
                    else:
                        raise RuntimeError(
                            f"Ambiguous GLTF dependency {uri!r}; matching archive members: {candidates[:8]}"
                        )
                else:
                    # Some exports append the image type to the texture basename
                    # (for example T_Hair_1_Normal_png.png) while the publisher's
                    # archive stores the underlying texture as T_Hair_1_Normal.png.
                    # Resolve only a unique same-extension, same-normalized-stem file.
                    target_path = pathlib.PurePosixPath(target_member)
                    target_stem = target_path.stem.casefold()
                    if target_stem.endswith("_png"):
                        target_stem = target_stem[:-4]
                    target_suffix = target_path.suffix.casefold()
                    stem_candidates = [
                        name for name in pack_files
                        if pathlib.PurePosixPath(name).suffix.casefold() == target_suffix
                        and pathlib.PurePosixPath(name).stem.casefold() == target_stem
                    ]
                    if len(stem_candidates) == 1:
                        source_member = stem_candidates[0]
                    elif len(stem_candidates) > 1:
                        target_dir_parts = posixpath.dirname(target_member).casefold().split("/")
                        ranked = []
                        for candidate in stem_candidates:
                            candidate_dir_parts = posixpath.dirname(candidate).casefold().split("/")
                            shared = 0
                            for left, right in zip(target_dir_parts, candidate_dir_parts):
                                if left != right:
                                    break
                                shared += 1
                            ranked.append((shared, candidate))
                        best_score = max(score for score, _ in ranked)
                        best_candidates = [candidate for score, candidate in ranked if score == best_score]
                        if best_score >= 1 and len(best_candidates) == 1:
                            source_member = best_candidates[0]
                        else:
                            raise RuntimeError(
                                f"Ambiguous normalized GLTF dependency {uri!r}; candidates: {stem_candidates[:8]}"
                            )
                    else:
                        similar_names = [
                            name for name in pack_files
                            if target_path.stem.split("_")[0].casefold() in pathlib.PurePosixPath(name).name.casefold()
                            and pathlib.PurePosixPath(name).suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}
                        ]
                        raise RuntimeError(
                            f"Missing GLTF dependency {target_member}; archive has no matching texture. "
                            f"Nearby candidates: {similar_names[:8]}"
                        )
            required[target_member] = source_member
        destination.mkdir(parents=True, exist_ok=True)
        for target_member, source_member in sorted(required.items()):
            relative = target_member[len(pack_root):]
            target = destination.joinpath(*pathlib.PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(source_member))
        license_member = next(
            (name for name in pack_files
             if pathlib.PurePosixPath(name).name.casefold() in
             {"license.txt", "license_standard.txt", "license.md", "license_standard.md"}),
            None,
        )
        if license_member:
            (OUTPUT / "LICENSE_Quaternius_Base_Characters.txt").write_bytes(archive.read(license_member))
        extracted_gltf = destination.joinpath(*pathlib.PurePosixPath(model_member[len(pack_root):]).parts)
        return extracted_gltf

def extract_animation_glb(archive_path: pathlib.Path, suffix: str, destination: pathlib.Path) -> pathlib.Path:
    with zipfile.ZipFile(archive_path) as archive:
        member = find_archive_member(archive, suffix)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(member))
        if destination.read_bytes()[:4] != b"glTF":
            raise RuntimeError(f"Animation library is not a binary GLB: {member}")
        license_member = next(
            (name for name in archive.namelist()
             if pathlib.PurePosixPath(name).name.casefold() in {"license.txt", "license_standard.txt", "license.md"}),
            None,
        )
        if license_member:
            (OUTPUT / f"LICENSE_Quaternius_{destination.stem}.txt").write_bytes(archive.read(license_member))
    return destination


def cache_is_valid() -> bool:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return (
            manifest.get("available") is True
            and manifest.get("license") == LICENSE
            and manifest.get("source_archive_sha256") == {p["key"]: p["sha256"] for p in PACKS}
            and HERO_GLB.is_file()
            and sha256_file(HERO_GLB) == manifest.get("hero_glb_sha256")
            and int(manifest.get("animation_count", 0)) >= 30
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def write_unavailable(reason: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if HERO_GLB.exists():
        HERO_GLB.unlink()
    manifest = {
        "available": False,
        "license": LICENSE,
        "source_pages": [pack["page"] for pack in PACKS],
        "source_archive_sha256": {p["key"]: p["sha256"] for p in PACKS},
        "animation_count": 0,
        "note": "The runtime uses its existing procedural character fallback until the pinned CC0 model and animation libraries can be fetched and merged.",
        "reason": reason[:1200],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", action="store_true", help="Fail if the licensed authored hero cannot be fetched and merged.")
    parser.add_argument("--force", action="store_true", help="Ignore a valid cached merge and fetch pinned source packs again.")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if not args.force and cache_is_valid():
        print(f"Quaternius hero cache verified: {HERO_GLB} ({sha256_file(HERO_GLB)}).")
        return 0

    try:
        with tempfile.TemporaryDirectory(prefix="project-a-square-hero-") as temp:
            work = pathlib.Path(temp)
            archives: dict[str, pathlib.Path] = {}
            for pack in PACKS:
                archive_path = work / f"{pack['key']}.zip"
                print(f"Fetching pinned CC0 asset pack: {pack['key']} from {pack['page']}", flush=True)
                download_itch_archive(pack, archive_path)
                archives[pack["key"]] = archive_path

            source_root = work / "base"
            character_gltf = extract_character_dependencies(archives["base_characters"], source_root)
            anim1 = extract_animation_glb(archives["animation_library_1"], "Unreal-Godot/UAL1_Standard.glb", work / "UAL1_Standard.glb")
            anim2 = extract_animation_glb(archives["animation_library_2"], "Unreal-Godot/UAL2_Standard.glb", work / "UAL2_Standard.glb")

            merge_dir = ROOT / "build" / "quaternius_character_merge"
            if merge_dir.exists():
                shutil.rmtree(merge_dir)
            merge_dir.mkdir(parents=True)
            merge_script = merge_dir / "merge_quaternius_character.mjs"
            merge_script.write_text(
                (ROOT / "tools" / "merge_quaternius_character.mjs").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            npm = shutil.which("npm")
            node = shutil.which("node")
            if not npm or not node:
                raise RuntimeError("Node.js/npm are required to assemble the pinned rigged character and clips.")
            subprocess.run(
                [npm, "install", "--no-audit", "--no-fund", "--no-package-lock", "@gltf-transform/core", "@gltf-transform/extensions"],
                cwd=merge_dir, check=True, timeout=240,
            )
            output_temp = work / "Project_A_Square_Hero.glb"
            report_temp = work / "merge_report.json"
            subprocess.run(
                [node, str(merge_script), str(character_gltf), str(output_temp), str(report_temp), str(anim1), str(anim2)],
                cwd=merge_dir, check=True, timeout=300,
            )
            report = json.loads(report_temp.read_text(encoding="utf-8"))
            if int(report.get("animation_clip_count", 0)) < 30:
                raise RuntimeError("The assembled hero GLB contains fewer than 30 usable animation clips.")
            glb_sha = sha256_file(output_temp)
            shutil.copy2(output_temp, HERO_GLB)
            shutil.copy2(report_temp, MERGE_REPORT)
            manifest = {
                "available": True,
                "asset": "Project_A_Square_Hero.glb",
                "license": LICENSE,
                "attribution_required": False,
                "source_pages": [pack["page"] for pack in PACKS],
                "source_archive_sha256": {p["key"]: p["sha256"] for p in PACKS},
                "hero_glb_sha256": glb_sha,
                "hero_glb_size_bytes": HERO_GLB.stat().st_size,
                "character_named_node_count": report.get("character_named_node_count", 0),
                "animation_count": report.get("animation_clip_count", 0),
                "animation_names": report.get("animation_names", []),
                "note": "One rigged, textured male hero mesh with compatible CC0 in-place UAL1/UAL2 animation clips; stylized regular-proportions character model, not a final photorealistic Bangladeshi civilian or CODM-quality military wardrobe.",
            }
            MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({
                "available": True,
                "hero_glb_size_bytes": manifest["hero_glb_size_bytes"],
                "animation_count": manifest["animation_count"],
                "hero_glb_sha256": glb_sha,
            }, indent=2))
        return 0
    except Exception as exc:  # A failed optional download must not break the playable fallback.
        write_unavailable(f"{type(exc).__name__}: {exc}")
        print(f"WARNING: authored Quaternius hero is unavailable; procedural fallback retained. {type(exc).__name__}: {exc}")
        return 1 if args.required else 0


if __name__ == "__main__":
    raise SystemExit(main())
