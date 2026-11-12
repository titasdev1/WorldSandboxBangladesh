from __future__ import annotations

import json
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import fetch_charactercreator_hero as pipeline
import convert_charactercreator_glbs as converter


def make_glb(document: dict) -> bytes:
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    total_length = 12 + 8 + len(payload)
    return (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<I4s", len(payload), b"JSON")
        + payload
    )


class CharacterCreatorHeroPipelineTests(unittest.TestCase):
    def test_upstream_source_is_immutable_and_assets_are_blob_pinned(self):
        self.assertEqual(len(pipeline.SOURCE_COMMIT), 40)
        self.assertTrue(pipeline.SOURCE_REPO.endswith("/CharacterCreator"))
        self.assertEqual(pipeline.LICENSE, "CC0-1.0")
        self.assertEqual(
            set(pipeline.ASSETS),
            {
                "base_body_anim.glb",
                "hair_short02.glb",
                "clothing_tshirt.glb",
                "clothing_jacket.glb",
                "clothing_jeans.glb",
                "clothing_boots.glb",
            },
        )
        for asset in pipeline.ASSETS.values():
            self.assertEqual(len(asset["blob_sha1"]), 40)
            self.assertTrue(asset["path"].startswith("output/"))

    def test_glb_parser_extracts_skin_animation_and_morph_metadata(self):
        bone_names = [
            "hand_r", "spine_02", "spine_03", "pelvis",
            "thigh_l", "thigh_r", "foot_l", "foot_r",
        ] + [f"bone_{index}" for index in range(45)]
        document = {
            "asset": {"version": "2.0"},
            "nodes": [{"name": name} for name in bone_names],
            "skins": [{"joints": list(range(len(bone_names)))}],
            "animations": [{"name": name} for name in [
                "idle", "idle_look", "idle_breathe", "idle_fidget",
                "walk", "run", "walk_back", "strafe_left",
                "strafe_right", "jump", "fall", "land",
            ]],
            "meshes": [{"primitives": [{"targets": [{} for _ in range(92)]}]}],
        }
        parsed = pipeline.parse_glb(make_glb(document), "synthetic.glb")
        metadata = pipeline.rig_metadata(parsed)
        self.assertEqual(metadata["bone_count"], 53)
        self.assertEqual(metadata["animation_count"], 12)
        self.assertEqual(metadata["morph_target_count_per_primitive"], 92)
        pipeline.verify_body(metadata)

    def test_invalid_or_non_rigged_glb_is_rejected(self):
        with self.assertRaises(RuntimeError):
            pipeline.parse_glb(b"not a glb", "bad.glb")
        with self.assertRaises(RuntimeError):
            pipeline.verify_body({
                "bone_count": 2,
                "bone_names": ["Root", "hand_r"],
                "animation_names": ["idle", "walk"],
                "animation_count": 2,
                "morph_target_count_per_primitive": 1,
            })

    def test_quantized_glb_is_rejected_until_dequantized(self):
        quantized = {
            "asset": {"version": "2.0"},
            "extensionsUsed": ["KHR_mesh_quantization"],
            "extensionsRequired": ["KHR_mesh_quantization"],
            "nodes": [],
            "skins": [],
            "animations": [],
            "meshes": [],
        }
        with self.assertRaisesRegex(RuntimeError, "KHR_mesh_quantization remains"):
            converter.assert_core_gltf_compatible(quantized, "quantized.glb")

    def test_core_gltf_without_mesh_quantization_is_accepted(self):
        compatible = {
            "asset": {"version": "2.0"},
            "extensionsUsed": [],
            "extensionsRequired": [],
            "nodes": [],
            "skins": [],
            "animations": [],
            "meshes": [],
        }
        converter.assert_core_gltf_compatible(compatible, "dequantized.glb")

    def test_accessory_requires_shared_skinned_bones(self):
        body = {f"bone_{index}" for index in range(25)}
        good = {"skin_count": 1, "bone_count": 20, "bone_names": sorted(body)[:20]}
        pipeline.verify_accessory(good, body, "clothing_jacket.glb")
        with self.assertRaises(RuntimeError):
            pipeline.verify_accessory(
                {"skin_count": 0, "bone_count": 0, "bone_names": []},
                body,
                "clothing_jacket.glb",
            )
        with self.assertRaises(RuntimeError):
            pipeline.verify_accessory(
                {"skin_count": 1, "bone_count": 1, "bone_names": ["other"]},
                body,
                "hair_short02.glb",
            )


if __name__ == "__main__":
    unittest.main()
