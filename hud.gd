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
 hint.text = "TOUCH: left move • right drag camera • Sprint • Jump • Crouch • FIRE"
 hint.position = Vector2(28, 680)
 hint.add_theme_font_size_override("font_size", 15)
 add_child(hint)

 add_touch_button("▲", Vector2(70, 500), Vector2(70, 55), "move_forward")
 add_touch_button("◀", Vector2(5, 555), Vector2(70, 55), "move_left")
 add_touch_button("▼", Vector2(70, 555), Vector2(70, 55), "move_back")
 add_touch_button("▶", Vector2(135, 555), Vector2(70, 55), "move_right")
 add_touch_button("SPRINT", Vector2(35, 615), Vector2(150, 45), "sprint")
 add_touch_button("JUMP", Vector2(205, 615), Vector2(95, 45), "jump")
 add_touch_button("CROUCH", Vector2(305, 615), Vector2(95, 45), "crouch")
 add_touch_button("FIRE", Vector2(1080, 540), Vector2(150, 75), "fire")
 add_touch_button("BARGAIN", Vector2(900, 630), Vector2(150, 45), "interact")
 add_touch_button("RAIN", Vector2(1060, 630), Vector2(150, 45), "rain")
 add_touch_button("SAVE", Vector2(800, 30), Vector2(90, 40), "save_game")
 add_touch_button("LOAD", Vector2(895, 30), Vector2(90, 40), "load_game")

func add_touch_button(label_text: String, pos: Vector2, size: Vector2, action_name: String):
 var b = Button.new()
 b.text = label_text
 b.position = pos
 b.size = size
 b.add_theme_font_size_override("font_size", 16)
 b.button_down.connect(func(): Input.action_press(action_name))
 b.button_up.connect(func(): Input.action_release(action_name))
 add_child(b)

func _process(_delta):
 if not w:
  return
 stats.text = "৳ %d    HP: %d    Wanted: %d/5    %s" % [w.cash, w.player.health if w.player else 100, w.wanted, "RAIN" if w.rain else "CLEAR"]
 if w.mission_active:
  var stage_names = ["Market delivery", "Tower pickup", "Bus terminal drop"]
  mission.text = "MISSION %d/3: %s    Rickshaw ৳%d → offer ৳%d" % [w.mission_stage + 1, stage_names[w.mission_stage], w.fare_requested, w.bargain_offer]
 else:
  mission.text = "MISSION COMPLETE  +৳1000   FREE ROAM"
 status.text = "Noborongo City • 3D third-person • 45 NPCs • traffic • police • camera drag"
