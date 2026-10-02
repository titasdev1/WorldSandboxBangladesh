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
 if world.rain:
  for n in world.get_children():
   if n is CharacterBody3D and str(n.name).begins_with("NPC_"): n.walk_speed = min(n.walk_speed,1.5)
