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
    var entry: Dictionary = building_models[rng.randi_range(0, building_models.size() - 1)]
    var resource = load(String(entry.path))
    if not resource is PackedScene:
        return false
    var instance = resource.instantiate()
    if not instance is Node3D:
        instance.free()
        return false

    instance.name = "Authored_" + String(entry.name).replace(" ", "_")
    instance.rotation.y = deg_to_rad(float([0, 90, 180, 270][rng.randi_range(0, 3)]))
    var source_bounds := _model_local_bounds(instance)
    if source_bounds.size.x < 0.01 or source_bounds.size.y < 0.01 or source_bounds.size.z < 0.01:
        instance.free()
        return false

    # Normalize the *actual imported mesh bounds*. The previous target_size/8
    # and target_size/12 heuristic assumed every GLTF had the same native units;
    # normalized Kenney GLTFs could consequently render as tiny doll-house blocks.
    # Scale to the lot dimensions, then put the source model's real bottom at y=0
    # and centre its footprint on the requested world position.
    var variation := rng.randf_range(0.96, 1.04)
    var normalized_scale := Vector3(
        target_size.x / source_bounds.size.x,
        target_size.y / source_bounds.size.y,
        target_size.z / source_bounds.size.z
    )
    instance.scale = normalized_scale * variation
    var local_ground_center := Vector3(
        source_bounds.position.x + source_bounds.size.x * 0.5,
        source_bounds.position.y,
        source_bounds.position.z + source_bounds.size.z * 0.5
    )
    instance.position = position - instance.basis * local_ground_center
    world.add_child(instance)
    return true


func _model_local_bounds(root: Node3D) -> AABB:
    # Imported GLTF scenes vary in nesting and local transforms. Combine each
    # visible MeshInstance3D's eight AABB corners in the root scene's coordinates
    # rather than assuming a nominal source-model width or height.
    var result := AABB()
    var has_bounds := false
    var mesh_nodes: Array[Node] = []
    if root is MeshInstance3D:
        mesh_nodes.append(root)
    mesh_nodes.append_array(root.find_children("*", "MeshInstance3D", true, false))
    for candidate in mesh_nodes:
        var mesh_instance := candidate as MeshInstance3D
        if mesh_instance == null or mesh_instance.mesh == null or not mesh_instance.visible:
            continue
        var relative_transform := Transform3D.IDENTITY
        var cursor: Node = mesh_instance
        while cursor != null and cursor != root:
            if cursor is Node3D:
                relative_transform = (cursor as Node3D).transform * relative_transform
            cursor = cursor.get_parent()
        if cursor != root:
            continue
        var mesh_bounds := mesh_instance.get_aabb()
        for endpoint_index in range(8):
            var point: Vector3 = relative_transform * mesh_bounds.get_endpoint(endpoint_index)
            if not has_bounds:
                result = AABB(point, Vector3.ZERO)
                has_bounds = true
            else:
                result = result.expand(point)
    return result if has_bounds else AABB()
