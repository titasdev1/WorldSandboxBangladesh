extends Node
class_name PBRSurfaceFactory

const MANIFEST_PATH := "res://external_content/polyhaven_pbr/asset_manifest.json"
var surfaces: Dictionary = {}
var material_cache: Dictionary = {}

func configure(_world: Node) -> void:
    surfaces.clear()
    if not FileAccess.file_exists(MANIFEST_PATH):
        return
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
    if not parsed is Dictionary or not bool(parsed.get("available", false)):
        return
    var entries = parsed.get("surfaces", {})
    if not entries is Dictionary:
        return
    surfaces = entries.duplicate(true)
    set_meta("pbr_surface_count", surfaces.size())

func material_for(surface_id: String, fallback: StandardMaterial3D) -> StandardMaterial3D:
    if not surfaces.has(surface_id):
        return fallback
    var cache_key := surface_id + ":" + fallback.albedo_color.to_html(true)
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
    material.uv1_scale = Vector3(2.0, 2.0, 2.0)
    material.set_meta("asset_source", String(entry.get("source_url", "Poly Haven CC0")))
    material_cache[cache_key] = material
    return material
