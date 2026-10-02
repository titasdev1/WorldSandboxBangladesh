extends Node
var world
var timer:Timer
func activate(w):
 world=w
 timer=Timer.new(); timer.wait_time=6.0; timer.autostart=true; timer.timeout.connect(_tick); add_child(timer)
func _tick():
 if not world or not is_instance_valid(world): return
 if world.player:
  var cam=world.player.get_node_or_null("CameraPivot/ThirdPersonCamera")
  if cam: cam.fov=lerp(cam.fov,68.0,0.08)
