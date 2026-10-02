extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=2.2; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var crime=float(world.get_meta("crime_cooldown",0.0)); world.set_meta("crime_cooldown",max(0.0,crime-0.5))
