extends Node
class_name CityAssetFactory

var world: Node3D
var rng := RandomNumberGenerator.new()
var building_models: Array[Dictionary] = []

const MANIFESTS := [
    "res://external_content/kenney_city_kit_suburban/asset_manifest.json",
    "res://external_content/kenney_city_kit_commercial/asset_manifest.json",
    "res://external_content/kenney_city_kit_industrial/asset_manifest.json"
]
const BUILDING_WORDS := ["building", "house", "apartment", "office", "shop", "skyscraper", "warehouse", "factory", "commercial"]

func configure(target: Node3D) -> void:
    world = target
    rng.randomize()
    _load_manifests()
    set_meta("authored_building_model_count", building_models.size())

func _load_manifests() -> void:
    building_models.clear()
    for manifest_path in MANIFESTS:
        if not FileAccess.file_exists(manifest_path):
            continue
        var file := FileAccess.open(manifest_path, FileAccess.READ)
        if file == null:
            continue
        var parsed = JSON.parse_string(file.get_as_text())
        if not parsed is Dictionary or not bool(parsed.get("available", false)):
            continue
        for item in parsed.get("models", []):
            if not item is Dictionary:
                continue
            var model_name := String(item.get("name", "")).to_lower()
            var model_path := String(item.get("path", ""))
            var suitable := false
            for token in BUILDING_WORDS:
                if model_name.contains(token):
                    suitable = true
                    break
            if suitable and model_path.begins_with("res://"):
                building_models.append({"name": model_name, "path": model_path})
    building_models.sort_custom(func(a, b): return String(a.name) < String(b.name))

func spawn_building(position: Vector3, target_size: Vector3) -> bool:
    if building_models.is_empty():
        return false
    # Rotate through the authored set with controlled variation instead of
    # repeatedly instancing the same model in every city block.
    var entry: Dictionary = building_models[rng.randi_range(0, building_models.size() - 1)]
    var resource = load(String(entry.path))
    if not resource is PackedScene:
        return false
    var instance = resource.instantiate()
    if not instance is Node3D:
        instance.free()
        return false
    instance.name = "Authored_" + String(entry.name).replace(" ", "_")
    instance.position = position
    instance.rotation.y = deg_to_rad(float([0, 90, 180, 270][rng.randi_range(0, 3)]))
    # Normalize unknown source dimensions to the same rough footprint as the
    # existing lot, while preserving real mesh geometry and materials.
    var variation := rng.randf_range(0.88, 1.12)
    instance.scale = Vector3(
        maxf(0.5, target_size.x / 8.0) * variation,
        maxf(0.5, target_size.y / 12.0) * variation,
        maxf(0.5, target_size.z / 8.0) * variation
    )
    world.add_child(instance)
    return true
