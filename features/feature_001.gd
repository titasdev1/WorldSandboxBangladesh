extends Node

var world
var timer: Timer

func activate(w):
 world = w
 timer = Timer.new()
 timer.wait_time = 1.67
 timer.autostart = true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player") and not v.occupied:
   v.speed = clamp(v.speed * (0.96 + 0.08 * sin(Time.get_ticks_msec() / 5000.0)), 2.0, 12.0)
