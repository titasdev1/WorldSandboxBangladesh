extends Node

var world
var timer: Timer

func activate(w):
 world = w
 timer = Timer.new()
 timer.wait_time = 2.35
 timer.autostart = true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 for v in world.get_children():
  if v is CharacterBody3D and v.has_method("enter_player") and not v.occupied and world.player:
   if v.global_position.distance_to(world.player.global_position) < 3.0: v.speed *= 0.98
