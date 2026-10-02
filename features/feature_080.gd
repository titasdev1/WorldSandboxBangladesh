extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.6; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 world.set_meta("school_bell",world.day_time>7.9 and world.day_time<8.1)
