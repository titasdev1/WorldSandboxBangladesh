extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=6.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player"):
   var fuel=float(v.get_meta("fuel",100.0)); v.set_meta("fuel",max(0.0,fuel-0.02))
