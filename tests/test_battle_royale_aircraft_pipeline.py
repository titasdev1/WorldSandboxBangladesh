from __future__ import annotations

import json
import struct
import unittest
from unittest.mock import patch
from urllib.error import URLError

from tools.fetch_battle_royale_aircraft import fetch_bytes, parse_glb


def make_glb(node_names):
    document = {
        "asset": {"version": "2.0", "generator": "Project A-Square test fixture"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(node_names)))}],
        "nodes": [{"name": name} for name in node_names],
        "meshes": [{"name": "CargoPlaneMesh", "primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [{"count": 3, "type": "VEC3", "componentType": 5126}],
        "materials": [{"name": "Paint"}],
        "images": [],
    }
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((4 - len(payload) % 4) % 4)
    chunk = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    total = 12 + len(chunk)
    return struct.pack("<4sII", b"glTF", 2, total) + chunk


class BattleRoyaleAircraftPipelineTests(unittest.TestCase):
    def test_parses_glb_and_detects_the_authored_cargo_parts(self):
        data = make_glb([
            "cargo-plane_cargo_ramp",
            "cargo-plane_cargo_door",
            "propeller_front_left",
            "propeller_front_right",
            "wheel_nose_left",
        ])
        report = parse_glb(data)
        self.assertEqual(report["node_count"], 5)
        self.assertEqual(report["mesh_count"], 1)
        self.assertTrue(report["has_ramp"])
        self.assertTrue(report["has_cargo_door"])
        self.assertEqual(report["propeller_nodes"], 2)
        self.assertEqual(report["wheel_nodes"], 1)

    def test_rejects_bad_magic_or_length(self):
        valid = make_glb(["cargo-plane_cargo_ramp"])
        with self.assertRaisesRegex(ValueError, "header"):
            parse_glb(b"BAD!" + valid[4:])
        with self.assertRaisesRegex(ValueError, "header"):
            parse_glb(valid[:-1])

    def test_fetcher_refuses_non_official_hosts_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "official Grab3D HTTPS host"):
            fetch_bytes("https://example.com/plane.glb", 1024)

    def test_fetcher_fails_closed_on_oversized_payload(self):
        class FakeResponse:
            status = 200
            headers = {"Content-Type": "application/octet-stream"}

            def geturl(self):
                return "https://grab3d.com/dl/cargo-plane/test.glb"

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _size=-1):
                return b"x" * 1025

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(ValueError, "safety cap"):
                fetch_bytes("https://grab3d.com/dl/cargo-plane/test.glb", 1024)

    def test_medium_stage_requires_a_full_and_light_aircraft_lod(self):
        from tools.verify_medium_stage_assets import REQUIRED
        self.assertEqual(REQUIRED["battle_royale_aircraft"], 2)


if __name__ == "__main__":
    unittest.main()
