extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=4
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for n in world.get_children():
  if n is CharacterBody3D and str(n.name).begins_with("NPC_") and int(n.name.trim_prefix("NPC_")) % 5 == 1: n.walk_speed = 2.2 if world.day_time>8.0 and world.day_time<18.0 else 1.1
