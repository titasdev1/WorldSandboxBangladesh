extends CanvasLayer

var stats: Label
var mission: Label
var status: Label

func _ready():
 var title = Label.new()
 title.text = "WORLD SANDBOX: BANGLADESH"
 title.position = Vector2(28, 20)
 title.add_theme_font_size_override("font_size", 28)
 add_child(title)

 stats = Label.new()
 stats.position = Vector2(28, 62)
 stats.add_theme_font_size_override("font_size", 20)
 add_child(stats)

 mission = Label.new()
 mission.position = Vector2(28, 104)
 mission.add_theme_font_size_override("font_size", 18)
 add_child(mission)

 status = Label.new()
 status.position = Vector2(28, 142)
 status.add_theme_font_size_override("font_size", 16)
 add_child(status)

 var hint = Label.new()
 hint.text = "WASD / TOUCH • SHIFT Sprint • E Bargain • FIRE • R Rain"
 hint.position = Vector2(28, 680)
 hint.add_theme_font_size_override("font_size", 16)
 add_child(hint)

 add_touch_button("MOVE", Vector2(40, 555), Vector2(140, 75), "")
 add_touch_button("FIRE", Vector2(1080, 560), Vector2(150, 75), "fire")
 add_touch_button("INTERACT", Vector2(910, 650), Vector2(150, 55), "interact")
 add_touch_button("RAIN", Vector2(1060, 650), Vector2(150, 55), "rain")

func add_touch_button(label_text: String, pos: Vector2, size: Vector2, action_name: String):
 var b = Button.new()
 b.text = label_text
 b.position = pos
 b.size = size
 b.add_theme_font_size_override("font_size", 18)
 if action_name != "":
  b.pressed.connect(func(): Input.action_press(action_name))
  b.button_up.connect(func(): Input.action_release(action_name))
 add_child(b)

func _process(_delta):
 var w = get_parent()
 if not w:
  return
 stats.text = "৳ %d    Wanted: %d/5    Weather: %s" % [w.cash, w.wanted, "RAIN" if w.rain else "CLEAR"]
 if w.mission_active:
  var stage_names = ["Market delivery", "Tower pickup", "Bus terminal drop"]
  mission.text = "MISSION %d/3: %s    Fare: ৳%d → offer ৳%d" % [w.mission_stage + 1, stage_names[w.mission_stage], w.fare_requested, w.bargain_offer]
 else:
  mission.text = "MISSION COMPLETE  +৳1000   Free Roam unlocked"
 status.text = "Noborongo City • Rickshaw • CNG • Cars • Buses • Police • 45 NPCs"
