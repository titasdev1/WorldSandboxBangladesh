extends Node

# Cumulative integration runtime for the complete 001-142 development history.
# The playable core is always booted first. Feature modules are then attached
# incrementally so a single bad/slow extension cannot hide the world at startup.

const BOOT_DELAY := 3.0
const FEATURE_INTERVAL := 0.35

var world
var paths: Array[String] = []
var index := 0
var timer: Timer
var boot_timer: Timer
var activated := 0

func _ready():
 for i in range(1, 100):
  paths.append("res://features/feature_%03d.gd" % i)

func start(w):
 world = w
 set_meta("integration_total", paths.size())
 set_meta("integration_activated", 0)
 boot_timer = Timer.new()
 boot_timer.one_shot = true
 boot_timer.wait_time = BOOT_DELAY
 boot_timer.timeout.connect(_begin_feature_activation)
 add_child(boot_timer)
 boot_timer.start()

func _begin_feature_activation():
 timer = Timer.new()
 timer.wait_time = FEATURE_INTERVAL
 timer.autostart = true
 timer.timeout.connect(_activate_next)
 add_child(timer)
 _activate_next()

func _activate_next():
 if index >= paths.size():
  if timer:
   timer.stop()
  set_meta("integration_complete", true)
  set_meta("integration_activated", activated)
  return

 var path = paths[index]
 index += 1
 if not ResourceLoader.exists(path):
  return

 var script = load(path)
 if script == null:
  return

 # Every feature owns its own timer/state. Adding it as a child keeps it in
 # the same canonical scene tree and preserves all earlier gameplay systems.
 var feature = script.new()
 if feature == null:
  return
 feature.name = path.get_file().get_basename()
 add_child(feature)
 if feature.has_method("activate"):
  feature.activate(world)
 activated += 1
 set_meta("integration_activated", activated)
