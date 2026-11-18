extends Node
class_name NpcSimulationLODManager

const REFRESH_INTERVAL_SECONDS := 0.5

var _world: Node
var _refresh_elapsed := 0.0


func configure(world: Node) -> void:
 _world = world
 _refresh_elapsed = 0.0
 call_deferred("refresh_now")


func _process(delta: float) -> void:
 _refresh_elapsed += delta
 if _refresh_elapsed < REFRESH_INTERVAL_SECONDS:
  return
 _refresh_elapsed = 0.0
 refresh_now()


func refresh_now() -> void:
 if not is_instance_valid(_world):
  return
 var player := _world.get("player") as Node3D
 if not is_instance_valid(player):
  return
 for candidate in get_tree().get_nodes_in_group("world_npc"):
  var npc := candidate as Node3D
  if not is_instance_valid(npc) or not npc.has_method("set_distance_lod"):
   continue
  npc.call("set_distance_lod", npc.global_position.distance_to(player.global_position))
