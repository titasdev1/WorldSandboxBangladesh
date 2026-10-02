extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=4.5; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var cd=float(world.get_meta("shop_cooldown",0.0)); world.set_meta("shop_cooldown",max(0.0,cd-0.5))
