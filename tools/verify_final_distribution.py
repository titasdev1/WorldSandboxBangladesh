#!/usr/bin/env python3
"""Verify the exact signed APK that will be uploaded with its Shariatpur map pack."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_report(
    apk_path: Path,
    metadata_path: Path,
    map_parts_dir: Path,
    checksum_path: Path,
    core_report_path: Path,
) -> str:
    if not apk_path.is_file() or not metadata_path.is_file():
        raise ValueError("Final distribution is missing the signed APK or map manifest.")
    if not checksum_path.is_file() or not core_report_path.is_file():
        raise ValueError("Final distribution is missing the APK checksum or core-content verification report.")

    apk_hash = sha256_file(apk_path)
    checksum_tokens = checksum_path.read_text(encoding="utf-8").strip().split()
    if not checksum_tokens or checksum_tokens[0].lower() != apk_hash:
        raise ValueError("Signed APK SHA-256 does not match apk-sha256.txt.")

    core_report = core_report_path.read_text(encoding="utf-8")
    required_core_markers = (
        "Core APK modularity: PASS",
        "District-map resources bundled in core APK: 0",
        "Imported district GLB scenes bundled in core APK: 0",
    )
    missing = [marker for marker in required_core_markers if marker not in core_report]
    if missing:
        raise ValueError("Core APK content gate is incomplete: " + "; ".join(missing))

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    parts = metadata.get("parts", [])
    if not isinstance(parts, list) or not parts:
        raise ValueError("Shariatpur map manifest contains no split parts.")

    total_bytes = 0
    for part in parts:
        filename = str(part.get("asset_filename", ""))
        # Filenames must stay within the designated distribution directory.
        if not filename or Path(filename).name != filename:
            raise ValueError(f"Unsafe or missing map-part filename: {filename!r}")
        part_path = map_parts_dir / filename
        expected_size = int(part.get("size_bytes", -1))
        expected_hash = str(part.get("sha256", "")).lower()
        if not part_path.is_file() or part_path.stat().st_size != expected_size:
            raise ValueError(f"Missing or wrong-sized map part: {part_path}")
        if sha256_file(part_path) != expected_hash:
            raise ValueError(f"SHA-256 mismatch for map part: {part_path}")
        total_bytes += expected_size

    manifest_size = int(metadata.get("size_bytes", -1))
    if total_bytes != manifest_size:
        raise ValueError("Verified map-part sizes do not equal the full-pack manifest size.")

    pack_hash = str(metadata.get("sha256", "")).lower()
    if len(pack_hash) != 64:
        raise ValueError("Shariatpur map manifest has no valid full-pack SHA-256.")

    lines = [
        "FINAL SIGNED ANDROID DISTRIBUTION VERIFICATION",
        "",
        f"Core APK: {apk_path.name}",
        f"Core APK bytes (signed upload): {apk_path.stat().st_size}",
        f"Core APK SHA-256 (signed upload): {apk_hash}",
        "Signed APK checksum cross-check against apk-sha256.txt: PASS",
        "Core APK modularity and map-exclusion checks: PASS",
        "District map scenes bundled in core APK: 0 (intentional modular distribution)",
        "",
        f"External map pack: {metadata.get('asset_filename', 'Shariatpur map')}",
        f"External map pack bytes: {total_bytes}",
        f"External map pack SHA-256 (manifest): {pack_hash}",
        f"Split map parts: {len(parts)}",
        "Every map-part size and SHA-256: PASS",
        "Split parts sum to manifest size: PASS",
        "Physical Android-device launch/gameplay/performance QA: NOT VERIFIED",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, default=Path("build/Android/world_sandbox_bangladesh.apk"))
    parser.add_argument("--metadata", type=Path, default=Path("build/MapPacks/Project-A-Square-Shariatpur-Map.json"))
    parser.add_argument("--map-parts-dir", type=Path, default=Path("build/MapPacks"))
    parser.add_argument("--checksum", type=Path, default=Path("build/apk-sha256.txt"))
    parser.add_argument("--core-report", type=Path, default=Path("build/core-apk-content-verification.txt"))
    parser.add_argument("--output", type=Path, default=Path("build/apk-content-verification.txt"))
    args = parser.parse_args()

    report = build_report(
        args.apk, args.metadata, args.map_parts_dir, args.checksum, args.core_report
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
