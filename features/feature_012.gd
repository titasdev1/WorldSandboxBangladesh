extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=4.5
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 var rush = world.day_time>7.0 and world.day_time<9.5 or world.day_time>17.0 and world.day_time<19.5
 world.set_meta("commuter_rush",rush)
