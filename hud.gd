extends CanvasLayer

var stats: Label
var mission: Label
var status: Label
var w
var settings_panel: PanelContainer
var quality_option: OptionButton
var fps_option: OptionButton
var settings_config := ConfigFile.new()
var _world_quality_applied := false
var lobby_overlay: ColorRect
var selected_mode := "deshi_story"
var mode_buttons: Array[Button] = []

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
 _build_lobby_ui()

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
 # HUD child _ready runs before the world creates its lights/environment.
 # Apply the saved preset once those world nodes actually exist.
 if not _world_quality_applied and w.get_node_or_null("Sun"):
  _apply_quality(quality_option.selected)
  _world_quality_applied = true
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


# First-boot mode lobby: intentionally uses vector UI so it stays crisp at any resolution.
func _build_lobby_ui() -> void:
 lobby_overlay = ColorRect.new()
 lobby_overlay.name = "ModeLobby"
 lobby_overlay.color = Color(0.015, 0.035, 0.065, 0.94)
 lobby_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 lobby_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
 lobby_overlay.z_index = 100
 add_child(lobby_overlay)

 var panel := PanelContainer.new()
 panel.position = Vector2(55, 42)
 panel.size = Vector2(1170, 625)
 panel.add_theme_stylebox_override("panel", _lobby_style(Color(0.035, 0.075, 0.12, 0.98), Color(0.12, 0.68, 0.82, 0.9), 2, 22))
 lobby_overlay.add_child(panel)

 var column := VBoxContainer.new()
 column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 column.size_flags_vertical = Control.SIZE_EXPAND_FILL
 column.add_theme_constant_override("separation", 14)
 panel.add_child(column)

 var eyebrow := Label.new()
 eyebrow.text = "PROJECT A-SQUARE  /  BANGLADESH OPEN-WORLD"
 eyebrow.add_theme_color_override("font_color", Color("#50d7e9"))
 eyebrow.add_theme_font_size_override("font_size", 15)
 column.add_child(eyebrow)

 var heading := Label.new()
 heading.text = "CHOOSE YOUR WORLD"
 heading.add_theme_color_override("font_color", Color("#f4f9ff"))
 heading.add_theme_font_size_override("font_size", 34)
 column.add_child(heading)

 var subheading := Label.new()
 subheading.text = "One city. Five ways to play. Touch controls and graphics settings are available in-game."
 subheading.add_theme_color_override("font_color", Color("#b6c8d9"))
 subheading.add_theme_font_size_override("font_size", 16)
 column.add_child(subheading)

 var cards := HBoxContainer.new()
 cards.size_flags_vertical = Control.SIZE_EXPAND_FILL
 cards.add_theme_constant_override("separation", 12)
 column.add_child(cards)

 var modes := [
  {"id":"deshi_story", "title":"DESHI STORIES", "subtitle":"MISSIONS", "desc":"Deliveries, local jobs, fare bargaining and a connected 3-stage story."},
  {"id":"free_roam", "title":"WORLD ROAM", "subtitle":"FREE EXPLORATION", "desc":"Explore the current city, meet NPCs, use transport and discover side activities."},
  {"id":"survival", "title":"LAST STAND", "subtitle":"SOLO PROTOTYPE", "desc":"Combat foundation for a future battle-royale mode. Not a full battle royale yet."},
  {"id":"arena_training", "title":"ARENA TRAINING", "subtitle":"OFFLINE PROTOTYPE", "desc":"Test movement and shooting. Real online multiplayer and matchmaking are not implemented."},
  {"id":"district_explorer", "title":"DISTRICT EXPLORER", "subtitle":"MAP LEARNING PROTOTYPE", "desc":"Navigation practice in the fictional city. Real Bangladesh map tiles are a later integration."}
 ]
 mode_buttons.clear()
 for mode in modes:
  var card := Button.new()
  card.text = ""
  card.custom_minimum_size = Vector2(205, 245)
  card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
  card.size_flags_vertical = Control.SIZE_EXPAND_FILL
  var card_content := VBoxContainer.new()
  card_content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
  card_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_theme_constant_override("separation", 10)
  card.add_child(card_content)
  var card_title := Label.new()
  card_title.text = mode.title
  card_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
  card_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_title.add_theme_font_size_override("font_size", 18)
  card_title.add_theme_color_override("font_color", Color("#f4f9ff"))
  card_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_title)
  var card_subtitle := Label.new()
  card_subtitle.text = mode.subtitle
  card_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
  card_subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_subtitle.add_theme_font_size_override("font_size", 12)
  card_subtitle.add_theme_color_override("font_color", Color("#50d7e9"))
  card_subtitle.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_subtitle)
  var card_desc := Label.new()
  card_desc.text = mode.desc
  card_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
  card_desc.add_theme_font_size_override("font_size", 14)
  card_desc.add_theme_color_override("font_color", Color("#c4d6e5"))
  card_desc.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_desc)
  card.add_theme_color_override("font_hover_color", Color("#ffffff"))
  card.add_theme_stylebox_override("normal", _lobby_style(Color("#10263a"), Color("#2b5268"), 1, 14))
  card.add_theme_stylebox_override("hover", _lobby_style(Color("#153c52"), Color("#50d7e9"), 2, 14))
  card.add_theme_stylebox_override("pressed", _lobby_style(Color("#14546a"), Color("#50d7e9"), 3, 14))
  card.toggle_mode = true
  card.button_pressed = mode.id == selected_mode
  card.pressed.connect(_select_lobby_mode.bind(mode.id, card))
  cards.add_child(card)
  mode_buttons.append(card)

 var footer := HBoxContainer.new()
 footer.add_theme_constant_override("separation", 16)
 column.add_child(footer)

 var note := Label.new()
 note.text = "ONLINE ROAM / REAL-WORLD MAP / FULL BR MODES: planned, not falsely presented as finished."
 note.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 note.add_theme_color_override("font_color", Color("#a7bacb"))
 note.add_theme_font_size_override("font_size", 13)
 footer.add_child(note)

 var play := Button.new()
 play.text = "ENTER CITY  →"
 play.custom_minimum_size = Vector2(210, 58)
 play.add_theme_font_size_override("font_size", 20)
 play.add_theme_color_override("font_color", Color("#061724"))
 play.add_theme_stylebox_override("normal", _lobby_style(Color("#50d7e9"), Color("#50d7e9"), 1, 12))
 play.add_theme_stylebox_override("hover", _lobby_style(Color("#8beafa"), Color("#ffffff"), 2, 12))
 play.pressed.connect(_enter_selected_mode)
 footer.add_child(play)

