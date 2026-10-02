extends Node

var world
var timer: Timer

func activate(w):
 world = w
 timer = Timer.new()
 timer.wait_time = 1.84
 timer.autostart = true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player") and not v.occupied:
   if v.lane_axis == "z": v.position.x = lerp(v.position.x, round(v.position.x / 1.8) * 1.8, 0.05)
   else: v.position.z = lerp(v.position.z, round(v.position.z / 1.8) * 1.8, 0.05)
