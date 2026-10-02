extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=2.8; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var p=[]
 for v in world.get_children():
  if v is CharacterBody3D and v.is_police: p.append(v.global_position)
 world.set_meta("map_police_positions",p)
