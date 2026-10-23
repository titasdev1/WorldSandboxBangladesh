import hashlib
import os
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from shapely.geometry import Polygon, box, shape
from tools.map_pipeline.prepare_dhaka_division_pbf import FEATURE_KEYS, build_tag_filter_command
from tools.map_pipeline.build_dhaka_division import (
    _clip_elements, _source_geometry, _replace_ground_with_boundary,
    order_tiles_shariatpur_first, select_tile_batch, effective_batch_limit, stage_gate_reached,
    build_boundary_for_stage, SHARIATPUR_PRIORITY_LAT_LON, has_feature,
    boundary_attribution_for_stage, tile_status_from_counts, pipeline_commit_sha,
    validate_shariatpur_release_approval, add_curated_manasha_footprint, add_curated_heritage_photo_footprints,
)
from tools.map_pipeline.build_dhaka_map import build_map




class OvertureBuildingSupplementTests(unittest.TestCase):
    def _feature(self, feature_id, coordinates, properties=None):
        return {
            "type": "Feature", "id": feature_id,
            "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            "properties": {"id": feature_id, **(properties or {})},
        }

    def test_overture_geojson_retains_names_height_floor_source_and_temple_class(self):
        from tools.map_pipeline.overture_buildings import OVERTURE_SOURCE_DATASET, load_overture_buildings
        coords = [
            [90.3000, 23.2000], [90.3002, 23.2000],
            [90.3002, 23.2002], [90.3000, 23.2002], [90.3000, 23.2000],
        ]
        document = {
            "type": "FeatureCollection",
            "features": [self._feature("building-temple-1", coords, {
                "class": "temple", "subtype": "religious", "height": 8.4, "num_floors": 2,
                "facade_color": "#d0b080", "roof_color": "#a05040",
                "names": {"primary": "Test Temple"},
                "sources": [{"dataset": "Microsoft", "record_id": "fixture-1"}],
            })],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "overture.geojson"
            path.write_text(json.dumps(document), encoding="utf-8")
            first = load_overture_buildings(path, (23.19, 90.29, 23.21, 90.31))
            second = load_overture_buildings(path, (23.19, 90.29, 23.21, 90.31))
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["id"], second[0]["id"])
        tags = first[0]["tags"]
        self.assertEqual(tags["building"], "temple")
        self.assertEqual(tags["name"], "Test Temple")
        self.assertEqual(tags["source_dataset"], OVERTURE_SOURCE_DATASET)
        self.assertEqual(tags["overture:height"], "8.4")
        self.assertEqual(tags["overture:num_floors"], "2")
        self.assertEqual(tags["overture_source_datasets"], "Microsoft")
        self.assertEqual(tags["building:colour"], "#d0b080")

    def test_deduplication_prefers_osm_overlapping_geometry_but_keeps_gap_fill(self):
        from tools.map_pipeline.overture_buildings import OVERTURE_SOURCE_DATASET, deduplicate_overture_overlaps
        shared = [
            {"lat": 23.2, "lon": 90.3}, {"lat": 23.2, "lon": 90.3002},
            {"lat": 23.2002, "lon": 90.3002}, {"lat": 23.2002, "lon": 90.3},
            {"lat": 23.2, "lon": 90.3},
        ]
        other = [
            {"lat": 23.2, "lon": 90.3005}, {"lat": 23.2, "lon": 90.3007},
            {"lat": 23.2002, "lon": 90.3007}, {"lat": 23.2002, "lon": 90.3005},
            {"lat": 23.2, "lon": 90.3005},
        ]
        osm = {"type": "way", "id": 1, "tags": {"building": "yes"}, "geometry": shared}
        duplicate = {
            "type": "way", "id": 2,
            "tags": {"building": "yes", "source_dataset": OVERTURE_SOURCE_DATASET, "overture_id": "dup"},
            "geometry": shared,
        }
        supplement = {
            "type": "way", "id": 3,
            "tags": {"building": "house", "source_dataset": OVERTURE_SOURCE_DATASET, "overture_id": "gap"},
            "geometry": other,
        }
        retained, suppressed = deduplicate_overture_overlaps([osm, duplicate, supplement])
        self.assertEqual(suppressed, 1)
        self.assertEqual([item["id"] for item in retained], [1, 3])

    def test_overture_height_and_floor_provenance_are_not_mislabelled_as_osm(self):
        from tools.map_pipeline.build_dhaka_map import building_height, building_height_source, building_floors_source
        tags = {
            "building": "temple",
            "source_dataset": "Overture Maps buildings theme",
            "overture:height": "8.4",
            "overture:num_floors": "2",
        }
        height, inferred = building_height(tags, 123)
        self.assertAlmostEqual(height, 8.4)
        self.assertFalse(inferred)
        self.assertEqual(building_height_source(tags), "OVERTURE_HEIGHT_TAG")
        self.assertEqual(building_floors_source(tags), "OVERTURE_NUM_FLOORS")


