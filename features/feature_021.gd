extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.5500000000000003; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.rain and fmod(Time.get_ticks_msec()/1000.0,31.0)>29.5: world.rain=false
