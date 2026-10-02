extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=5.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 SaveSystem.save_world(world)
