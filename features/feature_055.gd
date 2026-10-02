extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=2.5; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.player and world.player.global_position.distance_to(Vector3(-36,0,-36))<4.0: world.set_meta("ammo_reserve",int(world.get_meta("ammo_reserve",0))+6)
