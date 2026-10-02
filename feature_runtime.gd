extends Node

var world
var paths: Array[String] = []
var index := 0
var active := 0
const MAX_ACTIVE := 12
var timer: Timer

func start(w):
 world = w
 var resources = ResourceLoader.list_directory("res://features")
 for path in resources:
  if path.ends_with(".gd"):
   paths.append("res://features/" + path)
 paths.sort()
 timer = Timer.new()
 timer.wait_time = 0.15
 timer.autostart = true
 timer.timeout.connect(_activate_next)
 add_child(timer)

func _activate_next():
 if index >= paths.size():
  timer.stop()
  return
 var path = paths[index]
 index += 1
 var script = load(path)
 if script and script.can_instantiate() and active < MAX_ACTIVE:
  var feature = script.new()
  feature.name = path.get_file().get_basename()
  add_child(feature)
  if feature.has_method("activate"):
   feature.activate(world)
  active += 1
