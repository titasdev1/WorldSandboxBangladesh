extends Node
class_name PBRSurfaceFactory

const MANIFEST_PATH := "res://external_content/polyhaven_pbr/asset_manifest.json"
var surfaces: Dictionary = {}
var material_cache: Dictionary = {}

func configure(_world: Node) -> void:
    surfaces.clear()
    material_cache.clear()
    if not FileAccess.file_exists(MANIFEST_PATH):
        return
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    if not parsed is Dictionary or not (parsed.get("available", false) == true):
        return
    var entries = parsed.get("surfaces", {})
    if not entries is Dictionary:
        return
    surfaces = entries.duplicate(true)
    set_meta("pbr_surface_count", surfaces.size())


func material_for(surface_id: String, fallback: StandardMaterial3D, enable_parallax := false, use_triplanar := false) -> StandardMaterial3D:
    if not surfaces.has(surface_id):
        return fallback
    var cache_key := "%s:%s:rough=%.4f:metal=%.4f:pom=%s" % [
        surface_id,
        fallback.albedo_color.to_html(true),
        fallback.roughness,
        fallback.metallic,
        str(enable_parallax),
        str(use_triplanar)
    ]
    if material_cache.has(cache_key):
        return material_cache[cache_key]

    var entry: Dictionary = surfaces[surface_id]
    var maps: Dictionary = entry.get("maps", {})
    if not maps.has("albedo"):
        return fallback

    var material := StandardMaterial3D.new()
    material.albedo_color = fallback.albedo_color
    material.roughness = fallback.roughness
    material.metallic = fallback.metallic

    var albedo = load(String(maps.get("albedo", "")))
    if albedo is Texture2D:
        material.albedo_texture = albedo

    var normal = load(String(maps.get("normal", ""))) if maps.has("normal") else null
    if normal is Texture2D:
        material.normal_enabled = true
        material.normal_texture = normal

    var roughness = load(String(maps.get("roughness", ""))) if maps.has("roughness") else null
    if roughness is Texture2D:
        material.roughness_texture = roughness

    # The previous factory downloaded metalness maps but never bound them.
    # Bind the authored map so steel, painted metal and wet road details are
    # shaded from their texture data instead of one uniform fallback value.
    var metallic = load(String(maps.get("metallic", ""))) if maps.has("metallic") else null
    if metallic is Texture2D:
        material.metallic_texture = metallic
    elif surface_id == "metal":
        # Poly Haven's selected metal plate has no separate metalness image.
        # Its material class is known, so use a physically plausible fallback.
        material.metallic = maxf(material.metallic, 0.85)

    # Ambient occlusion restores small creases and contact detail in materials.
    var ao = load(String(maps.get("ao", ""))) if maps.has("ao") else null
    if ao is Texture2D:
        material.ao_enabled = true
        material.ao_texture = ao
        material.ao_light_affect = 0.25

    # Height mapping is opt-in and shallow by default. Use only on close-up
    # hero surfaces; do not enable expensive deep parallax across every street.
    var height = load(String(maps.get("height", ""))) if maps.has("height") else null
    if enable_parallax and height is Texture2D:
        material.heightmap_enabled = true
        material.heightmap_texture = height
        material.heightmap_scale = 1.5
        material.heightmap_deep_parallax = false

    material.uv1_scale = Vector3(0.55, 0.55, 0.55) if use_triplanar else Vector3(2.0, 2.0, 2.0)
    if use_triplanar:
        # OSM tile meshes are batched with vertex-colour material groups and do
        # not carry authored UVs. Triplanar projection makes the real-world PBR
        # textures visible without inventing UVs; vertex colour keeps mapped
        # facade/roof colour cues from the source data.
        material.uv1_triplanar = true
        material.vertex_color_use_as_albedo = true
        material.heightmap_enabled = false
        material.heightmap_deep_parallax = false
    material.set_meta("asset_source", String(entry.get("source_url", "Poly Haven CC0")))
    material.set_meta("pbr_maps", maps.keys())
    material_cache[cache_key] = material
    return material


func material_for_closeup(surface_id: String, fallback: StandardMaterial3D) -> StandardMaterial3D:
    return material_for(surface_id, fallback, true, false)


func material_for_tile(surface_id: String, fallback: StandardMaterial3D) -> StandardMaterial3D:
    # World-coordinate projection works on the streamed OSM/Overture meshes,
    # which are generated without UVs. POM is deliberately disabled for these
    # repeated mobile surfaces; only close-up, explicitly requested materials
    # may use shallow height mapping.
    return material_for(surface_id, fallback, false, true)
