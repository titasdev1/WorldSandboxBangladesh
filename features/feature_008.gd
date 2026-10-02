extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=2.5
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for n in world.get_children():
  if n is CharacterBody3D and str(n.name).begins_with("NPC_"): n.walk_speed = clamp(n.walk_speed * (0.97 + 0.06*sin(Time.get_ticks_msec()/4000.0)),0.6,3.0)
