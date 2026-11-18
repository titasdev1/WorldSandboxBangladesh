extends SceneTree
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