class RuntimeMapIntegrationWiringTests(unittest.TestCase):
    """Guard the real-map runtime path, not just the standalone map exporter."""

    ROOT = Path(__file__).resolve().parents[1]

    def test_selected_map_identity_and_nearby_place_api_are_exposed(self):
        loader = (self.ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
        minimap = (self.ROOT / "district_map_display.gd").read_text(encoding="utf-8")
        hud = (self.ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("func get_map_display_name() -> String:", loader)
        self.assertIn("func get_nearest_named_place(", loader)
        self.assertIn('loader.call("get_nearest_named_place"', minimap)
        self.assertIn('title_loader.call("get_map_display_name")', minimap)
        self.assertIn('map_loader.call("get_map_display_name")', hud)

    def test_real_map_mission_stops_route_on_the_offline_road_graph(self):
        loader = (self.ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
        missions = (self.ROOT / "systems" / "mission_factory.gd").read_text(encoding="utf-8")
        hud = (self.ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("func navigate_to_world_position(", loader)
        self.assertIn("func get_nearby_road_points(", loader)
        self.assertIn('loader.call("navigate_to_world_position", active_target.global_position, player)', missions)
        self.assertIn("_update_mission_navigation()", missions)
        self.assertIn('mission.text += "\\nROAD ROUTE: " + route_instruction', hud)
        self.assertIn('loader.call("clear_navigation_route")', missions)

    def test_real_map_missions_do_not_invent_off_road_fallback_targets(self):
        missions = (self.ROOT / "systems" / "mission_factory.gd").read_text(encoding="utf-8")
        guard = 'if bool(world.get("real_dhaka_loaded")) and positions.size() < count:\n        return positions'
        self.assertIn(guard, missions)
        self.assertIn("Not enough mapped road nodes are loaded nearby yet", missions)


    def test_turn_guidance_recalculates_as_player_progresses(self):
        loader = (self.ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
        self.assertIn("NAVIGATION_RECALCULATE_DISTANCE_M := 28.0", loader)
        self.assertIn("func _refresh_navigation_if_needed(", loader)
        self.assertIn("_navigation_target_active", loader)
        self.assertIn("navigate_to_world_position(destination, player, true)", loader)
        self.assertIn('if not bool(result.get("ok", false)):', loader)
        self.assertIn("_navigation_recalc_clock = 0.0", loader)
        self.assertIn("leave the last valid route visible", loader)

    def test_real_map_does_not_create_the_old_180m_raised_ground_platform(self):
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        factory = (self.ROOT / "systems" / "game_factory.gd").read_text(encoding="utf-8")
        environment_start = world.index("func build_environment():")
        city_start = world.index("func build_city():", environment_start)
        environment_code = world[environment_start:city_start]
        self.assertNotIn('box(Vector3(0, -0.5, 0), Vector3(180, 1, 180), Color("#58714b"), true, "ground")', environment_code)
        self.assertIn("func _expand_ground() -> void:", factory)
        self.assertIn('mesh_box(Vector3(0, -0.04, 0), Vector3(CITY_RADIUS * 2.0, 0.08, CITY_RADIUS * 2.0), Color("#526b49"), true)', factory)
        bootstrap_start = factory.index("func _bootstrap()")
        real_map_guard = factory.index('if bool(world.get("real_dhaka_loaded")):', bootstrap_start)
        ground_call = factory.index("_expand_ground()", bootstrap_start)
        self.assertLess(real_map_guard, ground_call)

    def test_real_map_initial_player_spawn_uses_mapped_roads(self):
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        spawn_start = world.index("func spawn_player():")
        spawn_end = world.index("func spawn_traffic():", spawn_start)
        spawn = world[spawn_start:spawn_end]
        self.assertIn("var initial_spawn := Vector3(0, 0, -12)", spawn)
        self.assertIn("if real_dhaka_loaded and is_instance_valid(real_dhaka_loader):", spawn)
        self.assertIn("initial_spawn = _nearest_mapped_respawn_position(initial_spawn)", spawn)
        self.assertIn("player.position = initial_spawn", spawn)

    def test_real_map_respawn_uses_mapped_roads_not_starter_city_origin(self):
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        respawn_start = world.index("func respawn_player():")
        helper_start = world.index("func _nearest_mapped_respawn_position(", respawn_start)
        interaction_start = world.index("func try_vehicle_interaction():", helper_start)
        respawn_code = world[respawn_start:interaction_start]
        self.assertIn("player.global_position = _nearest_mapped_respawn_position(player.global_position)", respawn_code)
        self.assertIn('real_dhaka_loader.call("get_nearby_road_points"', respawn_code)
        self.assertIn("best_side * 3.0", respawn_code)
        self.assertIn("if real_dhaka_loaded and is_instance_valid(real_dhaka_loader):", respawn_code)
        self.assertIn("player.position = Vector3(0, 0, -12)", respawn_code)
        self.assertIn("else:", respawn_code)

    def test_real_map_deshi_job_board_is_placed_from_mapped_roads(self):
        missions = (self.ROOT / "systems" / "mission_factory.gd").read_text(encoding="utf-8")
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        hub_start = missions.index("func _create_hub()")
        hub_end = missions.index("func _on_hub_entered", hub_start)
        hub_code = missions[hub_start:hub_end]
        self.assertIn('if bool(world.get("real_dhaka_loaded")):', hub_code)
        self.assertIn('loader.call("get_road_routes")', hub_code)
        self.assertIn("hub_position = best_point + sidewalk_side * 8.0", hub_code)
        self.assertIn("hub_created = true", hub_code)
        self.assertIn('if not hub_created and is_instance_valid(world) and bool(world.get("real_dhaka_loaded")):', missions)
        self.assertIn("if real_dhaka_loaded and mapped_routes.is_empty():", world)
        self.assertIn('npc.add_to_group("mapped_road_npc")', world)
        self.assertIn('get_tree().get_nodes_in_group("mapped_road_npc").size()', world)

    def test_player_crouch_preserves_normalized_humanoid_base_scale(self):
        player = (self.ROOT / "player.gd").read_text(encoding="utf-8")
        visual = (self.ROOT / "character_visual.gd").read_text(encoding="utf-8")
        self.assertIn("const HUMANOID_BASE_SCALE := Vector3(0.90, 0.90, 0.90)", player)
        self.assertIn("visual.scale = HUMANOID_BASE_SCALE * Vector3(1.0, 0.72, 1.0) if _is_crouched else HUMANOID_BASE_SCALE", player)
        self.assertIn("scale = Vector3(0.90, 0.90, 0.90)", visual)

    def test_real_map_player_interaction_never_uses_starter_city_money_coordinates(self):
        player = (self.ROOT / "player.gd").read_text(encoding="utf-8")
        interact_start = player.index("func interact():")
        interact_end = player.index("func take_damage(", interact_start)
        code = player[interact_start:interact_end]
        map_guard = code.index('if not bool(world.get("real_dhaka_loaded")):')
        starter_bargain = code.index("Vector3(42, 0, 42)")
        starter_reward = code.index("Vector3(30, 0, -30)")
        self.assertLess(map_guard, starter_bargain)
        self.assertLess(map_guard, starter_reward)
        self.assertIn("else:\n  world.try_vehicle_interaction()", code)

    def test_real_world_map_suppresses_fictional_factory_overlays(self):
        factories = [
            ("systems/game_factory.gd", "_expand_ground()", "real_map_mode_fictional_grid_suppressed"),
            ("systems/gameplay_factory.gd", "_create_job_hubs()", "real_map_mode_fixed_markers_suppressed"),
            ("systems/vehicle_gameplay_factory.gd", "_add_vehicle_depots()", "real_map_mode_fixed_markers_suppressed"),
            ("systems/population_factory.gd", "_spawn_outer_traffic()", "real_map_mode_mapped_population_only"),
        ]
        for relative_path, generator_call, expected_status in factories:
            with self.subTest(factory=relative_path):
                source = (self.ROOT / relative_path).read_text(encoding="utf-8")
                bootstrap_start = source.index("func _bootstrap()")
                map_guard = source.index('if bool(world.get("real_dhaka_loaded")):', bootstrap_start)
                fictional_generator = source.index(generator_call, bootstrap_start)
                self.assertLess(map_guard, fictional_generator)
                self.assertIn('set_meta("real_map_overlay_suppressed", true)', source)
                self.assertIn(expected_status, source)

        # Real traffic and normal NPCs remain in world.gd's mapped-road spawn path.
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        self.assertIn("get_vehicle_route_records()", world)
        self.assertIn("_spawn_mapped_traffic_vehicle(mapped_routes)", world)
        self.assertIn("get_road_routes()", world)


    def _make_minimal_shariatpur_apk(self, apk_path: Path, photo_sha_override: str | None = None) -> None:
        image_bytes = b"licensed-photo-bytes-for-apk-integration-test"
        import hashlib
        image_sha = photo_sha_override or hashlib.sha256(image_bytes).hexdigest()
        tile_ids = [f"tile_{i:02d}" for i in range(60)]
        photo_tile = tile_ids[0]
        relative_photo_path = "landmark_reference_photos/mosque-interior.jpg"
        match = {
            "osm_id": 12345,
            "building_name": "বুড়িরহাট ঐতিহাসিক জামে মসজিদ",
            "image_id": "burirhat_mosque_interior_01",
            "tile_id": photo_tile,
            "asset_relative_path": relative_photo_path,
            "sha256": image_sha,
            "source_page": "https://commons.wikimedia.org/wiki/File:Bibir_Hat_Mosque_01.jpg",
            "author": "Radman Siddiki",
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY-SA 4.0",
            "use": "INTERIOR_REFERENCE_ONLY",
            "visual_identity_verified": True,
        }
        exterior_matches = [
            {
                "osm_id": 620001,
                "building_name": "Manasha Temple, Shariatpur",
                "image_id": "manasha_temple_back_view_01",
                "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
                "author": "Shuvajit BD",
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Photo: Shuvajit BD / Wikimedia Commons, CC BY-SA 4.0",
            },
            {
                "osm_id": 620002,
                "building_name": "Rudrakar Moth",
                "image_id": "rudrakar_moth_35",
                "source_page": "https://commons.wikimedia.org/wiki/File:Rudrakar_Moth_35.jpg",
                "author": "Radman Siddiki",
                "license": "CC BY 4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": "Photo: Radman Siddiki / Wikimedia Commons, CC BY 4.0",
            },
            {
                "osm_id": 620003,
                "building_name": "Kartikpur Jomidar Bari",
                "image_id": "kartikpur_jomidar_bari_123242",
                "source_page": "https://commons.wikimedia.org/wiki/File:Kartikpur_Jomidar_Bari_(123242).jpg",
                "author": "Moheen Reeyad",
                "license": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": "Photo: Moheen Reeyad / Wikimedia Commons, CC BY-SA 4.0",
            },
        ]
        manifest = {
            "build_stage": "shariatpur_review",
            "complete_district_map": True,
            "tile_count_with_geometry": 60,
            "tile_count_total": 60,
            "tiles": [{"tile_id": item} for item in tile_ids],
            "interior_reference_photo_matches": [match],
            "interior_reference_photos_embedded": 1,
            "licensed_facade_photo_matches": exterior_matches,
            "licensed_facade_photo_panels_embedded": len(exterior_matches),
            "approved_facade_photo_ids_required": [item["image_id"] for item in exterior_matches],
            "approved_facade_photo_ids_embedded": [item["image_id"] for item in exterior_matches],
            "approved_facade_photo_ids_missing": [],
        }
        navigation = {"counts": {
            "named_places": 12,
            "named_roads": 14,
            "buildings_with_source_floor_count": 22,
            "buildings_with_independently_verified_floor_count": 0,
        }}
        map_root = "assets/assets/world/dhaka_tiles/"
        with zipfile.ZipFile(apk_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(map_root + "map_tiles_manifest.json", json.dumps(manifest))
            archive.writestr(map_root + "real_world_navigation_index.json", json.dumps(navigation))
            for tile_id in tile_ids:
                tile_matches = exterior_matches if tile_id == photo_tile else []
                tile_panel_count = len(tile_matches)
                archive.writestr(
                    map_root + tile_id + "/map_manifest.json",
                    json.dumps({
                        "feature_counts": {"licensed_facade_photo_panels": tile_panel_count},
                        "licensed_facade_photo_matches": tile_matches,
                    }),
                )
                archive.writestr(
                    map_root + tile_id + "/Dhaka_Explorable_Map.glb.import",
                    f'[remap]\nimporter="scene"\npath="res://.godot/imported/Dhaka_Explorable_Map.glb-{tile_id}.scn"\n',
                )
                scene_payload = "scene"
                if tile_id == photo_tile:
                    scene_payload += "|" + "|".join(
                        f"licensed_facade_photo_{item['image_id']}_{item['osm_id']}"
                        for item in exterior_matches
                    )
                archive.writestr("assets/.godot/imported/Dhaka_Explorable_Map.glb-" + tile_id + ".scn", scene_payload)
            source_glb = apk_path.parent / "assets" / "world" / "dhaka_tiles" / photo_tile / "Dhaka_Explorable_Map.glb"
            source_glb.parent.mkdir(parents=True, exist_ok=True)
            source_glb.write_bytes(ApkGlbFacadeEmbeddedAssetTests._make_glb([
                f"licensed_facade_photo_{item['image_id']}_{item['osm_id']}"
                for item in exterior_matches
            ]))
            seed = [{
                "osm_id": 12345,
                "interior_reference_photo": {
                    "image_id": match["image_id"],
                    "asset_relative_path": relative_photo_path,
                    "use": "INTERIOR_REFERENCE_ONLY",
                },
            }]
            archive.writestr(map_root + photo_tile + "/AI_Interior_Seeds.json", json.dumps(seed))
            archive.writestr(map_root + photo_tile + "/" + relative_photo_path, image_bytes)
            for pack_manifest in (
                "assets/external_content/kenney_car_kit/asset_manifest.json",
                "assets/external_content/kenney_city_kit_commercial/asset_manifest.json",
                "assets/external_content/kenney_city_kit_industrial/asset_manifest.json",
                "assets/external_content/kenney_city_kit_suburban/asset_manifest.json",
                "assets/external_content/polyhaven_pbr/asset_manifest.json",
            ):
                archive.writestr(pack_manifest, "{}")
            archive.writestr(
                "assets/external_content/quaternius_hero/asset_manifest.json",
                json.dumps({"available": False, "license": "CC0-1.0", "animation_count": 0}),
            )

    def test_android_apk_verifier_confirms_interior_photo_bytes_and_seed_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apk_path = root / "candidate.apk"
            self._make_minimal_shariatpur_apk(apk_path)
            verifier = self.ROOT / "tools" / "verify_apk_contents.py"
            result = subprocess.run(
                [sys.executable, str(verifier), "--apk", str(apk_path), "--map-package", "shariatpur_review"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + "\n" + result.stderr)
            self.assertIn("APK content integration: PASS", result.stdout)
            self.assertIn("Interior reference photo assets SHA-256 verified and linked to runtime seeds: 1/1", result.stdout)
            with zipfile.ZipFile(apk_path, "r") as archive:
                self.assertFalse(any(name.endswith("/Dhaka_Explorable_Map.glb") for name in archive.namelist()))
            self.assertIn("Licensed exterior façade panels validated in source GLBs and mapped into APK scenes: 3", result.stdout)

    def test_android_apk_verifier_confirms_authored_hero_source_checksum_and_imported_scene(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apk_path = root / "candidate.apk"
            self._make_minimal_shariatpur_apk(apk_path)
            with zipfile.ZipFile(apk_path, "r") as archive:
                members = {name: archive.read(name) for name in archive.namelist()}

            hero_source_path = "external_content/quaternius_hero/Project_A_Square_Hero.glb"
            hero_apk_path = "assets/" + hero_source_path
            hero_bytes = b"glTF" + b"Project-A-Square-CC0-rigged-hero-test"
            source_file = root / hero_source_path
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_bytes(hero_bytes)

            hero_manifest_path = "assets/external_content/quaternius_hero/asset_manifest.json"
            remap_path = hero_apk_path + ".import"
            members[remap_path] = (
                'path="res://.godot/imported/Project_A_Square_Hero.glb-test.scn"\n'
            ).encode("utf-8")
            members["assets/.godot/imported/Project_A_Square_Hero.glb-test.scn"] = b"imported-scene"
            members[hero_manifest_path] = json.dumps({
                "available": True,
                "license": "CC0-1.0",
                "hero_glb_sha256": hashlib.sha256(hero_bytes).hexdigest(),
                "animation_count": 86,
            }).encode("utf-8")

            with zipfile.ZipFile(apk_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in members.items():
                    archive.writestr(name, data)

            verifier = self.ROOT / "tools" / "verify_apk_contents.py"
            result = subprocess.run(
                [sys.executable, str(verifier), "--apk", str(apk_path), "--map-package", "shariatpur_review"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + "\\n" + result.stderr)
            self.assertIn("Authored CC0 hero packaged/imported: yes", result.stdout)
            self.assertIn("Authored hero imported Godot scenes: 1", result.stdout)
            self.assertIn("Authored hero animation clips: 86", result.stdout)
            with zipfile.ZipFile(apk_path, "r") as archive:
                names = set(archive.namelist())
            self.assertNotIn(hero_apk_path, names, "Godot may omit the original imported source GLB while shipping its scene and remap")
            self.assertIn(remap_path, names)
            self.assertIn("assets/.godot/imported/Project_A_Square_Hero.glb-test.scn", names)


    def test_android_apk_verifier_rejects_wrong_interior_photo_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            apk_path = root / "candidate.apk"
            self._make_minimal_shariatpur_apk(apk_path, "0" * 64)
            verifier = self.ROOT / "tools" / "verify_apk_contents.py"
            result = subprocess.run(
                [sys.executable, str(verifier), "--apk", str(apk_path), "--map-package", "shariatpur_review"],
                cwd=root, capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("licensed interior photo checksum mismatch", result.stderr)

    def test_licensed_interior_reference_photo_flows_from_map_bake_to_android_runtime(self):
        map_builder = (self.ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
        map_merger = (self.ROOT / "tools" / "map_pipeline" / "merge_dhaka_division_batches.py").read_text(encoding="utf-8")
        interior = (self.ROOT / "systems" / "interior_factory.gd").read_text(encoding="utf-8")
        verifier = (self.ROOT / "tools" / "verify_apk_contents.py").read_text(encoding="utf-8")
        catalog = json.loads((self.ROOT / "tools" / "map_pipeline" / "shariatpur_facade_images.json").read_text(encoding="utf-8"))
        mosque = next(item for item in catalog["images"] if item["id"] == "bibir_hat_mosque_01")

        self.assertFalse(mosque["facade_eligible"])
        self.assertEqual(mosque["view_type"], "unverified")
        self.assertTrue(mosque["interior_reference_eligible"])
        self.assertEqual(mosque["interior_view_type"], "interior")
        self.assertEqual(mosque["interior_visual_qa"], "passed")
        self.assertIn("def load_interior_reference_catalog(", map_builder)
        self.assertIn("interior_reference_photo_matches", map_builder)
        self.assertIn('"sha256": hashlib.sha256(image_bytes).hexdigest()', map_builder)
        self.assertIn("interior_reference_photo_matches", map_merger)
        self.assertIn("Use restriction: INTERIOR REFERENCE ONLY", map_merger)
        self.assertIn("func _add_licensed_interior_photo_reference(", interior)
        self.assertIn("FileAccess.get_file_as_bytes(texture_path)", interior)
        self.assertIn("photo_image.load_jpg_from_buffer(photo_bytes)", interior)
        self.assertIn("ImageTexture.create_from_image(photo_image)", interior)
        export_preset = (self.ROOT / "export_presets.cfg").read_text(encoding="utf-8")
        self.assertIn('include_filter="*.photo_bytes"', export_preset)
        self.assertIn('photo_record.get("asset_relative_path", "")', interior)
        self.assertIn('panel.set_meta("use", "INTERIOR_REFERENCE_ONLY")', interior)
        self.assertIn('hashlib.sha256(photo_data).hexdigest()', verifier)
        self.assertIn("exact mapped building's runtime interior seed", verifier)
        self.assertNotIn("ResourceLoader.load(texture_path) as Texture2D", interior)

    def test_player_character_has_hero_detail_and_mobile_readable_camera_distance(self):
        visual = (self.ROOT / "character_visual.gd").read_text(encoding="utf-8")
        player = (self.ROOT / "player.gd").read_text(encoding="utf-8")
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")

        self.assertIn("@export var is_player_character := false", visual)
        self.assertIn("func _add_clothing_and_face_detail() -> void:", visual)
        for component in (
            "LeftEyeWhite", "RightEyeWhite", "NoseBridge", "Mouth", "LeftEar",
            "RightEar", "ChestPocket_%s", "ShirtFrontPlacket",
            "Finger_%d", "KneePanel", "ShoeSole", "ShoeLace_%d",
            "RadioBody", "WristWatch", "CargoPocket",
        ):
            self.assertIn(component, visual)
        self.assertIn("visual.is_player_character = true", world)
        self.assertIn("camera_distance := 4.8 if Input.is_action_pressed", player)
        self.assertIn("else 7.4", player)
        # Real building footprints stay at their mapped metric dimensions; improving
        # character detail must not scale the world or distort real map coordinates.
        map_builder = (self.ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
        self.assertIn("local_xy(", map_builder)
        self.assertIn("building_height(tags, osm_id, polygon.area)", map_builder)

    def test_mapped_interior_interaction_uses_the_baked_door_anchor(self):
        loader = (self.ROOT / "real_dhaka_tile_loader.gd").read_text(encoding="utf-8")
        map_builder = (self.ROOT / "tools" / "map_pipeline" / "build_dhaka_map.py").read_text(encoding="utf-8")
        self.assertIn("def facade_door_geometry(", map_builder)
        self.assertIn('"door_anchor_local_m": door_anchor_local_m', map_builder)
        self.assertIn('"door_outward_xy": door_outward_xy', map_builder)
        placement_start = loader.index("func _interior_anchor_placement(")
        placement_end = loader.index("func _add_walkable_collisions(", placement_start)
        placement = loader[placement_start:placement_end]
        self.assertIn('seed.get("door_anchor_local_m", [])', placement)
        self.assertIn('seed.get("door_outward_xy", [])', placement)
        self.assertIn("var approach_distance := 1.25", placement)
        self.assertIn('var footprint: Array = seed.get("footprint_local_m", [])', placement)
        # Previous packages still load via the explicit backward-compatible fallback.

    def test_hud_touch_buttons_do_not_send_their_drags_to_camera_look(self):
        player = (self.ROOT / "player.gd").read_text(encoding="utf-8")
        hud = (self.ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("func _unhandled_input(event):", player)
        self.assertIn("Let on-screen HUD controls consume their own touch gestures first.", player)
        self.assertIn("stick.set_script(load(\"res://virtual_stick.gd\"))", hud)
        self.assertIn('add_touch_button("FIRE"', hud)
        self.assertIn('add_touch_button("AIM"', hud)

    def test_main_story_requires_mapped_targets_and_routes_each_stage(self):
        world = (self.ROOT / "world.gd").read_text(encoding="utf-8")
        hud = (self.ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("real_mission_targets.size() >= 3", world)
        self.assertIn("refresh_active_world_navigation()", world)
        self.assertIn("func refresh_active_world_navigation() -> void:", world)
        self.assertIn('call("navigate_to_world_position", mission_target, player)', world)
        self.assertIn('mission_target = real_mission_targets[1] if real_dhaka_loaded else Vector3(-36, 0, -36)', world)
        self.assertIn('mission_target = real_mission_targets[2] if real_dhaka_loaded else Vector3(30, 0, -30)', world)
        self.assertIn("func _current_route_instruction() -> String:", hud)
        self.assertIn('mission.text += "\\nROAD ROUTE: " + route_instruction', hud)
        self.assertIn("STORY ROUTE LOADING", hud)

    def test_side_job_returns_navigation_to_main_story_after_finishing(self):
        missions = (self.ROOT / "systems" / "mission_factory.gd").read_text(encoding="utf-8")
        self.assertIn("_clear_mission_navigation()\n    if world.has_method(\"refresh_active_world_navigation\"):", missions)
        self.assertIn("world.refresh_active_world_navigation()", missions)


class ShariatpurReleaseGateTests(unittest.TestCase):
    def test_current_unapproved_shariatpur_package_blocks_division_expansion(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            approval = Path(temp) / "approval.json"
            approval.write_text(json.dumps({
                "status": "BLOCKED",
                "checks": {
                    "all_tiles_have_renderable_osm_features": False,
                    "all_building_floor_counts_independently_verified": False,
                    "licensed_facade_imagery_visual_review_complete": False,
                    "named_place_search_and_turn_navigation_qa_passed": False,
                    "physical_android_integration_and_performance_passed": False,
                },
            }), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "no later tiles will be built"):
                validate_shariatpur_release_approval(approval)

    def test_missing_approval_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            approval = Path(temp) / "missing.json"
            with self.assertRaisesRegex(RuntimeError, "approval evidence file is missing"):
                validate_shariatpur_release_approval(approval)

    def test_all_checks_need_documented_human_review_before_approval(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            approval = Path(temp) / "approval.json"
            approval.write_text(json.dumps({
                "status": "APPROVED",
                "reviewed_at": "2026-10-19",
                "reviewer": "QA reviewer",
                "review_evidence_url": "https://example.org/shariatpur-qa",
                "checks": {
                    "all_tiles_have_renderable_osm_features": True,
                    "all_building_floor_counts_independently_verified": True,
                    "licensed_facade_imagery_visual_review_complete": True,
                    "named_place_search_and_turn_navigation_qa_passed": True,
                    "physical_android_integration_and_performance_passed": True,
                },
            }), encoding="utf-8")
            result = validate_shariatpur_release_approval(approval)
            self.assertEqual(result["status"], "APPROVED")


class DhakaDivisionPipelineTests(unittest.TestCase):
    def test_pinned_pipeline_commit_is_available_for_batch_manifests(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"WSB_PIPELINE_COMMIT_SHA": "fixture-pipeline-revision"}):
            self.assertEqual(pipeline_commit_sha(), "fixture-pipeline-revision")

    def test_cached_pbf_filter_covers_every_builder_feature_key(self):
        from tools.map_pipeline.build_dhaka_division import INTERESTING_KEYS
        self.assertEqual(set(FEATURE_KEYS), INTERESTING_KEYS)
        self.assertIn("building", FEATURE_KEYS)
        self.assertIn("highway", FEATURE_KEYS)
        self.assertIn("natural", FEATURE_KEYS)
        self.assertIn("waterway", FEATURE_KEYS)
        self.assertIn("power", FEATURE_KEYS)

    def test_filtered_pbf_command_preserves_referenced_nodes_and_all_feature_keys(self):
        command = build_tag_filter_command("osmium", Path("regional.osm.pbf"), Path("filtered.osm.pbf"))
        self.assertEqual(command[:3], ["osmium", "tags-filter", "regional.osm.pbf"])
        selectors = command[3:3 + len(FEATURE_KEYS)]
        self.assertEqual(selectors, [f"nwr/{key}" for key in FEATURE_KEYS])
        self.assertNotIn("-R", command)
        self.assertEqual(command[-3:], ["--overwrite", "-o", "filtered.osm.pbf"])

    def test_osm_extract_preserves_entrance_and_building_part_tags(self):
        from tools.map_pipeline.build_dhaka_division import INTERESTING_KEYS
        self.assertEqual(set(FEATURE_KEYS), INTERESTING_KEYS)
        self.assertIn("entrance", FEATURE_KEYS)
        self.assertIn("door", FEATURE_KEYS)
        self.assertIn("building:part", FEATURE_KEYS)
        command = build_tag_filter_command("osmium", Path("region.osm.pbf"), Path("filtered.osm.pbf"))
        selectors = command[3:3 + len(FEATURE_KEYS)]
        self.assertIn("nwr/entrance", selectors)
        self.assertIn("nwr/door", selectors)
        self.assertIn("nwr/building:part", selectors)

    def test_osm_extract_includes_trees_power_grid_and_street_lamps(self):
        self.assertTrue(has_feature({"natural": "tree"}))
        self.assertTrue(has_feature({"power": "pole"}))
        self.assertTrue(has_feature({"power": "tower"}))
        self.assertTrue(has_feature({"highway": "street_lamp"}))
        self.assertTrue(has_feature({"man_made": "utility_pole"}))

    def test_shariatpur_is_first_but_all_division_tiles_remain_in_order(self):
        tiles = [
            (23.80, 90.40, 23.85, 90.45),  # central Dhaka
            (23.20, 90.325, 23.25, 90.375),  # Shariatpur town
            (24.00, 90.50, 24.05, 90.55),  # farther division tile
        ]
        shariatpur_boundary = box(90.30, 23.20, 90.38, 23.27)
        ordered = order_tiles_shariatpur_first(tiles, shariatpur_boundary)
        self.assertEqual(ordered[0], tiles[1])
        self.assertEqual(set(ordered), set(tiles))
        self.assertEqual(len(select_tile_batch(ordered, 0, 2)), 2)
        self.assertEqual(select_tile_batch(ordered, 2, 2), [tiles[2]])
        self.assertEqual(SHARIATPUR_PRIORITY_LAT_LON, (23.2167, 90.3500))

    def test_shariatpur_review_batch_is_capped_at_district_boundary(self):
        ordered = [
            (23.10, 90.10, 23.15, 90.15),
            (23.15, 90.10, 23.20, 90.15),
            (23.20, 90.10, 23.25, 90.15),
            (23.25, 90.10, 23.30, 90.15),
            (23.30, 90.10, 23.35, 90.15),
        ]
        district_count = 4
        offset = 2
        limit = effective_batch_limit(offset, 3, district_count, "shariatpur_review")
        self.assertEqual(limit, 2)
        self.assertEqual(select_tile_batch(ordered, offset, limit), ordered[2:4])
        self.assertEqual(offset + len(select_tile_batch(ordered, offset, limit)), district_count)
        self.assertEqual(effective_batch_limit(2, 3, district_count, "full_division"), 3)
        self.assertFalse(stage_gate_reached(3, district_count, "shariatpur_review"))
        self.assertTrue(stage_gate_reached(4, district_count, "shariatpur_review"))
        self.assertFalse(stage_gate_reached(4, district_count, "full_division"))
        with self.assertRaises(ValueError):
            effective_batch_limit(-1, 3, district_count, "shariatpur_review")

    def test_review_stage_uses_shariatpur_boundary_not_division_boundary(self):
        division = box(89.0, 22.0, 92.0, 25.0)
        district = box(90.30, 23.20, 90.38, 23.27)
        self.assertIs(build_boundary_for_stage("shariatpur_review", division, district), district)
        self.assertIs(build_boundary_for_stage("full_division", division, district), division)
        with self.assertRaises(ValueError):
            build_boundary_for_stage("unknown", division, district)

    def test_ground_only_tiles_are_distinguished_from_mapped_tiles(self):
        self.assertEqual(tile_status_from_counts({"building_footprints": 1}), "BAKED_FROM_OSM")
        self.assertEqual(tile_status_from_counts({"water_polygons": 2}), "BAKED_FROM_OSM")
        self.assertEqual(tile_status_from_counts({"landuse_areas": 1}), "BAKED_FROM_OSM")
        self.assertEqual(tile_status_from_counts({}), "GROUND_ONLY_NO_RENDERABLE_FEATURES")
        self.assertEqual(tile_status_from_counts({"building_footprints": 0, "road_ways": 0}), "GROUND_ONLY_NO_RENDERABLE_FEATURES")

    def test_boundary_attribution_matches_selected_administrative_level(self):
        shariatpur = boundary_attribution_for_stage("shariatpur_review")
        division = boundary_attribution_for_stage("full_division")
        self.assertIn("Shariatpur District", shariatpur)
        self.assertIn("BGD ADM2", shariatpur)
        self.assertIn("Dhaka Division", division)
        self.assertIn("BGD ADM1", division)
        with self.assertRaises(ValueError):
            boundary_attribution_for_stage("unknown")

    def test_tile_batches_reject_invalid_limits(self):
        with self.assertRaises(ValueError):
            select_tile_batch([], -1, 2)
        with self.assertRaises(ValueError):
            select_tile_batch([], 0, 0)

    def test_landcover_area_is_clipped_as_polygon_and_keeps_inner_hole(self):
        from tools.map_pipeline.build_dhaka_division import _clip_elements, _source_geometry
        from shapely.geometry import Point, box

        area = {
            "type": "way", "id": 777,
            "tags": {"landuse": "forest"},
            "geometry": [
                {"lat": 23.0, "lon": 90.0}, {"lat": 23.0, "lon": 92.0},
                {"lat": 25.0, "lon": 92.0}, {"lat": 25.0, "lon": 90.0},
                {"lat": 23.0, "lon": 90.0},
            ],
            "inner_rings": [[
                {"lat": 23.5, "lon": 90.5}, {"lat": 23.5, "lon": 91.5},
                {"lat": 24.5, "lon": 91.5}, {"lat": 24.5, "lon": 90.5},
                {"lat": 23.5, "lon": 90.5},
            ]],
        }
        geom = _source_geometry(area)
        self.assertTrue(geom.geom_type == "Polygon")
        self.assertEqual(len(geom.interiors), 1)
        clipped = _clip_elements([area], box(90.25, 23.25, 91.75, 24.75))
        self.assertEqual(len(clipped), 1)
        clipped_geom = _source_geometry(clipped[0])
        self.assertEqual(clipped_geom.geom_type, "Polygon")
        self.assertEqual(len(clipped_geom.interiors), 1)
        self.assertFalse(clipped_geom.contains(Point(91.0, 24.0)))

    def test_boundary_clip_removes_outside_nodes_and_clips_crossing_road(self):
        boundary = box(90.0, 23.0, 90.1, 23.1)
        elements = [
            {"type": "node", "id": 1, "lat": 23.05, "lon": 90.05, "tags": {"shop": "convenience"}},
            {"type": "node", "id": 2, "lat": 23.2, "lon": 90.2, "tags": {"shop": "convenience"}},
            {"type": "way", "id": 3, "tags": {"highway": "residential"},
             "geometry": [{"lat": 23.05, "lon": 89.9}, {"lat": 23.05, "lon": 90.2}]},
        ]
        clipped = _clip_elements(elements, boundary)
        self.assertEqual(sum(e["type"] == "node" for e in clipped), 1)
        roads = [e for e in clipped if e["type"] == "way"]
        self.assertEqual(len(roads), 1)
        geom = _source_geometry(roads[0])
        self.assertGreaterEqual(geom.bounds[0], 90.0 - 1e-9)
        self.assertLessEqual(geom.bounds[2], 90.1 + 1e-9)

    def test_boundary_clip_keeps_building_inside_division_polygon(self):
        boundary = box(90.0, 23.0, 90.1, 23.1)
        elements = [{
            "type": "way", "id": 11,
            "tags": {"building": "yes", "building:levels": "2"},
            "geometry": [
                {"lat": 23.04, "lon": 89.98},
                {"lat": 23.04, "lon": 90.03},
                {"lat": 23.08, "lon": 90.03},
                {"lat": 23.08, "lon": 89.98},
                {"lat": 23.04, "lon": 89.98},
            ],
        }]
        clipped = _clip_elements(elements, boundary)
        self.assertEqual(len(clipped), 1)
        geom = _source_geometry(clipped[0])
        self.assertTrue(boundary.covers(geom))
        self.assertAlmostEqual(geom.area, 0.0012, places=6)

    def test_boundary_ground_mesh_is_written_as_valid_glb(self):
        bbox = (23.0, 90.0, 23.1, 90.1)
        boundary = Polygon([
            (90.01, 23.01), (90.09, 23.01), (90.09, 23.09),
            (90.01, 23.09), (90.01, 23.01)
        ])
        elements = [{
            "type": "way", "id": 12,
            "tags": {"building": "yes", "building:levels": "2"},
            "geometry": [
                {"lat": 23.02, "lon": 90.02},
                {"lat": 23.02, "lon": 90.04},
                {"lat": 23.04, "lon": 90.04},
                {"lat": 23.04, "lon": 90.02},
                {"lat": 23.02, "lon": 90.02},
            ],
        }, {
            "type": "way", "id": 13,
            "tags": {"highway": "residential"},
            "geometry": [{"lat": 23.02, "lon": 90.01}, {"lat": 23.02, "lon": 90.09}],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            build_map(elements, out, bbox)
            glb = out / "Dhaka_Explorable_Map.glb"
            _replace_ground_with_boundary(glb, boundary, bbox)
            data = glb.read_bytes()
            self.assertEqual(data[:4], b"glTF")
            self.assertGreater(len(data), 1000)
            import trimesh
            scene = trimesh.load(glb, force="scene")
            self.assertTrue(any(name.startswith("terrain_base") for name in scene.geometry),
                            "Division-clipped ground must retain the name used by the game's collision builder")


    def test_curated_manasha_fallback_is_labeled_and_not_duplicated(self):
        target_lat, target_lon = 23.2004, 90.3484
        clip = box(90.30, 23.17, 90.37, 23.24)
        fallback = add_curated_manasha_footprint([], clip)
        self.assertEqual(len(fallback), 1)
        feature = fallback[0]
        self.assertEqual(feature["tags"]["name:bn"], "মনসা মন্দির, শরীয়তপুর")
        self.assertEqual(feature["tags"]["source:geometry"], "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED")
        self.assertEqual(feature["tags"]["height:source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
        self.assertEqual(feature["tags"]["building:levels:source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
        self.assertTrue(clip.covers(_source_geometry(feature)))
        self.assertEqual(len(add_curated_manasha_footprint(fallback, clip)), 1)

        distant_clip = box(90.20, 23.10, 90.25, 23.15)
        self.assertEqual(add_curated_manasha_footprint([], distant_clip), [])

        existing = [{
            "type": "way", "id": 67890,
            "tags": {"building": "temple", "name": "Existing mapped shrine"},
            "geometry": [
                {"lat": target_lat - 0.00002, "lon": target_lon - 0.00003},
                {"lat": target_lat - 0.00002, "lon": target_lon + 0.00003},
                {"lat": target_lat + 0.00002, "lon": target_lon + 0.00003},
                {"lat": target_lat + 0.00002, "lon": target_lon - 0.00003},
                {"lat": target_lat - 0.00002, "lon": target_lon - 0.00003},
            ],
        }]
        self.assertEqual(add_curated_manasha_footprint(existing, clip), existing)

    def test_curated_heritage_photo_footprints_are_location_bound_and_explicitly_unsurveyed(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "tools" / "map_pipeline" / "shariatpur_facade_images.json").read_text(encoding="utf-8"))
        targets = {
            "rudrakar_moth_35": (23.1830, 90.3459),
            "kartikpur_jomidar_bari_123242": (23.252441, 90.472991),
        }
        for image_id, (lat, lon) in targets.items():
            with self.subTest(image_id=image_id):
                clip = box(lon - 0.025, lat - 0.025, lon + 0.025, lat + 0.025)
                features = add_curated_heritage_photo_footprints([], clip)
                self.assertEqual(len(features), 1)
                feature = features[0]
                metadata = next(item for item in catalog["images"] if item["id"] == image_id)
                self.assertEqual(feature["id"], metadata["curated_feature_id"])
                self.assertEqual(feature["tags"]["source:geometry"], "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED")
                self.assertEqual(feature["tags"]["height:source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
                self.assertEqual(feature["tags"]["building:levels:source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
                self.assertEqual(feature["tags"]["source:location:url"], metadata["target_location_source"])
                self.assertEqual(feature["tags"]["facade:photo_source_id"], image_id)
                self.assertTrue(clip.covers(_source_geometry(feature)))
                # The placeholder is deterministic and isn't duplicated on a repeated tile pass.
                self.assertEqual(len(add_curated_heritage_photo_footprints(features, clip)), 1)
                distant_clip = box(lon + 0.10, lat + 0.10, lon + 0.15, lat + 0.15)
                self.assertEqual(add_curated_heritage_photo_footprints([], distant_clip), [])


    def test_rudrakar_and_kartikpur_licensed_exterior_photos_reach_the_actual_glb(self):
        from PIL import Image
        from unittest.mock import patch
        import trimesh

        root = Path(__file__).resolve().parents[1]
        catalog_path = root / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        targets = ("rudrakar_moth_35", "kartikpur_jomidar_bari_123242")
        for image_id in targets:
            with self.subTest(image_id=image_id), tempfile.TemporaryDirectory() as tmp:
                metadata = next(item for item in catalog["images"] if item["id"] == image_id)
                lat, lon = metadata["target_location_lat_lon"]
                bbox = (lat - 0.025, lon - 0.025, lat + 0.025, lon + 0.025)
                clip = box(bbox[1], bbox[0], bbox[3], bbox[2])
                elements = add_curated_heritage_photo_footprints([], clip)
                photo_dir = Path(tmp) / "photos"
                photo_dir.mkdir()
                Image.new("RGB", (640, 480), (154, 105, 78)).save(photo_dir / metadata["file_name"], format="JPEG")
                out = Path(tmp) / "tile"
                with patch.dict(os.environ, {
                    "WSB_FACADE_IMAGE_DIR": str(photo_dir),
                    "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
                }):
                    manifest = build_map(elements, out, bbox)
                self.assertEqual(manifest["feature_counts"]["licensed_facade_photo_panels"], 1)
                self.assertEqual(manifest["licensed_facade_photo_matches"][0]["image_id"], image_id)
                self.assertEqual(
                    manifest["licensed_facade_photo_matches"][0]["feature_geometry_source"],
                    "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED",
                )
                self.assertEqual(
                    manifest["facade_photo_diagnostics"]["embedded_panel_image_ids"],
                    [image_id],
                )
                scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
                self.assertTrue(
                    any(f"licensed_facade_photo_{image_id}_" in name and mesh.visual.kind == "texture"
                        for name, mesh in scene.geometry.items()),
                    f"{image_id} must exist as a textured mesh in the exported GLB, not only in metadata",
                )


    def test_manasha_photo_is_embedded_in_glb_and_geometry_is_not_mislabeled_as_surveyed(self):
        from PIL import Image
        from unittest.mock import patch
        import trimesh

        root = Path(__file__).resolve().parents[1]
        catalog_path = root / "tools" / "map_pipeline" / "shariatpur_facade_images.json"
        bbox = (23.175, 90.32, 23.225, 90.37)
        clip = box(bbox[1], bbox[0], bbox[3], bbox[2])
        elements = add_curated_manasha_footprint([], clip)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            photos = tmp_path / "photos"
            photos.mkdir()
            Image.new("RGB", (640, 480), (148, 96, 66)).save(
                photos / "manasha_temple_shariatpur_back_view.jpg", format="JPEG"
            )
            out = tmp_path / "tile"
            with patch.dict(os.environ, {
                "WSB_FACADE_IMAGE_DIR": str(photos),
                "WSB_FACADE_IMAGE_CATALOG": str(catalog_path),
            }):
                manifest = build_map(elements, out, bbox)

            counts = manifest["feature_counts"]
            self.assertEqual(counts["licensed_facade_photo_panels"], 1)
            self.assertEqual(counts["curated_approximate_landmark_footprints"], 1)
            match = manifest["licensed_facade_photo_matches"][0]
            self.assertEqual(match["image_id"], "manasha_temple_back_view_01")
            self.assertEqual(match["license"], "CC BY-SA 4.0")
            self.assertEqual(match["feature_geometry_source"], "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED")
            self.assertEqual(match["height_source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
            self.assertEqual(match["floor_count_source"], "CURATED_APPROXIMATE_NOT_SURVEYED")
            exported_geojson = json.loads((out / "Dhaka_OSM_Source.geojson").read_text(encoding="utf-8"))
            props = exported_geojson["features"][0]["properties"]
            self.assertEqual(props["source:geometry"], "CURATED_APPROXIMATE_FOOTPRINT_NOT_SURVEYED")
            self.assertEqual(
                props["source:location:url"],
                "https://ghurifiri.bd/places/dhanuka-manasha-bari-shariatpur",
            )
            self.assertNotEqual(match["height_source"], "OSM_HEIGHT_TAG")
            self.assertNotEqual(match["floor_count_source"], "OSM_BUILDING_LEVELS_TAG")
            scene = trimesh.load(out / "Dhaka_Explorable_Map.glb", force="scene")
            self.assertTrue(
                any("licensed_facade_photo_manasha_temple_back_view_01" in name for name in scene.geometry),
                "The actual textured exterior panel must survive GLB export, not just be counted in source metadata.",
            )

class QuaterniusCharacterDependencyTests(unittest.TestCase):
    def test_texture_uris_with_publisher_filename_suffix_are_extracted_to_expected_paths(self):
        from unittest.mock import patch
        from tools.fetch_quaternius_character import extract_character_dependencies

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "quaternius-pack.zip"
            unpacked = root / "extracted"
            output = root / "output"
            prefix = "Universal Base Characters[Standard]/"
            model_member = prefix + "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf"
            expected_texture_uri = "T_Hair_1_Normal_png.png"
            texture_member = prefix + "Shared Textures/T_Hair_1_Normal.png"
            buffer_member = prefix + "Base Characters/Godot - UE/character.bin"
            gltf = {
                "asset": {"version": "2.0"},
                "buffers": [{"uri": "character.bin", "byteLength": 4}],
                "images": [{"uri": expected_texture_uri}],
            }
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(model_member, json.dumps(gltf))
                archive.writestr(buffer_member, b"BUFF")
                archive.writestr(texture_member, b"PNGDATA")
                archive.writestr(prefix + "License_Standard.txt", "CC0-1.0")

            with patch("tools.fetch_quaternius_character.OUTPUT", output):
                extracted_gltf = extract_character_dependencies(archive_path, unpacked)

            expected_model = unpacked / "Base Characters" / "Godot - UE" / "Superhero_Male_FullBody.gltf"
            expected_buffer = unpacked / "Base Characters" / "Godot - UE" / "character.bin"
            expected_texture = unpacked / "Base Characters" / "Godot - UE" / expected_texture_uri
            self.assertEqual(extracted_gltf, expected_model)
            self.assertTrue(expected_model.is_file())
            self.assertEqual(json.loads(expected_model.read_text(encoding="utf-8")), gltf)
            self.assertEqual(expected_buffer.read_bytes(), b"BUFF")
            self.assertEqual(expected_texture.read_bytes(), b"PNGDATA")
            self.assertEqual((output / "LICENSE_Quaternius_Base_Characters.txt").read_text(encoding="utf-8"), "CC0-1.0")

    def test_texture_dependency_filename_ambiguity_is_not_silently_guessed(self):
        from unittest.mock import patch
        from tools.fetch_quaternius_character import extract_character_dependencies

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "quaternius-pack.zip"
            unpacked = root / "extracted"
            prefix = "Universal Base Characters[Standard]/"
            model_member = prefix + "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf"
            gltf = {"asset": {"version": "2.0"}, "images": [{"uri": "T_Hair_1_Normal_png.png"}]}
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(model_member, json.dumps(gltf))
                archive.writestr(prefix + "TexturesA/T_Hair_1_Normal.png", b"A")
                archive.writestr(prefix + "TexturesB/T_Hair_1_Normal.png", b"B")

            with patch("tools.fetch_quaternius_character.OUTPUT", root / "output"):
                with self.assertRaisesRegex(RuntimeError, "Ambiguous normalized GLTF dependency"):
                    extract_character_dependencies(archive_path, unpacked)


class LicensedFacadeDownloaderUrlTests(unittest.TestCase):
    def test_commons_thumbnail_uses_remote_filename_not_local_output_alias(self):
        import hashlib
        from urllib.parse import quote
        from tools.map_pipeline.fetch_licensed_facade_images import wikimedia_thumbnail_url

        item = {
            "source_page": "https://commons.wikimedia.org/wiki/File:Manasha_Temple,_Shariatpur_(back_view).jpg",
            # The pipeline intentionally uses a shorter local filename.
            "file_name": "manasha_temple_shariatpur_back_view.jpg",
        }
        actual = wikimedia_thumbnail_url(item)
        source_filename = "Manasha_Temple,_Shariatpur_(back_view).jpg"
        digest = hashlib.md5(source_filename.encode("utf-8")).hexdigest()
        encoded = quote(source_filename, safe="()_,.-")
        expected = (
            "https://upload.wikimedia.org/wikipedia/commons/thumb/"
            f"{digest[0]}/{digest[:2]}/{encoded}/1024px-{encoded}"
        )
        self.assertEqual(actual, expected)
        self.assertNotIn(item["file_name"], actual)

    def test_thumbnail_url_rejects_non_commons_source(self):
        from tools.map_pipeline.fetch_licensed_facade_images import wikimedia_thumbnail_url

        self.assertIsNone(wikimedia_thumbnail_url({
            "source_page": "https://example.com/wiki/File:photo.jpg",
            "file_name": "photo.jpg",
        }))


class SelectedHeroModelTests(unittest.TestCase):
    def test_playable_hero_uses_pinned_free_cc0_model(self):
        from tools.fetch_quaternius_character import CHARACTER_MEMBER_SUFFIX, PACKS

        expected = "Base Characters/Godot - UE/Superhero_Male_FullBody.gltf"
        self.assertEqual(CHARACTER_MEMBER_SUFFIX, expected)
        self.assertEqual(PACKS[0]["required_member_suffix"], expected)



class ApkGlbFacadeEmbeddedAssetTests(unittest.TestCase):
    @staticmethod
    def _make_glb(mesh_name: str | list[str], external_image_uri: bool = False) -> bytes:
        import json
        import struct

        mesh_names = [mesh_name] if isinstance(mesh_name, str) else list(mesh_name)
        if not mesh_names:
            raise ValueError("at least one synthetic mesh name is required")
        binary = bytearray(b"POSITIONUV00INDEX")
        buffer_views = [
            {"buffer": 0, "byteOffset": 0, "byteLength": 8},
            {"buffer": 0, "byteOffset": 8, "byteLength": 4},
            {"buffer": 0, "byteOffset": 12, "byteLength": 5},
        ]
        image_records = []
        textures = []
        materials = []
        meshes = []
        nodes = []
        for index, name in enumerate(mesh_names):
            if external_image_uri:
                image_records.append({"uri": "photo.png"})
            else:
                image = b"\x89PNG\r\n\x1a\n" + (f"embedded-test-image-{index}").encode("ascii")
                image_offset = len(binary)
                binary.extend(image)
                image_records.append({
                    "bufferView": len(buffer_views),
                    "mimeType": "image/png",
                })
                buffer_views.append({
                    "buffer": 0,
                    "byteOffset": image_offset,
                    "byteLength": len(image),
                })
            textures.append({"source": index})
            materials.append({"pbrMetallicRoughness": {"baseColorTexture": {"index": index}}})
            meshes.append({
                "name": name,
                "primitives": [{
                    "attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                    "indices": 2,
                    "material": index,
                }],
            })
            nodes.append({"name": name, "mesh": index})

        document = {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": len(binary)}],
            "bufferViews": buffer_views,
            "images": image_records,
            "textures": textures,
            "materials": materials,
            "meshes": meshes,
            "nodes": nodes,
        }
        json_chunk = json.dumps(document, separators=(",", ":")).encode("utf-8")
        json_chunk += b" " * ((-len(json_chunk)) % 4)
        binary_chunk = bytes(binary) + b"\x00" * ((-len(binary)) % 4)
        total_length = 12 + 8 + len(json_chunk) + 8 + len(binary_chunk)
        return (
            struct.pack("<4sII", b"glTF", 2, total_length)
            + struct.pack("<II", len(json_chunk), 0x4E4F534A) + json_chunk
            + struct.pack("<II", len(binary_chunk), 0x004E4942) + binary_chunk
        )

    def test_apk_verifier_accepts_named_facade_mesh_with_embedded_texture(self):
        from tools.verify_apk_contents import _assert_glb_has_embedded_facade_panel

        image_id = "rudrakar_moth_35"
        osm_id = "-62900001"
        mesh_name = f"licensed_facade_photo_{image_id}_{osm_id}"
        _assert_glb_has_embedded_facade_panel(self._make_glb(mesh_name), image_id, osm_id)

    def test_apk_verifier_rejects_manifest_only_panel_without_mesh(self):
        from tools.verify_apk_contents import _assert_glb_has_embedded_facade_panel

        with self.assertRaisesRegex(ValueError, "named mesh"):
            _assert_glb_has_embedded_facade_panel(
                self._make_glb("unrelated_procedural_wall"), "rudrakar_moth_35", "-62900001"
            )

    def test_apk_verifier_rejects_external_texture_that_is_not_embedded_in_glb(self):
        from tools.verify_apk_contents import _assert_glb_has_embedded_facade_panel

        image_id = "rudrakar_moth_35"
        osm_id = "-62900001"
        mesh_name = f"licensed_facade_photo_{image_id}_{osm_id}"
        with self.assertRaisesRegex(ValueError, "embedded raster texture"):
            _assert_glb_has_embedded_facade_panel(
                self._make_glb(mesh_name, external_image_uri=True), image_id, osm_id
            )


if __name__ == "__main__":
    unittest.main()
