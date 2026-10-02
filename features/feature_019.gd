extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=4.5
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 if world.rain and world.rain_particles and world.rain_particles.process_material: world.rain_particles.process_material.direction=Vector3(sin(Time.get_ticks_msec()/3000.0)*0.35,-1,cos(Time.get_ticks_msec()/3000.0)*0.2).normalized()
