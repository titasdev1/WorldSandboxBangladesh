extends CanvasLayer
var stats:Label
var mission:Label
func _ready():
 var title=Label.new()
 title.text="WORLD SANDBOX: BANGLADESH"
 title.position=Vector2(28,22)
 title.add_theme_font_size_override("font_size",28)
 add_child(title)
 stats=Label.new()
 stats.position=Vector2(28,62)
 stats.add_theme_font_size_override("font_size",20)
 add_child(stats)
 mission=Label.new()
 mission.position=Vector2(28,105)
 mission.add_theme_font_size_override("font_size",18)
 add_child(mission)
 var hint=Label.new()
 hint.text="WASD • E Bargain • Click Fire • R Rain"
 hint.position=Vector2(28,680)
 add_child(hint)
func _process(_delta):
 var w=get_parent()
 if w:
  stats.text="৳ %d     Wanted: %d     Rain: %s" % [w.cash,w.wanted,"ON" if w.rain else "OFF"]
  mission.text="MISSION: Reach the market marker • %s" % ["COMPLETE +৳500" if not w.mission_active else "DELIVER PACKAGE"]
