extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=2.6500000000000004; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.player:
  var moving=world.player.velocity.length()>0.5
  var stamina=float(world.player.get_meta("stamina",100.0))
  stamina=clamp(stamina-(0.9 if moving else -1.2),0.0,100.0)
  world.player.set_meta("stamina",stamina)
  if stamina<5.0: world.player.velocity.x*=0.5; world.player.velocity.z*=0.5
