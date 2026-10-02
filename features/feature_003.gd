extends Node

var world
var timer: Timer

func activate(w):
 world = w
 timer = Timer.new()
 timer.wait_time = 2.01
 timer.autostart = true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 var pulse = 0.75 + 0.25 * sin(Time.get_ticks_msec() / 12000.0)
for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player") and not v.occupied:
   v.visible = pulse > 0.72
