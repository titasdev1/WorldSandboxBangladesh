extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=4.5; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.player: world.set_meta("context_prompt","ENTER VEHICLE" if world.player.global_position.distance_to(Vector3(42,0,42))<4.0 else "EXPLORE")
