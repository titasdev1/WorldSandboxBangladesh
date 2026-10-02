extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.1; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 world.fare_requested=clamp(120+int(sin(Time.get_ticks_msec()/9000.0)*25.0),70,180); world.bargain_offer=min(world.bargain_offer,world.fare_requested)
