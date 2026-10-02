extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=3.5
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for n in world.get_children():
  if n is CharacterBody3D and str(n.name).begins_with("NPC_") and int(n.name.trim_prefix("NPC_")) % 5 == 0: n.walk_speed = 1.6 if world.day_time>7.0 and world.day_time<16.0 else 0.9
