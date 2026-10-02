extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=5.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var hud=world.get_node_or_null("HUD"); if hud: hud.set_meta("objective_pulse",sin(Time.get_ticks_msec()/400.0))
