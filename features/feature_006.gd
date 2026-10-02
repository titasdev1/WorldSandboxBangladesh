extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=5
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for n in world.get_children():
  if n is CharacterBody3D and str(n.name).begins_with("NPC_"):
   n.position.x = clamp(n.position.x, -76.0, 76.0)
   n.position.z = clamp(n.position.z, -76.0, 76.0)
