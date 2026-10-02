extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.5500000000000003; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var rush=world.day_time>7.0 and world.day_time<9.5 or world.day_time>17.0 and world.day_time<19.5
 if rush: world.fare_requested=max(world.fare_requested,130)
