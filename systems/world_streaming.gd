extends Node
class_name WorldStreaming

@export var active_radius := 420.0
@export var unload_radius := 620.0
var player: Node3D
var districts: Array[Dictionary] = []
var loaded_ids: Dictionary = {}

func configure(target: Node3D, district_data: Array[Dictionary]) -> void:
    player = target
    districts = district_data

func update_streaming() -> void:
    if not is_instance_valid(player):
        return
    var p := player.global_position
    for district in districts:
        var id: String = str(district.get("id", ""))
        var center := Vector3(float(district.get("x", 0.0)), 0.0, float(district.get("z", 0.0)))
        var distance := center.distance_to(p)
        if distance <= active_radius:
            loaded_ids[id] = true
        elif distance >= unload_radius:
            loaded_ids.erase(id)

func is_loaded(id: String) -> bool:
    return loaded_ids.has(id)
