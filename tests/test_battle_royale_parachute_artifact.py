from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.verify_battle_royale_parachute import (
    EXPECTED_ANIMATION,
    REQUIRED_NODES,
    parse_glb,
    verify_asset,
)


def make_glb(*, omit_animation: bool = False, omit_node: str = "") -> bytes:
    nodes = [{"name": name} for name in REQUIRED_NODES if name != omit_node]
    nodes.extend([
        {"name": f"Suspension_Line_{i:02d}_{j}"}
        for i in range(9) for j in range(4)
    ])
    nodes.extend([{"name": f"Riser_Carabiner_{side}"} for side in ("L", "R")])
    meshes = [{"name": f"AssemblyMesh_{i}", "primitives": []} for i in range(24)]
    document = {
        "asset": {"version": "2.0", "generator": "A-Square test fixture"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [{"name": "A2_Fabric_Olive"}],
        "animations": [] if omit_animation else [{"name": EXPECTED_ANIMATION}],
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    chunk = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    total = 12 + len(chunk)
    return struct.pack("<4sII", b"glTF", 2, total) + chunk


class BattleRoyaleParachuteArtifactTests(unittest.TestCase):
    def test_validates_full_cc0_canopy_and_harness_assembly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb = root / "canopy.glb"
            licence = root / "LICENSE.txt"
            glb.write_bytes(make_glb())
            licence.write_text(
                "A-Square Ram-Air Canopy and Harness\nCC0 1.0 Universal",
                encoding="utf-8",
            )
            report = verify_asset(glb, licence)
            self.assertEqual(report["validation"], "PASS")
            self.assertEqual(report["license"], "CC0-1.0")
            self.assertEqual(report["animation_names"], [EXPECTED_ANIMATION])

    def test_rejects_missing_inflation_animation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb, licence = root / "canopy.glb", root / "LICENSE.txt"
            glb.write_bytes(make_glb(omit_animation=True))
            licence.write_text("A-Square Ram-Air Canopy and Harness\nCC0 1.0 Universal")
            with self.assertRaisesRegex(ValueError, "missing animation"):
                verify_asset(glb, licence)

    def test_rejects_missing_riser_harness_or_canopy_node(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb, licence = root / "canopy.glb", root / "LICENSE.txt"
            glb.write_bytes(make_glb(omit_node="Canopy_28_Inflated_Fabric_Cells"))
            licence.write_text("A-Square Ram-Air Canopy and Harness\nCC0 1.0 Universal")
            with self.assertRaisesRegex(ValueError, "required assembly nodes"):
                verify_asset(glb, licence)

    def test_rejects_invalid_glb_header_and_missing_license(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            glb, licence = root / "canopy.glb", root / "LICENSE.txt"
            glb.write_bytes(b"not a glb" * 500)
            licence.write_text("CC0")
            with self.assertRaisesRegex(ValueError, "invalid GLB"):
                verify_asset(glb, licence)
            glb.write_bytes(make_glb())
            licence.unlink()
            with self.assertRaisesRegex(ValueError, "licence file is missing"):
                verify_asset(glb, licence)


if __name__ == "__main__":
    unittest.main()
