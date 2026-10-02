extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var chance=0.55+0.25*sin(Time.get_ticks_msec()/7000.0); world.set_meta("fare_accept_chance",chance)
