extends Node

var world
const FEATURE_PATHS = [
  "res://features/feature_001.gd",
  "res://features/feature_002.gd",
  "res://features/feature_003.gd",
  "res://features/feature_004.gd"
]

func start(w):
 world = w
 for path in FEATURE_PATHS:
  var script = load(path)
  if script:
   var feature = script.new()
   feature.name = path.get_file().get_basename()
   add_child(feature)
   feature.activate(world)
