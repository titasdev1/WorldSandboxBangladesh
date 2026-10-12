extends CanvasLayer

var stats: Label
var mission: Label
var status: Label
var w
var settings_panel: PanelContainer
var quality_option: OptionButton
var fps_option: OptionButton
var settings_config := ConfigFile.new()

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
 hint.text = "CIRCULAR MOVE • DRAG RIGHT SIDE TO LOOK • SPRINT • BARGAIN • FIRE • RAIN"
 hint.position = Vector2(28, 680)
 hint.add_theme_font_size_override("font_size", 16)
 add_child(hint)

 # CODM/PUBG-style circular analog movement control replaces the four directional buttons.
 var stick = Control.new()
 stick.set_script(load("res://virtual_stick.gd"))
 stick.name = "MovementStick"
 stick.position = Vector2(24, 472)
 stick.size = Vector2(220, 220)
 stick.add_to_group("movement_stick")
 add_child(stick)
 add_touch_button("SPRINT", Vector2(35, 645), Vector2(150, 45), "sprint")
 add_touch_button("FIRE", Vector2(1080, 560), Vector2(150, 75), "fire")
 add_touch_button("BARGAIN", Vector2(900, 650), Vector2(150, 55), "interact")
 add_touch_button("RAIN", Vector2(1060, 650), Vector2(150, 55), "rain")
 _build_settings_ui()
 _load_graphics_settings()

func _build_settings_ui() -> void:
 var settings_button := Button.new()
 settings_button.text = "SETTINGS"
 settings_button.position = Vector2(1110, 18)
 settings_button.size = Vector2(140, 44)
 settings_button.add_theme_font_size_override("font_size", 17)
 settings_button.pressed.connect(_toggle_settings)
 add_child(settings_button)

 settings_panel = PanelContainer.new()
 settings_panel.name = "GraphicsSettingsPanel"
 settings_panel.position = Vector2(850, 72)
 settings_panel.size = Vector2(400, 340)
 settings_panel.custom_minimum_size = Vector2(400, 340)
 settings_panel.visible = false
 settings_panel.z_index = 30
 add_child(settings_panel)

 var column := VBoxContainer.new()
 column.add_theme_constant_override("separation", 12)
 settings_panel.add_child(column)

 var heading := Label.new()
 heading.text = "GRAPHICS & PERFORMANCE"
 heading.add_theme_font_size_override("font_size", 21)
 column.add_child(heading)

 var quality_label := Label.new()
 quality_label.text = "Graphics quality / 3D render scale"
 column.add_child(quality_label)
 quality_option = OptionButton.new()
 quality_option.add_item("Low • 65% render scale")
 quality_option.add_item("Medium • 80% render scale")
 quality_option.add_item("High • 100% render scale")
 quality_option.add_item("Ultra • 100% + shadows")
 quality_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 quality_option.item_selected.connect(_on_quality_selected)
 column.add_child(quality_option)

 var fps_label := Label.new()
 fps_label.text = "Frame-rate limit (device permitting)"
 column.add_child(fps_label)
 fps_option = OptionButton.new()
 for fps_label_text in ["30 FPS", "60 FPS", "90 FPS", "120 FPS", "144 FPS", "Uncapped"]:
  fps_option.add_item(fps_label_text)
 fps_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 fps_option.item_selected.connect(_on_fps_selected)
 column.add_child(fps_option)

 var note := Label.new()
 note.text = "Higher FPS / resolution needs capable hardware.\nThis limit cannot force unsupported refresh rates."
 note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 note.add_theme_font_size_override("font_size", 14)
 column.add_child(note)

 var close_button := Button.new()
 close_button.text = "DONE"
 close_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 close_button.pressed.connect(func(): settings_panel.visible = false)
 column.add_child(close_button)

func _toggle_settings() -> void:
 if settings_panel:
  settings_panel.visible = not settings_panel.visible

func _load_graphics_settings() -> void:
 var err := settings_config.load("user://graphics_settings.cfg")
 var quality_index := 2
 var fps_index := 1
 if err == OK:
  quality_index = clampi(int(settings_config.get_value("graphics", "quality", 2)), 0, 3)
  fps_index = clampi(int(settings_config.get_value("graphics", "fps_index", 1)), 0, 5)
 quality_option.select(quality_index)
 fps_option.select(fps_index)
 _apply_quality(quality_index)
 _apply_fps(fps_index)

func _on_quality_selected(index: int) -> void:
 _apply_quality(index)
 _save_graphics_settings()

func _on_fps_selected(index: int) -> void:
 _apply_fps(index)
 _save_graphics_settings()

func _apply_quality(index: int) -> void:
 # These settings change real runtime render scale and the world sun/fog.
 var scales := [0.65, 0.80, 1.0, 1.0]
 get_viewport().scaling_3d_scale = scales[clampi(index, 0, 3)]
 var shadows_enabled := index >= 3
 if w:
  var sun := w.get_node_or_null("Sun") as DirectionalLight3D
  if sun:
   sun.shadow_enabled = shadows_enabled
  for child in w.get_children():
   if child is WorldEnvironment and child.environment:
    child.environment.fog_enabled = index >= 1

func _apply_fps(index: int) -> void:
 var limits := [30, 60, 90, 120, 144, 0]
 Engine.max_fps = limits[clampi(index, 0, 5)]

func _save_graphics_settings() -> void:
 settings_config.set_value("graphics", "quality", quality_option.selected)
 settings_config.set_value("graphics", "fps_index", fps_option.selected)
 settings_config.save("user://graphics_settings.cfg")


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

# HUD integrated district/objective layer.
