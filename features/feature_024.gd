extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=2.2; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 var env=world.get_node_or_null("WorldEnvironment")
 if env and env.environment:
  env.environment.fog_enabled=world.rain
  env.environment.fog_light_energy=0.65
