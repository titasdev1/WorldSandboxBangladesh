extends Node

var world
var timer: Timer

func activate(w):
 world=w
 timer=Timer.new()
 timer.wait_time=4
 timer.autostart=true
 timer.timeout.connect(_tick)
 add_child(timer)

func _tick():
 if not world or not is_instance_valid(world): return
 if world.rain and world.rain_particles: world.rain_particles.amount = 450 + int(350.0*(0.5+0.5*sin(Time.get_ticks_msec()/7000.0)))
