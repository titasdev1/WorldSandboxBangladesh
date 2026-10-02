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
 var night=world.day_time>18.0 or world.day_time<6.0
 for c in world.get_children():
  if c is OmniLight3D: c.light_energy=0.8 if night else 0.12
