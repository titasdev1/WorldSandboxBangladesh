extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var zoom=clamp(float(world.get_meta("map_zoom",1.0))+0.01*sin(Time.get_ticks_msec()/5000.0),0.8,1.4); world.set_meta("map_zoom",zoom)
