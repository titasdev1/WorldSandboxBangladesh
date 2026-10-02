extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=2
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 if world.wanted>0 and world.player:
  for n in world.get_children():
   if n is CharacterBody3D and str(n.name).begins_with("NPC_"):
    if n.global_position.distance_to(world.player.global_position)<10.0: n.velocity = (n.global_position-world.player.global_position).normalized()*n.walk_speed
