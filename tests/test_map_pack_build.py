import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import map_pack_build


class MapPackBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.map_root = self.root / "assets" / "world" / "dhaka_tiles"
        self.map_root.mkdir(parents=True)
        self.preset = self.root / "export_presets.cfg"
        self.preset.write_text(
            '[preset.0]\n'
            'name="Android"\n'
            'platform="Android"\n'
            'export_filter="all_resources"\n'
            'include_filter="*.geojson,*.photo_bytes"\n'
            'exclude_filter=""\n'
            'export_path="./build/world.apk"\n'
            '\n[preset.0.options]\n'
            'package/unique_name="com.example.test"\n'
            'permissions/internet=false\n',
            encoding="utf-8",
        )
        tiles = []
        for index in range(60):
            tile_id = f"tile_{index:02d}"
            tile_dir = self.map_root / tile_id
            tile_dir.mkdir()
            glb = f"{tile_id}/Dhaka_Explorable_Map.glb"
            geojson = f"{tile_id}/roads.geojson"
            (self.map_root / glb).write_bytes(b"glb")
            (self.map_root / geojson).write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
            (tile_dir / "map_manifest.json").write_text("{}", encoding="utf-8")
            tiles.append({"tile_id": tile_id, "glb": glb, "geojson": geojson})
        manifest = {
            "build_stage": "shariatpur_review",
            "administrative_boundary": {"name": "Shariatpur"},
            "tile_count_total": 60,
            "tiles": tiles,
            "game_origin_lat_lon": [23.2, 90.4],
        }
        (self.map_root / "map_tiles_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.map_root / "real_world_navigation_index.json").write_text(
            json.dumps({"counts": {"named_roads": 1, "named_places": 1}}), encoding="utf-8"
        )
        self.old = (map_pack_build.ROOT, map_pack_build.MAP_ROOT, map_pack_build.PRESET_PATH)
        map_pack_build.ROOT = self.root
        map_pack_build.MAP_ROOT = self.map_root
        map_pack_build.PRESET_PATH = self.preset

    def tearDown(self):
        map_pack_build.ROOT, map_pack_build.MAP_ROOT, map_pack_build.PRESET_PATH = self.old
        self.temp.cleanup()

    def test_pack_preset_selects_all_tiles_and_required_data_without_changing_base(self):
        map_pack_build.configure_pack_preset()
        text = self.preset.read_text(encoding="utf-8")
        self.assertIn('name="Project A-Square Map Pack"', text)
        self.assertIn('platform="Android"', text)
        self.assertIn('export_filter="resources"', text)
        self.assertIn('res://assets/world/dhaka_tiles/tile_00/Dhaka_Explorable_Map.glb', text)
        self.assertIn('res://assets/world/dhaka_tiles/tile_59/Dhaka_Explorable_Map.glb', text)
        self.assertIn("real_world_navigation_index.json", text)
        self.assertIn("tile_37/roads.geojson", text)
        self.assertIn('export_filter="all_resources"', text)
        self.assertIn('include_filter="*.geojson,*.photo_bytes"', text)

    def test_core_export_removes_map_source_filters_and_adds_internet_permission(self):
        map_pack_build.configure_pack_preset()
        map_pack_build.prepare_core_export()
        text = self.preset.read_text(encoding="utf-8")
        preset0 = text.split("[preset.1]", 1)[0]
        self.assertIn('include_filter="assets/world/external_map_pack_required.flag"', preset0)
        self.assertIn('exclude_filter="assets/world/dhaka_tiles/**,.godot/imported/Dhaka_Explorable_Map.glb-*,build/**"', preset0)
        options = preset0.split("[preset.0.options]", 1)[1]
        self.assertIn("permissions/internet=true", options)
        preset1 = text.split("[preset.1]", 1)[1]
        self.assertIn('include_filter=', preset1)
        self.assertIn('exclude_filter=""', preset1)

    def test_metadata_splits_large_pack_under_release_limit_and_preserves_exact_bytes(self):
        pack = self.root / "Project-A-Square-Shariatpur-Map.pck"
        payload = bytes(range(251)) * 3
        pack.write_bytes(payload)
        output = self.root / "Project-A-Square-Shariatpur-Map.json"
        map_pack_build.write_metadata(
            pack,
            output,
            "shariatpur-review-candidate",
            max_part_bytes=200,
        )
        metadata = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(metadata["asset_filename"], pack.name)
        self.assertEqual(metadata["size_bytes"], len(payload))
        self.assertEqual(metadata["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(metadata["tile_count"], 60)
        self.assertEqual(metadata["part_count"], 4)
        reconstructed = bytearray()
        for index, part in enumerate(metadata["parts"], start=1):
            self.assertEqual(part["asset_filename"], f"{pack.name}.part{index:03d}")
            self.assertLess(part["size_bytes"], 2 * 1024 * 1024 * 1024)
            self.assertEqual(
                part["asset_url"],
                "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/"
                f"shariatpur-review-candidate/{pack.name}.part{index:03d}",
            )
            part_bytes = (self.root / part["asset_filename"]).read_bytes()
            self.assertEqual(len(part_bytes), part["size_bytes"])
            self.assertEqual(part["sha256"], hashlib.sha256(part_bytes).hexdigest())
            reconstructed.extend(part_bytes)
        self.assertEqual(bytes(reconstructed), payload)

    def test_metadata_rejects_a_part_limit_that_github_cannot_accept(self):
        pack = self.root / "Project-A-Square-Shariatpur-Map.pck"
        pack.write_bytes(b"fixture")
        output = self.root / "Project-A-Square-Shariatpur-Map.json"
        with self.assertRaises(SystemExit):
            map_pack_build.write_metadata(
                pack,
                output,
                "shariatpur-review-candidate",
                max_part_bytes=2 * 1024 * 1024 * 1024,
            )


if __name__ == "__main__":
    unittest.main()
