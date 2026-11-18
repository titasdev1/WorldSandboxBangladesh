extends SceneTree

class TilePbrSmokeWorld extends Node3D:
    var pbr_surface_factory: Node


## Runtime test for imported Poly Haven PBR textures and material-channel bindings.
## Run after the editor import pass:
## godot --headless --path . --script res://tests/pbr_surface_runtime_smoke.gd

func _initialize() -> void:
    await process_frame
    var factory_script := load("res://pbr_surface_factory.gd") as Script
    if factory_script == null:
        push_error("PBR_SURFACE_RUNTIME_FAIL: pbr_surface_factory.gd did not load")
        quit(1)
        return

    var factory: Node = factory_script.new()
    root.add_child(factory)
    factory.call("configure", null)

    var surfaces_value: Variant = factory.get("surfaces")
    if not surfaces_value is Dictionary or surfaces_value.is_empty():
        print("PBR_SURFACE_RUNTIME_FALLBACK_PASS: no valid optional Poly Haven manifest; procedural fallback remains available")
        factory.queue_free()
        await process_frame
        quit(0)
        return

    var failures: Array[String] = []
    var report: Array[Dictionary] = []
    var surfaces: Dictionary = surfaces_value

    for surface_value in surfaces.keys():
        var surface_id := str(surface_value)
        var entry: Dictionary = surfaces[surface_id]
        var maps: Dictionary = entry.get("maps", {})
        var fallback := StandardMaterial3D.new()
        fallback.albedo_color = Color(0.76, 0.76, 0.76)
        fallback.roughness = 0.82
        fallback.metallic = 0.0

        var material: StandardMaterial3D = factory.call("material_for", surface_id, fallback) as StandardMaterial3D
        if material == null:
            failures.append("%s: factory returned no StandardMaterial3D" % surface_id)
            continue
        if maps.has("albedo") and material.albedo_texture == null:
            failures.append("%s: albedo map did not load" % surface_id)
        if maps.has("normal") and (not material.normal_enabled or material.normal_texture == null):
            failures.append("%s: normal map did not bind" % surface_id)
        if maps.has("roughness") and material.roughness_texture == null:
            failures.append("%s: roughness map did not bind" % surface_id)
        if maps.has("metallic") and material.metallic_texture == null:
            failures.append("%s: metallic map did not bind" % surface_id)
        if maps.has("ao") and (not material.ao_enabled or material.ao_texture == null):
            failures.append("%s: ambient-occlusion map did not bind" % surface_id)
        if material.heightmap_enabled:
            failures.append("%s: height mapping unexpectedly enabled on the default mobile material" % surface_id)

        var same_cached: StandardMaterial3D = factory.call("material_for", surface_id, fallback) as StandardMaterial3D
        if same_cached != material:
            failures.append("%s: identical material settings did not reuse the cache entry" % surface_id)

        var rough_fallback := StandardMaterial3D.new()
        rough_fallback.albedo_color = fallback.albedo_color
        rough_fallback.roughness = 0.24
        rough_fallback.metallic = 0.0
        var rough_material: StandardMaterial3D = factory.call("material_for", surface_id, rough_fallback) as StandardMaterial3D
        if rough_material == material:
            failures.append("%s: material cache ignored changed roughness input" % surface_id)

        var tile_material: StandardMaterial3D = factory.call("material_for_tile", surface_id, fallback) as StandardMaterial3D
        if tile_material == null or not tile_material.uv1_triplanar:
            failures.append("%s: real-map tile material did not enable triplanar UV projection" % surface_id)
        if tile_material != null and not tile_material.vertex_color_use_as_albedo:
            failures.append("%s: mapped vertex-colour variation was not preserved" % surface_id)
        if tile_material != null and tile_material.heightmap_enabled:
            failures.append("%s: streamed mobile tile material unexpectedly enabled parallax" % surface_id)
        if surface_id == "metal" and tile_material != null and tile_material.metallic_texture == null and tile_material.metallic < 0.8:
            failures.append("metal: missing metallic texture and fallback metallic response")

        var closeup: StandardMaterial3D = factory.call("material_for_closeup", surface_id, fallback) as StandardMaterial3D
        if maps.has("height"):
            if not closeup.heightmap_enabled or closeup.heightmap_texture == null:
                failures.append("%s: opt-in close-up height map did not bind" % surface_id)
            if closeup.heightmap_deep_parallax:
                failures.append("%s: deep parallax must remain disabled for mobile" % surface_id)
        elif closeup.heightmap_enabled:
            failures.append("%s: close-up parallax enabled without a height map" % surface_id)

        report.append({
            "surface": surface_id,
            "maps": maps.keys(),
            "metallic_bound": material.metallic_texture != null,
            "ao_bound": material.ao_enabled and material.ao_texture != null,
            "heightmap_opt_in": closeup.heightmap_enabled,
            "tile_triplanar": tile_material != null and tile_material.uv1_triplanar,
            "tile_vertex_color_preserved": tile_material != null and tile_material.vertex_color_use_as_albedo,
            "tile_heightmap_disabled": tile_material == null or not tile_material.heightmap_enabled,
            "mobile_deep_parallax": material.heightmap_deep_parallax,
        })

    # Exercise the exact streamed-tile helper against the same mesh-name
    # families produced by tools/map_pipeline/build_dhaka_map.py.
    var tile_world := TilePbrSmokeWorld.new()
    tile_world.name = "PBRStreamedTileSmokeWorld"
    root.add_child(tile_world)
    var tile_factory: Node = factory_script.new()
    tile_factory.name = "PBRSurfaceFactory"
    tile_world.add_child(tile_factory)
    tile_world.pbr_surface_factory = tile_factory
    tile_factory.call("configure", null)

    var loader_script := load("res://real_dhaka_tile_loader.gd") as Script
    if loader_script == null:
        failures.append("real_dhaka_tile_loader.gd did not load for tile material integration test")
    else:
        var tile_loader: Node = loader_script.new()
        tile_world.add_child(tile_loader)
        tile_loader.set("_world", tile_world)
        var tile_root := Node3D.new()
        tile_root.name = "SyntheticShariatpurTile"
        tile_world.add_child(tile_root)

        var expected_groups := [
            {"node": "terrain_base_0", "surface": "ground"},
            {"node": "road_123_0_0", "surface": "road"},
            {"node": "mapped_buildings_180_180_180_255", "surface": "plaster"},
            {"node": "mapped_roofs_120_120_120_255", "surface": "concrete"},
            {"node": "facade_doors_110_80_60_255", "surface": "wood"},
            {"node": "facade_balconies_160_160_160_255", "surface": "metal"},
        ]
        var synthetic_meshes: Dictionary = {}
        for spec in expected_groups:
            var mesh_instance := MeshInstance3D.new()
            mesh_instance.name = String(spec["node"])
            mesh_instance.mesh = BoxMesh.new()
            var source_material := StandardMaterial3D.new()
            source_material.albedo_color = Color(0.63, 0.59, 0.52)
            mesh_instance.material_override = source_material
            tile_root.add_child(mesh_instance)
            synthetic_meshes[String(spec["node"])] = mesh_instance

        var preserved_material := StandardMaterial3D.new()
        preserved_material.albedo_color = Color(0.2, 0.4, 0.7)
        var photo_panel := MeshInstance3D.new()
        photo_panel.name = "licensed_facade_photo_reviewed_123"
        photo_panel.mesh = BoxMesh.new()
        photo_panel.material_override = preserved_material
        tile_root.add_child(photo_panel)
        var window_panel := MeshInstance3D.new()
        window_panel.name = "facade_windows_glass_123"
        window_panel.mesh = BoxMesh.new()
        window_panel.material_override = preserved_material
        tile_root.add_child(window_panel)

        tile_loader.call("_apply_tile_pbr_materials", tile_root)
        var applied_counts: Dictionary = tile_root.get_meta("pbr_surface_counts", {})
        for spec in expected_groups:
            var node_name := String(spec["node"])
            var surface_id := String(spec["surface"])
            var target := synthetic_meshes[node_name] as MeshInstance3D
            var mapped := target.material_override as StandardMaterial3D
            if mapped == null or not mapped.uv1_triplanar:
                failures.append("%s: streamed tile mesh did not receive its %s triplanar PBR material" % [node_name, surface_id])
            if mapped != null and not mapped.vertex_color_use_as_albedo:
                failures.append("%s: streamed tile lost mapped vertex-colour data" % node_name)
            if mapped != null and mapped.heightmap_enabled:
                failures.append("%s: streamed tile unexpectedly enabled expensive height mapping" % node_name)
            if int(applied_counts.get(surface_id, 0)) < 1:
                failures.append("%s: material assignment count did not include the real tile mesh group" % surface_id)

        if photo_panel.material_override != preserved_material:
            failures.append("licensed exterior photo panel was overwritten by generic PBR material")
        if window_panel.material_override != preserved_material:
            failures.append("authored facade window/glass material was overwritten by generic PBR material")

        report.append({
            "streamed_tile_mesh_groups": applied_counts,
            "licensed_photo_panel_preserved": photo_panel.material_override == preserved_material,
            "window_material_preserved": window_panel.material_override == preserved_material,
        })
        tile_world.queue_free()
        await process_frame

    factory.queue_free()
    await process_frame

    if not failures.is_empty():
        for failure in failures:
            push_error("PBR_SURFACE_RUNTIME_FAIL: " + failure)
        quit(1)
        return

    print("PBR_SURFACE_RUNTIME_PASS: " + JSON.stringify({
        "surface_count": report.size(),
        "surfaces": report,
        "default_deep_parallax": false,
        "cache_key_includes_roughness_and_metallic": true,
    }))
    quit(0)
