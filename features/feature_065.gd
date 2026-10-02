extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 world.set_meta("reward_streak",int(world.get_meta("reward_streak",0))+(1 if world.mission_progress>0 else 0))
