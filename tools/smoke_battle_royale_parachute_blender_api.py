#!/usr/bin/env python3
"""Blender-native smoke test for the parachute generator's slotted Action API."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_battle_royale_parachute import (  # noqa: E402
    action_fcurves_for_object,
    animate_wing,
)


def main() -> int:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    wing = bpy.data.objects.new("A2_Blender_Action_API_Smoke_Wing", None)
    bpy.context.collection.objects.link(wing)
    animate_wing(None, wing)

    animation_data = wing.animation_data
    if animation_data is None or animation_data.action is None:
        raise RuntimeError("Parachute wing did not receive a Blender Action")

    curves = list(action_fcurves_for_object(wing))
    if len(curves) != 3:
        raise RuntimeError(f"Expected 3 rotation F-curves, got {len(curves)}")

    curve_reports = []
    for curve in curves:
        if len(curve.keyframe_points) != 5:
            raise RuntimeError(
                f"{curve.data_path}[{curve.array_index}] should contain 5 keyframes"
            )
        if any(point.interpolation != "BEZIER" for point in curve.keyframe_points):
            raise RuntimeError(
                f"{curve.data_path}[{curve.array_index}] has non-BEZIER keyframes"
            )
        if not any(modifier.type == "CYCLES" for modifier in curve.modifiers):
            raise RuntimeError(
                f"{curve.data_path}[{curve.array_index}] is missing its looping CYCLES modifier"
            )
        curve_reports.append({
            "data_path": curve.data_path,
            "array_index": curve.array_index,
            "keyframes": len(curve.keyframe_points),
            "cycles": any(modifier.type == "CYCLES" for modifier in curve.modifiers),
        })

    if animation_data.action_slot is None and bpy.app.version >= (4, 4, 0):
        raise RuntimeError("Blender 4.4+ Action has no bound object slot")

    report = {
        "validation": "PASS",
        "blender_version": bpy.app.version_string,
        "action": animation_data.action.name,
        "slot_bound": animation_data.action_slot is not None,
        "fcurve_count": len(curves),
        "curves": curve_reports,
        "frame_range": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "fps": bpy.context.scene.render.fps,
    }
    print("A2_PARACHUTE_BLENDER_ACTION_API_PASS:", json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
