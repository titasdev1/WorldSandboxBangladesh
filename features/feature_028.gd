extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=4; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.player: world.player.set_meta("footstep_state","running" if world.player.velocity.length()>8 else ("walking" if world.player.velocity.length()>0.5 else "idle"))
