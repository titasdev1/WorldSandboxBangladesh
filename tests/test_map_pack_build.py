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
        self.assertIn('exclude_filter="assets/world/dhaka_tiles/**,.godot/imported/Dhaka_Explorable_Map.glb-*"', preset0)
        options = preset0.split("[preset.0.options]", 1)[1]
        self.assertIn("permissions/internet=true", options)
        preset1 = text.split("[preset.1]", 1)[1]
        self.assertIn('include_filter=', preset1)
        self.assertIn('exclude_filter=""', preset1)

    def test_metadata_contains_actual_pack_size_checksum_and_download_name(self):
        pack = self.root / "Project-A-Square-Shariatpur-Map.pck"
        payload = b"full resolution PCK fixture"
        pack.write_bytes(payload)
        output = self.root / "Project-A-Square-Shariatpur-Map.json"
        map_pack_build.write_metadata(pack, output, "shariatpur-review-candidate")
        metadata = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(metadata["asset_filename"], pack.name)
        self.assertEqual(metadata["size_bytes"], len(payload))
        self.assertEqual(metadata["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(metadata["tile_count"], 60)
        self.assertEqual(
            metadata["asset_url"],
            "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/Project-A-Square-Shariatpur-Map.pck",
        )


if __name__ == "__main__":
    unittest.main()
