extends CanvasLayer

var stats: Label
var mission: Label
var status: Label
var w

func _ready():
 w = get_parent()
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
 hint.text = "TOUCH / WASD • Sprint • E Bargain • FIRE • R Rain"
 hint.position = Vector2(28, 680)
 hint.add_theme_font_size_override("font_size", 16)
 add_child(hint)

 add_touch_button("▲", Vector2(70, 530), Vector2(70, 55), "move_forward")
 add_touch_button("◀", Vector2(5, 585), Vector2(70, 55), "move_left")
 add_touch_button("▼", Vector2(70, 585), Vector2(70, 55), "move_back")
 add_touch_button("▶", Vector2(135, 585), Vector2(70, 55), "move_right")
 add_touch_button("SPRINT", Vector2(35, 645), Vector2(150, 45), "sprint")
 add_touch_button("FIRE", Vector2(1080, 560), Vector2(150, 75), "fire")
 add_touch_button("BARGAIN", Vector2(900, 650), Vector2(150, 55), "interact")
 add_touch_button("RAIN", Vector2(1060, 650), Vector2(150, 55), "rain")

func add_touch_button(label_text: String, pos: Vector2, size: Vector2, action_name: String):
 var b = Button.new()
 b.text = label_text
 b.position = pos
 b.size = size
 b.add_theme_font_size_override("font_size", 18)
 b.button_down.connect(func(): Input.action_press(action_name))
 b.button_up.connect(func(): Input.action_release(action_name))
 add_child(b)

func _process(_delta):
 if not w:
  return
 stats.text = "৳ %d    Wanted: %d/5    Weather: %s" % [w.cash, w.wanted, "RAIN" if w.rain else "CLEAR"]
 if w.mission_active:
  var stage_names = ["Market delivery", "Tower pickup", "Bus terminal drop"]
  mission.text = "MISSION %d/3: %s    Rickshaw fare ৳%d → offer ৳%d" % [w.mission_stage + 1, stage_names[w.mission_stage], w.fare_requested, w.bargain_offer]
 else:
  mission.text = "MISSION COMPLETE  +৳1000   FREE ROAM"
 var ammo_text = "%d/%d" % [w.player.ammo, w.player.reserve_ammo] if w.player else "30/120"
 var reload_text = " • RELOADING" if w.player and w.player.reload_time > 0.0 else ""
 status.text = "NOBORONGO CITY • PLAYABLE CORE • VEHICLES • POLICE • WEATHER\nAMMO %s%s   %s" % [ammo_text, reload_text, w.event_text if w.event_time_left > 0 else "Explore • drive • bargain • fight"]
