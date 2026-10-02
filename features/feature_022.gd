extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=4; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var env=world.get_node_or_null("WorldEnvironment")
 if env and env.environment: env.environment.background_color=Color("#718da3") if world.rain else Color("#8fb9d2")
