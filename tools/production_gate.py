#!/usr/bin/env python3
"""Production repository gate for World Sandbox: Bangladesh.

This gate intentionally checks production integrity, not workflow-count progress.
It runs before the canonical Android export and fails closed on regressions such as
multiple APK-producing workflows, missing core files, malformed state metadata, or
nested archive/filler artifacts.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

REQUIRED = [
    "project.godot",
    "Main.tscn",
    "world.gd",
    "player.gd",
    "hud.gd",
    "development_state.json",
    "development_roadmap.md",
    "PRODUCTION_MASTER_DIRECTIVE.md",
    ".github/workflows/android.yml",
]

for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        raise SystemExit(f"PRODUCTION GATE FAILED: missing {rel}")

state_path = ROOT / "development_state.json"
try:
    state = json.loads(state_path.read_text(encoding="utf-8"))
except Exception as exc:
    raise SystemExit(f"PRODUCTION GATE FAILED: development_state.json is invalid: {exc}")

if state.get("canonical_repository") != "titasdev1/WorldSandboxBangladesh":
    raise SystemExit("PRODUCTION GATE FAILED: canonical repository metadata mismatch")

# There must be one APK-producing workflow: android.yml.
workflow_dir = ROOT / ".github" / "workflows"
apk_workflows = []
for p in workflow_dir.glob("*.y*ml"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"presets_to_export:\s*Android|\.apk\b|godot-export", text, re.I):
        apk_workflows.append(p.name)

if apk_workflows != ["android.yml"]:
    raise SystemExit(
        "PRODUCTION GATE FAILED: expected exactly one APK workflow (android.yml), "
        f"found {apk_workflows}"
    )

# Keep feature modules as repository material, but don't pretend they are all integrated.
features = sorted((ROOT / "features").glob("feature_*.gd"))
if len(features) < 90:
    raise SystemExit(f"PRODUCTION GATE FAILED: expected retained feature modules, found {len(features)}")

# Reject accidental archives checked into the game tree.
nested_zips = [
    p.relative_to(ROOT).as_posix()
    for p in ROOT.rglob("*.zip")
    if ".git" not in p.parts
]
if nested_zips:
    raise SystemExit(f"PRODUCTION GATE FAILED: nested/filler ZIPs found: {nested_zips[:10]}")

print("PRODUCTION GATE PASSED")
print(f"Canonical project: {state['canonical_repository']}")
print(f"Retained feature modules: {len(features)}")
print("Canonical Android pipeline: .github/workflows/android.yml")
print("No workflow-count progress is treated as game progress.")
