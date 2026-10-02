extends Node

var world
var paths: Array[String] = [
  "res://features/feature_001.gd",
  "res://features/feature_002.gd",
  "res://features/feature_003.gd",
  "res://features/feature_004.gd",
  "res://features/feature_005.gd",
  "res://features/feature_006.gd",
  "res://features/feature_007.gd",
  "res://features/feature_008.gd",
  "res://features/feature_009.gd",
  "res://features/feature_010.gd",
  "res://features/feature_011.gd",
  "res://features/feature_012.gd",
  "res://features/feature_013.gd",
  "res://features/feature_014.gd",
  "res://features/feature_015.gd",
  "res://features/feature_016.gd",
  "res://features/feature_017.gd",
  "res://features/feature_018.gd",
  "res://features/feature_019.gd",
  "res://features/feature_020.gd",
  "res://features/feature_021.gd",
  "res://features/feature_022.gd",
  "res://features/feature_023.gd",
  "res://features/feature_024.gd",
  "res://features/feature_025.gd",
  "res://features/feature_026.gd",
  "res://features/feature_027.gd",
  "res://features/feature_028.gd",
  "res://features/feature_029.gd",
  "res://features/feature_030.gd",
  "res://features/feature_031.gd",
  "res://features/feature_032.gd",
  "res://features/feature_033.gd",
  "res://features/feature_034.gd",
  "res://features/feature_035.gd",
  "res://features/feature_036.gd",
  "res://features/feature_037.gd",
  "res://features/feature_038.gd",
  "res://features/feature_039.gd",
  "res://features/feature_040.gd",
  "res://features/feature_041.gd",
  "res://features/feature_042.gd",
  "res://features/feature_043.gd",
  "res://features/feature_044.gd",
  "res://features/feature_045.gd",
  "res://features/feature_046.gd",
  "res://features/feature_047.gd",
  "res://features/feature_048.gd",
  "res://features/feature_049.gd",
  "res://features/feature_050.gd",
  "res://features/feature_051.gd",
  "res://features/feature_052.gd",
  "res://features/feature_053.gd",
  "res://features/feature_054.gd",
  "res://features/feature_055.gd",
  "res://features/feature_056.gd",
  "res://features/feature_057.gd",
  "res://features/feature_058.gd",
  "res://features/feature_059.gd",
  "res://features/feature_060.gd",
  "res://features/feature_061.gd",
  "res://features/feature_062.gd",
  "res://features/feature_063.gd",
  "res://features/feature_064.gd",
  "res://features/feature_065.gd",
  "res://features/feature_066.gd",
  "res://features/feature_067.gd",
  "res://features/feature_068.gd",
  "res://features/feature_069.gd",
  "res://features/feature_070.gd",
  "res://features/feature_071.gd",
  "res://features/feature_072.gd",
  "res://features/feature_073.gd",
  "res://features/feature_074.gd",
  "res://features/feature_075.gd",
  "res://features/feature_076.gd",
  "res://features/feature_077.gd",
  "res://features/feature_078.gd",
  "res://features/feature_079.gd",
  "res://features/feature_080.gd",
  "res://features/feature_081.gd",
  "res://features/feature_082.gd",
  "res://features/feature_083.gd",
  "res://features/feature_084.gd",
  "res://features/feature_085.gd",
  "res://features/feature_086.gd",
  "res://features/feature_087.gd",
  "res://features/feature_088.gd",
  "res://features/feature_089.gd",
  "res://features/feature_090.gd",
  "res://features/feature_091.gd",
  "res://features/feature_092.gd",
  "res://features/feature_093.gd",
  "res://features/feature_094.gd",
  "res://features/feature_095.gd",
  "res://features/feature_096.gd",
  "res://features/feature_097.gd",
  "res://features/feature_098.gd",
  "res://features/feature_099.gd"
]
var index := 0
var timer: Timer

func start(w):
 world = w
 timer = Timer.new()
 timer.wait_time = 0.12
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
 if script and script.can_instantiate():
  var feature = script.new()
  feature.name = path.get_file().get_basename()
  add_child(feature)
  if feature.has_method("activate"):
   feature.activate(world)
