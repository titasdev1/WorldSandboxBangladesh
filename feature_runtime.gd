extends Node

var world

func start(w):
 world = w
 var dir = DirAccess.open("res://features")
 if not dir:
  return
 var paths = dir.get_files()
 paths.sort()
 for path in paths:
  if not path.ends_with(".gd"):
   continue
  var script = load("res://features/" + path)
  if script:
   var feature = script.new()
   feature.name = path.get_file().get_basename()
   add_child(feature)
   if feature.has_method("activate"):
    feature.activate(world)
