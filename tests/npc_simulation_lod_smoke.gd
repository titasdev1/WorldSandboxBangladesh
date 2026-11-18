extends SceneTree

class SmokeWorld extends Node:
 var player: CharacterBody3D


func _initialize() -> void:
 call_deferred("_run_smoke")


func _expect(condition: bool, message: String) -> bool:
 if condition:
  return true
 push_error("NPC_SIMULATION_LOD_FAIL: " + message)
 quit(1)
 return false


func _run_smoke() -> void:
 var world := SmokeWorld.new()
 root.add_child(world)
 var player := CharacterBody3D.new()
 player.name = "Player"
 world.add_child(player)
 world.player = player

 var manager := Node.new()
 manager.name = "NpcSimulationLODManager"
 manager.set_script(load("res://systems/npc_simulation_lod_manager.gd"))
 world.add_child(manager)
 manager.call("configure", world)

 var npc := CharacterBody3D.new()
 npc.name = "LODTestCivilian"
 npc.set_script(load("res://npc.gd"))
 npc.set("world", world)
 npc.add_to_group("world_npc")
 var visual := Node3D.new()
 visual.name = "HumanoidVisual"
 npc.add_child(visual)
 var collision := CollisionShape3D.new()
 collision.name = "CollisionShape3D"
 var capsule := CapsuleShape3D.new()
 capsule.radius = 0.3
 capsule.height = 1.5
 collision.shape = capsule
 npc.add_child(collision)
 world.add_child(npc)
 await process_frame

 player.global_position = Vector3.ZERO
 npc.global_position = Vector3(30.0, 0.0, 0.0)
 manager.call("refresh_now")
 var near_diagnostic := "tier=%d physics=%s visual=%s collision_disabled=%s visible=%s" % [
  int(npc.get("_simulation_tier")),
  str(npc.is_physics_processing()),
  str(visual.is_processing()),
  str(collision.disabled),
  str(npc.visible)
 ]
 if not _expect(int(npc.get("_simulation_tier")) == 0 and npc.is_physics_processing() and visual.is_processing() and not collision.disabled and npc.visible, "near civilians must keep full physics, animation and collision; " + near_diagnostic):
  return

 npc.global_position = Vector3(90.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(int(npc.get("_simulation_tier")) == 1 and npc.is_physics_processing() and visual.is_processing(), "mid-distance civilians must keep animation while reducing physics cadence."):
  return

 npc.global_position = Vector3(155.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(int(npc.get("_simulation_tier")) == 2 and not npc.is_physics_processing() and not visual.is_processing() and collision.disabled and npc.visible, "far civilians must pause physics/animation and collision while still visible."):
  return

 npc.global_position = Vector3(190.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(not npc.visible and (npc.get("_distance_hidden") == true), "very distant civilians must be culled from rendering."):
  return

 npc.global_position = Vector3(160.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(not npc.visible, "visibility hysteresis must prevent flicker near the hide threshold."):
  return

 npc.global_position = Vector3(130.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(npc.visible and int(npc.get("_simulation_tier")) == 1 and npc.is_physics_processing() and not collision.disabled, "approaching civilians must restore visibility, physics and collision."):
  return

 npc.global_position = Vector3(25.0, 0.0, 0.0)
 manager.call("refresh_now")
 if not _expect(int(npc.get("_simulation_tier")) == 0 and npc.is_physics_processing() and visual.is_processing(), "nearby civilians must return to full simulation."):
  return

 print("NPC_SIMULATION_LOD_PASS • near=full • mid=8Hz physics • far=paused • cull=175m • reactivation=true")
 quit(0)
