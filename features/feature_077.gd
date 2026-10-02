extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=3.6; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.day_time>18.0 or world.day_time<5.0:
  for c in world.get_children():
   if c is OmniLight3D: c.light_energy*=0.92+0.08*sin(Time.get_ticks_msec()/700.0)