func _lobby_style(fill: Color, border_color: Color, border_width: int, corner_radius: int) -> StyleBoxFlat:
 var style := StyleBoxFlat.new()
 style.bg_color = fill
 style.border_color = border_color
 style.set_border_width_all(border_width)
 style.set_corner_radius_all(corner_radius)
 style.content_margin_left = 12
 style.content_margin_right = 12
 style.content_margin_top = 12
 style.content_margin_bottom = 12
 return style

func _select_lobby_mode(mode_id: String, selected_button: Button) -> void:
 selected_mode = mode_id
 for button in mode_buttons:
  button.button_pressed = button == selected_button

func _enter_selected_mode() -> void:
 if w:
  w.game_mode = selected_mode
  if selected_mode == "free_roam":
   w.mission_active = false
   w.event_text = "FREE ROAM SELECTED"
  elif selected_mode == "deshi_story":
   w.mission_active = true
   w.event_text = "DESHI STORIES: FOLLOW THE GOLD MARKER"
  elif selected_mode == "district_explorer":
   w.mission_active = true
   w.event_text = "EXPLORER PROTOTYPE: FOLLOW THE CITY MARKER"
  elif selected_mode == "survival":
   w.mission_active = false
   w.event_text = "SOLO SURVIVAL PROTOTYPE • NO ONLINE PLAY"
  else:
   w.mission_active = false
   w.event_text = "OFFLINE ARENA TRAINING • ONLINE MATCHES NOT AVAILABLE"
  w.event_time_left = 8.0
 if lobby_overlay:
  lobby_overlay.visible = false
