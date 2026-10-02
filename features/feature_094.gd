extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=5.5; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var count=0
 for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player"): count+=1
 world.set_meta("traffic_budget_used",count)
