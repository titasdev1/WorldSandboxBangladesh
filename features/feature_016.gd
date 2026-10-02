extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=3
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 var sun=world.get_node_or_null("Sun")
 if sun: sun.light_color=Color(1.0,0.82,0.65) if world.day_time>17.0 or world.day_time<7.0 else Color(1,1,1)
