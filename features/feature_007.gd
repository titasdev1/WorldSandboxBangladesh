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
 var npcs=[]
 for n in world.get_children():
  if n is CharacterBody3D and str(n.name).begins_with("NPC_"): npcs.append(n)
 for a in npcs:
  for b in npcs:
   if a!=b and a.global_position.distance_to(b.global_position)<1.2: a.velocity *= 0.5
